#!/bin/bash
set -e

# Reset test state
rm -rf cache/bus/inbox/* cache/bus/processed/* cache/bus/broadcast/* cache/bus/read_broadcasts_*


echo "=== 1. Testing Agent Status Board Update ==="
python3 scripts/update_agent_status.py --agent Vanguard --state running --summary "Pre-market scan in progress" --next-run "09:15"
cat cache/agent-status.json | grep -A 4 '"Vanguard"'

echo -e "\n=== 2. Testing Message Write ==="
python3 scripts/bus_write.py --from-agent Tracker --to-agent Strategist --topic screener_alert --payload '{"symbol": "TATASTEEL", "setup_score": 88}'
ls cache/bus/inbox/

echo -e "\n=== 3. Testing Deduplication (should skip) ==="
python3 scripts/bus_write.py --from-agent Tracker --to-agent Strategist --topic screener_alert --payload '{"symbol": "TATASTEEL", "setup_score": 88}'

echo -e "\n=== 4. Testing Message Polling ==="
python3 scripts/bus_poll.py --agent Strategist
echo "Inbox directory (should be empty):"
ls cache/bus/inbox/
echo "Processed directory (should contain message):"
ls cache/bus/processed/

echo -e "\n=== 5. Testing Bus Cleanup ==="
python3 scripts/bus_cleanup.py

echo -e "\n=== Validation Successful ==="
