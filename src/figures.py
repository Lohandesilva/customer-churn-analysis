"""Figures for the report pack."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config
from .viz import SERIES, SEQUENTIAL, INK, INK_MUTED, INK_SECONDARY, apply_house_style, save

SOURCE = "Source: IBM Telco customer churn extract, 7,043 accounts."

# Field names carry the source system's casing. Charts read better in plain
# business English, so the mapping is explicit rather than a regex guess.
TERM_LABELS = {
    "InternetService_Fiber_optic": "Fibre broadband",
    "InternetService_No": "No internet service",
    "Contract_One_year": "One-year contract",
    "Contract_Two_year": "Two-year contract",
    "PaymentMethod_Electronic_check": "Pays by electronic cheque",
    "PaymentMethod_Mailed_check": "Pays by mailed cheque",
    "PaymentMethod_Credit_card_automatic": "Card on file",
    "StreamingTV_Yes": "Streaming TV attached",
    "StreamingMovies_Yes": "Streaming films attached",
    "MultipleLines_Yes": "Multiple lines",
    "PaperlessBilling_Yes": "Paperless billing",
    "OnlineSecurity_Yes": "Online security attached",
    "TechSupport_Yes": "Tech support attached",
    "OnlineBackup_Yes": "Online backup attached",
    "DeviceProtection_Yes": "Device protection attached",
    "Partner_Yes": "Has a partner on account",
    "Dependents_Yes": "Has dependents",
    "senior": "Senior citizen",
    "tenure": "Each additional month on book",
    "MonthlyCharges": "Each additional $1 on the bill",
}


def retention_curves(curves: dict, path) -> None:
    apply_house_style()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    order = ["Two year", "One year", "Month-to-month"]
    for i, name in enumerate([n for n in order if n in curves]):
        km = curves[name]
        ax.plot(km["tenure_month"], km["survival"], color=SERIES[i], label=name)
        ax.fill_between(km["tenure_month"], km["survival_lo"], km["survival_hi"],
                        color=SERIES[i], alpha=0.12, linewidth=0)
        ax.annotate(name, (km["tenure_month"].iloc[-1], km["survival"].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", color=SERIES[i],
                    fontsize=8.5, va="center")
    ax.axhline(0.5, color=INK_MUTED, linewidth=0.8, linestyle=(0, (4, 4)))
    ax.text(1, 0.515, "50% retained", fontsize=7.5, color=INK_MUTED)
    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, 78)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
    ax.set_yticklabels([f"{v:.0%}" for v in np.arange(0, 1.01, 0.25)])
    ax.set_xlabel("Months on book")
    ax.set_ylabel("Share still active")
    ax.set_title("Contract type, not price, decides how long a customer stays")
    ax.grid(axis="x", visible=False)
    fig.text(0.005, -0.02, SOURCE + " Kaplan-Meier estimate, shaded 95% interval.",
             fontsize=7.5, color=INK_MUTED)
    save(fig, path)


def hazard_profile(km_all: pd.DataFrame, path) -> None:
    apply_house_style()
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    smooth = km_all["hazard"].rolling(3, center=True, min_periods=1).mean()
    ax.bar(km_all["tenure_month"], km_all["hazard"], color=SEQUENTIAL[1], width=0.8)
    ax.plot(km_all["tenure_month"], smooth, color=SERIES[0], linewidth=1.8)
    ax.set_xlim(0, 73)
    ax.set_xlabel("Months on book")
    ax.set_ylabel("Monthly churn hazard")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title("Churn risk is front-loaded and decays with tenure")
    ax.grid(axis="x", visible=False)
    peak = km_all.loc[km_all["hazard"].idxmax()]
    ax.annotate(
        f"Peak {peak['hazard']:.1%} at month {int(peak['tenure_month'])}",
        xy=(peak["tenure_month"], peak["hazard"]),
        xytext=(14, -6), textcoords="offset points", fontsize=8, color=INK_SECONDARY,
    )
    fig.text(0.005, -0.04, SOURCE + " Bars show the raw monthly hazard; line is a 3-month mean.",
             fontsize=7.5, color=INK_MUTED)
    save(fig, path)


def driver_odds(coefs: pd.DataFrame, path, top: int = 12) -> None:
    apply_house_style()
    sig = coefs[coefs["p_value"] < 0.05].copy()
    sig["distance"] = (sig["odds_ratio"] - 1).abs()
    show = sig.nlargest(top, "distance").sort_values("odds_ratio")

    labels = show["term"].map(lambda t: TERM_LABELS.get(t, t.replace("_", " ")))

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    y = np.arange(len(show))
    colors = [SERIES[7] if v > 1 else SERIES[2] for v in show["odds_ratio"]]
    ax.hlines(y, show["or_lo"], show["or_hi"], color=colors, linewidth=1.6, alpha=0.55)
    ax.scatter(show["odds_ratio"], y, color=colors, s=34, zorder=3)
    ax.axvline(1, color=INK_MUTED, linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5, color=INK_SECONDARY)
    ax.set_xscale("log")
    ax.set_xticks([0.25, 0.5, 1, 2, 4])
    ax.set_xticklabels(["0.25x", "0.5x", "1x", "2x", "4x"])
    ax.set_xlabel("Odds of churn versus the reference customer")
    ax.set_title("What actually moves churn odds, holding everything else constant")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    for yi, row in zip(y, show.itertuples()):
        ax.annotate(f"{row.odds_ratio:.2f}x", (row.or_hi, yi), xytext=(6, 0),
                    textcoords="offset points", fontsize=7.5, color=INK_MUTED, va="center")
    fig.text(0.005, -0.03,
             SOURCE + " Logistic regression, significant terms (p < 0.05), 95% intervals.",
             fontsize=7.5, color=INK_MUTED)
    save(fig, path)


def gains_curve(table: pd.DataFrame, path) -> None:
    apply_house_style()
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    x = np.concatenate([[0], table["cumulative_base_pct"].to_numpy()])
    y = np.concatenate([[0], table["cumulative_churn_revenue_pct"].to_numpy()])
    ax.plot([0, 1], [0, 1], color=INK_MUTED, linewidth=1, linestyle=(0, (4, 4)))
    ax.plot(x, y, color=SERIES[0])
    ax.fill_between(x, x, y, color=SERIES[0], alpha=0.10, linewidth=0)

    mark = table[table["decile"] == config.TARGETING_DECILES].iloc[0]
    ax.scatter([mark["cumulative_base_pct"]], [mark["cumulative_churn_revenue_pct"]],
               color=SERIES[0], s=48, zorder=4)
    ax.annotate(
        f"Top {config.TARGETING_DECILES} deciles: "
        f"{mark['cumulative_base_pct']:.0%} of the base holds "
        f"{mark['cumulative_churn_revenue_pct']:.0%} of lost revenue",
        xy=(mark["cumulative_base_pct"], mark["cumulative_churn_revenue_pct"]),
        xytext=(10, -22), textcoords="offset points", fontsize=8.5, color=INK,
    )
    ax.text(0.62, 0.55, "no targeting", fontsize=7.5, color=INK_MUTED, rotation=32)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("Share of the base contacted, highest modelled risk first")
    ax.set_ylabel("Share of lost monthly revenue reached")
    ax.set_title("Targeting concentrates the value: two deciles carry most of the loss")
    fig.text(0.005, -0.03, SOURCE + " Model-ranked deciles, holdout-validated.",
             fontsize=7.5, color=INK_MUTED)
    save(fig, path)


def revenue_bridge(segments: pd.DataFrame, path) -> None:
    apply_house_style()
    d = segments.sort_values("monthly_revenue_lost", ascending=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    y = np.arange(len(d))
    ax.barh(y, d["monthly_revenue_lost"], color=SEQUENTIAL[4], height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(d["segment"], fontsize=8.5, color=INK_SECONDARY)
    ax.xaxis.set_major_formatter(lambda v, _: f"${v/1000:,.0f}k")
    ax.set_xlabel("Monthly recurring revenue lost")
    ax.set_title("Where the lost revenue actually sits")
    ax.grid(axis="y", visible=False); ax.grid(axis="x", visible=True)
    for yi, row in zip(y, d.itertuples()):
        ax.annotate(f"${row.monthly_revenue_lost:,.0f}  ({row.churn_rate:.0%} churn)",
                    (row.monthly_revenue_lost, yi), xytext=(6, 0),
                    textcoords="offset points", fontsize=8, color=INK_MUTED, va="center")
    ax.set_xlim(0, d["monthly_revenue_lost"].max() * 1.42)
    fig.text(0.005, -0.03, SOURCE, fontsize=7.5, color=INK_MUTED)
    save(fig, path)


def breakeven_heatmap(sens: pd.DataFrame, path) -> None:
    apply_house_style()
    grid = sens.pivot(index="contribution_margin", columns="offer_discount",
                      values="breakeven_save_rate")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    im = ax.imshow(grid.to_numpy(), cmap="Blues", aspect="auto", origin="lower")
    ax.set_xticks(range(len(grid.columns)))
    ax.set_xticklabels([f"{c:.0%}" for c in grid.columns])
    ax.set_yticks(range(len(grid.index)))
    ax.set_yticklabels([f"{r:.0%}" for r in grid.index])
    ax.set_xlabel("Discount given away")
    ax.set_ylabel("Contribution margin")
    ax.set_title("Save rate the offer must clear to break even")
    ax.grid(False)
    vmax = np.nanmax(grid.to_numpy())
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid.to_numpy()[i, j]
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=8,
                    color="white" if v > vmax * 0.6 else INK)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Breakeven save rate")
    fig.text(0.005, -0.04,
             f"Assumes a {config.OFFER_DURATION_MONTHS}-month offer and "
             f"${config.OFFER_SERVICING_COST:.0f} servicing cost per contact.",
             fontsize=7.5, color=INK_MUTED)
    save(fig, path)
