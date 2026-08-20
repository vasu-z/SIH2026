import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor


class GemsQcAdapter:
    """
    Isolated adapter leveraging groundwater quality control & multi-detector ensemble algorithms from KITHydrogeology/GEMS-GER.
    """

    @classmethod
    def evaluate(cls, series: Union[pd.Series, np.ndarray]) -> Dict[str, Any]:
        """
        Evaluate time series for missingness, consecutive gaps, and multi-detector ensemble outlier consensus.
        """
        if isinstance(series, np.ndarray):
            s = pd.Series(series)
        else:
            s = series.copy()

        n = len(s)
        if n == 0:
            return {
                "completeness_score": 1.0,
                "missingness_score": 1.0,
                "consensus_anomaly_score": 1.0,
                "anomaly_points": 0,
                "evidence": ["No data available for QC evaluation."]
            }

        # 1. Missingness & Gap Analysis (GEMS-GER 01)
        nan_count = int(s.isna().sum())
        nan_ratio = nan_count / n
        completeness = 1.0 - nan_ratio

        is_nan = s.isna().astype(int)
        if is_nan.sum() == n:
            max_gap = n
        elif is_nan.sum() == 0:
            max_gap = 0
        else:
            groups = (is_nan != is_nan.shift()).cumsum()
            max_gap = int(is_nan.groupby(groups).sum().max())

        # Missingness score penalizes both overall missing fraction and long consecutive gaps
        gap_penalty = min(1.0, max_gap / 30.0) * 0.4
        missingness_score = max(0.0, completeness - gap_penalty)

        # 2. Multi-Model Outlier Consensus Ensemble (GEMS-GER 02)
        valid_series = s.dropna()
        anomaly_count = 0
        consensus_score = 1.0
        evidence = []

        if len(valid_series) >= 15:
            vals = valid_series.values.reshape(-1, 1)

            # Model A: Rolling Z-Score (window 14)
            roll_mean = s.rolling(window=14, min_periods=3, center=True).mean()
            roll_std = s.rolling(window=14, min_periods=3, center=True).std() + 1e-6
            z_score_mask = ((s - roll_mean).abs() / roll_std) > 3.0
            vote_z = z_score_mask.fillna(False).values

            # Model B: Isolation Forest
            try:
                iso = IsolationForest(contamination=0.02, random_state=42)
                vote_iso = (iso.fit_predict(vals) == -1)
            except Exception:
                vote_iso = np.zeros(len(vals), dtype=bool)

            # Model C: Local Outlier Factor
            try:
                n_neighbors = min(15, max(3, len(vals) // 4))
                lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=0.02)
                vote_lof = (lof.fit_predict(vals) == -1)
            except Exception:
                vote_lof = np.zeros(len(vals), dtype=bool)

            # Combine votes on valid subset
            valid_indices = valid_series.index
            votes_total = np.zeros(n, dtype=int)

            votes_total[valid_series.index] += vote_iso.astype(int)
            votes_total[valid_series.index] += vote_lof.astype(int)
            votes_total += vote_z.astype(int)

            # Consensus outlier flagged if >= 2 models agree
            consensus_outliers = votes_total >= 2
            anomaly_count = int(np.sum(consensus_outliers))
            consensus_score = max(0.0, 1.0 - (anomaly_count / max(1, len(valid_series))) * 4.0)

        # Build evidence
        if nan_ratio > 0.05:
            evidence.append(f"Data completeness: {round(completeness*100, 1)}% ({nan_count} missing days, max gap {max_gap} days)")
        if anomaly_count > 0:
            evidence.append(f"Multi-model ensemble (IsolationForest + LOF + Z-score) detected {anomaly_count} consensus anomalies")
        if not evidence:
            evidence.append("High time-series completeness and zero multi-model consensus anomalies.")

        return {
            "completeness_score": round(float(completeness), 3),
            "missingness_score": round(float(missingness_score), 3),
            "consensus_anomaly_score": round(float(consensus_score), 3),
            "anomaly_points": anomaly_count,
            "evidence": evidence
        }
