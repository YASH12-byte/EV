from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.train_all_real import train_tabular
if __name__ == "__main__":
    print(train_tabular().get("XGBoost"))
