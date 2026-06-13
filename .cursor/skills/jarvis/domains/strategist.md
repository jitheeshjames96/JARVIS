# Strategist — Trading & Risk Planner

## Scope
Consolidates raw setup alerts into institutional-grade, risk-managed trade plans. Ensures all parameters match your risk guidelines.

## Workflow
```
Poll Bus setups → Pull Risk Profiles → Compute Sizing & Targets → Write trade_plan_ready
```

## Bus Integration
- **Reads:** `screener_alert` (from Tracker), `forex_setup` (from Apex), and `equity_setup` (from Vanguard).
- **Reads:** `market_warning` (from Oracle) to instantly reject new planning requests if safety lock is active.
- **Writes:** `trade_plan_ready` (to Prime) to dispatch formatted plans to you.

## Sizing & Profit Taking Framework
*   **Position Sizing:** Compares account size with risk-per-trade (e.g. 1%) and stop distance (ATR-based) to output exact quantities.
*   **Targets (TP Ladder):** 50% position off at 1:1 R:R, 30% at 2:1 R:R, 20% runner with trailing stop.
