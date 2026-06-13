#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
import shutil

def main():
    if len(sys.argv) < 2:
        print("Usage: speak.py [text]")
        return

    text = " ".join(sys.argv[1:])
    
    # 1. Load config options
    tts_provider = "macos_say"
    voice_name = "Daniel"
    rate = 152
    piper_path = "voice/piper/piper"
    model_path = "voice/piper/en_GB-alan-medium.onnx"
    length_scale = 1.05

    config_path = "config/profile.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f)
            v_cfg = cfg.get("voice", {})
            tts_provider = v_cfg.get("tts_provider", "macos_say")
            voice_name = v_cfg.get("voice_name", "Daniel")
            rate = v_cfg.get("rate", 152)
            piper_path = v_cfg.get("piper_path", "voice/piper/piper")
            model_path = v_cfg.get("model_path", "voice/piper/en_GB-alan-medium.onnx")
            length_scale = v_cfg.get("length_scale", 1.05)
        except Exception:
            pass

    # Print to console (written delivery)
    print(f"\n[JARVIS]: {text}\n")
    
    # 2. TTS Generation
    success = False

    if tts_provider == "piper":
        # Create output directory
        out_dir = "voice/output"
        os.makedirs(out_dir, exist_ok=True)
        wav_path = os.path.join(out_dir, "last_speech.wav")

        # Determine which piper executable path to use
        cmd = None
        if os.path.exists(piper_path):
            cmd = [piper_path, "--model", model_path, "--output_file", wav_path, "--length_scale", str(length_scale)]
        elif shutil.which("piper"):
            cmd = ["piper", "--model", model_path, "--output_file", wav_path, "--length_scale", str(length_scale)]
        else:
            # Try running as python module
            try:
                # Dry run check
                res = subprocess.run(["python3", "-m", "piper", "--help"], capture_output=True, text=True)
                if res.returncode == 0:
                    cmd = ["python3", "-m", "piper", "--model", model_path, "--output_file", wav_path, "--length_scale", str(length_scale)]
            except Exception:
                pass

        if cmd and os.path.exists(model_path):
            try:
                # Run piper TTS generation
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
                p.communicate(input=text)
                p.wait()
                
                if os.path.exists(wav_path):
                    # Play generated audio on Mac
                    subprocess.run(["afplay", wav_path], check=True)
                    success = True
            except Exception as e:
                print(f"(Piper TTS execution failed: {e}. Falling back to macOS say.)", file=sys.stderr)
        else:
            print("(Piper TTS executable or voice model not found. Falling back to macOS say.)", file=sys.stderr)

    if not success:
        # Fallback to macOS say
        try:
            subprocess.run(["say", "-r", str(rate), "-v", voice_name, text], check=True)
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
