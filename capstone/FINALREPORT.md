# Git-to-Product Release Notes Agent

Jonathan Russell  
SDI-4243  
August 6, 2026

## Executive Summary
The Git-to-Product Release Notes Agent is a stateful, multi-agent pipeline designed to translate Git commit data into audience-specific release notes. One of the core challenges in this capstone was preventing "context-bleeding", where technical jargon inevitably leaks into user-facing product documentation when an LLM is exposed to raw source code. To solve this, the project implemented a Tool-Augmented ReAct (Reasoning + Acting) architecture that utilizes dual-agent drafting, token-optimization, and deterministic guardrails to ensure output reliability and non-technical purity.

## System Architecture
The system operates in three phases:

### Context Gathering (Hybrid Pipeline)
The orchestrator uses a two-phase context-gathering approach to balance efficiency with autonomous reasoning
- **Deterministic Baseline** - The system first fetches a token-optimized commit diff using `get_commit_diff_summary`. This tool strip raw code from the Git diff, returning a JSON object containing only modified filenames, altered function signatures, and line deltas. This creates a baseline of facts before the LLM takes over.
- **Autonomous ReAct Loop** - The Context Triage Agent enters a prompt-based ReAct loop, dynamically choosing whether to query the issue tracker (`mock_issue_lookup`) or inspect specific functions (`inspect_code_function`). To avoid infinite reasoning cycles, the agent is limited to a maximum of 8 loops per commit.

### Role-based Drafting
- **Technical Writer Agent** - Receives the complete technical context, such as filenames, functions and code snippets, to draft detailed internal/technical customer patch notes.
- **User Product Agent** -  Receives only the business context, ticket details/user stories, to draft the user-facing changelog. Raw code is strictly withheld from this agent to prevent context-bleeding, guaranteeing non-technical purity.

### Validation and Learning
The user changelog passes through a deterministic regex linter, `enforce_user_product_linter`. If technical jargon is detected, the failure pattern is appended to the adaptive memory store `rejected_patterns.json`, and the agent rewrites the draft using the memory store as a negative constraint.

## Key Engineering Decisions and Trade-Offs
- **Deterministic vs. Pure Autonomy vs. Hybrid Tool-Calling** - Pure autonomy is token-heavy and could lead to stalling if the agent doesn't orient itself in the repository, while a deterministic tool order could prevent the agent from picking up on vital context necessary for accurate patch notes. By hardcoding the initial diff summary, the LLM only spends its token-heavy loops making high-level decisions rather than wasting cycles on basic repository orientation.
- **Token Efficiency vs. Context Completeness** - Passing raw Git diffs for a multi-file PR rapidly exhausts the LLM context window and increases hallucination rates. Summarizing diffs into structured JSON sacrifices visibility of minor syntax tweaks but significantly reduces input tokens, allowing the agent to process larger commits.
- **Deterministic Linting vs. LLM-as-a-Judge** - An LLM critic is flexible but computationaly expensive. A regex linter is token-free and provides a deterministic guarantee that specific patterns and jargon never reach the final output.
- **Mock Data vs. Live External APIS** -  A local `mock_issue_lookup` JSON store was used instead of live ticketing APIs to control scope and maintain focus on agentic reasoning.

## Outcomes and Achievements
- **Multi-Language Code Extraction** - inspect_code_function was originally Python specific but has been refactored to be language-agnostic. It now uses multi-language declaration matching and brace-block counting to extract syntax from languages like Python, JavaScript, C, C++, etc.
- **Adaptive Memory Integration** - The implementation of `rejected_patterns.json` allows the agent to learn from failures, improving first-pass accuracy over time by avoiding previous violations.
- **Graceful Degradation** - The system has a deterministic fallback (`_build_deterministic_summary`) if the LLM fails validation or the ReAct loop times out.

## Future Development
- **Asynchronous HITL** - Replace the blocking CLI input() gate with an asynchronous approval method (eg. GitHub environment approval or Slack integration)
- **Dynamic Loop Constaints** - Replace static MAX_LOOPS cap with a dynamic bounding function based on commit size.
- **Live Issue Tracker API Integration** - Replace the local `mock_issue_lookup` with API calls to live ticketing systems such as Jira, Linear, or GitHub Issues to fetch real-time context.
- **Remote Repository API Integration** -Transition from using local Git commands to fetching diffs and code-snippets directly from remote repositories via GitHub APIs.