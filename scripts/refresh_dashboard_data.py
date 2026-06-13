#!/usr/bin/env python3
"""Refresh news + market data before dashboard render."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_STALE = 30 * 60       # 30 minutes
MARKET_STALE = 60 * 60     # 1 hour


def _is_stale(path: Path, seconds: int) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > seconds


def _watchlist_symbols() -> list[tuple[str, str]]:
    """Return [(symbol, type)] from trading.yaml or example."""
    import yaml
    for name in ("trading.yaml", "trading.yaml.example"):
        path = ROOT / "config" / name
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            wl = cfg.get("watchlists", {})
            symbols = []
            for sym in wl.get("forex", []):
                symbols.append((sym, "forex"))
            for sym in wl.get("india_equity", []):
                symbols.append((sym, "equity"))
            return symbols
        except Exception:
            pass
    return [("EURUSD", "forex"), ("NIFTY", "equity"), ("RELIANCE", "equity")]


def refresh_news() -> bool:
    news_path = ROOT / "cache" / "briefings" / "news-digest.json"
    if not _is_stale(news_path, NEWS_STALE):
        return False
    print("[refresh] Oracle news stale — fetching latest feeds...")
    subprocess.run(
        ["python3", str(ROOT / "scripts" / "fetch_news_digest.py")],
        cwd=ROOT, check=False,
    )
    return True


def refresh_markets() -> bool:
    snap_dir = ROOT / "cache" / "market-snapshots"
    refreshed = False
    for sym, kind in _watchlist_symbols():
        csv = snap_dir / f"{sym}.csv"
        if not _is_stale(csv, MARKET_STALE):
            continue
        print(f"[refresh] Market data stale for {sym} — fetching...")
        if kind == "forex":
            subprocess.run([
                "python3", str(ROOT / "scripts" / "fetch_forex_ohlcv.py"),
                "--symbol", sym, "--period", "5d", "--interval", "1h",
            ], cwd=ROOT, check=False)
        else:
            subprocess.run([
                "python3", str(ROOT / "scripts" / "fetch_nse_data.py"),
                "--symbol", sym, "--period", "5d", "--interval", "1h",
            ], cwd=ROOT, check=False)
        refreshed = True
    return refreshed


def refresh_weather() -> bool:
    weather_path = ROOT / "cache" / "weather.json"
    if not _is_stale(weather_path, 30 * 60):
        return False
    print("[refresh] Weather stale — fetching...")
    subprocess.run(["python3", str(ROOT / "scripts" / "fetch_weather.py")], cwd=ROOT, check=False)
    return True


def refresh_media() -> bool:
    media_path = ROOT / "cache" / "briefings" / "media-digest.json"
    if not _is_stale(media_path, 60 * 60):
        return False
    print("[refresh] Media digest stale — fetching...")
    subprocess.run(["python3", str(ROOT / "scripts" / "fetch_media_digest.py")], cwd=ROOT, check=False)
    return True


def refresh_devops() -> bool:
    report = ROOT / "cache" / "devops-gcp-report.json"
    if not _is_stale(report, 60 * 60):
        return False
    print("[refresh] DevOps GCP audit stale — running...")
    subprocess.run(["python3", str(ROOT / "scripts" / "devops_gcp_monitor.py")], cwd=ROOT, check=False)
    return True


def refresh_keeper() -> bool:
    report = ROOT / "cache" / "keeper-report.json"
    if not _is_stale(report, 12 * 60 * 60):
        return False
    print("[refresh] Keeper scan stale — running...")
    subprocess.run(["python3", str(ROOT / "scripts" / "keeper_reminders.py"), "--no-send"], cwd=ROOT, check=False)
    return True


def main() -> None:
    n = refresh_news()
    m = refresh_markets()
    w = refresh_weather()
    med = refresh_media()
    d = refresh_devops()
    k = refresh_keeper()
    if not n and not m and not w and not med and not d and not k:
        print("[refresh] Dashboard data is current.")
    subprocess.run(["python3", str(ROOT / "scripts" / "build_live_context.py")], cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
