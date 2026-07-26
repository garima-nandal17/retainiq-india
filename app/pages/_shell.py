"""
_shell.py — shared chrome for every RetainIQ page (Enterprise Edition).

The persistent frame: top executive bar (page title, operator, platform status),
the campaign banner (live decision state, carried across every module), and the
network composition strip.

Because the banner reads `state.status()`, a decision set on the Decision Engine
is the decision every page reports.
"""
from __future__ import annotations

from app.components import data as D
from app.components import state as S
from app.components import theme as T
from app.components import ui

OPERATOR = "BharatConnect · Retention Operations · India North"


def telemetry() -> list[tuple[str, str, str]]:
    dq = D.load_json("dq_report.json")
    mm = D.load_json("model_metrics.json")
    ok = all(c["passed"] for c in dq["checks"] if c["severity"] == "hard")
    return [
        ("Subscriber feed", "Healthy" if ok else "Degraded", "ok" if ok else "warn"),
        ("Risk engine", f"AUC {mm['logistic_calibrated']['roc_auc']:.4f}", "info"),
        ("Mode", "Simulation", "warn"),
    ]


def network_strip() -> None:
    net = D.load_network_profile()
    n = len(net)
    fibre = (net.internet_type == "Fiber optic").sum() / n * 100
    dsl = (net.internet_type == "DSL").sum() / n * 100
    ui.sim_base_ribbon([(fibre, T.BLUE), (dsl, T.TEAL), (100 - fibre - dsl, T.SURFACE_2)])


def header(page: str, question: str, workflow_step: str | None = None,
           banner: bool = True) -> None:
    """Page identity only.

    Global KPIs, platform health, scenario state and build metadata all live in the
    persistent command bar rendered once by the app chrome — repeating them here was
    the duplication that made five pages read as one long scroll. `workflow_step` and
    `banner` are retained for call-site compatibility and intentionally ignored."""
    ui.page_title(page, question)