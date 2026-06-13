#!/usr/bin/env python3
"""Enroll Jitheesh voice profile for speaker verification."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "cache" / "voice-profile.json"
sys.path.insert(0, str(ROOT / "voice"))

from audio_capture import check_microphone, record_wav  # noqa: E402
from speaker_verify import build_profile_from_samples, compute_embedding  # noqa: E402


def countdown(seconds: int = 3) -> None:
    for i in range(seconds, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)


def capture_phrase(phrase: str, index: int, total: int) -> tuple[str | None, str | None]:
    print(f"\n[{index}/{total}] Read aloud: \"{phrase}\"")
    print("Get ready — recording starts after countdown.", flush=True)
    countdown(3)
    print(">>> RECORDING — speak now <<<", flush=True)
    return record_wav(4)


def main():
    parser = argparse.ArgumentParser(description="Enroll JARVIS speaker voice profile")
    parser.add_argument("--check-mic", action="store_true", help="Diagnose ffmpeg + microphone only")
    parser.add_argument(
        "--manual", action="store_true",
        help="Legacy mode: press Enter before each phrase (skip if Enter key misbehaves)",
    )
    args = parser.parse_args()

    if args.check_mic:
        raise SystemExit(check_microphone())

    print("=== JARVIS Speaker Enrollment ===")
    print("Record 3 phrases. Only your voice will be accepted after enrollment.")
    print("No Enter key needed — auto countdown before each recording.")
    print("Tip: if recording fails, run: python3 voice/enroll_speaker.py --check-mic\n")
    time.sleep(1)

    phrases = [
        "JARVIS, report system status.",
        "JARVIS, what are my priorities?",
        "JARVIS, bring up the console.",
    ]

    wav_paths = []
    samples = []

    for i, phrase in enumerate(phrases, 1):
        if args.manual:
            try:
                input(f"Press Enter, then read: '{phrase}'")
            except (EOFError, KeyboardInterrupt):
                print("\nEnrollment cancelled.")
                sys.exit(1)
            wav, err = record_wav(4)
        else:
            wav, err = capture_phrase(phrase, i, len(phrases))

        if not wav:
            print(f"Recording failed.\n{err}")
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
    print("\nNext: python3 voice/jarvis_daemon.py --once --no-wake")


if __name__ == "__main__":
    main()
