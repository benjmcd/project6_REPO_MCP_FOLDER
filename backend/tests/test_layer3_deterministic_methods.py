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
    _COMPOSITION_SUMMARY_KINDS,
    _MEMBER_STATE_PROFILE_KINDS,
    _STALENESS_DIAGNOSTIC_KINDS,
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


# ===========================================================================
# New-method registry entries
# ===========================================================================


def test_registry_has_member_state_profile() -> None:
    assert "working_set_member_state_profile" in DETERMINISTIC_METHODS
    spec = DETERMINISTIC_METHODS["working_set_member_state_profile"]
    assert spec.method_id == "working_set_member_state_profile"
    assert spec.version == 1
    assert spec.product_kind == "summary"
    assert spec.consumes_member_state is True
    assert callable(spec.fn)
    assert callable(spec.render_title)
    assert callable(spec.render_body)


def test_registry_has_staleness_diagnostic() -> None:
    assert "working_set_staleness_diagnostic" in DETERMINISTIC_METHODS
    spec = DETERMINISTIC_METHODS["working_set_staleness_diagnostic"]
    assert spec.method_id == "working_set_staleness_diagnostic"
    assert spec.version == 1
    assert spec.product_kind == "diagnostic"
    assert spec.consumes_member_state is True
    assert callable(spec.fn)
    assert callable(spec.render_title)
    assert callable(spec.render_body)


def test_composition_summary_not_consumes_member_state() -> None:
    spec = DETERMINISTIC_METHODS["working_set_composition_summary"]
    assert spec.consumes_member_state is False


# ---------------------------------------------------------------------------
# Helper: build a synthetic member_states frame
# ---------------------------------------------------------------------------


def _make_states(
    *,
    prior_products: list[dict] | None = None,
    pass_runs: list[dict] | None = None,
    output_packages: list[dict] | None = None,
    material_snapshots: list[dict] | None = None,
    analysis_sets: list[dict] | None = None,
    unresolved: list[tuple[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (member_refs, member_states) for the given inputs."""
    refs: list[dict] = []
    states: list[dict] = []

    def _add(ref_kind: str, ref_id: str, extra: dict) -> None:
        refs.append({"ref_kind": ref_kind, "ref_id": ref_id})
        states.append({"ref_kind": ref_kind, "ref_id": ref_id, "resolved": True, **extra})

    for i, p in enumerate(prior_products or []):
        _add("prior_product", p.get("ref_id", f"pp-{i}"), {
            "lifecycle_status": p.get("lifecycle_status", "draft"),
            "product_kind": p.get("product_kind", "summary"),
            "executor_type": p.get("executor_type", "human"),
        })
    for i, r in enumerate(pass_runs or []):
        _add("pass_run", r.get("ref_id", f"pr-{i}"), {
            "status": r.get("status", "completed"),
            "pass_type": r.get("pass_type", "associated_cohort"),
            "engine_family": r.get("engine_family", "wrapped_quantitative_analysis"),
        })
    for i, op in enumerate(output_packages or []):
        _add("output_package", op.get("ref_id", f"op-{i}"), {
            "status": op.get("status", "ready"),
            "package_kind": op.get("package_kind", "workbench"),
        })
    for i, ms in enumerate(material_snapshots or []):
        _add("material_snapshot", ms.get("ref_id", f"ms-{i}"), {
            "source_plane": ms.get("source_plane", "runtime"),
            "source_shape": ms.get("source_shape", "dataset_version"),
        })
    for i, aset in enumerate(analysis_sets or []):
        _add("analysis_set", aset.get("ref_id", f"as-{i}"), {
            "set_type": aset.get("set_type", "associated_cohort"),
            "group_count": aset.get("group_count", 0),
            "unit_count": aset.get("unit_count", 0),
        })
    for ref_kind, ref_id in (unresolved or []):
        refs.append({"ref_kind": ref_kind, "ref_id": ref_id})
        states.append({"ref_kind": ref_kind, "ref_id": ref_id, "resolved": False})

    return refs, states


# ===========================================================================
# working_set_member_state_profile — unit tests
# ===========================================================================


def test_member_state_profile_purity() -> None:
    """Same input -> same result (pure function)."""
    refs, states = _make_states(
        prior_products=[{"lifecycle_status": "accepted"}],
        pass_runs=[{"status": "completed"}],
        material_snapshots=[{"source_plane": "runtime"}],
    )
    ws = _FakeWorkingSet(name="P", member_refs_json=refs, member_count=len(refs))
    r1 = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    r2 = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert r1 == r2


def test_member_state_profile_member_order_invariance() -> None:
    """Swapping member order must not change the result (full dict equality)."""
    refs_a, states_a = _make_states(
        prior_products=[{"ref_id": "pp-x", "lifecycle_status": "accepted"}],
        pass_runs=[{"ref_id": "pr-x", "status": "completed"}],
        unresolved=[("material_snapshot", "ms-ghost")],
    )
    import random
    rng = random.Random(42)
    combined = list(zip(refs_a, states_a))
    rng.shuffle(combined)
    refs_b, states_b = zip(*combined) if combined else ([], [])
    refs_b, states_b = list(refs_b), list(states_b)
    ws_a = _FakeWorkingSet(name="Inv", member_refs_json=refs_a, member_count=len(refs_a))
    ws_b = _FakeWorkingSet(name="Inv", member_refs_json=refs_b, member_count=len(refs_b))
    r_a = run_method("working_set_member_state_profile", working_set=ws_a, member_states=states_a)
    r_b = run_method("working_set_member_state_profile", working_set=ws_b, member_states=states_b)
    # Full result-dict equality: member order must not affect ANY field.
    assert r_a == r_b


def test_member_state_profile_rollup_counts() -> None:
    refs, states = _make_states(
        prior_products=[
            {"ref_id": "pp-1", "lifecycle_status": "accepted"},
            {"ref_id": "pp-2", "lifecycle_status": "superseded"},
            {"ref_id": "pp-3", "lifecycle_status": "accepted"},
        ],
        pass_runs=[
            {"ref_id": "pr-1", "status": "completed"},
            {"ref_id": "pr-2", "status": "failed"},
        ],
        material_snapshots=[{"ref_id": "ms-1", "source_plane": "runtime"}],
    )
    ws = _FakeWorkingSet(name="RC", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["prior_product"]["by_lifecycle_status"]["accepted"] == 2
    assert result["prior_product"]["by_lifecycle_status"]["superseded"] == 1
    assert result["pass_run"]["by_status"]["completed"] == 1
    assert result["pass_run"]["by_status"]["failed"] == 1
    assert result["material_snapshot"]["by_source_plane"]["runtime"] == 1
    assert result["member_count"] == len(refs)
    assert result["unresolved"]["count"] == 0


def test_member_state_profile_unresolved_prominence() -> None:
    """Unresolved members must appear in the result with an exact count (R5)."""
    refs, states = _make_states(
        prior_products=[{"ref_id": "pp-ok", "lifecycle_status": "draft"}],
        unresolved=[("pass_run", "pr-missing")],
    )
    ws = _FakeWorkingSet(name="Unres", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["unresolved"]["count"] == 1
    assert "pr-missing" in result["unresolved"]["refs"]


def test_member_state_profile_body_cap_20() -> None:
    """Body lists at most 20 unresolved refs, with '+K more' suffix."""
    n = 25
    refs, states = _make_states(
        unresolved=[("prior_product", f"pp-{i}") for i in range(n)],
    )
    ws = _FakeWorkingSet(name="Cap", member_refs_json=refs, member_count=n)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    body = render_body("working_set_member_state_profile", result=result)
    assert f"+{n - 20} more" in body
    assert result["unresolved"]["count"] == n


def test_member_state_profile_result_cap_100() -> None:
    """result_summary ref lists are capped at 100 (exact count preserved)."""
    n = 150
    refs, states = _make_states(
        unresolved=[("prior_product", f"pp-{i}") for i in range(n)],
    )
    ws = _FakeWorkingSet(name="Cap100", member_refs_json=refs, member_count=n)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["unresolved"]["count"] == n
    assert len(result["unresolved"]["refs"]) == 100


def test_member_state_profile_body_under_16384() -> None:
    """Body for a large synthetic frame must be < 16384 chars (R4)."""
    n = 200
    refs, states = _make_states(
        prior_products=[{"ref_id": f"pp-{i}", "lifecycle_status": "accepted"} for i in range(n)],
        pass_runs=[{"ref_id": f"pr-{i}", "status": "completed"} for i in range(n)],
        unresolved=[("material_snapshot", f"ms-{i}") for i in range(n)],
    )
    ws = _FakeWorkingSet(name="Large", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    body = render_body("working_set_member_state_profile", result=result)
    assert len(body) < 16384


def test_member_state_profile_consumes_state_none_raises() -> None:
    """Passing member_states=None for a state-consuming method raises ValueError."""
    ws = _FakeWorkingSet(name="X", member_refs_json=[], member_count=0)
    with pytest.raises(ValueError):
        run_method("working_set_member_state_profile", working_set=ws, member_states=None)


# ===========================================================================
# working_set_staleness_diagnostic — unit tests
# ===========================================================================


def test_staleness_diagnostic_clean_verdict() -> None:
    """All-clean working set -> clean=True, no issues."""
    refs, states = _make_states(
        prior_products=[{"ref_id": "pp-1", "lifecycle_status": "accepted"}],
        pass_runs=[{"ref_id": "pr-1", "status": "completed"}],
    )
    ws = _FakeWorkingSet(name="Clean", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is True
    assert result["superseded_prior_products"]["count"] == 0
    assert result["failed_pass_runs"]["count"] == 0
    assert result["unresolved_members"]["count"] == 0


def test_staleness_diagnostic_stale_superseded() -> None:
    refs, states = _make_states(
        prior_products=[
            {"ref_id": "pp-ok", "lifecycle_status": "accepted"},
            {"ref_id": "pp-sup", "lifecycle_status": "superseded"},
        ],
    )
    ws = _FakeWorkingSet(name="Stale", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is False
    assert result["superseded_prior_products"]["count"] == 1
    assert "pp-sup" in result["superseded_prior_products"]["members"]


def test_staleness_diagnostic_stale_failed_pass_run() -> None:
    refs, states = _make_states(
        pass_runs=[
            {"ref_id": "pr-ok", "status": "completed"},
            {"ref_id": "pr-fail", "status": "failed"},
        ],
    )
    ws = _FakeWorkingSet(name="Stale", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is False
    assert result["failed_pass_runs"]["count"] == 1
    assert "pr-fail" in result["failed_pass_runs"]["members"]


def test_staleness_diagnostic_stale_unresolved() -> None:
    refs, states = _make_states(
        unresolved=[("prior_product", "pp-ghost")],
    )
    ws = _FakeWorkingSet(name="Stale", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is False
    assert result["unresolved_members"]["count"] == 1
    assert "pp-ghost" in result["unresolved_members"]["members"]


def test_staleness_diagnostic_informational_not_stale() -> None:
    """incomplete + completed_with_warnings are informational and do NOT set clean=False."""
    refs, states = _make_states(
        pass_runs=[
            {"ref_id": "pr-plan", "status": "planned"},
            {"ref_id": "pr-warn", "status": "completed_with_warnings"},
        ],
    )
    ws = _FakeWorkingSet(name="Info", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is True
    assert result["incomplete_pass_runs"] == 1
    assert result["pass_runs_completed_with_warnings"] == 1


def test_staleness_diagnostic_body_verdict_line() -> None:
    refs, states = _make_states(
        prior_products=[{"ref_id": "pp-sup", "lifecycle_status": "superseded"}],
    )
    ws = _FakeWorkingSet(name="VLine", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    body = render_body("working_set_staleness_diagnostic", result=result)
    assert "Staleness verdict: stale" in body


def test_staleness_diagnostic_body_clean_verdict() -> None:
    refs, states = _make_states(
        pass_runs=[{"ref_id": "pr-1", "status": "completed"}],
    )
    ws = _FakeWorkingSet(name="VClean", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    body = render_body("working_set_staleness_diagnostic", result=result)
    assert "Staleness verdict: clean" in body


def test_staleness_diagnostic_body_cap_20() -> None:
    n = 30
    refs, states = _make_states(
        prior_products=[{"ref_id": f"pp-{i}", "lifecycle_status": "superseded"} for i in range(n)],
    )
    ws = _FakeWorkingSet(name="Cap20", member_refs_json=refs, member_count=n)
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    body = render_body("working_set_staleness_diagnostic", result=result)
    assert f"+{n - 20} more" in body
    assert result["superseded_prior_products"]["count"] == n


def test_staleness_diagnostic_result_cap_100() -> None:
    n = 150
    refs, states = _make_states(
        prior_products=[{"ref_id": f"pp-{i}", "lifecycle_status": "superseded"} for i in range(n)],
    )
    ws = _FakeWorkingSet(name="Cap100", member_refs_json=refs, member_count=n)
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["superseded_prior_products"]["count"] == n
    assert len(result["superseded_prior_products"]["members"]) == 100


def test_staleness_diagnostic_body_under_16384() -> None:
    n = 200
    refs, states = _make_states(
        prior_products=[{"ref_id": f"pp-{i}", "lifecycle_status": "superseded"} for i in range(n)],
        pass_runs=[{"ref_id": f"pr-{i}", "status": "failed"} for i in range(n)],
        unresolved=[("material_snapshot", f"ms-{i}") for i in range(n)],
    )
    ws = _FakeWorkingSet(name="Large", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    body = render_body("working_set_staleness_diagnostic", result=result)
    assert len(body) < 16384


def test_staleness_diagnostic_purity() -> None:
    refs, states = _make_states(
        prior_products=[{"ref_id": "pp-sup", "lifecycle_status": "superseded"}],
        pass_runs=[{"ref_id": "pr-fail", "status": "failed"}],
    )
    ws = _FakeWorkingSet(name="Pure", member_refs_json=refs, member_count=len(refs))
    r1 = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    r2 = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert r1 == r2


def test_staleness_diagnostic_member_order_invariance() -> None:
    """Shuffling member order must not change the staleness result (full dict equality)."""
    import random
    refs_a, states_a = _make_states(
        prior_products=[
            {"ref_id": "pp-sup", "lifecycle_status": "superseded"},
            {"ref_id": "pp-ok", "lifecycle_status": "accepted"},
        ],
        pass_runs=[
            {"ref_id": "pr-fail", "status": "failed"},
            {"ref_id": "pr-ok", "status": "completed"},
        ],
        unresolved=[("material_snapshot", "ms-ghost")],
    )
    rng = random.Random(99)
    combined = list(zip(refs_a, states_a))
    rng.shuffle(combined)
    refs_b, states_b = zip(*combined)
    refs_b, states_b = list(refs_b), list(states_b)
    ws_a = _FakeWorkingSet(name="Inv", member_refs_json=refs_a, member_count=len(refs_a))
    ws_b = _FakeWorkingSet(name="Inv", member_refs_json=refs_b, member_count=len(refs_b))
    r_a = run_method("working_set_staleness_diagnostic", working_set=ws_a, member_states=states_a)
    r_b = run_method("working_set_staleness_diagnostic", working_set=ws_b, member_states=states_b)
    # Full result-dict equality: member order must not affect ANY field.
    assert r_a == r_b


def test_staleness_diagnostic_consumes_state_none_raises() -> None:
    ws = _FakeWorkingSet(name="X", member_refs_json=[], member_count=0)
    with pytest.raises(ValueError):
        run_method("working_set_staleness_diagnostic", working_set=ws, member_states=None)


# ===========================================================================
# render_title / render_body dispatchers — generic fallback preserved
# ===========================================================================


def test_render_title_fallback_unknown_method() -> None:
    ws = _FakeWorkingSet(name="FB", member_refs_json=[], member_count=0)
    title = render_title("nonexistent_method_xyz", working_set=ws)
    assert "nonexistent_method_xyz" in title


def test_render_body_fallback_unknown_method() -> None:
    result = {"method_id": "nonexistent_method_xyz", "method_version": 99}
    body = render_body("nonexistent_method_xyz", result=result)
    assert "nonexistent_method_xyz" in body


def test_render_title_member_state_profile_includes_name() -> None:
    ws = _FakeWorkingSet(name="My Profile Set", member_refs_json=[], member_count=0)
    title = render_title("working_set_member_state_profile", working_set=ws)
    assert "My Profile Set" in title
    assert len(title) <= 512


def test_render_title_staleness_diagnostic_includes_name() -> None:
    ws = _FakeWorkingSet(name="My Diag Set", member_refs_json=[], member_count=0)
    title = render_title("working_set_staleness_diagnostic", working_set=ws)
    assert "My Diag Set" in title


# ===========================================================================
# Rollup bounding: _ROLLUP_RESULT_CAP=25, _ROLLUP_BODY_CAP=10
# ===========================================================================


def test_rollup_result_cap_lists_exactly_25_with_exact_distinct_count() -> None:
    """30 distinct source_plane values -> result lists exactly 25, distinct count = 30."""
    n = 30
    # Give each a unique source_plane value; one member per plane, so all counts == 1
    refs, states = _make_states(
        material_snapshots=[{"ref_id": f"ms-{i}", "source_plane": f"plane-{i:02d}"} for i in range(n)],
    )
    ws = _FakeWorkingSet(name="RollupCap", member_refs_json=refs, member_count=n)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    ms_section = result["material_snapshot"]
    assert ms_section["distinct_source_plane_values"] == n
    assert len(ms_section["by_source_plane"]) == 25


def test_rollup_result_cap_ordering_by_count_desc_then_key_asc() -> None:
    """Cap selects top entries by (-count, key): count descending, then key ascending."""
    # Create 30 planes: plane-00..plane-05 get 3 hits each, plane-06..plane-29 get 1 hit each
    # (6 high-count + 24 low-count = 30 total distinct)
    # Top 25 by (-count, key) = plane-00..05 (count=3) + plane-06..plane-24 (count=1, alpha order)
    high_planes = [f"plane-{i:02d}" for i in range(6)]  # 6 planes x 3 members = 18 members
    low_planes = [f"plane-{i:02d}" for i in range(6, 30)]  # 24 planes x 1 member = 24 members

    snapshots = []
    uid = 0
    for p in high_planes:
        for _ in range(3):
            snapshots.append({"ref_id": f"ms-h-{uid}", "source_plane": p})
            uid += 1
    for p in low_planes:
        snapshots.append({"ref_id": f"ms-l-{uid}", "source_plane": p})
        uid += 1

    refs, states = _make_states(material_snapshots=snapshots)
    ws = _FakeWorkingSet(name="Order", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    ms_section = result["material_snapshot"]

    assert ms_section["distinct_source_plane_values"] == 30
    listed_keys = list(ms_section["by_source_plane"].keys())
    assert len(listed_keys) == 25

    # All 6 high-count planes must be present
    for p in high_planes:
        assert p in ms_section["by_source_plane"]
        assert ms_section["by_source_plane"][p] == 3

    # The 19 low-count planes included must be the lexicographically first 19
    # (plane-06..plane-24), because among equal counts key-ascending order applies
    expected_low = sorted(low_planes)[:19]
    for p in expected_low:
        assert p in ms_section["by_source_plane"]

    # plane-25..plane-29 must be excluded (25th and beyond after sorting low-count set)
    excluded_low = sorted(low_planes)[19:]
    for p in excluded_low:
        assert p not in ms_section["by_source_plane"]


def test_rollup_body_cap_10_lines_plus_more_suffix() -> None:
    """30 distinct source_plane values -> body shows 10 lines + '+20 more values'."""
    n = 30
    refs, states = _make_states(
        material_snapshots=[{"ref_id": f"ms-{i}", "source_plane": f"plane-{i:02d}"} for i in range(n)],
    )
    ws = _FakeWorkingSet(name="BodyCap", member_refs_json=refs, member_count=n)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    body = render_body("working_set_member_state_profile", result=result)
    assert "+20 more values" in body
    # Count how many "plane-" lines appear in the body (each rollup entry line)
    plane_lines = [ln for ln in body.splitlines() if "plane-" in ln]
    assert len(plane_lines) == 10


def test_rollup_tie_ordering_is_key_ascending() -> None:
    """When counts are equal, keys must appear in ascending alphabetical order."""
    # All planes have count=1; alphabetical order must be preserved in listed keys
    planes = ["zebra-plane", "alpha-plane", "middle-plane", "beta-plane"]
    refs, states = _make_states(
        material_snapshots=[{"ref_id": f"ms-{i}", "source_plane": p} for i, p in enumerate(planes)],
    )
    ws = _FakeWorkingSet(name="TieOrder", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    listed = list(result["material_snapshot"]["by_source_plane"].keys())
    assert listed == sorted(planes)


def test_rollup_small_frame_full_mapping_and_distinct_count_equal() -> None:
    """Frames under caps keep full mappings and distinct_* == len(by_*)."""
    refs, states = _make_states(
        material_snapshots=[
            {"ref_id": "ms-a", "source_plane": "runtime"},
            {"ref_id": "ms-b", "source_plane": "archive"},
        ],
        output_packages=[
            {"ref_id": "op-a", "status": "ready"},
        ],
        prior_products=[
            {"ref_id": "pp-a", "lifecycle_status": "accepted"},
        ],
        pass_runs=[
            {"ref_id": "pr-a", "status": "completed"},
        ],
    )
    ws = _FakeWorkingSet(name="Small", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)

    ms = result["material_snapshot"]
    assert ms["distinct_source_plane_values"] == 2
    assert len(ms["by_source_plane"]) == 2

    op = result["output_package"]
    assert op["distinct_status_values"] == 1
    assert len(op["by_status"]) == 1

    pp = result["prior_product"]
    assert pp["distinct_lifecycle_status_values"] == 1
    assert len(pp["by_lifecycle_status"]) == 1

    pr = result["pass_run"]
    assert pr["distinct_status_values"] == 1
    assert len(pr["by_status"]) == 1


# ===========================================================================
# Method input authority / fail-closed (Lane 5)
# ===========================================================================


def test_method_spec_declares_accepted_member_kinds() -> None:
    """Every registry entry must declare a non-empty accepted_member_kinds frozenset."""
    for method_id, spec in DETERMINISTIC_METHODS.items():
        assert isinstance(spec.accepted_member_kinds, frozenset), (
            f"{method_id}: accepted_member_kinds must be a frozenset"
        )
        assert len(spec.accepted_member_kinds) > 0, (
            f"{method_id}: accepted_member_kinds must not be empty"
        )


def test_method_accepted_kinds_match_model_enum() -> None:
    """Drift guard: each method's accepted_member_kinds equals the model's current
    canonical ref-kind enum. This test FAILS when a new ref_kind is added to
    L3_WORKING_SET_MEMBER_REF_KIND_VALUES, forcing a deliberate review of every
    method's handler before the new kind is accepted — until then run_method fails
    closed on the new kind. The accepted sets are explicit literals (not derived
    from the enum) precisely so this check is meaningful."""
    from app.models.models import L3_WORKING_SET_MEMBER_REF_KIND_VALUES

    enum_kinds = frozenset(L3_WORKING_SET_MEMBER_REF_KIND_VALUES)
    for method_id, spec in DETERMINISTIC_METHODS.items():
        assert spec.accepted_member_kinds == enum_kinds, (
            f"{method_id}: accepted_member_kinds {sorted(spec.accepted_member_kinds)} "
            f"drifted from the model enum {sorted(enum_kinds)} — review this method's "
            f"handler for the new kind(s) and update its accepted set deliberately."
        )


def test_run_method_rejects_unsupported_member_kind() -> None:
    """A working set containing ref_kind='custom_unknown_type' raises ValueError for all 3 methods."""
    ws_state_free = _FakeWorkingSet(
        name="Bad Kind",
        member_refs_json=[{"ref_kind": "custom_unknown_type", "ref_id": "ref-001"}],
        member_count=1,
    )

    # State-free method
    with pytest.raises(ValueError) as exc_info:
        run_method("working_set_composition_summary", working_set=ws_state_free)
    msg = str(exc_info.value)
    assert "custom_unknown_type" in msg
    # Must list kind names only — not ref_ids
    assert "ref-001" not in msg

    # State-consuming methods need member_states; include the unsupported kind there too
    unknown_states = [{"ref_kind": "custom_unknown_type", "ref_id": "ref-001", "resolved": False}]

    with pytest.raises(ValueError) as exc_info:
        run_method(
            "working_set_member_state_profile",
            working_set=ws_state_free,
            member_states=unknown_states,
        )
    assert "custom_unknown_type" in str(exc_info.value)
    assert "ref-001" not in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        run_method(
            "working_set_staleness_diagnostic",
            working_set=ws_state_free,
            member_states=unknown_states,
        )
    assert "custom_unknown_type" in str(exc_info.value)
    assert "ref-001" not in str(exc_info.value)


def test_run_method_accepts_all_canonical_kinds() -> None:
    """A working set with one member of each canonical kind passes all 3 methods without raising."""
    refs = [{"ref_kind": k, "ref_id": f"ref-{k}"} for k in sorted(_COMPOSITION_SUMMARY_KINDS)]
    states = [{"ref_kind": k, "ref_id": f"ref-{k}", "resolved": False} for k in sorted(_COMPOSITION_SUMMARY_KINDS)]
    ws = _FakeWorkingSet(name="All Canonical", member_refs_json=refs, member_count=len(refs))

    # State-free method
    result = run_method("working_set_composition_summary", working_set=ws)
    assert result["member_count"] == len(refs)

    # State-consuming methods
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["member_count"] == len(refs)

    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["member_count"] == len(refs)


def test_run_method_fail_closed_partial_unsupported() -> None:
    """Mixing supported kinds with one unsupported kind still raises (no partial accept)."""
    refs = [
        {"ref_kind": "material_snapshot", "ref_id": "ms-1"},
        {"ref_kind": "pass_run", "ref_id": "pr-1"},
        {"ref_kind": "custom_unknown_type", "ref_id": "ref-bad"},
    ]
    ws = _FakeWorkingSet(name="Partial Bad", member_refs_json=refs, member_count=3)

    with pytest.raises(ValueError) as exc_info:
        run_method("working_set_composition_summary", working_set=ws)
    msg = str(exc_info.value)
    assert "custom_unknown_type" in msg
    # The message must mention what was accepted too
    assert "accepted" in msg


# ===========================================================================
# Lane 4 — fixture-backed expected-output + edge-case tests
# ===========================================================================


# ---------------------------------------------------------------------------
# composition_summary — fixture-backed + edge cases
# ---------------------------------------------------------------------------


def test_composition_summary_empty_working_set() -> None:
    """Empty working set: member_refs_json=[] -> zero counts, empty dicts/lists."""
    ws = _FakeWorkingSet(name="Empty", member_refs_json=[], member_count=0)
    result = run_method("working_set_composition_summary", working_set=ws)
    assert result["by_ref_kind"] == {}
    assert result["distinct_ref_kinds"] == []
    assert result["member_count"] == 0
    assert result["method_id"] == "working_set_composition_summary"
    assert result["method_version"] == 1


def test_composition_summary_single_member() -> None:
    """Single member of one kind -> by_ref_kind == {kind: 1}, distinct_ref_kinds == [kind]."""
    ws = _FakeWorkingSet(
        name="Single",
        member_refs_json=[{"ref_kind": "pass_run", "ref_id": "pr-solo"}],
        member_count=1,
    )
    result = run_method("working_set_composition_summary", working_set=ws)
    assert result["by_ref_kind"] == {"pass_run": 1}
    assert result["distinct_ref_kinds"] == ["pass_run"]
    assert result["member_count"] == 1


# ---------------------------------------------------------------------------
# member_state_profile — fixture-backed + edge cases
# ---------------------------------------------------------------------------


def test_member_state_profile_empty_working_set() -> None:
    """Empty working set and empty member_states -> all rollups empty, unresolved.count == 0."""
    ws = _FakeWorkingSet(name="EmptyProfile", member_refs_json=[], member_count=0)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=[])
    assert result["member_count"] == 0
    assert result["by_ref_kind"] == {}
    assert result["prior_product"]["by_lifecycle_status"] == {}
    assert result["prior_product"]["distinct_lifecycle_status_values"] == 0
    assert result["pass_run"]["by_status"] == {}
    assert result["pass_run"]["distinct_status_values"] == 0
    assert result["output_package"]["by_status"] == {}
    assert result["output_package"]["distinct_status_values"] == 0
    assert result["material_snapshot"]["by_source_plane"] == {}
    assert result["material_snapshot"]["distinct_source_plane_values"] == 0
    assert result["analysis_set"]["count"] == 0
    assert result["analysis_set"]["total_group_refs"] == 0
    assert result["analysis_set"]["total_unit_refs"] == 0
    assert result["unresolved"]["count"] == 0
    assert result["unresolved"]["refs"] == []


def test_member_state_profile_all_unresolved() -> None:
    """3 members all resolved=False -> unresolved.count == 3, every rollup empty."""
    refs = [
        {"ref_kind": "prior_product", "ref_id": "pp-a"},
        {"ref_kind": "pass_run", "ref_id": "pr-b"},
        {"ref_kind": "material_snapshot", "ref_id": "ms-c"},
    ]
    states = [
        {"ref_kind": "prior_product", "ref_id": "pp-a", "resolved": False},
        {"ref_kind": "pass_run", "ref_id": "pr-b", "resolved": False},
        {"ref_kind": "material_snapshot", "ref_id": "ms-c", "resolved": False},
    ]
    ws = _FakeWorkingSet(name="AllUnres", member_refs_json=refs, member_count=3)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["unresolved"]["count"] == 3
    # refs list must be sorted and contain all three
    assert result["unresolved"]["refs"] == sorted(["pp-a", "pr-b", "ms-c"])
    # Every rollup must be empty because all members are unresolved
    assert result["prior_product"]["by_lifecycle_status"] == {}
    assert result["pass_run"]["by_status"] == {}
    assert result["output_package"]["by_status"] == {}
    assert result["material_snapshot"]["by_source_plane"] == {}
    assert result["analysis_set"]["count"] == 0


def test_member_state_profile_missing_state_entry_counted_as_unresolved() -> None:
    """A member in member_refs_json with NO matching entry in member_states -> unresolved."""
    refs = [
        {"ref_kind": "pass_run", "ref_id": "pr-present"},
        {"ref_kind": "pass_run", "ref_id": "pr-missing"},
    ]
    # Only provide state for one of the two members
    states = [
        {"ref_kind": "pass_run", "ref_id": "pr-present", "resolved": True, "status": "completed"},
    ]
    ws = _FakeWorkingSet(name="MissingState", member_refs_json=refs, member_count=2)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["unresolved"]["count"] == 1
    assert "pr-missing" in result["unresolved"]["refs"]
    # The resolved one must appear in the rollup
    assert result["pass_run"]["by_status"]["completed"] == 1


def test_member_state_profile_missing_optional_fields_use_unknown_bucket() -> None:
    """Resolved prior_product with lifecycle_status absent/None -> 'unknown' bucket.
    Resolved material_snapshot with source_plane absent -> 'unknown' bucket."""
    refs = [
        {"ref_kind": "prior_product", "ref_id": "pp-no-status"},
        {"ref_kind": "prior_product", "ref_id": "pp-none-status"},
        {"ref_kind": "material_snapshot", "ref_id": "ms-no-plane"},
    ]
    states = [
        # lifecycle_status key absent entirely
        {"ref_kind": "prior_product", "ref_id": "pp-no-status", "resolved": True},
        # lifecycle_status present but None
        {"ref_kind": "prior_product", "ref_id": "pp-none-status", "resolved": True, "lifecycle_status": None},
        # source_plane key absent entirely
        {"ref_kind": "material_snapshot", "ref_id": "ms-no-plane", "resolved": True},
    ]
    ws = _FakeWorkingSet(name="MissingOptional", member_refs_json=refs, member_count=3)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    # Both prior_products with absent/None lifecycle_status fall into 'unknown'
    assert result["prior_product"]["by_lifecycle_status"].get("unknown") == 2
    # material_snapshot with absent source_plane falls into 'unknown'
    assert result["material_snapshot"]["by_source_plane"].get("unknown") == 1
    # All three are resolved, so unresolved.count == 0
    assert result["unresolved"]["count"] == 0


def test_member_state_profile_analysis_set_zero_counts() -> None:
    """Resolved analysis_sets with group_count/unit_count == 0 -> totals remain 0."""
    refs, states = _make_states(
        analysis_sets=[
            {"ref_id": "as-zero", "group_count": 0, "unit_count": 0},
        ],
    )
    ws = _FakeWorkingSet(name="ASZero", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["analysis_set"]["count"] == 1
    assert result["analysis_set"]["total_group_refs"] == 0
    assert result["analysis_set"]["total_unit_refs"] == 0


def test_member_state_profile_analysis_set_sum_totals() -> None:
    """Multiple resolved analysis_sets -> total_group_refs and total_unit_refs equal the sums."""
    refs, states = _make_states(
        analysis_sets=[
            {"ref_id": "as-1", "group_count": 3, "unit_count": 7},
            {"ref_id": "as-2", "group_count": 5, "unit_count": 2},
            {"ref_id": "as-3", "group_count": 0, "unit_count": 11},
        ],
    )
    ws = _FakeWorkingSet(name="ASSum", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    assert result["analysis_set"]["count"] == 3
    assert result["analysis_set"]["total_group_refs"] == 3 + 5 + 0
    assert result["analysis_set"]["total_unit_refs"] == 7 + 2 + 11


def test_member_state_profile_result_structure() -> None:
    """Result dict has exactly the documented top-level keys (guards against schema drift)."""
    refs, states = _make_states(
        prior_products=[{"ref_id": "pp-1", "lifecycle_status": "accepted"}],
    )
    ws = _FakeWorkingSet(name="Schema", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    expected_keys = {
        "method_id",
        "method_version",
        "member_count",
        "by_ref_kind",
        "prior_product",
        "pass_run",
        "output_package",
        "material_snapshot",
        "analysis_set",
        "unresolved",
    }
    assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# staleness_diagnostic — fixture-backed + edge cases
# ---------------------------------------------------------------------------


def test_staleness_diagnostic_empty_working_set() -> None:
    """Empty working set -> clean=True, all category counts 0."""
    ws = _FakeWorkingSet(name="EmptyDiag", member_refs_json=[], member_count=0)
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=[])
    assert result["clean"] is True
    assert result["member_count"] == 0
    assert result["superseded_prior_products"]["count"] == 0
    assert result["superseded_prior_products"]["members"] == []
    assert result["failed_pass_runs"]["count"] == 0
    assert result["failed_pass_runs"]["members"] == []
    assert result["unresolved_members"]["count"] == 0
    assert result["unresolved_members"]["members"] == []
    assert result["incomplete_pass_runs"] == 0
    assert result["pass_runs_completed_with_warnings"] == 0


def test_staleness_diagnostic_all_clean() -> None:
    """Resolved prior_product not superseded + resolved pass_run completed -> clean True."""
    refs, states = _make_states(
        prior_products=[{"ref_id": "pp-ok", "lifecycle_status": "accepted"}],
        pass_runs=[{"ref_id": "pr-ok", "status": "completed"}],
    )
    ws = _FakeWorkingSet(name="AllClean", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is True
    assert result["superseded_prior_products"]["count"] == 0
    assert result["failed_pass_runs"]["count"] == 0
    assert result["unresolved_members"]["count"] == 0
    assert result["incomplete_pass_runs"] == 0
    assert result["pass_runs_completed_with_warnings"] == 0


def test_staleness_diagnostic_multi_issue() -> None:
    """Superseded prior_product + failed pass_run + unresolved member -> clean False.
    Assert exact counts and that ref_ids appear in the right category lists."""
    refs = [
        {"ref_kind": "prior_product", "ref_id": "pp-sup"},
        {"ref_kind": "pass_run", "ref_id": "pr-fail"},
        {"ref_kind": "material_snapshot", "ref_id": "ms-ghost"},
    ]
    states = [
        {"ref_kind": "prior_product", "ref_id": "pp-sup", "resolved": True, "lifecycle_status": "superseded"},
        {"ref_kind": "pass_run", "ref_id": "pr-fail", "resolved": True, "status": "failed"},
        {"ref_kind": "material_snapshot", "ref_id": "ms-ghost", "resolved": False},
    ]
    ws = _FakeWorkingSet(name="MultiIssue", member_refs_json=refs, member_count=3)
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is False
    assert result["superseded_prior_products"]["count"] == 1
    assert "pp-sup" in result["superseded_prior_products"]["members"]
    assert result["failed_pass_runs"]["count"] == 1
    assert "pr-fail" in result["failed_pass_runs"]["members"]
    assert result["unresolved_members"]["count"] == 1
    assert "ms-ghost" in result["unresolved_members"]["members"]
    # Informational counts not affected by the flagged issues
    assert result["incomplete_pass_runs"] == 0
    assert result["pass_runs_completed_with_warnings"] == 0


def test_staleness_diagnostic_all_incomplete_statuses_clean() -> None:
    """All three incomplete statuses (planned/running/selected_not_started) plus
    completed_with_warnings do NOT set clean=False; assert exact informational counters
    using the imported status constants (not string literals)."""
    from app.models.models import (
        L3_PASS_RUN_STATUS_PLANNED,
        L3_PASS_RUN_STATUS_RUNNING,
        L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED,
        L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS,
    )
    refs = [
        {"ref_kind": "pass_run", "ref_id": "pr-planned"},
        {"ref_kind": "pass_run", "ref_id": "pr-running"},
        {"ref_kind": "pass_run", "ref_id": "pr-sns"},
        {"ref_kind": "pass_run", "ref_id": "pr-warn"},
    ]
    states = [
        {"ref_kind": "pass_run", "ref_id": "pr-planned", "resolved": True, "status": L3_PASS_RUN_STATUS_PLANNED},
        {"ref_kind": "pass_run", "ref_id": "pr-running", "resolved": True, "status": L3_PASS_RUN_STATUS_RUNNING},
        {"ref_kind": "pass_run", "ref_id": "pr-sns", "resolved": True, "status": L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED},
        {"ref_kind": "pass_run", "ref_id": "pr-warn", "resolved": True, "status": L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS},
    ]
    ws = _FakeWorkingSet(name="InfoOnly", member_refs_json=refs, member_count=4)
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is True
    assert result["superseded_prior_products"]["count"] == 0
    assert result["failed_pass_runs"]["count"] == 0
    assert result["unresolved_members"]["count"] == 0
    assert result["incomplete_pass_runs"] == 3
    assert result["pass_runs_completed_with_warnings"] == 1


def test_staleness_diagnostic_unknown_pass_run_status_not_failed() -> None:
    """A resolved pass_run with status='unknown' is not classified as failed; clean stays True."""
    refs = [{"ref_kind": "pass_run", "ref_id": "pr-unk"}]
    states = [{"ref_kind": "pass_run", "ref_id": "pr-unk", "resolved": True, "status": "unknown"}]
    ws = _FakeWorkingSet(name="UnknownStatus", member_refs_json=refs, member_count=1)
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    assert result["clean"] is True
    assert result["failed_pass_runs"]["count"] == 0
    assert result["incomplete_pass_runs"] == 0
    assert result["pass_runs_completed_with_warnings"] == 0


def test_staleness_diagnostic_result_structure() -> None:
    """Result dict has exactly the documented top-level keys (guards against schema drift)."""
    refs, states = _make_states(
        pass_runs=[{"ref_id": "pr-1", "status": "completed"}],
    )
    ws = _FakeWorkingSet(name="DiagSchema", member_refs_json=refs, member_count=len(refs))
    result = run_method("working_set_staleness_diagnostic", working_set=ws, member_states=states)
    expected_keys = {
        "method_id",
        "method_version",
        "clean",
        "member_count",
        "superseded_prior_products",
        "failed_pass_runs",
        "unresolved_members",
        "incomplete_pass_runs",
        "pass_runs_completed_with_warnings",
    }
    assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# render bounds — title length and body rollup cap wording
# ---------------------------------------------------------------------------


def test_render_title_composition_summary_max_256() -> None:
    """render_title for composition_summary must be <= 256 chars."""
    ws = _FakeWorkingSet(name="Title Len Check", member_refs_json=[], member_count=0)
    title = render_title("working_set_composition_summary", working_set=ws)
    assert len(title) <= 256


def test_render_title_member_state_profile_max_512() -> None:
    """render_title for member_state_profile must be <= 512 chars."""
    ws = _FakeWorkingSet(name="Profile Title Len", member_refs_json=[], member_count=0)
    title = render_title("working_set_member_state_profile", working_set=ws)
    assert len(title) <= 512


def test_render_title_staleness_diagnostic_max_512() -> None:
    """render_title for staleness_diagnostic must be <= 512 chars."""
    ws = _FakeWorkingSet(name="Diag Title Len", member_refs_json=[], member_count=0)
    title = render_title("working_set_staleness_diagnostic", working_set=ws)
    assert len(title) <= 512


def test_render_body_member_state_profile_rollup_body_cap_plus_more_values() -> None:
    """member_state_profile with > _ROLLUP_BODY_CAP (10) distinct values in a rollup
    shows at most 10 lines + a '+N more values' indicator in the rendered body.

    Setup: 15 distinct prior_product lifecycle statuses (1 member each).
    Result cap (_ROLLUP_RESULT_CAP=25) keeps all 15.
    Body cap (_ROLLUP_BODY_CAP=10) shows 10 lines; remainder = 15 - 10 = 5.
    Expected suffix: '+5 more values'.
    """
    n = 15
    refs, states = _make_states(
        prior_products=[
            {"ref_id": f"pp-{i}", "lifecycle_status": f"status-{i:02d}"}
            for i in range(n)
        ],
    )
    ws = _FakeWorkingSet(name="RollupBodyCap", member_refs_json=refs, member_count=n)
    result = run_method("working_set_member_state_profile", working_set=ws, member_states=states)
    body = render_body("working_set_member_state_profile", result=result)
    # The rendered body must include the '+5 more values' suffix
    assert "+5 more values" in body
    # Exactly 10 'status-XX' lines should appear (the body-capped entries)
    status_lines = [ln for ln in body.splitlines() if "status-" in ln]
    assert len(status_lines) == 10
