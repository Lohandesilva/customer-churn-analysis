# Technical appendix

Method, assumptions and the places where the analysis could be wrong.

## 1. Source and scope

IBM Telco customer churn extract: 7,043 rows, one per account, 21 fields covering
demographics, subscribed services, contract and billing terms, tenure in months,
and a churn flag for the observation month.

The extract is a **snapshot**, not a tracked panel. There is no event date, no
campaign history and no cost line. Those three absences set the boundaries of what
can honestly be concluded, and each is dealt with explicitly below.

## 2. Cleaning

Applied in `src/ingest.py`, logged to `outputs/metrics.json` under `data_quality`.

**`TotalCharges` blanks (11 rows).** The field arrives as text; eleven rows are
whitespace. All eleven have `tenure = 0`. These are new connections billed in
arrears, so the correct value is zero — not missing. The pipeline asserts the
tenure-zero condition rather than assuming it, so the assumption breaks loudly if
the source ever changes.

**Service-level collapse.** `"No internet service"` and `"No phone service"` are
distinct levels in the source but describe the same state as `"No"` for every
analytical purpose. Collapsing them stops the driver model spending degrees of
freedom on duplicate levels that are perfectly determined by `InternetService`.

**Not cleaned:** no rows dropped, no outliers winsorised, no values imputed. Zero
duplicate customer IDs, zero negative charges.

## 3. Survival estimation

`tenure` is months completed at observation; `Churn` flags accounts that closed in
the observation month. The analysis treats tenure as time on book, leavers as
events at *t* = tenure, and retained accounts as right-censored at *t* = tenure,
then estimates survival with the product-limit (Kaplan-Meier) estimator with
Greenwood variance.

**Why this reading and not the alternative.** The tempting alternative is to treat
the snapshot as a joined cohort — everyone entering at t = 0 — and read churn
directly off the tenure distribution. That is wrong here, and not conservatively
wrong: it would attribute every leaver's full tenure to a single period and
overstate early-life hazard, because short-tenure accounts are over-represented
among leavers by construction. The censoring treatment is the standard reading of
a cross-sectional subscriber extract.

**What it still cannot tell you.** Without entry dates there is no way to separate
a tenure effect from a cohort effect. If the company's acquisition mix shifted —
say it started selling harder into a worse-retaining segment three years ago —
part of what the curve reads as "risk falls with tenure" is really "older cohorts
were better". This is the single largest threat to the tenure findings and it
cannot be resolved inside this extract. It does not affect the contract comparison,
which is a between-group contrast at the same observation point.

Restricted mean survival is the area under the curve to a 60-month horizon, used
as expected months retained in the CLV and offer calculations. It is truncated
rather than extrapolated: no parametric tail is fitted, because the data does not
support one past month 72.

Group differences are tested with a multi-group log-rank test (χ² = 2,353 on 2 df,
p < 0.001), implemented directly in `src/survival.py` against the standard
observed-minus-expected construction.

## 4. Driver model

Logistic regression (statsmodels `Logit`), 70/30 stratified split, seed fixed in
`config.py`. Reported as odds ratios with 95% Wald intervals.

**Specification.** Thirteen categorical fields one-hot encoded with the first level
dropped, plus tenure, monthly charges and the senior-citizen flag as continuous
terms.

`addon_count` is excluded from the design matrix. It is the row-sum of the six
add-on dummies and therefore perfectly collinear with them; including it produced
infinite standard errors on every add-on term. It is retained in the analysis
frame for description and dashboarding. This was caught by inspecting the
confidence intervals, which is the reason they are reported at all.

**Performance.** AUC 0.836 on the holdout, 0.850 in-sample, McFadden pseudo-R²
0.290. The 0.014 train/test gap is small enough that the model is not memorising.

**Why logistic and not a gradient-boosted model.** A tuned GBM would likely add a
point or two of AUC. It would not change the recommendation, because the decision
depends on the *ranking* of the top two deciles and on effect sizes a commercial
owner can argue with. An odds ratio with an interval on it survives a steering
committee; a SHAP plot generally does not.

**Interpretation limit.** These are associations under a specific covariate set.
The 4.38x fibre coefficient is conditional on everything else in the model; it is
not an estimate of what would happen if a customer were moved onto fibre. Reading
it causally would be a mistake, which is why the recommendation asks for a
service-quality investigation rather than a product change.

## 5. Economics

Set in `src/config.py`, swept in `src/economics.py`.

| Assumption | Value | Basis |
|---|---|---|
| Contribution margin | 65% | Published telecom gross margin on recurring service revenue |
| Cost of capital | 10% annual | Standard corporate discount rate; applied monthly |
| CLV horizon | 60 months | Matches the restricted-mean truncation |
| Offer duration | 12 months | Typical contract-conversion offer |
| Servicing cost | $12 per contact | Outbound contact and fulfilment |
| Save rate | 25% | **Modelled input, not observed** |

CLV is discounted contribution over expected remaining months:
Σ (bill × margin) / (1 + r)^t.

The programme case charges the offer against **every contact** and credits the
benefit only to saved leavers. That asymmetry is the mechanism behind the
recommendation: precision inside the targeted group dominates the return, and
raising the discount inflates the cost base without expanding the addressable
saves.

Breakeven save rate = offer cost per contact ÷ discounted margin per save. The
sensitivity grid (`outputs/tables/breakeven_sensitivity.csv`) sweeps contribution
margin 50–75% against offer discount 5–25%. The recommendation holds across the
whole margin range.

## 6. Known limitations

1. **No campaign history.** The save rate is an input. The case is therefore
   anchored on the breakeven rate (9.5%), which is a property of the data and the
   offer design, not of the assumption.
2. **No cost lines.** Margin is supplied externally. Mitigated by the sweep.
3. **Single period.** No seasonality, no trend, no way to test whether the churn
   rate is rising or falling.
4. **Cohort confounding in the tenure curve.** See §3.
5. **No competitor or pricing context.** A 4.38x fibre effect could be a service
   problem or a competitive one; the data cannot distinguish them.
6. **Association, not causation, throughout.** Nothing here is an experiment. The
   first recommendation is to run one.

## 7. Reproducibility

Random seed fixed at 20260214. `make analysis` regenerates every table, figure and
number in the report pack from the raw extract. `outputs/metrics.json` is the
single source for every figure quoted in the README and executive summary — none
of them are typed by hand.
