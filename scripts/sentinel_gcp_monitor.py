#!/usr/bin/env python3
"""Sentinel GCP prod monitor — run locally or post to bus + dashboard."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gcp" / "sentinel"))

from monitor_core import (  # noqa: E402
    DEFAULT_ACCOUNT,
    DEFAULT_BUCKET,
    DEFAULT_PROJECT,
    REPORT_KEY,
    build_report,
    upload_report,
)


def load_gcp_config() -> dict:
    cfg_path = ROOT / "config" / "gcp.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml  # type: ignore
        with cfg_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def fetch_report_from_gcs(bucket: str) -> dict | None:
    dest = ROOT / "cache" / "sentinel-gcp-report.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    code = subprocess.run(
        ["gsutil", "cp", f"gs://{bucket}/{REPORT_KEY}", str(dest)],
        capture_output=True, check=False,
    ).returncode
    if code != 0 or not dest.exists():
        return None
    try:
        return json.loads(dest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def update_agent_status(summary: str, state: str) -> None:
    subprocess.run([
        "python3", str(ROOT / "scripts" / "update_agent_status.py"),
        "--agent", "Sentinel",
        "--state", state,
        "--summary", summary,
        "--next-run", "Hourly (GCP Cloud Scheduler)",
    ], check=False)


def write_bus_alert(report: dict) -> None:
    if report.get("status") not in ("degraded", "outage"):
        return
    payload = json.dumps({
        "event": f"GCP prod {report['status']}",
        "project": report.get("project"),
        "detail": report.get("outage", {}).get("message"),
        "latency_ms": report.get("performance", {}).get("dashboard_latency_ms"),
    })
    subprocess.run([
        "python3", str(ROOT / "scripts" / "bus_write.py"),
        "--from-agent", "Sentinel",
        "--to-agent", "Synergy",
        "--topic", "infra_alert",
        "--payload", payload,
        "--priority", "high",
    ], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel GCP production monitor")
    parser.add_argument("--fetch-only", action="store_true", help="Pull latest cloud report from GCS")
    parser.add_argument("--no-upload", action="store_true", help="Skip uploading report to GCS")
    parser.add_argument("--no-status", action="store_true", help="Skip agent-status update")
    args = parser.parse_args()

    cfg = load_gcp_config()
    project = cfg.get("project", DEFAULT_PROJECT)
    bucket = cfg.get("bucket", DEFAULT_BUCKET)
    environment = cfg.get("environment", "prod")

    if args.fetch_only:
        report = fetch_report_from_gcs(bucket)
        if report:
            print(json.dumps(report, indent=2))
            return 0
        print("[sentinel] No cloud report found in GCS.", file=sys.stderr)
        return 1

    report = build_report(
        project=project,
        bucket=bucket,
        environment=environment,
        source="local",
    )

    if not args.no_upload:
        upload_report(report, bucket)

    cache_path = ROOT / "cache" / "sentinel-gcp-report.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    state_map = {"healthy": "idle", "degraded": "running", "outage": "alert"}
    if not args.no_status:
        update_agent_status(report["summary"], state_map.get(report["status"], "running"))
        write_bus_alert(report)

    print(json.dumps(report, indent=2))
    return 0 if report["status"] != "outage" else 2


if __name__ == "__main__":
    raise SystemExit(main())
