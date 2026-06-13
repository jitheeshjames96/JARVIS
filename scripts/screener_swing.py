#!/usr/bin/env python3
import os
import yaml
import json
import subprocess
import pandas as pd
from ta_engine import score_setup

def load_trading_config():
    fpath = "config/trading.yaml"
    # Fallback to example if real doesn't exist
    if not os.path.exists(fpath):
        fpath = "config/trading.yaml.example"
    with open(fpath, "r") as f:
        return yaml.safe_load(f)

def main():
    # Update Tracker state to running
    subprocess.run([
        "python3", "scripts/update_agent_status.py",
        "--agent", "Tracker",
        "--state", "running",
        "--summary", "Running Swing Momentum Scan"
    ], check=True)

    config = load_trading_config()
    watchlist = config.get("watchlists", {}).get("india_equity", ["TATASTEEL", "RELIANCE"])
    min_score = config.get("screener", {}).get("min_score", 75)

    print(f"Starting Swing Momentum Screener for: {watchlist} (threshold={min_score})")

    for symbol in watchlist:
        # Fetch latest data
        print(f"Fetching data for {symbol}...")
        try:
            subprocess.run([
                "python3", "scripts/fetch_nse_data.py", 
                "--symbol", symbol, 
                "--period", "60d", 
                "--interval", "1d"
            ], check=True, capture_output=True)
        except Exception as e:
            print(f"Failed to fetch data for {symbol}: {e}")
            continue

        # Load data
        csv_path = f"cache/market-snapshots/{symbol}.csv"
        if not os.path.exists(csv_path):
            print(f"Data file missing for {symbol}")
            continue

        try:
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            score, direction, reason = score_setup(df, asset_class="india_equity")
            print(f"Scored {symbol}: score={score}, direction={direction}, reason={reason}")

            if score >= min_score and direction == "buy":
                # Build alert payload
                payload = {
                    "symbol": symbol,
                    "asset_class": "india_equity",
                    "screener_type": "swing_momentum",
                    "trigger_price": float(df['Close'].iloc[-1]),
                    "setup_score": int(score),
                    "indicators": {
                        "rsi_14": float(df['RSI'].iloc[-1]) if 'RSI' in df else None,
                        "close": float(df['Close'].iloc[-1])
                    }
                }
                
                # Write to message bus using bus_write.py
                print(f"Qualifying Setup Found! Writing alert to bus for {symbol}...")
                subprocess.run([
                    "python3", "scripts/bus_write.py",
                    "--from-agent", "Tracker",
                    "--to-agent", "Strategist",
                    "--topic", "screener_alert",
                    "--payload", json.dumps(payload)
                ], check=True)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")

    # Update Tracker state to idle
    subprocess.run([
        "python3", "scripts/update_agent_status.py",
        "--agent", "Tracker",
        "--state", "idle",
        "--summary", "Swing Momentum Scan complete"
    ], check=True)

if __name__ == "__main__":
    main()
