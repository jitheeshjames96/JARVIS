"""Cloud Function — JARVIS conversational voice API."""

from __future__ import annotations

import json

import functions_framework
from google.cloud import storage

from router import route_command

BUCKET = "jarvis-jitheesh-2026"
CONTEXT_KEY = "ops/hud-context.json"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "3600",
}


def _load_context() -> dict:
    client = storage.Client()
    blob = client.bucket(BUCKET).blob(CONTEXT_KEY)
    if not blob.exists():
        return {}
    try:
        return json.loads(blob.download_as_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@functions_framework.http
def voice_api(request):
    if request.method == "OPTIONS":
        return ("", 204, CORS_HEADERS)

    headers = {**CORS_HEADERS, "Content-Type": "application/json"}

    if request.method == "GET":
        return (json.dumps({"ok": True, "service": "jarvis-voice-api", "version": 2}), 200, headers)

    if request.method != "POST":
        return (json.dumps({"error": "method not allowed"}), 405, headers)

    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}

    command = (body.get("command") or "").strip()
    agent = (body.get("agent") or "").strip().lower() or None
    session = body.get("session")

    if not command:
        return (json.dumps({"error": "empty command"}), 400, headers)

    ctx = _load_context()
    result = route_command(command, ctx, agent=agent, session_raw=session)

    payload = {
        "command": command,
        "agent": agent,
        "response": result.get("response", ""),
        "active_agent": result.get("agent"),
        "handoff": result.get("handoff"),
        "action": result.get("action"),
        "url": result.get("url"),
        "tab": result.get("tab"),
        "links": result.get("links", []),
        "session": result.get("session", {}),
    }
    return (json.dumps(payload), 200, headers)
