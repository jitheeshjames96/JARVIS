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

    keeper = ctx.get("keeper") or {}
    due = keeper.get("due_today", [])
    if due:
        parts.append(f"Keeper reminder today: {due[0].get('label')} — {due[0].get('relation')}.")
    upcoming = keeper.get("upcoming", [])
    if upcoming and not due:
        nxt = upcoming[0]
        parts.append(
            f"Next personal event: {nxt.get('label')} in {nxt.get('days_until')} days."
        )

    parts.append("I stand ready.")
    return " ".join(parts)


def dashboard_url() -> str:
    try:
        import yaml
        cfg_path = ROOT / "config" / "gcp.yaml"
        if cfg_path.exists():
            with cfg_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            bucket = cfg.get("bucket", "jarvis-jitheesh-2026")
            return f"https://storage.googleapis.com/{bucket}/dashboard.html"
    except Exception:
        pass
    return "https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html"


def open_dashboard(tab: str | None = None) -> str:
    url = dashboard_url()
    if tab:
        url = f"{url}#tab={tab}"
    local = ROOT / "dashboard.html"
    subprocess.run(["python3", str(ROOT / "scripts" / "generate_dashboard.py")], check=False)
    if sys.platform == "darwin":
        if local.exists():
            target = str(local)
            if tab:
                target = f"file://{local}#tab={tab}"
            subprocess.run(["open", target], check=False)
        subprocess.run(["open", url], check=False)
    label = tab.upper() if tab else "COMMAND"
    return f"Dashboard online. {label} panel ready. Cloud URL: {url}"


def brief_devops(ctx: dict) -> str:
    devops = ctx.get("devops_gcp") or {}
    if not devops:
        subprocess.run(["python3", str(ROOT / "scripts" / "devops_gcp_monitor.py")], check=False)
        ctx = build()
        devops = ctx.get("devops_gcp") or {}
    status = devops.get("status", "unknown")
    issues = devops.get("issues", [])
    parts = [f"DevOps GCP report for jarvis-jitheesh-2026. Overall status: {status}."]
    if issues:
        parts.append(f"Found {len(issues)} issue{'s' if len(issues) != 1 else ''}.")
        for issue in issues[:4]:
            parts.append(issue)
        if len(issues) > 4:
            parts.append(f"And {len(issues) - 4} more. Open the DevOps tab for full detail.")
    else:
        parts.append("All checks passing on jitheeshjames27@gmail.com.")
    return " ".join(parts)


def brief_next(ctx: dict, name: str = "Jitheesh") -> str:
    priorities = ctx.get("priorities", [])
    devops = ctx.get("devops_gcp") or {}
    warnings = ctx.get("active_warnings", [])
    issues = devops.get("issues", [])

    parts = [f"Recommended next actions, {name}."]
    if issues:
        parts.append(f"First: resolve GCP issue — {issues[0]}. Say show DevOps for detail.")
    elif devops.get("status") == "degraded":
        parts.append("First: review DevOps panel — GCP is degraded.")
    if warnings:
        w = warnings[0].get("payload", {})
        parts.append(f"Oracle flagged {w.get('event', 'a market event')}. Review headlines before trading.")
    keeper = ctx.get("keeper") or {}
    due = keeper.get("due_today", [])
    if due:
        parts.append(f"Personal: {due[0].get('label')} is today. Wish them or take action.")
    elif keeper.get("upcoming"):
        nxt = keeper["upcoming"][0]
        if nxt.get("days_until", 99) <= 3:
            parts.append(
                f"Coming up: {nxt.get('label')} in {nxt.get('days_until')} days. Check Personal tab."
            )
    if priorities:
        parts.append(f"Your top task: {priorities[0]}.")
    else:
        parts.append("No urgent tasks. Review Oracle and Media tabs, then run market screeners.")
    parts.append("Clap anytime to give me a command.")
    return " ".join(parts)


def brief_media(ctx: dict) -> str:
    items = ctx.get("media_items", [])
    if not items:
        return "Media digest is empty. Refreshing video feeds now."
    parts = ["Latest video intelligence."]
    for m in items[:4]:
        parts.append(f"{m.get('source')}: {m.get('title')}.")
    parts.append("Open the Media tab on the dashboard for full list.")
    return " ".join(parts)


def brief_keeper(ctx: dict) -> str:
    keeper = ctx.get("keeper") or {}
    if not keeper:
        subprocess.run(["python3", str(ROOT / "scripts" / "keeper_reminders.py"), "--no-send"], check=False)
        ctx = build()
        keeper = ctx.get("keeper") or {}
    due = keeper.get("due_today", [])
    upcoming = keeper.get("upcoming", [])
    parts = ["Keeper personal brief."]
    if due:
        for item in due[:3]:
            parts.append(f"Today: {item.get('label')} ({item.get('relation')}).")
    if upcoming:
        for item in upcoming[:5]:
            days = item.get("days_until", 0)
            when = "today" if days == 0 else f"in {days} days"
            parts.append(f"{item.get('label')} ({item.get('kind')}) {when}.")
    missing = keeper.get("contacts_missing_birthdays", 0)
    if missing:
        parts.append(f"{missing} family contacts still need birthdays in personal.yaml.")
    if not due and not upcoming:
        parts.append("No upcoming events. Add birthdays in config/personal.yaml.")
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

    if any(w in cmd for w in ("dashboard", "bring up", "show console", "visual", "display", "open console")):
        tab = None
        if any(w in cmd for w in ("news", "oracle", "headline")):
            tab = "oracle"
        elif any(w in cmd for w in ("video", "videos", "media", "youtube")):
            tab = "media"
        elif any(w in cmd for w in ("devops", "gcp", "cloud", "infra")):
            tab = "devops"
        elif any(w in cmd for w in ("market", "markets", "nse", "forex")):
            tab = "markets"
        elif any(w in cmd for w in ("personal", "family", "birthday", "birthdays", "keeper")):
            tab = "personal"
        elif "agent" in cmd:
            tab = "agents"
        return open_dashboard(tab)

    if any(w in cmd for w in ("open oracle", "oracle tab", "show news tab", "news tab")):
        return open_dashboard("oracle")

    if any(w in cmd for w in ("open media", "media tab", "show videos", "video tab")):
        return open_dashboard("media")

    if any(w in cmd for w in ("open devops", "devops tab", "gcp tab", "show gcp")):
        return open_dashboard("devops")

    if any(w in cmd for w in ("open personal", "personal tab", "family tab", "show birthdays")):
        return open_dashboard("personal")

    if any(w in cmd for w in ("what next", "what should i do", "what do i do", "recommend")):
        return brief_next(ctx, name)

    if any(w in cmd for w in (
        "birthday", "birthdays", "family", "relative", "relatives",
        "sibling", "siblings", "coming up", "upcoming events", "keeper",
    )) and not any(w in cmd for w in ("devops", "gcp")):
        return brief_keeper(ctx)

    if any(w in cmd for w in ("personal reminders", "personal events")):
        return brief_keeper(ctx)

    if any(w in cmd for w in ("devops", "gcp health", "gcp status", "cloud health", "infrastructure")):
        return brief_devops(ctx)

    if any(w in cmd for w in ("videos", "youtube", "media digest")):
        return brief_media(ctx)

    if any(w in cmd for w in ("status", "brief", "report", "what's happening", "what is happening")):
        return brief_status(ctx, name)

    if "agent" in cmd and ("all" in cmd or "roster" in cmd or "each" in cmd):
        return brief_agents(ctx)

    if any(w in cmd for w in ("news", "headlines", "world", "oracle")):
        headlines = ctx.get("news_headlines", [])
        if not headlines:
            return "Oracle has no cached headlines. Refreshing feeds now."
        parts = ["Oracle live intelligence."]
        for h in headlines[:5]:
            age = h.get("age_display", "")
            when = h.get("published_display", "")
            parts.append(f"{h.get('title')}. Published {when}. {age}.")
        return " ".join(parts)

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
        "Try status, news, personal, DevOps, media, what next, or open a dashboard tab."
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
