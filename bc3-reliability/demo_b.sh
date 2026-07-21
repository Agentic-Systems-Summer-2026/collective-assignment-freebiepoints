#!/usr/bin/env bash
# Demo B: inject a bad URL for first 3 items, show harness handles failures,
# report stays valid and never corrupted
set -e
cd /workspaces/collective-assignment-freebiepoints

echo "=== Demo B: Injected Failure Recovery ==="
echo ""
echo "--- Step 1: Clean slate ---"
rm -f bc3-reliability/checkpoint.json bc3-reliability/approved_report.md bc3-reliability/approved_report.md.tmp
echo "Removed checkpoint and report."
echo ""

echo "--- Step 2: Run with BAD base URL (point at a port nothing is listening on) ---"
echo "(First 3 items will fail with connection refused; rest use real endpoint)"
echo ""

# Patch: override LITELLM_BASE_URL to a bad host for the first 3 calls only,
# then fall back to the real endpoint. We do this by wrapping classify with a
# counter via a small injection shim.
python3 - <<'PYEOF'
import json, sys, pathlib, importlib.util, unittest.mock, urllib.error

sys.path.insert(0, '/workspaces/collective-assignment-freebiepoints')
from common.llm import chat as real_chat

call_count = 0
FAIL_FIRST_N = 3

def patched_chat(messages, **kwargs):
    global call_count
    call_count += 1
    if call_count <= FAIL_FIRST_N:
        raise RuntimeError(f"Injected failure on call #{call_count} — simulated bad endpoint")
    return real_chat(messages, **kwargs)

spec = importlib.util.spec_from_file_location(
    'fixed_agent', '/workspaces/collective-assignment-freebiepoints/bc3-reliability/fixed_agent.py')
mod = importlib.util.module_from_spec(spec)

with unittest.mock.patch('common.llm.chat', side_effect=patched_chat):
    spec.loader.exec_module(mod)
    try:
        mod.main()
    except SystemExit as e:
        print(f"\n(Agent exited with code {e.code} — non-zero because failures occurred)")
PYEOF
echo ""

echo "--- Step 3: Inspect report after injected failures ---"
echo "approved_report.md (should be valid — not empty, not corrupted):"
cat bc3-reliability/approved_report.md
echo ""

echo "--- Step 4: Inspect checkpoint ---"
if [ -f bc3-reliability/checkpoint.json ]; then
    echo "checkpoint.json (failed items NOT in done list — will be retried):"
    cat bc3-reliability/checkpoint.json
else
    echo "No checkpoint (all items resolved — clean exit)"
fi
echo ""

echo "--- Step 5: Re-run with real endpoint to recover failed items ---"
echo "(Should skip already-done items, retry the 3 that failed)"
echo ""
python3 bc3-reliability/fixed_agent.py
echo ""

echo "--- Step 6: Final report after recovery ---"
cat bc3-reliability/approved_report.md
echo ""
echo "=== Demo B complete ==="
