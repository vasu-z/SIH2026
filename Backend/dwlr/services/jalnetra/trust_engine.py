import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from scipy.spatial import cKDTree

from ..adapters.tsod_adapter import TsodAdapter
from ..adapters.gems_qc_adapter import GemsQcAdapter
from ..adapters.trend_adapter import TrendAdapter

TRUST_WEIGHTS = {
    "missingness": 0.15,
    "range_validity": 0.10,
    "rate_of_change": 0.20,
    "persistence": 0.10,
    "neighbor_agreement": 0.20,
    "temporal_consistency": 0.15,
    "sensor_health": 0.10
}

# Verify weights sum exactly to 1.0
assert abs(sum(TRUST_WEIGHTS.values()) - 1.0) < 1e-6, "Trust weights must sum to 1.0"


def _compute_neighbor_agreement(station_id: str, df_all: Optional[pd.DataFrame] = None) -> float:
    """Calculate spatial neighbor agreement using spatial KDTree and Pearson correlation."""
    if df_all is None or df_all.empty or "lat" not in df_all.columns:
        return 0.85

    latest_stations = df_all.groupby("station_id").tail(1).copy()
    if len(latest_stations) < 2 or station_id not in latest_stations["station_id"].values:
        return 0.85

    coords = latest_stations[["lat", "lon"]].values
    tree = cKDTree(coords)

    target_idx = list(latest_stations["station_id"]).index(station_id)
    target_coord = coords[target_idx].reshape(1, -1)

    # Find k nearest neighbors (k=4: target + 3 neighbors)
    k = min(4, len(latest_stations))
    _, idxs = tree.query(target_coord, k=k)
    neighbor_indices = idxs[0]

    neighbor_sids = [latest_stations.iloc[idx]["station_id"] for idx in neighbor_indices if idx != target_idx]
    if not neighbor_sids:
        return 0.85

    # Compute correlation over last 30 days
    pivot = df_all.pivot_table(index="date", columns="station_id", values="water_level_m", aggfunc="mean").sort_index()
    if station_id not in pivot.columns or len(pivot) < 5:
        return 0.85

    target_series = pivot[station_id].dropna()
    corrs = []
    for nid in neighbor_sids:
        if nid in pivot.columns:
            ns = pivot[nid].reindex(target_series.index).dropna()
            common = target_series.loc[ns.index]
            if len(common) >= 5 and common.std() > 1e-4 and ns.std() > 1e-4:
                c = np.corrcoef(common, ns)[0, 1]
                if np.isfinite(c):
                    # Map [-1, 1] correlation to [0, 1] agreement score
                    corrs.append(max(0.0, (c + 1.0) / 2.0))

    if corrs:
        return round(float(np.mean(corrs)), 3)
    return 0.85


def evaluate_station_trust(
    station_df: pd.DataFrame,
    station_id: str,
    full_df: Optional[pd.DataFrame] = None,
    as_of: Optional[str] = None
) -> Dict[str, Any]:
    """
    Seven-factor scientific trust scoring engine combining TSOD, GEMS-GER, and UNIGRAC trend methodology.
    """
    df = station_df.copy()
    if as_of:
        df = df[df["date"].astype(str) <= str(as_of)]

    df = df.sort_values("date")
    series = df["water_level_m"].values if "water_level_m" in df.columns else np.array([])
    n = len(series)

    if n == 0:
        return {
            "station_id": station_id,
            "trust_score": 0.0,
            "classification": "PROBABLE_SENSOR_FAULT",
            "factors": {k: 0.0 for k in TRUST_WEIGHTS},
            "weights": TRUST_WEIGHTS,
            "evidence": ["No observations available on or before as_of date."],
            "coordinate_status": "DEMONSTRATION",
            "status": "VERIFIED"
        }

    # Factor 1: Missingness (GEMS-GER)
    gems_res = GemsQcAdapter.evaluate(series)
    f_missingness = gems_res["missingness_score"]

    # Factor 2 & 3: Range Validity & Rate of Change (TSOD)
    tsod_res = TsodAdapter.evaluate(series)
    f_range = tsod_res["range_validity_score"]
    f_roc = round((tsod_res["gradient_score"] * 0.5 + tsod_res["spike_anomaly_score"] * 0.5), 3)

    # Factor 4: Persistence (Sustained statistical deviation vs single point blip)
    if n >= 7:
        recent_7 = series[-7:]
        recent_std = float(np.nanstd(recent_7)) if len(recent_7) > 0 else 0.1
        f_persistence = 1.0 if recent_std < 1.0 else max(0.2, 1.0 - (recent_std / 5.0))
    else:
        f_persistence = 0.9

    # Factor 5: Neighbor Agreement (Spatial KD-Tree & Correlation)
    f_neighbor = _compute_neighbor_agreement(station_id, full_df)

    # Factor 6: Temporal Consistency (TrendAdapter Theil-Sen slope & Kendall Tau)
    trend_res = TrendAdapter.evaluate(series)
    f_temporal = trend_res["trend_confidence"]

    # Factor 7: Sensor Health (DATA_DERIVED from flatline, completeness, and consensus anomalies)
    f_sensor_health = round((
        tsod_res["flatline_score"] * 0.4 +
        gems_res["completeness_score"] * 0.3 +
        gems_res["consensus_anomaly_score"] * 0.3
    ), 3)

    factors = {
        "missingness": round(float(f_missingness), 3),
        "range_validity": round(float(f_range), 3),
        "rate_of_change": round(float(f_roc), 3),
        "persistence": round(float(f_persistence), 3),
        "neighbor_agreement": round(float(f_neighbor), 3),
        "temporal_consistency": round(float(f_temporal), 3),
        "sensor_health": round(float(f_sensor_health), 3)
    }

    # Weighted composite score (0 - 100)
    raw_trust = sum(factors[k] * TRUST_WEIGHTS[k] for k in TRUST_WEIGHTS) * 100.0
    trust_score = round(max(0.0, min(100.0, raw_trust)), 1)

    # Classification
    if trust_score >= 75.0:
        classification = "TRUSTED"
    elif trust_score >= 50.0:
        classification = "SUSPICIOUS"
    else:
        classification = "PROBABLE_SENSOR_FAULT"

    # Consolidate evidence
    evidence = []
    evidence.extend(tsod_res.get("evidence", []))
    evidence.extend(gems_res.get("evidence", []))
    evidence.append(f"Trend: {trend_res['trend_direction']} ({trend_res['sen_slope_m_per_year']} m/year, Kendall Tau {trend_res['kendall_tau']})")
    evidence.append(f"Spatial neighbor agreement factor: {f_neighbor}")
    evidence.append(f"Data-derived sensor health: {f_sensor_health} (DATA_DERIVED)")

    return {
        "station_id": station_id,
        "trust_score": trust_score,
        "classification": classification,
        "factors": factors,
        "weights": TRUST_WEIGHTS,
        "evidence": evidence,
        "coordinate_status": "DEMONSTRATION",
        "status": "VERIFIED"
    }
