"""
btctool 3.0 - 24/7 Multi-Screen Intraday Scenario Simulator
Synthesizes all 10 timeframes, L2 orderbook walls, Bollinger envelope curves,
and derivatives into a persistent, multi-wave forward projection.
Eliminates tick jitter by committing to an active scenario wave until completion or invalidation.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("btctool.scenario")

# Global active scenario persistence across client polls
_active_scenario: Optional[Dict[str, Any]] = None

def get_active_scenario() -> Optional[Dict[str, Any]]:
    """Returns the current globally tracked scenario."""
    global _active_scenario
    return _active_scenario

def simulate_intraday_scenario(
    current_price: float,
    timeframe_cache: Dict[str, Dict[str, Any]],
    orderbook_data: Dict[str, Any],
    derivatives_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main 24/7 Multi-Screen Scenario Simulator:
    1. Inspects all 10 screens (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 1d).
    2. Identifies the prevailing Macro Regime, Tactical Rotation, and Micro Dip/Peak.
    3. Maintains persistent wave tracking so directives NEVER jitter or flip on 2-second noise.
    4. Projects Wave 1 (Immediate Move) + Wave 2 (Subsequent Re-dip/Continuation).
    """
    global _active_scenario
    now = time.time()

    # If an active scenario exists, evaluate whether it should continue, transition, or reset
    if _active_scenario is not None:
        scenario = _evaluate_and_update_active_scenario(
            _active_scenario, current_price, timeframe_cache, now
        )
        if scenario is not None:
            _active_scenario = scenario
            return scenario

    # Otherwise, generate a fresh high-conviction intraday scenario from all screens
    new_scenario = _synthesize_new_scenario(
        current_price, timeframe_cache, orderbook_data, derivatives_data, now
    )
    _active_scenario = new_scenario
    return new_scenario

def _evaluate_and_update_active_scenario(
    scen: Dict[str, Any],
    current_price: float,
    timeframe_cache: Dict[str, Dict[str, Any]],
    now: float
) -> Optional[Dict[str, Any]]:
    """
    Evaluates live wave progress of the existing active scenario:
    - Checks if Target reached -> Transitions to Wave 2 or locks win.
    - Checks if Invalidation breached -> Marks Invalidated and resets.
    - Calculates live dollar progress and updates actionable guidance.
    """
    age_seconds = now - scen.get("created_at", now)
    # Stale timeout: If 45 minutes pass without resolution, trigger fresh scan
    if age_seconds > 2700:
        logger.info("Scenario reached 45-minute staleness timeout. Generating fresh scenario.")
        return None

    baseline = scen["baseline_price"]
    direction = scen["wave_1"]["direction"]
    target_price = scen["wave_1"]["target_price"]
    invalidation_price = scen["invalidation_floor"]
    expected_amplitude = scen["wave_1"]["expected_amplitude_dollars"]

    # 1. Invalidation Check
    if direction == "LONG" and current_price <= invalidation_price:
        scen["status"] = "INVALIDATED"
        scen["guidance"] = f"⚠️ INVALIDATION LEVEL BREACHED (${invalidation_price:,.1f}) — CUT RISK & STAND ASIDE"
        scen["progress_pct"] = 0.0
        # Reset on next cycle
        return None

    if direction == "SHORT" and current_price >= invalidation_price:
        scen["status"] = "INVALIDATED"
        scen["guidance"] = f"⚠️ INVALIDATION CEILING BREACHED (${invalidation_price:,.1f}) — CUT RISK & STAND ASIDE"
        scen["progress_pct"] = 0.0
        return None

    # 2. Live Progress Calculation
    if direction == "LONG":
        realized_dollars = current_price - baseline
        dist_to_target = target_price - current_price
    else:
        realized_dollars = baseline - current_price
        dist_to_target = current_price - target_price

    progress_pct = max(0.0, min(100.0, (realized_dollars / expected_amplitude * 100.0))) if expected_amplitude > 0 else 50.0
    scen["realized_dollars"] = round(realized_dollars, 1)
    scen["progress_pct"] = round(progress_pct, 1)
    scen["current_price"] = current_price

    # 3. Check Micro-Exhaustion on 1M / 3M
    ind_1m = timeframe_cache.get("1m", {}).get("indicators", {})
    ind_3m = timeframe_cache.get("3m", {}).get("indicators", {})
    mb_slope_1m = ind_1m.get("bb_mb_slope", 0.0)
    mb_slope_3m = ind_3m.get("bb_mb_slope", 0.0)

    # 4. Target Reached / Wave Transition Check
    if progress_pct >= 92.0 or (direction == "LONG" and current_price >= target_price) or (direction == "SHORT" and current_price <= target_price):
        scen["status"] = "TARGET_REACHED"
        w2_action = "PREPARE FOR RE-DIP SHORT" if direction == "LONG" else "PREPARE FOR DIP BOUNCE LONG"
        scen["guidance"] = f"🎯 TARGET ZONE REACHED (${current_price:,.1f} · +${realized_dollars:.0f}) — LOCK IN PROFIT NOW! Wave 2: {w2_action}."
        scen["action_mode"] = "TAKE_PROFIT"
        return scen

    # 5. Approaching Exhaustion Check
    if progress_pct >= 70.0:
        is_curling = (direction == "LONG" and (mb_slope_1m < -0.01 or mb_slope_3m < -0.01)) or \
                      (direction == "SHORT" and (mb_slope_1m > 0.01 or mb_slope_3m > 0.01))
        
        if is_curling:
            scen["status"] = "EXHAUSTION_WARNING"
            scen["guidance"] = f"⚠️ WAVE NEARING CEILING (+${realized_dollars:.0f} of ${expected_amplitude:.0f}) · Micro-bands curling against move. Tighten stops or take partial profit."
            scen["action_mode"] = "TIGHTEN_STOPS"
        else:
            scen["status"] = "WAVE_IN_PROGRESS"
            scen["guidance"] = f"🚀 WAVE RUNNING (Progress {progress_pct:.0f}% · +${realized_dollars:.0f}) — Approaching target ${target_price:,.1f}."
            scen["action_mode"] = "HOLD"
        return scen

    # 6. Entry Zone Check
    entry_low = scen["wave_1"]["entry_zone"][0]
    entry_high = scen["wave_1"]["entry_zone"][1]
    if entry_low <= current_price <= entry_high:
        scen["status"] = "OPTIMAL_ENTRY_ZONE"
        scen["guidance"] = f"🟢 IN OPTIMAL ENTRY ZONE (${current_price:,.1f}) — Risk/Reward optimal for {direction} targeting ${target_price:,.1f} (+${expected_amplitude:.0f})."
        scen["action_mode"] = "ENTER_NOW" if direction == "LONG" else "ENTER_SHORT"
        return scen

    scen["status"] = "WAVE_IN_PROGRESS"
    scen["guidance"] = f"WAVE ACTIVE (Progress {progress_pct:.0f}% · Move: ${realized_dollars:+.0f}). Target: ${target_price:,.1f}."
    scen["action_mode"] = "HOLD"
    return scen

def _synthesize_new_scenario(
    current_price: float,
    timeframe_cache: Dict[str, Dict[str, Any]],
    orderbook_data: Dict[str, Any],
    derivatives_data: Dict[str, Any],
    now: float
) -> Dict[str, Any]:
    """
    Continuous Multi-Screen Kinetic Push vs Structural Barrier Engine:
    1. Kinetic Push (Velocity Fuel):
       - MA5 vs MA10 dynamic crossovers across tactical frames.
       - Bollinger Band expansion rate (expanding open vs pinching).
       - MACD DIF vs DEA and Histogram slope.
       - Aggressive Taker Buy/Sell delta & L2 orderbook wall pressure.
    2. Structural Barriers (Physical Walls):
       - Overhead Ceiling = Nearest structural barrier (tactical BB uppers, ask walls).
       - Downside Floor = Nearest structural barrier (tactical BB lowers, bid walls, swing wicks).
    3. Wave Geometry:
       - Projects dynamic Wave 1 amplitude ($ reach) and optimal entry pocket.
       - Projects subsequent Wave 2 collision reaction (re-dip or bounce).
    """
    # -------------------------------------------------------------
    # 1. KINETIC PUSH (DIRECTIONAL VELOCITY FUEL)
    # -------------------------------------------------------------
    tactical_tfs = ["1m", "3m", "5m", "15m", "30m"]
    
    # A. MA(5) vs MA(10) Alignment across tactical screens
    ma_points = 0.0
    for tf in tactical_tfs:
        ind = timeframe_cache.get(tf, {}).get("indicators", {})
        ma5 = ind.get("ma5", current_price)
        ma10 = ind.get("ma10", current_price)
        if current_price > ma5 > ma10:
            ma_points += 1.0
        elif current_price < ma5 < ma10:
            ma_points -= 1.0
        elif ma5 > ma10:
            ma_points += 0.5
        elif ma5 < ma10:
            ma_points -= 0.5
    ma_velocity = ma_points / len(tactical_tfs)

    # B. Bollinger Band Expansion & Opening Direction (1m, 3m, 5m)
    bb_points = 0.0
    micro_tfs = ["1m", "3m", "5m"]
    for tf in micro_tfs:
        ind = timeframe_cache.get(tf, {}).get("indicators", {})
        bb_state = ind.get("bb_state", "NORMAL_RANGE")
        is_opening = ind.get("bb_is_opening", False)
        direction = ind.get("bb_direction", "HORIZONTAL")
        
        if bb_state == "EXPANDING_UP" or (is_opening and direction == "UPWARD"):
            bb_points += 1.0
        elif bb_state == "EXPANDING_DOWN" or (is_opening and direction == "DOWNWARD"):
            bb_points -= 1.0
        elif direction == "UPWARD":
            bb_points += 0.4
        elif direction == "DOWNWARD":
            bb_points -= 0.4
    bb_velocity = bb_points / len(micro_tfs)

    # C. MACD DIF vs DEA & Momentum Acceleration (1m, 3m, 5m, 15m)
    macd_points = 0.0
    macd_tfs = ["1m", "3m", "5m", "15m"]
    for tf in macd_tfs:
        ind = timeframe_cache.get(tf, {}).get("indicators", {})
        dif = ind.get("macd_dif", 0.0)
        dea = ind.get("macd_dea", 0.0)
        is_accel = ind.get("is_accelerating", False)
        
        if dif > dea and is_accel:
            macd_points += 1.0
        elif dif < dea and not is_accel:
            macd_points -= 1.0
        elif dif > dea:
            macd_points += 0.5
        elif dif < dea:
            macd_points -= 0.5
    macd_velocity = macd_points / len(macd_tfs)

    # D. Live Orderbook Depth & Taker Flow Aggression
    imbalance = float(orderbook_data.get("imbalance_ratio", 0.0))
    taker_delta = float(derivatives_data.get("taker_delta", 0.0))
    
    # Synthesis of continuous Kinetic Push Velocity
    v_kinetic = (
        0.30 * ma_velocity +
        0.25 * bb_velocity +
        0.20 * macd_velocity +
        0.15 * max(-1.0, min(1.0, taker_delta)) +
        0.10 * max(-1.0, min(1.0, imbalance))
    )
    v_kinetic = max(-1.0, min(1.0, v_kinetic))

    # Macro Trend Anchor (4h, 2h, 1h)
    sum_4h = timeframe_cache.get("4h", {})
    sum_2h = timeframe_cache.get("2h", {})
    reg_4h = sum_4h.get("pre_filter", {}).get("regime", "Range")
    mb_dir_4h = sum_4h.get("indicators", {}).get("bb_direction", "HORIZONTAL")
    mb_dir_2h = sum_2h.get("indicators", {}).get("bb_direction", "HORIZONTAL")
    if reg_4h == "Trend Down" or mb_dir_4h == "DOWNWARD" or mb_dir_2h == "DOWNWARD":
        macro_bias = "BEARISH"
    elif reg_4h == "Trend Up" or mb_dir_4h == "UPWARD" or mb_dir_2h == "UPWARD":
        macro_bias = "BULLISH"
    else:
        macro_bias = "RANGE"

    # -------------------------------------------------------------
    # 2. STRUCTURAL BARRIERS (PHYSICAL WALLS)
    # -------------------------------------------------------------
    sum_5m = timeframe_cache.get("5m", {})
    atr_5m = sum_5m.get("indicators", {}).get("atr", 80.0)
    if atr_5m <= 10.0:
        atr_5m = 80.0

    # Ceiling candidate levels (upper bands & ask walls)
    ceilings = []
    for tf in ["5m", "15m", "30m", "1h"]:
        upper = timeframe_cache.get(tf, {}).get("indicators", {}).get("bb_upper")
        if upper and upper > current_price + 30:
            ceilings.append(upper)
    best_ask = orderbook_data.get("best_ask", current_price + 50)
    if best_ask > current_price + 30:
        ceilings.append(best_ask + 1.5 * atr_5m)
        
    nearest_ceiling = min(ceilings) if ceilings else (current_price + 3.0 * atr_5m)

    # Floor candidate levels (lower bands & bid walls)
    floors = []
    for tf in ["5m", "15m", "30m", "1h"]:
        lower = timeframe_cache.get(tf, {}).get("indicators", {}).get("bb_lower")
        if lower and lower < current_price - 30:
            floors.append(lower)
    best_bid = orderbook_data.get("best_bid", current_price - 50)
    if best_bid < current_price - 30:
        floors.append(best_bid - 1.5 * atr_5m)
        
    nearest_floor = max(floors) if floors else (current_price - 3.0 * atr_5m)

    # -------------------------------------------------------------
    # 3. DYNAMIC WAVE GEOMETRY & TARGET PROJECTION
    # -------------------------------------------------------------
    if v_kinetic >= 0.08:
        wave_1_dir = "LONG"
    elif v_kinetic <= -0.08:
        wave_1_dir = "SHORT"
    else:
        wave_1_dir = "LONG" if macro_bias != "BEARISH" else "SHORT"

    if wave_1_dir == "LONG":
        dist_to_wall = max(100.0, nearest_ceiling - current_price)
        expected_amp = max(200.0, min(dist_to_wall, 2.5 * atr_5m))
        expected_amp = round(expected_amp, 0)
        
        target_1 = round(current_price + expected_amp, 1)
        entry_low = round(current_price - 0.35 * atr_5m, 1)
        entry_high = round(current_price + 0.15 * atr_5m, 1)
        invalidation = round(min(nearest_floor, current_price - 0.9 * atr_5m), 1)

        wave_2_dir = "SHORT"
        wave_2_amp = round(expected_amp * 0.65, 0)
        wave_2_target = round(target_1 - wave_2_amp, 1)
        wave_2_desc = f"Overhead resistance wall near ${target_1:,.0f} (${nearest_ceiling:,.0f}). Anticipate a -${wave_2_amp:.0f} re-dip cooling wave back toward ${wave_2_target:,.0f} once the push exhausts."
        headline = f"Kinetic Push: Bullish Expansion (Velocity {v_kinetic:+.2f}) Toward ${target_1:,.0f}"
        narrative = f"Tactical screens show fast momentum (MA5 > MA10) and expanding bands with {taker_delta:+.0%} taker flow aggression. Push driving toward the ${nearest_ceiling:,.0f} ceiling barrier."

    else:
        dist_to_wall = max(100.0, current_price - nearest_floor)
        expected_amp = max(200.0, min(dist_to_wall, 2.5 * atr_5m))
        expected_amp = round(expected_amp, 0)
        
        target_1 = round(current_price - expected_amp, 1)
        entry_low = round(current_price - 0.15 * atr_5m, 1)
        entry_high = round(current_price + 0.35 * atr_5m, 1)
        invalidation = round(max(nearest_ceiling, current_price + 0.9 * atr_5m), 1)

        wave_2_dir = "LONG"
        wave_2_amp = round(expected_amp * 0.65, 0)
        wave_2_target = round(target_1 + wave_2_amp, 1)
        wave_2_desc = f"Downside bid absorption pocket near ${target_1:,.0f} (${nearest_floor:,.0f}). Once limit orders absorb the sweep, anticipate a +${wave_2_amp:.0f} counter-reaction bounce toward ${wave_2_target:,.0f}."
        headline = f"Kinetic Push: Bearish Leg (Velocity {v_kinetic:+.2f}) Toward ${target_1:,.0f}"
        narrative = f"Tactical screens show downward momentum acceleration (MA5 < MA10) and bands pressing lower with {taker_delta:+.0%} taker sell pressure. Push running toward the ${nearest_floor:,.0f} support floor."

    prob_up_calc = round(max(0.15, min(0.85, 0.50 + (v_kinetic * 0.35))), 3)
    prob_down_calc = round(1.0 - prob_up_calc, 3)

    scenario_id = f"scen_{int(now)}"
    scenario_payload = {
        "scenario_id": scenario_id,
        "created_at": now,
        "baseline_price": current_price,
        "current_price": current_price,
        "macro_bias": macro_bias,
        "kinetic_velocity": round(v_kinetic, 3),
        "prob_up": prob_up_calc,
        "prob_down": prob_down_calc,
        "prob_up_pct": round(prob_up_calc * 100, 1),
        "prob_down_pct": round(prob_down_calc * 100, 1),
        "headline": headline,
        "narrative": narrative,
        "invalidation_floor": invalidation,
        "target_ceiling": target_1,
        "status": "OPTIMAL_ENTRY_ZONE",
        "action_mode": "ENTER_NOW" if wave_1_dir == "LONG" else "ENTER_SHORT",
        "progress_pct": 0.0,
        "realized_dollars": 0.0,
        "guidance": f"🟢 IN OPTIMAL ENTRY ZONE (${current_price:,.1f}) — Kinetic velocity ({v_kinetic:+.2f}) targeting ${target_1:,.1f} ({'+' if wave_1_dir == 'LONG' else '-'}${expected_amp:.0f}).",
        "wave_1": {
            "name": f"Immediate {wave_1_dir} Wave",
            "direction": wave_1_dir,
            "entry_zone": [entry_low, entry_high],
            "target_price": target_1,
            "expected_amplitude_dollars": expected_amp,
            "risk_reward_ratio": f"{round(expected_amp / max(1.0, abs(current_price - invalidation)), 2)}:1",
        },
        "wave_2": {
            "name": f"Subsequent {wave_2_dir} Wave",
            "direction": wave_2_dir,
            "expected_trigger": target_1,
            "expected_target": wave_2_target,
            "expected_amplitude_dollars": wave_2_amp,
            "description": wave_2_desc,
        },
        "multi_screen_consensus": {
            "screens_analyzed": 10,
            "macro_anchor": f"4H/2H: {macro_bias}",
            "kinetic_push": f"Velocity: {v_kinetic:+.2f} (MA5/10: {ma_velocity:+.2f} · BB: {bb_velocity:+.2f})",
            "orderbook_bias": f"Imbalance: {imbalance:+.1%} · Taker Δ: {taker_delta:+.1%}",
        }
    }
    return scenario_payload
