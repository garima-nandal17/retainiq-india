# Business Requirements Document (BRD)
## RetainIQ India — Customer Decision Intelligence Platform for Budget-Constrained Retention Optimization

| Field | Value |
|---|---|
| **Document** | BRD v1.1 |
| **Project** | RetainIQ India |
| **Positioning** | Customer Decision Intelligence Platform (not a churn-prediction project) |
| **Client (fictional)** | BharatConnect — telecom operator |
| **Prepared for** | Priya Menon, Head of Retention |
| **Prepared by** | [Your name], Analytics |
| **GitHub repo / local folder** | `retainiq-india` / `RetainIQ_India` |
| **Python** | 3.13 (locked) |
| **Status** | Draft for sign-off |
| **Date** | Day 1 |

---

## 1. Executive Summary

BharatConnect spends a fixed monthly retention budget trying to keep customers who are about to leave. Today that budget is spread by intuition and broad rules ("call everyone on a month-to-month contract"), which wastes money on customers who would have stayed anyway and on customers too far gone to save.

This project is a **Customer Decision Intelligence Platform**, not a churn predictor. It builds a **decision system**: given a fixed rupee budget, it recommends *which* customers to contact, with *which* offer, to **maximize net revenue retained**. Prediction is an input; the decision is the deliverable.

The single success metric is **net revenue retained** — the rupee value of revenue saved, minus the cost of the offers used to save it — under a hard budget ceiling.

---

## 2. Business Problem & Context

Telecom in India is a low-margin, high-volume, saturated market. Acquisition is expensive and slows once a market matures, so the lever that moves profit is **retention**. A churned post-paid customer is lost ARPU every month for the remaining lifetime they would have had.

BharatConnect's current retention process has three failure modes:

1. **Spray-and-pray targeting.** Offers go to broad segments, not to the customers where a rupee of offer buys the most retained revenue.
2. **No budget logic.** There is no method that says "with ₹X this month, this is the optimal contact list." Spend is justified after the fact, not optimised before.
3. **Accuracy theatre.** Past analytics efforts reported model accuracy, a number that does not tell Priya whether the campaign made or lost money.

The business question is therefore not *"who will churn?"* but *"given a fixed budget, whom do we contact, with which offer, to retain the most revenue?"*

---

## 3. Stakeholders

| Stakeholder | Role | Interest in this project |
|---|---|---|
| **Priya Menon** | Head of Retention (primary sponsor) | Wants a defensible monthly contact list and a number she can take to finance. |
| Finance / FP&A | Budget owner | Wants proof that retention spend returns more than it costs. |
| Campaign / CRM team | Executors | Need a ranked, offer-assigned list they can action, not a model file. |
| Data / Analytics Engineering | Pipeline owners | Need trustworthy, documented, reproducible inputs. |
| Compliance / Customer experience | Guardrail | Care that we don't over-contact or mis-offer customers. |

**Primary persona:** Priya Menon. Every deliverable is judged by whether it helps Priya make a defensible spend decision and explain it upward.

---

## 4. Objectives & Success Metrics

### 4.1 Primary success metric — the North Star
**Net revenue retained `(simulation-based estimate)`** = (expected revenue saved from retained customers) − (cost of offers deployed), subject to total offer cost ≤ budget.

### 4.2 Supporting / guardrail metrics
| Metric | Why it matters | Direction |
|---|---|---|
| Save rate | Share of targeted at-risk customers retained | Higher better |
| Cost per save (₹) | Efficiency of the budget | Lower better |
| Budget utilisation | Are we using the ceiling well, not blindly? | Near, not over, 100% |
| At-risk revenue identified | Sizing of the opportunity | Context metric |
| Efficiency vs. contact-everyone baseline | The headline differentiator | ~Z% more efficient `(simulation-based)` |

### 4.3 Explicitly *not* a success metric
- **Model accuracy / AUC in isolation.** Reported for diagnostics only. A high-accuracy model that loses money is a failed decision.

---

## 5. Scope

### 5.1 In scope
- One well-understood telecom customer dataset, relabeled as BharatConnect.
- SQL feature layer, data-quality framework, survival/segmentation, hypothesis tests.
- Interpretable churn-probability engine + SHAP explanation.
- LTV / expected value, rupee profit curve, cost-sensitive threshold.
- **Budget-constrained optimizer + offer-assignment logic (the core).**
- Sensitivity / what-if, A/B experiment *design*, Streamlit decision cockpit, executive memo.

### 5.2 Out of scope (deliberate — see README "Out of Scope")
Deep learning · LLM chatbot layer · real-time streaming · growth/acquisition funnel · reinforcement learning · **uplift modeling (named as future work only)** · any second / external dataset.

> **Scope discipline statement:** one dataset fully exploited beats two half-used. Each exclusion is a tradeoff against the thesis, not an oversight.

---

## 6. Constraints

| Constraint | Detail |
|---|---|
| **Budget** | Retention spend is a fixed monthly ceiling; the optimizer must respect it as a hard constraint. |
| **Interpretability** | A retention head must trust *why* a customer is flagged before spending budget → interpretable-first modeling. |
| **Data** | Single static dataset; no live event stream; campaign cadence is monthly, not real-time. |
| **Reproducibility** | Must run from one command and pass tests (senior-engineer signal). |
| **No deep learning / no second dataset / no chatbot** | Non-negotiable stopping lines for this version. |

---

## 7. Assumptions

1. Customer-level monthly charges and tenure are a reasonable proxy for revenue and expected value.
2. Offer cost and offer-acceptance rate are **assumed parameters** (stress-tested later via sensitivity analysis), not observed truths — every downstream rupee figure is therefore labeled `(simulation-based estimate)`.
3. The historical churn label is trustworthy enough to model after a leakage scan.
4. A contacted, accepting customer is "retained" for the modeling horizon; this is a simplification validated honestly in the memo.
5. Budget, margin, and acceptance assumptions are owned by Priya/Finance and are inputs to the cockpit, not hard-coded.

---

## 8. Key Risks

| Risk | Mitigation |
|---|---|
| Data leakage inflates the model | Day 4 leakage scan + leakage-free split (Day 7). |
| Single point estimates mislead | Day 11 sensitivity + what-if simulator. |
| Estimates read as facts | Every estimate explicitly labeled `(simulation-based)`. |
| Decision can't be validated causally | Day 12 A/B experiment **design** (power, guardrails, decision rule). |
| Stakeholder distrust of a black box | Interpretable-first model + SHAP narrative for Priya. |

---

## 9. The Decision Frame (the thesis in one chain)

```
churn probability → LTV / expected value → rupee profit curve
  → cost-sensitive threshold → BUDGET-CONSTRAINED OPTIMIZER
  → sensitivity / what-if → A/B validation design
  → decision cockpit → executive memo
```

Every component is either **load-bearing** (the decision fails without it) or **supporting** (it feeds the decision's trust, timing, or validation). If a component cannot be placed on this chain, it does not ship.

---

## 10. Glossary

| Term | Meaning |
|---|---|
| **Net revenue retained** | Revenue saved by retention minus offer cost, under budget. The success metric. |
| **ARPU** | Average revenue per user. |
| **LTV / expected value** | Expected rupee value of a customer over the modeling horizon. |
| **Cost-sensitive threshold** | The contact cut-off chosen to maximize rupees, not classification accuracy. |
| **Save rate** | Retained ÷ targeted at-risk customers. |
| **Cost per save** | Budget spent ÷ customers retained. |

---

## 11. Sign-off

| Name | Role | Decision | Date |
|---|---|---|---|
| Priya Menon | Head of Retention | ☐ Approved ☐ Changes requested | |
| Finance / FP&A | Budget owner | ☐ Approved ☐ Changes requested | |

---

*This BRD was authored before any data was touched, to define retention success as **net revenue retained under budget** rather than as model accuracy.*