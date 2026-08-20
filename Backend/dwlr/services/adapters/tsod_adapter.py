import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union

GAUSSIAN_SCALE_FACTOR = 1.4826

def _hampel_filter(values: np.ndarray, window_size: int = 5, threshold: float = 3.0, k: float = GAUSSIAN_SCALE_FACTOR) -> np.ndarray:
    """
    Hampel MAD outlier detector based on audited DHI/tsod implementation.
    Identifies point spikes and localized sensor blips.
    """
    n = len(values)
    is_outlier = np.zeros(n, dtype=bool)
    if n < window_size * 2 + 1:
        return is_outlier

    for t in range(window_size, n - window_size):
        window = values[t - window_size : t + window_size + 1]
        valid_window = window[np.isfinite(window)]
        if len(valid_window) == 0:
            continue
        med = np.median(valid_window)
        mad = k * np.median(np.abs(valid_window - med))
        if mad > 1e-6:
            diff = np.abs(values[t] - med)
            if diff > threshold * mad:
                is_outlier[t] = True
    return is_outlier


class TsodAdapter:
    """
    Isolated adapter leveraging time-series outlier and anomaly algorithms from DHI/tsod.
    """

    @classmethod
    def evaluate(
        cls,
        series: Union[pd.Series, np.ndarray],
        min_valid: float = 0.0,
        max_valid: float = 50.0,
        max_gradient: float = 1.5
    ) -> Dict[str, Any]:
        """
        Evaluate time series for point spikes (Hampel), sudden gradient jumps, range violations, and stuck flatlines.
        """
        vals = np.asarray(series, dtype=float)
        n = len(vals)
        if n == 0:
            return {
                "spike_anomaly_score": 1.0,
                "gradient_score": 1.0,
                "range_validity_score": 1.0,
                "flatline_score": 1.0,
                "anomalous_points": 0,
                "evidence": ["No observation records to evaluate."]
            }

        valid_vals = vals[np.isfinite(vals)]
        if len(valid_vals) == 0:
            return {
                "spike_anomaly_score": 0.0,
                "gradient_score": 0.0,
                "range_validity_score": 0.0,
                "flatline_score": 0.0,
                "anomalous_points": n,
                "evidence": ["All values in observation series are NaN/missing."]
            }

        # 1. Range Validation
        in_range = (vals >= min_valid) & (vals <= max_valid)
        range_score = float(np.mean(in_range[np.isfinite(vals)])) if len(valid_vals) > 0 else 1.0

        # 2. Gradient / Rate of Change
        diffs = np.abs(np.diff(vals))
        valid_diffs = diffs[np.isfinite(diffs)]
        if len(valid_diffs) > 0:
            excessive_gradients = np.sum(valid_diffs > max_gradient)
            gradient_score = max(0.0, 1.0 - (excessive_gradients / len(valid_diffs)) * 3.0)
        else:
            gradient_score = 1.0

        # 3. Hampel MAD Outlier Filter
        hampel_outliers = _hampel_filter(vals, window_size=4, threshold=3.0)
        spike_count = int(np.sum(hampel_outliers))
        spike_score = max(0.0, 1.0 - (spike_count / max(1, n)) * 5.0)

        # 4. Stuck Sensor / Flatline Check
        # Check for consecutive identical readings
        if len(valid_vals) >= 5:
            same_diff = np.diff(valid_vals) == 0.0
            max_flatline = 0
            curr_flat = 0
            for is_same in same_diff:
                if is_same:
                    curr_flat += 1
                    max_flatline = max(max_flatline, curr_flat)
                else:
                    curr_flat = 0
            flatline_score = max(0.0, 1.0 - (max_flatline / 30.0)) if max_flatline > 5 else 1.0
        else:
            flatline_score = 1.0

        evidence = []
        if range_score < 0.99:
            evidence.append(f"Range validity penalty: {round((1.0 - range_score)*100, 1)}% readings exceed [{min_valid}m, {max_valid}m]")
        if gradient_score < 0.90:
            evidence.append(f"Rate of change penalty: abrupt jumps exceeding {max_gradient} m/day")
        if spike_count > 0:
            evidence.append(f"Hampel filter flagged {spike_count} transient statistical point anomalies")
        if flatline_score < 0.90:
            evidence.append("Potential stuck sensor: repeated static water level readings")
        if not evidence:
            evidence.append("Time series satisfies range, gradient, Hampel MAD, and dynamic variation checks.")

        total_anomalous = int(spike_count + np.sum(~in_range[np.isfinite(vals)]))

        return {
            "spike_anomaly_score": round(float(spike_score), 3),
            "gradient_score": round(float(gradient_score), 3),
            "range_validity_score": round(float(range_score), 3),
            "flatline_score": round(float(flatline_score), 3),
            "anomalous_points": total_anomalous,
            "evidence": evidence
        }
