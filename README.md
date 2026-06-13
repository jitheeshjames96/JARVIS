# JARVIS

Your personal AI chief-of-staff — DevOps, planning, business, trading, and day-to-day execution across AWS and GCP.

## Quick start

1. **Open this folder in Cursor** — JARVIS rules and skills load automatically.
2. **Copy config templates** and fill in your details:
   ```bash
   cp config/profile.yaml.example config/profile.yaml
   cp config/infra.yaml.example config/infra.yaml
   ```
3. **Set up cloud MCP servers** (optional but recommended for live infra work):
   ```bash
   cp .cursor/mcp.json.example .cursor/mcp.json
   # Edit .cursor/mcp.json with your AWS/GCP MCP credentials
   ```
4. **Start a chat** and say: *"JARVIS, status report"* or *"JARVIS, help me plan the EKS upgrade"*.

## What JARVIS does

| Domain | Examples |
|--------|----------|
| **DevOps** | Terraform, CI/CD, K8s (EKS/GKE), runbooks, incident response |
| **AWS & GCP** | IAM, networking, cost, security, multi-cloud patterns |
| **Planning** | Weekly priorities, project breakdowns, decision matrices |
| **Business** | Strategy docs, stakeholder comms, process design |
| **Trading** | Research frameworks, risk checklists, journal templates |
| **Personal** | Scheduling, learning plans, habit tracking |

## Architecture

```
You (Cursor chat)
    │
    ▼
AGENTS.md + .cursor/rules/     ← persona, tone, safety guardrails
    │
    ▼
.cursor/skills/jarvis/         ← workflows per domain (DevOps, trading, etc.)
    │
    ▼
config/ + context/ + memory/   ← your profile, active projects, long-term notes
    │
    ▼
MCP servers (AWS, GCP, gh)   ← live cloud & tooling access
```

## Folder guide

| Path | Purpose |
|------|---------|
| `config/` | Your profile, infra accounts, preferences (gitignored secrets) |
| `context/` | Active projects, current priorities — update often |
| `memory/` | Durable facts JARVIS should remember across sessions |
| `runbooks/` | Your SOPs and incident playbooks |
| `scripts/` | Helper scripts for env checks and automation |

## Adding memory

After important decisions, ask JARVIS to *"save this to memory"* — it will append to `memory/notes.md` or the relevant file.

## Security

- Never commit `config/profile.yaml`, `config/infra.yaml`, or `.cursor/mcp.json` with secrets.
- JARVIS will ask before running destructive cloud commands.
- Use read-only IAM roles where possible for exploration.
