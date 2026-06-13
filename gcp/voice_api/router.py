"""GCP conversational router — follow-ups, chaining, links, navigation."""

from __future__ import annotations

import re
from typing import Any

from entities import (
    extract_person,
    extract_stock,
    is_follow_up,
    is_navigation_home,
    news_topic,
    tradingview_url,
)
from session import load_session, push_history, update_session

HUD_URL = "https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html"

MARKET_WORDS = (
    "market", "markets", "nse", "stock", "stocks", "equity", "vanguard",
    "nifty", "banknifty", "trade", "setup", "scan", "forex", "trading", "chart",
)
KEEPER_WORDS = (
    "keeper", "family", "birthday", "birthdays", "personal", "mother",
    "father", "wife", "relative", "anniversary", "event", "nephew", "brother", "sister",
)
DEVOPS_WORDS = ("devops", "gcp", "cloud", "infra", "infrastructure", "sentinel", "dcp")
ORACLE_WORDS = ("oracle", "news", "headline", "headlines", "world", "macro", "kerala", "local")
MEDIA_WORDS = ("media", "video", "videos", "youtube", "watch")


def _has(cmd: str, words: tuple[str, ...]) -> bool:
    return any(w in cmd for w in words)


def _snap(ctx: dict, symbol: str) -> str | None:
    for row in ctx.get("market_snapshots", []):
        if row.get("symbol", "").upper() == symbol.upper():
            return str(row.get("close", ""))
    return None


def _stock_setup(ctx: dict, symbol: str) -> dict | None:
    vg = ctx.get("vanguard") or {}
    sym = symbol.upper()
    for bucket in ("prefer", "consider", "avoid", "watch", "all_ranked"):
        for item in vg.get(bucket, []):
            if item.get("symbol", "").upper() == sym:
                return item
    return None


def _result(
    response: str,
    *,
    agent: str = "jarvis",
    handoff: str | None = None,
    action: str | None = None,
    url: str | None = None,
    tab: str | None = None,
    links: list[dict] | None = None,
    session: dict | None = None,
) -> dict[str, Any]:
    return {
        "response": response,
        "agent": agent,
        "handoff": handoff,
        "action": action,
        "url": url,
        "tab": tab,
        "links": links or [],
        "session": session or {},
    }


def _person_detail(ctx: dict, person: dict) -> str:
    name = person.get("full_label") or person.get("name", "Unknown")
    relation = person.get("relation", "")
    kind = person.get("kind", "event")
    notes = person.get("notes", "")
    days = person.get("days_until")
    when = person.get("display_date") or person.get("date", "")

    parts = [f"{name}"]
    if relation and relation not in name.lower():
        parts.append(f"your {relation}")
    if kind == "birthday":
        parts.append("birthday")
    elif kind == "event":
        parts.append("event")
    if when:
        parts.append(f"on {when}")
    if days is not None:
        parts.append("today" if days == 0 else f"in {days} days")
    if notes:
        parts.append(f"Note: {notes}")
    return ". ".join(p for p in parts if p) + "."


def _stock_detail(ctx: dict, symbol: str, *, open_chart: bool = False) -> dict[str, Any]:
    sym = symbol.upper()
    setup = _stock_setup(ctx, sym)
    price = _snap(ctx, sym) or (str(setup.get("close")) if setup else None)
    tv = tradingview_url(sym)

    parts = [f"{sym} brief"]
    if price:
        parts.append(f"last price {price}")
    if setup:
        lv = setup.get("levels", {})
        parts.append(
            f"tier {setup.get('tier', 'neutral')} score {setup.get('score')} "
            f"direction {setup.get('direction', 'hold')}"
        )
        if lv.get("entry"):
            parts.append(
                f"entry {lv.get('entry')}, stop {lv.get('stop')}, target {lv.get('target')}, "
                f"R:R {lv.get('rr')}"
            )
        reason = setup.get("reason")
        if reason:
            parts.append(reason)
    else:
        parts.append("not in latest Vanguard scan — check Markets tab for live quote")

    handoff = None
    warnings = ctx.get("active_warnings", [])
    if warnings and setup:
        w = warnings[0].get("payload", {})
        handoff = "oracle"
        parts.append(f"Oracle note: {w.get('event', w.get('title', 'macro caution'))} before trading.")

    resp = " ".join(parts)
    if open_chart:
        resp += f" Opening TradingView chart for {sym}."

    return _result(
        resp,
        agent="vanguard",
        handoff=handoff,
        action="open_url" if open_chart else None,
        url=tv if open_chart else None,
        tab="vanguard",
        links=[{"label": f"{sym} on TradingView", "url": tv}],
        session=update_session({}, topic="stock", agent="vanguard", entity={"type": "stock", "symbol": sym}),
    )


def _news_for_topic(ctx: dict, topic: str | None) -> dict[str, Any]:
    buckets = ctx.get("news_by_topic") or {}
    headlines = ctx.get("news_headlines", [])

    if topic and buckets.get(topic):
        items = buckets[topic][:5]
        label = topic.replace("_", " ")
    else:
        items = headlines[:5]
        label = "top"

    if not items:
        return _result(
            "Oracle has no cached headlines for that topic. Refresh the dashboard.",
            agent="oracle",
            tab="oracle",
        )

    parts = [f"Oracle {label} intelligence — broader feeds, not IT-only."]
    links = []
    for h in items[:4]:
        title = h.get("title", "")
        src = h.get("source", "")
        parts.append(f"{src}: {title}")
        if h.get("link"):
            links.append({"label": title[:60], "url": h["link"]})

    warnings = ctx.get("active_warnings", [])
    handoff = "vanguard" if topic == "market" and ctx.get("vanguard", {}).get("prefer") else None
    if handoff:
        p = ctx["vanguard"]["prefer"][0]
        parts.append(f"Vanguard adds: top setup {p.get('symbol')} score {p.get('score')}.")

    return _result(
        " ".join(parts),
        agent="oracle",
        handoff=handoff,
        tab="oracle",
        links=links,
        session=update_session({}, topic=f"news_{topic or 'general'}", agent="oracle"),
    )


def _brief_market(ctx: dict) -> dict[str, Any]:
    parts = ["Market status report."]
    nifty = _snap(ctx, "NIFTY")
    bank = _snap(ctx, "BANKNIFTY")
    if nifty:
        parts.append(f"NIFTY at {nifty}.")
    if bank:
        parts.append(f"BANK NIFTY at {bank}.")

    handoff = None
    warnings = ctx.get("active_warnings", [])
    if warnings:
        w = warnings[0].get("payload", {})
        handoff = "oracle"
        parts.append(f"Oracle warning: {w.get('event', w.get('title', 'macro event'))}.")

    vg = ctx.get("vanguard") or {}
    links = []
    if vg.get("prefer"):
        p = vg["prefer"][0]
        sym = p.get("symbol", "")
        lv = p.get("levels", {})
        parts.append(
            f"Vanguard top pick {sym} score {p.get('score')}. "
            f"Entry {lv.get('entry')}, stop {lv.get('stop')}, target {lv.get('target')}."
        )
        links.append({"label": f"{sym} TradingView", "url": tradingview_url(sym)})
    elif vg.get("consider"):
        c = vg["consider"][0]
        parts.append(f"Best consider: {c.get('symbol')} score {c.get('score')}.")

    return _result(
        " ".join(parts),
        agent="vanguard",
        handoff=handoff,
        tab="markets",
        links=links,
        session=update_session({}, topic="market", agent="vanguard"),
    )


def _brief_keeper(ctx: dict) -> dict[str, Any]:
    k = ctx.get("keeper") or {}
    due = k.get("due_today", [])
    upcoming = k.get("upcoming", [])
    parts = ["Keeper personal brief."]
    for item in due[:2]:
        parts.append(_person_detail(ctx, item))
    for item in upcoming[:4]:
        parts.append(_person_detail(ctx, item))
    if not due and not upcoming:
        parts.append("No upcoming events in cache.")
    return _result(
        " ".join(parts),
        agent="keeper",
        tab="personal",
        session=update_session({}, topic="family", agent="keeper"),
    )


def _brief_devops(ctx: dict) -> dict[str, Any]:
    d = ctx.get("devops_gcp") or {}
    issues = d.get("issues", [])
    parts = [f"DevOps GCP health: {d.get('status', 'unknown')}."]
    perf = d.get("performance", {})
    if perf.get("dashboard_latency_ms"):
        parts.append(f"Dashboard latency {perf['dashboard_latency_ms']} ms.")
    if issues:
        parts.extend(issues[:3])
    else:
        parts.append("All checks passing.")
    sg = ctx.get("sentinel_gcp") or {}
    if sg.get("summary"):
        parts.append(f"Sentinel confirms: {sg['summary']}")
    return _result(
        " ".join(parts),
        agent="devops",
        handoff="sentinel",
        tab="devops",
        session=update_session({}, topic="gcp", agent="devops"),
    )


def _brief_media(ctx: dict, *, open_first: bool = False) -> dict[str, Any]:
    items = ctx.get("media_items", [])
    if not items:
        return _result("Media digest empty. Open the Life tab.", agent="explorer", tab="media")
    parts = ["Latest videos and broader content."]
    links = []
    for m in items[:4]:
        parts.append(f"{m.get('source')}: {m.get('title')}")
        if m.get("url") or m.get("link"):
            links.append({"label": m.get("title", "Video")[:50], "url": m.get("url") or m.get("link")})
    first_url = links[0]["url"] if links else None
    return _result(
        " ".join(parts),
        agent="explorer",
        tab="media",
        action="open_url" if open_first and first_url else None,
        url=first_url,
        links=links,
        session=update_session({}, topic="media", agent="explorer"),
    )


def _brief_status(ctx: dict, name: str = "Jitheesh") -> dict[str, Any]:
    parts = [f"Good to see you, {name}. System brief."]
    if ctx.get("priorities"):
        parts.append(f"Top priority: {ctx['priorities'][0]}.")
    running = ctx.get("agents_running", [])
    if running:
        parts.append(f"Active: {', '.join(running)}.")
    return _result(
        " ".join(parts) + " Ask me anything — market, family by name, GCP, Kerala news, or a stock chart.",
        agent="jarvis",
        session=update_session({}, topic="system", agent="jarvis"),
    )


def _normalize(cmd: str) -> str:
    t = cmd.lower().strip()
    for prefix in ("hey jarvis", "ok jarvis", "jarvis", "hey", "ok"):
        if t.startswith(prefix):
            t = t[len(prefix):].strip(" ,.!-")
    return t


def _handle_follow_up(cmd: str, ctx: dict, session: dict) -> dict[str, Any] | None:
    entity = session.get("last_entity") or {}
    topic = session.get("last_topic", "")

    stock = extract_stock(cmd, ctx)
    person = extract_person(cmd, ctx)

    if stock:
        open_chart = _has(cmd, ("chart", "tradingview", "trading view", "setup", "show", "open"))
        return _stock_detail(ctx, stock, open_chart=open_chart)

    if person and (person.get("name") or person.get("full_label")):
        return _result(
            _person_detail(ctx, person),
            agent="keeper",
            tab="personal",
            session=update_session(session, topic="family", agent="keeper", entity={"type": "person", "name": person.get("name")}),
        )

    if is_follow_up(cmd) or _has(cmd, ("more", "detail", "elaborate")):
        etype = entity.get("type")
        if etype == "stock" and entity.get("symbol"):
            return _stock_detail(ctx, entity["symbol"], open_chart=_has(cmd, ("chart", "setup", "show")))
        if etype == "person":
            for p in (ctx.get("keeper") or {}).get("upcoming", []):
                if entity.get("name", "").lower() in (p.get("label") or "").lower():
                    return _result(_person_detail(ctx, p), agent="keeper", tab="personal")
        if topic.startswith("news"):
            return _news_for_topic(ctx, topic.replace("news_", "") or None)
        if topic == "market":
            return _brief_market(ctx)
        if topic == "family":
            return _brief_keeper(ctx)
        if topic == "gcp":
            return _brief_devops(ctx)

    return None


AGENT_HANDLERS = {
    "keeper": _brief_keeper,
    "vanguard": _brief_market,
    "devops": _brief_devops,
    "oracle": lambda c: _news_for_topic(c, None),
    "sentinel": lambda c: _brief_devops(c),
    "explorer": _brief_media,
    "apex": _brief_market,
}


def route_command(
    command: str,
    ctx: dict,
    agent: str | None = None,
    name: str = "Jitheesh",
    session_raw: dict | None = None,
) -> dict[str, Any]:
    cmd = _normalize(command)
    session = load_session(session_raw)

    if not cmd:
        return _result("I did not catch that.", session=session)

    if re.search(r"stand\s*down", cmd):
        return _result("Standing down. Clap when you need me again.", action="end_session", session={})

    # Navigation — return to main JARVIS
    if is_navigation_home(cmd):
        return _result(
            "Returning to main JARVIS command center. I'm ready for your next command.",
            agent="jarvis",
            action="navigate_home",
            url=HUD_URL,
            session={},
        )

    # Follow-up / entity-specific (highest priority in active session)
    if session.get("last_topic") or session.get("last_entity") or is_follow_up(cmd):
        fu = _handle_follow_up(cmd, ctx, session)
        if fu:
            fu["session"] = {**session, **fu.get("session", {})}
            fu["session"]["history"] = push_history(session, command, fu["response"])
            return fu

    # Explicit stock or person in utterance
    stock = extract_stock(cmd, ctx)
    if stock and _has(cmd, MARKET_WORDS + ("chart", "price", "quote", "setup", "about", "detail", "status")):
        r = _stock_detail(ctx, stock, open_chart=_has(cmd, ("chart", "tradingview", "setup", "show", "open")))
        r["session"] = {**session, **r["session"]}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    person = extract_person(cmd, ctx)
    if person and _has(cmd, KEEPER_WORDS + ("who", "when", "about", "tell", "detail", "birthday")):
        r = _result(
            _person_detail(ctx, person),
            agent="keeper",
            tab="personal",
            session=update_session(session, topic="family", agent="keeper", entity={"type": "person", "name": person.get("name")}),
        )
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    # Agent page context
    if agent and agent.lower() in AGENT_HANDLERS:
        slug = agent.lower()
        if is_navigation_home(cmd):
            pass  # handled above
        elif slug != "keeper" and _has(cmd, KEEPER_WORDS):
            r = _brief_keeper(ctx)
            r["response"] = f"Keeper relay. {r['response']}"
            r["handoff"] = "keeper"
        elif slug != "vanguard" and _has(cmd, MARKET_WORDS):
            r = _brief_market(ctx)
            r["response"] = f"Vanguard relay. {r['response']}"
            r["handoff"] = "vanguard"
        elif slug != "oracle" and _has(cmd, ORACLE_WORDS):
            r = _news_for_topic(ctx, news_topic(cmd))
            r["response"] = f"Oracle relay. {r['response']}"
            r["handoff"] = "oracle"
        else:
            r = AGENT_HANDLERS[slug](ctx)
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    # Named agent handoff
    for slug in AGENT_HANDLERS:
        if slug in cmd and slug not in ("apex",):
            r = AGENT_HANDLERS[slug](ctx)
            r["response"] = f"{slug.title()} here. {r['response']}"
            r["session"] = {**session, **r.get("session", {})}
            r["session"]["history"] = push_history(session, command, r["response"])
            return r

    # GCP / DevOps before news (avoids "gcp health" → health news)
    if _has(cmd, DEVOPS_WORDS):
        r = _brief_devops(ctx)
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    # News by topic (Kerala, business, sports, etc.)
    topic = news_topic(cmd)
    if topic or (_has(cmd, ORACLE_WORDS) and not _has(cmd, DEVOPS_WORDS)):
        r = _news_for_topic(ctx, topic)
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    # Video / media with optional open
    if _has(cmd, MEDIA_WORDS):
        r = _brief_media(ctx, open_first=_has(cmd, ("play", "open", "show", "watch")))
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    # TradingView / chart explicit
    if _has(cmd, ("tradingview", "trading view", "chart")) and stock:
        r = _stock_detail(ctx, stock, open_chart=True)
        r["session"] = {**session, **r["session"]}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    # Domain routes
    if _has(cmd, MARKET_WORDS):
        r = _brief_market(ctx)
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    if _has(cmd, KEEPER_WORDS):
        r = _brief_keeper(ctx)
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    if _has(cmd, ("what next", "recommend", "should i do", "focus")):
        parts = [f"Next for you, {name}."]
        if ctx.get("priorities"):
            parts.append(ctx["priorities"][0])
        r = _result(" ".join(parts), agent="synergy", session=update_session(session, topic="priorities", agent="synergy"))
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    if _has(cmd, ("status", "brief", "report", "happening", "update", "health")):
        # Disambiguate: "gcp health" already caught; "market status" caught above
        if _has(cmd, DEVOPS_WORDS):
            r = _brief_devops(ctx)
        elif _has(cmd, MARKET_WORDS):
            r = _brief_market(ctx)
        else:
            r = _brief_status(ctx, name)
        r["session"] = {**session, **r.get("session", {})}
        r["session"]["history"] = push_history(session, command, r["response"])
        return r

    r = _result(
        "I can help with stocks by name, family by name, Kerala and world news, GCP health, videos, "
        "and TradingView charts. Try a follow-up after any answer, or say return home.",
        agent="jarvis",
        session=session,
    )
    r["session"]["history"] = push_history(session, command, r["response"])
    return r
