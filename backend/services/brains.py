"""
btctool 3.0 - Tri-Brain Quantitative Ensemble & 5-State Squeeze Machine
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from backend.config import TIMEFRAME_PARAMETERS, KC_ATR_MULTIPLIER

def calc_wilder_rsi(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothed Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """True Range and Wilder-smoothed Average True Range."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return atr.bfill().fillna(0.0)

def calc_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder smoothed ADX(14), +DI, -DI."""
    high = df["high"]
    low = df["low"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    
    up_move = high - prev_high
    down_move = prev_low - low
    
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr = calc_atr(df, period)
    pos_dm_smooth = pd.Series(pos_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    neg_dm_smooth = pd.Series(neg_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    plus_di = 100 * (pos_dm_smooth / atr.replace(0, np.nan)).fillna(0.0)
    minus_di = 100 * (neg_dm_smooth / atr.replace(0, np.nan)).fillna(0.0)
    
    dx_denom = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / dx_denom.replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().fillna(20.0)
    
    return adx, plus_di, minus_di

def calc_bollinger_metrics(df: pd.DataFrame, bb_period: int = 20, bb_std: float = 2.0) -> Dict[str, Any]:
    """
    Calculates detailed Bollinger Band dynamics:
    - Middle Band (SMA 20) slope and directional tilt (UPWARD, DOWNWARD, HORIZONTAL).
    - Envelope bandwidth percentage = (Upper - Lower) / Middle * 100.
    - Band expansion derivative (true opening vs pinching parallel).
    - Fluid Regime Classification:
        * EXPANDING_UP: Bands opening outwards + upward MB slope
        * EXPANDING_DOWN: Bands opening outwards + downward MB slope
        * WIDE_RANGE: Bandwidth >= 0.50% (ample room for boundary scalps)
        * PINCHED_COMPRESSION: Bandwidth < 0.25% (dead chop, high risk)
        * NORMAL_RANGE: 0.25% <= Bandwidth < 0.50%
    """
    close = df["close"]
    sma_bb = close.rolling(window=bb_period).mean()
    std_bb = close.rolling(window=bb_period).std()
    bb_upper = sma_bb + (bb_std * std_bb)
    bb_lower = sma_bb - (bb_std * std_bb)
    bb_width = (bb_upper - bb_lower) / sma_bb.replace(0, np.nan)

    curr_close = float(close.iloc[-1])
    curr_mb = float(sma_bb.iloc[-1]) if not pd.isna(sma_bb.iloc[-1]) else curr_close
    prev_mb = float(sma_bb.iloc[-3]) if len(sma_bb) >= 3 and not pd.isna(sma_bb.iloc[-3]) else (float(sma_bb.iloc[-2]) if len(sma_bb) >= 2 and not pd.isna(sma_bb.iloc[-2]) else curr_mb)
    
    mb_slope_pct = ((curr_mb - prev_mb) / (2.0 * curr_close) * 100.0) if curr_close > 0 else 0.0

    curr_upper = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else curr_close
    curr_lower = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else curr_close
    prev_upper = float(bb_upper.iloc[-2]) if len(bb_upper) > 1 and not pd.isna(bb_upper.iloc[-2]) else curr_upper
    prev_lower = float(bb_lower.iloc[-2]) if len(bb_lower) > 1 and not pd.isna(bb_lower.iloc[-2]) else curr_lower
    
    bandwidth_pct = float(bb_width.iloc[-1] * 100.0) if not pd.isna(bb_width.iloc[-1]) else 0.0
    prev_bandwidth = float(bb_width.iloc[-2] * 100.0) if len(bb_width) > 1 and not pd.isna(bb_width.iloc[-2]) else bandwidth_pct

    # Direction: UPWARD, DOWNWARD, HORIZONTAL
    if mb_slope_pct > 0.015:
        bb_direction = "UPWARD"
    elif mb_slope_pct < -0.015:
        bb_direction = "DOWNWARD"
    else:
        bb_direction = "HORIZONTAL"

    # Opening / Expansion check: bands widening outward
    is_opening = bool(bandwidth_pct > prev_bandwidth and (curr_upper > prev_upper or curr_lower < prev_lower))

    # Fluid Regime State
    if is_opening and bb_direction == "UPWARD":
        bb_state = "EXPANDING_UP"
    elif is_opening and bb_direction == "DOWNWARD":
        bb_state = "EXPANDING_DOWN"
    elif bandwidth_pct >= 0.50:
        bb_state = "WIDE_RANGE"
    elif bandwidth_pct < 0.25:
        bb_state = "PINCHED_COMPRESSION"
    else:
        bb_state = "NORMAL_RANGE"

    return {
        "bb_middle": round(curr_mb, 2),
        "bb_upper": round(curr_upper, 2),
        "bb_lower": round(curr_lower, 2),
        "bb_mb_slope": round(mb_slope_pct, 4),
        "bb_bandwidth_pct": round(bandwidth_pct, 3),
        "bb_is_opening": is_opening,
        "bb_direction": bb_direction,
        "bb_state": bb_state,
        "bb_upper_series": bb_upper,
        "bb_lower_series": bb_lower,
        "sma_bb_series": sma_bb,
    }

def calc_squeeze_fsm(df: pd.DataFrame, bb_period: int, bb_std: float, loaded_bars_threshold: int) -> Tuple[str, str, pd.Series, pd.Series]:
    """
    5-State Volatility Squeeze Finite State Machine:
    Tracks Bollinger Bands compressing inside Keltner Channels.
    - IDLE: BB >= KC
    - BUILDING: BB < KC for 1 to (threshold-1) bars
    - LOADED: BB < KC sustained for >= threshold bars (Energy Loaded)
    - FIRING: First bar where BB expands outside KC after a squeeze
    - TRENDING: BB expands outside KC and bandwidth > 20-bar SMA of bandwidth
    """
    close = df["close"]
    sma_bb = close.rolling(window=bb_period).mean()
    std_bb = close.rolling(window=bb_period).std()
    bb_upper = sma_bb + (bb_std * std_bb)
    bb_lower = sma_bb - (bb_std * std_bb)
    bb_width = (bb_upper - bb_lower) / sma_bb.replace(0, np.nan)
    
    atr = calc_atr(df, 14)
    kc_mid = close.ewm(span=20, adjust=False).mean()
    kc_upper = kc_mid + (KC_ATR_MULTIPLIER * atr)
    kc_lower = kc_mid - (KC_ATR_MULTIPLIER * atr)
    
    # Squeeze condition: BB is entirely inside KC
    is_in_squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    
    # State tracking across bars
    squeeze_counts = []
    current_count = 0
    for sq in is_in_squeeze:
        if sq:
            current_count += 1
        else:
            current_count = 0
        squeeze_counts.append(current_count)
    
    squeeze_series = pd.Series(squeeze_counts, index=df.index)
    width_sma20 = bb_width.rolling(20).mean()
    
    # Evaluate current bar
    curr_sq = is_in_squeeze.iloc[-1]
    curr_count = squeeze_series.iloc[-1]
    prev_count = squeeze_series.iloc[-2] if len(squeeze_series) > 1 else 0
    curr_width = bb_width.iloc[-1]
    curr_width_sma = width_sma20.iloc[-1] if not pd.isna(width_sma20.iloc[-1]) else curr_width
    
    if curr_sq:
        if curr_count >= loaded_bars_threshold:
            state = "LOADED"
            badge = "🟡 SQUEEZE LOADED — WATCH FOR BREAK"
        else:
            state = "BUILDING"
            badge = "⚪ SQUEEZE BUILDING"
    else:
        # Not in squeeze now
        if prev_count >= loaded_bars_threshold:
            state = "FIRING"
            badge = "🔴 SQUEEZE FIRING — BREAKOUT ACTIVE"
        elif curr_width > curr_width_sma * 1.05 and prev_count > 0:
            state = "TRENDING"
            badge = "🟢 POST-SQUEEZE TREND — TRAIL STOP"
        else:
            state = "IDLE"
            badge = "NORMAL VOLATILITY"
            
    return state, badge, bb_upper, bb_lower

class StatisticalBrain:
    """Evaluates %B boundaries, Bollinger envelope elasticity, and regime-aware support/resistance."""
    @staticmethod
    def evaluate(close: float, bb_upper: float, bb_lower: float, macro_regime: str) -> Dict[str, Any]:
        span = bb_upper - bb_lower
        pct_b = (close - bb_lower) / span if span > 0 else 0.5
        pct_b = max(0.0, min(1.0, pct_b))
        
        # Baseline scores strictly based on local %B envelope
        bull_score = 0.50 + (0.50 - pct_b) * 0.7
        bear_score = 0.50 + (pct_b - 0.50) * 0.7
        regime_note = "Local %B Envelope"
        
        # Soft macro context advisory (zero hard veto)
        if macro_regime == "Trend Down":
            if pct_b >= 0.60:
                bear_score += 0.08
                bull_score -= 0.08
                regime_note = "Local Ceiling (4H Downtrend context)"
            elif pct_b <= 0.20:
                bull_score += 0.08
                bear_score -= 0.08
                regime_note = "Local Oversold Wick Support"
        elif macro_regime == "Trend Up":
            if pct_b <= 0.40:
                bull_score += 0.08
                bear_score -= 0.08
                regime_note = "Local Dip Support (4H Uptrend context)"
            elif pct_b >= 0.80:
                regime_note = "Local Upper Expansion"
                
        return {
            "bull_score": round(float(max(0.05, min(0.95, bull_score))), 4),
            "bear_score": round(float(max(0.05, min(0.95, bear_score))), 4),
            "pct_b": round(float(pct_b), 4),
            "bb_upper": round(float(bb_upper), 2),
            "bb_lower": round(float(bb_lower), 2),
            "regime_note": regime_note,
        }

class MomentumBrain:
    """Evaluates dynamic multi-scale RSI, EMA trend alignment, and smoothed MACD histogram slope."""
    @staticmethod
    def evaluate(df: pd.DataFrame, rsi_periods: Tuple[int, int, int], fast_ema_period: int, slow_ema_period: int,
                 macd_fast: int, macd_slow: int, macd_signal: int) -> Dict[str, Any]:
        close = df["close"]
        
        # 1. Multi-scale RSI
        rsi_fast = calc_wilder_rsi(close, rsi_periods[0]).iloc[-1]
        rsi_mid = calc_wilder_rsi(close, rsi_periods[1]).iloc[-1]
        rsi_slow = calc_wilder_rsi(close, rsi_periods[2]).iloc[-1]
        
        # 2. Dual EMAs
        fast_ema = close.ewm(span=fast_ema_period, adjust=False).mean()
        slow_ema = close.ewm(span=slow_ema_period, adjust=False).mean()
        curr_fast_ema = fast_ema.iloc[-1]
        curr_slow_ema = slow_ema.iloc[-1]
        curr_close = close.iloc[-1]
        
        # 3. MACD
        ema_m_fast = close.ewm(span=macd_fast, adjust=False).mean()
        ema_m_slow = close.ewm(span=macd_slow, adjust=False).mean()
        macd_line = ema_m_fast - ema_m_slow
        signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        curr_hist = macd_hist.iloc[-1]
        # 2-bar smoothed derivative: (hist_t - hist_{t-2}) / 2.0
        prev_hist_2 = macd_hist.iloc[-3] if len(macd_hist) >= 3 else macd_hist.iloc[-2]
        smooth_slope = (curr_hist - prev_hist_2) / 2.0
        
        # Scoring synthesis
        bull_points = 0.0
        bear_points = 0.0
        
        # RSI points (0-30 points)
        if rsi_fast > 50 and rsi_mid > 50:
            bull_points += 0.15
        elif rsi_fast < 50 and rsi_mid < 50:
            bear_points += 0.15
            
        if rsi_fast < 30:
            bull_points += 0.15 # Oversold bounce potential
        elif rsi_fast > 70:
            bear_points += 0.15 # Overbought fade potential
            
        # EMA trend points (0-35 points)
        if curr_close > curr_fast_ema > curr_slow_ema:
            bull_points += 0.35
        elif curr_close < curr_fast_ema < curr_slow_ema:
            bear_points += 0.35
        elif curr_fast_ema > curr_slow_ema:
            bull_points += 0.15
        else:
            bear_points += 0.15
            
        # MACD momentum slope (0-35 points)
        if smooth_slope > 0:
            bull_points += min(0.35, 0.15 + (abs(smooth_slope) / (curr_close * 0.001 + 1e-5)) * 0.1)
        else:
            bear_points += min(0.35, 0.15 + (abs(smooth_slope) / (curr_close * 0.001 + 1e-5)) * 0.1)
            
        total = bull_points + bear_points
        norm_bull = bull_points / total if total > 0 else 0.5
        norm_bear = bear_points / total if total > 0 else 0.5
        
        return {
            "bull_score": float(norm_bull),
            "bear_score": float(norm_bear),
            "rsi_fast": round(float(rsi_fast), 2),
            "rsi_mid": round(float(rsi_mid), 2),
            "rsi_slow": round(float(rsi_slow), 2),
            "fast_ema": round(float(curr_fast_ema), 2),
            "slow_ema": round(float(curr_slow_ema), 2),
            "macd_hist": round(float(curr_hist), 2),
            "smooth_slope": round(float(smooth_slope), 4),
            "is_accelerating": bool(smooth_slope > 0),
        }

class VolatilityBrain:
    """Evaluates ATR expansion, Keltner squeeze state, and breakout potential."""
    @staticmethod
    def evaluate(df: pd.DataFrame, bb_period: int, bb_std: float, loaded_threshold: int) -> Dict[str, Any]:
        atr_series = calc_atr(df, 14)
        curr_atr = float(atr_series.iloc[-1])
        curr_close = float(df["close"].iloc[-1])
        atr_pct = (curr_atr / curr_close * 100) if curr_close > 0 else 0.0
        
        boll_metrics = calc_bollinger_metrics(df, bb_period, bb_std)
        state, badge, bb_upper, bb_lower = calc_squeeze_fsm(df, bb_period, bb_std, loaded_threshold)
        
        # 100-bar ATR percentile rank (volatility regime)
        rolling_atr_window = atr_series.tail(100)
        rank = float((rolling_atr_window < curr_atr).sum() / len(rolling_atr_window)) if len(rolling_atr_window) > 0 else 0.5
        
        return {
            "atr": round(curr_atr, 2),
            "atr_pct": round(float(atr_pct), 3),
            "squeeze_state": str(state),
            "squeeze_badge": str(badge),
            "volatility_regime_rank": round(rank, 4),
            "is_loaded_or_firing": bool(state in ["LOADED", "FIRING"]),
            "bb_upper": boll_metrics["bb_upper"],
            "bb_lower": boll_metrics["bb_lower"],
            "bb_middle": boll_metrics["bb_middle"],
            "bb_mb_slope": boll_metrics["bb_mb_slope"],
            "bb_bandwidth_pct": boll_metrics["bb_bandwidth_pct"],
            "bb_is_opening": boll_metrics["bb_is_opening"],
            "bb_direction": boll_metrics["bb_direction"],
            "bb_state": boll_metrics["bb_state"],
        }

def evaluate_tri_brain_ensemble(df: pd.DataFrame, timeframe: str, macro_regime: str = "Range") -> Dict[str, Any]:
    """
    Executes the Tri-Brain ensemble with 9-timeframe scaled parameters:
    1. StatisticalBrain
    2. MomentumBrain
    3. VolatilityBrain
    """
    cfg = TIMEFRAME_PARAMETERS.get(timeframe, TIMEFRAME_PARAMETERS["1h"])
    
    # Run VolatilityBrain first to get BB and Squeeze
    vol_out = VolatilityBrain.evaluate(df, cfg["bb_period"], cfg["bb_std"], cfg["squeeze_loaded_bars"])
    
    # Run StatisticalBrain with BB levels and macro regime
    stat_out = StatisticalBrain.evaluate(df["close"].iloc[-1], vol_out["bb_upper"], vol_out["bb_lower"], macro_regime)
    
    # Run MomentumBrain with scaled RSI, EMA, MACD
    mom_out = MomentumBrain.evaluate(
        df,
        cfg["rsi_periods"],
        cfg["fast_ema"],
        cfg["slow_ema"],
        cfg["macd_fast"],
        cfg["macd_slow"],
        cfg["macd_signal"]
    )
    
    # Brain composite score
    composite_bull = (0.35 * stat_out["bull_score"] + 0.45 * mom_out["bull_score"] + 0.20 * (0.6 if vol_out["is_loaded_or_firing"] else 0.5))
    composite_bear = (0.35 * stat_out["bear_score"] + 0.45 * mom_out["bear_score"] + 0.20 * (0.6 if vol_out["is_loaded_or_firing"] else 0.5))
    
    return {
        "timeframe": timeframe,
        "statistical": stat_out,
        "momentum": mom_out,
        "volatility": vol_out,
        "composite_bull": round(composite_bull, 4),
        "composite_bear": round(composite_bear, 4),
    }
