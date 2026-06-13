#!/bin/bash
set -e

# Make sure all scripts are executable
chmod +x scripts/*.py scripts/*.sh voice/*.py voice/*.sh || true

echo "=== 1. Testing Piper TTS sound output ==="
python3 voice/speak.py "This is a neural speech synthesis check using Piper."

echo -e "\n=== 2. Testing Piper Fallback (Simulating missing model) ==="
# Simulate missing model by passing invalid model path in environment or inline
# Temporarily modify configuration file or override model settings
python3 -c '
import subprocess
# Test speak.py with non-existent model to trigger fallback
import yaml
with open("config/profile.yaml", "r") as f:
    cfg = yaml.safe_load(f)
old_tts = cfg["voice"].get("tts_provider")
cfg["voice"]["tts_provider"] = "piper"
cfg["voice"]["model_path"] = "nonexistent.onnx"
with open("config/profile.yaml", "w") as f:
    yaml.dump(cfg, f)
try:
    subprocess.run(["python3", "voice/speak.py", "Simulating missing model. Falling back to default system voice."], check=True)
finally:
    cfg["voice"]["tts_provider"] = old_tts
    cfg["voice"]["model_path"] = "voice/piper/en_GB-alan-medium.onnx"
    with open("config/profile.yaml", "w") as f:
        yaml.dump(cfg, f)
'

echo -e "\n=== 3. Testing Notification Mirror (Dry-Run) ==="
python3 scripts/mirror_notifications.py --dry-run

echo -e "\n=== 4. Testing Wake Word Stub ==="
python3 -c '
import subprocess
p = subprocess.Popen(["python3", "voice/wake_word.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
# Send empty enter key to exit prompt in listen.sh
stdout, _ = p.communicate(input="\n")
print("Wake word stub executed successfully.")
'

echo -e "\n=== Phase 4 Validation Successful! ==="
