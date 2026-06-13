#!/usr/bin/env python3
"""Load voice daemon tuning from config/profile.yaml."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_daemon_config() -> dict:
    defaults = {
        "wake_engine": "auto",
        "wake_keyword": "jarvis",
        "openwakeword_model": "hey_jarvis",
        "openwakeword_threshold": 0.60,
        "speaker_threshold": 0.68,
        "picovoice_access_key": "",
        "porcupine_keyword_path": "",
    }
    path = ROOT / "config" / "profile.yaml"
    if not path.exists():
        return defaults
    try:
        import yaml
        with path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        daemon = cfg.get("voice_daemon", {}) or {}
        merged = {**defaults, **daemon}
        return merged
    except Exception:
        return defaults


def speaker_threshold() -> float:
    return float(load_daemon_config().get("speaker_threshold", 0.68))


def wake_threshold() -> float:
    return float(load_daemon_config().get("openwakeword_threshold", 0.60))
