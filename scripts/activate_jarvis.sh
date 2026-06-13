#!/bin/bash
# JARVIS Phase 5b — one-shot activation helper
set -e
cd "$(dirname "$0")/.."

echo "=== JARVIS Activation ==="

# 1. Check dependencies
missing=0
for cmd in ffmpeg python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Missing: $cmd"
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "Install: brew install ffmpeg portaudio"
  exit 1
fi

# portaudio headers required for PyAudio build
if ! brew list portaudio &>/dev/null; then
  echo "Installing portaudio (PyAudio dependency)..."
  brew install portaudio
fi

# 2. Python voice packages
echo "Installing voice Python packages..."
pip3 install --user -q faster-whisper openwakeword pyaudio numpy pyyaml 2>/dev/null || \
  pip3 install faster-whisper openwakeword pyaudio numpy pyyaml

# 3. Validate programmatic stack
bash scripts/test_phase5b.sh

# 4. Refresh live data
python3 scripts/refresh_if_stale.py
python3 scripts/build_live_context.py
python3 scripts/generate_dashboard.py

# 5. Voice enrollment check
if [ ! -f cache/voice-profile.json ]; then
  echo ""
  echo ">>> ACTION REQUIRED: Enroll your voice (security lock)"
  echo "    python3 voice/enroll_speaker.py"
  echo ""
else
  echo "Voice profile: enrolled"
fi

# 6. Foreground test hint
echo ""
echo ">>> Foreground voice test:"
echo "    python3 voice/jarvis_daemon.py --once --no-wake"
echo ""
echo ">>> Cinema mode (background daemon):"
echo "    cp voice/launchd/com.jarvis.voice.plist ~/Library/LaunchAgents/"
echo "    launchctl load ~/Library/LaunchAgents/com.jarvis.voice.plist"
echo ""
echo ">>> Visual console:"
echo "    python3 scripts/launch_jarvis.py"
echo "    open dashboard.html"
echo ""
echo "=== Activation prep complete ==="
