"""
btctool 3.0 - Level 4 Scenario Decision Matrix & 4-Pillars Confluence Engine
Includes:
1. 4-Pillar Cross-Verification (Tape, Structure, Momentum, Derivatives)
2. Hierarchical Expected Volatility Radar (1W, 1D, 4H Strategic Roadmaps)
3. Tactical Sniper Execution Directives (1M, 5M, 15M, 30M, 1H)
"""

import math
from typing import Dict, Any, List, Tuple
from backend.config import TIMEFRAME_PARAMETERS

def evaluate_4_pillars(
    timeframe: str,
    ob_data: Dict[str, Any],
    deriv_data: Dict[str, Any],
    pct_b: float,
    mom_data: Dict[str, Any],
    pre_filter: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates market confirmation across 4 independent quantitative pillars:
    - Pillar 1: Tape & Order Book Flow (L2 Imbalance + Taker Delta)
    - Pillar 2: Price Action & Structure (%B location + Envelope wicks)
    - Pillar 3: Momentum Reality (Multi-scale RSI + Smoothed MACD derivative)
    - Pillar 4: Institutional Derivatives (Funding rate + OI Z-score)
    """
    imbalance = ob_data.get("imbalance_ratio", 0.0)
    taker_delta = deriv_data.get("taker_delta", 0.0)
    smooth_slope = mom_data.get("smooth_slope", 0.0)
    rsi_fast = mom_data.get("rsi_fast", 50.0)
    oi_zscore = deriv_data.get("oi_zscore", 0.0)
    funding = deriv_data.get("funding_rate", 0.0001)

    # -------------------------------------------------------------
    # Pillar 1: Tape & Order Book Flow
    # -------------------------------------------------------------
    # Weighted flow: combination of L2 depth and actual executed market taker trades
    flow_score = 0.5 * imbalance + 0.5 * taker_delta
    if flow_score >= 0.15:
        p1_state = "BULL"
        p1_note = f"Active Bid Support & Inflow (+{round(flow_score * 100)}%)"
    elif flow_score <= -0.15:
        p1_state = "BEAR"
        p1_note = f"Overhead Ask Walls & Outflow ({round(flow_score * 100)}%)"
    else:
        p1_state = "NEUTRAL"
        p1_note = "Balanced Book & Neutral Tape"

    # -------------------------------------------------------------
    # Pillar 2: Price Action & Structure
    # -------------------------------------------------------------
    if pct_b <= 0.28:
        p2_state = "BULL"
        p2_note = f"Lower Band Wick Support Absorption (%B={round(pct_b, 2)})"
    elif pct_b >= 0.72:
        p2_state = "BEAR"
        p2_note = f"Upper Band Resistance Ceiling (%B={round(pct_b, 2)})"
    else:
        p2_state = "NEUTRAL"
        p2_note = f"Mid-Range Equilibrium (%B={round(pct_b, 2)})"

    # -------------------------------------------------------------
    # Pillar 3: Momentum Reality
    # -------------------------------------------------------------
    if smooth_slope > 0 and rsi_fast >= 45:
        p3_state = "BULL"
        p3_note = f"Accelerating Upward (Slope +{round(smooth_slope, 3)}, RSI {round(rsi_fast, 1)})"
    elif smooth_slope < 0 and rsi_fast <= 55:
        p3_state = "BEAR"
        p3_note = f"Decelerating Downward (Slope {round(smooth_slope, 3)}, RSI {round(rsi_fast, 1)})"
    else:
        p3_state = "NEUTRAL"
        p3_note = f"Momentum Flat (Slope {round(smooth_slope, 3)})"

    # -------------------------------------------------------------
    # Pillar 4: Institutional Derivatives & OI
    # -------------------------------------------------------------
    if oi_zscore > 0.5 and funding <= 0.0003:
        p4_state = "BULL"
        p4_note = f"Expanding Open Interest (Z=+{round(oi_zscore, 1)}) with Clean Funding"
    elif oi_zscore < -1.5 or funding > 0.0004:
        p4_state = "BEAR"
        p4_note = "Derivatives Overheated or Liquidation Outflow"
    else:
        p4_state = "NEUTRAL"
        p4_note = "Normal Derivatives Flow"

    pillars = [p1_state, p2_state, p3_state, p4_state]
    bull_count = pillars.count("BULL")
    bear_count = pillars.count("BEAR")
    neutral_count = pillars.count("NEUTRAL")

    # Timeframe-scaled confirmation threshold:
    # 1M/5M: requires >= 2 confirming pillars
    # 15M/1H+: requires >= 3 confirming pillars
    required_confluence = 2 if timeframe in ["1m", "5m"] else 3
    has_bull_confluence = (bull_count >= required_confluence)
    has_bear_confluence = (bear_count >= required_confluence)

    return {
        "p1_tape": {"state": p1_state, "note": p1_note},
        "p2_structure": {"state": p2_state, "note": p2_note},
        "p3_momentum": {"state": p3_state, "note": p3_note},
        "p4_derivatives": {"state": p4_state, "note": p4_note},
        "bull_count": bull_count,
        "bear_count": bear_count,
        "neutral_count": neutral_count,
        "has_bull_confluence": has_bull_confluence,
        "has_bear_confluence": has_bear_confluence,
        "confluence_summary": f"{bull_count} Bull / {bear_count} Bear / {neutral_count} Neutral"
    }

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
    is_accelerating: bool,
    mom_data: Dict[str, Any] = None,
    deriv_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Computes trade directives using:
    1. 4-Pillar Confluence (prevents single-trade tape blips from flipping directives).
    2. Hierarchical Volatility Roadmap for Macro/Swing TFs (1W, 1D, 4H).
    3. Direct Sniper Action Directives for Tactical TFs (1M, 5M, 15M, 30M, 1H).
    """
    cfg = TIMEFRAME_PARAMETERS.get(timeframe, TIMEFRAME_PARAMETERS["1h"])
    atr_mult = cfg["atr_multiplier"]
    mom_data = mom_data or {"smooth_slope": 0.0, "rsi_fast": 50.0}
    deriv_data = deriv_data or {"taker_delta": 0.0, "oi_zscore": 0.0, "funding_rate": 0.0001}

    # Evaluate 4 Pillars
    pillars = evaluate_4_pillars(timeframe, ob_data, deriv_data, pct_b, mom_data, pre_filter)
    
    # ------------------------------------------------------------------
    # BRANCH A: MACRO ROADMAP TIMEFRAMES (1W, 1D, 4H)
    # Expected Volatility Forecasts & Strategic Trading Corridors
    # ------------------------------------------------------------------
    if timeframe in ["4h", "8h", "1d", "1w"]:
        if timeframe == "1w":
            forecast_period = "next 24h daily trading"
            expected_vol_pct = round(max(2.2, min(4.5, (atr / current_price * 100) * 0.40)), 1)
            vol_dollars = round(current_price * (expected_vol_pct / 100.0), 0)
            corridor_floor = round(current_price - 1.2 * atr, 0)
            corridor_roof = round(current_price + 1.2 * atr, 0)
            
            if pillars["has_bull_confluence"]:
                action = "WEEKLY ROADMAP: MACRO ACCUMULATION ZONE (BULLISH OUTLOOK)"
                action_type = "BUY"
            elif pillars["has_bear_confluence"]:
                action = "WEEKLY ROADMAP: DEFENSIVE REGIME / HEDGE EXPOSURE"
                action_type = "SELL_LIMIT"
            else:
                action = "WEEKLY ROADMAP: RANGE BOUND EXPANSION COMPASS"
                action_type = "NEUTRAL"
                
            scenario_name = f"Weekly Volatility Forecast: Expect ±{expected_vol_pct}% (±${int(vol_dollars)}) daily range"

        elif timeframe == "1d":
            forecast_period = "next 4h–8h session"
            expected_vol_pct = round(max(1.2, min(2.8, (atr / current_price * 100) * 0.50)), 1)
            vol_dollars = round(current_price * (expected_vol_pct / 100.0), 0)
            corridor_floor = round(current_price - 0.8 * atr, 0)
            corridor_roof = round(current_price + 0.8 * atr, 0)
            
            if pillars["has_bull_confluence"]:
                action = "DAILY STRATEGY: ACCUMULATE ON DIP TO SUPPORT"
                action_type = "BUY_LIMIT"
            elif pillars["has_bear_confluence"]:
                action = "DAILY STRATEGY: RANGE DEFENSE / FADE RESISTANCE"
                action_type = "SELL_LIMIT"
            else:
                action = "DAILY STRATEGY: INTRADAY PING-PONG RADAR"
                action_type = "NEUTRAL"
                
            scenario_name = f"Daily Session Forecast: Expect ±{expected_vol_pct}% (±${int(vol_dollars)}) in next 4h–8h"

        else: # 4h / 8h
            forecast_period = "next 1h–2h move"
            expected_vol_pct = round(max(0.6, min(1.8, (atr / current_price * 100) * 0.55)), 1)
            vol_dollars = round(current_price * (expected_vol_pct / 100.0), 0)
            corridor_floor = round(current_price - 0.6 * atr, 0)
            corridor_roof = round(current_price + 0.6 * atr, 0)
            
            if pillars["has_bull_confluence"]:
                action = "4H SWING SETUP: BULLISH SQUEEZE EXPANSION"
                action_type = "BUY"
            elif pillars["has_bear_confluence"]:
                action = "4H SWING SETUP: BEARISH BREAKDOWN WATCH"
                action_type = "SHORT"
            else:
                action = "4H SWING SETUP: SQUEEZE ENERGY BUILDING"
                action_type = "NEUTRAL"
                
            scenario_name = f"4H Wave Forecast: Expect ±{expected_vol_pct}% (±${int(vol_dollars)}) in next 1h–2h"

        return {
            "scenario": scenario_name,
            "action": action,
            "action_type": action_type,
            "is_roadmap": True,
            "expected_vol_pct": expected_vol_pct,
            "expected_vol_dollars": vol_dollars,
            "forecast_period": forecast_period,
            "corridor_floor": corridor_floor,
            "corridor_roof": corridor_roof,
            "long_entry_trigger": corridor_floor,
            "short_entry_trigger": corridor_roof,
            "stop_loss": round(corridor_floor * 0.98 if action_type == "BUY" else corridor_roof * 1.02, 2),
            "target_1": corridor_roof if action_type == "BUY" else corridor_floor,
            "target_2": round(corridor_roof * 1.02 if action_type == "BUY" else corridor_floor * 0.98, 2),
            "risk_reward_ratio": "Roadmap Corridor",
            "gain_pct": expected_vol_pct,
            "max_runner_pct": round(expected_vol_pct * 1.8, 1),
            "atr_stop_multiple": f"Corridor [${corridor_floor:,.0f} ── ${corridor_roof:,.0f}]",
            "four_pillars": pillars
        }

    # ------------------------------------------------------------------
    # BRANCH B: TACTICAL SNIPER EXECUTION DIRECTIVES (1M, 5M, 15M, 30M, 1H)
    # Direct orders: ENTER NOW / SET LIMIT with fee-clearing profit floors
    # ------------------------------------------------------------------
    min_gain_pct = 0.25 if timeframe in ["1m", "5m"] else (0.40 if timeframe in ["15m", "30m"] else 0.60)
    min_floor_dollars = (min_gain_pct / 100.0) * current_price

    # Stop distance with ATR and risk floor
    raw_stop = atr_mult * atr
    stop_dist = max(round(raw_stop, 2), round(min_floor_dollars * 0.70, 2))

    # Targets: scales dynamically with ATR in expansion, protected by floor in compression
    raw_tp1 = 0.75 * atr_mult * atr
    tp1_dist = max(round(raw_tp1, 2), round(min_floor_dollars, 2))
    raw_tp2 = 2.0 * atr_mult * atr
    tp2_dist = max(round(raw_tp2, 2), round(tp1_dist * 2.2, 2))

    if pre_filter.get("tighten_targets", False):
        tp1_dist = round(tp1_dist * 0.80, 2)
        tp2_dist = round(tp2_dist * 0.80, 2)

    suppress_long = pre_filter.get("suppress_market_long", False)
    suppress_short = pre_filter.get("suppress_market_short", False)

    # 4-Pillar Confluence Rule:
    # Requires >= 2 (for 1m/5m) or >= 3 (for 15m/1h) confirming pillars
    if pillars["has_bull_confluence"] and not suppress_long:
        scenario_name = f"Confluence Confirmed: {pillars['confluence_summary']} Bullish"
        if macro_regime == "Trend Down":
            action = "COUNTER-TREND SCALP: ENTER LONG NOW" if is_accelerating else "COUNTER-TREND SCALP: SET BUY LIMIT"
        else:
            action = "TREND EXPANSION: ENTER LONG NOW" if is_accelerating else "TREND FOLLOWING: SET BUY LIMIT AT SUPPORT"
            
        action_type = "BUY"
        long_entry = current_price
        short_entry = round(current_price - 1.5 * stop_dist, 2)
        stop_loss = round(long_entry - stop_dist, 2)
        target_1 = round(long_entry + tp1_dist, 2)
        target_2 = round(long_entry + tp2_dist, 2)

    elif pillars["has_bear_confluence"] and not suppress_short:
        scenario_name = f"Confluence Confirmed: {pillars['confluence_summary']} Bearish"
        if is_accelerating:
            action = "ENTER SHORT ON RETEST CEILING"
            action_type = "SELL_LIMIT"
            short_entry = round(current_price + 0.3 * stop_dist, 2)
            long_entry = round(current_price - 1.2 * stop_dist, 2)
        else:
            action = "TREND CONTINUATION: ENTER SHORT NOW"
            action_type = "SHORT"
            short_entry = current_price
            long_entry = round(current_price + 1.5 * stop_dist, 2)
            
        stop_loss = round(short_entry + stop_dist, 2)
        target_1 = round(short_entry - tp1_dist, 2)
        target_2 = round(short_entry - tp2_dist, 2)

    # If only 1 pillar blipped without confluence: Hold range boundaries
    else:
        scenario_name = f"Neutral Consolidation (Pillars: {pillars['confluence_summary']})"
        if prob_up >= prob_down and not suppress_long:
            action = "RANGE SETUP: SET BUY LIMIT ORDER"
            action_type = "BUY_LIMIT"
            long_entry = round(current_price - 0.4 * stop_dist, 2)
            short_entry = round(current_price + 0.8 * stop_dist, 2)
            stop_loss = round(long_entry - stop_dist, 2)
            target_1 = round(long_entry + tp1_dist, 2)
            target_2 = round(long_entry + tp2_dist, 2)
        else:
            action = "RANGE SETUP: SET SELL LIMIT ORDER"
            action_type = "SELL_LIMIT"
            long_entry = round(current_price - 0.8 * stop_dist, 2)
            short_entry = round(current_price + 0.4 * stop_dist, 2)
            stop_loss = round(short_entry + stop_dist, 2)
            target_1 = round(short_entry - tp1_dist, 2)
            target_2 = round(short_entry - tp2_dist, 2)

    # Anti-Collision Guard
    if abs(long_entry - short_entry) < (0.1 * atr):
        if action_type in ["BUY", "BUY_LIMIT"]:
            short_entry = round(long_entry - 1.5 * stop_dist, 2)
        else:
            long_entry = round(short_entry + 1.5 * stop_dist, 2)

    risk_dollars = abs(current_price - stop_loss)
    reward_dollars = abs(target_1 - current_price)
    rr_ratio = round(reward_dollars / risk_dollars, 2) if risk_dollars > 0 else 1.5
    gain_pct = round((abs(target_1 - current_price) / current_price) * 100, 2)
    max_runner_pct = round((abs(target_2 - current_price) / current_price) * 100, 2)

    return {
        "scenario": scenario_name,
        "action": action,
        "action_type": action_type,
        "is_roadmap": False,
        "long_entry_trigger": long_entry,
        "short_entry_trigger": short_entry,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "risk_reward_ratio": f"{rr_ratio}:1",
        "gain_pct": gain_pct,
        "max_runner_pct": max_runner_pct,
        "atr_stop_multiple": f"{atr_mult}x ATR (${stop_dist:,.2f})",
        "four_pillars": pillars
    }

def calculate_cross_timeframe_alignment(summaries_by_tf: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Inspects all 9 timeframes to compute systemic confluence score."""
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
