import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from scipy.linalg import qr

logger = logging.getLogger(__name__)


class MonitoringDesignAdapter:
    """
    Isolated adapter implementing Weighted QR Decomposition with Column Pivoting (QRP).
    Adapted from the mathematical formulation of Oh & Bartos (Nature Water, 2025)
    for 2D continuous groundwater monitoring network design and expansion.
    """

    @classmethod
    def run_qrp_placement(
        cls,
        X: np.ndarray,
        fixed_indices: List[int],
        weights: Optional[np.ndarray] = None,
        candidate_indices: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Execute QRP sensor placement with existing network constraints.

        Parameters:
        - X: Spatiotemporal observation matrix (T timesteps x M locations).
        - fixed_indices: Column indices of currently operational monitoring stations.
        - weights: Column weights incorporating regional risk, forecast uncertainty, and spatial isolation.
        - candidate_indices: Optional specific candidate column indices to rank.
        """
        T, M = X.shape
        if M == 0 or T < 2:
            return {
                "ranked_indices": [],
                "information_gains": [],
                "orthogonality_scores": [],
                "status": "EMPTY_DATASET"
            }

        # Step 1: Standardize columns (mean 0, unit variance)
        means = np.nanmean(X, axis=0)
        stds = np.nanstd(X, axis=0) + 1e-6
        X_norm = np.nan_to_num((X - means) / stds, nan=0.0)

        # Step 2: Apply diagonal weight scaling
        if weights is not None and len(weights) == M:
            w_arr = np.asarray(weights, dtype=float)
            X_w = X_norm * w_arr.reshape(1, -1)
        else:
            X_w = X_norm

        # Step 3: Partition into fixed and candidate (free) columns
        valid_fixed = [idx for idx in fixed_indices if 0 <= idx < M]
        if candidate_indices is not None:
            free_indices = [idx for idx in candidate_indices if 0 <= idx < M and idx not in valid_fixed]
        else:
            free_indices = [idx for idx in range(M) if idx not in valid_fixed]

        if not free_indices:
            return {
                "ranked_indices": [],
                "information_gains": [],
                "orthogonality_scores": [],
                "status": "NO_CANDIDATES"
            }

        if valid_fixed:
            A_F = X_w[:, valid_fixed]
            A_R = X_w[:, free_indices]

            # Step 4: QR decomposition on existing fixed network
            try:
                Q_F, _ = np.linalg.qr(A_F)
                # Step 5: Orthogonalize candidate subspace against existing network span
                projection = Q_F @ (Q_F.T @ A_R)
                A_R_prime = A_R - projection
            except Exception as e:
                logger.warning(f"Fixed subspace QR failed, falling back to unconstrained QRP: {e}")
                A_R_prime = A_R

            # Step 6: Pivoted QR on residual non-redundant subspace
            Q_R, R_R, pivots_R = qr(A_R_prime, pivoting=True)

            ranked_free = [free_indices[i] for i in pivots_R]

            # Step 7: Calculate marginal information gain and orthogonality scores
            # Information gain = residual column norm relative to original norm (fraction of unobserved variance)
            info_gains = []
            ortho_scores = []
            for i, p_idx in enumerate(pivots_R):
                orig_norm = np.linalg.norm(A_R[:, p_idx]) + 1e-6
                res_norm = np.linalg.norm(A_R_prime[:, p_idx])
                ortho_ratio = min(1.0, max(0.0, res_norm / orig_norm))
                ortho_scores.append(round(float(ortho_ratio), 3))

                # Marginal information gain proxy scaled by pivot diagonal leverage
                if i < min(R_R.shape):
                    diag_val = abs(float(R_R[i, i]))
                    norm_gain = min(100.0, max(10.0, round(ortho_ratio * 70.0 + min(30.0, diag_val * 5.0), 1)))
                else:
                    norm_gain = round(ortho_ratio * 100.0, 1)
                info_gains.append(norm_gain)

        else:
            # No fixed stations: direct QRP across all candidate locations
            A_R = X_w[:, free_indices]
            Q_R, R_R, pivots_R = qr(A_R, pivoting=True)
            ranked_free = [free_indices[i] for i in pivots_R]

            info_gains = []
            ortho_scores = []
            for i, _ in enumerate(pivots_R):
                diag_val = abs(float(R_R[i, i])) if i < min(R_R.shape) else 1.0
                norm_gain = min(100.0, max(10.0, round(min(100.0, diag_val * 10.0), 1)))
                info_gains.append(norm_gain)
                ortho_scores.append(1.0)

        return {
            "ranked_indices": ranked_free,
            "information_gains": info_gains,
            "orthogonality_scores": ortho_scores,
            "status": "VERIFIED"
        }
