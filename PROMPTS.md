# Prompt Changelog

Prompts are software artifacts. Every prompt lives as a file in `prompts/` —
never inline-only — and **every change gets a line here**: what changed, why,
and the observed effect. BC2's write-up must cite at least two entries.

Format: `YYYY-MM-DD · file · what changed · why · observed effect`

| Date | Prompt file | What changed | Why | Observed effect |
|---|---|---|---|---|
| 2026-07-13 | bc1-agent-system.txt | (seed) initial system prompt from template | starting point | agent answers but tool JSON occasionally wrapped in prose |
| 2026-07-16 | bc1-agent-system.txt | added tool preference guidance: prefer search_notes_snippet over search_notes_verbose; added write_note and word_count usage hints | BC1 requirement — steer model toward efficient tools and enable note-writing tasks | model now consistently chooses snippet search over verbose; write_note used correctly for disclosure output |
