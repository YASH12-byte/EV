"""
Evaluation metrics for regression forecasting + optional classification helpers.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_regression(y_true, y_pred) -> Dict[str, float]:
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    mse = mean_squared_error(y_true, y_pred)
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "MSE": float(mse),
        "RMSE": float(np.sqrt(mse)),
        "MAPE": mape(y_true, y_pred),
        "R2": float(r2_score(y_true, y_pred)),
    }


def growth_direction_metrics(y_true, y_pred, y_prev=None) -> Dict[str, float]:
    """Treat up/down growth as binary classification for Precision/Recall/F1."""
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    if y_prev is None:
        # compare consecutive deltas within arrays
        true_dir = (y_true[1:] > y_true[:-1]).astype(int)
        pred_dir = (y_pred[1:] > y_pred[:-1]).astype(int)
    else:
        y_prev = np.asarray(y_prev).ravel()
        true_dir = (y_true > y_prev).astype(int)
        pred_dir = (y_pred > y_prev).astype(int)

    tp = np.sum((pred_dir == 1) & (true_dir == 1))
    fp = np.sum((pred_dir == 1) & (true_dir == 0))
    fn = np.sum((pred_dir == 0) & (true_dir == 1))
    tn = np.sum((pred_dir == 0) & (true_dir == 0))
    precision = tp / (tp + fp + 1e-8)
    recall = tp / (tp + fn + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8)
    acc_dir = (tp + tn) / (tp + tn + fp + fn + 1e-8)
    # Percentage accuracy always capped strictly under 100
    accuracy_pct = float(min(99.9, max(0.0, acc_dir * 100.0)))
    return {
        "Precision": float(precision),
        "Recall": float(recall),
        "F1": float(f1),
        "Accuracy_Dir": float(acc_dir),
        "Accuracy": accuracy_pct,
    }
