"""JARVIS LLM brain — Google Gen AI SDK + automatic tool calling."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from router import route_command

_CTX: dict = {}


def _tool_lookup_stock(symbol: str) -> dict:
    """Get live price and change for any NSE stock or index (e.g. TCS, RELIANCE, NIFTY)."""
    from tools import lookup_stock
    return lookup_stock(symbol)


def _tool_analyze_stock_setup(symbol: str) -> dict:
    """Technical analysis with trend, RSI, entry, stop, target for any NSE stock."""
    from tools import analyze_stock_setup
    return analyze_stock_setup(symbol)


def _tool_search_news(query: str) -> dict:
    """Search live news — Kerala, business, market, sports, world. Broad, not IT-only."""
    from tools import search_news
    return search_news(query, _CTX)


def _tool_get_family_info(query: str) -> dict:
    """Family birthdays and events by person name or relation (mother, wife, Felix, etc.)."""
    from tools import get_family_info
    return get_family_info(query, _CTX)


def _tool_get_gcp_status() -> dict:
    """GCP DevOps and Sentinel health, latency, cost for jarvis-jitheesh-2026."""
    from tools import get_gcp_status
    return get_gcp_status(_CTX)


def _tool_get_agent_status(agent_name: str) -> dict:
    """Status of a JARVIS agent: Vanguard, Keeper, Oracle, DevOps, Sentinel, etc."""
    from tools import get_agent_status
    return get_agent_status(agent_name, _CTX)


def _tool_get_media(topic: str = "") -> dict:
    """Video and media recommendations; optional topic filter."""
    from tools import get_media
    return get_media(topic, _CTX)


def _tool_get_market_summary() -> dict:
    """NIFTY, Bank Nifty, Vanguard picks, and active market warnings."""
    from tools import get_market_summary
    return get_market_summary(_CTX)


TOOLS = [
    _tool_lookup_stock,
    _tool_analyze_stock_setup,
    _tool_search_news,
    _tool_get_family_info,
    _tool_get_gcp_status,
    _tool_get_agent_status,
    _tool_get_media,
    _tool_get_market_summary,
]

SYSTEM_BASE = """Talk naturally like a sharp human assistant. Use tools for every factual question.

- Look up ANY NSE stock live — not limited to a cached list.
- Use conversation history for follow-ups ("tell me more", "what about that", "open the chart").
- Use full names from family data — never vague labels like "nephew" without a name.
- Chain agents: Oracle warnings + Vanguard setups + Sentinel GCP health when relevant.
- For charts, mention TradingView URL from tool data.
- "return home" / "back to JARVIS" → say you're returning to command center.
- "stand down" → brief goodbye.
- Not financial advice.

Keep answers conversational, 2-5 sentences unless user wants detail.
At the very end on its own line output:
ACTION_JSON={{"action":null,"url":null,"tab":null,"agent":"jarvis","handoff":null}}
Set action to navigate_home, open_url, or open_tab when appropriate.
"""


def _system_prompt(ctx: dict) -> str:
    p = ctx.get("user_profile") or {}
    name = p.get("name", "Jitheesh")
    loc = p.get("location_label") or f"{p.get('city', 'Kottayam')}, {p.get('state', 'Kerala')}, {p.get('region', 'India')}"
    job = p.get("occupation", "")
    employer = p.get("employer", "")
    markets = ", ".join(p.get("markets_focus") or ["NIFTY", "BANKNIFTY"])
    news = ", ".join(p.get("news_bias") or ["Kerala", "India business", "NSE"])
    trigger = (p.get("voice_daemon") or {}).get("trigger", "clap")

    family_names = [c.get("name") for c in (ctx.get("family_contacts") or [])[:8] if c.get("name")]
    family_hint = ", ".join(family_names) if family_names else "see family tools"

    header = (
        f"You are JARVIS — {name}'s personal AI chief-of-staff based in {loc}."
    )
    if job:
        header += f" {name} is a {job}" + (f" at {employer}." if employer else ".")
    header += f" Voice wake: {trigger}. Market focus: {markets}. News bias: {news}."
    header += f" Family contacts include: {family_hint}."
    return header + "\n\n" + SYSTEM_BASE


def _llm_enabled() -> bool:
    return os.environ.get("LLM_ENABLED", "true").lower() in ("1", "true", "yes")


def _make_client():
    from google import genai

    project = os.environ.get("GCP_PROJECT", "jarvis-jitheesh-2026")
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        return genai.Client(api_key=api_key), "apikey"

    for location in ("us-central1", "asia-south1", "europe-west1"):
        try:
            return genai.Client(vertexai=True, project=project, location=location), f"vertex@{location}"
        except Exception:
            continue
    return genai.Client(vertexai=True, project=project, location="us-central1"), "vertex@us-central1"


def _models() -> list[str]:
    raw = os.environ.get("GEMINI_MODEL", "")
    defaults = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-001"]
    if raw:
        return [raw] + [m for m in defaults if m != raw]
    return defaults


def _prefetch(command: str, ctx: dict, session: dict) -> str:
    """Inject live/cache tool results into prompt — backup if auto-tools fail."""
    from entities import extract_person, extract_stock, news_topic
    from tools import (
        analyze_stock_setup,
        get_agent_status,
        get_family_info,
        get_gcp_status,
        get_market_summary,
        get_media,
        lookup_stock,
        search_news,
    )

    parts = []
    sym = extract_stock(command, ctx) or (session.get("last_entity") or {}).get("symbol")
    if sym:
        parts.append(f"STOCK[{sym}]: {json.dumps(lookup_stock(sym))}")
        if any(w in command.lower() for w in ("setup", "chart", "trade", "analysis", "technical")):
            parts.append(f"SETUP[{sym}]: {json.dumps(analyze_stock_setup(sym))}")

    person = extract_person(command, ctx)
    if person or any(w in command.lower() for w in ("family", "birthday", "mother", "wife", "father")):
        q = person.get("name", "") if person else command
        parts.append(f"FAMILY: {json.dumps(get_family_info(q or command, ctx))}")

    topic = news_topic(command)
    if topic or any(w in command.lower() for w in ("news", "headline", "kerala", "market news")):
        parts.append(f"NEWS: {json.dumps(search_news(topic or command, ctx))}")

    if any(w in command.lower() for w in ("gcp", "cloud", "devops", "dcp", "infra")):
        parts.append(f"GCP: {json.dumps(get_gcp_status(ctx))}")

    for agent in ("vanguard", "keeper", "oracle", "devops", "sentinel", "tracker"):
        if agent in command.lower():
            parts.append(f"AGENT[{agent}]: {json.dumps(get_agent_status(agent, ctx))}")

    if any(w in command.lower() for w in ("video", "youtube", "media")):
        parts.append(f"MEDIA: {json.dumps(get_media(command, ctx))}")

    if any(w in command.lower() for w in ("market", "nifty", "nse")) and not sym:
        parts.append(f"MARKET: {json.dumps(get_market_summary(ctx))}")

    return "\n".join(parts)


def _build_contents(command: str, session: dict, agent: str | None, enrichment: str = "") -> list:
    from google.genai import types

    contents = []
    for turn in session.get("history", [])[-6:]:
        role = "user" if turn.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn.get("text", ""))]))

    user = command
    if agent:
        user = f"[Agent page: {agent}] {command}"
    if session.get("last_entity"):
        user += f"\n[Prior context: {json.dumps(session.get('last_entity'))}]"
    if enrichment:
        user += f"\n[Pre-fetched data for this question — use this, do not say tools failed:\n{enrichment}]"
    contents.append(types.Content(role="user", parts=[types.Part(text=user)]))
    return contents


def _parse_action_json(text: str) -> tuple[str, dict]:
    action_meta = {}
    clean = text
    m = re.search(r"ACTION_JSON=(\{.*?\})\s*$", text, re.DOTALL)
    if m:
        try:
            action_meta = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
        clean = text[: m.start()].strip()
    return clean, action_meta


def think(
    command: str,
    ctx: dict,
    agent: str | None = None,
    session_raw: dict | None = None,
) -> dict[str, Any]:
    global _CTX
    _CTX = ctx
    from tools import set_context
    set_context(ctx)

    session = session_raw or {}

    # Pre-fetch data so LLM always has facts (GCP may block yfinance IPs)
    enrichment = _prefetch(command, ctx, session)

    if not _llm_enabled():
        return route_command(command, ctx, agent=agent, session_raw=session)

    try:
        from google.genai import types

        client, backend = _make_client()
        contents = _build_contents(command, session, agent, enrichment)
        config = types.GenerateContentConfig(system_instruction=_system_prompt(ctx), tools=TOOLS)

        text = ""
        model_used = None
        last_err = None
        for model_name in _models():
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                text = response.text or ""
                model_used = f"{model_name} ({backend})"
                break
            except Exception as e:
                last_err = e
                continue

        if not text and last_err:
            raise last_err

        spoken, meta = _parse_action_json(text)
        if re.search(r"stand\s*down", command.lower()):
            meta["action"] = "end_session"
        if re.search(r"return home|return to jarvis|back to jarvis|go home|main hud", command.lower()):
            meta["action"] = "navigate_home"
            meta["url"] = "https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html"

        links = []
        url = meta.get("url")
        if url:
            links.append({"label": "Open", "url": url})

        pname = (ctx.get("user_profile") or {}).get("name", "Jitheesh")
        out = {
            "response": spoken or f"I'm here, {pname}. What do you need?",
            "agent": meta.get("agent") or agent or "jarvis",
            "handoff": meta.get("handoff"),
            "action": meta.get("action"),
            "url": url,
            "tab": meta.get("tab"),
            "links": links,
            "session": {
                **session,
                "last_agent": meta.get("agent") or agent or "jarvis",
                "history": (session.get("history") or []) + [
                    {"role": "user", "text": command},
                    {"role": "jarvis", "text": spoken},
                ],
            },
            "llm": True,
            "llm_model": model_used,
        }
        out["session"]["history"] = out["session"]["history"][-8:]
        return out

    except Exception as e:
        result = route_command(command, ctx, agent=agent, session_raw=session)
        result["llm"] = False
        result["llm_error"] = str(e)[:200]
        return result
