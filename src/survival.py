"""Tenure and survival work.

The extract is a single snapshot: `tenure` is months completed at observation
and `Churn` flags the accounts that left in the observation month. Treating
tenure as time-on-book, churners as events at t = tenure and retained accounts
as right-censored at t = tenure gives a Kaplan-Meier estimate of the retention
curve. That is the standard reading of this extract and it is stated as an
assumption in the technical appendix, because the alternative -- treating the
snapshot as a cohort -- would overstate early-life churn.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def kaplan_meier(durations: pd.Series, events: pd.Series) -> pd.DataFrame:
    """Product-limit estimator with Greenwood standard errors."""
    df = pd.DataFrame({"t": durations.astype(int), "e": events.astype(int)})
    grid = np.sort(df["t"].unique())

    rows = []
    survival = 1.0
    greenwood = 0.0
    for t in grid:
        at_risk = int((df["t"] >= t).sum())
        events_t = int(df.loc[df["t"] == t, "e"].sum())
        if at_risk == 0:
            continue
        hazard = events_t / at_risk
        survival *= 1 - hazard
        if at_risk > events_t:
            greenwood += events_t / (at_risk * (at_risk - events_t))
        se = survival * np.sqrt(greenwood)
        rows.append(
            {
                "tenure_month": int(t),
                "at_risk": at_risk,
                "events": events_t,
                "hazard": hazard,
                "survival": survival,
                "survival_se": se,
                "survival_lo": max(0.0, survival - 1.96 * se),
                "survival_hi": min(1.0, survival + 1.96 * se),
            }
        )
    return pd.DataFrame(rows)


def restricted_mean_months(km: pd.DataFrame, horizon: int) -> float:
    """Area under the survival curve to `horizon` -- expected months retained."""
    curve = km[km["tenure_month"] <= horizon]
    t = curve["tenure_month"].to_numpy()
    s = curve["survival"].to_numpy()
    if len(t) == 0:
        return 0.0
    t = np.concatenate([[0], t, [horizon]])
    s = np.concatenate([[1.0], s, [s[-1]]])
    widths = np.diff(t)
    heights = s[:-1]
    return float((widths * heights).sum())


def median_survival(km: pd.DataFrame) -> float | None:
    below = km[km["survival"] <= 0.5]
    return float(below["tenure_month"].iloc[0]) if len(below) else None


def curves_by_group(df: pd.DataFrame, group_col: str, horizon: int) -> tuple[dict, pd.DataFrame]:
    curves, summary = {}, []
    for name, part in df.groupby(group_col, observed=True):
        km = kaplan_meier(part["tenure"], part["churned"])
        curves[str(name)] = km
        summary.append(
            {
                "segment": str(name),
                "customers": int(len(part)),
                "churn_rate": float(part["churned"].mean()),
                "median_tenure_months": median_survival(km),
                "expected_months_to_horizon": restricted_mean_months(km, horizon),
                "mean_monthly_bill": float(part["MonthlyCharges"].mean()),
            }
        )
    return curves, pd.DataFrame(summary).sort_values("churn_rate", ascending=False)


def logrank(df: pd.DataFrame, group_col: str) -> dict:
    """Multi-group log-rank test on the tenure curves."""
    from scipy import stats

    groups = sorted(df[group_col].dropna().unique().tolist())
    k = len(groups)
    times = np.sort(df.loc[df["churned"] == 1, "tenure"].unique())

    observed = np.zeros(k)
    expected = np.zeros(k)
    variance = np.zeros((k, k))

    for t in times:
        n_j = np.array([int(((df[group_col] == g) & (df["tenure"] >= t)).sum()) for g in groups])
        d_j = np.array(
            [int(((df[group_col] == g) & (df["tenure"] == t) & (df["churned"] == 1)).sum())
             for g in groups]
        )
        n, d = n_j.sum(), d_j.sum()
        if n <= 1 or d == 0:
            continue
        e_j = n_j * d / n
        observed += d_j
        expected += e_j
        factor = d * (n - d) / (n * n * (n - 1))
        for i in range(k):
            for j in range(k):
                variance[i, j] += factor * (n * (n_j[i] if i == j else 0) - n_j[i] * n_j[j])

    diff = (observed - expected)[:-1]
    cov = variance[:-1, :-1]
    stat = float(diff @ np.linalg.pinv(cov) @ diff)
    dof = k - 1
    return {
        "statistic": stat,
        "degrees_of_freedom": dof,
        "p_value": float(stats.chi2.sf(stat, dof)),
        "groups": groups,
    }
