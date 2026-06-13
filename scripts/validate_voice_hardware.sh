#!/bin/bash
# JARVIS voice hardware + pipeline validation (non-interactive)
set -e
cd "$(dirname "$0")/.."
PASS=0
FAIL=0

ok()   { echo "  OK: $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

echo "=== JARVIS Voice Hardware Validation ==="

# Dependencies
for cmd in ffmpeg python3; do
  command -v "$cmd" &>/dev/null && ok "$cmd found" || fail "$cmd missing"
done

python3 -c "import pyaudio, faster_whisper, openwakeword, numpy, yaml" 2>/dev/null \
  && ok "Python voice imports" || fail "Python voice imports"

# Mic device
if ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -qi microphone; then
  ok "Microphone device detected"
else
  fail "No microphone in ffmpeg device list"
fi

# Record test
TEST_WAV="/tmp/jarvis_validate_mic.wav"
rm -f "$TEST_WAV"
if ffmpeg -y -f avfoundation -i ":0" -t 2 -ac 1 -ar 16000 "$TEST_WAV" \
     -loglevel error 2>/dev/null && [ -s "$TEST_WAV" ]; then
  ok "Microphone recording ($(wc -c < "$TEST_WAV") bytes)"
else
  fail "Microphone recording"
fi

# Speaker verify (open mode if not enrolled)
if [ -f "$TEST_WAV" ]; then
  python3 -c "
from voice.speaker_verify import verify, profile_enrolled
a,s = verify('$TEST_WAV')
assert a, f'verify failed score={s}'
print('enrolled=' + str(profile_enrolled()))
" 2>/dev/null && ok "Speaker verify module" || fail "Speaker verify module"
fi

# Whisper transcribe
if [ -f "$TEST_WAV" ]; then
  python3 -c "
import sys; sys.path.insert(0,'voice')
from jarvis_loop import transcribe
t = transcribe('$TEST_WAV')
print('heard:', repr(t))
" 2>/dev/null | grep -q heard && ok "Whisper transcription" || fail "Whisper transcription"
fi

# TTS
python3 voice/speak.py "Voice stack validation complete." >/dev/null 2>&1 \
  && ok "TTS synthesis" || fail "TTS synthesis"

# Intent router
python3 voice/intent_router.py "status" 2>/dev/null | grep -q '"response"' \
  && ok "Intent router + live brief" || fail "Intent router"

# Enrollment
if [ -f cache/voice-profile.json ]; then
  ok "Voice profile enrolled"
else
  echo "  PENDING: Voice profile not enrolled — run: python3 voice/enroll_speaker.py"
fi

# Cinema mode
if launchctl list 2>/dev/null | grep -q com.jarvis.voice; then
  ok "Cinema mode daemon loaded"
else
  echo "  PENDING: Cinema mode not loaded (may need Full Disk Access for Desktop path)"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
