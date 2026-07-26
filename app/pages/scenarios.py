"""Scenario Simulator — "What would break this recommendation?"

Interactive by design: the assumption controls live here, and they write to the
shared campaign state, so the Decision Engine and Executive Briefing immediately
report whatever is set on this page.

Comparison is against the plan of record — never against a placeholder.
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


# Named assumption sets. These only move the *declared* assumptions the Scenario
# Lab already exposes as sliders — no new business logic, no new calculation path.
PRESETS = {
    "Conservative": dict(acceptance=0.7, offer_cost=1.3, margin=0.50,
                         note="Cautious planning: acceptance below plan, offers cost "
                              "more, thinner margin."),
    "Expected": dict(acceptance=1.0, offer_cost=1.0, margin=0.60,
                     note="The plan of record — the committed campaign assumptions."),
    "Aggressive": dict(acceptance=1.3, offer_cost=0.9, margin=0.65,
                       note="Optimistic: offers land better and cost less than costed."),
    "Worst case": dict(acceptance=0.4, offer_cost=2.0, margin=0.45,
                       note="Stress test: acceptance collapses, offer cost doubles."),
    "Best case": dict(acceptance=1.6, offer_cost=0.7, margin=0.75,
                      note="Upper bound: strong acceptance, cheap offers, rich margin."),
}


def _delta_tone(v: float) -> str:
    return "up" if v > 0 else ("down" if v < 0 else "flat")


@st.fragment
def simulator() -> None:
    """Live assumption controls + impact vs plan of record. Isolated rerun."""
    c = S.get()
    opt = D.load_json("optimizer_result.json")
    plan = opt["results"]["optimizer_roi"]

    ctl, cmp_ = st.columns([1, 2.6], gap="large")
    with ctl:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="k-lab">Scenario preset</div>', unsafe_allow_html=True)
        preset = st.selectbox(
            "Preset", list(PRESETS.keys()), index=1, key="sim_preset",
            label_visibility="collapsed",
            help="Presets set all four assumptions at once. Adjust any slider "
                 "afterwards to build a custom scenario.")
        if st.button("Apply preset", width="stretch", key="sim_apply"):
            p = PRESETS[preset]
            S.set_field("acceptance", p["acceptance"])
            S.set_field("offer_cost", p["offer_cost"])
            S.set_field("margin", p["margin"])
            for k, v in (("sim_acc", p["acceptance"]), ("sim_cost", p["offer_cost"]),
                         ("sim_margin", p["margin"])):
                st.session_state[k] = v
            st.rerun()
        st.caption(PRESETS[preset]["note"])
        st.markdown('<div class="k-lab" style="margin-top:.7rem">'
                    'Assumption controls</div>', unsafe_allow_html=True)
        budget = st.slider("Retention budget (₹)", 10_000, 300_000, int(c.budget), 5_000,
                           format="₹%d", key="sim_budget")
        acc = st.slider("Offer acceptance vs plan", 0.4, 1.6, float(c.acceptance), 0.1,
                        key="sim_acc",
                        help="Multiplier on the planned 35% acceptance rate.")
        cost = st.slider("Offer cost vs plan", 0.5, 3.0, float(c.offer_cost), 0.1,
                         key="sim_cost")
        margin = st.slider("Gross margin", 0.40, 0.80, float(c.margin), 0.05,
                           key="sim_margin")
        if st.button("Reset to plan of record", width="stretch", key="sim_reset"):
            S.reset()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    S.set_field("budget", int(budget)); S.set_field("acceptance", float(acc))
    S.set_field("offer_cost", float(cost)); S.set_field("margin", float(margin))
    with st.spinner("Running simulation — re-pricing every subscriber…"):
        d = S.decision()

    d_net = d["net_retained_inr"] - plan["net_retained_inr"]
    d_n = d["n_contacted"] - plan["n_contacted"]
    d_spend = d["spend_inr"] - plan["spend_inr"]

    with cmp_:
        # impact cards
        i1, i2, i3, i4 = st.columns([1.3, 1, 1, 1], gap="medium")
        with i1:
            ui.metric("Net revenue retained", D.inr_exact(d["net_retained_inr"]),
                      sub=f"Under the assumptions at left. {D.SIM_LABEL}",
                      tag=f"{'+' if d_net >= 0 else ''}{D.inr_exact(d_net)} vs plan",
                      tone=_delta_tone(d_net), hero=True)
        with i2:
            ui.metric("Subscribers targeted", f"{d['n_contacted']:,}",
                      sub=f"Plan of record: {plan['n_contacted']:,}.",
                      tag=f"{d_n:+,}", tone=_delta_tone(d_n))
        with i3:
            ui.metric("Offer spend", D.inr_exact(d["spend_inr"]),
                      sub=f"{d['budget_utilisation_pct']:.0f}% of budget deployed.",
                      bar=d["budget_utilisation_pct"],
                      tag=f"{'+' if d_spend >= 0 else ''}{D.inr_exact(d_spend)}",
                      tone="flat")
        with i4:
            roi = ((d["net_retained_inr"] + d["spend_inr"]) / d["spend_inr"]
                   if d["spend_inr"] else 0)
            ui.metric("Return per rupee", f"{roi:.2f}×",
                      sub="Recovery per rupee of offer spend.",
                      tag="above break-even" if roi > 1 else "below break-even",
                      tone="up" if roi > 1 else "down")

        # side-by-side comparison
        cA, cB = st.columns(2, gap="medium")
        with cA:
            ui.ledger("Plan of record", [
                ("Budget", D.inr(opt["budget_inr"])),
                ("Acceptance", "35% (planned)"),
                ("Offer cost", "As costed"),
                ("Gross margin", "60%"),
                ("Subscribers targeted", f"{plan['n_contacted']:,}"),
                ("Net revenue retained", D.inr_exact(plan["net_retained_inr"])),
            ], sub="The committed campaign.")
        with cB:
            ui.ledger("Current scenario", [
                ("Budget", D.inr(budget)),
                ("Acceptance", f"{35 * acc:.0f}% ({acc:.1f}× plan)"),
                ("Offer cost", f"{cost:.1f}× plan"),
                ("Gross margin", f"{margin:.0%}"),
                ("Subscribers targeted", f"{d['n_contacted']:,}"),
                ("Net revenue retained", D.inr_exact(d["net_retained_inr"])),
            ], sub="Carried through to the Decision Engine and Briefing.")

    if d["n_contacted"] == 0:
        st.error("**Under these assumptions the platform recommends holding the budget.** "
                 "No subscriber has positive expected value. A decision system that knows "
                 "when to stand down is more trustworthy than one that always spends.")


def render() -> None:
    header("Scenario Lab", "What would break this recommendation?",
           workflow_step="Optimizer")
    sens = D.load_json("sensitivity.json")
    scen = D.load_json("scenarios.json")
    opt = D.load_json("optimizer_result.json")

    ui.section("Live simulation", "Adjust assumptions; the recommendation updates across the platform")
    simulator()

    ui.section("Assumption sensitivity", "Which input moves the outcome most")
    s1, s2 = st.columns([1.4, 1], gap="medium")
    with s1:
        st.plotly_chart(C.tornado(sens["one_way"], sens["baseline_net_inr"]),
                        width="stretch", config=C.CONF)
        st.caption(f"Swing in net revenue retained as each assumption crosses its plausible "
                   f"range, against a {D.inr_exact(sens['baseline_net_inr'])} baseline. "
                   f"Offer cost dominates — it is the assumption to negotiate hardest. "
                   f"{D.SIM_LABEL}")
    with s2:
        ui.metric("Break-even acceptance",
                  f"{sens['break_even_protection_acceptance_pct']:.1f}%",
                  sub="Below this offer-acceptance rate the campaign stops paying. The plan "
                      "assumes 35% — roughly a threefold cushion.",
                  tag="robust", tone="up")
        ui.metric("Budget saturation", D.inr(scen.get("saturation_budget_inr", 200_000)),
                  sub="Beyond this point additional budget buys nothing: no subscriber "
                      "worth contacting remains.",
                  tag="ceiling", tone="flat")

    ui.section("Acceptance against offer cost", "Where the campaign stops paying")
    h1, h2 = st.columns([1.25, 1], gap="medium")
    with h1:
        st.plotly_chart(C.sensitivity_heatmap(sens["two_way_grid"]),
                        width="stretch", config=C.CONF)
        st.caption("Net revenue retained across the two assumptions that matter most.")
    with h2:
        st.plotly_chart(C.budget_response(scen["budget_response_curve"],
                                          float(opt["budget_inr"])),
                        width="stretch", config=C.CONF)
        st.caption("Net retained as the budget scales. The curve flattens at saturation.")

    ui.section("Named scenarios", "Pre-costed cases for the steering committee")
    cols = st.columns(3, gap="medium")
    tone_of = {"pessimistic": "down", "base": "flat", "optimistic": "up"}
    for col, (name, r) in zip(cols, scen["scenarios"].items()):
        inp = r["inputs"]
        with col:
            ui.metric(name.capitalize(), D.inr_exact(r["net_retained_inr"]),
                      sub=(f"{r['n_contacted']:,} subscribers · "
                           f"{D.inr_exact(r['spend_inr'])} deployed."
                           if r["n_contacted"] else
                           "No subscriber is worth contacting. Hold the budget."),
                      tag=(f"acceptance {35*inp['acceptance_scale']:.0f}% · "
                           f"cost {inp['offer_cost_multiplier']:.1f}×"),
                      tone=tone_of[name],
                      alert=(name == "pessimistic" and not r["n_contacted"]))

    ui.note("Offer acceptance is the one assumption the subscriber feed cannot establish — "
            "only a randomised trial can. That is why the A/B design exists, and why "
            "<b>uplift modelling is deliberately deferred</b>: identifying persuadables "
            "requires the very data the trial would generate. Every rupee figure on this "
            f"page is a {D.SIM_LABEL}.")

    if ui.next_step("Stress-tested — now summarise the decision for leadership.", "Executive Brief", "brief"):
        from app.dashboard import goto
        goto("brief")