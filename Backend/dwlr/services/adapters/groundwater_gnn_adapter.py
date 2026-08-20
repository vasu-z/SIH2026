import os
import sys
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Search paths for isolated external repository
EXTERNAL_GNN_PATHS = [
    r"C:\Users\S\SIH2026\external\GroundwaterFlowGNN",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "external", "GroundwaterFlowGNN")),
]

def _ensure_gnn_import():
    """Ensure GroundwaterFlowGNN repository is on sys.path without modifying its source."""
    for path in EXTERNAL_GNN_PATHS:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
            break
    try:
        import torch
        from models.mtgnn import MTGNN
        return torch, MTGNN
    except Exception as e:
        logger.warning(f"Could not import MTGNN from external repository: {e}")
        return None, None


class GroundwaterGNNAdapter:
    """
    Isolated adapter for external GroundwaterFlowGNN (MTGNN architecture).
    Adheres strictly to the JalNetra Fail-Safe and Scientific Integrity rules.
    """

    @classmethod
    def is_available(cls) -> bool:
        torch, mtgnn_cls = _ensure_gnn_import()
        return torch is not None and mtgnn_cls is not None

    @classmethod
    def predict(cls, station_id: str, df: pd.DataFrame, horizon: int = 30, seq_length: int = 30) -> Dict[str, Any]:
        """
        Execute MTGNN forward pass on pivoted multi-station groundwater time series.
        """
        torch, mtgnn_cls = _ensure_gnn_import()
        if torch is None or mtgnn_cls is None:
            return {
                "station_id": station_id,
                "model": "ST-GNN",
                "status": "UNAVAILABLE",
                "execution": "FAILED",
                "trained": False,
                "reason": "GroundwaterFlowGNN external dependencies or models.mtgnn module unavailable.",
                "fallback": "Ridge"
            }

        try:
            if df.empty or "station_id" not in df.columns or "water_level_m" not in df.columns:
                raise ValueError("Input dataframe is empty or missing required columns ('station_id', 'water_level_m').")

            # Pivot to get (timesteps x stations)
            pivot = df.pivot_table(index="date", columns="station_id", values="water_level_m", aggfunc="mean").sort_index()

            if station_id not in pivot.columns:
                raise ValueError(f"Station {station_id} not found in observation dataset.")

            stations = list(pivot.columns)
            num_nodes = len(stations)
            target_idx = stations.index(station_id)

            if len(pivot) < seq_length:
                # Forward-fill / back-fill if fewer than seq_length
                pivot = pivot.reindex(range(seq_length)).ffill().bfill().fillna(0.0)

            # Extract the last seq_length timesteps: shape (num_nodes, seq_length)
            sub_series = pivot.iloc[-seq_length:].ffill().bfill().fillna(0.0).values.T

            # Input tensor shape: (batch_size=1, in_channels=1, num_nodes, seq_length)
            tensor_in = torch.tensor(sub_series, dtype=torch.float32).unsqueeze(0).unsqueeze(0)

            # Build MTGNN matching available nodes & sequence length
            subgraph_size = min(num_nodes, 20)
            model = mtgnn_cls(
                gcn_true=True,
                build_adj=True,
                gcn_depth=2,
                num_nodes=num_nodes,
                kernel_set=[2, 3, 6, 7],
                kernel_size=7,
                dropout=0.0,
                subgraph_size=subgraph_size,
                node_dim=10,
                dilation_exponential=1,
                conv_channels=16,
                residual_channels=16,
                skip_channels=32,
                end_channels=64,
                seq_length=seq_length,
                in_dim=1,
                out_dim=horizon,
                layers=2,
                propalpha=0.05,
                tanhalpha=3,
                layer_norm_affline=True
            )
            model.eval()

            with torch.no_grad():
                out = model(tensor_in)
                # Output shape is (batch_size=1, horizon, num_nodes, 1)
                # Extract predicted sequence for the target station
                pred_seq = out[0, :, target_idx, 0].cpu().numpy().tolist()

            return {
                "station_id": station_id,
                "model": "ST-GNN",
                "status": "EXPERIMENTAL",
                "execution": "SUCCESS",
                "trained": False,
                "forecast": [round(float(v), 3) for v in pred_seq],
                "p50": [round(float(v), 3) for v in pred_seq],
                "uncertainty": None,
                "metrics": None,
                "fallback": "Ridge",
                "message": "Architecture executed successfully but no pretrained checkpoint is available. Predictions are from untrained MTGNN."
            }

        except Exception as e:
            logger.exception("Error executing ST-GNN prediction:")
            return {
                "station_id": station_id,
                "model": "ST-GNN",
                "status": "UNAVAILABLE",
                "execution": "FAILED",
                "trained": False,
                "reason": str(e),
                "fallback": "Ridge"
            }
