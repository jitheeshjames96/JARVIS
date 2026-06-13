# Trading Gateway — Market Operations

This is the central entry point for JARVIS trading tools. It coordinates:
*   [Apex — Forex Analyst](apex.md)
*   [Vanguard — India Equity](vanguard.md)
*   [Tracker — Market Screener](tracker.md)
*   [Strategist — Trading Planner](strategist.md)

## Shared Indicator Engine
Raw market data is processed locally using `scripts/ta_engine.py` to calculate confluences.

## Standard Signal Path
```
Tracker (Screens) → cache/bus/ → Strategist (Position sizes) → Prime (Notifies you)
```
Refer to the individual agent files above for specific scan settings and session times.
