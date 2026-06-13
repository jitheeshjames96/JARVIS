#!/usr/bin/env python3
"""Aggregate all live JARVIS data sources into a single context snapshot."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def read_bus_folder(folder: Path, limit: int = 10) -> list[dict]:
    if not folder.exists():
        return []
    messages = []
    for fpath in folder.glob("*.json"):
        data = read_json(fpath)
        if data:
            messages.append(data)
    messages.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    return messages[:limit]


def parse_tasks(md_path: Path) -> dict:
    urgent, backlog = [], []
    section = None
    if not md_path.exists():
        return {"urgent": urgent, "backlog": backlog}
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if "## Urgent" in line:
            section = "urgent"
            continue
        if "## Backlog" in line:
            section = "backlog"
            continue
        m = re.match(r"^- \[[ x]\] (.+)$", line.strip())
        if m and section:
            text = m.group(1).split("#")[0].strip()
            done = line.strip().startswith("- [x]")
            item = {"text": text, "done": done}
            (urgent if section == "urgent" else backlog).append(item)
    return {"urgent": urgent, "backlog": backlog}


def parse_projects(md_path: Path) -> list[dict]:
    projects = []
    if not md_path.exists():
        return projects
    blocks = re.split(r"\n## ", md_path.read_text(encoding="utf-8"))
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip()
        status = "Unknown"
        next_actions = []
        for line in lines[1:]:
            if line.strip().startswith("*") and "**Status:**" in line:
                status = line.split("**Status:**")[-1].strip().strip("*").strip()
            if line.strip().startswith("- ["):
                next_actions.append(line.strip())
        projects.append({"name": name, "status": status, "next_actions": next_actions[:3]})
    return projects


def latest_market_snapshots() -> list[dict]:
    folder = ROOT / "cache" / "market-snapshots"
    if not folder.exists():
        return []
    rows = []
    for csv in folder.glob("*.csv"):
        try:
            lines = csv.read_text(encoding="utf-8").strip().splitlines()
            if len(lines) < 2:
                continue
            last = lines[-1].split(",")
            rows.append({
                "symbol": csv.stem,
                "close": last[4] if len(last) > 4 else last[-1],
                "updated": datetime.fromtimestamp(csv.stat().st_mtime).isoformat(timespec="seconds"),
            })
        except OSError:
            continue
    return rows


def build() -> dict:
    status = read_json(ROOT / "cache" / "agent-status.json", {"agents": {}, "updated_at": None})
    sentinel_gcp = read_json(ROOT / "cache" / "sentinel-gcp-report.json", None)
    news = read_json(ROOT / "cache" / "briefings" / "news-digest.json", [])
    tasks = parse_tasks(ROOT / "memory" / "tasks.md")
    projects = parse_projects(ROOT / "context" / "active-projects.md")

    inbox = read_bus_folder(ROOT / "cache" / "bus" / "inbox", 8)
    processed = read_bus_folder(ROOT / "cache" / "bus" / "processed", 5)
    broadcast = read_bus_folder(ROOT / "cache" / "bus" / "broadcast", 5)

    warnings = [m for m in broadcast if m.get("topic") == "market_warning"]
    trade_plans = [
        m for m in (inbox + processed)
        if m.get("topic") in ("trade_plan_ready", "screener_alert", "forex_setup", "equity_setup")
    ]

    agents_running = [a for a, i in status.get("agents", {}).items() if i.get("state") == "running"]
    agents_alert = [a for a, i in status.get("agents", {}).items() if i.get("state") == "alert"]

    priorities = [t["text"] for t in tasks["urgent"] if not t["done"]][:5]

    context = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "agents": status.get("agents", {}),
        "agents_running": agents_running,
        "agents_alert": agents_alert,
        "active_warnings": warnings,
        "trade_signals": trade_plans[:5],
        "inbox_count": len(list((ROOT / "cache" / "bus" / "inbox").glob("*.json"))) if (ROOT / "cache" / "bus" / "inbox").exists() else 0,
        "priorities": priorities,
        "tasks": tasks,
        "projects": projects,
        "news_headlines": [
            {"title": n.get("title"), "source": n.get("source"), "link": n.get("link")}
            for n in news[:5]
        ],
        "market_snapshots": latest_market_snapshots(),
        "sentinel_gcp": sentinel_gcp,
    }
    return context


def main():
    ctx = build()
    out = ROOT / "cache" / "live-context.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)
        f.write("\n")
    print(f"Live context written: {out}")
    return ctx


if __name__ == "__main__":
    main()
