# BC1 Write-Up — Tool/Function Calling

---

## 1. Tool Specs and Design Rationale

The starter agent shipped with four tools: `list_notes`, `search_notes_verbose`,
`read_note`, and `finish`. I added three new tools.

---

### `search_notes_snippet`
```json
{"tool": "search_notes_snippet", "query": "x"}
-> [{"file": "...", "line": N, "snippet": "..."}]
```
**Why:** `search_notes_verbose` returns the full text of every matching document.
That works, but it's wasteful — the model gets hundreds of chars of context it
didn't ask for. `search_notes_snippet` scans line by line and returns only the
lines that matched, along with the filename and line number. The model gets
exactly what it needs to decide whether to `read_note` for more detail. The
design follows the principle from the course reading: *tool descriptions matter
as much as prompts* — so the spec labels the verbose version `[WASTEFUL]` and
describes what snippet returns in concrete terms, not abstract ones.

---

### `word_count`
```json
{"tool": "word_count", "name": "<file>"}   -> {"file": "...", "words": N, "chars": N}
{"tool": "word_count"}                     -> {"file1": {"words": N, "chars": N}, ...}
```
**Why:** Two uses. First, it's a genuine task tool — a model that needs to find
the longest note, enforce a word limit, or report note sizes has a clean way to
do it without reading every file. Second, it's a measurement instrument: running
it against both search tools' outputs gives hard char counts for the before/after
comparison. Making `name` optional (omit it → all notes) keeps the interface
minimal; one parameter covers both the single-file and all-notes cases.

---

### `write_note`
```json
{"tool": "write_note", "name": "<file>", "content": "<text>"}
-> "OK: wrote N chars to <file>"
```
**Why:** Without this tool the agent can only read and answer. Adding `write_note`
lets it produce a tangible artifact — a summary file, a disclosure log, a key
points doc — and persist it for the user. It also closes the loop on the
disclosure use case: the agent used tools to read the notes, synthesized the
result, and saved it, all without any extra scripting outside the tool loop.
The implementation guards against path traversal by stripping to basename only.

---

## 2. Full Trace

**Task:** `"Find my longest note and summarize its key points in 50 words or less"`

```
── step 1: request≈1629 chars → chose word_count {}
           tool returned 315 chars
── step 2: request≈1980 chars → chose list_notes {}
           tool returned 141 chars
── step 3: request≈2157 chars → chose read_note {'name': 'demo_summary.txt'}
           tool returned 402 chars
── step 4: request≈2622 chars → chose write_note {'name': 'demo_summary_key_points.txt'}
           tool returned 50 chars
── step 5: request≈2988 chars → chose finish {}

ANSWER: Identified demo_summary.txt as the longest note (62 words) and created
a 50-word summary of its key points about the helpdesk ticket triage agent demo.

STATS: {'calls': 5, 'tokens': 3334, 'cache_hits': 0}
```

**Step-by-step reasoning:**

- **Step 1 — `word_count` (no name):** The model needed to find the longest note
  without reading all of them first. Calling `word_count` with no argument returned
  sizes for all 7 notes in one shot (315 chars). It identified `demo_summary.txt`
  at 62 words / 402 chars as the longest.
- **Step 2 — `list_notes`:** Slight redundancy here — the model had filenames from
  `word_count` already, but called `list_notes` to confirm the directory contents
  before committing to a read. Cautious but harmless.
- **Step 3 — `read_note`:** Full text of `demo_summary.txt` fetched (402 chars).
- **Step 4 — `write_note`:** Model synthesized the summary and saved it as
  `demo_summary_key_points.txt` rather than just answering inline. It used the
  tool unprompted — the spec said it was available and the task implied a
  deliverable.
- **Step 5 — `finish`:** One-sentence summary confirming what was done.

**Saved output (`demo_summary_key_points.txt`):**
> Capstone demo: Helpdesk ticket triage agent. Key points: Human approval gates,
> keyword-only retrieval due to OpenRouter constraints, live run with visible
> trace, 8-minute time limit. Developed in Codespace starter environment.

---

## 3. Before/After Token Comparison

Query used: `"agent"` (appears across multiple notes — maximizes the gap).

| Tool | Result size | Notes |
|---|---|---|
| `search_notes_verbose` | **1,899 chars** | Full text of every matching document |
| `search_notes_snippet` | **1,513 chars** | Matching lines only, with file + line number |
| **Reduction** | **386 chars (20.3% smaller)** | |

The verbose tool returned complete document text for every note containing
"agent" — including surrounding context the model didn't need. The snippet tool
returned only the lines that matched. The gap is 20% here with 7 small notes;
it grows proportionally as notes get longer or the collection gets larger, since
verbose scales with document size while snippet scales with match count.

**word_count output** (the measurement tool at work):
```json
{
  "demo_summary.txt":          {"words": 62, "chars": 402},
  "AI_disclosure.txt":         {"words": 50, "chars": 400},
  "standup-notes.txt":         {"words": 50, "chars": 308},
  "reading-summary.txt":       {"words": 33, "chars": 231},
  "demo_summary_key_points.txt":{"words": 30, "chars": 226},
  "capstone-brainstorm.txt":   {"words": 47, "chars": 296},
  "capstone-demo-summary.txt": {"words": 23, "chars": 147}
}
```

This is the same output the model saw in step 1 of the trace — 315 chars to
size all 7 notes, vs. reading every file individually which would have cost
~2,000+ chars of tool results.

---

## 4. Delegation Log

**AI used:** OpenClaw (Claude Sonnet 4.6 via LiteLLM)

**My key prompts:**

1. *"I thought a word_count tool would be useful for evaluating tool
   efficiency/conciseness. What tools could we build to help generate a summary
   for AI usage and disclosure?"*
   — This is where the tool set came from. I had `word_count` in mind; the AI
   suggested that char count would be more precise than word count for token
   comparisons, and turned my disclosure idea into two concrete tools:
   `search_notes_snippet` and `write_note`.

2. *"Let's implement it"*
   — The AI wrote the full updated `agent.py`, the revised system prompt, and
   the `PROMPTS.md` entry in one pass. I reviewed the code and watched both
   test runs execute live.

3. *"Let's go through what was done and build a draft together"*
   — Used to build the journal entry. I answered four questions about what I
   planned, what surprised me, what failed, and how I verified the output; the
   AI drafted the entry in my voice from those answers.

**One thing the AI got wrong:**

The AI described my original intent for the disclosure tools as wanting to
"generate my write-up text." That's not quite right — I wanted tools that could
*assist* with generating an AI disclosure summary, not write the whole write-up.
The framing in the first journal draft made it sound more passive than it was.
I caught it while reviewing the draft and corrected the wording to better
reflect that I came in with a specific idea (`word_count`) and the collaboration
shaped how it got implemented.

**How I verified:**
Reviewed all code changes before committing, watched both test runs execute with
live traces, and checked the output files (`AI_disclosure.txt`,
`capstone-demo-summary.txt`, `demo_summary_key_points.txt`) to confirm correct
content and format.
