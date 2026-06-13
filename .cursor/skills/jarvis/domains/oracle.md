# Oracle — Intelligence & World Briefings

## Scope
Scans feeds, macroeconomic events, sector rotations, and tech/AI product announcements. Translates broad events into direct impacts on your personal projects or watchlists.

## Workflow
```
Fetch Feeds → Parse JSON → Analyze Significance → Write Broadcast/Cache → Report Summary
```

## Bus Integration
- **Writes:** `market_warning` (to `broadcast/` for Apex/Vanguard/Strategist) when a high-impact news event is pending or active.
- **Writes:** `intel_brief` (to Prime) to summarize global indicators.

## Intelligence Briefing Structure
Every briefing produces a cached file at `cache/briefings/YYYY-MM-DD-morning.json` containing:
1. **Global Macro:** Key central bank events, interest rates, major headlines.
2. **Markets Snapshot:** VIX, index futures, DXY, commodity highlights.
3. **Tech & Cloud News:** DevOps/AI/cloud releases relevant to Sentinel or active projects.
4. **Personal Implications:** Custom checklist items for Jitheesh.
