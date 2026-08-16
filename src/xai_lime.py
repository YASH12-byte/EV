"""LIME explanations for tabular models (secondary XAI)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "xai"
MODEL_DIR = ROOT / "models" / "saved"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    model_path = MODEL_DIR / "random_forest.pkl"
    if not model_path.exists():
        raise SystemExit("Train models first.")

    try:
        from lime.lime_tabular import LimeTabularExplainer
    except Exception as exc:  # noqa: BLE001
        note = {
            "status": "skipped",
            "reason": f"LIME not installed or unavailable: {exc}",
            "guidance": "Install lime or rely on SHAP TreeExplainer for the RF model. "
            "LIME is less natural for pure sequence CNN-LSTM; use SHAP/RF surrogate for local explanations.",
        }
        (OUT / "lime_status.json").write_text(json.dumps(note, indent=2), encoding="utf-8")
        print(note["reason"])
        return

    cfg = json.loads((ROOT / "outputs" / "feature_config_registrations.json").read_text(encoding="utf-8"))
    feature_cols = cfg["feature_cols"]
    data = np.load(PROC / "registrations_xy.npz")
    X_train, X_test = data["X_train"], data["X_test"]
    model = joblib.load(model_path)

    explainer = LimeTabularExplainer(
        X_train,
        feature_names=feature_cols,
        mode="regression",
        discretize_continuous=True,
    )
    exp = explainer.explain_instance(X_test[0], model.predict, num_features=min(8, len(feature_cols)))
    exp.save_to_file(str(OUT / "lime_explanation.html"))
    (OUT / "lime_status.json").write_text(
        json.dumps({"status": "ok", "sample_index": 0, "file": "lime_explanation.html"}, indent=2),
        encoding="utf-8",
    )
    print("LIME explanation saved.")


if __name__ == "__main__":
    main()
