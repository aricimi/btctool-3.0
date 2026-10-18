"""
btctool 3.0 - Sentiment Service (Alternative.me Macro + Dynamic Intraday Synthesis)
"""

import logging
from typing import Dict, Any, Optional
from backend.config import FEAR_GREED_URL
from backend.utils.http_client import fetch_json

logger = logging.getLogger("btctool.sentiment")

_cached_macro_fng: Optional[Dict[str, Any]] = None

async def fetch_macro_fear_and_greed() -> Dict[str, Any]:
    """Fetch 24h macro Fear & Greed index from Alternative.me."""
    global _cached_macro_fng
    data = await fetch_json(FEAR_GREED_URL)
    if data and "data" in data and len(data["data"]) > 0:
        item = data["data"][0]
        val = int(item.get("value", 50))
        classification = item.get("value_classification", "Neutral")
        _cached_macro_fng = {
            "value": val,
            "classification": classification,
            "source": "Alternative.me",
        }
        return _cached_macro_fng

    if _cached_macro_fng:
        return _cached_macro_fng

    return {"value": 50, "classification": "Neutral", "source": "Fallback"}

def get_timeframe_sentiment(timeframe: str, macro_fng: Dict[str, Any], fast_rsi: float, price_change_pct: float) -> Dict[str, Any]:
    """
    Timeframe-aware sentiment:
    - 4h, 8h, 1d, 1w: Uses the 24h Macro Alternative.me Fear & Greed Index.
    - 1m, 5m, 15m, 30m, 1h: Synthesizes dynamic local market sentiment from fast RSI and local price flow
      so intraday dumps are correctly labeled Extreme Fear / Oversold rather than conflicting with a 24h Greed tag.
    """
    if timeframe in ["4h", "8h", "1d", "1w"]:
        return macro_fng

    # Intraday dynamic sentiment synthesis
    # RSI: 0-100 -> weighted with price change
    rsi_component = fast_rsi
    flow_component = 50.0 + (price_change_pct * 15.0)
    intraday_score = int(0.7 * rsi_component + 0.3 * flow_component)
    intraday_score = max(5, min(95, intraday_score))

    if intraday_score <= 25:
        classification = "Extreme Fear (Oversold)"
    elif intraday_score <= 45:
        classification = "Fear"
    elif intraday_score <= 55:
        classification = "Neutral"
    elif intraday_score <= 75:
        classification = "Greed"
    else:
        classification = "Extreme Greed (Overbought)"

    return {
        "value": intraday_score,
        "classification": classification,
        "source": f"Dynamic Local Flow ({timeframe})",
    }
