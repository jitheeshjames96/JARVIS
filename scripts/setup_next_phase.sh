#!/bin/bash
# JARVIS next-phase setup — trading config, schedules, notifications template
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== JARVIS Next-Phase Setup ==="

# 1. Trading config
if [ ! -f config/trading.yaml ]; then
  cp config/trading.yaml.example config/trading.yaml
  echo "✓ Created config/trading.yaml from example"
else
  echo "✓ config/trading.yaml already exists"
fi

# 2. Notifications template
if [ ! -f config/notifications.yaml ]; then
  cp config/notifications.yaml.example config/notifications.yaml
  echo "✓ Created config/notifications.yaml — add Telegram token to enable"
else
  echo "✓ config/notifications.yaml already exists"
fi

# 3. LaunchAgents
mkdir -p ~/Library/LaunchAgents logs
for plist in voice/launchd/com.jarvis.{morning,premarket,eod}.plist; do
  name=$(basename "$plist")
  cp "$plist" ~/Library/LaunchAgents/
  launchctl bootout "gui/$(id -u)" ~/Library/LaunchAgents/"$name" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/"$name" 2>/dev/null && \
    echo "✓ Loaded $name" || echo "⚠ Could not load $name (check paths)"
done

# 4. Fetch live data now
echo "Refreshing live news + markets + weather..."
python3 scripts/fetch_news_digest.py
python3 scripts/fetch_weather.py
python3 scripts/refresh_dashboard_data.py
python3 scripts/generate_dashboard.py

echo ""
echo "=== Setup complete ==="
echo "Dashboard: open dashboard.html"
echo "Cloud:     https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html"
echo ""
echo "Schedules loaded (IST):"
echo "  07:00  morning brief"
echo "  08:45  premarket scan"
echo "  15:45  eod scan"
echo ""
echo "Optional: edit config/notifications.yaml for Telegram alerts"
