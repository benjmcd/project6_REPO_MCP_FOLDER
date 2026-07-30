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

import pytest  # noqa: E402

from app.api.deps import get_db  # noqa: E402
from app.core.config import bootstrap_storage_tree, settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.models import (  # noqa: E402
    ConnectorRun,
    ConnectorRunTarget,
    DatasetSourceProvenance,
    L3ConnectorSourceIntakeRecord,
    L3GateBIdempotencyKey,
    L3Session,
)
from app.services import (  # noqa: E402
    layer3_connector_source_intake as connector_intake,
)
from app.services.layer3_connector_source_intake import (  # noqa: E402
    CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
    ConnectorSourceIntakeError,
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
    validate_connector_intake_gate_b_decision_basis,
)
from app.services.layer3_source_intake import (  # noqa: E402
    SourceIntakeError,
    validate_source_intake_gate_b_decision_basis,
)
from main import app  # noqa: E402


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


def _seed_downloaded_sciencebase_target(
    db,
    *,
    content: bytes | None = None,
    public_read_confirmed: bool = True,
) -> tuple[ConnectorRun, ConnectorRunTarget, bytes]:
    blob = content if content is not None else b"site_id,value\nSB-001,42\nSB-002,43\n"
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
        downloaded_sha256=hashlib.sha256(blob).hexdigest(),
        raw_storage_ref=_write_raw_blob(
            run.connector_run_id,
            "target-sciencebase-envelope",
            "water-quality.csv",
            blob,
        ),
        public_read_confirmed=public_read_confirmed,
        status="downloaded",
    )
    db.add(run)
    db.add(target)
    db.commit()
    return run, target, blob


def _seed_strict_sciencebase_target(
    db,
) -> tuple[ConnectorRun, ConnectorRunTarget, bytes]:
    blob = b"county,value\n001,1\n"
    digest = hashlib.sha256(blob).hexdigest()
    raw_dir = Path(settings.connector_raw_dir) / "sha256"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{digest}.csv"
    raw_path.write_bytes(blob)
    run = ConnectorRun(
        connector_run_id="sciencebase-strict-intake-run",
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="sciencebase-strict-intake-target",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id="63d1a3c6d34e06fef15006be",
        sciencebase_item_url=None,
        sciencebase_file_name="mcs2023-germa_salient.csv",
        sciencebase_download_uri=None,
        artifact_surface="files",
        artifact_locator_type="downloadUri_hash_only",
        source_artifact_key=(
            "sciencebase:63d1a3c6d34e06fef15006be:"
            "mcs2023-germa_salient.csv"
        ),
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path.resolve()),
        public_read_confirmed=True,
        status="downloaded",
    )
    db.add_all([run, target])
    db.commit()
    return run, target, blob


def _strict_intake_stager():
    stager = getattr(
        connector_intake,
        "_stage_strict_sciencebase_source_intake",
        None,
    )
    assert stager is not None, "private strict intake stager is missing"
    return stager


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
        assert body["next_state"] == "connector_source_intake_gate_b_admitted"
        assert body["approved_candidate_ids"] == [candidate["candidate_id"]]
        assert body["authority_rail"]["current_gate"] == "gate_b"
        assert body["authority_rail"]["source_authority"]["source_classes"] == [
            CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
        ]
        stored_session = db.get(L3Session, body["session_id"])
        assert stored_session is not None
        assert stored_session.summary_json["current_gate"] == "gate_b"

        summary_response = client.get(f"/api/v1/layer3/session/{body['session_id']}")
        assert summary_response.status_code == 200, summary_response.text
        summary_body = summary_response.json()
        assert summary_body["current_gate"] == "gate_b"
        assert summary_body["authority_rail"]["current_gate"] == "gate_b"

        gate_c_response = client.post(
            "/api/v1/layer3/gate-c/preview",
            json={
                "client_request_id": "sciencebase-envelope-gate-c-readback-001",
                "session_id": body["session_id"],
            },
        )
        assert gate_c_response.status_code == 200, gate_c_response.text
        gate_c_body = gate_c_response.json()
        assert gate_c_body["next_state"] == "connector_source_intake_gate_b_admitted"
        assert gate_c_body["authority_rail"]["current_gate"] == "gate_b"
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


def test_connector_intake_requires_explicit_media_type(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="sciencebase-envelope-record-005",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="ScienceBase missing media type",
                source_description="Downloaded public ScienceBase CSV raw blob.",
                media_type=None,
            )
        assert excinfo.value.code == "connector_source_intake_media_type_required"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_connector_intake_requires_public_read_confirmed(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(
            db,
            public_read_confirmed=False,
        )

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="sciencebase-envelope-record-006",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="ScienceBase private-read CSV",
                source_description="Downloaded ScienceBase CSV raw blob without public-read proof.",
                media_type="text/csv",
            )
        assert excinfo.value.code == "connector_source_intake_public_read_not_confirmed"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_connector_intake_rejects_zero_byte_raw_blob(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db, content=b"")

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="sciencebase-envelope-record-007",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="ScienceBase empty CSV",
                source_description="Downloaded public ScienceBase zero-byte raw blob.",
                media_type="text/csv",
            )
        assert excinfo.value.code == "connector_source_intake_raw_blob_empty"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_connector_gate_b_rejects_raw_storage_reference_aliases(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)
        record = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-008",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase storage alias CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record["connector_source_intake_record_id"],
        )
        candidate = preview["material_candidate"]
        decision_basis = _decision_basis(candidate)
        decision_basis["payload"] = {
            **decision_basis["payload"],
            "raw_storage_ref": target.raw_storage_ref,
            "storage_ref": target.raw_storage_ref,
            "blob_ref": target.raw_storage_ref,
        }

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate["candidate_id"],
                decision_basis=decision_basis,
            )
        assert excinfo.value.code == "connector_source_intake_gate_b_forbidden_field_not_admitted"
        assert excinfo.value.details["blocked_fields"] == [
            "candidate_decisions.decision_basis.payload.blob_ref",
            "candidate_decisions.decision_basis.payload.raw_storage_ref",
            "candidate_decisions.decision_basis.payload.storage_ref",
        ]
    finally:
        db.close()


def test_connector_gate_b_rejects_mixed_case_and_camel_case_forbidden_fields(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)
        record = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-009",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase mixed-case forbidden fields CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record["connector_source_intake_record_id"],
        )
        candidate = preview["material_candidate"]
        decision_basis = _decision_basis(candidate)
        decision_basis["payload"] = {
            **decision_basis["payload"],
            "StorageRef": target.raw_storage_ref,
            "localPath": target.raw_storage_ref,
            "providerUrl": "https://www.sciencebase.gov/catalog/file/get/sb-item-001",
            "rawStorageRef": target.raw_storage_ref,
        }

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate["candidate_id"],
                decision_basis=decision_basis,
            )
        assert excinfo.value.code == "connector_source_intake_gate_b_forbidden_field_not_admitted"
        assert excinfo.value.details["blocked_fields"] == [
            "candidate_decisions.decision_basis.payload.StorageRef",
            "candidate_decisions.decision_basis.payload.localPath",
            "candidate_decisions.decision_basis.payload.providerUrl",
            "candidate_decisions.decision_basis.payload.rawStorageRef",
        ]
    finally:
        db.close()


def test_connector_source_intake_contract_documents_idempotency_axes():
    doc = record_connector_produced_source_intake.__doc__ or ""

    assert "client_request_id" in doc
    assert "authority_basis_hash" in doc
    assert "connector_run_target_id is not unique" in doc


def test_private_strict_intake_stager_flushes_without_committing(client):
    db = client.layer3_session_factory()
    try:
        run, target, content = _seed_strict_sciencebase_target(db)
        record = _strict_intake_stager()(
            db,
            run=run,
            target=target,
        )

        assert record.connector_key == "sciencebase_mcs"
        assert record.connector_run_id == run.connector_run_id
        assert record.connector_run_target_id == target.connector_run_target_id
        assert record.media_type == "text/csv"
        assert record.content_size_bytes == len(content)
        assert record.content_sha256 == hashlib.sha256(content).hexdigest()
        assert record.storage_ref == target.raw_storage_ref
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 1

        db.rollback()
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_private_strict_intake_rejects_open_handle_identity_swap(
    client,
    monkeypatch,
):
    db = client.layer3_session_factory()
    try:
        _, target, _ = _seed_strict_sciencebase_target(db)
        real_fstat = os.fstat
        fstat_calls = 0

        class ChangedFileIdentity:
            def __init__(self, original):
                self._original = original

            @property
            def st_ino(self):
                return int(self._original.st_ino) + 1

            def __getattr__(self, name):
                return getattr(self._original, name)

        def swapped_fstat(fd):
            nonlocal fstat_calls
            current = real_fstat(fd)
            fstat_calls += 1
            if fstat_calls >= 2:
                return ChangedFileIdentity(current)
            return current

        monkeypatch.setattr(os, "fstat", swapped_fstat)

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            connector_intake._hash_file(Path(target.raw_storage_ref))

        assert (
            excinfo.value.code
            == "connector_source_intake_raw_blob_changed"
        )
        assert fstat_calls >= 2
    finally:
        db.close()


def test_private_strict_intake_stager_rejects_duplicate_target_run(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_strict_sciencebase_target(db)
        stager = _strict_intake_stager()
        first = stager(db, run=run, target=target)

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            stager(db, run=run, target=target)

        assert (
            excinfo.value.code
            == "connector_source_intake_strict_cardinality_conflict"
        )
        rows = db.query(L3ConnectorSourceIntakeRecord).all()
        assert rows == [first]
    finally:
        db.rollback()
        db.close()


def test_connector_intake_allows_same_target_with_distinct_request_ids(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)

        first = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-010",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase same target first CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )
        second = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-011",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase same target second CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )

        assert first["connector_source_intake_record_id"] != second["connector_source_intake_record_id"]
        assert (
            db.query(L3ConnectorSourceIntakeRecord)
            .filter(
                L3ConnectorSourceIntakeRecord.connector_run_target_id
                == target.connector_run_target_id
            )
            .count()
            == 2
        )
    finally:
        db.close()


def test_connector_intake_rejects_duplicate_client_request_id(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)
        record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-012",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase duplicate request first CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="sciencebase-envelope-record-012",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="ScienceBase duplicate request second CSV",
                source_description="Downloaded public ScienceBase CSV raw blob.",
                media_type="text/csv",
            )
        assert excinfo.value.code == "connector_source_intake_idempotency_conflict"
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 1
    finally:
        db.close()


def test_connector_gate_b_rejects_payload_connector_identity_tampering(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_downloaded_sciencebase_target(db)
        record = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-envelope-record-013",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase tampered identity CSV",
            source_description="Downloaded public ScienceBase CSV raw blob.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=record["connector_source_intake_record_id"],
        )
        candidate = preview["material_candidate"]
        decision_basis = _decision_basis(candidate)
        decision_basis["payload"] = {
            **decision_basis["payload"],
            "connector_key": "different-connector",
            "connector_run_id": "different-run",
            "connector_run_target_id": "different-target",
        }

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate["candidate_id"],
                decision_basis=decision_basis,
            )
        assert excinfo.value.code == "connector_source_intake_gate_b_payload_mismatch"
        assert excinfo.value.details["blocked_fields"] == [
            "candidate_decisions.decision_basis.payload.connector_key",
            "candidate_decisions.decision_basis.payload.connector_run_id",
            "candidate_decisions.decision_basis.payload.connector_run_target_id",
        ]
    finally:
        db.close()
