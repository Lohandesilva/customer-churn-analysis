# Source data

Not committed. `make data` fetches it.

**IBM Telco customer churn** — 7,043 accounts, 21 fields, one row per customer.
Published by IBM as a sample dataset for churn modelling and widely used as a
benchmark for subscription retention work.

- Source: https://github.com/IBM/telco-customer-churn-on-icp4d
- File: `Telco-Customer-Churn.csv` → saved here as `telco_customer_churn.csv`
- Licence: sample data published by IBM for public use

## Known quirks

`TotalCharges` is typed as text and is blank on 11 rows. All 11 are tenure-zero
accounts billed in arrears; the pipeline sets them to zero and asserts the
tenure-zero condition rather than assuming it.

`MultipleLines`, `OnlineSecurity` and the other service fields carry a third level
("No phone service" / "No internet service") that is analytically identical to
"No". The pipeline collapses it.
