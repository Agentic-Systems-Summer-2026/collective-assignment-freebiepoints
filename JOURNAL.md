# Build Journal

One short entry per build — all five Build Challenges plus the smaller daily
builds. Four to eight sentences each: this is a lab notebook, not an essay.
It is also your AI-use disclosure record for the course. Graded on
completeness and honesty about failures, not polish. (50 pts, due Aug 6.)

Template per entry:

## Day N — <build name>
- **What I built:**
- **What failed:**
- **What I changed:**
- **Where AI helped, and how I verified its output:**

---

## Day 1 — Lab 0 (example format; replace with your own)
- **What I built:** connected my Codespace to OpenRouter and ran the end-to-end demo.
- **What failed:** didn't notice any failures
- **What I changed:** NA
- **Where AI helped, and how I verified its output:** 

---

## BC1 — Tool/Function Calling
- **What I built:** Extended the starter `agent.py` with three new tools: `word_count` (returns word and char counts for one note or all notes), `search_notes_snippet` (token-efficient search returning only matching lines with file and line number instead of full document text), and `write_note` (saves agent-generated output back to the data folder). Also updated the system prompt to steer the model toward the efficient tools.
- **What failed:** Nothing broke outright. My original idea was to use the AI disclosure tools to help generate my write-up text, but the agent interpreted the task more literally — it read and summarized the notes in the data folder and wrote the disclosure there. Useful, just not what I had in mind.
- **What I changed:** Added three tools to both `TOOLS_SPEC` and `run_tool` so the model could discover and call them. Updated `prompts/bc1-agent-system.txt` to explicitly prefer `search_notes_snippet` over the verbose version and to guide use of `write_note` for saving output. Logged the prompt change in `PROMPTS.md`.
- **Where AI helped, and how I verified its output:** I came into this knowing I wanted a `word_count` tool to measure tool efficiency. The AI pointed out that char count would be more precise than word count for token comparisons, and turned my idea of using tools for AI disclosure generation into two concrete tools: `write_note` and `search_notes_snippet`. I collaborated on the design, let the agent write the code, then reviewed the code changes myself and watched both test runs execute live. I checked the output files (`AI_disclosure.txt`, `capstone-demo-summary.txt`) to confirm they were correct. One thing that surprised me: even without being forced, the model chose `search_notes_snippet` over `search_notes_verbose` from step 1 of the first run — the tool description in `TOOLS_SPEC` and the system prompt nudge were enough. Before/after on the "capstone demo" query: verbose returned 517 chars, snippet returned 347 chars (33% smaller).

---

## Day 2 — Mini-Build: Workflow vs. Agent

| Run | Version  | Calls | Tokens | Turns | Score /7 | Notes |
|-----|----------|-------|--------|-------|----------|-------|
| 1   | workflow |   3   |  727   | n/a   |     7    |       |
| 2   | workflow |   3   |  725   | n/a   |     7    |       |
| 3   | workflow |   3   |  725   | n/a   |     7    |       |
| 4   | agent    |   3   | 1530   |   3   |     6    |       |
| 5   | agent    |   3   | 1532   |   3   |     6    |       |
| 6   | agent    |   3   | 1532   |   3   |     6    |       |

Verdict — for THIS task I would ship the workflow because: it was able to generate consistent, reliable results that meet the need. The agent approach was more complex for worse outcomes, using more tokens and failing to flag health inspection action item was missing a deadline in all 3 runs.
Cost: which version used more tokens, and roughly how much more? The agent approach used more than twice as many tokens.
Reliability: which scored more consistently across runs? They both were very consistent.
One thing that surprised me: The agent failing to flag the missing deadline every time
What I had to correct in code my agent wrote (AI-use disclosure — expected, not penalized): The agent.py script prompts were being rejectedwith HTTP 400 due to only containing a system prompt. After several attempts to have openclaw resolve the issue failed, where it instead wrote a new script that did not meet the requirements and another with similar issues, I instead prompted Github Copilot to fix the code. 

---

## Day 3 — BC 1
- **What I built:** Extended the starter agent.py with three new tools: word_count        
  (returns word and char counts for one note or all notes), search_notes_snippet      
  (token-efficient search returning only matching lines with file and line number     
  instead of full document text), and write_note (saves agent-generated output back to
  the data folder). Also updated the system prompt to steer the model toward the      
  efficient tools.
- **What failed:** Nothing broke outright. My original idea was to use the AI disclosure  
  tools to help generate my write-up text, but the agent interpreted the task more    
  literally — it read and summarized the notes in the data folder and wrote the       
  disclosure there. Useful, just not what I had in mind.
- **What I changed:** Added three tools to both TOOLS_SPEC and run_tool so the model could
  discover and call them. Updated prompts/bc1-agent-system.txt to explicitly prefer   
  search_notes_snippet over the verbose version and to guide use of write_note for    
  saving output. Logged the prompt change in PROMPTS.md.
- **Where AI helped, and how I verified its output:** I came into this knowing I wanted a 
  word_count tool to measure tool efficiency. The AI pointed out that char count would
  be more precise than word count for token comparisons, and turned my idea of using  
  tools for AI disclosure generation into two concrete tools: write_note and          
  search_notes_snippet. I collaborated on the design, let the agent write the code,   
  then reviewed the code changes myself and watched both test runs execute live. I    
  checked the output files to confirm they were correct. One thing that surprised me: 
  even without being forced, the model chose search_notes_snippet over                
  search_notes_verbose from step 1 of the first run — the tool description and system 
  prompt nudge were enough. Before/after on the "capstone demo" query: verbose        
  returned 517 chars, snippet returned 347 chars (33% smaller)

## Day 5 — BC2 Context & Prompt Design
- **What I built:** Built fixed_task.py based off overload_task.py, but using JIT 
  keyword extraction to create a list of relative keywords, and compaction to reduce the 
  context to only the most relevant documents. Created bc2-retriever.txt prompt 
  for running keyword-filter tool, and modified bc2-analyst to include policy status 
  rules so stale policies are ignored.
- **What failed:** fixed_task.py would find the relevant policies AS-17 and AS-18, but
  would not find policy AS-24 (read-only creds/data-owner sign-off).
- **What I changed:** Expanded the amount of relevant keywords for bc2-retriever and 
  set an explicit answer format for bc2-analyst to help ensure all parts of the policy
  question are addressed
- **Where AI helped, and how I verified its output:** I prompted the AI to build 
  fixed_task.py based on overload_task.py, but to include a filter tool and use the principles
  of JIT and compaction to improve the agent's performance. I validated it's output in 
  fixed_task.py, read and clarified the new and modified prompt files, and ran the new task
  to verify the improved performance.
---

## Day 7 — BC3 Reliability & Rollback
- **What I built:** Diagnosed six reliability flaws in `broken_agent.py`, then built `fixed_agent.py` with retries/timeouts via `common.llm.chat()`, a `parse_verdict()` helper that strips markdown fences and validates JSON, staged atomic writes to protect the last good report, a `checkpoint.json` that survives a kill/restart without re-spending tokens, explicit failure logging to stderr, and an honest exit banner that exits non-zero when any item fails. Captured both recovery demos as asciinema recordings (`bc3-recovery-a.cast`, `bc3-recovery-b.cast`).

- **What failed:** The first asciinema recording for Demo A cut off early because `set -e` in the demo script caused the shell to exit when the background agent process was killed — the recording ended right at the kill instead of continuing to show the resume. Re-recorded after removing `set -e`. Also hit a minor environment issue during the timeout test: `nc` wasn't available in the Codespace, so we switched to a Python socket server to simulate the hanging endpoint.

- **What I changed:** Kept `broken_agent.py` untouched as the "before" artifact. Built `fixed_agent.py` from scratch addressing all six flaws per the plan. Added `demo_a.sh` and `demo_b.sh` as reproducible test harnesses for the two recovery scenarios. Committed both `.cast` files alongside the code.

- **Where AI helped, and how I verified its output:** The AI did the majority of the flaw testing and code writing. It designed the mock harnesses, identified the `set -e` issue, and built `fixed_agent.py` and both demo scripts. I steered the process at each phase — the AI initially wanted to move straight into building, but I made sure we diagnosed all flaws first, planned each fix explicitly, reviewed the plan before any code was written, and verified each test result before moving to the next. One thing that surprised me: after Demo A, the final report only showed 3 approved items instead of the expected 4. CR-102 had been checkpointed as done before the kill, but the staged `.tmp` file hadn't been atomically renamed yet when the process was killed — so it didn't appear in the final report. After thinking it through I agreed this is correct behavior: the staging mechanism prioritizes report integrity over completeness, which is the right tradeoff.
