"""Tests for layer3_deterministic_methods registry.

Verifies: method purity (same input -> same result), composition counts,
unknown method handling, and render helpers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import pytest

from app.services.layer3_deterministic_methods import (
    DETERMINISTIC_METHODS,
    DETERMINISTIC_METHODS_SCHEMA_ID,
    render_body,
    render_title,
    run_method,
)


# ---------------------------------------------------------------------------
# Minimal stub to avoid importing ORM machinery for pure-method tests
# ---------------------------------------------------------------------------


class _FakeWorkingSet:
    """Minimal stand-in for L3WorkingSet for pure-method testing."""

    def __init__(self, *, name: str, member_refs_json: list, member_count: int, basis_hash: str = "abc123"):
        self.name = name
        self.member_refs_json = member_refs_json
        self.member_count = member_count
        self.basis_hash = basis_hash


# ---------------------------------------------------------------------------
# Schema ID
# ---------------------------------------------------------------------------


def test_schema_id_is_stable() -> None:
    assert DETERMINISTIC_METHODS_SCHEMA_ID == "layer3.deterministic_method.v1"


# ---------------------------------------------------------------------------
# Registry structure
# ---------------------------------------------------------------------------


def test_registry_has_working_set_composition_summary() -> None:
    assert "working_set_composition_summary" in DETERMINISTIC_METHODS
    spec = DETERMINISTIC_METHODS["working_set_composition_summary"]
    assert spec.method_id == "working_set_composition_summary"
    assert spec.version == 1
    assert callable(spec.fn)


# ---------------------------------------------------------------------------
# Method purity: same input -> same result
# ---------------------------------------------------------------------------


def test_run_method_is_pure_same_input_same_result() -> None:
    ws = _FakeWorkingSet(
        name="Test Set",
        member_refs_json=[
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
            {"ref_kind": "pass_run", "ref_id": "run-1"},
        ],
        member_count=2,
    )
    result1 = run_method("working_set_composition_summary", working_set=ws)
    result2 = run_method("working_set_composition_summary", working_set=ws)
    assert result1 == result2


def test_run_method_reorder_members_same_counts() -> None:
    """Order of member_refs does not change composition counts."""
    ws_a = _FakeWorkingSet(
        name="Test Set",
        member_refs_json=[
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
            {"ref_kind": "pass_run", "ref_id": "run-1"},
        ],
        member_count=2,
    )
    ws_b = _FakeWorkingSet(
        name="Test Set",
        member_refs_json=[
            {"ref_kind": "pass_run", "ref_id": "run-1"},
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
        ],
        member_count=2,
    )
    r_a = run_method("working_set_composition_summary", working_set=ws_a)
    r_b = run_method("working_set_composition_summary", working_set=ws_b)
    # Full result equality (not just by_ref_kind): member order must not affect ANY field.
    assert r_a == r_b


# ---------------------------------------------------------------------------
# Composition counts are correct
# ---------------------------------------------------------------------------


def test_composition_counts_single_kind() -> None:
    ws = _FakeWorkingSet(
        name="Single Kind",
        member_refs_json=[
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
            {"ref_kind": "material_snapshot", "ref_id": "snap-2"},
            {"ref_kind": "material_snapshot", "ref_id": "snap-3"},
        ],
        member_count=3,
    )
    result = run_method("working_set_composition_summary", working_set=ws)
    assert result["method_id"] == "working_set_composition_summary"
    assert result["method_version"] == 1
    assert result["by_ref_kind"] == {"material_snapshot": 3}
    assert result["member_count"] == 3
    assert result["distinct_ref_kinds"] == ["material_snapshot"]


def test_composition_counts_multiple_kinds() -> None:
    ws = _FakeWorkingSet(
        name="Multi Kind",
        member_refs_json=[
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
            {"ref_kind": "material_snapshot", "ref_id": "snap-2"},
            {"ref_kind": "pass_run", "ref_id": "run-1"},
            {"ref_kind": "analysis_set", "ref_id": "set-1"},
        ],
        member_count=4,
    )
    result = run_method("working_set_composition_summary", working_set=ws)
    assert result["by_ref_kind"] == {
        "material_snapshot": 2,
        "pass_run": 1,
        "analysis_set": 1,
    }
    assert result["member_count"] == 4
    # distinct_ref_kinds must be sorted
    assert result["distinct_ref_kinds"] == sorted(result["by_ref_kind"].keys())


def test_distinct_ref_kinds_is_sorted() -> None:
    ws = _FakeWorkingSet(
        name="Sort Test",
        member_refs_json=[
            {"ref_kind": "pass_run", "ref_id": "run-1"},
            {"ref_kind": "analysis_set", "ref_id": "set-1"},
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
        ],
        member_count=3,
    )
    result = run_method("working_set_composition_summary", working_set=ws)
    assert result["distinct_ref_kinds"] == sorted(result["distinct_ref_kinds"])


# ---------------------------------------------------------------------------
# Unknown method raises KeyError
# ---------------------------------------------------------------------------


def test_unknown_method_raises_key_error() -> None:
    ws = _FakeWorkingSet(name="X", member_refs_json=[], member_count=0)
    with pytest.raises(KeyError):
        run_method("nonexistent_method", working_set=ws)


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


def test_render_title_includes_name() -> None:
    ws = _FakeWorkingSet(name="My Analysis Set", member_refs_json=[], member_count=0)
    title = render_title("working_set_composition_summary", working_set=ws)
    assert "My Analysis Set" in title
    assert len(title) <= 256


def test_render_body_includes_counts() -> None:
    ws = _FakeWorkingSet(
        name="Body Test",
        member_refs_json=[
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
            {"ref_kind": "pass_run", "ref_id": "run-1"},
        ],
        member_count=2,
    )
    result = run_method("working_set_composition_summary", working_set=ws)
    body = render_body("working_set_composition_summary", result=result)
    assert "material_snapshot" in body
    assert "pass_run" in body
    assert "2" in body
    assert len(body) > 0


def test_render_body_is_deterministic() -> None:
    ws = _FakeWorkingSet(
        name="Det Body",
        member_refs_json=[
            {"ref_kind": "material_snapshot", "ref_id": "snap-1"},
        ],
        member_count=1,
    )
    result = run_method("working_set_composition_summary", working_set=ws)
    body1 = render_body("working_set_composition_summary", result=result)
    body2 = render_body("working_set_composition_summary", result=result)
    assert body1 == body2
