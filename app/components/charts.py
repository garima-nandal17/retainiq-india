"""
charts.py — RetainIQ enterprise visuals (Day 13 v2, UI only).

Every figure is built from an existing artifact in `reports/` or the frozen
`customer_value.parquet` / `feature_customer` view. Nothing is recomputed:
arithmetic here is presentation-only aggregation of stored columns.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from . import theme as T

CONF = {"displayModeBar": False}


def _f(**kw) -> go.Figure:
    f = go.Figure()
    f.update_layout(**T.layout(**kw))
    return f


# ── donuts ───────────────────────────────────────────────────────────────────
def donut(labels, values, centre_top: str, centre_sub: str,
          colors=None, height: int = 290) -> go.Figure:
    f = _f(height=height, showlegend=True)
    f.add_trace(go.Pie(
        labels=labels, values=values, hole=.68, sort=False,
        marker=dict(colors=colors or T.SEQ, line=dict(color=T.CANVAS, width=2)),
        textinfo="percent", textfont=dict(family="Inter, sans-serif", size=10,
                                          color=T.TEXT),
        hovertemplate="%{label}<br>%{value:,} subscribers (%{percent})<extra></extra>"))
    f.update_layout(
        legend=dict(orientation="v", x=1.0, y=.5, font=dict(size=10)),
        annotations=[
            dict(text=centre_top, x=.5, y=.55, showarrow=False,
                 font=dict(family="Inter, sans-serif", size=24, color=T.TEXT)),
            dict(text=centre_sub, x=.5, y=.40, showarrow=False,
                 font=dict(family="Inter, sans-serif", size=9, color=T.MUTED)),
        ], margin=dict(l=6, r=6, t=14, b=6))
    return f


# ── churn / retention funnel ────────────────────────────────────────────────
def churn_funnel(stages: list[tuple[str, float]]) -> go.Figure:
    labels = [s for s, _ in stages]
    vals = [v for _, v in stages]
    f = _f(height=330)
    # ordered stages -> ONE hue deepening, not five competing colours
    ramp = ["#2C5A9E", "#356BB8", "#3E7CD1", "#5B93DE", "#84B0E8"]
    f.add_trace(go.Funnel(
        y=labels, x=vals, textposition="inside",
        textinfo="value+percent initial",
        textfont=dict(family="Inter, sans-serif", size=11, color="#FFFFFF"),
        marker=dict(color=ramp[:len(labels)],
                    line=dict(color=T.CANVAS, width=2)),
        connector=dict(line=dict(color=T.BORDER, width=1)),
        hovertemplate="%{y}<br>%{x:,.0f} subscribers<extra></extra>"))
    f.update_layout(margin=dict(l=8, r=8, t=16, b=8))
    return f


# ── revenue waterfall ───────────────────────────────────────────────────────
def revenue_waterfall(gross_save: float, offer_cost: float, net: float) -> go.Figure:
    """Campaign revenue bridge: gross recovery − offer cost = net retained."""
    f = _f(height=330)
    f.add_trace(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Gross recovery", "Offer deployment cost", "Net revenue retained"],
        y=[gross_save, -offer_cost, net],
        text=[f"₹{gross_save:,.0f}", f"−₹{offer_cost:,.0f}", f"₹{net:,.0f}"],
        textposition="outside",
        textfont=dict(family="Inter, sans-serif", size=10, color=T.TEXT),
        increasing=dict(marker=dict(color="#4E9E7E")),   # muted green (recovery)
        decreasing=dict(marker=dict(color="#C77B72")),   # muted coral (cost)
        totals=dict(marker=dict(color=T.BLUE)),           # brand blue = the answer
        connector=dict(line=dict(color=T.BORDER, width=1)),
        hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>"))
    f.update_layout(showlegend=False, yaxis_title="₹", margin=dict(l=8, r=8, t=26, b=8))
    return f


# ── sankey: SIM base → risk band → offer deployed ───────────────────────────
def retention_sankey(contacts: pd.DataFrame, total_subs: int) -> go.Figure:
    risks = ["High", "Medium", "Low"]
    offers = sorted(contacts.offer.unique().tolist())
    nodes = ["SIM base"] + [f"{r} risk" for r in risks] + offers + ["Not contacted"]
    idx = {n: i for i, n in enumerate(nodes)}

    src, tgt, val, col = [], [], [], []
    contacted_by_risk = contacts.risk_segment.value_counts().to_dict()
    rc = {"High": T.RISK[2], "Medium": T.RISK[1], "Low": T.RISK[0]}

    for r in risks:
        n = int(contacted_by_risk.get(r, 0))
        if n:
            src.append(idx["SIM base"]); tgt.append(idx[f"{r} risk"]); val.append(n)
            col.append("rgba(59,130,246,0.20)")
    uncontacted = total_subs - len(contacts)
    src.append(idx["SIM base"]); tgt.append(idx["Not contacted"]); val.append(uncontacted)
    col.append("rgba(148,163,184,0.10)")

    link_rgba = {"High": "rgba(217,115,106,0.22)",
                 "Medium": "rgba(224,164,88,0.22)",
                 "Low": "rgba(79,176,172,0.22)"}
    for r in risks:
        sub = contacts[contacts.risk_segment == r]
        for o in offers:
            n = int((sub.offer == o).sum())
            if n:
                src.append(idx[f"{r} risk"]); tgt.append(idx[o]); val.append(n)
                col.append(link_rgba[r])

    node_cols = [T.STEEL] + [rc[r] for r in risks] + [T.BLUE] * len(offers) + [T.MUTED]
    f = _f(height=380)
    f.add_trace(go.Sankey(
        arrangement="snap",
        node=dict(pad=16, thickness=13, label=nodes, color=node_cols,
                  line=dict(color=T.CANVAS, width=1),
                  hovertemplate="%{label}<br>%{value:,} subscribers<extra></extra>"),
        link=dict(source=src, target=tgt, value=val, color=col,
                  hovertemplate="%{source.label} → %{target.label}"
                                "<br>%{value:,} subscribers<extra></extra>")))
    f.update_layout(font=dict(family="Inter, sans-serif", size=10, color=T.TEXT),
                    margin=dict(l=6, r=6, t=16, b=6))
    return f


# ── treemap: revenue leakage ────────────────────────────────────────────────
def leakage_treemap(cv: pd.DataFrame) -> go.Figure:
    g = (cv.groupby(["contract_type", "risk_segment"], as_index=False)
           .agg(leakage=("value_at_risk_inr", "sum"), subs=("customer_id", "size")))
    labels, parents, values, colors = [], [], [], []
    rc = {"High": T.RISK[2], "Medium": T.RISK[1], "Low": T.RISK[0]}
    for ct in g.contract_type.unique():
        labels.append(ct); parents.append(""); values.append(0); colors.append(T.SURFACE_2)
    for r in g.itertuples():
        labels.append(f"{r.risk_segment} · {r.subs:,}")
        parents.append(r.contract_type)
        values.append(float(r.leakage))
        colors.append(rc[r.risk_segment])
    f = _f(height=340)
    f.add_trace(go.Treemap(
        labels=labels, parents=parents, values=values, branchvalues="remainder",
        marker=dict(colors=colors, line=dict(color=T.CANVAS, width=2)),
        textfont=dict(family="Inter, sans-serif", size=11, color="#0A0F1A"),
        texttemplate="<b>%{label}</b><br>₹%{value:,.0f}",
        hovertemplate="%{parent} · %{label}<br>revenue leakage ₹%{value:,.0f}<extra></extra>"))
    f.update_layout(margin=dict(l=4, r=4, t=16, b=4))
    return f


# ── gauges ──────────────────────────────────────────────────────────────────
def gauge(value: float, title: str, suffix: str = "%", vmax: float = 100,
          bands=None, color: str | None = None, height: int = 190) -> go.Figure:
    color = color or T.BLUE
    steps = bands or [dict(range=[0, vmax], color="rgba(148,163,184,0.10)")]
    f = _f(height=height)
    f.add_trace(go.Indicator(
        mode="gauge+number", value=value,
        number=dict(suffix=suffix, font=dict(family="Inter, sans-serif",
                                             size=24, color=T.TEXT)),
        title=dict(text=title, font=dict(family="Inter, sans-serif",
                                         size=9, color=T.MUTED)),
        gauge=dict(
            axis=dict(range=[0, vmax], tickcolor=T.MUTED,
                      tickfont=dict(size=8, color=T.MUTED)),
            bar=dict(color=color, thickness=.7),
            bgcolor="rgba(0,0,0,0)", borderwidth=1, bordercolor=T.BORDER,
            steps=steps)))
    f.update_layout(margin=dict(l=14, r=14, t=30, b=6))
    return f


# ── campaign progress (offer deployment) ────────────────────────────────────
def campaign_progress(mix: list[dict], budget: float) -> go.Figure:
    df = pd.DataFrame(mix)
    f = _f(height=250)
    f.add_trace(go.Bar(
        y=df.offer, x=df.spend, orientation="h", name="Deployed",
        marker=dict(color=[T.BLUE, T.STEEL, T.TEAL][:len(df)], line_width=0),
        text=[f"₹{v:,.0f}" for v in df.spend], textposition="outside",
        textfont=dict(family="Inter, sans-serif", size=10, color=T.TEXT),
        hovertemplate="%{y}<br>₹%{x:,.0f} deployed<extra></extra>"))
    f.update_layout(showlegend=False, xaxis_title="Budget deployed (₹)",
                    margin=dict(l=8, r=60, t=14, b=8))
    return f


# ── strategy comparison ─────────────────────────────────────────────────────
def strategy_bars(results: dict, height: int = 300) -> go.Figure:
    order = ["optimizer_roi", "rank_by_probability", "random", "contact_everyone"]
    names = {"optimizer_roi": "RetainIQ optimizer", "rank_by_probability": "Churn-risk ranking",
             "random": "Random outreach", "contact_everyone": "Blanket campaign"}
    vals = [results[k]["net_retained_inr"] for k in order]
    cols = [T.BLUE if v == max(vals) else ("#4FB0AC" if v > 0 else "#C77B72") for v in vals]
    f = _f(height=height)
    f.add_trace(go.Bar(x=[names[k] for k in order], y=vals, marker_color=cols,
                       marker_line_width=0,
                       text=[f"₹{v:,.0f}" for v in vals], textposition="outside",
                       textfont=dict(family="Inter, sans-serif", size=10, color=T.TEXT),
                       hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>"))
    f.add_hline(y=0, line=dict(color=T.MUTED, width=.9))
    f.update_layout(showlegend=False, yaxis_title="Net revenue retained (₹)")
    return f


def profit_curve(curve: list[dict], optimal: float) -> go.Figure:
    df = pd.DataFrame(curve)
    f = _f(height=310)
    f.add_trace(go.Scatter(x=df.threshold, y=df.net_retained_inr, mode="lines",
                           line=dict(color=T.BLUE, width=2.4), fill="tozeroy",
                           fillcolor="rgba(59,130,246,0.10)",
                           hovertemplate="cut-off %{x:.2f}<br>₹%{y:,.0f}<extra></extra>"))
    f.add_vline(x=optimal, line=dict(color="#4E9E7E", dash="dash", width=1.5),
                annotation_text=f"optimal {optimal:.2f}",
                annotation_font=dict(color=T.GREEN, size=10))
    f.add_vline(x=.5, line=dict(color="#C77B72", dash="dot", width=1.2),
                annotation_text="naive 0.50", annotation_font=dict(color=T.RED, size=10))
    f.add_hline(y=0, line=dict(color=T.MUTED, width=.8))
    f.update_layout(xaxis_title="Contact cut-off (churn probability)",
                    yaxis_title="Net revenue retained (₹)")
    return f


def decile_lift(deciles: list[dict]) -> go.Figure:
    df = pd.DataFrame(deciles)
    f = _f(height=300)
    f.add_trace(go.Bar(x=df.decile, y=df.churn_rate, name="Churn rate",
                       marker_color=T.STEEL, marker_line_width=0, opacity=.85,
                       hovertemplate="band %{x}<br>%{y:.1%}<extra></extra>"))
    f.add_trace(go.Scatter(x=df.decile, y=df.cum_capture, name="Churners captured",
                           yaxis="y2", mode="lines+markers",
                           line=dict(color=T.BLUE, width=2.4),
                           marker=dict(size=5, color=T.BLUE),
                           hovertemplate="top %{x} bands<br>%{y:.0%}<extra></extra>"))
    f.update_layout(xaxis_title="Risk band (1 = highest)",
                    yaxis=dict(title="Churn rate", tickformat=".0%"),
                    yaxis2=dict(overlaying="y", side="right", tickformat=".0%",
                                range=[0, 1.05], gridcolor="rgba(0,0,0,0)"),
                    legend=dict(orientation="h", y=1.18, x=0))
    return f


def drivers(coef_drivers: list[dict], n: int = 10) -> go.Figure:
    df = pd.DataFrame(coef_drivers).head(n).iloc[::-1]
    cols = ["#C77B72" if c > 0 else "#4E9E7E" for c in df.coef]
    f = _f(height=360)
    f.add_trace(go.Bar(y=df.feature, x=df.coef, orientation="h",
                       marker_color=cols, marker_line_width=0,
                       hovertemplate="%{y}<br>%{x:+.3f}<extra></extra>"))
    f.add_vline(x=0, line=dict(color=T.MUTED, width=.9))
    f.update_layout(showlegend=False,
                    xaxis_title="←  retains subscriber      drives churn  →")
    return f


def arpu_by_risk(cv: pd.DataFrame) -> go.Figure:
    f = _f(height=300)
    for seg, col in [("Low", T.RISK[0]), ("Medium", T.RISK[1]), ("High", T.RISK[2])]:
        s = cv[cv.risk_segment == seg]
        if len(s):
            f.add_trace(go.Violin(y=s.monthly_charges_inr, name=seg, line_color=col,
                                  fillcolor=col, opacity=.30, meanline_visible=True,
                                  points=False, hoverinfo="y"))
    f.update_layout(yaxis_title="Monthly ARPU (₹)", showlegend=False,
                    xaxis_title="Network risk segment")
    return f



def budget_response(curve: list[dict], current: float) -> go.Figure:
    df = pd.DataFrame(curve)
    f = _f(height=290)
    f.add_trace(go.Scatter(x=df.budget_inr, y=df.net_retained_inr, mode="lines+markers",
                           line=dict(color=T.BLUE, width=2.4),
                           marker=dict(size=5, color=T.BLUE), fill="tozeroy",
                           fillcolor="rgba(59,130,246,0.10)",
                           hovertemplate="budget ₹%{x:,.0f}<br>net ₹%{y:,.0f}<extra></extra>"))
    f.add_vline(x=current, line=dict(color="#4E9E7E", dash="dash", width=1.5),
                annotation_text="in force", annotation_font=dict(color=T.GREEN, size=10))
    f.update_layout(xaxis_title="Retention budget (₹)", yaxis_title="Net retained (₹)")
    return f


def sensitivity_heatmap(two_way: dict) -> go.Figure:
    """Acceptance × offer-cost grid — the two assumptions that matter most."""
    df = pd.DataFrame(two_way)
    f = _f(height=320)
    f.add_trace(go.Heatmap(
        z=df.values, x=list(df.columns), y=list(df.index),
        colorscale=[[0, "#C77B72"], [0.5, T.SURFACE_2], [1, "#4E9E7E"]],
        zmid=0, colorbar=dict(title="₹ net", thickness=10,
                              tickfont=dict(size=9, color=T.MUTED)),
        text=[[f"₹{v:,.0f}" for v in row] for row in df.values],
        texttemplate="%{text}", textfont=dict(family="Inter, sans-serif",
                                              size=9, color=T.TEXT),
        hovertemplate="%{y} · %{x}<br>net ₹%{z:,.0f}<extra></extra>"))
    f.update_layout(xaxis_title="Offer cost vs plan", yaxis_title="Acceptance vs plan",
                    margin=dict(l=8, r=8, t=16, b=8))
    return f


def subscriber_lifecycle(cohort: list[dict]) -> go.Figure:
    """Tenure cohorts as a lifecycle: retained vs churned across the base."""
    df = pd.DataFrame(cohort)
    f = _f(height=300)
    f.add_trace(go.Bar(x=df.tenure_bucket, y=df.retained, name="On network",
                       marker_color="#4E9E7E", marker_line_width=0,
                       hovertemplate="%{x} months<br>%{y:,} on network<extra></extra>"))
    f.add_trace(go.Bar(x=df.tenure_bucket, y=df.churned, name="Churned",
                       marker_color="#C77B72", marker_line_width=0,
                       hovertemplate="%{x} months<br>%{y:,} churned<extra></extra>"))
    f.add_trace(go.Scatter(x=df.tenure_bucket, y=df.churn_rate, name="Churn rate",
                           yaxis="y2", mode="lines+markers",
                           line=dict(color=T.BLUE, width=2.4),
                           marker=dict(size=6, color=T.BLUE),
                           hovertemplate="%{x} months<br>%{y:.1%} churn<extra></extra>"))
    f.update_layout(barmode="stack", xaxis_title="Tenure on network (months)",
                    yaxis_title="Subscribers",
                    yaxis2=dict(overlaying="y", side="right", tickformat=".0%",
                                range=[0, df.churn_rate.max() * 1.2],
                                gridcolor="rgba(0,0,0,0)"),
                    legend=dict(orientation="h", y=1.16, x=0))
    return f


def tornado(one_way: dict, baseline: float) -> go.Figure:
    pretty = {"acceptance_scale": "Offer acceptance", "offer_cost_multiplier": "Offer cost",
              "gross_margin": "Gross margin", "budget_inr": "Retention budget"}
    labels, lows, highs = [], [], []
    for k, rows in one_way.items():
        vals = [r["net_retained_inr"] for r in rows]
        labels.append(pretty.get(k, k)); lows.append(min(vals) - baseline)
        highs.append(max(vals) - baseline)
    order = sorted(range(len(labels)), key=lambda i: highs[i] - lows[i])
    f = _f(height=290)
    f.add_trace(go.Bar(y=[labels[i] for i in order], x=[highs[i] - lows[i] for i in order],
                       base=[lows[i] for i in order], orientation="h",
                       marker_color=T.BLUE, marker_line_width=0, opacity=.9,
                       hovertemplate="%{y}<br>swing ₹%{x:,.0f}<extra></extra>"))
    f.add_vline(x=0, line=dict(color=T.BLUE, dash="dash", width=1.3))
    f.update_layout(showlegend=False, xaxis_title="Swing in net retained vs plan (₹)")
    return f