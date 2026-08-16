"""Smoke tests for evaluation metrics helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.evaluation.metrics import evaluate_regression


def test_regression_metrics_basic():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([11.0, 18.0, 33.0])
    m = evaluate_regression(y_true, y_pred)
    assert "MAE" in m and "RMSE" in m and "MAPE" in m and "R2" in m
    assert m["MAE"] >= 0
    assert m["RMSE"] >= 0


def test_mape_handles_zeros():
    y_true = np.array([0.0, 10.0, 0.0])
    y_pred = np.array([1.0, 12.0, 2.0])
    m = evaluate_regression(y_true, y_pred)
    assert np.isfinite(m["MAPE"])
