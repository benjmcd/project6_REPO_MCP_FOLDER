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
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
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
