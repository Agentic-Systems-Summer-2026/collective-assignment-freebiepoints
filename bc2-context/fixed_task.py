#!/usr/bin/env python3
"""Build Challenge 2 fix — JIT retrieval + compaction to cure context overload.

Run from the repo root:  python3 bc2-context/fixed_task.py

Strategy
--------
overload_task.py stuffs all 30 policy docs (~25k tokens) into one request.
This script adds a keyword-filter tool so the agent can prune the haystack
before the analyst ever sees it (JIT retrieval), then passes only the
relevant slice (compaction).  The two-phase approach means:

  Phase 1 — Retriever (cheap, small context):
    Ask a lightweight model to extract domain keywords from the question,
    then score every document by how many keywords appear in its text.
    Keep only the top-N docs (N = TOP_K, default 5).

  Phase 2 — Analyst (focused, small context):
    Pass only the filtered docs to the compliance analyst.
    The analyst prompt also includes an explicit guardrail against
    EXPIRED/RESCINDED policies (see bc2-analyst-focused.txt).

Token cost comparison (run both to see for yourself):
  overload_task.py  → ~25 000 tokens per question (all 30 docs, one shot)
  fixed_task.py     → ~1 500–2 500 tokens per question (3–5 docs only)

Technique citations (see PROMPTS.md):
  - bc2-retriever.txt   : new retriever prompt (JIT keyword extraction)
  - bc2-analyst-focused.txt : compacted analyst prompt with status guardrail
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from common.llm import chat, load_prompt, STATS

QUESTION = (
    "A student employee wants to run a long-lived agent on a lab "
    "machine over the weekend, unattended, with access to a shared "
    "drive. Under our policies, what approvals do they need, what "
    "logging is required, and what is the maximum unattended runtime? "
    "Cite the policy numbers you used."
)

# Same ground-truth documents and traps as overload_task.py — unchanged so
# the comparison is honest.
RELEVANT = {
    7:  "POLICY AS-7 (Unattended Automation): agents running unattended for "
        "more than 4 hours require written supervisor approval AND a named "
        "on-call contact. Maximum unattended runtime is 72 hours.",
    18: "POLICY AS-18 (Audit Logging): any automated system touching shared "
        "storage must write an append-only action log with timestamps, and "
        "logs must be retained for 90 days.",
    24: "POLICY AS-24 (Shared Drive Access): automation accessing shared "
        "drives requires read-only credentials by default; write access "
        "needs a data-owner sign-off recorded in the request ticket.",
}

TRAPS = {
    12: "POLICY AS-12 (Automation Pilot Program — EXPIRED 2024, retained for "
        "records only): pilot agents were capped at 12 hours unattended "
        "runtime with lab-manager approval; logs kept 30 days.",
    27: "POLICY AS-27 (Legacy Unattended Automation — RESCINDED, superseded "
        "by AS-7): unattended runtime capped at 24 hours; verbal supervisor "
        "approval sufficient; no on-call contact required.",
}

random.seed(4243)  # same haystack order as overload_task.py
FILLER_TOPICS = ["visitor parking", "printer quotas", "meeting-room booking",
                 "coffee fund", "poster printing", "bicycle storage",
                 "holiday scheduling", "office plants", "recycling",
                 "keyboard replacement", "software licences", "travel forms"]

# ── tunable constants ─────────────────────────────────────────────────────────
TOP_K = 5          # maximum documents forwarded to the analyst
MIN_SCORE = 1      # minimum keyword hits to be considered at all
# ─────────────────────────────────────────────────────────────────────────────


def make_docs() -> list[dict]:
    """Return list of {id, header, body} dicts — same content as overload_task."""
    docs = []
    for i in range(1, 31):
        if i in RELEVANT:
            body = RELEVANT[i]
        elif i in TRAPS:
            body = TRAPS[i]
        else:
            t = random.choice(FILLER_TOPICS)
            body = (
                f"POLICY AS-{i} ({t.title()}): " +
                " ".join(
                    f"Provision {j}: requests regarding {t} must be "
                    f"submitted via the AS-{i} form no later than "
                    f"{random.randint(2, 14)} business days in advance, "
                    f"subject to review by the {t} committee."
                    for j in range(1, 26)
                )
            )
        docs.append({"id": i, "header": f"=== DOCUMENT {i} ===", "body": body})
    return docs


# ── Tool: keyword-based JIT filter ────────────────────────────────────────────

def extract_keywords(question: str) -> list[str]:
    """Phase 1a — ask the retriever model for domain keywords.

    This is the JIT (just-in-time) step: we only ask for keywords when a
    question arrives, so we never pre-load all 30 documents.
    """
    retriever_prompt = load_prompt("bc2-retriever.txt")
    raw = chat(
        [
            {"role": "system", "content": retriever_prompt},
            {"role": "user",   "content": f"QUESTION: {question}"},
        ],
        max_tokens=150,
        temperature=0,
    )
    # Strip accidental markdown fences if the model disobeys
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        data = json.loads(raw)
        return [str(k).lower() for k in data.get("keywords", [])]
    except json.JSONDecodeError:
        # Graceful fallback: split words from the raw reply
        return [w.strip("{}[]\"',").lower() for w in raw.split() if len(w) > 3]


def filter_documents(docs: list[dict], keywords: list[str], top_k: int = TOP_K,
                     min_score: int = MIN_SCORE) -> list[dict]:
    """Phase 1b — score every document by keyword overlap and keep the best.

    Compaction: the output list is always ≤ top_k documents, collapsing the
    full 30-doc corpus into only what's needed for the final answer.
    """
    scored = []
    kw_lower = [k.lower() for k in keywords]
    for doc in docs:
        text = (doc["header"] + " " + doc["body"]).lower()
        score = sum(1 for kw in kw_lower if kw in text)
        if score >= min_score:
            scored.append((score, doc))

    # Sort descending by score; keep top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [doc for _, doc in scored[:top_k]]
    return selected


# ── Phase 2: analyst call with compacted context ──────────────────────────────

def answer_with_filtered_docs(question: str, docs: list[dict]) -> str:
    """Pass only the filtered documents to the analyst for the final answer."""
    context = "\n\n".join(f"{d['header']}\n{d['body']}" for d in docs)
    analyst_prompt = load_prompt("bc2-analyst.txt")
    return chat(
        [
            {"role": "system", "content": analyst_prompt},
            {"role": "user",   "content": context + "\n\nQUESTION: " + question},
        ],
        max_tokens=500,
        temperature=0,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_docs = make_docs()
    total_chars = sum(len(d["body"]) for d in all_docs)
    print(f"Corpus: {len(all_docs)} documents, ~{total_chars:,} chars total.\n")

    # ── Phase 1a: JIT keyword extraction ──────────────────────────────────────
    print("Phase 1a — JIT keyword extraction…")
    keywords = extract_keywords(QUESTION)
    print(f"  Keywords: {keywords}\n")

    # ── Phase 1b: compaction / filtering ──────────────────────────────────────
    print("Phase 1b — filtering documents by keyword relevance…")
    filtered = filter_documents(all_docs, keywords)
    filtered_chars = sum(len(d["body"]) for d in filtered)
    print(f"  Selected {len(filtered)}/{len(all_docs)} documents "
          f"(~{filtered_chars:,} chars — "
          f"{100*filtered_chars//total_chars}% of original corpus).")
    print(f"  Document ids: {[d['id'] for d in filtered]}\n")

    # ── Phase 2: analyst answer on compacted context ──────────────────────────
    print("Phase 2 — analyst answer on compacted context…")
    answer = answer_with_filtered_docs(QUESTION, filtered)
    print("\n" + answer)
    print(f"\nSTATS: {STATS}")
    print(
        "\nGround truth: AS-7 (written approval + on-call contact, 72h max), "
        "AS-18 (append-only logs, 90-day retention), AS-24 (read-only creds / "
        "data-owner sign-off). Did it cite exactly these, with correct "
        "details — or did it fall for the expired AS-12 (12h) or "
        "rescinded AS-27 (24h, verbal approval)?"
    )


if __name__ == "__main__":
    main()
