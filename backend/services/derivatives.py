"""
btctool 3.0 - Derivatives & Order Flow Service (Bybit Linear Perpetuals)
"""

import logging
import numpy as np
from collections import deque
from typing import Dict, Any, Optional
from backend.config import BYBIT_BASE_URL, OI_ZSCORE_LOOKBACK
from backend.utils.http_client import fetch_json

logger = logging.getLogger("btctool.derivatives")

# Rolling memory for Open Interest Z-score calculation
_oi_history = deque(maxlen=OI_ZSCORE_LOOKBACK + 5)

async def fetch_bybit_linear_ticker() -> Optional[Dict[str, Any]]:
    """Fetch Bybit Linear BTCUSDT ticker for funding rate and open interest."""
    url = f"{BYBIT_BASE_URL}/v5/market/tickers"
    params = {"category": "linear", "symbol": "BTCUSDT"}
    data = await fetch_json(url, params=params)
    if not data or data.get("retCode") != 0:
        return None
    tickers = data.get("result", {}).get("list", [])
    if not tickers:
        return None
    return tickers[0]

async def fetch_bybit_taker_delta() -> float:
    """
    Fetch recent 100 trades from Bybit Linear and compute taker delta:
    (Buy Vol - Sell Vol) / (Buy Vol + Sell Vol) in [-1.0, 1.0]
    """
    url = f"{BYBIT_BASE_URL}/v5/market/recent-trade"
    params = {"category": "linear", "symbol": "BTCUSDT", "limit": 100}
    data = await fetch_json(url, params=params)
    if not data or data.get("retCode") != 0:
        return 0.0

    trades = data.get("result", {}).get("list", [])
    if not trades:
        return 0.0

    buy_vol = 0.0
    sell_vol = 0.0
    for t in trades:
        size = float(t.get("size", 0.0))
        side = t.get("side", "")
        if side.lower() == "buy":
            buy_vol += size
        elif side.lower() == "sell":
            sell_vol += size

    total = buy_vol + sell_vol
    if total <= 0:
        return 0.0

    delta = (buy_vol - sell_vol) / total
    return max(-1.0, min(1.0, delta))

async def get_derivatives_metrics() -> Dict[str, Any]:
    """
    Unified derivatives metrics:
    - Funding rate (decimal float)
    - Open Interest (BTC)
    - 20-period OI Z-score
    - Taker Delta ratio
    - Retail Long/Short estimated ratio
    """
    ticker = await fetch_bybit_linear_ticker()
    taker_delta = await fetch_bybit_taker_delta()

    if not ticker:
        return {
            "funding_rate": 0.0001,
            "open_interest_btc": 0.0,
            "oi_zscore": 0.0,
            "taker_delta": taker_delta,
            "long_short_ratio": 1.0,
            "is_valid": False,
        }

    # Funding rate
    funding_rate_str = ticker.get("fundingRate", "0.0001")
    try:
        funding_rate = float(funding_rate_str)
    except (ValueError, TypeError):
        funding_rate = 0.0001

    # Open Interest
    oi_str = ticker.get("openInterest", "0.0")
    try:
        open_interest = float(oi_str)
    except (ValueError, TypeError):
        open_interest = 0.0

    # Rolling OI Z-score
    if open_interest > 0:
        _oi_history.append(open_interest)

    oi_zscore = 0.0
    if len(_oi_history) >= 5:
        arr = np.array(_oi_history)
        diffs = np.diff(arr)
        if len(diffs) > 0 and np.std(diffs) > 1e-6:
            oi_zscore = float((diffs[-1] - np.mean(diffs)) / np.std(diffs))
            oi_zscore = max(-4.0, min(4.0, oi_zscore))

    # Long/Short ratio estimate from 24h turnover & taker flow
    # Normal baseline is 50/50 (1.0). High funding tilts long ratio up.
    implied_long_ratio = 0.50 + (funding_rate * 200.0) + (taker_delta * 0.1)
    implied_long_ratio = max(0.20, min(0.80, implied_long_ratio))

    return {
        "funding_rate": round(funding_rate, 6),
        "funding_rate_pct": round(funding_rate * 100, 4),
        "open_interest_btc": round(open_interest, 2),
        "oi_zscore": round(oi_zscore, 2),
        "taker_delta": round(taker_delta, 4),
        "long_ratio": round(implied_long_ratio, 3),
        "is_valid": True,
    }
