"""
btctool 3.0 - Level 2 ML Meta-Learner (HistGradientBoosting + Platt Scaling)
"""

import time
import math
import gc
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from backend.config import TIMEFRAME_PARAMETERS
from backend.services.brains import calc_atr, calc_adx

logger = logging.getLogger("btctool.ml_learner")

# Model and training timestamp cache per timeframe
_model_cache: Dict[str, Any] = {}
_last_train_time: Dict[str, float] = {}

def get_session_feature() -> int:
    """
    Time-of-day market session:
    - 0: Asia (00:00 - 08:00 UTC)
    - 1: London (08:00 - 13:00 UTC)
    - 2: New York / US-EU Overlap (13:00 - 22:00 UTC)
    """
    utc_hour = datetime.now(timezone.utc).hour
    if 0 <= utc_hour < 8:
        return 0
    elif 8 <= utc_hour < 13:
        return 1
    else:
        return 2

def build_feature_vector(brain_out: Dict[str, Any], ob_data: Dict[str, Any], deriv_data: Dict[str, Any],
                         adx_val: float) -> np.ndarray:
    """
    Constructs the 9-dimensional orthogonal feature vector:
    [composite_bull, composite_bear, pct_b, mom_slope, ob_tanh_alpha, funding_rate, oi_zscore, taker_delta, session]
    """
    stat = brain_out.get("statistical", {})
    mom = brain_out.get("momentum", {})
    vol = brain_out.get("volatility", {})
    
    comp_bull = brain_out.get("composite_bull", 0.5)
    comp_bear = brain_out.get("composite_bear", 0.5)
    pct_b = stat.get("pct_b", 0.5)
    mom_slope = mom.get("smooth_slope", 0.0)
    
    ob_alpha = ob_data.get("tanh_alpha", 0.0)
    funding_rate = deriv_data.get("funding_rate", 0.0001)
    oi_zscore = deriv_data.get("oi_zscore", 0.0)
    taker_delta = deriv_data.get("taker_delta", 0.0)
    session = get_session_feature()
    
    features = np.array([
        comp_bull,
        comp_bear,
        pct_b,
        mom_slope,
        ob_alpha,
        funding_rate,
        oi_zscore,
        taker_delta,
        float(session),
    ], dtype=np.float32).reshape(1, -1)
    
    return features

def train_calibrated_model(df: pd.DataFrame, timeframe: str) -> Optional[CalibratedClassifierCV]:
    """
    Trains HistGradientBoostingClassifier with Platt Scaling (CalibratedClassifierCV).
    Look-forward labeling: 1 if close[t + N] > close[t] + 0.2 * ATR_14 else 0.
    """
    cfg = TIMEFRAME_PARAMETERS.get(timeframe, TIMEFRAME_PARAMETERS["1h"])
    horizon = cfg["ml_horizon_bars"]
    n_bars = len(df)
    
    if n_bars < 50:
        return None
        
    close = df["close"].values
    atr = calc_atr(df, 14).values
    
    # Generate labels
    # label = 1 if close[t + N] > close[t] + 0.2 * ATR else 0
    X_rows = []
    y_rows = []
    
    fast_ema = df["close"].ewm(span=cfg["fast_ema"], adjust=False).mean().values
    slow_ema = df["close"].ewm(span=cfg["slow_ema"], adjust=False).mean().values
    
    for t in range(20, n_bars - horizon):
        curr_c = close[t]
        future_c = close[t + horizon]
        curr_atr = atr[t] if atr[t] > 0 else (curr_c * 0.005)
        
        target = 1 if future_c > (curr_c + 0.20 * curr_atr) else 0
        
        # Synthetic historical features for training matrix
        ema_ratio = (fast_ema[t] - slow_ema[t]) / curr_c
        pct_move_5 = (curr_c - close[t - 5]) / close[t - 5]
        pct_move_1 = (curr_c - close[t - 1]) / close[t - 1]
        vol_norm = curr_atr / curr_c
        
        feat = [
            0.5 + ema_ratio * 5.0,
            0.5 - ema_ratio * 5.0,
            0.5 + pct_move_5 * 2.0,
            pct_move_1 * 10.0,
            0.0, # historical OB placeholder
            0.0001, # historical funding placeholder
            0.0, # historical OI Z-score placeholder
            0.0, # historical taker delta placeholder
            1.0,
        ]
        X_rows.append(feat)
        y_rows.append(target)
        
    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.int32)
    
    # Ensure both classes exist
    if len(np.unique(y)) < 2:
        return None
        
    base_clf = HistGradientBoostingClassifier(
        max_depth=3,
        max_iter=35,
        min_samples_leaf=20 if len(X) >= 150 else 10,
        l2_regularization=1.0,
        random_state=42
    )
    
    # Adaptive Cross-Validation Calibration
    if len(X) >= 300:
        calibrated = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=3)
    else:
        # Held-out single split calibration for smaller samples
        val_size = max(10, int(len(X) * 0.25))
        train_idx = np.arange(len(X) - val_size)
        val_idx = np.arange(len(X) - val_size, len(X))
        calibrated = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=[(train_idx, val_idx)])
        
    calibrated.fit(X, y)
    
    # Immediate memory cleanup
    del X, y, X_rows, y_rows
    gc.collect()
    
    return calibrated

def predict_calibrated_probability(df: pd.DataFrame, timeframe: str, brain_out: Dict[str, Any],
                                   ob_data: Dict[str, Any], deriv_data: Dict[str, Any], adx_val: float) -> Tuple[float, float]:
    """
    Returns (calibrated_prob_up, calibrated_prob_down).
    Uses cached model or triggers retrain when cadence expires.
    """
    now = time.time()
    last_time = _last_train_time.get(timeframe, 0.0)
    
    # Cadence: 30 min for <= 30m, 60m for 1h/4h, 6h for 1d/1w
    cadence_sec = 1800 if timeframe in ["1m", "5m", "15m", "30m"] else (3600 if timeframe in ["1h", "4h", "8h"] else 21600)
    
    model = _model_cache.get(timeframe)
    if model is None or (now - last_time) > cadence_sec:
        try:
            model = train_calibrated_model(df, timeframe)
            if model is not None:
                _model_cache[timeframe] = model
                _last_train_time[timeframe] = now
        except Exception as e:
            logger.error(f"Error training ML model for {timeframe}: {e}")
            
    features = build_feature_vector(brain_out, ob_data, deriv_data, adx_val)
    
    if model is not None:
        try:
            probs = model.predict_proba(features)[0]
            prob_up = float(probs[1])
            prob_down = float(probs[0])
        except Exception as e:
            logger.warning(f"Prediction fallback for {timeframe}: {e}")
            prob_up = brain_out.get("composite_bull", 0.5)
            prob_down = brain_out.get("composite_bear", 0.5)
    else:
        # Cold start fallback using brain composite
        prob_up = brain_out.get("composite_bull", 0.5)
        prob_down = brain_out.get("composite_bear", 0.5)
        
    # Microstructure tanh alpha additive injection
    tanh_alpha = ob_data.get("tanh_alpha", 0.0)
    prob_up = max(0.05, min(0.95, prob_up + tanh_alpha))
    prob_down = max(0.05, min(0.95, prob_down - tanh_alpha))
    
    # Normalize to 1.0 sum
    total = prob_up + prob_down
    if total > 0:
        prob_up = prob_up / total
        prob_down = prob_down / total
        
    return round(prob_up, 4), round(prob_down, 4)
