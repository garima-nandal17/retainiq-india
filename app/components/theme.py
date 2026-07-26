"""
theme.py — RetainIQ India design system (Enterprise Edition).

Direction: deep-navy enterprise console — Azure Portal / Datadog / Cisco Control
Center. Restraint is the point: the dashboard should impress through clarity and
decision support, never through colour or size.

Rules encoded here:
  · one brand accent (blue). Teal is the secondary series. Green/amber/red are
    SEMANTIC only — they mean retained / caution / alert, never decoration.
  · zero gradients. zero animation except 150ms hover transitions.
  · Inter throughout, with tabular numerals so figures align like an instrument.
  · 8pt spacing grid, 6px radius, a single shadow elevation.
  · hierarchy comes from placement and whitespace, not from font size.

No business logic.
"""
from __future__ import annotations

import streamlit as st

# ── surfaces (Palette A · plum-tinted charcoal) ──────────────────────────────
CANVAS = "#0E0B12"      # deep plum-charcoal base
SURFACE = "#171320"     # cards
SURFACE_2 = "#201A2E"   # raised: tables, wells
BORDER = "rgba(200,180,210,0.14)"    # plum-tinted hairline
BORDER_S = "rgba(200,180,210,0.26)"  # stronger

# ── type ─────────────────────────────────────────────────────────────────────
TEXT = "#F2EEF5"
MUTED = "#9E93AC"
FAINT = "#6E6479"

# ── the single rose/plum family ──────────────────────────────────────────────
# Every accent lives in ONE hue band; roles are separated by lightness + warmth,
# not by jumping to unrelated hues. Each colour carries ONE business meaning.
ACCENT = "#C77DA0"       # dusty rose — the brand
RISK_C = "#B0537A"       # deep saturated rose  → risk / at-risk revenue / churn
OPP_C = "#D9A5C0"        # light mauve          → opportunity / retained / positive
REVENUE_C = "#8E6BA8"    # cool plum-violet     → revenue / value / money
RECO_C = "#C77DA0"       # brand rose           → recommendation / the action
ALERT_C = "#D96B84"      # warm coral-rose      → alert / loss / urgency
NEUTRAL_C = "#6E6479"    # muted plum-grey      → context / "other" in busy charts

# Back-compat aliases so existing chart code keeps working, now pointing at family:
BLUE = RECO_C            # was brand primary  → recommendation rose
BLUE_FILL = "#A85E86"    # muted brand for large filled areas
TEAL = OPP_C             # secondary series   → opportunity mauve
STEEL = NEUTRAL_C        # neutral            → plum-grey
GREEN = OPP_C            # positive           → opportunity (light mauve)
AMBER = REVENUE_C        # was caution        → revenue plum
RED = ALERT_C            # alert / loss       → coral-rose

# categorical ramp — LIGHTNESS steps within the family (+ 1 neutral) for busy charts
CAT = ["#C77DA0",        # brand rose
       "#8E6BA8",        # plum-violet
       "#D9A5C0",        # light mauve
       "#A85E86",        # deep rose
       "#6E6479",        # plum-grey neutral
       "#B98FC0"]        # soft lilac
# risk-ordered ramp (low→high): light mauve → mid rose → deep saturated rose
RISK = [OPP_C, ACCENT, RISK_C]

SEQ = CAT

PLOT_BG = "rgba(0,0,0,0)"
GRID = "rgba(200,180,210,0.07)"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3/dist/tabler-icons.min.css');

:root {{
  --canvas:{CANVAS}; --surface:{SURFACE}; --surface-2:{SURFACE_2};
  --border:{BORDER}; --border-s:{BORDER_S};
  --text:{TEXT}; --muted:{MUTED}; --faint:{FAINT};
  --blue:{BLUE}; --teal:{TEAL}; --steel:{STEEL};
  --green:{GREEN}; --amber:{AMBER}; --red:{RED};
  --accent:{ACCENT}; --risk:{RISK_C}; --opp:{OPP_C}; --revenue:{REVENUE_C};
  --reco:{RECO_C}; --alert:{ALERT_C}; --neutral:{NEUTRAL_C};
  --shadow: 0 1px 2px rgba(0,0,0,.30);
  --r: 6px;
}}

#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ display:none !important; }}
/* keep the header transparent but PRESENT — it holds the sidebar expand control */
header[data-testid="stHeader"] {{ background:transparent !important; height:0 !important; }}
/* make sure the sidebar and its collapse toggle can never be hidden */
[data-testid="stSidebar"] {{ display:flex !important; }}
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{
  display:flex !important; visibility:visible !important; }}

/* ── product layer: onboarding, state feedback, empty states ─────────────── */
.onboard {{ border:1px solid var(--border-s);border-left:3px solid var(--blue);
  border-radius:var(--r);background:var(--surface);padding:.9rem 1.1rem;
  margin-bottom:1rem;box-shadow:var(--shadow); }}
.onboard-t {{ font-size:1rem;font-weight:600;color:var(--text);
  display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem; }}
.onboard-t .dot {{ width:7px;height:7px;border-radius:50%;background:var(--blue);
  display:inline-block; }}
.onboard-d {{ font-size:.875rem;color:var(--muted);line-height:1.6;max-width:74ch; }}
.onboard-d b {{ color:var(--text);font-weight:600; }}

.sflag {{ display:inline-flex;align-items:center;gap:.45rem;font-size:.78rem;
  font-weight:500;padding:.35rem .7rem;border-radius:var(--r);margin-bottom:.9rem;
  border:1px solid var(--border); }}
.sflag .ti {{ font-size:.875rem; }}
.sflag.plan {{ color:var(--muted);background:var(--surface); }}
.sflag.custom {{ color:var(--blue);background:rgba(199,125,160,.12);
  border-color:rgba(199,125,160,.30); }}

.empty {{ display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:2.4rem 1rem;border:1px dashed var(--border-s);
  border-radius:var(--r);background:var(--surface);gap:.5rem; }}
.empty-icon {{ width:44px;height:44px;border-radius:50%;display:grid;place-items:center;
  background:var(--surface-2);color:var(--muted);font-size:1.375rem;margin-bottom:.2rem; }}
.empty-t {{ font-size:1rem;font-weight:600;color:var(--text); }}
.empty-d {{ font-size:.78rem;color:var(--muted);line-height:1.6;max-width:52ch; }}

/* ── colour legend (Executive landing only) ──────────────────────────────── */
.legend {{ display:flex;gap:1.4rem;flex-wrap:wrap;align-items:center;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:.7rem 1rem;margin-bottom:1.1rem;box-shadow:var(--shadow); }}
.lg-item {{ display:inline-flex;align-items:center;gap:.5rem;min-width:0; }}
.lg-sw {{ width:12px;height:12px;border-radius:3px;flex:none; }}
.lg-k {{ font-size:.78rem;font-weight:600;color:var(--text); }}
.lg-d {{ font-size:.72rem;color:var(--muted); }}

/* ── narrative spine: next-step link ─────────────────────────────────────── */
.nextstep {{ display:flex;align-items:center;gap:.8rem;margin:1.75rem 0 .5rem;
  padding:.8rem 1rem;background:var(--surface);border:1px solid var(--border);
  border-left:3px solid var(--reco);border-radius:var(--r);box-shadow:var(--shadow); }}
.ns-cap {{ font-size:.62rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--faint);flex:none; }}
.ns-q {{ font-size:.85rem;color:var(--muted);flex:1; }}
.ns-p {{ font-size:.82rem;font-weight:600;color:var(--reco);flex:none; }}

/* ── top navigation (main-content, always visible) ───────────────────────── */
.topnav-brand {{ display:flex;align-items:center;gap:.6rem;margin:0 0 .9rem; }}
.tnb-mark {{ width:30px;height:30px;flex:none;border-radius:7px;background:var(--accent);
  display:grid;place-items:center;color:#1a0f16;font-size:.95rem;font-weight:700; }}
.tnb-name {{ font-size:1.05rem;font-weight:500;color:var(--text);letter-spacing:-0.01em; }}
.tnb-name b {{ font-weight:700;color:var(--accent); }}
.tnb-sub {{ font-size:.74rem;color:var(--faint);margin-left:.35rem; }}
.topnav-rule {{ height:1px;background:var(--border);margin:.15rem 0 1.4rem; }}

/* style the nav row buttons as flat tabs */
div[data-testid="stHorizontalBlock"]:has(button[kind]) {{ gap:.3rem !important; }}
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-primary"] {{
  font-family:'Inter',sans-serif !important;font-weight:500 !important;
  font-size:.86rem !important;border-radius:8px !important; }}

/* ── narrative spine: next-step pointer ──────────────────────────────────── */
.nextstep {{ display:flex;align-items:center;justify-content:space-between;gap:1rem;
  margin-top:2rem;padding:.9rem 1.15rem;border:1px solid var(--border);
  border-left:3px solid var(--accent);border-radius:var(--r);
  background:linear-gradient(90deg, rgba(199,125,160,.06), transparent 70%); }}
.ns-q {{ font-size:.86rem;color:var(--muted); }}
.ns-go {{ font-size:.84rem;font-weight:600;color:var(--accent);
  display:inline-flex;align-items:center;gap:.4rem;white-space:nowrap; }}

/* ── colour legend (Executive only) + inline badges ──────────────────────── */
.legend {{ display:flex;align-items:center;gap:1.4rem;flex-wrap:wrap;
  padding:.6rem .9rem;margin-bottom:1.1rem;border:1px solid var(--border);
  border-radius:var(--r);background:var(--surface); }}
.lg-cap {{ font-size:.62rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--faint);white-space:nowrap; }}
.lg-item {{ display:inline-flex;align-items:center;gap:.4rem;white-space:nowrap; }}
.lg-sw {{ width:12px;height:12px;border-radius:3px;flex:none; }}
.lg-k {{ font-size:.78rem;font-weight:600;color:var(--text); }}
.lg-d {{ font-size:.72rem;color:var(--muted); }}

.badge {{ display:inline-flex;align-items:center;gap:.3rem;font-size:.68rem;font-weight:600;
  padding:.14rem .48rem;border-radius:4px;white-space:nowrap; }}
.badge::before {{ content:"";width:6px;height:6px;border-radius:50%;background:currentColor;
  opacity:.9; }}
.b-risk {{ color:{RISK_C};background:rgba(176,83,122,.13); }}
.b-opp {{ color:{OPP_C};background:rgba(217,165,192,.13); }}
.b-revenue {{ color:{REVENUE_C};background:rgba(142,107,168,.15); }}
.b-reco {{ color:{RECO_C};background:rgba(199,125,160,.13); }}
.b-alert {{ color:{ALERT_C};background:rgba(217,107,132,.14); }}
.b-neutral {{ color:{MUTED};background:rgba(158,147,172,.12); }}

/* ── chart business takeaway ─────────────────────────────────────────────── */
.takeaway {{ display:flex;gap:.45rem;align-items:flex-start;font-size:.76rem;
  color:var(--muted);line-height:1.55;margin:.15rem 0 .1rem;padding:.4rem .55rem;
  background:rgba(255,255,255,.018);border-left:2px solid var(--accent);
  border-radius:0 5px 5px 0; }}
.takeaway b {{ color:var(--text);font-weight:600; }}
.tk-i {{ color:var(--accent);flex:none;font-size:.7rem;line-height:1.7; }}

/* ── recommendation card ─────────────────────────────────────────────────── */
.reco {{ border:1px solid var(--border-s);border-left:3px solid var(--accent);
  border-radius:9px;background:linear-gradient(180deg, rgba(199,125,160,.06),
  transparent 55%), var(--surface);padding:.9rem 1.05rem;margin-bottom:.7rem;
  box-shadow:0 2px 8px rgba(0,0,0,.28);animation:rq-fade .28s ease both; }}
.rc-head {{ display:flex;align-items:flex-start;justify-content:space-between;
  gap:1.5rem;flex-wrap:wrap; }}
.rc-cap {{ font-size:.62rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;
  color:var(--faint); }}
.rc-verdict {{ font-size:1.5rem;font-weight:600;letter-spacing:-.02em;color:var(--text);
  line-height:1.15;margin-top:.1rem; }}
.rc-headline {{ font-size:.82rem;color:var(--muted);margin-top:.2rem;max-width:70ch; }}
.rc-metrics {{ display:flex;gap:1.6rem;flex:none; }}
.rc-m {{ display:flex;flex-direction:column;align-items:flex-end; }}
.rc-mk {{ font-size:.62rem;font-weight:500;letter-spacing:.05em;text-transform:uppercase;
  color:var(--faint); }}
.rc-mv {{ font-size:1rem;font-weight:600;color:var(--text);
  font-variant-numeric:tabular-nums; }}
.rc-mv.high {{ color:var(--opp); }} .rc-mv.med {{ color:var(--revenue); }}
.rc-mv.low {{ color:var(--alert); }}
.rc-why {{ margin-top:.75rem;padding-top:.65rem;border-top:1px solid var(--border); }}
.rc-why ul {{ margin:.35rem 0 0;padding-left:1.05rem; }}
.rc-why li {{ font-size:.78rem;color:var(--muted);line-height:1.6;margin-bottom:.15rem; }}
.rc-caveat {{ margin-top:.6rem;font-size:.73rem;color:var(--faint);
  border-left:2px solid var(--revenue);padding-left:.55rem;line-height:1.5; }}

/* ── consulting report blocks (Executive Brief) ──────────────────────────── */
.rpt {{ border:1px solid var(--border);border-radius:9px;background:var(--surface);
  padding:.85rem 1rem;margin-bottom:.7rem;box-shadow:0 1px 2px rgba(0,0,0,.26);
  animation:rq-fade .28s ease both; }}
.rpt-h {{ display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;
  padding-bottom:.4rem;border-bottom:1px solid var(--border); }}
.rpt-n {{ width:20px;height:20px;border-radius:5px;background:var(--surface-2);
  color:var(--accent);font-size:.66rem;font-weight:700;display:grid;place-items:center;
  flex:none; }}
.rpt-t {{ font-size:.78rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;
  color:var(--text); }}
.rpt-b {{ font-size:.83rem;color:var(--muted);line-height:1.65; }}
.rpt-b b, .rpt-b strong {{ color:var(--text);font-weight:600; }}

/* ══════════════════════════════════════════════════════════════════════════
   PRODUCTION POLISH — command bar · typography scale · density · interactions
   ══════════════════════════════════════════════════════════════════════════ */

/* ── persistent global command bar ───────────────────────────────────────── */
.cmdbar {{ border:1px solid var(--border);border-radius:10px;background:
  linear-gradient(180deg, var(--surface-2), var(--surface));
  box-shadow:0 1px 3px rgba(0,0,0,.35);margin:0 0 .85rem;overflow:hidden; }}
.cb-row {{ display:flex;align-items:center;justify-content:space-between;
  gap:1.25rem;padding:.6rem .95rem;flex-wrap:wrap; }}
.cb-top {{ border-bottom:1px solid var(--border); }}
.cb-brand {{ display:flex;align-items:center;gap:.55rem;min-width:0; }}
.cb-mark {{ width:26px;height:26px;flex:none;border-radius:6px;background:var(--accent);
  display:grid;place-items:center;color:#1a0f16;font-size:.8rem;font-weight:700; }}
.cb-name {{ font-size:.98rem;font-weight:500;color:var(--text);letter-spacing:-.01em;
  white-space:nowrap; }}
.cb-name b {{ font-weight:700;color:var(--accent); }}
.cb-sub {{ font-size:.72rem;color:var(--faint);white-space:nowrap;
  padding-left:.55rem;margin-left:.2rem;border-left:1px solid var(--border); }}
.cb-health {{ display:flex;gap:.4rem;flex-wrap:wrap; }}
.cb-chip {{ display:inline-flex;align-items:center;gap:.35rem;font-size:.7rem;
  font-weight:500;color:var(--muted);padding:.2rem .5rem;border-radius:5px;
  border:1px solid var(--border);background:rgba(255,255,255,.02);white-space:nowrap; }}
.cb-chip b {{ font-weight:600;color:var(--text);margin-left:.1rem; }}
.cb-chip i {{ width:5px;height:5px;border-radius:50%;background:var(--neutral);
  display:inline-block;flex:none; }}
.cb-chip.ok i {{ background:var(--opp); }} .cb-chip.ok b {{ color:var(--opp); }}
.cb-chip.warn i {{ background:var(--revenue); }} .cb-chip.warn b {{ color:var(--revenue); }}
.cb-chip.info i {{ background:var(--accent); }} .cb-chip.info b {{ color:var(--accent); }}
.cb-kpis {{ display:flex;gap:2rem;flex-wrap:wrap; }}
.cb-kpi {{ display:flex;flex-direction:column;line-height:1.2; }}
.cb-k {{ font-size:.62rem;font-weight:500;letter-spacing:.05em;text-transform:uppercase;
  color:var(--faint); }}
.cb-v {{ font-size:1rem;font-weight:600;color:var(--text);
  font-variant-numeric:tabular-nums;white-space:nowrap; }}
.cb-state {{ display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;
  justify-content:flex-end; }}
.cb-flag {{ font-size:.68rem;font-weight:600;padding:.2rem .55rem;border-radius:5px;
  white-space:nowrap;border:1px solid var(--border); }}
.cb-plan {{ color:var(--muted); }}
.cb-custom {{ color:var(--accent);background:rgba(199,125,160,.12);
  border-color:rgba(199,125,160,.30); }}
.cb-meta {{ font-size:.66rem;color:var(--faint);white-space:nowrap;
  font-variant-numeric:tabular-nums; }}

/* ── typography hierarchy: four clearly distinct levels ──────────────────── */
.pagehead {{ margin:.2rem 0 1rem; }}
.ph-t {{ font-size:1.6rem !important;font-weight:600;letter-spacing:-.025em;
  color:var(--text);margin:0 0 .15rem !important;line-height:1.15; }}
.ph-q {{ font-size:.9rem;color:var(--muted);margin:0 !important;line-height:1.45; }}

/* section heading — smaller, uppercase-tracked, clearly subordinate to page title */
.sec {{ display:flex;align-items:baseline;gap:.65rem;margin:1.35rem 0 .6rem !important;
  padding-bottom:.35rem;border-bottom:1px solid var(--border); }}
.sec h3 {{ margin:0 !important;font-size:.8rem !important;font-weight:600;
  letter-spacing:.04em;text-transform:uppercase;color:var(--text); }}
.sec .hint {{ font-size:.76rem;color:var(--faint);font-weight:400;text-transform:none;
  letter-spacing:0; }}

/* ── density: ~25% less vertical air ─────────────────────────────────────── */
.block-container {{ padding:.9rem 1.75rem 2rem !important;max-width:1600px; }}
div[data-testid="stVerticalBlock"] {{ gap:.55rem !important; }}
div[data-testid="stHorizontalBlock"] {{ gap:.65rem !important; }}
div[data-testid="stElementContainer"] {{ margin-bottom:0 !important; }}
[data-testid="stCaptionContainer"] {{ margin-top:-.25rem; }}
[data-testid="stCaptionContainer"] p {{ font-size:.73rem;line-height:1.5;
  color:var(--faint); }}
hr {{ margin:.8rem 0 !important; }}

/* ── cards: premium depth, restrained ────────────────────────────────────── */
.card {{ background:linear-gradient(180deg, rgba(255,255,255,.022), transparent 60%),
  var(--surface);border:1px solid var(--border);border-radius:9px;
  padding:.8rem .9rem;height:100%;
  box-shadow:0 1px 2px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.03);
  transition:border-color .18s ease, box-shadow .18s ease, transform .18s ease; }}
.card:hover {{ border-color:var(--border-s);
  box-shadow:0 4px 14px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.05);
  transform:translateY(-1px); }}
.card.lead {{ border-left:3px solid var(--accent); }}
.card.alert {{ border-left:3px solid var(--alert); }}
.k-lab {{ font-size:.68rem;font-weight:500;letter-spacing:.03em;text-transform:uppercase;
  color:var(--faint);margin-bottom:.35rem; }}
.k-val {{ font-size:1.5rem;font-weight:600;line-height:1.1;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; }}
.k-sub {{ font-size:.73rem;color:var(--muted);margin-top:.35rem;line-height:1.45; }}

/* ── tables: sticky header, zebra, hover ─────────────────────────────────── */
[data-testid="stDataFrame"] {{ border:1px solid var(--border) !important;
  border-radius:8px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.25); }}
[data-testid="stDataFrame"] [role="columnheader"] {{
  background:var(--surface-2) !important;position:sticky;top:0;z-index:2;
  font-size:.7rem !important;font-weight:600 !important;letter-spacing:.03em;
  text-transform:uppercase;color:var(--muted) !important;
  border-bottom:1px solid var(--border-s) !important; }}
[data-testid="stDataFrame"] [role="row"]:nth-child(even) {{
  background:rgba(255,255,255,.018); }}
[data-testid="stDataFrame"] [role="row"]:hover {{
  background:rgba(199,125,160,.09) !important; }}
[data-testid="stDataFrame"] [role="gridcell"] {{ font-size:.78rem !important;
  font-variant-numeric:tabular-nums; }}

/* ── micro-interactions ──────────────────────────────────────────────────── */
@keyframes rq-fade {{ from {{ opacity:0; transform:translateY(4px); }}
                      to   {{ opacity:1; transform:none; }} }}
.card, .legend, .cmdbar, .nextstep, [data-testid="stPlotlyChart"],
[data-testid="stDataFrame"] {{ animation:rq-fade .28s ease both; }}
.stButton button, .stDownloadButton button {{ transition:background .16s ease,
  border-color .16s ease, transform .1s ease, box-shadow .16s ease !important; }}
.stButton button:hover, .stDownloadButton button:hover {{
  box-shadow:0 2px 8px rgba(199,125,160,.20) !important; }}
.stButton button:active, .stDownloadButton button:active {{
  transform:translateY(1px) !important; }}
[data-testid="stPlotlyChart"] {{ border-radius:8px;overflow:hidden; }}

/* scroll anchor target */
#rq-top {{ position:absolute;top:0;height:0; }}

.statusstrip {{ display:flex;align-items:center;justify-content:space-between;gap:1.5rem;
  padding:.5rem .85rem;margin-bottom:1.1rem;border:1px solid var(--border);
  border-radius:var(--r);background:var(--surface);box-shadow:var(--shadow); }}
.ss-q {{ font-size:.875rem;color:var(--muted);min-width:0; }}
.ss-r {{ display:flex;align-items:center;gap:1.4rem;flex-wrap:wrap;justify-content:flex-end; }}
.ss-verdict {{ font-size:.78rem;font-weight:700;letter-spacing:.03em;white-space:nowrap;
  display:inline-flex;align-items:center;gap:.4rem; }}
.ss-led {{ width:6px;height:6px;border-radius:50%;flex:none; }}
.ss-cell {{ display:inline-flex;flex-direction:column;line-height:1.15; }}
.ss-k {{ font-size:.68rem;color:var(--faint);font-weight:500; }}
.ss-v {{ font-size:.875rem;color:var(--text);font-weight:600;
  font-variant-numeric:tabular-nums;white-space:nowrap; }}

.stApp {{ background:var(--canvas); color:var(--text);
  font-family:'Inter',-apple-system,'Segoe UI',system-ui,sans-serif;
  font-feature-settings:'tnum' 1,'cv05' 1; }}
.block-container {{ padding:1.25rem 2rem 3rem; max-width:1560px; }}

h1,h2,h3,h4 {{ font-family:'Inter',sans-serif; font-weight:600;
  letter-spacing:-0.011em; color:var(--text); }}
p, li, span, div {{ font-family:'Inter',sans-serif; }}

/* ── left navigation rail ────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{ background:{SURFACE}; border-right:1px solid var(--border); }}
[data-testid="stSidebar"] .block-container {{ padding-top:1.25rem; }}

.brand {{ display:flex; align-items:center; gap:.6rem; padding:0 .25rem; }}
.brand-mark {{ width:30px;height:30px;flex:none;border-radius:var(--r);
  background:{BLUE}; display:grid;place-items:center;
  font-weight:700;color:#fff;font-size:.78rem;letter-spacing:.02em; }}
.brand-name {{ font-weight:600;font-size:1rem;line-height:1.15;color:var(--text);
  letter-spacing:-0.01em; }}
.brand-sub {{ font-size:.68rem;color:var(--faint);line-height:1.3;margin-top:1px; }}
.rail-div {{ height:1px;background:var(--border);margin:1rem 0 .75rem; }}
.rail-cap {{ font-size:.68rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--faint);margin:.25rem .25rem .4rem; }}
.rail-kv {{ font-size:.78rem;line-height:1.4;color:var(--text);padding:0 .25rem .5rem; }}
.rail-kv small {{ display:block;color:var(--faint);font-size:.78rem;font-weight:400; }}

[data-testid="stSidebarNav"] ul {{ gap:1px;padding:0; }}
[data-testid="stSidebarNav"] li {{ list-style:none; }}
[data-testid="stSidebarNav"] a {{
  border-radius:var(--r);padding:.5rem .6rem !important;
  transition:background .15s ease;
}}
[data-testid="stSidebarNav"] a:hover {{ background:rgba(148,163,184,.07); }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background:rgba(199,125,160,.16); }}
[data-testid="stSidebarNav"] a span {{
  font-family:'Inter',sans-serif !important;font-weight:500 !important;
  font-size:.875rem !important;color:var(--muted) !important;letter-spacing:0 !important; }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{
  color:var(--text) !important;font-weight:600 !important; }}
[data-testid="stSidebarNav"]::before {{
  content:"PLATFORM";display:block;font-size:.68rem;font-weight:600;
  letter-spacing:.08em;color:var(--faint);padding:.25rem .6rem .45rem; }}

/* ── top executive bar ───────────────────────────────────────────────────── */
.topbar {{ display:flex;align-items:center;justify-content:space-between;gap:1.5rem;
  padding:0 0 .9rem;border-bottom:1px solid var(--border);margin-bottom:1.1rem; }}
.topbar-l {{ min-width:0; }}
.topbar-title {{ font-size:1.375rem;font-weight:600;letter-spacing:-0.02em;
  color:var(--text);line-height:1.2; }}
.topbar-q {{ font-size:.78rem;color:var(--muted);margin-top:.2rem; }}
.topbar-r {{ display:flex;gap:.4rem;flex-wrap:wrap;justify-content:flex-end;flex:none; }}

.chip {{ font-size:.68rem;font-weight:500;padding:.24rem .55rem;border-radius:4px;
  border:1px solid var(--border);background:var(--surface-2);color:var(--muted);
  white-space:nowrap;display:inline-flex;align-items:center;gap:.34rem; }}
.chip b {{ color:var(--text);font-weight:600; }}
.chip .led {{ width:5px;height:5px;border-radius:50%;background:var(--steel);flex:none; }}
.chip.ok .led {{ background:var(--green); }}
.chip.ok b {{ color:var(--green); }}
.chip.warn .led {{ background:var(--amber); }}
.chip.warn b {{ color:var(--amber); }}
.chip.info .led {{ background:var(--blue); }}
.chip.info b {{ color:var(--blue); }}

/* network composition strip */
.netmix {{ display:flex;height:4px;border-radius:4px;overflow:hidden;
  margin:0 0 1.15rem;background:var(--surface-2); }}
.netmix span {{ display:block;height:100%; }}

/* ── cards ───────────────────────────────────────────────────────────────── */
.card {{ background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:1rem 1.1rem;height:100%;box-shadow:var(--shadow);
  transition:border-color .15s ease; }}
.card:hover {{ border-color:var(--border-s); }}
.card.lead {{ border-left:3px solid var(--blue); }}
.card.alert {{ border-left:3px solid var(--red); }}

.k-lab {{ font-size:.68rem;font-weight:500;color:var(--muted);margin-bottom:.45rem;
  letter-spacing:.01em; }}
.k-val {{ font-size:1.5rem;font-weight:600;line-height:1.15;color:var(--text);
  letter-spacing:-0.02em;font-variant-numeric:tabular-nums; }}
.card.lead .k-val {{ font-size:2rem; }}
.k-sub {{ font-size:.78rem;color:var(--faint);margin-top:.4rem;line-height:1.5; }}
.k-tag {{ font-size:.78rem;font-weight:600;margin-top:.45rem;display:inline-block;
  padding:.14rem .42rem;border-radius:4px;font-variant-numeric:tabular-nums; }}
.k-tag.up {{ color:var(--green);background:rgba(217,165,192,.14); }}
.k-tag.down {{ color:var(--red);background:rgba(217,107,132,.14); }}
.k-tag.flat {{ color:var(--muted);background:rgba(148,163,184,.10); }}
.k-tag.hot {{ color:var(--blue);background:rgba(199,125,160,.14); }}

.bar {{ height:4px;border-radius:4px;background:rgba(148,163,184,.14);
  margin-top:.65rem;overflow:hidden; }}
.bar > i {{ display:block;height:100%;background:var(--blue);border-radius:4px; }}

/* ── section headers ─────────────────────────────────────────────────────── */
.sec {{ display:flex;align-items:baseline;gap:.6rem;margin:1.75rem 0 .8rem; }}
.sec h3 {{ margin:0;font-size:1rem;font-weight:600;letter-spacing:-0.01em; }}
.sec .hint {{ font-size:.78rem;color:var(--faint);font-weight:400; }}

.note {{ font-size:.78rem;color:var(--muted);line-height:1.6;
  border:1px solid var(--border);border-left:3px solid var(--amber);
  border-radius:var(--r);padding:.7rem .85rem;background:var(--surface);margin-top:.9rem; }}
.note b {{ color:var(--text);font-weight:600; }}
.note code {{ color:var(--text);background:var(--surface-2);padding:.05rem .3rem;
  border-radius:4px;font-size:.94em; }}

/* ledger rows */
.row {{ display:flex;justify-content:space-between;align-items:center;gap:1rem;
  font-size:.78rem;padding:.45rem 0;border-bottom:1px solid rgba(148,163,184,.08); }}
.row:last-of-type {{ border-bottom:none; }}
.row .n {{ color:var(--muted); }}
.row .v {{ color:var(--text);font-weight:600;font-variant-numeric:tabular-nums;
  white-space:nowrap; }}

/* status banner */
.banner {{ display:flex;align-items:center;gap:1.5rem;background:var(--surface);
  border:1px solid var(--border);border-left:3px solid var(--blue);
  border-radius:var(--r);padding:.7rem 1rem;margin-bottom:1.1rem;
  box-shadow:var(--shadow); }}
.banner.hold {{ border-left-color:var(--amber); }}
.banner-v {{ font-size:.78rem;font-weight:600;letter-spacing:.04em;color:var(--text);
  white-space:nowrap;display:flex;align-items:center;gap:.45rem; }}
.banner-v .led {{ width:6px;height:6px;border-radius:50%;background:var(--blue); }}
.banner.hold .banner-v .led {{ background:var(--amber); }}
.banner-cells {{ display:flex;gap:1.75rem;flex-wrap:wrap;flex:1; }}
.bc-k {{ font-size:.68rem;color:var(--faint);font-weight:500; }}
.bc-v {{ font-size:1rem;color:var(--text);font-weight:600;margin-top:1px;
  font-variant-numeric:tabular-nums; }}

/* ── streamlit widget normalisation ──────────────────────────────────────── */
[data-testid="stDataFrame"] {{ border:1px solid var(--border);border-radius:var(--r); }}
div[data-testid="stExpander"] {{ border:1px solid var(--border);border-radius:var(--r);
  background:var(--surface);box-shadow:var(--shadow); }}
div[data-testid="stExpander"] summary {{ font-size:.875rem;font-weight:500; }}

.stSlider [data-baseweb="slider"] div[role="slider"] {{ background:{BLUE} !important; }}
.stSlider [data-testid="stTickBar"] {{ background:transparent; }}
label p {{ font-size:.78rem !important;font-weight:500 !important;color:var(--muted) !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap:.15rem;border-bottom:1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ font-size:.78rem;font-weight:500;color:var(--muted);
  padding:.5rem .85rem; }}
.stTabs [aria-selected="true"] {{ color:var(--text) !important;font-weight:600 !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:{BLUE}; }}

.stDownloadButton button, .stButton button {{
  font-family:'Inter',sans-serif;font-weight:500;font-size:.78rem;
  border-radius:var(--r);border:1px solid var(--border-s);
  background:var(--surface-2);color:var(--text);
  transition:background .15s ease,border-color .15s ease; }}
.stDownloadButton button:hover, .stButton button:hover {{
  background:rgba(199,125,160,.16);border-color:{BLUE}; }}

[data-testid="stCaptionContainer"] p {{ font-size:.78rem;color:var(--faint);line-height:1.55; }}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def layout(**kw):
    """Shared chart styling: minimal gridlines, no chart junk, business palette."""
    base = dict(
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
        font=dict(family="Inter, sans-serif", color=MUTED, size=11),
        margin=dict(l=8, r=8, t=24, b=8),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER,
                   showgrid=False, ticks="outside", tickcolor=BORDER, ticklen=4),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="rgba(0,0,0,0)",
                   showgrid=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=MUTED)),
        hoverlabel=dict(bgcolor=SURFACE_2, bordercolor=BORDER_S,
                        font=dict(family="Inter, sans-serif", size=11, color=TEXT)),
        colorway=SEQ,
    )
    base.update(kw)
    return base


# breadcrumb for the operational workflow (appended to CSS at import)
CSS += """
<style>
.flow { display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;margin:-.2rem 0 1rem; }
.flow .step { font-size:.68rem;color:#64748B;padding:.16rem .1rem; }
.flow .step.on { color:#F1F5F9;font-weight:600; }
.flow .sep { color:#334155;font-size:.78rem; }
</style>
"""