#!/usr/bin/env python3
"""Load merged user profile from config/profile.yaml, region.yaml, personal.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load_user_profile(*, for_cloud: bool = False) -> dict[str, Any]:
    """Merge profile + region + personal owner. Strips secrets when for_cloud=True."""
    profile = _read_yaml(ROOT / "config" / "profile.yaml")
    region = _read_yaml(ROOT / "config" / "region.yaml")
    personal = _read_yaml(ROOT / "config" / "personal.yaml")
    owner = personal.get("owner") or {}

    voice = profile.get("voice") or {}
    daemon = profile.get("voice_daemon") or {}

    out: dict[str, Any] = {
        "name": profile.get("name") or owner.get("name") or "Jitheesh",
        "timezone": profile.get("timezone") or region.get("timezone") or "Asia/Kolkata",
        "locale": profile.get("locale") or region.get("locale") or "en-IN",
        "city": region.get("city") or (owner.get("location", "").split(",")[0].strip() if owner.get("location") else "Kottayam"),
        "state": region.get("state", "Kerala"),
        "region": region.get("region", "India"),
        "location_label": owner.get("location") or f"{region.get('city', 'Kottayam')}, {region.get('state', 'Kerala')}",
        "occupation": owner.get("occupation", ""),
        "employer": owner.get("employer", ""),
        "birthday": owner.get("birthday", ""),
        "markets_focus": region.get("markets_focus", []),
        "forex_focus": region.get("forex_focus", []),
        "news_bias": region.get("news_bias", []),
        "voice": {
            "enabled": voice.get("enabled", True),
            "tts_provider": voice.get("tts_provider", "piper"),
            "voice_name": voice.get("voice_name", "Daniel"),
            "rate": voice.get("rate", 152),
        },
        "voice_daemon": {
            "trigger": daemon.get("trigger", "clap"),
            "clap_mode": daemon.get("clap_mode", "single"),
            "clap_threshold": daemon.get("clap_threshold", 0.12),
            "clap_spike_ratio": daemon.get("clap_spike_ratio", 2.8),
            "speaker_threshold": daemon.get("speaker_threshold", 0.68),
            "wake_keyword": daemon.get("wake_keyword", "jarvis"),
        },
    }

    if not for_cloud:
        out["email"] = owner.get("email") or profile.get("email", "")
        out["phone"] = owner.get("phone", "")
    else:
        # Cloud voice context — no phone/email; family names only via roster
        out.pop("email", None)
        out.pop("phone", None)

    return out


def load_family_contacts(*, for_cloud: bool = True) -> list[dict]:
    """Family contacts from personal.yaml for Keeper / voice."""
    personal = _read_yaml(ROOT / "config" / "personal.yaml")
    contacts = []
    for c in personal.get("contacts", []):
        entry = {
            "name": c.get("name", ""),
            "relation": c.get("relation", ""),
            "birthday": c.get("birthday", ""),
            "notes": c.get("notes", ""),
            "deceased": c.get("deceased", False),
        }
        if not for_cloud:
            entry["phone"] = c.get("phone", "")
        contacts.append(entry)
    for ev in personal.get("events", []):
        contacts.append({
            "name": ev.get("title", ""),
            "relation": ev.get("category", "event"),
            "birthday": ev.get("date", ""),
            "notes": ev.get("notes", ""),
            "kind": "event",
        })
    return contacts
