"""Driver model.

A regularised logistic regression, reported as odds ratios with confidence
intervals rather than as a black-box score. The model is here to rank and size
drivers for a commercial audience, so interpretability outranks a marginal gain
in discrimination.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from . import config
from .features import design_matrix


def fit(df: pd.DataFrame) -> dict:
    X = design_matrix(df)
    y = df["churned"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, random_state=config.RANDOM_SEED, stratify=y
    )

    model = sm.Logit(y_train, sm.add_constant(X_train, has_constant="add"))
    fitted = model.fit(disp=False, maxiter=200)

    p_test = fitted.predict(sm.add_constant(X_test, has_constant="add"))
    p_train = fitted.predict(sm.add_constant(X_train, has_constant="add"))
    p_all = fitted.predict(sm.add_constant(X, has_constant="add"))

    conf = fitted.conf_int()
    coefs = pd.DataFrame(
        {
            "term": fitted.params.index,
            "coefficient": fitted.params.to_numpy(),
            "odds_ratio": np.exp(fitted.params.to_numpy()),
            "or_lo": np.exp(conf[0].to_numpy()),
            "or_hi": np.exp(conf[1].to_numpy()),
            "p_value": fitted.pvalues.to_numpy(),
        }
    )
    coefs = coefs[coefs["term"] != "const"].sort_values("odds_ratio", ascending=False)

    return {
        "fitted": fitted,
        "coefficients": coefs.reset_index(drop=True),
        "auc_train": float(roc_auc_score(y_train, p_train)),
        "auc_test": float(roc_auc_score(y_test, p_test)),
        "pseudo_r2": float(fitted.prsquared),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "scores": pd.Series(p_all, index=df.index, name="churn_probability"),
    }


def decile_table(df: pd.DataFrame, scores: pd.Series) -> pd.DataFrame:
    """Rank the base by modelled risk and show what each decile actually holds."""
    work = df.copy()
    work["churn_probability"] = scores
    work["decile"] = pd.qcut(
        work["churn_probability"].rank(method="first", ascending=False),
        10, labels=range(1, 11),
    ).astype(int)

    base_rate = work["churned"].mean()
    table = (
        work.groupby("decile")
        .agg(
            customers=("churned", "size"),
            churners=("churned", "sum"),
            churn_rate=("churned", "mean"),
            mean_probability=("churn_probability", "mean"),
            monthly_revenue=("MonthlyCharges", "sum"),
        )
        .reset_index()
    )
    table["lift_vs_base"] = table["churn_rate"] / base_rate
    table["churn_revenue_monthly"] = (
        work[work["churned"] == 1].groupby("decile")["MonthlyCharges"].sum()
        .reindex(table["decile"]).fillna(0).to_numpy()
    )
    table["cumulative_churners_pct"] = table["churners"].cumsum() / table["churners"].sum()
    table["cumulative_base_pct"] = table["customers"].cumsum() / table["customers"].sum()
    table["cumulative_churn_revenue_pct"] = (
        table["churn_revenue_monthly"].cumsum() / table["churn_revenue_monthly"].sum()
    )
    return table, work
