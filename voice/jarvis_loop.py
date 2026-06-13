#!/usr/bin/env python3
"""
JARVIS conversational loop — listen, transcribe, route, speak.
Used by jarvis_daemon.py for command capture after wake word.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "voice"))

from speaker_verify import verify  # noqa: E402
from audio_capture import record_wav  # noqa: E402


def speak(text: str) -> None:
    subprocess.run(["python3", str(ROOT / "voice" / "speak.py"), text], check=False)


def record_audio(seconds: int = 5) -> str | None:
    wav, err = record_wav(seconds)
    if err:
        print(f"[audio] {err}")
    return wav


def transcribe(wav_path: str) -> str | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(wav_path, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        return text or None
    except ImportError:
        return None
    except Exception:
        return None


def verify_speaker(wav_path: str) -> bool:
    accepted, score = verify(wav_path)
    print(f"[speaker] verification score: {score:.3f} accepted={accepted}")
    return accepted


def listen_once() -> str | None:
    print("[JARVIS] Listening for command...")
    wav = record_audio(6)
    if not wav:
        try:
            cmd = input("[JARVIS fallback] Type your command: ").strip()
            return cmd or None
        except EOFError:
            return None

    if not verify_speaker(wav):
        speak("Voice profile mismatch. Access denied.")
        try:
            import os
            os.remove(wav)
        except OSError:
            pass
        return None

    text = transcribe(wav)
    try:
        import os
        os.remove(wav)
    except OSError:
        pass

    if not text:
        try:
            cmd = input("[JARVIS fallback] Whisper unavailable. Type command: ").strip()
            return cmd or None
        except EOFError:
            return None

    print(f"[JARVIS heard] {text}")
    return text


def normalize_command(text: str) -> str:
    t = text.lower().strip()
    for prefix in ("hey jarvis", "ok jarvis", "jarvis"):
        if t.startswith(prefix):
            return text[len(prefix):].strip(" ,.!-")
    return text


def main():
    print("=== JARVIS Conversational Loop (push-to-talk) ===")
    speak("JARVIS online. Awaiting your instruction.")

    while True:
        try:
            raw = listen_once()
            if not raw:
                continue
            command = normalize_command(raw)
            if not command:
                speak("I didn't catch an instruction.")
                continue
            subprocess.run(["python3", str(ROOT / "voice" / "intent_router.py"), command], check=False)
            subprocess.run(["python3", str(ROOT / "scripts" / "build_live_context.py")], check=False)
            subprocess.run(["python3", str(ROOT / "scripts" / "generate_dashboard.py")], check=False)
            time.sleep(0.5)
        except KeyboardInterrupt:
            speak("Going offline.")
            break


if __name__ == "__main__":
    main()
