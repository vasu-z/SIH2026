def optimize(interventions, budget):
    """Greedy cost-efficient knapsack: sort by risk_reduction per rupee, fill budget."""
    ranked = sorted(interventions, key=lambda i: i["risk_reduction"] / max(i["cost"], 1), reverse=True)
    selected = []
    spent = 0
    for item in ranked:
        if spent + item["cost"] <= budget:
            selected.append(item)
            spent += item["cost"]
    return {
        "selected": selected,
        "budget_used": spent,
        "budget_remaining": budget - spent
    }