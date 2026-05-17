from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "alembic" / "versions"))
MIGRATION = BACKEND / "alembic" / "versions" / "0033_layer3_corrected_package_artifact_set.py"

from app.db.session import Base
from app.models.models import (
    L3AnalysisPlan,
    L3AnalysisSet,
    L3CorrectedPackageArtifactSet,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageArtifactMaterialization,
    L3Session,
)
from app.services import layer3_corrected_package_artifact_set as corrected_service
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench import Layer3WorkbenchError


PACKAGE_KINDS = ["canonical_internal", "user_facing", "review_facing"]
PACKAGE_REVIEW_PREVIEW_HASH = "package-review-preview-hash-1"


def test_corrected_package_artifact_set_migration_defines_durable_authority(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_corrected_package_artifact_set_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    created_tables = []
    created_indexes = []

    def capture_create_table(name, *elements):
        created_tables.append((name, elements))

    def capture_create_index(name, table, columns, **kwargs):
        created_indexes.append((name, table, columns, kwargs))

    monkeypatch.setattr(module, "create_table_idempotent", capture_create_table)
    monkeypatch.setattr(module, "create_index_idempotent", capture_create_index)
    module.upgrade()

    elements = next(items for name, items in created_tables if name == "l3_corrected_package_artifact_set")
    unique_names = {element.name for element in elements if isinstance(element, UniqueConstraint)}
    assert "uq_l3_corrected_artifact_set_client_request" in unique_names
    assert "uq_l3_corrected_artifact_set_basis_hash" in unique_names
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    operator_constraint = next(
        element for element in constraints if element.name == "ck_l3_corrected_artifact_set_operator_decision"
    )
    status_constraint = next(element for element in constraints if element.name == "ck_l3_corrected_artifact_set_status")
    assert "record_corrected_package_artifact_set_from_review_corrections" in str(operator_constraint.sqltext)
    assert "recorded" in str(status_constraint.sqltext)
    assert (
        "ix_l3_corrected_artifact_set_materialization",
        "l3_corrected_package_artifact_set",
        ["replacement_artifact_materialization_id"],
        {},
    ) in created_indexes


def _hash_payload(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _source_rows(tmp_path: Path) -> list[dict]:
    payload_dir = tmp_path / "source-payloads"
    payload_dir.mkdir(exist_ok=True)
    rows = []
    for package_kind in PACKAGE_KINDS:
        payload = {"package_kind": package_kind, "source": True}
        payload_ref = payload_dir / f"{package_kind}.json"
        payload_ref.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        rows.append(
            {
                "output_package_id": f"source-{package_kind}",
                "package_kind": package_kind,
                "status": "ready",
                "payload_ref": str(payload_ref),
                "payload_hash": _hash_payload(payload),
            }
        )
    return rows


def _source_package_set_hash(rows: list[dict]) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": "session-1",
            "reconciliation_record_id": "recon-1",
            "output_packages": rows,
        }
    )


def _reviewed_items() -> list[dict]:
    return [
        {
            "index": 0,
            "item_ref": "finding-1",
            "item_type": "finding",
            "trace_status": "resolved",
            "missing_trace_fields": [],
        }
    ]


def _reviewed_items_hash() -> str:
    return stable_hash(
        {
            "schema_id": "layer3.corrected_package_artifact_set_reviewed_items.v1",
            "reviewed_output_items": _reviewed_items(),
        }
    )


def _artifact_candidates(tmp_path: Path) -> tuple[list[str], list[str]]:
    artifact_dir = tmp_path / "replacement-package-artifacts"
    artifact_dir.mkdir(exist_ok=True)
    refs = []
    hashes = []
    for package_kind in PACKAGE_KINDS:
        payload = {"package_kind": package_kind, "corrected": True}
        artifact_ref = artifact_dir / f"{package_kind}.json"
        artifact_ref.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        refs.append(str(artifact_ref))
        hashes.append(_hash_payload(payload))
    return refs, hashes


def _seed_authority(db, tmp_path: Path) -> dict:
    source_rows = _source_rows(tmp_path)
    source_package_set_hash = _source_package_set_hash(source_rows)
    reviewed_items = _reviewed_items()
    db.add(L3Session(session_id="session-1", selection_manifest_id="manifest-1"))
    db.add(
        L3AnalysisSet(
            analysis_set_id="set-1",
            session_id="session-1",
            analysis_group_ids_json=[],
            analysis_unit_ids_json=[],
            set_type="quant",
            formation_basis_json={},
        )
    )
    db.add(
        L3AnalysisPlan(
            analysis_plan_id="plan-1",
            session_id="session-1",
            analysis_set_ids_json=["set-1"],
            status="approved",
            approved_by_operator=True,
            plan_json={},
        )
    )
    db.add(
        L3PassRun(
            pass_run_id="pass-1",
            session_id="session-1",
            analysis_plan_id="plan-1",
            analysis_set_id="set-1",
            pass_type="quantitative",
            engine_family="deterministic",
            status="completed",
            input_payload_ref="input.json",
            output_payload_ref="output.json",
            summary_json={
                "execution_result_review": {
                    "schema_id": "layer3.execution_result_review_state.v1",
                    "review_state": "execution_result_review_approved",
                    "operator_decision": "approved",
                    "review_record_ref": "result-review-ref-1",
                    "reviewed_output_items": reviewed_items,
                }
            },
        )
    )
    db.add(
        L3ReconciliationRecord(
            reconciliation_record_id="recon-1",
            session_id="session-1",
            status="constructed",
            summary_json={
                "workbench_package_commit": {
                    "package_review_preview_hash": PACKAGE_REVIEW_PREVIEW_HASH,
                }
            },
        )
    )
    for row in source_rows:
        db.add(
            L3OutputPackage(
                output_package_id=row["output_package_id"],
                session_id="session-1",
                reconciliation_record_id="recon-1",
                package_kind=row["package_kind"],
                status=row["status"],
                payload_ref=row["payload_ref"],
                payload_hash=row["payload_hash"],
                summary_json={},
            )
        )
    artifact_refs, artifact_hashes = _artifact_candidates(tmp_path)
    materialization_basis_hash = stable_hash(
        {
            "schema_id": "test.materialization_basis.v1",
            "source_package_set_hash": source_package_set_hash,
            "artifact_refs": artifact_refs,
            "artifact_hashes": artifact_hashes,
        }
    )
    db.add(
        L3ReplacementPackageArtifactMaterialization(
            replacement_artifact_materialization_id="materialization-1",
            client_request_id="req-materialization",
            session_id="session-1",
            analysis_plan_id="plan-1",
            pass_run_id="pass-1",
            reconciliation_record_id="recon-1",
            package_supersession_preview_hash=PACKAGE_REVIEW_PREVIEW_HASH,
            source_package_set_hash=source_package_set_hash,
            source_output_package_ids_json=[row["output_package_id"] for row in source_rows],
            source_package_kinds_json=[row["package_kind"] for row in source_rows],
            source_payload_refs_json=[row["payload_ref"] for row in source_rows],
            source_payload_hashes_json=[row["payload_hash"] for row in source_rows],
            replacement_package_set_id="replacement-set-1",
            replacement_package_set_hash=stable_hash({"replacement": artifact_hashes}),
            replacement_package_kinds_json=PACKAGE_KINDS,
            replacement_payload_refs_json=artifact_refs,
            replacement_payload_hashes_json=artifact_hashes,
            authority_basis_hash=stable_hash({"authority": "materialization-1"}),
            materialization_basis_hash=materialization_basis_hash,
            materialization_snapshot_json={},
            operator_decision="materialize_replacement_package_artifacts_from_supersession_preview",
            status="materialized",
        )
    )
    db.commit()
    return {
        "source_package_set_hash": source_package_set_hash,
        "source_output_package_ids": [row["output_package_id"] for row in source_rows],
        "source_package_kinds": [row["package_kind"] for row in source_rows],
        "source_payload_refs": [row["payload_ref"] for row in source_rows],
        "source_payload_hashes": [row["payload_hash"] for row in source_rows],
        "materialization_basis_hash": materialization_basis_hash,
        "artifact_refs": artifact_refs,
    }


def _record_payload(seed: dict, request_id: str = "req-corrected-set") -> dict:
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "reconciliation_record_id": "recon-1",
        "source_package_set_hash": seed["source_package_set_hash"],
        "source_output_package_ids": seed["source_output_package_ids"],
        "source_package_kinds": seed["source_package_kinds"],
        "source_payload_refs": seed["source_payload_refs"],
        "source_payload_hashes": seed["source_payload_hashes"],
        "result_review_record_ref": "result-review-ref-1",
        "reviewed_output_items_hash": _reviewed_items_hash(),
        "package_review_preview_hash": PACKAGE_REVIEW_PREVIEW_HASH,
        "replacement_artifact_materialization_id": "materialization-1",
        "materialization_basis_hash": seed["materialization_basis_hash"],
        "operator_decision": "record_corrected_package_artifact_set_from_review_corrections",
    }


def test_corrected_package_artifact_set_records_redacted_authority_and_idempotency(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'corrected-set.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        seed = _seed_authority(db, tmp_path)
        source_packages_before = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        payload = _record_payload(seed)

        response = corrected_service.record_corrected_package_artifact_set(db, payload)

        assert response["schema_id"] == "layer3.corrected_package_artifact_set.v1"
        assert response["status"] == "recorded"
        assert response["artifact_refs_redacted"] is True
        assert all(ref.startswith("artifact://corrected-package-artifacts/") for ref in response["corrected_artifact_refs"])
        assert not any(ref in seed["artifact_refs"] for ref in response["corrected_artifact_refs"])
        assert "source_payload_refs" not in response
        assert response["package_rebuild_enabled"] is False
        assert response["source_l3_output_package_mutation_enabled"] is False
        assert response["connector_dispatch_enabled"] is False
        assert response["provider_public_url_enabled"] is False
        assert db.query(L3CorrectedPackageArtifactSet).count() == 1
        assert db.query(L3OutputPackage).count() == 3
        source_packages_after = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        assert source_packages_after == source_packages_before

        replay = corrected_service.record_corrected_package_artifact_set(db, payload)
        assert replay["status"] == "already_recorded"
        assert replay["corrected_package_artifact_set_id"] == response["corrected_package_artifact_set_id"]
        same_basis = corrected_service.record_corrected_package_artifact_set(
            db,
            {**payload, "client_request_id": "req-corrected-set-same-basis"},
        )
        assert same_basis["status"] == "already_recorded"
        assert same_basis["corrected_package_artifact_set_id"] == response["corrected_package_artifact_set_id"]
    finally:
        db.close()
        engine.dispose()


def test_corrected_package_artifact_set_prechecks_fail_closed(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'corrected-set-prechecks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        seed = _seed_authority(db, tmp_path)
        payload = _record_payload(seed)
        cases = [
            ({**payload, "rebuild_package": True}, "corrected_package_artifact_set_scope_not_admitted"),
            (
                {**payload, "operator_decision": "record_replacement_package_set_authority"},
                "unsupported_corrected_package_artifact_set_decision",
            ),
            (
                {**payload, "source_package_set_hash": "stale-source-hash"},
                "corrected_package_artifact_set_source_package_set_hash_mismatch",
            ),
            (
                {**payload, "reviewed_output_items_hash": "stale-review-items"},
                "corrected_package_artifact_set_reviewed_output_items_hash_mismatch",
            ),
            (
                {**payload, "package_review_preview_hash": "stale-package-preview"},
                "corrected_package_artifact_set_package_review_preview_hash_mismatch",
            ),
            (
                {**payload, "package_supersession_preview_hash": "stale-supersession-preview"},
                "corrected_package_artifact_set_materialization_package_supersession_preview_hash_mismatch",
            ),
            (
                {**payload, "source_payload_refs": list(reversed(payload["source_payload_refs"]))},
                "corrected_package_artifact_set_source_payload_refs_mismatch",
            ),
            (
                {**payload, "replacement_artifact_manifest_id": "manifest-1"},
                "corrected_package_artifact_set_scope_not_admitted",
            ),
            (
                {key: value for key, value in payload.items() if key != "replacement_artifact_materialization_id"},
                "corrected_package_artifact_set_requires_materialization",
            ),
        ]
        for bad_payload, expected_error in cases:
            try:
                corrected_service.record_corrected_package_artifact_set(db, bad_payload)
            except Layer3WorkbenchError as exc:
                assert exc.error_code == expected_error
            else:
                raise AssertionError(f"expected {expected_error}")

        Path(seed["artifact_refs"][0]).write_text("tampered", encoding="utf-8")
        try:
            corrected_service.record_corrected_package_artifact_set(
                db,
                {**payload, "client_request_id": "req-corrected-set-tampered"},
            )
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "corrected_package_artifact_set_artifact_hash_mismatch"
        else:
            raise AssertionError("expected artifact hash mismatch")
    finally:
        db.close()
        engine.dispose()
