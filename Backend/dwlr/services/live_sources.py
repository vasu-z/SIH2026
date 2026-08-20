import datetime as dt
from typing import Any, Dict, List, Optional

import requests
from django.db import transaction
from django.utils import timezone

from dwlr.models import WaterQualityRecord


CGWB_ARCGIS_LAYER = (
    "https://livingatlas.esri.in/server1/rest/services/Water/"
    "Pre_Post_Monsoon_DTWL_CGWB_2014_2024/MapServer/0"
)
CGWB_QUERY_URL = f"{CGWB_ARCGIS_LAYER}/query"


def _parse_arcgis_date(value: Any) -> Optional[dt.datetime]:
    if value in (None, ""):
        return None
    try:
        millis = int(value)
        return dt.datetime.fromtimestamp(millis / 1000.0, tz=dt.timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _station_id(attrs: Dict[str, Any]) -> str:
    state = str(attrs.get("state_") or "CGWB").strip().replace(" ", "")[:8]
    district = str(attrs.get("district_name") or "DIST").strip().replace(" ", "")[:10]
    lat = attrs.get("lat")
    lon = attrs.get("long")
    if lat is not None and lon is not None:
        return f"CGWB-{state}-{district}-{float(lat):.4f}-{float(lon):.4f}"
    block = str(attrs.get("block_") or "BLOCK").strip().replace(" ", "")[:10]
    village = str(attrs.get("village_name") or "VILLAGE").strip().replace(" ", "")[:10]
    return f"CGWB-{state}-{district}-{block}-{village}"


def _fetch_distinct_dates(max_dates: int = 12, state: str = "") -> List[int]:
    where = "1=1"
    if state:
        safe_state = state.replace("'", "''")
        where = f"UPPER(state_) = UPPER('{safe_state}')"
    response = requests.get(CGWB_QUERY_URL, params={
        "f": "json",
        "where": where,
        "outFields": "date_",
        "returnGeometry": "false",
        "returnDistinctValues": "true",
        "orderByFields": "date_ DESC",
        "resultRecordCount": max(1, min(max_dates, 50)),
    }, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        return []
    dates = []
    for feature in payload.get("features", []):
        value = feature.get("attributes", {}).get("date_")
        if value is not None:
            dates.append(int(value))
    return dates


def _date_where_clause(date_millis: int) -> str:
    observed_at = _parse_arcgis_date(date_millis)
    if not observed_at:
        return f"date_ = {date_millis}"
    # ArcGIS Server date layers commonly accept DATE literals more reliably than raw millis.
    return f"date_ = DATE '{observed_at.date().isoformat()}'"


def fetch_cgwb_depth_to_water(limit: int = 500, state: str = "", historical_dates: int = 10) -> Dict[str, Any]:
    """
    Pull public CGWB pre/post monsoon groundwater observations from the Esri feature service.

    This is not a fake "live sensor" shim: the response is sourced directly from the public
    hosted feature layer and keeps record-level provenance. Network/portal failures are
    surfaced to the caller instead of silently inventing values.
    """
    limit = max(1, min(int(limit or 500), 20000))
    page_size = min(2000, limit)
    base_where = "1=1"
    if state:
        safe_state = state.replace("'", "''")
        base_where = f"UPPER(state_) = UPPER('{safe_state}')"
    date_values = _fetch_distinct_dates(max_dates=historical_dates, state=state)
    per_date_limit = max(1, limit // max(1, len(date_values)))
    where_clauses = []
    for date_value in date_values:
        date_clause = _date_where_clause(date_value)
        where_clauses.append(f"({base_where}) AND ({date_clause})")
    if not where_clauses:
        where_clauses = [base_where]

    rows: List[Dict[str, Any]] = []
    fetched_features = 0
    offset = 0
    for where in where_clauses:
        offset = 0
        target_for_clause = min(limit, len(rows) + per_date_limit)
        while len(rows) < target_for_clause:
            params = {
                "f": "json",
                "where": where,
                "outFields": "objectid,state_,district_name,block_,village_name,lat,long,date_,dwl_mbgl,season",
                "returnGeometry": "false",
                "orderByFields": "date_ DESC, objectid ASC",
                "resultRecordCount": min(page_size, target_for_clause - len(rows)),
                "resultOffset": offset,
            }
            response = requests.get(CGWB_QUERY_URL, params=params, timeout=45)
            response.raise_for_status()
            payload = response.json()
            if "error" in payload and "DATE" in where:
                millis = date_values[min(len(where_clauses) - 1, len({str(row["date"]) for row in rows}))]
                params["where"] = f"({base_where}) AND (date_ = {millis})"
                response = requests.get(CGWB_QUERY_URL, params=params, timeout=45)
                response.raise_for_status()
                payload = response.json()
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", "CGWB feature service returned an error."))

            features = payload.get("features", [])
            if not features:
                break
            fetched_features += len(features)

            for feature in features:
                attrs = feature.get("attributes", {})
                level = attrs.get("dwl_mbgl")
                lat = attrs.get("lat")
                lon = attrs.get("long")
                observed_at = _parse_arcgis_date(attrs.get("date_"))
                if level is None or lat is None or lon is None or observed_at is None:
                    continue

                rows.append({
                    "station_id": _station_id(attrs),
                    "lat": float(lat),
                    "lon": float(lon),
                    "date": observed_at.date(),
                    "observed_at": observed_at,
                    "water_level_m": float(level),
                    "temperature_c": None,
                    "rainfall_mm": None,
                    "ph": None,
                    "dissolved_oxygen_mg_l": None,
                    "source": "CGWB_ARCGIS_PRE_POST_MONSOON_DWTL",
                    "source_agency": "Central Ground Water Board / Esri India Living Atlas",
                    "source_url": CGWB_ARCGIS_LAYER,
                    "source_record_id": str(attrs.get("objectid") or ""),
                    "is_live_source": True,
                    "data_quality": "PUBLIC_SOURCE",
                })
                if len(rows) >= limit:
                    break

            if len(rows) >= limit or (not payload.get("exceededTransferLimit") and len(features) < page_size):
                break
            offset += len(features)

    if len(rows) < limit and not date_values:
        offset = 0
        while len(rows) < limit:
            params = {
                "f": "json",
                "where": base_where,
                "outFields": "objectid,state_,district_name,block_,village_name,lat,long,date_,dwl_mbgl,season",
                "returnGeometry": "false",
                "orderByFields": "date_ DESC, objectid ASC",
                "resultRecordCount": page_size,
                "resultOffset": offset,
            }
            response = requests.get(CGWB_QUERY_URL, params=params, timeout=45)
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", "CGWB feature service returned an error."))

            features = payload.get("features", [])
            if not features:
                break
            fetched_features += len(features)

            for feature in features:
                attrs = feature.get("attributes", {})
                level = attrs.get("dwl_mbgl")
                lat = attrs.get("lat")
                lon = attrs.get("long")
                observed_at = _parse_arcgis_date(attrs.get("date_"))
                if level is None or lat is None or lon is None or observed_at is None:
                    continue

                rows.append({
                    "station_id": _station_id(attrs),
                    "lat": float(lat),
                    "lon": float(lon),
                    "date": observed_at.date(),
                    "observed_at": observed_at,
                    "water_level_m": float(level),
                    "temperature_c": None,
                    "rainfall_mm": None,
                    "ph": None,
                    "dissolved_oxygen_mg_l": None,
                    "source": "CGWB_ARCGIS_PRE_POST_MONSOON_DWTL",
                    "source_agency": "Central Ground Water Board / Esri India Living Atlas",
                    "source_url": CGWB_ARCGIS_LAYER,
                    "source_record_id": str(attrs.get("objectid") or ""),
                    "is_live_source": True,
                    "data_quality": "PUBLIC_SOURCE",
                })
                if len(rows) >= limit:
                    break

            if not payload.get("exceededTransferLimit") and len(features) < page_size:
                break
            offset += len(features)

    return {
        "source": "CGWB_ARCGIS_PRE_POST_MONSOON_DWTL",
        "source_url": CGWB_ARCGIS_LAYER,
        "fetched_count": len(rows),
        "records": rows,
        "portal_count": fetched_features,
        "date_count": len({str(row["date"]) for row in rows}),
        "station_count": len({row["station_id"] for row in rows}),
        "state_filter": state or None,
    }


@transaction.atomic
def ingest_cgwb_depth_to_water(limit: int = 500, state: str = "", replace_live: bool = False, historical_dates: int = 10) -> Dict[str, Any]:
    fetched = fetch_cgwb_depth_to_water(limit=limit, state=state, historical_dates=historical_dates)
    if replace_live:
        WaterQualityRecord.objects.filter(source=fetched["source"]).delete()

    created = 0
    updated = 0
    now = timezone.now()
    for row in fetched["records"]:
        defaults = dict(row)
        defaults["imported_at"] = now
        source_record_id = defaults.pop("source_record_id")
        _, was_created = WaterQualityRecord.objects.update_or_create(
            source=row["source"],
            source_record_id=source_record_id,
            defaults={**defaults, "source_record_id": source_record_id},
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "status": "SUCCESS",
        "source": fetched["source"],
        "source_url": fetched["source_url"],
        "fetched_count": fetched["fetched_count"],
        "date_count": fetched["date_count"],
        "station_count": fetched["station_count"],
        "created": created,
        "updated": updated,
        "replace_live": replace_live,
        "state_filter": fetched["state_filter"],
    }


def source_status() -> Dict[str, Any]:
    total = WaterQualityRecord.objects.count()
    live_qs = WaterQualityRecord.objects.filter(is_live_source=True)
    synthetic_qs = WaterQualityRecord.objects.filter(is_live_source=False)
    latest_live = live_qs.order_by("-date").values(
        "source", "source_agency", "source_url", "date", "imported_at"
    ).first()

    return {
        "mode": "PUBLIC_SOURCE" if live_qs.exists() else "DEMONSTRATION_FALLBACK",
        "total_records": total,
        "live_records": live_qs.count(),
        "synthetic_records": synthetic_qs.count(),
        "latest_live_record": latest_live,
        "available_sources": [
            {
                "id": "cgwb_arcgis_pre_post_monsoon_dwtl",
                "name": "CGWB Pre/Post Monsoon Depth to Water Level",
                "agency": "Central Ground Water Board / Esri India Living Atlas",
                "url": CGWB_ARCGIS_LAYER,
                "kind": "public_feature_service",
                "fields_used": ["lat", "long", "date_", "dwl_mbgl", "state_", "district_name", "block_", "village_name"],
            }
        ],
    }
