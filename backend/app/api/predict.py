"""Prediction, metrics, dataset, and XAI API endpoints."""
from __future__ import annotations

import json
import time
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from backend.app import db
from backend.app.models.prediction import PredictionLog
from backend.app.services.ml_service import MLService

predict_bp = Blueprint("predict", __name__)
_ml_service = None


def get_ml_service():
    """Lazy-load MLService so Flask can start without waiting on TensorFlow."""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
    return _ml_service


@predict_bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "EV Market Hybrid Forecasting API", "version": "1.0.0"})


@predict_bp.get("/dataset/summary")
def dataset_summary():
    return jsonify(get_ml_service().dataset_summary())


@predict_bp.get("/dataset/timeseries")
def dataset_timeseries():
    region = request.args.get("region")
    return jsonify(get_ml_service().timeseries(region=region))


@predict_bp.get("/models/comparison")
def model_comparison():
    return jsonify(get_ml_service().comparison_results())


@predict_bp.get("/models/feature-importance")
def feature_importance():
    return jsonify(get_ml_service().feature_importance())


@predict_bp.post("/predict")
@jwt_required(optional=True)
def predict():
    payload = request.get_json(silent=True) or {}
    t0 = time.time()
    result = get_ml_service().predict(payload)
    result["latency_ms"] = round((time.time() - t0) * 1000, 2)

    try:
        uid = get_jwt_identity()
        log = PredictionLog(
            user_id=int(uid) if uid else None,
            region=payload.get("region", "National"),
            model_name=result.get("model", "Hybrid_CNN_LSTM_Attention"),
            input_payload=json.dumps(payload),
            prediction=float(result.get("prediction", 0)),
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify(result)


@predict_bp.get("/regions")
def regions():
    payload = get_ml_service().list_regions_display()
    payload["region_codes"] = [r["code"] for r in payload["regions"]]
    return jsonify(payload)


@predict_bp.get("/dashboard/snapshot")
def dashboard_snapshot():
    region = request.args.get("region", "ALL") or "ALL"
    try:
        data = get_ml_service().dashboard_snapshot(region=region)
        status = 200 if data.get("ok") else 400
        return jsonify(data), status
    except Exception as exc:
        return jsonify({"ok": False, "message": f"Dashboard snapshot failed: {exc}"}), 500


@predict_bp.get("/refresh")
def dashboard_refresh_alias():
    """Same as /dashboard/snapshot — reloads processed data only (no retrain)."""
    return dashboard_snapshot()


@predict_bp.get("/forecast")
def forecast():
    region = request.args.get("region", "ALL")
    months = int(request.args.get("months", 3))
    target = request.args.get("target", "registrations")
    vehicle_type = request.args.get("vehicle_type", "All")
    result = get_ml_service().forecast_region(
        region=region, months=months, target=target, vehicle_type=vehicle_type
    )
    if result.get("ok"):
        from src.state_names import display_name

        code = result.get("region", region)
        result["region_code"] = code
        result.setdefault("region_name", display_name(code))
    return jsonify(result)


@predict_bp.get("/xai/insights")
def xai_insights():
    return jsonify(get_ml_service().xai_insights())
