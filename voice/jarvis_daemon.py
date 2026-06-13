#!/usr/bin/env python3
"""Always-on JARVIS daemon — clap, wake word, speaker verify, live intent routing."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "voice"))

from clap_detect import wait_for_clap  # noqa: E402
from daemon_config import trigger_mode  # noqa: E402
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


def wait_for_trigger(mode: str) -> bool:
    if mode in ("none", "push", "off"):
        return True
    if mode == "clap":
        return wait_for_clap()
    if mode in ("wake_word", "wake"):
        return wait_for_wake_word()
    if mode == "auto":
        return wait_for_clap()
    return wait_for_clap()


def handle_interaction(trigger: str = "clap", refresh: bool = False, session: bool = True) -> None:
    if refresh:
        refresh_stale_caches()

    if trigger not in ("none", "push", "off"):
        if not wait_for_trigger(trigger):
            return
        speak("Yes? I'm listening. Say stand down when finished.")

    while True:
        raw = listen_once()
        if not raw:
            if session:
                continue
            return
        command = normalize_command(raw)
        if not command:
            speak("I didn't catch an instruction. Try again, or say stand down.")
            if not session:
                return
            continue
        if "stand down" in command.lower():
            speak("Standing down.")
            break
        process_command(command)
        if not session:
            break


def main():
    parser = argparse.ArgumentParser(description="JARVIS always-on voice daemon")
    parser.add_argument("--once", action="store_true", help="Single interaction then exit")
    parser.add_argument(
        "--trigger",
        choices=["clap", "wake_word", "none", "auto"],
        default=None,
        help="Activation trigger (default: config profile voice_daemon.trigger)",
    )
    parser.add_argument(
        "--no-wake", action="store_true",
        help="Skip trigger — listen immediately (same as --trigger none)",
    )
    parser.add_argument(
        "--no-session", action="store_true",
        help="Single command per wake (legacy mode)",
    )
    args = parser.parse_args()

    if args.no_wake:
        trigger = "none"
    elif args.trigger:
        trigger = args.trigger
    else:
        trigger = trigger_mode()

    if not profile_enrolled():
        print("[daemon] No voice profile — run: python3 voice/enroll_speaker.py")
        print("[daemon] Operating in open speaker mode until enrolled.")

    if args.once:
        refresh_stale_caches()
        handle_interaction(trigger=trigger, session=not args.no_session)
        return

    label = {"clap": "clap", "wake_word": "wake word", "none": "voice"}.get(trigger, trigger)
    refresh_stale_caches()
    speak(f"JARVIS daemon online. Clap to wake. Say stand down to end session.")
    while True:
        try:
            handle_interaction(trigger=trigger, refresh=False, session=not args.no_session)
            time.sleep(0.3)
        except KeyboardInterrupt:
            speak("Daemon standing down.")
            break


if __name__ == "__main__":
    main()
