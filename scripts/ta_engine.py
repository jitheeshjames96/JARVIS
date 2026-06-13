#!/usr/bin/env python3
import pandas as pd
import numpy as np

def compute_ema(series, period):
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()

def compute_rsi(series, period=14):
    """Calculate Relative Strength Index using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    both_zero = (avg_gain == 0) & (avg_loss == 0)
    rs = avg_gain / (avg_loss + 1e-10) # avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(~both_zero, 50.0)
    
    # Preserve the first row as NaN since it has no diff
    if len(rsi) > 0:
        rsi.iloc[0] = np.nan
        
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    """Calculate MACD Line, Signal Line, and Histogram."""
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist

def compute_atr(df, period=14):
    """Calculate Average True Range."""
    high = df['High']
    low = df['Low']
    
    # Handle shifted close if exists
    if 'Close' in df:
        close_prev = df['Close'].shift(1)
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    else:
        tr = high - low
        
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr

def score_setup(df, asset_class="india_equity", config=None):
    """
    Score the setup of the asset.
    Returns: (score, direction, reason)
    score: 0-100
    direction: 'buy' | 'sell' | 'hold'
    reason: summary of why the score was given
    """
    if len(df) < 50:
        return 0, "hold", "Insufficient data history"

    # Calculate indicators
    df = df.copy()
    df['EMA_20'] = compute_ema(df['Close'], 20)
    df['EMA_50'] = compute_ema(df['Close'], 50)
    df['EMA_200'] = compute_ema(df['Close'], 200)
    df['RSI'] = compute_rsi(df['Close'], 14)
    macd_line, signal_line, _ = compute_macd(df['Close'])
    df['MACD'] = macd_line
    df['MACD_Signal'] = signal_line
    df['ATR'] = compute_atr(df, 14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0
    reasons = []
    direction = "hold"

    close = last['Close']
    rsi = last['RSI']
    ema20 = last['EMA_20']
    ema50 = last['EMA_50']
    ema200 = last['EMA_200']

    # 1. Trend Filter (EMA Stack)
    bullish_trend = close > ema50 and ema50 > ema200
    bearish_trend = close < ema50 and ema50 < ema200

    if bullish_trend:
        score += 30
        reasons.append("Bullish Trend (Close > EMA50 > EMA200)")
        direction = "buy"
    elif bearish_trend:
        score += 30
        reasons.append("Bearish Trend (Close < EMA50 < EMA200)")
        direction = "sell"
    else:
        reasons.append("No clear long-term trend stack")

    # 2. RSI Pullback / Momentum
    if direction == "buy":
        # Pullback setup: trend is bullish, but RSI is cooling down (e.g. 40 to 60)
        if 40 <= rsi <= 60:
            score += 30
            reasons.append(f"RSI in Pullback/Support Zone ({rsi:.1f})")
        elif rsi > 60:
            score += 15
            reasons.append(f"RSI is Strong/Overbought ({rsi:.1f})")
        else:
            reasons.append(f"RSI is Weak ({rsi:.1f})")
    elif direction == "sell":
        # Bearish pullback: trend is bearish, RSI bounces to oversold/cool zone (40 to 60)
        if 40 <= rsi <= 60:
            score += 30
            reasons.append(f"RSI in Pullback/Resistance Zone ({rsi:.1f})")
        elif rsi < 40:
            score += 15
            reasons.append(f"RSI is Weak/Oversold ({rsi:.1f})")
        else:
            reasons.append(f"RSI is Strong ({rsi:.1f})")

    # 3. MACD Crossover
    macd_cross_up = prev['MACD'] <= prev['MACD_Signal'] and last['MACD'] > last['MACD_Signal']
    macd_cross_down = prev['MACD'] >= prev['MACD_Signal'] and last['MACD'] < last['MACD_Signal']

    if direction == "buy" and macd_cross_up:
        score += 20
        reasons.append("Bullish MACD Crossover")
    elif direction == "sell" and macd_cross_down:
        score += 20
        reasons.append("Bearish MACD Crossover")
    elif direction == "buy" and last['MACD'] > last['MACD_Signal']:
        score += 10
        reasons.append("MACD is Bullish")
    elif direction == "sell" and last['MACD'] < last['MACD_Signal']:
        score += 10
        reasons.append("MACD is Bearish")

    # 4. Volume Validation (if applicable)
    if 'Volume' in last and 'Volume' in df:
        avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
        if last['Volume'] > 1.5 * avg_vol:
            score += 20
            reasons.append(f"High Volume Spike ({last['Volume']/avg_vol:.1f}x avg)")
        elif last['Volume'] > avg_vol:
            score += 10
            reasons.append("Above Average Volume")

    # Limit score to 100
    score = min(score, 100)

    # Normalize hold direction if score is too low
    if score < 50:
        direction = "hold"

    reason_str = ", ".join(reasons)
    return score, direction, reason_str
