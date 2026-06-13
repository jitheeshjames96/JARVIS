#!/usr/bin/env python3
"""Route spoken/text commands to JARVIS intents using live context."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_live_context import build  # noqa: E402


def speak(text: str) -> None:
    subprocess.run(["python3", str(ROOT / "voice" / "speak.py"), text], check=False)


def brief_status(ctx: dict, name: str = "Jitheesh") -> str:
    agents = ctx.get("agents", {})
    running = ctx.get("agents_running", [])
    alerts = ctx.get("agents_alert", [])
    warnings = ctx.get("active_warnings", [])
    priorities = ctx.get("priorities", [])
    headlines = ctx.get("news_headlines", [])
    signals = ctx.get("trade_signals", [])

    parts = [f"Good to see you, {name}. Here is your live system brief."]

    if warnings:
        w = warnings[0].get("payload", {})
        parts.append(f"Oracle has an active market warning: {w.get('event', 'high impact event')}.")
    else:
        parts.append("No active macro warnings on the bus.")

    if running:
        parts.append(f"Agents currently running: {', '.join(running)}.")
    if alerts:
        parts.append(f"Agents in alert state: {', '.join(alerts)}.")

    if signals:
        s = signals[0].get("payload", {})
        parts.append(
            f"Latest trade signal: {s.get('symbol')} with setup score {s.get('setup_score', 'pending')}."
        )

    if priorities:
        parts.append(f"Your top priority is: {priorities[0]}.")
        if len(priorities) > 1:
            parts.append(f"Also pending: {priorities[1]}.")
    else:
        parts.append("No urgent tasks in your queue.")

    if headlines:
        parts.append(f"Top headline: {headlines[0].get('title')}.")

    parts.append("I stand ready.")
    return " ".join(parts)


def brief_agents(ctx: dict) -> str:
    agents = ctx.get("agents", {})
    if not agents:
        return "Agent status board is unavailable."
    lines = ["Agent roster report."]
    for name, info in agents.items():
        state = info.get("state", "idle")
        summary = info.get("summary", "standing by")
        if state != "idle" or "initialized" not in summary.lower():
            lines.append(f"{name} is {state}. {summary}.")
    return " ".join(lines)


def route(command: str, name: str = "Jitheesh") -> str:
    cmd = command.lower().strip()
    ctx = build()

    if any(w in cmd for w in ("launch", "console", "startup", "come online")):
        subprocess.run(["python3", str(ROOT / "scripts" / "launch_jarvis.py")], check=False)
        return "Launch sequence initiated."

    if any(w in cmd for w in ("status", "brief", "report", "what's happening", "what is happening")):
        return brief_status(ctx, name)

    if "agent" in cmd and ("all" in cmd or "roster" in cmd or "each" in cmd):
        return brief_agents(ctx)

    if any(w in cmd for w in ("news", "headlines", "world", "oracle")):
        headlines = ctx.get("news_headlines", [])
        if not headlines:
            return "Oracle has no cached headlines. Run the morning brief pipeline first."
        return "Oracle headlines. " + ". ".join(h["title"] for h in headlines[:3]) + "."

    if any(w in cmd for w in ("priority", "priorities", "tasks", "todo")):
        p = ctx.get("priorities", [])
        if not p:
            return "Synergy reports no urgent priorities."
        return "Your priorities. " + ". ".join(p[:3]) + "."

    if any(w in cmd for w in ("trade", "setup", "forex", "stock", "market")):
        signals = ctx.get("trade_signals", [])
        if not signals:
            return "No active trade signals on the bus. Run the screeners or wait for the next scan."
        s = signals[0].get("payload", {})
        return (
            f"Latest signal on {s.get('symbol')}. "
            f"Score {s.get('setup_score', 'n/a')}. "
            f"Topic {signals[0].get('topic')}."
        )

    if any(w in cmd for w in ("warning", "alert", "caution")):
        warnings = ctx.get("active_warnings", [])
        if not warnings:
            return "No active market warnings."
        w = warnings[0].get("payload", {})
        return f"Active warning. {w.get('event')}. {w.get('title', '')}."

    return (
        "I heard you, but I'm not sure which specialist to route that to. "
        "Try status, news, priorities, agents, or trade setups."
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: intent_router.py <command text>")
        sys.exit(1)
    command = " ".join(sys.argv[1:])
    response = route(command)
    speak(response)
    print(json.dumps({"command": command, "response": response}, indent=2))


if __name__ == "__main__":
    main()
