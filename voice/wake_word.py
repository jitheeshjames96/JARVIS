#!/usr/bin/env python3
"""
Wake word detector — blocks until 'JARVIS' is heard.

Tiers (auto-selected):
1. openWakeWord (local, free) — if installed
2. Porcupine (local after key) — if PICOVOICE_ACCESS_KEY set
3. Whisper chunk scan (local) — if faster-whisper installed
4. Keyboard fallback — press Enter to activate
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_voice_config() -> dict:
    try:
        import yaml
        path = ROOT / "config" / "profile.yaml"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return yaml.safe_load(f).get("voice_daemon", {})
    except Exception:
        pass
    return {}


def detect_openwakeword(keyword: str = "hey_jarvis") -> bool | None:
    """Return True on detection, None if engine unavailable."""
    cfg = _load_voice_config()
    try:
        import pyaudio  # type: ignore
        from openwakeword.model import Model  # type: ignore

        models = [keyword]
        oww = Model(wakeword_models=models, inference_framework="onnx")
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=16000, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=1280,
        )
        print(f"[wake] openWakeWord listening ({models})...")
        threshold = float(cfg.get("openwakeword_threshold", 0.60))
        try:
            from daemon_config import wake_threshold
            threshold = wake_threshold()
        except Exception:
            pass
        try:
            while True:
                audio = stream.read(1280, exception_on_overflow=False)
                preds = oww.predict(audio)
                for name, score in preds.items():
                    if score > threshold:
                        print(f"[wake] Detected {name} ({score:.2f})")
                        return True
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
    except Exception as e:
        print(f"[wake] openWakeWord unavailable: {e}")
        return None


def detect_porcupine(access_key: str, keyword_path: str | None = None) -> bool | None:
    try:
        import pvporcupine  # type: ignore
        import pvrecorder  # type: ignore

        kwargs: dict = {"access_key": access_key}
        if keyword_path and Path(keyword_path).exists():
            kwargs["keyword_paths"] = [keyword_path]
        else:
            kw = "jarvis" if "jarvis" in pvporcupine.KEYWORDS else "computer"
            kwargs["keywords"] = [kw]

        porcupine = pvporcupine.create(**kwargs)
        recorder = pvrecorder.PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
        recorder.start()
        print("[wake] Porcupine listening...")
        try:
            while True:
                pcm = recorder.read()
                if porcupine.process(pcm) >= 0:
                    print("[wake] Porcupine wake word detected")
                    return True
        finally:
            recorder.stop()
            recorder.delete()
            porcupine.delete()
    except Exception as e:
        print(f"[wake] Porcupine unavailable: {e}")
        return None


def detect_whisper_chunk(keyword: str = "jarvis", chunk_seconds: int = 2) -> bool | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print(f"[wake] Whisper chunk listener (say '{keyword}')...")
        while True:
            wav = tempfile.mktemp(suffix=".wav")
            cmd = [
                "ffmpeg", "-y", "-f", "avfoundation", "-i", ":0",
                "-t", str(chunk_seconds), "-ac", "1", "-ar", "16000", wav,
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=chunk_seconds + 3)
                if os.path.getsize(wav) > 1000:
                    segments, _ = model.transcribe(wav, language="en")
                    text = " ".join(s.text for s in segments).lower()
                    if keyword in text:
                        print(f"[wake] Heard: {text}")
                        return True
            except (subprocess.SubprocessError, OSError):
                pass
            finally:
                try:
                    os.remove(wav)
                except OSError:
                    pass
            time.sleep(0.2)
    except ImportError:
        print("[wake] faster-whisper not installed")
        return None
    except Exception as e:
        print(f"[wake] Whisper listener error: {e}")
        return None


def keyboard_fallback() -> bool:
    print("[wake] Press Enter to activate JARVIS (keyboard fallback)...")
    try:
        input()
        return True
    except EOFError:
        return False


def wait_for_wake_word() -> bool:
    cfg = _load_voice_config()
    keyword = cfg.get("wake_keyword", "jarvis")
    engine = cfg.get("wake_engine", "auto")

    if engine == "keyboard":
        return keyboard_fallback()

    engines = []
    if engine == "auto":
        engines = ["openwakeword", "porcupine", "whisper", "keyboard"]
    else:
        engines = [engine, "keyboard"]

    for eng in engines:
        if eng == "openwakeword":
            result = detect_openwakeword(cfg.get("openwakeword_model", "hey_jarvis"))
            if result is True:
                return True
        elif eng == "porcupine":
            key = os.environ.get("PICOVOICE_ACCESS_KEY") or cfg.get("picovoice_access_key")
            if key:
                result = detect_porcupine(key, cfg.get("porcupine_keyword_path"))
                if result is True:
                    return True
        elif eng == "whisper":
            result = detect_whisper_chunk(keyword)
            if result is True:
                return True
        elif eng == "keyboard":
            return keyboard_fallback()

    return keyboard_fallback()


def main():
    print("=== JARVIS Wake Word Listener ===")
    if wait_for_wake_word():
        subprocess.run(["python3", str(ROOT / "voice" / "jarvis_daemon.py"), "--once"], check=False)


if __name__ == "__main__":
    main()
