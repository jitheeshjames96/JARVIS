"""Conversation session — follow-ups and agent chaining."""

from __future__ import annotations

from typing import Any


def load_session(raw: dict | None) -> dict:
    if not raw:
        return {}
    return {
        "last_topic": raw.get("last_topic"),
        "last_agent": raw.get("last_agent"),
        "last_entity": raw.get("last_entity") or {},
        "history": (raw.get("history") or [])[-6:],
    }


def push_history(session: dict, user: str, jarvis: str) -> list[dict]:
    hist = list(session.get("history", []))
    hist.append({"role": "user", "text": user})
    hist.append({"role": "jarvis", "text": jarvis})
    return hist[-8:]


def update_session(
    session: dict,
    *,
    topic: str | None = None,
    agent: str | None = None,
    entity: dict | None = None,
) -> dict:
    out = dict(session)
    if topic:
        out["last_topic"] = topic
    if agent:
        out["last_agent"] = agent
    if entity:
        out["last_entity"] = entity
    return out
