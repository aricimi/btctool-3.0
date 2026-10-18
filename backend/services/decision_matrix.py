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
    # 1M/3M/5M: requires >= 2 confirming pillars
    # 15M/1H+: requires >= 3 confirming pillars
    required_confluence = 2 if timeframe in ["1m", "3m", "5m"] else 3
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
    deriv_data: Dict[str, Any] = None,
    vol_data: Dict[str, Any] = None,
    higher_tf_context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Computes trade directives using:
    1. 4-Pillar Confluence (prevents single-trade tape blips from flipping directives).
    2. Hierarchical Volatility Roadmap for Macro/Swing TFs (1D, 4H, 8H).
    3. Direct Sniper Action Directives for Tactical TFs (1M, 3M, 5M, 15M, 30M, 1H, 2H).
    """
    cfg = TIMEFRAME_PARAMETERS.get(timeframe, TIMEFRAME_PARAMETERS["1h"])
    atr_mult = cfg["atr_multiplier"]
    mom_data = mom_data or {"smooth_slope": 0.0, "rsi_fast": 50.0}
    deriv_data = deriv_data or {"taker_delta": 0.0, "oi_zscore": 0.0, "funding_rate": 0.0001}

    # Evaluate 4 Pillars
    pillars = evaluate_4_pillars(timeframe, ob_data, deriv_data, pct_b, mom_data, pre_filter)
    
    # ------------------------------------------------------------------
    # BRANCH A: MACRO ROADMAP TIMEFRAMES (1D, 8H, 4H)
    # Expected Volatility Forecasts & Strategic Trading Corridors
    # ------------------------------------------------------------------
    if timeframe in ["4h", "8h", "1d"]:
        if timeframe == "1d":
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
    min_gain_pct = 0.25 if timeframe in ["1m", "3m", "5m"] else (0.40 if timeframe in ["15m", "30m"] else 0.60)
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

    vol_data = vol_data or {}
    higher_tf_context = higher_tf_context or {}

    # Extract higher timeframe (5M, 15M, 30M) Bollinger & momentum context
    context_5m = higher_tf_context.get("5m") or {}
    context_15m = higher_tf_context.get("15m") or {}
    context_30m = higher_tf_context.get("30m") or {}

    ind_5m = context_5m.get("indicators", {})
    vol_5m = context_5m.get("brain_ensemble", {}).get("volatility", {})
    bb_width_5m = ind_5m.get("bb_bandwidth_pct", vol_5m.get("bb_bandwidth_pct", vol_data.get("bb_bandwidth_pct", 0.35)))
    bb_state_5m = ind_5m.get("bb_state", vol_5m.get("bb_state", vol_data.get("bb_state", "NORMAL_RANGE")))
    bb_dir_5m = ind_5m.get("bb_direction", vol_5m.get("bb_direction", vol_data.get("bb_direction", "HORIZONTAL")))
    is_opening_5m = ind_5m.get("bb_is_opening", vol_5m.get("bb_is_opening", False))
    pct_b_5m = ind_5m.get("pct_b", pct_b)

    ind_15m = context_15m.get("indicators", {})
    vol_15m = context_15m.get("brain_ensemble", {}).get("volatility", {})
    bb_state_15m = ind_15m.get("bb_state", vol_15m.get("bb_state", "NORMAL_RANGE"))
    bb_dir_15m = ind_15m.get("bb_direction", vol_15m.get("bb_direction", "HORIZONTAL"))
    is_opening_15m = ind_15m.get("bb_is_opening", vol_15m.get("bb_is_opening", False))

    is_htf_expanding_up = (bb_state_5m == "EXPANDING_UP" or (bb_dir_5m == "UPWARD" and is_opening_5m) or
                           bb_state_15m == "EXPANDING_UP" or (bb_dir_15m == "UPWARD" and is_opening_15m))
    is_htf_expanding_down = (bb_state_5m == "EXPANDING_DOWN" or (bb_dir_5m == "DOWNWARD" and is_opening_5m) or
                             bb_state_15m == "EXPANDING_DOWN" or (bb_dir_15m == "DOWNWARD" and is_opening_15m))

    # Check for Pinched Compression (<0.25% bandwidth without opening)
    is_pinched_chop = False
    if timeframe in ["1m", "3m"]:
        is_pinched_chop = bool((bb_state_5m == "PINCHED_COMPRESSION" or bb_width_5m < 0.25) and not is_opening_5m)
    elif timeframe == "5m":
        cur_bb_w = vol_data.get("bb_bandwidth_pct", 1.0)
        is_pinched_chop = bool((vol_data.get("bb_state") == "PINCHED_COMPRESSION" or cur_bb_w < 0.25) and not vol_data.get("bb_is_opening", False))

    # Check for Wide Range (>= 0.50% bandwidth, horizontal, not opening)
    is_wide_range = False
    if timeframe in ["1m", "3m", "5m"] and bb_width_5m >= 0.50 and bb_dir_5m == "HORIZONTAL" and not is_opening_5m:
        is_wide_range = True

    # -------------------------------------------------------------
    # FLUID TACTICAL STATE MACHINE (1M / 3M / 5M / 15M / 30M / 1H / 2H)
    # -------------------------------------------------------------
    # Branch 1: Pinched Squeeze with No Room (Wait for band expansion)
    if is_pinched_chop:
        w_val = bb_width_5m if timeframe in ["1m", "3m"] else vol_data.get("bb_bandwidth_pct", 0.20)
        scenario_name = f"Choked Bollinger Compression ({w_val}% width): Awaiting Band Opening"
        action = "⏸️ WAIT: 5M BOLLINGER PINCHED (<0.25% SPREAD) — AWAITING BAND EXPANSION" if timeframe in ["1m", "3m"] else "⏸️ WAIT: BOLLINGER PINCHED (<0.25% SPREAD) — AWAITING BAND EXPANSION"
        action_type = "WAIT"
        long_entry = current_price
        short_entry = current_price
        stop_loss = round(current_price - stop_dist, 2)
        target_1 = round(current_price + tp1_dist, 2)
        target_2 = round(current_price + tp2_dist, 2)

    # Branch 2: Higher-Timeframe Directional Breakout/Expansion (Ride the strong momentum)
    elif timeframe in ["1m", "3m"] and is_htf_expanding_up and not suppress_long:
        scenario_name = f"Higher TF Surge: 5M/15M Bollinger Expanding Upward ({pillars['confluence_summary']})"
        action = "TREND EXPANSION: ENTER LONG NOW (5M/15M OPENING NORTH)"
        action_type = "BUY"
        long_entry = current_price
        short_entry = round(current_price - 1.5 * stop_dist, 2)
        stop_loss = round(long_entry - stop_dist, 2)
        target_1 = round(long_entry + tp1_dist, 2)
        target_2 = round(long_entry + tp2_dist, 2)

    elif timeframe in ["1m", "3m"] and is_htf_expanding_down and not suppress_short:
        scenario_name = f"Higher TF Breakdown: 5M/15M Bollinger Expanding Downward ({pillars['confluence_summary']})"
        action = "TREND EXPANSION: ENTER SHORT NOW (5M/15M OPENING SOUTH)"
        action_type = "SHORT"
        short_entry = current_price
        long_entry = round(current_price + 1.5 * stop_dist, 2)
        stop_loss = round(short_entry + stop_dist, 2)
        target_1 = round(short_entry - tp1_dist, 2)
        target_2 = round(short_entry - tp2_dist, 2)

    # Branch 3: Wide Horizontal Range Scalp (>= 0.50% range - don't wait, scalp the extremes)
    elif is_wide_range:
        if pct_b_5m <= 0.35 and not suppress_long:
            scenario_name = f"Wide 5M Channel ({bb_width_5m}% range): Floor Bounce Mean-Reversion"
            action = "WIDE RANGE SCALP: ENTER LONG OFF 5M LOWER SUPPORT"
            action_type = "BUY"
            long_entry = current_price
            short_entry = round(current_price - 1.5 * stop_dist, 2)
            stop_loss = round(current_price - stop_dist, 2)
            target_1 = round(current_price + (tp1_dist * 1.2), 2)
            target_2 = round(current_price + (tp2_dist * 1.5), 2)
        elif pct_b_5m >= 0.65 and not suppress_short:
            scenario_name = f"Wide 5M Channel ({bb_width_5m}% range): Ceiling Fade Mean-Reversion"
            action = "WIDE RANGE SCALP: ENTER SHORT OFF 5M UPPER CEILING"
            action_type = "SHORT"
            short_entry = current_price
            long_entry = round(current_price + 1.5 * stop_dist, 2)
            stop_loss = round(current_price + stop_dist, 2)
            target_1 = round(current_price - (tp1_dist * 1.2), 2)
            target_2 = round(current_price - (tp2_dist * 1.5), 2)
        else:
            scenario_name = f"Wide 5M Channel ({bb_width_5m}% range): Mid-Channel Range Setup"
            if prob_up >= prob_down and not suppress_long:
                action = "WIDE RANGE: SET BUY LIMIT AT 5M SUPPORT FLOOR"
                action_type = "BUY_LIMIT"
                long_entry = round(current_price - 0.5 * stop_dist, 2)
                short_entry = round(current_price + 1.0 * stop_dist, 2)
                stop_loss = round(long_entry - stop_dist, 2)
                target_1 = round(long_entry + tp1_dist, 2)
                target_2 = round(long_entry + tp2_dist, 2)
            else:
                action = "WIDE RANGE: SET SELL LIMIT AT 5M CEILING ROOF"
                action_type = "SELL_LIMIT"
                long_entry = round(current_price - 1.0 * stop_dist, 2)
                short_entry = round(current_price + 0.5 * stop_dist, 2)
                stop_loss = round(short_entry + stop_dist, 2)
                target_1 = round(short_entry - tp1_dist, 2)
                target_2 = round(short_entry - tp2_dist, 2)

    # Branch 4: Standard 4-Pillar Confluence Rule
    elif pillars["has_bull_confluence"] and not suppress_long:
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

    # Branch 5: Neutral Consolidation (hold boundaries)
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
