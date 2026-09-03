"""Project configuration and the commercial assumptions the analysis rests on.

Every assumption that is not observable in the data lives here, with a stated
basis. Nothing downstream hard-codes a number.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"
EXTRACTS = ROOT / "dashboard" / "extracts"

SOURCE_FILE = RAW / "telco_customer_churn.csv"
SOURCE_URL = (
    "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/"
    "master/data/Telco-Customer-Churn.csv"
)

RANDOM_SEED = 20260214

# --- Commercial assumptions -------------------------------------------------
# The dataset carries revenue but no cost lines, so margin and cost of capital
# have to be supplied. Both are set to conservative published telecom norms and
# both are swept in the sensitivity grid in economics.py, so no conclusion in
# the report depends on a single point estimate.

CONTRIBUTION_MARGIN = 0.65     # gross margin on recurring service revenue
DISCOUNT_RATE_ANNUAL = 0.10    # cost of capital used to discount future margin
HORIZON_MONTHS = 60            # CLV truncation horizon

# Retention offer modelled in the recommendation: a monthly bill reduction held
# for twelve months, in exchange for the customer moving off month-to-month.
OFFER_DISCOUNT = 0.15          # share of monthly bill given away
OFFER_DURATION_MONTHS = 12
OFFER_SERVICING_COST = 12.00   # one-off outbound contact and fulfilment cost

# Share of the base the retention programme is sized to contact each month.
TARGETING_DECILES = 2

MONTHLY_DISCOUNT_RATE = (1 + DISCOUNT_RATE_ANNUAL) ** (1 / 12) - 1
