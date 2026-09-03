# Retention programme: recommendation

**To:** Commercial Director, Consumer
**From:** Lohan De Silva
**Re:** Sizing the churn problem and what to do about it

---

## The position

The book carries $456,117 of monthly recurring revenue across 7,043 accounts. In
the observation month, 1,869 accounts closed — 26.5% of customers, but **30.5% of
revenue**. Leavers were billing $74.44 a month against $61.27 for the accounts
that stayed, a 21.5% gap. Annualised, the loss is **$1.67M of revenue and $1.09M
of contribution**.

That gap between the account share and the revenue share is the finding that
should change how the programme is funded. Churn here is not a low-value-customer
problem, and treating it as one has been costing the higher-margin end of the book.

## Where it sits

The loss is not spread across the base. **Month-to-month fibre accounts are 30% of
customers and 72% of lost revenue** — $100,482 a month from a single segment.

Contract term is the dominant variable. Month-to-month accounts churn at 42.7%;
one-year at 11.3%; two-year at 2.8%. Median tenure on month-to-month is 35 months,
while neither annual contract reaches 50% attrition inside six years. The
difference is statistically unambiguous (log-rank χ² = 2,353, p < 0.001).

Price is not the driver it is assumed to be. Once contract type and product mix
are held constant, a higher monthly bill is associated with marginally *lower*
churn odds. What does drive churn is the fibre product itself: **4.38x the churn
odds** of a comparable non-fibre account, holding tenure, bill, contract and every
attached service constant. That is the largest effect in the model and it points
at product experience, not pricing.

The counterweight is attachment. Accounts with online security (0.78x) or tech
support (0.79x) attached churn significantly less. Those products are already sold
as ARPU plays; they are also the cheapest retention lever on the book.

## What to do

A scoring model built on the same data reaches AUC 0.836 on a held-out 30% sample.
Its top decile churns at 76.6% — 2.89x the base rate — and the top two deciles
hold 56% of the lost revenue while covering only 20% of customers.

**Recommendation: contact the top two risk deciles — 1,409 accounts — with a 10%
bill reduction held for twelve months, conditional on moving off month-to-month.**

| | |
|---|---|
| Programme spend | $155,222 |
| Contribution retained at a 25% save rate | $275,432 |
| **Net value** | **$120,210** |
| Return on spend | 1.77x |
| Save rate required to break even | 9.5% |

## The part that is counter-intuitive

The instinct in a retention programme is to make the offer more generous to lift
acceptance. On this book that destroys value.

The offer is paid to everyone contacted; the benefit only lands on the people who
would otherwise have left. Even in the top two deciles, 457 of 1,409 contacts are
customers who were staying anyway. Raising the discount inflates the cost across
all 1,409 while the addressable saves stay fixed at 952.

The arithmetic:

| Offer | Cost | Benefit | Net | Return |
|---|---|---|---|---|
| 10% | $155,222 | $275,432 | **$120,210** | 1.77x |
| 15% | $224,379 | $275,432 | $51,053 | 1.23x |
| 20% | $293,537 | $275,432 | **–$18,104** | 0.94x |

Moving from a 15% to a 10% offer on the *same* audience more than doubles net
value. A 20% offer is loss-making. If budget is tight, cut depth rather than
generosity — the top decile alone returns 2.02x.

## Risks to the case

The save rate is modelled, not observed; there is no campaign history in the data.
That is why the recommendation is anchored on the **9.5% breakeven** rather than
on the 25% assumption — the programme has roughly 2.5x of headroom before it stops
paying.

Contribution margin (65%) and cost of capital (10%) are supplied from outside the
data. The recommendation holds anywhere above a 50% margin.

The 4.38x fibre effect is an association, not a mechanism. It is large enough and
tight enough (95% CI 2.68–7.17) to act on, but the next step is a service-quality
read on the fibre estate, not a price change.

## Next

1. Run the top-decile cell as a controlled test with a holdout, so the save rate
   stops being an assumption. One quarter is enough at this volume.
2. Get a service-quality and fault-rate read on the fibre base. A 4.38x odds
   ratio on the largest revenue segment is worth understanding before it is
   discounted against.
3. Move online security and tech support attachment into the retention plan
   rather than leaving them purely in the ARPU plan.

---

Method, assumptions and limitations: `reports/technical-appendix.md`.
All figures reproduce from `make analysis`.
