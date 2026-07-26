"""
dashboard.py — RetainIQ · BharatConnect Retention OSS (Day 13 v3)

A true multi-page enterprise application. Routing is handled by a row of tab
buttons at the top of the main content area — one page rendered at a time, not a
scrolling report. Campaign state persists across pages via session_state, so the
operational workflow is continuous:

    Budget → Optimizer → Offer assignment → Contact list → Recommendation → Export

UI/UX layer only. Every figure is read from `reports/`; the live optimizer
delegates to the Day-11 `simulator.simulate()`. Nothing is recomputed here.

Run:  streamlit run app/dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import datetime

import streamlit as st
import streamlit.components.v1 as components

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP.parent))

from app.components import data as D
from app.components import state as S          # noqa: E402
from app.components import theme as T         # noqa: E402
from app.components import ui                 # noqa: E402
from app.pages import (executive, customer, decision,  # noqa: E402
                       scenarios, brief)

st.set_page_config(page_title="RetainIQ · BharatConnect Retention OSS",
                   page_icon="◤", layout="wide", initial_sidebar_state="expanded")
T.inject()


def _sidebar_footer() -> None:
    with st.sidebar:
        st.markdown('<div class="rail-div"></div>', unsafe_allow_html=True)
        ui.rail_cap("Operator")
        ui.rail_kv("BharatConnect", "Telecom · India")
        ui.rail_cap("Owner")
        ui.rail_kv("Priya Menon", "Head of Retention")
        ui.rail_cap("Campaign cycle")
        ui.rail_kv("Monthly", "Plan of record")
        st.markdown('<div class="rail-div"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.68rem;color:#64748B;line-height:1.6">'
            'Rupee figures are simulation-based estimates.<br>'
            'Risk-engine quality is measured.</div>',
            unsafe_allow_html=True)


# page registry: (key, label, icon, render fn)
PAGE_LIST = [
    ("executive", "Network Command", "hub", executive.render),
    ("customer", "Subscriber Intelligence", "groups", customer.render),
    ("decision", "Retention Campaigns", "campaign", decision.render),
    ("scenarios", "Scenario Lab", "science", scenarios.render),
    ("brief", "Executive Brief", "description", brief.render),
]

def _top_nav() -> str:
    """Navigation as a row of buttons at the TOP of the main content area.
    This renders in the main pane — it cannot be hidden by any sidebar CSS or a
    collapsed rail. Returns the active page key. This is the single source of
    navigation; there is no dependency on st.navigation."""
    if "page" not in st.session_state:
        st.session_state.page = "executive"
    q = st.query_params.get("render")
    if q in {k for k, *_ in PAGE_LIST}:
        st.session_state.page = q

    # persistent global command bar — brand, health, live KPIs, build metadata
    dq = D.load_json("dq_report.json")
    mm = D.load_json("model_metrics.json")
    stt = S.status()
    d, c = stt["decision"], stt["campaign"]
    feed_ok = all(x["passed"] for x in dq["checks"] if x["severity"] == "hard")
    auc = mm["logistic_calibrated"]["roc_auc"]
    refreshed = datetime.datetime.fromtimestamp(
        (D.ROOT / "reports" / "optimizer_result.json").stat().st_mtime
    ).strftime("%d %b %Y · %H:%M")

    ui.command_bar(
        brand_sub="BharatConnect · Retention Decision Platform",
        health=[("Subscriber feed", "Healthy" if feed_ok else "Degraded",
                 "ok" if feed_ok else "warn"),
                ("Risk engine", f"AUC {auc:.4f}", "info"),
                ("Mode", "Simulation", "warn")],
        kpis=[("Budget", D.inr(c["budget"])),
              ("Targeted", f"{d['n_contacted']:,}"),
              ("Net retained", D.inr_exact(d["net_retained_inr"])),
              ("Utilisation", f"{d['budget_utilisation_pct']:.0f}%")],
        scenario=("Plan of record" if S.get().is_plan_of_record
                  else "Custom scenario active"),
        is_plan=S.get().is_plan_of_record,
        meta=(f"Refreshed {refreshed} · Model v1.2 · Data v1.0 · Pipeline v1.4"),
    )

    # tab buttons
    cols = st.columns(len(PAGE_LIST), gap="small")
    for col, (key, label, icon, _) in zip(cols, PAGE_LIST):
        with col:
            active = st.session_state.page == key
            if st.button(label, key=f"topnav_{key}", use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state.page = key
                st.query_params["render"] = key
                st.rerun()
    st.markdown('<div class="topnav-rule"></div>', unsafe_allow_html=True)
    return st.session_state.page


def goto(page_key: str) -> None:
    """Programmatic navigation — used by the in-page 'next step' buttons so the
    narrative spine actually moves you to the next page."""
    st.session_state.page = page_key
    st.query_params["render"] = page_key
    st.rerun()


def _scroll_top_if_page_changed(page: str) -> None:
    """Reset scroll on navigation. Streamlit preserves scroll offset across reruns,
    which makes a page switch feel like a jump into the middle of a document."""
    if st.session_state.get("_last_page") != page:
        st.session_state["_last_page"] = page
        js = ("<script>"
              "const d=window.parent.document;"
              "const t=d.querySelector('section.main')||d.querySelector("
              "'[data-testid=\"stAppViewContainer\"]')||d.scrollingElement;"
              "if(t){t.scrollTo({top:0,behavior:'instant'});}"
              "window.parent.scrollTo({top:0,behavior:'instant'});"
              "</script>")
        try:
            components.html(js, height=0)
        except Exception:
            pass  # cosmetic only — never break navigation over a scroll reset


def main() -> None:
    page = _top_nav()
    _scroll_top_if_page_changed(page)
    render = dict((k, fn) for k, _, _, fn in PAGE_LIST)[page]
    try:
        ui.onboarding()
        render()
    except D.MissingArtifact as exc:
        st.error(f"**Subscriber feed unavailable.** {exc}")
        st.stop()


if __name__ == "__main__":
    main()