#!/usr/bin/env bash
# Demo A: kill mid-run, show checkpoint survives, resume completes correctly
# Note: no set -e — we intentionally kill a background process mid-run
cd /workspaces/collective-assignment-freebiepoints

echo "=== Demo A: Checkpoint + Rollback Recovery ==="
echo ""
echo "--- Step 1: Clean slate ---"
rm -f bc3-reliability/checkpoint.json bc3-reliability/approved_report.md bc3-reliability/approved_report.md.tmp
echo "Removed checkpoint and report."
echo ""

echo "--- Step 2: Start fixed_agent.py, kill it after 2 items complete ---"
python3 bc3-reliability/fixed_agent.py &
AGENTPID=$!

# Wait until checkpoint has at least 2 entries then kill
for i in $(seq 1 20); do
    sleep 0.5
    if [ -f bc3-reliability/checkpoint.json ]; then
        COUNT=$(python3 -c "import json; d=json.load(open('bc3-reliability/checkpoint.json')); print(len(d['done']))")
        if [ "$COUNT" -ge 2 ]; then
            echo ""
            echo ">>> Checkpoint has $COUNT entries — killing agent now (simulating Codespace stop)"
            kill $AGENTPID 2>/dev/null
            wait $AGENTPID 2>/dev/null
            break
        fi
    fi
done
echo ""

echo "--- Step 3: Inspect checkpoint and report after kill ---"
echo "checkpoint.json:"
cat bc3-reliability/checkpoint.json
echo ""
echo "approved_report.md (should be intact or partial, NOT empty):"
cat bc3-reliability/approved_report.md
echo ""

echo "--- Step 4: Resume — restart fixed_agent.py ---"
echo "(Watch for 'Resuming: skipping...' and only unprocessed items being run)"
echo ""
python3 bc3-reliability/fixed_agent.py
echo ""

echo "--- Step 5: Final report ---"
cat bc3-reliability/approved_report.md
echo ""
echo "=== Demo A complete ==="
