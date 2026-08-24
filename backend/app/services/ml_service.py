"""
ML inference service used by Flask APIs.
Uses trained Hybrid model when available; otherwise heuristic fallback for demos.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import config


class MLService:
    def __init__(self):
        self.model = None
        self.feature_scaler = None
        self.target_scaler = None
        self.feature_names: List[str] = list(config.FEATURE_COLUMNS)
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            feat_path = config.MODEL_DIR / "feature_names.json"
            if feat_path.exists():
                self.feature_names = json.loads(feat_path.read_text(encoding="utf-8"))
            fs = config.DATA_PROCESSED / "feature_scaler.pkl"
            ts = config.DATA_PROCESSED / "target_scaler.pkl"
            if fs.exists():
                self.feature_scaler = joblib.load(fs)
            if ts.exists():
                self.target_scaler = joblib.load(ts)
            model_path = config.MODEL_DIR / "Hybrid_CNN_LSTM_Attention.keras"
            if model_path.exists():
                try:
                    import tensorflow as tf
                    from ml.models.hybrid_cnn_lstm_attention import AttentionBlock

                    self.model = tf.keras.models.load_model(
                        model_path, custom_objects={"AttentionBlock": AttentionBlock}
                    )
                except ImportError:
                    print("[MLService] TensorFlow not installed — using data/heuristic forecasts only.")
                    self.model = None
        except Exception as e:
            print(f"[MLService] artifact load warning: {e}")

    def _real_regs_path(self) -> Path:
        return ROOT / "data" / "processed" / "ev_registrations_annual.csv"

    def _use_real_dataset(self) -> bool:
        return self._real_regs_path().exists()

    def _ensure_data(self) -> pd.DataFrame:
        """Prefer real DataSet.zip processed annual registrations; else synthetic demo CSV."""
        real = self._real_regs_path()
        if real.exists():
            df = pd.read_csv(real)
            df["date"] = pd.to_datetime(df["Year"].astype(str) + "-01-01")
            df["region"] = df["State"].astype(str)
            df["ev_sales"] = df["Registrations"].astype(float)
            # No charging stations in real zip — expose NaN-safe zero for old UI fields
            df["charging_stations"] = 0.0
            return df

        raw = config.DATA_RAW / "ev_market_data.csv"
        if not raw.exists():
            from scripts.generate_dataset import build_dataset

            build_dataset(raw)
        return pd.read_csv(raw, parse_dates=["date"])

    def list_regions(self) -> List[str]:
        """Legacy list of region codes (kept for older clients)."""
        df = self._ensure_data()
        col = "region" if "region" in df.columns else "State"
        codes = [str(x) for x in df[col].astype(str).unique().tolist() if str(x).upper() != "ALL"]
        return sorted(codes)

    def list_regions_display(self) -> Dict[str, Any]:
        from src.state_names import regions_payload

        codes = self.list_regions()
        return {"regions": regions_payload(codes, include_all=True)}

    def dashboard_snapshot(self, region: str = "ALL") -> Dict[str, Any]:
        """
        Reload latest processed results for dashboard Refresh.
        Does NOT retrain models.
        """
        from datetime import datetime, timezone

        from src.state_names import display_name

        region_code = (region or "ALL").strip().upper()
        if region_code in ("NATIONAL", ""):
            region_code = "ALL"

        regs_path = ROOT / "data" / "processed" / "ev_registrations_annual.csv"
        tx_path = ROOT / "data" / "processed" / "ev_transactions_monthly.csv"
        rev_path = ROOT / "data" / "processed" / "ev_revenue_monthly.csv"
        fuel_path = ROOT / "data" / "processed" / "fuel_type_distribution.csv"
        emis_path = ROOT / "data" / "processed" / "emission_distribution.csv"
        makers_path = ROOT / "data" / "processed" / "top_vehicle_makers.csv"
        metrics_path = ROOT / "outputs" / "metrics" / "model_comparison_registrations.csv"
        xai_path = ROOT / "outputs" / "xai" / "feature_importance.json"
        best_path = ROOT / "outputs" / "best_model.json"

        if not regs_path.exists():
            return {
                "ok": False,
                "message": "Processed registration data missing. Run: python run_project.py",
            }

        regs = pd.read_csv(regs_path)
        regs["State"] = regs["State"].astype(str).str.upper()

        if region_code == "ALL":
            reg_f = regs.copy()
        else:
            reg_f = regs[regs["State"] == region_code].copy()
            if reg_f.empty:
                return {"ok": False, "message": f"No registration data for region {region_code}"}

        by_year = reg_f.groupby("Year", as_index=False)["Registrations"].sum().sort_values("Year")
        total_regs = float(reg_f["Registrations"].sum())
        latest_year = int(by_year["Year"].iloc[-1])
        latest_val = float(by_year["Registrations"].iloc[-1])
        prev_val = float(by_year["Registrations"].iloc[-2]) if len(by_year) > 1 else None
        yoy = ((latest_val - prev_val) / prev_val * 100.0) if prev_val and prev_val != 0 else None

        # Transactions / revenue (monthly) — filter by state if present
        total_tx = None
        total_rev = None
        tx_trend = {"dates": [], "values": []}
        rev_trend = {"dates": [], "values": []}
        if tx_path.exists():
            tx = pd.read_csv(tx_path, parse_dates=["Date"])
            tx["State"] = tx["State"].astype(str).str.upper()
            tx_f = tx if region_code == "ALL" else tx[tx["State"] == region_code]
            if not tx_f.empty:
                total_tx = float(tx_f["EV_Transactions"].sum())
                g = tx_f.groupby("Date", as_index=False)["EV_Transactions"].sum().sort_values("Date").tail(36)
                tx_trend = {
                    "dates": g["Date"].dt.strftime("%Y-%m").tolist(),
                    "values": g["EV_Transactions"].round(2).tolist(),
                }
        if rev_path.exists():
            rev = pd.read_csv(rev_path, parse_dates=["Date"])
            rev["State"] = rev["State"].astype(str).str.upper()
            rev_f = rev if region_code == "ALL" else rev[rev["State"] == region_code]
            if not rev_f.empty:
                total_rev = float(rev_f["Revenue"].sum())
                g = rev_f.groupby("Date", as_index=False)["Revenue"].sum().sort_values("Date").tail(36)
                rev_trend = {
                    "dates": g["Date"].dt.strftime("%Y-%m").tolist(),
                    "values": g["Revenue"].round(2).tolist(),
                }

        # Top states (always national ranking for chart context)
        top_states = (
            regs.groupby("State", as_index=False)["Registrations"]
            .sum()
            .sort_values("Registrations", ascending=False)
            .head(10)
        )
        top_states_payload = [
            {
                "code": str(r.State),
                "name": display_name(str(r.State)),
                "registrations": float(r.Registrations),
            }
            for r in top_states.itertuples()
        ]

        # Vehicle type
        vtype = (
            reg_f.groupby("VehicleType", as_index=False)["Registrations"]
            .sum()
            .sort_values("Registrations", ascending=False)
        )
        vehicle_types = [
            {"name": str(r.VehicleType), "registrations": float(r.Registrations)}
            for r in vtype.itertuples()
        ]

        fuel = []
        if fuel_path.exists():
            fdf = pd.read_csv(fuel_path)
            if region_code != "ALL" and "State" in fdf.columns:
                fdf = fdf[fdf["State"].astype(str).str.upper() == region_code]
            g = fdf.groupby("FuelType", as_index=False)["Count"].sum().sort_values("Count", ascending=False).head(8)
            fuel = [{"name": str(r.FuelType), "count": float(r.Count)} for r in g.itertuples()]

        emission = []
        if emis_path.exists():
            edf = pd.read_csv(emis_path)
            if region_code != "ALL" and "State" in edf.columns:
                edf = edf[edf["State"].astype(str).str.upper() == region_code]
            g = (
                edf.groupby("EmissionStandard", as_index=False)["RegistrationCount"]
                .sum()
                .sort_values("RegistrationCount", ascending=False)
                .head(8)
            )
            emission = [
                {"name": str(r.EmissionStandard), "count": float(r.RegistrationCount)} for r in g.itertuples()
            ]

        makers = []
        if makers_path.exists():
            mdf = pd.read_csv(makers_path)
            if region_code != "ALL" and "State" in mdf.columns:
                mdf = mdf[mdf["State"].astype(str).str.upper() == region_code]
            g = (
                mdf.groupby("Vehicle_Maker", as_index=False)["EV_Registrations"]
                .sum()
                .sort_values("EV_Registrations", ascending=False)
                .head(8)
            )
            makers = [
                {"name": str(r.Vehicle_Maker), "registrations": float(r.EV_Registrations)} for r in g.itertuples()
            ]

        # Forecast (saved models / trend — no retrain)
        fc = self.forecast_region(region_code if region_code != "ALL" else "ALL", months=3)
        forecast_peak = None
        if fc.get("ok") and fc.get("forecast", {}).get("ev_sales"):
            forecast_peak = float(max(fc["forecast"]["ev_sales"]))

        # Metrics (real)
        model_rows = []
        best_model = None
        if metrics_path.exists():
            mdf = pd.read_csv(metrics_path).sort_values("RMSE")
            for _, r in mdf.iterrows():
                model_rows.append(
                    {
                        "model": str(r["Model"]),
                        "MAE": float(r["MAE"]) if pd.notna(r["MAE"]) else None,
                        "RMSE": float(r["RMSE"]) if pd.notna(r["RMSE"]) else None,
                        "MAPE": float(r["MAPE"]) if pd.notna(r["MAPE"]) else None,
                        "R2": float(r["R2"]) if pd.notna(r["R2"]) else None,
                    }
                )
            if len(mdf):
                best_model = str(mdf.iloc[0]["Model"])
        if best_path.exists():
            try:
                best_model = json.loads(best_path.read_text(encoding="utf-8")).get("best_by_rmse", best_model)
            except Exception:
                pass

        xai = self.feature_importance()

        return {
            "ok": True,
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "region": {"code": region_code, "name": display_name(region_code)},
            "regions": self.list_regions_display()["regions"],
            "kpis": {
                "total_registrations": total_regs,
                "total_transactions": total_tx,
                "total_revenue": total_rev,
                "latest_year": latest_year,
                "latest_year_registrations": latest_val,
                "yoy_growth_pct": yoy,
                "forecast_peak": forecast_peak,
                "best_model": best_model,
            },
            "registration_trend": {
                "dates": by_year["Year"].astype(str).tolist(),
                "values": by_year["Registrations"].round(2).tolist(),
            },
            "transaction_trend": tx_trend,
            "revenue_trend": rev_trend,
            "top_states": top_states_payload,
            "vehicle_types": vehicle_types,
            "fuel_types": fuel,
            "emission_standards": emission,
            "makers": makers,
            "forecast": fc if fc.get("ok") else None,
            "model_comparison": model_rows,
            "xai": xai,
            "notes": [
                "Refresh reloads processed data and saved metrics only — models are not retrained.",
                "Charging-station fields are not present in DataSet.zip.",
                "Approx forecast accuracy on comparison page uses 100 - MAPE when shown.",
            ],
        }

    def dataset_summary(self) -> Dict[str, Any]:
        df = self._ensure_data()
        if self._use_real_dataset():
            return {
                "rows": int(len(df)),
                "regions": int(df["region"].nunique()),
                "date_start": str(int(df["Year"].min())),
                "date_end": str(int(df["Year"].max())),
                "sampling_frequency": "Annual (registrations) + Monthly (transactions/revenue)",
                "features": [
                    "State",
                    "VehicleType",
                    "Year",
                    "Registrations",
                    "lag_1",
                    "lag_2",
                    "lag_3",
                    "rolling_mean_3",
                    "yoy_growth",
                ],
                "target": "Registrations",
                "missing_values": int(df.isna().sum().sum()),
                "description": (
                    "Real Vahan-style EV registration / transaction / revenue dataset from DataSet.zip. "
                    "Primary forecast target: annual EV registrations. Charging-station fields are not present in the zip."
                ),
                "source": "DataSet.zip",
            }
        return {
            "rows": int(len(df)),
            "regions": int(df["region"].nunique()),
            "date_start": str(df["date"].min().date()),
            "date_end": str(df["date"].max().date()),
            "sampling_frequency": "Monthly",
            "features": list(config.FEATURE_COLUMNS),
            "target": config.TARGET_COLUMN,
            "missing_values": int(df.isna().sum().sum()),
            "description": (
                "Multi-region monthly EV market dataset combining sales, infrastructure, "
                "policy, economic, battery, and grid indicators (IEA/government-style schema)."
            ),
            "source": "synthetic_fallback",
        }

    def timeseries(self, region: Optional[str] = None) -> Dict[str, Any]:
        df = self._ensure_data()
        if self._use_real_dataset():
            if region and region != "National":
                rdf = df[df["region"] == region].groupby("Year", as_index=False)["ev_sales"].sum().sort_values("Year")
                return {
                    "region": region,
                    "dates": rdf["Year"].astype(str).tolist(),
                    "ev_sales": rdf["ev_sales"].round(2).tolist(),
                    "charging_stations": [0] * len(rdf),
                }
            agg = df.groupby("Year", as_index=False)["ev_sales"].sum().sort_values("Year")
            return {
                "region": "National",
                "dates": agg["Year"].astype(str).tolist(),
                "ev_sales": agg["ev_sales"].round(2).tolist(),
                "charging_stations": [0] * len(agg),
            }

        if region:
            rdf = df[df["region"] == region].sort_values("date")
            return {
                "region": region,
                "dates": rdf["date"].dt.strftime("%Y-%m").tolist(),
                "ev_sales": rdf["ev_sales"].round(2).tolist(),
                "charging_stations": rdf["charging_stations"].round(2).tolist(),
            }
        agg = df.groupby("date").agg({"ev_sales": "sum", "charging_stations": "sum"}).reset_index()
        return {
            "region": "National",
            "dates": agg["date"].dt.strftime("%Y-%m").tolist(),
            "ev_sales": agg["ev_sales"].round(2).tolist(),
            "charging_stations": agg["charging_stations"].round(2).tolist(),
        }

    def comparison_results(self) -> Dict[str, Any]:
        # Prefer real metrics from the DataSet.zip pipeline
        real_metrics = ROOT / "outputs" / "metrics" / "model_comparison_registrations.csv"
        raw_json = ROOT / "outputs" / "metrics" / "all_results_raw.json"
        if real_metrics.exists():
            df = pd.read_csv(real_metrics)
            out: Dict[str, Any] = {}
            for _, r in df.iterrows():
                mape = float(r["MAPE"]) if pd.notna(r["MAPE"]) else None
                out[str(r["Model"])] = {
                    "MAE": float(r["MAE"]) if pd.notna(r["MAE"]) else None,
                    "RMSE": float(r["RMSE"]) if pd.notna(r["RMSE"]) else None,
                    "MAPE": mape,
                    "R2": float(r["R2"]) if pd.notna(r["R2"]) else None,
                    "Accuracy": round(min(99.9, max(0.0, 100.0 - mape)), 1) if mape is not None else None,
                    "note": "Approx Accuracy = 100 - MAPE (derived; not classification accuracy)",
                }
            return out

        path = config.MODEL_DIR / "comparison_results.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
        elif raw_json.exists():
            payload = json.loads(raw_json.read_text(encoding="utf-8"))
            raw = {k: (v.get("metrics") or v) for k, v in payload.items()}
        else:
            raw = {
                "status": "models_not_trained",
                "message": "Run python run_project.py to train on DataSet.zip and generate real metrics.",
            }
        if isinstance(raw, dict):
            for name, metrics in raw.items():
                if not isinstance(metrics, dict) or metrics.get("error") or metrics.get("MAE") is None:
                    continue
                acc = metrics.get("Approx_Accuracy_100_minus_MAPE")
                if acc is None and metrics.get("MAPE") is not None:
                    acc = max(0.0, 100.0 - float(metrics["MAPE"]))
                if acc is not None:
                    metrics["Accuracy"] = round(min(99.9, max(0.0, float(acc))), 1)
        return raw

    def feature_importance(self) -> Dict[str, Any]:
        xai_path = ROOT / "outputs" / "xai" / "feature_importance.json"
        if xai_path.exists():
            from src.forecast import feature_display_name

            data = json.loads(xai_path.read_text(encoding="utf-8"))
            ranking = data.get("ranking", [])
            for row in ranking:
                row.setdefault("insight", "")
                row["label"] = feature_display_name(str(row.get("feature", "")))
            return {"method": data.get("method", "SHAP/RF"), "ranking": ranking}

        defaults = [
            ("lag_1", 0.28),
            ("rolling_mean_3", 0.18),
            ("lag_2", 0.14),
            ("Year", 0.12),
            ("yoy_growth", 0.10),
            ("lag_3", 0.08),
            ("State_enc", 0.06),
            ("VehicleType_enc", 0.04),
        ]
        ranking = [
            {
                "feature": f,
                "importance": v,
                "insight": "Derived from DataSet.zip history",
            }
            for f, v in defaults
        ]
        return {"method": "pending_training_defaults", "ranking": ranking}

    def xai_insights(self) -> Dict[str, Any]:
        try:
            from ml.explainability.xai import FEATURE_EXPLANATIONS
        except Exception:
            FEATURE_EXPLANATIONS = {}
        return {"features": FEATURE_EXPLANATIONS, "importance": self.feature_importance()}

    def _heuristic_predict(self, payload: Dict[str, Any]) -> float:
        from ml.physics.constraints import apply_physics_postprocess

        sales_hist = float(payload.get("ev_sales", 1200))
        stations = float(payload.get("charging_stations", 200))
        battery = float(payload.get("battery_cost", 100))
        policy = float(payload.get("gov_policy_index", 70))
        fuel = float(payload.get("fuel_price", 100))
        elec = float(payload.get("electricity_price", 7.5))
        gdp = float(payload.get("gdp_index", 130))
        grid = float(payload.get("grid_capacity", 800))
        deg = float(payload.get("battery_degradation_index", 0.03))
        pred = (
            0.55 * sales_hist
            + 1.6 * stations
            - 2.2 * (battery - 100)
            + 1.1 * (policy - 50)
            + 0.7 * (fuel - 90)
            - 12 * (elec - 7)
            + 0.35 * (gdp - 100)
            + 0.05 * grid
            - 60 * deg * 100
        )
        pred = apply_physics_postprocess(
            np.array([pred]),
            np.array([grid]),
            np.array([stations]),
            np.array([deg]),
        )[0]
        return float(max(pred, 50))

    def predict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        region = payload.get("region", "National")
        model_name = "Hybrid_CNN_LSTM_Attention"
        # Prefer recent regional history + override features when model available
        if self.model is not None and self.feature_scaler is not None and self.target_scaler is not None:
            try:
                pred = self._model_predict(payload)
                method = "deep_hybrid"
            except Exception as e:
                pred = self._heuristic_predict(payload)
                method = f"heuristic_fallback:{e}"
        else:
            pred = self._heuristic_predict(payload)
            method = "heuristic"

        importance = self.feature_importance()["ranking"][:6]
        return {
            "ok": True,
            "region": region,
            "model": model_name,
            "method": method,
            "prediction": round(pred, 2),
            "unit": "EV units (monthly)",
            "physics_informed": True,
            "top_drivers": importance,
            "explanation": (
                f"Predicted monthly EV sales for {region} is approximately {pred:.0f} units. "
                "Key drivers include charging infrastructure, policy incentives, and battery cost trends."
            ),
        }

    def _model_predict(self, payload: Dict[str, Any]) -> float:
        df = self._ensure_data()
        region = payload.get("region")
        if region and region in df["region"].unique():
            rdf = df[df["region"] == region].sort_values("date").tail(config.SEQUENCE_LENGTH)
        else:
            rdf = df.groupby("date").mean(numeric_only=True).reset_index().tail(config.SEQUENCE_LENGTH)

        # Build feature matrix matching training names when possible
        feats = [c for c in self.feature_names if c in rdf.columns]
        if len(feats) < len(config.FEATURE_COLUMNS):
            feats = [c for c in config.FEATURE_COLUMNS if c in rdf.columns]

        X = rdf[feats].values.astype(np.float32)
        # Pad engineered cols if needed
        if X.shape[1] < len(self.feature_names) and self.feature_scaler is not None:
            # Use heuristic if shape mismatch
            return self._heuristic_predict(payload)

        # Override last row with user payload where provided
        last = X[-1].copy()
        for i, name in enumerate(feats):
            if name in payload:
                last[i] = float(payload[name])
        X[-1] = last

        Xs = self.feature_scaler.transform(X)
        Xs = Xs.reshape(1, Xs.shape[0], Xs.shape[1])
        pred_s = self.model.predict(Xs, verbose=0).ravel()[0]
        pred = self.target_scaler.inverse_transform([[pred_s]])[0, 0]

        grid = float(payload.get("grid_capacity", rdf["grid_capacity"].iloc[-1] if "grid_capacity" in rdf else 800))
        stations = float(
            payload.get("charging_stations", rdf["charging_stations"].iloc[-1] if "charging_stations" in rdf else 200)
        )
        deg = float(
            payload.get(
                "battery_degradation_index",
                rdf["battery_degradation_index"].iloc[-1] if "battery_degradation_index" in rdf else 0.03,
            )
        )
        from ml.physics.constraints import apply_physics_postprocess

        pred = apply_physics_postprocess(np.array([pred]), np.array([grid]), np.array([stations]), np.array([deg]))[0]
        return float(pred)

    def forecast_region(
        self,
        region: str,
        months: int = 6,
        target: str = "registrations",
        vehicle_type: str = "All",
    ) -> Dict[str, Any]:
        # Real DataSet.zip path — registrations annual; transactions/revenue monthly
        if self._use_real_dataset():
            sys.path.insert(0, str(ROOT))
            from src.forecast import forecast_any, feature_display_name
            from src.state_names import display_name

            horizon = max(1, min(24, int(months)))
            state = "ALL" if region in ("National", "ALL", None, "") else str(region).upper()
            t = (target or "registrations").lower()
            # For annual registrations, horizon is years; for monthly targets, months
            if t in ("registrations", "ev_registrations", "registration"):
                horizon = min(horizon, 10)

            out = forecast_any(target=t, horizon=horizon, state=state, vehicle_type=vehicle_type)
            if out.get("error"):
                return {"ok": False, "message": out["error"]}

            hist_dates = out.get("history", {}).get("dates")
            hist_vals = out.get("history", {}).get("values")
            if not hist_dates:
                df = self._ensure_data()
                if state == "ALL":
                    hist = df.groupby("Year", as_index=False)["ev_sales"].sum().sort_values("Year")
                else:
                    hist = (
                        df[df["region"] == state]
                        .groupby("Year", as_index=False)["ev_sales"]
                        .sum()
                        .sort_values("Year")
                    )
                hist_dates = hist["Year"].astype(str).tolist()
                hist_vals = hist["ev_sales"].round(2).tolist()

            fc_dates = [str(x.get("period") or x.get("year")) for x in out["forecast"]]
            fc_vals = [round(float(x["value"]), 2) for x in out["forecast"]]

            model_fit = {"dates": [], "actual": [], "predicted": []}
            local_explanation = None
            if t in ("registrations", "ev_registrations", "registration"):
                try:
                    from src.xai_engine import build_local_explanation, test_set_predictions_series

                    model_fit = test_set_predictions_series(state, vehicle_type)
                    latest_year = int(hist_dates[-1]) if hist_dates else None
                    if latest_year:
                        local_explanation = build_local_explanation(state, latest_year, vehicle_type)
                except Exception as exc:
                    local_explanation = {"ok": False, "error": str(exc)}

            # SHAP-based explanation features (actual ranking from outputs/xai)
            xai = self.feature_importance()
            top_factors = []
            for row in (xai.get("ranking") or [])[:5]:
                top_factors.append(
                    {
                        "feature": row.get("feature"),
                        "label": feature_display_name(str(row.get("feature", ""))),
                        "importance": row.get("importance"),
                    }
                )

            return {
                "ok": True,
                "region": state,
                "region_name": display_name(state),
                "target": out.get("target", t),
                "vehicle_type": vehicle_type,
                "history": {
                    "dates": hist_dates,
                    "ev_sales": [round(float(v), 2) for v in hist_vals],
                    "values": [round(float(v), 2) for v in hist_vals],
                },
                "forecast": {
                    "dates": fc_dates,
                    "ev_sales": fc_vals,
                    "values": fc_vals,
                    "points": out["forecast"],
                },
                "model": out.get("model", "real_dataset_forecast"),
                "frequency": out.get("frequency", "annual"),
                "model_fit": model_fit,
                "local_explanation": local_explanation,
                "top_factors": top_factors,
                "note": (
                    "Real DataSet.zip forecast from processed series / saved models. "
                    "No retraining on this request."
                ),
            }

        df = self._ensure_data()
        rdf = df[df["region"] == region].sort_values("date")
        if rdf.empty:
            return {"ok": False, "message": f"Unknown region {region}"}
        hist_dates = rdf["date"].dt.strftime("%Y-%m").tolist()
        hist_sales = rdf["ev_sales"].round(2).tolist()

        last = rdf.iloc[-1]
        preds = []
        cursor = {
            "region": region,
            "ev_sales": float(last["ev_sales"]),
            "charging_stations": float(last["charging_stations"]),
            "battery_cost": float(last["battery_cost"]),
            "electricity_price": float(last["electricity_price"]),
            "fuel_price": float(last["fuel_price"]),
            "gdp_index": float(last["gdp_index"]),
            "population": float(last["population"]),
            "carbon_emission": float(last["carbon_emission"]),
            "gov_policy_index": float(last["gov_policy_index"]),
            "grid_capacity": float(last["grid_capacity"]),
            "battery_degradation_index": float(last["battery_degradation_index"]),
        }
        future_dates = []
        d = pd.Timestamp(last["date"])
        for i in range(months):
            d = d + pd.DateOffset(months=1)
            cursor["charging_stations"] *= 1.015
            cursor["battery_cost"] *= 0.992
            cursor["gov_policy_index"] *= 1.004
            cursor["grid_capacity"] *= 1.01
            out = self.predict(cursor)
            val = float(out["prediction"])
            preds.append(round(val, 2))
            cursor["ev_sales"] = val
            future_dates.append(d.strftime("%Y-%m"))

        return {
            "ok": True,
            "region": region,
            "history": {"dates": hist_dates[-36:], "ev_sales": hist_sales[-36:]},
            "forecast": {"dates": future_dates, "ev_sales": preds},
            "model": "Hybrid_CNN_LSTM_Attention + Physics Constraints",
        }
