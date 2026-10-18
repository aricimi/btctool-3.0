"""
btctool 3.0 - Market Data Service (Bybit Primary + Binance/yfinance Fallback)
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from backend.config import (
    BYBIT_BASE_URL,
    BINANCE_BASE_URL,
    BYBIT_INTERVAL_MAP,
    BINANCE_INTERVAL_MAP,
)
from backend.utils.http_client import fetch_json

logger = logging.getLogger("btctool.market_data")

async def fetch_bybit_klines(timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
    """Fetch spot klines from Bybit API v5."""
    interval = BYBIT_INTERVAL_MAP.get(timeframe)
    if not interval:
        return None
    url = f"{BYBIT_BASE_URL}/v5/market/kline"
    params = {
        "category": "spot",
        "symbol": "BTCUSDT",
        "interval": interval,
        "limit": min(limit, 200),
    }
    data = await fetch_json(url, params=params)
    if not data or data.get("retCode") != 0:
        return None
    
    rows = data.get("result", {}).get("list", [])
    if not rows:
        return None
    
    # Bybit klines are returned in reverse order: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    
    df["timestamp"] = pd.to_numeric(df["timestamp"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Sort ascending by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

async def fetch_binance_klines(timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
    """Fetch spot klines from Binance API v3 (Fallback 1)."""
    interval = BINANCE_INTERVAL_MAP.get(timeframe)
    if not interval:
        return None
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": interval,
        "limit": min(limit, 500),
    }
    data = await fetch_json(url, params=params)
    if not data or not isinstance(data, list):
        return None
    
    # Binance format: [openTime, open, high, low, close, volume, closeTime, quoteAssetVolume, numberOfTrades, ...]
    rows = []
    for item in data:
        rows.append({
            "timestamp": int(item[0]),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5]),
        })
    df = pd.DataFrame(rows)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def fetch_yfinance_klines_sync(timeframe: str, limit: int = 150) -> Optional[pd.DataFrame]:
    """Fetch klines via yfinance (Fallback 2, synchronous fallback)."""
    import yfinance as yf
    yf_tf_map = {
        "1m": ("1m", "5d"),
        "5m": ("5m", "5d"),
        "15m": ("15m", "5d"),
        "30m": ("30m", "1mo"),
        "1h": ("60m", "1mo"),
        "4h": ("1h", "1mo"), # yf doesn't support 4h directly
        "8h": ("1h", "1mo"),
        "1d": ("1d", "1y"),
        "1w": ("1wk", "2y"),
    }
    interval, period = yf_tf_map.get(timeframe, ("1d", "6mo"))
    try:
        ticker = yf.Ticker("BTC-USD")
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return None
        df = hist.reset_index()
        time_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df[[time_col, "Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        df["timestamp"] = df["timestamp"].astype("int64") // 10**6
        return df.tail(limit).reset_index(drop=True)
    except Exception as e:
        logger.error(f"yfinance fallback error: {e}")
        return None

async def get_klines(timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
    """
    Get klines with automatic cascading failover:
    Bybit (Primary) -> Binance (Fallback 1) -> yfinance (Fallback 2)
    """
    # 1. Bybit
    df = await fetch_bybit_klines(timeframe, limit)
    if df is not None and len(df) >= 30:
        return df
    
    logger.warning(f"Bybit failed for {timeframe}, trying Binance...")
    # 2. Binance
    df = await fetch_binance_klines(timeframe, limit)
    if df is not None and len(df) >= 30:
        return df

    logger.warning(f"Binance failed for {timeframe}, trying yfinance...")
    # 3. yfinance
    import asyncio
    loop = asyncio.get_running_loop()
    df = await loop.run_in_executor(None, fetch_yfinance_klines_sync, timeframe, limit)
    if df is not None and len(df) >= 20:
        return df
    
    logger.error(f"All market data sources exhausted for {timeframe}")
    return None

async def get_current_price() -> float:
    """Fetch current BTC price via Bybit spot ticker or Binance fallback."""
    url = f"{BYBIT_BASE_URL}/v5/market/tickers?category=spot&symbol=BTCUSDT"
    data = await fetch_json(url)
    if data and data.get("retCode") == 0:
        tickers = data.get("result", {}).get("list", [])
        if tickers and "lastPrice" in tickers[0]:
            return float(tickers[0]["lastPrice"])
    
    # Fallback to Binance
    b_url = f"{BINANCE_BASE_URL}/api/v3/ticker/price?symbol=BTCUSDT"
    b_data = await fetch_json(b_url)
    if b_data and "price" in b_data:
        return float(b_data["price"])
    
    return 0.0
