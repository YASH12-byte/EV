"""
Display-name mapping for Indian state / UT codes used in DataSet.zip.
Raw codes stay unchanged in processed CSVs; UI uses these full names.
"""
from __future__ import annotations

from typing import Dict, List, Optional

# Reliable Vahan / MoRTH-style abbreviations → full display names
STATE_DISPLAY_NAMES: Dict[str, str] = {
    "ALL": "All India",
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "CT": "Chhattisgarh",
    "DD": "Dadra and Nagar Haveli and Daman and Diu",
    "DL": "Delhi",
    "DN": "Dadra and Nagar Haveli and Daman and Diu",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "OR": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TG": "Telangana",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "TS": "Telangana",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "UT": "Uttarakhand",
    "WB": "West Bengal",
}


def display_name(code: Optional[str]) -> str:
    if code is None:
        return "Unknown"
    raw = str(code).strip()
    if not raw:
        return "Unknown"
    key = raw.upper()
    if key in STATE_DISPLAY_NAMES:
        return STATE_DISPLAY_NAMES[key]
    # Already a full name or unknown code — keep as-is (never invent)
    return raw


def regions_payload(codes: List[str], include_all: bool = True) -> List[Dict[str, str]]:
    uniq = []
    seen = set()
    for c in codes:
        key = str(c).strip().upper()
        if not key or key in seen or key == "ALL":
            continue
        seen.add(key)
        uniq.append(key)
    items = [{"code": c, "name": display_name(c)} for c in uniq]
    items.sort(key=lambda x: x["name"].lower())
    if include_all:
        items.insert(0, {"code": "ALL", "name": display_name("ALL")})
    return items
