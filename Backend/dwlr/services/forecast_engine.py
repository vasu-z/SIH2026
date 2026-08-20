import numpy as np
from sklearn.linear_model import Ridge

def forecast_station(series: np.ndarray, horizon=30):
    n = len(series)
    X = np.arange(n).reshape(-1, 1)
    y = series

    model = Ridge(alpha=1.0)
    model.fit(X, y)

    future_X = np.arange(n, n + horizon).reshape(-1, 1)
    y_pred = model.predict(future_X)

    residuals = y - model.predict(X)
    resid_std = residuals.std()

    p10 = (y_pred - 1.2816 * resid_std).tolist()
    p90 = (y_pred + 1.2816 * resid_std).tolist()

    return {
        "p50": y_pred.tolist(),
        "p10": p10,
        "p90": p90,
        "mae": float(np.abs(residuals).mean()),
        "rmse": float(np.sqrt((residuals**2).mean()))
    }