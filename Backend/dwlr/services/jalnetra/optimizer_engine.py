import logging
from typing import Dict, Any, List, Tuple, Optional
from ..adapters.optimizer_adapter import OrToolsOptimizerAdapter
from ..optimizer import optimize as greedy_optimize

logger = logging.getLogger(__name__)

DEFAULT_REGIONS = [
    {"region_id": "R17", "name": "Region 17 (North Basin)", "risk": 91, "population": 142000, "uncertainty": 0.82},
    {"region_id": "R08", "name": "Region 08 (East Aquifer)", "risk": 74, "population": 88000, "uncertainty": 0.65},
    {"region_id": "R12", "name": "Region 12 (Central Plains)", "risk": 68, "population": 62000, "uncertainty": 0.94},
    {"region_id": "R04", "name": "Region 04 (South Hills)", "risk": 52, "population": 35000, "uncertainty": 0.40},
    {"region_id": "R22", "name": "Region 22 (West Valley)", "risk": 84, "population": 115000, "uncertainty": 0.70},
]

DEFAULT_INTERVENTIONS = [
    {
        "id": "RS-R17-01",
        "type": "RECHARGE_STRUCTURE",
        "region_id": "R17",
        "region": "Region 17",
        "cost": 1500000,
        "teams": 1,
        "expected_risk_reduction": 27,
        "feasibility": 0.92
    },
    {
        "id": "DM-R08-01",
        "type": "DEMAND_MANAGEMENT",
        "region_id": "R08",
        "region": "Region 08",
        "cost": 800000,
        "teams": 1,
        "expected_risk_reduction": 15,
        "feasibility": 0.88
    },
    {
        "id": "ME-R12-01",
        "type": "MONITORING_EXPANSION",
        "region_id": "R12",
        "region": "Region 12",
        "cost": 400000,
        "teams": 1,
        "expected_risk_reduction": 9,
        "feasibility": 0.95
    },
    {
        "id": "RS-R22-01",
        "type": "RECHARGE_STRUCTURE",
        "region_id": "R22",
        "region": "Region 22",
        "cost": 1800000,
        "teams": 2,
        "expected_risk_reduction": 24,
        "feasibility": 0.85
    },
    {
        "id": "DM-R17-02",
        "type": "DEMAND_MANAGEMENT",
        "region_id": "R17",
        "region": "Region 17",
        "cost": 1000000,
        "teams": 1,
        "expected_risk_reduction": 18,
        "feasibility": 0.90
    },
    {
        "id": "ME-R04-01",
        "type": "MONITORING_EXPANSION",
        "region_id": "R04",
        "region": "Region 04",
        "cost": 500000,
        "teams": 1,
        "expected_risk_reduction": 7,
        "feasibility": 0.96
    }
]


def validate_optimizer_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Validate optimizer input payload constraints."""
    try:
        raw_budget = data.get("budget", 5000000)
        raw_teams = data.get("team_capacity", data.get("teams", 3))

        budget = int(raw_budget)
        team_capacity = int(raw_teams)

        if budget <= 0:
            return False, f"Budget must be a positive integer (received {budget}).", {}

        if team_capacity <= 0:
            return False, f"Team capacity must be at least 1 team (received {team_capacity}).", {}

        interventions = data.get("interventions", DEFAULT_INTERVENTIONS)
        if not isinstance(interventions, list) or len(interventions) == 0:
            return False, "Interventions list cannot be empty.", {}

        for i, item in enumerate(interventions):
            cost = int(item.get("cost", 0))
            if cost < 0:
                return False, f"Intervention #{i+1} has invalid negative cost: {cost}", {}

        regions = data.get("regions", DEFAULT_REGIONS)

        return True, None, {
            "budget": budget,
            "team_capacity": team_capacity,
            "interventions": interventions,
            "regions": regions
        }
    except (ValueError, TypeError) as e:
        return False, f"Malformed optimizer payload: {e}", {}


def execute_optimization(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Execute constrained decision optimization using OR-Tools CP-SAT.
    Falls back gracefully to greedy algorithm if OR-Tools is unavailable.
    """
    valid, error_msg, validated = validate_optimizer_payload(data)
    if not valid:
        return {"error": "Invalid optimization parameters", "details": error_msg}, 400

    budget = validated["budget"]
    team_capacity = validated["team_capacity"]
    interventions = validated["interventions"]
    regions = validated["regions"]

    # Solve with OR-Tools
    result = OrToolsOptimizerAdapter.solve(
        budget=budget,
        team_capacity=team_capacity,
        interventions=interventions,
        regions=regions
    )

    if result.get("status") == "VERIFIED":
        return result, 200

    # Fallback to greedy optimizer if unavailable
    greedy_res = greedy_optimize(interventions, budget)
    return {
        "engine": "GREEDY_FALLBACK",
        "status": "FALLBACK",
        "execution": "SUCCESS",
        "budget": budget,
        "budget_used": greedy_res.get("budget_used", 0),
        "remaining_budget": greedy_res.get("budget_remaining", budget),
        "team_capacity": team_capacity,
        "selected_interventions": greedy_res.get("selected", []),
        "fallback_reason": result.get("reason", "OR-Tools solver not available.")
    }, 200
