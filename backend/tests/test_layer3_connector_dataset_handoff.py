from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db  # noqa: E402
from app.core.config import Settings, bootstrap_storage_tree, settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.models import (  # noqa: E402
    AnalysisArtifact,
    AnalysisRun,
    ConnectorRun,
    ConnectorRunTarget,
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3TypingRecord,
)
from app.services.layer3_connector_source_intake import (  # noqa: E402
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
)
from app.services.layer3_gate_b_state import (  # noqa: E402
    material_candidate_basis_from_decision,
    material_preview_hash,
)
from app.services import layer3_workbench  # noqa: E402
from main import app  # noqa: E402


FIXTURE_BYTES = b"site_id,value\nSB-001,42\nSB-002,43\n"
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
NESTED_VALUE_SENTINEL = "UNMODELED-PRIVATE-SAMPLE"
NESTED_NUMERIC_SENTINEL = 987654321
HANDOFF_ROUTE = "/api/v1/layer3/handoff/connector/dataset"
DATASET_HANDOFF_FLAG = "layer3_connector_dataset_handoff_enabled"
EXPECTED_DOWNSTREAM_UNAVAILABLE = {
    "package_review_submit_enabled": False,
    "handoff_enabled": False,
    "external_export_download_enabled": False,
    "connector_dispatch_enabled": False,
    "provider_public_delivery_enabled": False,
    "frontend_durable_authority_enabled": False,
}
EXPECTED_NEGATIVE_INVARIANTS = {
    "source_package_row_mutation_enabled": False,
    "package_payload_rewrite_enabled": False,
    "package_review_submit_enabled": False,
    "handoff_export_enabled": False,
    "connector_dispatch_enabled": False,
    "provider_public_delivery_enabled": False,
    "network_egress_enabled": False,
    "frontend_durable_authority_enabled": False,
    "prompt_model_provider_runtime_enabled": False,
}
EXPECTED_DOWNSTREAM_UNAVAILABLE_ACTIONS = [
    "package_review_submit",
    "handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_delivery",
    "frontend_durable_authority",
]
FORBIDDEN_VALUE_KEYS = {
    "rows",
    "cells",
    "row_values",
    "cell_values",
    "preview_text",
    "raw_bytes",
    "csv_text",
}


@pytest.fixture(autouse=True)
def restore_dataset_handoff_flag():
    existed = DATASET_HANDOFF_FLAG in settings.__dict__
    previous = settings.__dict__.get(DATASET_HANDOFF_FLAG)
    try:
        yield
    finally:
        if existed:
            settings.__dict__[DATASET_HANDOFF_FLAG] = previous
        else:
            settings.__dict__.pop(DATASET_HANDOFF_FLAG, None)


def _set_dataset_handoff_enabled(value: bool) -> None:
    settings.__dict__[DATASET_HANDOFF_FLAG] = value


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'handoff.db'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 0.2},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.layer3_session_factory = session_factory
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _decision_basis(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        key: candidate[key]
        for key in (
            "source_ref",
            "query_basis",
            "provenance_ref",
            "source_identity",
            "source_provenance",
            "payload",
            "load_summary",
        )
    }


def _admit_connector(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    stem: str,
    basis_extras: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    raw_dir = Path(settings.connector_raw_dir) / stem
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "water-quality.csv"
    raw_path.write_bytes(FIXTURE_BYTES)
    run = ConnectorRun(
        connector_run_id=f"{stem}-run",
        connector_key="sciencebase_public",
        source_system="sciencebase",
        source_mode="synthetic_local_direct_intake",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id=f"{stem}-target",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id="synthetic-sb-item-001",
        sciencebase_file_name="water-quality.csv",
        artifact_surface="synthetic_fixture",
        artifact_locator_type="intake_storage_ref",
        source_artifact_key=f"{stem}-source-artifact",
        downloaded_sha256=FIXTURE_SHA256,
        raw_storage_ref=str(raw_path),
        public_read_confirmed=True,
        status="downloaded",
    )
    db = client.layer3_session_factory()
    try:
        db.add_all([run, target])
        db.commit()
        recorded = record_connector_produced_source_intake(
            db,
            client_request_id=f"{stem}-intake",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="Synthetic connector CSV",
            source_description="Offline identities/provenance/counts fixture.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=recorded["connector_source_intake_record_id"],
        )
        candidate = preview["material_candidate"]
        assert candidate["load_summary"]["loaded_records"] == 1
        decision_basis = _decision_basis(candidate)
        for field, extras in (basis_extras or {}).items():
            current = decision_basis.get(field)
            assert isinstance(current, dict)
            decision_basis[field] = {**current, **extras}
        submitted_preview_hash = material_preview_hash(
            [
                material_candidate_basis_from_decision(
                    candidate_id=candidate["candidate_id"],
                    source_class=candidate["source_class"],
                    decision_basis=decision_basis,
                )
            ]
        )
        intake_record_id = recorded["connector_source_intake_record_id"]
        target_id = target.connector_run_target_id
        db.rollback()
    finally:
        db.close()

    gate_b_response = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": f"{stem}-gate-b",
            "preflight_id": f"{stem}-preflight",
            "source_set_id": f"{stem}-source-set",
            "material_preview_id": preview["material_preview_id"],
            "material_preview_hash": submitted_preview_hash,
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": decision_basis,
                }
            ],
        },
    )
    assert gate_b_response.status_code == 200, gate_b_response.text
    gate_b = gate_b_response.json()
    assert gate_b["next_state"] == "connector_source_intake_gate_b_admitted"
    assert gate_b["authority_rail"]["current_gate"] == "gate_b"
    verify_db = client.layer3_session_factory()
    try:
        receipt = (
            verify_db.query(L3ConnectorPromotionReceipt)
            .filter(L3ConnectorPromotionReceipt.gate_b_session_id == gate_b["session_id"])
            .one()
        )
        snapshot = verify_db.get(L3MaterialSnapshot, receipt.gate_b_material_snapshot_id)
        assert snapshot is not None
        assert snapshot.load_summary_json["loaded_records"] == 1
        receipt_id = receipt.connector_promotion_receipt_id
        manifest_id = receipt.gate_b_selection_manifest_id
        snapshot_id = receipt.gate_b_material_snapshot_id
    finally:
        verify_db.close()
    return {
        "gate_b": gate_b,
        "raw_path": raw_path,
        "intake_record_id": intake_record_id,
        "target_id": target_id,
        "receipt_id": receipt_id,
        "manifest_id": manifest_id,
        "snapshot_id": snapshot_id,
    }


def _downstream_census(db: Session) -> dict[str, int]:
    return {
        model.__name__: db.query(model).count()
        for model in (
            L3ReconciliationRecord,
            L3OutputPackage,
            L3TypingRecord,
            L3PassRun,
            AnalysisRun,
            AnalysisArtifact,
        )
    }


def _assert_zero_downstream(db: Session) -> None:
    assert _downstream_census(db) == {
        "L3ReconciliationRecord": 0,
        "L3OutputPackage": 0,
        "L3TypingRecord": 0,
        "L3PassRun": 0,
        "AnalysisRun": 0,
        "AnalysisArtifact": 0,
    }


def _leaf_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaf_values(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaf_values(item)]
    return [value]


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _all_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


def _package_file_set() -> set[str]:
    return {
        str(path)
        for path in (Path(settings.artifact_storage_dir) / "layer3").glob("l3_package_*.json")
    }


def test_flag_off_is_unavailable_and_preserves_gate_b_zero_downstream(client, monkeypatch):
    monkeypatch.delenv("LAYER3_CONNECTOR_DATASET_HANDOFF_ENABLED", raising=False)
    assert Settings(_env_file=None).layer3_connector_dataset_handoff_enabled is False
    _set_dataset_handoff_enabled(False)
    seeded = _admit_connector(client, monkeypatch, stem="b1b06-off")
    response = client.post(
        HANDOFF_ROUTE,
        json={"session_id": seeded["gate_b"]["session_id"], "client_request_id": "b1b06-off-handoff"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["error_code"] == "connector_dataset_handoff_unavailable"
    # Assert the OFF-path response's OWN next_state (not just the captured gate-b value below),
    # proving the unavailable envelope preserves the gate-b admission state.
    assert body["next_state"] == "connector_source_intake_gate_b_admitted"
    assert seeded["gate_b"]["next_state"] == "connector_source_intake_gate_b_admitted"
    assert seeded["gate_b"]["authority_rail"]["current_gate"] == "gate_b"
    with client.layer3_session_factory() as db:
        _assert_zero_downstream(db)


def test_flag_on_materializes_review_only_packages_without_value_projection(client, monkeypatch):
    _set_dataset_handoff_enabled(True)
    seeded = _admit_connector(
        client,
        monkeypatch,
        stem="b1b06-on",
        basis_extras={
            "source_identity": {
                "observations": [
                    {
                        "station_token": NESTED_VALUE_SENTINEL,
                        "magnitude": NESTED_NUMERIC_SENTINEL,
                    }
                ]
            },
            "source_provenance": {
                "unmodeled_samples": {
                    "token": NESTED_VALUE_SENTINEL,
                    "magnitude": NESTED_NUMERIC_SENTINEL,
                }
            },
            "load_summary": {
                "diagnostic_samples": [NESTED_VALUE_SENTINEL, NESTED_NUMERIC_SENTINEL]
            },
        },
    )
    with client.layer3_session_factory() as db:
        assert db.query(L3ConnectorPromotionReceipt).count() == 1
        snapshot = db.get(L3MaterialSnapshot, seeded["snapshot_id"])
        assert snapshot is not None
        assert NESTED_VALUE_SENTINEL in _leaf_values(snapshot.source_identity_json)
        assert NESTED_NUMERIC_SENTINEL in _leaf_values(snapshot.source_provenance_json)
        assert NESTED_VALUE_SENTINEL in _leaf_values(snapshot.load_summary_json)
    response = client.post(
        HANDOFF_ROUTE,
        json={"session_id": seeded["gate_b"]["session_id"], "client_request_id": "b1b06-on-handoff"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["next_state"] == "connector_dataset_handoff_ready"
    assert body["replayed"] is False
    assert body["handoff_enabled"] is False
    assert body["downstream_unavailable"] == EXPECTED_DOWNSTREAM_UNAVAILABLE
    assert body["negative_invariants"] == EXPECTED_NEGATIVE_INVARIANTS
    with client.layer3_session_factory() as db:
        reconciliation = db.query(L3ReconciliationRecord).one()
        packages = db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        record = db.get(L3ConnectorSourceIntakeRecord, seeded["intake_record_id"])
        target = db.get(ConnectorRunTarget, seeded["target_id"])
        receipt = db.get(L3ConnectorPromotionReceipt, seeded["receipt_id"])
        snapshot = db.get(L3MaterialSnapshot, seeded["snapshot_id"])
        manifest = db.get(L3SelectionManifest, seeded["manifest_id"])
        assert record is not None
        assert target is not None
        assert receipt is not None
        assert snapshot is not None
        assert manifest is not None
        assert reconciliation.status == "review_only"
        assert len(packages) == 3
        assert {package.package_kind for package in packages} == {
            "canonical_internal",
            "user_facing",
            "review_facing",
        }
        assert {package.status for package in packages} == {"package_review_only"}
        canonical = next(package for package in packages if package.package_kind == "canonical_internal")
        canonical_payload = json.loads(Path(canonical.payload_ref).read_text(encoding="utf-8"))
        source_summary = canonical_payload["connector_source_summary"]
        binding = canonical_payload["promotion_receipt_binding"]
        assert source_summary["content_sha256"] == receipt.content_sha256
        assert receipt.content_sha256 == record.content_sha256
        assert record.content_sha256 == target.downloaded_sha256 == FIXTURE_SHA256
        assert source_summary["content_size_bytes"] == len(FIXTURE_BYTES)
        assert record.content_size_bytes == len(FIXTURE_BYTES)
        assert source_summary["load_summary"]["loaded_records"] == 1
        assert source_summary["source_identity"]["connector_run_id"] == record.connector_run_id
        assert source_summary["source_identity"]["connector_run_target_id"] == record.connector_run_target_id
        assert source_summary["source_identity"]["connector_source_intake_record_id"] == record.connector_source_intake_record_id
        assert source_summary["source_provenance"]["connector_run_id"] == record.connector_run_id
        assert source_summary["source_provenance"]["connector_run_target_id"] == record.connector_run_target_id
        assert binding == {
            "connector_promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "canonical_identity_key_hash": receipt.canonical_identity_key_hash,
            "approval_hash": receipt.approval_hash,
            "promotion_basis_hash": receipt.promotion_basis_hash,
        }
        assert canonical_payload["analysis_plan_id"] is None
        assert canonical_payload["pass_run_ids"] == []
        assert canonical_payload["handoff_enabled"] is False
        assert canonical_payload["negative_invariants"] == EXPECTED_NEGATIVE_INVARIANTS
        assert canonical_payload["downstream_unavailable"] == EXPECTED_DOWNSTREAM_UNAVAILABLE
        assert {package.session_id for package in packages} == {seeded["gate_b"]["session_id"]}
        assert receipt.gate_b_session_id == seeded["gate_b"]["session_id"]
        assert snapshot.session_id == manifest.session_id == receipt.gate_b_session_id
        assert receipt.gate_b_selection_manifest_id == manifest.selection_manifest_id
        assert receipt.gate_b_material_snapshot_id == snapshot.material_snapshot_id
        assert receipt.connector_source_intake_record_id == record.connector_source_intake_record_id
        assert {package.reconciliation_record_id for package in packages} == {
            reconciliation.reconciliation_record_id
        }
        commit_summary = reconciliation.summary_json["workbench_package_commit"]
        assert commit_summary["client_request_id"] == "b1b06-on-handoff"
        assert commit_summary["package_review_submit_enabled"] is False
        assert commit_summary["handoff_enabled"] is False
        assert commit_summary["downstream_unavailable"] == EXPECTED_DOWNSTREAM_UNAVAILABLE_ACTIONS
        assert commit_summary["construction_basis_hash"] == body["construction_basis_hash"]
        for package in packages:
            payload_bytes = Path(package.payload_ref).read_bytes()
            assert hashlib.sha256(payload_bytes).hexdigest() == package.payload_hash
            payload = json.loads(payload_bytes)
            assert payload["package_header"]["package_kind"] == package.package_kind
            assert payload["package_header"]["package_status"] == "package_review_only"
            assert payload["analysis_plan_id"] is None
            assert payload["pass_run_ids"] == []
            assert payload["handoff_enabled"] is False
            assert payload["downstream_unavailable"] == EXPECTED_DOWNSTREAM_UNAVAILABLE
            assert payload["negative_invariants"] == EXPECTED_NEGATIVE_INVARIANTS
            leaves = _leaf_values(payload)
            assert "SB-001" not in leaves
            assert "SB-002" not in leaves
            assert 42 not in leaves
            assert 43 not in leaves
            assert NESTED_VALUE_SENTINEL not in leaves
            assert NESTED_NUMERIC_SENTINEL not in leaves
            assert FIXTURE_BYTES.decode("utf-8") not in json.dumps(payload)
            assert _all_keys(payload).isdisjoint(FORBIDDEN_VALUE_KEYS)
            assert _all_keys(payload).isdisjoint(
                {"observations", "unmodeled_samples", "diagnostic_samples"}
            )
        assert _downstream_census(db) == {
            "L3ReconciliationRecord": 1,
            "L3OutputPackage": 3,
            "L3TypingRecord": 0,
            "L3PassRun": 0,
            "AnalysisRun": 0,
            "AnalysisArtifact": 0,
        }
        package_projection = layer3_workbench.session_summary(
            db,
            seeded["gate_b"]["session_id"],
        )["package_construction"]
        assert package_projection["package_review_submit_enabled"] is False
        assert package_projection["handoff_enabled"] is False
        assert package_projection["downstream_unavailable"] == EXPECTED_DOWNSTREAM_UNAVAILABLE_ACTIONS


def test_exact_client_request_replays_without_new_rows(client, monkeypatch):
    _set_dataset_handoff_enabled(True)
    seeded = _admit_connector(client, monkeypatch, stem="b1b06-replay")
    payload = {"session_id": seeded["gate_b"]["session_id"], "client_request_id": "b1b06-replay-handoff"}
    first = client.post(HANDOFF_ROUTE, json=payload)
    first_files = _package_file_set()
    second = client.post(HANDOFF_ROUTE, json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["replayed"] is False
    assert second.json()["replayed"] is True
    assert second.json()["reconciliation_record_id"] == first.json()["reconciliation_record_id"]
    assert set(second.json()["output_package_ids"]) == set(first.json()["output_package_ids"])
    assert set(second.json()["payload_hashes"]) == set(first.json()["payload_hashes"])
    assert _package_file_set() == first_files
    with client.layer3_session_factory() as db:
        assert db.query(L3ReconciliationRecord).count() == 1
        assert db.query(L3OutputPackage).count() == 3


def test_non_connector_session_is_rejected_even_when_flag_on(client, monkeypatch):
    _set_dataset_handoff_enabled(True)
    seeded = _admit_connector(client, monkeypatch, stem="b1b06-reject")
    with client.layer3_session_factory() as db:
        manifest = db.get(L3SelectionManifest, seeded["manifest_id"])
        assert manifest is not None
        manifest.source_plane_hints_json = {
            **dict(manifest.source_plane_hints_json or {}),
            "source_classes": ["dataset_version"],
        }
        db.commit()
    response = client.post(
        HANDOFF_ROUTE,
        json={"session_id": seeded["gate_b"]["session_id"], "client_request_id": "b1b06-reject-handoff"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "connector_dataset_handoff_not_eligible"
    with client.layer3_session_factory() as db:
        _assert_zero_downstream(db)


def test_stored_byte_drift_fails_closed_without_persistence(client, monkeypatch):
    _set_dataset_handoff_enabled(True)
    seeded = _admit_connector(client, monkeypatch, stem="b1b06-drift")
    package_files_before = _package_file_set()
    seeded["raw_path"].write_bytes(FIXTURE_BYTES + b"\n")
    response = client.post(
        HANDOFF_ROUTE,
        json={"session_id": seeded["gate_b"]["session_id"], "client_request_id": "b1b06-drift-handoff"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "connector_promotion_not_eligible"
    assert _package_file_set() == package_files_before
    with client.layer3_session_factory() as db:
        assert db.query(L3ConnectorPromotionReceipt).count() == 1
        _assert_zero_downstream(db)
