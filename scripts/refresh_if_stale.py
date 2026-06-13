#!/usr/bin/env python3
"""Refresh news and market caches if older than threshold."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STALE_SECONDS = 6 * 3600  # 6 hours


def is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > STALE_SECONDS


def main():
    news = ROOT / "cache" / "briefings" / "news-digest.json"
    refreshed = []

    if is_stale(news):
        print("News digest stale — refreshing Oracle pipeline...")
        subprocess.run(["python3", str(ROOT / "scripts" / "fetch_news_digest.py")], check=False)
        refreshed.append("news")

    # Refresh core watchlist market snapshots if any CSV stale
    snap_dir = ROOT / "cache" / "market-snapshots"
    watchlist = ["EURUSD", "TATASTEEL", "RELIANCE", "NIFTY"]
    for sym in watchlist:
        csv = snap_dir / f"{sym}.csv"
        if is_stale(csv):
            if sym == "EURUSD":
                subprocess.run([
                    "python3", str(ROOT / "scripts" / "fetch_forex_ohlcv.py"),
                    "--symbol", sym, "--period", "60d", "--interval", "1d",
                ], check=False)
            else:
                subprocess.run([
                    "python3", str(ROOT / "scripts" / "fetch_nse_data.py"),
                    "--symbol", sym, "--period", "60d", "--interval", "1d",
                ], check=False)
            refreshed.append(sym)

    subprocess.run(["python3", str(ROOT / "scripts" / "build_live_context.py")], check=False)
    if refreshed:
        subprocess.run(["python3", str(ROOT / "scripts" / "generate_dashboard.py")], check=False)
        print(f"Refreshed: {', '.join(refreshed)}")
    else:
        print("All caches fresh (< 6h).")


if __name__ == "__main__":
    main()
