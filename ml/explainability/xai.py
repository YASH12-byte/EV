"""
Explainable AI: SHAP, LIME, Attention maps, and feature importance summaries.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config


FEATURE_EXPLANATIONS = {
    "battery_cost": "Lower battery pack costs increase EV affordability and adoption.",
    "charging_stations": "Dense charging infrastructure reduces range anxiety and boosts sales.",
    "gov_policy_index": "Subsidies, tax credits, and mandates strongly shift EV demand.",
    "fuel_price": "Higher petrol/diesel prices make EVs relatively more attractive.",
    "electricity_price": "Charging cost competitiveness versus ICE running costs.",
    "gdp_index": "Economic growth correlates with vehicle purchasing power.",
    "population": "Larger populations expand the absolute vehicle market base.",
    "carbon_emission": "Emission pressure and ESG goals accelerate fleet electrification.",
    "grid_capacity": "Grid headroom enables reliable high-power charging expansion.",
    "battery_degradation_index": "Perceived battery longevity affects buyer confidence.",
    "ev_sales": "Autoregressive history of market momentum and seasonality.",
}


def shap_feature_importance(model, X_sample: np.ndarray, feature_names: List[str], max_samples: int = 100) -> Dict:
    try:
        import shap
    except ImportError:
        return _fallback_importance(model, X_sample, feature_names)

    X = X_sample[:max_samples]
    # Tabular models expect 2D; DL expects 3D
    try:
        if hasattr(model, "predict") and X.ndim == 3:
            # Kernel SHAP on flattened last step for DL approximate explanations
            X2 = X[:, -1, :]

            def f(z):
                # Broadcast last-step perturbation into full sequences (approx)
                seq = np.repeat(X[: len(z)], repeats=1, axis=0) if False else None
                # Rebuild sequences using background last timesteps
                base = X[: z.shape[0]].copy()
                base[:, -1, :] = z
                return model.predict(base, verbose=0).ravel()

            explainer = shap.KernelExplainer(f, X2[:20])
            sv = explainer.shap_values(X2[:30], nsamples=50)
            vals = np.abs(np.asarray(sv)).mean(axis=0)
        else:
            explainer = shap.Explainer(model.predict, X[:50])
            sv = explainer(X[:50])
            vals = np.abs(sv.values).mean(axis=0)
    except Exception:
        return _fallback_importance(model, X_sample, feature_names)

    ranking = sorted(
        [{"feature": n, "importance": float(v), "insight": FEATURE_EXPLANATIONS.get(n, "")} for n, v in zip(feature_names, vals)],
        key=lambda d: d["importance"],
        reverse=True,
    )
    return {"method": "SHAP", "ranking": ranking}


def lime_explain_instance(model, X_instance: np.ndarray, X_train: np.ndarray, feature_names: List[str]) -> Dict:
    try:
        from lime.lime_tabular import LimeTabularExplainer
    except ImportError:
        return {"method": "LIME", "error": "lime not installed", "explanation": []}

    Xtr = X_train[:, -1, :] if X_train.ndim == 3 else X_train
    inst = X_instance[-1] if X_instance.ndim == 2 else X_instance

    def predict_fn(z):
        if hasattr(model, "predict"):
            # DL path
            try:
                base = np.repeat(X_instance[None, ...], z.shape[0], axis=0)
                base[:, -1, :] = z
                return model.predict(base, verbose=0).ravel()
            except Exception:
                return model.predict(z)

    explainer = LimeTabularExplainer(
        Xtr,
        feature_names=feature_names,
        mode="regression",
        discretize_continuous=True,
    )
    exp = explainer.explain_instance(inst, predict_fn, num_features=min(10, len(feature_names)))
    pairs = [{"feature": f, "weight": float(w), "insight": FEATURE_EXPLANATIONS.get(f.split("=")[0].split("<")[0].strip(), "")} for f, w in exp.as_list()]
    return {"method": "LIME", "explanation": pairs}


def _fallback_importance(model, X_sample: np.ndarray, feature_names: List[str]) -> Dict:
    """Permutation importance fallback."""
    X = X_sample.copy()
    if X.ndim == 3:
        base_pred = model.predict(X, verbose=0).ravel()
        importances = []
        for i, name in enumerate(feature_names):
            Xp = X.copy()
            rng = np.random.default_rng(0)
            Xp[:, :, i] = rng.permutation(Xp[:, :, i], axis=0)
            pred = model.predict(Xp, verbose=0).ravel()
            importances.append(float(np.mean(np.abs(base_pred - pred))))
    else:
        if hasattr(model, "feature_importances_"):
            importances = list(map(float, model.feature_importances_))
        else:
            importances = [1.0 / len(feature_names)] * len(feature_names)

    ranking = sorted(
        [
            {"feature": n, "importance": float(v), "insight": FEATURE_EXPLANATIONS.get(n, "")}
            for n, v in zip(feature_names, importances)
        ],
        key=lambda d: d["importance"],
        reverse=True,
    )
    return {"method": "Permutation/Native", "ranking": ranking}


def attention_map_from_model(model, X_batch: np.ndarray) -> Optional[np.ndarray]:
    """Extract attention weights if AttentionBlock present."""
    import tensorflow as tf

    try:
        attn_layer = model.get_layer("attention")
        # Build intermediate model up to LSTM output feeding attention
        # Walk inputs: sequence -> ... -> lstm
        lstm_out = model.get_layer("lstm").output
        # Recreate attention call
        context, weights = attn_layer(lstm_out)
        # Need a model that maps input to weights — reconstruct via functional API
        # Simpler: manually forward using sublayers
    except Exception:
        return None

    # Manual forward for attention weights
    try:
        x = X_batch
        for layer in model.layers:
            if layer.name == "sequence_input":
                continue
            if layer.name == "attention":
                _, weights = layer(x)
                return weights.numpy()
            if isinstance(layer, tf.keras.layers.Dense) and layer.name.startswith("dense"):
                break
            # Only propagate feature extractors
            if layer.name in {"forecast", "dropout_dense", "dense_1"}:
                break
            try:
                x = layer(x)
            except Exception:
                break
    except Exception:
        return None
    return None


def save_default_explanations(path: Optional[Path] = None):
    path = path or (config.MODEL_DIR / "feature_insights.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(FEATURE_EXPLANATIONS, f, indent=2)
