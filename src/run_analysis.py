"""End-to-end run. Every number quoted in the report pack is produced here.

    python -m src.run_analysis
"""

from __future__ import annotations

import json

import pandas as pd

from . import config, drivers, economics, figures, survival
from .features import add_features
from .ingest import clean, load_raw


def main() -> dict:
    for path in (config.PROCESSED, config.FIGURES, config.TABLES, config.EXTRACTS):
        path.mkdir(parents=True, exist_ok=True)

    raw = load_raw()
    df, quality = clean(raw)
    df = add_features(df)
    df.to_parquet(config.PROCESSED / "customers.parquet", index=False)

    # --- Portfolio position -------------------------------------------------
    risk = economics.revenue_at_risk(df)

    # --- Survival -----------------------------------------------------------
    km_all = survival.kaplan_meier(df["tenure"], df["churned"])
    curves, contract_summary = survival.curves_by_group(df, "Contract", config.HORIZON_MONTHS)
    lr = survival.logrank(df, "Contract")

    km_all.to_csv(config.TABLES / "hazard_by_tenure_month.csv", index=False)
    contract_summary.to_csv(config.TABLES / "survival_by_contract.csv", index=False)

    # --- Drivers ------------------------------------------------------------
    model = drivers.fit(df)
    decile, scored = drivers.decile_table(df, model["scores"])
    model["coefficients"].to_csv(config.TABLES / "driver_odds_ratios.csv", index=False)
    decile.to_csv(config.TABLES / "risk_deciles.csv", index=False)

    # --- Segment revenue ----------------------------------------------------
    seg = (
        df.assign(
            segment=df["Contract"] + " / "
            + df["InternetService"].replace({"Fiber optic": "fibre", "DSL": "DSL", "No": "no internet"})
        )
        .groupby("segment")
        .apply(
            lambda g: pd.Series(
                {
                    "customers": len(g),
                    "churn_rate": g["churned"].mean(),
                    "monthly_revenue_lost": g.loc[g["churned"] == 1, "MonthlyCharges"].sum(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        .sort_values("monthly_revenue_lost", ascending=False)
    )
    seg.to_csv(config.TABLES / "revenue_lost_by_segment.csv", index=False)

    # --- Economics ----------------------------------------------------------
    m2m = contract_summary.set_index("segment").loc["Month-to-month"]
    one_year = contract_summary.set_index("segment").loc["One year"]
    months_gained = float(one_year["expected_months_to_horizon"] - m2m["expected_months_to_horizon"])
    mean_bill_at_risk = float(
        scored[scored["decile"] <= config.TARGETING_DECILES]["MonthlyCharges"].mean()
    )

    breakeven = economics.offer_breakeven(mean_bill_at_risk, months_gained)
    sens = economics.sensitivity(mean_bill_at_risk, months_gained)
    sens.to_csv(config.TABLES / "breakeven_sensitivity.csv", index=False)

    # The programme case is run at the breakeven rate itself plus a realistic
    # campaign save rate, so the reader sees the margin of safety rather than a
    # single optimistic number.
    options = []
    for d in (1, 2, 3, 4):
        bill_d = float(scored[scored["decile"] <= d]["MonthlyCharges"].mean())
        for offer in (0.10, 0.15, 0.20):
            options.append(
                economics.programme_case(
                    decile, d, bill_d, months_gained,
                    assumed_save_rate=0.25, offer_discount=offer,
                )
            )
    options_df = pd.DataFrame(options)
    options_df.to_csv(config.TABLES / "programme_options.csv", index=False)
    best = options_df.loc[options_df["net_value"].idxmax()].to_dict()

    case = economics.programme_case(
        decile, config.TARGETING_DECILES, mean_bill_at_risk, months_gained,
        assumed_save_rate=0.25,
    )

    clv_by_contract = {
        row["segment"]: economics.customer_lifetime_value(
            row["mean_monthly_bill"], row["expected_months_to_horizon"]
        )
        for _, row in contract_summary.iterrows()
    }

    # --- Dashboard extracts -------------------------------------------------
    scored_out = scored[[
        "customerID", "Contract", "InternetService", "PaymentMethod", "tenure",
        "tenure_band", "MonthlyCharges", "TotalCharges", "addon_count",
        "churned", "churn_probability", "decile",
    ]]
    scored_out.to_csv(config.EXTRACTS / "fct_customer_risk.csv", index=False)
    km_all.to_csv(config.EXTRACTS / "dim_tenure_hazard.csv", index=False)
    decile.to_csv(config.EXTRACTS / "agg_risk_deciles.csv", index=False)

    # --- Figures ------------------------------------------------------------
    figures.retention_curves(curves, config.FIGURES / "01-retention-by-contract.png")
    figures.hazard_profile(km_all, config.FIGURES / "02-hazard-by-tenure.png")
    figures.driver_odds(model["coefficients"], config.FIGURES / "03-churn-drivers.png")
    figures.gains_curve(decile, config.FIGURES / "04-targeting-gains.png")
    figures.revenue_bridge(seg.head(8), config.FIGURES / "05-revenue-lost-by-segment.png")
    figures.breakeven_heatmap(sens, config.FIGURES / "06-breakeven-sensitivity.png")

    metrics = {
        "data_quality": quality,
        "portfolio": {
            "customers": int(len(df)),
            "monthly_recurring_revenue": float(df["MonthlyCharges"].sum()),
            **risk,
        },
        "survival": {
            "median_tenure_overall": survival.median_survival(km_all),
            "by_contract": contract_summary.to_dict("records"),
            "logrank": lr,
            "clv_by_contract": clv_by_contract,
        },
        "model": {
            "auc_test": model["auc_test"],
            "auc_train": model["auc_train"],
            "pseudo_r2": model["pseudo_r2"],
            "n_train": model["n_train"],
            "n_test": model["n_test"],
            "top_risk_terms": model["coefficients"].head(6).to_dict("records"),
            "top_protective_terms": model["coefficients"].tail(6).to_dict("records"),
        },
        "targeting": {
            "decile_table": decile.to_dict("records"),
            "top_decile_lift": float(decile.iloc[0]["lift_vs_base"]),
        },
        "economics": {
            "months_gained_on_contract_move": months_gained,
            "mean_bill_in_target": mean_bill_at_risk,
            **breakeven,
            "programme": case,
            "programme_options": options,
            "recommended_option": best,
            "assumptions": {
                "contribution_margin": config.CONTRIBUTION_MARGIN,
                "discount_rate_annual": config.DISCOUNT_RATE_ANNUAL,
                "offer_discount": config.OFFER_DISCOUNT,
                "offer_duration_months": config.OFFER_DURATION_MONTHS,
                "offer_servicing_cost": config.OFFER_SERVICING_COST,
                "horizon_months": config.HORIZON_MONTHS,
            },
        },
    }

    with open(config.OUTPUTS / "metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2, default=float)

    print(json.dumps(metrics, indent=2, default=float)[:200])
    return metrics


if __name__ == "__main__":
    main()
