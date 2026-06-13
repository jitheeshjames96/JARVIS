#!/bin/bash
set -e

echo "=== Starting End-Of-Day (EOD) Scan ==="

# 1. Update Tracker status
python3 scripts/update_agent_status.py --agent Tracker --state running --summary "EOD momentum scans active"

# 2. Run both screeners
python3 scripts/screener_swing.py
python3 scripts/screener_penny.py

# 3. Update Tracker status to idle
python3 scripts/update_agent_status.py --agent Tracker --state idle --summary "EOD momentum scans completed"

echo "=== EOD Scan Finished ==="
