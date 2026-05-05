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
MIGRATION = BACKEND / "alembic" / "versions" / "0020_layer3_replacement_package_artifact_manifest.py"

from app.db.session import Base
from app.models.models import (
    L3AnalysisPlan,
    L3AnalysisSet,
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_package_supersession_commit as commit_service
from app.services import layer3_replacement_package_artifact_manifest as manifest_service
from app.services import layer3_replacement_package_set_authority as authority_service
from app.services.layer3_package_mutation_entry import PACKAGE_SUPERSESSION_PREVIEW_MODE
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench import Layer3WorkbenchError


PACKAGE_KINDS = ["canonical_internal", "user_facing", "review_facing"]
PACKAGE_REVIEW_PREVIEW_HASH = "package-review-preview-hash-1"


def test_replacement_package_artifact_manifest_migration_defines_durable_manifest_constraints(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_replacement_package_artifact_manifest_migration", MIGRATION)
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

    elements = next(items for name, items in created_tables if name == "l3_replacement_package_artifact_manifest")
    unique_names = {element.name for element in elements if isinstance(element, UniqueConstraint)}
    assert "uq_l3_replacement_artifact_manifest_client_request" in unique_names
    assert "uq_l3_replacement_artifact_manifest_basis_hash" in unique_names
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    operator_constraint = next(
        element for element in constraints if element.name == "ck_l3_replacement_artifact_manifest_operator_decision"
    )
    status_constraint = next(
        element for element in constraints if element.name == "ck_l3_replacement_artifact_manifest_status"
    )
    assert "record_replacement_package_artifact_manifest" in str(operator_constraint.sqltext)
    assert "verified" in str(status_constraint.sqltext)
    assert (
        "ix_l3_replacement_artifact_manifest_session",
        "l3_replacement_package_artifact_manifest",
        ["session_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_replacement_artifact_manifest_replacement_authority",
        "l3_replacement_package_artifact_manifest",
        ["replacement_package_set_authority_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_replacement_artifact_manifest_supersession_commit",
        "l3_replacement_package_artifact_manifest",
        ["package_supersession_commit_id"],
        {},
    ) in created_indexes


def _hash_payload(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _source_package_rows(tmp_path: Path) -> list[dict]:
    rows = []
    payload_dir = tmp_path / "source-payloads"
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


def _seed_source(db, tmp_path: Path) -> dict:
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


def _replacement_artifacts(tmp_path: Path, request_id: str = "replacement-artifacts") -> dict:
    artifact_dir = tmp_path / manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE
    artifact_dir.mkdir(exist_ok=True)
    refs = []
    hashes = []
    byte_sizes = []
    for package_kind in PACKAGE_KINDS:
        payload = {"package_kind": package_kind, "replacement": request_id}
        payload_ref = artifact_dir / f"{package_kind}.json"
        payload_ref.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        refs.append(str(payload_ref))
        hashes.append(_hash_payload(payload))
        byte_sizes.append(len(payload_ref.read_bytes()))
    return {
        "replacement_payload_refs": refs,
        "replacement_payload_hashes": hashes,
        "verified_artifact_refs": [str(Path(ref).resolve(strict=True)) for ref in refs],
        "verified_artifact_hashes": list(hashes),
        "verified_artifact_byte_sizes": byte_sizes,
    }


def _authority_payload(source: dict, artifacts: dict, request_id: str = "req-replacement-authority") -> dict:
    replacement_package_set_hash = authority_service.replacement_package_set_hash(
        replacement_package_set_id="replacement-set-1",
        replacement_package_kinds=PACKAGE_KINDS,
        replacement_payload_refs=artifacts["replacement_payload_refs"],
        replacement_payload_hashes=artifacts["replacement_payload_hashes"],
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
        replacement_payload_refs=artifacts["replacement_payload_refs"],
        replacement_payload_hashes=artifacts["replacement_payload_hashes"],
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
        "replacement_payload_refs": artifacts["replacement_payload_refs"],
        "replacement_payload_hashes": artifacts["replacement_payload_hashes"],
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


def _manifest_payload(
    *,
    authority: dict,
    commit: dict,
    artifacts: dict,
    request_id: str = "req-artifact-manifest",
) -> dict:
    artifact_manifest_hash = manifest_service.replacement_package_artifact_manifest_hash(
        replacement_package_set_authority_id=authority["replacement_package_set_authority_id"],
        package_supersession_commit_id=commit["package_supersession_commit_id"],
        replacement_package_set_id=authority["replacement_package_set_id"],
        replacement_package_set_hash=authority["replacement_package_set_hash"],
        replacement_package_kinds=authority["replacement_package_kinds"],
        replacement_payload_refs=authority["replacement_payload_refs"],
        replacement_payload_hashes=authority["replacement_payload_hashes"],
        verified_artifact_refs=artifacts["verified_artifact_refs"],
        verified_artifact_hashes=artifacts["verified_artifact_hashes"],
        verified_artifact_byte_sizes=artifacts["verified_artifact_byte_sizes"],
        artifact_namespace=manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
    )
    authority_basis_hash = manifest_service.replacement_package_artifact_manifest_authority_basis_hash(
        session_id="session-1",
        analysis_plan_id="plan-1",
        pass_run_id="pass-1",
        reconciliation_record_id="recon-1",
        replacement_package_set_authority_id=authority["replacement_package_set_authority_id"],
        replacement_authority_basis_hash=authority["authority_basis_hash"],
        package_supersession_commit_id=commit["package_supersession_commit_id"],
        package_supersession_commit_basis_hash=commit["commit_basis_hash"],
        artifact_manifest_hash=artifact_manifest_hash,
    )
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-1",
        "reconciliation_record_id": "recon-1",
        "replacement_package_set_authority_id": authority["replacement_package_set_authority_id"],
        "package_supersession_commit_id": commit["package_supersession_commit_id"],
        "package_supersession_commit_basis_hash": commit["commit_basis_hash"],
        "replacement_package_set_id": authority["replacement_package_set_id"],
        "replacement_package_set_hash": authority["replacement_package_set_hash"],
        "replacement_package_kinds": authority["replacement_package_kinds"],
        "replacement_payload_refs": authority["replacement_payload_refs"],
        "replacement_payload_hashes": authority["replacement_payload_hashes"],
        "hash_algorithm": manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
        "artifact_namespace": manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
        "artifact_manifest_hash": artifact_manifest_hash,
        "authority_basis_hash": authority_basis_hash,
        "operator_decision": "record_replacement_package_artifact_manifest",
    }


def _record_authority_chain(db, tmp_path: Path) -> tuple[dict, dict, dict, dict]:
    source = _seed_source(db, tmp_path)
    artifacts = _replacement_artifacts(tmp_path)
    authority = authority_service.record_replacement_package_set_authority(db, _authority_payload(source, artifacts))
    commit = commit_service.commit_package_supersession(db, _commit_payload(source, authority))
    return source, artifacts, authority, commit


def test_replacement_package_artifact_manifest_records_server_verified_manifest_only(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'artifact-manifest.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, artifacts, authority, commit = _record_authority_chain(db, tmp_path)
        source_packages_before = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        files_before = {ref: Path(ref).read_bytes() for ref in artifacts["replacement_payload_refs"]}
        payload = _manifest_payload(authority=authority, commit=commit, artifacts=artifacts)

        response = manifest_service.record_replacement_package_artifact_manifest(db, payload)

        assert response["schema_id"] == "layer3.replacement_package_artifact_manifest.v1"
        assert response["status"] == "recorded"
        assert response["replacement_package_set_authority_id"] == authority["replacement_package_set_authority_id"]
        assert response["package_supersession_commit_id"] == commit["package_supersession_commit_id"]
        assert response["replacement_payload_refs"] == authority["replacement_payload_refs"]
        assert response["replacement_payload_hashes"] == authority["replacement_payload_hashes"]
        assert response["verified_artifact_refs"] == artifacts["verified_artifact_refs"]
        assert response["verified_artifact_hashes"] == artifacts["verified_artifact_hashes"]
        assert response["verified_artifact_byte_sizes"] == artifacts["verified_artifact_byte_sizes"]
        assert response["artifact_generation_enabled"] is False
        assert response["package_row_mutation_enabled"] is False
        assert response["package_payload_write_enabled"] is False
        assert response["l3_output_package_write_enabled"] is False
        assert response["connector_dispatch_enabled"] is False
        assert response["provider_public_url_enabled"] is False
        assert response["source_widening_enabled"] is False
        assert response["qualitative_hybrid_rag_execution_enabled"] is False
        assert response["authority_rail"]["server_artifact_namespace_allowlist"] == ["replacement-package-artifacts"]
        assert db.query(L3ReplacementPackageArtifactManifest).count() == 1
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
        assert db.query(L3PackageSupersessionCommit).count() == 1
        assert db.query(L3OutputPackage).count() == 3
        source_packages_after = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        assert source_packages_after == source_packages_before
        assert {ref: Path(ref).read_bytes() for ref in artifacts["replacement_payload_refs"]} == files_before

        replay = manifest_service.record_replacement_package_artifact_manifest(db, payload)
        assert replay["status"] == "already_recorded"
        assert replay["replacement_package_artifact_manifest_id"] == response["replacement_package_artifact_manifest_id"]
        same_basis = manifest_service.record_replacement_package_artifact_manifest(
            db,
            {**payload, "client_request_id": "req-artifact-manifest-same-basis"},
        )
        assert same_basis["status"] == "already_recorded"
        assert same_basis["replacement_package_artifact_manifest_id"] == response[
            "replacement_package_artifact_manifest_id"
        ]
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_artifact_manifest_prechecks_fail_closed(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'artifact-manifest-prechecks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, artifacts, authority, commit = _record_authority_chain(db, tmp_path)
        payload = _manifest_payload(authority=authority, commit=commit, artifacts=artifacts)
        cases = [
            (
                {**payload, "operator_decision": "commit_package_supersession"},
                "unsupported_replacement_package_artifact_manifest_decision",
            ),
            (
                {**payload, "generate_artifact": True},
                "replacement_package_artifact_manifest_scope_not_admitted",
            ),
            (
                {**payload, "hash_algorithm": "md5"},
                "unsupported_replacement_package_artifact_manifest_hash_algorithm",
            ),
            (
                {**payload, "artifact_namespace": "source-payloads"},
                "unsupported_replacement_package_artifact_manifest_namespace",
            ),
            (
                {**payload, "package_supersession_commit_basis_hash": "stale-commit-basis"},
                "replacement_package_artifact_manifest_package_supersession_commit_basis_hash_mismatch",
            ),
            (
                {**payload, "replacement_package_set_hash": "stale-replacement-set-hash"},
                "replacement_package_artifact_manifest_replacement_package_set_hash_mismatch",
            ),
            (
                {**payload, "artifact_manifest_hash": "stale-artifact-manifest-hash"},
                "replacement_package_artifact_manifest_hash_mismatch",
            ),
            (
                {**payload, "authority_basis_hash": "stale-authority-basis-hash"},
                "replacement_package_artifact_manifest_authority_basis_hash_mismatch",
            ),
        ]
        for bad_payload, expected_error in cases:
            try:
                manifest_service.record_replacement_package_artifact_manifest(db, bad_payload)
            except Layer3WorkbenchError as exc:
                assert exc.error_code == expected_error
            else:
                raise AssertionError(f"expected {expected_error}")

        authority_row = (
            db.query(L3ReplacementPackageSetAuthority)
            .filter(
                L3ReplacementPackageSetAuthority.replacement_package_set_authority_id
                == authority["replacement_package_set_authority_id"]
            )
            .one()
        )
        authority_row.replacement_payload_hashes_json = authority_row.replacement_payload_hashes_json[:-1]
        db.commit()
        try:
            manifest_service.record_replacement_package_artifact_manifest(db, payload)
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "replacement_package_artifact_manifest_authority_vector_mismatch"
        else:
            raise AssertionError("expected stale replacement authority vector")

        missing_artifacts = _replacement_artifacts(tmp_path, request_id="missing")
        missing_ref = tmp_path / manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE / "missing.json"
        missing_artifacts["replacement_payload_refs"][0] = str(missing_ref)
        missing_artifacts["replacement_payload_hashes"][0] = hashlib.sha256(b"missing").hexdigest()
        missing_authority = authority_service.record_replacement_package_set_authority(
            db,
            _authority_payload(source, missing_artifacts, request_id="req-missing-authority"),
        )
        missing_commit = commit_service.commit_package_supersession(
            db,
            _commit_payload(source, missing_authority, request_id="req-missing-commit"),
        )
        missing_payload = {
            "client_request_id": "req-artifact-manifest-missing-ref",
            "session_id": "session-1",
            "analysis_plan_id": "plan-1",
            "pass_run_id": "pass-1",
            "reconciliation_record_id": "recon-1",
            "replacement_package_set_authority_id": missing_authority["replacement_package_set_authority_id"],
            "package_supersession_commit_id": missing_commit["package_supersession_commit_id"],
            "package_supersession_commit_basis_hash": missing_commit["commit_basis_hash"],
            "replacement_package_set_id": missing_authority["replacement_package_set_id"],
            "replacement_package_set_hash": missing_authority["replacement_package_set_hash"],
            "replacement_package_kinds": missing_authority["replacement_package_kinds"],
            "replacement_payload_refs": missing_authority["replacement_payload_refs"],
            "replacement_payload_hashes": missing_authority["replacement_payload_hashes"],
            "hash_algorithm": manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "artifact_namespace": manifest_service.REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
            "artifact_manifest_hash": "placeholder-artifact-manifest-hash",
            "authority_basis_hash": "placeholder-authority-basis-hash",
            "operator_decision": "record_replacement_package_artifact_manifest",
        }
        try:
            manifest_service.record_replacement_package_artifact_manifest(db, missing_payload)
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "replacement_package_artifact_manifest_ref_missing"
        else:
            raise AssertionError("expected missing replacement artifact ref")
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_artifact_manifest_rejects_hash_mismatch_outside_namespace_and_source_ref_reuse(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'artifact-manifest-ref-checks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, artifacts, authority, commit = _record_authority_chain(db, tmp_path)
        payload = _manifest_payload(authority=authority, commit=commit, artifacts=artifacts)

        Path(artifacts["replacement_payload_refs"][0]).write_text("tampered", encoding="utf-8")
        try:
            manifest_service.record_replacement_package_artifact_manifest(
                db,
                {**payload, "client_request_id": "req-artifact-manifest-hash-mismatch"},
            )
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "replacement_package_artifact_manifest_payload_hash_mismatch"
        else:
            raise AssertionError("expected payload hash mismatch")

        outside_artifacts = _replacement_artifacts(tmp_path, request_id="outside")
        outside_ref = tmp_path / "outside-artifacts" / "canonical_internal.json"
        outside_ref.parent.mkdir(exist_ok=True)
        outside_ref.write_text("outside", encoding="utf-8")
        outside_artifacts["replacement_payload_refs"][0] = str(outside_ref)
        outside_artifacts["replacement_payload_hashes"][0] = hashlib.sha256(b"outside").hexdigest()
        outside_artifacts["verified_artifact_refs"][0] = str(outside_ref.resolve(strict=True))
        outside_artifacts["verified_artifact_hashes"][0] = hashlib.sha256(b"outside").hexdigest()
        outside_artifacts["verified_artifact_byte_sizes"][0] = len(outside_ref.read_bytes())
        outside_authority = authority_service.record_replacement_package_set_authority(
            db,
            _authority_payload(source, outside_artifacts, request_id="req-outside-authority"),
        )
        outside_commit = commit_service.commit_package_supersession(
            db,
            _commit_payload(source, outside_authority, request_id="req-outside-commit"),
        )
        outside_payload = _manifest_payload(
            authority=outside_authority,
            commit=outside_commit,
            artifacts=outside_artifacts,
            request_id="req-outside-manifest",
        )
        try:
            manifest_service.record_replacement_package_artifact_manifest(db, outside_payload)
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "replacement_package_artifact_manifest_ref_outside_namespace"
        else:
            raise AssertionError("expected outside namespace rejection")

        reused_artifacts = _replacement_artifacts(tmp_path, request_id="reuse-source")
        reused_artifacts["replacement_payload_refs"][0] = source["source_payload_refs"][0]
        reused_artifacts["replacement_payload_hashes"][0] = source["source_payload_hashes"][0]
        reused_artifacts["verified_artifact_refs"][0] = str(Path(source["source_payload_refs"][0]).resolve(strict=True))
        reused_artifacts["verified_artifact_hashes"][0] = source["source_payload_hashes"][0]
        reused_artifacts["verified_artifact_byte_sizes"][0] = len(Path(source["source_payload_refs"][0]).read_bytes())
        try:
            authority_service.record_replacement_package_set_authority(
                db,
                _authority_payload(source, reused_artifacts, request_id="req-reuse-authority"),
            )
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "replacement_package_set_authority_reuses_source_payload_ref"
        else:
            raise AssertionError("expected source ref reuse rejection")
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_artifact_manifest_concurrent_duplicate_request_records_one_manifest(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'artifact-manifest-concurrent.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    setup_db = SessionLocal()
    try:
        _source, artifacts, authority, commit = _record_authority_chain(setup_db, tmp_path)
        payload = _manifest_payload(authority=authority, commit=commit, artifacts=artifacts)
    finally:
        setup_db.close()

    def record_manifest() -> tuple[str, str]:
        db = SessionLocal()
        try:
            response = manifest_service.record_replacement_package_artifact_manifest(db, payload)
            return ("returned", response["status"])
        except Layer3WorkbenchError as exc:
            return ("rejected", exc.error_code)
        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _idx: record_manifest(), range(2)))
        assert all(
            (kind == "returned" and status in {"recorded", "already_recorded"})
            or (kind == "rejected" and status == "replacement_package_artifact_manifest_in_progress")
            for kind, status in results
        )
        db = SessionLocal()
        try:
            assert db.query(L3ReplacementPackageArtifactManifest).count() == 1
            assert db.query(L3OutputPackage).count() == 3
            manifest = db.query(L3ReplacementPackageArtifactManifest).one()
            assert manifest.client_request_id == "req-artifact-manifest"
            assert manifest.authority_basis_hash == payload["authority_basis_hash"]
            assert manifest.verified_artifact_refs_json == artifacts["verified_artifact_refs"]
        finally:
            db.close()
    finally:
        engine.dispose()
