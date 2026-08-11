from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
import threading

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import Settings, bootstrap_storage_tree, settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.models import (  # noqa: E402
    ConnectorRun,
    ConnectorRunTarget,
    L3ConnectorSourceIntakeRecord,
)
from app.services.layer3_connector_source_intake import (  # noqa: E402
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
)
from app.services.layer3_workbench import gate_b_decision  # noqa: E402
from app.services.layer3_workbench_error import Layer3WorkbenchError  # noqa: E402


ALEMBIC_INI = BACKEND / "alembic.ini"
RAW_BYTES = b"site_id,value\nSB-001,42\nSB-002,43\n"


def _run_alembic(url: str, operation, revision: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(BACKEND / "alembic"))
        config.set_main_option("sqlalchemy.url", url)
        operation(config, revision)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture()
def db(tmp_path, monkeypatch):
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
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_candidate(db, *, suffix: str = "one", public_read: bool = True):
    run_id = f"run-{suffix}"
    target_id = f"target-{suffix}"
    raw_dir = Path(settings.connector_raw_dir) / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{target_id}_water-quality.csv"
    raw_path.write_bytes(RAW_BYTES)
    digest = hashlib.sha256(RAW_BYTES).hexdigest()
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="sciencebase_public",
        source_system="sciencebase",
        source_mode="synthetic_local_direct_intake",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        sciencebase_item_id="synthetic-sb-item-001",
        sciencebase_file_name="water-quality.csv",
        artifact_surface="synthetic_fixture",
        artifact_locator_type="intake_storage_ref",
        source_artifact_key="f07-c01-synthetic",
        downloaded_sha256=digest,
        raw_storage_ref=str(raw_path),
        public_read_confirmed=public_read,
        status="downloaded",
    )
    db.add_all([run, target])
    db.commit()
    recorded = record_connector_produced_source_intake(
        db,
        client_request_id=f"intake-{suffix}",
        connector_key=run.connector_key,
        connector_run_id=run_id,
        connector_run_target_id=target_id,
        source_label="Synthetic exact connector source",
        source_description="A0 identity fixture.",
        media_type="text/csv",
    )
    preview = connector_source_intake_material_preview(
        db,
        connector_source_intake_record_id=recorded["connector_source_intake_record_id"],
    )
    return db.get(L3ConnectorSourceIntakeRecord, recorded["connector_source_intake_record_id"]), preview


def _gate_b_payload(preview: dict, *, request_id: str) -> dict:
    candidate = preview["material_candidate"]
    return {
        "client_request_id": request_id,
        "preflight_id": "a0-preflight",
        "source_set_id": "a0-source-set",
        "material_preview_id": preview["material_preview_id"],
        "material_preview_hash": preview["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": {
                    key: candidate[key]
                    for key in (
                        "source_ref",
                        "query_basis",
                        "provenance_ref",
                        "source_identity",
                        "source_provenance",
                        "payload",
                        "load_summary",
                    )
                },
            }
        ],
    }


def test_flag_defaults_false_and_honors_alias(monkeypatch):
    monkeypatch.delenv("LAYER3_CONNECTOR_PROMOTION_IDENTITY_ENABLED", raising=False)
    assert Settings(_env_file=None).layer3_connector_promotion_identity_enabled is False
    monkeypatch.setenv("LAYER3_CONNECTOR_PROMOTION_IDENTITY_ENABLED", "true")
    assert Settings(_env_file=None).layer3_connector_promotion_identity_enabled is True


def test_migration_adds_identity_pair_receipt_and_safe_downgrade(tmp_path):
    db_path = tmp_path / "a0.db"
    url = f"sqlite:///{db_path.as_posix()}"
    _run_alembic(url, command.upgrade, "0056_layer3_connector_source_intake_record")
    _run_alembic(url, command.upgrade, "head")
    engine = create_engine(url)
    schema = inspect(engine)
    intake_columns = {column["name"] for column in schema.get_columns("l3_connector_source_intake_record")}
    assert {"identity_metadata_hash_version", "identity_metadata_hash"} <= intake_columns
    assert schema.has_table("l3_connector_promotion_receipt")
    receipt_uniques = {tuple(item["column_names"]) for item in schema.get_unique_constraints("l3_connector_promotion_receipt")}
    assert (
        "identity_metadata_hash_version",
        "source_family",
        "content_sha256",
        "identity_metadata_hash",
    ) in receipt_uniques
    foreign_targets = {
        (tuple(item["constrained_columns"]), item["referred_table"], tuple(item["referred_columns"]))
        for item in schema.get_foreign_keys("l3_connector_promotion_receipt")
    }
    assert (("connector_source_intake_record_id",), "l3_connector_source_intake_record", ("connector_source_intake_record_id",)) in foreign_targets
    assert (("gate_b_session_id",), "l3_session", ("session_id",)) in foreign_targets
    assert (("gate_b_selection_manifest_id",), "l3_selection_manifest", ("selection_manifest_id",)) in foreign_targets
    assert (("gate_b_material_snapshot_id",), "l3_material_snapshot", ("material_snapshot_id",)) in foreign_targets
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO l3_connector_promotion_receipt "
                "(connector_promotion_receipt_id, receipt_schema_version, identity_metadata_hash_version, "
                "source_family, content_sha256, identity_metadata_hash, canonical_identity_key_hash, "
                "connector_source_intake_record_id, gate_b_session_id, gate_b_selection_manifest_id, "
                "gate_b_material_snapshot_id, gate_b_decision_manifest_id, gate_b_decision_manifest_hash, "
                "material_preview_hash, approval_hash, promotion_basis_hash, created_at) VALUES "
                "('r', 'layer3.connector_promotion_receipt.v1', 'v1', 'family', :h, :h, :h, "
                "'i', 's', 'm', 'x', 'd', :h, :h, :h, :h, CURRENT_TIMESTAMP)"
            ),
            {"h": "a" * 64},
        )
    with pytest.raises(RuntimeError, match="receipt rows exist"):
        _run_alembic(url, command.downgrade, "0056_layer3_connector_source_intake_record")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM l3_connector_promotion_receipt"))
    engine.dispose()
    _run_alembic(url, command.downgrade, "0056_layer3_connector_source_intake_record")
    downgraded = create_engine(url)
    assert not inspect(downgraded).has_table("l3_connector_promotion_receipt")
    downgraded.dispose()


def test_deterministic_server_identity_uses_durable_rows(db):
    record, preview = _seed_candidate(db)
    from app.services.layer3_connector_promotion_identity import derive_candidate_identity

    first = derive_candidate_identity(db, preview["material_candidate"])
    second = derive_candidate_identity(db, preview["material_candidate"])
    assert first == second
    assert first.connector_source_intake_record_id == record.connector_source_intake_record_id
    assert len(first.identity_metadata_hash) == 64
    assert len(first.canonical_identity_key_hash) == 64


def test_flag_false_preserves_gate_b_without_a0_mutation(db, monkeypatch):
    record, preview = _seed_candidate(db)
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", False)
    response = gate_b_decision(db, _gate_b_payload(preview, request_id="gate-b-disabled"))
    db.refresh(record)
    assert response["status"] == "ok"
    assert "connector_promotion_receipt" not in response
    assert record.identity_metadata_hash_version is None
    assert record.identity_metadata_hash is None
    assert db.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 0


def test_flag_false_preserves_raw_database_error(db, monkeypatch):
    _record, preview = _seed_candidate(db)
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", False)
    from app.services import layer3_workbench

    def fail_claim(*args, **kwargs):
        raise IntegrityError("legacy statement", {}, RuntimeError("legacy db failure"))

    monkeypatch.setattr(layer3_workbench, "claim_gate_b_idempotency", fail_claim)
    with pytest.raises(IntegrityError, match="legacy db failure"):
        gate_b_decision(db, _gate_b_payload(preview, request_id="gate-b-disabled-db-error"))


def test_flag_true_rejects_multi_candidate_connector_shape_without_mutation(db, monkeypatch):
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    first_record, first_preview = _seed_candidate(db, suffix="shape-one")
    second_record, second_preview = _seed_candidate(db, suffix="shape-two")
    payload = _gate_b_payload(first_preview, request_id="gate-b-invalid-shape")
    payload["candidate_decisions"].extend(
        _gate_b_payload(second_preview, request_id="unused")["candidate_decisions"]
    )
    payload["material_preview_hash"] = ""

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        gate_b_decision(db, payload)

    assert excinfo.value.error_code == "connector_promotion_invalid_shape"
    db.refresh(first_record)
    db.refresh(second_record)
    assert first_record.identity_metadata_hash_version is None
    assert first_record.identity_metadata_hash is None
    assert second_record.identity_metadata_hash_version is None
    assert second_record.identity_metadata_hash is None
    for table_name in (
        "l3_session",
        "l3_selection_manifest",
        "l3_material_snapshot",
        "l3_connector_promotion_receipt",
    ):
        assert db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one() == 0


def test_flag_true_creates_receipt_and_same_request_reuses(db, monkeypatch):
    record, preview = _seed_candidate(db)
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    db.rollback()
    payload = _gate_b_payload(preview, request_id="gate-b-enabled")
    created = gate_b_decision(db, payload)
    replayed = gate_b_decision(db, payload)
    db.refresh(record)
    assert created["connector_promotion_receipt"]["receipt_disposition"] == "created"
    assert replayed["connector_promotion_receipt"]["receipt_disposition"] == "reused"
    assert created["connector_promotion_receipt"]["connector_promotion_receipt_id"] == replayed["connector_promotion_receipt"]["connector_promotion_receipt_id"]
    assert record.identity_metadata_hash_version
    assert record.identity_metadata_hash
    assert db.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 1
    db.execute(
        text("UPDATE l3_connector_promotion_receipt SET promotion_basis_hash = :hash"),
        {"hash": "f" * 64},
    )
    db.commit()
    with pytest.raises(Layer3WorkbenchError) as divergent:
        gate_b_decision(db, payload)
    assert divergent.value.error_code == "connector_promotion_identity_conflict"


def test_near_miss_and_distinct_request_fail_closed(db, monkeypatch):
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    record, preview = _seed_candidate(db)
    db.get(ConnectorRunTarget, record.connector_run_target_id).public_read_confirmed = False
    db.commit()
    with pytest.raises(Layer3WorkbenchError) as near_miss:
        gate_b_decision(db, _gate_b_payload(preview, request_id="gate-b-near-miss"))
    assert near_miss.value.error_code == "connector_promotion_not_eligible"
    assert db.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 0
    db.rollback()
    db.get(ConnectorRunTarget, record.connector_run_target_id).public_read_confirmed = True
    db.commit()
    first = gate_b_decision(db, _gate_b_payload(preview, request_id="gate-b-first"))
    assert first["connector_promotion_receipt"]["receipt_disposition"] == "created"
    with pytest.raises(Layer3WorkbenchError) as duplicate:
        gate_b_decision(db, _gate_b_payload(preview, request_id="gate-b-distinct"))
    assert duplicate.value.error_code == "connector_promotion_identity_conflict"
    denied = _gate_b_payload(preview, request_id="gate-b-denied")
    denied["candidate_decisions"][0]["decision"] = "denied"
    denied["candidate_decisions"][0]["operator_reason"] = "operator denied"
    with pytest.raises(Layer3WorkbenchError) as decision_conflict:
        gate_b_decision(db, denied)
    assert decision_conflict.value.error_code == "connector_promotion_identity_conflict"
    assert db.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 1


def test_failure_after_staging_rolls_back_gate_b_and_a0(db, monkeypatch):
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    record, preview = _seed_candidate(db)
    db.rollback()
    from app.services import layer3_connector_promotion_identity as identity_service

    original = identity_service.stage_promotion_receipt

    def fail_after_stage(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected before commit")

    monkeypatch.setattr(identity_service, "stage_promotion_receipt", fail_after_stage)
    with pytest.raises(RuntimeError, match="injected before commit"):
        gate_b_decision(db, _gate_b_payload(preview, request_id="gate-b-rollback"))
    db.rollback()
    db.refresh(record)
    assert record.identity_metadata_hash_version is None
    assert record.identity_metadata_hash is None
    assert db.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 0
    assert db.execute(text("SELECT COUNT(*) FROM l3_session")).scalar_one() == 0


def _file_sessions(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'a0-lock.db').as_posix()}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 0.2},
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, future=True)


def test_concurrent_independent_sessions_yield_one_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    engine, factory = _file_sessions(tmp_path, monkeypatch)
    seed = factory()
    try:
        record, first_preview = _seed_candidate(seed)
        second = record_connector_produced_source_intake(
            seed,
            client_request_id="intake-two",
            connector_key=record.connector_key,
            connector_run_id=record.connector_run_id,
            connector_run_target_id=record.connector_run_target_id,
            source_label="Same canonical identity, distinct intake",
            source_description="Concurrent A0 arbitration fixture.",
            media_type="text/csv",
        )
        second_preview = connector_source_intake_material_preview(
            seed,
            connector_source_intake_record_id=second["connector_source_intake_record_id"],
        )
    finally:
        seed.rollback()
        seed.close()

    barrier = threading.Barrier(2)

    def submit(preview, request_id):
        session = factory()
        try:
            barrier.wait(timeout=5)
            result = gate_b_decision(session, _gate_b_payload(preview, request_id=request_id))
            return "ok", result["connector_promotion_receipt"]["receipt_disposition"]
        except Layer3WorkbenchError as exc:
            return "error", exc.error_code
        finally:
            session.rollback()
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda args: submit(*args),
                ((first_preview, "gate-b-race-one"), (second_preview, "gate-b-race-two")),
            )
        )
    assert sorted(outcomes) == [
        ("error", "connector_promotion_identity_conflict"),
        ("ok", "created"),
    ]
    verify = factory()
    try:
        assert verify.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 1
        assert verify.execute(text("SELECT COUNT(*) FROM l3_session")).scalar_one() == 1
    finally:
        verify.close()
        engine.dispose()


def test_sqlite_identity_lock_timeout_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "layer3_connector_promotion_identity_enabled", True)
    engine, factory = _file_sessions(tmp_path, monkeypatch)
    seed = factory()
    try:
        _record, preview = _seed_candidate(seed)
    finally:
        seed.rollback()
        seed.close()
    locker = factory()
    contender = factory()
    try:
        locker.execute(text("BEGIN IMMEDIATE"))
        with pytest.raises(Layer3WorkbenchError) as excinfo:
            gate_b_decision(contender, _gate_b_payload(preview, request_id="gate-b-lock-timeout"))
        assert excinfo.value.error_code == "connector_promotion_identity_lock_unavailable"
        contender.rollback()
        assert contender.execute(text("SELECT COUNT(*) FROM l3_connector_promotion_receipt")).scalar_one() == 0
        assert contender.execute(text("SELECT COUNT(*) FROM l3_session")).scalar_one() == 0
    finally:
        locker.rollback()
        contender.rollback()
        locker.close()
        contender.close()
        engine.dispose()
