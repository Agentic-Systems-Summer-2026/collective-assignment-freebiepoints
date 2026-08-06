# Git-to-Product Release Notes Agent

A stateful, multi-agent Python pipeline that translates technical Git commit data into audience-specific release notes. Utilizing a Tool-Augmented ReAct (Reasoning + Acting) architecture, the system autonomously queries issue trackers and inspects source code to generate precise technical patch notes and jargon-free user changelogs.

## Features
* **Hybrid Tool-Calling Pipeline:** Automatically fetches a token-optimized Git diff baseline before dynamically deciding which follow-up tools to run (issue lookups or deep-dive code inspections).
* **Multi-Language Code Inspection:** Capable of extracting target functions and methods from a variety of languages (Python, JavaScript, Kotlin, etc.) utilizing generalized regex and brace-block counting.
* **Dual-Agent Drafting:** Separates technical and user-facing generation to guarantee non-technical purity in product marketing updates.
* **Deterministic Guardrails:** Uses a strict Python regex linter to block code symbols or file paths from leaking into user-facing copy.

## Prerequisites
* Python 3.9+
* A local clone of the target repository (default: `collective-assignment-freebiepoints`).
* A configured LLM provider via the `common.llm` wrapper.

## Usage

The primary entry point is the orchestrator script, `agent.py`. It requires a target Git commit hash and the corresponding commit message.

### Basic Execution
```bash
python3 agent_2.py <commit_hash> "<commit_message>"
```

### Advanced Arguments & Overrides

You can override default paths for the target repository or the mock issue tracker using command-line flags:
```bash
python3 agent_2.py <commit_hash> "<commit_message>" --repo /path/to/repo --issues /path/to/issues.json
```

### Available Flags:
* `commit_hash`: (Required) The SHA of the commit you wish to profile.
* `commit_message`: (Required) The raw commit message string.
* `--repo`: (Optional) Overrides the TARGET_REPO_PATH environment variable.
* `--issues`: (Optional) Overrides the MOCK_ISSUES_PATH environment variable.

### Environment Variables
* `AUTO_APPROVE_HITL=1`: Bypasses the synchronous Human-in-the-Loop terminal prompt, automatically writing generated artifacts to disk. Ideal for automated evaluation harnesses.

## Profiling Commit Tokens

To evaluate the token efficiency of the deterministic Git diff summarizer against a raw git show payload, use the included profiling script:  
```bash
python3 profile_tokens.py <commit_hash>
```
This will output the estimated token payload reduction percentage before it is fed to the Context Triage Agent.

## Generated Artifacts & State Files

When the agent executes successfully, it interacts with several local files:
* `user_changelog.md`: The final, non-technical release notes intended for end-users.
* `technical_patch_notes.md`: The detailed internal engineering notes.
* `agent_audit.jsonl`: An append-only log recording tool-call counts, validation errors, and execution timestamps for post-mortem analysis.
* `rejected_patterns.json`: An adaptive memory store that logs regex linter failures, allowing the agent to learn and avoid rejected phrasing on subsequent runs.