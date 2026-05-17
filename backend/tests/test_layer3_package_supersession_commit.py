from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "alembic" / "versions"))
MIGRATION = BACKEND / "alembic" / "versions" / "0019_layer3_package_supersession_commit.py"

from app.db.session import Base
from app.models.models import (
    L3AnalysisPlan,
    L3AnalysisSet,
    L3CorrectedPackageArtifactSet,
    L3OutputPackage,
    L3PackageReplacementActivation,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementOutputPackage,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_package_supersession_commit as commit_service
from app.services import layer3_replacement_package_set_authority as authority_service
from app.services.layer3_package_mutation_entry import PACKAGE_SUPERSESSION_PREVIEW_MODE
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench import Layer3WorkbenchError


PACKAGE_KINDS = ["canonical_internal", "user_facing", "review_facing"]
PACKAGE_REVIEW_PREVIEW_HASH = "package-review-preview-hash-1"


def test_package_supersession_commit_migration_defines_durable_lineage_constraints(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_package_supersession_commit_migration", MIGRATION)
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

    elements = next(items for name, items in created_tables if name == "l3_package_supersession_commit")
    unique_names = {element.name for element in elements if isinstance(element, UniqueConstraint)}
    assert "uq_l3_package_supersession_commit_client_request" in unique_names
    assert "uq_l3_package_supersession_commit_basis_hash" in unique_names
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    operator_constraint = next(
        element for element in constraints if element.name == "ck_l3_package_supersession_commit_operator_decision"
    )
    status_constraint = next(
        element for element in constraints if element.name == "ck_l3_package_supersession_commit_status"
    )
    assert "commit_package_supersession" in str(operator_constraint.sqltext)
    assert "committed" in str(status_constraint.sqltext)
    assert (
        "ix_l3_package_supersession_commit_session",
        "l3_package_supersession_commit",
        ["session_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_package_supersession_commit_reconciliation",
        "l3_package_supersession_commit",
        ["reconciliation_record_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_package_supersession_commit_replacement_authority",
        "l3_package_supersession_commit",
        ["replacement_package_set_authority_id"],
        {},
    ) in created_indexes


def _hash_payload(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _source_package_rows(tmp_path: Path) -> list[dict]:
    rows = []
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir(exist_ok=True)
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


def _source_package_set_hash(source_rows: list[dict]) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": "session-1",
            "reconciliation_record_id": "recon-1",
            "output_packages": source_rows,
        }
    )


def _seed_commit_source(db, tmp_path: Path) -> dict:
    source_rows = _source_package_rows(tmp_path)
    source_package_set_hash = _source_package_set_hash(source_rows)
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
    db.add(
        L3ReconciliationRecord(
            reconciliation_record_id="recon-1",
            session_id="session-1",
            status="constructed",
            summary_json={
                "workbench_package_commit": {
                    "package_review_preview_hash": PACKAGE_REVIEW_PREVIEW_HASH,
                    "package_review_submit_enabled": False,
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
    db.commit()
    return {
        "source_rows": source_rows,
        "source_package_set_hash": source_package_set_hash,
        "source_output_package_ids": [row["output_package_id"] for row in source_rows],
        "source_package_kinds": [row["package_kind"] for row in source_rows],
        "source_payload_refs": [row["payload_ref"] for row in source_rows],
        "source_payload_hashes": [row["payload_hash"] for row in source_rows],
    }


def _authority_payload(source: dict, request_id: str = "req-replacement-authority") -> dict:
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
        source_package_set_hash=source["source_package_set_hash"],
        source_output_package_ids=source["source_output_package_ids"],
        source_package_kinds=source["source_package_kinds"],
        source_payload_refs=source["source_payload_refs"],
        source_payload_hashes=source["source_payload_hashes"],
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
        "source_package_set_hash": source["source_package_set_hash"],
        "source_output_package_ids": source["source_output_package_ids"],
        "source_package_kinds": source["source_package_kinds"],
        "source_payload_refs": source["source_payload_refs"],
        "source_payload_hashes": source["source_payload_hashes"],
        "replacement_package_set_id": "replacement-set-1",
        "replacement_package_set_hash": replacement_package_set_hash,
        "replacement_package_kinds": PACKAGE_KINDS,
        "replacement_payload_refs": replacement_payload_refs,
        "replacement_payload_hashes": replacement_payload_hashes,
        "authority_basis_hash": authority_basis_hash,
        "operator_decision": "record_replacement_package_set_authority",
    }


def _commit_payload(source: dict, authority: dict, request_id: str = "req-supersession-commit") -> dict:
    downstream_dependencies: list[dict] = []
    downstream_dependency_hash = commit_service.package_supersession_downstream_dependency_hash(
        downstream_dependencies
    )
    package_supersession_preview_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_preview_basis.v1",
            "mode": PACKAGE_SUPERSESSION_PREVIEW_MODE,
            "session_id": "session-1",
            "analysis_plan_id": "plan-1",
            "pass_run_id": "pass-1",
            "reconciliation_record_id": "recon-1",
            "package_review_preview_hash": PACKAGE_REVIEW_PREVIEW_HASH,
            "package_set_hash": source["source_package_set_hash"],
            "downstream_dependencies": downstream_dependencies,
        }
    )
    commit_basis_hash = commit_service.package_supersession_commit_basis_hash(
        session_id="session-1",
        analysis_plan_id="plan-1",
        pass_run_id="pass-1",
        reconciliation_record_id="recon-1",
        package_supersession_preview_hash=package_supersession_preview_hash,
        source_package_set_hash=source["source_package_set_hash"],
        source_output_package_ids=source["source_output_package_ids"],
        source_package_kinds=source["source_package_kinds"],
        source_payload_refs=source["source_payload_refs"],
        source_payload_hashes=source["source_payload_hashes"],
        replacement_package_set_authority_id=authority["replacement_package_set_authority_id"],
        replacement_authority_basis_hash=authority["authority_basis_hash"],
        replacement_package_set_id=authority["replacement_package_set_id"],
        replacement_package_set_hash=authority["replacement_package_set_hash"],
        replacement_package_kinds=authority["replacement_package_kinds"],
        replacement_payload_refs=authority["replacement_payload_refs"],
        replacement_payload_hashes=authority["replacement_payload_hashes"],
        downstream_dependency_hash=downstream_dependency_hash,
    )
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "reconciliation_record_id": "recon-1",
        "package_supersession_preview_hash": package_supersession_preview_hash,
        "source_package_set_hash": source["source_package_set_hash"],
        "source_output_package_ids": source["source_output_package_ids"],
        "source_package_kinds": source["source_package_kinds"],
        "source_payload_refs": source["source_payload_refs"],
        "source_payload_hashes": source["source_payload_hashes"],
        "replacement_package_set_authority_id": authority["replacement_package_set_authority_id"],
        "replacement_package_set_id": authority["replacement_package_set_id"],
        "replacement_package_set_hash": authority["replacement_package_set_hash"],
        "replacement_package_kinds": authority["replacement_package_kinds"],
        "replacement_payload_refs": authority["replacement_payload_refs"],
        "replacement_payload_hashes": authority["replacement_payload_hashes"],
        "replacement_authority_basis_hash": authority["authority_basis_hash"],
        "downstream_dependency_hash": downstream_dependency_hash,
        "commit_basis_hash": commit_basis_hash,
        "operator_decision": "commit_package_supersession",
    }


def _seed_corrected_artifact_commit_authority(db, tmp_path: Path) -> dict:
    source = _seed_commit_source(db, tmp_path)
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
    corrected_package_set_hash = authority_service.replacement_package_set_hash(
        replacement_package_set_id="corrected-package-set-1",
        replacement_package_kinds=PACKAGE_KINDS,
        replacement_payload_refs=corrected_refs,
        replacement_payload_hashes=corrected_hashes,
    )
    artifact_manifest_hash = stable_hash(
        {
            "schema_id": "test.corrected_package_artifact_manifest.v1",
            "corrected_package_set_hash": corrected_package_set_hash,
            "corrected_artifact_hashes": corrected_hashes,
        }
    )
    corrected_basis_hash = stable_hash(
        {
            "schema_id": "test.corrected_artifact_basis.v1",
            "source_package_set_hash": source["source_package_set_hash"],
            "corrected_package_set_hash": corrected_package_set_hash,
            "artifact_manifest_hash": artifact_manifest_hash,
        }
    )
    corrected = L3CorrectedPackageArtifactSet(
        corrected_package_artifact_set_id="corrected-set-1",
        client_request_id="req-corrected-set",
        session_id="session-1",
        analysis_plan_id="plan-1",
        pass_run_id="pass-1",
        reconciliation_record_id="recon-1",
        replacement_artifact_materialization_id="materialization-1",
        materialization_basis_hash="materialization-basis-1",
        source_package_set_hash=source["source_package_set_hash"],
        source_output_package_ids_json=source["source_output_package_ids"],
        source_package_kinds_json=source["source_package_kinds"],
        source_payload_refs_json=source["source_payload_refs"],
        source_payload_hashes_json=source["source_payload_hashes"],
        result_review_record_ref="result-review-ref-1",
        reviewed_output_items_hash="reviewed-items-hash-1",
        package_review_preview_hash=PACKAGE_REVIEW_PREVIEW_HASH,
        corrected_package_set_id="corrected-package-set-1",
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
    db.add(corrected)
    db.commit()
    authority = authority_service.record_replacement_package_set_authority_from_corrected_artifact_set(
        db,
        {
            "client_request_id": "req-from-corrected-authority",
            "session_id": "session-1",
            "analysis_plan_id": "plan-1",
            "pass_run_id": "pass-1",
            "reconciliation_record_id": "recon-1",
            "source_package_set_hash": source["source_package_set_hash"],
            "corrected_package_artifact_set_id": "corrected-set-1",
            "corrected_artifact_basis_hash": corrected_basis_hash,
            "operator_decision": "record_replacement_package_set_authority",
        },
    )
    return {
        "source": source,
        "authority": authority,
        "corrected_artifact_basis_hash": corrected_basis_hash,
        "raw_corrected_refs": corrected_refs,
    }


def _commit_from_corrected_payload(seed: dict, request_id: str = "req-corrected-supersession-commit") -> dict:
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "reconciliation_record_id": "recon-1",
        "corrected_package_artifact_set_id": "corrected-set-1",
        "corrected_artifact_basis_hash": seed["corrected_artifact_basis_hash"],
        "replacement_package_set_authority_id": seed["authority"]["replacement_package_set_authority_id"],
        "replacement_authority_basis_hash": seed["authority"]["authority_basis_hash"],
        "operator_decision": "commit_package_supersession",
    }


def test_package_supersession_commit_concurrent_duplicate_request_records_one_lineage(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'supersession-commit.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    setup_db = SessionLocal()
    try:
        source = _seed_commit_source(setup_db, tmp_path)
        authority = authority_service.record_replacement_package_set_authority(
            setup_db,
            _authority_payload(source),
        )
        payload = _commit_payload(source, authority)
        original_summary = setup_db.query(L3ReconciliationRecord).one().summary_json
    finally:
        setup_db.close()

    def submit_commit(_actor: str) -> tuple[str, str]:
        db = SessionLocal()
        try:
            response = commit_service.commit_package_supersession(db, payload)
            return ("returned", response["status"])
        except Layer3WorkbenchError as exc:
            return ("rejected", exc.error_code)
        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit_commit, ("pytest-1", "pytest-2")))
        assert sum(kind == "returned" and status == "committed" for kind, status in results) == 1
        assert all(
            (kind == "returned" and status in {"committed", "already_committed"})
            or (kind == "rejected" and status == "package_supersession_commit_in_progress")
            for kind, status in results
        )
        db = SessionLocal()
        try:
            assert db.query(L3PackageSupersessionCommit).count() == 1
            assert db.query(L3OutputPackage).count() == 3
            assert db.query(L3ReplacementPackageSetAuthority).count() == 1
            assert db.query(L3ReconciliationRecord).one().summary_json == original_summary
            commit = db.query(L3PackageSupersessionCommit).one()
            assert commit.client_request_id == "req-supersession-commit"
            assert commit.commit_basis_hash == payload["commit_basis_hash"]
            assert commit.operator_decision == "commit_package_supersession"
            assert commit.status == "committed"
        finally:
            db.close()
    finally:
        engine.dispose()


def test_package_supersession_commit_from_corrected_artifact_authority_redacts_refs(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'corrected-supersession-commit.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        seed = _seed_corrected_artifact_commit_authority(db, tmp_path)
        payload = _commit_from_corrected_payload(seed)
        packages_before = [
            (package.output_package_id, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.output_package_id).all()
        ]

        response = commit_service.commit_package_supersession_from_corrected_artifact_set_authority(db, payload)

        assert response["schema_id"] == "layer3.package_supersession_commit.v1"
        assert response["status"] == "committed"
        assert response["operator_decision"] == "commit_package_supersession"
        assert response["source_gate"] == (
            "711_CORRECTED_ARTIFACT_PACKAGE_REBUILD_DOWNSTREAM_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC"
        )
        assert response["authority_rail"]["response_payload_refs_redacted"] is True
        assert all(ref.startswith("artifact://source-output-package/") for ref in response["source_payload_refs"])
        assert all(
            ref.startswith("artifact://package-supersession-commit-replacement/")
            for ref in response["replacement_payload_refs"]
        )
        assert not any(raw_ref in str(response) for raw_ref in seed["raw_corrected_refs"])
        assert response["commit_snapshot"]["source"]["raw_payload_refs_exposed"] is False
        assert response["commit_snapshot"]["replacement"]["raw_payload_refs_exposed"] is False
        assert response["commit_snapshot"]["corrected_artifact_set"]["raw_artifact_refs_exposed"] is False

        assert db.query(L3PackageSupersessionCommit).count() == 1
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
        assert db.query(L3ReplacementPackageArtifactManifest).count() == 0
        assert db.query(L3ReplacementOutputPackage).count() == 0
        assert db.query(L3PackageReplacementActivation).count() == 0
        packages_after = [
            (package.output_package_id, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.output_package_id).all()
        ]
        assert packages_after == packages_before

        replay = commit_service.commit_package_supersession_from_corrected_artifact_set_authority(db, payload)
        assert replay["status"] == "already_committed"
        assert replay["package_supersession_commit_id"] == response["package_supersession_commit_id"]
        same_basis = commit_service.commit_package_supersession_from_corrected_artifact_set_authority(
            db,
            {**payload, "client_request_id": "req-corrected-supersession-commit-same-basis"},
        )
        assert same_basis["status"] == "already_committed"
        assert same_basis["package_supersession_commit_id"] == response["package_supersession_commit_id"]
        assert db.query(L3PackageSupersessionCommit).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_package_supersession_commit_from_corrected_artifact_authority_prechecks_fail_closed(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'corrected-supersession-prechecks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        seed = _seed_corrected_artifact_commit_authority(db, tmp_path)
        payload = _commit_from_corrected_payload(seed)
        cases = [
            (
                {**payload, "replacement_payload_refs": [str(tmp_path / "forbidden.json")]},
                "package_supersession_commit_from_corrected_artifact_set_scope_not_admitted",
            ),
            (
                {**payload, "destination_url": "file:///tmp/out"},
                "package_supersession_commit_from_corrected_artifact_set_scope_not_admitted",
            ),
            (
                {**payload, "operator_decision": "record_replacement_package_set_authority"},
                "unsupported_package_supersession_commit_from_corrected_artifact_set_decision",
            ),
            (
                {**payload, "corrected_artifact_basis_hash": "stale-corrected-basis"},
                "package_supersession_commit_corrected_artifact_basis_hash_mismatch",
            ),
            (
                {**payload, "replacement_authority_basis_hash": "stale-replacement-basis"},
                "package_supersession_commit_corrected_replacement_authority_basis_hash_mismatch",
            ),
            (
                {**payload, "replacement_package_set_authority_id": "missing-authority"},
                "package_supersession_commit_corrected_replacement_authority_not_found",
            ),
            (
                {**payload, "session_id": "wrong-session"},
                "package_supersession_commit_corrected_artifact_set_session_id_mismatch",
            ),
        ]
        for bad_payload, expected_error in cases:
            try:
                commit_service.commit_package_supersession_from_corrected_artifact_set_authority(db, bad_payload)
            except Layer3WorkbenchError as exc:
                assert exc.error_code == expected_error
            else:
                raise AssertionError(f"expected {expected_error}")

        response = commit_service.commit_package_supersession_from_corrected_artifact_set_authority(db, payload)
        assert response["status"] == "committed"
        try:
            commit_service.commit_package_supersession_from_corrected_artifact_set_authority(
                db,
                {**payload, "client_request_id": payload["client_request_id"], "corrected_artifact_basis_hash": "other"},
            )
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "package_supersession_commit_corrected_artifact_basis_hash_mismatch"
        else:
            raise AssertionError("expected same-key different-basis conflict to fail closed")
        assert db.query(L3PackageSupersessionCommit).count() == 1
    finally:
        db.close()
        engine.dispose()
