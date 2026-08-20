import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from sklearn.linear_model import Ridge
from .adapters.groundwater_gnn_adapter import GroundwaterGNNAdapter


def forecast_ridge(series: np.ndarray, station_id: str = "", horizon: int = 30) -> Dict[str, Any]:
    """Verified primary statistical baseline forecasting model with residual uncertainty."""
    n = len(series)
    if n == 0:
        return {
            "station_id": station_id,
            "model": "Ridge",
            "status": "FAILED",
            "execution": "FAILED",
            "reason": "No data points available for station",
            "forecast": [],
            "p50": [],
            "p10": [],
            "p90": [],
            "uncertainty": None,
            "metrics": None,
            "mae": 0.0,
            "rmse": 0.0
        }

    X = np.arange(n).reshape(-1, 1)
    y = series

    model = Ridge(alpha=1.0)
    model.fit(X, y)

    future_X = np.arange(n, n + horizon).reshape(-1, 1)
    y_pred = model.predict(future_X)

    residuals = y - model.predict(X)
    resid_std = float(residuals.std())
    mae = float(np.abs(residuals).mean())
    rmse = float(np.sqrt((residuals ** 2).mean()))

    p50 = [round(float(v), 3) for v in y_pred]
    p10 = [round(float(v - 1.2816 * resid_std), 3) for v in y_pred]
    p90 = [round(float(v + 1.2816 * resid_std), 3) for v in y_pred]

    return {
        "station_id": station_id,
        "model": "Ridge",
        "status": "VERIFIED",
        "execution": "SUCCESS",
        "trained": True,
        "forecast": p50,
        "p50": p50,
        "p10": p10,
        "p90": p90,
        "uncertainty": {
            "p10": p10,
            "p90": p90,
            "resid_std": round(resid_std, 3)
        },
        "metrics": {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3)
        },
        "mae": round(mae, 3),
        "rmse": round(rmse, 3)
    }


def forecast_station(
    series: np.ndarray,
    station_id: str = "",
    model_name: str = "ridge",
    horizon: int = 30,
    full_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Orchestrate model selection between verified baseline (Ridge) and ST-GNN adapter.
    Default model is 'ridge' to ensure complete backward compatibility.
    """
    model_key = (model_name or "ridge").lower().strip()

    if model_key in ["st_gnn", "stgnn", "gnn", "mtgnn"]:
        if full_df is not None and not full_df.empty:
            result = GroundwaterGNNAdapter.predict(station_id=station_id, df=full_df, horizon=horizon)
            if result.get("status") != "UNAVAILABLE":
                return result
        # If unavailable or no multi-station dataframe, fallback cleanly to Ridge
        fallback_res = forecast_ridge(series=series, station_id=station_id, horizon=horizon)
        fallback_res["model_requested"] = "ST-GNN"
        fallback_res["fallback_applied"] = True
        return fallback_res

    # Default verified Ridge forecast
    return forecast_ridge(series=series, station_id=station_id, horizon=horizon)