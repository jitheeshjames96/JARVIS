#!/usr/bin/env python3
import unittest
import pandas as pd
import numpy as np
from ta_engine import compute_ema, compute_rsi, compute_macd, compute_atr, score_setup

class TestIndicatorCalculations(unittest.TestCase):
    def setUp(self):
        # Create a basic dataframe with 100 rows for testing
        dates = pd.date_range(start="2026-01-01", periods=100)
        self.df = pd.DataFrame({
            "Open": np.linspace(100, 200, 100),
            "High": np.linspace(105, 205, 100),
            "Low": np.linspace(95, 195, 100),
            "Close": np.linspace(100, 200, 100),
            "Volume": [1000] * 100
        }, index=dates)

    def test_ema(self):
        ema_20 = compute_ema(self.df["Close"], 20)
        self.assertEqual(len(ema_20), 100)
        self.assertFalse(ema_20.isnull().any())
        self.assertAlmostEqual(ema_20.iloc[0], 100.0)

    def test_rsi_flat(self):
        # A perfectly flat line should result in an RSI around 50 or close to it (no change)
        flat_series = pd.Series([100] * 50)
        rsi = compute_rsi(flat_series, 14)
        # First element is NaN due to diff
        self.assertTrue(np.isnan(rsi.iloc[0]))
        # The rest should be 50 (or NaN if no gains/losses occur depending on implementation; Wilder's is 50 when RS is 1)
        self.assertAlmostEqual(rsi.iloc[-1], 50.0)

    def test_macd(self):
        macd, signal, hist = compute_macd(self.df["Close"])
        self.assertEqual(len(macd), 100)
        self.assertEqual(len(signal), 100)
        self.assertEqual(len(hist), 100)

    def test_atr(self):
        atr = compute_atr(self.df, 14)
        self.assertEqual(len(atr), 100)
        # High - Low is always 10, Close - Close_prev is 1.01. True range is 10.
        self.assertAlmostEqual(atr.iloc[-1], 10.0, places=1)

    def test_score_setup(self):
        # Our df is a strong uptrend
        score, direction, reasons = score_setup(self.df)
        self.assertGreaterEqual(score, 30)
        self.assertEqual(direction, "buy")

if __name__ == "__main__":
    unittest.main()
