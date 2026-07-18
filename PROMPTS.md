# Prompt Changelog

Prompts are software artifacts. Every prompt lives as a file in `prompts/` —
never inline-only — and **every change gets a line here**: what changed, why,
and the observed effect. BC2's write-up must cite at least two entries.

Format: `YYYY-MM-DD · file · what changed · why · observed effect`


2026-07-13 · bc1-agent-system.txt · (seed) initial system prompt from template · starting point · agent answers but tool JSON occasionally wrapped in prose
2026-07-15 · bc1-agent-system.txt · added tool preference guidance: prefer search_notes_snippet over search_notes_verbose; added write_note and word_count usage hints · BC1 requirement — steer model toward efficient tools and enable note-writing tasks · model now consistently chooses snippet search over verbose; write_note used correctly for disclosure output
2026-07-17 · bc2-retriever.txt · new JIT keyword extraction prompt used in fixed_task.py · drives the keyword-filter tool so only relevant documents are retrieved before the analyst call · retriever correctly returns domain keywords
2026-07-17 · bc2-analyst.txt · added policy status rules (marked IMPORTANT) to ignore stale policies, not cite them when no relevant non-stale policy exists, nor blend policies for compliance requirements · agent should ignore any out-of-date policies when determining compliance · out of date policies are ignored
2026-07-17 · bc2-retriever.txt · expanded keyword count from 5-12 to 8-15; added explicit instruction to cover every distinct concern in the question (approvals, logging, runtime, AND access/credentials); added concrete operational terms like "credentials", "shared storage", "sign-off", "write access" · fix for AS-24 (Shared Drive Access) being missed when retriever keywords were too narrow · retriever now reliably returns shared-drive/credential terms that score AS-24 into the filtered set
2026-07-17 · bc2-analyst.txt · added answer-completeness section requiring the analyst to address all four dimensions: approvals, logging/audit, max runtime, AND access/credential requirements · fix for analyst silently dropping AS-24 even when it was present in the filtered context · analyst now explicitly covers shared drive credential requirements and data-owner sign-off from AS-24
