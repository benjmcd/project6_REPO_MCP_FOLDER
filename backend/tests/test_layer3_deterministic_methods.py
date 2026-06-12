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
