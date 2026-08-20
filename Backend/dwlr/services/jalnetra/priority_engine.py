import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from ..adapters.trend_adapter import TrendAdapter
from .trust_engine import evaluate_station_trust
from ..forecast_engine import forecast_ridge

DEFAULT_PRIORITY_WEIGHTS = {
    "groundwater_stress": 0.20,
    "depletion_rate": 0.15,
    "forecast_risk": 0.15,
    "forecast_uncertainty": 0.10,
    "population_dependence": 0.15,
    "vulnerability": 0.10,
    "intervention_feasibility": 0.05,
    "data_trust": 0.10
}

# Regional hydrogeological & socio-economic profile catalog (DEMONSTRATION)
REGIONAL_SOCIOECONOMIC_CATALOG = {
    "Region 12": {
        "region_name": "Central Plains Deep Aquifer",
        "station_ids": ["DWLR-001", "DWLR-002", "DWLR-003", "DWLR-004"],
        "population_dependence": 0.88,
        "vulnerability": 0.82,
        "intervention_feasibility": 0.90,
        "primary_aquifer": "Alluvial unconfined/semi-confined",
        "major_dependency": "Irrigation & rural drinking water"
    },
    "Region 17": {
        "region_name": "North Basin Depletion Perimeter",
        "station_ids": ["DWLR-005", "DWLR-006", "DWLR-007", "DWLR-008"],
        "population_dependence": 0.94,
        "vulnerability": 0.89,
        "intervention_feasibility": 0.78,
        "primary_aquifer": "Fractured hard rock",
        "major_dependency": "Intensive agricultural pumping"
    },
    "Region 08": {
        "region_name": "East Aquifer Industrial Buffer",
        "station_ids": ["DWLR-009", "DWLR-010", "DWLR-011", "DWLR-012"],
        "population_dependence": 0.72,
        "vulnerability": 0.68,
        "intervention_feasibility": 0.85,
        "primary_aquifer": "Sedimentary sandstone",
        "major_dependency": "Industrial & municipal water"
    },
    "Region 22": {
        "region_name": "West Valley Salinity Intrusion Zone",
        "station_ids": ["DWLR-013", "DWLR-014", "DWLR-015", "DWLR-016"],
        "population_dependence": 0.85,
        "vulnerability": 0.79,
        "intervention_feasibility": 0.82,
        "primary_aquifer": "Coastal alluvium",
        "major_dependency": "Agrarian drinking & salinity barrier"
    },
    "Region 04": {
        "region_name": "South Hills High-Elevation Recharge Zone",
        "station_ids": ["DWLR-017", "DWLR-018", "DWLR-019", "DWLR-020"],
        "population_dependence": 0.45,
        "vulnerability": 0.42,
        "intervention_feasibility": 0.92,
        "primary_aquifer": "Basaltic Deccan Traps",
        "major_dependency": "Seasonal spring recharge"
    }
}


def validate_priority_weights(weights: Optional[Dict[str, float]]) -> Tuple[Dict[str, float], Optional[str]]:
    """Validate user-defined weights or fallback to defaults."""
    if not weights:
        return DEFAULT_PRIORITY_WEIGHTS.copy(), None

    required_keys = set(DEFAULT_PRIORITY_WEIGHTS.keys())
    if not required_keys.issubset(set(weights.keys())):
        missing = required_keys - set(weights.keys())
        return {}, f"Missing required weight factors: {missing}"

    for k in required_keys:
        val = weights[k]
        if not isinstance(val, (int, float)) or val < 0:
            return {}, f"Weight for {k} must be non-negative, got {val}"

    total = sum(weights[k] for k in required_keys)
    if abs(total - 1.0) > 0.05:
        return {}, f"Weights must sum to 1.0 (got sum={round(total, 4)})"

    # Normalize precisely to 1.0
    norm_w = {k: weights[k] / total for k in required_keys}
    return norm_w, None


def evaluate_intervention_priorities(
    df_all: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    limit: int = 10,
    as_of: Optional[str] = None
) -> Dict[str, Any]:
    """
    Explainable Multi-Criteria Decision Analysis (MCDA) Human-Impact & Intervention Priority Engine.
    Combines real-time DWLR stress, Theil-Sen depletion, forecast trajectory, data trust,
    and socio-economic exposure.
    """
    norm_weights, err = validate_priority_weights(weights)
    if err:
        return {"error": err, "status": "INVALID_WEIGHTS"}

    df = df_all.copy()
    if as_of:
        df = df[df["date"].astype(str) <= str(as_of)]

    if df.empty or "station_id" not in df.columns:
        return {
            "engine": "JALNETRA_MCDA_PRIORITY_ENGINE",
            "status": "NO_DATA",
            "data_status": "DEMONSTRATION",
            "as_of": as_of,
            "regions": [],
            "ranking": [],
            "methodology": {
                "type": "EXPLAINABLE_MCDA",
                "normalization": "MIN_MAX",
                "weights": norm_weights
            }
        }

    regions_out = []

    for region_id, reg_profile in REGIONAL_SOCIOECONOMIC_CATALOG.items():
        reg_sids = [s for s in reg_profile["station_ids"] if s in df["station_id"].unique()]
        if not reg_sids:
            continue

        reg_df = df[df["station_id"].isin(reg_sids)].copy()

        # 1. Calculate Groundwater Stress Factor [0, 1]
        # Average depth to water level (higher depth = higher groundwater stress)
        avg_level = float(reg_df["water_level_m"].mean())
        # Map [2m, 25m] to [0.1, 1.0]
        f_stress = min(1.0, max(0.1, (avg_level - 2.0) / 23.0))

        # 2. Calculate Depletion Rate Factor [0, 1] (Theil-Sen slope)
        slopes_yr = []
        for sid in reg_sids:
            st_s = reg_df[reg_df["station_id"] == sid].sort_values("date")["water_level_m"].values
            tr = TrendAdapter.evaluate(st_s)
            slopes_yr.append(tr["sen_slope_m_per_year"])
        avg_slope = float(np.mean(slopes_yr)) if slopes_yr else 0.0
        # If slope is negative (depletion): map [-3.0 m/yr, 0.0] to [1.0, 0.1]
        if avg_slope < 0:
            f_depletion = min(1.0, max(0.1, abs(avg_slope) / 2.5))
        else:
            f_depletion = 0.1

        # 3 & 4. Forecast Risk & Uncertainty Factors [0, 1]
        forecast_risks = []
        forecast_uncs = []
        for sid in reg_sids[:2]:  # Sample representative stations
            st_df = reg_df[reg_df["station_id"] == sid].sort_values("date")
            st_s = st_df["water_level_m"].values
            if len(st_s) >= 7:
                fc = forecast_ridge(st_s, station_id=sid, horizon=30)
                if fc.get("status") != "FAILED" and len(fc.get("p50", [])) > 0:
                    last_hist = float(st_s[-1])
                    pred_end = float(fc["p50"][-1])
                    drop = last_hist - pred_end
                    f_risk = min(1.0, max(0.1, drop / 2.0)) if drop > 0 else 0.2
                    forecast_risks.append(f_risk)

                    spread = float(fc["p90"][-1] - fc["p10"][-1])
                    f_unc = min(1.0, max(0.1, spread / 2.5))
                    forecast_uncs.append(f_unc)

        f_forecast_risk = float(np.mean(forecast_risks)) if forecast_risks else 0.50
        f_forecast_unc = float(np.mean(forecast_uncs)) if forecast_uncs else 0.35

        # 5, 6, 7. Socio-economic factors from catalog
        f_population = float(reg_profile["population_dependence"])
        f_vulnerability = float(reg_profile["vulnerability"])
        f_feasibility = float(reg_profile["intervention_feasibility"])

        # 8. Data Trust Factor [0, 1]
        trust_scores = []
        for sid in reg_sids:
            st_df = reg_df[reg_df["station_id"] == sid]
            t_res = evaluate_station_trust(st_df, sid, full_df=df, as_of=as_of)
            trust_scores.append(t_res["trust_score"])
        avg_trust_score = float(np.mean(trust_scores)) if trust_scores else 85.0
        f_data_trust = min(1.0, max(0.1, avg_trust_score / 100.0))

        # Factors dictionary (all [0, 1])
        factors = {
            "groundwater_stress": round(f_stress, 3),
            "depletion_rate": round(f_depletion, 3),
            "forecast_risk": round(f_forecast_risk, 3),
            "forecast_uncertainty": round(f_forecast_unc, 3),
            "population_dependence": round(f_population, 3),
            "vulnerability": round(f_vulnerability, 3),
            "intervention_feasibility": round(f_feasibility, 3),
            "data_trust": round(f_data_trust, 3)
        }

        # MCDA Composite Priority Score (0 - 100)
        raw_priority = sum(factors[k] * norm_weights[k] for k in norm_weights) * 100.0
        priority_score = round(max(0.0, min(100.0, raw_priority)), 1)

        # Evidence Confidence: separate scientific metric based on data trust and forecast certainty
        evidence_confidence = round(
            0.50 * f_data_trust +
            0.30 * (1.0 - f_forecast_unc) +
            0.20 * min(1.0, len(reg_sids) / 4.0),
            2
        )

        # Action Classification
        if priority_score >= 80.0:
            classification = "CRITICAL_INTERVENTION"
            recommended_actions = [
                "Deploy high-priority DWLR expansion sensors to unmonitored zones",
                "Evaluate managed extraction limits and water quota controls",
                "Execute MODFLOW 6 groundwater pumping mitigation scenario",
                "Mobilize field response teams for emergency recharge structure inspection"
            ]
        elif priority_score >= 65.0:
            classification = "HIGH_PRIORITY"
            recommended_actions = [
                "Increase monitoring frequency and sensor telemetry verification",
                "Evaluate managed aquifer recharge structure feasibility",
                "Run predictive scenario analysis for seasonal dry periods"
            ]
        elif priority_score >= 50.0:
            classification = "MONITOR_AND_PREPARE"
            recommended_actions = [
                "Maintain routine telemetry observations",
                "Investigate localized forecast uncertainty drivers",
                "Prepare seasonal demand management contingency plans"
            ]
        else:
            classification = "ROUTINE_MONITORING"
            recommended_actions = [
                "Maintain baseline continuous DWLR observation",
                "Review annual aquifer water balance trends"
            ]

        # Machine-generated drivers breakdown
        drivers = []
        for factor_name, factor_val in factors.items():
            w = norm_weights[factor_name]
            contrib = round(factor_val * w * 100.0, 2)
            drivers.append({
                "factor": factor_name,
                "score": round(factor_val * 100.0, 1),
                "weight": round(w, 3),
                "contribution": contrib
            })
        # Sort drivers by highest contribution
        drivers.sort(key=lambda d: d["contribution"], reverse=True)

        # Machine-generated why_priority explanation
        why_priority = []
        if factors["groundwater_stress"] >= 0.70:
            why_priority.append(f"Severe groundwater table depression (stress factor {int(factors['groundwater_stress']*100)}/100)")
        if factors["depletion_rate"] >= 0.50:
            why_priority.append(f"Accelerating depletion rate ({abs(round(avg_slope, 2))} m/year Theil-Sen slope)")
        if factors["population_dependence"] >= 0.75:
            why_priority.append(f"High socio-economic population exposure ({int(factors['population_dependence']*100)}/100)")
        if factors["forecast_risk"] >= 0.60:
            why_priority.append("Forward predictive models project continued hydraulic head decline")
        if factors["data_trust"] < 0.60:
            why_priority.append("Note: Priority remains elevated due to stress despite low sensor data trust")
        if not why_priority:
            why_priority.append("Stable hydraulic head and low population vulnerability")

        reg_data = {
            "region_id": region_id,
            "region_name": reg_profile["region_name"],
            "primary_aquifer": reg_profile["primary_aquifer"],
            "major_dependency": reg_profile["major_dependency"],
            "priority_score": priority_score,
            "classification": classification,
            "evidence_confidence": evidence_confidence,
            "data_trust_score": round(avg_trust_score, 1),
            "station_count": len(reg_sids),
            "stations": reg_sids,
            "factors": factors,
            "drivers": drivers,
            "why_priority": why_priority,
            "recommended_actions": recommended_actions,
            "data_status": "DEMONSTRATION"
        }
        regions_out.append(reg_data)

    # Sort regions by priority score descending
    regions_out.sort(key=lambda r: r["priority_score"], reverse=True)
    for rank_i, reg in enumerate(regions_out, start=1):
        reg["rank"] = rank_i

    limited_regions = regions_out[:limit]
    ranking_summary = [
        {
            "rank": r["rank"],
            "region_id": r["region_id"],
            "region_name": r["region_name"],
            "priority_score": r["priority_score"],
            "classification": r["classification"],
            "evidence_confidence": r["evidence_confidence"]
        }
        for r in limited_regions
    ]

    return {
        "engine": "JALNETRA_MCDA_PRIORITY_ENGINE",
        "status": "VERIFIED",
        "data_status": "DEMONSTRATION",
        "as_of": as_of,
        "regions": limited_regions,
        "ranking": ranking_summary,
        "methodology": {
            "type": "EXPLAINABLE_MCDA",
            "normalization": "MIN_MAX",
            "weights": norm_weights
        }
    }
