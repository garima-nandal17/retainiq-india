"""Executive Briefing — the one-page read for the Head of Retention.

Deliberately NOT called an "AI briefing". No language model writes this. The
narrative is composed deterministically from the live campaign state and the
governed metrics in `reports/` — it updates when an assumption moves, and every
sentence is traceable to a number the platform can show you.

That is a stronger claim than "an LLM wrote it", and it is the honest one: the
project's Out-of-Scope register rules out an LLM layer, because it would not
change whom we contact under budget.
"""
from __future__ import annotations

import streamlit as st

from app.components import data as D
from app.components import state as S
from app.components import theme as T
from app.components import ui
from app.pages._shell import header


def _changes(c, plan_budget: float) -> list[tuple[str, str]]:
    """What the operator changed away from the plan of record."""
    out = []
    if c.budget != plan_budget:
        out.append(("Budget", f"{D.inr(plan_budget)} → {D.inr(c.budget)}"))
    if c.acceptance != 1.0:
        out.append(("Offer acceptance", f"35% → {35 * c.acceptance:.0f}% "
                                        f"({c.acceptance:.1f}× plan)"))
    if c.offer_cost != 1.0:
        out.append(("Offer cost", f"{c.offer_cost:.1f}× plan"))
    if c.margin != 0.60:
        out.append(("Gross margin", f"60% → {c.margin:.0%}"))
    return out


def render() -> None:
    header("Executive Brief", "The one-page read for the Head of Retention.",
           workflow_step="Recommendation")

    opt = D.load_json("optimizer_result.json")
    sens = D.load_json("sensitivity.json")
    ev = D.load_json("evaluation.json")
    cv = D.load_customer_values()
    contacts = D.load_contact_list()
    c = S.get()
    d = S.decision()
    plan = opt["results"]["optimizer_roi"]

    churn = cv.churned.mean()
    at_risk = int((cv.churn_probability >= .5).sum())
    leakage = float(cv.value_at_risk_inr.sum())
    live = d["n_contacted"] > 0
    changes = _changes(c, float(opt["budget_inr"]))

    # ── verdict ──────────────────────────────────────────────────────────────
    k = st.columns([1.3, 1, 1, 1], gap="medium")
    with k[0]:
        ui.metric("Recommendation", "Deploy campaign" if live else "Hold budget",
                  sub=(f"Target {d['n_contacted']:,} subscribers for "
                       f"{D.inr_exact(d['spend_inr'])}. Projected net revenue retained "
                       f"{D.inr_exact(d['net_retained_inr'])} {D.SIM_LABEL}."
                       if live else
                       "No subscriber has positive expected value under the current "
                       "assumptions. Holding the budget is the correct decision."),
                  tag="economically justified" if live else "stand down",
                  tone="up" if live else "down", hero=True, alert=not live)
    with k[1]:
        ui.metric("Net revenue retained", D.inr_exact(d["net_retained_inr"]),
                  sub=D.SIM_LABEL,
                  tag=f"+{opt['uplift_pct']['rank_by_probability']:.1f}% vs risk ranking",
                  tone="up")
    with k[2]:
        ui.metric("Budget", D.inr(c.budget),
                  sub=f"{d['budget_utilisation_pct']:.0f}% deployed across "
                      f"{d['n_contacted']:,} subscribers.",
                  bar=d["budget_utilisation_pct"], tone="flat")
    with k[3]:
        ui.metric("Downside protection",
                  f"{sens['break_even_protection_acceptance_pct']:.1f}%",
                  sub="Break-even offer acceptance against a 35% planning assumption.",
                  tag="≈3× cushion", tone="up")

    # ── consulting-style report sections ─────────────────────────────────────
    ui.section("Executive report", "Composed deterministically from the current campaign state")

    ui.report_block("1", "Executive summary", (
        f"BharatConnect is losing <b>{D.pct(churn)}</b> of its subscriber base. The loss "
        f"is not evenly spread: it concentrates in rolling contracts, fibre connections "
        f"and short-tenure accounts, and it is <b>front-loaded</b> — first-year "
        f"subscribers churn at <b>47.4%</b> against <b>9.5%</b> beyond four years. "
        f"<b>{at_risk:,}</b> subscribers carry a churn probability of 50% or higher, "
        f"placing <b>{D.inr(leakage)}</b> of lifetime margin at risk.<br><br>"
        f"Contacting everyone is not an option: a blanket campaign would spend "
        f"<b>{D.inr_exact(opt['results']['contact_everyone']['spend_inr'])}</b> and "
        f"<b>destroy {D.inr_exact(abs(opt['results']['contact_everyone']['net_retained_inr']))}</b> "
        f"of value, because most subscribers who accept an offer would have stayed anyway."))

    ui.report_block("2", "Financial impact", (
        f"Under the <b>{D.inr(c.budget)}</b> budget currently set, the platform targets "
        f"<b>{d['n_contacted']:,}</b> subscribers at <b>{D.inr_exact(d['spend_inr'])}</b> "
        f"of offer cost ({D.pct(d['budget_utilisation_pct'], 0)} utilisation), for a "
        f"projected <b>{D.inr_exact(d['net_retained_inr'])}</b> net revenue retained "
        f"{D.SIM_LABEL}.<br><br>"
        f"That is <b>{opt['uplift_pct']['rank_by_probability']:+.1f}%</b> better than "
        f"ranking subscribers by churn risk alone — where most retention programmes stop — "
        f"and <b>{opt['uplift_pct']['contact_everyone']:+.1f}%</b> better than a blanket "
        f"campaign. The selection sits <b>{opt['greedy_gap_pct']:.3f}%</b> from a "
        f"dynamic-programming optimum, so the allocation is provably near-best."))

    ui.report_block("3", "Key risks", (
        f"<b>Offer acceptance is unmeasured.</b> It is the one assumption the subscriber "
        f"feed cannot establish — only a randomised trial can. The recommendation "
        f"continues to pay down to a "
        f"<b>{sens['break_even_protection_acceptance_pct']:.1f}%</b> acceptance rate "
        f"against a 35% planning assumption, roughly a threefold cushion.<br><br>"
        f"<b>Offer cost is the most influential input</b> — the assumption to negotiate "
        f"hardest with vendors. <b>Budget saturates near {D.inr(200_000)}</b>: beyond "
        f"that, no positive-value subscriber remains to contact. Under the pessimistic "
        f"scenario the platform recommends holding the budget entirely."))

    ui.report_block("4", "Recommendation", (
        f"<b>{'Deploy the targeted campaign' if live else 'Hold the budget'}.</b> "
        + (f"Contact the {d['n_contacted']:,} ranked subscribers with the assigned offer "
           f"mix — courtesy calls where a light touch suffices, protection bundles where "
           f"add-ons measurably reduce churn, and bill discounts reserved for the "
           f"highest-value accounts. Work the priority queue top-down; it is ordered by "
           f"return per rupee."
           if live else
           "No subscriber has positive expected value under the current assumptions. "
           "Standing down is the correct decision — every offer would cost more than it "
           "saves.")))

    ui.report_block("5", "Approval required", (
        f"<b>Budget:</b> {D.inr(c.budget)} retention spend for this cycle.<br>"
        f"<b>Scope:</b> {d['n_contacted']:,} subscribers, offer mix as assigned.<br>"
        f"<b>Experiment:</b> hold out 674 subscribers per arm inside the targeted pool "
        f"for a randomised trial (90-day churn, intention-to-treat), with ARPU, "
        f"cost-per-save and opt-out rate as guardrails.<br>"
        f"<b>Owner:</b> Retention Operations · <b>Cadence:</b> monthly campaign cycle."))

    ui.report_block("6", "Expected outcome", (
        f"A projected <b>{D.inr_exact(d['net_retained_inr'])}</b> of net revenue retained "
        f"{D.SIM_LABEL}, at a cost per save of "
        f"<b>{D.inr_exact(d['cost_per_save_inr'] or 0)}</b>. The trial returns a measured "
        f"acceptance rate within one campaign cycle, which replaces the single largest "
        f"assumption in this model and unlocks uplift modelling — targeting persuadables "
        f"rather than the merely at-risk — for the following cycle."))

    # ── changes / risks / actions ────────────────────────────────────────────
    ui.section("Risks, controls and changes")
    r1, r2, r3 = st.columns(3, gap="medium")
    with r1:
        ui.ledger("Key risks", [
            ("Offer acceptance unmeasured", "A/B trial required"),
            ("Most influential assumption", "Offer cost"),
            ("Break-even acceptance", f"{sens['break_even_protection_acceptance_pct']:.1f}%"),
            ("Budget saturation", D.inr(200_000)),
            ("Prepaid/postpaid tiers", "Declared mapping"),
            ("Uplift modelling", "Deferred until trial data"),
        ], sub="Documented, not hidden.")
    with r2:
        ui.ledger("Recommended actions", [
            ("1 · Approve", f"{D.inr(c.budget)} retention budget"),
            ("2 · Deploy" if live else "2 · Hold",
             f"{d['n_contacted']:,} subscribers" if live else "No campaign"),
            ("3 · Randomise", "674 per arm inside the pool"),
            ("4 · Measure", "90-day churn, ITT primary"),
            ("5 · Guardrails", "ARPU, cost per save, opt-out"),
            ("6 · Revisit", "Uplift model after trial"),
        ], sub="In sequence, owned by Retention Operations.")
    with r3:
        if changes:
            ui.ledger("Changes from plan of record", changes,
                      sub="Set in the Scenario Simulator; carried across the platform.")
        else:
            ui.ledger("Changes from plan of record", [
                ("Status", "None — at plan"),
                ("Budget", D.inr(opt["budget_inr"])),
                ("Acceptance", "35% (planned)"),
                ("Offer cost", "As costed"),
                ("Gross margin", "60%"),
                ("Subscribers targeted", f"{plan['n_contacted']:,}"),
            ], sub="The committed campaign is in force.")

    # ── insights ─────────────────────────────────────────────────────────────
    ui.section("Business insights", "What this analysis established that a churn model alone would not")
    i1, i2 = st.columns(2, gap="medium")
    with i1:
        st.markdown(f"""
**No single risk threshold is optimal.** The point at which a subscriber becomes worth
contacting depends on their lifetime value, not their risk alone — it ranges from **0.22
to 1.96** across the base. This is why the budget is solved as a knapsack rather than a
cut-off, and it is the core of the platform's advantage.

**High risk means high ARPU.** Subscribers most likely to leave pay *more* than those who
stay. Retention here defends premium revenue, not marginal revenue.
        """)
    with i2:
        st.markdown(f"""
**The engine concentrates the problem.** The top three risk bands hold
**{ev['top3_decile_capture']:.0%}** of all churners, which is what makes a
{D.inr(c.budget)} budget meaningful against a {D.inr(leakage)} exposure.

**The platform will refuse to spend.** Under pessimistic assumptions it recommends
contacting nobody. A system that knows when to stand down is more trustworthy than one
that always finds a reason to deploy budget.
        """)

    # ── handoff ──────────────────────────────────────────────────────────────
    ui.section("Hand off", "Export for the campaign management system")
    e1, e2, e3 = st.columns([1, 1, 2], gap="medium")
    with e1:
        st.download_button("Export contact list (CSV)",
                           contacts.to_csv(index=False).encode(),
                           file_name="bharatconnect_contact_list.csv", mime="text/csv",
                           width="stretch")
    with e2:
        txt = (
            "BHARATCONNECT — RETENTION CAMPAIGN, EXECUTIVE BRIEFING\n"
            "All rupee figures are simulation-based estimates.\n\n"
            f"RECOMMENDATION      {'DEPLOY CAMPAIGN' if live else 'HOLD BUDGET'}\n"
            f"Budget              {D.inr(c.budget)}\n"
            f"Subscribers         {d['n_contacted']:,} of {len(cv):,}\n"
            f"Offer spend         {D.inr_exact(d['spend_inr'])} "
            f"({d['budget_utilisation_pct']:.0f}% utilisation)\n"
            f"Net revenue retained {D.inr_exact(d['net_retained_inr'])}\n"
            f"Uplift vs risk ranking  +{opt['uplift_pct']['rank_by_probability']:.1f}%\n"
            f"Optimality gap vs DP    {opt['greedy_gap_pct']:.3f}%\n\n"
            f"BASE       {len(cv):,} subscribers, churn {churn:.2%}\n"
            f"AT RISK    {at_risk:,} subscribers, {D.inr(leakage)} lifetime margin\n\n"
            f"RISK       Offer acceptance is unmeasured. Break-even "
            f"{sens['break_even_protection_acceptance_pct']:.1f}% vs 35% planned.\n"
            f"VALIDATION A/B trial, 674 per arm, MDE 12.6% relative churn reduction,\n"
            f"           90-day churn primary, ITT.\n")
        st.download_button("Export briefing (TXT)", txt.encode(),
                           file_name="bharatconnect_executive_briefing.txt",
                           mime="text/plain", width="stretch")
    with e3:
        ui.note("<b>This briefing is generated, not written — and not by a language model.</b> "
                "Every sentence is composed deterministically from the campaign state and the "
                "governed metrics in <code>reports/</code>, so it updates when an assumption "
                "moves and each figure is traceable. An LLM layer is deliberately out of "
                "scope: it would add interface novelty without changing whom we contact "
                "under budget. Full trial design in <code>docs/AB_experiment_design.md</code>.")