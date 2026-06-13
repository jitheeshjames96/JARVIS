#!/usr/bin/env python3
"""Generate cinematic JARVIS dashboard with live data refresh."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_json_file(fpath, default=None):
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def read_actions_log(fpath):
    entries = []
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception:
            pass
    return entries[::-1][:15]


def read_bus_messages(folder):
    messages = []
    if os.path.exists(folder):
        try:
            for fname in os.listdir(folder):
                if fname.endswith(".json"):
                    with open(os.path.join(folder, fname), "r", encoding="utf-8") as f:
                        messages.append(json.load(f))
        except Exception:
            pass
    messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return messages[:10]


def main():
    # Refresh live news + markets if stale
    subprocess.run(
        ["python3", str(ROOT / "scripts" / "refresh_dashboard_data.py")],
        cwd=ROOT, check=False,
    )

    live = read_json_file(ROOT / "cache" / "live-context.json", {})
    status = read_json_file(ROOT / "cache" / "agent-status.json", {"updated_at": "N/A", "agents": {}})
    news = read_json_file(ROOT / "cache" / "briefings" / "news-digest.json", [])
    actions = read_actions_log(ROOT / "logs" / "agent-actions.jsonl")
    inbox_msgs = read_bus_messages(ROOT / "cache" / "bus" / "inbox")
    processed_msgs = read_bus_messages(ROOT / "cache" / "bus" / "processed")
    broadcast_msgs = read_bus_messages(ROOT / "cache" / "bus" / "broadcast")
    sentinel_gcp = live.get("sentinel_gcp") or read_json_file(ROOT / "cache" / "sentinel-gcp-report.json", {})
    devops_gcp = live.get("devops_gcp") or read_json_file(ROOT / "cache" / "devops-gcp-report.json", {})
    weather = read_json_file(ROOT / "cache" / "weather.json", {})
    media_raw = read_json_file(ROOT / "cache" / "briefings" / "media-digest.json", {})
    media_items = media_raw.get("items", []) if isinstance(media_raw, dict) else []
    keeper = live.get("keeper") or read_json_file(ROOT / "cache" / "keeper-report.json", {})

    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from dashboard_render import render_dashboard  # noqa: E402

    html_content = render_dashboard(
        live, status, news, actions,
        inbox_msgs, processed_msgs, broadcast_msgs, sentinel_gcp,
        weather=weather,
        devops_gcp=devops_gcp,
        media_items=media_items,
        keeper=keeper,
    )

    fpath = ROOT / "dashboard.html"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Visual status dashboard updated: {fpath}")

    try:
        import yaml
        gcp_cfg = ROOT / "config" / "gcp.yaml"
        if gcp_cfg.exists():
            with gcp_cfg.open(encoding="utf-8") as gf:
                gcp = yaml.safe_load(gf) or {}
            if gcp.get("enabled"):
                subprocess.run(
                    ["python3", str(ROOT / "scripts" / "sentinel_gcp_monitor.py"), "--fetch-only"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                subprocess.run(["python3", str(ROOT / "scripts" / "gcp_sync.py")], check=False)
    except Exception:
        pass


if __name__ == "__main__":
    main()
