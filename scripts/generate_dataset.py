"""
Synthetic + realistic EV market dataset generator.
Mirrors IEA / government registration style features for offline BE demos.
Replace with real CSVs from Kaggle/IEA/Open Charge Map when available.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = [
    "Maharashtra",
    "Karnataka",
    "Delhi",
    "Tamil Nadu",
    "Gujarat",
    "Telangana",
    "Rajasthan",
    "Uttar Pradesh",
]


def generate_region_series(
    region: str,
    n_months: int = 96,
    seed: int = 42,
    base_sales: float = 800.0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + abs(hash(region)) % 10_000)
    dates = pd.date_range("2018-01-01", periods=n_months, freq="MS")
    t = np.arange(n_months)

    # Structural drivers
    trend = base_sales * (1.0 + 0.018 * t + 0.00012 * t**2)
    seasonality = 120 * np.sin(2 * np.pi * t / 12) + 60 * np.cos(2 * np.pi * t / 6)
    policy_shocks = np.zeros(n_months)
    for idx in [24, 48, 72]:
        if idx < n_months:
            policy_shocks[idx : idx + 6] += rng.uniform(150, 400)

    battery_cost = 180 - 0.9 * t + rng.normal(0, 2.5, n_months)
    battery_cost = np.clip(battery_cost, 55, 200)
    electricity_price = 6.5 + 0.01 * t + 0.4 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 0.15, n_months)
    fuel_price = 85 + 0.08 * t + 5 * np.sin(2 * np.pi * t / 18) + rng.normal(0, 1.2, n_months)
    gdp_index = 100 + 0.35 * t + rng.normal(0, 0.8, n_months)
    population = 10_000_000 + 8_000 * t + rng.normal(0, 2_000, n_months)
    carbon_emission = 220 - 0.25 * t + rng.normal(0, 1.5, n_months)
    gov_policy_index = 40 + 0.4 * t + policy_shocks / 20 + rng.normal(0, 1.0, n_months)
    charging_stations = np.maximum(
        50,
        40 + 2.2 * t + 0.015 * t**2 + policy_shocks * 0.3 + rng.normal(0, 5, n_months),
    )
    grid_capacity = 500 + 3.5 * t + 0.2 * charging_stations + rng.normal(0, 8, n_months)
    battery_degradation_index = 0.02 + 0.00015 * t + rng.normal(0, 0.001, n_months)

    # Nonlinear market response
    demand = (
        trend
        + seasonality
        + policy_shocks
        + 1.8 * charging_stations
        - 2.5 * (battery_cost - 100)
        - 15 * (electricity_price - 7)
        + 0.8 * (fuel_price - 90)
        + 1.2 * (gov_policy_index - 50)
        + 0.4 * (gdp_index - 100)
        - 80 * battery_degradation_index * 100
        + rng.normal(0, 35, n_months)
    )
    # Soft grid constraint: sales cannot explode beyond charging/grid capacity
    capacity_cap = 0.55 * charging_stations + 0.08 * grid_capacity
    ev_sales = np.minimum(np.maximum(demand, 50), capacity_cap * 8 + trend * 0.35)
    ev_sales = np.maximum(ev_sales, 50)

    return pd.DataFrame(
        {
            "date": dates,
            "region": region,
            "ev_sales": ev_sales.round(2),
            "charging_stations": charging_stations.round(2),
            "battery_cost": battery_cost.round(2),
            "electricity_price": electricity_price.round(3),
            "fuel_price": fuel_price.round(2),
            "gdp_index": gdp_index.round(2),
            "population": population.round(0),
            "carbon_emission": carbon_emission.round(2),
            "gov_policy_index": gov_policy_index.round(2),
            "grid_capacity": grid_capacity.round(2),
            "battery_degradation_index": battery_degradation_index.round(5),
        }
    )


def build_dataset(output_path: Path, n_months: int = 96) -> pd.DataFrame:
    frames = []
    bases = [900, 1100, 1300, 1000, 950, 850, 700, 1200]
    for i, region in enumerate(REGIONS):
        frames.append(generate_region_series(region, n_months=n_months, seed=42 + i, base_sales=bases[i]))
    df = pd.concat(frames, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate EV market dataset")
    parser.add_argument("--months", type=int, default=96)
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "raw" / "ev_market_data.csv"),
    )
    args = parser.parse_args()
    df = build_dataset(Path(args.out), n_months=args.months)
    print(f"Saved {len(df)} rows -> {args.out}")
    print(df.head())


if __name__ == "__main__":
    main()
