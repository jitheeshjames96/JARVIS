"""Entity extraction — stocks, people, news topics from voice commands."""

from __future__ import annotations

import re

# Common NSE tickers + indices (expanded from scan universe)
KNOWN_SYMBOLS = {
    "nifty", "banknifty", "reliance", "tatasteel", "maruti", "infy", "itc",
    "hdfcbank", "icicibank", "sbin", "bhartiartl", "tcs", "wipro", "axisbank",
    "kotakbank", "lt", "hcltech", "asianpaint", "bajfinance", "tatamotors",
    "eurusd", "gbpusd", "usdjpy",
}

RELATION_ALIASES = {
    "mother": ("mother", "mom", "amma", "rosamma"),
    "father": ("father", "dad", "appa", "dd james"),
    "wife": ("wife", "anjana", "spouse"),
    "brother": ("brother", "jamal", "sajeesh"),
    "sister": ("sister", "chechi", "akka"),
    "self": ("me", "myself", "jitheesh", "my birthday"),
    "nephew": ("nephew", "felix", "gordia", "gordon"),
}


def _symbols_from_ctx(ctx: dict) -> set[str]:
    syms: set[str] = set(KNOWN_SYMBOLS)
    for row in ctx.get("market_snapshots", []):
        if row.get("symbol"):
            syms.add(row["symbol"].lower())
    vg = ctx.get("vanguard") or {}
    for bucket in ("prefer", "consider", "avoid", "watch", "all_ranked"):
        for item in vg.get(bucket, []):
            if item.get("symbol"):
                syms.add(item["symbol"].lower())
    return syms


def extract_stock(cmd: str, ctx: dict) -> str | None:
    tokens = re.findall(r"[a-z0-9]+", cmd.lower())
    syms = _symbols_from_ctx(ctx)
    for tok in tokens:
        if tok in syms:
            return tok.upper()
    # Phrase patterns: "about reliance", "detail on maruti"
    for sym in sorted(syms, key=len, reverse=True):
        if sym in cmd:
            return sym.upper()
    return None


def _keeper_people(ctx: dict) -> list[dict]:
    people: list[dict] = []
    k = ctx.get("keeper") or {}
    for bucket in ("due_today", "upcoming"):
        for item in k.get(bucket, []):
            people.append({
                "name": item.get("label", "").split("—")[0].strip(),
                "full_label": item.get("label", ""),
                "relation": item.get("relation", ""),
                "kind": item.get("kind", ""),
                "date": item.get("date", ""),
                "days_until": item.get("days_until"),
                "display_date": item.get("display_date", ""),
                "notes": item.get("notes", ""),
            })
    for c in ctx.get("family_roster", []):
        people.append(c)
    return people


def extract_person(cmd: str, ctx: dict) -> dict | None:
    low = cmd.lower()
    people = _keeper_people(ctx)

    # Direct name match
    for p in people:
        name = (p.get("name") or "").lower()
        if name and len(name) > 2 and name in low:
            return p
        for part in name.split():
            if len(part) > 3 and part in low:
                return p

    # Relation aliases
    for relation, aliases in RELATION_ALIASES.items():
        if any(a in low for a in aliases):
            for p in people:
                if p.get("relation") == relation:
                    return p
            return {"name": relation.title(), "relation": relation, "kind": "lookup"}

    return None


def news_topic(cmd: str) -> str | None:
    low = cmd.lower()
    if any(w in low for w in ("gcp", "cloud", "devops", "infra", "sentinel")):
        return None
    if any(w in low for w in ("kerala", "kochi", "kottayam", "local news", "local level")):
        return "kerala"
    if any(w in low for w in ("business", "corporate", "economy", "rbi", "gdp")):
        return "business"
    if any(w in low for w in ("market news", "stock news", "nse", "sensex", "trading")):
        return "market"
    if any(w in low for w in ("sport", "cricket", "football", "ipl")):
        return "sports"
    if any(w in low for w in ("health", "wellness", "life")):
        return "health"
    if any(w in low for w in ("world", "global", "international")):
        return "world"
    if any(w in low for w in ("funny", "viral", "entertainment", "celebrity")):
        return "general"
    return None


def is_follow_up(cmd: str) -> bool:
    low = cmd.lower()
    return any(
        p in low
        for p in (
            "tell me more", "more detail", "more about", "what about", "how about",
            "elaborate", "expand", "follow up", "and what", "go on", "details on",
            "detail on", "who is", "when is", "whose", "that stock", "that person",
            "same stock", "same person", "him", "her", "them", "it",
        )
    )


def is_navigation_home(cmd: str) -> bool:
    low = cmd.lower()
    return any(
        p in low
        for p in (
            "go back to jarvis", "back to jarvis", "return to jarvis", "return home",
            "go home", "main hud", "main dashboard", "back to home", "home page",
            "central command", "command center",
        )
    )


def tradingview_url(symbol: str) -> str:
    sym = symbol.upper()
    if sym in ("NIFTY", "BANKNIFTY"):
        tv = "NSE:NIFTY" if sym == "NIFTY" else "NSE:BANKNIFTY"
    elif sym in ("EURUSD", "GBPUSD", "USDJPY"):
        tv = f"FX:{sym[:3]}{sym[3:]}"
    else:
        tv = f"NSE:{sym}"
    from urllib.parse import quote
    return f"https://www.tradingview.com/chart/?symbol={quote(tv, safe='')}"
