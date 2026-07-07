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