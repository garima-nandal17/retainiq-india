# A/B Experiment Design — Validating the RetainIQ Retention Campaign

*Day 12 deliverable. How BharatConnect would prove — causally — that the
optimizer's contact list actually saves customers, rather than merely correlating
with them. Every projection so far is `(simulation-based)`; **this is the design
that would replace assumption with measurement.***

---

## 1. Why we need this
The Day-10 optimizer projects ₹63,133 net revenue retained under a ₹1,00,000
budget `(simulation-based)`. That figure rests on a **declared** acceptance rate
(35%), not a measured one. Worse, the customers we contact are — by construction
— the ones most likely to churn. If we simply observe them and compare to
everyone else, we will confuse *targeting* with *treatment effect*.

Only randomisation **within the eligible population** can isolate the causal
effect of contacting a customer.

## 2. Hypothesis
- **H₀:** Contacting an at-risk customer with a retention offer does not change
  their probability of churning within 90 days.
- **H₁:** Contacting an at-risk customer reduces their 90-day churn probability.
- **Primary metric:** 90-day churn rate (binary, per customer).
- **Decision metric (business):** net revenue retained per rupee spent.

## 3. Unit, population, and assignment
- **Unit of randomisation:** the customer (no interference — one customer's offer
  doesn't affect another's churn; no household clustering available in this data).
- **Eligible population:** the customers the optimizer *would* contact under the
  live budget — **1,349 customers** (the Day-10 contact list). Randomising outside
  this pool would answer a question we don't need.
- **Assignment:** 50/50 stratified randomisation, **stratified by `risk_segment`
  and `offer` tier**, so both arms carry the same risk and offer mix.
  - **Treatment (n≈674):** receives the optimizer-assigned offer.
  - **Control (n≈674):** receives no contact (business as usual).

**Ethical / commercial note.** Withholding contact from at-risk customers has a
real expected cost — approximately half the projected benefit for one cycle. This
is the price of knowing whether the campaign works at all, and it is cheaper than
scaling an ineffective campaign. It should be an explicit, time-boxed decision by
Priya, not a silent default.

## 4. Power analysis (computed, not asserted)
Baseline: expected 90-day churn among *targeted* customers = **0.600** (mean
predicted churn probability across the contact list).
α = 0.05 (two-sided), power = 0.80, equal allocation.

| Relative churn reduction | Treatment churn | Required n **per arm** | Feasible with 674/arm? |
|---|---|---|---|
| 5%  | 0.570 | 4,229 | ✗ underpowered |
| 10% | 0.540 | 1,067 | ✗ underpowered |
| 15% | 0.510 | 477 | ✓ |
| 20% | 0.480 | 270 | ✓ |
| 30% | 0.420 | 120 | ✓ |

> **Minimum detectable effect (MDE) at 674 per arm: a 12.6% relative reduction in
> churn.** This is the design's honest limit — a single monthly cohort **cannot**
> detect a 10% improvement. Our modelled acceptance rate (35%) implies a far larger
> effect, so if the model's premise is right, this test will see it.

**If a smaller effect matters:** pool 2–3 monthly cohorts (n≈1,350–2,000 per arm)
before reading the result, or accept power = 0.7. Do **not** peek and stop early
(see §7).

## 5. Guardrail metrics
A campaign can "win" on churn and still damage the business. We monitor:

| Guardrail | Why | Stop / investigate if |
|---|---|---|
| Revenue per user (ARPU) in treatment | Discounts can save the customer and lose the revenue | ARPU drop > 5% vs control |
| Cost per save | The optimizer's whole premise | > ₹350 (≈ 3× baseline) |
| Complaint / opt-out rate | Contact fatigue | > 2× control |
| Support-ticket volume | Operational load | > 1.5× control |

**Net revenue retained is the North Star**, but churn rate is the *primary* metric
because it is the cleanest, highest-powered measurement; revenue is noisier.

## 6. Decision rule (pre-registered, before data is seen)
- **Ship** if: churn reduction is statistically significant (p < 0.05, two-proportion
  z-test) **and** the 95% CI lower bound on net revenue retained is > ₹0 **and** no
  guardrail is breached.
- **Iterate** if: the direction is right but not significant, and no guardrail is
  breached → extend by one cohort (pre-committed), do not re-test repeatedly.
- **Kill** if: point estimate favours control, or any guardrail breached.

Analysis: two-proportion z-test on churn; difference-in-means with bootstrap CI on
net revenue retained; report **effect size (absolute pp and relative %) alongside
p-values** — the same discipline as Day 6.

## 7. Threats to validity and how we handle them
- **Peeking / optional stopping.** Fixed sample size, single read at 90 days. If
  interim monitoring is required, use an alpha-spending (O'Brien-Fleming) boundary.
- **Selection bias.** Randomisation happens *inside* the optimizer's eligible pool,
  so the estimate is a **CATE** (effect on the targeted), not an ATE on all
  customers. That is the population the decision applies to — stated, not hidden.
- **Non-compliance.** Some treated customers won't answer the call. Report both
  **ITT** (primary, unbiased) and a CACE/LATE estimate via instrumental variables
  using assignment as the instrument.
- **Spillover.** Assumed negligible (no referral or household structure in this
  data). Documented as an assumption, not a proof.
- **Novelty / seasonality.** One 90-day window may catch a billing-cycle artefact;
  a second cohort in a different month is the cheapest check.

## 8. What this experiment unlocks — and what it deliberately defers
The test measures whether contacting helps *on average* among the targeted. It
does **not** identify **persuadables** — customers who stay *because* they were
contacted, versus those who would have stayed anyway (and "sleeping dogs" whom
contact actively annoys).

That is **uplift modeling**, and it requires exactly the randomised data this
experiment generates. It remains **future work by design**: you cannot honestly
build an uplift model before you have run the trial that produces its training
data. This experiment is the prerequisite, not an afterthought.

---

*Assumptions and their sources: `src/economics.py`. Sensitivity of the projection
to those assumptions: `reports/sensitivity.json` — the break-even acceptance rate
is ≈12.2%, so the campaign has roughly a 3× cushion under our 35% assumption
`(simulation-based)`.*