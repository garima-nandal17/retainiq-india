# STAR Stories — RetainIQ India


---

## STAR #1 — Data-quality framework & leakage defence (Day 4 milestone: *foundation locked*)

**Situation.** RetainIQ India would decide how to spend a fixed retention budget
using a churn model. If the underlying data were silently wrong or the model
leaked the target, every downstream rupee decision would be built on sand — and
past churn projects had reported only accuracy, never data trust.

**Task.** Replace ad-hoc validation with a real, named data-quality framework and
prove the feature layer was free of target leakage, before any modeling.

**Action.** I built a 5-dimension DQ framework (freshness, completeness,
uniqueness, consistency, accuracy) with 47 automated checks, each emitting a
pass/fail plus a logged metric, and tagged **hard** (blocking) vs **soft**
(informational) — the dbt `error`/`warn` pattern. I added a leakage scan that
flags any feature whose absolute correlation with the target exceeds 0.95, plus
a unit test that plants a leaky column and confirms the scan catches it. When one
consistency rule (`total ≈ tenure × monthly`) held for only 80.5% of rows, I
diagnosed it as a *wrong assumption* (the monthly rate evolves over tenure) and
marked it soft rather than corrupting the data to force a pass.

**Result.** 46/46 hard checks pass; the leakage scan's worst predictor sits at
|corr| = 0.405, well clear of the alarm; the 11 tenure-0 `total_charges` nulls
are kept honest at the data layer and imputed only at model-training time. The
foundation is provably trustworthy, and the framework doubles as an
analytics-engineering talking point ("I don't fake freshness on a static dataset —
I implement the mechanism and document the limitation").

**One-line résumé version.** *"Built a 5-dimension data-quality framework (47
checks, hard/soft severity) with an automated target-leakage scan and tests,
locking a provably trustworthy feature layer before modeling."*
STAR #2 — Evaluation, explainability & the business read (Day 8 milestone: modeling locked)

Situation. The churn engine produced calibrated probabilities, but a probability nobody understands or trusts can't justify spending a retention budget — and accuracy on a 26.5%-churn base is misleading (predicting "nobody churns" scores ~73%).

Task. Evaluate the model beyond accuracy, explain why it flags a customer in language Priya (Head of Retention) can act on, and translate both into a targeting recommendation.

Action. I evaluated on ranking and probability quality rather than accuracy — ROC-AUC 0.844, PR-AUC 0.660, a reliability curve (max calibration gap 0.055), a precision/recall/F1 threshold sweep, and a decile-lift gains table. I explained drivers two ways that agree: logistic odds ratios and SHAP (explaining the base logistic, valid because calibration is a monotonic transform). I then wrote a stakeholder "business read" — and, importantly, flagged an honest caveat: total_charges shows a churn-raising coefficient only conditional on tenure (a collinearity effect), so I anchored the narrative on the drivers all methods agree on (tenure, contract, protection adoption) rather than over-reading any single collinear coefficient.

Result. A defensible, explainable model with a concrete targeting rule: the top 3 risk deciles (30% of customers) capture 65% of all churners, and lowering the threshold to 0.30 raises recall to 76% — with the exact operating point deferred to the Day 9-10 profit curve. The model is locked; explanation and evaluation are reproducible artifacts, not slideware.

One-line résumé version. "Evaluated a churn model on ranking + calibration (AUC 0.844, calibration gap 0.055), explained it with SHAP and odds ratios, and translated it into a decile-based targeting rule capturing 65% of churners in the top 30%."
STAR #3 — Budget-constrained retention optimizer (Day 10 milestone: thesis proven)

Situation. BharatConnect's retention team had a churn ranking but a fixed monthly budget. A churn score alone doesn't say whom to call: contacting every customer the model flags would cost more than it saves, because the most at-risk customers are not always the most valuable to save.

Task. Turn calibrated probabilities into a decision — whom to contact, with which offer, under a hard budget — and prove the decision beats the obvious alternatives.

Action. I attached money to every customer: a 24-month LTV discounted by their contract's actual Kaplan-Meier survival curve, giving expected value at risk. I built a rupee profit curve, then discovered the key insight — a single global threshold can never be optimal, because a customer's break-even churn probability depends on their LTV and ranged from 0.22 to 1.96 across the base. So I formulated targeting as a 0/1 knapsack: choose customers and offers maximising net revenue retained subject to the budget, solved greedily by benefit-to-cost ratio, and verified the greedy solution against a dynamic-programming bound (gap 0.000%). Critically, I centralised every rupee assumption in one auditable module and rejected an initial ₹500 offer-cost assumption after measurement showed it made 0 of 7,043 customers profitable to contact.

Result. Under a binding ₹1,00,000 budget the optimizer contacts 1,349 customers with a tailored offer mix, using 100% of budget and retaining ₹63,133 net — 23.9% more than ranking by churn probability alone (the typical churn-project approach), and 205% better than contacting everyone, which actually loses ₹60,009 (simulation-based). Sensitivity analysis showed the campaign survives down to a 12.2% acceptance rate — a ~3× cushion — while the pessimistic scenario correctly recommends contacting nobody.

One-line résumé version. "Built a budget-constrained retention optimizer (0/1 knapsack, DP-verified) that assigns offers to maximise net revenue retained — 23.9% more efficient than probability-ranked targeting under a fixed budget (simulation-based)."