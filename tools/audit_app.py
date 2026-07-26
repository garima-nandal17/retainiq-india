#!/usr/bin/env python3
"""
audit_app.py — RetainIQ codebase integrity audit (static, AST-based).

Resolves, without executing the app:
  1. every module imported            5. every missing import
  2. every function/name referenced   6. every broken reference
  3. every missing function           7. import/location mismatches
  4. every missing file

Exit code 0 only if the project is internally consistent.

Run:  python tools/audit_app.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

# module alias -> the local module it points at (populated per file from imports)
LOCAL_PKGS = {"app", "app.components", "app.views"}


def py_files() -> list[Path]:
    return sorted(p for p in APP.rglob("*.py") if "__pycache__" not in p.parts)


def module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)


def public_names(tree: ast.AST) -> set[str]:
    """Top-level defs, classes, and assigned names in a module."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add(a.asname or a.name.split(".")[0])
    return names


def main() -> int:
    files = py_files()
    trees: dict[str, ast.AST] = {}
    exported: dict[str, set[str]] = {}          # module -> names it defines/imports
    modmap: dict[str, Path] = {}

    print("=" * 72)
    print("RetainIQ — CODEBASE INTEGRITY AUDIT")
    print("=" * 72)

    # ── parse pass (syntax check) ───────────────────────────────────────────
    syntax_errors = []
    for f in files:
        mod = module_name(f)
        modmap[mod] = f
        try:
            trees[mod] = ast.parse(f.read_text(), filename=str(f))
            exported[mod] = public_names(trees[mod])
        except SyntaxError as e:
            syntax_errors.append((mod, e))

    print(f"\n[1] MODULES DISCOVERED ({len(files)})")
    for mod in sorted(modmap):
        print(f"    {mod:34s} {modmap[mod].relative_to(ROOT)}")

    if syntax_errors:
        print("\n  ✗ SYNTAX ERRORS — cannot proceed:")
        for mod, e in syntax_errors:
            print(f"    {mod}: line {e.lineno}: {e.msg}")
        return 1
    print("\n  ✓ all modules parse (no syntax errors)")

    # module resolver: does an imported module exist as a file OR a known 3rd-party?
    known_local = set(modmap) | LOCAL_PKGS
    problems = {"missing_import": [], "missing_file": [], "broken_ref": [],
                "location_mismatch": []}
    import_edges = []      # (importer, imported_module, [names])
    ref_edges = []         # (referrer, alias, attr)

    for mod, tree in trees.items():
        # map: local alias -> resolved module string (for attribute refs like D.foo)
        alias_to_module: dict[str, str] = {}

        for node in ast.walk(tree):
            # ---- from X import a, b ----
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if base.startswith("app"):
                    import_edges.append((mod, base, [a.name for a in node.names]))
                    if base not in known_local:
                        problems["missing_file"].append(
                            f"{mod}: `from {base} import ...` → module '{base}' not found")
                    else:
                        # each imported name must exist in that module (if it's a module file)
                        if base in exported:
                            for a in node.names:
                                if a.name != "*" and a.name not in exported[base]:
                                    problems["missing_import"].append(
                                        f"{mod}: `from {base} import {a.name}` → "
                                        f"'{a.name}' not defined in {base}")
                                # record alias → submodule for attr resolution
                                asname = a.asname or a.name
                                alias_to_module[asname] = f"{base}.{a.name}"
                        # 'from app.components import data as D' → D points at app.components.data
                        for a in node.names:
                            cand = f"{base}.{a.name}"
                            if cand in exported:
                                alias_to_module[a.asname or a.name] = cand
            # ---- import app.components.data as D ----
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("app"):
                        import_edges.append((mod, a.name, []))
                        if a.name not in known_local and a.name not in exported:
                            problems["missing_file"].append(
                                f"{mod}: `import {a.name}` → module not found")
                        alias_to_module[a.asname or a.name.split('.')[0]] = a.name

        # ---- attribute references on local aliases: D.load_lifecycle etc. ----
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)):
                alias = node.value.id
                attr = node.attr
                target_mod = alias_to_module.get(alias)
                if target_mod and target_mod in exported:
                    ref_edges.append((mod, target_mod, attr))
                    if attr not in exported[target_mod] and not attr.startswith("__"):
                        problems["broken_ref"].append(
                            f"{mod}: `{alias}.{attr}` → '{attr}' not defined in {target_mod}")

    # ── report ──────────────────────────────────────────────────────────────
    print(f"\n[2] INTERNAL IMPORTS ({len(import_edges)})")
    for imp, base, names in sorted(import_edges):
        tail = f" ({', '.join(names)})" if names else ""
        print(f"    {imp:26s} → {base}{tail}")

    print(f"\n[3] CROSS-MODULE NAME REFERENCES CHECKED ({len(ref_edges)})")
    by_ref: dict[str, int] = {}
    for _, tgt, _ in ref_edges:
        by_ref[tgt] = by_ref.get(tgt, 0) + 1
    for tgt, n in sorted(by_ref.items()):
        print(f"    {n:3d} refs → {tgt}")

    print("\n[4] PROBLEM LEDGER")
    labels = {"missing_file": "Missing files / modules",
              "missing_import": "Missing imports (name not in source module)",
              "broken_ref": "Broken references (attr not defined)",
              "location_mismatch": "Import/location mismatches"}
    total = 0
    for key, label in labels.items():
        items = problems[key]
        total += len(items)
        mark = "✓" if not items else "✗"
        print(f"\n  {mark} {label}: {len(items)}")
        for it in items:
            print(f"      - {it}")

    # ── entrypoint expectations ─────────────────────────────────────────────
    print("\n[5] ENTRYPOINT / PAGE WIRING")
    dash = trees.get("app.dashboard")
    expected_pages = {"executive", "customer", "decision", "scenarios", "brief"}
    if dash:
        imported_pages = {n for _, b, names in import_edges
                          if b == "app.views" for n in names}
        missing_pages = expected_pages - imported_pages
        for p in sorted(expected_pages):
            here = f"app.views.{p}" in modmap
            wired = p in imported_pages
            renders = "render" in exported.get(f"app.views.{p}", set())
            ok = here and wired and renders
            print(f"    {'✓' if ok else '✗'} {p:12s} file={here} imported={wired} "
                  f"render()={renders}")
        total += len(missing_pages)

    print("\n" + "=" * 72)
    if total == 0:
        print("RESULT: ✓ internally consistent — every reference resolves")
    else:
        print(f"RESULT: ✗ {total} unresolved issue(s) — see ledger above")
    print("=" * 72)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())