#!/usr/bin/env python3
"""Pack live HUD context for GCP voice API — enriched for conversation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from user_profile import load_family_contacts, load_user_profile  # noqa: E402


def _categorize_news(headlines: list[dict]) -> dict[str, list]:
    buckets: dict[str, list] = {
        "kerala": [],
        "business": [],
        "market": [],
        "sports": [],
        "health": [],
        "world": [],
        "general": [],
    }
    for h in headlines:
        src = (h.get("source") or "").lower()
        title = (h.get("title") or "").lower()
        placed = False
        rules = [
            ("kerala", ("kerala", "kochi", "kottayam", "thiruvananthapuram")),
            ("sports", ("sport", "cricket", "football", "ipl", "odi", "match")),
            ("market", ("market", "stock", "nse", "sensex", "nifty", "investor", "share", "ipo")),
            ("business", ("business", "economy", "rbi", "corporate", "gdp", "mint", "hindu business")),
            ("health", ("health", "wellness", "life", "medical")),
            ("world", ("world", "bbc", "global", "international", "us ", "europe")),
        ]
        for key, kws in rules:
            if any(k in src or k in title for k in kws):
                buckets[key].append(h)
                placed = True
                break
        if not placed:
            buckets["general"].append(h)
    return {k: v[:8] for k, v in buckets.items() if v}


def _family_roster(keeper: dict, contacts: list[dict]) -> list[dict]:
    roster = []
    seen = set()
    for c in contacts:
        name = c.get("name", "")
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        roster.append({
            "name": name,
            "full_label": name,
            "relation": c.get("relation", ""),
            "kind": c.get("kind", "birthday" if c.get("birthday") else "contact"),
            "date": c.get("birthday", ""),
            "notes": c.get("notes", ""),
            "deceased": c.get("deceased", False),
        })
    for bucket in ("due_today", "upcoming"):
        for item in keeper.get(bucket, []):
            label = item.get("label", "")
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            roster.append({
                "name": label.split("—")[0].strip(),
                "full_label": label,
                "relation": item.get("relation", ""),
                "kind": item.get("kind", ""),
                "date": item.get("date", ""),
                "days_until": item.get("days_until"),
                "display_date": item.get("display_date", ""),
                "notes": item.get("notes", ""),
            })
    return roster


def pack() -> Path:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_live_context.py")], cwd=ROOT, check=False)
    live_path = ROOT / "cache" / "live-context.json"
    live = {}
    if live_path.exists():
        live = json.loads(live_path.read_text(encoding="utf-8"))

    for key, fname in (
        ("keeper", "keeper-report.json"),
        ("vanguard", "vanguard-report.json"),
        ("devops_gcp", "devops-gcp-report.json"),
        ("sentinel_gcp", "sentinel-gcp-report.json"),
    ):
        p = ROOT / "cache" / fname
        if p.exists() and not live.get(key):
            live[key] = json.loads(p.read_text(encoding="utf-8"))

    headlines = live.get("news_headlines", [])
    live["news_by_topic"] = _categorize_news(headlines)
    keeper = live.get("keeper") or {}
    contacts = load_family_contacts(for_cloud=True)
    live["user_profile"] = load_user_profile(for_cloud=True)
    live["family_contacts"] = contacts
    live["family_roster"] = _family_roster(keeper, contacts)

    out = ROOT / "cache" / "hud-context.json"
    out.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    p = pack()
    print(f"HUD context packed: {p}")
