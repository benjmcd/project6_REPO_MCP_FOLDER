from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
MIGRATION = BACKEND / "alembic" / "versions" / "0018_layer3_replacement_package_set_authority.py"

from app.db.session import Base
from app.models.models import (
    L3AnalysisPlan,
    L3AnalysisSet,
    L3CorrectedPackageArtifactSet,
    L3OutputPackage,
    L3PackageReplacementActivation,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementOutputPackage,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_replacement_package_set_authority as authority_service
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench import Layer3WorkbenchError


PACKAGE_KINDS = ["canonical_internal", "user_facing", "review_facing"]


def test_replacement_package_set_authority_migration_defines_durable_unique_authority(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_replacement_package_set_authority_migration", MIGRATION)
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

    elements = next(items for name, items in created_tables if name == "l3_replacement_package_set_authority")
    unique_names = {element.name for element in elements if isinstance(element, UniqueConstraint)}
    assert "uq_l3_replacement_package_set_client_request" in unique_names
    assert "uq_l3_replacement_package_set_basis_hash" in unique_names
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    constraint = next(element for element in constraints if element.name == "ck_l3_replacement_package_set_operator_decision")
    assert "record_replacement_package_set_authority" in str(constraint.sqltext)
    assert (
        "ix_l3_replacement_package_set_session",
        "l3_replacement_package_set_authority",
        ["session_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_replacement_package_set_reconciliation",
        "l3_replacement_package_set_authority",
        ["reconciliation_record_id"],
        {},
    ) in created_indexes


def _seed_authority_source(db) -> None:
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
            summary_json={},
        )
    )
    db.add(L3ReconciliationRecord(reconciliation_record_id="recon-1", session_id="session-1", status="constructed"))
    for package_kind in PACKAGE_KINDS:
        db.add(
            L3OutputPackage(
                output_package_id=f"source-{package_kind}",
                session_id="session-1",
                reconciliation_record_id="recon-1",
                package_kind=package_kind,
                status="ready",
                payload_ref=f"/authority/source/{package_kind}.json",
                payload_hash=hashlib.sha256(f"source:{package_kind}".encode("utf-8")).hexdigest(),
                summary_json={},
            )
        )
    db.commit()


def _authority_payload(request_id: str = "req-replacement-authority") -> dict:
    source_rows = [
        {
            "output_package_id": f"source-{package_kind}",
            "package_kind": package_kind,
            "status": "ready",
            "payload_ref": f"/authority/source/{package_kind}.json",
            "payload_hash": hashlib.sha256(f"source:{package_kind}".encode("utf-8")).hexdigest(),
        }
        for package_kind in PACKAGE_KINDS
    ]
    source_package_set_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": "session-1",
            "reconciliation_record_id": "recon-1",
            "output_packages": source_rows,
        }
    )
    replacement_payload_refs = [f"/authority/replacement/{package_kind}.json" for package_kind in PACKAGE_KINDS]
    replacement_payload_hashes = [
        hashlib.sha256(f"replacement:{package_kind}".encode("utf-8")).hexdigest() for package_kind in PACKAGE_KINDS
    ]
    replacement_package_set_hash = authority_service.replacement_package_set_hash(
        replacement_package_set_id="replacement-set-1",
        replacement_package_kinds=PACKAGE_KINDS,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    authority_basis_hash = authority_service.replacement_package_set_authority_basis_hash(
        session_id="session-1",
        analysis_plan_id="plan-1",
        pass_run_id="pass-1",
        reconciliation_record_id="recon-1",
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=[row["output_package_id"] for row in source_rows],
        source_package_kinds=PACKAGE_KINDS,
        source_payload_refs=[row["payload_ref"] for row in source_rows],
        source_payload_hashes=[row["payload_hash"] for row in source_rows],
        replacement_package_set_id="replacement-set-1",
        replacement_package_set_hash=replacement_package_set_hash,
        replacement_package_kinds=PACKAGE_KINDS,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "reconciliation_record_id": "recon-1",
        "source_package_set_hash": source_package_set_hash,
        "source_output_package_ids": [row["output_package_id"] for row in source_rows],
        "source_package_kinds": PACKAGE_KINDS,
        "source_payload_refs": [row["payload_ref"] for row in source_rows],
        "source_payload_hashes": [row["payload_hash"] for row in source_rows],
        "replacement_package_set_id": "replacement-set-1",
        "replacement_package_set_hash": replacement_package_set_hash,
        "replacement_package_kinds": PACKAGE_KINDS,
        "replacement_payload_refs": replacement_payload_refs,
        "replacement_payload_hashes": replacement_payload_hashes,
        "authority_basis_hash": authority_basis_hash,
        "operator_decision": "record_replacement_package_set_authority",
    }


def _seed_corrected_artifact_set_authority(db, tmp_path: Path) -> dict:
    _seed_authority_source(db)
    source_rows = [
        {
            "output_package_id": f"source-{package_kind}",
            "package_kind": package_kind,
            "status": "ready",
            "payload_ref": f"/authority/source/{package_kind}.json",
            "payload_hash": hashlib.sha256(f"source:{package_kind}".encode("utf-8")).hexdigest(),
        }
        for package_kind in PACKAGE_KINDS
    ]
    source_package_set_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": "session-1",
            "reconciliation_record_id": "recon-1",
            "output_packages": source_rows,
        }
    )
    corrected_refs = []
    corrected_hashes = []
    corrected_sizes = []
    for package_kind in PACKAGE_KINDS:
        artifact_path = tmp_path / f"corrected-{package_kind}.json"
        payload = f"corrected:{package_kind}".encode("utf-8")
        artifact_path.write_bytes(payload)
        corrected_refs.append(str(artifact_path))
        corrected_hashes.append(hashlib.sha256(payload).hexdigest())
        corrected_sizes.append(len(payload))
    corrected_package_set_id = "corrset-1"
    corrected_package_set_hash = stable_hash(
        {
            "schema_id": "layer3.corrected_package_artifact_set_identity.v1",
            "corrected_package_set_id": corrected_package_set_id,
            "corrected_artifacts": [
                {
                    "package_kind": package_kind,
                    "artifact_ref": artifact_ref,
                    "artifact_hash": artifact_hash,
                    "artifact_byte_size": artifact_byte_size,
                }
                for package_kind, artifact_ref, artifact_hash, artifact_byte_size in zip(
                    PACKAGE_KINDS,
                    corrected_refs,
                    corrected_hashes,
                    corrected_sizes,
                )
            ],
        }
    )
    artifact_manifest_hash = stable_hash(
        {
            "schema_id": "layer3.corrected_package_artifact_manifest.v1",
            "corrected_package_set_id": corrected_package_set_id,
            "corrected_package_set_hash": corrected_package_set_hash,
            "corrected_artifact_hashes": corrected_hashes,
        }
    )
    corrected_basis_hash = stable_hash(
        {
            "schema_id": "test.corrected_artifact_basis.v1",
            "source_package_set_hash": source_package_set_hash,
            "corrected_package_set_hash": corrected_package_set_hash,
            "artifact_manifest_hash": artifact_manifest_hash,
        }
    )
    db.add(
        L3CorrectedPackageArtifactSet(
            corrected_package_artifact_set_id="corrected-set-1",
            client_request_id="req-corrected-set",
            session_id="session-1",
            analysis_plan_id="plan-1",
            pass_run_id="pass-1",
            reconciliation_record_id="recon-1",
            replacement_artifact_materialization_id="materialization-1",
            materialization_basis_hash="materialization-basis-1",
            source_package_set_hash=source_package_set_hash,
            source_output_package_ids_json=[row["output_package_id"] for row in source_rows],
            source_package_kinds_json=PACKAGE_KINDS,
            source_payload_refs_json=[row["payload_ref"] for row in source_rows],
            source_payload_hashes_json=[row["payload_hash"] for row in source_rows],
            result_review_record_ref="result-review-ref-1",
            reviewed_output_items_hash="reviewed-items-hash-1",
            package_review_preview_hash="package-review-preview-hash-1",
            corrected_package_set_id=corrected_package_set_id,
            corrected_package_set_hash=corrected_package_set_hash,
            corrected_package_kinds_json=PACKAGE_KINDS,
            corrected_artifact_refs_json=corrected_refs,
            corrected_artifact_hashes_json=corrected_hashes,
            corrected_artifact_byte_sizes_json=corrected_sizes,
            artifact_namespace="corrected-package-artifacts",
            artifact_manifest_hash=artifact_manifest_hash,
            corrected_artifact_basis_hash=corrected_basis_hash,
            audit_history_json=[],
            authority_snapshot_json={},
            operator_decision="record_corrected_package_artifact_set_from_review_corrections",
            status="recorded",
        )
    )
    db.commit()
    return {
        "source_package_set_hash": source_package_set_hash,
        "corrected_artifact_basis_hash": corrected_basis_hash,
        "raw_corrected_refs": corrected_refs,
    }


def _from_corrected_payload(seed: dict, request_id: str = "req-from-corrected") -> dict:
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "reconciliation_record_id": "recon-1",
        "source_package_set_hash": seed["source_package_set_hash"],
        "corrected_package_artifact_set_id": "corrected-set-1",
        "corrected_artifact_basis_hash": seed["corrected_artifact_basis_hash"],
        "operator_decision": "record_replacement_package_set_authority",
    }


def test_replacement_package_set_authority_concurrent_duplicate_request_records_one_authority(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'replacement-authority.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    setup_db = SessionLocal()
    try:
        _seed_authority_source(setup_db)
        payload = _authority_payload()
    finally:
        setup_db.close()

    def submit_authority(_actor: str) -> tuple[str, str]:
        db = SessionLocal()
        try:
            response = authority_service.record_replacement_package_set_authority(db, payload)
            return ("returned", response["status"])
        except Layer3WorkbenchError as exc:
            return ("rejected", exc.error_code)
        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit_authority, ("pytest-1", "pytest-2")))
        assert sum(kind == "returned" and status == "recorded" for kind, status in results) == 1
        assert all(
            (kind == "returned" and status in {"recorded", "already_recorded"})
            or (kind == "rejected" and status == "replacement_package_set_authority_in_progress")
            for kind, status in results
        )
        db = SessionLocal()
        try:
            assert db.query(L3ReplacementPackageSetAuthority).count() == 1
            assert db.query(L3OutputPackage).count() == 3
            authority = db.query(L3ReplacementPackageSetAuthority).one()
            assert authority.client_request_id == "req-replacement-authority"
            assert authority.authority_basis_hash == payload["authority_basis_hash"]
        finally:
            db.close()
    finally:
        engine.dispose()


def test_replacement_package_set_authority_records_same_basis_replay_request_ids(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'replacement-authority-replay.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        _seed_authority_source(db)
        first = authority_service.record_replacement_package_set_authority(db, _authority_payload())
        replay = authority_service.record_replacement_package_set_authority(
            db,
            _authority_payload(request_id="req-replacement-authority-same-basis-replay"),
        )
        assert replay["status"] == "already_recorded"
        assert replay["replacement_package_set_authority_id"] == first["replacement_package_set_authority_id"]

        authority = db.query(L3ReplacementPackageSetAuthority).one()
        assert authority.client_request_id == "req-replacement-authority"
        assert authority.authority_snapshot_json["same_basis_replay_client_request_ids"] == [
            "req-replacement-authority-same-basis-replay"
        ]
        assert authority.authority_snapshot_json["same_basis_replay_client_request_count"] == 1
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_set_authority_from_corrected_artifact_set_records_redacted_authority(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'from-corrected.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        seed = _seed_corrected_artifact_set_authority(db, tmp_path)
        source_packages_before = [
            (package.output_package_id, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.output_package_id).all()
        ]
        payload = _from_corrected_payload(seed)

        response = authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(db, payload)

        assert response["schema_id"] == "layer3.replacement_package_set_authority.v1"
        assert response["status"] == "recorded"
        assert response["replacement_package_set_authority_mode"] == (
            "replacement_package_set_authority_from_corrected_artifact_set"
        )
        assert response["operator_decision"] == "record_replacement_package_set_authority"
        assert response["authority_rail"]["response_payload_refs_redacted"] is True
        assert all(ref.startswith("artifact://replacement-package-set/") for ref in response["replacement_payload_refs"])
        assert all(ref.startswith("artifact://source-output-package/") for ref in response["source_payload_refs"])
        assert not any(raw_ref in str(response) for raw_ref in seed["raw_corrected_refs"])
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(L3ReplacementPackageArtifactManifest).count() == 0
        assert db.query(L3ReplacementOutputPackage).count() == 0
        assert db.query(L3PackageReplacementActivation).count() == 0
        source_packages_after = [
            (package.output_package_id, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.output_package_id).all()
        ]
        assert source_packages_after == source_packages_before

        replay = authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(db, payload)
        assert replay["status"] == "already_recorded"
        assert replay["replacement_package_set_authority_id"] == response["replacement_package_set_authority_id"]
        same_basis = authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(
            db,
            {**payload, "client_request_id": "req-from-corrected-same-basis"},
        )
        assert same_basis["status"] == "already_recorded"
        assert same_basis["replacement_package_set_authority_id"] == response["replacement_package_set_authority_id"]
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_set_authority_from_corrected_artifact_set_prechecks_fail_closed(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'from-corrected-prechecks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        seed = _seed_corrected_artifact_set_authority(db, tmp_path)
        payload = _from_corrected_payload(seed)
        cases = [
            (
                {**payload, "replacement_payload_refs": [str(tmp_path / "forbidden.json")]},
                "replacement_package_set_authority_from_corrected_artifact_set_scope_not_admitted",
            ),
            (
                {**payload, "destination_url": "file:///tmp/out"},
                "replacement_package_set_authority_from_corrected_artifact_set_scope_not_admitted",
            ),
            (
                {**payload, "operator_decision": "record_replacement_package_set_authority_from_corrected_artifact_set"},
                "unsupported_replacement_package_set_authority_from_corrected_artifact_set_decision",
            ),
            (
                {**payload, "corrected_artifact_basis_hash": "stale-corrected-basis"},
                "replacement_package_set_authority_corrected_artifact_basis_hash_mismatch",
            ),
            (
                {**payload, "session_id": "wrong-session"},
                "replacement_package_set_authority_corrected_artifact_set_session_id_mismatch",
            ),
            (
                {**payload, "source_package_set_hash": "stale-source-package-set"},
                "replacement_package_set_authority_corrected_artifact_set_source_package_set_hash_mismatch",
            ),
            (
                {**payload, "corrected_package_artifact_set_id": "missing-corrected-set"},
                "replacement_package_set_authority_corrected_artifact_set_not_found",
            ),
        ]
        for bad_payload, expected_error in cases:
            try:
                authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(db, bad_payload)
            except Layer3WorkbenchError as exc:
                assert exc.error_code == expected_error
            else:
                raise AssertionError(f"expected {expected_error}")

        response = authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(db, payload)
        original_corrected = db.query(L3CorrectedPackageArtifactSet).filter_by(
            corrected_package_artifact_set_id="corrected-set-1"
        ).one()
        second_corrected_basis = stable_hash(
            {
                "schema_id": "test.second_corrected_artifact_basis.v1",
                "source_package_set_hash": seed["source_package_set_hash"],
                "corrected_package_set_id": "corrset-2",
            }
        )
        db.add(
            L3CorrectedPackageArtifactSet(
                corrected_package_artifact_set_id="corrected-set-2",
                client_request_id="req-corrected-set-2",
                session_id=original_corrected.session_id,
                analysis_plan_id=original_corrected.analysis_plan_id,
                pass_run_id=original_corrected.pass_run_id,
                reconciliation_record_id=original_corrected.reconciliation_record_id,
                replacement_artifact_materialization_id=original_corrected.replacement_artifact_materialization_id,
                materialization_basis_hash=original_corrected.materialization_basis_hash,
                source_package_set_hash=original_corrected.source_package_set_hash,
                source_output_package_ids_json=list(original_corrected.source_output_package_ids_json),
                source_package_kinds_json=list(original_corrected.source_package_kinds_json),
                source_payload_refs_json=list(original_corrected.source_payload_refs_json),
                source_payload_hashes_json=list(original_corrected.source_payload_hashes_json),
                result_review_record_ref=original_corrected.result_review_record_ref,
                reviewed_output_items_hash=original_corrected.reviewed_output_items_hash,
                package_review_preview_hash=original_corrected.package_review_preview_hash,
                corrected_package_set_id="corrset-2",
                corrected_package_set_hash=stable_hash({"corrected_package_set_id": "corrset-2"}),
                corrected_package_kinds_json=list(original_corrected.corrected_package_kinds_json),
                corrected_artifact_refs_json=list(original_corrected.corrected_artifact_refs_json),
                corrected_artifact_hashes_json=list(original_corrected.corrected_artifact_hashes_json),
                corrected_artifact_byte_sizes_json=list(original_corrected.corrected_artifact_byte_sizes_json),
                artifact_namespace=original_corrected.artifact_namespace,
                artifact_manifest_hash=stable_hash({"artifact_manifest": "corrset-2"}),
                corrected_artifact_basis_hash=second_corrected_basis,
                audit_history_json=[],
                authority_snapshot_json={},
                operator_decision="record_corrected_package_artifact_set_from_review_corrections",
                status="recorded",
            )
        )
        db.commit()
        try:
            authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(
                db,
                {
                    **payload,
                    "corrected_package_artifact_set_id": "corrected-set-2",
                    "corrected_artifact_basis_hash": second_corrected_basis,
                },
            )
        except Layer3WorkbenchError as exc:
            assert exc.error_code == (
                "replacement_package_set_authority_from_corrected_artifact_set_client_request_conflict"
            )
        else:
            raise AssertionError("expected same-key different-basis conflict")
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
        assert response["status"] == "recorded"
    finally:
        db.close()
        engine.dispose()
