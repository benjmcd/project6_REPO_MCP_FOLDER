"""AST-level drift guard for review_nrc_aps.py operator identity gating.

ALL routes (any HTTP method) in review_nrc_aps.py must:
  1. Accept a ``request: Request`` parameter.
  2. Have a Try block as the first executable statement whose body begins with a
     call to ``_route_level_operator_identity``.

No exemptions — every route in this module serves NRC APS review content and is
a sensitive read surface.
"""
from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCE_FILE = BACKEND / "app" / "api" / "review_nrc_aps.py"


# ---------------------------------------------------------------------------
# AST helpers (mirror the pattern from test_layer3_operator_identity_drift_guard.py)
# ---------------------------------------------------------------------------


def _is_router_route(decorator: ast.expr) -> bool:
    """Return True if the decorator is any router.get/post/put/patch/delete call."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr in {
            "get", "post", "put", "patch", "delete", "head", "options",
        }:
            return True
    return False


def _has_param_named(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    all_args = node.args.args + node.args.posonlyargs + node.args.kwonlyargs
    if node.args.vararg and node.args.vararg.arg == name:
        return True
    if node.args.kwarg and node.args.kwarg.arg == name:
        return True
    return any(a.arg == name for a in all_args)


def _first_executable_stmt(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.stmt | None:
    for stmt in node.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        return stmt
    return None


def _is_try_with_route_level_call(stmt: ast.stmt | None) -> tuple[bool, str]:
    if stmt is None:
        return False, "body is empty after optional docstring"
    if not isinstance(stmt, ast.Try):
        return False, f"first executable statement is {type(stmt).__name__}, expected Try"
    try_body = stmt.body
    if not try_body:
        return False, "Try body is empty"
    first = try_body[0]
    if not isinstance(first, ast.Expr):
        return False, f"first statement in Try body is {type(first).__name__}, expected Expr"
    call = first.value
    if not isinstance(call, ast.Call):
        return False, f"expression in Try is {type(call).__name__}, expected Call"
    func = call.func
    if isinstance(func, ast.Name) and func.id == "_route_level_operator_identity":
        return True, ""
    if isinstance(func, ast.Attribute) and func.attr == "_route_level_operator_identity":
        return True, ""
    return False, f"called {ast.dump(func)!r}, expected _route_level_operator_identity"


_VALID_ACCESS_VALUES = {"read", "write"}


def _extract_access_kwarg(stmt: ast.stmt | None) -> str | None:
    """Return the string value of access= kwarg on the _route_level_operator_identity call,
    or None if not found or not a string constant."""
    if stmt is None or not isinstance(stmt, ast.Try):
        return None
    try_body = stmt.body
    if not try_body:
        return None
    first = try_body[0]
    if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Call):
        return None
    call = first.value
    for kw in call.keywords:
        if kw.arg == "access" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_routes_have_wired_identity_seam() -> None:
    """Every route handler in review_nrc_aps.py must gate on operator identity."""
    tree = ast.parse(SOURCE_FILE.read_text(encoding="utf-8"), filename=str(SOURCE_FILE))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_router_route(d) for d in node.decorator_list):
            continue

        fname = node.name
        lineno = node.lineno
        label = f"review_nrc_aps.py:{lineno} {fname}"

        if not _has_param_named(node, "request"):
            violations.append(f"{label}: missing parameter 'request'")
            continue

        first = _first_executable_stmt(node)
        ok, reason = _is_try_with_route_level_call(first)
        if not ok:
            violations.append(f"{label}: {reason}")

    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(
            f"{len(violations)} route(s) in review_nrc_aps.py missing wired identity seam:\n{formatted}"
        )


def test_all_routes_declare_access_keyword() -> None:
    """Every _route_level_operator_identity call must declare access= as 'read' or 'write'."""
    tree = ast.parse(SOURCE_FILE.read_text(encoding="utf-8"), filename=str(SOURCE_FILE))
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_router_route(d) for d in node.decorator_list):
            continue

        fname = node.name
        lineno = node.lineno
        label = f"review_nrc_aps.py:{lineno} {fname}"

        first = _first_executable_stmt(node)
        # Only check if the seam is wired (seam test handles missing-seam case)
        ok, _ = _is_try_with_route_level_call(first)
        if not ok:
            continue

        access_val = _extract_access_kwarg(first)
        if access_val is None:
            violations.append(f"{label}: access= keyword not present or not a string constant")
        elif access_val not in _VALID_ACCESS_VALUES:
            violations.append(
                f"{label}: access={access_val!r} is not a valid access class (must be 'read' or 'write')"
            )

    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(
            f"{len(violations)} route(s) in review_nrc_aps.py with invalid or missing access= declaration:\n{formatted}"
        )


def test_source_file_is_parseable() -> None:
    assert SOURCE_FILE.exists(), f"source file not found: {SOURCE_FILE}"
    ast.parse(SOURCE_FILE.read_text(encoding="utf-8"), filename=str(SOURCE_FILE))
