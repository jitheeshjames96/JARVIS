#!/usr/bin/env python3
import os
import json
from datetime import datetime

def read_json_file(fpath, default=None):
    if os.path.exists(fpath):
        try:
            with open(fpath, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}

def read_actions_log(fpath):
    entries = []
    if os.path.exists(fpath):
        try:
            with open(fpath, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception:
            pass
    return entries[::-1][:15] # Return top 15 recent actions

def read_bus_messages(folder):
    messages = []
    if os.path.exists(folder):
        try:
            for fname in os.listdir(folder):
                if fname.endswith(".json"):
                    with open(os.path.join(folder, fname), "r") as f:
                        messages.append(json.load(f))
        except Exception:
            pass
    # Sort by timestamp
    messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return messages[:10]

def main():
    # Refresh live context snapshot before rendering
    try:
        import subprocess
        subprocess.run(["python3", "scripts/build_live_context.py"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    live = read_json_file("cache/live-context.json", {})
    status = read_json_file("cache/agent-status.json", {"updated_at": "N/A", "agents": {}})
    news = read_json_file("cache/briefings/news-digest.json", [])
    actions = read_actions_log("logs/agent-actions.jsonl")
    
    inbox_msgs = read_bus_messages("cache/bus/inbox")
    processed_msgs = read_bus_messages("cache/bus/processed")
    broadcast_msgs = read_bus_messages("cache/bus/broadcast")

    priorities = live.get("priorities", [])
    warnings = live.get("active_warnings", [])
    markets = live.get("market_snapshots", [])
    projects = live.get("projects", [])
    sentinel_gcp = live.get("sentinel_gcp") or {}

    # Generate CSS/HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS Chief-of-Staff Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #030712;
            --card-bg: rgba(17, 24, 39, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #10b981;
            --accent: #3b82f6;
            --danger: #ef4444;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', sans-serif;
        }}

        body {{
            background: var(--bg-color);
            color: var(--text-color);
            background-image: radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.05) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 40%);
            background-attachment: fixed;
            min-height: 100vh;
            padding: 2rem;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(10px);
        }}

        header h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(to right, #10b981, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }}

        header p {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }}
        .status-dot.idle {{ background-color: var(--accent); box-shadow: 0 0 8px var(--accent); }}
        .status-dot.running {{ 
            background-color: var(--primary); 
            box-shadow: 0 0 8px var(--primary);
            animation: pulse 1.5s infinite alternate;
        }}
        .status-dot.alert {{ background-color: var(--danger); box-shadow: 0 0 8px var(--danger); }}

        @keyframes pulse {{
            0% {{ transform: scale(1); opacity: 0.6; }}
            100% {{ transform: scale(1.3); opacity: 1; }}
        }}

        /* Visualizer HUD */
        .hud-visualizer-container {{
            background: rgba(17, 24, 39, 0.4);
            border: 1px dashed rgba(59, 130, 246, 0.3);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .hud-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .hud-title {{
            font-size: 0.85rem;
            font-weight: 800;
            color: #3b82f6;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }}

        .hud-wave {{
            display: flex;
            align-items: flex-end;
            gap: 3px;
            height: 24px;
        }}

        .hud-bar {{
            width: 3px;
            height: 4px;
            background-color: #3b82f6;
            border-radius: 2px;
            animation: bounce 1.2s infinite ease-in-out;
        }}

        .hud-bar:nth-child(2) {{ height: 8px; animation-delay: 0.1s; }}
        .hud-bar:nth-child(3) {{ height: 16px; animation-delay: 0.2s; }}
        .hud-bar:nth-child(4) {{ height: 20px; animation-delay: 0.3s; }}
        .hud-bar:nth-child(5) {{ height: 12px; animation-delay: 0.4s; }}
        .hud-bar:nth-child(6) {{ height: 6px; animation-delay: 0.5s; }}

        @keyframes bounce {{
            0%, 100% {{ transform: scaleY(1); }}
            50% {{ transform: scaleY(2.2); }}
        }}

        .grid-container {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
        }}

        @media (max-width: 1024px) {{
            .grid-container {{
                grid-template-columns: 1fr;
            }}
        }}

        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            margin-bottom: 2rem;
            transition: border-color 0.3s ease;
        }}

        .card:hover {{
            border-color: rgba(255, 255, 255, 0.15);
        }}

        .card h2 {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1.2rem;
            border-left: 4px solid var(--primary);
            padding-left: 0.6rem;
            letter-spacing: -0.5px;
        }}

        /* Agent Roster Grid */
        .agents-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 1.2rem;
        }}

        .agent-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .agent-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
        }}

        .agent-name {{
            font-weight: 600;
            font-size: 1.05rem;
        }}

        .agent-summary {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 0.8rem;
            line-height: 1.3;
        }}

        .agent-footer {{
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.3);
            display: flex;
            justify-content: space-between;
        }}

        /* Table and List logs */
        .bus-list, .actions-list {{
            list-style: none;
            font-size: 0.9rem;
        }}

        .bus-item, .action-item {{
            padding: 0.8rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .bus-item:last-child, .action-item:last-child {{
            border-bottom: none;
        }}

        .badge {{
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .badge.screener {{ background: rgba(59, 130, 246, 0.15); color: var(--accent); }}
        .badge.warning {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); }}
        .badge.plan {{ background: rgba(16, 185, 129, 0.15); color: var(--primary); }}

        .news-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .news-item {{
            text-decoration: none;
            color: var(--text-color);
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.8rem;
            transition: all 0.2s ease;
        }}

        .news-item:hover {{
            background: rgba(255, 255, 255, 0.03);
            transform: translateX(4px);
        }}

        .news-title {{
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.3rem;
        }}

        .news-meta {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>

    <header>
        <div>
            <h1>JARVIS Chief-of-Staff</h1>
            <p>Avengers-Style Personal AI Workspace</p>
        </div>
        <div style="text-align: right;">
            <p style="font-weight: 600;">System Clock: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p style="font-size: 0.75rem;">Live context: {live.get("generated_at", "N/A")}</p>
            <p style="font-size: 0.75rem;">Status board: {status.get("updated_at")}</p>
        </div>
    </header>
"""

    if warnings:
        w = warnings[0].get("payload", {})
        html_content += f"""
    <div class="card" style="border-color: rgba(239,68,68,0.5); background: rgba(239,68,68,0.08);">
        <h2 style="border-left-color: var(--danger);">Active Market Warning</h2>
        <p><strong>{w.get('event', 'High impact event')}</strong> — {w.get('title', '')}</p>
    </div>
"""

    html_content += f"""
    <div class="hud-visualizer-container">
        <div class="hud-left">
            <div class="hud-wave">
                <div class="hud-bar"></div>
                <div class="hud-bar"></div>
                <div class="hud-bar"></div>
                <div class="hud-bar"></div>
                <div class="hud-bar"></div>
                <div class="hud-bar"></div>
            </div>
            <span class="hud-title">Vocal Channel Online — Piper Neural TTS</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--accent); font-family: monospace;">
            LIVE DATA &bull; AUTO-REFRESH 30s &bull; SAY "JARVIS" IN voice/jarvis_loop.py
        </div>
    </div>

    <div class="card">
        <h2>Synergy Priorities (live)</h2>
        <ul class="bus-list">
"""

    if not priorities:
        html_content += '<li style="color: var(--text-muted); padding: 1rem;">No urgent priorities in memory/tasks.md</li>'
    else:
        for p in priorities:
            html_content += f'<li class="bus-item"><span>{p}</span></li>'

    html_content += """
        </ul>
    </div>

    <div class="card">
        <h2>Specialist Agents Board (live)</h2>
        <div class="agents-grid">
    """

    for agent, info in status.get("agents", {}).items():
        state = info.get("state", "idle")
        html_content += f"""
            <div class="agent-card">
                <div class="agent-header">
                    <span class="agent-name">{agent}</span>
                    <span class="status-dot {state}"></span>
                </div>
                <div class="agent-summary">
                    {info.get("summary", "Standing by")}
                </div>
                <div class="agent-footer">
                    <span>Last: {info.get("last_run", "N/A")[:16].replace("T", " ") if info.get("last_run") else "N/A"}</span>
                    <span>Next: {info.get("next_run") or "On demand"}</span>
                </div>
            </div>
        """

    html_content += """
        </div>
    </div>
"""

    # Sentinel GCP prod ops panel
    if sentinel_gcp:
        sg_status = sentinel_gcp.get("status", "unknown")
        sg_color = {"healthy": "var(--primary)", "degraded": "#f59e0b", "outage": "var(--danger)"}.get(sg_status, "var(--text-muted)")
        perf = sentinel_gcp.get("performance", {})
        cost = sentinel_gcp.get("cost", {})
        outage = sentinel_gcp.get("outage", {})
        html_content += f"""
    <div class="card" style="border-color: {sg_color};">
        <h2 style="border-left-color: {sg_color};">Sentinel — GCP Prod Ops</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
            <div><span style="color: var(--text-muted); font-size: 0.75rem;">STATUS</span><br><strong style="color: {sg_color}; text-transform: uppercase;">{sg_status}</strong></div>
            <div><span style="color: var(--text-muted); font-size: 0.75rem;">LATENCY</span><br><strong>{perf.get('dashboard_latency_ms', '—')} ms</strong></div>
            <div><span style="color: var(--text-muted); font-size: 0.75rem;">EST. COST</span><br><strong>${cost.get('estimated_monthly_usd', '—')}/mo</strong></div>
            <div><span style="color: var(--text-muted); font-size: 0.75rem;">ENVIRONMENT</span><br><strong>{sentinel_gcp.get('environment', 'prod')}</strong></div>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">{outage.get('message', sentinel_gcp.get('summary', ''))}</p>
        <p style="font-size: 0.75rem; color: var(--text-muted);">Project: {sentinel_gcp.get('project', '')} &bull; Checked: {sentinel_gcp.get('checked_at', '')[:19].replace('T', ' ')} &bull; Source: {sentinel_gcp.get('source', '')}</p>
    </div>
"""

    html_content += """
    <div class="grid-container">
        <div class="left-col">
            <div class="card">
                <h2>Active Message Bus (cache/bus/inbox)</h2>
                <ul class="bus-list">
    """

    all_inbox = inbox_msgs + broadcast_msgs
    if not all_inbox and not processed_msgs:
        html_content += '<li style="color: var(--text-muted); padding: 1rem;">Bus queue is currently empty.</li>'
    else:
        for msg in all_inbox[:10]:
            topic = msg.get("topic")
            badge_class = "screener" if "screener" in topic else ("warning" if "warning" in topic else "plan")
            html_content += f"""
                <li class="bus-item">
                    <div>
                        <span class="badge {badge_class}">{topic}</span>
                        <span style="margin-left: 0.8rem; font-weight: 600; color: #10b981;">[Active]</span>
                        <span style="margin-left: 0.8rem; font-weight: 600;">{msg.get("from")} &rarr; {msg.get("to")}</span>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">{json.dumps(msg.get("payload"))}</div>
                    </div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">{msg.get("timestamp")[11:16]}</span>
                </li>
            """
        for msg in processed_msgs[:5]:
            topic = msg.get("topic")
            badge_class = "screener" if "screener" in topic else ("warning" if "warning" in topic else "plan")
            html_content += f"""
                <li class="bus-item" style="opacity: 0.55;">
                    <div>
                        <span class="badge {badge_class}" style="background: rgba(156, 163, 175, 0.15); color: #9ca3af;">{topic}</span>
                        <span style="margin-left: 0.8rem; font-weight: 600; color: #9ca3af;">[Archived]</span>
                        <span style="margin-left: 0.8rem; font-weight: 600;">{msg.get("from")} &rarr; {msg.get("to")}</span>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.3rem;">{json.dumps(msg.get("payload"))}</div>
                    </div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">{msg.get("timestamp")[11:16]}</span>
                </li>
            """

    html_content += """
                </ul>
            </div>

            <div class="card">
                <h2>Recent Agent Actions Trail (logs/agent-actions.jsonl)</h2>
                <ul class="actions-list">
    """

    if not actions:
        html_content += '<li style="color: var(--text-muted); padding: 1rem;">No actions logged in audit log yet.</li>'
    else:
        for action in actions:
            html_content += f"""
                <li class="action-item">
                    <div>
                        <span style="font-weight: 600; color: var(--accent);">{action.get("agent")}</span>
                        <span style="margin-left: 0.5rem;">{action.get("action")}</span>
                    </div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">{action.get("timestamp")[11:16]} ({action.get("approved_by")})</span>
                </li>
            """

    html_content += """
                </ul>
            </div>
        </div>

        <div class="right-col">
            <div class="card">
                <h2>Market Snapshots (live)</h2>
                <ul class="bus-list">
    """

    if not markets:
        html_content += '<li style="color: var(--text-muted); padding: 1rem;">No market data cached. Run fetch scripts.</li>'
    else:
        for m in markets[:6]:
            html_content += f"""
                <li class="bus-item">
                    <span style="font-weight:600;">{m.get('symbol')}</span>
                    <span style="color: var(--primary);">{m.get('close')}</span>
                </li>
            """

    html_content += """
                </ul>
            </div>
            <div class="card">
                <h2>Active Projects (live)</h2>
                <ul class="bus-list">
    """

    if not projects:
        html_content += '<li style="color: var(--text-muted); padding: 1rem;">No projects in context/active-projects.md</li>'
    else:
        for p in projects:
            html_content += f"""
                <li class="bus-item">
                    <div>
                        <span style="font-weight:600;">{p.get('name')}</span>
                        <div style="font-size:0.8rem;color:var(--text-muted);">{p.get('status')}</div>
                    </div>
                </li>
            """

    html_content += """
                </ul>
            </div>
            <div class="card">
                <h2>Oracle News Feed Digest</h2>
                <div class="news-list">
    """

    if not news:
        html_content += '<div style="color: var(--text-muted); padding: 1rem;">No news digest compiled yet.</div>'
    else:
        for item in news[:8]:
            html_content += f"""
                <a class="news-item" href="{item.get("link")}" target="_blank">
                    <div class="news-title">{item.get("title")}</div>
                    <div class="news-meta">{item.get("source")} &bull; {item.get("published")[:16] if item.get("published") else ""}</div>
                </a>
            """

    html_content += """
                </div>
            </div>
        </div>
    </div>

</body>
</html>
    """

    fpath = "dashboard.html"
    with open(fpath, "w") as f:
        f.write(html_content)
    print(f"Visual status dashboard updated: {fpath}")

    try:
        import subprocess
        from pathlib import Path
        gcp_cfg = Path("config/gcp.yaml")
        if gcp_cfg.exists():
            import yaml  # type: ignore
            with gcp_cfg.open(encoding="utf-8") as gf:
                gcp = yaml.safe_load(gf) or {}
            if gcp.get("enabled"):
                # Pull latest Sentinel cloud report before sync
                subprocess.run(
                    ["python3", "scripts/sentinel_gcp_monitor.py", "--fetch-only"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["python3", "scripts/gcp_sync.py"],
                    check=False,
                )
    except Exception:
        pass

if __name__ == "__main__":
    main()
