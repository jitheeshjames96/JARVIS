#!/usr/bin/env python3
"""DevOps agent — comprehensive GCP health audit for jarvis-jitheesh-2026."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "cache" / "devops-gcp-report.json"
REQUIRED_ACCOUNT = "jitheeshjames27@gmail.com"
REQUIRED_PROJECT = "jarvis-jitheesh-2026"
REQUIRED_BUCKET = "jarvis-jitheesh-2026"
REQUIRED_CONFIG = "jarvis-personal"


def gcloud(args: list[str], project: str | None = None) -> tuple[int, str]:
    cmd = ["gcloud", *args]
    if project:
        cmd.extend(["--project", project])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=45, check=False)
        return r.returncode, (r.stdout or r.stderr or "").strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, str(exc)


def http_check(url: str) -> dict:
    start = __import__("time").perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-DevOps/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            ms = round((__import__("time").perf_counter() - start) * 1000, 1)
            return {"ok": 200 <= resp.status < 400, "status": resp.status, "latency_ms": ms}
    except Exception as exc:
        ms = round((__import__("time").perf_counter() - start) * 1000, 1)
        return {"ok": False, "status": None, "latency_ms": ms, "error": str(exc)}


def audit() -> dict:
    issues = []
    checks = {}

    # Account & config
    code, account = gcloud(["config", "get-value", "account"])
    checks["account"] = {"value": account, "ok": account == REQUIRED_ACCOUNT}
    if account != REQUIRED_ACCOUNT:
        issues.append(f"Wrong gcloud account: {account} (need {REQUIRED_ACCOUNT})")

    code, cfg = gcloud([
        "config", "configurations", "list",
        "--filter", "IS_ACTIVE=true", "--format", "value(name)",
    ])
    checks["config_profile"] = {"value": cfg, "ok": cfg == REQUIRED_CONFIG}
    if cfg != REQUIRED_CONFIG:
        issues.append(f"Active config is {cfg}, expected {REQUIRED_CONFIG}")

    code, proj = gcloud(["config", "get-value", "project"])
    checks["project"] = {"value": proj, "ok": proj == REQUIRED_PROJECT}
    if proj != REQUIRED_PROJECT:
        issues.append(f"Active project is {proj}")

    # Billing
    code, billing_out = gcloud(["billing", "projects", "describe", REQUIRED_PROJECT, "--format=json"])
    billing_ok = False
    if code == 0:
        try:
            b = json.loads(billing_out)
            billing_ok = bool(b.get("billingEnabled"))
            checks["billing"] = {"enabled": billing_ok, "account": b.get("billingAccountName"), "ok": billing_ok}
        except json.JSONDecodeError:
            checks["billing"] = {"ok": False, "error": billing_out[:200]}
    else:
        checks["billing"] = {"ok": False, "error": billing_out[:200]}
    if not billing_ok:
        issues.append("Billing not enabled on jarvis-jitheesh-2026")

    # GCS bucket + dashboard
    code, _ = subprocess.run(
        ["gsutil", "stat", f"gs://{REQUIRED_BUCKET}/dashboard.html"],
        capture_output=True, check=False,
    ).returncode, ""
    checks["gcs_dashboard"] = {"ok": code == 0, "path": f"gs://{REQUIRED_BUCKET}/dashboard.html"}
    if code != 0:
        issues.append("dashboard.html missing from GCS bucket")

    dash_url = f"https://storage.googleapis.com/{REQUIRED_BUCKET}/dashboard.html"
    dash_probe = http_check(dash_url)
    checks["dashboard_http"] = dash_probe
    if not dash_probe.get("ok"):
        issues.append(f"Dashboard URL unreachable: {dash_probe.get('error', dash_probe.get('status'))}")

    # Cloud Function
    code, fn_out = gcloud([
        "functions", "describe", "sentinel-gcp-monitor",
        "--gen2", "--region=asia-south1", "--format=json(state,updateTime)",
    ], project=REQUIRED_PROJECT)
    fn_ok = code == 0
    fn_state = ""
    if fn_ok:
        try:
            fn_state = json.loads(fn_out).get("state", "UNKNOWN")
            fn_ok = fn_state == "ACTIVE"
        except json.JSONDecodeError:
            pass
    checks["cloud_function"] = {"name": "sentinel-gcp-monitor", "state": fn_state, "ok": fn_ok}
    if not fn_ok:
        issues.append(f"Cloud Function not ACTIVE (state={fn_state or 'missing'})")

    # Scheduler
    code, sch_out = gcloud([
        "scheduler", "jobs", "describe", "sentinel-gcp-hourly",
        "--location=asia-south1", "--format=json(state,lastAttemptTime,status)",
    ], project=REQUIRED_PROJECT)
    sch_ok = code == 0
    sch_state = ""
    if sch_ok:
        try:
            s = json.loads(sch_out)
            sch_state = s.get("state", "")
            sch_ok = sch_state == "ENABLED"
            checks["scheduler"] = {
                "state": sch_state,
                "last_attempt": s.get("lastAttemptTime"),
                "ok": sch_ok,
            }
        except json.JSONDecodeError:
            checks["scheduler"] = {"ok": False}
    else:
        checks["scheduler"] = {"ok": False, "error": sch_out[:120]}
    if not sch_ok:
        issues.append("Cloud Scheduler sentinel-gcp-hourly not enabled")

    # Enabled APIs
    required_apis = [
        "storage.googleapis.com",
        "cloudfunctions.googleapis.com",
        "cloudscheduler.googleapis.com",
        "run.googleapis.com",
    ]
    api_status = {}
    for api in required_apis:
        code, out = gcloud(["services", "list", "--enabled", f"--filter=config.name:{api}", "--format=value(config.name)"], project=REQUIRED_PROJECT)
        api_status[api] = api in out
        if api not in out:
            issues.append(f"API not enabled: {api}")
    checks["apis"] = api_status

    status = "healthy" if not issues else ("degraded" if len(issues) <= 2 else "critical")

    return {
        "agent": "DevOps",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "account": REQUIRED_ACCOUNT,
        "project": REQUIRED_PROJECT,
        "status": status,
        "issue_count": len(issues),
        "issues": issues,
        "checks": checks,
        "dashboard_url": dash_url,
        "summary": (
            f"GCP {status}: {len(issues)} issue(s)"
            if issues else f"GCP healthy — dashboard {dash_probe.get('latency_ms')}ms"
        ),
    }


def update_status(report: dict) -> None:
    state_map = {"healthy": "idle", "degraded": "running", "critical": "alert"}
    subprocess.run([
        "python3", str(ROOT / "scripts" / "update_agent_status.py"),
        "--agent", "DevOps",
        "--state", state_map.get(report["status"], "running"),
        "--summary", report["summary"],
        "--next-run", "Hourly + on dashboard refresh",
    ], check=False)

    if report["status"] != "healthy":
        payload = json.dumps({
            "event": f"GCP {report['status']}",
            "issues": report["issues"][:5],
            "project": REQUIRED_PROJECT,
        })
        subprocess.run([
            "python3", str(ROOT / "scripts" / "bus_write.py"),
            "--from-agent", "DevOps",
            "--to-agent", "Synergy",
            "--topic", "infra_alert",
            "--payload", payload,
            "--priority", "high",
        ], check=False)


def main() -> int:
    report = audit()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    update_status(report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
