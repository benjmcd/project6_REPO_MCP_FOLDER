from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCE_FILES = [
    BACKEND / "app" / "api" / "layer3" / "handoff.py",
    BACKEND / "app" / "api" / "layer3" / "package.py",
    BACKEND / "app" / "api" / "layer3" / "source_ingestion.py",
]


def _is_router_post(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr == "post":
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


def _collect_violations() -> list[str]:
    violations: list[str] = []
    for source_path in SOURCE_FILES:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(_is_router_post(d) for d in node.decorator_list):
                continue
            fname = node.name
            lineno = node.lineno
            label = f"{source_path.name}:{lineno} {fname}"
            if not _has_param_named(node, "request"):
                violations.append(f"{label}: missing parameter 'request'")
                continue
            first = _first_executable_stmt(node)
            ok, reason = _is_try_with_route_level_call(first)
            if not ok:
                violations.append(f"{label}: {reason}")
    return violations


def test_all_post_routes_have_wired_identity_seam() -> None:
    violations = _collect_violations()
    if violations:
        formatted = "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(
            f"{len(violations)} POST route(s) missing wired identity seam:\n{formatted}"
        )


def test_source_files_are_parseable() -> None:
    for path in SOURCE_FILES:
        assert path.exists(), f"source file not found: {path}"
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
