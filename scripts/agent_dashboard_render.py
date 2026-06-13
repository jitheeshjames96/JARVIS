#!/usr/bin/env python3
"""Per-agent detail dashboards — user-friendly deep dives."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
ROOT = Path(__file__).resolve().parent.parent

AGENTS = {
    "sentinel": {
        "title": "Sentinel",
        "role": "Cloud Security & Infrastructure Guard",
        "icon": "🛡",
        "about": "Watches your GCP production footprint — billing, uptime, latency, and scheduled health checks.",
    },
    "oracle": {
        "title": "Oracle",
        "role": "Intelligence & World Briefings",
        "icon": "🌐",
        "about": "Aggregates India, Kerala, markets, sports, health, and world news. Flags macro warnings that affect trading.",
    },
    "apex": {
        "title": "Apex",
        "role": "Forex Chart Analyst",
        "icon": "💱",
        "about": "Analyses forex pairs for pullback and momentum setups. Pauses when Oracle issues macro warnings.",
    },
    "vanguard": {
        "title": "Vanguard",
        "role": "India Equity Analyst",
        "icon": "📈",
        "about": "Auto-scans NSE universe without a manual watchlist. Ranks PREFER / CONSIDER / AVOID with entry, stop, and target.",
    },
    "tracker": {
        "title": "Tracker",
        "role": "Momentum & Penny Screener",
        "icon": "🔍",
        "about": "Screens swing momentum and high-volume names. Sends top candidates to Strategist via the message bus.",
    },
    "strategist": {
        "title": "Strategist",
        "role": "Trade Planning & Position Sizing",
        "icon": "🎯",
        "about": "Turns setups into trade plans with risk rules from your trading config. You always execute manually.",
    },
    "synergy": {
        "title": "Synergy",
        "role": "Chief of Staff & Priorities",
        "icon": "📋",
        "about": "Coordinates daily priorities, project tasks, and elevates infra alerts into your urgent queue.",
    },
    "explorer": {
        "title": "Explorer",
        "role": "Deep Research",
        "icon": "🔬",
        "about": "On-demand research reports. Invoke when you need thorough analysis beyond daily scans.",
    },
    "devops": {
        "title": "DevOps",
        "role": "GCP Health Auditor",
        "icon": "☁",
        "about": "Full audit of jarvis-jitheesh-2026 — APIs, billing, dashboard hosting, Cloud Function, and scheduler.",
    },
    "keeper": {
        "title": "Keeper",
        "role": "Personal Life & Family",
        "icon": "💚",
        "about": "Your family tree, birthdays, death anniversaries, and life events. Reminds you via WhatsApp, Telegram, or email.",
    },
}


def _e(t) -> str:
    return html.escape(str(t or ""))


def _section(title: str, body: str) -> str:
    return f'<section class="card"><h2>{_e(title)}</h2>{body}</section>'


def _render_vanguard(vg: dict) -> str:
    rows = ""
    for tier, label in (("prefer", "✅ PREFER"), ("consider", "👀 CONSIDER"), ("avoid", "⛔ AVOID")):
        items = vg.get(tier, [])
        if not items:
            continue
        rows += f'<h3>{label}</h3><ul class="setup-list">'
        for r in items:
            lv = r.get("levels", {})
            rows += f"""<li><strong>{_e(r.get('symbol'))}</strong> — score {_e(r.get('score'))}
            <br>Entry {_e(lv.get('entry'))} · SL {_e(lv.get('stop'))} · TP {_e(lv.get('target'))} · R:R {_e(lv.get('rr'))}
            <br><em>{_e(r.get('reason'))}</em></li>"""
        rows += "</ul>"
    return rows or "<p>No scan data yet. Say <em>scan markets</em> on the main HUD.</p>"


def _render_keeper(k: dict) -> str:
    body = f"<p>{_e(k.get('summary',''))}</p>"
    if k.get("due_today"):
        body += "<h3>Today</h3><ul>"
        for i in k["due_today"]:
            body += f"<li><strong>{_e(i.get('label'))}</strong> — {_e(i.get('relation'))}</li>"
        body += "</ul>"
    if k.get("upcoming"):
        body += "<h3>Coming up</h3><ul>"
        for i in k["upcoming"][:15]:
            body += f"<li>{_e(i.get('label'))} ({_e(i.get('relation'))}) — {_e(i.get('display_date'))} · in {_e(i.get('days_until'))}d</li>"
        body += "</ul>"
    return body


def _render_oracle(headlines: list, warnings: list) -> str:
    body = ""
    if warnings:
        body += "<h3>⚠ Active warnings</h3><ul>"
        for w in warnings[:5]:
            p = w.get("payload", w)
            body += f"<li>{_e(p.get('event', p.get('title','')))}</li>"
        body += "</ul>"
    body += "<h3>Latest headlines</h3><ul class='news-list'>"
    for h in headlines[:12]:
        body += f'<li><a href="{_e(h.get("link","#"))}" target="_blank">{_e(h.get("title"))}</a> <span class="meta">{_e(h.get("source"))}</span></li>'
    body += "</ul>"
    return body


def _render_devops(d: dict) -> str:
    if not d:
        return "<p>No DevOps report cached.</p>"
    body = f'<p class="status-{ _e(d.get("status","unknown")) }">Status: <strong>{_e(d.get("status"))}</strong></p>'
    if d.get("issues"):
        body += "<ul>"
        for i in d["issues"]:
            body += f"<li>{_e(i)}</li>"
        body += "</ul>"
    else:
        body += "<p>✓ All checks passing.</p>"
    return body


def _voice_api() -> str:
    try:
        import yaml
        p = ROOT / "config" / "gcp.yaml"
        if p.exists():
            with p.open(encoding="utf-8") as f:
                return (yaml.safe_load(f) or {}).get("voice_api_url", "")
    except Exception:
        pass
    return ""


def _voice_js_inline() -> str:
    p = ROOT / "scripts" / "dashboard_voice.js"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def render_agent_page(slug: str, ctx: dict, status: dict, voice_api: str = "") -> str:
    meta = AGENTS.get(slug, {"title": slug.title(), "role": "Agent", "icon": "◎", "about": ""})
    agent_info = status.get("agents", {}).get(meta["title"], {})
    state = agent_info.get("state", "idle")
    summary = agent_info.get("summary", "Standing by")
    now = datetime.now(IST).strftime("%H:%M %d %b %Y IST")

    detail = ""
    if slug == "vanguard":
        detail = _section("Live setups", _render_vanguard(ctx.get("vanguard") or {}))
    elif slug == "keeper":
        detail = _section("Family & events", _render_keeper(ctx.get("keeper") or {}))
    elif slug == "oracle":
        detail = _section("Intelligence feed", _render_oracle(ctx.get("news_headlines", []), ctx.get("active_warnings", [])))
    elif slug == "devops":
        detail = _section("GCP audit", _render_devops(ctx.get("devops_gcp") or {}))
    elif slug == "sentinel":
        sg = ctx.get("sentinel_gcp") or {}
        detail = _section("Production monitor", f"<p>Status: <strong>{_e(sg.get('status','unknown'))}</strong></p><p>{_e(sg.get('summary',''))}</p>")
    elif slug == "synergy":
        prios = ctx.get("priorities", [])
        pl = "".join(f"<li>{_e(p)}</li>" for p in prios) or "<li>All clear</li>"
        detail = _section("Your priorities", f"<ul>{pl}</ul>")
    else:
        signals = ctx.get("trade_signals", [])
        if signals:
            detail = _section("Recent bus signals", "<ul>" + "".join(
                f"<li>{_e(s.get('topic'))}: {_e(s.get('payload',{}).get('symbol', ''))}</li>" for s in signals[:8]
            ) + "</ul>")
        else:
            detail = _section("Activity", "<p>No recent signals. Agent runs on schedule or voice command.</p>")

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS — {meta['title']}</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600&family=Rajdhani:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--c:#00d4ff;--bg:#010608;--text:#c8e8ff;--muted:#4a7a9a;--card:rgba(0,20,35,0.85)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Rajdhani',sans-serif;background:var(--bg);color:var(--text);padding:1.5rem;max-width:900px;margin:0 auto}}
a{{color:var(--c)}}
.hdr{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.5rem;border-bottom:1px solid rgba(0,212,255,0.3);padding-bottom:1rem}}
.hdr h1{{font-family:'Orbitron',sans-serif;font-size:1.4rem;color:var(--c)}}
.badge{{display:inline-block;padding:0.2rem 0.6rem;border:1px solid var(--c);border-radius:3px;font-size:0.75rem;margin-top:0.4rem}}
.badge.running,.badge.alert{{border-color:#ffb020;color:#ffb020}}
.card{{background:var(--card);border:1px solid rgba(0,212,255,0.2);border-radius:6px;padding:1rem;margin-bottom:1rem}}
.card h2{{font-family:'Orbitron',sans-serif;font-size:0.75rem;color:var(--c);margin-bottom:0.6rem;letter-spacing:2px}}
.card h3{{font-size:0.9rem;color:var(--c);margin:0.6rem 0 0.3rem}}
.card p,.card li{{font-size:0.95rem;line-height:1.5;margin:0.3rem 0}}
.meta{{color:var(--muted);font-size:0.8rem}}
.setup-list li{{margin-bottom:0.8rem;list-style:none;border-left:3px solid var(--c);padding-left:0.6rem}}
.back{{font-size:0.85rem;margin-top:1rem;display:inline-block}}
.status-healthy{{color:#00ffcc}}.status-critical{{color:#ff4466}}
.agent-voice{{border:1px solid rgba(0,212,255,0.35);border-radius:8px;padding:1rem;margin-bottom:1rem;background:rgba(0,30,50,0.5)}}
.agent-voice h2{{margin-bottom:0.5rem}}
.voice-mic-agent{{width:52px;height:52px;border-radius:50%;border:2px solid var(--c);background:rgba(0,212,255,0.1);
  font-size:1.4rem;cursor:pointer;margin-bottom:0.5rem}}
.voice-mic-agent.listening{{border-color:#00ffcc;box-shadow:0 0 20px rgba(0,255,204,0.5)}}
#voice-hint{{font-size:0.8rem;color:var(--muted);margin-bottom:0.5rem}}
.voice-input-row{{display:flex;gap:0.4rem;margin:0.5rem 0}}
.voice-input-row input{{flex:1;background:rgba(0,10,20,0.9);border:1px solid rgba(0,212,255,0.3);color:var(--text);padding:0.4rem;border-radius:4px}}
.voice-input-row button{{border:1px solid var(--c);background:rgba(0,212,255,0.15);color:var(--c);padding:0.4rem 0.8rem;cursor:pointer;border-radius:4px}}
#voice-log{{max-height:200px;overflow-y:auto;font-size:0.85rem}}
.vlog-line{{padding:0.4rem 0;border-bottom:1px solid rgba(0,212,255,0.08)}}
.v-you{{color:var(--muted);font-size:0.65rem}}.v-j{{color:var(--c);font-size:0.65rem}}
.v-links a{{color:var(--c2);font-size:0.7rem;margin-right:0.5rem}}.v-handoff{{color:#ffb020;font-size:0.6rem}}
.quick-cmds{{display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.5rem}}
.quick-cmds button{{font-size:0.7rem;padding:0.25rem 0.5rem;border:1px solid rgba(0,212,255,0.25);
  background:transparent;color:var(--muted);cursor:pointer;border-radius:3px}}
.quick-cmds button:hover{{color:var(--c);border-color:var(--c)}}
</style></head><body>
<div class="hdr">
  <div>
    <h1>{meta['icon']} {meta['title']}</h1>
    <div class="badge {state}">{state.upper()}</div>
    <p style="margin-top:0.5rem;color:var(--muted)">{_e(meta['role'])}</p>
  </div>
  <div style="text-align:right;font-size:0.8rem;color:var(--muted)">{now}</div>
</div>
<section class="card"><h2>ABOUT</h2><p>{_e(meta['about'])}</p><p style="margin-top:0.5rem"><strong>Now:</strong> {_e(summary)}</p></section>
<section class="agent-voice card">
  <h2>TALK TO {meta['title'].upper()}</h2>
  <button type="button" id="voice-mic" class="voice-mic-agent" title="Session (V)">🎤</button>
  <div id="voice-hint">Clap to wake · press V for session · say stand down to end</div>
  <div class="voice-input-row">
    <input id="cmd-input" type="text" placeholder="Type a command…" autocomplete="off"/>
    <button type="button" id="cmd-send">Send</button>
    <button type="button" id="clap-toggle" title="Toggle clap wake">👏</button>
  </div>
  <div id="clap-status" style="font-size:0.65rem;color:var(--muted);margin-bottom:0.3rem">Clap watch starting…</div>
  <div class="quick-cmds">
    <button type="button" data-cmd="Give me a status brief">Status</button>
    <button type="button" data-cmd="What should I focus on?">Focus</button>
    <button type="button" data-cmd="Report latest update">Report</button>
  </div>
  <div id="voice-log"></div>
</section>
{detail}
<a class="back" href="../dashboard.html">← Main HUD</a>
<script>window.JARVIS_API="{_e(voice_api)}";window.JARVIS_AGENT="{_e(slug)}";window.JARVIS_HUD="https://storage.googleapis.com/jarvis-jitheesh-2026/dashboard.html";</script>
<script>
document.querySelectorAll('.quick-cmds button').forEach(b=>{{
  b.addEventListener('click',()=>{{
    const inp=document.getElementById('cmd-input');
    if(inp){{inp.value=b.dataset.cmd;document.getElementById('cmd-send')?.click();}}
  }});
}});
{_voice_js_inline()}
</script>
</body></html>"""


def generate_all(ctx: dict, status: dict) -> list[Path]:
    out_dir = ROOT / "dashboards" / "agents"
    out_dir.mkdir(parents=True, exist_ok=True)
    api = _voice_api()
    written = []
    for slug in AGENTS:
        html_doc = render_agent_page(slug, ctx, status, voice_api=api)
        path = out_dir / f"{slug}.html"
        path.write_text(html_doc, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_live_context import build  # noqa: E402
    ctx = build()
    status = json.loads((ROOT / "cache" / "agent-status.json").read_text(encoding="utf-8"))
    paths = generate_all(ctx, status)
    print(f"Generated {len(paths)} agent dashboards in dashboards/agents/")
