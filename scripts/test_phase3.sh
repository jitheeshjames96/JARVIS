#!/bin/bash
set -e

# Make sure scripts are executable
chmod +x voice/*.sh voice/*.py scripts/*.sh scripts/*.py || true

echo "=== 1. Testing speak.sh ==="
./voice/speak.sh "Hello Jitheesh, testing the voice output system."

echo -e "\n=== 2. Testing Keyword Regex Boundaries (Regex validation) ==="
python3 -c '
import re
title = "Software updates completed toward the target"
pattern = re.compile(r"\bWAR\b", re.IGNORECASE)
assert not pattern.search(title), "Failed: matched substring toward as WAR"
title_valid = "New trade war escalation"
assert pattern.search(title_valid), "Failed: did not match word WAR"
print("Keyword regex validation passed!")
'

echo -e "\n=== 3. Writing Mock Alerts to the Bus ==="
# Reset spoken alerts cache first
rm -f cache/voice-alerts-spoken.json
# Write a trade plan for Prime
python3 scripts/bus_write.py \
  --from-agent Strategist \
  --to-agent Prime \
  --topic trade_plan_ready \
  --payload '{"symbol": "TATASTEEL", "trigger_price": 167.40, "setup_score": 88}'
# Write an infra alert for Synergy
python3 scripts/bus_write.py \
  --from-agent Sentinel \
  --to-agent Synergy \
  --topic infra_alert \
  --payload '{"event": "Disk space low on EKS nodes"}'

echo -e "\n=== 4. Testing alert.sh Polling & Speaking ==="
./voice/alert.sh

echo -e "\n=== 5. Checking Audit Log File ==="
cat logs/agent-actions.jsonl

echo -e "\n=== Phase 3 Validation Successful! ==="
