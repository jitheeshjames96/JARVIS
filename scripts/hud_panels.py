#!/usr/bin/env python3
"""Iron Man-style HUD tab overlay panels."""

from __future__ import annotations

import html


def _e(t) -> str:
    return html.escape(str(t or ""))


def build_tab_panels(
    headlines: list,
    media: list,
    devops: dict,
    agents: dict,
    markets: list,
    priorities: list,
    bus_html: str,
    keeper: dict | None = None,
) -> str:
    # Oracle / news panel
    news_rows = ""
    for h in headlines[:25]:
        news_rows += f"""
        <a class="panel-row" href="{_e(h.get('link','#'))}" target="_blank">
          <span class="pr-src">{_e(h.get('source'))}</span>
          <span class="pr-title">{_e(h.get('title'))}</span>
          <span class="pr-meta">{_e(h.get('published_display',''))} · {_e(h.get('age_display',''))}</span>
        </a>"""

    # Media / video panel
    media_rows = ""
    for m in media[:20]:
        thumb = m.get("thumbnail", "")
        media_rows += f"""
        <a class="panel-row video-row" href="{_e(m.get('link','#'))}" target="_blank">
          {f'<img src="{_e(thumb)}" alt="" class="thumb"/>' if thumb else ''}
          <div>
            <span class="pr-src">{_e(m.get('source'))} · VIDEO</span>
            <span class="pr-title">{_e(m.get('title'))}</span>
            <span class="pr-meta">{_e(m.get('published_display',''))} · {_e(m.get('age_display',''))}</span>
          </div>
        </a>"""

    # DevOps panel
    devops = devops or {}
    issues = devops.get("issues", [])
    checks = devops.get("checks", {})
    devops_rows = f"""
    <div class="devops-status { _e(devops.get('status','unknown')) }">
      STATUS: <strong>{_e(devops.get('status','unknown')).upper()}</strong>
      · {_e(devops.get('checked_at','')[:19].replace('T',' '))} UTC
    </div>"""
    if issues:
        devops_rows += "<ul class='issue-list'>"
        for issue in issues:
            devops_rows += f"<li>{_e(issue)}</li>"
        devops_rows += "</ul>"
    else:
        devops_rows += "<p class='ok-msg'>✓ All GCP checks passing on jitheeshjames27@gmail.com</p>"
    for key, val in checks.items():
        if isinstance(val, dict):
            ok = val.get("ok", True)
            devops_rows += f"<div class='check-row {'ok' if ok else 'fail'}'><span>{_e(key)}</span><span>{'PASS' if ok else 'FAIL'}</span></div>"

    # Agents panel
    agent_rows = ""
    for name, info in agents.items():
        state = info.get("state", "idle")
        agent_rows += f"""
        <div class="panel-row agent-row">
          <span class="pr-src">{_e(name)} · {_e(state).upper()}</span>
          <span class="pr-title">{_e(info.get('summary',''))}</span>
          <span class="pr-meta">Last {_e(str(info.get('last_run',''))[:16].replace('T',' '))}</span>
        </div>"""

    # Markets panel
    mkt_rows = ""
    for m in markets:
        mkt_rows += f"""
        <div class="panel-row">
          <span class="pr-src">{_e(m.get('symbol'))} · NSE/FOREX</span>
          <span class="pr-title">{_e(m.get('close'))}</span>
          <span class="pr-meta">Updated {_e(str(m.get('updated',''))[:19].replace('T',' '))}</span>
        </div>"""

    prio_rows = "".join(f"<li>{_e(p)}</li>" for p in priorities) or "<li>All clear</li>"

    keeper = keeper or {}
    keeper_rows = f"""
    <div class="devops-status { _e(keeper.get('status','idle')) }">
      KEEPER · <strong>{_e(keeper.get('summary','Standing by'))}</strong>
    </div>"""
    due = keeper.get("due_today", [])
    if due:
        keeper_rows += "<p class='ok-msg'>Today:</p><ul class='issue-list'>"
        for item in due:
            keeper_rows += f"<li>{_e(item.get('label'))} — {_e(item.get('relation'))}</li>"
        keeper_rows += "</ul>"
    upcoming = keeper.get("upcoming", [])
    if upcoming:
        for item in upcoming[:20]:
            days = item.get("days_until", 0)
            when = "TODAY" if days == 0 else f"in {days}d"
            keeper_rows += f"""
            <div class="panel-row">
              <span class="pr-src">{_e(item.get('kind','')).upper()} · {_e(item.get('relation'))} · {when}</span>
              <span class="pr-title">{_e(item.get('label'))}</span>
              <span class="pr-meta">{_e(item.get('display_date',''))}</span>
            </div>"""
    else:
        keeper_rows += "<p class='hint'>Add family birthdays in config/personal.yaml</p>"
    missing = keeper.get("contacts_missing_birthdays", 0)
    if missing:
        keeper_rows += f"<p class='hint'>{missing} contact(s) need birthday dates filled in.</p>"

    return f"""
<div id="hud-overlay" class="hud-overlay" aria-hidden="true">
  <div class="overlay-backdrop" onclick="closeHudTab()"></div>
  <div class="overlay-panel">
    <div class="overlay-header">
      <span id="overlay-title" class="overlay-title">PANEL</span>
      <button class="overlay-close" onclick="closeHudTab()" aria-label="Close">✕</button>
    </div>
    <div id="overlay-body" class="overlay-body"></div>
  </div>
</div>

<div id="tab-store" hidden>
  <div id="tab-command"><ul class="prio-list">{prio_rows}</ul><p class="hint">Say: "JARVIS, what is my status?" or clap to activate voice.</p></div>
  <div id="tab-agents">{agent_rows or '<p class="hint">No agent data</p>'}</div>
  <div id="tab-markets">{mkt_rows or '<p class="hint">Fetching NSE/Forex...</p>'}</div>
  <div id="tab-oracle">{news_rows or '<p class="hint">Refreshing Oracle feeds...</p>'}</div>
  <div id="tab-media">{media_rows or '<p class="hint">Loading video digest...</p>'}</div>
  <div id="tab-devops">{devops_rows}</div>
  <div id="tab-personal">{keeper_rows}</div>
  <div id="tab-bus">{bus_html or '<p class="hint">Bus quiet</p>'}</div>
</div>
"""

OVERLAY_CSS = """
.hud-overlay{position:fixed;inset:0;z-index:1000;display:none;align-items:stretch;justify-content:flex-end}
.hud-overlay.open{display:flex;animation:fadeIn .25s ease}
.overlay-backdrop{flex:1;background:rgba(0,8,16,0.75);backdrop-filter:blur(4px)}
.overlay-panel{
  width:min(520px,92vw);background:rgba(2,14,28,0.97);
  border-left:2px solid var(--c);box-shadow:-20px 0 60px rgba(0,212,255,0.15);
  display:flex;flex-direction:column;animation:slideIn .3s cubic-bezier(.2,.8,.2,1);
}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:none;opacity:1}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.overlay-header{display:flex;justify-content:space-between;align-items:center;
  padding:0.8rem 1rem;border-bottom:1px solid var(--line)}
.overlay-title{font-family:'Orbitron',sans-serif;font-size:0.75rem;letter-spacing:3px;color:var(--c)}
.overlay-close{background:none;border:1px solid var(--line);color:var(--c);font-size:1rem;
  cursor:pointer;padding:0.2rem 0.5rem;border-radius:3px}
.overlay-body{flex:1;overflow-y:auto;padding:0.8rem 1rem}
.panel-row{display:block;text-decoration:none;color:inherit;padding:0.6rem 0;
  border-bottom:1px solid rgba(0,212,255,0.08)}
.panel-row:hover{background:var(--c-dim);padding-left:0.4rem}
.pr-src{font-size:0.58rem;color:var(--c);letter-spacing:1px;display:block}
.pr-title{font-size:0.8rem;display:block;margin:0.15rem 0;line-height:1.35}
.pr-meta{font-size:0.62rem;color:var(--muted)}
.video-row{display:flex;gap:0.6rem;align-items:flex-start}
.thumb{width:80px;height:45px;object-fit:cover;border:1px solid var(--line);border-radius:3px}
.devops-status{padding:0.5rem;margin-bottom:0.6rem;border:1px solid var(--line);font-size:0.75rem}
.devops-status.healthy{border-color:var(--c2);color:var(--c2)}
.devops-status.degraded{border-color:#ffb020;color:#ffb020}
.devops-status.critical{border-color:#ff4466;color:#ff4466}
.issue-list{font-size:0.75rem;color:#ff8899;margin:0.5rem 0 0.5rem 1rem}
.ok-msg{color:var(--c2);font-size:0.8rem}
.check-row{display:flex;justify-content:space-between;font-size:0.7rem;padding:0.25rem 0;
  border-bottom:1px solid rgba(0,212,255,0.05)}
.check-row.ok span:last-child{color:var(--c2)}
.check-row.fail span:last-child{color:#ff4466}
.hint{font-size:0.72rem;color:var(--muted);margin-top:0.5rem}
.bot-tabs span{cursor:pointer;padding:0.2rem 0}
.bot-tabs span:hover{color:var(--c)}
"""

OVERLAY_JS = """
const TAB_LABELS = {
  command:'COMMAND', agents:'AVENGERS ROSTER', markets:'VANGUARD MARKETS',
  oracle:'ORACLE INTELLIGENCE', media:'MEDIA & VIDEO', devops:'DEVOPS GCP',
  personal:'KEEPER — PERSONAL', bus:'MESSAGE BUS'
};
function openHudTab(name){
  const store = document.getElementById('tab-'+name);
  if(!store) return;
  document.getElementById('overlay-title').textContent = TAB_LABELS[name] || name.toUpperCase();
  document.getElementById('overlay-body').innerHTML = store.innerHTML;
  document.getElementById('hud-overlay').classList.add('open');
  document.getElementById('hud-overlay').setAttribute('aria-hidden','false');
  document.querySelectorAll('.bot-tabs span').forEach(s=>{
    s.classList.toggle('active', s.dataset.tab===name);
  });
  history.replaceState(null,'','#tab='+name);
}
function closeHudTab(){
  document.getElementById('hud-overlay').classList.remove('open');
  document.getElementById('hud-overlay').setAttribute('aria-hidden','true');
  history.replaceState(null,'',' ');
}
document.querySelectorAll('.bot-tabs span[data-tab]').forEach(el=>{
  el.addEventListener('click',()=>openHudTab(el.dataset.tab));
});
const hash = location.hash.match(/tab=(\\w+)/);
if(hash) openHudTab(hash[1]);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeHudTab();});
"""
