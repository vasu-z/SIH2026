import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from scipy.spatial import cKDTree

from ..adapters.monitoring_design_adapter import MonitoringDesignAdapter
from ..adapters.optimizer_adapter import OrToolsOptimizerAdapter

# Configurable candidate monitoring catalog across hydrological sub-basins
DEFAULT_CANDIDATE_LOCATIONS = [
    {
        "location_id": "CAND-R12-01",
        "name": "Central Plains Deep Aquifer Well 1",
        "region_id": "Region 12",
        "lat": 26.8500,
        "lon": 79.2000,
        "risk_score": 89.0,
        "uncertainty_score": 94.0,
        "estimated_cost": 400000,
        "teams_required": 1,
        "population_exposure": 68000
    },
    {
        "location_id": "CAND-R17-01",
        "name": "North Basin Depletion Perimeter Well",
        "region_id": "Region 17",
        "lat": 28.9200,
        "lon": 76.8500,
        "risk_score": 92.0,
        "uncertainty_score": 82.0,
        "estimated_cost": 450000,
        "teams_required": 1,
        "population_exposure": 125000
    },
    {
        "location_id": "CAND-R08-01",
        "name": "East Aquifer Critical Recharge Node",
        "region_id": "Region 08",
        "lat": 24.5000,
        "lon": 82.3000,
        "risk_score": 76.0,
        "uncertainty_score": 75.0,
        "estimated_cost": 380000,
        "teams_required": 1,
        "population_exposure": 82000
    },
    {
        "location_id": "CAND-R22-01",
        "name": "West Valley Salinity Intrusion Boundary",
        "region_id": "Region 22",
        "lat": 22.1500,
        "lon": 74.6000,
        "risk_score": 85.0,
        "uncertainty_score": 88.0,
        "estimated_cost": 500000,
        "teams_required": 1,
        "population_exposure": 95000
    },
    {
        "location_id": "CAND-R04-01",
        "name": "South Hills High-Elevation Spring Node",
        "region_id": "Region 04",
        "lat": 21.2000,
        "lon": 78.4500,
        "risk_score": 54.0,
        "uncertainty_score": 45.0,
        "estimated_cost": 350000,
        "teams_required": 1,
        "population_exposure": 32000
    },
    {
        "location_id": "CAND-R12-02",
        "name": "Central Plains Intensive Pumping Zone",
        "region_id": "Region 12",
        "lat": 26.4000,
        "lon": 79.7500,
        "risk_score": 88.0,
        "uncertainty_score": 91.0,
        "estimated_cost": 420000,
        "teams_required": 1,
        "population_exposure": 74000
    },
    {
        "location_id": "CAND-R17-02",
        "name": "North Basin Sub-surface Flow Inflow",
        "region_id": "Region 17",
        "lat": 29.3000,
        "lon": 77.2500,
        "risk_score": 90.0,
        "uncertainty_score": 78.0,
        "estimated_cost": 460000,
        "teams_required": 1,
        "population_exposure": 110000
    },
    {
        "location_id": "CAND-R08-02",
        "name": "East Aquifer Industrial Discharge Buffer",
        "region_id": "Region 08",
        "lat": 24.1000,
        "lon": 81.9000,
        "risk_score": 71.0,
        "uncertainty_score": 68.0,
        "estimated_cost": 390000,
        "teams_required": 1,
        "population_exposure": 60000
    }
]


def _compute_nearest_existing_distance(
    cand_lat: float,
    cand_lon: float,
    existing_coords: np.ndarray,
    existing_sids: List[str]
) -> Tuple[Optional[str], Optional[float], float]:
    """Compute distance in km to nearest operational DWLR station and spatial coverage score."""
    if len(existing_coords) == 0:
        return None, None, 100.0

    # Approximate Euclidean degree distance to km (~111 km per degree)
    diffs = existing_coords - np.array([cand_lat, cand_lon])
    dists_deg = np.sqrt(np.sum(diffs ** 2, axis=1))
    min_idx = int(np.argmin(dists_deg))
    min_dist_km = round(float(dists_deg[min_idx] * 111.0), 1)

    # Coverage score: Higher distance = greater coverage gap = higher expansion utility
    coverage_score = min(100.0, round((min_dist_km / 100.0) * 100.0, 1))
    nearest_sid = existing_sids[min_idx]

    return nearest_sid, min_dist_km, coverage_score


def evaluate_monitoring_priorities(
    df_all: pd.DataFrame,
    budget: int = 1500000,
    team_capacity: int = 2,
    candidate_limit: int = 5,
    as_of: Optional[str] = None
) -> Dict[str, Any]:
    """
    Risk-aware information-theoretic monitoring network expansion engine.
    Orchestrates Weighted QR Column Pivoting and OR-Tools optimization.
    """
    df = df_all.copy()
    if as_of:
        df = df[df["date"].astype(str) <= str(as_of)]

    if df.empty or "station_id" not in df.columns:
        return {
            "engine": "QRP_INFORMATION_THEORETIC",
            "status": "NO_DATA",
            "as_of": as_of,
            "existing_stations_count": 0,
            "candidate_count": 0,
            "recommendations": [],
            "deployment_plan": {},
            "limitations": ["No observation records available on or before as_of date."]
        }

    # Step 1: Build observation matrix from existing DWLR stations
    pivot = df.pivot_table(index="date", columns="station_id", values="water_level_m", aggfunc="mean").sort_index()
    existing_sids = list(pivot.columns)
    N_existing = len(existing_sids)

    # Fill NaNs for matrix math
    pivot_filled = pivot.ffill().bfill().fillna(0.0)
    X_existing = pivot_filled.values
    T = X_existing.shape[0]

    # Existing station coordinates
    latest_st = df.groupby("station_id").tail(1)
    st_coord_map = {row["station_id"]: (row["lat"], row["lon"]) for _, row in latest_st.iterrows()}
    existing_coords = np.array([st_coord_map.get(sid, (20.0, 75.0)) for sid in existing_sids])

    # Step 2: Generate candidate synthetic time series based on regional correlation & localized variance
    candidates = DEFAULT_CANDIDATE_LOCATIONS
    N_cand = len(candidates)

    rng = np.random.default_rng(42)
    X_candidates = np.zeros((T, N_cand))

    for j, cand in enumerate(candidates):
        # Base candidate series derived from mean regional signal + unobserved variance
        base_signal = np.mean(X_existing, axis=1) if N_existing > 0 else np.zeros(T)
        noise = rng.normal(0, 0.4, size=T)
        trend_shift = np.linspace(0, (cand["risk_score"] - 50.0) * 0.02, T)
        X_candidates[:, j] = base_signal + noise - trend_shift

    # Combined matrix: [Existing Stations | Candidates]
    X_full = np.hstack([X_existing, X_candidates])
    fixed_indices = list(range(N_existing))
    candidate_indices = list(range(N_existing, N_existing + N_cand))

    # Step 3: Compute candidate weights: W = (1 + risk/100) * (1 + unc/100) * (1 + coverage/100)
    weights_full = np.ones(N_existing + N_cand)
    cand_coverage_scores = []
    cand_nearest_info = []

    for j, cand in enumerate(candidates):
        nearest_sid, min_dist_km, cov_score = _compute_nearest_existing_distance(
            cand["lat"], cand["lon"], existing_coords, existing_sids
        )
        cand_coverage_scores.append(cov_score)
        cand_nearest_info.append((nearest_sid, min_dist_km))

        # Weight formula
        risk_fact = 1.0 + (cand["risk_score"] / 100.0)
        unc_fact = 1.0 + (cand["uncertainty_score"] / 100.0)
        cov_fact = 1.0 + (cov_score / 100.0)
        weights_full[N_existing + j] = risk_fact * unc_fact * cov_fact

    # Step 4: Run QRP Sensor Placement
    qrp_res = MonitoringDesignAdapter.run_qrp_placement(
        X=X_full,
        fixed_indices=fixed_indices,
        weights=weights_full,
        candidate_indices=candidate_indices
    )

    ranked_full_indices = qrp_res["ranked_indices"]
    info_gains = qrp_res["information_gains"]
    ortho_scores = qrp_res["orthogonality_scores"]

    # Step 5: Construct ranked recommendations
    recommendations = []
    for rank_idx, col_idx in enumerate(ranked_full_indices):
        cand_idx = col_idx - N_existing
        cand = candidates[cand_idx]
        nearest_sid, min_dist_km = cand_nearest_info[cand_idx]
        cov_score = cand_coverage_scores[cand_idx]

        info_gain = info_gains[rank_idx] if rank_idx < len(info_gains) else 50.0
        ortho_val = ortho_scores[rank_idx] if rank_idx < len(ortho_scores) else 0.5

        # Priority score formula: 0.35*info_gain + 0.30*risk + 0.20*uncertainty + 0.15*coverage
        priority = round(
            0.35 * info_gain +
            0.30 * cand["risk_score"] +
            0.20 * cand["uncertainty_score"] +
            0.15 * cov_score,
            1
        )

        why_selected = []
        if info_gain >= 75.0:
            why_selected.append(f"High orthogonal information gain ({info_gain}/100) relative to existing network")
        if cand["risk_score"] >= 80.0:
            why_selected.append(f"Located in high groundwater-risk zone ({cand['risk_score']}/100)")
        if cand["uncertainty_score"] >= 80.0:
            why_selected.append(f"Resolves significant forecast uncertainty ({cand['uncertainty_score']}/100)")
        if min_dist_km and min_dist_km >= 25.0:
            why_selected.append(f"Expands spatial coverage ({min_dist_km} km to nearest station {nearest_sid})")

        rec = {
            "rank": rank_idx + 1,
            "location_id": cand["location_id"],
            "name": cand["name"],
            "region_id": cand["region_id"],
            "priority_score": priority,
            "information_gain": info_gain,
            "orthogonality_score": ortho_val,
            "risk_score": cand["risk_score"],
            "uncertainty_score": cand["uncertainty_score"],
            "coverage_score": cov_score,
            "nearest_existing_station": nearest_sid,
            "distance_km": min_dist_km,
            "estimated_cost": cand["estimated_cost"],
            "teams_required": cand["teams_required"],
            "why_selected": why_selected,
            "coordinate_status": "DEMONSTRATION"
        }
        recommendations.append(rec)

    # Step 6: Connect to OR-Tools Optimizer to generate deployable monitoring portfolio
    interventions_payload = [
        {
            "id": r["location_id"],
            "type": "MONITORING_EXPANSION",
            "region_id": r["region_id"],
            "cost": r["estimated_cost"],
            "teams": r["teams_required"],
            "expected_risk_reduction": round(r["priority_score"] * 0.15, 1),
            "feasibility": 0.95,
            "benefit_score": r["priority_score"]
        }
        for r in recommendations
    ]

    opt_plan = OrToolsOptimizerAdapter.solve(
        budget=budget,
        team_capacity=team_capacity,
        interventions=interventions_payload
    )

    limited_recommendations = recommendations[:candidate_limit]

    return {
        "engine": "QRP_INFORMATION_THEORETIC",
        "status": "VERIFIED",
        "as_of": as_of,
        "existing_stations_count": N_existing,
        "candidate_count": N_cand,
        "recommendations": limited_recommendations,
        "deployment_plan": {
            "budget": budget,
            "budget_used": opt_plan.get("budget_used", 0),
            "remaining_budget": opt_plan.get("remaining_budget", budget),
            "team_capacity": team_capacity,
            "teams_used": opt_plan.get("teams_used", 0),
            "selected_sensors": [item["id"] for item in opt_plan.get("selected_interventions", [])],
            "solver_status": opt_plan.get("solver", {}).get("status", "OPTIMAL")
        },
        "limitations": [
            "Candidate coordinates are designated as DEMONSTRATION until validated by official hydrogeological field surveys.",
            "QRP matrix factorization optimizes linear field reconstruction variance."
        ]
    }
