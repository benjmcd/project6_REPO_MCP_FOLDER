"""AST-level drift guard: every _route_level_operator_identity call in the
layer3 route modules must declare access= as a keyword argument with a
constant value of "read" or "write".

No exemptions.  All call sites in the covered modules were annotated in the
same commit that introduced this guard, so it ships green and fully enforced.
"""
from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

# All layer3 modules that call _route_level_operator_identity via the standard
# Try-first-Expr shape (sec_xbrl.py uses a stricter mechanism for most routes
# but still calls _route_level_operator_identity for the runtime/posture GET).
SOURCE_FILES = [
    BACKEND / "app" / "api" / "layer3" / "__init__.py",
    BACKEND / "app" / "api" / "layer3" / "handoff.py",
    BACKEND / "app" / "api" / "layer3" / "package.py",
    BACKEND / "app" / "api" / "layer3" / "source_sec_edgar.py",
    BACKEND / "app" / "api" / "layer3" / "source_ingestion.py",
    BACKEND / "app" / "api" / "layer3" / "sec_xbrl.py",
]

_VALID_ACCESS_VALUES = {"read", "write"}


def _extract_access_kwarg(call: ast.Call) -> str | None:
    """Return the string value of access= kwarg on the call, or None."""
    for kw in call.keywords:
        if kw.arg == "access" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return None


def _collect_violations(source_path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "_route_level_operator_identity":
            continue
        # Found a call — check access= kwarg
        access_val = _extract_access_kwarg(node)
        label = f"{source_path.name}:{node.lineno}"
        if access_val is None:
            violations.append(
                f"{label}: access= keyword not present or not a string constant"
            )
        elif access_val not in _VALID_ACCESS_VALUES:
            violations.append(
                f"{label}: access={access_val!r} is not a valid access class "
                f"(must be 'read' or 'write')"
            )
    return violations


def test_all_layer3_identity_calls_declare_access_keyword() -> None:
    """Every _route_level_operator_identity call in layer3 modules must
    pass access= as a keyword argument with value 'read' or 'write'."""
    all_violations: list[str] = []
    for source_path in SOURCE_FILES:
        all_violations.extend(_collect_violations(source_path))

    if all_violations:
        formatted = "\n".join(f"  - {v}" for v in all_violations)
        raise AssertionError(
            f"{len(all_violations)} _route_level_operator_identity call(s) "
            f"missing or invalid access= declaration:\n{formatted}"
        )


def test_source_files_are_parseable() -> None:
    for path in SOURCE_FILES:
        assert path.exists(), f"source file not found: {path}"
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
