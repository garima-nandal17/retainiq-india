# Model Business Read — for Priya Menon (Head of Retention)

*Day 8 deliverable. Plain-English translation of the churn engine: what it does,
what to trust, what drives churn, and what to do about it. All impact figures are
`(simulation-based estimate)`.*

## What the model gives you
A **calibrated churn probability** for every customer — not a yes/no label. Two
properties make it usable for budget decisions:
- **It ranks risk well.** ROC-AUC **0.844**: given a churner and a non-churner,
  the model scores the churner higher 84% of the time.
- **The probabilities are honest.** The reliability curve tracks the diagonal
  (max gap 0.055), so "18% risk" really means roughly 18 in 100 — which is what
  lets us treat a probability as a rupee weight later.

## What drives churn — plain English
From SHAP and the logistic coefficients, corroborated by the Day-6 hypothesis
tests. "Odds ×N" = multiplies a customer's churn odds, holding other factors fixed.

**Pushes churn UP**
- **Fiber-optic internet** (odds ×1.9) and **month-to-month contracts** (×1.7) —
  premium, low-commitment customers leave most.
- **Paperless billing / electronic-check payers** — a consistent friction signal.
- **Early tenure** — the first year is by far the most fragile (Day-5 survival:
  month-to-month median life ≈ 35 months).

**Pulls churn DOWN**
- **Longer tenure** — the single strongest protective factor (odds ×0.25).
- **Two-year contracts** (×0.43) and **no-frills phone-only plans** (×0.44).
- **Protection add-ons** — every extra protection service lowers odds (×0.51);
  Day-5 showed OnlineSecurity / TechSupport roughly *halve* churn.

## One honest caveat
These are **conditional** effects. Some inputs are correlated (e.g. `total_charges`
rises with tenure), so an individual coefficient like "total charges ×1.9" should
**not** be read in isolation — it's the effect *after* tenure is already accounted
for. The robust, decision-grade story is the one all three methods agree on:
**tenure, contract type, and protection adoption**. Treat the rest as supporting
colour, not standalone levers.

## What to do with it
- **Concentrate the budget on the top of the risk ranking.** The **top 3 risk
  deciles (30% of customers) contain 65% of all churners** — spraying contact
  across everyone wastes most of the spend.
- **The right cut-off is not 50%.** A retention campaign should tolerate some
  false alarms to catch more real churners; at a 0.30 threshold recall rises to
  **76%**. The *exact* operating point isn't guessed — the **rupee profit curve
  (Day 9-10)** sets it by balancing offer cost against revenue saved.
- **Lead with protection-bundle offers** for at-risk fiber / month-to-month
  customers — it's the lever the data most consistently rewards.

*Next: attach rupees (LTV + profit curve, Day 9) and turn this ranking into a
budget-constrained contact list (optimizer, Day 10).*