"""Customer Intelligence — "Which subscribers are leaving the network, and why?"

A customer analytics workspace: composition, risk and value distribution,
behavioural drivers, a segment table, and archetype profile cards built from the
real base. Validation evidence sits in an expander, one click away.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components import charts as C
from app.components import data as D
from app.components import theme as T
from app.components import ui
from app.pages._shell import header


def render() -> None:
    header("Customer Intelligence",
           "Which subscribers are leaving the network, and why?", banner=False)

    cv = D.load_customer_values()
    net = D.load_network_profile()
    ev = D.load_json("evaluation.json")
    sh = D.load_json("shap_drivers.json")
    mm = D.load_json("model_metrics.json")
    prof = D.load_json("profit_curve.json")
    contacts = D.load_contact_list()

    base = cv.merge(net[["customer_id", "internet_type"]], on="customer_id", how="left")

    # ── composition ──────────────────────────────────────────────────────────
    ui.section("Base composition", "Contract mix and access network across the SIM base")
    d1, d2, d3 = st.columns([1, 1, 1.5], gap="medium")
    with d1:
        mix = cv.contract_type.value_counts()
        st.plotly_chart(C.donut([D.CONTRACT_TIER.get(k, k) for k in mix.index], mix.values,
                                f"{len(cv):,}", "SUBSCRIBERS",
                                colors=T.CAT[:3]),
                        width="stretch", config=C.CONF)
        st.caption("**Contract mix.** Rolling tiers carry the churn.")
    with d2:
        acc = net.internet_type.replace({"No": "Voice only", "Fiber optic": "Fibre"})
        vc = acc.value_counts()
        st.plotly_chart(C.donut(vc.index.tolist(), vc.values,
                                f"{(net.internet_type == 'Fiber optic').mean():.0%}", "FIBRE",
                                colors=T.CAT[:3]),
                        width="stretch", config=C.CONF)
        st.caption("**Internet mix.** Fibre churns hardest.")
    with d3:
        seg = (base.groupby(["contract_type", "internet_type"], as_index=False)
                   .agg(subscribers=("customer_id", "size"),
                        churn=("churned", "mean"),
                        arpu=("monthly_charges_inr", "mean"),
                        at_risk=("value_at_risk_inr", "sum"))
                   .sort_values("at_risk", ascending=False))
        seg["contract_type"] = seg.contract_type.map(lambda k: D.CONTRACT_TIER.get(k, k))
        st.dataframe(seg, width="stretch", hide_index=True, height=290,
                     column_config={
                         "contract_type": "Contract tier",
                         "internet_type": "Access",
                         "subscribers": st.column_config.NumberColumn("Subscribers",
                                                                      format="%d"),
                         "churn": st.column_config.NumberColumn("Churn", format="%.1f%%"),
                         "arpu": st.column_config.NumberColumn("ARPU", format="₹%.0f"),
                         "at_risk": st.column_config.NumberColumn("Revenue at risk",
                                                                  format="₹%.0f"),
                     })
        st.caption("Segment matrix, ranked by revenue at risk. Churn shown as a rate "
                   f"(0–1). {D.SIM_LABEL} for the rupee column.")

    # ── risk and value ───────────────────────────────────────────────────────
    ui.section("Risk and value distribution", "Where the revenue actually leaks")
    r1, r2 = st.columns([1.3, 1], gap="medium")
    with r1:
        st.plotly_chart(C.leakage_treemap(cv), width="stretch", config=C.CONF)
        st.caption(f"Revenue leakage by contract tier and risk band — area is rupees at "
                   f"risk. {D.SIM_LABEL}")
    with r2:
        st.plotly_chart(C.arpu_by_risk(cv), width="stretch", config=C.CONF)
        st.caption("High-risk subscribers pay **more**, not less. The leakage is "
                   "concentrated in premium ARPU — which is what makes targeting pay.")

    # ── archetype profile cards ──────────────────────────────────────────────
    ui.section("Subscriber archetypes", "The three segments carrying the most exposure")
    arch = (base.groupby(["risk_segment", "customer_value_segment"], as_index=False)
                .agg(n=("customer_id", "size"), churn=("churn_probability", "mean"),
                     ltv=("ltv_inr", "mean"), arpu=("monthly_charges_inr", "mean"),
                     tenure=("tenure_months", "mean"),
                     at_risk=("value_at_risk_inr", "sum"))
                .sort_values("at_risk", ascending=False).head(3))
    cards = st.columns(3, gap="medium")
    for col, r in zip(cards, arch.itertuples()):
        tone = {"High": "down", "Medium": "flat", "Low": "up"}[r.risk_segment]
        with col:
            ui.metric(f"{r.risk_segment} risk · {r.customer_value_segment} value",
                      f"{r.n:,} subscribers",
                      sub=f"Mean churn probability {r.churn:.0%} · lifetime value "
                          f"₹{r.ltv:,.0f} · ARPU ₹{r.arpu:,.0f} · {r.tenure:.0f} months "
                          f"on network.",
                      tag=f"{D.inr(r.at_risk)} at risk",
                      tone=tone, alert=(r.risk_segment == "High"))

    # ── behaviour ────────────────────────────────────────────────────────────
    ui.section("Churn drivers", "What the risk engine reads, and what it means")
    b1, b2 = st.columns([1.15, 1], gap="medium")
    with b1:
        st.plotly_chart(C.drivers(sh["coef_drivers"]), width="stretch", config=C.CONF)
        st.caption("Logistic coefficients. SHAP agrees on direction and ranking.")
    with b2:
        k1, k2 = st.columns(2, gap="small")
        with k1:
            ui.metric("Ranking quality", f"{mm['logistic_calibrated']['roc_auc']:.4f}",
                      sub="ROC-AUC on held-out subscribers.", tag="measured", tone="flat")
        with k2:
            ui.metric("Probability reliability", f"{ev['max_calibration_gap']:.3f}",
                      sub="Largest calibration gap.", tag="trustworthy", tone="up")
        st.markdown("**Raises churn**")
        for x in sh["narrative"]["raises_churn"][:4]:
            st.markdown(f"- {x}")
        st.markdown("**Holds subscribers on network**")
        for x in sh["narrative"]["lowers_churn"][:4]:
            st.markdown(f"- {x}")
        ui.note("<b>Honest caveat.</b> These are conditional effects; correlated inputs "
                "(total charges rises with tenure) must not be read alone. The "
                "decision-grade drivers — where SHAP, coefficients and the hypothesis tests "
                "all agree — are <b>tenure, contract tier and protection adoption</b>.")

    # ── funnel ───────────────────────────────────────────────────────────────
    ui.section("From at-risk to saved", "Flagging a subscriber is not the same as keeping one")
    f1, f2 = st.columns([1.3, 1], gap="medium")
    exp_saves = float((contacts.offer_benefit_inr / contacts.ltv_inr).sum())
    with f1:
        st.plotly_chart(C.churn_funnel([
            ("SIM base", len(cv)),
            ("Flagged at risk", int((cv.churn_probability >= .5).sum())),
            ("Economically viable", prof["n_positive_ev_customers"]),
            ("Funded under budget", len(contacts)),
            ("Expected saves", exp_saves)]), width="stretch", config=C.CONF)
    with f2:
        st.markdown("""
Between **at risk** and **economically viable** sits the economics: a subscriber
earns an offer only when the value we expect to save exceeds what the offer costs.
Between **viable** and **funded** sits the budget.

The final stage is the honest one — expected saves assume subscribers accept at
the planned rate, which only the A/B trial can establish.
        """)
        ui.metric("Retention pipeline yield", f"{exp_saves / len(cv):.2%}",
                  sub=f"≈{exp_saves:,.0f} subscribers expected to be retained, as a share "
                      f"of the SIM base.",
                  tag="expected", tone="up")

    with st.expander("Risk engine validation — ROC, calibration, decile lift"):
        v1, v2, v3 = st.columns([1, 1, 1.2], gap="medium")
        with v1:
            f = D.figure("roc_pr_curves.png")
            if f:
                st.image(str(f), width="stretch")
        with v2:
            f = D.figure("calibration_curve.png")
            if f:
                st.image(str(f), width="stretch")
        with v3:
            st.plotly_chart(C.decile_lift(ev["decile_lift"]), width="stretch", config=C.CONF)
        cm = ev["confusion_at_0.5"]
        st.caption(f"Sorted by risk, the top three bands hold **{ev['top3_decile_capture']:.0%}** "
                   f"of all churners. At the naive 0.50 cut the engine misses {cm['fn']} "
                   f"churners; the operating cut-off is set by the profit curve, not here.")