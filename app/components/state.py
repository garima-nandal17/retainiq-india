"""
state.py — RetainIQ campaign decision state (Day 13 v3, UI only).

The workflow spine. Campaign controls (budget / acceptance / offer cost / margin)
live in st.session_state and PERSIST across pages, so a decision set on Decision
Intelligence is the same decision the Executive Brief reports. This is what turns
five separate reports into one product.

The live decision itself delegates to the Day-11 pure `simulator.simulate()`.
No business logic is defined here — this only holds the operator's chosen inputs
and caches the resulting decision.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import streamlit as st

from . import data as D

PLAN = dict(budget=100_000, acceptance=1.0, offer_cost=1.0, margin=0.60)


@dataclass
class Campaign:
    budget: int = PLAN["budget"]
    acceptance: float = PLAN["acceptance"]
    offer_cost: float = PLAN["offer_cost"]
    margin: float = PLAN["margin"]

    @property
    def is_plan_of_record(self) -> bool:
        return (self.budget == PLAN["budget"] and self.acceptance == 1.0
                and self.offer_cost == 1.0 and self.margin == 0.60)


def get() -> Campaign:
    if "campaign" not in st.session_state:
        st.session_state.campaign = Campaign()
    return st.session_state.campaign


def set_field(name: str, value) -> None:
    c = get()
    setattr(c, name, value)
    st.session_state.campaign = c


def reset() -> None:
    st.session_state.campaign = Campaign()


def decision() -> dict:
    """The live decision under the current campaign controls (cached)."""
    c = get()
    return D.simulate(float(c.budget), float(c.acceptance),
                      float(c.offer_cost), float(c.margin))


def changes_from_plan() -> list[tuple[str, str]]:
    """Human-readable diff of the current campaign vs the plan of record.
    Feeds the 'custom scenario active' feedback so state changes are legible."""
    c = get()
    out: list[tuple[str, str]] = []
    if c.budget != PLAN["budget"]:
        out.append(("budget", f"₹{c.budget:,}"))
    if c.acceptance != 1.0:
        out.append(("acceptance", f"{c.acceptance:.1f}×"))
    if c.offer_cost != 1.0:
        out.append(("offer cost", f"{c.offer_cost:.1f}×"))
    if c.margin != 0.60:
        out.append(("margin", f"{c.margin:.0%}"))
    return out


def status() -> dict:
    """Campaign status header shared by every page."""
    c = get()
    d = decision()
    if d["n_contacted"] == 0:
        verdict, tone = "STAND DOWN", "down"
    elif c.is_plan_of_record:
        verdict, tone = "ARMED · PLAN", "hot"
    else:
        verdict, tone = "ARMED · CUSTOM", "hot"
    return {"verdict": verdict, "tone": tone, "campaign": asdict(c), "decision": d}