"""
btctool 3.0 - Level 4 Scenario Decision Matrix (5 Scenarios, Pure ATR, Anti-Collision)
"""

import math
from typing import Dict, Any, List
from backend.config import TIMEFRAME_PARAMETERS

def compute_trade_plan(
    current_price: float,
    atr: float,
    timeframe: str,
    macro_regime: str,
    squeeze_state: str,
    prob_up: float,
    prob_down: float,
    pct_b: float,
    ob_data: Dict[str, Any],
    pre_filter: Dict[str, Any],
    is_accelerating: bool
) -> Dict[str, Any]:
    """
    Computes professional trade directives, entries, stops, and dynamic targets.
    Guarantees:
    1. Zero collision: Long and Short triggers are NEVER identical.
    2. Zero dollar amounts: All stops and targets are computed strictly in ATR multiples.
    3. No passive 'WAIT': Always generates actionable human-hedge-fund directives.
    """
    cfg = TIMEFRAME_PARAMETERS.get(timeframe, TIMEFRAME_PARAMETERS["1h"])
    atr_mult = cfg["atr_multiplier"]
    
    stop_dist = round(atr_mult * atr, 2)
    tp1_dist = round(0.75 * atr_mult * atr, 2)
    tp2_dist = round(2.0 * atr_mult * atr, 2)
    
    # Tighten targets if OI exhaustion is flagged
    if pre_filter.get("tighten_targets", False):
        tp1_dist = round(tp1_dist * 0.75, 2)
        tp2_dist = round(tp2_dist * 0.75, 2)
        
    imbalance = ob_data.get("imbalance_ratio", 0.0)
    suppress_long = pre_filter.get("suppress_market_long", False)
    suppress_short = pre_filter.get("suppress_market_short", False)
    
    # 5 Scenarios Evaluation
    
    # Scenario 1: Downtrend Resistance Fade
    if macro_regime == "Trend Down" and pct_b >= 0.58 and imbalance < -0.10:
        scenario_name = "Scenario 1: Downtrend Resistance Fade"
        action = "SET SELL LIMIT AT RESISTANCE (BEARISH FADE)"
        action_type = "SELL_LIMIT"
        long_entry = round(current_price - 1.2 * stop_dist, 2)
        short_entry = round(current_price + 0.3 * stop_dist, 2)
        stop_loss = round(short_entry + stop_dist, 2)
        target_1 = round(short_entry - tp1_dist, 2)
        target_2 = round(short_entry - tp2_dist, 2)
        
    # Scenario 2: Downtrend Continuation
    elif macro_regime == "Trend Down" and prob_down >= 0.58 and not suppress_short:
        scenario_name = "Scenario 2: Downtrend Continuation"
        action = "TREND CONTINUATION: ENTER SHORT NOW" if is_accelerating else "ENTER SHORT ON RETEST"
        action_type = "SHORT"
        short_entry = current_price
        long_entry = round(current_price + 1.5 * stop_dist, 2) # Breakout invalidation
        stop_loss = round(short_entry + stop_dist, 2)
        target_1 = round(short_entry - tp1_dist, 2)
        target_2 = round(short_entry - tp2_dist, 2)

    # Scenario 3: Bottom Sweep Rebound
    elif (pct_b <= 0.22 or prob_up >= 0.65) and imbalance > 0.10 and not suppress_long:
        scenario_name = "Scenario 3: Bottom Sweep Rebound"
        action = "ENTER LONG NOW (LIQUIDITY RECLAIM)"
        action_type = "BUY"
        long_entry = current_price
        short_entry = round(current_price - 1.5 * stop_dist, 2) # Structural breakdown
        stop_loss = round(long_entry - stop_dist, 2)
        target_1 = round(long_entry + tp1_dist, 2)
        target_2 = round(long_entry + tp2_dist, 2)

    # Scenario 4: Uptrend Dip Buy
    elif macro_regime == "Trend Up" and pct_b <= 0.45:
        scenario_name = "Scenario 4: Uptrend Dip Support"
        action = "TREND FOLLOWING: SET BUY LIMIT AT SUPPORT"
        action_type = "BUY_LIMIT"
        long_entry = round(current_price - 0.4 * stop_dist, 2)
        short_entry = round(current_price - 1.8 * stop_dist, 2)
        stop_loss = round(long_entry - stop_dist, 2)
        target_1 = round(long_entry + tp1_dist, 2)
        target_2 = round(long_entry + tp2_dist, 2)

    # Scenario 5: Range-Bound Consolidation
    else:
        scenario_name = "Scenario 5: Range Consolidation"
        if prob_up > prob_down and not suppress_long:
            action = "RANGE SETUP: SET BUY LIMIT ORDER"
            action_type = "BUY_LIMIT"
            long_entry = round(current_price - 0.5 * stop_dist, 2)
            short_entry = round(current_price + 0.8 * stop_dist, 2)
            stop_loss = round(long_entry - stop_dist, 2)
            target_1 = round(long_entry + tp1_dist, 2)
            target_2 = round(long_entry + tp2_dist, 2)
        else:
            action = "RANGE SETUP: SET SELL LIMIT ORDER"
            action_type = "SELL_LIMIT"
            long_entry = round(current_price - 0.8 * stop_dist, 2)
            short_entry = round(current_price + 0.5 * stop_dist, 2)
            stop_loss = round(short_entry + stop_dist, 2)
            target_1 = round(short_entry - tp1_dist, 2)
            target_2 = round(short_entry - tp2_dist, 2)
            
    # Anti-Collision Guard Verification: Long & Short triggers can NEVER be identical
    if abs(long_entry - short_entry) < (0.1 * atr):
        if action_type in ["BUY", "BUY_LIMIT"]:
            short_entry = round(long_entry - 1.5 * stop_dist, 2)
        else:
            long_entry = round(short_entry + 1.5 * stop_dist, 2)
            
    # Calculate Expected Reward:Risk Ratio
    risk_dollars = abs(current_price - stop_loss)
    reward_dollars = abs(target_1 - current_price)
    rr_ratio = round(reward_dollars / risk_dollars, 2) if risk_dollars > 0 else 1.5

    # Potential Gain Percent
    gain_pct = round((abs(target_1 - current_price) / current_price) * 100, 2)
    max_runner_pct = round((abs(target_2 - current_price) / current_price) * 100, 2)

    return {
        "scenario": scenario_name,
        "action": action,
        "action_type": action_type,
        "long_entry_trigger": long_entry,
        "short_entry_trigger": short_entry,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward_ratio": f"{rr_ratio}:1",
        "gain_pct": gain_pct,
        "max_runner_pct": max_runner_pct,
        "atr_stop_multiple": f"{atr_mult}x ATR (${stop_dist})",
    }

def calculate_cross_timeframe_alignment(summaries_by_tf: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Cross-Timeframe Alignment Score (New Merged Feature):
    Inspects all 9 timeframes to compute systemic confluence:
    - 7 to 9 aligned: STRONG CONFLUENCE (Full sizing)
    - 5 to 6 aligned: MODERATE SETUP (Reduced sizing)
    - < 5 aligned: CONFLICTED / NO TRADE (Directive suppressed or warning issued)
    """
    long_votes = 0
    short_votes = 0
    total_tfs = len(summaries_by_tf)
    
    for tf, data in summaries_by_tf.items():
        prob_up = data.get("prob_up", 0.5)
        prob_down = data.get("prob_down", 0.5)
        if prob_up >= 0.55:
            long_votes += 1
        elif prob_down >= 0.55:
            short_votes += 1
            
    dominant_direction = "BULLISH" if long_votes > short_votes else ("BEARISH" if short_votes > long_votes else "NEUTRAL")
    dominant_count = max(long_votes, short_votes)
    
    if dominant_count >= 7:
        status = "STRONG CONFLUENCE"
        directive_mode = "HIGH CONVICTION — FULL SIZING"
        badge = "🟢 7-9 TF ALIGNED"
    elif dominant_count >= 5:
        status = "MODERATE SETUP"
        directive_mode = "MODERATE CONVICTION — REDUCED SIZING"
        badge = "🟡 5-6 TF ALIGNED"
    else:
        status = "CONFLICTED CHOP"
        directive_mode = "CONFLICTED — CAUTION / REDUCE RISK"
        badge = "🔴 <5 TF ALIGNED (NO TRADE / STAND ASIDE)"
        
    return {
        "dominant_direction": dominant_direction,
        "dominant_count": dominant_count,
        "long_votes": long_votes,
        "short_votes": short_votes,
        "total_timeframes": total_tfs,
        "alignment_status": status,
        "directive_mode": directive_mode,
        "badge": badge,
    }
