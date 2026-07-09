"""
economics.py — RetainIQ India (Day 9)

SINGLE SOURCE OF TRUTH for every rupee assumption in the project.

Nothing downstream (LTV, profit curve, optimizer, sensitivity, dashboard) may
hardcode a monetary constant — it imports from here. That makes the entire
decision chain auditable and lets Day 11 sweep these values as scenarios.

HONESTY: the IBM Telco dataset contains ARPU and tenure but NO cost, margin,
offer, or acceptance data. Every constant below is therefore an explicitly
DECLARED ASSUMPTION, not an estimate from data. All downstream figures inherit
this and are labelled `(simulation-based)`. Sourcing rationale is given per field.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Economics:
    # Gross margin on telecom service revenue. Telecom opex is heavy; 60% gross
    # margin on incremental subscriber revenue is a conservative industry-typical
    # figure. ASSUMPTION.
    gross_margin: float = 0.60

    # Monthly discount rate for present-valuing future margin (~10% annual).
    # ASSUMPTION.
    monthly_discount_rate: float = 0.008

    # Horizon over which we value a retained customer. Matches the dataset's
    # 72-month observation window; avoids extrapolating beyond observed tenure.
    horizon_months: int = 24

    # Cost of one retention contact/offer = call-centre contact (~Rs 40) + average
    # discount/credit value (~Rs 80). ASSUMPTION — swept in Day-11 sensitivity.
    # NOTE: an initial Rs 500 assumption was REJECTED after measurement: mean 24-month
    # LTV is ~Rs 708, so a Rs 500 offer consumes ~70% of a customer's entire lifetime
    # margin and makes expected net negative for 100% of customers (0/7043 viable).
    # An offer must be small relative to the margin it protects. See runlog D-036.
    offer_cost_inr: float = 120.0

    # Probability an at-risk contacted customer accepts the offer AND stays.
    # ASSUMPTION — the single most load-bearing assumption in the project.
    # Deliberately conservative; swept in Day 11; measured for real only by the
    # Day-12 A/B test.
    acceptance_rate: float = 0.35

    # Total monthly retention budget available to Priya. ASSUMPTION (scenario).
    # Chosen to be BINDING: the offer set the optimizer would like to fund costs
    # ~Rs 1.63 L, and contacting the whole base costs ~Rs 3.59 L, so a Rs 1.0 L
    # ceiling forces genuine prioritisation. A non-binding budget would make every
    # targeting strategy identical and the optimizer meaningless. See runlog D-038.
    budget_inr: float = 100_000.0

    def as_dict(self) -> dict:
        return asdict(self)


ECON = Economics()

# Provenance note reused by docs/dashboard so the caveat travels with the number.
ASSUMPTION_NOTE = (
    "All monetary results are (simulation-based estimates). The source dataset "
    "contains ARPU and tenure but no cost, margin, offer, or acceptance data; "
    "margin, offer cost, acceptance rate, and budget are declared assumptions "
    "(see src/economics.py) and are stress-tested in the Day-11 sensitivity "
    "analysis. Only the Day-12 A/B design can measure acceptance for real."
)