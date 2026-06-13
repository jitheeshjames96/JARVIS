#!/usr/bin/env python3
"""Iron Man JARVIS HUD dashboard renderer — cinematic command interface."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
ROOT = Path(__file__).resolve().parent.parent

from hud_panels import OVERLAY_CSS, OVERLAY_JS, build_tab_panels  # noqa: E402


def _voice_js() -> str:
    p = ROOT / "scripts" / "dashboard_voice.js"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _esc(t) -> str:
    return html.escape(str(t or ""))


def _news_items(raw) -> list[dict]:
    if isinstance(raw, dict):
        return raw.get("items", [])
    return raw if isinstance(raw, list) else []


def _ring(pct: float, label: str, value: str, r: int = 36) -> str:
    pct = max(0, min(100, pct))
    c = 2 * 3.14159 * r
    dash = c * pct / 100
    return f"""
    <div class="ring-widget">
      <svg viewBox="0 0 90 90" class="ring-svg">
        <circle cx="45" cy="45" r="{r}" class="ring-bg"/>
        <circle cx="45" cy="45" r="{r}" class="ring-fg"
          stroke-dasharray="{dash:.1f} {c:.1f}" transform="rotate(-90 45 45)"/>
        <text x="45" y="42" class="ring-val">{_esc(value)}</text>
        <text x="45" y="54" class="ring-sub">{int(pct)}%</text>
      </svg>
      <div class="ring-label">{_esc(label)}</div>
    </div>"""


def _weather_icon(code: int) -> str:
    if code in (0, 1):
        return "☀"
    if code in (2, 3):
        return "◐"
    if code in (45, 48):
        return "≡"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "☂"
    if code in (71, 73, 75):
        return "❄"
    if code >= 95:
        return "⚡"
    return "◎"


def _voice_api_url() -> str:
    try:
        import yaml
        for name in ("gcp.yaml", "gcp.yaml.example"):
            path = ROOT / "config" / name
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                url = cfg.get("voice_api_url", "")
                if url:
                    return url
    except Exception:
        pass
    return ""


def _gcp_hud_url() -> str:
    try:
        import yaml
        path = ROOT / "config" / "gcp.yaml"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            bucket = cfg.get("bucket", "jarvis-jitheesh-2026")
            return f"https://storage.googleapis.com/{bucket}/dashboard.html"
    except Exception:
        pass
    return "https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html"


def _region_label() -> str:
    try:
        import yaml
        path = ROOT / "config" / "region.yaml"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                r = yaml.safe_load(f) or {}
            return f"{r.get('city', 'Kochi')}, {r.get('state', 'Kerala')} · {r.get('region', 'India')}"
    except Exception:
        pass
    return "Kochi, Kerala · India"


def render_dashboard(
    live: dict,
    status: dict,
    news_raw,
    actions: list,
    inbox_msgs: list,
    processed_msgs: list,
    broadcast_msgs: list,
    sentinel_gcp: dict,
    weather: dict | None = None,
    devops_gcp: dict | None = None,
    media_items: list | None = None,
    keeper: dict | None = None,
    vanguard: dict | None = None,
) -> str:
    now = datetime.now(IST)
    day_num = now.strftime("%d")
    month = now.strftime("%B").upper()
    year = now.strftime("%Y")
    clock_init = now.strftime("%H:%M:%S")
    generated = live.get("generated_at", "")

    agents = status.get("agents", {})
    priorities = live.get("priorities", [])
    warnings = live.get("active_warnings", [])
    markets = live.get("market_snapshots", [])
    headlines = live.get("news_headlines") or _news_items(news_raw)[:25]
    media = media_items if media_items is not None else live.get("media_items", [])
    devops = devops_gcp if devops_gcp is not None else live.get("devops_gcp") or {}
    keeper_data = keeper if keeper is not None else live.get("keeper") or {}
    vanguard_data = vanguard if vanguard is not None else live.get("vanguard") or {}
    region_label = _region_label()
    news_meta = ""
    if isinstance(news_raw, dict) and news_raw.get("fetched_at"):
        try:
            ft = datetime.fromisoformat(news_raw["fetched_at"].replace("Z", "+00:00")).astimezone(IST)
            news_meta = ft.strftime("%d %b %H:%M IST")
        except ValueError:
            pass

    weather = weather or {}
    wcur = weather.get("current", {})
    wloc = weather.get("location", "Kochi, India")
    wtemp = wcur.get("temp_c", "—")
    whum = wcur.get("humidity", "—")
    wwind = wcur.get("wind_kmh", "—")
    wdesc = wcur.get("description", "")
    wcode = wcur.get("code", 0)

    # Ring gauge values
    agent_total = max(len(agents), 1)
    agent_active = sum(1 for a in agents.values() if a.get("state") in ("running", "alert"))
    agent_pct = round(agent_active / agent_total * 100)

    sg = sentinel_gcp or {}
    sg_status = sg.get("status", "unknown")
    latency = sg.get("performance", {}).get("dashboard_latency_ms", 0) or 0
    gcp_pct = 95 if sg_status == "healthy" else (60 if sg_status == "degraded" else 20)

    news_count = len(headlines)
    news_pct = min(100, news_count * 4)

    market_pct = min(100, len(markets) * 12)

    # Center hub agent orbit labels
    orbit_agents = list(agents.keys())[:9] or [
        "Sentinel", "Oracle", "Apex", "Vanguard", "Tracker", "Strategist", "Synergy", "Keeper", "Explorer"
    ]

    # News column
    news_html = ""
    for item in headlines[:18]:
        title = item.get("title", "")
        link = item.get("link", "#")
        src = item.get("source", "Oracle")
        pub = item.get("published_display") or item.get("published", "")
        age = item.get("age_display", "")
        news_html += f"""
        <a class="news-line" href="{_esc(link)}" target="_blank" rel="noopener">
          <span class="nl-src">{_esc(src)}</span>
          <span class="nl-title">{_esc(title)}</span>
          <span class="nl-time">{_esc(pub)} · <em>{_esc(age)}</em></span>
        </a>"""

    # Weather forecast rows
    forecast_html = ""
    for day in weather.get("forecast", [])[:7]:
        forecast_html += f"""
        <div class="fc-row">
          <span>{_esc(day.get('day_label',''))}</span>
          <span class="fc-icon">{_weather_icon(day.get('code',0))}</span>
          <span>{day.get('max_c','—')}°</span>
          <span class="fc-min">{day.get('min_c','—')}°</span>
        </div>"""

    # Market strip
    market_html = ""
    for m in markets[:6]:
        market_html += f"""
        <div class="mkt-row">
          <span class="mkt-sym">{_esc(m.get('symbol'))}</span>
          <span class="mkt-px">{_esc(m.get('close'))}</span>
          <span class="mkt-ts">{_esc(str(m.get('updated',''))[5:16].replace('T',' '))}</span>
        </div>"""

    # Agent mini tiles around hub
    agent_orbit = ""
    for i, name in enumerate(orbit_agents):
        info = agents.get(name, {})
        state = info.get("state", "idle")
        angle = i * (360 / len(orbit_agents))
        agent_orbit += f"""
        <div class="orbit-label {state}" style="--angle:{angle}deg">{_esc(name)}</div>"""

    # Bus feed
    bus_html = ""
    for msg in (inbox_msgs + broadcast_msgs)[:6]:
        bus_html += f"""
        <div class="bus-line">
          <span class="bl-tag">{_esc(msg.get('topic',''))}</span>
          <span>{_esc(msg.get('from'))}→{_esc(msg.get('to'))}</span>
          <span class="bl-ts">{_esc(str(msg.get('timestamp',''))[11:16])}</span>
        </div>"""

    warn_strip = ""
    if warnings:
        w = warnings[0].get("payload", {})
        warn_strip = f'<div class="warn-strip">⚠ ORACLE: {_esc(w.get("event",""))} — {_esc(w.get("title",""))}</div>'

    prio_html = "".join(f'<li>{_esc(p)}</li>' for p in priorities[:5]) or "<li>All clear</li>"

    voice_api = _voice_api_url()
    gcp_url = _gcp_hud_url()
    devops_status = (devops or {}).get("status", sg_status)
    tab_panels = build_tab_panels(
        headlines, media, devops, agents, markets, priorities, bus_html,
        keeper_data, vanguard_data,
    )

    ticker_parts = " &nbsp;·&nbsp; ".join(_esc(h.get("title", "")[:60]) for h in headlines[:12])
    ticker_inner = f"{ticker_parts} &nbsp;·&nbsp; {ticker_parts}" if ticker_parts else "Oracle feed loading..."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>J.A.R.V.I.S. HUD</title>
<meta http-equiv="refresh" content="60">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Rajdhani:wght@300;500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --c: #00d4ff; --c2: #00ffcc; --c-dim: rgba(0,212,255,0.12);
  --bg: #010608; --panel: rgba(0,20,35,0.75);
  --line: rgba(0,212,255,0.3); --text: #c8e8ff; --muted: #4a7a9a;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%;overflow:hidden}}
body{{
  font-family:'Rajdhani',sans-serif; background:var(--bg); color:var(--text);
  background-image:
    radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0,60,90,0.15) 0%, transparent 70%),
    repeating-conic-gradient(from 0deg at 50% 50%, transparent 0deg 10deg, rgba(0,212,255,0.015) 10deg 11deg);
}}

/* ── HUD grid ── */
.hud {{
  display:grid;
  grid-template-columns: 220px 1fr 280px;
  grid-template-rows: 52px 1fr 48px;
  height:100vh; gap:0;
  grid-template-areas:
    "top top top"
    "left center right"
    "bot bot bot";
}}

/* ── TOP BAR ── */
.topbar {{
  grid-area:top; display:flex; align-items:center; justify-content:space-between;
  padding:0 1.2rem; border-bottom:1px solid var(--line);
  background:rgba(0,10,20,0.9);
}}
.brand {{
  font-family:'Orbitron',sans-serif; font-size:0.7rem; letter-spacing:3px;
  color:var(--muted);
}}
.brand strong{{color:var(--c); font-size:0.85rem; letter-spacing:5px}}
.digiclock {{
  font-family:'Orbitron',sans-serif; font-size:1.6rem; color:var(--c);
  letter-spacing:4px; text-shadow:0 0 20px rgba(0,212,255,0.6);
}}
.loc {{ font-size:0.8rem; color:var(--muted); letter-spacing:2px; text-align:right }}
.loc strong{{display:block; color:var(--c2); font-size:0.95rem}}

/* ── LEFT PANEL ── */
.left {{
  grid-area:left; padding:0.8rem; display:flex; flex-direction:column; gap:0.6rem;
  border-right:1px solid var(--line); overflow:hidden;
}}
.date-ring {{
  width:90px; height:90px; border-radius:50%;
  border:2px solid var(--c); display:flex; flex-direction:column;
  align-items:center; justify-content:center; margin:0 auto 0.4rem;
  box-shadow:0 0 15px rgba(0,212,255,0.3);
}}
.date-ring .dn{{font-family:'Orbitron',sans-serif;font-size:1.8rem;color:var(--c);line-height:1}}
.date-ring .dm{{font-size:0.6rem;letter-spacing:2px;color:var(--muted)}}
.rings-row{{display:flex;flex-wrap:wrap;gap:0.3rem;justify-content:center}}
.ring-widget{{text-align:center}}
.ring-svg{{width:72px;height:72px}}
.ring-bg{{fill:none;stroke:rgba(0,212,255,0.1);stroke-width:5}}
.ring-fg{{fill:none;stroke:var(--c);stroke-width:5;stroke-linecap:round;
  filter:drop-shadow(0 0 4px var(--c))}}
.ring-val{{fill:var(--c);font-size:9px;font-family:'Orbitron',sans-serif;text-anchor:middle}}
.ring-sub{{fill:var(--muted);font-size:7px;text-anchor:middle}}
.ring-label{{font-size:0.55rem;letter-spacing:1px;color:var(--muted);margin-top:-4px}}

.panel-box {{
  background:var(--panel); border:1px solid var(--line); border-radius:4px;
  padding:0.5rem 0.6rem; flex:1; overflow:hidden;
}}
.panel-hdr {{
  font-family:'Orbitron',sans-serif; font-size:0.55rem; letter-spacing:2px;
  color:var(--c); margin-bottom:0.4rem; opacity:0.8;
}}
.prio-list{{list-style:none;font-size:0.75rem;line-height:1.6}}
.prio-list li::before{{content:'▸ ';color:var(--c)}}
.mkt-row{{display:grid;grid-template-columns:1fr auto;gap:0.1rem;
  font-size:0.72rem;padding:0.2rem 0;border-bottom:1px solid rgba(0,212,255,0.06)}}
.mkt-sym{{color:var(--c);font-family:'Orbitron',sans-serif;font-size:0.65rem}}
.mkt-px{{color:var(--c2);font-weight:700}}
.mkt-ts{{grid-column:1/-1;font-size:0.58rem;color:var(--muted)}}

/* ── CENTER HUB ── */
.center {{
  grid-area:center; position:relative; display:flex;
  align-items:center; justify-content:center; overflow:hidden;
}}
.hub-wrap{{position:relative;width:min(420px,90vw);height:min(420px,90vw)}}
.hub-ring{{
  position:absolute;inset:0;border-radius:50%;
  border:1px solid var(--line);
}}
.hub-ring:nth-child(1){{inset:5%;animation:spin 30s linear infinite}}
.hub-ring:nth-child(2){{inset:15%;border-style:dashed;animation:spin 20s linear infinite reverse}}
.hub-ring:nth-child(3){{inset:28%;border-color:rgba(0,212,255,0.5);animation:spin 12s linear infinite}}
.hub-ring:nth-child(4){{inset:38%;border:2px solid var(--c);box-shadow:0 0 30px rgba(0,212,255,0.2);
  animation:pulse-hub 3s ease-in-out infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes pulse-hub{{
  0%,100%{{box-shadow:0 0 20px rgba(0,212,255,0.2)}}
  50%{{box-shadow:0 0 50px rgba(0,212,255,0.5)}}
}}
.hub-core{{
  position:absolute;inset:42%;border-radius:50%;
  background:radial-gradient(circle,rgba(0,212,255,0.3) 0%,transparent 70%);
  display:flex;align-items:center;justify-content:center;flex-direction:column;
}}
.hub-core span{{
  font-family:'Orbitron',sans-serif;font-size:0.65rem;color:var(--c);
  letter-spacing:3px;text-shadow:0 0 10px var(--c);
}}
.hub-core small{{font-size:0.45rem;color:var(--muted);letter-spacing:1px;margin-top:2px}}
.orbit-label{{
  position:absolute;top:50%;left:50%;
  font-size:0.55rem;letter-spacing:1px;color:var(--muted);
  transform:rotate(var(--angle)) translateX(155px) rotate(calc(-1 * var(--angle)));
  white-space:nowrap;
}}
.orbit-label.running{{color:var(--c2)}}
.orbit-label.alert{{color:#ff4466}}
.hub-stats{{
  position:absolute;bottom:1rem;left:50%;transform:translateX(-50%);
  display:flex;gap:1.5rem;font-size:0.65rem;color:var(--muted);white-space:nowrap;
}}
.hub-stats strong{{color:var(--c);font-family:'Orbitron',sans-serif}}

/* connector lines */
.center::before,.center::after{{
  content:'';position:absolute;background:var(--line);z-index:0;
}}
.center::before{{top:50%;left:0;right:0;height:1px}}
.center::after{{left:50%;top:0;bottom:0;width:1px}}

/* ── RIGHT PANEL ── */
.right {{
  grid-area:right; padding:0.8rem; display:flex; flex-direction:column; gap:0.5rem;
  border-left:1px solid var(--line); overflow:hidden;
}}
.weather-box {{
  background:var(--panel); border:1px solid var(--line); border-radius:4px;
  padding:0.6rem;
}}
.wx-now{{display:flex;align-items:center;gap:0.8rem;margin-bottom:0.5rem}}
.wx-icon{{font-size:2rem;color:var(--c)}}
.wx-temp{{font-family:'Orbitron',sans-serif;font-size:2rem;color:var(--c)}}
.wx-meta{{font-size:0.65rem;color:var(--muted);line-height:1.5}}
.fc-row{{
  display:grid;grid-template-columns:2rem 1.5rem 2.5rem 2.5rem;
  font-size:0.7rem;padding:0.15rem 0;border-bottom:1px solid rgba(0,212,255,0.05);
  align-items:center;
}}
.fc-icon{{color:var(--c);text-align:center}}
.fc-min{{color:var(--muted)}}
.news-box{{flex:1;overflow:hidden;display:flex;flex-direction:column}}
.news-scroll{{overflow-y:auto;flex:1}}
.news-scroll::-webkit-scrollbar{{width:3px}}
.news-scroll::-webkit-scrollbar-thumb{{background:var(--c-dim)}}
.news-line{{
  display:block;text-decoration:none;color:inherit;
  padding:0.45rem 0;border-bottom:1px solid rgba(0,212,255,0.07);
  transition:padding-left 0.15s;
}}
.news-line:hover{{padding-left:0.3rem;background:var(--c-dim)}}
.nl-src{{font-size:0.55rem;color:var(--c);letter-spacing:1px;display:block}}
.nl-title{{font-size:0.72rem;line-height:1.3;display:block;margin:0.1rem 0}}
.nl-time{{font-size:0.58rem;color:var(--muted)}}
.nl-time em{{color:var(--c2);font-style:normal}}

/* ── BOTTOM BAR ── */
.botbar {{
  grid-area:bot; display:flex; align-items:center; justify-content:space-between;
  padding:0 1.2rem; border-top:1px solid var(--line);
  background:rgba(0,10,20,0.9); font-size:0.65rem; color:var(--muted);
}}
.bot-tabs{{display:flex;gap:1.5rem}}
.bot-tabs span{{letter-spacing:2px;cursor:default}}
.bot-tabs span.active{{color:var(--c);border-bottom:1px solid var(--c)}}
.ticker-mini{{
  flex:1;margin:0 2rem;overflow:hidden;white-space:nowrap;
  font-size:0.62rem;color:var(--muted);
}}
.ticker-inner{{display:inline-block;animation:scroll 40s linear infinite}}
@keyframes scroll{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}

.warn-strip{{
  position:fixed;top:52px;left:0;right:0;z-index:99;
  background:rgba(255,60,60,0.15);border-bottom:1px solid #ff4466;
  padding:0.3rem 1rem;font-size:0.7rem;color:#ff8899;text-align:center;
}}
.bus-line{{font-size:0.65rem;padding:0.2rem 0;border-bottom:1px solid rgba(0,212,255,0.05);
  display:grid;grid-template-columns:auto 1fr auto;gap:0.3rem;align-items:center}}
.bl-tag{{background:var(--c-dim);color:var(--c);padding:0 0.3rem;font-size:0.55rem;border-radius:2px}}
.bl-ts{{color:var(--muted)}}
.hub-wrap.listening .hub-ring{{animation-duration:3s!important;border-color:var(--c2)!important;box-shadow:0 0 25px rgba(0,255,204,0.4)}}
.hub-wrap.listening .hub-ring:nth-child(4){{box-shadow:0 0 60px rgba(0,255,204,0.7)}}
.hub-wrap.processing .hub-core{{animation:pulse-hub 0.6s ease-in-out infinite}}
.hub-wrap.speaking .hub-core span{{color:var(--c2);text-shadow:0 0 20px var(--c2)}}
.voice-mic{{
  background:rgba(0,212,255,0.15);border:2px solid var(--c);border-radius:50%;
  width:48px;height:48px;font-size:1.3rem;cursor:pointer;margin-bottom:0.3rem;
  transition:transform 0.15s,box-shadow 0.15s;
}}
.voice-mic:hover{{transform:scale(1.08);box-shadow:0 0 20px rgba(0,212,255,0.5)}}
.hub-wrap.listening .voice-mic,.hub-wrap.session .voice-mic{{border-color:var(--c2);box-shadow:0 0 30px rgba(0,255,204,0.6);animation:mic-pulse 1s ease-in-out infinite}}
.hub-wrap.session .voice-mic{{border-color:#ffb020;box-shadow:0 0 25px rgba(255,176,32,0.5)}}
@keyframes mic-pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.1)}}}}
.voice-panel{{
  position:fixed;bottom:56px;left:50%;transform:translateX(-50%);width:min(520px,92vw);
  background:rgba(2,14,28,0.95);border:1px solid var(--line);border-radius:6px;
  padding:0.6rem 0.8rem;z-index:50;max-height:140px;overflow-y:auto;
}}
.voice-panel .panel-hdr{{font-family:'Orbitron',sans-serif;font-size:0.55rem;color:var(--c);margin-bottom:0.3rem}}
#voice-hint{{font-size:0.7rem;color:var(--muted);margin-bottom:0.4rem}}
.vlog-line{{font-size:0.72rem;line-height:1.45;margin-bottom:0.35rem;border-bottom:1px solid rgba(0,212,255,0.06);padding-bottom:0.3rem}}
.v-you{{color:var(--muted);font-size:0.6rem;letter-spacing:1px}}
.v-j{{color:var(--c);font-size:0.6rem;letter-spacing:1px}}
.v-links{{margin-top:0.2rem;font-size:0.68rem}}.v-links a{{color:var(--c2);margin-right:0.5rem}}
.v-handoff{{color:#ffb020;font-size:0.58rem}}
.voice-input-row{{display:flex;gap:0.4rem;margin:0.4rem 0}}
.voice-input-row input{{flex:1;background:rgba(0,20,35,0.9);border:1px solid var(--line);color:var(--text);
  padding:0.35rem 0.5rem;border-radius:3px;font-size:0.8rem}}
.voice-input-row button{{background:var(--c-dim);border:1px solid var(--c);color:var(--c);padding:0.35rem 0.7rem;
  cursor:pointer;border-radius:3px;font-size:0.75rem}}
{OVERLAY_CSS}
</style>
</head>
<body>
{warn_strip}
<div class="hud">

  <!-- TOP -->
  <div class="topbar">
    <div class="brand"><strong>J.A.R.V.I.S.</strong><br>PERSONAL COMMAND INTERFACE</div>
    <div class="digiclock" id="clk">{clock_init}</div>
    <div class="loc"><strong>{_esc(wloc)}</strong>{_esc(region_label)} · EN-IN</div>
  </div>

  <!-- LEFT -->
  <div class="left">
    <div class="date-ring">
      <div class="dn">{day_num}</div>
      <div class="dm">{month}<br>{year}</div>
    </div>
    <div class="rings-row">
      {_ring(agent_pct, "AGENTS", str(agent_active))}
      {_ring(gcp_pct, "GCP", sg_status[:4].upper())}
      {_ring(news_pct, "NEWS", str(news_count))}
      {_ring(market_pct, "MKT", str(len(markets)))}
    </div>
    <div class="panel-box">
      <div class="panel-hdr">SYNERGY // PRIORITIES</div>
      <ul class="prio-list">{prio_html}</ul>
    </div>
    <div class="panel-box">
      <div class="panel-hdr">VANGUARD // MARKETS</div>
      {market_html or '<div style="font-size:0.7rem;color:var(--muted)">Fetching...</div>'}
    </div>
    <div class="panel-box">
      <div class="panel-hdr">BUS // SIGNALS</div>
      {bus_html or '<div style="font-size:0.65rem;color:var(--muted)">Quiet</div>'}
    </div>
  </div>

  <!-- CENTER HUB -->
  <div class="center">
    <div class="hub-wrap">
      <div class="hub-ring"></div>
      <div class="hub-ring"></div>
      <div class="hub-ring"></div>
      <div class="hub-ring"></div>
      {agent_orbit}
      <div class="hub-core">
        <button type="button" id="voice-mic" class="voice-mic" title="Speak to JARVIS (V)">🎤</button>
        <span>J.A.R.V.I.S.</span>
        <small id="voice-status">ONLINE</small>
        <small id="active-agent" style="display:block;color:var(--muted);font-size:0.55rem">JARVIS</small>
      </div>
      <div class="hub-stats">
        <span>CTX <strong>{_esc(str(generated)[11:19])}</strong></span>
        <span>DEVOPS <strong>{_esc(devops_status).upper()}</strong></span>
        <span>LAT <strong>{latency}ms</strong></span>
        <span>NEWS <strong>{news_meta or 'live'}</strong></span>
      </div>
    </div>
  </div>

  <!-- RIGHT -->
  <div class="right">
    <div class="weather-box">
      <div class="wx-now">
        <div class="wx-icon">{_weather_icon(wcode)}</div>
        <div>
          <div class="wx-temp">{wtemp}°C</div>
          <div class="wx-meta">{_esc(wdesc)}<br>Humidity {_esc(whum)}% · Wind {_esc(wwind)} km/h</div>
        </div>
      </div>
      {forecast_html}
    </div>
    <div class="panel-box news-box">
      <div class="panel-hdr">ORACLE // LIVE NEWS ({len(headlines)})</div>
      <div class="news-scroll">{news_html or '<div style="color:var(--muted);font-size:0.7rem">Refreshing feeds...</div>'}</div>
    </div>
  </div>

  <!-- BOTTOM -->
  <div class="botbar">
    <div class="bot-tabs">
      <span class="active" data-tab="command">COMMAND</span>
      <span data-tab="agents">AGENTS</span>
      <span data-tab="markets">MARKETS</span>
      <span data-tab="vanguard">VANGUARD</span>
      <span data-tab="oracle">ORACLE</span>
      <span data-tab="media">LIFE</span>
      <span data-tab="devops">DEVOPS</span>
      <span data-tab="personal">PERSONAL</span>
    </div>
    <div class="ticker-mini">
      <div class="ticker-inner">{ticker_inner}</div>
    </div>
    <div>MIC · GCP HUD · HTTPS VOICE</div>
  </div>

</div>
<div class="voice-panel">
  <div class="panel-hdr">VOICE INTERFACE · GCP · CLAP WAKE</div>
  <div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.3rem">
    <span id="clap-status" style="font-size:0.65rem;color:var(--c2)">CLAP …</span>
    <button type="button" id="clap-toggle" style="font-size:0.65rem;padding:0.2rem 0.5rem;border:1px solid var(--line);
      background:transparent;color:var(--muted);cursor:pointer;border-radius:3px">Toggle clap</button>
  </div>
  <div id="voice-hint">Clap to wake · press V for session · say stand down to end</div>
  <div class="voice-input-row">
    <input id="cmd-input" type="text" placeholder="Type a command or ask an agent…" autocomplete="off"/>
    <button type="button" id="cmd-send">Send</button>
  </div>
  <div id="voice-log"></div>
</div>
{tab_panels}
<script>window.JARVIS_API="{_esc(voice_api)}";window.JARVIS_HUD="{_esc(gcp_url)}";</script>
<script>
function tick(){{
  const el=document.getElementById('clk');
  if(!el)return;
  const n=new Date();
  const p=v=>String(v).padStart(2,'0');
  el.textContent=p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds());
}}
tick();setInterval(tick,1000);
{OVERLAY_JS}
{_voice_js()}
</script>
</body>
</html>"""
