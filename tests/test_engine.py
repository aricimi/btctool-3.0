"""
btctool 3.0 - Comprehensive Unit Test Suite
"""

import unittest
import numpy as np
import pandas as pd
from backend.services.brains import (
    calc_wilder_rsi,
    calc_atr,
    calc_adx,
    calc_squeeze_fsm,
    StatisticalBrain,
    MomentumBrain,
    VolatilityBrain,
)
from backend.services.orderbook import _calc_weighted_depth
from backend.services.decision_matrix import compute_trade_plan, calculate_cross_timeframe_alignment

class TestBtcToolEngine(unittest.TestCase):

    def setUp(self):
        # Generate synthetic klines DataFrame (100 bars)
        np.random.seed(42)
        prices = 80000 + np.cumsum(np.random.randn(100) * 150)
        highs = prices + np.random.uniform(50, 200, 100)
        lows = prices - np.random.uniform(50, 200, 100)
        volumes = np.random.uniform(10, 100, 100)
        
        self.df = pd.DataFrame({
            "timestamp": np.arange(100) * 3600,
            "open": prices - 20,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": volumes,
        })

    def test_weighted_orderbook_depth(self):
        bids = [[80000.0, 1.5], [79900.0, 3.0]]
        asks = [[80100.0, 1.0], [80200.0, 2.5]]
        mid = 80050.0
        depth = _calc_weighted_depth(bids, asks, mid)
        self.assertIn("imbalance", depth)
        self.assertGreaterEqual(depth["imbalance"], -1.0)
        self.assertLessEqual(depth["imbalance"], 1.0)
        self.assertGreater(depth["bid_usd"], 0.0)
        self.assertGreater(depth["ask_usd"], 0.0)

    def test_wilder_rsi(self):
        rsi = calc_wilder_rsi(self.df["close"], 14)
        self.assertEqual(len(rsi), len(self.df))
        self.assertGreaterEqual(rsi.iloc[-1], 0.0)
        self.assertLessEqual(rsi.iloc[-1], 100.0)

    def test_atr_and_adx(self):
        atr = calc_atr(self.df, 14)
        self.assertEqual(len(atr), len(self.df))
        self.assertGreater(atr.iloc[-1], 0.0)

        adx, pdi, mdi = calc_adx(self.df, 14)
        self.assertEqual(len(adx), len(self.df))
        self.assertGreaterEqual(adx.iloc[-1], 0.0)

    def test_squeeze_fsm(self):
        state, badge, upper, lower = calc_squeeze_fsm(self.df, 20, 2.0, 3)
        self.assertIn(state, ["IDLE", "BUILDING", "LOADED", "FIRING", "TRENDING"])
        self.assertIsInstance(badge, str)
        self.assertGreater(upper.iloc[-1], lower.iloc[-1])

    def test_statistical_brain(self):
        # Close at 81500 with bounds [80000, 82000] gives %B = 0.75 (resistance zone)
        out = StatisticalBrain.evaluate(81500.0, 82000.0, 80000.0, "Trend Down")
        self.assertIn("bull_score", out)
        self.assertIn("bear_score", out)
        self.assertIn("pct_b", out)
        self.assertEqual(out["pct_b"], 0.75)
        # In Trend Down with %B >= 0.58, bear score must be elevated
        self.assertGreater(out["bear_score"], out["bull_score"])

    def test_anti_collision_guarantee(self):
        # Long entry and Short entry MUST NEVER be identical
        plan = compute_trade_plan(
            current_price=81000.0,
            atr=500.0,
            timeframe="1h",
            macro_regime="Range",
            squeeze_state="IDLE",
            prob_up=0.52,
            prob_down=0.48,
            pct_b=0.50,
            ob_data={"imbalance_ratio": 0.05},
            pre_filter={},
            is_accelerating=True
        )
        self.assertNotEqual(plan["long_entry_trigger"], plan["short_entry_trigger"])
        self.assertGreater(abs(plan["long_entry_trigger"] - plan["short_entry_trigger"]), 100.0)

    def test_cross_timeframe_alignment(self):
        summaries = {
            "1m": {"prob_up": 0.70, "prob_down": 0.30},
            "5m": {"prob_up": 0.65, "prob_down": 0.35},
            "15m": {"prob_up": 0.68, "prob_down": 0.32},
            "30m": {"prob_up": 0.60, "prob_down": 0.40},
            "1h": {"prob_up": 0.62, "prob_down": 0.38},
            "4h": {"prob_up": 0.72, "prob_down": 0.28},
            "8h": {"prob_up": 0.66, "prob_down": 0.34},
            "1d": {"prob_up": 0.58, "prob_down": 0.42},
            "1w": {"prob_up": 0.50, "prob_down": 0.50},
        }
        align = calculate_cross_timeframe_alignment(summaries)
        self.assertEqual(align["dominant_direction"], "BULLISH")
        self.assertGreaterEqual(align["dominant_count"], 7)
        self.assertEqual(align["alignment_status"], "STRONG CONFLUENCE")

if __name__ == "__main__":
    unittest.main()
