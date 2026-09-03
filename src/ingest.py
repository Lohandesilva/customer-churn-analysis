"""Load the raw extract and apply the documented cleaning rules.

The cleaning is deliberately narrow. Anything that changes a customer's revenue
or churn status is logged rather than silently corrected.
"""

from __future__ import annotations

import pandas as pd

from . import config

SERVICE_COLUMNS = [
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies",
]


def load_raw() -> pd.DataFrame:
    if not config.SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"{config.SOURCE_FILE} not found. Run `make data` to fetch it from {config.SOURCE_URL}"
        )
    return pd.read_csv(config.SOURCE_FILE)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return the analysis frame plus a data-quality log."""
    log: dict = {"rows_in": int(len(df))}

    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # TotalCharges arrives as text and is blank for accounts that have not yet
    # been billed. Those are tenure-zero accounts, not missing data: they are
    # new connections billed in arrears, so the correct value is zero.
    total = pd.to_numeric(df["TotalCharges"].astype(str).str.strip(), errors="coerce")
    unbilled = total.isna()
    log["blank_total_charges"] = int(unbilled.sum())
    log["blank_total_charges_all_tenure_zero"] = bool((df.loc[unbilled, "tenure"] == 0).all())
    df["TotalCharges"] = total.fillna(0.0)

    log["duplicate_customer_ids"] = int(df["customerID"].duplicated().sum())
    log["negative_charges"] = int((df["MonthlyCharges"] < 0).sum())

    df["churned"] = (df["Churn"].str.strip() == "Yes").astype(int)
    df["senior"] = df["SeniorCitizen"].astype(int)

    # "No internet service" and "No phone service" are the same state as "No"
    # for every analytical purpose; collapsing them keeps the driver model from
    # spending degrees of freedom on a duplicate level.
    for col in SERVICE_COLUMNS:
        df[col] = df[col].replace(
            {"No internet service": "No", "No phone service": "No"}
        )

    log["rows_out"] = int(len(df))
    log["churn_rate"] = round(float(df["churned"].mean()), 6)
    return df, log
