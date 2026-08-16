"""
Data cleaning and construction of primary forecasting datasets.
All decisions are logged to outputs/cleaning_log.json.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW = ROOT / "data" / "raw" / "DataSet" / "DataSet"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
PROC.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

CLEAN_LOG: List[Dict[str, Any]] = []


def log(action: str, detail: str, **extra: Any) -> None:
    entry = {"action": action, "detail": detail, **extra}
    CLEAN_LOG.append(entry)
    print(f"[CLEAN] {action}: {detail}")


def parse_count_dict(val: Any) -> Optional[float]:
    """Parse {'totalTransactions': '22,387'} or plain numbers."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    m = re.search(r"['\"]totalTransactions['\"]\s*:\s*['\"]?([\d,]+)", s)
    if m:
        return float(m.group(1).replace(",", ""))
    s2 = s.replace(",", "")
    try:
        return float(s2)
    except ValueError:
        return None


def expand_nested_registration(df: pd.DataFrame) -> pd.DataFrame:
    """Expand data/labels list columns into Year/Registrations rows."""
    rows = []
    for _, r in df.iterrows():
        try:
            data = ast.literal_eval(str(r["data"])) if isinstance(r["data"], str) else r["data"]
            labels = ast.literal_eval(str(r["labels"])) if isinstance(r["labels"], str) else r["labels"]
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, list) or not isinstance(labels, list):
            continue
        n = min(len(data), len(labels))
        for i in range(n):
            rows.append(
                {
                    "State": r.get("State"),
                    "VehicleType": r.get("VehicleType"),
                    "Year": int(labels[i]),
                    "Registrations": float(data[i]),
                }
            )
    out = pd.DataFrame(rows)
    log("expand_nested", f"Expanded registration lists into {len(out)} rows")
    return out


def month_to_num(m: Any) -> Optional[int]:
    if pd.isna(m):
        return None
    if isinstance(m, (int, float)) and 1 <= int(m) <= 12:
        return int(m)
    key = str(m).strip().lower()
    return MONTH_MAP.get(key)


def concat_folder(folder: Path, pattern: str) -> pd.DataFrame:
    frames = []
    for p in sorted(folder.glob(pattern)):
        if p.suffix.lower() != ".csv":
            continue
        try:
            frames.append(pd.read_csv(p))
        except Exception as exc:  # noqa: BLE001
            log("skip_file", f"{p.name}: {exc}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def clean_registrations() -> pd.DataFrame:
    primary = pd.read_csv(RAW / "Register" / "ev_yearwise_registration.csv")
    primary["Year"] = pd.to_numeric(primary["Year"], errors="coerce").astype("Int64")
    primary["Registrations"] = pd.to_numeric(primary["Registrations"], errors="coerce")
    primary["State"] = primary["State"].astype(str).str.strip().str.upper()
    primary["VehicleType"] = primary["VehicleType"].astype(str).str.strip()
    before = len(primary)
    primary = primary.dropna(subset=["Year", "Registrations", "State", "VehicleType"])
    primary = primary.drop_duplicates(subset=["State", "VehicleType", "Year"])
    primary = primary.sort_values(["State", "VehicleType", "Year"]).reset_index(drop=True)
    log(
        "clean_primary_registrations",
        f"Kept {len(primary)}/{before} rows; removed nulls/duplicates",
        source="ev_yearwise_registration.csv",
    )

    nested = pd.read_csv(RAW / "Register" / "registration_2010-2026.csv")
    expanded = expand_nested_registration(nested)
    if not expanded.empty:
        expanded["State"] = expanded["State"].astype(str).str.strip().str.upper()
        expanded["VehicleType"] = expanded["VehicleType"].astype(str).str.strip()
        # Prefer primary when both exist for same key
        merged = expanded.merge(
            primary[["State", "VehicleType", "Year"]],
            on=["State", "VehicleType", "Year"],
            how="left",
            indicator=True,
        )
        only_expanded = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
        only_expanded = only_expanded[["State", "VehicleType", "Year", "Registrations"]]
        combined = pd.concat([primary, only_expanded], ignore_index=True)
        combined = combined.drop_duplicates(subset=["State", "VehicleType", "Year"])
        combined = combined.sort_values(["State", "VehicleType", "Year"]).reset_index(drop=True)
        log(
            "merge_registrations",
            f"Added {len(only_expanded)} non-overlapping expanded rows; total={len(combined)}",
        )
    else:
        combined = primary

    # National aggregate
    national = (
        combined.groupby("Year", as_index=False)["Registrations"].sum()
        .assign(State="ALL", VehicleType="All")
    )
    national = national[["State", "VehicleType", "Year", "Registrations"]]
    log("national_aggregate", f"National annual series length={len(national)}")

    combined.to_csv(PROC / "ev_registrations_annual.csv", index=False)
    national.to_csv(PROC / "ev_registrations_national_annual.csv", index=False)
    return combined


def clean_monthly(kind: str) -> pd.DataFrame:
    if kind == "transactions":
        folder = RAW / "Revenue" / "Transaction_data(2010_2026)"
        pattern = "EV_Transaction_Line_Chart*.csv"
        value_col = "EV_Transactions"
        out_name = "ev_transactions_monthly.csv"
    else:
        folder = RAW / "Revenue" / "Revenue_fee_line_chart(2010-2026)"
        pattern = "EV_Revenue_Line_Chart*.csv"
        value_col = "Revenue"
        out_name = "ev_revenue_monthly.csv"

    df = concat_folder(folder, pattern)
    if df.empty:
        log("empty_monthly", f"No files for {kind}")
        return df

    df["State"] = df["State"].astype(str).str.strip().str.upper()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["MonthNum"] = df["Month"].map(month_to_num)
    df[value_col] = (
        df[value_col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )
    before = len(df)
    df = df.dropna(subset=["State", "Year", "MonthNum", value_col])
    df = df[(df["MonthNum"] >= 1) & (df["MonthNum"] <= 12)]
    df["Year"] = df["Year"].astype(int)
    df["MonthNum"] = df["MonthNum"].astype(int)
    df["Date"] = pd.to_datetime(
        dict(year=df["Year"], month=df["MonthNum"], day=1), errors="coerce"
    )
    df = df.dropna(subset=["Date"])
    df = df.drop_duplicates(subset=["State", "Date"])
    df = df.sort_values(["State", "Date"]).reset_index(drop=True)
    # Clip extreme negatives if any
    neg = int((df[value_col] < 0).sum())
    if neg:
        df.loc[df[value_col] < 0, value_col] = np.nan
        df[value_col] = df.groupby("State")[value_col].ffill().bfill()
        log("abnormal_values", f"Replaced {neg} negative {value_col} via ffill/bfill")

    log("clean_monthly", f"{kind}: kept {len(df)}/{before} rows -> {out_name}")
    cols = ["State", "Year", "Month", "MonthNum", "Date", value_col]
    df[cols].to_csv(PROC / out_name, index=False)

    national = (
        df.groupby("Date", as_index=False)
        .agg(Year=("Year", "first"), MonthNum=("MonthNum", "first"), **{value_col: (value_col, "sum")})
        .assign(State="ALL")
    )
    national.to_csv(PROC / out_name.replace(".csv", "_national.csv"), index=False)
    return df


def clean_distributions() -> None:
    # Fuel
    fuel = pd.read_csv(RAW / "Register" / "fuel_type_ev_data.csv")
    fuel["State"] = fuel["State"].astype(str).str.strip().str.upper()
    fuel["Count"] = pd.to_numeric(fuel["Count"], errors="coerce")
    fuel = fuel.dropna(subset=["Count"])
    fuel.to_csv(PROC / "fuel_type_distribution.csv", index=False)

    emis = pd.read_csv(RAW / "Register" / "ev_emission_distribution.csv")
    emis["State"] = emis["State"].astype(str).str.strip().str.upper()
    emis["RegistrationCount"] = pd.to_numeric(emis["RegistrationCount"], errors="coerce")
    emis = emis.dropna(subset=["RegistrationCount"])
    emis.to_csv(PROC / "emission_distribution.csv", index=False)

    vclass = pd.read_csv(RAW / "Register" / "ev_vehicle_class_distribution.csv")
    vclass["State"] = vclass["State"].astype(str).str.strip().str.upper()
    vclass["RegistrationCount"] = pd.to_numeric(vclass["RegistrationCount"], errors="coerce")
    vclass = vclass.dropna(subset=["RegistrationCount"])
    vclass.to_csv(PROC / "vehicle_class_distribution.csv", index=False)

    makers = pd.read_csv(RAW / "Register" / "top5_vehicle_makers_all_states.csv")
    makers["State"] = makers["State"].astype(str).str.strip().str.upper()
    makers["EV_Registrations"] = pd.to_numeric(makers["EV_Registrations"], errors="coerce")
    makers = makers.dropna(subset=["EV_Registrations"])
    makers.to_csv(PROC / "top_vehicle_makers.csv", index=False)

    dash = pd.read_csv(RAW / "Register" / "dashboardcount_all_states.csv")
    dash["State"] = dash["State"].astype(str).str.strip().str.upper()
    dash["Total_EV_Registrations"] = dash["Total_EV_Registrations"].map(parse_count_dict)
    dash = dash.dropna(subset=["Total_EV_Registrations"])
    dash.to_csv(PROC / "dashboard_state_totals.csv", index=False)
    log("distributions", "Saved fuel/emission/class/makers/dashboard cleaned tables")


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Missing raw data at {RAW}")

    regs = clean_registrations()
    tx = clean_monthly("transactions")
    rev = clean_monthly("revenue")
    clean_distributions()

    summary = {
        "registrations_rows": int(len(regs)),
        "transactions_rows": int(len(tx)),
        "revenue_rows": int(len(rev)),
        "states_registration": sorted(regs["State"].unique().tolist()),
        "year_range_registration": [int(regs["Year"].min()), int(regs["Year"].max())],
        "cleaning_log": CLEAN_LOG,
        "leakage_notes": [
            "Scalers and encoders must be fit on training period only (enforced in feature_engineering/train scripts).",
            "Monthly features are not joined into annual targets at monthly grain.",
            "Forecast inputs use only lagged historical values.",
        ],
    }
    (OUT / "cleaning_log.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Processed datasets written to {PROC}")
    print(f"Cleaning log → {OUT / 'cleaning_log.json'}")


if __name__ == "__main__":
    main()
