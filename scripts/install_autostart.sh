#!/usr/bin/env bash
# JARVIS launchd installer — light by default (GCP handles dashboard + DevOps).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHD="$HOME/Library/LaunchAgents"
MODE="light"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) MODE="full" ;;
    --light) MODE="light" ;;
    --with-voice) WITH_VOICE=1 ;;
    *) echo "Usage: $0 [--light|--full] [--with-voice]"; exit 1 ;;
  esac
  shift
done

mkdir -p "$LAUNCHD" "$ROOT/logs"

install_plist() {
  local src="$1"
  local label
  label="$(/usr/libexec/PlistBuddy -c 'Print :Label' "$src")"
  echo "→ Installing $label"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  cp "$src" "$LAUNCHD/"
  launchctl bootstrap "gui/$(id -u)" "$LAUNCHD/$(basename "$src")"
  launchctl enable "gui/$(id -u)/$label"
  launchctl kickstart -k "gui/$(id -u)/$label" 2>/dev/null || true
}

uninstall_plist() {
  local label="$1"
  echo "→ Removing $label (local offload to GCP)"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  rm -f "$LAUNCHD/$label.plist"
}

echo "JARVIS autostart — mode: $MODE"
echo "Workspace: $ROOT"
echo ""

# Always: Keeper personal reminders (lightweight, 2×/day)
install_plist "$ROOT/scripts/launchd/com.jarvis.keeper.plist"

if [[ "$MODE" == "full" ]]; then
  install_plist "$ROOT/scripts/launchd/com.jarvis.dashboard.plist"
  install_plist "$ROOT/scripts/launchd/com.jarvis.devops.plist"
  [[ -n "${WITH_VOICE:-}" ]] && install_plist "$ROOT/voice/launchd/com.jarvis.voice.plist"
else
  uninstall_plist "com.jarvis.dashboard"
  uninstall_plist "com.jarvis.devops"
  uninstall_plist "com.jarvis.voice"
  [[ -n "${WITH_VOICE:-}" ]] && install_plist "$ROOT/voice/launchd/com.jarvis.voice.plist"
fi

echo ""
launchctl list | grep com.jarvis || true
echo ""
if [[ "$MODE" == "light" ]]; then
  echo "✓ Light mode — Keeper only (personal reminders 07:00 & 20:00 IST)"
  echo "✓ Dashboard + DevOps run on GCP (Sentinel hourly) — zero local load"
  echo "✓ Dashboard refreshes on-demand when you say 'bring up the dashboard'"
else
  echo "✓ Full mode — all local services installed"
fi
[[ -n "${WITH_VOICE:-}" ]] && echo "✓ Voice daemon enabled (needs Full Disk Access on Desktop)"
