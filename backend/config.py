"""
btctool 3.0 - Unified Configuration & Constants
"""

import os

# Server & Network Settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
APP_NAME = "btctool 3.0"
VERSION = "3.0.0"

# Endpoints
BYBIT_BASE_URL = "https://api.bybit.com"
BINANCE_BASE_URL = "https://api.binance.com"
OKX_BASE_URL = "https://www.okx.com"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"

# 9 Supported Timeframes in Hierarchical Order
TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"]

# Bybit Kline Interval Mapping
BYBIT_INTERVAL_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "8h": "480",
    "1d": "D",
    "1w": "W",
}

# Binance Kline Interval Mapping (Fallback)
BINANCE_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "8h": "8h",
    "1d": "1d",
    "1w": "1w",
}

# Timeframe-Adaptive Indicator Parameters Matrix (v1 Institutional Upgrade)
TIMEFRAME_PARAMETERS = {
    "1m": {
        "horizon_desc": "3 min (3 bars)",
        "rsi_periods": (3, 7, 14),
        "fast_ema": 5,
        "slow_ema": 13,
        "bb_period": 14,
        "bb_std": 2.0,
        "macd_fast": 6,
        "macd_slow": 13,
        "macd_signal": 5,
        "atr_multiplier": 1.0,
        "ml_horizon_bars": 5,
        "squeeze_loaded_bars": 5,
        "role": "Ultra Scalp ($120–$300 micro-bounces, 0.2%–0.5% scalps)",
    },
    "5m": {
        "horizon_desc": "15 min",
        "rsi_periods": (5, 9, 14),
        "fast_ema": 8,
        "slow_ema": 21,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 8,
        "macd_slow": 17,
        "macd_signal": 7,
        "atr_multiplier": 1.0,
        "ml_horizon_bars": 3,
        "squeeze_loaded_bars": 5,
        "role": "Scalp Momentum (Wick sweep & reclaim)",
    },
    "15m": {
        "horizon_desc": "45 min",
        "rsi_periods": (6, 12, 24),
        "fast_ema": 9,
        "slow_ema": 21,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 1.5,
        "ml_horizon_bars": 2,
        "squeeze_loaded_bars": 3,
        "role": "Momentum & intraday rotation",
    },
    "30m": {
        "horizon_desc": "1.5 hours",
        "rsi_periods": (6, 14, 28),
        "fast_ema": 12,
        "slow_ema": 26,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 1.5,
        "ml_horizon_bars": 2,
        "squeeze_loaded_bars": 3,
        "role": "Short-Term swing setup",
    },
    "1h": {
        "horizon_desc": "3 hours",
        "rsi_periods": (6, 12, 24),
        "fast_ema": 9,
        "slow_ema": 21,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 1.5,
        "ml_horizon_bars": 2,
        "squeeze_loaded_bars": 3,
        "role": "Intraday benchmark structure",
    },
    "4h": {
        "horizon_desc": "12 hours",
        "rsi_periods": (7, 14, 28),
        "fast_ema": 10,
        "slow_ema": 30,
        "bb_period": 20,
        "bb_std": 2.2,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 2.0,
        "ml_horizon_bars": 1,
        "squeeze_loaded_bars": 3,
        "role": "Multi-session swing trends",
    },
    "8h": {
        "horizon_desc": "24 hours",
        "rsi_periods": (7, 14, 28),
        "fast_ema": 12,
        "slow_ema": 36,
        "bb_period": 20,
        "bb_std": 2.2,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 2.0,
        "ml_horizon_bars": 1,
        "squeeze_loaded_bars": 3,
        "role": "Position / Multi-day structure",
    },
    "1d": {
        "horizon_desc": "3 days",
        "rsi_periods": (9, 14, 30),
        "fast_ema": 20,
        "slow_ema": 50,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 2.0,
        "ml_horizon_bars": 1,
        "squeeze_loaded_bars": 3,
        "role": "Macro Trend & Daily Strategic Roadmap",
    },
    "1w": {
        "horizon_desc": "3 weeks",
        "rsi_periods": (7, 14, 21),
        "fast_ema": 10,
        "slow_ema": 40,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_multiplier": 2.0,
        "ml_horizon_bars": 1,
        "squeeze_loaded_bars": 3,
        "role": "Macro weekly regime",
    },
}

# Microstructure & ML Constants
OB_DECAY_LAMBDA = 40.0         # Distance decay factor in orderbook weighting
OB_TANH_SCALE = 3.0           # Tanh sensitivity scale
OB_TANH_MAX_ALPHA = 0.15      # Maximum probability bump from orderbook
OI_ZSCORE_LOOKBACK = 20       # 20-period rolling z-score for Open Interest
ADX_TREND_THRESHOLD = 22.0    # Minimum ADX to confirm trend regime
KC_ATR_MULTIPLIER = 1.5       # Keltner Channel multiplier for Squeeze Machine

# Derivatives Pre-Filter Thresholds
FUNDING_RATE_HIGH = 0.0005    # +0.05% funding rate (long overcrowding)
FUNDING_RATE_LOW = -0.0003    # -0.03% funding rate (short overcrowding)

# Memory & Cache Settings
CACHE_WARMUP_INTERVAL_SEC = 45 # Cycling through all 9 timeframes
WARMUP_IDLE_TIMEOUT_SEC = 300  # 5 minutes of no client requests triggers idle throttle
