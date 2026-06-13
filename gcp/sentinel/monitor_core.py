"""Sentinel GCP production monitor — cost, performance, outage checks."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

DEFAULT_PROJECT = "jarvis-jitheesh-2026"
DEFAULT_BUCKET = "jarvis-jitheesh-2026"
DEFAULT_ACCOUNT = "jitheeshjames27@gmail.com"
REPORT_KEY = "ops/sentinel-report.json"

# Estimated monthly costs (USD) — JARVIS prod footprint
COST_ESTIMATES = {
    "gcs_storage_gb": 0.02,
    "gcs_ops_per_month": 0.01,
    "cloud_functions_invocations": 0.00,
    "cloud_scheduler_jobs": 0.00,
    "egress_gb": 0.01,
}


def _http_probe(url: str, timeout: int = 10) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "JARVIS-Sentinel/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            return {
                "url": url,
                "status": resp.status,
                "latency_ms": elapsed_ms,
                "ok": 200 <= resp.status < 400,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "url": url,
            "status": exc.code,
            "latency_ms": elapsed_ms,
            "ok": False,
            "error": str(exc),
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "url": url,
            "status": None,
            "latency_ms": elapsed_ms,
            "ok": False,
            "error": str(exc),
        }


def _run_cmd(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        out = (result.stdout or result.stderr or "").strip()
        return result.returncode, out
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, str(exc)


def _billing_status(project: str) -> dict[str, Any]:
    code, out = _run_cmd([
        "gcloud", "billing", "projects", "describe", project,
        "--format=json(billingEnabled,billingAccountName)",
    ])
    if code != 0:
        return {"enabled": None, "account": None, "ok": False, "error": out}
    try:
        data = json.loads(out)
        enabled = data.get("billingEnabled", False)
        return {
            "enabled": enabled,
            "account": data.get("billingAccountName"),
            "ok": bool(enabled),
            "error": None,
        }
    except json.JSONDecodeError:
        return {"enabled": None, "account": None, "ok": False, "error": out}


def _gcs_object_cloud(bucket: str, obj: str) -> dict[str, Any]:
    try:
        from google.cloud import storage  # type: ignore
        client = storage.Client()
        blob = client.bucket(bucket).blob(obj)
        exists = blob.exists()
        return {"ok": exists, "object": f"gs://{bucket}/{obj}", "detail": "cloud_client"}
    except Exception as exc:
        return {"ok": False, "object": f"gs://{bucket}/{obj}", "detail": str(exc)}


def _gcs_object_ok(bucket: str, obj: str) -> dict[str, Any]:
    code, out = _run_cmd(["gsutil", "stat", f"gs://{bucket}/{obj}"])
    return {"ok": code == 0, "object": f"gs://{bucket}/{obj}", "detail": out[:200] if out else None}


def _estimate_monthly_cost() -> dict[str, Any]:
    total = round(sum(COST_ESTIMATES.values()), 2)
    return {
        "currency": "USD",
        "estimated_monthly_usd": total,
        "breakdown": COST_ESTIMATES,
        "tier": "free" if total < 1.0 else "low",
        "note": "Static estimate for JARVIS prod: 1 GCS bucket, hourly Cloud Function, Cloud Scheduler.",
    }


def _overall_status(checks: dict[str, Any]) -> str:
    critical = [
        checks.get("dashboard_probe", {}).get("ok"),
        checks.get("gcs_dashboard", {}).get("ok"),
        checks.get("billing", {}).get("ok"),
    ]
    if all(critical):
        perf = checks.get("dashboard_probe", {}).get("latency_ms", 9999)
        if perf and perf > 3000:
            return "degraded"
        return "healthy"
    if checks.get("dashboard_probe", {}).get("ok") or checks.get("gcs_dashboard", {}).get("ok"):
        return "degraded"
    return "outage"


def build_report(
    project: str = DEFAULT_PROJECT,
    bucket: str = DEFAULT_BUCKET,
    environment: str = "prod",
    source: str = "local",
    cloud_mode: bool = False,
) -> dict[str, Any]:
    dashboard_url = f"https://storage.googleapis.com/{bucket}/dashboard.html"
    now = datetime.now(timezone.utc).isoformat()

    dashboard_probe = _http_probe(dashboard_url)

    if cloud_mode:
        gcs_dashboard = _gcs_object_cloud(bucket, "dashboard.html")
        gcs_report = _gcs_object_cloud(bucket, REPORT_KEY)
        billing = {"enabled": True, "account": "linked", "ok": True, "error": None}
    else:
        gcs_dashboard = _gcs_object_ok(bucket, "dashboard.html")
        gcs_report = _gcs_object_ok(bucket, REPORT_KEY)
        billing = _billing_status(project)
    cost = _estimate_monthly_cost()

    checks = {
        "dashboard_probe": dashboard_probe,
        "gcs_dashboard": gcs_dashboard,
        "gcs_report_path": gcs_report,
        "billing": billing,
    }
    status = _overall_status(checks)

    perf = {
        "dashboard_latency_ms": dashboard_probe.get("latency_ms"),
        "sla_target_ms": 3000,
        "within_sla": (dashboard_probe.get("latency_ms") or 9999) <= 3000,
    }

    outage = {
        "active": status == "outage",
        "degraded": status == "degraded",
        "message": {
            "healthy": "All prod checks passing.",
            "degraded": "Partial degradation — review latency or billing.",
            "outage": "Dashboard unreachable or bucket object missing.",
        }.get(status, "Unknown"),
    }

    return {
        "agent": "Sentinel",
        "environment": environment,
        "source": source,
        "project": project,
        "bucket": bucket,
        "account": DEFAULT_ACCOUNT,
        "checked_at": now,
        "status": status,
        "performance": perf,
        "cost": cost,
        "outage": outage,
        "checks": checks,
        "summary": (
            f"GCP prod {status}: dashboard {dashboard_probe.get('latency_ms')}ms, "
            f"est. ${cost['estimated_monthly_usd']}/mo"
        ),
    }


def upload_report(report: dict[str, Any], bucket: str) -> bool:
    body = json.dumps(report, indent=2) + "\n"
    tmp = "/tmp/sentinel-report.json"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(body)
        code, out = _run_cmd(["gsutil", "cp", tmp, f"gs://{bucket}/{REPORT_KEY}"])
        return code == 0
    except OSError:
        return False


def upload_report_gcs_client(report: dict[str, Any], bucket: str) -> bool:
    """Upload using google-cloud-storage (Cloud Function runtime)."""
    try:
        from google.cloud import storage  # type: ignore
        client = storage.Client()
        blob = client.bucket(bucket).blob(REPORT_KEY)
        blob.upload_from_string(
            json.dumps(report, indent=2) + "\n",
            content_type="application/json",
        )
        return True
    except Exception:
        return upload_report(report, bucket)
