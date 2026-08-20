import time
import math
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def _generate_why_selected(item: Dict[str, Any], region_info: Dict[str, Any]) -> List[str]:
    """Generate deterministic, explainable reasons based strictly on scoring factors and input parameters."""
    reasons = []
    reg_risk = region_info.get("risk", 50)
    reg_pop = region_info.get("population", 10000)
    risk_red = item.get("expected_risk_reduction", 10)
    feasibility = item.get("feasibility", 1.0)
    teams = item.get("teams", 1)

    if reg_risk >= 70:
        reasons.append(f"High regional groundwater risk index ({reg_risk}/100)")
    elif reg_risk >= 50:
        reasons.append(f"Moderate regional water stress ({reg_risk}/100)")

    if reg_pop >= 50000:
        reasons.append(f"Protects significant vulnerable population ({reg_pop:,} residents)")

    if risk_red >= 15:
        reasons.append(f"Strong expected risk reduction impact ({risk_red}%)")
    else:
        reasons.append(f"Modeled risk reduction contribution ({risk_red}%)")

    if feasibility >= 0.8:
        reasons.append(f"High operational feasibility score ({int(feasibility * 100)}%)")

    reasons.append(f"Optimal return under available budget and team capacity ({teams} team required)")
    return reasons


class OrToolsOptimizerAdapter:
    """
    Isolated adapter for Google OR-Tools CP-SAT discrete multi-constraint optimizer.
    """

    @classmethod
    def is_available(cls) -> bool:
        try:
            from ortools.sat.python import cp_model
            return True
        except ImportError:
            return False

    @classmethod
    def solve(
        cls,
        budget: int,
        team_capacity: int,
        interventions: List[Dict[str, Any]],
        regions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Solve exact binary knapsack portfolio optimization subject to budget & team capacity constraints.
        """
        start_time = time.time()
        try:
            from ortools.sat.python import cp_model
        except ImportError as e:
            return {
                "engine": "OR-TOOLS",
                "status": "UNAVAILABLE",
                "execution": "FAILED",
                "reason": f"Google OR-Tools is not available in Python environment: {e}",
                "fallback": "existing_greedy_optimizer"
            }

        try:
            region_map = {r.get("region_id", ""): r for r in (regions or [])}

            model = cp_model.CpModel()
            decision_vars = []
            benefit_scores = []

            for i, item in enumerate(interventions):
                var = model.NewBoolVar(f"x_{i}")
                decision_vars.append(var)

                # Regional metadata factors
                reg_id = item.get("region_id") or item.get("region") or ""
                reg_data = region_map.get(reg_id, {})
                reg_risk = float(reg_data.get("risk", 50.0))
                reg_pop = float(reg_data.get("population", 10000.0))
                reg_unc = float(reg_data.get("uncertainty", 0.5))

                risk_red = float(item.get("expected_risk_reduction", item.get("risk_reduction", 10.0)))
                feasibility = float(item.get("feasibility", 1.0))

                # Benefit formulation: risk_reduction * (1 + risk/100) * log10(pop + 10) * (1 + unc/2) * feasibility
                pop_factor = math.log10(max(10.0, reg_pop))
                risk_factor = 1.0 + (reg_risk / 100.0)
                unc_factor = 1.0 + (reg_unc * 0.5)

                raw_benefit = risk_red * risk_factor * pop_factor * unc_factor * feasibility
                integer_benefit = int(round(raw_benefit * 100.0))
                benefit_scores.append((raw_benefit, integer_benefit))

            # Constraint 1: Budget limit
            cost_expr = sum(
                decision_vars[i] * int(item.get("cost", 0))
                for i, item in enumerate(interventions)
            )
            model.Add(cost_expr <= int(budget))

            # Constraint 2: Field/team capacity limit
            team_expr = sum(
                decision_vars[i] * int(item.get("teams", 1))
                for i, item in enumerate(interventions)
            )
            model.Add(team_expr <= int(team_capacity))

            # Objective: Maximize total weighted benefit
            objective_expr = sum(
                decision_vars[i] * benefit_scores[i][1]
                for i in range(len(interventions))
            )
            model.Maximize(objective_expr)

            # Solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 10.0
            solver_status = solver.Solve(model)
            status_name = solver.StatusName(solver_status)

            if solver_status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                return {
                    "engine": "OR-TOOLS",
                    "status": "INFEASIBLE",
                    "execution": "FAILED",
                    "reason": f"No feasible intervention portfolio found under budget ₹{budget:,} and {team_capacity} teams.",
                    "fallback": "existing_greedy_optimizer"
                }

            selected = []
            unselected = []
            spent_budget = 0
            spent_teams = 0
            total_risk_red = 0.0

            for i, item in enumerate(interventions):
                reg_id = item.get("region_id") or item.get("region") or ""
                reg_data = region_map.get(reg_id, {})
                cost = int(item.get("cost", 0))
                teams = int(item.get("teams", 1))
                risk_red = float(item.get("expected_risk_reduction", item.get("risk_reduction", 0.0)))
                benefit_val = round(benefit_scores[i][0], 2)

                formatted_item = dict(item)
                formatted_item["id"] = item.get("id", f"INT-{i+1:02d}")
                formatted_item["region_id"] = reg_id
                formatted_item["type"] = item.get("type", item.get("name", "INTERVENTION"))
                formatted_item["cost"] = cost
                formatted_item["teams"] = teams
                formatted_item["expected_risk_reduction"] = risk_red
                formatted_item["benefit_score"] = benefit_val

                if solver.Value(decision_vars[i]) == 1:
                    formatted_item["why_selected"] = _generate_why_selected(formatted_item, reg_data)
                    selected.append(formatted_item)
                    spent_budget += cost
                    spent_teams += teams
                    total_risk_red += risk_red
                else:
                    unselected.append(formatted_item)

            runtime = round(time.time() - start_time, 4)

            return {
                "engine": "OR-TOOLS",
                "status": "VERIFIED",
                "execution": "SUCCESS",
                "budget": budget,
                "budget_used": spent_budget,
                "remaining_budget": budget - spent_budget,
                "team_capacity": team_capacity,
                "teams_used": spent_teams,
                "remaining_teams": team_capacity - spent_teams,
                "selected_interventions": selected,
                "unselected_interventions": unselected,
                "total_expected_risk_reduction": round(total_risk_red, 2),
                "objective_value": round(solver.ObjectiveValue() / 100.0, 2),
                "solver": {
                    "name": "OR-TOOLS CP-SAT",
                    "status": status_name,
                    "runtime_seconds": runtime
                }
            }

        except Exception as e:
            logger.exception("OR-Tools optimizer solver failed:")
            return {
                "engine": "OR-TOOLS",
                "status": "UNAVAILABLE",
                "execution": "FAILED",
                "reason": str(e),
                "fallback": "existing_greedy_optimizer"
            }
