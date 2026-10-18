"""
btctool 3.0 - Level 3 Derivatives Pre-Filter & ADX Regime Gate
"""

from typing import Dict, Any, List
from backend.config import FUNDING_RATE_HIGH, FUNDING_RATE_LOW, ADX_TREND_THRESHOLD

def evaluate_derivatives_pre_filter(deriv_data: Dict[str, Any], adx_val: float, delta_adx: float,
                                   is_4h_bull: bool) -> Dict[str, Any]:
    """
    Derivatives Pre-Filter (Level 3):
    - Funding Rate Suppression: Prevents buying into overheated perpetual funding.
    - Liquidation Trap Detection: Flags crowded retail traps.
    - OI Exhaustion Filter: Tightens targets if OI collapses ($Z < -2.0$).
    - ADX Regime Gate: Forces range mode if ADX <= 22 and falling.
    """
    funding = deriv_data.get("funding_rate", 0.0001)
    oi_zscore = deriv_data.get("oi_zscore", 0.0)
    long_ratio = deriv_data.get("long_ratio", 0.50)
    
    suppress_market_long = False
    suppress_market_short = False
    tighten_targets = False
    warnings: List[str] = []
    
    # 1. Funding Rate Suppression
    if funding > FUNDING_RATE_HIGH:
        suppress_market_long = True
        warnings.append(f"Funding Overheated (+{round(funding * 100, 3)}%): Market long suppressed to Limit Dip")
    elif funding < FUNDING_RATE_LOW:
        suppress_market_short = True
        warnings.append(f"Negative Funding ({round(funding * 100, 3)}%): Market short suppressed to Limit Retest")
        
    # 2. Liquidation Trap Risk
    if long_ratio > 0.60:
        warnings.append("⚠️ CROWDED LONG RISK: Retail skew > 60% — Watch for liquidation wicks")
    elif long_ratio < 0.40:
        warnings.append("⚠️ CROWDED SHORT RISK: Retail skew < 40% — Watch for short squeeze wicks")
        
    # 3. OI Exhaustion
    if oi_zscore < -2.0:
        tighten_targets = True
        warnings.append("OI Exhaustion (Z < -2.0): Target distances tightened by 25%")
    elif oi_zscore > 2.0:
        warnings.append("Institutional Inflow (Z > 2.0): Trend confirmed with expanding open interest")
        
    # 4. ADX Regime Gate
    if adx_val > ADX_TREND_THRESHOLD or delta_adx > 0:
        regime = "Trend Up" if is_4h_bull else "Trend Down"
    else:
        regime = "Range"
        
    return {
        "suppress_market_long": bool(suppress_market_long),
        "suppress_market_short": bool(suppress_market_short),
        "tighten_targets": bool(tighten_targets),
        "regime": str(regime),
        "adx_val": round(float(adx_val), 2),
        "warnings": warnings,
    }
