"""Smoke tests for state display-name mapping."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.state_names import display_name, regions_payload


def test_known_codes():
    assert display_name("MH") == "Maharashtra"
    assert display_name("ALL") == "All India"
    assert display_name("DL") == "Delhi"


def test_unknown_kept_as_is():
    assert display_name("CustomRegion") == "CustomRegion"


def test_regions_payload_sorted_and_includes_all():
    items = regions_payload(["MH", "KA", "DL"], include_all=True)
    assert items[0]["code"] == "ALL"
    names = [x["name"] for x in items[1:]]
    assert names == sorted(names, key=str.lower)
