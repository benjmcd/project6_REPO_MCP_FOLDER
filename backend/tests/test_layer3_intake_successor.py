"""B1a Option-2 successor split provenance: predecessor blob 8ec90984."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
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
    L3ConnectorSourceIntakeRecord,
)
from app.services import (  # noqa: E402
    layer3_connector_source_intake as connector_intake,
)
from app.services.layer3_connector_source_intake import (  # noqa: E402
    CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
    STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS,
    ConnectorSourceIntakeError,
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
    validate_connector_intake_gate_b_decision_basis,
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
    session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )

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


def _decision_basis(candidate: dict) -> dict:
    return {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": candidate["source_identity"],
        "source_provenance": candidate["source_provenance"],
        "payload": candidate["payload"],
        "load_summary": candidate["load_summary"],
    }


def _seed_generic_sciencebase_target(
    db,
) -> tuple[ConnectorRun, ConnectorRunTarget, bytes]:
    blob = b"site_id,value\nSB-001,42\nSB-002,43\n"
    digest = hashlib.sha256(blob).hexdigest()
    raw_dir = Path(settings.connector_raw_dir) / "generic"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "water-quality.csv"
    raw_path.write_bytes(blob)
    run = ConnectorRun(
        connector_run_id="sciencebase-generic-successor-run",
        connector_key="sciencebase-public",
        source_system="sciencebase",
        source_mode="public_api",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="sciencebase-generic-successor-target",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id="sb-item-successor",
        sciencebase_item_url=(
            "https://www.sciencebase.gov/catalog/item/sb-item-successor"
        ),
        sciencebase_file_name="water-quality.csv",
        sciencebase_download_uri=(
            "https://www.sciencebase.gov/catalog/file/get/sb-item-successor"
        ),
        artifact_surface="files",
        artifact_locator_type="download_uri",
        source_artifact_key=(
            "sciencebase://sb-item-successor/water-quality.csv"
        ),
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path),
        public_read_confirmed=True,
        status="downloaded",
    )
    db.add_all([run, target])
    db.commit()
    return run, target, blob


def test_generic_sciencebase_cannot_spoof_strict_gate_c_authority(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_generic_sciencebase_target(db)
        record = record_connector_produced_source_intake(
            db,
            client_request_id="sciencebase-generic-successor-record",
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            source_label="ScienceBase generic successor CSV",
            source_description="Generic public ScienceBase successor coverage.",
            media_type="text/csv",
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=(
                record["connector_source_intake_record_id"]
            ),
        )
        candidate = preview["material_candidate"]
        decision_basis = deepcopy(_decision_basis(candidate))
        decision_basis["connector_target"] = {
            "connector_run_target_id": target.connector_run_target_id,
            "connector_key": run.connector_key,
        }
        assert (
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate["candidate_id"],
                decision_basis=decision_basis,
            )
            == CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
        )

        spoofed_basis = deepcopy(decision_basis)
        spoofed_basis["payload"]["source_class"] = (
            STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
        )
        with pytest.raises(ConnectorSourceIntakeError) as spoofed:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=candidate["candidate_id"],
                decision_basis=spoofed_basis,
            )
        assert (
            spoofed.value.code
            == "connector_source_intake_gate_b_payload_mismatch"
        )

        gate_b = client.post(
            "/api/v1/layer3/gate-b/decision",
            json={
                "client_request_id": "sciencebase-generic-successor-gate-b",
                "preflight_id": "sciencebase-generic-successor-preflight",
                "source_set_id": "sciencebase-generic-successor-source-set",
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
        assert gate_b.status_code == 200, gate_b.text
        body = gate_b.json()
        assert body["next_state"] == "connector_source_intake_gate_b_admitted"
        blocked_gate_c = client.post(
            "/api/v1/layer3/gate-c/preview",
            json={
                "client_request_id": "sciencebase-generic-successor-gate-c",
                "session_id": body["session_id"],
                "commit_typing": True,
            },
        )
        assert blocked_gate_c.status_code == 409, blocked_gate_c.text
        assert blocked_gate_c.json()["error_code"] == "typing_not_ready"
    finally:
        db.close()


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
        with pytest.raises(ConnectorSourceIntakeError) as preview_error:
            connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=(
                    record.connector_source_intake_record_id
                ),
            )
        assert (
            preview_error.value.code
            == "connector_source_intake_preview_origin_receipt_missing"
        )
        with pytest.raises(ConnectorSourceIntakeError) as gate_error:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=(
                    "mat-connector_source_intake_record-"
                    f"{record.connector_source_intake_record_id}"
                ),
                decision_basis={},
            )
        assert (
            gate_error.value.code
            == "connector_source_intake_gate_b_origin_receipt_missing"
        )
        record.connector_key = "tampered-strict-shape"
        with pytest.raises(ConnectorSourceIntakeError) as strict_shape_error:
            connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=(
                    record.connector_source_intake_record_id
                ),
            )
        assert (
            strict_shape_error.value.code
            == "connector_source_intake_preview_strict_shape_invalid"
        )

        db.rollback()
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_strict_sciencebase_intake_builder_has_acyclic_pre_post_projection(
    client,
):
    db = client.layer3_session_factory()
    try:
        run, target, content = _seed_strict_sciencebase_target(db)
        digest = hashlib.sha256(content).hexdigest()
        builder = getattr(
            connector_intake,
            "_strict_sciencebase_intake_values",
        )
        builder_inputs = {
            "connector_key": run.connector_key,
            "connector_run_id": run.connector_run_id,
            "connector_run_target_id": target.connector_run_target_id,
            "raw_storage_ref": str(target.raw_storage_ref),
            "freshness_timestamp": target.downloaded_at,
            "content_size_bytes": len(content),
            "content_sha256": digest,
        }
        pre_mint = builder(
            **builder_inputs,
            connector_origin_receipt_hash=None,
        )
        projection = {
            "connector_run_target_id": target.connector_run_target_id,
            "connector_origin_receipt_hash": "a" * 64,
        }
        post_mint = builder(
            **builder_inputs,
            connector_origin_receipt_hash=(
                projection["connector_origin_receipt_hash"]
            ),
        )

        assert pre_mint["content_sha256"] == post_mint["content_sha256"]
        assert pre_mint["content_size_bytes"] == post_mint["content_size_bytes"]
        assert pre_mint["storage_ref"] == post_mint["storage_ref"]
        assert pre_mint["metadata_hash"] != post_mint["metadata_hash"]
        assert pre_mint["authority_basis_hash"] != post_mint["authority_basis_hash"]
        assert pre_mint["provenance_json"] != post_mint["provenance_json"]
        assert pre_mint["summary_json"] != post_mint["summary_json"]
        for values in (
            post_mint["provenance_json"],
            post_mint["summary_json"]["metadata"],
            post_mint["summary_json"]["authority_basis"],
        ):
            assert values["connector_run_target_id"] == (
                projection["connector_run_target_id"]
            )
            assert values["connector_origin_receipt_hash"] == (
                projection["connector_origin_receipt_hash"]
            )
        assert "url" not in json.dumps(post_mint).lower()
        assert projection == {
            "connector_run_target_id": target.connector_run_target_id,
            "connector_origin_receipt_hash": "a" * 64,
        }
    finally:
        db.close()


def test_reserved_sciencebase_rejects_all_intake_signal_downgrade(client):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_strict_sciencebase_target(db)
        record = _strict_intake_stager()(
            db,
            run=run,
            target=target,
        )
        record.client_request_id = "generic-downgrade"
        record.connector_key = "generic-sciencebase"
        record.source_label = "Generic CSV"
        record.source_description = "Generic intake"
        record.original_filename = "generic.csv"
        db.commit()

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=(
                    record.connector_source_intake_record_id
                ),
            )
        assert (
            excinfo.value.code
            == "connector_source_intake_preview_strict_shape_invalid"
        )
    finally:
        db.close()


def test_reserved_sciencebase_rejects_forged_self_consistent_projection(
    client,
    monkeypatch,
):
    from app.services import layer3_origin_continuity as origin

    db = client.layer3_session_factory()
    try:
        run, target, content = _seed_strict_sciencebase_target(db)
        record = _strict_intake_stager()(
            db,
            run=run,
            target=target,
        )
        forged_hash = "f" * 64
        forged = connector_intake._strict_sciencebase_intake_values(
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            raw_storage_ref=str(target.raw_storage_ref),
            freshness_timestamp=record.freshness_timestamp,
            content_size_bytes=len(content),
            content_sha256=hashlib.sha256(content).hexdigest(),
            connector_origin_receipt_hash=forged_hash,
        )
        for field in (
            "metadata_hash",
            "authority_basis_hash",
            "provenance_json",
            "summary_json",
        ):
            setattr(record, field, forged[field])
        db.commit()
        calls: list[str] = []

        def verified_projection(
            verify_db,
            *,
            connector_run_target_id: str,
        ) -> dict[str, str]:
            assert verify_db is db
            calls.append(connector_run_target_id)
            return {
                "connector_run_target_id": connector_run_target_id,
                "connector_origin_receipt_hash": "a" * 64,
            }

        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            verified_projection,
        )
        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=(
                    record.connector_source_intake_record_id
                ),
            )
        assert (
            excinfo.value.code
            == "connector_source_intake_preview_origin_receipt_missing"
        )
        assert calls == [target.connector_run_target_id]
    finally:
        db.close()


def test_generic_creation_is_blocked_on_reserved_strict_sciencebase_target(
    client,
):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_strict_sciencebase_target(db)
        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            record_connector_produced_source_intake(
                db,
                client_request_id="generic-sciencebase-mcs-record",
                connector_key=run.connector_key,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                source_label="Generic ScienceBase MCS CSV",
                source_description="Generic/manual intake is reserved here.",
                media_type="text/csv",
            )
        assert (
            excinfo.value.code
            == "connector_source_intake_reserved_strict_lane"
        )
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
    finally:
        db.close()


def test_orphaned_strict_sciencebase_intake_fails_preview_and_gate_b(
    client,
):
    db = client.layer3_session_factory()
    try:
        run, target, _ = _seed_strict_sciencebase_target(db)
        record = _strict_intake_stager()(
            db,
            run=run,
            target=target,
        )
        record_id = record.connector_source_intake_record_id
        db.delete(target)
        db.commit()

        with pytest.raises(ConnectorSourceIntakeError) as preview_error:
            connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=record_id,
            )
        assert (
            preview_error.value.code
            == "connector_source_intake_preview_reserved_authority_invalid"
        )

        with pytest.raises(ConnectorSourceIntakeError) as gate_error:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=(
                    f"mat-connector_source_intake_record-{record_id}"
                ),
                decision_basis={},
            )
        assert (
            gate_error.value.code
            == "connector_source_intake_gate_b_reserved_authority_invalid"
        )
    finally:
        db.close()


def test_gate_b_rejects_hidden_conflicting_origin_claim(
    client,
    monkeypatch,
):
    from app.services import layer3_origin_continuity as origin

    db = client.layer3_session_factory()
    try:
        run, target, content = _seed_strict_sciencebase_target(db)
        record = _strict_intake_stager()(
            db,
            run=run,
            target=target,
        )
        canonical_hash = "a" * 64
        projected = connector_intake._strict_sciencebase_intake_values(
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=target.connector_run_target_id,
            raw_storage_ref=str(target.raw_storage_ref),
            freshness_timestamp=record.freshness_timestamp,
            content_size_bytes=len(content),
            content_sha256=hashlib.sha256(content).hexdigest(),
            connector_origin_receipt_hash=canonical_hash,
        )
        for field in (
            "metadata_hash",
            "authority_basis_hash",
            "provenance_json",
            "summary_json",
        ):
            setattr(record, field, projected[field])
        db.commit()
        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            lambda *args, **kwargs: {
                "connector_run_target_id": target.connector_run_target_id,
                "connector_origin_receipt_hash": canonical_hash,
            },
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=(
                record.connector_source_intake_record_id
            ),
        )
        decision_basis = _decision_basis(preview["material_candidate"])
        decision_basis["source_identity"]["hidden"] = {
            "connector_run_target_id": target.connector_run_target_id,
            "connector_origin_receipt_hash": "f" * 64,
        }

        with pytest.raises(ConnectorSourceIntakeError) as excinfo:
            validate_connector_intake_gate_b_decision_basis(
                db,
                candidate_id=preview["material_candidate"]["candidate_id"],
                decision_basis=decision_basis,
            )
        assert (
            excinfo.value.code
            == "connector_source_intake_gate_b_basis_mismatch"
        )
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
