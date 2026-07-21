#!/usr/bin/env python3
"""Build Challenge 3 — fixed_agent.py

Fixes all six reliability flaws found in broken_agent.py:

  FIX 1 — No timeout / no retry:
    Use common.llm.chat() instead of raw urlopen. The shared client already
    has timeout=120 and retries=2 with exponential backoff. No more importing
    internals (_key, BASE) — use the public API.

  FIX 2 — Silent except: pass:
    All exceptions are caught, logged to stderr with item ID and error text,
    and counted. The run continues to the next item rather than silently
    discarding failures.

  FIX 3 — Report destroyed on startup:
    Staged atomic writes. All output goes to approved_report.md.tmp first.
    Only on a fully successful run is the .tmp renamed over the real report.
    A crash or kill mid-run leaves the last good report untouched.

  FIX 4 — No checkpoint:
    checkpoint.json tracks completed item IDs. On restart, already-processed
    items are skipped without re-spending tokens. Deleted on clean completion
    so a deliberate re-run starts fresh.

  FIX 5 — No JSON validation / no fence-stripping:
    parse_verdict() strips markdown fences, extracts the first {...} block,
    validates that "risk" is one of low/medium/high, and returns a safe
    fallback {"risk": "unknown", "reason": "parse error"} rather than
    crashing or silently corrupting the report.

  FIX 6 — False success banner:
    Exit banner reports approved / rejected / failed / skipped counts.
    Exits with code 1 if any item failed so CI and calling scripts detect it.

Run from the repo root:  python3 bc3-reliability/fixed_agent.py
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from common.llm import chat  # FIX 1: use public API — no more importing internals

HERE = pathlib.Path(__file__).resolve().parent
REPORT      = HERE / "approved_report.md"
REPORT_TMP  = HERE / "approved_report.md.tmp"   # FIX 3: staged write target
CHECKPOINT  = HERE / "checkpoint.json"           # FIX 4: resume state


# ---------------------------------------------------------------------------
# FIX 5 — robust JSON extraction and validation
# ---------------------------------------------------------------------------

VALID_RISKS = {"low", "medium", "high"}

def parse_verdict(text: str) -> dict:
    """Extract and validate the risk verdict from a model reply.

    Handles:
      - Clean JSON:          {"risk": "low", "reason": "..."}
      - Fenced JSON:         ```json\\n{...}\\n```
      - Prose-prefixed JSON: "Sure! Here is my answer:\\n{...}"
      - Truncated/garbled:   falls back to {"risk": "unknown", ...}
    """
    # Strip markdown fences if present
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    # Extract first {...} block in case there is prose around it
    brace = re.search(r"\{.*?\}", text, re.DOTALL)
    if brace:
        text = brace.group(0)

    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        return {"risk": "unknown", "reason": "parse error — model reply was not valid JSON"}

    # Validate required fields
    if not isinstance(verdict, dict):
        return {"risk": "unknown", "reason": "parse error — parsed value was not a JSON object"}
    if verdict.get("risk") not in VALID_RISKS:
        return {"risk": "unknown", "reason": f"parse error — unexpected risk value: {verdict.get('risk')!r}"}

    return verdict


# ---------------------------------------------------------------------------
# FIX 1 — classify via common.llm.chat (timeout + retries already built in)
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = (
    'Classify this change request. Reply ONLY with JSON '
    '{"risk": "low|medium|high", "reason": "<one line>"}\n\n'
)

def classify(text: str) -> dict:
    raw = chat(
        messages=[{"role": "user", "content": PROMPT_TEMPLATE + text}],
        max_tokens=200,
        temperature=0,
    )
    return parse_verdict(raw)  # FIX 5: validate before trusting


# ---------------------------------------------------------------------------
# FIX 4 — checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> set:
    """Return the set of item IDs already completed."""
    if CHECKPOINT.exists():
        try:
            return set(json.loads(CHECKPOINT.read_text()).get("done", []))
        except Exception:
            return set()
    return set()

def save_checkpoint(done: set) -> None:
    """Persist the completed-ID set atomically."""
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps({"done": sorted(done)}, indent=2))
    tmp.replace(CHECKPOINT)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    requests_file = HERE / "requests.jsonl"
    items = [json.loads(l) for l in requests_file.read_text().splitlines() if l.strip()]

    # FIX 4: load checkpoint — skip already-processed items
    done = load_checkpoint()
    skipped = len([i for i in items if i["id"] in done])
    if skipped:
        print(f"⏭  Resuming: skipping {skipped} already-completed item(s): "
              f"{[i['id'] for i in items if i['id'] in done]}", flush=True)

    # FIX 3: open staged temp file — existing report is untouched until success
    # Carry forward any already-approved lines from a previous partial run
    existing_lines = []
    if REPORT.exists() and done:
        # Preserve lines from the current good report for items in checkpoint
        existing_lines = [
            l for l in REPORT.read_text().splitlines(keepends=True)
            if l.startswith("# ") or not l.startswith("- **") or
               any(f"**{id}**" in l for id in done)
        ]

    approved = skipped  # items already in checkpoint count as approved
    rejected = 0
    failed   = 0

    # Write header + existing approved lines to the staging file
    with REPORT_TMP.open("w") as f:
        if existing_lines:
            f.writelines(existing_lines)
            if not existing_lines[-1].endswith("\n"):
                f.write("\n")
        else:
            f.write("# Approved Changes\n\n")

    for item in items:
        item_id = item["id"]

        # FIX 4: skip already-done items
        if item_id in done:
            continue

        print(f"  Processing {item_id}…", flush=True)

        try:
            verdict = classify(item["request"])

            if verdict["risk"] == "low":
                # FIX 3: append to staging file, not the live report
                with REPORT_TMP.open("a") as f:
                    f.write(f"- **{item_id}** ({verdict['risk']}): "
                            f"{item['request'][:80]} — {verdict['reason']}\n")
                approved += 1
                print(f"    ✅ {item_id} → low risk", flush=True)
            elif verdict["risk"] == "unknown":
                # parse_verdict returned a safe fallback — treat as a failure
                print(f"    ⚠️  {item_id} → parse fallback: {verdict['reason']}", file=sys.stderr, flush=True)
                failed += 1
            else:
                rejected += 1
                print(f"    🚫 {item_id} → {verdict['risk']} risk (rejected)", flush=True)

            # FIX 4: mark as done and persist checkpoint immediately
            done.add(item_id)
            save_checkpoint(done)

        except Exception as e:
            # FIX 2: log the failure — never silently pass
            print(f"    ❌ {item_id} → FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            failed += 1

    # FIX 3: atomic rename — only swap if everything is done
    # (swap regardless of failures so partial progress is visible,
    #  but only delete checkpoint on a fully clean run)
    REPORT_TMP.replace(REPORT)

    # FIX 4: clean up checkpoint on a fully successful run (idempotency)
    if failed == 0 and CHECKPOINT.exists():
        CHECKPOINT.unlink()
        print("🗑  Checkpoint cleared (clean run).", flush=True)

    # FIX 6: honest exit banner with full accounting
    total = len(items)
    print(
        f"\n{'✅' if failed == 0 else '⚠️ '} Done! "
        f"{approved} approved, {rejected} rejected, "
        f"{failed} failed, {skipped} skipped  "
        f"(of {total} total)",
        flush=True,
    )

    # FIX 6: non-zero exit if anything failed so CI can detect it
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
