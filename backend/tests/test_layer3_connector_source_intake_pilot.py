from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import pytest

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    ConnectorRun,
    ConnectorRunTarget,
    DatasetSourceProvenance,
    L3ConnectorSourceIntakeRecord,
    L3GateBIdempotencyKey,
)
from app.services.layer3_connector_source_intake import (
    CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
    ConnectorSourceIntakeError,
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
    validate_connector_intake_gate_b_decision_basis,
)
from app.services.layer3_source_intake import (
    SourceIntakeError,
    validate_source_intake_gate_b_decision_basis,
)
from main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.layer3_session_factory = session_local
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _write_raw_blob(run_id: str, target_id: str, file_name: str, content: bytes) -> str:
    out_dir = Path(settings.connector_raw_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{target_id}_{file_name}"
    out.write_bytes(content)
    return str(out)


def _seed_downloaded_sciencebase_target(db) -> tuple[ConnectorRun, ConnectorRunTarget, bytes]:
    content = b"site_id,value\nSB-001,42\nSB-002,43\n"
    run = ConnectorRun(
        connector_run_id="run-sciencebase-envelope",
        connector_key="sciencebase-public",
        source_system="sciencebase",
        source_mode="public_api",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-sciencebase-envelope",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id="sb-item-001",
        sciencebase_item_url="https://www.sciencebase.gov/catalog/item/sb-item-001",
        sciencebase_file_name="water-quality.csv",
        sciencebase_download_uri="https://www.sciencebase.gov/catalog/file/get/sb-item-001",
        artifact_surface="files",
        artifact_locator_type="download_uri",
        source_artifact_key="sciencebase://sb-item-001/water-quality.csv",
        downloaded_sha256=hashlib.sha256(content).hexdigest(),
        raw_storage_ref=_write_raw_blob(
            run.connector_run_id,
            "target-sciencebase-envelope",
            "water-quality.csv",
            content,
        ),
        status="downloaded",
    )
    db.add(run)
    db.add(target)
    db.commit()
    return run, target, content


def _decision_basis(candidate: dict, *, include_connector_target: bool = False) -> dict:
    basis = {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": candidate["source_identity"],
        "source_provenance": candidate["source_provenance"],
        "payload": candidate["payload"],
        "load_summary": candidate["load_summary"],
    }
    if include_connector_target:
        basis["connector_target"] = {
            "connector_run_target_id": candidate["payload"]["connector_run_target_id"],
            "connector_key": "sciencebase-public",
        }
    return basis


def test_sciencebase_csv_connector_intake_reaches_gate_b_through_existing_route(client):
    db = client.layer3_session_factory()
    try:
        run, target, content = _seed_downloaded_sciencebase_target(db)

        record_response = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-001",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase water-quality CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )
        record_id = record_response["connector_source_intake_record_id"]
        record = db.get(L3ConnectorSourceIntakeRecord, record_id)

        assert record is not None
        assert record.connector_key == "sciencebase-public"
        assert record.connector_run_id == run.connector_run_id
        assert record.connector_run_target_id == target.connector_run_target_id
        assert record.content_sha256 == hashlib.sha256(content).hexdigest()
        assert record.content_sha256 == target.downloaded_sha256
        assert record.original_filename == "water-quality.csv"
        assert record.source_family == CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
        assert record.metadata_hash
        assert record.authority_basis_hash
        assert (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.connector_run_id == run.connector_run_id)
            .count()
            == 0
        )

        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record_id,
        )
        candidate = preview["material_candidate"]
        assert candidate["candidate_id"] == f"mat-connector_source_intake_record-{record_id}"
        assert candidate["source_class"] == CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
        assert candidate["payload"]["connector_source_intake_record_id"] == record_id
        assert candidate["payload"]["connector_run_target_id"] == target.connector_run_target_id
        assert "SB-001,42" in candidate["preview_text"]
        assert preview["material_preview_hash"]

        decision_basis = _decision_basis(candidate, include_connector_target=True)
        response = client.post(
            "/api/v1/layer3/gate-b/decision",
            json={
                "client_request_id": "sciencebase-envelope-gate-b-001",
                "preflight_id": "sciencebase-envelope-preflight",
                "source_set_id": "sciencebase-envelope-source-set",
                "material_preview_id": preview["material_preview_id"],
                "material_preview_hash": preview["material_preview_hash"],
                "candidate_decisions": [
                    {
                        "candidate_id": candidate["candidate_id"],
                        "decision": "approved",
                        "decision_basis": decision_basis,
                    }
                ],
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ok"
        assert body["next_state"] == "gate_c_preview_ready"
        assert body["approved_candidate_ids"] == [candidate["candidate_id"]]
        assert body["authority_rail"]["current_gate"] == "gate_c"
        assert body["authority_rail"]["source_authority"]["source_classes"] == [
            CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
        ]
        assert (
            db.query(L3GateBIdempotencyKey)
            .filter(L3GateBIdempotencyKey.client_request_id == "sciencebase-envelope-gate-b-001")
            .count()
            == 1
        )
    finally:
        db.close()


def test_connector_basis_does_not_weaken_operator_intake_gate_b_invariant(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)
        record = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-002",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase invariant CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record["connector_source_intake_record_id"],
        )
        candidate = preview["material_candidate"]
        decision_basis = _decision_basis(candidate, include_connector_target=True)

        validate_connector_intake_gate_b_decision_basis(
            db,
            candidate_id=candidate["candidate_id"],
            decision_basis=decision_basis,
        )

        with pytest.raises(SourceIntakeError) as excinfo:
            validate_source_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate["candidate_id"],
                decision_basis=decision_basis,
            )
        assert excinfo.value.code == "source_intake_gate_b_forbidden_field_not_admitted"
        assert (
            "candidate_decisions.decision_basis.connector_target"
            in excinfo.value.details["blocked_fields"]
        )
    finally:
        db.close()


def test_connector_intake_rejects_unusable_sciencebase_file_name(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)
        target.sciencebase_file_name = None
        db.commit()

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="sciencebase-envelope-record-003",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="ScienceBase bad filename CSV",
                source_description="Downloaded public ScienceBase CSV raw blob.",
                media_type="text/csv",
            )
        assert excinfo.value.code == "connector_source_intake_unusable_file_name"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_connector_intake_rejects_media_type_widening(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="sciencebase-envelope-record-004",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="ScienceBase non-CSV source",
                source_description="Downloaded public ScienceBase raw blob.",
                media_type="text/plain",
            )
        assert excinfo.value.code == "connector_source_intake_media_type_not_admitted"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()
