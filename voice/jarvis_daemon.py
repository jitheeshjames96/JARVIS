#!/usr/bin/env python3
"""Always-on JARVIS daemon — wake word, speaker verify, live intent routing."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "voice"))

from jarvis_loop import (  # noqa: E402
    listen_once,
    normalize_command,
    speak,
)
from speaker_verify import profile_enrolled  # noqa: E402
from wake_word import wait_for_wake_word  # noqa: E402


def refresh_stale_caches() -> None:
    subprocess.run(["python3", str(ROOT / "scripts" / "refresh_if_stale.py")], check=False)


def process_command(command: str) -> None:
    subprocess.run(
        ["python3", str(ROOT / "voice" / "intent_router.py"), command],
        check=False,
    )
    subprocess.run(["python3", str(ROOT / "scripts" / "build_live_context.py")], check=False)
    subprocess.run(["python3", str(ROOT / "scripts" / "generate_dashboard.py")], check=False)


def handle_interaction(use_wake_word: bool = False) -> None:
    refresh_stale_caches()

    if use_wake_word:
        if not wait_for_wake_word():
            return
        speak("Yes?")

    raw = listen_once()
    if not raw:
        return
    command = normalize_command(raw)
    if not command:
        speak("I didn't catch an instruction.")
        return
    process_command(command)


def main():
    parser = argparse.ArgumentParser(description="JARVIS always-on voice daemon")
    parser.add_argument("--once", action="store_true", help="Single interaction then exit")
    parser.add_argument("--no-wake", action="store_true", help="Skip wake word (push-to-talk)")
    args = parser.parse_args()

    if not profile_enrolled():
        print("[daemon] No voice profile — run: python3 voice/enroll_speaker.py")
        print("[daemon] Operating in open speaker mode until enrolled.")

    if args.once:
        handle_interaction(use_wake_word=not args.no_wake)
        return

    speak("JARVIS daemon online. Awaiting wake word.")
    while True:
        try:
            handle_interaction(use_wake_word=not args.no_wake)
            time.sleep(0.3)
        except KeyboardInterrupt:
            speak("Daemon standing down.")
            break


if __name__ == "__main__":
    main()
