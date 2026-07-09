"""
run_pipeline.py — RetainIQ India

One-command, ordered execution of the whole decision chain. Run this instead of
invoking modules ad hoc; it makes the dependency order explicit and fails fast
with an actionable message.

    python src/run_pipeline.py            # full chain
    python src/run_pipeline.py --from ltv # resume from a stage

Dependency order (each stage's outputs feed the next):

    load_data      (Day 2)  raw CSV -> DuckDB schema
    build_features (Day 3)  schema  -> feature_customer view + parquet
    data_quality   (Day 4)  47 checks, hard/soft  -> reports/dq_report.json
    model          (Day 7)  churn engine          -> models/churn_model.pkl
    ltv            (Day 9)  KM survival + churn P -> customer_value.parquet
    profit_curve   (Day 9)  rupee profit curve    -> reports/profit_curve.json
    optimizer      (Day 10) budget knapsack       -> reports/contact_list.csv
    sensitivity    (Day 11) assumption sweeps     -> reports/sensitivity.json
    simulator      (Day 11) named scenarios       -> reports/scenarios.json

NOTE on Day 5/7 artifacts: `ltv` does NOT read stored `churn_probability` or
`km_expected_months` columns. It regenerates both deterministically (fixed seeds,
ORDER BY customer_id — see runlog D-029), loading models/churn_model.pkl when
present. Days 5, 6 and 8 are analysis/reporting stages and are not on the
critical path to the optimizer.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | pipeline | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("pipeline")

# (stage name, module, callable) — order is the contract.
STAGES: list[tuple[str, str, str]] = [
    ("load_data", "load_data", "main"),
    ("build_features", "build_features", "build"),
    ("data_quality", "data_quality", "run"),
    ("model", "model", "train"),
    ("ltv", "ltv", "build"),
    ("profit_curve", "profit_curve", "run"),
    ("optimizer", "optimizer", "run"),
    ("sensitivity", "sensitivity", "run"),
    ("simulator", "simulator", "run"),
]


def main() -> int:
    names = [s[0] for s in STAGES]
    ap = argparse.ArgumentParser(description="Run the RetainIQ decision pipeline.")
    ap.add_argument("--from", dest="start", choices=names, default=names[0],
                    help="resume from this stage")
    ap.add_argument("--only", choices=names, help="run a single stage")
    args = ap.parse_args()

    if args.only:
        todo = [s for s in STAGES if s[0] == args.only]
    else:
        todo = STAGES[names.index(args.start):]

    logger.info("running %d stage(s): %s", len(todo), " -> ".join(s[0] for s in todo))
    for name, mod_name, fn_name in todo:
        t0 = time.time()
        logger.info("── %s ──────────────────────────────", name)
        try:
            mod = __import__(mod_name)
            getattr(mod, fn_name)()
        except Exception as exc:
            logger.error("stage '%s' FAILED: %s: %s", name, type(exc).__name__, exc)
            logger.error("fix the above, then resume with: "
                         "python src/run_pipeline.py --from %s", name)
            return 1
        logger.info("✓ %s (%.1fs)", name, time.time() - t0)

    logger.info("pipeline complete — see reports/ for outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())