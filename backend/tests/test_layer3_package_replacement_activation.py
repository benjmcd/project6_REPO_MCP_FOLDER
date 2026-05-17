from __future__ import annotations

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
MIGRATION = BACKEND / "alembic" / "versions" / "0032_layer3_package_replacement_activation.py"

from app.db.session import Base
from app.models.models import (
    L3OutputPackage,
    L3PackageReplacementActivation,
    L3ReplacementOutputPackage,
)
from app.services import layer3_package_replacement_activation as activation_service
from app.services import layer3_replacement_package_namespace as namespace_service
from app.services.layer3_workbench import Layer3WorkbenchError
from test_layer3_replacement_package_artifact_manifest import PACKAGE_KINDS
from test_layer3_replacement_package_namespace import _namespace_payload, _record_manifest_chain


def test_package_replacement_activation_migration_defines_durable_activation_constraints(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_package_replacement_activation_migration", MIGRATION)
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

    elements = next(items for name, items in created_tables if name == "l3_package_replacement_activation")
    unique_names = {element.name for element in elements if isinstance(element, UniqueConstraint)}
    assert "uq_l3_package_replacement_activation_client_request" in unique_names
    assert "uq_l3_package_replacement_activation_basis_hash" in unique_names
    assert "uq_l3_package_replacement_activation_session" in unique_names
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    operator_constraint = next(
        element for element in constraints if element.name == "ck_l3_package_replacement_activation_operator_decision"
    )
    status_constraint = next(
        element for element in constraints if element.name == "ck_l3_package_replacement_activation_status"
    )
    assert "activate_replacement_output_package_namespace" in str(operator_constraint.sqltext)
    assert "activated" in str(status_constraint.sqltext)
    assert (
        "ix_l3_package_replacement_activation_manifest",
        "l3_package_replacement_activation",
        ["replacement_artifact_manifest_id"],
        {},
    ) in created_indexes


def _record_namespace_set(db, *, source: dict, authority: dict, commit: dict, manifest: dict) -> list[dict]:
    rows = []
    for package_kind in PACKAGE_KINDS:
        payload = _namespace_payload(
            source=source,
            authority=authority,
            commit=commit,
            manifest=manifest,
            request_id=f"req-replacement-namespace-{package_kind}",
            package_kind=package_kind,
        )
        rows.append(namespace_service.record_replacement_package_namespace(db, payload))
    return rows


def _activation_payload(
    *,
    source: dict,
    authority: dict,
    commit: dict,
    manifest: dict,
    namespaces: list[dict],
    request_id: str = "req-package-replacement-activation",
) -> dict:
    replacement_output_package_ids = [row["replacement_output_package_id"] for row in namespaces]
    namespace_basis_hashes = [row["authority_basis_hash"] for row in namespaces]
    active_artifact_refs = [row["artifact_ref"] for row in namespaces]
    active_artifact_hashes = [row["artifact_hash"] for row in namespaces]
    basis_hash = activation_service.package_replacement_activation_basis_hash(
        session_id="session-1",
        source_output_package_ids=source["source_output_package_ids"],
        source_package_kinds=PACKAGE_KINDS,
        source_payload_hashes=source["source_payload_hashes"],
        replacement_output_package_ids=replacement_output_package_ids,
        replacement_namespace_basis_hashes=namespace_basis_hashes,
        active_artifact_refs=active_artifact_refs,
        active_artifact_hashes=active_artifact_hashes,
        replacement_artifact_manifest_id=manifest["replacement_package_artifact_manifest_id"],
        replacement_artifact_manifest_authority_basis_hash=manifest["authority_basis_hash"],
        replacement_artifact_manifest_hash=manifest["artifact_manifest_hash"],
        replacement_package_set_authority_id=authority["replacement_package_set_authority_id"],
        replacement_package_set_authority_basis_hash=authority["authority_basis_hash"],
        package_supersession_commit_id=commit["package_supersession_commit_id"],
        package_supersession_commit_basis_hash=commit["commit_basis_hash"],
        package_kinds=PACKAGE_KINDS,
        operator_decision="activate_replacement_output_package_namespace",
    )
    return {
        "client_request_id": request_id,
        "session_id": "session-1",
        "replacement_artifact_manifest_id": manifest["replacement_package_artifact_manifest_id"],
        "replacement_package_set_authority_id": authority["replacement_package_set_authority_id"],
        "package_supersession_commit_id": commit["package_supersession_commit_id"],
        "replacement_output_package_ids": replacement_output_package_ids,
        "source_output_package_ids": source["source_output_package_ids"],
        "package_kinds": PACKAGE_KINDS,
        "replacement_activation_basis_hash": basis_hash,
        "operator_decision": "activate_replacement_output_package_namespace",
    }


def test_package_replacement_activation_selects_namespace_without_package_mutation(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'replacement-activation.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, authority, commit, manifest = _record_manifest_chain(db, tmp_path)
        namespaces = _record_namespace_set(db, source=source, authority=authority, commit=commit, manifest=manifest)
        payload = _activation_payload(source=source, authority=authority, commit=commit, manifest=manifest, namespaces=namespaces)
        source_packages_before = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        files_before = {ref: Path(ref).read_bytes() for ref in manifest["verified_artifact_refs"]}

        response = activation_service.commit_package_replacement_activation(db, payload)

        assert response["schema_id"] == "layer3.package_replacement_activation.v1"
        assert response["status"] == "activated"
        assert response["source_output_package_ids"] == payload["source_output_package_ids"]
        assert response["replacement_output_package_ids"] == payload["replacement_output_package_ids"]
        assert response["package_kinds"] == PACKAGE_KINDS
        assert response["replacement_activation_basis_hash"] == payload["replacement_activation_basis_hash"]
        assert response["operator_decision"] == "activate_replacement_output_package_namespace"
        assert response["package_replacement_activation_mode"] == "source_l3_output_package_replacement_activation"
        assert response["source_gate"] == "664_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_FREEZE"
        assert response["activation_receipt_persisted"] is True
        assert response["package_activation_state_persisted"] is True
        assert response["source_l3_output_package_mutated"] is False
        assert response["package_row_mutation_enabled"] is False
        assert response["package_payload_write_enabled"] is False
        assert response["package_payload_rewrite_enabled"] is False
        assert response["downstream_handoff_rebinding_enabled"] is False
        assert response["connector_dispatch_enabled"] is False
        assert response["provider_public_url_enabled"] is False
        assert response["source_widening_enabled"] is False
        assert response["qualitative_hybrid_rag_execution_enabled"] is False
        assert response["authority_rail"]["dedicated_activation_table"] is True
        assert response["authority_rail"]["active_package_authority_resolver_available"] is True
        assert response["authority_rail"]["raw_local_paths_exposed"] is False
        assert all(ref.startswith("artifact://replacement-package-artifacts/") for ref in response["active_artifact_refs"])
        assert str(tmp_path) not in json.dumps(response["activation_snapshot"], sort_keys=True)

        assert db.query(L3PackageReplacementActivation).count() == 1
        assert db.query(L3ReplacementOutputPackage).count() == 3
        assert db.query(L3OutputPackage).count() == 3
        source_packages_after = [
            (package.output_package_id, package.package_kind, package.payload_ref, package.payload_hash)
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind).all()
        ]
        assert source_packages_after == source_packages_before
        assert {ref: Path(ref).read_bytes() for ref in manifest["verified_artifact_refs"]} == files_before

        resolved = activation_service.resolve_active_replacement_package_authority(db, session_id="session-1")
        assert resolved is not None
        assert resolved["replacement_output_package_ids"] == payload["replacement_output_package_ids"]
        assert resolved["active_artifact_refs"] == response["active_artifact_refs"]

        same_request_replay = activation_service.commit_package_replacement_activation(db, payload)
        assert same_request_replay["status"] == "already_activated"
        same_basis_new_request = activation_service.commit_package_replacement_activation(
            db,
            {**payload, "client_request_id": "req-package-replacement-activation-same-basis"},
        )
        assert same_basis_new_request["status"] == "already_activated"
        assert (
            same_basis_new_request["package_replacement_activation_id"]
            == response["package_replacement_activation_id"]
        )
    finally:
        db.close()
        engine.dispose()


def test_package_replacement_activation_prechecks_fail_closed(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'replacement-activation-prechecks.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, authority, commit, manifest = _record_manifest_chain(db, tmp_path)
        namespaces = _record_namespace_set(db, source=source, authority=authority, commit=commit, manifest=manifest)
        payload = _activation_payload(source=source, authority=authority, commit=commit, manifest=manifest, namespaces=namespaces)
        cases = [
            ({**payload, "package_payload": {"not": "admitted"}}, "package_replacement_activation_scope_not_admitted"),
            (
                {**payload, "operator_decision": "record_replacement_package_namespace"},
                "unsupported_package_replacement_activation_decision",
            ),
            (
                {**payload, "package_kinds": ["canonical_internal"]},
                "package_replacement_activation_package_kinds_mismatch",
            ),
            (
                {**payload, "replacement_activation_basis_hash": "0" * 64},
                "package_replacement_activation_basis_hash_mismatch",
            ),
            (
                {**payload, "source_output_package_ids": list(reversed(payload["source_output_package_ids"]))},
                "package_replacement_activation_replacement_authority_source_output_package_ids_json_mismatch",
            ),
        ]
        for bad_payload, expected_error in cases:
            try:
                activation_service.commit_package_replacement_activation(db, bad_payload)
            except Layer3WorkbenchError as exc:
                assert exc.error_code == expected_error
            else:
                raise AssertionError(f"expected {expected_error}")

        source_package = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id == payload["source_output_package_ids"][0])
            .one()
        )
        source_package.payload_hash = "stale-source-payload-hash"
        db.commit()
        try:
            activation_service.commit_package_replacement_activation(db, payload)
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "package_replacement_activation_source_payload_mismatch"
        else:
            raise AssertionError("expected stale source payload rejection")
    finally:
        db.close()
        engine.dispose()


def test_package_replacement_activation_requires_complete_namespace_set(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'replacement-activation-missing.sqlite'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        source, authority, commit, manifest = _record_manifest_chain(db, tmp_path)
        namespaces = _record_namespace_set(db, source=source, authority=authority, commit=commit, manifest=manifest)
        payload = _activation_payload(source=source, authority=authority, commit=commit, manifest=manifest, namespaces=namespaces)
        db.query(L3ReplacementOutputPackage).filter(
            L3ReplacementOutputPackage.replacement_output_package_id == namespaces[-1]["replacement_output_package_id"]
        ).delete()
        db.commit()

        try:
            activation_service.commit_package_replacement_activation(db, payload)
        except Layer3WorkbenchError as exc:
            assert exc.error_code == "package_replacement_activation_missing_namespace_or_source_rows"
        else:
            raise AssertionError("expected missing namespace rejection")
    finally:
        db.close()
        engine.dispose()
