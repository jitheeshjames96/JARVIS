#!/bin/bash
set -e

PIPER_DIR="voice/piper"
mkdir -p "$PIPER_DIR"

echo "=== 1. Checking Voice Model ==="
MODEL_FILE="$PIPER_DIR/en_GB-alan-medium.onnx"
MODEL_JSON="$PIPER_DIR/en_GB-alan-medium.onnx.json"

if [ -f "$MODEL_FILE" ]; then
    echo "Voice model already exists."
else
    echo "Downloading en_GB-alan-medium model..."
    curl -L -o "$MODEL_FILE" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
    curl -L -o "$MODEL_JSON" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"
    echo "Model downloaded."
fi

echo -e "\n=== 2. Installing Piper Python Package ==="
if python3 -c "import piper" &>/dev/null; then
    echo "Piper python package is already installed."
else
    echo "Installing piper-tts package..."
    pip3 install --user piper-tts || echo "Warning: pip3 install failed. Speak script will fall back to macOS say."
fi

echo -e "\n=== Piper Setup Complete ==="
