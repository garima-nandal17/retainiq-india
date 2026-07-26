"""
test_app_integrity.py — RetainIQ

Makes the codebase-integrity audit a permanent guarantee: every import resolves,
every cross-module reference exists, every page has a render() and is wired, and
all five pages render without raising. Guards against the "referenced but never
generated" class of defect.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

APP_MODULES = [
    "app.components.theme", "app.components.ui", "app.components.charts",
    "app.components.data", "app.components.state", "app.pages._shell",
    "app.pages.executive", "app.pages.customer", "app.pages.decision",
    "app.pages.scenarios", "app.pages.brief", "app.dashboard",
]
needs_reports = pytest.mark.skipif(
    not (ROOT / "reports" / "optimizer_result.json").exists(),
    reason="pipeline reports not present")


def test_static_audit_passes():
    """The AST auditor must report zero unresolved references."""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "audit_app.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("mod", APP_MODULES)
def test_every_module_imports(mod):
    importlib.import_module(mod)


def test_every_page_exposes_render():
    for p in ["executive", "customer", "decision", "scenarios", "brief"]:
        m = importlib.import_module(f"app.pages.{p}")
        assert callable(getattr(m, "render", None)), f"{p}.render() missing"


@needs_reports
@pytest.mark.parametrize("path", ["executive", "customer", "decision", "scenarios", "brief"])
def test_page_renders(path):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app" / "dashboard.py"), default_timeout=300)
    at.query_params["render"] = path
    at.run()
    assert not at.exception, f"{path}: {[e.value for e in at.exception]}"


# --- data-loader smoke tests: execute EVERY loader against the real DB ---------
# These bypass Streamlit's cache and render harness, which is where three
# DuckDB binder errors slipped through AppTest. If a loader's SQL is invalid on
# the installed DuckDB, THIS is the test that fails — loudly, directly.

@needs_reports
def test_all_data_loaders_execute():
    from app.components import data as D
    # clear caches so the SQL actually runs, not a memoised value
    for fn in [D.load_json, D.load_contact_list, D.load_customer_values,
               D.load_network_profile, D.load_lifecycle]:
        try:
            fn.clear()
        except Exception:
            pass
    assert D.load_customer_values().shape[0] == 7043
    assert D.load_network_profile().shape[0] == 7043
    lc = D.load_lifecycle()
    assert len(lc) == 4
    # reconciles to the frozen base-churn count
    assert sum(int(r["churned"]) for r in lc) == 1869
    assert D.load_contact_list().shape[0] == 1349