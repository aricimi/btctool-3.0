"""
btctool 3.0 - L2 Order Book Microstructure Service (Bybit + OKX Multi-Exchange)
"""

import math
import logging
from collections import deque
from typing import Dict, Any, List, Optional
from backend.config import (
    BYBIT_BASE_URL,
    OKX_BASE_URL,
    OB_DECAY_LAMBDA,
    OB_TANH_SCALE,
    OB_TANH_MAX_ALPHA,
)
from backend.utils.http_client import fetch_json

logger = logging.getLogger("btctool.orderbook")

# Rolling snapshot memory for anti-spoofing filter
_recent_snapshots = deque(maxlen=3)

def _calc_weighted_depth(bids: List[List[float]], asks: List[List[float]], mid: float) -> Dict[str, float]:
    """Calculates exponential distance-weighted depth for bids and asks."""
    if mid <= 0:
        return {"bid_usd": 0.0, "ask_usd": 0.0, "imbalance": 0.0}

    total_bid_weighted = 0.0
    for price, size in bids:
        dist = abs(price - mid) / mid
        weight = math.exp(-OB_DECAY_LAMBDA * dist)
        total_bid_weighted += (price * size) * weight

    total_ask_weighted = 0.0
    for price, size in asks:
        dist = abs(price - mid) / mid
        weight = math.exp(-OB_DECAY_LAMBDA * dist)
        total_ask_weighted += (price * size) * weight

    denom = total_bid_weighted + total_ask_weighted
    imbalance = (total_bid_weighted - total_ask_weighted) / denom if denom > 0 else 0.0

    return {
        "bid_usd": total_bid_weighted,
        "ask_usd": total_ask_weighted,
        "imbalance": max(-1.0, min(1.0, imbalance)),
    }

async def fetch_bybit_orderbook() -> Optional[Dict[str, Any]]:
    """Fetch Bybit spot orderbook (50 levels)."""
    url = f"{BYBIT_BASE_URL}/v5/market/orderbook"
    params = {"category": "spot", "symbol": "BTCUSDT", "limit": 50}
    data = await fetch_json(url, params=params)
    if not data or data.get("retCode") != 0:
        return None

    result = data.get("result", {})
    raw_bids = result.get("b", [])
    raw_asks = result.get("a", [])
    if not raw_bids or not raw_asks:
        return None

    bids = [[float(p), float(s)] for p, s in raw_bids]
    asks = [[float(p), float(s)] for p, s in raw_asks]
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    mid = (best_bid + best_ask) / 2.0

    depth = _calc_weighted_depth(bids, asks, mid)
    return {
        "source": "Bybit",
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid,
        **depth,
    }

async def fetch_okx_orderbook() -> Optional[Dict[str, Any]]:
    """Fetch OKX spot orderbook (50 levels)."""
    url = f"{OKX_BASE_URL}/api/v5/market/books"
    params = {"instId": "BTC-USDT", "sz": "50"}
    data = await fetch_json(url, params=params)
    if not data or not data.get("data"):
        return None

    book = data["data"][0]
    raw_bids = book.get("bids", [])
    raw_asks = book.get("asks", [])
    if not raw_bids or not raw_asks:
        return None

    bids = [[float(p), float(s)] for p, s, *_ in raw_bids]
    asks = [[float(p), float(s)] for p, s, *_ in raw_asks]
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    mid = (best_bid + best_ask) / 2.0

    depth = _calc_weighted_depth(bids, asks, mid)
    return {
        "source": "OKX",
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid,
        **depth,
    }

async def get_orderbook_microstructure() -> Dict[str, Any]:
    """
    Unified multi-exchange L2 microstructure with anti-spoofing filter and tanh probability alpha.
    """
    # Prefer Bybit, fallback to OKX
    ob = await fetch_bybit_orderbook()
    if not ob:
        ob = await fetch_okx_orderbook()

    if not ob:
        return {
            "imbalance_ratio": 0.0,
            "tanh_alpha": 0.0,
            "best_bid": 0.0,
            "best_ask": 0.0,
            "mid_price": 0.0,
            "bid_depth_usd": 0.0,
            "ask_depth_usd": 0.0,
            "persistent_confirmed": False,
            "source": "None",
        }

    raw_imb = ob["imbalance"]
    _recent_snapshots.append(raw_imb)

    # 3-snapshot anti-spoofing persistence filter
    # Requires 3 consecutive snapshots with the same sign to confirm full alpha
    if len(_recent_snapshots) >= 3:
        all_positive = all(x > 0.03 for x in _recent_snapshots)
        all_negative = all(x < -0.03 for x in _recent_snapshots)
        persistent = all_positive or all_negative
    else:
        persistent = False

    # Damped if not persistent (anti-spoofing defense)
    effective_imb = raw_imb if persistent else (raw_imb * 0.5)

    # Bounded tanh alpha: ΔP = 0.15 * tanh(3.0 * effective_imb)
    tanh_alpha = OB_TANH_MAX_ALPHA * math.tanh(OB_TANH_SCALE * effective_imb)

    return {
        "imbalance_ratio": round(raw_imb, 4),
        "effective_imbalance": round(effective_imb, 4),
        "tanh_alpha": round(tanh_alpha, 4),
        "best_bid": ob["best_bid"],
        "best_ask": ob["best_ask"],
        "mid_price": ob["mid_price"],
        "bid_depth_usd": round(ob["bid_usd"], 2),
        "ask_depth_usd": round(ob["ask_usd"], 2),
        "persistent_confirmed": persistent,
        "source": ob["source"],
    }
