"""Decision Engine — "Which subscribers do we contact, with which offer, under budget?"

The flagship module and the thesis of the platform. Operational software: the
recommendation and the queue lead; the evidence sits one click away in tabs.

The optimizer is an st.fragment — moving the budget reruns only that panel.
Campaign state persists, so the decision made here is the decision every other
module reports.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components import charts as C
from app.components import data as D
from app.components import state as S
from app.components import theme as T
from app.components import ui
from app.pages._shell import header


@st.fragment
def optimizer_console() -> None:
    """Budget control + live recommendation. Reruns in isolation."""
    c = S.get()
    opt = D.load_json("optimizer_result.json")

    ctl, out = st.columns([1, 2.6], gap="large")
    with ctl:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="k-lab">Campaign budget</div>', unsafe_allow_html=True)
        budget = st.slider("Retention budget (₹)", 10_000, 300_000, int(c.budget), 5_000,
                           format="₹%d", key="sl_budget", label_visibility="collapsed")
        ui.takeaway("Assumption controls — acceptance, offer cost, margin — live in the "
                   "Scenario Simulator and carry through to this recommendation.")
        if st.button("Reset to plan of record", width="stretch"):
            S.reset()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    S.set_field("budget", int(budget))
    with st.spinner("Updating optimizer — re-solving the budget allocation…"):
        d = S.decision()
    delta = d["net_retained_inr"] - opt["results"]["optimizer_roi"]["net_retained_inr"]
    roi = ((d["net_retained_inr"] + d["spend_inr"]) / d["spend_inr"]) if d["spend_inr"] else 0

    with out:
        a, b, c2, e = st.columns([1.35, 1, 1, 1], gap="medium")
        with a:
            ui.metric("Projected net revenue retained", D.inr_exact(d["net_retained_inr"]),
                      sub=f"Live optimizer output. {D.SIM_LABEL}",
                      tag=(f"{D.inr_exact(delta)} vs plan of record" if delta
                           else "at plan of record"),
                      tone="up" if delta >= 0 else "down", hero=True)
        with b:
            ui.metric("Subscribers to contact", f"{d['n_contacted']:,}",
                      sub=f"Offer spend {D.inr_exact(d['spend_inr'])}.",
                      bar=d["budget_utilisation_pct"],
                      tag=f"{d['budget_utilisation_pct']:.0f}% of budget", tone="flat")
        with c2:
            ui.metric("Return per rupee", f"{roi:.2f}×",
                      sub="Expected recovery per rupee of offer spend.",
                      tag="above break-even" if roi > 1 else "below break-even",
                      tone="up" if roi > 1 else "down")
        with e:
            ui.metric("Cost per save", D.inr_exact(d["cost_per_save_inr"] or 0),
                      sub="Offer spend per expected retained subscriber.",
                      tag="unit economics", tone="flat")

        if d["n_contacted"] > 0:
            cv = D.load_customer_values()
            sens = D.load_json("sensitivity.json")
            ev = D.load_json("evaluation.json")
            be = sens["break_even_protection_acceptance_pct"]
            cushion = 35.0 / be if be else 0
            conf, tone = (("High", "high") if cushion >= 2.5 else
                          ("Moderate", "med") if cushion >= 1.5 else ("Low", "low"))
            ui.recommendation(
                verdict="Deploy targeted campaign",
                headline=(f"Contact {d['n_contacted']:,} of {len(cv):,} subscribers for "
                          f"{D.inr_exact(d['spend_inr'])}, to retain a projected "
                          f"{D.inr_exact(d['net_retained_inr'])} {D.SIM_LABEL}."),
                confidence=conf, conf_tone=tone, roi=f"{roi:.2f}×",
                reasons=[
                    f"Beats churn-risk ranking by <b>+{opt['uplift_pct']['rank_by_probability']:.1f}%</b> "
                    f"and a blanket campaign by <b>+{opt['uplift_pct']['contact_everyone']:.1f}%</b> "
                    f"at the same budget.",
                    f"Selection sits <b>{opt['greedy_gap_pct']:.3f}%</b> from a "
                    f"dynamic-programming optimum — the allocation is provably near-best.",
                    f"Risk engine concentrates the problem: the top three risk deciles "
                    f"hold <b>{ev['top3_decile_capture']:.0%}</b> of all churners "
                    f"(ROC-AUC {D.load_json('model_metrics.json')['logistic_calibrated']['roc_auc']:.4f}).",
                    f"Economics hold down to <b>{be:.1f}%</b> offer acceptance against a "
                    f"35% planning assumption — roughly a {cushion:.1f}× cushion.",
                ],
                caveat=("Offer acceptance is the one assumption the subscriber feed cannot "
                        "establish — only the A/B trial can. All rupee figures are "
                        f"{D.SIM_LABEL}."))

        if d["n_contacted"] == 0:
            ui.empty_state(
                "ti-hand-stop", "Recommendation: hold the budget",
                "Under the current assumptions no subscriber has positive expected "
                "value — every offer would cost more than it saves. Standing down is "
                "the correct decision. Raise the budget or adjust assumptions in the "
                "Scenario Simulator to see when contacting becomes worthwhile.")


def render() -> None:
    header("Retention Campaigns",
           "Which subscribers do we contact, with which offer, under a fixed budget?",
           workflow_step="Optimizer")

    opt = D.load_json("optimizer_result.json")
    prof = D.load_json("profit_curve.json")
    contacts = D.load_contact_list()
    cv = D.load_customer_values()
    d = S.decision()

    ui.section("Optimizer", "Set the budget; the recommendation updates immediately")
    optimizer_console()

    # ── offer strategy: decision cards ───────────────────────────────────────
    ui.section("Offer strategy", "How the budget is allocated across the offer portfolio")
    mix = pd.DataFrame(opt["offer_mix"])
    cards = st.columns(len(mix), gap="medium")
    tone_by_rank = ["hot", "flat", "flat"]
    for i, (col, r) in enumerate(zip(cards, mix.itertuples())):
        share = r.spend / float(opt["budget_inr"]) * 100
        with col:
            ui.metric(r.offer, f"{r.n:,} subscribers",
                      sub=f"{D.inr_exact(r.spend)} deployed · {share:.0f}% of budget.",
                      bar=share, tag=f"₹{r.spend/r.n:,.0f} per subscriber",
                      tone=tone_by_rank[i % 3])

    alloc, pipe = st.columns([1, 1.45], gap="medium")
    with alloc:
        st.plotly_chart(C.donut(mix.offer.tolist(), mix.n.tolist(),
                                f"{int(mix.n.sum()):,}", "TARGETED",
                                colors=T.CAT[:3]),
                        width="stretch", config=C.CONF)
        ui.takeaway("Offer allocation under the plan of record.")
    with pipe:
        st.plotly_chart(C.retention_sankey(contacts, len(cv)), width="stretch", config=C.CONF)
        ui.takeaway("Retention pipeline: subscriber base → risk band → offer deployed. "
                   "Courtesy calls carry the volume; bill discounts are reserved for the "
                   "highest-value accounts.")

    # ── priority queue ───────────────────────────────────────────────────────
    ui.section("Priority queue", "Ranked by return per rupee — work the list top-down")

    f1, f2, f3, f4 = st.columns([1, 1, 1, 1.5])
    with f1:
        pick = st.selectbox("Offer", ["All offers"] + sorted(contacts.offer.unique().tolist()))
    with f2:
        rpick = st.selectbox("Risk band", ["All risk bands", "High", "Medium", "Low"])
    with f3:
        vpick = st.selectbox("Value tier", ["All value tiers", "High", "Mid", "Low"])
    view = contacts.copy()
    if pick != "All offers":
        view = view[view.offer == pick]
    if rpick != "All risk bands":
        view = view[view.risk_segment == rpick]
    if vpick != "All value tiers":
        view = view[view.customer_value_segment == vpick]
    view = view.sort_values("roi_per_rupee", ascending=False).reset_index(drop=True)
    view.insert(0, "priority", view.index + 1)
    with f4:
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        st.download_button(f"Export {len(view):,} subscribers (CSV)",
                           view.to_csv(index=False).encode(),
                           file_name="bharatconnect_contact_list.csv", mime="text/csv",
                           width="stretch")

    q1, q2 = st.columns([3, 1], gap="medium")
    with q1:
        if len(view) == 0:
            ui.empty_state(
                "ti-filter-off", "No subscribers match these filters",
                "No funded subscriber fits the current offer, risk band and value "
                "tier combination. Clear a filter to widen the queue.")
        else:
            st.dataframe(
                view.head(200)[["priority", "customer_id", "risk_segment",
                                "customer_value_segment", "churn_proba", "ltv_inr", "offer",
                                "offer_cost_inr", "offer_net_inr", "roi_per_rupee"]],
                width="stretch", hide_index=True, height=340,
                column_config={
                    "priority": st.column_config.NumberColumn("#", width="small"),
                    "customer_id": "Subscriber",
                    "risk_segment": "Risk band",
                    "customer_value_segment": "Value tier",
                    "churn_proba": st.column_config.ProgressColumn(
                        "Churn probability", format="%.2f", min_value=0, max_value=1),
                    "ltv_inr": st.column_config.NumberColumn("Lifetime value", format="₹%.0f"),
                    "offer": "Offer",
                    "offer_cost_inr": st.column_config.NumberColumn("Cost", format="₹%.0f"),
                    "offer_net_inr": st.column_config.NumberColumn("Expected net", format="₹%.0f"),
                    "roi_per_rupee": st.column_config.NumberColumn("Return per ₹", format="%.2f×"),
                })
    with q2:
        ui.ledger("Queue summary", [
            ("In view", f"{len(view):,} of {len(contacts):,}"),
            ("Offer spend", D.inr_exact(view.offer_cost_inr.sum())),
            ("Expected net", D.inr_exact(view.offer_net_inr.sum())),
            ("Mean return", f"{view.roi_per_rupee.mean():.2f}×" if len(view) else "—"),
            ("Mean churn risk", f"{view.churn_proba.mean():.0%}" if len(view) else "—"),
            ("Mean lifetime value", D.inr_exact(view.ltv_inr.mean()) if len(view) else "—"),
        ], sub="Filtering never rewrites the saved contact list.")

    # ── evidence, one click away ─────────────────────────────────────────────
    ui.section("Evidence", "Why this beats calling the riskiest subscribers")
    t1, t2, t3 = st.tabs(["Expected uplift", "Profit curve", "Optimality"])
    with t1:
        st.plotly_chart(C.strategy_bars(opt["results"]), width="stretch", config=C.CONF)
        ui.takeaway(f"Net revenue retained by targeting strategy at the same budget. The "
                   f"optimizer beats churn-risk ranking by "
                   f"**+{opt['uplift_pct']['rank_by_probability']:.1f}%** and a blanket "
                   f"campaign by **+{opt['uplift_pct']['contact_everyone']:.1f}%**. "
                   f"{D.SIM_LABEL}")
    with t2:
        st.plotly_chart(C.profit_curve(prof["curve"], prof["optimal_threshold"]),
                        width="stretch", config=C.CONF)
        ui.takeaway("A subscriber earns an offer when expected saved value exceeds offer "
                   "cost — and that break-even depends on lifetime value, not risk alone "
                   "(it ranges 0.22 to 1.96 across the base). No single cut-off can be "
                   "optimal, which is why the budget is solved as a knapsack.")
    with t3:
        o1, o2 = st.columns([1, 1.6], gap="medium")
        with o1:
            ui.ledger("Optimisation", [
                ("Method", "0/1 knapsack, greedy by ROI"),
                ("Verified against", "Dynamic programming"),
                ("Optimality gap", f"{opt['greedy_gap_pct']:.3f}%"),
                ("Budget", D.inr(opt["budget_inr"])),
                ("Utilisation", f"{opt['budget_utilisation_pct']:.1f}%"),
                ("Selected", f"{opt['results']['optimizer_roi']['n_contacted']:,} subscribers"),
            ])
        with o2:
            st.plotly_chart(C.campaign_progress(opt["offer_mix"], float(opt["budget_inr"])),
                            width="stretch", config=C.CONF)
            ui.takeaway("Budget deployed by offer, plan of record.")

    if ui.next_step("The plan is set — but what would break this recommendation?", "Scenario Lab", "scenarios"):
        from app.dashboard import goto
        goto("scenarios")