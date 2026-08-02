#!/usr/bin/env python3
"""Build Challenge 5 — quiet_agent.py with full observability.

Adds:
  1. Structured JSONL tracing → bc5-observability/trace.jsonl
     Each record: timestamp, step, model, prompt_len, response_len,
                  prompt_tokens, completion_tokens, total_tokens, latency_s,
                  decision, cumulative_tokens, cumulative_calls
  2. A reusable `traced_chat()` helper that wraps every LLM call.
  3. A human approval gate before writing summary.md:
     Shows the pending summary + live cost/usage snapshot.
     Logs the human decision in the trace.
     Aborts without writing if the user declines.

Run from the repo root:  python3 bc5-observability/observed_agent.py
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from common.llm import chat, STATS, DEFAULT_MODEL

HERE = pathlib.Path(__file__).resolve().parent
TRACE_FILE = HERE / "trace.jsonl"
TOPIC = "why long-running agents need checkpoints"


# ---------------------------------------------------------------------------
# Tracing helper
# ---------------------------------------------------------------------------

def traced_chat(
    step: str,
    messages: list[dict],
    decision: str = "",
    model: str = DEFAULT_MODEL,
    **kwargs,
) -> str:
    """Run a chat call, measure timing, capture metadata, write a trace entry.

    Args:
        step:     Human-readable name for this pipeline step.
        messages: The message list passed to the LLM.
        decision: Short label for what the result is used for (e.g. "plan").
        model:    Model to use (defaults to common.llm DEFAULT_MODEL).
        **kwargs: Extra kwargs forwarded to chat().

    Returns:
        The assistant's response text.
    """
    prompt_len = sum(len(m.get("content", "")) for m in messages)

    # Snapshot STATS before the call so we can compute per-call token delta
    tokens_before = STATS["tokens"]
    calls_before = STATS["calls"]

    t_start = time.monotonic()
    response = chat(messages, model=model, **kwargs)
    latency = time.monotonic() - t_start

    tokens_this_call = STATS["tokens"] - tokens_before

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "step": step,
        "model": model,
        "prompt_len": prompt_len,
        "response_len": len(response),
        # Token counts — common.llm tracks total_tokens per call via STATS;
        # we report what we can derive without patching the underlying lib.
        "tokens_this_call": tokens_this_call,
        "cumulative_tokens": STATS["tokens"],
        "cumulative_calls": STATS["calls"],
        "latency_s": round(latency, 3),
        "decision": decision or step,
    }

    with TRACE_FILE.open("a") as fh:
        fh.write(json.dumps(record) + "\n")

    print(f"[trace] step={step!r}  tokens={tokens_this_call}  "
          f"latency={latency:.2f}s  cumulative_tokens={STATS['tokens']}")

    return response


# ---------------------------------------------------------------------------
# Human approval gate
# ---------------------------------------------------------------------------

def approval_gate(summary: str) -> bool:
    """Show the pending summary and current usage, then ask for explicit approval.

    Writes the human decision to the trace.
    Returns True (approved) or False (declined).
    """
    border = "=" * 60
    print(f"\n{border}")
    print("PENDING SUMMARY — please review before it is written to disk")
    print(border)
    print(summary)
    print(border)
    print("\nCost / Usage Snapshot")
    print(f"  LLM calls so far : {STATS['calls']}")
    print(f"  Total tokens     : {STATS['tokens']}")
    print(f"  Cache hits       : {STATS.get('cache_hits', 0)}")
    print(border)
    print("\nType  'yes'  to write summary.md   |   anything else to abort")

    try:
        answer = input("Your decision > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "no"

    approved = answer in {"yes", "y"}

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "step": "human_approval_gate",
        "model": None,
        "prompt_len": len(summary),
        "response_len": 0,
        "tokens_this_call": 0,
        "cumulative_tokens": STATS["tokens"],
        "cumulative_calls": STATS["calls"],
        "latency_s": 0,
        "decision": "approved" if approved else "declined",
        "human_input": answer,
    }
    with TRACE_FILE.open("a") as fh:
        fh.write(json.dumps(record) + "\n")

    return approved


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    # Fresh trace for this run — append-only so re-runs stack up in order.
    print(f"[trace] Writing to {TRACE_FILE}")

    # Step 1 — generate research questions
    plan = traced_chat(
        step="plan_questions",
        messages=[{"role": "user", "content":
                   f"List 3 short bullet questions someone should answer "
                   f"to explain: {TOPIC}"}],
        decision="research questions for the topic",
    )

    # Step 2 — answer each question
    answers = traced_chat(
        step="answer_questions",
        messages=[{"role": "user", "content":
                   "Answer each question in 2 sentences:\n" + plan}],
        decision="detailed answers to research questions",
    )

    # Step 3 — compress into a student-friendly summary
    summary = traced_chat(
        step="compress_summary",
        messages=[{"role": "user", "content":
                   "Compress this into a 4-sentence summary for a student:\n"
                   + answers}],
        decision="final student-facing summary",
    )

    # Human approval gate
    if not approval_gate(summary):
        print("\nDeclined — nothing written to disk.")
        sys.exit(0)

    # Approved — write output
    output_path = HERE / "summary.md"
    output_path.write_text(f"# {TOPIC}\n\n{summary}\n")
    print(f"\nApproved — wrote {output_path}")
    print("Trace log:", TRACE_FILE)


if __name__ == "__main__":
    main()
