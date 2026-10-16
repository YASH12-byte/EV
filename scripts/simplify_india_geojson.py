"""One-off: simplify raw India states GeoJSON for the forecast choropleth."""
from __future__ import annotations

import json
import os
from math import hypot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "static", "data", "india-states.raw.geojson")
OUT = os.path.join(ROOT, "frontend", "static", "data", "india-states.geojson")

NAME_TO_CODE = {
    "Andaman and Nicobar": "AN",
    "Andhra Pradesh": "AP",
    "Arunachal Pradesh": "AR",
    "Assam": "AS",
    "Bihar": "BR",
    "Chandigarh": "CH",
    "Chhattisgarh": "CG",
    "Dadra and Nagar Haveli": "DD",
    "Daman and Diu": "DD",
    "Delhi": "DL",
    "Goa": "GA",
    "Gujarat": "GJ",
    "Haryana": "HR",
    "Himachal Pradesh": "HP",
    "Jammu and Kashmir": "JK",
    "Jharkhand": "JH",
    "Karnataka": "KA",
    "Kerala": "KL",
    "Lakshadweep": "LD",
    "Madhya Pradesh": "MP",
    "Maharashtra": "MH",
    "Manipur": "MN",
    "Meghalaya": "ML",
    "Mizoram": "MZ",
    "Nagaland": "NL",
    "Orissa": "OD",
    "Odisha": "OD",
    "Puducherry": "PY",
    "Punjab": "PB",
    "Rajasthan": "RJ",
    "Sikkim": "SK",
    "Tamil Nadu": "TN",
    "Telangana": "TG",
    "Tripura": "TR",
    "Uttar Pradesh": "UP",
    "Uttaranchal": "UK",
    "Uttarakhand": "UK",
    "West Bengal": "WB",
}


def dist_point_seg(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return hypot(px - (ax + t * dx), py - (ay + t * dy))


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    stack = [(0, len(pts) - 1)]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    while stack:
        i, j = stack.pop()
        maxd = -1.0
        idx = None
        a, b = pts[i], pts[j]
        for k in range(i + 1, j):
            d = dist_point_seg(pts[k], a, b)
            if d > maxd:
                maxd = d
                idx = k
        if maxd > eps and idx is not None:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [pts[i] for i in range(len(pts)) if keep[i]]


def round_ring(ring, nd=3):
    return [[round(x, nd), round(y, nd)] for x, y in ring]


def simplify_ring(ring, eps):
    if len(ring) < 4:
        return round_ring(ring)
    closed = ring[0] == ring[-1]
    body = ring[:-1] if closed else ring
    if len(body) > 800:
        step = max(1, len(body) // 400)
        body = body[::step]
    simp = rdp(body, eps)
    if len(simp) < 3:
        simp = body[:3] if len(body) >= 3 else body
    if closed and simp and simp[0] != simp[-1]:
        simp.append(simp[0][:])
    rnd = round_ring(simp)
    cleaned = [rnd[0]]
    for p in rnd[1:]:
        if p != cleaned[-1]:
            cleaned.append(p)
    if cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0][:])
    if len(cleaned) < 4:
        return None
    return cleaned


def simplify_coords(coords, gtype, eps):
    if gtype == "Polygon":
        rings = [simplify_ring(r, eps) for r in coords]
        rings = [r for r in rings if r]
        return rings or [round_ring(coords[0])]
    if gtype == "MultiPolygon":
        out = []
        for poly in coords:
            rings = [simplify_ring(r, eps) for r in poly]
            rings = [r for r in rings if r]
            if rings:
                out.append(rings)
        return out or [[round_ring(coords[0][0])]]
    return coords


def as_multipolygon(geoms):
    coords = []
    for g in geoms:
        if g["type"] == "Polygon":
            coords.append(g["coordinates"])
        else:
            coords.extend(g["coordinates"])
    if len(coords) == 1:
        return {"type": "Polygon", "coordinates": coords[0]}
    return {"type": "MultiPolygon", "coordinates": coords}


def main():
    print("loading...")
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    eps = 0.06
    merged = {}
    for feat in data["features"]:
        name = feat["properties"]["NAME_1"]
        code = NAME_TO_CODE.get(name)
        if not code:
            print("UNMAPPED", name)
            continue
        geom = feat["geometry"]
        simp = {
            "type": geom["type"],
            "coordinates": simplify_coords(geom["coordinates"], geom["type"], eps),
        }
        if code not in merged:
            merged[code] = {"name": name, "geoms": [simp]}
        else:
            merged[code]["geoms"].append(simp)

    features = []
    for code, item in sorted(merged.items()):
        features.append(
            {
                "type": "Feature",
                "properties": {"code": code, "name": item["name"]},
                "geometry": as_multipolygon(item["geoms"]),
            }
        )

    out_obj = {"type": "FeatureCollection", "features": features}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, separators=(",", ":"))
    print("out bytes", os.path.getsize(OUT), "features", len(features))
    print("codes", [f["properties"]["code"] for f in features])


if __name__ == "__main__":
    main()
