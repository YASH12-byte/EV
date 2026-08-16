"""SHAP explanations for tabular Random Forest on registration features."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "xai"
MODEL_DIR = ROOT / "models" / "saved"
OUT.mkdir(parents=True, exist_ok=True)


def _bar_fallback(ranking, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    top = ranking[:12]
    ax.barh([t["feature"] for t in top][::-1], [t["importance"] for t in top][::-1], color="#2563EB")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    model_path = MODEL_DIR / "random_forest.pkl"
    if not model_path.exists():
        raise SystemExit("Train models first (random_forest.pkl missing).")

    cfg = json.loads((ROOT / "outputs" / "feature_config_registrations.json").read_text(encoding="utf-8"))
    feature_cols = cfg["feature_cols"]
    data = np.load(PROC / "registrations_xy.npz")
    X_train, X_test = data["X_train"], data["X_test"]
    model = joblib.load(model_path)

    used = "feature_importances_"
    ranking = []
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        background = X_train[: min(200, len(X_train))]
        sample = X_test[: min(100, len(X_test))]
        shap_values = explainer.shap_values(sample)

        plt.figure()
        shap.summary_plot(shap_values, sample, feature_names=feature_cols, show=False)
        plt.tight_layout()
        plt.savefig(OUT / "shap_summary.png", dpi=140, bbox_inches="tight")
        plt.close()

        plt.figure()
        shap.summary_plot(shap_values, sample, feature_names=feature_cols, plot_type="bar", show=False)
        plt.tight_layout()
        plt.savefig(OUT / "shap_bar.png", dpi=140, bbox_inches="tight")
        plt.close()

        mean_abs = np.abs(np.asarray(shap_values)).mean(axis=0)
        ranking = sorted(
            [{"feature": f, "importance": float(v)} for f, v in zip(feature_cols, mean_abs)],
            key=lambda x: -x["importance"],
        )

        try:
            ev = explainer.expected_value
            ev = float(np.asarray(ev).reshape(-1)[0])
            plt.figure()
            shap.plots._waterfall.waterfall_legacy(ev, shap_values[0], feature_names=feature_cols, show=False)
            plt.tight_layout()
            plt.savefig(OUT / "prediction_explanation.png", dpi=140, bbox_inches="tight")
            plt.close()
        except Exception as wexc:  # noqa: BLE001
            print(f"[WARN] waterfall skipped: {wexc}")
            _bar_fallback(ranking, "Mean |SHAP| feature importance", OUT / "prediction_explanation.png")

        used = "shap"
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] SHAP unavailable ({exc}); using RF impurity importance.")
        imp = model.feature_importances_
        ranking = sorted(
            [{"feature": f, "importance": float(v)} for f, v in zip(feature_cols, imp)],
            key=lambda x: -x["importance"],
        )
        _bar_fallback(ranking, "Feature Importance (Random Forest)", OUT / "shap_bar.png")
        _bar_fallback(ranking, "Feature Importance (Random Forest)", OUT / "shap_summary.png")
        _bar_fallback(ranking, "Feature Importance (Random Forest)", OUT / "prediction_explanation.png")

    (OUT / "feature_importance.json").write_text(
        json.dumps({"method": used, "ranking": ranking}, indent=2),
        encoding="utf-8",
    )
    print("XAI artifacts written to", OUT)


if __name__ == "__main__":
    main()
