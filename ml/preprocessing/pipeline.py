"""
Preprocessing, denoising, feature engineering, and sequence builders.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config


@dataclass
class PreparedData:
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    feature_scaler: MinMaxScaler
    target_scaler: MinMaxScaler
    feature_names: List[str]
    meta: Dict


def load_raw(path: Optional[Path] = None) -> pd.DataFrame:
    path = path or (config.DATA_RAW / "ev_market_data.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values(["region", "date"]).reset_index(drop=True)


def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    num_cols = out.select_dtypes(include=[np.number]).columns
    out[num_cols] = out.groupby("region")[num_cols].transform(lambda s: s.ffill().bfill())
    out[num_cols] = out[num_cols].fillna(out[num_cols].median())
    return out


def remove_outliers(df: pd.DataFrame, cols: List[str], z_thresh: float = 3.5) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        med = out[col].median()
        mad = np.median(np.abs(out[col] - med)) + 1e-8
        modified_z = 0.6745 * (out[col] - med) / mad
        out.loc[np.abs(modified_z) > z_thresh, col] = np.nan
    return impute_missing(out)


def denoise_moving_average(df: pd.DataFrame, cols: List[str], window: int = 3) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        out[col] = out.groupby("region")[col].transform(
            lambda s: s.rolling(window=window, min_periods=1, center=True).mean()
        )
    return out


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    g = out.groupby("region", group_keys=False)
    out["ev_sales_lag1"] = g["ev_sales"].shift(1)
    out["ev_sales_lag3"] = g["ev_sales"].shift(3)
    out["ev_sales_roll3"] = g["ev_sales"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    out["ev_sales_roll6"] = g["ev_sales"].transform(lambda s: s.rolling(6, min_periods=1).mean())
    out["stations_per_capita"] = out["charging_stations"] / (out["population"] / 1e5)
    out["cost_to_fuel_ratio"] = out["battery_cost"] / (out["fuel_price"] + 1e-6)
    out["policy_x_stations"] = out["gov_policy_index"] * np.log1p(out["charging_stations"])
    out["grid_utilization"] = out["charging_stations"] / (out["grid_capacity"] + 1e-6)
    out["month"] = out["date"].dt.month
    out["year"] = out["date"].dt.year
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)
    out = impute_missing(out)
    return out


def get_model_features(df: pd.DataFrame) -> List[str]:
    base = list(config.FEATURE_COLUMNS)
    engineered = [
        "ev_sales_lag1",
        "ev_sales_lag3",
        "ev_sales_roll3",
        "ev_sales_roll6",
        "stations_per_capita",
        "cost_to_fuel_ratio",
        "policy_x_stations",
        "grid_utilization",
        "month_sin",
        "month_cos",
    ]
    return [c for c in base + engineered if c in df.columns]


def create_sequences(
    features: np.ndarray,
    target: np.ndarray,
    seq_len: int,
    horizon: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    Xs, ys = [], []
    for i in range(len(features) - seq_len - horizon + 1):
        Xs.append(features[i : i + seq_len])
        ys.append(target[i + seq_len + horizon - 1])
    return np.asarray(Xs), np.asarray(ys)


def prepare_dataset(
    df: Optional[pd.DataFrame] = None,
    seq_len: int = None,
    horizon: int = None,
) -> PreparedData:
    seq_len = seq_len or config.SEQUENCE_LENGTH
    horizon = horizon or 1

    if df is None:
        df = load_raw()
    df = impute_missing(df)
    df = remove_outliers(df, config.FEATURE_COLUMNS)
    df = denoise_moving_average(df, config.FEATURE_COLUMNS, window=3)
    df = engineer_features(df)

    feature_names = get_model_features(df)
    X_all, y_all = [], []
    for region, rdf in df.groupby("region"):
        feat = rdf[feature_names].values.astype(np.float32)
        tgt = rdf[config.TARGET_COLUMN].values.astype(np.float32)
        Xs, ys = create_sequences(feat, tgt, seq_len, horizon)
        if len(Xs):
            X_all.append(Xs)
            y_all.append(ys)
    X = np.concatenate(X_all, axis=0)
    y = np.concatenate(y_all, axis=0)

    n = len(X)
    n_test = int(n * config.TEST_RATIO)
    n_val = int(n * config.VAL_RATIO)
    n_train = n - n_test - n_val

    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train : n_train + n_val], y[n_train : n_train + n_val]
    X_test, y_test = X[n_train + n_val :], y[n_train + n_val :]

    # Fit scalers on train only (flatten time for feature scale)
    feature_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()
    flat_train = X_train.reshape(-1, X_train.shape[-1])
    feature_scaler.fit(flat_train)
    target_scaler.fit(y_train.reshape(-1, 1))

    def scale_X(arr):
        shape = arr.shape
        return feature_scaler.transform(arr.reshape(-1, shape[-1])).reshape(shape)

    X_train_s = scale_X(X_train)
    X_val_s = scale_X(X_val)
    X_test_s = scale_X(X_test)
    y_train_s = target_scaler.transform(y_train.reshape(-1, 1)).ravel()
    y_val_s = target_scaler.transform(y_val.reshape(-1, 1)).ravel()
    y_test_s = target_scaler.transform(y_test.reshape(-1, 1)).ravel()

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump(feature_scaler, config.DATA_PROCESSED / "feature_scaler.pkl")
    joblib.dump(target_scaler, config.DATA_PROCESSED / "target_scaler.pkl")
    df.to_csv(config.DATA_PROCESSED / "ev_market_processed.csv", index=False)

    return PreparedData(
        X_train=X_train_s,
        y_train=y_train_s,
        X_val=X_val_s,
        y_val=y_val_s,
        X_test=X_test_s,
        y_test=y_test_s,
        feature_scaler=feature_scaler,
        target_scaler=target_scaler,
        feature_names=feature_names,
        meta={"n_train": n_train, "n_val": n_val, "n_test": n_test, "seq_len": seq_len},
    )
