# Calculated fields

Tableau syntax, with the DAX equivalent where the two differ in a way that
matters. Field names match the column headers in `extracts/`.

---

## Core rates

**Churn rate (accounts)**

```
SUM([Churned]) / COUNT([Customerid])
```
```dax
Churn Rate Accounts = DIVIDE(SUM(fct[churned]), COUNTROWS(fct))
```

An aggregate ratio, not `AVG([Churned])`. The average-of-averages form gives the
right answer only when every group is the same size, which is never true after a
filter is applied.

**Churn rate (revenue)**

```
SUM(IF [Churned] = 1 THEN [Monthlycharges] END) / SUM([Monthlycharges])
```
```dax
Churn Rate Revenue =
DIVIDE(
    CALCULATE(SUM(fct[MonthlyCharges]), fct[churned] = 1),
    SUM(fct[MonthlyCharges])
)
```

The pair of these two is the headline. Showing either one alone hides the finding.

**Revenue gap (leaver premium)**

```
AVG(IF [Churned] = 1 THEN [Monthlycharges] END)
/ AVG(IF [Churned] = 0 THEN [Monthlycharges] END) - 1
```

---

## Revenue at risk

**MRR lost**

```
SUM(IF [Churned] = 1 THEN [Monthlycharges] END)
```

**Share of total loss** — must survive filtering

```
SUM(IF [Churned] = 1 THEN [Monthlycharges] END)
/ { FIXED : SUM(IF [Churned] = 1 THEN [Monthlycharges] END) }
```
```dax
Share Of Total Loss =
DIVIDE(
    CALCULATE(SUM(fct[MonthlyCharges]), fct[churned] = 1),
    CALCULATE(SUM(fct[MonthlyCharges]), fct[churned] = 1, ALL(fct))
)
```

The `FIXED` LOD (and `ALL()` in DAX) anchors the denominator to the whole book.
Without it the share reads 100% for whatever segment is selected, which looks
plausible and is wrong.

**Annualised loss**

```
[MRR Lost] * 12
```

---

## Targeting

**Cumulative revenue captured** — for the gains curve

```
RUNNING_SUM(SUM([Churn Revenue Monthly]))
/ TOTAL(SUM([Churn Revenue Monthly]))
```

Table calculation. Set *Compute Using* to `Decile`, ascending. Leaving it on
*Table (across)* is the usual cause of a gains curve that does not end at 100%.

**Lift vs base rate**

```
[Churn Rate Accounts] / { FIXED : SUM([Churned]) / COUNT([Customerid]) }
```

**Precision in selection** — share of contacts who would actually have left

```
SUM([Churned]) / COUNT([Customerid])
```

Same expression as churn rate, different name because it means something
different in the targeting context: it is the share of the offer budget that is
not wasted.

**Wasted contacts**

```
COUNT([Customerid]) - SUM([Churned])
```

---

## Economics

Parameters: `Contribution Margin` (default 0.65), `Offer Discount` (default 0.10),
`Offer Duration Months` (default 12), `Servicing Cost` (default 12).

**Offer cost per contact**

```
AVG([Monthlycharges]) * [Offer Discount] * [Offer Duration Months]
+ [Servicing Cost]
```

**Programme cost**

```
COUNT([Customerid]) * [Offer Cost Per Contact]
```

Charged on every contact — including the customers who were staying anyway. This
is the term that makes generous offers lose money, so it should not be quietly
netted off.

**Margin retained per save**

```
AVG([Monthlycharges]) * [Contribution Margin] * [Months Gained]
```

`Months Gained` is a parameter set from the pipeline output (23.8 months, the
difference in restricted mean survival between month-to-month and one-year). It is
not recomputed in Tableau — a survival estimate is not something to reimplement in
a calculated field.

**Breakeven save rate**

```
[Offer Cost Per Contact] / [Margin Retained Per Save]
```

Put this on the dashboard next to the assumed save rate. The distance between the
two is the margin of safety, and it is the number that should drive the decision.

---

## Tenure

**Tenure band** — pre-computed in the extract, not derived in Tableau, so the
bucket definition cannot drift between the report and the dashboard.

**Survival** — read directly from `dim_tenure_hazard.csv`. Kaplan-Meier is
computed in the pipeline. A window function over a filtered table would give a
different curve depending on the filter state, which is not what a survival
estimate means.
