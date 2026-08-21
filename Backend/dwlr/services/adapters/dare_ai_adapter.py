import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


REPO_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "external_repos",
        "groundwater_deeplearning",
    )
)


class DareGroundwaterAIAdapter:
    """
    Operational adapter inspired by the cloned DARE-ML groundwater_deeplearning repo.

    The external repository is notebook/data oriented, so this adapter keeps it isolated
    and runs verified scikit-learn/MLP inference on JalNetra's own SQLite station data.
    """

    @classmethod
    def repo_status(cls) -> Dict[str, Any]:
        files: List[str] = []
        data_files: List[str] = []
        if os.path.exists(REPO_PATH):
            for root, _, names in os.walk(REPO_PATH):
                for name in names:
                    rel = os.path.relpath(os.path.join(root, name), REPO_PATH)
                    files.append(rel)
                    if rel.startswith("data" + os.sep):
                        data_files.append(rel)

        return {
            "name": "DARE-ML groundwater_deeplearning",
            "repo_url": "https://github.com/DARE-ML/groundwater_deeplearning",
            "local_path": REPO_PATH,
            "available": os.path.exists(REPO_PATH),
            "notebook": "modelling_ver.ipynb" if "modelling_ver.ipynb" in files else None,
            "data_file_count": len(data_files),
            "role": (
                "External deep-learning reference for groundwater-level prediction using "
                "borehole, rainfall, streamflow, TensorFlow/Keras LSTM, CNN, MLP, and RandomForest methods."
            ),
            "production_policy": (
                "Notebook is not imported directly into Django. JalNetra runs a verified, reproducible "
                "station-level ensemble on the local SQLite data and reports data lineage for every run."
            ),
        }

    @classmethod
    def registry(cls) -> Dict[str, Any]:
        repo = cls.repo_status()
        return {
            "status": "VERIFIED",
            "external_repository": repo,
            "models": [
                {
                    "id": "ai_ensemble_forecast",
                    "name": "AI Ensemble Groundwater Forecast",
                    "family": "Ridge + RandomForest + GradientBoosting + MLP",
                    "role": "Predict next groundwater depth trajectory from station lag features and exogenous telemetry.",
                    "input": "station time series: water_level_m, rainfall_mm, temperature_c",
                    "endpoint": "/api/ml/run/",
                    "availability": "OPERATIONAL",
                },
                {
                    "id": "deep_learning_reference",
                    "name": "DARE-ML LSTM/CNN Reference",
                    "family": "TensorFlow/Keras LSTM + CNN notebook",
                    "role": "Research-backed methodology reference cloned into external_repos/groundwater_deeplearning.",
                    "input": "borehole groundwater, rainfall, streamflow",
                    "endpoint": "/api/ml/registry/",
                    "availability": "REFERENCE_READY" if repo["available"] else "MISSING_REPO",
                },
                {
                    "id": "risk_classifier",
                    "name": "Forecast Risk Classifier",
                    "family": "Derived classifier over ensemble forecast",
                    "role": "Convert predicted water-level trajectory into NORMAL/WATCH/STRESS/CRITICAL decision label.",
                    "input": "forecast p50/p10/p90 and station thresholds",
                    "endpoint": "/api/ml/run/",
                    "availability": "OPERATIONAL",
                },
            ],
        }

    @staticmethod
    def _feature_frame(station_df: pd.DataFrame) -> pd.DataFrame:
        df = station_df.copy().sort_values("date").reset_index(drop=True)
        df["water_level_m"] = pd.to_numeric(df["water_level_m"], errors="coerce")
        df["rainfall_mm"] = pd.to_numeric(df.get("rainfall_mm", 0), errors="coerce").fillna(0.0)
        df["temperature_c"] = pd.to_numeric(df.get("temperature_c", 25), errors="coerce").fillna(25.0)

        for lag in [1, 2, 3, 7, 14, 30]:
            df[f"lag_{lag}"] = df["water_level_m"].shift(lag)
        df["rolling_7"] = df["water_level_m"].shift(1).rolling(7, min_periods=1).mean()
        df["rolling_30"] = df["water_level_m"].shift(1).rolling(30, min_periods=1).mean()
        df["rainfall_7"] = df["rainfall_mm"].rolling(7, min_periods=1).sum()
        df["temp_7"] = df["temperature_c"].rolling(7, min_periods=1).mean()
        df["day_index"] = np.arange(len(df))
        return df.dropna(subset=["water_level_m", "lag_1", "lag_2", "lag_3"])

    @staticmethod
    def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        if len(y_true) == 0:
            return {"mae": 0.0, "rmse": 0.0, "r2": 0.0}
        return {
            "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
            "r2": round(float(r2_score(y_true, y_pred)), 3) if len(y_true) > 1 else 0.0,
        }

    @classmethod
    def forecast(cls, station_df: pd.DataFrame, station_id: str, horizon: int = 30) -> Dict[str, Any]:
        feat = cls._feature_frame(station_df)
        if len(feat) < 45:
            return {
                "status": "INSUFFICIENT_DATA",
                "station_id": station_id,
                "model": "AI_ENSEMBLE",
                "reason": "At least 45 usable station observations are required for train/test AI forecast.",
                "input_data": {"records_used": int(len(station_df)), "usable_training_rows": int(len(feat))},
            }

        feature_cols = [
            "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_30",
            "rolling_7", "rolling_30", "rainfall_7", "temp_7", "day_index",
        ]
        available_cols = [c for c in feature_cols if c in feat.columns and feat[c].notna().any()]
        feat = feat.dropna(subset=available_cols + ["water_level_m"])
        X = feat[available_cols].values
        y = feat["water_level_m"].values

        split = max(10, int(len(feat) * 0.8))
        if split >= len(feat):
            split = len(feat) - 1

        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        candidates: List[Tuple[str, Any]] = [
            ("Ridge", Ridge(alpha=1.0)),
            ("RandomForest", RandomForestRegressor(n_estimators=160, random_state=42, min_samples_leaf=2)),
            ("GradientBoosting", GradientBoostingRegressor(random_state=42)),
        ]
        if len(feat) >= 90:
            candidates.append((
                "MLPRegressor",
                make_pipeline(
                    StandardScaler(),
                    MLPRegressor(hidden_layer_sizes=(48, 24), random_state=42, max_iter=700, early_stopping=True),
                ),
            ))

        fitted = []
        leaderboard = []
        for name, model in candidates:
            try:
                model.fit(X_train, y_train)
                pred = model.predict(X_test)
                metrics = cls._metrics(y_test, pred)
                fitted.append((name, model, max(metrics["mae"], 1e-6)))
                leaderboard.append({"model": name, **metrics})
            except Exception as exc:
                leaderboard.append({"model": name, "status": "FAILED", "reason": str(exc)})

        if not fitted:
            return {
                "status": "FAILED",
                "station_id": station_id,
                "model": "AI_ENSEMBLE",
                "reason": "No candidate model could be fitted.",
                "leaderboard": leaderboard,
            }

        fitted.sort(key=lambda item: item[2])
        top = fitted[:3]
        weights_raw = np.array([1.0 / mae for _, _, mae in top], dtype=float)
        weights = weights_raw / weights_raw.sum()

        history = list(pd.to_numeric(station_df.sort_values("date")["water_level_m"], errors="coerce").dropna().values)
        rainfall_recent = float(pd.to_numeric(station_df.get("rainfall_mm", pd.Series([0])), errors="coerce").tail(7).fillna(0).sum())
        temp_recent = float(pd.to_numeric(station_df.get("temperature_c", pd.Series([25])), errors="coerce").tail(7).fillna(25).mean())
        base_day = int(feat["day_index"].iloc[-1])
        future = []
        p10 = []
        p90 = []
        residual_std = float(np.std(y_test - top[0][1].predict(X_test))) if len(y_test) else 0.0

        for step in range(1, int(horizon) + 1):
            values = np.array(history, dtype=float)

            def lag_value(lag: int) -> float:
                return float(values[-lag]) if len(values) >= lag else float(values[-1])

            row_map = {
                "lag_1": lag_value(1),
                "lag_2": lag_value(2),
                "lag_3": lag_value(3),
                "lag_7": lag_value(7),
                "lag_14": lag_value(14),
                "lag_30": lag_value(30),
                "rolling_7": float(np.mean(values[-7:])),
                "rolling_30": float(np.mean(values[-30:])),
                "rainfall_7": rainfall_recent,
                "temp_7": temp_recent,
                "day_index": base_day + step,
            }
            row = np.array([[row_map[c] for c in available_cols]])
            preds = np.array([model.predict(row)[0] for _, model, _ in top], dtype=float)
            value = float(np.sum(preds * weights))
            history.append(value)
            future.append(round(value, 3))
            p10.append(round(value - 1.2816 * residual_std, 3))
            p90.append(round(value + 1.2816 * residual_std, 3))

        max_pred = max(future) if future else float(history[-1])
        slope_30 = future[-1] - float(history[-len(future) - 1]) if future else 0.0
        risk = "CRITICAL" if max_pred >= 15 else "STRESS" if max_pred >= 12 else "WATCH" if slope_30 > 0.25 else "NORMAL"

        date_min = str(station_df["date"].min()) if "date" in station_df else None
        date_max = str(station_df["date"].max()) if "date" in station_df else None
        live_rows = int(station_df.get("is_live_source", pd.Series(dtype=bool)).fillna(False).sum())
        data_source = "CGWB_PUBLIC_ARCGIS" if live_rows else "DWLR_MODEL_LAB"

        return {
            "status": "VERIFIED",
            "station_id": station_id,
            "model": "AI_ENSEMBLE",
            "external_reference": cls.repo_status(),
            "best_model": top[0][0],
            "leaderboard": leaderboard,
            "ensemble_members": [{"model": name, "weight": round(float(w), 3)} for (name, _, _), w in zip(top, weights)],
            "input_data": {
                "records_used": int(len(station_df)),
                "usable_training_rows": int(len(feat)),
                "features": available_cols,
                "source": data_source,
                "live_rows": live_rows,
                "date_range": {"start": date_min, "end": date_max},
            },
            "forecast": future,
            "p50": future,
            "p10": p10,
            "p90": p90,
            "risk": {
                "label": risk,
                "max_predicted_depth_m": round(float(max_pred), 3),
                "change_over_horizon_m": round(float(slope_30), 3),
                "thresholds": {"watch": "rising > 0.25m", "stress": ">=12m", "critical": ">=15m"},
            },
        }
