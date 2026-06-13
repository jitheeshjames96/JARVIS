# Vanguard — India Equity Analyst

## Scope
Scans Nifty/Bank Nifty indices, sector indices, and a configured watchlist for day-trading (opening range breakouts) and swing setups.

## Workflow
```
Scan Pre-market Index → Fetch NSE Prices → Score Confluence → Write Setup to Bus
```

## Bus Integration
- **Reads:** `market_warning` (from Oracle) to lock trading on high-impact macro news.
- **Writes:** `equity_setup` (to Strategist) when a stock meets criteria.

## Trade Routines
1. **Intraday (08:45 Pre-market + 11:30 Scan):** Looks for opening range breakouts (ORB) on high-volume large-caps.
2. **Swing Trading (15:45 End-of-Day Scan):** Looks for breakout-retests and momentum continuations above the 50/200 EMA stack.
