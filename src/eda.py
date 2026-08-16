"""EDA charts from processed EV datasets."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def main() -> None:
    nat = pd.read_csv(PROC / "ev_registrations_national_annual.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(nat["Year"], nat["Registrations"], marker="o", color="#2563EB")
    ax.set_title("National EV Registrations (Annual)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Registrations")
    fig.tight_layout()
    fig.savefig(FIG / "national_registration_trend.png", dpi=140)
    plt.close(fig)

    regs = pd.read_csv(PROC / "ev_registrations_annual.csv")
    top_states = (
        regs.groupby("State")["Registrations"].sum().sort_values(ascending=False).head(10)
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    top_states.sort_values().plot(kind="barh", ax=ax, color="#06B6D4")
    ax.set_title("Top 10 States by Total EV Registrations")
    fig.tight_layout()
    fig.savefig(FIG / "state_registrations_top10.png", dpi=140)
    plt.close(fig)

    if (PROC / "fuel_type_distribution.csv").exists():
        fuel = pd.read_csv(PROC / "fuel_type_distribution.csv")
        g = fuel.groupby("FuelType")["Count"].sum().sort_values(ascending=False).head(8)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        g.plot(kind="bar", ax=ax, color="#10B981")
        ax.set_title("Fuel Type Distribution (EV-related)")
        plt.xticks(rotation=30, ha="right")
        fig.tight_layout()
        fig.savefig(FIG / "fuel_type_distribution.png", dpi=140)
        plt.close(fig)

    if (PROC / "ev_transactions_monthly_national.csv").exists():
        tx = pd.read_csv(PROC / "ev_transactions_monthly_national.csv", parse_dates=["Date"])
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(tx["Date"], tx["EV_Transactions"], color="#2563EB", linewidth=1)
        ax.set_title("National EV Transactions (Monthly)")
        fig.tight_layout()
        fig.savefig(FIG / "national_transactions_trend.png", dpi=140)
        plt.close(fig)

    if (PROC / "ev_revenue_monthly_national.csv").exists():
        rev = pd.read_csv(PROC / "ev_revenue_monthly_national.csv", parse_dates=["Date"])
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(rev["Date"], rev["Revenue"], color="#10B981", linewidth=1)
        ax.set_title("National EV Revenue (Monthly)")
        fig.tight_layout()
        fig.savefig(FIG / "national_revenue_trend.png", dpi=140)
        plt.close(fig)

    print("EDA figures written to", FIG)


if __name__ == "__main__":
    main()
