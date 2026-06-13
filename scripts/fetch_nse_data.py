#!/usr/bin/env python3
import os
import argparse
import yfinance as yf

# Map generic names/indices to yfinance tickers
SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTY50": "^NSEI",
    "NIFTY_BANK": "^NSEBANK"
}

def get_yfinance_ticker(symbol):
    symbol_upper = symbol.upper()
    if symbol_upper in SYMBOL_MAP:
        return SYMBOL_MAP[symbol_upper]
    # For standard NSE equities, append .NS
    return f"{symbol_upper}.NS"

def main():
    parser = argparse.ArgumentParser(description="Fetch NSE (India Equity) historical OHLCV data using yfinance.")
    parser.add_argument("--symbol", required=True, help="Equities ticker symbol or index (e.g. NIFTY, TATASTEEL)")
    parser.add_argument("--interval", default="1d", choices=["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"], help="Data interval")
    parser.add_argument("--period", default="60d", help="Data period (e.g. 60d, 1mo, 1y)")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    ticker = get_yfinance_ticker(symbol)

    print(f"Fetching NSE data for {symbol} ({ticker}) for period {args.period}...")
    
    try:
        df = yf.download(ticker, period=args.period, interval=args.interval, progress=False)
        if df.empty:
            print(f"Error: No data returned for ticker {ticker}.")
            return

        # Flatten multi-index columns if they exist
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Save to snapshot
        snapshot_dir = "cache/market-snapshots"
        os.makedirs(snapshot_dir, exist_ok=True)
        fpath = os.path.join(snapshot_dir, f"{symbol}.csv")
        df.to_csv(fpath)
        print(f"NSE data saved to {fpath} ({len(df)} rows)")
    except Exception as e:
        print(f"Error downloading NSE data: {e}")

if __name__ == "__main__":
    import pandas as pd
    main()
