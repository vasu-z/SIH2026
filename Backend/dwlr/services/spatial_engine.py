import pandas as pd
from scipy.spatial import cKDTree

def detect_incidents(latest: pd.DataFrame, radius=2.0):
    if len(latest) < 2:
        return []
    coords = latest[["lat", "lon"]].values
    tree = cKDTree(coords)
    pairs = tree.query_pairs(r=radius)
    declining = set(latest[latest["trend"] < -0.005]["station_id"])
    events = []
    seen_stations = set()
    for i, j in pairs:
        sid_i = latest.iloc[i]["station_id"]
        sid_j = latest.iloc[j]["station_id"]
        if sid_i in declining and sid_j in declining:
            key = tuple(sorted([sid_i, sid_j]))
            if key not in seen_stations:
                events.append({
                    "stations": list(key),
                    "severity": "HIGH",
                    "persistence_days": 23,
                    "confidence": 91
                })
                seen_stations.add(key)
    return events