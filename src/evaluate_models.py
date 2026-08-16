"""Shared evaluation metrics — computed from actual predictions only."""
from __future__ import annotations

from typing import Dict

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def mape_safe(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.abs(y_true) > 1e-8
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def evaluate(y_true, y_pred) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) == 0:
        return {"MAE": float("nan"), "RMSE": float("nan"), "MAPE": float("nan"), "R2": float("nan"),
                "Approx_Accuracy_100_minus_MAPE": float("nan"), "n": 0}
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = mape_safe(y_true, y_pred)
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan")
    approx_acc = float(max(0.0, 100.0 - mape)) if mape == mape else float("nan")
    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "R2": r2,
        "Approx_Accuracy_100_minus_MAPE": approx_acc,
        "n": int(len(y_true)),
    }
