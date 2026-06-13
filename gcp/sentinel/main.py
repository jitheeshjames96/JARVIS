"""Cloud Function entry — Sentinel GCP prod monitor (hourly)."""

from __future__ import annotations

import json

import functions_framework

from monitor_core import (
    DEFAULT_BUCKET,
    DEFAULT_PROJECT,
    build_report,
    upload_report_gcs_client,
)


@functions_framework.http
def run_monitor(request):
    """HTTP trigger for Cloud Scheduler."""
    report = build_report(
        project=DEFAULT_PROJECT,
        bucket=DEFAULT_BUCKET,
        environment="prod",
        source="cloud_function",
        cloud_mode=True,
    )
    uploaded = upload_report_gcs_client(report, DEFAULT_BUCKET)
    report["uploaded"] = uploaded
    status_code = 200 if report["status"] in ("healthy", "degraded") else 503
    return (
        json.dumps(report),
        status_code,
        {"Content-Type": "application/json"},
    )
