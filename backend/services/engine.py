"""
btctool 3.0 - Unified Master Prediction & Telemetry Engine
"""

import time
import asyncio
import logging
import gc
from typing import Dict, Any, Optional
from backend.config import TIMEFRAMES, TIMEFRAME_PARAMETERS, CACHE_WARMUP_INTERVAL_SEC, WARMUP_IDLE_TIMEOUT_SEC
from backend.services.market_data import get_klines, get_current_price
from backend.services.orderbook import get_orderbook_microstructure
from backend.services.derivatives import get_derivatives_metrics
from backend.services.sentiment import fetch_macro_fear_and_greed, get_timeframe_sentiment
from backend.services.brains import evaluate_tri_brain_ensemble, calc_adx
from backend.services.ml_learner import predict_calibrated_probability
from backend.services.pre_filter import evaluate_derivatives_pre_filter
from backend.services.decision_matrix import compute_trade_plan, calculate_cross_timeframe_alignment
from backend.services.scenario_simulator import simulate_intraday_scenario, get_active_scenario

logger = logging.getLogger("btctool.engine")

# High-speed in-memory cache for all 9 timeframes
_timeframe_cache: Dict[str, Dict[str, Any]] = {}
_last_request_timestamp: float = time.time()
_warmup_running: bool = False

def record_activity():
    """Records user request activity to reset idle sleep timeout."""
    global _last_request_timestamp
    _last_request_timestamp = time.time()

async def generate_timeframe_summary(timeframe: str, macro_4h_regime: str = "Range") -> Optional[Dict[str, Any]]:
    """
    Generates a full institutional analytics summary for a single timeframe.
    """
    df = await get_klines(timeframe, limit=200)
    if df is None or len(df) < 30:
        logger.error(f"Insufficient klines for {timeframe}")
        return None

    current_price = float(df["close"].iloc[-1])
    
    # 1. Microstructure & Derivatives
    ob_data = await get_orderbook_microstructure()
    deriv_data = await get_derivatives_metrics()
    
    # 2. ADX calculation
    adx_series, _, _ = calc_adx(df, 14)
    curr_adx = float(adx_series.iloc[-1])
    prev_adx = float(adx_series.iloc[-2]) if len(adx_series) > 1 else curr_adx
    delta_adx = float(curr_adx - prev_adx)
    
    # 3. Tri-Brain Ensemble
    brain_out = evaluate_tri_brain_ensemble(df, timeframe, macro_4h_regime)
    
    # 4. ML Meta-Learner (HistGBM + Platt Scaling)
    prob_up, prob_down = predict_calibrated_probability(
        df, timeframe, brain_out, ob_data, deriv_data, curr_adx
    )
    
    # 5. Derivatives Pre-Filter
    is_bullish = bool(brain_out["momentum"]["bull_score"] > brain_out["momentum"]["bear_score"])
    pre_filter = evaluate_derivatives_pre_filter(deriv_data, curr_adx, delta_adx, is_bullish)
    
    # 6. Scenario Decision Matrix & Trade Plan
    atr_val = brain_out["volatility"]["atr"]
    pct_b = brain_out["statistical"]["pct_b"]
    squeeze_state = brain_out["volatility"]["squeeze_state"]
    is_accel = brain_out["momentum"]["is_accelerating"]
    
    plan = compute_trade_plan(
        current_price=current_price,
        atr=atr_val,
        timeframe=timeframe,
        macro_regime=macro_4h_regime,
        squeeze_state=squeeze_state,
        prob_up=prob_up,
        prob_down=prob_down,
        pct_b=pct_b,
        ob_data=ob_data,
        pre_filter=pre_filter,
        is_accelerating=is_accel,
        mom_data=brain_out["momentum"],
        deriv_data=deriv_data,
        vol_data=brain_out["volatility"],
        higher_tf_context={
            "3m": _timeframe_cache.get("3m"),
            "5m": _timeframe_cache.get("5m"),
            "15m": _timeframe_cache.get("15m"),
            "30m": _timeframe_cache.get("30m"),
            "1h": _timeframe_cache.get("1h"),
            "2h": _timeframe_cache.get("2h"),
        }
    )
    
    # 7. Sentiment
    macro_fng = await fetch_macro_fear_and_greed()
    pct_change_24h = ((current_price - df["close"].iloc[0]) / df["close"].iloc[0] * 100) if len(df) > 0 else 0.0
    sentiment = get_timeframe_sentiment(timeframe, macro_fng, brain_out["momentum"]["rsi_fast"], pct_change_24h)
    
    summary = {
        "timeframe": timeframe,
        "current_price": current_price,
        "timestamp": int(time.time()),
        "prob_up": prob_up,
        "prob_down": prob_down,
        "prob_up_pct": round(prob_up * 100, 1),
        "prob_down_pct": round(prob_down * 100, 1),
        "macro_regime": macro_4h_regime,
        "brain_ensemble": brain_out,
        "orderbook": ob_data,
        "derivatives": deriv_data,
        "pre_filter": pre_filter,
        "trade_plan": plan,
        "sentiment": sentiment,
        "indicators": {
            "rsi_fast": brain_out["momentum"]["rsi_fast"],
            "rsi_mid": brain_out["momentum"]["rsi_mid"],
            "rsi_slow": brain_out["momentum"]["rsi_slow"],
            "fast_ema": brain_out["momentum"]["fast_ema"],
            "slow_ema": brain_out["momentum"]["slow_ema"],
            "macd_hist": brain_out["momentum"]["macd_hist"],
            "macd_dif": brain_out["momentum"].get("macd_dif", 0.0),
            "macd_dea": brain_out["momentum"].get("macd_dea", 0.0),
            "is_accelerating": brain_out["momentum"].get("is_accelerating", False),
            "ma5": brain_out["momentum"].get("ma5", current_price),
            "ma10": brain_out["momentum"].get("ma10", current_price),
            "volume_surge": brain_out["momentum"].get("volume_surge", 1.0),
            "pct_b": brain_out["statistical"]["pct_b"],
            "atr": atr_val,
            "adx": round(curr_adx, 2),
            "squeeze_state": squeeze_state,
            "squeeze_badge": brain_out["volatility"]["squeeze_badge"],
            "bb_middle": brain_out["volatility"].get("bb_middle", 0.0),
            "bb_upper": brain_out["volatility"].get("bb_upper", 0.0),
            "bb_lower": brain_out["volatility"].get("bb_lower", 0.0),
            "bb_bandwidth_pct": brain_out["volatility"].get("bb_bandwidth_pct", 0.0),
            "bb_mb_slope": brain_out["volatility"].get("bb_mb_slope", 0.0),
            "bb_direction": brain_out["volatility"].get("bb_direction", "HORIZONTAL"),
            "bb_is_opening": brain_out["volatility"].get("bb_is_opening", False),
            "bb_state": brain_out["volatility"].get("bb_state", "NORMAL_RANGE"),
        }
    }
    
    # 8. 24/7 Multi-Screen Intraday Scenario Simulation
    try:
        scenario = simulate_intraday_scenario(
            current_price=current_price,
            timeframe_cache=_timeframe_cache,
            orderbook_data=ob_data,
            derivatives_data=deriv_data
        )
        summary["intraday_scenario"] = scenario
        # Synchronize Card 2 Probability with the Master Kinetic Engine
        if scenario and "prob_up" in scenario:
            summary["prob_up"] = scenario["prob_up"]
            summary["prob_down"] = scenario["prob_down"]
            summary["prob_up_pct"] = scenario["prob_up_pct"]
            summary["prob_down_pct"] = scenario["prob_down_pct"]
    except Exception as e:
        logger.error(f"Error simulating intraday scenario: {e}")

    _timeframe_cache[timeframe] = summary
    return summary

async def get_summary_for_timeframe(timeframe: str) -> Dict[str, Any]:
    """Retrieves cached summary or generates fresh on demand with cross-TF alignment."""
    record_activity()
    
    # Ensure 4H macro regime is established
    macro_regime = "Range"
    if "4h" in _timeframe_cache:
        macro_regime = _timeframe_cache["4h"].get("pre_filter", {}).get("regime", "Range")
    else:
        summary_4h = await generate_timeframe_summary("4h", "Range")
        if summary_4h:
            macro_regime = summary_4h.get("pre_filter", {}).get("regime", "Range")
            
    summary = _timeframe_cache.get(timeframe)
    if not summary or (time.time() - summary.get("timestamp", 0)) > 60:
        summary = await generate_timeframe_summary(timeframe, macro_regime)
        
    # Inject cross-timeframe alignment score
    alignment = calculate_cross_timeframe_alignment(_timeframe_cache)
    if summary:
        summary["cross_tf_alignment"] = alignment
        if "current_price" in summary:
            try:
                scenario = simulate_intraday_scenario(
                    current_price=summary["current_price"],
                    timeframe_cache=_timeframe_cache,
                    orderbook_data=summary.get("orderbook", {}),
                    derivatives_data=summary.get("derivatives", {})
                )
                summary["intraday_scenario"] = scenario
                if scenario and "prob_up" in scenario:
                    summary["prob_up"] = scenario["prob_up"]
                    summary["prob_down"] = scenario["prob_down"]
                    summary["prob_up_pct"] = scenario["prob_up_pct"]
                    summary["prob_down_pct"] = scenario["prob_down_pct"]
            except Exception as e:
                logger.error(f"Error updating scenario in get_summary: {e}")
        
    return summary or {"error": "Failed to generate market summary"}

async def warmup_cache_loop():
    """
    Background cache warming loop:
    Cycles through all 9 timeframes so UI requests return in <0.1s.
    Throttles to idle when no user activity detected for 5 minutes.
    """
    global _warmup_running
    if _warmup_running:
        return
    _warmup_running = True
    logger.info("Starting background cache warmup loop...")
    
    while True:
        try:
            now = time.time()
            # Check idle timeout
            if (now - _last_request_timestamp) > WARMUP_IDLE_TIMEOUT_SEC:
                # Idle sleep for 60 seconds to preserve free tier CPU/RAM
                await asyncio.sleep(60)
                continue
                
            # First refresh 4H to maintain macro anchor
            summary_4h = await generate_timeframe_summary("4h", "Range")
            macro_regime = summary_4h.get("pre_filter", {}).get("regime", "Range") if summary_4h else "Range"
            await asyncio.sleep(2.0)
            
            # Paced cycle through remaining timeframes
            for tf in TIMEFRAMES:
                if tf == "4h":
                    continue
                await generate_timeframe_summary(tf, macro_regime)
                # 2.0s pace and garbage collection between timeframes to respect memory budget
                gc.collect()
                await asyncio.sleep(2.0)
                
            await asyncio.sleep(CACHE_WARMUP_INTERVAL_SEC)
        except Exception as e:
            logger.error(f"Error in warmup loop: {e}")
            await asyncio.sleep(10)
