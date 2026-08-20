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