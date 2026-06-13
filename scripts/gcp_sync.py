#!/usr/bin/env python3
"""Upload dashboard.html to GCS via gsutil (opt-in via config/gcp.yaml)."""

from __future__ import annotations

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
        import yaml  # type: ignore
        with CONFIG.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def gcloud_value(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["gcloud", *args],
            capture_output=True, text=True, check=False,
        )
        value = (result.stdout or "").strip()
        return value or None
    except OSError:
        return None


def sync() -> int:
    cfg = load_config()
    if not cfg.get("enabled"):
        return 0

    account = cfg.get("account", REQUIRED_ACCOUNT)
    bucket = cfg.get("bucket")
    project = cfg.get("project")
    cache_control = cfg.get("cache_control", "max-age=30")

    if not bucket:
        print("[gcp_sync] Missing bucket in config/gcp.yaml", file=sys.stderr)
        return 1

    if not DASHBOARD.exists():
        print("[gcp_sync] dashboard.html not found — run generate_dashboard.py first", file=sys.stderr)
        return 1

    active_account = gcloud_value(["config", "get-value", "account"])
    if active_account != account:
        print(
            f"[gcp_sync] Refusing upload: active account is '{active_account}', "
            f"required '{account}'.\n"
            f"  gcloud config configurations activate {REQUIRED_CONFIG}\n"
            f"  gcloud config set account {account}",
            file=sys.stderr,
        )
        return 1

    active_cfg = gcloud_value([
        "config", "configurations", "list",
        "--filter", "IS_ACTIVE=true", "--format", "value(name)",
    ])
    if active_cfg != REQUIRED_CONFIG:
        print(
            f"[gcp_sync] Refusing upload: active config is '{active_cfg}', "
            f"required '{REQUIRED_CONFIG}'.\n"
            f"  gcloud config configurations activate {REQUIRED_CONFIG}",
            file=sys.stderr,
        )
        return 1

    gs_uri = f"gs://{bucket}/dashboard.html"
    public_url = f"https://storage.googleapis.com/{bucket}/dashboard.html"

    env = None
    if project:
        import os
        env = os.environ.copy()
        env["CLOUDSDK_CORE_PROJECT"] = project

    cmd = [
        "gsutil", "-h", f"Cache-Control:{cache_control}",
        "cp", str(DASHBOARD), gs_uri,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    except OSError as exc:
        print(f"[gcp_sync] gsutil not available: {exc}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        print(f"[gcp_sync] Upload failed: {err}", file=sys.stderr)
        return result.returncode

    print(f"Visual status dashboard uploaded to GCS: {public_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync())
