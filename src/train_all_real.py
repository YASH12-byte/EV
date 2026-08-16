"""
Train baseline + deep models for annual EV registration forecasting.
Metrics are computed from real chronological test predictions only.
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluate_models import evaluate
from src.feature_engineering import chronological_split, make_sequences

warnings.filterwarnings("ignore")

PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
MET = OUT / "metrics"
FORE = OUT / "forecasts"
MODEL_DIR = ROOT / "models" / "saved"
for d in (FIG, MET, FORE, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)

SEED = 42
np.random.seed(SEED)


def load_national_annual() -> pd.DataFrame:
    path = PROC / "ev_registrations_national_annual.csv"
    df = pd.read_csv(path).sort_values("Year").reset_index(drop=True)
    return df


def try_xgboost():
    try:
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=SEED,
            objective="reg:squarederror",
        )
    except Exception:
        return None


def train_tabular() -> Dict[str, Any]:
    data = np.load(PROC / "registrations_xy.npz")
    X_train, y_train = data["X_train"], data["y_train"]
    X_val, y_val = data["X_val"], data["y_val"]
    X_test, y_test = data["X_test"], data["y_test"]
    results = {}

    # Naive: predict lag_1 which is feature index after encoding — use previous y by aligning meta
    meta_test = pd.read_csv(PROC / "registrations_test_meta.csv")
    naive_pred = meta_test["lag_1"].values.astype(float)
    y_true = meta_test["Registrations"].values.astype(float)
    results["Naive"] = {"metrics": evaluate(y_true, naive_pred), "train_seconds": 0.0}
    print("Naive", results["Naive"]["metrics"])

    # Random Forest
    t0 = time.time()
    rf = RandomForestRegressor(
        n_estimators=300, max_depth=12, min_samples_leaf=2, random_state=SEED, n_jobs=-1
    )
    # Prefer train+val for final fit after val used for early sense-check
    X_tr = np.vstack([X_train, X_val]) if len(X_val) else X_train
    y_tr = np.concatenate([y_train, y_val]) if len(y_val) else y_train
    rf.fit(X_tr, y_tr)
    pred = rf.predict(X_test)
    results["RandomForest"] = {"metrics": evaluate(y_test, pred), "train_seconds": time.time() - t0}
    joblib.dump(rf, MODEL_DIR / "random_forest.pkl")
    print("RandomForest", results["RandomForest"]["metrics"])

    xgb = try_xgboost()
    if xgb is not None:
        t0 = time.time()
        xgb.fit(X_tr, y_tr)
        pred = xgb.predict(X_test)
        results["XGBoost"] = {"metrics": evaluate(y_test, pred), "train_seconds": time.time() - t0}
        joblib.dump(xgb, MODEL_DIR / "xgboost_model.pkl")
        print("XGBoost", results["XGBoost"]["metrics"])
    else:
        results["XGBoost"] = {
            "metrics": {"MAE": None, "RMSE": None, "MAPE": None, "R2": None, "note": "xgboost not installed"},
            "train_seconds": None,
        }

    # Persist test predictions for plotting
    plot_df = meta_test.copy()
    plot_df["pred_naive"] = naive_pred
    plot_df["pred_rf"] = rf.predict(X_test)
    if xgb is not None:
        plot_df["pred_xgb"] = xgb.predict(X_test)
    plot_df.to_csv(FORE / "registrations_test_predictions_tabular.csv", index=False)
    return results


def train_arima_national() -> Dict[str, Any]:
    from statsmodels.tsa.arima.model import ARIMA

    df = load_national_annual()
    years = df["Year"].astype(int).tolist()
    values = df["Registrations"].astype(float).values
    split = chronological_split(np.array(years))
    train_idx = [i for i, y in enumerate(years) if y in split["train"] + split["val"]]
    test_idx = [i for i, y in enumerate(years) if y in split["test"]]
    if len(train_idx) < 3 or not test_idx:
        return {"ARIMA": {"metrics": {"note": "insufficient national annual points"}, "train_seconds": None}}

    y_train = values[train_idx]
    y_test = values[test_idx]
    best = None
    best_aic = np.inf
    t0 = time.time()
    for p in range(0, 3):
        for d in range(0, 2):
            for q in range(0, 3):
                try:
                    model = ARIMA(y_train, order=(p, d, q)).fit()
                    if model.aic < best_aic:
                        best_aic = model.aic
                        best = (p, d, q, model)
                except Exception:
                    continue
    if best is None:
        return {"ARIMA": {"metrics": {"note": "ARIMA fit failed"}, "train_seconds": None}}

    p, d, q, model = best
    # Refit rolling one-step for test horizon
    history = list(y_train)
    preds = []
    for _ in y_test:
        m = ARIMA(history, order=(p, d, q)).fit()
        fc = float(m.forecast(1)[0])
        preds.append(max(0.0, fc))
        history.append(y_test[len(preds) - 1])  # use true for one-step eval only
    metrics = evaluate(y_test, np.array(preds))
    joblib.dump({"order": (p, d, q), "history_years": years, "last_train": list(y_train)}, MODEL_DIR / "arima_model.pkl")
    # Save future forecast from full series
    full = ARIMA(values, order=(p, d, q)).fit()
    future = full.forecast(3)
    fut_years = [years[-1] + i for i in range(1, 4)]
    pd.DataFrame({"Year": fut_years, "Forecast_Registrations": np.maximum(0, future)}).to_csv(
        FORE / "national_registrations_future_arima.csv", index=False
    )
    print("ARIMA", (p, d, q), metrics)
    return {"ARIMA": {"metrics": metrics, "train_seconds": time.time() - t0, "order": (p, d, q)}}


def _keras_available() -> bool:
    try:
        import tensorflow as tf  # noqa: F401
        return True
    except Exception:
        return False


def build_cnn(seq_len: int):
    from tensorflow import keras
    from tensorflow.keras import layers

    model = keras.Sequential(
        [
            layers.Input(shape=(seq_len, 1)),
            layers.Conv1D(32, 2, activation="relu", padding="causal"),
            layers.MaxPooling1D(pool_size=1),
            layers.Flatten(),
            layers.Dense(32, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    return model


def build_lstm(seq_len: int):
    from tensorflow import keras
    from tensorflow.keras import layers

    model = keras.Sequential(
        [
            layers.Input(shape=(seq_len, 1)),
            layers.LSTM(32),
            layers.Dropout(0.2),
            layers.Dense(16, activation="relu"),
            layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    return model


def build_cnn_lstm(seq_len: int):
    from tensorflow import keras
    from tensorflow.keras import layers

    model = keras.Sequential(
        [
            layers.Input(shape=(seq_len, 1)),
            layers.Conv1D(32, 2, activation="relu", padding="causal"),
            layers.MaxPooling1D(pool_size=1),
            layers.LSTM(32),
            layers.Dropout(0.25),
            layers.Dense(16, activation="relu"),
            layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    return model


def train_sequence_models(seq_len: int = 3) -> Dict[str, Any]:
    if not _keras_available():
        note = {"note": "tensorflow not installed — deep models skipped"}
        return {"CNN": note, "LSTM": note, "CNN-LSTM": note}

    from tensorflow import keras

    df = load_national_annual()
    years = df["Year"].astype(int).values
    values = df["Registrations"].astype(float).values
    split = chronological_split(years)

    # Scale using train only
    train_mask = np.isin(years, split["train"])
    vmax = values[train_mask].max() if train_mask.any() else values.max()
    vmin = values[train_mask].min() if train_mask.any() else values.min()
    denom = max(vmax - vmin, 1e-8)
    scaled = (values - vmin) / denom

    # Build sequences from full series then assign by target year
    X_all, y_all = make_sequences(scaled, seq_len)
    target_years = years[seq_len:]
    def subset(year_list):
        m = np.isin(target_years, year_list)
        return X_all[m], y_all[m]

    X_tr, y_tr = subset(split["train"])
    X_va, y_va = subset(split["val"])
    X_te, y_te = subset(split["test"])
    if len(X_tr) < 2 or len(X_te) < 1:
        note = {"note": "insufficient sequence samples for deep models"}
        return {"CNN": note, "LSTM": note, "CNN-LSTM": note}

    callbacks = [
        keras.callbacks.EarlyStopping(patience=20, restore_best_weights=True, monitor="val_loss"),
        keras.callbacks.ReduceLROnPlateau(patience=8, factor=0.5, min_lr=1e-5),
    ]

    results = {}
    builders = {
        "CNN": (build_cnn, "cnn_model.keras"),
        "LSTM": (build_lstm, "lstm_model.keras"),
        "CNN-LSTM": (build_cnn_lstm, "cnn_lstm_model.keras"),
    }
    preds_store = {"Year": target_years[np.isin(target_years, split["test"])].tolist()}

    for name, (builder, fname) in builders.items():
        t0 = time.time()
        model = builder(seq_len)
        model.fit(
            X_tr,
            y_tr,
            validation_data=(X_va, y_va) if len(X_va) else None,
            epochs=120,
            batch_size=8,
            verbose=0,
            callbacks=callbacks,
        )
        pred_s = model.predict(X_te, verbose=0).reshape(-1)
        pred = pred_s * denom + vmin
        true = y_te * denom + vmin
        metrics = evaluate(true, pred)
        model.save(MODEL_DIR / fname)
        results[name] = {"metrics": metrics, "train_seconds": time.time() - t0}
        preds_store[f"pred_{name}"] = pred.tolist()
        preds_store["actual"] = true.tolist()
        print(name, metrics)

    joblib.dump({"vmin": float(vmin), "vmax": float(vmax), "seq_len": seq_len}, MODEL_DIR / "seq_scaler_registrations.pkl")
    pd.DataFrame({k: pd.Series(v) for k, v in preds_store.items()}).to_csv(
        FORE / "national_registrations_test_dl.csv", index=False
    )

    # Future forecast with CNN-LSTM
    model = keras.models.load_model(MODEL_DIR / "cnn_lstm_model.keras")
    hist = list(scaled)
    future_scaled = []
    for _ in range(3):
        window = np.array(hist[-seq_len:], dtype=float).reshape(1, seq_len, 1)
        nxt = float(model.predict(window, verbose=0).reshape(-1)[0])
        future_scaled.append(nxt)
        hist.append(nxt)
    future = np.array(future_scaled) * denom + vmin
    fut_years = [int(years[-1]) + i for i in range(1, 4)]
    pd.DataFrame({"Year": fut_years, "Forecast_Registrations": np.maximum(0, future)}).to_csv(
        FORE / "national_registrations_future_cnn_lstm.csv", index=False
    )
    return results


def plot_results(all_results: Dict[str, Any]) -> None:
    rows = []
    for model, payload in all_results.items():
        m = payload.get("metrics") or {}
        if not isinstance(m, dict) or m.get("MAE") is None:
            continue
        rows.append(
            {
                "Model": model,
                "Target": "EV_Registrations",
                "MAE": m.get("MAE"),
                "RMSE": m.get("RMSE"),
                "MAPE": m.get("MAPE"),
                "R2": m.get("R2"),
                "Approx_Accuracy_100_minus_MAPE": m.get("Approx_Accuracy_100_minus_MAPE"),
                "Training_Time": payload.get("train_seconds"),
            }
        )
    if not rows:
        print("No numeric results to plot")
        return
    df = pd.DataFrame(rows).sort_values("RMSE")
    df.to_csv(OUT / "final_results.csv", index=False)
    df.to_csv(MET / "model_comparison_registrations.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(df["Model"], df["RMSE"], color="#2563EB")
    ax.set_ylabel("RMSE (test)")
    ax.set_title("Model Comparison — EV Registrations (chronological test)")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(OUT / "model_comparison.png", dpi=140)
    fig.savefig(FIG / "model_comparison.png", dpi=140)
    plt.close(fig)

    # Actual vs predicted for RF if available
    tab = FORE / "registrations_test_predictions_tabular.csv"
    if tab.exists():
        p = pd.read_csv(tab)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.scatter(p["Registrations"], p["pred_rf"], alpha=0.6, c="#06B6D4", label="RF")
        lims = [0, max(p["Registrations"].max(), p["pred_rf"].max()) * 1.05]
        ax.plot(lims, lims, "--", color="#94a3b8")
        ax.set_xlabel("Actual")
        ax.set_ylabel("Predicted")
        ax.set_title("Actual vs Predicted (Random Forest, test)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT / "actual_vs_predicted.png", dpi=140)
        fig.savefig(FIG / "actual_vs_predicted.png", dpi=140)
        plt.close(fig)

    fut = FORE / "national_registrations_future_cnn_lstm.csv"
    hist = load_national_annual()
    if fut.exists():
        fdf = pd.read_csv(fut)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(hist["Year"], hist["Registrations"], marker="o", label="Historical", color="#2563EB")
        ax.plot(fdf["Year"], fdf["Forecast_Registrations"], marker="s", label="CNN-LSTM Forecast", color="#10B981")
        ax.set_title("National EV Registrations — Historical + Forecast")
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT / "future_forecast.png", dpi=140)
        fig.savefig(FIG / "future_forecast.png", dpi=140)
        plt.close(fig)

    # Best model note
    best = df.iloc[0]
    (OUT / "best_model.json").write_text(
        json.dumps(
            {
                "best_by_rmse": best["Model"],
                "rmse": best["RMSE"],
                "mae": best["MAE"],
                "mape": best["MAPE"],
                "r2": best["R2"],
                "note": "CNN-LSTM remains the proposed research model even if another model wins on RMSE.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    all_results: Dict[str, Any] = {}
    all_results.update(train_tabular())
    all_results.update(train_arima_national())
    all_results.update(train_sequence_models(seq_len=3))
    (MET / "all_results_raw.json").write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    plot_results(all_results)
    print("Training + evaluation complete.")


if __name__ == "__main__":
    main()
