#!/usr/bin/env python3
import os
import yaml
import json
import subprocess
import pandas as pd
from ta_engine import score_setup, compute_rsi

def load_trading_config():
    fpath = "config/trading.yaml"
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
        "--summary", "Running Penny Momentum Scan"
    ], check=True)

    config = load_trading_config()
    watchlist = config.get("watchlists", {}).get("india_equity", ["TATASTEEL", "RELIANCE"])
    
    # Read penny parameters from config
    p_config = config.get("screener", {}).get("penny", {})
    price_min = p_config.get("price_min", 5)
    price_max = p_config.get("price_max", 50)
    min_volume = p_config.get("min_volume", 500000)
    min_day_change = p_config.get("min_day_change_pct", 3)
    rsi_min = p_config.get("rsi_min", 50)
    rsi_max = p_config.get("rsi_max", 75)

    print(f"Starting Penny Momentum Screener on: {watchlist}")
    print(f"Filters: Price={price_min}-{price_max}, MinVol={min_volume}, DayChange>={min_day_change}%, RSI={rsi_min}-{rsi_max}")

    for symbol in watchlist:
        # Fetch latest data
        print(f"Fetching data for {symbol}...")
        try:
            # Penny stocks usually need daily data
            subprocess.run([
                "python3", "scripts/fetch_nse_data.py", 
                "--symbol", symbol, 
                "--period", "60d", 
                "--interval", "1d"
            ], check=True, capture_output=True)
        except Exception as e:
            print(f"Failed to fetch data for {symbol}: {e}")
            continue

        csv_path = f"cache/market-snapshots/{symbol}.csv"
        if not os.path.exists(csv_path):
            print(f"Data file missing for {symbol}")
            continue

        try:
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            if len(df) < 20:
                continue

            last = df.iloc[-1]
            prev = df.iloc[-2]

            close = float(last['Close'])
            volume = float(last['Volume']) if 'Volume' in last else 0
            day_change = ((close - float(prev['Close'])) / float(prev['Close'])) * 100
            
            # Compute RSI manually if not computed
            df['RSI'] = compute_rsi(df['Close'], 14)
            rsi = float(df['RSI'].iloc[-1])

            # Apply Penny filters
            price_ok = price_min <= close <= price_max
            volume_ok = volume >= min_volume
            change_ok = day_change >= min_day_change
            rsi_ok = rsi_min <= rsi <= rsi_max

            print(f"{symbol} Stats: Price={close:.2f} ({price_ok}), Vol={volume:,.0f} ({volume_ok}), Change={day_change:.2f}% ({change_ok}), RSI={rsi:.1f} ({rsi_ok})")

            if price_ok and volume_ok and change_ok and rsi_ok:
                score, direction, reason = score_setup(df, asset_class="india_equity")
                
                payload = {
                    "symbol": symbol,
                    "asset_class": "india_equity",
                    "screener_type": "penny_momentum",
                    "trigger_price": close,
                    "setup_score": int(score),
                    "indicators": {
                        "rsi_14": rsi,
                        "day_change_pct": day_change,
                        "volume": volume
                    }
                }
                
                print(f"Qualifying Penny Stock Setup Found! Writing alert for {symbol}...")
                subprocess.run([
                    "python3", "scripts/bus_write.py",
                    "--from-agent", "Tracker",
                    "--to-agent", "Strategist",
                    "--topic", "screener_alert",
                    "--payload", json.dumps(payload)
                ], check=True)
        except Exception as e:
            print(f"Error analyzing penny candidate {symbol}: {e}")

    # Update Tracker state to idle
    subprocess.run([
        "python3", "scripts/update_agent_status.py",
        "--agent", "Tracker",
        "--state", "idle",
        "--summary", "Penny Momentum Scan complete"
    ], check=True)

if __name__ == "__main__":
    main()
