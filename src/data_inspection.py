"""
Dataset inspection for DataSet.zip (EV Market Growth Prediction).
Extracts inventory, quality stats, and target recommendations.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW_ROOT = ROOT / "data" / "raw" / "DataSet" / "DataSet"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_read(path: Path) -> Optional[pd.DataFrame]:
    try:
        if path.suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(path)
        return pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Failed to read {path}: {exc}")
        return None


def _year_bounds(df: pd.DataFrame) -> Dict[str, Any]:
    years: List[int] = []
    for col in df.columns:
        cl = str(col).lower()
        if cl == "year" or cl.endswith("_year"):
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            years.extend(int(x) for x in s.tolist() if 1900 <= x <= 2100)
        if cl in {"labels", "data"} and df[col].dtype == object:
            for val in df[col].dropna().head(50):
                try:
                    parsed = ast.literal_eval(str(val)) if isinstance(val, str) else val
                    if isinstance(parsed, list):
                        for x in parsed:
                            if isinstance(x, (int, float)) and 1900 <= int(x) <= 2100:
                                years.append(int(x))
                except Exception:  # noqa: BLE001
                    continue
    if not years:
        return {"min_year": None, "max_year": None}
    return {"min_year": min(years), "max_year": max(years)}


def _unique_sample(df: pd.DataFrame, col_names: List[str], limit: int = 40) -> List[str]:
    for c in col_names:
        if c in df.columns:
            vals = sorted({str(x) for x in df[c].dropna().unique().tolist()})
            return vals[:limit]
    return []


def profile_file(path: Path) -> Dict[str, Any]:
    rel = str(path.relative_to(RAW_ROOT)).replace("\\", "/")
    df = _safe_read(path)
    if df is None:
        return {"file": rel, "error": "unreadable"}

    missing = {c: int(df[c].isna().sum()) for c in df.columns}
    dups = int(df.duplicated().sum())
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if c not in num_cols]
    yb = _year_bounds(df)

    possible_targets = [
        c
        for c in df.columns
        if any(
            k in str(c).lower()
            for k in (
                "registration",
                "revenue",
                "transaction",
                "count",
                "ev_",
            )
        )
    ]

    return {
        "file": rel,
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "column_names": list(map(str, df.columns)),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "missing_values": missing,
        "duplicate_rows": dups,
        "numeric_columns": num_cols,
        "categorical_columns": cat_cols,
        "min_year": yb["min_year"],
        "max_year": yb["max_year"],
        "unique_states": _unique_sample(df, ["State", "Filter_State"]),
        "unique_vehicle_types": _unique_sample(df, ["VehicleType", "Vehicle_Type"]),
        "possible_targets": possible_targets,
        "sample_head": df.head(2).astype(str).to_dict(orient="records"),
    }


def recommend_targets(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "primary_target": {
            "name": "EV_Registrations",
            "preferred_source": "Register/ev_yearwise_registration.csv",
            "columns": ["State", "VehicleType", "Year", "Registrations"],
            "frequency": "annual",
            "reason": "Already tidy long-format annual registrations (1067 rows).",
        },
        "secondary_targets": [
            {
                "name": "EV_Transactions",
                "preferred_source": "Revenue/Transaction_data(2010_2026)/*.csv",
                "columns": ["State", "Year", "Month", "EV_Transactions"],
                "frequency": "monthly",
            },
            {
                "name": "EV_Revenue",
                "preferred_source": "Revenue/Revenue_fee_line_chart(2010-2026)/*.csv",
                "columns": ["State", "Year", "Month", "Revenue"],
                "frequency": "monthly",
            },
        ],
        "not_supported": [
            "Charging stations — not present in DataSet.zip",
            "Battery health sensors — not present",
            "True geospatial deep learning — only state codes available",
        ],
        "merge_plan": {
            "annual_registrations": "Use ev_yearwise_registration.csv as primary; expand registration_2010-2026.csv lists as validation/supplement without duplicating identical rows.",
            "monthly_transactions": "Concatenate all EV_Transaction_Line_Chart*.csv; build datetime from Year+Month.",
            "monthly_revenue": "Concatenate all EV_Revenue_Line_Chart*.csv; build datetime from Year+Month.",
            "do_not": "Do not join monthly revenue into annual registration rows at monthly grain without aggregation. Aggregate to common frequency first.",
        },
        "training_strategy": {
            "approach_1": "Annual EV registration forecast (Naive, ARIMA, RF, XGB, CNN, LSTM, CNN-LSTM) with chronological split.",
            "approach_2": "Monthly EV transaction/revenue forecast (ARIMA/SARIMA, CNN, LSTM, CNN-LSTM) with chronological split.",
            "split": "70/15/15 chronological when enough points; otherwise leave-last-N-years out.",
        },
    }


def main() -> None:
    if not RAW_ROOT.exists():
        raise SystemExit(f"Raw dataset not found at {RAW_ROOT}. Extract DataSet.zip first.")

    files = sorted(
        [p for p in RAW_ROOT.rglob("*") if p.suffix.lower() in {".csv", ".xlsx", ".xls"}]
    )
    print(f"Found {len(files)} tabular files under {RAW_ROOT}")

    profiles = [profile_file(p) for p in files]
    recommendations = recommend_targets(profiles)

    report = {
        "dataset_root": str(RAW_ROOT),
        "file_count": len(files),
        "files": profiles,
        "recommendations": recommendations,
        "relationships": {
            "overlapping_registration_sources": [
                "ev_yearwise_registration.csv",
                "registration_2010-2026.csv (nested lists)",
                "ev_data.csv (single nested sample)",
            ],
            "distributional_tables": [
                "fuel_type_ev_data.csv",
                "ev_emission_distribution.csv",
                "ev_vehicle_class_distribution.csv",
                "top5_vehicle_makers_all_states.csv",
                "top5_states_all_filters.csv",
            ],
        },
    }

    json_path = OUT_DIR / "data_profile.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    rows = []
    for p in profiles:
        if "error" in p:
            rows.append({"file": p["file"], "error": p["error"]})
            continue
        rows.append(
            {
                "file": p["file"],
                "rows": p["rows"],
                "columns": p["columns"],
                "column_names": "|".join(p["column_names"]),
                "duplicate_rows": p["duplicate_rows"],
                "min_year": p["min_year"],
                "max_year": p["max_year"],
                "possible_targets": "|".join(p["possible_targets"]),
                "missing_total": sum(p["missing_values"].values()),
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "data_profile.csv", index=False)

    print(f"Wrote {json_path}")
    print(f"Wrote {OUT_DIR / 'data_profile.csv'}")
    print("\n=== TARGET RECOMMENDATION ===")
    print(json.dumps(recommendations, indent=2))


if __name__ == "__main__":
    main()
