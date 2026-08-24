"""
Explainable AI engine for EV registration forecasting (DataSet.zip features only).
SHAP/LIME explain model contributions — not proven real-world causation.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "xai"
MODEL_DIR = ROOT / "models" / "saved"
CACHE_DIR = OUT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-process caches (avoid reloading model/scaler/SHAP on every request)
_ARTIFACTS: Dict[str, Any] = {}
_DATA_CACHE: Dict[str, Any] = {}

# Factors commonly requested but NOT in DataSet.zip
UNAVAILABLE_FACTORS = [
    "Charging infrastructure availability",
    "Government policy / subsidy indicators",
    "Fuel prices",
    "Battery cost",
    "Economic indicators (GDP, etc.)",
    "EV adoption index (external)",
]

FEATURE_META: Dict[str, Dict[str, str]] = {
    "Year": {"label": "Year", "group": "temporal", "description": "Calendar year of the observation."},
    "lag_1": {"label": "Previous year EV registrations", "group": "temporal", "description": "Registrations one year earlier for this state and vehicle type."},
    "lag_2": {"label": "EV registrations (2 years ago)", "group": "temporal", "description": "Historical registrations from two years prior."},
    "lag_3": {"label": "EV registrations (3 years ago)", "group": "temporal", "description": "Historical registrations from three years prior."},
    "rolling_mean_3": {"label": "3-year rolling average", "group": "temporal", "description": "Average of the previous three years' registrations (excluding current year)."},
    "yoy_growth": {"label": "Year-over-year growth rate", "group": "temporal", "description": "Percentage change vs. the previous year."},
    "State_enc": {"label": "State / region", "group": "spatial", "description": "Encoded state identity from the dataset."},
    "VehicleType_enc": {"label": "Vehicle type", "group": "spatial", "description": "Transport vs non-transport category."},
    "mom_growth": {"label": "Month-over-month growth", "group": "temporal", "description": "Monthly growth rate (monthly targets only)."},
    "rolling_mean_6": {"label": "6-month rolling average", "group": "temporal", "description": "Six-month rolling mean (monthly targets)."},
    "rolling_mean_12": {"label": "12-month rolling average", "group": "temporal", "description": "Twelve-month rolling mean (monthly targets)."},
}

DISCLAIMER = (
    "SHAP and LIME describe factors that influenced the model prediction "
    "(correlation / contribution), not guaranteed real-world causation."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _feature_label(name: str) -> str:
    return FEATURE_META.get(name, {}).get("label", name.replace("_", " ").title())


def _growth_rate(current: float, previous: Optional[float]) -> Optional[float]:
    if previous is None or previous == 0 or not np.isfinite(previous):
        return None
    return float((current - previous) / previous * 100.0)


def _direction(pct: Optional[float]) -> str:
    if pct is None or not np.isfinite(pct):
        return "Stable"
    if pct > 0.5:
        return "Increase"
    if pct < -0.5:
        return "Decrease"
    return "Stable"


def _trend_label(pct: Optional[float]) -> str:
    d = _direction(pct)
    return {"Increase": "Growing", "Decrease": "Declining", "Stable": "Stable"}[d]


def _load_config() -> Dict[str, Any]:
    path = ROOT / "outputs" / "feature_config_registrations.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"feature_cols": []}


def _load_global_ranking() -> List[Dict[str, Any]]:
    path = OUT / "feature_importance.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for r in data.get("ranking", []):
        rows.append(
            {
                "feature": r["feature"],
                "label": _feature_label(r["feature"]),
                "importance": float(r["importance"]),
                "impact": "Positive",
            }
        )
    return rows


def _load_predictions() -> pd.DataFrame:
    """Prefer file that includes model prediction columns (pred_rf, etc.)."""
    if "preds" in _DATA_CACHE:
        return _DATA_CACHE["preds"]
    alt = ROOT / "outputs" / "forecasts" / "registrations_test_predictions_tabular.csv"
    meta = PROC / "registrations_test_meta.csv"
    if alt.exists():
        df = pd.read_csv(alt)
    elif meta.exists():
        df = pd.read_csv(meta)
    else:
        df = pd.DataFrame()
    if not df.empty:
        df["State"] = df["State"].astype(str).str.upper()
    _DATA_CACHE["preds"] = df
    return df


def _load_features() -> pd.DataFrame:
    if "feats" in _DATA_CACHE:
        return _DATA_CACHE["feats"]
    path = PROC / "features_registrations_annual.csv"
    if not path.exists():
        df = pd.DataFrame()
    else:
        df = pd.read_csv(path)
        df["State"] = df["State"].astype(str).str.upper()
    _DATA_CACHE["feats"] = df
    return df


def _get_rf_artifacts() -> Dict[str, Any]:
    """Load Random Forest + scaler + encoders + TreeExplainer once per process."""
    if _ARTIFACTS.get("ready"):
        return _ARTIFACTS
    model_path = MODEL_DIR / "random_forest.pkl"
    if not model_path.exists():
        return _ARTIFACTS
    _ARTIFACTS["model"] = joblib.load(model_path)
    sp = MODEL_DIR / "scaler_registrations.pkl"
    _ARTIFACTS["scaler"] = joblib.load(sp) if sp.exists() else None
    ep = MODEL_DIR / "encoders_registrations.pkl"
    _ARTIFACTS["encoders"] = joblib.load(ep) if ep.exists() else {}
    import shap

    _ARTIFACTS["explainer"] = shap.TreeExplainer(_ARTIFACTS["model"])
    ev = _ARTIFACTS["explainer"].expected_value
    _ARTIFACTS["base_value"] = float(np.asarray(ev).reshape(-1)[0]) if ev is not None else 0.0
    _ARTIFACTS["ready"] = True
    return _ARTIFACTS


def _cache_path(state: str, year: int, vehicle_type: str, target: str) -> Path:
    safe = f"{state}_{year}_{vehicle_type}_{target}".replace(" ", "_").replace("/", "-")
    return CACHE_DIR / f"dashboard_{safe}.json"


def _national_trend() -> pd.DataFrame:
    path = PROC / "ev_registrations_national_annual.csv"
    if path.exists():
        return pd.read_csv(path).sort_values("Year")
    feats = _load_features()
    if feats.empty:
        return pd.DataFrame()
    return (
        feats.groupby("Year", as_index=False)["Registrations"]
        .sum()
        .sort_values("Year")
    )


def _filter_rows(
    state: str,
    year: int,
    vehicle_type: str,
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return df
    state = (state or "ALL").upper()
    m = df["Year"] == int(year)
    if state != "ALL":
        m &= df["State"] == state
    if vehicle_type and vehicle_type not in ("All", "ALL", ""):
        m &= df["VehicleType"] == vehicle_type
    return df[m].copy()


def _select_row(
    state: str,
    year: int,
    vehicle_type: str,
    df: pd.DataFrame,
) -> Optional[pd.Series]:
    sub = _filter_rows(state, year, vehicle_type, df)
    if sub.empty:
        return None
    if (state or "ALL").upper() == "ALL" and len(sub) > 1:
        # Representative row: highest registrations (for single-row fallback display)
        return sub.sort_values("Registrations", ascending=False).iloc[0]
    return sub.iloc[0]


def _encode_row(row: pd.Series, feature_cols: List[str]) -> pd.Series:
    """Add State_enc / VehicleType_enc using saved encoders when missing."""
    work = row.copy()
    encoders = _get_rf_artifacts().get("encoders") or {}
    if not encoders:
        enc_path = MODEL_DIR / "encoders_registrations.pkl"
        if enc_path.exists():
            encoders = joblib.load(enc_path)
    for col, le in encoders.items():
        enc_col = f"{col}_enc"
        if enc_col in feature_cols and enc_col not in work.index and col in work.index:
            val = str(work[col])
            classes = set(le.classes_)
            work[enc_col] = float(le.transform([val])[0]) if val in classes else -1.0
    for c in feature_cols:
        if c not in work.index:
            work[c] = 0.0
    return work


def _scale_matrix(rows: pd.DataFrame, feature_cols: List[str]) -> Optional[np.ndarray]:
    if rows.empty:
        return None
    arts = _get_rf_artifacts()
    encoded = [_encode_row(r, feature_cols) for _, r in rows.iterrows()]
    X = np.array([[float(r[c]) for c in feature_cols] for r in encoded], dtype=float)
    scaler = arts.get("scaler")
    if scaler is not None:
        return scaler.transform(X)
    return X


def _scale_row(row: pd.Series, feature_cols: List[str]) -> Optional[np.ndarray]:
    mat = _scale_matrix(row.to_frame().T, feature_cols)
    return mat if mat is None else mat.reshape(1, -1)


def _format_num(n: Optional[float]) -> str:
    if n is None or not np.isfinite(n):
        return "—"
    return f"{float(n):,.0f}"


def _feature_references(feats: pd.DataFrame, feature_cols: List[str]) -> Dict[str, float]:
    refs: Dict[str, float] = {}
    if feats.empty:
        return refs
    for f in feature_cols:
        if f in feats.columns:
            refs[f] = float(feats[f].astype(float).mean())
    return refs


def _display_feature_value(feature: str, raw_val: float, row: pd.Series) -> str:
    if feature == "State_enc" and "State" in row.index:
        from src.state_names import display_name

        return display_name(str(row["State"]))
    if feature == "VehicleType_enc" and "VehicleType" in row.index:
        return str(row["VehicleType"])
    if feature == "yoy_growth":
        return f"{float(raw_val) * 100:.1f}%" if abs(float(raw_val)) <= 5 else f"{float(raw_val):.1f}%"
    if feature == "Year":
        return str(int(raw_val))
    return _format_num(raw_val)


def _shap_values(X_scaled: np.ndarray) -> Tuple[np.ndarray, float, str, Optional[str]]:
    """Batch TreeSHAP. X_scaled shape (n_samples, n_features)."""
    arts = _get_rf_artifacts()
    if not arts.get("ready"):
        return np.array([]), 0.0, "none", "Random Forest model not found. Run: python run_project.py"
    try:
        explainer = arts["explainer"]
        model = arts["model"]
        sv = explainer.shap_values(X_scaled)
        if isinstance(sv, list):
            sv = sv[0]
        sv = np.asarray(sv)
        if sv.ndim == 1:
            sv = sv.reshape(1, -1)
        base = arts["base_value"]
        preds = model.predict(X_scaled)
        # spot-check first row additivity
        if len(preds) and abs(base + float(sv[0].sum()) - float(preds[0])) > max(1.0, abs(preds[0]) * 0.01):
            return sv, base, "shap_tree", f"SHAP reconciliation gap on sample row"
        return sv, base, "shap_tree", None
    except Exception as exc:
        return np.array([]), 0.0, "none", f"Local SHAP failed: {exc}"


def _contribs_from_shap_row(
    shap_row: np.ndarray,
    feature_cols: List[str],
) -> List[Dict[str, Any]]:
    total_abs = float(np.abs(shap_row).sum()) or 1.0
    contribs = []
    for f, v in zip(feature_cols, shap_row):
        contribs.append(
            {
                "feature": f,
                "label": _feature_label(f),
                "shap_value": float(v),
                "contribution": float(v),
                "pct": float(abs(v) / total_abs * 100),
                "direction": "positive" if v >= 0 else "negative",
            }
        )
    contribs.sort(key=lambda x: -abs(x["shap_value"]))
    return contribs


def _local_shap(
    X_scaled: np.ndarray,
    feature_cols: List[str],
) -> Tuple[List[Dict[str, Any]], float, str, Optional[str]]:
    """TreeSHAP on Random Forest (single row). Returns (contribs, base, method, error)."""
    sv, base, method, err = _shap_values(X_scaled)
    if sv.size == 0:
        return [], base, method, err
    return _contribs_from_shap_row(sv[0], feature_cols), base, method, err


def _enrich_contributions(
    contribs: List[Dict[str, Any]],
    row: pd.Series,
    refs: Dict[str, float],
) -> List[Dict[str, Any]]:
    encoded = _encode_row(row, list({c["feature"] for c in contribs}))
    out = []
    for c in contribs:
        f = c["feature"]
        actual = float(encoded[f]) if f in encoded.index else None
        ref = refs.get(f)
        item = dict(c)
        if actual is not None and (math.isnan(actual) or math.isinf(actual)):
            actual = None
        if ref is not None and (math.isnan(ref) or math.isinf(ref)):
            ref = None
        item["actual_value"] = actual
        item["actual_display"] = _display_feature_value(f, actual, row) if actual is not None else "—"
        item["reference_value"] = ref
        item["reference_display"] = _format_num(ref) if ref is not None else "—"
        if f == "yoy_growth" and ref is not None:
            item["reference_display"] = f"{ref * 100:.1f}%"
        out.append(item)
    return out


def _compute_local_explanation(
    state: str,
    year: int,
    vehicle_type: str,
    feats: pd.DataFrame,
    feature_cols: List[str],
    preds: pd.DataFrame,
) -> Dict[str, Any]:
    """Genuine local TreeSHAP for the selected input row(s)."""
    state = (state or "ALL").upper()
    rows = _filter_rows(state, year, vehicle_type, feats)
    refs = _feature_references(feats, feature_cols)

    if rows.empty:
        return {"ok": False, "error": f"No feature row for state={state}, year={year}, vehicle={vehicle_type}"}
    arts = _get_rf_artifacts()
    if not arts.get("ready"):
        return {"ok": False, "error": "Random Forest model not found. Run: python run_project.py"}

    model = arts["model"]
    pred_rows = _filter_rows(state, year, vehicle_type, preds)

    # Resolve displayed prediction from saved test preds or live RF
    predicted = None
    if not pred_rows.empty and "pred_rf" in pred_rows.columns:
        predicted = float(pred_rows["pred_rf"].sum()) if state == "ALL" else float(pred_rows["pred_rf"].iloc[0])
    elif not pred_rows.empty:
        for col in ("pred_rf", "pred_xgb", "pred_naive"):
            if col in pred_rows.columns:
                predicted = float(pred_rows[col].sum()) if state == "ALL" else float(pred_rows[col].iloc[0])
                break

    if state == "ALL" and len(rows) > 1:
        X_all = _scale_matrix(rows, feature_cols)
        if X_all is None:
            return {"ok": False, "error": "Could not scale feature rows for SHAP."}
        sv_all, base, method, error = _shap_values(X_all)
        if sv_all.size == 0:
            return {"ok": False, "error": error or "Local SHAP returned no contributions."}

        preds_all = model.predict(X_all)
        base_total = base * len(rows)
        pred_total = float(np.sum(preds_all))
        contrib_map: Dict[str, float] = {f: 0.0 for f in feature_cols}
        value_w: Dict[str, float] = {f: 0.0 for f in feature_cols}
        total_regs = float(rows["Registrations"].sum()) or 1.0

        for i, (_, row) in enumerate(rows.iterrows()):
            shap_row = sv_all[i]
            w = float(row["Registrations"]) / total_regs
            encoded = _encode_row(row, feature_cols)
            for j, f in enumerate(feature_cols):
                contrib_map[f] += float(shap_row[j])
                value_w[f] += float(encoded[f]) * w

        if predicted is None:
            predicted = pred_total

        contribs = []
        for f in feature_cols:
            av = float(value_w[f])
            if math.isnan(av) or math.isinf(av):
                av = None
            rv = refs.get(f)
            if rv is not None and (math.isnan(rv) or math.isinf(rv)):
                rv = None
            contribs.append(
                {
                    "feature": f,
                    "label": _feature_label(f),
                    "shap_value": float(contrib_map[f]),
                    "contribution": float(contrib_map[f]),
                    "pct": float(abs(contrib_map[f]) / (sum(abs(v) for v in contrib_map.values()) or 1) * 100),
                    "direction": "positive" if contrib_map[f] >= 0 else "negative",
                    "actual_value": av,
                    "actual_display": _format_num(av) if av is not None else "—",
                    "reference_value": rv,
                    "reference_display": _format_num(rv) if rv is not None else "—",
                }
            )
        contribs.sort(key=lambda x: -abs(x["shap_value"]))
        aggregate_note = (
            f"National view: SHAP contributions summed across {len(rows)} state×vehicle rows for {year}."
        )
        rep_row = rows.sort_values("Registrations", ascending=False).iloc[0]
    else:
        row = rows.iloc[0]
        X = _scale_row(row, feature_cols)
        if X is None:
            return {"ok": False, "error": "Could not scale feature row for SHAP."}
        contribs, base_total, method, error = _local_shap(X, feature_cols)
        if not contribs:
            return {"ok": False, "error": error or "Local SHAP returned no contributions."}
        if predicted is None:
            predicted = float(model.predict(X)[0])
        contribs = _enrich_contributions(contribs, row, refs)
        aggregate_note = None
        rep_row = row

    positive = [c for c in contribs if c["shap_value"] > 0][:5]
    negative = sorted([c for c in contribs if c["shap_value"] < 0], key=lambda x: x["shap_value"])[:5]
    prev_actual = float(rep_row["lag_1"]) if "lag_1" in rep_row.index and pd.notna(rep_row["lag_1"]) else None
    actual = float(rep_row["Registrations"]) if "Registrations" in rep_row.index else None
    if state == "ALL":
        nat = _national_trend()
        nat_row = nat[nat["Year"] == int(year)]
        if not nat_row.empty:
            actual = float(nat_row["Registrations"].iloc[0])
            prev_y = nat[nat["Year"] == int(year) - 1]
            if not prev_y.empty:
                prev_actual = float(prev_y["Registrations"].iloc[0])

    growth = _growth_rate(predicted, prev_actual)
    direction = _direction(growth)

    return {
        "ok": True,
        "method": method,
        "error": error,
        "model": "RandomForest",
        "xai_type": "local",
        "baseline": base_total,
        "prediction": predicted,
        "reconciled_prediction": base_total + sum(c["shap_value"] for c in contribs),
        "actual": actual,
        "previous": prev_actual,
        "growth_pct": growth,
        "direction": direction,
        "positive_contributors": positive,
        "negative_contributors": negative,
        "all_contributions": contribs[:12],
        "aggregate_note": aggregate_note,
        "disclaimer": DISCLAIMER,
    }


def test_set_predictions_series(
    state: str = "ALL",
    vehicle_type: str = "All",
) -> Dict[str, List[Any]]:
    """Actual vs RF test-set predictions for chart overlay."""
    preds = _load_predictions()
    feats = _load_features()
    if preds.empty or "pred_rf" not in preds.columns:
        return {"dates": [], "actual": [], "predicted": []}

    state = (state or "ALL").upper()
    pm = preds.copy()
    if state != "ALL":
        pm = pm[pm["State"] == state]
    if vehicle_type and vehicle_type not in ("All", "ALL", ""):
        pm = pm[pm["VehicleType"] == vehicle_type]

    if pm.empty:
        return {"dates": [], "actual": [], "predicted": []}

    pg = pm.groupby("Year", as_index=False).agg(
        Registrations=("Registrations", "sum"),
        pred_rf=("pred_rf", "sum"),
    ).sort_values("Year")

    return {
        "dates": pg["Year"].astype(str).tolist(),
        "actual": pg["Registrations"].round(2).tolist(),
        "predicted": pg["pred_rf"].round(2).tolist(),
    }


def build_local_explanation(
    state: str = "ALL",
    year: Optional[int] = None,
    vehicle_type: str = "All",
) -> Dict[str, Any]:
    """Public API for local XAI on a specific dataset row."""
    cfg = _load_config()
    feature_cols = cfg.get("feature_cols", [])
    feats = _load_features()
    preds = _load_predictions()
    if year is None:
        nat = _national_trend()
        year = int(nat["Year"].iloc[-1]) if not nat.empty else 2024
    expl = _compute_local_explanation(state, int(year), vehicle_type, feats, feature_cols, preds)
    if expl.get("ok"):
        expl["natural_language"] = _natural_language_detailed(expl)
        expl["waterfall"] = {
            "base": expl["baseline"],
            "contributions": [
                {"feature": c["feature"], "label": c["label"], "value": c["shap_value"],
                 "actual_display": c.get("actual_display"), "reference_display": c.get("reference_display")}
                for c in expl["all_contributions"]
            ],
            "final": expl["prediction"],
        }
    return expl


def _natural_language_detailed(expl: Dict[str, Any]) -> Dict[str, str]:
    """Dynamic NL explanation from actual SHAP contribution values."""
    pos = expl.get("positive_contributors") or []
    neg = expl.get("negative_contributors") or []
    direction = expl.get("direction", "Stable")
    growth = expl.get("growth_pct")
    pred = expl.get("prediction")
    base = expl.get("baseline")
    prev = expl.get("previous")

    def _contrib_line(c: Dict[str, Any]) -> str:
        sign = "+" if c["shap_value"] >= 0 else "−"
        return f"{c['label']} ({c.get('actual_display', '—')} vs ref {c.get('reference_display', '—')}) contributed {sign}{abs(c['shap_value']):,.0f}"

    main_reasons = [_contrib_line(c) for c in pos[:3]]
    reducing = [_contrib_line(c) for c in neg[:3]]

    if direction == "Increase":
        overall = (
            "The model predicted an increase because positive contributions from "
            + ", ".join(c["label"].lower() for c in pos[:3])
            + " were stronger than negative contributions"
            + (f" from {neg[0]['label'].lower()}." if neg else ".")
        )
    elif direction == "Decrease":
        overall = (
            "The model predicted a decrease because "
            + (f"{neg[0]['label'].lower()} contributed negatively to the model output." if neg else "negative feature contributions dominated.")
            + (f" Some upward pressure came from {pos[0]['label'].lower()}." if pos else "")
        )
    else:
        overall = "The model predicted a relatively stable outcome with balanced positive and negative feature contributions."

    summary = (
        f"Prediction: {_format_num(pred)} (baseline {_format_num(base)}). "
        f"Change vs previous period: {f'{growth:.1f}%' if growth is not None else '—'}."
    )

    return {
        "summary": summary,
        "main_reasons": main_reasons,
        "reducing_factors": reducing,
        "overall": overall,
        "causality_note": "Contributions describe model behavior, not proven real-world causation.",
    }


def _natural_language(
    direction: str,
    growth_pct: Optional[float],
    positive: List[Dict[str, Any]],
    negative: List[Dict[str, Any]],
    context: str = "prediction",
) -> str:
    pos_names = [p["label"] for p in positive[:3]]
    neg_names = [n["label"] for n in negative[:3]]
    prefix = "The model associates this forecast with" if context == "forecast" else "According to the model,"

    if direction == "Increase":
        if pos_names:
            main = pos_names[0]
            also = ", ".join(pos_names[1:2]) if len(pos_names) > 1 else ""
            text = (
                f"{prefix} higher EV registrations mainly because {main.lower()} "
                f"contributed positively to the prediction."
            )
            if also:
                text += f" {also} also influenced the model output positively."
            if neg_names:
                text += f" Partially offsetting factors included {neg_names[0].lower()}."
            return text
        return f"{prefix} an upward movement in EV registrations based on historical lag and trend features."

    if direction == "Decrease":
        if neg_names:
            text = (
                f"{prefix} lower EV registrations mainly because {neg_names[0].lower()} "
                f"reduced the predicted value."
            )
            if pos_names:
                text += f" Some positive contribution came from {pos_names[0].lower()}."
            return text
        return f"{prefix} a decline associated with weaker recent registration momentum in the model inputs."

    return f"{prefix} stable EV registrations with balanced positive and negative feature contributions."


def _load_model_metrics() -> Dict[str, Any]:
    """Real test-set metrics from model_comparison_registrations.csv."""
    metrics_path = ROOT / "outputs" / "metrics" / "model_comparison_registrations.csv"
    out: Dict[str, Any] = {
        "source": "outputs/metrics/model_comparison_registrations.csv",
        "best_by_rmse": None,
        "explanation_model": "RandomForest",
        "explanation_model_metrics": None,
        "all_models": [],
        "note": "Metrics from chronological held-out test data. Approx accuracy = max(0, 100 − MAPE).",
    }
    if not metrics_path.exists():
        out["note"] = "Run python run_project.py to generate real evaluation metrics."
        return out

    df = pd.read_csv(metrics_path)
    rows = []
    for _, r in df.iterrows():
        mape = float(r["MAPE"]) if pd.notna(r.get("MAPE")) else None
        row = {
            "model": str(r["Model"]),
            "MAE": float(r["MAE"]) if pd.notna(r.get("MAE")) else None,
            "RMSE": float(r["RMSE"]) if pd.notna(r.get("RMSE")) else None,
            "MAPE": mape,
            "R2": float(r["R2"]) if pd.notna(r.get("R2")) else None,
            "approx_accuracy": round(max(0.0, 100.0 - mape), 1) if mape is not None else None,
        }
        rows.append(row)
    out["all_models"] = rows

    if rows:
        best = min(rows, key=lambda x: x["RMSE"] if x["RMSE"] is not None else float("inf"))
        out["best_by_rmse"] = best["model"]
        out["best_model_metrics"] = best

    for row in rows:
        if row["model"] in ("RandomForest", "Random Forest"):
            out["explanation_model_metrics"] = row
            break

    return out


def _point_forecast_error(actual: Optional[float], predicted: Optional[float]) -> Optional[Dict[str, float]]:
    if actual is None or predicted is None:
        return None
    err = predicted - actual
    pct = (abs(err) / actual * 100.0) if actual != 0 else None
    return {"error": float(err), "abs_error": float(abs(err)), "abs_pct_error": pct}


def _model_xai_status() -> Dict[str, Any]:
    metrics = _load_model_metrics()
    compatible = ["RandomForest", "XGBoost"]
    limited = ["Naive", "ARIMA"]
    not_supported = ["CNN", "LSTM", "CNN-LSTM"]
    return {
        "explanation_model": "Random Forest (SHAP TreeExplainer)",
        "best_by_rmse": metrics.get("best_by_rmse") or "Naive",
        "xai_compatible": compatible,
        "xai_limited": limited,
        "xai_not_supported": not_supported,
        "note": "Local SHAP uses the tabular Random Forest on registration lag/trend features.",
        "metrics": metrics,
    }


def build_xai_dashboard(
    state: str = "ALL",
    year: Optional[int] = None,
    vehicle_type: str = "All",
    target: str = "registrations",
    refresh: bool = False,
) -> Dict[str, Any]:
    from src.state_names import display_name, regions_payload

    if refresh:
        for f in CACHE_DIR.glob("*.json"):
            try:
                f.unlink()
            except OSError:
                pass
        _DATA_CACHE.clear()

    state = (state or "ALL").upper()
    cfg = _load_config()
    feature_cols = cfg.get("feature_cols", [])
    feats = _load_features()
    preds = _load_predictions()
    nat = _national_trend()

    if year is None:
        year = int(nat["Year"].iloc[-1]) if not nat.empty else 2025

    if not refresh:
        cp = _cache_path(state, int(year), vehicle_type, target)
        if cp.exists():
            try:
                cached = json.loads(cp.read_text(encoding="utf-8"))
                if cached.get("ok"):
                    return cached
            except (json.JSONDecodeError, OSError):
                pass

    row = _select_row(state, year, vehicle_type, feats)

    local = _compute_local_explanation(state, int(year), vehicle_type, feats, feature_cols, preds)
    if not local.get("ok"):
        contribs = []
        base_value = 0.0
        shap_method = "none"
        positive: List[Dict[str, Any]] = []
        negative: List[Dict[str, Any]] = []
        predicted = None
        actual = None
        prev_actual = None
        growth_pred = None
        growth_actual = None
        direction = "Stable"
        main_reason = local.get("error", "Local explanation could not be generated.")
        nl = {"summary": main_reason, "main_reasons": [], "reducing_factors": [], "overall": main_reason}
    else:
        local["natural_language"] = _natural_language_detailed(local)
        contribs = local["all_contributions"]
        base_value = local["baseline"]
        shap_method = local["method"]
        positive = local["positive_contributors"]
        negative = local["negative_contributors"]
        predicted = local["prediction"]
        actual = local["actual"]
        prev_actual = local["previous"]
        growth_pred = local["growth_pct"]
        growth_actual = _growth_rate(actual, prev_actual) if actual is not None else None
        direction = local["direction"]
        nl = local["natural_language"]
        main_reason = nl.get("overall", "")

    global_rank = _load_global_ranking()
    metrics_block = _load_model_metrics()
    rf_metrics = metrics_block.get("explanation_model_metrics") or {}
    best_metrics = metrics_block.get("best_model_metrics") or {}
    approx_acc = best_metrics.get("approx_accuracy")
    if rf_metrics.get("approx_accuracy") is not None:
        explanation_acc = rf_metrics["approx_accuracy"]
    else:
        explanation_acc = approx_acc

    point_err = _point_forecast_error(actual, predicted)

    # Time series for charts
    if state == "ALL":
        ts_df = nat.copy()
    else:
        ts_df = feats[feats["State"] == state]
        if vehicle_type and vehicle_type not in ("All", "ALL", ""):
            ts_df = ts_df[ts_df["VehicleType"] == vehicle_type]
        ts_df = ts_df.groupby("Year", as_index=False)["Registrations"].sum()

    ts_dates = ts_df["Year"].astype(str).tolist() if not ts_df.empty else []
    ts_actual = ts_df["Registrations"].round(2).tolist() if not ts_df.empty else []

    ts_pred_aligned: List[Optional[float]] = []
    if not preds.empty and "pred_rf" in preds.columns:
        pm = preds.copy()
        if state != "ALL":
            pm = pm[pm["State"] == state]
        if vehicle_type and vehicle_type not in ("All", "ALL", ""):
            pm = pm[pm["VehicleType"] == vehicle_type]
        if not pm.empty:
            pg = pm.groupby("Year", as_index=False)["pred_rf"].sum().sort_values("Year")
            pred_map = dict(zip(pg["Year"].astype(str), pg["pred_rf"].round(2)))
            ts_pred_aligned = [pred_map.get(d) for d in ts_dates]

    # Forecast from saved file
    fc_dates, fc_vals, fc_lo, fc_hi = [], [], [], []
    fc_path = ROOT / "outputs" / "forecasts" / "national_registrations_future_cnn_lstm.csv"
    if state == "ALL" and fc_path.exists():
        fc = pd.read_csv(fc_path)
        fc_dates = fc["Year"].astype(str).tolist()
        fc_vals = fc["Forecast_Registrations"].round(2).tolist()
        if "Lower" in fc.columns:
            fc_lo = fc["Lower"].round(2).tolist()
            fc_hi = fc["Upper"].round(2).tolist()
        else:
            fc_lo = [max(0, v * 0.85) for v in fc_vals]
            fc_hi = [v * 1.15 for v in fc_vals]

    waterfall = {
        "base": base_value,
        "contributions": [
            {
                "feature": c["feature"],
                "label": c["label"],
                "value": c["shap_value"],
                "actual_display": c.get("actual_display"),
                "reference_display": c.get("reference_display"),
            }
            for c in contribs[:12]
        ],
        "final": predicted if predicted is not None else actual,
        "reconciled": base_value + sum(c["shap_value"] for c in contribs) if contribs else None,
    }

    dep_feature = positive[0]["feature"] if positive else (feature_cols[0] if feature_cols else "lag_1")
    dependence = {"feature": dep_feature, "label": _feature_label(dep_feature), "x": [], "y": []}
    if not feats.empty and dep_feature in feats.columns and feature_cols:
        sample = feats.dropna(subset=[dep_feature]).head(200)
        if len(sample):
            dependence["x"] = sample[dep_feature].round(4).tolist()
            # proxy impact: correlation with registrations
            dependence["y"] = sample["Registrations"].round(2).tolist()

    regions = regions_payload(
        sorted(feats["State"].unique().tolist()) if not feats.empty else [],
        include_all=True,
    )
    years = sorted(feats["Year"].unique().tolist()) if not feats.empty else []
    vtypes = sorted(feats["VehicleType"].unique().tolist()) if not feats.empty else ["All"]

    main_reason = nl.get("overall", main_reason)
    forecast_reason = _natural_language(
        _direction(_growth_rate(fc_vals[0], ts_actual[-1] if ts_actual else None) if fc_vals else None),
        _growth_rate(fc_vals[0], ts_actual[-1] if ts_actual else None) if fc_vals else None,
        positive,
        negative,
        "forecast",
    )

    if local.get("ok") and not local.get("natural_language"):
        local["natural_language"] = nl

    lime_status_path = OUT / "lime_status.json"
    lime_ok = lime_status_path.exists() and json.loads(lime_status_path.read_text()).get("status") == "ok"

    payload = {
        "ok": True,
        "refreshed_at": _utc_now(),
        "disclaimer": DISCLAIMER,
        "filters": {
            "state": state,
            "state_name": display_name(state),
            "year": int(year),
            "vehicle_type": vehicle_type,
            "target": target,
        },
        "filter_options": {"regions": regions, "years": years, "vehicle_types": ["All"] + [v for v in vtypes if v != "All"]},
        "available_features": [{"name": f, "label": _feature_label(f)} for f in feature_cols],
        "unavailable_factors": UNAVAILABLE_FACTORS,
        "kpis": {
            "current_sales": actual,
            "predicted_sales": predicted,
            "previous_sales": prev_actual,
            "growth_pct": growth_pred if growth_pred is not None else growth_actual,
            "forecast_accuracy_approx": approx_acc,
            "explanation_model_accuracy_approx": explanation_acc,
            "best_model": metrics_block.get("best_by_rmse"),
            "top_positive_factor": positive[0]["label"] if positive else None,
            "top_negative_factor": negative[0]["label"] if negative else None,
        },
        "accuracy": {
            "best_model": metrics_block.get("best_by_rmse"),
            "best_model_metrics": best_metrics,
            "explanation_model": "RandomForest",
            "explanation_model_metrics": rf_metrics,
            "all_models": metrics_block.get("all_models", []),
            "point_forecast_error": point_err,
            "label_approx": "Approx. forecast accuracy = max(0, 100 − MAPE) on held-out test years",
        },
        "prediction_card": {
            "predicted_ev_sales": predicted,
            "previous_period_sales": prev_actual,
            "expected_growth_pct": growth_pred,
            "direction": direction,
            "overall_trend": _trend_label(growth_pred),
            "main_positive_factor": positive[0]["label"] if positive else None,
            "main_negative_factor": negative[0]["label"] if negative else None,
            "confidence": {
                "lower": fc_lo[0] if fc_lo else None,
                "upper": fc_hi[0] if fc_hi else None,
                "note": "Interval derived from saved forecast or ±15% band when bounds not stored.",
            },
        },
        "local_explanation": local if local.get("ok") else {"ok": False, "error": local.get("error"), "xai_type": "local"},
        "explanation_panel": {
            "trend": _trend_label(growth_pred),
            "change_pct": growth_pred,
            "main_reason": main_reason,
            "positive_contributors": positive,
            "negative_contributors": negative,
            "model_interpretation": nl.get("overall", main_reason),
            "historical_explanation": nl.get("overall", main_reason),
            "forecast_explanation": forecast_reason,
            "natural_language": nl,
            "baseline": base_value,
            "prediction": predicted,
            "reconciled_prediction": waterfall.get("reconciled"),
            "aggregate_note": local.get("aggregate_note"),
        },
        "factor_impact": {
            "positive_drivers": positive,
            "negative_drivers": negative,
            "global_importance": global_rank,
        },
        "charts": {
            "timeseries": {
                "dates": ts_dates,
                "actual": ts_actual,
                "predicted": ts_pred_aligned,
                "forecast_dates": fc_dates,
                "forecast": fc_vals,
                "lower": fc_lo,
                "upper": fc_hi,
            },
            "waterfall": waterfall,
            "dependence": dependence,
            "importance_table": global_rank,
        },
        "artifacts": {
            "shap_summary": "/api/xai/artifacts/shap_summary.png",
            "shap_bar": "/api/xai/artifacts/shap_bar.png",
            "waterfall_png": "/api/xai/artifacts/prediction_explanation.png",
            "lime_html": "/api/xai/artifacts/lime_explanation.html" if lime_ok else None,
        },
        "models": _model_xai_status(),
        "shap_method": shap_method,
        "lime": {"available": lime_ok, "url": "/api/xai/artifacts/lime_explanation.html" if lime_ok else None},
    }
    try:
        _cache_path(state, int(year), vehicle_type, target).write_text(
            json.dumps(payload, default=str), encoding="utf-8"
        )
    except OSError:
        pass
    return payload
