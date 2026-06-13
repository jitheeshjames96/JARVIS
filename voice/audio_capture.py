"""macOS microphone capture via ffmpeg avfoundation."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def resolve_ffmpeg() -> str | None:
    for candidate in (
        shutil.which("ffmpeg"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def record_wav(seconds: int = 4, device: str = ":0") -> tuple[str | None, str | None]:
    """
    Record mono 16kHz WAV. Returns (path, error_message).
    error_message is set when recording fails.
    """
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return None, (
            "ffmpeg not found. Install: brew install ffmpeg\n"
            "Then ensure /opt/homebrew/bin is in your PATH."
        )

    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    cmd = [
        ffmpeg, "-y",
        "-f", "avfoundation",
        "-i", device,
        "-t", str(seconds),
        "-ac", "1",
        "-ar", "16000",
        wav,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=seconds + 10,
            check=False,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            hint = _failure_hint(err)
            return None, f"ffmpeg exit {result.returncode}: {err[-400:]}\n{hint}"

        size = Path(wav).stat().st_size
        if size <= 1000:
            return None, (
                f"Recording too small ({size} bytes). "
                "Check microphone input level and speak during the capture window."
            )
        return wav, None
    except subprocess.TimeoutExpired:
        return None, f"Recording timed out after {seconds + 10}s."
    except OSError as exc:
        return None, str(exc)


def _failure_hint(stderr: str) -> str:
    low = stderr.lower()
    if "input/output error" in low or "operation not permitted" in low:
        return (
            "Likely macOS microphone permission issue.\n"
            "Grant mic access: System Settings → Privacy & Security → Microphone → enable Terminal (or iTerm)."
        )
    if "no such file" in low or "not found" in low:
        return "ffmpeg missing from PATH. Run: brew install ffmpeg"
    return "Run: python3 voice/enroll_speaker.py --check-mic"


def check_microphone(device: str = ":0") -> int:
    ffmpeg = resolve_ffmpeg()
    print("=== JARVIS Microphone Check ===")
    print(f"ffmpeg: {ffmpeg or 'NOT FOUND'}")
    if not ffmpeg:
        print("\nInstall: brew install ffmpeg")
        return 1

    try:
        result = subprocess.run(
            [ffmpeg, "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True, text=True, timeout=15, check=False,
        )
        for line in (result.stderr or "").splitlines():
            if "audio devices" in line.lower() or "microphone" in line.lower() or line.strip().startswith("["):
                print(line)
    except subprocess.SubprocessError as exc:
        print(f"Device list failed: {exc}")

    print("\nRecording 2s test sample...")
    wav, err = record_wav(seconds=2, device=device)
    if wav:
        print(f"OK: captured {Path(wav).stat().st_size} bytes → {wav}")
        return 0
    print(f"FAIL: {err}")
    return 1
