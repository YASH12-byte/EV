"""
Physics-Informed constraints for EV market forecasting.
Encodes soft penalties for battery degradation, grid capacity, and charging limits.
"""
from __future__ import annotations

import numpy as np

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config

try:
    import tensorflow as tf
except ImportError:  # optional for UI-only demos
    tf = None


def battery_degradation_penalty(pred_sales, degradation):
    """Higher degradation should constrain aggressive sales growth."""
    return tf.reduce_mean(tf.nn.relu(pred_sales * degradation - 0.15) ** 2)


def grid_capacity_penalty(pred_sales, grid_capacity, stations):
    """Sales demand should not unrealistically exceed grid + station capacity."""
    capacity = 0.08 * grid_capacity + 0.55 * stations
    overload = tf.nn.relu(pred_sales - capacity * 8.0)
    return tf.reduce_mean(overload ** 2)


def charging_capacity_penalty(pred_sales, stations):
    """Approx. vehicles-per-station soft upper bound."""
    per_station = pred_sales / (stations + 1e-3)
    return tf.reduce_mean(tf.nn.relu(per_station - 25.0) ** 2)


def apply_physics_postprocess(
    predictions: np.ndarray,
    grid_capacity: np.ndarray,
    charging_stations: np.ndarray,
    degradation: np.ndarray,
) -> np.ndarray:
    """Clip/adjust forecasts using physical feasibility bounds (inference-time)."""
    capacity = 0.08 * grid_capacity + 0.55 * charging_stations
    upper = capacity * 8.0
    shrink = 1.0 / (1.0 + 5.0 * np.maximum(degradation, 0))
    adjusted = np.minimum(predictions * shrink, upper)
    return np.maximum(adjusted, 0)


if tf is not None:

    class PhysicsInformedLoss(tf.keras.losses.Loss):
        def __init__(
            self,
            feature_index: dict,
            lambda_battery: float = None,
            lambda_grid: float = None,
            lambda_charge: float = None,
            name: str = "physics_informed_mse",
        ):
            super().__init__(name=name)
            self.feature_index = feature_index
            self.lambda_battery = lambda_battery or config.PHYSICS_LAMBDA_BATTERY
            self.lambda_grid = lambda_grid or config.PHYSICS_LAMBDA_GRID
            self.lambda_charge = lambda_charge or config.PHYSICS_LAMBDA_CHARGE
            self.mse = tf.keras.losses.MeanSquaredError()

        def call(self, y_true, y_pred):
            return self.mse(y_true, y_pred)

        def combined(self, y_true, y_pred, X_seq):
            last = X_seq[:, -1, :]
            base = self.mse(y_true, y_pred)
            deg_idx = self.feature_index.get("battery_degradation_index")
            grid_idx = self.feature_index.get("grid_capacity")
            st_idx = self.feature_index.get("charging_stations")
            pen = 0.0
            if deg_idx is not None:
                pen += self.lambda_battery * battery_degradation_penalty(y_pred, last[:, deg_idx : deg_idx + 1])
            if grid_idx is not None and st_idx is not None:
                pen += self.lambda_grid * grid_capacity_penalty(
                    y_pred, last[:, grid_idx : grid_idx + 1], last[:, st_idx : st_idx + 1]
                )
            if st_idx is not None:
                pen += self.lambda_charge * charging_capacity_penalty(y_pred, last[:, st_idx : st_idx + 1])
            return base + pen
else:
    PhysicsInformedLoss = None  # type: ignore
