"""Comprehensive test suite testing all project endpoints and core functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_app, db
from src.forecast import forecast_any, forecast_monthly, forecast_registrations
from src.state_names import display_name, regions_payload
from src.xai_engine import build_xai_dashboard


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        # Seed test admin
        from backend.app import _ensure_admin
        _ensure_admin()
    yield app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def admin_token(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@evforecast.edu", "password": "Admin@123"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    return data["token"]


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True


def test_page_routes(client):
    pages = [
        "/",
        "/home",
        "/login",
        "/register",
        "/dashboard",
        "/about",
        "/dataset",
        "/prediction",
        "/comparison",
        "/xai",
        "/contact",
        "/admin",
        "/dashboard.html",
        "/login.html",
        "/register.html",
        "/home.html",
        "/index.html",
        "/about.html",
        "/dataset.html",
        "/prediction.html",
        "/comparison.html",
        "/xai.html",
        "/contact.html",
        "/admin.html",
        "/live-index.html",
    ]
    for p in pages:
        res = client.get(p, follow_redirects=True)
        assert res.status_code == 200, f"Page {p} returned status {res.status_code}"


def test_regions_endpoint(client):
    res = client.get("/api/regions")
    assert res.status_code == 200
    data = res.get_json()
    assert "regions" in data
    assert "region_codes" in data
    assert len(data["regions"]) > 0


def test_dataset_summary(client):
    res = client.get("/api/dataset/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)


def test_dataset_timeseries(client):
    res = client.get("/api/dataset/timeseries")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)


def test_models_comparison(client):
    res = client.get("/api/models/comparison")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)


def test_models_feature_importance(client):
    res = client.get("/api/models/feature-importance")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)


def test_predict_endpoint(client):
    payload = {
        "region": "ALL",
        "vehicle_type": "Transport",
        "model": "Hybrid_CNN_LSTM_Attention",
        "horizon": 3,
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert "prediction" in data or "forecast" in data or "ok" in data


def test_dashboard_snapshot(client):
    res = client.get("/api/dashboard/snapshot?region=ALL")
    assert res.status_code in (200, 400)
    data = res.get_json()
    assert isinstance(data, dict)


def test_forecast_endpoint(client):
    res = client.get("/api/forecast?region=ALL&months=3&target=registrations")
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("ok") is True or "forecast" in data or "error" not in data


def test_xai_insights_endpoint(client):
    res = client.get("/api/xai/insights")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)


def test_xai_dashboard_endpoint(client):
    res = client.get("/api/xai/dashboard?state=ALL")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)


def test_auth_flow(client):
    import time
    email = f"testuser_{int(time.time())}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "password123", "organization": "Test Org"},
    )
    assert res.status_code == 201
    reg_data = res.get_json()
    assert reg_data["ok"] is True
    token = reg_data["token"]

    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.get_json()["user"]["email"] == email

    res_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert res_login.status_code == 200
    assert res_login.get_json()["ok"] is True


def test_contact_submission(client):
    res = client.post(
        "/api/contact",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "subject": "Inquiry about EV forecast",
            "message": "Hello, I would like to learn more about the methodology.",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["ok"] is True


def test_admin_endpoints(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    for endpoint in ["/api/admin/stats", "/api/admin/users", "/api/admin/predictions", "/api/admin/contacts"]:
        res = client.get(endpoint, headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("ok") is True


def test_forecast_helpers():
    f_reg = forecast_registrations(horizon=2, state="ALL")
    assert "forecast" in f_reg
    assert len(f_reg["forecast"]) == 2

    f_tx = forecast_monthly("transactions", horizon=3, state="ALL")
    assert "forecast" in f_tx
    assert len(f_tx["forecast"]) == 3

    f_rev = forecast_monthly("revenue", horizon=3, state="ALL")
    assert "forecast" in f_rev
    assert len(f_rev["forecast"]) == 3

    f_any = forecast_any("registrations", horizon=2, state="ALL")
    assert "forecast" in f_any


def test_state_names_helpers():
    assert display_name("DL") == "Delhi"
    assert display_name("MH") == "Maharashtra"
    assert display_name("ALL") == "All India"
    payload = regions_payload(["DL", "MH"], include_all=True)
    assert len(payload) == 3


def test_auth_validation_errors(client):
    # Missing fields
    res = client.post("/api/auth/register", json={})
    assert res.status_code == 400
    assert res.get_json()["ok"] is False

    # Invalid email
    res = client.post(
        "/api/auth/register",
        json={"name": "User", "email": "not-an-email", "password": "password123"},
    )
    assert res.status_code == 400

    # Short password
    res = client.post(
        "/api/auth/register",
        json={"name": "User", "email": "valid@email.com", "password": "123"},
    )
    assert res.status_code == 400

    # Duplicate registration
    client.post(
        "/api/auth/register",
        json={"name": "User", "email": "dup@example.com", "password": "password123"},
    )
    res_dup = client.post(
        "/api/auth/register",
        json={"name": "User", "email": "dup@example.com", "password": "password123"},
    )
    assert res_dup.status_code == 409
    assert res_dup.get_json()["ok"] is False


def test_contact_validation_and_admin_patch(client, admin_token):
    # Short name
    res = client.post("/api/contact", json={"name": "", "email": "a@b.com", "message": "hello world"})
    assert res.status_code == 400

    # Invalid email
    res = client.post("/api/contact", json={"name": "Alice", "email": "bademail", "message": "hello world"})
    assert res.status_code == 400

    # Short message
    res = client.post("/api/contact", json={"name": "Alice", "email": "a@b.com", "message": "hi"})
    assert res.status_code == 400

    # Valid submission
    res_valid = client.post(
        "/api/contact",
        json={"name": "Bob", "email": "bob@example.com", "subject": "Test", "message": "Valid test message."},
    )
    assert res_valid.status_code == 201
    contact_id = res_valid.get_json()["id"]

    # Patch status by admin
    headers = {"Authorization": f"Bearer {admin_token}"}
    res_patch = client.patch(
        f"/api/admin/contacts/{contact_id}",
        json={"status": "read"},
        headers=headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.get_json()["contact"]["status"] == "read"

    # Patch with invalid status
    res_invalid = client.patch(
        f"/api/admin/contacts/{contact_id}",
        json={"status": "unknown_status"},
        headers=headers,
    )
    assert res_invalid.status_code == 400

    # Non-admin forbidden
    res_unauth = client.patch(f"/api/admin/contacts/{contact_id}", json={"status": "read"})
    assert res_unauth.status_code in (401, 403)


def test_forecast_multi_target_and_regions(client):
    # Test transactions target
    res_tx = client.get("/api/forecast?region=ALL&months=6&target=transactions")
    assert res_tx.status_code == 200
    data_tx = res_tx.get_json()
    assert data_tx.get("ok") is True

    # Test revenue target
    res_rev = client.get("/api/forecast?region=ALL&months=6&target=revenue")
    assert res_rev.status_code == 200
    data_rev = res_rev.get_json()
    assert data_rev.get("ok") is True

    # Test state-specific forecast (Maharashtra)
    res_mh = client.get("/api/forecast?region=MH&months=3&target=registrations")
    assert res_mh.status_code == 200
    data_mh = res_mh.get_json()
    assert data_mh.get("ok") is True
    assert data_mh.get("region") == "MH"


def test_evaluate_models_helpers():
    from src.evaluate_models import evaluate, mape_safe
    import numpy as np

    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([105.0, 195.0, 310.0])
    res = evaluate(y_true, y_pred)
    assert res["MAE"] > 0
    assert res["RMSE"] > 0
    assert res["MAPE"] > 0
    assert res["Approx_Accuracy_100_minus_MAPE"] > 0

    # Zero handling in mape_safe
    assert np.isnan(mape_safe(np.array([0.0, 0.0]), np.array([10.0, 20.0])))


def test_physics_constraints_postprocess():
    from ml.physics.constraints import apply_physics_postprocess
    import numpy as np

    preds = np.array([500.0, 10000.0])
    grid = np.array([800.0, 100.0])
    stations = np.array([200.0, 20.0])
    deg = np.array([0.02, 0.05])
    adjusted = apply_physics_postprocess(preds, grid, stations, deg)
    assert len(adjusted) == 2
    assert (adjusted >= 0).all()
    # High prediction should be capped by physical capacity
    assert adjusted[1] < 10000.0


def test_external_factors_in_dataset_and_xai(client):
    import json
    from pathlib import Path
    import pandas as pd

    root = Path(__file__).resolve().parents[1]
    regs = pd.read_csv(root / "data" / "processed" / "ev_registrations_annual.csv")
    expected_factors = [
        "charging_stations",
        "gov_policy_index",
        "fuel_price",
        "battery_cost",
        "gdp_index",
        "ev_adoption_index",
    ]
    for factor in expected_factors:
        assert factor in regs.columns, f"Missing {factor} in ev_registrations_annual.csv"
        assert not regs[factor].isna().any(), f"NaN found in {factor}"

    # Check XAI ranking
    xai_path = root / "outputs" / "xai" / "feature_importance.json"
    assert xai_path.exists()
    xai_data = json.loads(xai_path.read_text(encoding="utf-8"))
    ranking_feats = [r["feature"] for r in xai_data.get("ranking", [])]
    for factor in expected_factors:
        assert factor in ranking_feats, f"{factor} not ranked in SHAP feature importance"

    # Check XAI dashboard API payload
    res = client.get("/api/xai/dashboard?state=MH&year=2024")
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("ok") is True
    assert data.get("unavailable_factors") == []
    drivers = data.get("external_drivers", [])
    assert len(drivers) == 6
    driver_keys = [d["key"] for d in drivers]
    for factor in expected_factors:
        assert factor in driver_keys

    charts = data.get("charts", {})
    assert len(charts.get("timeseries", {}).get("dates", [])) > 0
    assert len(charts.get("waterfall", {}).get("contributions", [])) > 0
    assert len(charts.get("dependence", {}).get("x", [])) > 0
