# Retention dashboard — build notes

The dashboard is the operational half of this analysis: the report answers the
question once, the dashboard lets the retention team re-ask it every month.

The extracts in `extracts/` are written by `make analysis` and are the only
inputs — no manual reshaping between the pipeline and the dashboard.

**Live dashboard:** https://lohandesilva.github.io/lohan-desilva-portfolio/dashboards/churn.html

The dashboard is built and hosted directly rather than through a BI tool, so it
has no third-party account behind it and no refresh to keep alive: it reads the
same extracts this pipeline writes, and the page is a single self-contained file.

The Tableau build below is kept as a specification. It is the same data model and
the same measure definitions, so the workbook can be rebuilt in Tableau or, with
the DAX equivalents in `calculated-fields.md`, in Power BI on a Windows machine.


---

## Data model

Three flat extracts, joined on nothing — each drives a different sheet. A star
schema would be overkill for a single-entity dataset, and flattening keeps the
extract refresh to one step.

| File | Grain | Rows | Drives |
|---|---|---|---|
| `fct_customer_risk.csv` | one row per customer | 7,043 | KPI tiles, segment views, the account list |
| `agg_risk_deciles.csv` | one row per risk decile | 10 | gains curve, targeting selector |
| `dim_tenure_hazard.csv` | one row per tenure month | 73 | hazard and survival curves |

`fct_customer_risk.csv` carries the modelled `churn_probability` and `decile`
alongside the raw attributes, so the ranking the analysis is built on is the same
ranking the dashboard filters on. Scores are recomputed by the pipeline, not
inside Tableau.

## Calculated fields

Definitions live in [`calculated-fields.md`](calculated-fields.md). Two rules
worth keeping:

1. **Every rate is an aggregate ratio, never an average of ratios.** Churn rate is
   `SUM([Churned]) / COUNT([Customer Id])`, not `AVG([Churned])` over a
   pre-aggregated table. The second gives the wrong answer the moment anyone
   filters.
2. **Revenue lost is a FIXED LOD where it needs to survive filtering.** The
   "share of total loss" tile has to stay anchored to the whole book even when a
   segment filter is applied, or the share reads 100% on every selection.

## Sheets

**1. Position (KPI row).** Five tiles: MRR, accounts, churn rate on accounts,
churn rate on revenue, MRR lost. The two churn rates sit side by side deliberately
— the 26.5% / 30.5% gap is the point of the whole dashboard and it should be
visible before anyone scrolls.

**2. Where the loss sits.** Horizontal bar, contract × internet service, sorted by
revenue lost descending, with a running-total reference line. Not sorted by churn
rate: a 50% churn rate on 40 accounts is not a priority and sorting by rate makes
it look like one.

**3. Retention curves.** Line chart from `dim_tenure_hazard.csv`, one line per
contract type, tenure month on columns. Add a constant reference line at 50%.

**4. Risk deciles.** Bar of churn rate by decile with a base-rate reference line,
plus a cumulative revenue-capture line on a second sheet beneath it — **not** on a
second axis. Dual axes on different scales are how these charts get misread.

**5. Account list.** The action layer: customer ID, contract, tenure, bill,
probability, decile. Filtered to the selected deciles, sorted by monthly charges
descending so the highest-value at-risk accounts surface first. This is the sheet
the retention team actually exports.

## Dashboard layout

Fixed size, 1200 × 900. Tiled, not floating — floating layouts break on every
screen that is not the author's.

```
┌─────────────────────────────────────────────────────────┐
│  KPI row (5 tiles)                                      │
├──────────────────────────────┬──────────────────────────┤
│  Where the loss sits         │  Retention curves        │
├──────────────────────────────┴──────────────────────────┤
│  Risk deciles     │  Account list (scrollable)          │
└─────────────────────────────────────────────────────────┘
```

Filters: contract type, internet service, tenure band, risk decile. Applied to all
sheets using this data source. Keep them in a single row above the charts rather
than in a right-hand rail — a vertical filter rail costs 200px of chart width for
four controls.

## Colour

The workbook uses the same palette as the report figures so the two read as one
document:

| Role | Hex |
|---|---|
| Primary series | `#2a78d6` |
| Secondary series | `#eb6834` |
| Positive / retained | `#1baf7a` |
| At risk | `#d03b3b` |
| Grid | `#e1e0d9` |
| Body text | `#52514e` |

Set these once as a custom palette in `Preferences.tps` rather than picking them
per sheet.

## Publishing

Tableau Public only accepts extracts, not live connections, so `make analysis`
then re-upload. If the workbook is being refreshed monthly, keep the file names
stable — Tableau Public re-maps the data source on every filename change and
silently breaks calculated fields that reference the old name.

## Why not Power BI

Power BI Desktop does not run on macOS, and browser authoring in the Power BI
Service cannot produce a publicly shareable report on the free tier. The
measure definitions in `calculated-fields.md` include the DAX equivalents, so the
same model can be rebuilt in Power BI on a Windows machine without redoing the
thinking.
