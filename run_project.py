"""
End-to-end runner for the real DataSet.zip pipeline.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_step(label: str, script: str) -> None:
    print("\n" + "=" * 72)
    print(label)
    print("=" * 72)
    cmd = [sys.executable, str(ROOT / script)]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"Step failed: {script} (exit {proc.returncode})")


def write_objective_file() -> None:
    text = """# Objective Achievement Mapping

## Objective 1
Study existing ML and XAI techniques for EV market trend analysis and sales forecasting.

**Achievement:** Implemented and compared Naive, ARIMA, Random Forest, XGBoost (if available), CNN, LSTM, and Hybrid CNN-LSTM on real Vahan-style registration data. Added SHAP (primary) and LIME (secondary/tabular) explainability modules.

## Objective 2
Develop a Hybrid ML-Time-Series model for EV market growth prediction.

**Achievement:** Implemented Causal Conv1D → MaxPool → LSTM → Dense Hybrid CNN-LSTM for national annual EV registrations, with EarlyStopping and ReduceLROnPlateau.

## Objective 3
Improve forecasting accuracy using CNN, LSTM and advanced time-series techniques.

**Achievement:** Evaluated all models on a chronological test split using MAE, RMSE, MAPE, and R² computed from actual predictions (see `outputs/final_results.csv`). Best model is selected by lowest RMSE without fabricating scores. Approximate accuracy is reported only as `100 - MAPE` and labeled as derived.

## Objective 4
Extract temporal and state-level patterns from EV registration and transaction/revenue data and explain predictions using XAI.

**Achievement:** Built annual registration and monthly transaction/revenue processed datasets from DataSet.zip; produced state-wise EDA figures; SHAP feature rankings for the tabular model; forecast endpoints for registrations.

## Dataset limitations honestly reported
- No charging-station columns in DataSet.zip.
- `registration_2010-2026.csv` uses nested list encodings that were expanded carefully without inventing values.
- Monthly revenue/transactions are not naively joined onto annual registration rows at mismatched frequency.
"""
    out = ROOT / "outputs" / "objective_achievement.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("Wrote", out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train", action="store_true", help="Skip training if models already exist")
    parser.add_argument("--serve", action="store_true", help="Start Flask app after pipeline")
    args = parser.parse_args()

    run_step("1) Dataset inspection", "src/data_inspection.py")
    run_step("2) Data preprocessing", "src/data_preprocessing.py")
    run_step("3) EDA", "src/eda.py")
    run_step("4) Feature engineering", "src/feature_engineering.py")

    model_exists = (ROOT / "models" / "saved" / "random_forest.pkl").exists()
    if args.skip_train and model_exists:
        print("Skipping training (--skip-train and models present)")
    else:
        run_step("5) Train + evaluate models", "src/train_all_real.py")
        run_step("6) SHAP XAI", "src/xai_shap.py")
        run_step("7) LIME XAI", "src/xai_lime.py")

    write_objective_file()
    print("\nPipeline complete. Key outputs:")
    print(" - outputs/data_profile.json")
    print(" - outputs/final_results.csv")
    print(" - outputs/model_comparison.png")
    print(" - outputs/xai/")
    print(" - data/processed/")

    if args.serve:
        run_step("8) Flask app", "run.py")


if __name__ == "__main__":
    main()
