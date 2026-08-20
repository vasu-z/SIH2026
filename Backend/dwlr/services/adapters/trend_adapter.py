import numpy as np
import pandas as pd
from typing import Dict, Any, Union
from scipy import stats


class TrendAdapter:
    """
    Isolated adapter leveraging robust non-parametric groundwater trend methodology (Theil-Sen slope & Kendall Tau).
    Based on UNIGRAC/groundwater-trends-dashboard methodology using verified scipy.stats algorithms.
    """

    @classmethod
    def evaluate(cls, series: Union[pd.Series, np.ndarray]) -> Dict[str, Any]:
        """
        Calculate Theil-Sen robust slope and Kendall Tau trend significance over groundwater time series.
        """
        vals = np.asarray(series, dtype=float)
        valid_mask = np.isfinite(vals)
        y = vals[valid_mask]
        n = len(y)

        if n < 5:
            return {
                "sen_slope_m_per_day": 0.0,
                "sen_slope_m_per_year": 0.0,
                "kendall_tau": 0.0,
                "p_value": 1.0,
                "trend_direction": "STABLE",
                "trend_confidence": 0.5
            }

        x = np.arange(n)

        # 1. Theil-Sen robust median estimator
        theil_res = stats.theilslopes(y, x)
        slope_per_day = float(theil_res.slope)
        slope_per_year = round(slope_per_day * 365.25, 4)

        # 2. Kendall Tau rank correlation
        tau_res = stats.kendalltau(x, y)
        tau = float(tau_res.correlation) if np.isfinite(tau_res.correlation) else 0.0
        p_val = float(tau_res.pvalue) if np.isfinite(tau_res.pvalue) else 1.0

        # Classify trend direction
        # Note: For water level (depth or head): negative slope = declining water table
        if p_val < 0.05:
            if slope_per_year < -0.05:
                direction = "DECLINING"
            elif slope_per_year > 0.05:
                direction = "RISING"
            else:
                direction = "STABLE"
        else:
            direction = "STABLE"

        # Statistical confidence derived strictly from (1 - p_value) and Kendall Tau magnitude
        confidence = max(0.1, min(0.99, (1.0 - p_val) * 0.7 + abs(tau) * 0.3))

        return {
            "sen_slope_m_per_day": round(slope_per_day, 6),
            "sen_slope_m_per_year": slope_per_year,
            "kendall_tau": round(tau, 4),
            "p_value": round(p_val, 6),
            "trend_direction": direction,
            "trend_confidence": round(float(confidence), 3)
        }
