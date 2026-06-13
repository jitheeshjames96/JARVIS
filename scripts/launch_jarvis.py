#!/usr/bin/env python3
"""Avengers-style JARVIS console startup — live data only."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_live_context import build  # noqa: E402


def speak(text: str) -> None:
    subprocess.run(["python3", str(ROOT / "voice" / "speak.py"), text], check=False)


def main():
    print("=== JARVIS Console Launch ===")

    # Refresh all live sources first
    subprocess.run(["python3", str(ROOT / "scripts" / "build_live_context.py")], check=False)
    subprocess.run(["python3", str(ROOT / "scripts" / "generate_dashboard.py")], check=False)

    ctx_path = ROOT / "cache" / "live-context.json"
    with ctx_path.open(encoding="utf-8") as f:
        ctx = json.load(f)

    name = "Jitheesh"
    profile = ROOT / "config" / "profile.yaml"
    if profile.exists():
        try:
            import yaml
            with profile.open(encoding="utf-8") as f:
                name = yaml.safe_load(f).get("name", name)
        except Exception:
            pass

    speak(
        f"Online and ready, {name}. "
        "Re-establishing specialist agent connections. Bringing up your visual console."
    )

    subprocess.run(["open", str(ROOT / "dashboard.html")], check=False)
    time.sleep(1.2)

    # Live brief — only meaningful state, not robotic read of every idle agent
    warnings = ctx.get("active_warnings", [])
    if warnings:
        w = warnings[0].get("payload", {})
        speak(f"Oracle flags an active warning. {w.get('event', 'Macro event')}. Exercise caution.")

    running = ctx.get("agents_running", [])
    if running:
        summaries = []
        for agent in running:
            info = ctx.get("agents", {}).get(agent, {})
            summaries.append(f"{agent}: {info.get('summary', 'active')}")
        speak("Agents currently running. " + ". ".join(summaries) + ".")

    alerts = ctx.get("agents_alert", [])
    if alerts:
        speak(f"Alert state detected on {', '.join(alerts)}. Review the console immediately.")

    signals = ctx.get("trade_signals", [])
    if signals:
        s = signals[0].get("payload", {})
        speak(
            f"Strategist queue shows a signal on {s.get('symbol')}. "
            f"Setup score {s.get('setup_score', 'pending')}."
        )

    priorities = ctx.get("priorities", [])
    if priorities:
        speak(f"Synergy priority one: {priorities[0]}.")

    headlines = ctx.get("news_headlines", [])
    if headlines:
        speak(f"Oracle top headline: {headlines[0].get('title')}.")

    # Mention non-idle agents only
    for agent, info in ctx.get("agents", {}).items():
        state = info.get("state", "idle")
        summary = info.get("summary", "")
        if state == "idle" and ("initialized" in summary.lower() or "standing by" in summary.lower()):
            continue
        if agent in running or agent in alerts:
            continue
        speak(f"{agent} is {state}. {summary}.")

    speak(f"All connection lines established, {name}. The system console is yours.")


if __name__ == "__main__":
    main()
