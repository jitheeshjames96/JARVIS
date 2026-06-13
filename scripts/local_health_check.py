#!/usr/bin/env python3
"""Read-only laptop health snapshot for JARVIS — no org settings touched."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
        return (r.stdout or r.stderr or "").strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return str(exc)


def disk_report() -> dict:
    usage = shutil.disk_usage("/")
    pct = round(usage.used / usage.total * 100, 1)
    return {
        "total_gb": round(usage.total / 1e9, 1),
        "used_gb": round(usage.used / 1e9, 1),
        "free_gb": round(usage.free / 1e9, 1),
        "used_pct": pct,
        "status": "warn" if pct > 80 else "ok",
    }


def jarvis_services() -> list[dict]:
    out = _run(["launchctl", "list"])
    services = []
    for line in out.splitlines():
        if "com.jarvis" not in line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            pid, code, label = parts[0], parts[1], parts[2]
            services.append({
                "label": label,
                "pid": pid if pid != "-" else None,
                "last_exit": int(code) if code.lstrip("-").isdigit() else code,
                "healthy": pid != "-" and code == "0",
            })
    return services


def voice_daemon_issue() -> str | None:
    log = ROOT / "logs" / "jarvis_daemon_stderr.log"
    if not log.exists():
        return None
    try:
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]
    except OSError:
        return None
    if any("Operation not permitted" in line for line in tail):
        return "Voice daemon blocked — repo on Desktop needs Full Disk Access or move to ~/Projects/JARVIS"
    return None


def repo_footprint() -> dict:
    def sz(p: Path) -> float:
        if not p.exists():
            return 0.0
        if p.is_file():
            return p.stat().st_size / 1e6
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6

    return {
        "repo_mb": round(sz(ROOT), 1),
        "cache_mb": round(sz(ROOT / "cache"), 2),
        "logs_mb": round(sz(ROOT / "logs"), 2),
    }


def recommendations(disk: dict, services: list[dict], voice_issue: str | None) -> list[str]:
    recs = []
    if disk["status"] == "warn":
        recs.append(
            f"Disk {disk['used_pct']}% full — clear Downloads, old Xcode simulators, or large caches. "
            "No org settings involved."
        )
    crashing = [s for s in services if s["last_exit"] not in (0, "-", 0) and s["pid"] is None]
    heavy = {"com.jarvis.dashboard", "com.jarvis.devops", "com.jarvis.voice"}
    if any(s["label"] in heavy for s in crashing):
        recs.append(
            "Disable local dashboard/devops/voice launchd — GCP Sentinel + on-demand refresh is enough. "
            "Run: bash scripts/install_autostart.sh --light"
        )
    if voice_issue:
        recs.append(voice_issue)
    if not recs:
        recs.append("Local system looks fine. Keep only Keeper (2×/day) for personal reminders.")
    return recs


def main() -> None:
    disk = disk_report()
    services = jarvis_services()
    voice_issue = voice_daemon_issue()
    report = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "platform": _run(["sw_vers", "-productVersion"]),
        "disk": disk,
        "jarvis_services": services,
        "repo": repo_footprint(),
        "recommendations": recommendations(disk, services, voice_issue),
        "local_policy": "Read-only audit — no org/MDM settings modified.",
    }
    out = ROOT / "cache" / "local-health.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
