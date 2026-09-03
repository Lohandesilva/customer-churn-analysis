"""Derived fields used by the survival, driver and economics work."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ingest import SERVICE_COLUMNS

TENURE_BANDS = [(0, 6), (6, 12), (12, 24), (24, 48), (48, 72), (72, 1_000)]
TENURE_LABELS = ["0-6m", "6-12m", "12-24m", "24-48m", "48-72m", "72m+"]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["tenure_band"] = pd.cut(
        df["tenure"],
        bins=[b[0] for b in TENURE_BANDS] + [TENURE_BANDS[-1][1]],
        labels=TENURE_LABELS,
        right=False,
        include_lowest=True,
    )

    # Count of paid add-ons attached to the line. Attachment is the lever the
    # commercial team actually controls, so it is worth measuring directly.
    addons = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
              "StreamingTV", "StreamingMovies"]
    df["addon_count"] = (df[addons] == "Yes").sum(axis=1)
    df["has_fibre"] = (df["InternetService"] == "Fiber optic").astype(int)
    df["no_internet"] = (df["InternetService"] == "No").astype(int)
    df["autopay"] = df["PaymentMethod"].str.contains("automatic").astype(int)
    df["electronic_check"] = (df["PaymentMethod"] == "Electronic check").astype(int)
    df["paperless"] = (df["PaperlessBilling"] == "Yes").astype(int)
    df["month_to_month"] = (df["Contract"] == "Month-to-month").astype(int)

    # Average revenue actually realised per month of tenure, which diverges from
    # the current bill when a customer has moved plans.
    df["arpu_realised"] = np.where(
        df["tenure"] > 0, df["TotalCharges"] / df["tenure"], df["MonthlyCharges"]
    )
    df["bill_vs_realised"] = df["MonthlyCharges"] - df["arpu_realised"]

    df["services_total"] = (df[SERVICE_COLUMNS] == "Yes").sum(axis=1)
    return df


MODEL_CATEGORICALS = [
    "Contract", "InternetService", "PaymentMethod", "OnlineSecurity",
    "TechSupport", "OnlineBackup", "DeviceProtection", "StreamingTV",
    "StreamingMovies", "MultipleLines", "PaperlessBilling", "Partner",
    "Dependents",
]
# `addon_count` is the row-sum of the six add-on dummies and is therefore
# perfectly collinear with them. It stays in the frame for description and
# dashboarding but is kept out of the design matrix.
MODEL_NUMERICS = ["tenure", "MonthlyCharges", "senior"]


def design_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encoded matrix with an explicit, stable reference level."""
    X = pd.get_dummies(
        df[MODEL_CATEGORICALS], drop_first=True, dtype=float
    )
    X = pd.concat([df[MODEL_NUMERICS].astype(float), X], axis=1)
    X.columns = [c.replace(" ", "_").replace("(", "").replace(")", "") for c in X.columns]
    return X
