#!/usr/bin/env python3
"""Upload full JARVIS HUD site + context to GCS."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard.html"
CONFIG = ROOT / "config" / "gcp.yaml"
REQUIRED_ACCOUNT = "jitheeshjames27@gmail.com"
REQUIRED_CONFIG = "jarvis-personal"


def load_config() -> dict:
    if not CONFIG.exists():
        return {}
    try:
        import yaml
        with CONFIG.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def gcloud_value(args: list[str]) -> str | None:
    try:
        r = subprocess.run(["gcloud", *args], capture_output=True, text=True, check=False)
        return (r.stdout or "").strip() or None
    except OSError:
        return None


def gsutil(args: list[str], project: str | None = None) -> int:
    import os
    env = os.environ.copy()
    if project:
        env["CLOUDSDK_CORE_PROJECT"] = project
    r = subprocess.run(["gsutil", *args], capture_output=True, text=True, check=False, env=env)
    if r.returncode != 0:
        print(f"[gcp_sync] gsutil fail: {r.stderr or r.stdout}", file=sys.stderr)
    return r.returncode


def sync() -> int:
    cfg = load_config()
    if not cfg.get("enabled"):
        return 0

    account = cfg.get("account", REQUIRED_ACCOUNT)
    bucket = cfg.get("bucket", "jarvis-jitheesh-2026")
    project = cfg.get("project")
    cache_control = cfg.get("cache_control", "max-age=60")

    if gcloud_value(["config", "get-value", "account"]) != account:
        print(f"[gcp_sync] Wrong gcloud account. Need {account}", file=sys.stderr)
        return 1
    if gcloud_value(["config", "configurations", "list", "--filter", "IS_ACTIVE=true", "--format", "value(name)"]) != REQUIRED_CONFIG:
        print(f"[gcp_sync] Wrong gcloud config. Need {REQUIRED_CONFIG}", file=sys.stderr)
        return 1

    subprocess.run([sys.executable, str(ROOT / "scripts" / "pack_hud_context.py")], cwd=ROOT, check=False)

    if not DASHBOARD.exists():
        print("[gcp_sync] Run generate_dashboard.py first", file=sys.stderr)
        return 1

    base = f"gs://{bucket}"
    h = f"-h"
    cc = f"Cache-Control:{cache_control}"

    uploads = [
        ([h, cc, "cp", str(DASHBOARD), f"{base}/dashboard.html"], "dashboard.html"),
    ]

    agents_dir = ROOT / "dashboards" / "agents"
    if agents_dir.exists():
        for html in agents_dir.glob("*.html"):
            uploads.append((
                [h, cc, "cp", str(html), f"{base}/agents/{html.name}"],
                f"agents/{html.name}",
            ))

    ctx = ROOT / "cache" / "hud-context.json"
    if ctx.exists():
        uploads.append((
            [h, "Cache-Control:no-cache", "cp", str(ctx), f"{base}/ops/hud-context.json"],
            "ops/hud-context.json",
        ))

    for args, label in uploads:
        if gsutil(args, project) != 0:
            return 1
        print(f"[gcp_sync] ↑ {label}")

    public = f"https://storage.googleapis.com/{bucket}/dashboard.html"
    voice_url = cfg.get("voice_api_url", "")
    print(f"HUD live: {public}")
    if voice_url:
        print(f"Voice API: {voice_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync())
