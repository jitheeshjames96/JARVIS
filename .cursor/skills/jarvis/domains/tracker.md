# Tracker — Market Screener Agent

## Scope
Automates broad technical screening across watchlists and stock lists (India penny stocks & momentum stocks) using local python scripts to rank candidates before LLM analysis.

## Workflow
```
Run Screen Scripts → Filter by Config Rules → Ranks Assets → Write Alert to Bus
```

## Bus Integration
- **Writes:** `screener_alert` (to Strategist) containing the top 5 ranked momentum or penny stock candidates.

## Screener Engines
1. **Penny Momentum:** Filters ₹5–₹50 stocks with >500k average volume, daily gain >3%, and RSI between 50–75.
2. **Swing Momentum:** Filters stocks >₹50 in the top return decile, pulling back to EMA supports, with a target R:R of ≥2:1.
