"""Forecast helpers for Flask / CLI — registrations (annual) and transactions/revenue (monthly)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
FORE = ROOT / "outputs" / "forecasts"

FEATURE_DISPLAY_NAMES = {
    "lag_1": "Historical value (lag 1)",
    "lag_2": "Historical value (lag 2)",
    "lag_3": "Historical value (lag 3)",
    "rolling_mean_3": "3-period rolling mean",
    "rolling_mean_6": "6-period rolling mean",
    "rolling_mean_12": "12-period rolling mean",
    "yoy_growth": "Year-over-year growth",
    "mom_growth": "Month-over-month growth",
    "Year": "Year",
    "MonthNum": "Month",
    "State_enc": "State / Region",
    "VehicleType_enc": "Vehicle Type",
}


def feature_display_name(name: str) -> str:
    return FEATURE_DISPLAY_NAMES.get(name, name.replace("_", " ").title())


def _trend_extrapolate(values: List[float], n: int) -> List[float]:
    hist = list(values)
    out: List[float] = []
    for _ in range(n):
        yoy = pd.Series(hist).pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        growth = float(yoy.tail(3).median()) if len(yoy) else 0.05
        growth = float(np.clip(growth, -0.5, 1.5))
        nxt = max(0.0, hist[-1] * (1 + growth))
        out.append(nxt)
        hist.append(nxt)
    return out


def _accuracy_block() -> Dict:
    path = ROOT / "outputs" / "metrics" / "model_comparison_registrations.csv"
    out: Dict = {
        "best_model": "Naive",
        "approx_accuracy": None,
        "MAPE": None,
        "MAE": None,
        "RMSE": None,
        "R2": None,
        "note": "Held-out test years. Approx. accuracy = max(0, 100 − MAPE).",
    }
    if not path.exists():
        return out
    df = pd.read_csv(path)
    if df.empty:
        return out
    rows = []
    for _, r in df.iterrows():
        mape = float(r["MAPE"]) if pd.notna(r.get("MAPE")) else None
        rows.append(
            {
                "model": str(r["Model"]),
                "MAE": float(r["MAE"]) if pd.notna(r.get("MAE")) else None,
                "RMSE": float(r["RMSE"]) if pd.notna(r.get("RMSE")) else None,
                "MAPE": mape,
                "R2": float(r["R2"]) if pd.notna(r.get("R2")) else None,
                "approx_accuracy": round(max(0.0, 100.0 - mape), 1) if mape is not None else None,
            }
        )
    best = min(rows, key=lambda x: x["RMSE"] if x["RMSE"] is not None else float("inf"))
    out.update(
        {
            "best_model": best["model"],
            "approx_accuracy": best.get("approx_accuracy"),
            "MAPE": best.get("MAPE"),
            "MAE": best.get("MAE"),
            "RMSE": best.get("RMSE"),
            "R2": best.get("R2"),
            "all_models": rows,
        }
    )
    return out


def forecast_registrations(horizon: int = 3, state: str = "ALL", vehicle_type: str = "All") -> Dict:
    from src.state_names import display_name

    state = (state or "ALL").upper()
    regs = pd.read_csv(PROC / "ev_registrations_annual.csv")
    regs["State"] = regs["State"].astype(str).str.upper()
    if state == "ALL":
        g = regs.groupby("Year", as_index=False)["Registrations"].sum().sort_values("Year")
    else:
        g = regs[(regs["State"] == state)].copy()
        if vehicle_type and vehicle_type not in ("All", "ALL", ""):
            g = g[g["VehicleType"] == vehicle_type]
        g = g.groupby("Year", as_index=False)["Registrations"].sum().sort_values("Year")
    if g.empty:
        return {"error": f"No history for {display_name(state)}"}

    years = g["Year"].astype(int).tolist()
    vals = g["Registrations"].astype(float).tolist()
    preds = _trend_extrapolate(vals, horizon)
    forecast = [{"year": years[-1] + i + 1, "period": str(years[-1] + i + 1), "value": preds[i]} for i in range(horizon)]
    acc = _accuracy_block()
    return {
        "target": "EV_Registrations",
        "state": state,
        "state_name": display_name(state),
        "vehicle_type": vehicle_type or "All",
        "model": "trend_extrapolation",
        "frequency": "annual",
        "forecast": forecast,
        "history": {"dates": [str(y) for y in years], "values": vals},
        "accuracy": acc,
    }


def forecast_monthly(target: str, horizon: int = 6, state: str = "ALL") -> Dict:
    """Forecast EV_Transactions or Revenue at monthly frequency."""
    state = (state or "ALL").upper()
    target = (target or "transactions").lower()
    if target in ("revenue", "ev_revenue"):
        path = PROC / "ev_revenue_monthly.csv"
        value_col = "Revenue"
        label = "EV_Revenue"
    else:
        path = PROC / "ev_transactions_monthly.csv"
        value_col = "EV_Transactions"
        label = "EV_Transactions"

    if not path.exists():
        return {"error": f"Processed file missing for {label}"}

    df = pd.read_csv(path, parse_dates=["Date"])
    df["State"] = df["State"].astype(str).str.upper()
    if state == "ALL":
        g = df.groupby("Date", as_index=False)[value_col].sum().sort_values("Date")
    else:
        g = df[df["State"] == state].groupby("Date", as_index=False)[value_col].sum().sort_values("Date")
    if g.empty:
        return {"error": f"No {label} history for state={state}"}

    dates = pd.to_datetime(g["Date"]).tolist()
    vals = g[value_col].astype(float).tolist()
    preds = _trend_extrapolate(vals, horizon)
    last = dates[-1]
    forecast = []
    for i, v in enumerate(preds):
        d = last + pd.DateOffset(months=i + 1)
        forecast.append({"period": d.strftime("%Y-%m"), "year": int(d.year), "month": int(d.month), "value": float(v)})
    from src.state_names import display_name

    return {
        "target": label,
        "state": state,
        "state_name": display_name(state),
        "model": "trend_extrapolation",
        "frequency": "monthly",
        "forecast": forecast,
        "history": {
            "dates": [d.strftime("%Y-%m") for d in dates],
            "values": vals,
        },
        "accuracy": _accuracy_block(),
    }


def forecast_any(
    target: str = "registrations",
    horizon: int = 3,
    state: str = "ALL",
    vehicle_type: str = "All",
) -> Dict:
    t = (target or "registrations").lower().replace(" ", "_")
    if t in ("transactions", "ev_transactions", "tx"):
        return forecast_monthly("transactions", horizon=horizon, state=state)
    if t in ("revenue", "ev_revenue"):
        return forecast_monthly("revenue", horizon=horizon, state=state)
    return forecast_registrations(horizon=horizon, state=state, vehicle_type=vehicle_type)


def main() -> None:
    out = forecast_registrations(3, "ALL", "All")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
