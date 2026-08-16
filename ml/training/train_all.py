"""
Train hybrid model + baseline comparisons. Saves metrics and artifacts.
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config
from ml.evaluation.metrics import evaluate_regression, growth_direction_metrics
from ml.models.hybrid_cnn_lstm_attention import (
    AttentionBlock,
    build_bilstm,
    build_cnn_gru,
    build_hybrid_cnn_lstm_attention,
    build_lstm,
    build_transformer_encoder,
)
from ml.preprocessing.pipeline import prepare_dataset


def _try_import_boosters():
    models = {}
    try:
        from xgboost import XGBRegressor

        models["XGBoost"] = XGBRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.08, subsample=0.9, random_state=config.RANDOM_SEED
        )
    except Exception:
        pass
    try:
        from lightgbm import LGBMRegressor

        models["LightGBM"] = LGBMRegressor(
            n_estimators=200, learning_rate=0.08, random_state=config.RANDOM_SEED
        )
    except Exception:
        pass
    try:
        from catboost import CatBoostRegressor

        models["CatBoost"] = CatBoostRegressor(
            iterations=200, depth=6, learning_rate=0.08, verbose=0, random_seed=config.RANDOM_SEED
        )
    except Exception:
        pass
    return models


def flatten_last(X: np.ndarray) -> np.ndarray:
    """Use last timestep features for tabular ML baselines."""
    return X[:, -1, :]


def train_tabular_baselines(data) -> dict:
    results = {}
    Xtr, ytr = flatten_last(data.X_train), data.y_train
    Xte, yte = flatten_last(data.X_test), data.y_test
    # Inverse for metrics in original scale
    yte_inv = data.target_scaler.inverse_transform(yte.reshape(-1, 1)).ravel()

    candidates = {
        "DecisionTree": DecisionTreeRegressor(max_depth=8, random_state=config.RANDOM_SEED),
        "RandomForest": RandomForestRegressor(
            n_estimators=150, max_depth=12, random_state=config.RANDOM_SEED, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingRegressor(random_state=config.RANDOM_SEED),
    }
    candidates.update(_try_import_boosters())

    for name, model in candidates.items():
        t0 = time.time()
        try:
            model.fit(Xtr, ytr)
            pred_s = model.predict(Xte)
            pred = data.target_scaler.inverse_transform(pred_s.reshape(-1, 1)).ravel()
            metrics = evaluate_regression(yte_inv, pred)
            metrics.update(growth_direction_metrics(yte_inv, pred))
            metrics["TrainingTimeSec"] = round(time.time() - t0, 3)
            results[name] = metrics
            joblib.dump(model, config.MODEL_DIR / f"{name.lower()}_model.pkl")
            print(f"[OK] {name}: RMSE={metrics['RMSE']:.2f} R2={metrics['R2']:.3f}")
        except Exception as e:
            print(f"[SKIP] {name}: {e}")
            results[name] = {"error": str(e)}
    return results


def train_classical_ts(data) -> dict:
    """Lightweight ARIMA/Prophet on national aggregate for comparison."""
    results = {}
    try:
        from statsmodels.tsa.arima.model import ARIMA

        df = pd.read_csv(config.DATA_PROCESSED / "ev_market_processed.csv", parse_dates=["date"])
        series = df.groupby("date")["ev_sales"].mean().sort_index()
        split = int(len(series) * 0.8)
        train, test = series.iloc[:split], series.iloc[split:]
        t0 = time.time()
        model = ARIMA(train, order=(2, 1, 2)).fit()
        pred = model.forecast(steps=len(test))
        metrics = evaluate_regression(test.values, pred.values)
        metrics["TrainingTimeSec"] = round(time.time() - t0, 3)
        results["ARIMA"] = metrics
        print(f"[OK] ARIMA: RMSE={metrics['RMSE']:.2f}")
    except Exception as e:
        results["ARIMA"] = {"error": str(e)}
        print(f"[SKIP] ARIMA: {e}")

    try:
        from prophet import Prophet

        df = pd.read_csv(config.DATA_PROCESSED / "ev_market_processed.csv", parse_dates=["date"])
        series = df.groupby("date")["ev_sales"].mean().reset_index()
        series.columns = ["ds", "y"]
        split = int(len(series) * 0.8)
        train, test = series.iloc[:split], series.iloc[split:]
        t0 = time.time()
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.fit(train)
        future = m.make_future_dataframe(periods=len(test), freq="MS")
        forecast = m.predict(future).tail(len(test))["yhat"].values
        metrics = evaluate_regression(test["y"].values, forecast)
        metrics["TrainingTimeSec"] = round(time.time() - t0, 3)
        results["Prophet"] = metrics
        print(f"[OK] Prophet: RMSE={metrics['RMSE']:.2f}")
    except Exception as e:
        results["Prophet"] = {"error": str(e)}
        print(f"[SKIP] Prophet: {e}")
    return results


def train_dl_models(data, epochs: int = None) -> dict:
    epochs = epochs or config.EPOCHS
    results = {}
    seq_len, n_features = data.X_train.shape[1], data.X_train.shape[2]
    yte_inv = data.target_scaler.inverse_transform(data.y_test.reshape(-1, 1)).ravel()

    builders = {
        "LSTM": build_lstm,
        "BiLSTM": build_bilstm,
        "CNN_GRU": build_cnn_gru,
        "Transformer": build_transformer_encoder,
        "Hybrid_CNN_LSTM_Attention": build_hybrid_cnn_lstm_attention,
    }

    callbacks_common = [
        EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-6),
    ]

    for name, builder in builders.items():
        print(f"\n=== Training {name} ===")
        t0 = time.time()
        try:
            tf.keras.backend.clear_session()
            model = builder(seq_len, n_features)
            ckpt_path = config.MODEL_DIR / f"{name}.keras"
            cbs = callbacks_common + [
                ModelCheckpoint(str(ckpt_path), monitor="val_loss", save_best_only=True)
            ]
            history = model.fit(
                data.X_train,
                data.y_train,
                validation_data=(data.X_val, data.y_val),
                epochs=epochs,
                batch_size=config.BATCH_SIZE,
                callbacks=cbs,
                verbose=1,
            )
            pred_s = model.predict(data.X_test, verbose=0).ravel()
            pred = data.target_scaler.inverse_transform(pred_s.reshape(-1, 1)).ravel()
            metrics = evaluate_regression(yte_inv, pred)
            metrics.update(growth_direction_metrics(yte_inv, pred))
            metrics["TrainingTimeSec"] = round(time.time() - t0, 3)
            metrics["FinalValLoss"] = float(min(history.history["val_loss"]))
            results[name] = metrics
            model.save(ckpt_path)
            print(f"[OK] {name}: RMSE={metrics['RMSE']:.2f} R2={metrics['R2']:.3f}")
        except Exception as e:
            traceback.print_exc()
            results[name] = {"error": str(e)}
            print(f"[FAIL] {name}: {e}")
    return results


def main(fast: bool = False):
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    raw = config.DATA_RAW / "ev_market_data.csv"
    if not raw.exists():
        from scripts.generate_dataset import build_dataset

        build_dataset(raw)

    print("Preparing dataset...")
    data = prepare_dataset()
    print(f"Train/Val/Test: {data.meta}")

    epochs = 8 if fast else config.EPOCHS
    all_results = {}
    all_results.update(train_tabular_baselines(data))
    all_results.update(train_classical_ts(data))
    all_results.update(train_dl_models(data, epochs=epochs))

    out = config.MODEL_DIR / "comparison_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved comparison → {out}")

    # Persist feature names for API/XAI
    with open(config.MODEL_DIR / "feature_names.json", "w", encoding="utf-8") as f:
        json.dump(data.feature_names, f, indent=2)

    return all_results


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--fast", action="store_true", help="Quick training for demo")
    args = p.parse_args()
    main(fast=args.fast)
