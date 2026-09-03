"""Retention economics.

Turns the survival and driver output into the two numbers a commercial owner
actually decides on: what the churn is worth, and what an intervention has to
achieve to pay for itself.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def customer_lifetime_value(monthly_bill: float, expected_months: float,
                            margin: float = config.CONTRIBUTION_MARGIN,
                            monthly_rate: float = config.MONTHLY_DISCOUNT_RATE) -> float:
    """Discounted contribution over the expected remaining months on book."""
    months = np.arange(1, int(round(expected_months)) + 1)
    if len(months) == 0:
        return 0.0
    discount = 1 / (1 + monthly_rate) ** months
    return float(monthly_bill * margin * discount.sum())


def revenue_at_risk(df: pd.DataFrame) -> dict:
    churners = df[df["churned"] == 1]
    monthly = float(churners["MonthlyCharges"].sum())
    return {
        "churned_customers": int(len(churners)),
        "monthly_revenue_lost": monthly,
        "annualised_revenue_lost": monthly * 12,
        "annualised_margin_lost": monthly * 12 * config.CONTRIBUTION_MARGIN,
        "share_of_book_monthly": monthly / float(df["MonthlyCharges"].sum()),
        "mean_bill_churner": float(churners["MonthlyCharges"].mean()),
        "mean_bill_retained": float(df.loc[df["churned"] == 0, "MonthlyCharges"].mean()),
    }


def offer_breakeven(mean_bill: float, months_gained: float,
                    margin: float = config.CONTRIBUTION_MARGIN,
                    offer_discount: float | None = None) -> dict:
    """What share of contacted customers must be saved for the offer to wash.

    Cost is paid on everyone contacted; the benefit accrues only to those who
    would otherwise have left and are retained. That asymmetry is the whole
    reason targeting precision matters.
    """
    offer_discount = config.OFFER_DISCOUNT if offer_discount is None else offer_discount
    offer_cost = (
        mean_bill * offer_discount * config.OFFER_DURATION_MONTHS
        + config.OFFER_SERVICING_COST
    )
    months = np.arange(1, int(round(months_gained)) + 1)
    discount = 1 / (1 + config.MONTHLY_DISCOUNT_RATE) ** months
    margin_saved = float(mean_bill * margin * discount.sum())
    return {
        "offer_cost_per_contact": offer_cost,
        "margin_saved_per_save": margin_saved,
        "breakeven_save_rate": offer_cost / margin_saved if margin_saved else np.nan,
        "months_gained": float(months_gained),
    }


def programme_case(decile_table: pd.DataFrame, deciles: int, mean_bill: float,
                   months_gained: float, assumed_save_rate: float,
                   offer_discount: float | None = None) -> dict:
    """Size the programme over the top `deciles` of modelled risk.

    The cost line is paid on every contact, including the customers who were
    never going to leave. Precision inside the targeted group is therefore the
    dominant term in the return, not the save rate.
    """
    target = decile_table[decile_table["decile"] <= deciles]
    contacted = int(target["customers"].sum())
    churners_in_target = int(target["churners"].sum())
    revenue_in_target = float(target["churn_revenue_monthly"].sum())

    be = offer_breakeven(mean_bill, months_gained, offer_discount=offer_discount)
    saves = churners_in_target * assumed_save_rate
    cost = contacted * be["offer_cost_per_contact"]
    benefit = saves * be["margin_saved_per_save"]

    return {
        "deciles_targeted": deciles,
        "offer_discount": offer_discount if offer_discount is not None else config.OFFER_DISCOUNT,
        "customers_contacted": contacted,
        "precision_in_target": churners_in_target / contacted if contacted else np.nan,
        "wasted_contacts": contacted - churners_in_target,
        "share_of_base_contacted": contacted / float(decile_table["customers"].sum()),
        "churners_captured": churners_in_target,
        "share_of_churners_captured": churners_in_target / float(decile_table["churners"].sum()),
        "share_of_churn_revenue_captured": revenue_in_target
        / float(decile_table["churn_revenue_monthly"].sum()),
        "monthly_churn_revenue_in_target": revenue_in_target,
        "assumed_save_rate": assumed_save_rate,
        "programme_cost": cost,
        "programme_benefit": benefit,
        "net_value": benefit - cost,
        "return_on_spend": benefit / cost if cost else np.nan,
        **be,
    }


def sensitivity(mean_bill: float, months_gained: float,
                margins=(0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
                discounts=(0.05, 0.10, 0.15, 0.20, 0.25)) -> pd.DataFrame:
    """Breakeven save rate across the two assumptions the case is exposed to."""
    rows = []
    months = np.arange(1, int(round(months_gained)) + 1)
    disc = 1 / (1 + config.MONTHLY_DISCOUNT_RATE) ** months
    for margin in margins:
        for offer in discounts:
            cost = mean_bill * offer * config.OFFER_DURATION_MONTHS + config.OFFER_SERVICING_COST
            saved = mean_bill * margin * disc.sum()
            rows.append(
                {
                    "contribution_margin": margin,
                    "offer_discount": offer,
                    "breakeven_save_rate": cost / saved,
                }
            )
    return pd.DataFrame(rows)
