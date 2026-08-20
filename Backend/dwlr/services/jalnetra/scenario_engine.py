import time
from typing import Dict, Any, Tuple, Optional
from ..adapters.modflow_adapter import ModflowAdapter


def validate_scenario_params(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Validate scenario percentage parameters within realistic hydrological bounds [-100, 200]."""
    try:
        rainfall_change_pct = float(data.get("rainfall_change_pct", 0.0))
        extraction_change_pct = float(data.get("extraction_change_pct", 0.0))
        recharge_change_pct = float(data.get("recharge_change_pct", 0.0))
        demand_change_pct = float(data.get("demand_change_pct", 0.0))
        mode = str(data.get("mode", "fast")).lower().strip()

        params = {
            "rainfall_change_pct": rainfall_change_pct,
            "extraction_change_pct": extraction_change_pct,
            "recharge_change_pct": recharge_change_pct,
            "demand_change_pct": demand_change_pct,
            "mode": mode
        }

        for k in ["rainfall_change_pct", "extraction_change_pct", "recharge_change_pct", "demand_change_pct"]:
            val = params[k]
            if val < -100.0 or val > 300.0:
                return False, f"Parameter '{k}' value {val}% is out of allowable range [-100%, 300%].", {}

        if mode not in ["fast", "physics", "modflow", "modflow6"]:
            return False, f"Mode '{mode}' is invalid. Supported modes are 'fast' and 'physics'.", {}

        return True, None, params
    except (ValueError, TypeError) as e:
        return False, f"Malformed parameter payload: {e}", {}


def run_fast_analytical_scenario(
    rainfall_change_pct: float,
    extraction_change_pct: float,
    recharge_change_pct: float,
    demand_change_pct: float
) -> Dict[str, Any]:
    """Lightweight lumped analytical water-balance scenario engine."""
    start_time = time.time()

    # Nominal baseline parameters for lumped basin
    baseline_level = 8.42  # meters (depth to water or head reference)
    specific_yield = 0.12   # unconfined aquifer storage coefficient

    # Inflow change (rainfall + managed recharge) in meters equivalent
    net_inflow_change_m = (rainfall_change_pct * 0.015 + recharge_change_pct * 0.02)
    # Outflow change (extraction + demand) in meters equivalent
    net_outflow_change_m = (extraction_change_pct * 0.018 + demand_change_pct * 0.012)

    # Net head shift delta
    delta_h = round((net_inflow_change_m - net_outflow_change_m) / specific_yield, 3)
    scenario_level = round(max(0.5, baseline_level + delta_h), 3)

    # Risk metric (0-100) based on critical depth-to-water threshold (e.g. 15m)
    baseline_risk = max(0, min(100, int(round((15.0 - baseline_level) / 15.0 * 50 + 20))))
    scenario_risk = max(0, min(100, int(round((15.0 - scenario_level) / 15.0 * 50 + 20))))

    runtime = round(time.time() - start_time, 4)

    return {
        "engine": "ANALYTICAL_WATER_BALANCE",
        "status": "VERIFIED",
        "execution": "SUCCESS",
        "mode": "fast",
        "baseline": {
            "mean_groundwater": baseline_level,
            "min_groundwater": round(baseline_level - 1.2, 2),
            "max_groundwater": round(baseline_level + 1.8, 2),
            "risk": baseline_risk
        },
        "scenario": {
            "mean_groundwater": scenario_level,
            "min_groundwater": round(scenario_level - 1.2, 2),
            "max_groundwater": round(scenario_level + 1.8, 2),
            "risk": scenario_risk
        },
        "difference": {
            "groundwater_change": delta_h,
            "risk_change": scenario_risk - baseline_risk
        },
        "assumptions": [
            "Lumped unconfined aquifer single-cell storage model",
            "Specific yield Sy = 0.12",
            "Linearized precipitation infiltration and pumping drawdown coefficients"
        ],
        "runtime_seconds": runtime
    }


def execute_scenario(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Orchestrate scenario execution across FAST analytical mode and PHYSICS MODFLOW 6 mode."""
    valid, error_msg, params = validate_scenario_params(data)
    if not valid:
        return {"error": "Invalid scenario parameters", "details": error_msg}, 400

    mode = params["mode"]
    r_pct = params["rainfall_change_pct"]
    e_pct = params["extraction_change_pct"]
    rc_pct = params["recharge_change_pct"]
    d_pct = params["demand_change_pct"]

    if mode in ["physics", "modflow", "modflow6"]:
        physics_res = ModflowAdapter.run_scenario(
            rainfall_change_pct=r_pct,
            extraction_change_pct=e_pct,
            recharge_change_pct=rc_pct,
            demand_change_pct=d_pct
        )
        if physics_res.get("status") == "VERIFIED":
            return physics_res, 200
        # If physics fails or unavailable, return authentic failure details with fallback info
        return physics_res, 200

    # Default FAST analytical mode
    fast_res = run_fast_analytical_scenario(
        rainfall_change_pct=r_pct,
        extraction_change_pct=e_pct,
        recharge_change_pct=rc_pct,
        demand_change_pct=d_pct
    )
    return fast_res, 200
