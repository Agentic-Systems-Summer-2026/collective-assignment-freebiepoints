# Deployment-Readiness Checklist & Production Architecture

## 1. Current Environment (Codespaces / Development Build)
* **Execution Host:** GitHub Codespaces (Ephemeral container environment).
* **LLM Provider:** Configured via `common.llm` routing (OU LiteLLM Sandbox / OpenRouter).
* **Context Storage:** Local file system (`issues.json`, local Git diffs via `subprocess`).
* **Adaptive Memory & State:** Local JSON files (`rejected_patterns.json`, `agent_audit.jsonl`).
* **Human-in-the-Loop (HITL):** Synchronous terminal `input()` block before writing files to disk. 
* **Observability:** Ephemeral `STATS` dictionary printed to standard output at the end of execution.

## 2. Production Deployment Requirements

To transition this agentic pipeline from a local capstone build to an enterprise production service, the following architectural upgrades are required:

### A. Hosting & Infrastructure
* **Async Event-Driven Triggers:** Replace CLI execution with a GitHub App webhook listener or GitLab Pipeline runner triggered on Pull Request merge / commit events.
* **Compute Layer:** Host orchestrator and worker nodes on serverless compute (AWS Lambda, Google Cloud Run) or asynchronous task queues (Celery / Redis).

### B. Live Data & Integration APIs
* **Issue Tracker Integration:** Replace `mock_issue_lookup` and local `issues.json` with authenticated OAuth2 API calls to Jira, Linear, or GitHub Issues.
* **Git Repository Hosting:** Fetch diffs via GitHub/GitLab REST or GraphQL APIs rather than local `git diff-tree` subprocess calls on disk.

### C. Asynchronous Human-in-the-Loop (HITL)
* **Distributed State Approvals:** Replace the blocking CLI `input()` gate with an asynchronous approval state. The agent must halt execution, persist its context to a database, and trigger an external notification (e.g., an interactive Slack message or GitHub environment approval). The write-to-disk operation will only resume upon receiving an authenticated webhook callback from the human reviewer. 

### D. Observability & Token Economics
* **Telemetry Streaming:** Replace local `STATS` printing with an OpenTelemetry-compatible instrumentation layer (integrating with tools like Langfuse, Braintrust, or Datadog). 
* **Cost Governance:** Implement structured logging to track token usage, trace execution paths, and set automated budget alerts to prevent runaway loops from exhausting API funds. 

### E. Enterprise Security & Access Control
* **Secrets Management:** Secure API keys and tokens in AWS Secrets Manager or HashiCorp Vault instead of environment variables.
* **Prompt Injection Protection:** Enforce strict input sanitization at the API gateway layer before passing untrusted commit messages or ticket descriptions to LLMs.