"""Live data tools for JARVIS LLM brain — fetch on demand, not static cache only."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

import yfinance as yf

_CTX: dict = {}

SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTY50": "^NSEI",
}


def set_context(ctx: dict) -> None:
    global _CTX
    _CTX = ctx or {}


def _cache_price(symbol: str) -> dict | None:
    sym = symbol.upper()
    for row in _CTX.get("market_snapshots", []):
        if row.get("symbol", "").upper() == sym:
            return {"symbol": sym, "price": row.get("close"), "source": "cache"}
    vg = _CTX.get("vanguard") or {}
    for bucket in ("prefer", "consider", "avoid", "all_ranked"):
        for item in vg.get(bucket, []):
            if item.get("symbol", "").upper() == sym:
                return {"symbol": sym, "price": item.get("close"), "setup": item, "source": "vanguard_cache"}
    return None


def _yf_ticker(symbol: str) -> str:
    s = symbol.upper().strip()
    return SYMBOL_MAP.get(s, f"{s}.NS")


def tradingview_url(symbol: str) -> str:
    sym = symbol.upper()
    if sym in ("NIFTY", "NIFTY50"):
        tv = "NSE:NIFTY"
    elif sym == "BANKNIFTY":
        tv = "NSE:BANKNIFTY"
    elif sym in ("EURUSD", "GBPUSD", "USDJPY"):
        tv = f"FX:{sym[:3]}{sym[3:]}"
    else:
        tv = f"NSE:{sym}"
    return f"https://www.tradingview.com/chart/?symbol={quote(tv, safe='')}"


def lookup_stock(symbol: str) -> dict[str, Any]:
    sym = symbol.upper().strip()
    ticker = _yf_ticker(sym)
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d", timeout=10)
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass
        if not hist.empty:
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last
            close = float(last["Close"])
            prev_close = float(prev["Close"])
            chg_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0
            return {
                "symbol": sym,
                "ticker": ticker,
                "price": round(close, 2),
                "change_pct": chg_pct,
                "volume": int(last.get("Volume", 0)),
                "name": info.get("shortName") or info.get("longName") or sym,
                "sector": info.get("sector", ""),
                "tradingview": tradingview_url(sym),
                "source": "live",
            }
    except Exception:
        pass
    cached = _cache_price(sym)
    if cached:
        cached["tradingview"] = tradingview_url(sym)
        cached["note"] = "Live quote unavailable from cloud — using latest cached scan."
        return cached
    return {"symbol": sym, "error": f"No data for {sym}", "ticker": ticker}


def analyze_stock_setup(symbol: str) -> dict[str, Any]:
    sym = symbol.upper().strip()
    cached = _cache_price(sym)
    setup_from_cache = (cached or {}).get("setup")
    ticker = _yf_ticker(sym)
    try:
        hist = yf.download(ticker, period="90d", interval="1d", progress=False, timeout=12)
        if hist.empty:
            raise ValueError("empty history")
        if hasattr(hist.columns, "levels"):
            hist.columns = hist.columns.get_level_values(0)
        close = hist["Close"]
        ema20 = close.ewm(span=20).mean()
        ema50 = close.ewm(span=50).mean()
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-9)
        rsi = 100 - (100 / (1 + rs))
        last = float(close.iloc[-1])
        r = float(rsi.iloc[-1]) if len(rsi) else 50
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])
        if last > e20 > e50:
            trend = "bullish"
        elif last < e20 < e50:
            trend = "bearish"
        else:
            trend = "mixed"
        atr = float((hist["High"] - hist["Low"]).rolling(14).mean().iloc[-1] or last * 0.02)
        if trend == "bullish":
            stop, target = round(last - 1.5 * atr, 2), round(last + 2.5 * atr, 2)
            direction = "buy"
        elif trend == "bearish":
            stop, target = round(last + 1.5 * atr, 2), round(last - 2.5 * atr, 2)
            direction = "sell"
        else:
            stop, target, direction = None, None, "hold"
        return {
            "symbol": sym,
            "price": round(last, 2),
            "rsi": round(r, 1),
            "trend": trend,
            "direction": direction,
            "entry": round(last, 2),
            "stop": stop,
            "target": target,
            "tradingview": tradingview_url(sym),
            "note": f"RSI {r:.1f}, trend {trend}. Not financial advice.",
        }
    except Exception:
        if setup_from_cache:
            lv = setup_from_cache.get("levels", {})
            return {
                "symbol": sym,
                "price": setup_from_cache.get("close"),
                "tier": setup_from_cache.get("tier"),
                "score": setup_from_cache.get("score"),
                "direction": setup_from_cache.get("direction"),
                "entry": lv.get("entry"),
                "stop": lv.get("stop"),
                "target": lv.get("target"),
                "reason": setup_from_cache.get("reason"),
                "tradingview": tradingview_url(sym),
                "source": "vanguard_cache",
            }
        if cached and cached.get("price"):
            return {
                "symbol": sym,
                "price": cached.get("price"),
                "note": "Technical scan unavailable — price from cache only.",
                "tradingview": tradingview_url(sym),
                "source": "cache",
            }
        return {"symbol": sym, "error": "No history"}


def _fetch_rss(query: str, limit: int = 6) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    items = []
    try:
        req = Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item")[:limit]:
            items.append({
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "published": (item.findtext("pubDate") or "")[:22],
            })
    except Exception:
        pass
    return items


def search_news(query: str, ctx: dict | None = None) -> dict[str, Any]:
    ctx = ctx or _CTX
    q = query.strip() or "India news"
    live = _fetch_rss(q, 6)
    cached = []
    qwords = [w for w in q.lower().split() if len(w) > 3]
    for h in ctx.get("news_headlines", [])[:40]:
        title = (h.get("title") or "").lower()
        src = (h.get("source") or "").lower()
        if any(w in title or w in src for w in qwords) or not qwords:
            cached.append(h)
    buckets = ctx.get("news_by_topic") or {}
    for key, items in buckets.items():
        if key in q.lower() and items:
            cached = items + cached
    merged = live or cached[:5]
    if live and cached:
        seen = {x.get("title") for x in merged}
        for c in cached[:3]:
            if c.get("title") not in seen:
                merged.append(c)
    return {
        "query": q,
        "headlines": merged[:6],
        "source": "live_rss" if live else "cache",
        "broader": "Kerala, business, sports, world — not IT-only.",
    }


def get_family_info(query: str, ctx: dict) -> dict[str, Any]:
    q = query.lower()
    roster = list(ctx.get("family_contacts") or []) + list(ctx.get("family_roster") or [])
    keeper = ctx.get("keeper") or {}
    matches = []
    for p in roster:
        name = (p.get("name") or "").lower()
        rel = (p.get("relation") or "").lower()
        notes = (p.get("notes") or "").lower()
        if q in name or q in rel or q in notes or any(w in name for w in q.split() if len(w) > 2):
            matches.append(p)
    aliases = {
        "mother": "mother", "mom": "mother", "amma": "mother", "rosamma": "mother",
        "father": "father", "dad": "father", "wife": "wife", "anjana": "wife",
        "brother": "brother", "sister": "sister", "nephew": "nephew", "felix": "nephew",
    }
    for alias, rel in aliases.items():
        if alias in q:
            matches.extend(p for p in roster if p.get("relation") == rel)
    seen = set()
    unique = []
    for m in matches:
        key = m.get("name")
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return {
        "query": query,
        "owner": (ctx.get("user_profile") or {}).get("name") or keeper.get("owner", "Jitheesh"),
        "owner_profile": ctx.get("user_profile") or {},
        "due_today": keeper.get("due_today", []),
        "matches": unique[:5] or roster[:6],
    }


def get_gcp_status(ctx: dict) -> dict[str, Any]:
    d = ctx.get("devops_gcp") or {}
    s = ctx.get("sentinel_gcp") or {}
    return {
        "project": "jarvis-jitheesh-2026",
        "status": d.get("status", s.get("status", "unknown")),
        "issues": d.get("issues", []),
        "latency_ms": (d.get("performance") or {}).get("dashboard_latency_ms"),
        "cost_usd_month": (s.get("cost") or {}).get("estimated_monthly_usd"),
        "sentinel_summary": s.get("summary", ""),
    }


def get_agent_status(name: str, ctx: dict) -> dict[str, Any]:
    agents = ctx.get("agents") or {}
    key = name.strip().title()
    if key not in agents:
        for k in agents:
            if k.lower() == name.lower():
                key = k
                break
    info = agents.get(key, {})
    return {"agent": key, **info, "running": ctx.get("agents_running", [])}


def get_media(topic: str, ctx: dict) -> dict[str, Any]:
    items = ctx.get("media_items") or []
    t = topic.lower()
    if t:
        items = [m for m in items if t in (m.get("title") or "").lower() or t in (m.get("source") or "").lower()]
    return {"topic": topic, "videos": (items or ctx.get("media_items") or [])[:5]}


def get_market_summary(ctx: dict) -> dict[str, Any]:
    indices = {}
    for sym in ("NIFTY", "BANKNIFTY"):
        r = lookup_stock(sym)
        if "price" in r:
            indices[sym] = r
    vg = ctx.get("vanguard") or {}
    return {
        "indices": indices,
        "vanguard_prefer": vg.get("prefer", [])[:2],
        "warnings": [
            (w.get("payload") or {}).get("event", "")
            for w in ctx.get("active_warnings", [])[:2]
        ],
    }


TOOL_MAP = {
    "lookup_stock": lambda args, ctx: lookup_stock(args.get("symbol", "")),
    "analyze_stock_setup": lambda args, ctx: analyze_stock_setup(args.get("symbol", "")),
    "search_news": lambda args, ctx: search_news(args.get("query", ""), ctx),
    "get_family_info": lambda args, ctx: get_family_info(args.get("query", ""), ctx),
    "get_gcp_status": lambda args, ctx: get_gcp_status(ctx),
    "get_agent_status": lambda args, ctx: get_agent_status(args.get("agent_name", ""), ctx),
    "get_media": lambda args, ctx: get_media(args.get("topic", ""), ctx),
    "get_market_summary": lambda args, ctx: get_market_summary(ctx),
}
