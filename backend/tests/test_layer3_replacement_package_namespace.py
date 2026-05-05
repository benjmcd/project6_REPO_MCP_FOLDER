from __future__ import annotations

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
sys.path.insert(0, str(BACKEND / "alembic" / "versions"))
MIGRATION = BACKEND / "alembic" / "versions" / "0021_layer3_replacement_output_package.py"

from app.db.session import Base
from app.models.models import (
    L3OutputPackage,
    L3ReplacementOutputPackage,
)
from app.services import layer3_replacement_package_artifact_manifest as manifest_service
from app.services import layer3_replacement_package_namespace as namespace_service
from app.services.layer3_package_entry import PACKAGE_SCHEMA_IDS
from app.services.layer3_workbench import Layer3WorkbenchError
from test_layer3_replacement_package_artifact_manifest import (
    PACKAGE_KINDS,
    _manifest_payload,
    _record_authority_chain,
)


def test_replacement_package_namespace_migration_defines_durable_namespace_constraints(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_replacement_output_package_migration", MIGRATION)
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

    elements = next(items for name, items in created_tables if name == "l3_replacement_output_package")
    unique_names = {element.name for element in elements if isinstance(element, UniqueConstraint)}
    assert "uq_l3_replacement_output_package_manifest_kind" in unique_names
    assert "uq_l3_replacement_output_package_client_request" in unique_names
    assert "uq_l3_replacement_output_package_basis_hash" in unique_names
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    operator_constraint = next(
        element for element in constraints if element.name == "ck_l3_replacement_output_package_operator_decision"
    )
    status_constraint = next(
        element for element in constraints if element.name == "ck_l3_replacement_output_package_status"
    )
    assert "record_replacement_package_namespace" in str(operator_constraint.sqltext)
    assert "recorded" in str(status_constraint.sqltext)
    assert (
        "ix_l3_replacement_output_package_manifest",
        "l3_replacement_output_package",
        ["replacement_artifact_manifest_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_replacement_output_package_source",
        "l3_replacement_output_package",
        ["source_output_package_id"],
        {},
    ) in created_indexes
    assert (
        "ix_l3_replacement_output_package_supersession_commit",
        "l3_replacement_output_package",
        ["package_supersession_commit_id"],
        {},
    ) in created_indexes


def _record_manifest_chain(db, tmp_path: Path) -> tuple[dict, dict, dict, dict]:
    source, artifacts, authority, commit = _record_authority_chain(db, tmp_path)
    manifest = manifest_service.record_replacement_package_artifact_manifest(
        db,
        _manifest_payload(authority=authority, commit=commit, artifacts=artifacts),
    )
    return source, authority, commit, manifest


def _namespace_payload(
    *,
    source: dict,
    authority: dict,
    commit: dict,
    manifest: dict,
    request_id: str = "req-replacement-namespace",
    package_kind: str = "canonical_internal",
) -> dict:
    index = PACKAGE_KINDS.index(package_kind)
    source_output_package_id = source["source_output_package_ids"][index]
    package_schema_id = PACKAGE_SCHEMA_IDS[package_kind]
    artifact_ref = manifest["verified_artifact_refs"][index]
    artifact_hash = manifest["verified_artifact_hashes"][index]
    authority_basis_hash = namespace_service.replacement_package_namespace_authority_basis_hash(
        session_id="session-1",
        source_output_package_id=source_output_package_id,
        source_package_kind=package_kind,
        source_package_schema_id=package_schema_id,
        source_payload_ref=source["source_payload_refs"][index],
        source_payload_hash=source["source_payload_hashes"][index],
        replacement_artifact_manifest_id=manifest["replacement_package_artifact_manifest_id"],
        replacement_artifact_manifest_authority_basis_hash=manifest["authority_basis_hash"],
        replacement_artifact_ref=artifact_ref,
        replacement_artifact_hash=artifact_hash,
        replacement_package_set_authority_id=authority["replacement_package_set_authority_id"],
        replacement_package_set_authority_basis_hash=authority["authority_basis_hash"],
        package_supersession_commit_id=commit["package_supersession_commit_id"],
        package_supersession_commit_basis_hash=commit["commit_basis_hash"],
        package_kind=package_kind,
        package_schema_id=package_schema_id,
        operator_decision="record_replacement_package_namespace",
        client_request_id=request_id,
    )
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "replacement_artifact_manifest_id": manifest["replacement_package_artifact_manifest_id"],
        "replacement_package_set_authority_id": authority["replacement_package_set_authority_id"],
        "package_supersession_commit_id": commit["package_supersession_commit_id"],
        "source_output_package_id": source_output_package_id,
        "package_kind": package_kind,
        "package_schema_id": package_schema_id,
        "artifact_ref": artifact_ref,
        "artifact_hash": artifact_hash,
        "authority_basis_hash": authority_basis_hash,
        "operator_decision": "record_replacement_package_namespace",
    }


def test_replacement_package_namespace_records_separate_row_without_package_mutation(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'replacement-namespace.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, authority, commit, manifest = _record_manifest_chain(db, tmp_path)
        payload = _namespace_payload(source=source, authority=authority, commit=commit, manifest=manifest)
        source_packages_before = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        files_before = {ref: Path(ref).read_bytes() for ref in manifest["verified_artifact_refs"]}

        response = namespace_service.record_replacement_package_namespace(db, payload)

        assert response["schema_id"] == "layer3.replacement_package_namespace.v1"
        assert response["status"] == "recorded"
        assert response["source_output_package_id"] == payload["source_output_package_id"]
        assert response["replacement_artifact_manifest_id"] == payload["replacement_artifact_manifest_id"]
        assert response["replacement_package_set_authority_id"] == payload["replacement_package_set_authority_id"]
        assert response["package_supersession_commit_id"] == payload["package_supersession_commit_id"]
        assert response["package_kind"] == "canonical_internal"
        assert response["package_schema_id"] == PACKAGE_SCHEMA_IDS["canonical_internal"]
        assert response["artifact_ref"] == payload["artifact_ref"]
        assert response["artifact_hash"] == payload["artifact_hash"]
        assert response["operator_decision"] == "record_replacement_package_namespace"
        assert response["replacement_package_namespace_mode"] == "replacement_package_namespace_rows"
        assert response["source_gate"] == "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE"
        assert response["namespace_row_persisted"] is True
        assert response["package_row_mutation_enabled"] is False
        assert response["package_payload_write_enabled"] is False
        assert response["l3_output_package_write_enabled"] is False
        assert response["broad_package_mutation_enabled"] is False
        assert response["connector_dispatch_enabled"] is False
        assert response["provider_public_url_enabled"] is False
        assert response["source_widening_enabled"] is False
        assert response["qualitative_hybrid_rag_execution_enabled"] is False
        assert response["authority_rail"]["separate_replacement_output_package_table"] is True
        assert response["authority_rail"]["source_l3_output_package_mutated"] is False
        assert db.query(L3ReplacementOutputPackage).count() == 1
        assert db.query(L3OutputPackage).count() == 3
        source_packages_after = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        assert source_packages_after == source_packages_before
        assert {ref: Path(ref).read_bytes() for ref in manifest["verified_artifact_refs"]} == files_before

        replay = namespace_service.record_replacement_package_namespace(db, payload)
        assert replay["status"] == "already_recorded"
        assert replay["replacement_output_package_id"] == response["replacement_output_package_id"]
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_namespace_prechecks_fail_closed(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'replacement-namespace-prechecks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, authority, commit, manifest = _record_manifest_chain(db, tmp_path)
        payload = _namespace_payload(source=source, authority=authority, commit=commit, manifest=manifest)
        cases = [
            ({**payload, "package_payload": {"not": "admitted"}}, "replacement_package_namespace_scope_not_admitted"),
            (
                {**payload, "operator_decision": "record_replacement_package_artifact_manifest"},
                "unsupported_replacement_package_namespace_decision",
            ),
            (
                {**payload, "package_schema_id": "layer3.wrong_package.v1"},
                "replacement_package_namespace_package_schema_mismatch",
            ),
            (
                {**payload, "source_output_package_id": source["source_output_package_ids"][1]},
                "replacement_package_namespace_source_package_kind_mismatch",
            ),
            (
                {**payload, "artifact_ref": "stale-artifact-ref"},
                "replacement_package_namespace_artifact_ref_mismatch",
            ),
            (
                {**payload, "artifact_hash": "stale-artifact-hash"},
                "replacement_package_namespace_artifact_hash_mismatch",
            ),
            (
                {**payload, "authority_basis_hash": "stale-authority-basis-hash"},
                "replacement_package_namespace_authority_basis_hash_mismatch",
            ),
        ]
        for bad_payload, expected_error in cases:
            try:
                namespace_service.record_replacement_package_namespace(db, bad_payload)
            except Layer3WorkbenchError as exc:
                assert exc.error_code == expected_error
            else:
                raise AssertionError(f"expected {expected_error}")

        source_package = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id == payload["source_output_package_id"])
            .one()
        )
        source_package.payload_hash = "stale-source-payload-hash"
        db.commit()
        try:
            namespace_service.record_replacement_package_namespace(db, payload)
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "replacement_package_namespace_source_payload_mismatch"
        else:
            raise AssertionError("expected stale source payload rejection")
    finally:
        db.close()
        engine.dispose()


def test_replacement_package_namespace_concurrent_duplicate_request_records_one_row(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'replacement-namespace-concurrent.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    setup_db = SessionLocal()
    try:
        source, authority, commit, manifest = _record_manifest_chain(setup_db, tmp_path)
        payload = _namespace_payload(source=source, authority=authority, commit=commit, manifest=manifest)
    finally:
        setup_db.close()

    def record_namespace() -> tuple[str, str]:
        db = SessionLocal()
        try:
            response = namespace_service.record_replacement_package_namespace(db, payload)
            return ("returned", response["status"])
        except Layer3WorkbenchError as exc:
            return ("rejected", exc.error_code)
        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _idx: record_namespace(), range(2)))
        assert all(
            (kind == "returned" and status in {"recorded", "already_recorded"})
            or (kind == "rejected" and status == "replacement_package_namespace_in_progress")
            for kind, status in results
        )
        db = SessionLocal()
        try:
            assert db.query(L3ReplacementOutputPackage).count() == 1
            assert db.query(L3OutputPackage).count() == 3
            row = db.query(L3ReplacementOutputPackage).one()
            assert row.client_request_id == "req-replacement-namespace"
            assert row.authority_basis_hash == payload["authority_basis_hash"]
            assert row.artifact_ref == payload["artifact_ref"]
        finally:
            db.close()
    finally:
        engine.dispose()
