#!/usr/bin/env python3
"""BC5 Incident Simulation — network loss mid-pipeline.

Runs the same three-step pipeline as observed_agent.py, but injects a
simulated network failure after step 1 succeeds. This lets us:
  - Produce a real trace showing one clean step followed by failure
  - Diagnose the incident FROM the trace alone
  - Write an honest incident report with concrete trace evidence

Simulation mechanism:
  After step 1 completes we replace urllib.request.urlopen with a stub
  that raises socket.timeout, which is exactly what a dead network looks
  like to common.llm's retry loop.
"""
import json
import pathlib
import socket
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from common.llm import chat, STATS, DEFAULT_MODEL

HERE = pathlib.Path(__file__).resolve().parent
TRACE_FILE = HERE / "trace.jsonl"
TOPIC = "why long-running agents need checkpoints"


# ---------------------------------------------------------------------------
# Network-loss injector
# ---------------------------------------------------------------------------

_real_urlopen = urllib.request.urlopen
_network_severed = False


def _severed_urlopen(req, *args, **kwargs):
    """Drop-in for urlopen that simulates a dead network."""
    raise socket.timeout("Simulated network loss — connection timed out")


def sever_network():
    """Swap in the dead-network stub. Called after step 1 completes."""
    global _network_severed
    urllib.request.urlopen = _severed_urlopen
    _network_severed = True
    print("\n[INCIDENT SIM] *** Network severed after step 1 ***\n")


def restore_network():
    """Restore real urlopen (not used in this script, but good practice)."""
    urllib.request.urlopen = _real_urlopen


# ---------------------------------------------------------------------------
# Tracing helper (same as observed_agent.py)
# ---------------------------------------------------------------------------

def traced_chat(step, messages, decision="", model=DEFAULT_MODEL, **kwargs):
    prompt_len = sum(len(m.get("content", "")) for m in messages)
    tokens_before = STATS["tokens"]

    t_start = time.monotonic()
    error_info = None
    response = None

    try:
        response = chat(messages, model=model, **kwargs)
    except Exception as exc:
        error_info = repr(exc)
        raise
    finally:
        latency = time.monotonic() - t_start
        tokens_this_call = STATS["tokens"] - tokens_before

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "step": step,
            "model": model,
            "prompt_len": prompt_len,
            "response_len": len(response) if response else 0,
            "tokens_this_call": tokens_this_call,
            "cumulative_tokens": STATS["tokens"],
            "cumulative_calls": STATS["calls"],
            "latency_s": round(latency, 3),
            "decision": decision or step,
            "error": error_info,
        }
        with TRACE_FILE.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

        status = "ERROR" if error_info else "OK"
        print(f"[trace] step={step!r}  status={status}  "
              f"tokens={tokens_this_call}  latency={latency:.2f}s")
        if error_info:
            print(f"        error={error_info[:120]}")

    return response


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    print(f"[trace] Appending to {TRACE_FILE}")
    print(f"[info]  Model: {DEFAULT_MODEL}\n")

    # ── Step 1 — succeeds ──────────────────────────────────────────────────
    plan = traced_chat(
        step="plan_questions",
        messages=[{"role": "user", "content":
                   f"List 3 short bullet questions someone should answer "
                   f"to explain: {TOPIC}"}],
        decision="research questions for the topic",
    )
    print(f"\nStep 1 output:\n{plan}\n")

    # ── Inject failure ─────────────────────────────────────────────────────
    sever_network()

    # ── Step 2 — will exhaust retries and raise ────────────────────────────
    try:
        answers = traced_chat(
            step="answer_questions",
            messages=[{"role": "user", "content":
                       "Answer each question in 2 sentences:\n" + plan}],
            decision="detailed answers to research questions",
        )
    except Exception as exc:
        print(f"\n[INCIDENT] Pipeline aborted at step 'answer_questions': {exc}")
        print("[INCIDENT] summary.md was NOT written.")
        _write_incident_marker(step="answer_questions", exc=exc)
        sys.exit(1)

    # Step 3 — never reached
    summary = traced_chat(
        step="compress_summary",
        messages=[{"role": "user", "content":
                   "Compress this into a 4-sentence summary for a student:\n"
                   + answers}],
        decision="final student-facing summary",
    )

    (HERE / "summary.md").write_text(f"# {TOPIC}\n\n{summary}\n")
    print("Done.")


def _write_incident_marker(step: str, exc: Exception):
    """Write a final trace record marking the incident boundary."""
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "step": "INCIDENT_BOUNDARY",
        "model": None,
        "prompt_len": 0,
        "response_len": 0,
        "tokens_this_call": 0,
        "cumulative_tokens": STATS["tokens"],
        "cumulative_calls": STATS["calls"],
        "latency_s": 0,
        "decision": "pipeline_aborted",
        "error": repr(exc),
        "failed_step": step,
        "note": "Network loss simulation — summary.md not written",
    }
    with TRACE_FILE.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    print(f"\n[trace] Incident boundary written to {TRACE_FILE}")


if __name__ == "__main__":
    main()
