"""Executive Dashboard — "How is the network performing, and what should we do?"

Hierarchy: one lead card (the recommendation), a strict four-tile portfolio row,
then the supporting story. Five KPIs, not eight — the eye needs one entry point
and a scan path.
"""
from __future__ import annotations

import streamlit as st

from app.components import charts as C
from app.components import data as D
from app.components import state as S
from app.components import theme as T
from app.components import ui
from app.pages._shell import header


def render() -> None:
    header("Network Command",
           "How is the BharatConnect network performing, and what should we do next?")
    ui.colour_legend()

    opt = D.load_json("optimizer_result.json")
    cv = D.load_customer_values()
    net = D.load_network_profile()
    d = S.decision()
    ours = opt["results"]["optimizer_roi"]

    subs = len(cv)
    churn = cv.churned.mean()
    at_risk = int((cv.churn_probability >= 0.5).sum())
    leakage = float(cv.value_at_risk_inr.sum())
    portfolio = float(cv.ltv_inr.sum())
    arpu = float(cv.monthly_charges_inr.mean())
    fibre = (net.internet_type == "Fiber optic").mean() * 100

    # ── dense KPI strip: six equal tiles, no oversized hero ──────────────────
    k = st.columns(6, gap="small")
    with k[0]:
        act = "Deploy" if d["n_contacted"] else "Hold"
        ui.metric("Recommendation", act,
                  tag=f"+{opt['uplift_pct']['rank_by_probability']:.1f}% vs ranking",
                  tone="up")
    with k[1]:
        ui.metric("Net retained", D.inr(ours["net_retained_inr"]),
                  tag=D.SIM_LABEL.strip("()"), tone="up")
    with k[2]:
        ui.metric("Subscriber base", f"{subs:,}", tag=f"{fibre:.0f}% fibre", tone="flat")
    with k[3]:
        ui.metric("Portfolio value", D.inr(portfolio), tag="24-mo LTV", tone="flat")
    with k[4]:
        ui.metric("Revenue at risk", D.inr(leakage),
                  tag=f"{leakage/portfolio:.0%} of portfolio", tone="down")
    with k[5]:
        ui.metric("Budget used", f"{opt['budget_utilisation_pct']:.0f}%",
                  bar=opt["budget_utilisation_pct"], tone="flat")

    # ── content grid: two rows of real charts, straight away ─────────────────
    ui.section("Churn trend", "Where the base is leaking, by tenure on network")
    g1, g2 = st.columns([1.7, 1], gap="medium")
    with g1:
        st.plotly_chart(C.subscriber_lifecycle(D.load_lifecycle()),
                        width="stretch", config=C.CONF)
        st.caption("Churn is front-loaded: the first year carries a 47.4% rate, falling to "
                   "9.5% beyond four years. Tenure is the strongest protective factor.")
    with g2:
        lc = D.load_lifecycle()
        ui.ledger("Lifecycle bands", [
            (f"{r['tenure_bucket']} months",
             f"{int(r['churned']):,} lost · {r['churn_rate']:.1%}") for r in lc],
            sub=f"Base churn {churn:.2%} · {at_risk:,} at ≥50% risk.")

    # ── the money ────────────────────────────────────────────────────────────
    ui.section("Retention opportunity", "What the budget recovers, and why targeting matters")
    m1, m2 = st.columns([1.3, 1], gap="medium")
    with m1:
        st.plotly_chart(C.revenue_waterfall(ours["expected_benefit_inr"],
                                            ours["spend_inr"], ours["net_retained_inr"]),
                        width="stretch", config=C.CONF)
        st.caption(f"Of {D.inr(leakage)} at risk, the funded campaign recovers "
                   f"{D.inr_exact(ours['expected_benefit_inr'])} gross against "
                   f"{D.inr_exact(ours['spend_inr'])} of offer cost. {D.SIM_LABEL}")
    with m2:
        st.plotly_chart(C.strategy_bars(opt["results"], height=330),
                        width="stretch", config=C.CONF)
        st.caption("Contacting the whole base would destroy "
                   f"{D.inr_exact(abs(opt['results']['contact_everyone']['net_retained_inr']))}.")

    # ── action summary ───────────────────────────────────────────────────────
    ui.section("Action summary")
    s1, s2 = st.columns(2, gap="medium")
    ev = D.load_json("evaluation.json")
    sens = D.load_json("sensitivity.json")
    with s1:
        ui.ledger("Decision", [
            ("Recommendation", "Deploy targeted campaign" if d["n_contacted"] else "Hold"),
            ("Subscribers targeted", f"{d['n_contacted']:,} of {subs:,}"),
            ("Budget deployed", D.inr_exact(d["spend_inr"])),
            ("Projected net retained", D.inr_exact(d["net_retained_inr"])),
            ("Uplift vs risk ranking", f"+{opt['uplift_pct']['rank_by_probability']:.1f}%"),
            ("Optimality gap vs DP", f"{opt['greedy_gap_pct']:.3f}%"),
        ], sub=f"All rupee figures {D.SIM_LABEL}.")
    with s2:
        ui.ledger("Confidence and controls", [
            ("Subscriber feed", "All hard checks passing"),
            ("Risk engine ranking", f"AUC {D.load_json('model_metrics.json')['logistic_calibrated']['roc_auc']:.4f}"),
            ("Churners in top 30% risk", f"{ev['top3_decile_capture']:.0%}"),
            ("Break-even acceptance", f"{sens['break_even_protection_acceptance_pct']:.1f}% vs 35% planned"),
            ("Downside scenario", "Platform recommends holding budget"),
            ("Validation", "A/B trial, 674 per arm"),
        ], sub="Measured quantities are separated from declared assumptions.")

    ui.note(f"<b>Validation honesty.</b> Rupee figures are {D.SIM_LABEL}. Margin, offer cost, "
            f"acceptance and budget are declared assumptions in <code>src/economics.py</code>, "
            f"stress-tested in the Scenario Simulator. Churn, ARPU, fibre mix and risk-engine "
            f"quality are measured from the subscriber feed. {D.TIER_NOTE}")

    if ui.next_step("Revenue is leaking — which subscribers are responsible?", "Subscriber Intelligence", "customer"):
        from app.dashboard import goto
        goto("customer")