#!/usr/bin/env python3
"""Enroll Jitheesh voice profile for speaker verification."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "cache" / "voice-profile.json"
sys.path.insert(0, str(ROOT / "voice"))

from speaker_verify import build_profile_from_samples, compute_embedding  # noqa: E402


def record(seconds: int = 4) -> str | None:
    wav = tempfile.mktemp(suffix=".wav")
    cmd = ["ffmpeg", "-y", "-f", "avfoundation", "-i", ":0", "-t", str(seconds), "-ac", "1", "-ar", "16000", wav]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=seconds + 5)
        if Path(wav).stat().st_size > 1000:
            return wav
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass
    return None


def main():
    print("=== JARVIS Speaker Enrollment ===")
    print("Record 3 phrases. Only your voice will be accepted after enrollment.\n")

    phrases = [
        "JARVIS, report system status.",
        "JARVIS, what are my priorities?",
        "JARVIS, bring up the console.",
    ]

    wav_paths = []
    samples = []

    for phrase in phrases:
        input(f"Press Enter, then read: '{phrase}'")
        wav = record(4)
        if not wav:
            print("Recording failed. Install ffmpeg: brew install ffmpeg")
            continue
        emb = compute_embedding(wav)
        samples.append({
            "phrase": phrase,
            "wav": wav,
            "embedding_preview": emb[:4],
            "recorded_at": datetime.now().isoformat(),
        })
        wav_paths.append(wav)
        print("Sample captured.")

    if len(wav_paths) < 2:
        print("Need at least 2 samples. Enrollment aborted.")
        sys.exit(1)

    mean_embedding = build_profile_from_samples(wav_paths)

    profile = {
        "owner": "Jitheesh",
        "enrolled_at": datetime.now().isoformat(),
        "embedding": mean_embedding,
        "samples": samples,
        "threshold": 0.68,
        "engine": "resemblyzer_or_spectral",
    }

    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    with PROFILE.open("w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")

    print(f"\nVoice profile saved: {PROFILE}")
    print("Speaker verification active. Non-matching voices will be denied.")


if __name__ == "__main__":
    main()
