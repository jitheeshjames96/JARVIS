#!/bin/bash
set -e

echo "=== Running Morning Brief Pipeline ==="

# 1. Update Oracle state to running
python3 scripts/update_agent_status.py --agent Oracle --state running --summary "Fetching global news & macro data"

# 2. Fetch news
if python3 scripts/fetch_news_digest.py; then
    # 3. Update Oracle state to idle on success
    python3 scripts/update_agent_status.py --agent Oracle --state idle --summary "Morning brief cached and warning filters evaluated" --next-run "12:00"
    
    # 4. Speak morning brief headlines
    python3 scripts/speak_morning_brief.py
    
    # 5. Open visual dashboard
    echo "Opening visual control dashboard..."
    open dashboard.html || true
    
    echo "Morning brief completed successfully."
else
    # Update to alert on failure
    python3 scripts/update_agent_status.py --agent Oracle --state alert --summary "News fetch pipeline failed"
    echo "Morning brief failed."
    exit 1
fi
