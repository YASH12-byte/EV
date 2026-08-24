"""Flask-facing XAI service."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


class XAIService:
    _warmed = False

    def _warm(self) -> None:
        if self._warmed:
            return
        try:
            from src.xai_engine import _get_rf_artifacts, _load_features, _load_predictions

            _get_rf_artifacts()
            _load_features()
            _load_predictions()
            self._warmed = True
        except Exception:
            pass

    def dashboard(
        self,
        state: str = "ALL",
        year: Optional[int] = None,
        vehicle_type: str = "All",
        target: str = "registrations",
        refresh: bool = False,
    ) -> Dict[str, Any]:
        self._warm()
        from src.xai_engine import build_xai_dashboard

        return build_xai_dashboard(
            state=state,
            year=year,
            vehicle_type=vehicle_type,
            target=target,
            refresh=refresh,
        )

    def artifacts_dir(self) -> Path:
        return ROOT / "outputs" / "xai"
