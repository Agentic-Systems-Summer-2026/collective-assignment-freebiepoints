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