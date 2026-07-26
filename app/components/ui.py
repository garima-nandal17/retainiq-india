"""
ui.py — RetainIQ India UI primitives (Enterprise Edition).

Presentation only. Copy discipline: label what the retention team controls, in
telecom terms, never how the system is built.

Function signatures are kept stable so pages keep working; only the emitted
markup and visual language changed.
"""
from __future__ import annotations

import streamlit as st

from . import theme as T


def next_step(question: str, target_label: str, target_key: str) -> bool:
    """Narrative spine — a REAL navigation button. Renders the next business
    question and, when clicked, returns True so the caller can navigate. This is
    a working control, not a decorative link."""
    st.markdown(
        f'<div class="nextstep"><span class="ns-cap">Next decision</span>'
        f'<span class="ns-q">{question}</span></div>', unsafe_allow_html=True)
    return st.button(f"{target_label}  →", key=f"next_{target_key}",
                     use_container_width=True, type="primary")


# ── page chrome ──────────────────────────────────────────────────────────────
def colour_legend() -> None:
    """The colour system, stated once on the landing page. Every accent maps to
    one business meaning; after this page the colours speak for themselves."""
    items = [
        ("var(--risk)", "Risk", "at-risk revenue, churn exposure"),
        ("var(--opp)", "Opportunity", "recoverable / retained value"),
        ("var(--revenue)", "Revenue", "portfolio value, ARPU"),
        ("var(--reco)", "Recommendation", "the platform's chosen action"),
        ("var(--alert)", "Alert", "loss, or a decision to stand down"),
    ]
    cells = "".join(
        f'<span class="lg-item"><span class="lg-sw" style="background:{c}"></span>'
        f'<span class="lg-k">{k}</span><span class="lg-d">{d}</span></span>'
        for c, k, d in items)
    st.markdown(f'<div class="legend">{cells}</div>', unsafe_allow_html=True)



def console(page: str, operator: str, telemetry: list[tuple[str, str, str]]) -> None:
    """Top executive bar: page identity + platform status chips."""
    chips = "".join(
        f'<span class="chip {tone}"><span class="led"></span>{k} <b>{v}</b></span>'
        for k, v, tone in telemetry)
    st.markdown(
        f'<div class="topbar"><div class="topbar-l">'
        f'  <div class="topbar-title">{page}</div>'
        f'  <div class="topbar-q">{operator}</div>'
        f'</div><div class="topbar-r">{chips}</div></div>', unsafe_allow_html=True)


def sim_base_ribbon(segments: list[tuple[float, str]]) -> None:
    """Network composition strip: access-mix across the SIM base. Static, no motion."""
    spans = "".join(f'<span style="width:{w:.2f}%;background:{c}"></span>'
                    for w, c in segments)
    st.markdown(f'<div class="netmix">{spans}</div>', unsafe_allow_html=True)


def onboarding() -> None:
    """First-run affordance. Shows once per session, points at the flagship,
    then dismisses. A cold-open user needs a start line, not a mid-workflow drop."""
    if st.session_state.get("onboarded"):
        return
    st.markdown(
        '<div class="onboard">'
        '  <div class="onboard-body">'
        '    <div class="onboard-t"><i class="dot"></i>Welcome to RetainIQ India</div>'
        '    <div class="onboard-d">A decision platform, not a report. It picks which '
        'subscribers to contact, with which offer, under a fixed budget. '
        '<b>Start on the Decision Engine</b> — set a budget and watch the recommendation, '
        'contact list and briefing update together.</div>'
        '  </div>'
        '</div>', unsafe_allow_html=True)
    if st.button("Got it — start", key="onboard_dismiss"):
        st.session_state.onboarded = True
        st.rerun()


def scenario_flag(is_plan: bool, changes: list[tuple[str, str]] | None = None) -> None:
    """State-change feedback. When the operator has moved assumptions off the plan
    of record, say so — visibly — so the propagation across pages is legible."""
    if is_plan:
        st.markdown(
            '<div class="sflag plan"><i class="ti ti-lock"></i>'
            'Plan of record — committed campaign assumptions</div>',
            unsafe_allow_html=True)
    else:
        detail = ""
        if changes:
            detail = " · ".join(f"{k} {v}" for k, v in changes[:3])
        st.markdown(
            f'<div class="sflag custom"><i class="ti ti-adjustments"></i>'
            f'Custom scenario active{" — " + detail if detail else ""}. '
            f'Carried across every page.</div>', unsafe_allow_html=True)


def empty_state(icon: str, title: str, body: str) -> None:
    """A designed empty/hold state — the crafted presentation of 'nothing to show',
    which is where student projects usually fall back to a blank panel or a traceback."""
    st.markdown(
        f'<div class="empty"><div class="empty-icon"><i class="ti {icon}"></i></div>'
        f'<div class="empty-t">{title}</div><div class="empty-d">{body}</div></div>',
        unsafe_allow_html=True)



def takeaway(text: str) -> None:
    """A business takeaway under a chart — styled as a deliberate conclusion rather
    than fine print. The chart shows what happened; this says what it means."""
    st.markdown(f'<div class="takeaway"><span class="tk-i">▸</span>'
                f'<span>{text}</span></div>', unsafe_allow_html=True)


def report_block(number: str, title: str, body_html: str) -> None:
    """A numbered section of the executive report — consulting-deliverable styling."""
    st.markdown(
        f'<div class="rpt"><div class="rpt-h"><span class="rpt-n">{number}</span>'
        f'<span class="rpt-t">{title}</span></div>'
        f'<div class="rpt-b">{body_html}</div></div>', unsafe_allow_html=True)


def recommendation(verdict: str, headline: str, confidence: str, conf_tone: str,
                   roi: str, reasons: list[str], caveat: str = "") -> None:
    """A decision card that explains itself.

    A recommendation without reasoning is an assertion. This surfaces the confidence,
    the return, and the specific evidence the platform used — so the operator can
    audit the decision rather than take it on trust."""
    bullets = "".join(f'<li>{r}</li>' for r in reasons)
    cav = f'<div class="rc-caveat">{caveat}</div>' if caveat else ""
    st.markdown(
        f'<div class="reco">'
        f'  <div class="rc-head">'
        f'    <div><div class="rc-cap">Recommendation</div>'
        f'      <div class="rc-verdict">{verdict}</div>'
        f'      <div class="rc-headline">{headline}</div></div>'
        f'    <div class="rc-metrics">'
        f'      <div class="rc-m"><span class="rc-mk">Confidence</span>'
        f'        <span class="rc-mv {conf_tone}">{confidence}</span></div>'
        f'      <div class="rc-m"><span class="rc-mk">Return per ₹</span>'
        f'        <span class="rc-mv">{roi}</span></div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="rc-why"><span class="rc-cap">Why this decision</span>'
        f'    <ul>{bullets}</ul></div>{cav}'
        f'</div>', unsafe_allow_html=True)


def command_bar(brand_sub: str, health: list[tuple[str, str, str]],
                kpis: list[tuple[str, str]], scenario: str, is_plan: bool,
                meta: str) -> None:
    """The persistent global command bar — rendered ONCE in the app chrome.

    Carries platform health, the live campaign KPIs and the build metadata, so no
    page has to repeat them. Everything here is global state; page-specific
    context belongs in the page header."""
    chips = "".join(
        f'<span class="cb-chip {tone}"><i></i>{k}<b>{v}</b></span>'
        for k, v, tone in health)
    cells = "".join(
        f'<div class="cb-kpi"><span class="cb-k">{k}</span>'
        f'<span class="cb-v">{v}</span></div>' for k, v in kpis)
    flag = ("cb-plan" if is_plan else "cb-custom")
    st.markdown(
        f'<div class="cmdbar">'
        f'  <div class="cb-row cb-top">'
        f'    <div class="cb-brand"><span class="cb-mark">◤</span>'
        f'      <span class="cb-name">RetainIQ <b>India</b></span>'
        f'      <span class="cb-sub">{brand_sub}</span></div>'
        f'    <div class="cb-health">{chips}</div>'
        f'  </div>'
        f'  <div class="cb-row cb-bottom">'
        f'    <div class="cb-kpis">{cells}</div>'
        f'    <div class="cb-state"><span class="cb-flag {flag}">{scenario}</span>'
        f'      <span class="cb-meta">{meta}</span></div>'
        f'  </div>'
        f'</div>', unsafe_allow_html=True)


def page_title(title: str, question: str) -> None:
    """Page-level identity only. Global KPIs live in the command bar; this is just
    'which page am I on, and what question does it answer'."""
    st.markdown(
        f'<div class="pagehead"><h1 class="ph-t">{title}</h1>'
        f'<p class="ph-q">{question}</p></div>', unsafe_allow_html=True)


def color_legend() -> None:
    """The full colour legend — shown on the Executive Dashboard only, where users
    land. Every accent maps to one business meaning; the system is intuitive after
    this first page, so other pages use small badges rather than repeating it."""
    items = [
        (T.RISK_C, "Risk", "at-risk revenue, churn exposure"),
        (T.OPP_C, "Opportunity", "retained value, upside"),
        (T.REVENUE_C, "Revenue", "portfolio value, ARPU"),
        (T.RECO_C, "Recommendation", "the recommended action"),
        (T.ALERT_C, "Alert", "loss, urgent attention"),
    ]
    cells = "".join(
        f'<span class="lg-item"><span class="lg-sw" style="background:{c}"></span>'
        f'<span class="lg-k">{k}</span><span class="lg-d">{d}</span></span>'
        for c, k, d in items)
    st.markdown(f'<div class="legend"><span class="lg-cap">Colour key</span>{cells}</div>',
                unsafe_allow_html=True)


def badge(text: str, kind: str = "neutral") -> str:
    """A small inline status badge (returns HTML). `kind` maps to a family colour so
    the colour system stays consistent without repeating the full legend."""
    return f'<span class="badge b-{kind}">{text}</span>'


def status_strip(question: str, verdict: str, tone: str,
                 cells: list[tuple[str, str]]) -> None:
    """Thin one-line strip: the page question on the left, live campaign figures
    inline on the right. Replaces the full-width hero banner (the MacroPulse tell)."""
    led = {"hot": "var(--blue)", "up": "var(--green)", "down": "var(--amber)",
           "flat": "var(--steel)"}.get(tone, "var(--steel)")
    body = "".join(
        f'<span class="ss-cell"><span class="ss-k">{k}</span>'
        f'<span class="ss-v">{v}</span></span>' for k, v in cells)
    st.markdown(
        f'<div class="statusstrip">'
        f'  <div class="ss-q">{question}</div>'
        f'  <div class="ss-r"><span class="ss-verdict" style="color:{led}">'
        f'  <span class="ss-led" style="background:{led}"></span>{verdict}</span>{body}</div>'
        f'</div>', unsafe_allow_html=True)



def workflow(active: str) -> None:
    """Operational workflow breadcrumb."""
    steps = ["Budget", "Optimizer", "Offer assignment", "Contact list",
             "Recommendation", "Export"]
    out = []
    for i, s in enumerate(steps):
        out.append(f'<span class="step {"on" if s == active else ""}">{s}</span>')
        if i < len(steps) - 1:
            out.append('<span class="sep">›</span>')
    st.markdown(f'<div class="flow">{"".join(out)}</div>', unsafe_allow_html=True)


# ── content ──────────────────────────────────────────────────────────────────
def metric(label: str, value: str, sub: str = "", tag: str = "",
           tone: str = "flat", hero: bool = False, bar: float | None = None,
           dot: str | None = None, alert: bool = False) -> None:
    """A KPI card. `hero` promotes it to the lead card (blue rule, larger numeral)."""
    t = f'<div class="k-tag {tone}">{tag}</div>' if tag else ""
    b = (f'<div class="bar"><i style="width:{max(0, min(bar, 100)):.1f}%"></i></div>'
         if bar is not None else "")
    s = f'<div class="k-sub">{sub}</div>' if sub else ""
    cls = "card lead" if hero else ("card alert" if alert else "card")
    st.markdown(
        f'<div class="{cls}"><div class="k-lab">{label}</div>'
        f'<div class="k-val">{value}</div>{t}{b}{s}</div>', unsafe_allow_html=True)


def section(title: str, hint: str = "") -> None:
    h = f'<div class="hint">{hint}</div>' if hint else ""
    st.markdown(f'<div class="sec"><h3>{title}</h3>{h}</div>', unsafe_allow_html=True)


def brief(text: str) -> None:
    """The single business question this page answers."""
    st.markdown(f'<div class="topbar-q" style="margin:-0.55rem 0 1rem">{text}</div>',
                unsafe_allow_html=True)


def note(html: str) -> None:
    st.markdown(f'<div class="note">{html}</div>', unsafe_allow_html=True)


def ledger(title: str, rows: list[tuple[str, str]], sub: str = "") -> None:
    body = "".join(f'<div class="row"><span class="n">{n}</span>'
                   f'<span class="v">{v}</span></div>' for n, v in rows)
    s = f'<div class="k-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="card"><div class="k-lab">{title}</div>{body}{s}</div>',
                unsafe_allow_html=True)


# ── navigation rail ──────────────────────────────────────────────────────────
def rail_brand() -> None:
    st.markdown(
        '<div class="brand"><div class="brand-mark">RQ</div>'
        '<div><div class="brand-name">RetainIQ India</div>'
        '<div class="brand-sub">Customer Decision Intelligence<br>Enterprise Edition</div>'
        '</div></div><div class="rail-div"></div>', unsafe_allow_html=True)


def rail_cap(text: str) -> None:
    st.markdown(f'<div class="rail-cap">{text}</div>', unsafe_allow_html=True)


def rail_kv(value: str, sub: str) -> None:
    st.markdown(f'<div class="rail-kv">{value}<small>{sub}</small></div>',
                unsafe_allow_html=True)