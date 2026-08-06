# System Architecture: Git-to-Product Release Notes Agent

## 1. System Overview & Execution Flow
The system is a stateful, multi-agent Python pipeline that translates technical Git commit data into audience-specific release notes. It operates in three distinct phases: context gathering, specialized drafting, and deterministic validation.

**Execution Pipeline:**
*   **Ingestion:** A Python orchestrator script reads a target commit hash from the local collective-assignment-freebiepoints repository.
*   **Context Gathering (Hybrid Pipeline):** The orchestrator utilizes a two-phase process. Phase 1 is a Deterministic Baseline where it automatically fetches a token-optimized commit diff. Phase 2 is an Autonomous ReAct Loop where the Context Triage Agent dynamically chooses whether to query the issue tracker or inspect specific code functions.
*   **Role-Based Drafting:** The gathered context payload is split. The Technical Writer Agent receives raw technical diffs to draft patch notes. The User Product Agent receives only business context (no code) to draft the user changelog.
*   **Validation & Learning:** The user changelog passes through a deterministic Python regex linter. If technical jargon is detected, the draft is rejected, the failure pattern is logged to rejected_patterns.json, and the User Product Agent rewrites the draft.
*   **Output:** Validated Markdown files are saved to disk.

## 2. Component Specifications

### 2.1 The Agentic Core
*   **The Orchestrator / Router (Prompt-Based ReAct Loop):** A lightweight Python loop leveraging Claude-Sonnet (via common.llm). Because the provided wrapper lacks native API tool-calling support, the system utilizes a Prompt-Based ReAct (Reasoning + Acting) loop. It maintains conversational state, injects tool schemas directly into the system prompt, and manually parses the LLM's raw text output for JSON execution blocks.
*   **State Management:** An in-memory dictionary tracking the current commit being processed, the accumulated context payload, and a hardcoded counter limiting the agent to a maximum of 8 loops per commit to prevent infinite loops and allow sufficient multi-step reasoning.

### 2.2 Tool Interfaces
*   `get_commit_diff_summary(commit_hash)`: Parses raw Git diffs into a compressed JSON object containing only modified filenames, altered function signatures, and line deltas.
*   `mock_issue_lookup(ticket_id)`: Queries a local issues.json store to return user stories and business requirements.
*   `inspect_code_function(file_path, function_name)`: Returns a specific code block for deep-dive technical context, utilizing language-agnostic multi-language declaration matching and brace-block extraction.
*   `write_documentation_artifact(type, content)`: Triggers the linter and saves the final Markdown to disk.

### 2.3 Adaptive Memory Store
*   `rejected_patterns.json`: A persistent local file that stores historical linter failures. This is injected into the User Product Agent's system prompt as a dynamic "Negative Few-Shot" list to improve first-pass accuracy over time.

## 3. Key Architectural Trade-Offs

**Trade-Off 1: Token Efficiency vs. Context Completeness**
*   **The Design Choice:** Implementing get_commit_diff_summary to aggressively strip raw code out of Git diffs before passing them to the agent.
*   **The Defense:** Passing raw Git diffs for a multi-file PR rapidly exhausts the LLM context window and increases hallucination rates. By summarizing the diffs into structured JSON (files changed, functions altered), we sacrifice the visibility of minor syntax tweaks but gain a significant reduction in input tokens, enabling the agent to process significantly larger commits without crashing.

**Trade-Off 2: Multi-Agent Slicing vs. Single-Agent Prompting**
*   **The Design Choice:** Routing data to two separate agents (User Product vs. Technical Writer) rather than asking one agent to output both formats.
*   **The Defense:** Using a single agent is faster and cheaper (lower latency/API calls). However, LLMs suffer from "context bleeding"—if a model sees technical code in its prompt, it will inevitably leak jargon into the user-facing output. By physically separating the agents and withholding the raw code payload from the User Product Agent entirely, we guarantee non-technical purity at the architectural level.

**Trade-Off 3: Deterministic Linting vs. LLM-as-a-Judge**
*   **The Design Choice:** Using a hardcoded Python regex linter for the primary validation gate instead of asking a Critic Agent to evaluate the draft.
*   **The Defense:** LLM critics are flexible but non-deterministic and computationally expensive. A Python regex linter checking for snake_case, .py extensions, and SQL keywords is instant, costs zero tokens, and provides an absolute, deterministic guarantee that specific jargon will never reach the final output. The LLM is strictly reserved for generative tasks, while traditional code handles the rigid constraints.

**Trade-Off 4: Mock Data vs. Live External APIs (Jira/Linear)**
*   **The Choice:** Building a local `mock_issue_lookup` JSON store instead of integrating directly with live ticketing APIs like Jira or GitHub Issues.
*   **The Defense:** We made this choice for three critical reasons: 1) Scope control for a 4-week sprint (avoiding OAuth flows and rate limits); 2) Deterministic evaluation to prove the agent is learning over time in a stable testing environment; and 3) Keeping the focus on agentic reasoning rather than traditional API authentication plumbing.

**Trade-Off 5: Hybrid Tool-Calling vs. Pure Autonomy**
*   **The Choice:** Enforcing a deterministic fetch of `get_commit_diff_summary` to build a baseline before granting the LLM autonomy, rather than starting from a blank state.
*   **The Defense:** Pure autonomy is token-heavy and prone to stalling if the model fails to orient itself in the repository. By hardcoding the initial diff summary, we guarantee a highly compressed, token-efficient baseline of facts. The LLM only spends its expensive autonomous loops making high-level decisions (like fetching business context or inspecting specific functions) rather than wasting cycles on basic repository orientation.