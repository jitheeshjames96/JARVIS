# Apex — Forex Specialist Analyst

## Scope
Performs technical analysis and alerts for major and minor currency pairs during active session overlaps (London/NY).

## Workflow
```
Check Safety Lock → Fetch OHLCV → Run Indicator Engine → Grade Setup → Write Signal to Bus
```

## Bus Integration
- **Reads:** `market_warning` (from Oracle) to pause alerts or downgrade sizing before volatile news.
- **Writes:** `forex_setup` (to Strategist) when a candidate setup achieves a grade of A or B.

## Setup Grading Scale
*   **Grade A:** Multi-timeframe trend alignment, price at key S/R level, confluence in indicators (RSI/MACD), and positive volume validation.
*   **Grade B:** Single timeframe pullback/retest, clear S/R invalidation level, tradeable R:R.
*   **Grade C:** Chop/sideways zone, near earnings or news events — watch only, no signals written.
