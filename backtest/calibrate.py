"""
btctool 3.0 - Offline Parameter Calibration & Backtesting Harness
Calibrates:
1. K-factor (Keltner Channel multiplier: 1.2, 1.5, 1.8, 2.0)
2. Squeeze LOADED candle threshold (3 vs 5 vs 7 bars)
3. ADX trend gate threshold (18 vs 20 vs 22 vs 25)
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from backend.services.market_data import get_klines
from backend.services.brains import calc_atr, calc_adx

async def run_calibration(timeframe: str = "1h", limit: int = 200) -> Dict[str, Any]:
    print(f"\n==========================================")
    print(f"CALIBRATION RUN: Timeframe={timeframe}, Bars={limit}")
    print(f"==========================================")
    
    df = await get_klines(timeframe, limit)
    if df is None or len(df) < 50:
        print("Error: Could not retrieve sufficient historical klines.")
        return {}

    close = df["close"]
    atr = calc_atr(df, 14)
    adx, plus_di, minus_di = calc_adx(df, 14)
    
    # ----------------------------------------------------
    # 1. Calibrate Keltner Channel Multiplier (k-factor)
    # ----------------------------------------------------
    print("\n[1] Calibrating Keltner Channel Multiplier (k-factor)...")
    k_candidates = [1.2, 1.4, 1.5, 1.8, 2.0]
    k_results = []
    
    sma_bb = close.rolling(20).mean()
    std_bb = close.rolling(20).std()
    bb_upper = sma_bb + (2.0 * std_bb)
    bb_lower = sma_bb - (2.0 * std_bb)
    
    for k in k_candidates:
        kc_mid = close.ewm(span=20, adjust=False).mean()
        kc_upper = kc_mid + (k * atr)
        kc_lower = kc_mid - (k * atr)
        
        in_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        squeeze_pct = in_squeeze.mean() * 100
        
        # Squeeze breakout expansion yield (5 bars forward return following a squeeze break)
        firing_bars = in_squeeze.shift(1, fill_value=False) & (~in_squeeze)
        breakout_returns = []
        for idx in np.where(firing_bars)[0]:
            if idx + 5 < len(close):
                ret = abs(close.iloc[idx + 5] - close.iloc[idx]) / close.iloc[idx] * 100
                breakout_returns.append(ret)
                
        avg_expansion = np.mean(breakout_returns) if breakout_returns else 0.0
        k_results.append({
            "k_factor": k,
            "squeeze_frequency_pct": round(squeeze_pct, 1),
            "firing_events": int(firing_bars.sum()),
            "avg_breakout_expansion_pct": round(avg_expansion, 2),
        })
        print(f"  k={k}: Frequency={round(squeeze_pct, 1)}%, Breakout Events={int(firing_bars.sum())}, Avg Expansion={round(avg_expansion, 2)}%")

    # Optimal k-factor: highest expansion yield while maintaining >= 10% squeeze density
    valid_k = [x for x in k_results if x["squeeze_frequency_pct"] >= 10.0]
    best_k = max(valid_k, key=lambda x: x["avg_breakout_expansion_pct"]) if valid_k else k_results[2]
    print(f"  --> Optimal k-factor: {best_k['k_factor']} (Balanced frequency & post-squeeze expansion)")

    # ----------------------------------------------------
    # 2. Calibrate Squeeze LOADED Candle Count Threshold
    # ----------------------------------------------------
    print("\n[2] Calibrating Squeeze LOADED Candle Count...")
    kc_upper_opt = close.ewm(span=20, adjust=False).mean() + (best_k["k_factor"] * atr)
    kc_lower_opt = close.ewm(span=20, adjust=False).mean() - (best_k["k_factor"] * atr)
    in_sq = (bb_upper < kc_upper_opt) & (bb_lower > kc_lower_opt)
    
    counts = []
    c = 0
    for s in in_sq:
        c = (c + 1) if s else 0
        counts.append(c)
    counts = pd.Series(counts, index=df.index)
    
    loaded_thresholds = [2, 3, 4, 5, 6]
    loaded_results = []
    for thresh in loaded_thresholds:
        # Firing after sustained >= thresh bars
        fired = (counts.shift(1, fill_value=0) >= thresh) & (~in_sq)
        win_count = 0
        total_fired = int(fired.sum())
        
        for idx in np.where(fired)[0]:
            if idx + 3 < len(close):
                # Win = price expanded >= 0.5 * ATR in either direction without collapsing back
                exp = abs(close.iloc[idx + 3] - close.iloc[idx])
                if exp >= 0.5 * atr.iloc[idx]:
                    win_count += 1
                    
        win_rate = (win_count / total_fired * 100) if total_fired > 0 else 0.0
        loaded_results.append({
            "threshold_bars": thresh,
            "fired_events": total_fired,
            "expansion_win_rate": round(win_rate, 1),
        })
        print(f"  Threshold={thresh} bars: Events={total_fired}, Breakout Validity Win-Rate={round(win_rate, 1)}%")

    best_loaded = max(loaded_results, key=lambda x: x["expansion_win_rate"]) if loaded_results else loaded_results[1]
    print(f"  --> Optimal LOADED Threshold: {best_loaded['threshold_bars']} bars")

    # ----------------------------------------------------
    # 3. Calibrate ADX Trend Gate Threshold
    # ----------------------------------------------------
    print("\n[3] Calibrating ADX Trend Gate Threshold...")
    adx_thresholds = [18.0, 20.0, 22.0, 24.0, 26.0]
    fast_ema = close.ewm(span=9, adjust=False).mean()
    slow_ema = close.ewm(span=21, adjust=False).mean()
    
    adx_results = []
    for adx_t in adx_thresholds:
        trend_mode = adx > adx_t
        trend_signals = trend_mode & (fast_ema > slow_ema)
        whipsaw_flips = (trend_signals != trend_signals.shift(1)).sum()
        
        # Measure directional continuation when trend_mode is active
        continuation_wins = 0
        samples = 0
        for idx in range(len(close) - 3):
            if trend_signals.iloc[idx]:
                samples += 1
                if close.iloc[idx + 3] > close.iloc[idx]:
                    continuation_wins += 1
                    
        cont_rate = (continuation_wins / samples * 100) if samples > 0 else 0.0
        adx_results.append({
            "adx_threshold": adx_t,
            "whipsaw_flips": int(whipsaw_flips),
            "trend_continuation_pct": round(cont_rate, 1),
        })
        print(f"  ADX > {adx_t}: Whipsaw Flips={whipsaw_flips}, Continuation Accuracy={round(cont_rate, 1)}%")

    best_adx = max(adx_results, key=lambda x: x["trend_continuation_pct"]) if adx_results else adx_results[2]
    print(f"  --> Optimal ADX Trend Threshold: {best_adx['adx_threshold']}")

    summary = {
        "optimal_k_factor": best_k["k_factor"],
        "optimal_loaded_bars": best_loaded["threshold_bars"],
        "optimal_adx_threshold": best_adx["adx_threshold"],
    }
    print("\n==========================================")
    print("CALIBRATION SUMMARY:", summary)
    print("==========================================\n")
    return summary

if __name__ == "__main__":
    asyncio.run(run_calibration("1h", 200))
