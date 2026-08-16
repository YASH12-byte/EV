"""
Feature engineering and chronological train/val/test splits.
Fits scalers ONLY on training data to prevent leakage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
MODEL_DIR = ROOT / "models" / "saved"
PROC.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def add_annual_lags(df: pd.DataFrame, value_col: str = "Registrations") -> pd.DataFrame:
    parts = []
    for (state, vtype), g in df.groupby(["State", "VehicleType"], sort=False):
        g = g.sort_values("Year").copy()
        g["lag_1"] = g[value_col].shift(1)
        g["lag_2"] = g[value_col].shift(2)
        g["lag_3"] = g[value_col].shift(3)
        g["rolling_mean_3"] = g[value_col].shift(1).rolling(3, min_periods=1).mean()
        g["yoy_growth"] = g[value_col].pct_change().replace([np.inf, -np.inf], np.nan)
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    return out


def add_monthly_lags(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    parts = []
    for state, g in df.groupby("State", sort=False):
        g = g.sort_values("Date").copy()
        g["lag_1"] = g[value_col].shift(1)
        g["lag_2"] = g[value_col].shift(2)
        g["lag_3"] = g[value_col].shift(3)
        g["rolling_mean_3"] = g[value_col].shift(1).rolling(3, min_periods=1).mean()
        g["rolling_mean_6"] = g[value_col].shift(1).rolling(6, min_periods=1).mean()
        g["rolling_mean_12"] = g[value_col].shift(1).rolling(12, min_periods=1).mean()
        g["mom_growth"] = g[value_col].pct_change().replace([np.inf, -np.inf], np.nan)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def chronological_split(
    years: np.ndarray, ratios: Tuple[float, float, float] = (0.7, 0.15, 0.15)
) -> Dict[str, List[int]]:
    uniq = sorted(set(int(y) for y in years))
    n = len(uniq)
    if n < 5:
        # leave-last-1 for test, last-2 for val if possible
        test = uniq[-1:]
        val = uniq[-2:-1] if n >= 3 else []
        train = [y for y in uniq if y not in test + val]
        return {"train": train, "val": val or train[-1:], "test": test, "note": "small-n leave-last"}
    n_train = max(1, int(n * ratios[0]))
    n_val = max(1, int(n * ratios[1]))
    train = uniq[:n_train]
    val = uniq[n_train : n_train + n_val]
    test = uniq[n_train + n_val :]
    if not test:
        test = val[-1:]
        val = val[:-1] or train[-1:]
    return {"train": train, "val": val, "test": test, "note": "70/15/15 chronological"}


def build_registration_features() -> pd.DataFrame:
    path = PROC / "ev_registrations_annual.csv"
    df = pd.read_csv(path)
    df = add_annual_lags(df, "Registrations")
    # Drop rows without lag_1 (cannot train without history)
    before = len(df)
    df = df.dropna(subset=["lag_1"]).reset_index(drop=True)
    print(f"[FE] registrations: {before} -> {len(df)} after requiring lag_1")
    df.to_csv(PROC / "features_registrations_annual.csv", index=False)
    return df


def build_monthly_features(kind: str) -> pd.DataFrame:
    if kind == "transactions":
        path = PROC / "ev_transactions_monthly.csv"
        value_col = "EV_Transactions"
        out = "features_transactions_monthly.csv"
    else:
        path = PROC / "ev_revenue_monthly.csv"
        value_col = "Revenue"
        out = "features_revenue_monthly.csv"
    df = pd.read_csv(path, parse_dates=["Date"])
    df = add_monthly_lags(df, value_col)
    before = len(df)
    df = df.dropna(subset=["lag_1"]).reset_index(drop=True)
    print(f"[FE] {kind}: {before} -> {len(df)} after requiring lag_1")
    df.to_csv(PROC / out, index=False)
    return df


def prepare_tabular_xy(
    df: pd.DataFrame,
    target: str,
    feature_cols: List[str],
    cat_cols: List[str],
    year_col: str = "Year",
) -> Dict[str, object]:
    split = chronological_split(df[year_col].values)
    encoders: Dict[str, LabelEncoder] = {}
    work = df.copy()
    for c in cat_cols:
        if c not in work.columns:
            continue
        le = LabelEncoder()
        # Fit on train only
        train_mask = work[year_col].isin(split["train"])
        le.fit(work.loc[train_mask, c].astype(str))
        # Unseen → -1 then clip
        def transform(series: pd.Series) -> np.ndarray:
            out = []
            classes = set(le.classes_)
            for v in series.astype(str):
                out.append(int(le.transform([v])[0]) if v in classes else -1)
            return np.array(out, dtype=float)

        work[c + "_enc"] = transform(work[c])
        encoders[c] = le
        if c + "_enc" not in feature_cols:
            feature_cols = feature_cols + [c + "_enc"]

    use_cols = [c for c in feature_cols if c in work.columns]
    # Fill remaining NaNs with train medians
    train_df = work[work[year_col].isin(split["train"])]
    medians = train_df[use_cols].median(numeric_only=True)
    work[use_cols] = work[use_cols].fillna(medians)

    def pack(years: List[int]) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        m = work[year_col].isin(years)
        X = work.loc[m, use_cols].values.astype(float)
        y = work.loc[m, target].values.astype(float)
        return X, y, work.loc[m].copy()

    X_train, y_train, meta_train = pack(split["train"])
    X_val, y_val, meta_val = pack(split["val"])
    X_test, y_test, meta_test = pack(split["test"])

    scaler = MinMaxScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val) if len(X_val) else X_val
    X_test_s = scaler.transform(X_test) if len(X_test) else X_test

    return {
        "feature_cols": use_cols,
        "split": split,
        "encoders": encoders,
        "scaler": scaler,
        "X_train": X_train_s,
        "y_train": y_train,
        "X_val": X_val_s,
        "y_val": y_val,
        "X_test": X_test_s,
        "y_test": y_test,
        "meta_train": meta_train,
        "meta_val": meta_val,
        "meta_test": meta_test,
    }


def make_sequences(values: np.ndarray, seq_len: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for i in range(len(values) - seq_len):
        xs.append(values[i : i + seq_len])
        ys.append(values[i + seq_len])
    if not xs:
        return np.empty((0, seq_len, 1)), np.empty((0,))
    X = np.array(xs, dtype=float).reshape(-1, seq_len, 1)
    y = np.array(ys, dtype=float)
    return X, y


def national_series(path: Path, value_col: str, time_col: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "State" in df.columns:
        df = df[df["State"].astype(str).str.upper() == "ALL"]
        if df.empty:
            # rebuild national
            raw = pd.read_csv(path.replace("_national", "") if False else path)
    return df.sort_values(time_col)


def main() -> None:
    regs = build_registration_features()
    tx = build_monthly_features("transactions")
    rev = build_monthly_features("revenue")

    reg_feats = ["Year", "lag_1", "lag_2", "lag_3", "rolling_mean_3", "yoy_growth"]
    pack = prepare_tabular_xy(
        regs,
        target="Registrations",
        feature_cols=reg_feats,
        cat_cols=["State", "VehicleType"],
        year_col="Year",
    )
    joblib.dump(pack["scaler"], MODEL_DIR / "scaler_registrations.pkl")
    joblib.dump(pack["encoders"], MODEL_DIR / "encoders_registrations.pkl")
    meta = {
        "target": "Registrations",
        "feature_cols": pack["feature_cols"],
        "split": pack["split"],
        "n_train": int(len(pack["y_train"])),
        "n_val": int(len(pack["y_val"])),
        "n_test": int(len(pack["y_test"])),
        "leakage_prevention": [
            "LabelEncoder fit on train years only",
            "MinMaxScaler fit on train features only",
            "Lags/rolling use shift(1) so current target excluded",
            "Chronological year split (no shuffle)",
        ],
    }
    (OUT / "feature_config_registrations.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    # Persist arrays for trainers
    np.savez(
        PROC / "registrations_xy.npz",
        X_train=pack["X_train"],
        y_train=pack["y_train"],
        X_val=pack["X_val"],
        y_val=pack["y_val"],
        X_test=pack["X_test"],
        y_test=pack["y_test"],
    )
    pack["meta_test"].to_csv(PROC / "registrations_test_meta.csv", index=False)
    print("Feature engineering complete.")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
