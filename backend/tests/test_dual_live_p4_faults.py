from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import socket
from types import ModuleType

import pytest

import support_dual_live_p4 as p4


_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECOVERY_TOOL = _REPO_ROOT / "tools" / "dual_live_recovery.py"


def _load_recovery_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "dual_live_recovery_p4_integration",
        _RECOVERY_TOOL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def phase_a_template(tmp_path_factory) -> p4.PhaseAFixture:
    return p4.build_phase_a_fixture(tmp_path_factory.mktemp("p4-phase-a"))


def test_phase_b_fault_census_declares_exact_commit_boundaries() -> None:
    assert [item.connector_key for item in p4.PHASE_B_COMMIT_BOUNDARIES].count(
        "nrc_adams_aps"
    ) == 12
    assert [item.connector_key for item in p4.PHASE_B_COMMIT_BOUNDARIES].count(
        "sciencebase_mcs"
    ) == 10
    assert len({item.name for item in p4.PHASE_B_COMMIT_BOUNDARIES}) == 22
    assert [item.ordinal for item in p4.PHASE_B_COMMIT_BOUNDARIES] == list(
        range(1, 23)
    )


def test_fault_child_environment_is_secret_free_and_default_off() -> None:
    child_environment = p4.phase_b_child_environment(
        {
            "PATH": "fixture-path",
            "SYSTEMROOT": "C:\\Windows",
            "CONNECTOR_LIVE_EGRESS_ENABLED": "true",
            "CONNECTOR_NRC_APS_GRANT_PATH": "C:\\authority.json",
            "NRC_API_SUBSCRIPTION_KEY": "not-a-real-key",
            "UNRELATED_SECRET": "must-not-inherit",
        }
    )

    assert child_environment == {
        "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
        "PATH": "fixture-path",
        "SYSTEMROOT": "C:\\Windows",
        "TRUSTED_PROXY_MODE": "false",
    }


def test_phase_a_fixture_is_complete_and_phase_b_clean(tmp_path) -> None:
    fixture = p4.build_phase_a_fixture(tmp_path / "phase-a")

    snapshot = p4.snapshot_phase_a(fixture.root, fixture)

    assert snapshot["connector_keys"] == ["nrc_adams_aps", "sciencebase_mcs"]
    assert snapshot["run_statuses"] == ["completed", "completed"]
    assert len(snapshot["target_identities"]) == 2
    assert len(snapshot["raw_artifacts"]) == 2
    assert snapshot["phase_b_row_counts"] == {
        "aps_content_linkage": 0,
        "l3_session": 0,
    }


def test_real_process_kill_after_first_phase_b_commit_is_nonpass(tmp_path) -> None:
    fixture = p4.build_phase_a_fixture(tmp_path / "template")
    boundary = p4.PHASE_B_COMMIT_BOUNDARIES[0]

    result = p4.run_fault_cell(
        fixture,
        cell_root=tmp_path / "cell-01",
        boundary=boundary,
    )

    assert result.signal == boundary.name
    assert result.process_was_alive_at_kill is True
    assert result.returncode != 0
    assert result.durable_prefix == (boundary.name,)
    assert result.phase_a_before == result.phase_a_after
    assert result.evaluator_status in {"FAIL", "INDETERMINATE"}
    assert result.evaluator_status != "PASS"


def test_actual_killed_cell_is_poisoned_inspected_and_archived(
    tmp_path,
    monkeypatch,
) -> None:
    recovery = _load_recovery_tool()
    fixture = p4.build_phase_a_fixture(tmp_path / "phase-a")
    boundary = next(
        item
        for item in p4.PHASE_B_COMMIT_BOUNDARIES
        if item.name == "nrc_gate_b_decision"
    )
    result = p4.run_fault_cell(
        fixture,
        cell_root=tmp_path / "killed-cell",
        boundary=boundary,
    )
    recovery_input = result.recovery_input
    assert result.durable_prefix[-1] == boundary.name
    assert result.phase_a_before == result.phase_a_after

    arguments = {
        "campaign_id": recovery_input.campaign_id,
        "campaign_fingerprint": recovery_input.campaign_fingerprint,
        "database_path": str(recovery_input.database_path),
        "storage_root": str(recovery_input.storage_root),
        "evidence_root": str(recovery_input.evidence_root),
        "environ": {"CONNECTOR_LIVE_EGRESS_ENABLED": "false"},
    }
    network_calls: list[str] = []

    def deny_network(*_args: object, **_kwargs: object) -> None:
        network_calls.append("attempted")
        raise AssertionError("recovery network seam reached")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    poisoned = recovery.poison_campaign(
        **arguments,
        reason_code="phase_b_killed_after_commit",
    )
    poison_path = Path(poisoned["marker_path"])

    source_paths = [
        recovery_input.database_path,
        *(
            path
            for root in (
                recovery_input.storage_root,
                recovery_input.evidence_root,
            )
            for path in root.rglob("*")
            if path.is_file()
        ),
    ]
    source_hashes = {path: _file_sha256(path) for path in source_paths}
    inspected = recovery.inspect_campaign(**arguments)
    assert inspected["status"] == "POISONED_UNSEALED"
    assert inspected["capture"]["marker_kinds"] == ["poison"]

    archived = recovery.archive_campaign(
        **arguments,
        archive_root=str((tmp_path / "archive").resolve()),
    )
    assert archived["status"] == "ARCHIVED_POISONED_UNSEALED"
    archive_dir = Path(archived["archive_path"])
    manifest_path = archive_dir / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest_bytes == (
        json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert manifest["classification"] == "POISONED_UNSEALED"
    for item in manifest["files"]:
        if item["scope"] == "derived_inspection":
            continue
        copied = archive_dir / item["archive_relative_path"]
        assert _file_sha256(copied) == item["sha256"]
        assert copied.stat().st_size == item["size"]
    assert {path: _file_sha256(path) for path in source_paths} == source_hashes
    assert poison_path.is_file()
    assert network_calls == []

    with pytest.raises(recovery.RecoveryRefusal, match="archive_exists"):
        recovery.archive_campaign(
            **arguments,
            archive_root=str((tmp_path / "archive").resolve()),
        )
    assert _file_sha256(manifest_path) == archived["manifest_sha256"]


@pytest.mark.parametrize(
    "boundary",
    p4.PHASE_B_COMMIT_BOUNDARIES,
    ids=lambda item: item.name,
)
def test_each_phase_b_commit_kill_preserves_acquisition_and_never_passes(
    phase_a_template: p4.PhaseAFixture,
    tmp_path,
    boundary: p4.PhaseBCommitBoundary,
) -> None:
    result = p4.run_fault_cell(
        phase_a_template,
        cell_root=tmp_path / f"cell-{boundary.ordinal:02d}",
        boundary=boundary,
    )

    assert result.signal == boundary.name
    assert result.process_was_alive_at_kill is True
    assert result.returncode != 0
    assert result.durable_prefix == tuple(
        item.name
        for item in p4.PHASE_B_COMMIT_BOUNDARIES
        if item.ordinal <= boundary.ordinal
    )
    assert result.phase_a_before == result.phase_a_after
    assert result.evaluator_status in {"FAIL", "INDETERMINATE"}
    assert result.evaluator_status != "PASS"
