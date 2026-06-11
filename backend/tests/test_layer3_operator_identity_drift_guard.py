from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCE_FILES = [
    BACKEND / "app" / "api" / "layer3" / "__init__.py",
    BACKEND / "app" / "api" / "layer3" / "handoff.py",
    BACKEND / "app" / "api" / "layer3" / "package.py",
    BACKEND / "app" / "api" / "layer3" / "source_sec_edgar.py",
    BACKEND / "app" / "api" / "layer3" / "source_ingestion.py",
    BACKEND / "app" / "api" / "layer3" / "sec_xbrl.py",
]
SENSITIVE_GET_SOURCE_FILES = [
    BACKEND / "app" / "api" / "layer3" / "__init__.py",
    BACKEND / "app" / "api" / "layer3" / "handoff.py",
    BACKEND / "app" / "api" / "layer3" / "source_sec_edgar.py",
    BACKEND / "app" / "api" / "layer3" / "source_ingestion.py",
    BACKEND / "app" / "api" / "layer3" / "sec_xbrl.py",
]
PUBLIC_GET_EXEMPTIONS = {
    "__init__.py": {
        "get_bootstrap",
        "get_readiness",
        "get_authority_matrix",
    },
}

# Source files whose routes use the stricter sec_xbrl route-family authorization
# mechanism instead of (or in addition to) the standard _route_level_operator_identity
# call pattern.  For these files the checker accepts any route handler that calls one of
# the STRICTER_MECHANISM_CALL_NAMES anywhere in its body rather than requiring the
# standard Try-first-Expr pattern.
#
# sec_xbrl.py POST routes use _sec_xbrl_policy_decision (which wraps authorize_sec_xbrl_route)
# or derive_sec_xbrl_evidence_owner — both are stricter than the plain identity seam.
# sec_xbrl.py GET get_sec_xbrl_controlled_value_reveal_submit_status uses authorize_sec_xbrl_route
# directly.  All are intentional and audited.
STRICTER_MECHANISM_SOURCE_FILES: set[str] = {
    "sec_xbrl.py",
}

# Auth call names that constitute valid stricter-mechanism gating.
STRICTER_MECHANISM_CALL_NAMES: set[str] = {
    "authorize_sec_xbrl_route",
    "_sec_xbrl_policy_decision",
    "derive_sec_xbrl_evidence_owner",
}

# GET routes that are designed fail-soft BY CONTRACT and must NOT gate on operator
# identity.  These diagnose proxy misconfiguration and always return 200 with a
# projection_status of blocked_* when headers are absent.
# doc-1351: sec_xbrl_proxy_identity_read_only_live_projection_contract
DESIGNED_FAIL_SOFT_EXEMPTIONS = {
    "sec_xbrl.py": {
        "get_sec_xbrl_proxy_identity_readonly_projection",
    },
}


def _is_router_post(decorator: ast.expr) -> bool:
    return _is_router_route(decorator, "post")


def _is_router_get(decorator: ast.expr) -> bool:
    return _is_router_route(decorator, "get")


def _is_router_route(decorator: ast.expr, method: str) -> bool:
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr == method:
            return True
    return False


def _has_param_named(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    all_args = (
        node.args.args
        + node.args.posonlyargs
        + node.args.kwonlyargs
    )
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


def _walk_no_nested_scopes(node: ast.AST):
    """Yield all descendant AST nodes, but do NOT descend into nested
    FunctionDef / AsyncFunctionDef / Lambda scopes.  This keeps the walk
    within the lexical body of the handler being inspected so that a stricter
    auth call that only appears inside a helper defined *inside* the handler
    (dead code for the handler's own control flow) does not satisfy the gate.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            # Do not recurse into nested scopes.
            continue
        yield from _walk_no_nested_scopes(child)


def _function_calls_stricter_mechanism(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the handler body contains a stricter-mechanism auth call that is
    reachable from the handler's own control flow.

    Rule: the stricter call must appear within the handler's top-level statement
    sequence (not inside a nested FunctionDef/AsyncFunctionDef/Lambda).  We walk
    the handler body using _walk_no_nested_scopes, which descends into Try blocks,
    If branches, and any other control-flow constructs at the handler scope, but
    stops at nested function/lambda definitions.

    This rejects a stricter call that only exists inside a nested helper defined
    within the handler body (dead code from the handler's perspective) while
    accepting all 12 known sec_xbrl handler shapes:
      - try: ... authorize_sec_xbrl_route / _sec_xbrl_policy_decision as first stmt in try body
      - Assign(s) before try: ... (e.g. route_family = ...; try: policy_decision = ...)
      - try: derive_sec_xbrl_evidence_owner as the first stmt in the first try
    """
    for child in _walk_no_nested_scopes(node):
        if isinstance(child, ast.Call):
            func = child.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in STRICTER_MECHANISM_CALL_NAMES:
                return True
    return False


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


def _collect_violations(
    *,
    source_files: list[Path],
    matcher,
    exemptions: dict[str, set[str]] | None = None,
    fail_soft_exemptions: dict[str, set[str]] | None = None,
) -> list[str]:
    violations: list[str] = []
    for source_path in source_files:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        allow_stricter = source_path.name in STRICTER_MECHANISM_SOURCE_FILES
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(matcher(d) for d in node.decorator_list):
                continue
            fname = node.name
            if fname in (exemptions or {}).get(source_path.name, set()):
                continue
            if fname in (fail_soft_exemptions or {}).get(source_path.name, set()):
                # Designed fail-soft: must NOT have the standard identity gate (by contract).
                continue
            lineno = node.lineno
            label = f"{source_path.name}:{lineno} {fname}"
            if not _has_param_named(node, "request"):
                violations.append(f"{label}: missing parameter 'request'")
                continue
            # For stricter-mechanism source files, accept any route that calls one of the
            # known stricter auth functions anywhere in its body.
            if allow_stricter and _function_calls_stricter_mechanism(node):
                continue
            first = _first_executable_stmt(node)
            ok, reason = _is_try_with_route_level_call(first)
            if not ok:
                violations.append(f"{label}: {reason}")
    return violations


def test_all_post_routes_have_wired_identity_seam() -> None:
    violations = _collect_violations(
        source_files=SOURCE_FILES,
        matcher=_is_router_post,
    )
    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(
            f"{len(violations)} POST route(s) missing wired identity seam:\n{formatted}"
        )


def test_sensitive_get_routes_have_wired_identity_seam() -> None:
    violations = _collect_violations(
        source_files=SENSITIVE_GET_SOURCE_FILES,
        matcher=_is_router_get,
        exemptions=PUBLIC_GET_EXEMPTIONS,
        fail_soft_exemptions=DESIGNED_FAIL_SOFT_EXEMPTIONS,
    )
    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(
            f"{len(violations)} GET route(s) missing wired identity seam:\n{formatted}"
        )


def test_source_files_are_parseable() -> None:
    for path in [*SOURCE_FILES, *SENSITIVE_GET_SOURCE_FILES]:
        assert path.exists(), f"source file not found: {path}"
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
