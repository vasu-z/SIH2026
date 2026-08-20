from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
import pandas as pd
from .models import WaterQualityRecord
from .serializers import WaterQualityRecordSerializer
from .services.trust_engine import score_trust
from .services.spatial_engine import detect_incidents
from .services.forecast_engine import forecast_station
from .services.optimizer import optimize


class WaterQualityRecordViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityRecord.objects.all()
    serializer_class = WaterQualityRecordSerializer


def _load_df():
    qs = WaterQualityRecord.objects.all().values(
        "station_id", "lat", "lon", "date", "water_level_m",
        "temperature_c", "rainfall_mm", "ph", "dissolved_oxygen_mg_l"
    )
    df = pd.DataFrame(list(qs))
    df["ph"] = df["ph"].astype(float)
    return df


def _latest_with_trend():
    df = _load_df()
    df = df.sort_values("date")
    trends = df.groupby("station_id")["water_level_m"].apply(
        lambda s: s.diff().mean()
    ).rename("trend")
    latest = df.groupby("station_id").tail(1).copy()
    latest = latest.merge(trends, on="station_id")
    return latest


@api_view(["GET"])
def stations_view(request):
    latest = _latest_with_trend()
    return Response(latest.to_dict("records"))


@api_view(["GET"])
def trust_view(request, station_id):
    df = _load_df()
    station_df = df[df["station_id"] == station_id]
    if station_df.empty:
        return Response({"error": "station not found"}, status=404)
    scored = score_trust(station_df)
    latest_row = scored.sort_values("date").tail(1).iloc[0]
    return Response({
        "station_id": station_id,
        "trust_score": round(float(latest_row["trust_score"]), 1),
        "status": latest_row["status"],
        "history": scored[["date", "water_level_m", "trust_score", "status"]].to_dict("records")
    })


@api_view(["GET"])
def incidents_view(request):
    latest = _latest_with_trend()
    events = detect_incidents(latest)
    return Response(events)


@api_view(["GET"])
def forecast_view(request, station_id):
    df = _load_df()
    station_df = df[df["station_id"] == station_id].sort_values("date")
    if station_df.empty:
        return Response({"error": "station not found"}, status=404)
    model_name = request.GET.get("model", "ridge")
    result = forecast_station(
        series=station_df["water_level_m"].values,
        station_id=station_id,
        model_name=model_name,
        full_df=df
    )
    return Response(result)


@api_view(["POST"])
def optimize_view(request):
    interventions = request.data.get("interventions", [
        {"name": "Recharge Structure", "region": "Region 17", "cost": 1500000, "risk_reduction": 27},
        {"name": "Demand Management", "region": "Region 08", "cost": 800000, "risk_reduction": 15},
        {"name": "Monitoring Expansion", "region": "Region 12", "cost": 400000, "risk_reduction": 9},
    ])
    budget = request.data.get("budget", 5000000)
    result = optimize(interventions, budget)
    return Response(result)


@api_view(["POST"])
def scenario_run_view(request):
    from .services.jalnetra.scenario_engine import execute_scenario
    payload = request.data if isinstance(request.data, dict) else {}
    result, status_code = execute_scenario(payload)
    return Response(result, status=status_code)


@api_view(["POST"])
def jalnetra_optimizer_run_view(request):
    from .services.jalnetra.optimizer_engine import execute_optimization
    payload = request.data if isinstance(request.data, dict) else {}
    result, status_code = execute_optimization(payload)
    return Response(result, status=status_code)


@api_view(["GET"])
def jalnetra_trust_view(request, station_id):
    from .services.jalnetra.trust_engine import evaluate_station_trust
    df = _load_df()
    station_df = df[df["station_id"] == station_id]
    if station_df.empty:
        return Response({"error": "station not found"}, status=404)
    as_of = request.GET.get("as_of")
    result = evaluate_station_trust(station_df, station_id, full_df=df, as_of=as_of)
    return Response(result)


@api_view(["GET"])
def jalnetra_incidents_view(request):
    from .services.jalnetra.incident_engine import detect_regional_incidents
    df = _load_df()
    as_of = request.GET.get("as_of")
    incidents = detect_regional_incidents(df, as_of=as_of)
    return Response(incidents)


@api_view(["GET", "POST"])
def jalnetra_monitoring_priority_view(request):
    from .services.jalnetra.monitoring_engine import evaluate_monitoring_priorities
    df = _load_df()
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        budget = int(data.get("budget", 1500000))
        team_capacity = int(data.get("team_capacity", data.get("teams", 2)))
        candidate_limit = int(data.get("candidate_limit", data.get("limit", 5)))
        as_of = data.get("as_of")
    else:
        budget = int(request.GET.get("budget", 1500000))
        team_capacity = int(request.GET.get("team_capacity", request.GET.get("teams", 2)))
        candidate_limit = int(request.GET.get("candidate_limit", request.GET.get("limit", 5)))
        as_of = request.GET.get("as_of")

    result = evaluate_monitoring_priorities(
        df_all=df,
        budget=budget,
        team_capacity=team_capacity,
        candidate_limit=candidate_limit,
        as_of=as_of
    )
    return Response(result)


@api_view(["GET", "POST"])
def jalnetra_priority_view(request):
    from .services.jalnetra.priority_engine import evaluate_intervention_priorities
    df = _load_df()
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        weights = data.get("weights")
        limit = int(data.get("limit", 10))
        as_of = data.get("as_of")
    else:
        weights = None
        limit = int(request.GET.get("limit", 10))
        as_of = request.GET.get("as_of")

    result = evaluate_intervention_priorities(
        df_all=df,
        weights=weights,
        limit=limit,
        as_of=as_of
    )
    if "error" in result:
        return Response(result, status=400)
    return Response(result)


@api_view(["GET", "POST"])
def jalnetra_unified_decision_view(request):
    from .services.jalnetra.unified_engine import run_unified_decision_pipeline
    df = _load_df()
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        budget = int(data.get("budget", 5000000))
        team_capacity = int(data.get("team_capacity", data.get("teams", 3)))
        pumping_red = float(data.get("pumping_reduction_pct", 20.0))
        recharge_rate = float(data.get("recharge_m3_day", 500.0))
        as_of = data.get("as_of")
    else:
        budget = int(request.GET.get("budget", 5000000))
        team_capacity = int(request.GET.get("team_capacity", request.GET.get("teams", 3)))
        pumping_red = float(request.GET.get("pumping_reduction_pct", 20.0))
        recharge_rate = float(request.GET.get("recharge_m3_day", 500.0))
        as_of = request.GET.get("as_of")

    result = run_unified_decision_pipeline(
        df_all=df,
        budget=budget,
        team_capacity=team_capacity,
        scenario_pumping_reduction_pct=pumping_red,
        scenario_recharge_m3_day=recharge_rate,
        as_of=as_of
    )
    return Response(result)


def command_center_view(request):
    from django.shortcuts import render
    return render(request, 'command_center.html')