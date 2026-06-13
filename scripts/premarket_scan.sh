#!/bin/bash
set -e

echo "=== Starting Premarket Scan ==="

# 1. Update Vanguard status
python3 scripts/update_agent_status.py --agent Vanguard --state running --summary "Premarket scanning active"

# 2. Run swing scan
python3 scripts/screener_swing.py

# 3. Update Vanguard status to idle
python3 scripts/update_agent_status.py --agent Vanguard --state idle --summary "Premarket scan completed"

echo "=== Premarket Scan Finished ==="
