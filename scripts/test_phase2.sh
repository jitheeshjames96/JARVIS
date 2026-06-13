#!/bin/bash
set -e

# Make sure all scripts are executable
chmod +x scripts/*.py scripts/*.sh || true

echo "=== 1. Running Indicators Math Unit Tests ==="
python3 scripts/test_ta.py

echo -e "\n=== 2. Testing Forex Fetch (EURUSD) ==="
python3 scripts/fetch_forex_ohlcv.py --symbol EURUSD --period 60d --interval 1d
ls -l cache/market-snapshots/EURUSD.csv

echo -e "\n=== 3. Testing NSE Equity Fetch (TATASTEEL) ==="
python3 scripts/fetch_nse_data.py --symbol TATASTEEL --period 60d --interval 1d
ls -l cache/market-snapshots/TATASTEEL.csv

echo -e "\n=== 4. Testing Swing Screener Engine ==="
python3 scripts/screener_swing.py

echo -e "\n=== 5. Testing Penny Screener Engine ==="
python3 scripts/screener_penny.py

echo -e "\n=== 6. Testing Morning Brief & News Warnings ==="
./scripts/morning_brief.sh
ls -l cache/briefings/news-digest.json

echo -e "\n=== Phase 2 Validation Successful! ==="
