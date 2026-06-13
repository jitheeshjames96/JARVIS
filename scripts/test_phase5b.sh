#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "=== 1. Speaker verify module ==="
python3 -c "
from voice.speaker_verify import compute_embedding, cosine_similarity
import tempfile, wave, struct, math
# synthetic tone wav
p = tempfile.mktemp(suffix='.wav')
with wave.open(p,'w') as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
    for i in range(16000):
        wf.writeframes(struct.pack('<h', int(8000*math.sin(i/100))))
e1 = compute_embedding(p)
e2 = compute_embedding(p)
assert cosine_similarity(e1,e2) > 0.99
print('speaker_verify: OK')
"

echo "=== 2. Live context build ==="
python3 scripts/build_live_context.py
test -f cache/live-context.json && echo "live-context.json: OK"

echo "=== 3. Stale cache refresh ==="
python3 scripts/refresh_if_stale.py

echo "=== 4. Intent router (live) ==="
python3 voice/intent_router.py "priorities" 2>&1 | grep -q "priorities" && echo "intent_router: OK"

echo "=== 5. Dashboard regen ==="
python3 scripts/generate_dashboard.py
grep -q "Synergy Priorities" dashboard.html && echo "dashboard priorities panel: OK"

echo "=== 6. Daemon import check ==="
python3 -c "import voice.jarvis_daemon; import voice.wake_word; print('daemon modules: OK')"

echo ""
echo "=== Phase 5b validation passed (mic/wake tests are manual) ==="
echo "Manual steps:"
echo "  1. python3 voice/enroll_speaker.py"
echo "  2. python3 voice/jarvis_daemon.py --once --no-wake"
echo "  3. python3 voice/wake_word.py   # requires mic + optional openwakeword"
echo "  4. cp voice/launchd/com.jarvis.voice.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.jarvis.voice.plist"
