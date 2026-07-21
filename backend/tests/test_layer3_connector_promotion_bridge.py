"""B1b connector promotion bridge — B1b-01 schema-foundation tests.

Covers the owner-bound Option II receipt DDL and the bridge feature flag:
- LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED defaults to False
- nullable intake identity pair, joint-null check, non-unique lookup index
- no-backfill upgrade and flag-false intake-path inertness
- receipt-aware downgrade refusal and clean dependency-ordered downgrade
- migrated SQLite schema: exact 23-column receipt table, D33 four-column
  unique tuple, receipt-schema pin check, joint-state check, 7 indexes
- joint-state semantics: the three valid states insert; invalid mixtures fail
- unique-tuple enforcement and schema-version pin enforcement

FK parent scaffolding is deliberately out of scope here: SQLite leaves
foreign_keys OFF by default on these connections, which lets this suite
exercise the B1b-01 check/uniqueness semantics without seeding Gate-B
parents. The FK *DDL shape* (exact targets, columns, and ON DELETE
RESTRICT) IS asserted here via reflection; runtime FK *enforcement*
belongs to the later service-level tests (test_layer3_migrations.py's
parity check covers table/column presence only, not FK behavior).
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from alembic.config import Config  # noqa: E402
from alembic import command  # noqa: E402
import main  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.models import (  # noqa: E402
    AnalysisArtifact,
    AnalysisRun,
    AssumptionCheck,
    CaveatNote,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetRow,
    DatasetSourceProvenance,
    DatasetVersion,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3Descriptor,
    L3GateBIdempotencyKey,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    SourceConnector,
    VariableDefinition,
)
from app.api.layer3 import Layer3PlanApprovalRequest, Layer3PlanPreviewRequest  # noqa: E402
from app.services.layer3_connector_source_intake import (  # noqa: E402
    connector_source_intake_material_preview,
    record_connector_produced_source_intake,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError  # noqa: E402
from app.services import layer3_pass_entry  # noqa: E402
from app.services import layer3_workbench  # noqa: E402
from app.services.layer3_utils import stable_hash, stable_json_bytes  # noqa: E402

ALEMBIC_INI = BACKEND / "alembic.ini"

TABLE = "l3_connector_promotion_receipt"
INTAKE_TABLE = "l3_connector_source_intake_record"
INTAKE_IDENTITY_CHECK = "ck_l3_connector_source_intake_identity_metadata_joint_null"
INTAKE_IDENTITY_INDEX = "ix_l3_connector_intake_material_identity"
INTAKE_IDENTITY_COLUMNS = ["identity_metadata_hash_version", "identity_metadata_hash"]
RECEIPT_SCHEMA_VERSION = "layer3.connector_promotion_receipt.v1"

EXPECTED_COLUMNS = [
    "connector_promotion_receipt_id",
    "receipt_schema_version",
    "identity_metadata_hash_version",
    "source_family",
    "content_sha256",
    "identity_metadata_hash",
    "canonical_identity_key_hash",
    "connector_source_intake_record_id",
    "gate_b_session_id",
    "gate_b_selection_manifest_id",
    "gate_b_material_snapshot_id",
    "gate_b_decision_manifest_id",
    "gate_b_decision_manifest_hash",
    "material_preview_hash",
    "approval_hash",
    "promotion_basis_hash",
    "dataset_id",
    "dataset_version_id",
    "promoted_session_id",
    "materialization_status",
    "materialization_basis_hash",
    "created_at",
    "materialized_at",
]

BASE_INTAKE_COLUMNS = [
    "connector_source_intake_record_id",
    "client_request_id",
    "operator_decision",
    "source_family",
    "source_label",
    "source_description",
    "original_filename",
    "media_type",
    "content_size_bytes",
    "content_sha256",
    "metadata_hash",
    "authority_basis_hash",
    "storage_ref",
    "freshness_timestamp",
    "provenance_json",
    "downstream_eligibility_json",
    "summary_json",
    "status",
    "created_at",
    "updated_at",
    "connector_key",
    "connector_run_id",
    "connector_run_target_id",
]

MIGRATED_INTAKE_COLUMNS = [
    *BASE_INTAKE_COLUMNS[:10],
    *INTAKE_IDENTITY_COLUMNS,
    *BASE_INTAKE_COLUMNS[10:],
]


def _run_alembic(url: str, operation, revision: str) -> None:
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    manager = logging.Logger.manager
    disabled_before = {
        name: lg.disabled
        for name, lg in manager.loggerDict.items()
        if isinstance(lg, logging.Logger)
    }
    try:
        cfg = Config(str(ALEMBIC_INI))
        cfg.set_main_option("script_location", str(BACKEND / "alembic"))
        cfg.set_main_option("sqlalchemy.url", url)
        operation(cfg, revision)
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev
        for name, lg in manager.loggerDict.items():
            if isinstance(lg, logging.Logger):
                lg.disabled = disabled_before.get(name, False)


def _run_upgrade(url: str) -> None:
    _run_alembic(url, command.upgrade, "head")


def _run_upgrade_to(url: str, revision: str) -> None:
    _run_alembic(url, command.upgrade, revision)


def _run_downgrade_to(url: str, revision: str) -> None:
    _run_alembic(url, command.downgrade, revision)


@pytest.fixture(scope="module")
def migrated_engine(tmp_path_factory: pytest.TempPathFactory):
    db_path = tmp_path_factory.mktemp("b1b_bridge") / "bridge.db"
    url = f"sqlite:///{db_path.as_posix()}"
    _run_upgrade(url)
    engine = create_engine(url)
    yield engine
    engine.dispose()


def _origin_row(**overrides) -> dict:
    row = {
        "connector_promotion_receipt_id": str(uuid.uuid4()),
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "identity_metadata_hash_version": "layer3.connector_source_intake.identity_metadata.v1",
        "source_family": "connector_produced_single_source",
        "content_sha256": "d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad",
        "identity_metadata_hash": uuid.uuid4().hex + uuid.uuid4().hex,
        "canonical_identity_key_hash": "2198fa283f1191bf30e8c3c39dec83e32cf5337f440fd5e1c21b70c923cf02c0",
        "connector_source_intake_record_id": str(uuid.uuid4()),
        "gate_b_session_id": str(uuid.uuid4()),
        "gate_b_selection_manifest_id": str(uuid.uuid4()),
        "gate_b_material_snapshot_id": str(uuid.uuid4()),
        "gate_b_decision_manifest_id": "gate-b-0123456789abcdef",
        "gate_b_decision_manifest_hash": "a" * 64,
        "material_preview_hash": "b" * 64,
        "approval_hash": "c" * 64,
        "promotion_basis_hash": "d" * 64,
        "dataset_id": None,
        "dataset_version_id": None,
        "promoted_session_id": None,
        "materialization_status": None,
        "materialization_basis_hash": None,
        "created_at": datetime.now(timezone.utc),
        "materialized_at": None,
    }
    row.update(overrides)
    return row


_INSERT = text(
    f"INSERT INTO {TABLE} ({', '.join(EXPECTED_COLUMNS)}) VALUES "
    f"({', '.join(':' + c for c in EXPECTED_COLUMNS)})"
)


def _insert(conn, **overrides) -> dict:
    row = _origin_row(**overrides)
    conn.execute(_INSERT, row)
    return row


def _intake_row(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    row = {
        "connector_source_intake_record_id": str(uuid.uuid4()),
        "client_request_id": f"b1b-predecessor-{uuid.uuid4()}",
        "operator_decision": "record_connector_produced_source",
        "source_family": "connector_produced_single_source",
        "source_label": "B1b predecessor repair fixture",
        "source_description": "Inert schema-repair test row.",
        "original_filename": "water-quality.csv",
        "media_type": "text/csv",
        "content_size_bytes": 34,
        "content_sha256": "d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad",
        "identity_metadata_hash_version": None,
        "identity_metadata_hash": None,
        "metadata_hash": uuid.uuid4().hex + uuid.uuid4().hex,
        "authority_basis_hash": uuid.uuid4().hex + uuid.uuid4().hex,
        "storage_ref": "connector-raw/run/target_water-quality.csv",
        "freshness_timestamp": None,
        "provenance_json": "{}",
        "downstream_eligibility_json": "{}",
        "summary_json": "{}",
        "status": "recorded",
        "created_at": now,
        "updated_at": now,
        "connector_key": "sciencebase-public",
        "connector_run_id": str(uuid.uuid4()),
        "connector_run_target_id": str(uuid.uuid4()),
    }
    row.update(overrides)
    return row


def _insert_intake(conn, *, include_identity: bool = True, **overrides) -> dict:
    row = _intake_row(**overrides)
    columns = MIGRATED_INTAKE_COLUMNS if include_identity else BASE_INTAKE_COLUMNS
    statement = text(
        f"INSERT INTO {INTAKE_TABLE} ({', '.join(columns)}) VALUES "
        f"({', '.join(':' + column for column in columns)})"
    )
    conn.execute(statement, {column: row[column] for column in columns})
    return row


# ---------------------------------------------------------------------------
# Flag default
# ---------------------------------------------------------------------------


def test_bridge_flag_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED", raising=False)
    from app.core.config import Settings

    settings = Settings()
    assert settings.layer3_connector_promotion_bridge_enabled is False


def test_bridge_flag_alias_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED", "true")
    from app.core.config import Settings

    settings = Settings()
    assert settings.layer3_connector_promotion_bridge_enabled is True


def test_bridge_flag_false_existing_intake_path_leaves_identity_pair_null(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_dir = tmp_path / "storage"
    raw_dir = storage_dir / "connectors" / "raw"
    raw_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = session_local()
    try:
        blob = b"site_id,value\nSB-001,42\nSB-002,43\n"
        run_id = str(uuid.uuid4())
        target_id = str(uuid.uuid4())
        raw_path = raw_dir / f"{target_id}_water-quality.csv"
        raw_path.write_bytes(blob)
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="sciencebase-public",
            source_system="sciencebase",
            source_mode="public_api",
            status="running",
        )
        target = ConnectorRunTarget(
            connector_run_target_id=target_id,
            connector_run_id=run_id,
            ordinal=1,
            sciencebase_item_id="sb-item-001",
            sciencebase_item_url="https://www.sciencebase.gov/catalog/item/sb-item-001",
            sciencebase_file_name="water-quality.csv",
            sciencebase_download_uri="https://www.sciencebase.gov/catalog/file/get/sb-item-001",
            artifact_surface="files",
            artifact_locator_type="download_uri",
            source_artifact_key="sciencebase://sb-item-001/water-quality.csv",
            downloaded_sha256=hashlib.sha256(blob).hexdigest(),
            raw_storage_ref=str(raw_path),
            public_read_confirmed=True,
            status="downloaded",
        )
        db.add_all([run, target])
        db.commit()

        response = record_connector_produced_source_intake(
            db,
            client_request_id="b1b-predecessor-flag-false",
            connector_key=run.connector_key,
            connector_run_id=run_id,
            connector_run_target_id=target_id,
            source_label="Flag-false inert intake",
            source_description="Existing intake path must not populate B1b identity metadata.",
            media_type="text/csv",
        )
        db.expire_all()
        record = db.get(
            L3ConnectorSourceIntakeRecord,
            response["connector_source_intake_record_id"],
        )
        assert record is not None
        assert record.identity_metadata_hash_version is None
        assert record.identity_metadata_hash is None
    finally:
        db.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Migrated DDL shape
# ---------------------------------------------------------------------------


def test_intake_identity_schema_shape_and_orm_parity(migrated_engine) -> None:
    inspector = sa_inspect(migrated_engine)
    reflected_columns = {column["name"]: column for column in inspector.get_columns(INTAKE_TABLE)}
    for column_name in INTAKE_IDENTITY_COLUMNS:
        assert str(reflected_columns[column_name]["type"]).upper() == "VARCHAR(64)"
        assert reflected_columns[column_name]["nullable"] is True

    reflected_indexes = {index["name"]: index for index in inspector.get_indexes(INTAKE_TABLE)}
    identity_index = reflected_indexes[INTAKE_IDENTITY_INDEX]
    assert identity_index["column_names"] == [
        "identity_metadata_hash_version",
        "source_family",
        "content_sha256",
        "identity_metadata_hash",
    ]
    assert bool(identity_index["unique"]) is False
    unique_column_sets = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(INTAKE_TABLE)
    }
    assert tuple(identity_index["column_names"]) not in unique_column_sets
    reflected_check_names = {
        constraint["name"] for constraint in inspector.get_check_constraints(INTAKE_TABLE)
    }
    assert INTAKE_IDENTITY_CHECK in reflected_check_names

    orm_table = L3ConnectorSourceIntakeRecord.__table__
    for column_name in INTAKE_IDENTITY_COLUMNS:
        assert str(orm_table.c[column_name].type).upper() == "VARCHAR(64)"
        assert orm_table.c[column_name].nullable is True
    orm_identity_index = next(index for index in orm_table.indexes if index.name == INTAKE_IDENTITY_INDEX)
    assert [column.name for column in orm_identity_index.columns] == identity_index["column_names"]
    assert orm_identity_index.unique is False
    assert INTAKE_IDENTITY_CHECK in {constraint.name for constraint in orm_table.constraints}


def test_intake_identity_joint_null_and_non_unique_semantics(migrated_engine) -> None:
    version = "layer3.connector_source_intake.identity_metadata.v1"
    identity_hash = "7" * 64
    with migrated_engine.begin() as conn:
        _insert_intake(conn)
        _insert_intake(
            conn,
            identity_metadata_hash_version=version,
            identity_metadata_hash=identity_hash,
        )
        _insert_intake(
            conn,
            identity_metadata_hash_version=version,
            identity_metadata_hash=identity_hash,
        )


@pytest.mark.parametrize(
    ("identity_metadata_hash_version", "identity_metadata_hash"),
    [
        (None, "8" * 64),
        ("layer3.connector_source_intake.identity_metadata.v1", None),
    ],
)
def test_intake_identity_one_null_rejected(
    migrated_engine,
    identity_metadata_hash_version,
    identity_metadata_hash,
) -> None:
    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as conn:
            _insert_intake(
                conn,
                identity_metadata_hash_version=identity_metadata_hash_version,
                identity_metadata_hash=identity_metadata_hash,
            )


def test_receipt_table_exact_columns(migrated_engine) -> None:
    inspector = sa_inspect(migrated_engine)
    assert inspector.has_table(TABLE)
    cols = [c["name"] for c in inspector.get_columns(TABLE)]
    assert cols == EXPECTED_COLUMNS


def test_receipt_unique_tuple_and_indexes(migrated_engine) -> None:
    inspector = sa_inspect(migrated_engine)
    uniques = inspector.get_unique_constraints(TABLE)
    # Exactly ONE non-PK uniqueness rule, and it is the D33 four-column tuple.
    assert len(uniques) == 1, uniques
    assert uniques[0]["column_names"] == [
        "identity_metadata_hash_version",
        "source_family",
        "content_sha256",
        "identity_metadata_hash",
    ], uniques
    # Exactly the seven explicit FK indexes — no extras, none missing.
    explicit_indexes = {
        i["name"] for i in inspector.get_indexes(TABLE) if not i["name"].startswith("sqlite_autoindex")
    }
    assert explicit_indexes == {
        "ix_l3_connector_promotion_intake",
        "ix_l3_connector_promotion_gate_b_session",
        "ix_l3_connector_promotion_selection_manifest",
        "ix_l3_connector_promotion_material_snapshot",
        "ix_l3_connector_promotion_dataset",
        "ix_l3_connector_promotion_dataset_version",
        "ix_l3_connector_promotion_promoted_session",
    }, explicit_indexes


EXPECTED_TYPES_NULLABILITY = {
    "connector_promotion_receipt_id": ("VARCHAR(36)", False),
    "receipt_schema_version": ("VARCHAR(64)", False),
    "identity_metadata_hash_version": ("VARCHAR(64)", False),
    "source_family": ("VARCHAR(64)", False),
    "content_sha256": ("VARCHAR(64)", False),
    "identity_metadata_hash": ("VARCHAR(64)", False),
    "canonical_identity_key_hash": ("VARCHAR(64)", False),
    "connector_source_intake_record_id": ("VARCHAR(36)", False),
    "gate_b_session_id": ("VARCHAR(36)", False),
    "gate_b_selection_manifest_id": ("VARCHAR(36)", False),
    "gate_b_material_snapshot_id": ("VARCHAR(36)", False),
    "gate_b_decision_manifest_id": ("VARCHAR(64)", False),
    "gate_b_decision_manifest_hash": ("VARCHAR(64)", False),
    "material_preview_hash": ("VARCHAR(64)", False),
    "approval_hash": ("VARCHAR(64)", False),
    "promotion_basis_hash": ("VARCHAR(64)", False),
    "dataset_id": ("VARCHAR(36)", True),
    "dataset_version_id": ("VARCHAR(36)", True),
    "promoted_session_id": ("VARCHAR(36)", True),
    "materialization_status": ("VARCHAR(32)", True),
    "materialization_basis_hash": ("VARCHAR(64)", True),
    "created_at": ("DATETIME", False),
    "materialized_at": ("DATETIME", True),
}


def test_receipt_column_types_and_nullability(migrated_engine) -> None:
    inspector = sa_inspect(migrated_engine)
    reflected = {
        c["name"]: (str(c["type"]).upper(), bool(c["nullable"]))
        for c in inspector.get_columns(TABLE)
    }
    assert reflected == EXPECTED_TYPES_NULLABILITY


EXPECTED_FKS = {
    "connector_source_intake_record_id": (
        "l3_connector_source_intake_record",
        "connector_source_intake_record_id",
    ),
    "gate_b_session_id": ("l3_session", "session_id"),
    "gate_b_selection_manifest_id": ("l3_selection_manifest", "selection_manifest_id"),
    "gate_b_material_snapshot_id": ("l3_material_snapshot", "material_snapshot_id"),
    "dataset_id": ("dataset", "dataset_id"),
    "dataset_version_id": ("dataset_version", "dataset_version_id"),
    "promoted_session_id": ("l3_session", "session_id"),
}


def test_receipt_fk_targets_and_restrict(migrated_engine) -> None:
    inspector = sa_inspect(migrated_engine)
    fks = inspector.get_foreign_keys(TABLE)
    assert len(fks) == 7, fks
    seen = {}
    for fk in fks:
        assert fk["constrained_columns"] and len(fk["constrained_columns"]) == 1, fk
        col = fk["constrained_columns"][0]
        assert fk["referred_columns"] == [EXPECTED_FKS[col][1]], fk
        assert fk["referred_table"] == EXPECTED_FKS[col][0], fk
        assert (fk.get("options") or {}).get("ondelete") == "RESTRICT", fk
        seen[col] = True
    assert set(seen) == set(EXPECTED_FKS)


# ---------------------------------------------------------------------------
# No-backfill upgrade and guarded downgrade
# ---------------------------------------------------------------------------


def test_upgrade_preserves_preexisting_intake_row_without_backfill(tmp_path: Path) -> None:
    db_path = tmp_path / "no-backfill.db"
    url = f"sqlite:///{db_path.as_posix()}"
    _run_upgrade_to(url, "0056_layer3_connector_source_intake_record")
    engine = create_engine(url)
    with engine.begin() as conn:
        row = _insert_intake(conn, include_identity=False)
        before = dict(
            conn.execute(
                text(
                    f"SELECT {', '.join(BASE_INTAKE_COLUMNS)} FROM {INTAKE_TABLE} "
                    "WHERE connector_source_intake_record_id = :record_id"
                ),
                {"record_id": row["connector_source_intake_record_id"]},
            )
            .mappings()
            .one()
        )
    engine.dispose()

    _run_upgrade(url)
    engine = create_engine(url)
    with engine.connect() as conn:
        after = dict(
            conn.execute(
                text(
                    f"SELECT {', '.join(MIGRATED_INTAKE_COLUMNS)} FROM {INTAKE_TABLE} "
                    "WHERE connector_source_intake_record_id = :record_id"
                ),
                {"record_id": row["connector_source_intake_record_id"]},
            )
            .mappings()
            .one()
        )
        receipt_count = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
    engine.dispose()

    assert {column: after[column] for column in BASE_INTAKE_COLUMNS} == before
    assert after["identity_metadata_hash_version"] is None
    assert after["identity_metadata_hash"] is None
    assert receipt_count == 0


def test_downgrade_refuses_before_ddl_when_receipt_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "downgrade-refusal.db"
    url = f"sqlite:///{db_path.as_posix()}"
    _run_upgrade(url)
    engine = create_engine(url)
    with engine.begin() as conn:
        _insert(conn)
    engine.dispose()

    with pytest.raises(RuntimeError, match="promotion receipt rows exist"):
        _run_downgrade_to(url, "0056_layer3_connector_source_intake_record")

    engine = create_engine(url)
    inspector = sa_inspect(engine)
    assert inspector.has_table(TABLE)
    assert set(INTAKE_IDENTITY_COLUMNS) <= {
        column["name"] for column in inspector.get_columns(INTAKE_TABLE)
    }
    assert INTAKE_IDENTITY_INDEX in {
        index["name"] for index in inspector.get_indexes(INTAKE_TABLE)
    }
    assert INTAKE_IDENTITY_CHECK in {
        constraint["name"] for constraint in inspector.get_check_constraints(INTAKE_TABLE)
    }
    with engine.connect() as conn:
        assert conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one() == 1
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0057_layer3_b1b_connector_promotion"
        )
    engine.dispose()


def test_clean_downgrade_preserves_intake_row_and_removes_b1b_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "clean-downgrade.db"
    url = f"sqlite:///{db_path.as_posix()}"
    _run_upgrade(url)
    engine = create_engine(url)
    with engine.begin() as conn:
        row = _insert_intake(
            conn,
            identity_metadata_hash_version="layer3.connector_source_intake.identity_metadata.v1",
            identity_metadata_hash="9" * 64,
        )
        before = dict(
            conn.execute(
                text(
                    f"SELECT {', '.join(BASE_INTAKE_COLUMNS)} FROM {INTAKE_TABLE} "
                    "WHERE connector_source_intake_record_id = :record_id"
                ),
                {"record_id": row["connector_source_intake_record_id"]},
            )
            .mappings()
            .one()
        )
    engine.dispose()

    _run_downgrade_to(url, "0056_layer3_connector_source_intake_record")
    engine = create_engine(url)
    inspector = sa_inspect(engine)
    assert not inspector.has_table(TABLE)
    assert set(INTAKE_IDENTITY_COLUMNS).isdisjoint(
        column["name"] for column in inspector.get_columns(INTAKE_TABLE)
    )
    assert INTAKE_IDENTITY_INDEX not in {
        index["name"] for index in inspector.get_indexes(INTAKE_TABLE)
    }
    assert INTAKE_IDENTITY_CHECK not in {
        constraint["name"] for constraint in inspector.get_check_constraints(INTAKE_TABLE)
    }
    with engine.connect() as conn:
        after = dict(
            conn.execute(
                text(
                    f"SELECT {', '.join(BASE_INTAKE_COLUMNS)} FROM {INTAKE_TABLE} "
                    "WHERE connector_source_intake_record_id = :record_id"
                ),
                {"record_id": row["connector_source_intake_record_id"]},
            )
            .mappings()
            .one()
        )
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()
    assert after == before
    assert revision == "0056_layer3_connector_source_intake_record"


# ---------------------------------------------------------------------------
# Joint-state semantics
# ---------------------------------------------------------------------------


def test_state1_initial_committed_receipt_inserts(migrated_engine) -> None:
    with migrated_engine.begin() as conn:
        _insert(conn)


def test_state3_committed_output_inserts(migrated_engine) -> None:
    with migrated_engine.begin() as conn:
        _insert(
            conn,
            materialization_status="materialized",
            materialization_basis_hash="e" * 64,
            dataset_id=str(uuid.uuid4()),
            dataset_version_id=str(uuid.uuid4()),
            promoted_session_id=str(uuid.uuid4()),
            materialized_at=datetime.now(timezone.utc),
        )


def test_state2_claim_shape_inserts(migrated_engine) -> None:
    # The 'materializing' claim is never visible as a committed row in the
    # resolver contract, but the DDL joint-state check itself must accept it
    # (it exists only inside the claim transaction).
    with migrated_engine.begin() as conn:
        _insert(
            conn,
            materialization_status="materializing",
            materialization_basis_hash="f" * 64,
        )


@pytest.mark.parametrize(
    "overrides",
    [
        # materialized but outputs missing
        {"materialization_status": "materialized", "materialization_basis_hash": "1" * 64},
        # basis set without status
        {"materialization_basis_hash": "2" * 64},
        # output link set in initial state
        {"dataset_id": "not-null-value"},
        # materializing with an output link already set
        {
            "materialization_status": "materializing",
            "materialization_basis_hash": "3" * 64,
            "promoted_session_id": "premature",
        },
        # unknown status value
        {"materialization_status": "failed", "materialization_basis_hash": "4" * 64},
        # materializing claim WITHOUT a basis — guards the SQL-NULL defect class
        {"materialization_status": "materializing"},
        # materialized_at without full output state
        {"materialized_at": datetime.now(timezone.utc)},
    ],
)
def test_invalid_joint_states_rejected(migrated_engine, overrides) -> None:
    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as conn:
            _insert(conn, **overrides)


# ---------------------------------------------------------------------------
# Uniqueness + schema pin
# ---------------------------------------------------------------------------


def test_identity_tuple_unique(migrated_engine) -> None:
    fixed_identity_hash = "9" * 64
    with migrated_engine.begin() as conn:
        _insert(conn, identity_metadata_hash=fixed_identity_hash)
    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as conn:
            _insert(conn, identity_metadata_hash=fixed_identity_hash)


def test_receipt_schema_version_pinned(migrated_engine) -> None:
    with pytest.raises(IntegrityError):
        with migrated_engine.begin() as conn:
            _insert(conn, receipt_schema_version="layer3.connector_promotion_receipt.v2")


# ---------------------------------------------------------------------------
# Digest primitives (B1b-01 step 2) — golden vectors and contract behavior
# ---------------------------------------------------------------------------

import hashlib as _hashlib
import json as _json

from app.services import layer3_connector_promotion as pm


@pytest.fixture(scope="module")
def b1b_03_golden_preimages() -> dict[str, bytes]:
    return {
        "question": b"Within the two synthetic C01 rows (`SB-001=42` and `SB-002=43`), what per-column classification, missingness, top values, and `value` minimum, maximum, mean, median, and sample standard deviation does `descriptive_summary` report, subject to the fixture being synthetic, non-temporal, and too small for official, causal, or population-wide inference?",
        "transformation": b'{"input":{"bom":false,"bytes":34,"encoding":"utf-8-strict","final_lf":true,"line_endings":"lf","sha256":"d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad"},"output":{"coercion_count":0,"column_count":2,"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"drop_count":0,"row_count":2,"rows":[["SB-001",42],["SB-002",43]]},"parse":{"fallbacks":[],"header":["site_id","value"],"row_order":"source"},"schema_id":"layer3.connector_promotion_transform.v1"}',
        "method_input": b'{"columns":[{"logical_type":"categorical_string","name":"site_id"},{"logical_type":"numeric_integer","name":"value"}],"rows":[["SB-001",42],["SB-002",43]],"schema_id":"layer3.descriptive_summary.input.v1","time_column":null}',
        "method_contract": b'{"analysis_authority":{"git_blob":"e38beab8a29d3e024a442573624199dc2e93fba0","path":"backend/app/services/analysis.py","runner":"_run_descriptive_summary"},"annotation_window_id":null,"dependency_lock_git_blob":"3a0fec8abe04341a192822862dfa0be1861d137b","goal_type":null,"method_id":"descriptive_summary","method_input_sha256":"907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b","method_version":"1","parameters":{},"question_id":"CT4B-C01-DESC-001","question_text":"Within the two synthetic C01 rows (`SB-001=42` and `SB-002=43`), what per-column classification, missingness, top values, and `value` minimum, maximum, mean, median, and sample standard deviation does `descriptive_summary` report, subject to the fixture being synthetic, non-temporal, and too small for official, causal, or population-wide inference?","schema_id":"layer3.descriptive_summary.method_contract.v1"}',
    }


def test_b1b_03_golden_preimages_and_entry_gate_are_exact(
    b1b_03_golden_preimages: dict[str, bytes],
) -> None:
    expected = {
        "question": (350, "c7ca8c1ffd1693be3e32a0d6172923714f2396bffc29d251a38eb1d7c22f911d"),
        "transformation": (531, "951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179"),
        "method_input": (224, "907672513191cd069b19b761a60f9bbc51334bb0ca25e4c316d35faf48a3155b"),
        "method_contract": (894, "586745d83f62f60e32a94fb62cd5557341866e5319d48eece7d0ea741a5e89e5"),
    }
    for name, data in b1b_03_golden_preimages.items():
        assert (len(data), _hashlib.sha256(data).hexdigest()) == expected[name]
        assert not data.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in data and not data.endswith(b"\n")
        if name != "question":
            assert pm.d33_canonical_bytes(_json.loads(data)) == data

    transformation = _json.loads(b1b_03_golden_preimages["transformation"])
    method_input = _json.loads(b1b_03_golden_preimages["method_input"])
    method_contract = _json.loads(b1b_03_golden_preimages["method_contract"])
    assert transformation["output"] == {
        "coercion_count": 0,
        "column_count": 2,
        "columns": [
            {"logical_type": "categorical_string", "name": "site_id"},
            {"logical_type": "numeric_integer", "name": "value"},
        ],
        "drop_count": 0,
        "row_count": 2,
        "rows": [["SB-001", 42], ["SB-002", 43]],
    }
    assert method_input["rows"] == transformation["output"]["rows"]
    assert method_contract["method_input_sha256"] == expected["method_input"][1]
    assert method_contract["question_text"].encode("utf-8") == b1b_03_golden_preimages["question"]

    repo = BACKEND.parent
    pins = {
        "backend/app/services/analysis.py": "e38beab8a29d3e024a442573624199dc2e93fba0",
        "backend/requirements.lock.txt": "3a0fec8abe04341a192822862dfa0be1861d137b",
    }
    assert {
        path: subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{path}"], cwd=repo, text=True
        ).strip()
        for path in pins
    } == pins


def test_b1b_03_request_models_reject_all_derived_analysis_overrides() -> None:
    overrides = {
        "connector_promotion_receipt_id": "caller-receipt",
        "dataset_version_id": "caller-version",
        "question_id": "caller-question",
        "question_text": "caller text",
        "method_id": "caller_method",
        "method_version": "999",
        "parameters": {"caller": True},
        "goal_type": "caller-goal",
        "annotation_window_id": "caller-window",
        "method_input_sha256": "1" * 64,
        "method_contract_sha256": "2" * 64,
        "transformation_contract_sha256": "3" * 64,
        "method_contract": {"method_id": "caller_method"},
        "receipt_bound_analysis_contract": {"inputs": {"dataset_version_id": "caller-version"}},
    }
    model_payloads = (
        (Layer3PlanPreviewRequest, {"session_id": "session-1"}),
        (
            Layer3PlanApprovalRequest,
            {
                "session_id": "session-1",
                "preview_id": "preview-1",
                "preview_hash": "a" * 64,
                "operator_confirmation": True,
            },
        ),
    )
    for model, payload in model_payloads:
        for field, value in overrides.items():
            with pytest.raises(ValidationError) as caught:
                model.model_validate({**payload, field: value})
            assert caught.value.errors()[0]["type"] == "extra_forbidden"
            assert caught.value.errors()[0]["loc"] == (field,)


def test_b1b_closed_error_registry_and_attestation_default_are_exact() -> None:
    expected = [
        ("promotion_identity_decision_conflict", 409, "Promotion identity decision conflicts with the committed receipt.", False),
        ("connector_promotion_bridge_unavailable", 503, "Connector promotion bridge is unavailable.", True),
        ("b1b_handoff_full_body_required", 400, "Handoff requires a full-body request.", False),
        ("connector_promotion_session_not_found", 404, "Connector promotion session was not found.", False),
        ("connector_promotion_not_eligible", 409, "Connector promotion is not eligible.", False),
        ("b1b_request_validation_failed", 422, "Request body failed validation.", False),
        ("promotion_identity_lock_unavailable", 503, "Promotion identity lock is unavailable.", True),
        ("connector_promotion_basis_conflict", 409, "Promotion basis conflicts with the committed receipt.", False),
        ("connector_result_review_decision_conflict", 409, "Result review decision conflicts with the recorded review.", False),
        ("connector_package_basis_conflict", 409, "Package basis conflicts with the committed package set.", False),
        ("connector_package_review_decision_conflict", 409, "Package review decision conflicts with the recorded review.", False),
        ("connector_materialization_basis_conflict", 409, "Materialization basis conflicts with the committed output.", False),
    ]
    assert [
        (code, status, message, retryable)
        for code, (status, message, retryable) in pm._B1B_ERROR_SPECS.items()
    ] == expected
    assert pm.attestation_precondition_available() is False
    with pytest.raises(pm.PromotionIdentityError):
        pm.b1b_error_body("not-a-closed-code")


def test_metadata_contract_golden_vector() -> None:
    data = pm.METADATA_CONTRACT_CANONICAL_JSON.encode("utf-8")
    assert len(data) == 2180
    assert _hashlib.sha256(data).hexdigest() == pm.METADATA_CONTRACT_SHA256
    # Round trip: the embedded string IS the D33-canonical form of its object.
    assert pm.d33_canonical_bytes(_json.loads(data)) == data


def test_identity_metadata_hash_golden_vector() -> None:
    assert (
        pm.identity_metadata_hash(pm.F07_CONNECTOR_KEY, pm.F07_SCIENCEBASE_ITEM_ID, pm.F07_MEDIA_TYPE)
        == pm.F07_IDENTITY_METADATA_HASH
    )


def test_canonical_identity_key_golden_vector() -> None:
    assert (
        pm.canonical_identity_key_hash(
            pm.IDENTITY_METADATA_HASH_VERSION,
            pm.F07_SOURCE_FAMILY,
            pm.F07_CONTENT_SHA256,
            pm.F07_IDENTITY_METADATA_HASH,
        )
        == pm.F07_CANONICAL_IDENTITY_KEY_HASH
    )


def test_d33_serializer_rejections() -> None:
    for bad in [float("nan"), float("inf"), {1: "x"}, {"a": {2: "y"}}, {"a": set()}, {"a": b"bytes"}]:
        with pytest.raises(pm.PromotionIdentityError):
            pm.d33_canonical_bytes(bad if isinstance(bad, (dict, list)) else {"v": bad})


def test_media_type_normalization_matrix() -> None:
    # Essence + parameter-name lowercasing; parameter order irrelevant; value case preserved.
    a = pm.parse_media_type("Text/CSV; Foo=Bar; baz=qux")
    b = pm.parse_media_type("text/csv; BAZ=qux; foo=Bar")
    assert a == b == {"charset": None, "essence": "text/csv", "parameters": {"baz": "qux", "foo": "Bar"}}
    # charset moves to the explicit nullable key, token lowercased, no alias guessing.
    c = pm.parse_media_type('text/csv; charset="UTF-8"')
    assert c == {"charset": "utf-8", "essence": "text/csv", "parameters": {}}
    d = pm.parse_media_type("text/csv; charset=utf8")
    assert d["charset"] == "utf8"  # utf8 is NOT normalized to utf-8
    # Rejections: malformed essence, duplicate names after lowercasing, empty segment.
    for bad in ["textcsv", "text/", "/csv", "text/csv; a=1; A=2", "text/csv; ;", "text/csv; name", "text/csv; =v"]:
        with pytest.raises(pm.PromotionIdentityError):
            pm.parse_media_type(bad)


def test_identity_string_rules() -> None:
    # Trim + NFC + case preserved; empty/None invalid, never a wildcard.
    assert (
        pm.identity_metadata_hash("  sciencebase_public  ", pm.F07_SCIENCEBASE_ITEM_ID, pm.F07_MEDIA_TYPE)
        == pm.F07_IDENTITY_METADATA_HASH
    )
    for bad_key in ["", "   ", None, 7]:
        with pytest.raises(pm.PromotionIdentityError):
            pm.identity_metadata_hash(bad_key, pm.F07_SCIENCEBASE_ITEM_ID, pm.F07_MEDIA_TYPE)


def test_decision_semantics_hash_behavior() -> None:
    args = (
        pm.IDENTITY_METADATA_HASH_VERSION,
        pm.F07_SOURCE_FAMILY,
        pm.F07_CONTENT_SHA256,
        pm.F07_IDENTITY_METADATA_HASH,
    )
    approved = pm.decision_semantics_hash("approved", *args)
    denied = pm.decision_semantics_hash("denied", *args)
    assert approved != denied
    assert approved == pm.decision_semantics_hash("approved", *args)  # deterministic
    with pytest.raises(pm.PromotionIdentityError):
        pm.decision_semantics_hash("maybe", *args)


def test_promotion_basis_hash_structure() -> None:
    kwargs = dict(
        approval_hash="a" * 64,
        gate_b_session_id="s-1",
        gate_b_selection_manifest_id="m-1",
        gate_b_material_snapshot_id="snap-1",
        gate_b_decision_manifest_id="gate-b-0123456789abcdef",
        gate_b_decision_manifest_hash="b" * 64,
        material_preview_hash="c" * 64,
        canonical_identity_key_hash=pm.F07_CANONICAL_IDENTITY_KEY_HASH,
        identity_metadata_hash_version=pm.IDENTITY_METADATA_HASH_VERSION,
        source_family=pm.F07_SOURCE_FAMILY,
        content_sha256=pm.F07_CONTENT_SHA256,
        identity_metadata_hash=pm.F07_IDENTITY_METADATA_HASH,
        connector_source_intake_record_id="intake-1",
    )
    h1 = pm.promotion_basis_hash(**kwargs)
    assert len(h1) == 64 and h1 == pm.promotion_basis_hash(**kwargs)
    # Any single component change changes the digest.
    changed = dict(kwargs, gate_b_session_id="s-2")
    assert pm.promotion_basis_hash(**changed) != h1
    # Uppercase hex rejected (lowercase 64-hex contract).
    with pytest.raises(pm.PromotionIdentityError):
        pm.promotion_basis_hash(**dict(kwargs, approval_hash="A" * 64))


def test_storage_ref_hash_domains() -> None:
    ref = "b1b/dataset-versions/ab/abcd.parquet"
    expected_in = _hashlib.sha256(b"project6-storage-ref-v1\x00" + ref.encode()).hexdigest()
    expected_out = _hashlib.sha256(b"project6-dataset-storage-ref-v1\x00" + ref.encode()).hexdigest()
    assert pm.storage_ref_hash(ref) == expected_in
    assert pm.dataset_storage_ref_hash(ref) == expected_out
    assert expected_in != expected_out  # domains never interchange
    # Backslashes normalize to '/', case preserved.
    assert pm.storage_ref_hash("b1b\\dataset-versions\\ab\\abcd.parquet") == expected_in
    for bad in ["", "/lead", "trail/", "a//b", "a/./b", "a/../b", "C:/x", "a\x00b", ".."]:
        with pytest.raises(pm.PromotionIdentityError):
            pm.storage_ref_hash(bad)


def test_materialization_basis_and_record_wrapper() -> None:
    basis = pm.build_materialization_basis(
        dataframe_io_git_blob="4" * 40,
        implementation_commit="1" * 40,
        ingest_git_blob="3" * 40,
        promotion_git_blob="2" * 40,
        input_storage_ref_hash="f" * 64,
        connector_run_id="66666666-6666-6666-6666-666666666666",
        connector_run_target_id="77777777-7777-7777-7777-777777777777",
        connector_source_intake_record_id="11111111-1111-1111-1111-111111111111",
        gate_b_material_snapshot_id="44444444-4444-4444-4444-444444444444",
        gate_b_selection_manifest_id="33333333-3333-3333-3333-333333333333",
        gate_b_session_id="22222222-2222-2222-2222-222222222222",
        canonical_identity_key_hash=pm.F07_CANONICAL_IDENTITY_KEY_HASH,
        connector_promotion_receipt_id="55555555-5555-5555-5555-555555555555",
        promotion_basis_hash="cd3edda3b436481aaf4caaa39d483b54b2c86979ae9b6df6b293d1c1c9e6a938",
    )
    bh = pm.materialization_basis_hash(basis)
    canonical_basis = pm.d33_canonical_bytes(basis)
    assert len(canonical_basis) == 1787
    assert bh == "2f4b1251c42f753558d66352218358883c33de44543adfc497d209b783dfaca7"
    # Embedded fixed sections are exact.
    assert basis["code"]["metadata_contract_sha256"] == pm.METADATA_CONTRACT_SHA256
    assert basis["transformation"]["contract_sha256"] == pm.TRANSFORM_CONTRACT_SHA256
    assert basis["input"]["bytes"] == 34

    record = pm.build_materialization_record(
        basis_hash=bh,
        dataset_file_bytes=1234,
        dataset_file_sha256="0" * 64,
        dataset_id="88888888-8888-8888-8888-888888888888",
        dataset_source_provenance_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        dataset_storage_ref_hash="9" * 64,
        dataset_version_content_sha256=pm.F07_CONTENT_SHA256,
        dataset_version_id="99999999-9999-9999-9999-999999999999",
        promoted_session_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        source_connector_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
    )
    wrapper = pm.build_materialization_wrapper(record)
    canonical_record = pm.d33_canonical_bytes(record)
    assert len(canonical_record) == 848
    assert _hashlib.sha256(canonical_record).hexdigest() == (
        "b43f3ba85a0ec153367368cc7a895dd8d0377a282d65ef6ac81df4c8e3483d0f"
    )
    assert record["output"]["source_connector_id"] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert wrapper["record"] is record
    assert wrapper["record_hash"] == pm.d33_sha256(record)  # inner record only, never the wrapper
    with pytest.raises(pm.PromotionIdentityError):
        pm.build_materialization_record(
            basis_hash=bh,
            dataset_file_bytes=0,
            dataset_file_sha256="7" * 64,
            dataset_id="ds-1",
            dataset_source_provenance_id="prov-1",
            dataset_storage_ref_hash="8" * 64,
            dataset_version_content_sha256=pm.F07_CONTENT_SHA256,
            dataset_version_id="dsv-1",
            promoted_session_id="promoted-1",
            source_connector_id="conn-1",
        )


# ---------------------------------------------------------------------------
# Gate-B arbitration and receipt mint/reuse (B1b-01 step 3)
# ---------------------------------------------------------------------------

_F07_BYTES = b"site_id,value\nSB-001,42\nSB-002,43\n"
_GATE_B_MODELS = (
    L3GateBIdempotencyKey,
    L3Session,
    L3SelectionManifest,
    L3Descriptor,
    L3RetrievalEvent,
    L3MaterialSnapshot,
    L3ConnectorPromotionReceipt,
)
_GATE_B_SPINE_DELTA = {
    "L3GateBIdempotencyKey": 1,
    "L3Session": 1,
    "L3SelectionManifest": 1,
    "L3Descriptor": 1,
    "L3RetrievalEvent": 1,
    "L3MaterialSnapshot": 1,
    "L3ConnectorPromotionReceipt": 0,
}
_GATE_B_MINT_DELTA = {**_GATE_B_SPINE_DELTA, "L3ConnectorPromotionReceipt": 1}
_PUBLIC_GATE_B_KEYS = {
    "schema_id",
    "schema_version",
    "request_id",
    "server_time",
    "status",
    "session_id",
    "selection_manifest_id",
    "material_preview_hash",
    "gate_b_decision_manifest_id",
    "approved_candidate_ids",
    "denied_candidate_ids",
    "isolated_candidate_ids",
    "flagged_candidate_ids",
    "next_state",
    "authority_rail",
}


@pytest.fixture
def b1b_step3_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage_dir = tmp_path / "storage"
    raw_dir = storage_dir / "connectors" / "raw" / "f07"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "water-quality.csv"
    raw_path.write_bytes(_F07_BYTES)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)

    db_path = tmp_path / "step3.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    with factory() as db:
        db.add_all(
            [
                ConnectorRun(
                    connector_run_id=run_id,
                    connector_key=pm.F07_CONNECTOR_KEY,
                    source_system="sciencebase",
                    source_mode="synthetic_local_direct_intake",
                    status="running",
                ),
                ConnectorRunTarget(
                    connector_run_target_id=target_id,
                    connector_run_id=run_id,
                    ordinal=1,
                    sciencebase_item_id=pm.F07_SCIENCEBASE_ITEM_ID,
                    sciencebase_item_url=None,
                    sciencebase_file_name="water-quality.csv",
                    sciencebase_download_uri=None,
                    artifact_surface="synthetic_fixture",
                    artifact_locator_type="intake_storage_ref",
                    source_artifact_key="f07-c01-synthetic",
                    downloaded_sha256=pm.F07_CONTENT_SHA256,
                    raw_storage_ref=str(raw_path.resolve()),
                    public_read_confirmed=True,
                    status="downloaded",
                ),
            ]
        )
        db.commit()
    runtime = {
        "engine": engine,
        "factory": factory,
        "storage_dir": storage_dir,
        "raw_path": raw_path,
        "run_id": run_id,
        "target_id": target_id,
    }
    yield runtime
    engine.dispose()


def _capture_f07(runtime: dict, stem: str) -> tuple[dict, dict]:
    with runtime["factory"]() as db:
        intake = record_connector_produced_source_intake(
            db,
            client_request_id=f"{stem}-intake",
            connector_key=pm.F07_CONNECTOR_KEY,
            connector_run_id=runtime["run_id"],
            connector_run_target_id=runtime["target_id"],
            source_label="Synthetic F07 C01 connector material",
            source_description="Offline synthetic fixture; not official public data.",
            media_type=pm.F07_MEDIA_TYPE,
        )
        preview = connector_source_intake_material_preview(
            db,
            connector_source_intake_record_id=intake["connector_source_intake_record_id"],
        )
    return intake, preview


def _step3_decision_basis(candidate: dict) -> dict:
    return {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": copy.deepcopy(candidate["source_identity"]),
        "source_provenance": copy.deepcopy(candidate["source_provenance"]),
        "payload": copy.deepcopy(candidate["payload"]),
        "load_summary": copy.deepcopy(candidate["load_summary"]),
        "connector_target": {
            "connector_run_target_id": candidate["payload"]["connector_run_target_id"],
            "connector_key": pm.F07_CONNECTOR_KEY,
        },
    }


def _step3_payload(preview: dict, stem: str, *, decision: str = "approved") -> dict:
    candidate = preview["material_candidate"]
    return {
        "client_request_id": f"{stem}-gate-b",
        "preflight_id": f"{stem}-preflight",
        "source_set_id": f"{stem}-source-set",
        "material_preview_id": preview["material_preview_id"],
        "material_preview_hash": preview["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": decision,
                "operator_reason": "" if decision == "approved" else f"Operator selected {decision}.",
                "decision_basis": _step3_decision_basis(candidate),
            }
        ],
        "actor": "pytest-b1b-step3",
    }


def _invoke_step3(runtime: dict, payload: dict) -> dict:
    with runtime["factory"]() as db:
        return layer3_workbench.gate_b_decision(db, payload)


def _gate_b_census(runtime: dict) -> dict[str, int]:
    with runtime["factory"]() as db:
        return {model.__name__: db.query(model).count() for model in _GATE_B_MODELS}


def _gate_b_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {name: after[name] - before[name] for name in before}


def _snapshot_files(runtime: dict) -> set[Path]:
    root = runtime["storage_dir"] / "artifacts" / "layer3"
    return {path for path in root.rglob("*") if path.is_file()} if root.exists() else set()


def _intake_record(runtime: dict, record_id: str) -> L3ConnectorSourceIntakeRecord:
    with runtime["factory"]() as db:
        record = db.get(L3ConnectorSourceIntakeRecord, record_id)
        assert record is not None
        db.expunge(record)
        return record


def _enable_step3(monkeypatch: pytest.MonkeyPatch, captured: list[dict]) -> None:
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    monkeypatch.setattr(pm, "attestation_precondition_available", lambda _candidate: True)
    monkeypatch.setattr(
        pm,
        "consume_gate_b_promotion_result",
        lambda result: captured.append(copy.deepcopy(result)),
    )


def _boom(*_args, **_kwargs):
    raise AssertionError("promotion branch must not be called")


def test_step3_duplicate_receipt_query_maps_to_basis_conflict() -> None:
    class DuplicateReceiptQuery:
        def filter(self, *_args):
            return self

        def one_or_none(self):
            raise MultipleResultsFound("duplicate receipt identity")

    class DuplicateReceiptDb:
        def query(self, *_args):
            return DuplicateReceiptQuery()

    with pytest.raises(pm.ConnectorPromotionError) as caught:
        pm._receipt_for_identity(DuplicateReceiptDb())
    assert (caught.value.code, caught.value.http_status, caught.value.retryable) == (
        "connector_promotion_basis_conflict",
        409,
        False,
    )


@pytest.mark.parametrize("shape", ["mixed", "multi", "other", "legacy"])
def test_step3_classifier_misses_bypass_new_side_effect_branches(shape: str) -> None:
    candidate = {
        "candidate_id": f"mat-connector_source_intake_record-{uuid.uuid4()}",
        "decision": "approved",
        "operator_reason": "",
        "decision_basis": {
            "source_identity": {
                "source_family": pm.F07_SOURCE_FAMILY,
                "content_sha256": pm.F07_CONTENT_SHA256,
                "connector_key": pm.F07_CONNECTOR_KEY,
            },
            "payload": {
                "source_class": pm.F07_SOURCE_FAMILY,
                "content_sha256": pm.F07_CONTENT_SHA256,
                "connector_key": pm.F07_CONNECTOR_KEY,
            },
        },
    }
    decisions = [candidate]
    if shape == "mixed":
        decisions.append({"candidate_id": "mat-dataset_version-other", "decision": "approved"})
    elif shape == "multi":
        duplicate = copy.deepcopy(candidate)
        duplicate["candidate_id"] = f"mat-connector_source_intake_record-{uuid.uuid4()}"
        decisions.append(duplicate)
    elif shape == "other":
        candidate["candidate_id"] = "mat-dataset_version-other"
    else:
        candidate["candidate_id"] = "legacy-material-candidate"
    assert pm.possible_gate_b_promotion_candidate(decisions) is None


def test_step3_classifier_miss_bypasses_new_branches_through_public_workbench(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "classifier-public")
    payload = _step3_payload(preview, "classifier-public")
    payload["candidate_decisions"].append(copy.deepcopy(payload["candidate_decisions"][0]))
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    for name in (
        "side_effect_free_server_exact_candidate",
        "attestation_precondition_available",
        "begin_gate_b_arbitration",
        "consume_gate_b_promotion_result",
    ):
        monkeypatch.setattr(pm, name, _boom)
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    with pytest.raises(Layer3WorkbenchError) as caught:
        _invoke_step3(b1b_step3_runtime, payload)
    assert caught.value.error_code == "duplicate_material_candidate_decision"
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


def test_step3_flag_false_exact_shape_preserves_gate_b_response_and_state(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "flag-false")
    for name in (
        "possible_gate_b_promotion_candidate",
        "side_effect_free_server_exact_candidate",
        "attestation_precondition_available",
        "begin_gate_b_arbitration",
        "consume_gate_b_promotion_result",
    ):
        monkeypatch.setattr(pm, name, _boom)
    before = _gate_b_census(b1b_step3_runtime)
    response = _invoke_step3(b1b_step3_runtime, _step3_payload(preview, "flag-false"))
    after = _gate_b_census(b1b_step3_runtime)
    assert set(response) == _PUBLIC_GATE_B_KEYS
    assert response["status"] == "ok"
    assert _gate_b_delta(before, after) == _GATE_B_SPINE_DELTA
    assert after["L3ConnectorPromotionReceipt"] == 0
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


# PostgreSQL execution is deliberately deferred to the isolated Section 10 provider.
# These are real case bodies: once the provider declares itself provisioned,
# absence of its fixture or any unequal fact fails closed instead of skipping.
_B1B_POSTGRES_URL = os.environ.get("LAYER3_MIGRATION_TEST_DATABASE_URL", "")
_B1B_POSTGRES_SCHEMA = os.environ.get("B1B_POSTGRESQL_TEST_SCHEMA", "")
_B1B_POSTGRES_PROVISIONED = os.environ.get("B1B_POSTGRESQL_STEP3_PROVISIONED") == "1"


def _b1b_psycopg_available() -> bool:
    try:
        import psycopg  # noqa: F401

        return True
    except ImportError:
        return False


_skip_b1b_postgresql = pytest.mark.skipif(
    not (
        _b1b_psycopg_available()
        and bool(_B1B_POSTGRES_URL)
        and bool(_B1B_POSTGRES_SCHEMA)
        and _B1B_POSTGRES_SCHEMA != "public"
        and _B1B_POSTGRES_PROVISIONED
    ),
    reason=(
        "B1b Step 3 PostgreSQL cases require the later isolated two-connection "
        "provider, psycopg, URL, and non-public pre-provisioned schema"
    ),
)


def _postgres_step3_case(request, case_id: str):
    factory = request.getfixturevalue("b1b_postgresql_step3_case")
    case = factory(case_id)
    assert case.case_id == case_id
    assert case.canonical_identity_key_hash == pm.F07_CANONICAL_IDENTITY_KEY_HASH
    assert case.two_independent_sessions is True
    assert case.schema_name == _B1B_POSTGRES_SCHEMA
    return case


@_skip_b1b_postgresql
def test_b1b_postgresql_equivalent_approval_uniqueness(request) -> None:
    case = _postgres_step3_case(request, "equivalent_approval_uniqueness")
    facts = case.run_equivalent_approval_uniqueness()
    assert tuple(facts) == (
        200,
        200,
        "created",
        "reused",
        1,
        1,
        7,
        1,
        0,
        0,
    )
    case.register_and_cleanup(facts)


@_skip_b1b_postgresql
def test_b1b_postgresql_race_approved_first(request) -> None:
    case = _postgres_step3_case(request, "race_approved_first")
    facts = case.run_race(winner="approved", contender="nonapproved")
    assert tuple(facts) == (
        200,
        409,
        "promotion_identity_decision_conflict",
        True,
        False,
        1,
        7,
        1,
        0,
        0,
        0,
    )
    case.register_and_cleanup(facts)


@_skip_b1b_postgresql
def test_b1b_postgresql_race_nonapproved_first(request) -> None:
    case = _postgres_step3_case(request, "race_nonapproved_first")
    facts = case.run_race(winner="nonapproved", contender="approved")
    assert tuple(facts) == (200, 200, True, True, 1, 6, 1, 7, 1, 0)
    case.register_and_cleanup(facts)


@_skip_b1b_postgresql
def test_b1b_postgresql_lock_timeout(request) -> None:
    case = _postgres_step3_case(request, "lock_timeout")
    facts = case.run_lock_timeout(lock_timeout_seconds=5)
    assert tuple(facts) == (
        503,
        "promotion_identity_lock_unavailable",
        0,
        0,
        0,
    )
    case.register_and_cleanup(facts)


def test_step3_flag_true_non_f07_stays_legacy_and_mints_no_receipt(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    non_f07 = b"site_id,value\nSB-001,44\nSB-002,45\n"
    non_f07_hash = hashlib.sha256(non_f07).hexdigest()
    b1b_step3_runtime["raw_path"].write_bytes(non_f07)
    with b1b_step3_runtime["factory"]() as db:
        target = db.get(ConnectorRunTarget, b1b_step3_runtime["target_id"])
        assert target is not None
        target.downloaded_sha256 = non_f07_hash
        db.commit()
    intake, preview = _capture_f07(b1b_step3_runtime, "non-f07")
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    for name in (
        "attestation_precondition_available",
        "begin_gate_b_arbitration",
        "consume_gate_b_promotion_result",
    ):
        monkeypatch.setattr(pm, name, _boom)
    response = _invoke_step3(b1b_step3_runtime, _step3_payload(preview, "non-f07"))
    assert set(response) == _PUBLIC_GATE_B_KEYS
    assert _gate_b_census(b1b_step3_runtime)["L3ConnectorPromotionReceipt"] == 0
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


@pytest.mark.parametrize(
    ("owner", "field", "near_miss"),
    [
        ("run", "source_system", "other"),
        ("run", "source_mode", "other"),
        ("run", "status", "completed"),
        ("target", "ordinal", 2),
        ("target", "sciencebase_item_url", "https://example.invalid/item"),
        ("target", "sciencebase_file_name", "other.csv"),
        ("target", "sciencebase_download_uri", "https://example.invalid/file"),
        ("target", "artifact_surface", "other"),
        ("target", "artifact_locator_type", "other"),
        ("target", "source_artifact_key", "other"),
        ("target", "public_read_confirmed", False),
        ("target", "status", "discovered"),
    ],
)
def test_step3_server_provenance_near_miss_stays_legacy(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    owner: str,
    field: str,
    near_miss: object,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, f"near-{owner}-{field}")
    with b1b_step3_runtime["factory"]() as db:
        row = db.get(
            ConnectorRun if owner == "run" else ConnectorRunTarget,
            b1b_step3_runtime["run_id" if owner == "run" else "target_id"],
        )
        assert row is not None
        setattr(row, field, near_miss)
        db.commit()
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    for name in (
        "attestation_precondition_available",
        "begin_gate_b_arbitration",
        "consume_gate_b_promotion_result",
    ):
        monkeypatch.setattr(pm, name, _boom)
    before = _gate_b_census(b1b_step3_runtime)
    response = _invoke_step3(
        b1b_step3_runtime,
        _step3_payload(preview, f"near-{owner}-{field}"),
    )
    after = _gate_b_census(b1b_step3_runtime)
    assert set(response) == _PUBLIC_GATE_B_KEYS
    assert _gate_b_delta(before, after) == _GATE_B_SPINE_DELTA
    assert after["L3ConnectorPromotionReceipt"] == 0
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


def test_step3_request_basis_cannot_bypass_server_exact_scope(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "server-scope")
    payload = _step3_payload(preview, "server-scope")
    payload["candidate_decisions"][0]["decision_basis"]["source_identity"][
        "content_sha256"
    ] = "0" * 64
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    before = _gate_b_census(b1b_step3_runtime)
    with pytest.raises(Layer3WorkbenchError) as caught:
        _invoke_step3(b1b_step3_runtime, payload)
    assert (caught.value.error_code, caught.value.http_status) == (
        "connector_promotion_bridge_unavailable",
        503,
    )
    assert _gate_b_census(b1b_step3_runtime) == before
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


def test_step3_attestation_unavailable_is_503_with_zero_mutation(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "attestation")
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    with pytest.raises(Layer3WorkbenchError) as caught:
        _invoke_step3(b1b_step3_runtime, _step3_payload(preview, "attestation"))
    assert (
        caught.value.error_code,
        caught.value.message,
        caught.value.http_status,
        caught.value.recoverable,
    ) == (
        "connector_promotion_bridge_unavailable",
        "Connector promotion bridge is unavailable.",
        503,
        True,
    )
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


def test_step3_mints_exact_receipt_and_populates_identity_pair(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "mint")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    response = _invoke_step3(b1b_step3_runtime, _step3_payload(preview, "mint"))
    after = _gate_b_census(b1b_step3_runtime)
    assert set(response) == _PUBLIC_GATE_B_KEYS
    assert _gate_b_delta(before, after) == _GATE_B_MINT_DELTA
    assert len(_snapshot_files(b1b_step3_runtime) - files_before) == 1
    assert len(captured) == 1 and set(captured[0]) == {
        "candidate_id",
        "decision",
        "receipt_disposition",
        "connector_promotion_receipt_id",
    }
    assert captured[0]["decision"] == "approved"
    assert captured[0]["receipt_disposition"] == "created"

    with b1b_step3_runtime["factory"]() as db:
        receipt = db.query(L3ConnectorPromotionReceipt).one()
        record = db.get(
            L3ConnectorSourceIntakeRecord,
            intake["connector_source_intake_record_id"],
        )
        assert record is not None
        assert receipt.connector_promotion_receipt_id == captured[0]["connector_promotion_receipt_id"]
        assert (
            receipt.receipt_schema_version,
            receipt.identity_metadata_hash_version,
            receipt.source_family,
            receipt.content_sha256,
            receipt.identity_metadata_hash,
            receipt.canonical_identity_key_hash,
        ) == (
            pm.RECEIPT_SCHEMA_VERSION,
            pm.IDENTITY_METADATA_HASH_VERSION,
            pm.F07_SOURCE_FAMILY,
            pm.F07_CONTENT_SHA256,
            pm.F07_IDENTITY_METADATA_HASH,
            pm.F07_CANONICAL_IDENTITY_KEY_HASH,
        )
        assert receipt.approval_hash == pm.decision_semantics_hash(
            "approved",
            pm.IDENTITY_METADATA_HASH_VERSION,
            pm.F07_SOURCE_FAMILY,
            pm.F07_CONTENT_SHA256,
            pm.F07_IDENTITY_METADATA_HASH,
        )
        session = db.get(L3Session, receipt.gate_b_session_id)
        manifest = db.get(L3SelectionManifest, receipt.gate_b_selection_manifest_id)
        snapshot = db.get(L3MaterialSnapshot, receipt.gate_b_material_snapshot_id)
        assert session is not None and manifest is not None and snapshot is not None
        decision_manifest = session.operator_context_json["layer3_gate_b_decision_manifest_v1"]
        assert (
            receipt.connector_source_intake_record_id,
            receipt.gate_b_session_id,
            receipt.gate_b_selection_manifest_id,
            receipt.gate_b_material_snapshot_id,
            manifest.session_id,
            snapshot.session_id,
            receipt.gate_b_decision_manifest_id,
            receipt.gate_b_decision_manifest_hash,
            receipt.material_preview_hash,
        ) == (
            intake["connector_source_intake_record_id"],
            response["session_id"],
            response["selection_manifest_id"],
            snapshot.material_snapshot_id,
            session.session_id,
            session.session_id,
            pm.gate_b_decision_manifest_id(decision_manifest),
            stable_hash(decision_manifest),
            preview["material_preview_hash"],
        )
        assert receipt.promotion_basis_hash == pm.promotion_basis_hash(
            approval_hash=receipt.approval_hash,
            gate_b_session_id=receipt.gate_b_session_id,
            gate_b_selection_manifest_id=receipt.gate_b_selection_manifest_id,
            gate_b_material_snapshot_id=receipt.gate_b_material_snapshot_id,
            gate_b_decision_manifest_id=receipt.gate_b_decision_manifest_id,
            gate_b_decision_manifest_hash=receipt.gate_b_decision_manifest_hash,
            material_preview_hash=receipt.material_preview_hash,
            canonical_identity_key_hash=receipt.canonical_identity_key_hash,
            identity_metadata_hash_version=receipt.identity_metadata_hash_version,
            source_family=receipt.source_family,
            content_sha256=receipt.content_sha256,
            identity_metadata_hash=receipt.identity_metadata_hash,
            connector_source_intake_record_id=receipt.connector_source_intake_record_id,
        )
        assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (
            pm.IDENTITY_METADATA_HASH_VERSION,
            pm.F07_IDENTITY_METADATA_HASH,
        )


def _receipt_state(runtime: dict) -> tuple:
    with runtime["factory"]() as db:
        receipt = db.query(L3ConnectorPromotionReceipt).one()
        return tuple(getattr(receipt, column) for column in EXPECTED_COLUMNS)


def test_step3_equivalent_approval_reuses_winning_receipt_without_update(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_intake, first_preview = _capture_f07(b1b_step3_runtime, "reuse-first")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    first_payload = _step3_payload(first_preview, "reuse-first")
    first_response = _invoke_step3(b1b_step3_runtime, first_payload)
    winning_state = _receipt_state(b1b_step3_runtime)
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)

    captured.clear()
    replay_response = _invoke_step3(b1b_step3_runtime, first_payload)
    assert replay_response["status"] == "already_committed"
    assert replay_response["session_id"] == first_response["session_id"]
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert captured == [
        {
            "candidate_id": first_preview["material_candidate"]["candidate_id"],
            "decision": "approved",
            "receipt_disposition": "reused",
            "connector_promotion_receipt_id": winning_state[0],
        }
    ]

    second_intake, second_preview = _capture_f07(b1b_step3_runtime, "reuse-second")
    captured.clear()
    second_response = _invoke_step3(
        b1b_step3_runtime,
        _step3_payload(second_preview, "reuse-second"),
    )
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert _receipt_state(b1b_step3_runtime) == winning_state
    assert second_response["session_id"] == first_response["session_id"]
    assert second_response["selection_manifest_id"] == first_response["selection_manifest_id"]
    assert set(second_response) == _PUBLIC_GATE_B_KEYS
    assert captured == [
        {
            "candidate_id": second_preview["material_candidate"]["candidate_id"],
            "decision": "approved",
            "receipt_disposition": "reused",
            "connector_promotion_receipt_id": winning_state[0],
        }
    ]
    assert _intake_record(
        b1b_step3_runtime,
        first_intake["connector_source_intake_record_id"],
    ).identity_metadata_hash == pm.F07_IDENTITY_METADATA_HASH
    second_record = _intake_record(
        b1b_step3_runtime,
        second_intake["connector_source_intake_record_id"],
    )
    assert (second_record.identity_metadata_hash_version, second_record.identity_metadata_hash) == (
        None,
        None,
    )


def test_step3_legacy_idempotency_replay_returns_receipt_winning_origin(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_intake, legacy_preview = _capture_f07(b1b_step3_runtime, "legacy-replay")
    legacy_payload = _step3_payload(legacy_preview, "legacy-replay")
    legacy_response = _invoke_step3(b1b_step3_runtime, legacy_payload)

    winning_intake, winning_preview = _capture_f07(b1b_step3_runtime, "winner")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    winning_response = _invoke_step3(
        b1b_step3_runtime,
        _step3_payload(winning_preview, "winner"),
    )
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    receipt_id = _receipt_state(b1b_step3_runtime)[0]

    captured.clear()
    replay_response = _invoke_step3(b1b_step3_runtime, legacy_payload)
    assert replay_response["status"] == "already_committed"
    assert replay_response["session_id"] == winning_response["session_id"]
    assert replay_response["session_id"] != legacy_response["session_id"]
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert captured == [
        {
            "candidate_id": legacy_preview["material_candidate"]["candidate_id"],
            "decision": "approved",
            "receipt_disposition": "reused",
            "connector_promotion_receipt_id": receipt_id,
        }
    ]
    assert _intake_record(
        b1b_step3_runtime,
        legacy_intake["connector_source_intake_record_id"],
    ).identity_metadata_hash is None
    assert _intake_record(
        b1b_step3_runtime,
        winning_intake["connector_source_intake_record_id"],
    ).identity_metadata_hash == pm.F07_IDENTITY_METADATA_HASH


def test_step3_reuse_rejects_prepopulated_nonwinning_identity_pair(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, first_preview = _capture_f07(b1b_step3_runtime, "pair-first")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    _invoke_step3(b1b_step3_runtime, _step3_payload(first_preview, "pair-first"))
    winning_state = _receipt_state(b1b_step3_runtime)

    second_intake, second_preview = _capture_f07(b1b_step3_runtime, "pair-second")
    with b1b_step3_runtime["factory"]() as db:
        record = db.get(
            L3ConnectorSourceIntakeRecord,
            second_intake["connector_source_intake_record_id"],
        )
        assert record is not None
        record.identity_metadata_hash_version = pm.IDENTITY_METADATA_HASH_VERSION
        record.identity_metadata_hash = pm.F07_IDENTITY_METADATA_HASH
        db.commit()
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    captured.clear()
    with pytest.raises(Layer3WorkbenchError) as caught:
        _invoke_step3(
            b1b_step3_runtime,
            _step3_payload(second_preview, "pair-second"),
        )
    assert (caught.value.error_code, caught.value.http_status, caught.value.recoverable) == (
        "connector_promotion_not_eligible",
        409,
        False,
    )
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert _receipt_state(b1b_step3_runtime) == winning_state
    assert captured == []


@pytest.mark.parametrize(
    ("corruption", "decision"),
    [
        ("receipt_hash", "approved"),
        ("receipt_hash", "denied"),
        ("idempotency_link", "approved"),
        ("descriptor_link", "approved"),
        ("event_link", "approved"),
        ("snapshot_identity", "approved"),
        ("extra_event", "approved"),
        ("malformed_context", "approved"),
        ("malformed_payload_ref", "approved"),
    ],
)
def test_step3_corrupt_stored_basis_rejected_without_new_state(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
    decision: str,
) -> None:
    _, first_preview = _capture_f07(b1b_step3_runtime, "corrupt-first")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    _invoke_step3(b1b_step3_runtime, _step3_payload(first_preview, "corrupt-first"))
    with b1b_step3_runtime["factory"]() as db:
        if corruption == "receipt_hash":
            db.query(L3ConnectorPromotionReceipt).one().promotion_basis_hash = "0" * 64
        elif corruption == "idempotency_link":
            db.query(L3GateBIdempotencyKey).one().selection_manifest_id = None
        elif corruption == "descriptor_link":
            db.query(L3Descriptor).one().status = "failed"
        elif corruption == "event_link":
            db.query(L3RetrievalEvent).one().material_snapshot_ids_json = []
        elif corruption == "snapshot_identity":
            db.query(L3MaterialSnapshot).one().source_identity_json = {
                "candidate_id": "wrong"
            }
        elif corruption == "extra_event":
            event = db.query(L3RetrievalEvent).one()
            db.add(
                L3RetrievalEvent(
                    session_id=event.session_id,
                    descriptor_id=event.descriptor_id,
                    outcome="failed",
                    reason_code="corrupt_duplicate_event",
                    material_snapshot_ids_json=[],
                    event_payload_json={},
                )
            )
        elif corruption == "malformed_context":
            db.query(L3Session).one().operator_context_json = []
        else:
            db.query(L3MaterialSnapshot).one().payload_ref = "\x00"
        db.commit()
    _, second_preview = _capture_f07(b1b_step3_runtime, "corrupt-second")
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    with pytest.raises(Layer3WorkbenchError) as caught:
        _invoke_step3(
            b1b_step3_runtime,
            _step3_payload(second_preview, "corrupt-second", decision=decision),
        )
    assert (caught.value.error_code, caught.value.http_status, caught.value.recoverable) == (
        "connector_promotion_basis_conflict",
        409,
        False,
    )
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before


def test_step3_nonapproved_commits_six_row_spine_without_receipt(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "denied")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    response = _invoke_step3(
        b1b_step3_runtime,
        _step3_payload(preview, "denied", decision="denied"),
    )
    after = _gate_b_census(b1b_step3_runtime)
    assert set(response) == _PUBLIC_GATE_B_KEYS
    assert response["denied_candidate_ids"] == [preview["material_candidate"]["candidate_id"]]
    assert response["next_state"] == "gate_b_decision_recorded"
    assert response["authority_rail"]["current_gate"] == "gate_b"
    assert _gate_b_delta(before, after) == _GATE_B_SPINE_DELTA
    assert after["L3ConnectorPromotionReceipt"] == 0
    assert len(_snapshot_files(b1b_step3_runtime) - files_before) == 1
    assert captured == [
        {
            "candidate_id": preview["material_candidate"]["candidate_id"],
            "decision": "denied",
            "receipt_disposition": "none",
            "connector_promotion_receipt_id": None,
        }
    ]
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


def test_step3_public_wrapper_releases_lock_after_ordinary_post_lock_error(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "wrapper-cleanup")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)

    def raise_post_lock_error(*_args, **_kwargs):
        raise Layer3WorkbenchError(
            "post_lock_probe",
            "Ordinary post-lock failure for wrapper cleanup proof.",
            status="blocked",
        )

    monkeypatch.setattr(
        layer3_workbench,
        "find_gate_b_idempotency_session",
        raise_post_lock_error,
    )
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        with pytest.raises(Layer3WorkbenchError) as caught:
            layer3_workbench.gate_b_decision(
                db,
                _step3_payload(preview, "wrapper-cleanup"),
            )
        assert caught.value.error_code == "post_lock_probe"
        assert not db.in_transaction()
        assert "b1b_promotion_identity_lock" not in db.info
        pm.acquire_promotion_identity_lock(db)
        assert db.info["b1b_promotion_identity_lock"] == pm.F07_CANONICAL_IDENTITY_KEY_HASH
        db.rollback()
        db.info.pop("b1b_promotion_identity_lock", None)
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert captured == []
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


def test_step3_divergent_decision_rolls_back_without_partial_state(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, first_preview = _capture_f07(b1b_step3_runtime, "diverge-first")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    _invoke_step3(b1b_step3_runtime, _step3_payload(first_preview, "diverge-first"))
    winning_state = _receipt_state(b1b_step3_runtime)
    second_intake, second_preview = _capture_f07(b1b_step3_runtime, "diverge-second")
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    captured.clear()
    with b1b_step3_runtime["factory"]() as db:
        with pytest.raises(Layer3WorkbenchError) as caught:
            layer3_workbench.gate_b_decision(
                db,
                _step3_payload(second_preview, "diverge-second", decision="denied"),
            )
        assert not db.in_transaction()
        assert "b1b_promotion_identity_lock" not in db.info
        pm.acquire_promotion_identity_lock(db)
        assert db.info["b1b_promotion_identity_lock"] == pm.F07_CANONICAL_IDENTITY_KEY_HASH
        db.rollback()
        db.info.pop("b1b_promotion_identity_lock", None)
    assert (
        caught.value.error_code,
        caught.value.message,
        caught.value.http_status,
        caught.value.recoverable,
    ) == (
        "promotion_identity_decision_conflict",
        "Promotion identity decision conflicts with the committed receipt.",
        409,
        False,
    )
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert _receipt_state(b1b_step3_runtime) == winning_state
    assert captured == []
    second_record = _intake_record(
        b1b_step3_runtime,
        second_intake["connector_source_intake_record_id"],
    )
    assert (second_record.identity_metadata_hash_version, second_record.identity_metadata_hash) == (
        None,
        None,
    )


def test_step3_sqlite_second_connection_lock_timeout_is_503_zero_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, preview = _capture_f07(b1b_step3_runtime, "sqlite-timeout")
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    before = _gate_b_census(b1b_step3_runtime)
    files_before = _snapshot_files(b1b_step3_runtime)
    blocker = b1b_step3_runtime["engine"].connect()
    try:
        blocker.exec_driver_sql("PRAGMA busy_timeout=5000")
        blocker.exec_driver_sql("BEGIN IMMEDIATE")
        with pytest.raises(Layer3WorkbenchError) as caught:
            _invoke_step3(
                b1b_step3_runtime,
                _step3_payload(preview, "sqlite-timeout"),
            )
        assert (
            caught.value.error_code,
            caught.value.message,
            caught.value.http_status,
            caught.value.recoverable,
        ) == (
            "promotion_identity_lock_unavailable",
            "Promotion identity lock is unavailable.",
            503,
            True,
        )
    finally:
        blocker.rollback()
        blocker.close()
    assert _gate_b_census(b1b_step3_runtime) == before
    assert _snapshot_files(b1b_step3_runtime) == files_before
    assert captured == []
    record = _intake_record(b1b_step3_runtime, intake["connector_source_intake_record_id"])
    assert (record.identity_metadata_hash_version, record.identity_metadata_hash) == (None, None)


# ---------------------------------------------------------------------------
# Durable materialization and closed resolver route (B1b-01 step 5)
# ---------------------------------------------------------------------------

_MATERIALIZATION_MODELS = (
    SourceConnector,
    Dataset,
    DatasetVersion,
    VariableDefinition,
    DatasetSourceProvenance,
    DatasetRow,
    L3TypingRecord,
    L3AnalysisUnit,
    L3AnalysisGroup,
    L3AnalysisSet,
    L3Session,
    L3SelectionManifest,
    L3Descriptor,
    L3RetrievalEvent,
    L3MaterialSnapshot,
)
_B1B_03_ROW_CONTRACT_MODELS = (
    ConnectorRun,
    ConnectorRunTarget,
    L3ConnectorSourceIntakeRecord,
    L3GateBIdempotencyKey,
    L3Session,
    L3SelectionManifest,
    L3Descriptor,
    L3RetrievalEvent,
    L3MaterialSnapshot,
    L3ConnectorPromotionReceipt,
    SourceConnector,
    Dataset,
    DatasetVersion,
    VariableDefinition,
    DatasetSourceProvenance,
    DatasetRow,
    L3TypingRecord,
    L3AnalysisUnit,
    L3AnalysisGroup,
    L3AnalysisSet,
    L3AnalysisPlan,
    L3PassRun,
    AnalysisRun,
    AssumptionCheck,
    AnalysisArtifact,
    CaveatNote,
    L3ReconciliationRecord,
    L3OutputPackage,
)
_SESSION_CHAIN_MODELS = (
    L3Session,
    L3SelectionManifest,
    L3Descriptor,
    L3RetrievalEvent,
    L3MaterialSnapshot,
    L3TypingRecord,
    L3AnalysisUnit,
    L3AnalysisGroup,
    L3AnalysisSet,
)
_RESOLVE_KEYS = {
    "approval_hash",
    "canonical_identity_key_hash",
    "connector_promotion_receipt_id",
    "dataset_id",
    "dataset_version_id",
    "disposition",
    "gate_b_session_id",
    "materialization_basis_hash",
    "materialization_record_hash",
    "promoted_session_id",
    "promotion_basis_hash",
    "row_count",
    "schema_id",
    "source_row_count",
    "variable_count",
}
_FIXED_CODE_IDENTITY = {
    "implementation_commit": "1" * 40,
    "promotion_git_blob": "2" * 40,
    "ingest_git_blob": "3" * 40,
    "dataframe_io_git_blob": "4" * 40,
}


def _enable_step5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    monkeypatch.setattr(pm, "attestation_precondition_available", lambda _candidate=None: True)
    monkeypatch.setattr(
        pm,
        "_read_clean_materialization_code_identity",
        lambda: dict(_FIXED_CODE_IDENTITY),
    )


def _seed_materializable_receipt(
    runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    stem: str,
) -> str:
    _, preview = _capture_f07(runtime, stem)
    captured: list[dict] = []
    _enable_step3(monkeypatch, captured)
    response = _invoke_step3(runtime, _step3_payload(preview, stem))
    assert captured[0]["receipt_disposition"] == "created"
    return response["session_id"]


def _materialization_census(runtime: dict) -> dict[str, int]:
    with runtime["factory"]() as db:
        return {model.__name__: db.query(model).count() for model in _MATERIALIZATION_MODELS}


def _b1b_03_row_census(runtime: dict) -> dict[str, int]:
    with runtime["factory"]() as db:
        return {model.__name__: db.query(model).count() for model in _B1B_03_ROW_CONTRACT_MODELS}


def _project_query_rows(query, model) -> list[dict[str, object]]:
    primary_key = list(model.__table__.primary_key.columns)
    return [
        {
            column.name: copy.deepcopy(getattr(row, column.name))
            for column in model.__table__.columns
        }
        for row in query.order_by(*primary_key).all()
    ]


def _b1b_03_row_projection(runtime: dict) -> dict[str, list[dict[str, object]]]:
    with runtime["factory"]() as db:
        return {
            model.__name__: _project_query_rows(db.query(model), model)
            for model in _B1B_03_ROW_CONTRACT_MODELS
        }


def _session_chain_projection(runtime: dict, session_id: str) -> dict[str, list[dict[str, object]]]:
    with runtime["factory"]() as db:
        return {
            model.__name__: _project_query_rows(
                db.query(model).filter(model.session_id == session_id),
                model,
            )
            for model in _SESSION_CHAIN_MODELS
        }


def _all_storage_files(runtime: dict) -> dict[str, tuple[int, str]]:
    root = runtime["storage_dir"]
    return {
        path.relative_to(root).as_posix(): (len(data), _hashlib.sha256(data).hexdigest())
        for path in sorted(root.rglob("*"))
        if path.is_file()
        for data in [path.read_bytes()]
    }


def _session_chain_census(runtime: dict, session_id: str) -> dict[str, int]:
    with runtime["factory"]() as db:
        return {
            model.__name__: db.query(model).filter(model.session_id == session_id).count()
            for model in _SESSION_CHAIN_MODELS
        }


def _lane_files(runtime: dict) -> dict[str, tuple[int, str]]:
    root = runtime["storage_dir"]
    files: dict[str, tuple[int, str]] = {}
    for lane_root in (
        root / "datasets" / "b1b",
        root / "artifacts" / "layer3" / "b1b",
        root / "artifacts" / "layer3" / "b1b-staging",
        root / "artifacts" / "layer3" / "b1b-containment",
    ):
        if not lane_root.exists():
            continue
        for path in lane_root.rglob("*"):
            if path.is_file():
                data = path.read_bytes()
                files[path.relative_to(root).as_posix()] = (len(data), _hashlib.sha256(data).hexdigest())
    return files


def _assert_exact_containment_ledgers(runtime: dict) -> list[tuple[Path, dict[str, object]]]:
    pairs: list[tuple[Path, dict[str, object]]] = []
    roots = (
        runtime["storage_dir"] / "datasets" / "b1b" / "containment",
        runtime["storage_dir"] / "artifacts" / "layer3" / "b1b-containment",
    )
    for root in roots:
        if not root.exists():
            continue
        files = {path for path in root.rglob("*") if path.is_file()}
        artifacts = {
            path for path in files if not path.name.endswith(pm._CONTAINMENT_RECORD_SUFFIX)
        }
        records = files - artifacts
        assert records == {pm._containment_record_path(path) for path in artifacts}
        for artifact in sorted(artifacts):
            record = json.loads(pm._containment_record_path(artifact).read_bytes())
            data = artifact.read_bytes()
            assert record["artifact_bytes"] == len(data)
            assert record["artifact_sha256"] == _hashlib.sha256(data).hexdigest()
            assert record["basis_hash"] == artifact.parent.name
            assert record["status"] == "non_authoritative_non_reusable"
            pairs.append((artifact, record))
    return pairs


def _target_projection(runtime: dict) -> dict[str, object]:
    with runtime["factory"]() as db:
        target = db.get(ConnectorRunTarget, runtime["target_id"])
        assert target is not None
        return {column.name: copy.deepcopy(getattr(target, column.name)) for column in target.__table__.columns}


def _resolve(runtime: dict, gate_b_session_id: str) -> dict:
    with runtime["factory"]() as db:
        return pm.resolve_connector_promotion(db, gate_b_session_id=gate_b_session_id)


def _materialize_replay_subject(
    runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    stem: str,
) -> tuple[str, dict]:
    gate_b_session_id = _seed_materializable_receipt(runtime, monkeypatch, stem)
    _enable_step5(monkeypatch)
    return gate_b_session_id, _resolve(runtime, gate_b_session_id)


def _replay_summary_contract_valid(db, promoted_session_id: str) -> bool:
    promoted = db.get(L3Session, promoted_session_id)
    receipt = (
        db.query(L3ConnectorPromotionReceipt)
        .filter_by(promoted_session_id=promoted_session_id)
        .one()
    )
    assert promoted is not None
    return pm._materialized_replay_summary_is_valid(
        db,
        receipt=receipt,
        promoted=promoted,
    )


def _approve_replay_subject(db, promoted_session_id: str, stem: str) -> tuple[dict, dict]:
    preview = layer3_workbench.plan_preview(
        db,
        {
            "client_request_id": f"{stem}-preview",
            "session_id": promoted_session_id,
        },
    )
    approval = layer3_workbench.plan_approval(
        db,
        {
            "client_request_id": f"{stem}-approval",
            "session_id": promoted_session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_confirmation": True,
        },
    )
    return preview, approval


def _select_replay_subject(
    db,
    promoted_session_id: str,
    stem: str,
    preview: dict,
    approval: dict,
) -> dict:
    return layer3_workbench.execution_selection(
        db,
        {
            "client_request_id": f"{stem}-selection",
            "session_id": promoted_session_id,
            "analysis_plan_id": approval["analysis_plan_id"],
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
    )


def _start_replay_subject(
    db,
    promoted_session_id: str,
    stem: str,
    preview: dict,
    approval: dict,
    selection: dict,
) -> dict:
    return layer3_workbench.analysis_execution_start(
        db,
        {
            "client_request_id": f"{stem}-start",
            "session_id": promoted_session_id,
            "analysis_plan_id": approval["analysis_plan_id"],
            "pass_run_id": selection["pass_run_ids"][0],
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
    )


_RESULT_REVIEW_STATE_BY_DECISION = {
    "approved": "execution_result_review_approved",
    "changes_requested": "execution_result_review_changes_requested",
    "rejected": "execution_result_review_rejected",
    "blocked": "execution_result_review_blocked",
}
_PACKAGE_REVIEW_STATE_BY_DECISION = {
    "approved": "package_review_approved",
    "changes_requested": "package_review_changes_requested",
    "rejected": "package_review_rejected",
    "blocked": "package_review_blocked",
}
_PACKAGE_ORDER = ("canonical_internal", "user_facing", "review_facing")


def _install_closed_result_review(db, receipt, promoted, decision: str) -> dict:
    plan = db.query(L3AnalysisPlan).filter_by(session_id=promoted.session_id).one()
    pass_run = db.query(L3PassRun).filter_by(session_id=promoted.session_id).one()
    analysis_run = db.get(AnalysisRun, pass_run.summary_json["analysis_run_id"])
    artifact = db.query(AnalysisArtifact).filter_by(analysis_run_id=analysis_run.analysis_run_id).one()
    checks = (
        db.query(AssumptionCheck)
        .filter_by(analysis_run_id=analysis_run.analysis_run_id)
        .order_by(AssumptionCheck.assumption_check_id)
        .all()
    )
    caveat = db.query(CaveatNote).filter_by(analysis_run_id=analysis_run.analysis_run_id).one()
    review_notes = None if decision == "approved" else f"{decision} note"
    record = {
        "schema_id": "layer3.b1b_result_review_record.v1",
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session_id": promoted.session_id,
        "analysis_plan_id": plan.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_id": plan.plan_json["source_preview_id"],
        "preview_hash": plan.plan_json["source_preview_hash"],
        "analysis_run_id": analysis_run.analysis_run_id,
        "result_payload_sha256": "a" * 64,
        "analysis_artifact_id": artifact.artifact_id,
        "analysis_artifact_sha256": "b" * 64,
        "assumption_check_ids": [row.assumption_check_id for row in checks],
        "caveat_note_id": caveat.caveat_note_id,
        "reviewed_output_items": [
            {
                "index": 0,
                "item_ref": f"analysis-artifact:{artifact.artifact_id}",
                "item_type": "fact",
                "trace_status": "resolved",
                "missing_trace_fields": [],
            },
            {
                "index": 1,
                "item_ref": f"caveat:{caveat.caveat_note_id}",
                "item_type": "caveat",
                "trace_status": "resolved",
                "missing_trace_fields": [],
            },
        ],
        "unresolved_trace_count": 0,
        "operator_decision": decision,
        "review_notes": review_notes,
        "result_review_request_basis_hash": "c" * 64,
    }
    result_review_hash = pm.d33_sha256(record)
    review_record_ref = f"b1b-result-review-{result_review_hash}"
    review_state = _RESULT_REVIEW_STATE_BY_DECISION[decision]
    pass_run.summary_json = {
        **copy.deepcopy(pass_run.summary_json),
        "execution_result_review": {
            **record,
            "review_record_ref": review_record_ref,
            "review_state": review_state,
            "result_review_hash": result_review_hash,
        },
    }
    promoted.summary_json = {
        "schema_id": "layer3.b1b_session_state.v1",
        "review_record_ref": review_record_ref,
        "review_state": review_state,
        "result_review_hash": result_review_hash,
        "analysis_plan_id": plan.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "analysis_run_id": analysis_run.analysis_run_id,
        "package_review_state": None,
        "package_review_hash": None,
        "reconciliation_record_id": None,
        "packages": None,
        "connector_dataset_handoff_basis_hash": None,
    }
    db.flush()
    return copy.deepcopy(promoted.summary_json)


def _install_closed_package_review(db, receipt, promoted, decision: str) -> dict:
    result_state = _install_closed_result_review(db, receipt, promoted, "approved")
    reconciliation = db.query(L3ReconciliationRecord).filter_by(session_id=promoted.session_id).one_or_none()
    if reconciliation is None:
        reconciliation = L3ReconciliationRecord(
            reconciliation_record_id=str(uuid.uuid4()),
            session_id=promoted.session_id,
            status="reconciled",
            summary_json={},
        )
        db.add(reconciliation)
        db.flush()
        for index, package_kind in enumerate(_PACKAGE_ORDER):
            db.add(
                L3OutputPackage(
                    output_package_id=str(uuid.uuid4()),
                    session_id=promoted.session_id,
                    reconciliation_record_id=reconciliation.reconciliation_record_id,
                    package_kind=package_kind,
                    status="package_complete",
                    payload_ref=f"b1b://package/{package_kind}",
                    payload_hash=str(index + 1) * 64,
                    summary_json={},
                )
            )
        db.flush()
    rows = {
        row.package_kind: row
        for row in db.query(L3OutputPackage).filter_by(session_id=promoted.session_id).all()
    }
    packages = [
        {
            "package_kind": kind,
            "output_package_id": rows[kind].output_package_id,
            "payload_sha256": rows[kind].payload_hash,
        }
        for kind in _PACKAGE_ORDER
    ]
    package_set = {
        "construction_basis_hash": "d" * 64,
        "member_count": 9,
        "bundle_index_order_hash": "e" * 64,
        "package_manifest_sha256": "f" * 64,
        "package_rehash_sha256": "0" * 64,
        "packages": [
            {**item, "payload_bytes": 1000 + index}
            for index, item in enumerate(packages)
        ],
    }
    package_record = {
        "schema_id": "layer3.b1b_package_review_record.v1",
        "review_request_basis_hash": "1" * 64,
        "package_review_preview_hash": "2" * 64,
        "construction_basis_hash": package_set["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_package_ids": [item["output_package_id"] for item in packages],
        "package_kinds": [item["package_kind"] for item in packages],
        "payload_hashes": [item["payload_sha256"] for item in packages],
        "operator_decision": decision,
        "decision_notes": None if decision == "approved" else f"{decision} note",
    }
    package_review_hash = pm.d33_sha256(package_record)
    handoff_basis = None
    handoff_hash = None
    if decision == "approved":
        handoff_basis = {
            "approved_reviews": {
                "package_review_hash": package_review_hash,
                "result_review_hash": result_state["result_review_hash"],
            },
            "canonical_internal": {
                "byte_length": package_set["packages"][0]["payload_bytes"],
                "output_package_id": packages[0]["output_package_id"],
                "payload_hash": packages[0]["payload_sha256"],
            },
            "package_set": {
                "reconciliation_record_id": reconciliation.reconciliation_record_id,
                "review_facing_output_package_id": packages[2]["output_package_id"],
                "review_facing_payload_hash": packages[2]["payload_sha256"],
                "user_facing_output_package_id": packages[1]["output_package_id"],
                "user_facing_payload_hash": packages[1]["payload_sha256"],
            },
            "promoted_session_id": promoted.session_id,
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "schema_id": "layer3.connector_dataset_handoff_basis.v1",
        }
        handoff_hash = pm.d33_sha256(handoff_basis)
    reconciliation.summary_json = {
        "schema_id": "layer3.b1b_reconciliation_summary.v1",
        "profile": "receipt_bound_b1b",
        "source_gate": "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE",
        "promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "promoted_session_id": promoted.session_id,
        "result_review_hash": result_state["result_review_hash"],
        "package_review_preview_hash": package_record["package_review_preview_hash"],
        "package_set": package_set,
        "package_review_submit": package_record,
        "package_review_hash": package_review_hash,
        "connector_dataset_handoff_basis": handoff_basis,
        "connector_dataset_handoff_basis_hash": handoff_hash,
    }
    promoted.summary_json = {
        **result_state,
        "package_review_state": _PACKAGE_REVIEW_STATE_BY_DECISION[decision],
        "package_review_hash": package_review_hash,
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "packages": packages,
        "connector_dataset_handoff_basis_hash": handoff_hash,
    }
    db.flush()
    return copy.deepcopy(promoted.summary_json)


def test_closed_replay_contract_accepts_all_staged_success_progressions(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _gate_b_session_id, resolved = _materialize_replay_subject(
        b1b_step3_runtime,
        monkeypatch,
        "closed-success",
    )
    promoted_session_id = resolved["promoted_session_id"]
    with b1b_step3_runtime["factory"]() as db:
        assert _replay_summary_contract_valid(db, promoted_session_id)
        preview, approval = _approve_replay_subject(db, promoted_session_id, "closed-success")
        assert _replay_summary_contract_valid(db, promoted_session_id)
        selection = _select_replay_subject(
            db,
            promoted_session_id,
            "closed-success",
            preview,
            approval,
        )
        assert _replay_summary_contract_valid(db, promoted_session_id)
        start = _start_replay_subject(
            db,
            promoted_session_id,
            "closed-success",
            preview,
            approval,
            selection,
        )
        assert start["pass_run_status"] == "completed_with_warnings"
        assert _replay_summary_contract_valid(db, promoted_session_id)


def test_closed_replay_contract_accepts_failed_terminal_and_replay_is_inert(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id, resolved = _materialize_replay_subject(
        b1b_step3_runtime,
        monkeypatch,
        "closed-failed",
    )
    promoted_session_id = resolved["promoted_session_id"]
    with b1b_step3_runtime["factory"]() as db:
        preview, approval = _approve_replay_subject(db, promoted_session_id, "closed-failed")
        selection = _select_replay_subject(
            db,
            promoted_session_id,
            "closed-failed",
            preview,
            approval,
        )

        def _fail_analysis(*_args, **_kwargs):
            raise RuntimeError("expected closed replay failure")

        monkeypatch.setattr(layer3_pass_entry, "run_analysis", _fail_analysis)
        start = _start_replay_subject(
            db,
            promoted_session_id,
            "closed-failed",
            preview,
            approval,
            selection,
        )
        assert start["pass_run_status"] == "failed"
        assert db.query(AnalysisRun).count() == 0
        assert _replay_summary_contract_valid(db, promoted_session_id)
    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    assert _resolve(b1b_step3_runtime, gate_b_session_id) == {
        **resolved,
        "disposition": "reused",
    }
    assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
    assert _all_storage_files(b1b_step3_runtime) == files_before


def test_closed_replay_contract_accepts_all_result_and_package_decision_states(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _gate_b_session_id, resolved = _materialize_replay_subject(
        b1b_step3_runtime,
        monkeypatch,
        "closed-reviews",
    )
    promoted_session_id = resolved["promoted_session_id"]
    with b1b_step3_runtime["factory"]() as db:
        preview, approval = _approve_replay_subject(db, promoted_session_id, "closed-reviews")
        selection = _select_replay_subject(db, promoted_session_id, "closed-reviews", preview, approval)
        _start_replay_subject(
            db,
            promoted_session_id,
            "closed-reviews",
            preview,
            approval,
            selection,
        )
        promoted = db.get(L3Session, promoted_session_id)
        receipt = db.query(L3ConnectorPromotionReceipt).filter_by(promoted_session_id=promoted_session_id).one()
        assert promoted is not None
        for decision, expected_state in _RESULT_REVIEW_STATE_BY_DECISION.items():
            state = _install_closed_result_review(db, receipt, promoted, decision)
            assert state["review_state"] == expected_state
            assert all(state[key] is None for key in tuple(state)[-5:])
            assert _replay_summary_contract_valid(db, promoted_session_id)
        for decision, expected_state in _PACKAGE_REVIEW_STATE_BY_DECISION.items():
            state = _install_closed_package_review(db, receipt, promoted, decision)
            assert state["package_review_state"] == expected_state
            assert [item["package_kind"] for item in state["packages"]] == list(_PACKAGE_ORDER)
            assert (state["connector_dataset_handoff_basis_hash"] is not None) is (
                decision == "approved"
            )
            assert _replay_summary_contract_valid(db, promoted_session_id)


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        pytest.param(("loaded_snapshot_count",), True, id="loaded-snapshot-bool"),
        pytest.param(("retrieved_descriptor_count",), 1.0, id="retrieved-descriptor-float"),
        pytest.param(("unresolved_descriptor_count",), False, id="unresolved-descriptor-bool"),
        pytest.param(
            ("descriptor_status_counts", "resolved_loaded"),
            True,
            id="resolved-loaded-bool",
        ),
        pytest.param(("retrieval_outcome_counts", "loaded"), 1.0, id="loaded-float"),
        pytest.param(
            ("plan_approval", "approved_set_count"),
            True,
            id="approved-set-count-bool",
        ),
        pytest.param(
            ("execution_selection", "execution_started"),
            1,
            id="execution-started-int",
        ),
    ),
)
def test_closed_replay_contract_rejects_numeric_type_substitutions_without_durable_mutation(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[str, ...],
    replacement: object,
) -> None:
    stem = f"typed-{path[-1].replace('_', '-')}"
    _gate_b_session_id, resolved = _materialize_replay_subject(
        b1b_step3_runtime,
        monkeypatch,
        stem,
    )
    promoted_session_id = resolved["promoted_session_id"]
    with b1b_step3_runtime["factory"]() as db:
        preview, approval = _approve_replay_subject(db, promoted_session_id, stem)
        _select_replay_subject(db, promoted_session_id, stem, preview, approval)

    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        promoted = db.get(L3Session, promoted_session_id)
        assert promoted is not None
        malformed = copy.deepcopy(promoted.summary_json)
        target = malformed
        for key in path[:-1]:
            target = target[key]
            assert isinstance(target, dict)
        target[path[-1]] = replacement
        promoted.summary_json = malformed
        db.flush()
        assert not _replay_summary_contract_valid(db, promoted_session_id)
        db.rollback()

    assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
    assert _all_storage_files(b1b_step3_runtime) == files_before


def test_closed_replay_contract_rejects_malformed_states_without_resolver_mutation(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id, _resolved = _materialize_replay_subject(
        b1b_step3_runtime,
        monkeypatch,
        "closed-reject",
    )
    with b1b_step3_runtime["factory"]() as db:
        promoted = db.query(L3Session).filter(L3Session.session_id != gate_b_session_id).one()
        promoted_session_id = promoted.session_id
        preview, approval = _approve_replay_subject(db, promoted_session_id, "closed-reject")
        selection = _select_replay_subject(db, promoted_session_id, "closed-reject", preview, approval)
        _start_replay_subject(
            db,
            promoted_session_id,
            "closed-reject",
            preview,
            approval,
            selection,
        )
        staged = copy.deepcopy(promoted.summary_json)
        assert _replay_summary_contract_valid(db, promoted_session_id)
        base = {
            key: value
            for key, value in staged.items()
            if key not in {"plan_approval", "execution_selection", "analysis_execution_start"}
        }
        staged_cases: dict[str, dict] = {}
        staged_cases["unknown_top_level"] = {**staged, "unexpected": True}
        staged_cases["partial_base"] = copy.deepcopy(staged)
        staged_cases["partial_base"].pop("loaded_snapshot_count")
        staged_cases["out_of_order"] = {
            **base,
            "execution_selection": copy.deepcopy(staged["execution_selection"]),
        }
        staged_cases["mixed_top_schema"] = {**staged, "schema_id": "layer3.b1b_session_state.v1"}
        staged_cases["nested_schema_mismatch"] = copy.deepcopy(staged)
        staged_cases["nested_schema_mismatch"]["execution_selection"]["schema_id"] = (
            "layer3.b1b_session_state.v1"
        )
        staged_cases["unknown_nested_field"] = copy.deepcopy(staged)
        staged_cases["unknown_nested_field"]["plan_approval"]["unexpected"] = True
        staged_cases["boolean_domain"] = copy.deepcopy(staged)
        staged_cases["boolean_domain"]["execution_selection"]["operator_reason_recorded"] = 1
        staged_cases["cardinality"] = copy.deepcopy(staged)
        staged_cases["cardinality"]["execution_selection"]["pass_run_ids_json"] = []
        staged_cases["terminal_partial"] = copy.deepcopy(staged)
        staged_cases["terminal_partial"]["analysis_execution_start"].pop("completed_at")
        staged_cases["terminal_status_link"] = copy.deepcopy(staged)
        staged_cases["terminal_status_link"]["analysis_execution_start"]["pass_run_status"] = "failed"
        staged_cases["terminal_timestamp_link"] = copy.deepcopy(staged)
        staged_cases["terminal_timestamp_link"]["analysis_execution_start"]["completed_at"] = (
            "2000-01-01T00:00:00+00:00"
        )
        for name, candidate in staged_cases.items():
            promoted.summary_json = candidate
            db.flush()
            assert not _replay_summary_contract_valid(db, promoted_session_id), name

        receipt = db.query(L3ConnectorPromotionReceipt).filter_by(promoted_session_id=promoted_session_id).one()
        approved = _install_closed_package_review(db, receipt, promoted, "approved")
        assert _replay_summary_contract_valid(db, promoted_session_id)
        closed_cases: dict[str, dict] = {}
        closed_cases["unknown_top_level"] = {**approved, "unexpected": True}
        closed_cases["partial"] = copy.deepcopy(approved)
        closed_cases["partial"].pop("package_review_hash")
        closed_cases["unknown_schema"] = {**approved, "schema_id": "layer3.unknown.v1"}
        closed_cases["package_order"] = copy.deepcopy(approved)
        closed_cases["package_order"]["packages"] = list(reversed(closed_cases["package_order"]["packages"]))
        closed_cases["approved_missing_handoff"] = {
            **approved,
            "connector_dataset_handoff_basis_hash": None,
        }
        closed_cases["package_hash_link"] = {**approved, "package_review_hash": "9" * 64}
        for name, candidate in closed_cases.items():
            promoted.summary_json = candidate
            db.flush()
            assert not _replay_summary_contract_valid(db, promoted_session_id), name

        rejected = _install_closed_result_review(db, receipt, promoted, "rejected")
        rejected_with_package = {
            **rejected,
            **{key: approved[key] for key in tuple(approved)[-5:]},
        }
        promoted.summary_json = rejected_with_package
        db.flush()
        assert not _replay_summary_contract_valid(db, promoted_session_id)

        blocked = _install_closed_package_review(db, receipt, promoted, "blocked")
        blocked["connector_dataset_handoff_basis_hash"] = approved[
            "connector_dataset_handoff_basis_hash"
        ]
        promoted.summary_json = blocked
        db.flush()
        assert not _replay_summary_contract_valid(db, promoted_session_id)

        resolver_invalid = _install_closed_package_review(db, receipt, promoted, "approved")
        resolver_invalid["unexpected"] = True
        promoted.summary_json = resolver_invalid
        db.commit()

    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
    assert _all_storage_files(b1b_step3_runtime) == files_before


def test_step5_first_call_profile_wrapper_links_and_response_are_exact(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import ingest as ingest_service

    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-first",
    )
    _enable_step5(monkeypatch)
    monkeypatch.setattr(ingest_service, "ingest_csv_bytes_to_dataset", _boom)
    before = _materialization_census(b1b_step3_runtime)
    raw_before = {
        path: path.read_bytes()
        for path in (b1b_step3_runtime["storage_dir"] / "connectors" / "raw").rglob("*")
        if path.is_file()
    }
    target_before = _target_projection(b1b_step3_runtime)
    original_session_before = _session_chain_census(b1b_step3_runtime, gate_b_session_id)
    assert original_session_before == {
        "L3Session": 1,
        "L3SelectionManifest": 1,
        "L3Descriptor": 1,
        "L3RetrievalEvent": 1,
        "L3MaterialSnapshot": 1,
        "L3TypingRecord": 0,
        "L3AnalysisUnit": 0,
        "L3AnalysisGroup": 0,
        "L3AnalysisSet": 0,
    }

    response = _resolve(b1b_step3_runtime, gate_b_session_id)

    assert set(response) == _RESOLVE_KEYS
    assert response["schema_id"] == "layer3.connector_promotion_resolve_response.v1"
    assert response["disposition"] == "materialized"
    assert response["gate_b_session_id"] == gate_b_session_id
    assert (response["row_count"], response["source_row_count"], response["variable_count"]) == (2, 2, 2)
    after = _materialization_census(b1b_step3_runtime)
    assert {name: after[name] - before[name] for name in before} == {
        "SourceConnector": 1,
        "Dataset": 1,
        "DatasetVersion": 1,
        "VariableDefinition": 2,
        "DatasetSourceProvenance": 1,
        "DatasetRow": 0,
        "L3TypingRecord": 1,
        "L3AnalysisUnit": 1,
        "L3AnalysisGroup": 1,
        "L3AnalysisSet": 1,
        "L3Session": 1,
        "L3SelectionManifest": 1,
        "L3Descriptor": 1,
        "L3RetrievalEvent": 1,
        "L3MaterialSnapshot": 1,
    }
    assert _session_chain_census(b1b_step3_runtime, gate_b_session_id) == original_session_before
    assert _session_chain_census(b1b_step3_runtime, response["promoted_session_id"]) == {
        model.__name__: 1 for model in _SESSION_CHAIN_MODELS
    }
    raw_after = {
        path: path.read_bytes()
        for path in (b1b_step3_runtime["storage_dir"] / "connectors" / "raw").rglob("*")
        if path.is_file()
    }
    assert raw_after == raw_before

    with b1b_step3_runtime["factory"]() as db:
        source = db.query(SourceConnector).one()
        dataset = db.get(Dataset, response["dataset_id"])
        version = db.get(DatasetVersion, response["dataset_version_id"])
        provenance = db.query(DatasetSourceProvenance).one()
        receipt = db.query(L3ConnectorPromotionReceipt).one()
        promoted = db.get(L3Session, response["promoted_session_id"])
        target = db.get(ConnectorRunTarget, b1b_step3_runtime["target_id"])
        assert dataset is not None and version is not None and promoted is not None and target is not None
        assert (source.source_name, source.source_category, source.automation_tier) == (
            "synthetic_f07_c01_connector",
            "synthetic_local_proof",
            "tier_0",
        )
        assert dataset.source_id == source.source_id
        assert version.dataset_id == dataset.dataset_id
        assert version.content_hash == pm.F07_CONTENT_SHA256
        assert (version.row_count, version.source_row_count, version.dropped_row_count) == (2, 2, 0)
        variables = db.query(VariableDefinition).order_by(VariableDefinition.ordinal_position).all()
        assert [(v.variable_name, v.dtype, v.is_numeric, v.is_time_index) for v in variables] == [
            ("site_id", "object", False, False),
            ("value", "float64", True, False),
        ]
        assert provenance.dataset_version_id == version.dataset_version_id
        assert provenance.connector_run_id == b1b_step3_runtime["run_id"]
        intake = db.get(L3ConnectorSourceIntakeRecord, receipt.connector_source_intake_record_id)
        assert intake is not None and provenance.raw_storage_ref == intake.storage_ref
        wrapper = provenance.source_reference_json["layer3_connector_promotion_materialization_v1"]
        assert promoted.operator_context_json["layer3_connector_promotion_materialization_v1"] == wrapper
        assert wrapper["record_hash"] == response["materialization_record_hash"]
        assert wrapper["record"]["basis_hash"] == receipt.materialization_basis_hash
        assert wrapper["record"]["output"]["source_connector_id"] == source.source_id
        final_path = Path(version.storage_ref)
        final_bytes = final_path.read_bytes()
        assert wrapper["record"]["output"]["dataset_file_sha256"] == _hashlib.sha256(final_bytes).hexdigest()
        assert wrapper["record"]["output"]["dataset_file_bytes"] == len(final_bytes)
        assert receipt.materialization_status == "materialized"
        assert (receipt.dataset_id, receipt.dataset_version_id, receipt.promoted_session_id) == (
            dataset.dataset_id,
            version.dataset_version_id,
            promoted.session_id,
        )
        assert promoted.status == "completed_with_warnings"
        original_snapshot = db.query(L3MaterialSnapshot).filter_by(session_id=gate_b_session_id).one()
        snapshot = db.query(L3MaterialSnapshot).filter_by(session_id=promoted.session_id).one()
        event = db.query(L3RetrievalEvent).filter_by(session_id=promoted.session_id).one()
        typing_record = db.query(L3TypingRecord).filter_by(session_id=promoted.session_id).one()
        analysis_unit = db.query(L3AnalysisUnit).filter_by(session_id=promoted.session_id).one()
        analysis_group = db.query(L3AnalysisGroup).filter_by(session_id=promoted.session_id).one()
        analysis_set = db.query(L3AnalysisSet).filter_by(session_id=promoted.session_id).one()
        assert original_snapshot.source_shape == pm.F07_SOURCE_FAMILY
        assert snapshot.source_shape == "dataset_version"
        assert original_snapshot.material_snapshot_id != snapshot.material_snapshot_id
        assert typing_record.material_snapshot_id == snapshot.material_snapshot_id
        assert typing_record.candidate_modalities_json == ["quantitative"]
        assert typing_record.chosen_modality == "quantitative"
        assert typing_record.confidence == 1.0
        assert typing_record.overridden_by_operator is False
        assert analysis_unit.member_snapshot_ids_json == [snapshot.material_snapshot_id]
        assert analysis_unit.typing_record_ids_json == [typing_record.typing_record_id]
        assert (analysis_unit.unit_kind, analysis_unit.analysis_modality, analysis_unit.must_remain_intact) == (
            "atomic",
            "quantitative",
            False,
        )
        assert analysis_group.analysis_unit_ids_json == [analysis_unit.analysis_unit_id]
        assert analysis_group.typing_basis_json["group_basis"] == "singleton"
        assert (analysis_group.analysis_modality, analysis_group.status) == ("quantitative", "formed")
        assert analysis_set.analysis_group_ids_json == [analysis_group.analysis_group_id]
        assert analysis_set.analysis_unit_ids_json == [analysis_unit.analysis_unit_id]
        assert analysis_set.set_type == "single_item"
        assert Path(snapshot.payload_ref).is_file()
        assert _hashlib.sha256(Path(snapshot.payload_ref).read_bytes()).hexdigest() == snapshot.payload_hash
        assert event.event_payload_json["loaded_items"][0]["payload_ref"] == snapshot.payload_ref
        assert (target.dataset_id, target.dataset_version_id) == (dataset.dataset_id, version.dataset_version_id)
        for key, value in target_before.items():
            if key not in {"dataset_id", "dataset_version_id"}:
                assert getattr(target, key) == value


def test_b1b_03_receipt_bound_public_analysis_is_exact_and_replay_inert(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    b1b_03_golden_preimages: dict[str, bytes],
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-03-analysis",
    )
    _enable_step5(monkeypatch)
    original_session = _session_chain_projection(b1b_step3_runtime, gate_b_session_id)
    resolved = _resolve(b1b_step3_runtime, gate_b_session_id)
    promoted_session_id = resolved["promoted_session_id"]
    assert _session_chain_projection(b1b_step3_runtime, gate_b_session_id) == original_session

    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
    with b1b_step3_runtime["factory"]() as db:
        legacy_preview = layer3_pass_entry.preview_pass_entry(
            db,
            session_id=promoted_session_id,
        )
        assert len(legacy_preview.admitted_sets) == 1
        analysis_set_id = legacy_preview.admitted_sets[0]["analysis_set_id"]
        expected_legacy_plan = {
            "plan_version": "gatec_pass_entry_v1",
            "planned_passes_json": [
                {
                    "analysis_set_id": analysis_set_id,
                    "set_type": "single_item",
                    "pass_type": "single_item",
                    "pass_scope": "quantitative_single_item_dataset_version",
                    "engine_family": "wrapped_quantitative_analysis",
                    "selected_method_name": "descriptive_summary",
                    "source_gate": "06_GATEC_PASS_FREEZE",
                    "dataset_version_id": resolved["dataset_version_id"],
                }
            ],
            "excluded_sets_json": [],
            "formation_reason": "quantitative_dataset_version_backed_gatec_only",
            "source_gate": "06_GATEC_PASS_FREEZE",
        }
        assert stable_json_bytes(legacy_preview.owner_plan_payload) == stable_json_bytes(
            expected_legacy_plan
        )
        legacy_hash_basis = {
            "schema_id": "layer3.plan_preview_hash.v1",
            "session_id": promoted_session_id,
            "admitted_sets": legacy_preview.admitted_sets,
            "excluded_sets": legacy_preview.excluded_sets,
            "planned_passes": legacy_preview.planned_passes,
            "warnings": legacy_preview.warnings,
            "owner_service_basis": legacy_preview.owner_service_basis,
            "owner_plan_payload": expected_legacy_plan,
        }
        assert legacy_preview.preview_hash == stable_hash(legacy_hash_basis)

    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    expected_receipt_contract = {
        "inputs": {
            "connector_promotion_receipt_id": resolved["connector_promotion_receipt_id"],
            "dataset_version_id": resolved["dataset_version_id"],
        },
        "method_contract": _json.loads(b1b_03_golden_preimages["method_contract"]),
        "method_contract_sha256": "586745d83f62f60e32a94fb62cd5557341866e5319d48eece7d0ea741a5e89e5",
        "transformation_contract_sha256": "951b3a88b1eaa9ef2b1da0480396e3b4c7a01b7e16687a726b2566bd1caf3179",
    }
    expected_enriched_plan = copy.deepcopy(expected_legacy_plan)
    expected_enriched_plan["planned_passes_json"][0][
        "receipt_bound_analysis_contract"
    ] = expected_receipt_contract

    with b1b_step3_runtime["factory"]() as db:
        enriched_preview = layer3_pass_entry.preview_pass_entry(
            db,
            session_id=promoted_session_id,
        )
        repeated_preview = layer3_pass_entry.preview_pass_entry(
            db,
            session_id=promoted_session_id,
        )
        assert enriched_preview.owner_plan_payload == expected_enriched_plan
        assert pm.d33_canonical_bytes(
            enriched_preview.owner_plan_payload["planned_passes_json"][0][
                "receipt_bound_analysis_contract"
            ]["method_contract"]
        ) == b1b_03_golden_preimages["method_contract"]
        assert enriched_preview.preview_hash == repeated_preview.preview_hash
        assert enriched_preview.preview_hash != legacy_preview.preview_hash
        assert enriched_preview.preview_hash == stable_hash(
            {**legacy_hash_basis, "owner_plan_payload": expected_enriched_plan}
        )

        public_preview = layer3_workbench.plan_preview(
            db,
            {
                "client_request_id": "b1b-03-plan-preview",
                "session_id": promoted_session_id,
                "question_text": "caller must not replace the frozen question",
                "receipt_bound_analysis_contract": {"method_contract": {"method_id": "caller"}},
            },
        )
        assert public_preview["preview_hash"] == enriched_preview.preview_hash

    before_census = _b1b_03_row_census(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        approval = layer3_workbench.plan_approval(
            db,
            {
                "client_request_id": "b1b-03-plan-approval",
                "session_id": promoted_session_id,
                "preview_id": public_preview["preview_id"],
                "preview_hash": public_preview["preview_hash"],
                "operator_confirmation": True,
            },
        )
        selection_payload = {
            "client_request_id": "b1b-03-execution-selection",
            "session_id": promoted_session_id,
            "analysis_plan_id": approval["analysis_plan_id"],
            "preview_id": public_preview["preview_id"],
            "preview_hash": public_preview["preview_hash"],
        }
        selection = layer3_workbench.execution_selection(db, selection_payload)
        start_payload = {
            "client_request_id": "b1b-03-analysis-start",
            "session_id": promoted_session_id,
            "analysis_plan_id": approval["analysis_plan_id"],
            "pass_run_id": selection["pass_run_ids"][0],
            "preview_id": public_preview["preview_id"],
            "preview_hash": public_preview["preview_hash"],
        }
        start = layer3_workbench.analysis_execution_start(db, start_payload)

    after_census = _b1b_03_row_census(b1b_step3_runtime)
    expected_delta = {name: 0 for name in before_census}
    expected_delta.update(
        {
            "L3AnalysisPlan": 1,
            "L3PassRun": 1,
            "AnalysisRun": 1,
            "AssumptionCheck": 4,
            "AnalysisArtifact": 1,
            "CaveatNote": 1,
        }
    )
    assert {
        name: after_census[name] - before_census[name]
        for name in before_census
    } == expected_delta

    files_after = _all_storage_files(b1b_step3_runtime)
    assert {name: files_after[name] for name in files_before} == files_before
    added_files = set(files_after) - set(files_before)
    assert len(added_files) == 2
    assert len(
        [name for name in added_files if name.startswith("artifacts/descriptive_summary_result_")]
    ) == 1
    assert len(
        [name for name in added_files if name.startswith("artifacts/layer3/l3_pass_run_")]
    ) == 1

    with b1b_step3_runtime["factory"]() as db:
        plan = db.query(L3AnalysisPlan).filter_by(session_id=promoted_session_id).one()
        pass_run = db.query(L3PassRun).filter_by(session_id=promoted_session_id).one()
        analysis_run = db.query(AnalysisRun).one()
        checks = db.query(AssumptionCheck).all()
        artifact = db.query(AnalysisArtifact).one()
        caveat = db.query(CaveatNote).one()
        assert approval["plan_status"] == plan.status == "approved"
        assert plan.approved_by_operator is True
        assert plan.analysis_set_ids_json == [analysis_set_id]
        assert plan.plan_json["source_preview_hash"] == public_preview["preview_hash"]
        assert (
            plan.plan_json["planned_passes_json"][0]["receipt_bound_analysis_contract"]
            == expected_receipt_contract
        )
        assert pass_run.analysis_plan_id == plan.analysis_plan_id
        assert pass_run.analysis_set_id == analysis_set_id
        assert pass_run.status == start["pass_run_status"] == "completed_with_warnings"
        assert (
            pass_run.summary_json["planned_pass"]["receipt_bound_analysis_contract"]
            == expected_receipt_contract
        )
        assert pass_run.summary_json["analysis_run_id"] == analysis_run.analysis_run_id
        assert analysis_run.dataset_version_id == resolved["dataset_version_id"]
        assert (analysis_run.method_name, analysis_run.goal_type, analysis_run.parameters_json) == (
            "descriptive_summary",
            None,
            {},
        )
        assert analysis_run.window_scope_json == {}
        assert analysis_run.status == "completed"

        assert {
            check.assumption_name: (
                check.check_method,
                check.check_result,
                check.severity,
                check.notes,
            )
            for check in checks
        } == {
            "data_availability": ("dataframe_shape", "pass", "high", "rows=2; columns=2"),
            "column_classification": (
                "deterministic_dtype_scan",
                "pass",
                "medium",
                '{"categorical": 1, "numeric": 1}',
            ),
            "missingness_scan": (
                "cell_missingness",
                "pass",
                "medium",
                "missing_cells=0; missing_fraction=0.000000",
            ),
            "time_column_coverage": (
                "declared_time_column_scan",
                "warn",
                "medium",
                "time_column=; present=False",
            ),
        }
        assert (
            caveat.caveat_type,
            caveat.severity,
            caveat.message,
        ) == (
            "non_time_series_interpretation",
            "medium",
            "Dataset does not declare a usable time column; descriptive summary is non-time-series only.",
        )
        assert artifact.analysis_run_id == analysis_run.analysis_run_id
        assert artifact.artifact_type == "descriptive_summary_result"
        artifact_path = Path(settings.artifact_storage_dir) / Path(artifact.storage_ref).name
        result_payload = _json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact.metadata_json == result_payload["summary_stats"]
        assert result_payload["summary_stats"] == {
            "row_count": 2,
            "column_count": 2,
            "numeric_column_count": 1,
            "categorical_column_count": 1,
            "boolean_column_count": 0,
            "time_column_count": 0,
            "missing_cell_count": 0,
            "missing_fraction": 0.0,
        }
        assert result_payload["columns"]["site_id"] == {
            "inferred_class": "categorical",
            "non_null_count": 2,
            "missing_count": 0,
            "missing_fraction": 0.0,
            "unsupported_nested_values": False,
            "unique_count": 2,
            "top_values": [
                {"value": "SB-001", "count": 1},
                {"value": "SB-002", "count": 1},
            ],
        }
        value_summary = result_payload["columns"]["value"]
        assert {
            key: value_summary[key]
            for key in (
                "inferred_class",
                "non_null_count",
                "missing_count",
                "missing_fraction",
                "unsupported_nested_values",
                "top_values",
            )
        } == {
            "inferred_class": "numeric",
            "non_null_count": 2,
            "missing_count": 0,
            "missing_fraction": 0.0,
            "unsupported_nested_values": False,
            "top_values": [{"value": 42, "count": 1}, {"value": 43, "count": 1}],
        }
        numeric_summary = value_summary["numeric_summary"]
        assert {key: numeric_summary[key] for key in ("non_null_count", "min", "max", "mean", "median")} == {
            "non_null_count": 2,
            "min": 42.0,
            "max": 43.0,
            "mean": 42.5,
            "median": 42.5,
        }
        assert numeric_summary["std_dev"] == pytest.approx(
            0.7071067811865476,
            rel=1e-12,
            abs=1e-12,
        )
        output_manifest = _json.loads(Path(pass_run.output_payload_ref).read_text(encoding="utf-8"))
        assert output_manifest == {
            "analysis_run_id": analysis_run.analysis_run_id,
            "analysis_set_id": analysis_set_id,
            "dataset_version_id": resolved["dataset_version_id"],
            "selected_method_name": "descriptive_summary",
            "artifact_refs_json": [artifact.storage_ref],
            "artifact_types_json": ["descriptive_summary_result"],
            "source_gate": "06_GATEC_PASS_FREEZE",
        }

    frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
    frozen_files = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        selection_replay = layer3_workbench.execution_selection(db, selection_payload)
        start_replay = layer3_workbench.analysis_execution_start(db, start_payload)
    assert selection_replay["status"] == "already_selected"
    assert start_replay["status"] == "already_completed"
    resolver_replay = _resolve(b1b_step3_runtime, gate_b_session_id)
    assert resolver_replay == {**resolved, "disposition": "reused"}
    assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
    assert _all_storage_files(b1b_step3_runtime) == frozen_files
    assert _session_chain_projection(b1b_step3_runtime, gate_b_session_id) == original_session


def test_step5_exact_replay_is_zero_delta_and_rehashes_final(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-replay")
    _enable_step5(monkeypatch)
    first = _resolve(b1b_step3_runtime, gate_b_session_id)
    census = _materialization_census(b1b_step3_runtime)
    files = _lane_files(b1b_step3_runtime)
    target = _target_projection(b1b_step3_runtime)
    receipt = _receipt_state(b1b_step3_runtime)

    replay = _resolve(b1b_step3_runtime, gate_b_session_id)

    assert replay == {**first, "disposition": "reused"}
    assert _materialization_census(b1b_step3_runtime) == census
    assert _lane_files(b1b_step3_runtime) == files
    assert _target_projection(b1b_step3_runtime) == target
    assert _receipt_state(b1b_step3_runtime) == receipt


def test_step5_replay_rejects_final_file_drift_without_db_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-replay-drift")
    _enable_step5(monkeypatch)
    first = _resolve(b1b_step3_runtime, gate_b_session_id)
    with b1b_step3_runtime["factory"]() as db:
        version = db.get(DatasetVersion, first["dataset_version_id"])
        assert version is not None
        final_path = Path(version.storage_ref)
    final_path.write_bytes(final_path.read_bytes() + b"drift")
    census = _materialization_census(b1b_step3_runtime)
    target = _target_projection(b1b_step3_runtime)
    receipt = _receipt_state(b1b_step3_runtime)

    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert _materialization_census(b1b_step3_runtime) == census
    assert _target_projection(b1b_step3_runtime) == target
    assert _receipt_state(b1b_step3_runtime) == receipt


def test_step5_replay_rejects_metadata_profile_drift_without_further_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-profile-drift")
    _enable_step5(monkeypatch)
    _resolve(b1b_step3_runtime, gate_b_session_id)
    with b1b_step3_runtime["factory"]() as db:
        source = db.query(SourceConnector).one()
        source.source_category = "drifted"
        db.commit()
    census = _materialization_census(b1b_step3_runtime)
    files = _lane_files(b1b_step3_runtime)

    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert _materialization_census(b1b_step3_runtime) == census
    assert _lane_files(b1b_step3_runtime) == files


def _assert_receipt_and_target_unmaterialized(runtime: dict) -> None:
    with runtime["factory"]() as db:
        receipt = db.query(L3ConnectorPromotionReceipt).one()
        target = db.get(ConnectorRunTarget, runtime["target_id"])
        assert target is not None
        assert (
            receipt.materialization_status,
            receipt.materialization_basis_hash,
            receipt.dataset_id,
            receipt.dataset_version_id,
            receipt.promoted_session_id,
            receipt.materialized_at,
        ) == (None, None, None, None, None, None)
        assert (target.dataset_id, target.dataset_version_id) == (None, None)


def _authoritative_step5_files(runtime: dict) -> set[str]:
    root = runtime["storage_dir"]
    result: set[str] = set()
    for lane_root in (
        root / "datasets" / "b1b" / "dataset-versions",
        root / "artifacts" / "layer3" / "b1b",
    ):
        if lane_root.exists():
            result.update(
                path.relative_to(root).as_posix()
                for path in lane_root.rglob("*")
                if path.is_file()
            )
    return result


def test_step5_code_identity_failure_is_before_mutation(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-code")
    _enable_step5(monkeypatch)
    before = _materialization_census(b1b_step3_runtime)
    files_before = _lane_files(b1b_step3_runtime)

    def dirty_checkout():
        raise pm.PromotionIdentityError("tracked checkout is dirty")

    monkeypatch.setattr(pm, "_read_clean_materialization_code_identity", dirty_checkout)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert (caught.value.code, caught.value.http_status, caught.value.retryable) == (
        "connector_materialization_basis_conflict",
        409,
        False,
    )
    assert _materialization_census(b1b_step3_runtime) == before
    assert _lane_files(b1b_step3_runtime) == files_before
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)


def test_step5_code_identity_provider_double_checks_head_and_clean_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_reads = 0
    blob_specs: list[str] = []

    def stable_git(_root: Path, *args: str) -> str:
        nonlocal status_reads
        if args[:2] == ("status", "--porcelain=v1"):
            status_reads += 1
            return ""
        if args == ("rev-parse", "HEAD"):
            return "a" * 40
        blob_specs.append(args[1])
        return {
            f"{'a' * 40}:backend/app/services/layer3_connector_promotion.py": "b" * 40,
            f"{'a' * 40}:backend/app/services/ingest.py": "c" * 40,
            f"{'a' * 40}:backend/app/services/dataframe_io.py": "d" * 40,
        }[args[1]]

    monkeypatch.setattr(pm, "_git_text", stable_git)
    assert pm._read_clean_materialization_code_identity() == {
        "implementation_commit": "a" * 40,
        "promotion_git_blob": "b" * 40,
        "ingest_git_blob": "c" * 40,
        "dataframe_io_git_blob": "d" * 40,
    }
    assert status_reads == 2
    assert blob_specs == [
        f"{'a' * 40}:backend/app/services/layer3_connector_promotion.py",
        f"{'a' * 40}:backend/app/services/ingest.py",
        f"{'a' * 40}:backend/app/services/dataframe_io.py",
    ]

    def drifting_git(root: Path, *args: str) -> str:
        if args[:2] == ("status", "--porcelain=v1") and drifting_git.status_seen:
            return " M backend/app/services/layer3_connector_promotion.py"
        if args[:2] == ("status", "--porcelain=v1"):
            drifting_git.status_seen = True
        return stable_git(root, *args)

    drifting_git.status_seen = False
    monkeypatch.setattr(pm, "_git_text", drifting_git)
    with pytest.raises(pm.PromotionIdentityError, match="changed during re-read"):
        pm._read_clean_materialization_code_identity()


def test_step5_failure_before_publish_rolls_back_and_contains_stage(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-prepublish")
    _enable_step5(monkeypatch)
    before = _materialization_census(b1b_step3_runtime)

    def fail_before_publish() -> None:
        raise RuntimeError("injected failure before publish")

    monkeypatch.setattr(pm, "_before_materialization_publish", fail_before_publish)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert isinstance(caught.value.__cause__, RuntimeError)

    assert _materialization_census(b1b_step3_runtime) == before
    assert _authoritative_step5_files(b1b_step3_runtime) == set()
    assert any("containment" in path for path in _lane_files(b1b_step3_runtime))
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)


def test_step5_failure_after_publish_contains_orphan_then_retry_rebuilds(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-postpublish")
    _enable_step5(monkeypatch)
    before = _materialization_census(b1b_step3_runtime)

    def fail_after_publish() -> None:
        raise RuntimeError("injected failure after publish")

    monkeypatch.setattr(pm, "_after_materialization_publish", fail_after_publish)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert _materialization_census(b1b_step3_runtime) == before
    assert _authoritative_step5_files(b1b_step3_runtime) == set()
    failed_files = _lane_files(b1b_step3_runtime)
    contained_parquets = {
        path: facts for path, facts in failed_files.items() if "containment" in path and path.endswith(".parquet")
    }
    assert len(contained_parquets) == 1
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)

    monkeypatch.setattr(pm, "_after_materialization_publish", lambda: None)
    response = _resolve(b1b_step3_runtime, gate_b_session_id)
    assert response["disposition"] == "materialized"
    authoritative_parquets = {
        path: facts
        for path, facts in _lane_files(b1b_step3_runtime).items()
        if "/dataset-versions/" in path and path.endswith(".parquet")
    }
    assert len(authoritative_parquets) == 1
    assert next(iter(authoritative_parquets.values())) == next(iter(contained_parquets.values()))
    containment_pairs = _assert_exact_containment_ledgers(b1b_step3_runtime)
    assert len(containment_pairs) == 2
    assert {artifact.suffix for artifact, _record in containment_pairs} == {
        ".json",
        ".parquet",
    }


def test_step5_commit_then_raise_is_reconciled_as_committed_without_containment(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-commit-ack-lost",
    )
    _enable_step5(monkeypatch)

    def commit_then_raise(db) -> None:
        db.commit()
        raise RuntimeError("injected acknowledgement loss after durable commit")

    monkeypatch.setattr(pm, "_commit_materialization", commit_then_raise)
    response = _resolve(b1b_step3_runtime, gate_b_session_id)
    assert response["disposition"] == "materialized"
    assert _assert_exact_containment_ledgers(b1b_step3_runtime) == []
    census = _materialization_census(b1b_step3_runtime)
    files = _lane_files(b1b_step3_runtime)

    replay = _resolve(b1b_step3_runtime, gate_b_session_id)
    assert replay == {**response, "disposition": "reused"}
    assert _materialization_census(b1b_step3_runtime) == census
    assert _lane_files(b1b_step3_runtime) == files


def test_step5_precommit_failure_rolls_back_and_contains_both_published_files(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-commit-not-applied",
    )
    _enable_step5(monkeypatch)
    before = _materialization_census(b1b_step3_runtime)

    def fail_before_commit(_db) -> None:
        raise RuntimeError("injected failure before commit")

    monkeypatch.setattr(pm, "_commit_materialization", fail_before_commit)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert _materialization_census(b1b_step3_runtime) == before
    assert _authoritative_step5_files(b1b_step3_runtime) == set()
    pairs = _assert_exact_containment_ledgers(b1b_step3_runtime)
    assert len(pairs) == 2
    assert {artifact.suffix for artifact, _record in pairs} == {".json", ".parquet"}
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)


def test_step5_commit_then_raise_reconciles_even_when_original_rollback_fails(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-commit-rollback-broken",
    )
    _enable_step5(monkeypatch)

    def commit_then_raise(db) -> None:
        db.commit()
        raise RuntimeError("injected acknowledgement loss after durable commit")

    def rollback_fails() -> None:
        raise RuntimeError("injected original-session rollback failure")

    monkeypatch.setattr(pm, "_commit_materialization", commit_then_raise)
    with b1b_step3_runtime["factory"]() as db:
        monkeypatch.setattr(db, "rollback", rollback_fails)
        response = pm.resolve_connector_promotion(
            db,
            gate_b_session_id=gate_b_session_id,
        )
    assert response["disposition"] == "materialized"
    assert _assert_exact_containment_ledgers(b1b_step3_runtime) == []
    assert _resolve(b1b_step3_runtime, gate_b_session_id) == {
        **response,
        "disposition": "reused",
    }


def test_step5_precommit_failure_leaves_uncertain_files_for_next_locked_census(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-precommit-rollback-broken",
    )
    _enable_step5(monkeypatch)
    before = _materialization_census(b1b_step3_runtime)
    commit_materialization = pm._commit_materialization

    def fail_before_commit(_db) -> None:
        raise RuntimeError("injected failure before commit")

    def rollback_fails() -> None:
        raise RuntimeError("injected original-session rollback failure")

    monkeypatch.setattr(pm, "_commit_materialization", fail_before_commit)
    with b1b_step3_runtime["factory"]() as db:
        monkeypatch.setattr(db, "rollback", rollback_fails)
        with pytest.raises(pm.ConnectorPromotionError) as caught:
            pm.resolve_connector_promotion(
                db,
                gate_b_session_id=gate_b_session_id,
            )
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert _materialization_census(b1b_step3_runtime) == before
    assert len(_authoritative_step5_files(b1b_step3_runtime)) == 2
    assert _assert_exact_containment_ledgers(b1b_step3_runtime) == []
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)

    monkeypatch.setattr(pm, "_commit_materialization", commit_materialization)
    response = _resolve(b1b_step3_runtime, gate_b_session_id)
    assert response["disposition"] == "materialized"
    assert len(_authoritative_step5_files(b1b_step3_runtime)) == 2
    assert len(_assert_exact_containment_ledgers(b1b_step3_runtime)) == 2


def test_step5_absent_cleanup_holds_i1_lock_against_second_writer(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-cleanup-lock-barrier",
    )
    _enable_step5(monkeypatch)
    commit_materialization = pm._commit_materialization
    acquire_lock = pm.acquire_promotion_identity_lock
    cleanup_entered = threading.Event()
    release_cleanup = threading.Event()
    second_attempted = threading.Event()
    second_done = threading.Event()
    outcomes: dict[str, object] = {}
    errors: list[BaseException] = []

    def commit_by_writer(db) -> None:
        if threading.current_thread().name == "failed-writer":
            raise RuntimeError("injected first-writer precommit failure")
        commit_materialization(db)

    def observe_lock_attempt(db, canonical_key_hash=pm.F07_CANONICAL_IDENTITY_KEY_HASH) -> None:
        if threading.current_thread().name == "second-writer":
            second_attempted.set()
        acquire_lock(db, canonical_key_hash)

    def hold_cleanup() -> None:
        if threading.current_thread().name == "failed-writer":
            cleanup_entered.set()
            if not release_cleanup.wait(10):
                raise RuntimeError("cleanup barrier timed out")

    def run_failed_writer() -> None:
        try:
            outcomes["first"] = _resolve(b1b_step3_runtime, gate_b_session_id)
        except pm.ConnectorPromotionError as exc:
            outcomes["first"] = exc.code
        except BaseException as exc:
            errors.append(exc)

    def run_second_writer() -> None:
        try:
            outcomes["second"] = _resolve(b1b_step3_runtime, gate_b_session_id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            second_done.set()

    monkeypatch.setattr(pm, "_commit_materialization", commit_by_writer)
    monkeypatch.setattr(pm, "acquire_promotion_identity_lock", observe_lock_attempt)
    monkeypatch.setattr(pm, "_before_failed_materialization_containment", hold_cleanup)
    first = threading.Thread(target=run_failed_writer, name="failed-writer")
    second: threading.Thread | None = None
    first.start()
    try:
        assert cleanup_entered.wait(10)
        second = threading.Thread(target=run_second_writer, name="second-writer")
        second.start()
        assert second_attempted.wait(10)
        assert not second_done.wait(0.25)
    finally:
        release_cleanup.set()
        first.join(10)
        if second is not None:
            second.join(10)

    assert not first.is_alive()
    assert second is not None and not second.is_alive()
    assert errors == []
    assert outcomes["first"] == "connector_materialization_basis_conflict"
    second_result = outcomes["second"]
    assert isinstance(second_result, dict)
    assert second_result["disposition"] == "materialized"
    assert len(_authoritative_step5_files(b1b_step3_runtime)) == 2
    assert len(_assert_exact_containment_ledgers(b1b_step3_runtime)) == 2


def test_step5_no_expectation_reconciliation_preserves_second_writer_commit(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(
        b1b_step3_runtime,
        monkeypatch,
        "step5-inverse-cleanup-barrier",
    )
    _enable_step5(monkeypatch)
    best_effort_rollback = pm._best_effort_rollback
    first_rolled_back = threading.Event()
    release_reconciliation = threading.Event()
    second_done = threading.Event()
    outcomes: dict[str, object] = {}
    errors: list[BaseException] = []

    def fail_first_after_publish() -> None:
        if threading.current_thread().name == "failed-writer":
            raise RuntimeError("injected failure before commit expectation")

    def rollback_then_pause(db) -> None:
        best_effort_rollback(db)
        if (
            threading.current_thread().name == "failed-writer"
            and not first_rolled_back.is_set()
        ):
            first_rolled_back.set()
            if not release_reconciliation.wait(10):
                raise RuntimeError("reconciliation barrier timed out")

    def run_failed_writer() -> None:
        try:
            outcomes["first"] = _resolve(b1b_step3_runtime, gate_b_session_id)
        except pm.ConnectorPromotionError as exc:
            outcomes["first"] = exc.code
        except BaseException as exc:
            errors.append(exc)

    def run_second_writer() -> None:
        try:
            outcomes["second"] = _resolve(b1b_step3_runtime, gate_b_session_id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            second_done.set()

    monkeypatch.setattr(pm, "_after_materialization_publish", fail_first_after_publish)
    monkeypatch.setattr(pm, "_best_effort_rollback", rollback_then_pause)
    first = threading.Thread(target=run_failed_writer, name="failed-writer")
    second: threading.Thread | None = None
    first.start()
    try:
        assert first_rolled_back.wait(10)
        second = threading.Thread(target=run_second_writer, name="second-writer")
        second.start()
        assert second_done.wait(10)
    finally:
        release_reconciliation.set()
        first.join(10)
        if second is not None:
            second.join(10)

    assert not first.is_alive()
    assert second is not None and not second.is_alive()
    assert errors == []
    assert outcomes["first"] == "connector_materialization_basis_conflict"
    second_result = outcomes["second"]
    assert isinstance(second_result, dict)
    assert second_result["disposition"] == "materialized"
    assert len(_authoritative_step5_files(b1b_step3_runtime)) == 2
    assert len(_assert_exact_containment_ledgers(b1b_step3_runtime)) == 2
    assert _resolve(b1b_step3_runtime, gate_b_session_id) == {
        **second_result,
        "disposition": "reused",
    }


def test_step5_kill_after_rename_fresh_process_contains_then_retries_once(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-kill")
    _enable_step5(monkeypatch)
    database_path = str(b1b_step3_runtime["engine"].url.database)
    storage_dir = str(b1b_step3_runtime["storage_dir"])
    child_code = "\n".join(
        [
            "import os, sys",
            f"sys.path.insert(0, {str(BACKEND)!r})",
            "os.environ['DB_INIT_MODE'] = 'none'",
            "from sqlalchemy import create_engine",
            "from sqlalchemy.orm import sessionmaker",
            "from app.core.config import settings",
            "from app.services import layer3_connector_promotion as pm",
            f"settings.storage_dir = {storage_dir!r}",
            f"engine = create_engine('sqlite:///{Path(database_path).as_posix()}', future=True, connect_args={{'check_same_thread': False}})",
            "factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)",
            f"pm._read_clean_materialization_code_identity = lambda: {_FIXED_CODE_IDENTITY!r}",
            "pm.attestation_precondition_available = lambda _candidate=None: True",
            "pm._after_materialization_publish = lambda: os._exit(73)",
            "with factory() as db:",
            f"    pm.resolve_connector_promotion(db, gate_b_session_id={gate_b_session_id!r})",
        ]
    )

    child = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=BACKEND.parent,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert child.returncode == 73, (child.stdout, child.stderr)
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)
    orphaned_parquets = {
        path: facts
        for path, facts in _lane_files(b1b_step3_runtime).items()
        if "/dataset-versions/" in path and path.endswith(".parquet")
    }
    assert len(orphaned_parquets) == 1

    response = _resolve(b1b_step3_runtime, gate_b_session_id)
    assert response["disposition"] == "materialized"
    lane_files = _lane_files(b1b_step3_runtime)
    authoritative = {
        path: facts
        for path, facts in lane_files.items()
        if "/dataset-versions/" in path and path.endswith(".parquet")
    }
    contained = {
        path: facts
        for path, facts in lane_files.items()
        if "containment" in path and path.endswith(".parquet")
    }
    assert len(authoritative) == 1
    assert len(contained) == 1
    assert next(iter(authoritative.values())) == next(iter(orphaned_parquets.values()))
    assert next(iter(contained.values())) == next(iter(orphaned_parquets.values()))


def test_step5_rejects_out_of_root_intake_reference_without_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-outside")
    _enable_step5(monkeypatch)
    outside = b1b_step3_runtime["storage_dir"].parent / "outside.csv"
    outside.write_bytes(_F07_BYTES)
    with b1b_step3_runtime["factory"]() as db:
        receipt = db.query(L3ConnectorPromotionReceipt).one()
        intake = db.get(L3ConnectorSourceIntakeRecord, receipt.connector_source_intake_record_id)
        assert intake is not None
        intake.storage_ref = str(outside)
        db.commit()
    before = _materialization_census(b1b_step3_runtime)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_promotion_basis_conflict"
    assert _materialization_census(b1b_step3_runtime) == before
    assert _authoritative_step5_files(b1b_step3_runtime) == set()
    _assert_receipt_and_target_unmaterialized(b1b_step3_runtime)


def test_step5_storage_ref_rejects_symlink_component(tmp_path: Path) -> None:
    root = tmp_path / "storage"
    real_dir = root / "real"
    real_dir.mkdir(parents=True)
    (real_dir / "fixture.csv").write_bytes(_F07_BYTES)
    link = root / "linked"
    try:
        link.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        pytest.skip("local Windows policy does not permit creating a symlink probe")
    with pytest.raises(pm.PromotionIdentityError, match="reparse"):
        pm._resolve_regular_reference(str(link / "fixture.csv"), str(root))
    with pytest.raises(pm.PromotionIdentityError, match="reparse"):
        pm._resolve_regular_reference(str(real_dir / "fixture.csv"), str(link))


def test_step5_lane_root_reparse_is_rejected_before_descendant_creation(tmp_path: Path) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked"
    try:
        linked_parent.symlink_to(real_parent, target_is_directory=True)
    except OSError:
        pytest.skip("local Windows policy does not permit creating a symlink probe")
    custody_root = linked_parent / "custody"

    with pytest.raises(pm.PromotionIdentityError, match="reparse"):
        pm._ensure_nonreparse_lane_directory(custody_root / "lane", custody_root)

    assert not (real_parent / "custody").exists()


def test_step5_containment_record_write_failure_is_repaired_on_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basis_hash = "b" * 64
    source = tmp_path / "stage.parquet"
    source.write_bytes(b"contained payload")
    containment_root = tmp_path / "containment"
    write_record = pm._write_containment_record

    def fail_record_write(_path: Path, _record: dict) -> None:
        raise RuntimeError("injected containment record failure")

    monkeypatch.setattr(pm, "_write_containment_record", fail_record_write)
    with pytest.raises(RuntimeError, match="containment record failure"):
        pm._contain_file(
            source,
            containment_root=containment_root,
            basis_hash=basis_hash,
            namespace="record-recovery",
        )
    assert not source.exists()
    artifacts = [
        path
        for path in containment_root.rglob("*")
        if path.is_file() and not path.name.endswith(pm._CONTAINMENT_RECORD_SUFFIX)
    ]
    assert len(artifacts) == 1
    assert not pm._containment_record_path(artifacts[0]).exists()

    monkeypatch.setattr(pm, "_write_containment_record", write_record)
    pm._reconcile_containment_records(containment_root)
    record = json.loads(pm._containment_record_path(artifacts[0]).read_bytes())
    assert record["basis_hash"] == basis_hash
    assert record["artifact_sha256"] == _hashlib.sha256(b"contained payload").hexdigest()


@pytest.mark.parametrize("prefix_size", [0, 17], ids=["empty", "mid-prefix"])
def test_step5_partial_containment_record_is_completed_on_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prefix_size: int,
) -> None:
    basis_hash = "c" * 64
    source = tmp_path / "stage.parquet"
    source.write_bytes(b"partial-ledger payload")
    containment_root = tmp_path / "containment"
    write_record = pm._write_containment_record
    captured: list[bytes] = []

    def fail_after_prefix(record_path: Path, record: dict) -> None:
        record_bytes = pm.d33_canonical_bytes(dict(record))
        captured.append(record_bytes)
        with record_path.open("xb") as handle:
            handle.write(record_bytes[:prefix_size])
            handle.flush()
            os.fsync(handle.fileno())
        raise RuntimeError("injected partial containment record write")

    monkeypatch.setattr(pm, "_write_containment_record", fail_after_prefix)
    with pytest.raises(RuntimeError, match="partial containment record"):
        pm._contain_file(
            source,
            containment_root=containment_root,
            basis_hash=basis_hash,
            namespace="partial-record-recovery",
        )
    artifacts = [
        path
        for path in containment_root.rglob("*")
        if path.is_file() and not path.name.endswith(pm._CONTAINMENT_RECORD_SUFFIX)
    ]
    assert len(artifacts) == 1
    record_path = pm._containment_record_path(artifacts[0])
    assert record_path.read_bytes() == captured[0][:prefix_size]

    monkeypatch.setattr(pm, "_write_containment_record", write_record)
    pm._reconcile_containment_records(containment_root)
    assert record_path.read_bytes() == captured[0]
    assert json.loads(record_path.read_bytes())["basis_hash"] == basis_hash


def test_step5_orphan_census_preserves_the_orphans_own_basis(
    b1b_step3_runtime: dict,
) -> None:
    current_basis = "a" * 64
    orphan_basis = "b" * 64
    paths = pm._lane_paths(current_basis)
    orphan = (
        paths["dataset_final_root"]
        / orphan_basis[:2]
        / f"{orphan_basis}.parquet"
    )
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"old-basis orphan")

    with b1b_step3_runtime["factory"]() as db:
        pm._contain_unreferenced_lane_files(db, paths=paths)

    assert not orphan.exists()
    pairs = _assert_exact_containment_ledgers(b1b_step3_runtime)
    assert len(pairs) == 1
    artifact, record = pairs[0]
    assert artifact.parent.name == orphan_basis
    assert record["basis_hash"] == orphan_basis
    assert record["basis_hash"] != current_basis


def test_step5_atomic_publish_never_overwrites_an_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "stage.parquet"
    destination = tmp_path / "final.parquet"
    source.write_bytes(b"new")
    destination.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        pm._atomic_rename_no_overwrite(source, destination)
    assert source.read_bytes() == b"new"
    assert destination.read_bytes() == b"existing"


def test_step5_atomic_publish_refuses_cross_volume_without_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "stage.parquet"
    destination_dir = tmp_path / "final"
    destination = destination_dir / "output.parquet"
    source.write_bytes(b"source")
    destination_dir.mkdir()
    real_stat = Path.stat
    destination_parent_stat = real_stat(destination_dir)
    source_device = real_stat(source).st_dev
    rename_calls: list[tuple[object, object]] = []

    class DifferentDeviceStat:
        st_mode = destination_parent_stat.st_mode
        st_dev = source_device + 1

    def mismatched_device_stat(path: Path, *args, **kwargs):
        if path == destination_dir:
            return DifferentDeviceStat()
        return real_stat(path, *args, **kwargs)

    def unexpected_rename(source_path, destination_path) -> None:
        rename_calls.append((source_path, destination_path))
        raise AssertionError("rename must not run across volumes")

    monkeypatch.setattr(Path, "stat", mismatched_device_stat)
    monkeypatch.setattr(pm.os, "rename", unexpected_rename)
    with pytest.raises(pm.PromotionIdentityError, match="crosses volumes"):
        pm._atomic_rename_no_overwrite(source, destination)
    assert rename_calls == []
    assert source.read_bytes() == b"source"
    assert not destination.exists()


def test_step5_rejects_prelinked_unequal_target_without_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-target")
    _enable_step5(monkeypatch)
    with b1b_step3_runtime["factory"]() as db:
        target = db.get(ConnectorRunTarget, b1b_step3_runtime["target_id"])
        assert target is not None
        target.dataset_id = str(uuid.uuid4())
        target.dataset_version_id = str(uuid.uuid4())
        db.commit()
    before = _materialization_census(b1b_step3_runtime)
    with pytest.raises(pm.ConnectorPromotionError) as caught:
        _resolve(b1b_step3_runtime, gate_b_session_id)
    assert caught.value.code == "connector_materialization_basis_conflict"
    assert _materialization_census(b1b_step3_runtime) == before
    assert _authoritative_step5_files(b1b_step3_runtime) == set()


_B1B_POSTGRES_STEP5_PROVISIONED = os.environ.get("B1B_POSTGRESQL_STEP5_PROVISIONED") == "1"
_skip_b1b_step5_postgresql = pytest.mark.skipif(
    not (
        _b1b_psycopg_available()
        and bool(_B1B_POSTGRES_URL)
        and bool(_B1B_POSTGRES_SCHEMA)
        and _B1B_POSTGRES_SCHEMA != "public"
        and _B1B_POSTGRES_STEP5_PROVISIONED
    ),
    reason=(
        "B1b Step 5 PostgreSQL cases require the later isolated materialization "
        "provider, psycopg, URL, and non-public pre-provisioned schema"
    ),
)


def _postgres_step5_case(request, case_id: str):
    factory = request.getfixturevalue("b1b_postgresql_step5_case")
    case = factory(case_id)
    assert case.case_id == case_id
    assert case.canonical_identity_key_hash == pm.F07_CANONICAL_IDENTITY_KEY_HASH
    assert case.two_independent_sessions is True
    assert case.schema_name == _B1B_POSTGRES_SCHEMA
    return case


@_skip_b1b_step5_postgresql
def test_b1b_postgresql_materialization_claim_race_is_single_winner(request) -> None:
    case = _postgres_step5_case(request, "materialization_claim_race")
    facts = case.run_materialization_claim_race()
    assert facts.status_codes == (200, 200)
    assert set(facts.dispositions) == {"materialized", "reused"}
    assert facts.materialized_receipt_count == 1
    assert facts.authoritative_parquet_count == 1
    assert facts.authoritative_snapshot_count == 1
    assert facts.unreferenced_output_count == 0
    case.register_and_cleanup(facts)


@_skip_b1b_step5_postgresql
def test_b1b_postgresql_post_publish_crash_recovery_contains_orphan(request) -> None:
    case = _postgres_step5_case(request, "post_publish_crash_recovery")
    facts = case.run_post_publish_crash_recovery(exit_code=73)
    assert facts.crash_exit_code == 73
    assert (facts.retry_status, facts.retry_disposition) == (200, "materialized")
    assert facts.contained_parquet_count == 1
    assert facts.contained_snapshot_count == 1
    assert facts.authoritative_parquet_count == 1
    assert facts.authoritative_snapshot_count == 1
    assert facts.orphan_adopted is False
    case.register_and_cleanup(facts)


_RESOLVE_PATH = "/api/v1/layer3/source/connector/promotion/resolve"
_OPERATOR_HEADERS = {
    "content-type": "application/json",
    "x-forwarded-groups": "b1b-workspace",
    "x-forwarded-user": "b1b-operator",
    "x-forwarded-roles": "owner",
}


def _configure_step5_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "proxy_roles_header", "x-forwarded-roles")
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")


def _closed_error(code: str, message: str, *, retryable: bool) -> dict[str, object]:
    return {
        "schema_id": "layer3.b1b_error.v1",
        "status": "error",
        "error_code": code,
        "message": message,
        "retryable": retryable,
    }


def _install_step5_db_override(runtime: dict) -> None:
    def override_db():
        with runtime["factory"]() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_db


def test_step5_route_precedence_auth_then_availability_then_validation(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        flag_false_before = _materialization_census(b1b_step3_runtime)
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        absent = client.post(
            _RESOLVE_PATH,
            content="{not-json",
            headers={"content-type": "application/json", "x-forwarded-groups": "bridge-sentinel"},
        )
        assert absent.status_code == 401
        assert absent.json()["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
        assert "connector_promotion_bridge_unavailable" not in absent.text

        auditor = client.post(
            _RESOLVE_PATH,
            content="{not-json",
            headers={
                "content-type": "application/json",
                "x-forwarded-groups": "b1b-workspace",
                "x-forwarded-user": "bridge-sentinel",
                "x-forwarded-roles": "auditor",
            },
        )
        assert auditor.status_code == 403
        assert auditor.json()["error_code"] == "sec_xbrl_in_app_auth_policy_role_access_forbidden"
        assert "connector_promotion_bridge_unavailable" not in auditor.text

        unavailable = client.post(_RESOLVE_PATH, content="{not-json", headers=_OPERATOR_HEADERS)
        assert unavailable.status_code == 503
        assert unavailable.json() == _closed_error(
            "connector_promotion_bridge_unavailable",
            "Connector promotion bridge is unavailable.",
            retryable=True,
        )
        assert _materialization_census(b1b_step3_runtime) == flag_false_before

        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
        monkeypatch.setattr(pm, "attestation_precondition_available", lambda _candidate=None: False)
        unattested = client.post(_RESOLVE_PATH, content="{not-json", headers=_OPERATOR_HEADERS)
        assert unattested.status_code == 503
        assert unattested.json() == unavailable.json()

        monkeypatch.setattr(pm, "attestation_precondition_available", lambda _candidate=None: True)
        sentinel = "b1b-rejected-secret-sentinel"
        monkeypatch.setattr(pm, "resolve_connector_promotion", _boom)
        with caplog.at_level(logging.INFO):
            malformed_responses = [
                client.post(
                    _RESOLVE_PATH,
                    content=f'{{"gate_b_session_id":"{sentinel}"',
                    headers=_OPERATOR_HEADERS,
                ),
                client.post(_RESOLVE_PATH, json={}, headers=_OPERATOR_HEADERS),
                client.post(_RESOLVE_PATH, json={"gate_b_session_id": 7}, headers=_OPERATOR_HEADERS),
                client.post(
                    _RESOLVE_PATH,
                    json={"gate_b_session_id": str(uuid.uuid4()), "forbidden_secret": sentinel},
                    headers=_OPERATOR_HEADERS,
                ),
            ]
        for malformed in malformed_responses:
            assert malformed.status_code == 422
            assert list(malformed.json()) == ["error_code", "message", "retryable", "schema_id", "status"]
            assert malformed.content == pm.d33_canonical_bytes(malformed.json())
            assert malformed.json() == _closed_error(
                "b1b_request_validation_failed",
                "Request body failed validation.",
                retryable=False,
            )
            assert sentinel not in malformed.text
            assert sentinel not in str(malformed.headers)
        assert sentinel not in caplog.text
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_step5_route_maps_not_found_and_not_eligible_to_closed_domains(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_step5_proxy(monkeypatch)
    _enable_step5(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        missing = client.post(
            _RESOLVE_PATH,
            json={"gate_b_session_id": str(uuid.uuid4())},
            headers=_OPERATOR_HEADERS,
        )
        assert missing.status_code == 404
        assert missing.json() == _closed_error(
            "connector_promotion_session_not_found",
            "Connector promotion session was not found.",
            retryable=False,
        )

        session_id = str(uuid.uuid4())
        with b1b_step3_runtime["factory"]() as db:
            db.add(
                L3Session(
                    session_id=session_id,
                    status="completed",
                    selection_manifest_id=str(uuid.uuid4()),
                    entry_route_context_json={},
                    operator_context_json={},
                    summary_json={},
                )
            )
            db.commit()
        ineligible = client.post(
            _RESOLVE_PATH,
            json={"gate_b_session_id": session_id},
            headers=_OPERATOR_HEADERS,
        )
        assert ineligible.status_code == 409
        assert ineligible.json() == _closed_error(
            "connector_promotion_not_eligible",
            "Connector promotion is not eligible.",
            retryable=False,
        )
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_step5_route_transports_all_closed_error_codes_canonically(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_step5_proxy(monkeypatch)
    _enable_step5(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    before = _materialization_census(b1b_step3_runtime)
    try:
        for code, (http_status, message, retryable) in pm._B1B_ERROR_SPECS.items():
            def fail_closed(*_args, _code=code, **_kwargs):
                raise pm._closed_b1b_error(_code)

            monkeypatch.setattr(pm, "resolve_connector_promotion", fail_closed)
            response = client.post(
                _RESOLVE_PATH,
                json={"gate_b_session_id": str(uuid.uuid4())},
                headers=_OPERATOR_HEADERS,
            )
            assert response.status_code == http_status
            assert response.json() == _closed_error(code, message, retryable=retryable)
            assert response.content == pm.d33_canonical_bytes(response.json())
        assert _materialization_census(b1b_step3_runtime) == before
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_step5_route_ignores_mutable_exception_transport_fields(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_step5_proxy(monkeypatch)
    _enable_step5(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)

    def fail_with_mismatched_transport(*_args, **_kwargs):
        raise pm.ConnectorPromotionError(
            "connector_promotion_not_eligible",
            "caller-controlled text",
            http_status=418,
            retryable=True,
        )

    monkeypatch.setattr(pm, "resolve_connector_promotion", fail_with_mismatched_transport)
    try:
        response = client.post(
            _RESOLVE_PATH,
            json={"gate_b_session_id": str(uuid.uuid4())},
            headers=_OPERATOR_HEADERS,
        )
        assert response.status_code == 409
        assert response.json() == _closed_error(
            "connector_promotion_not_eligible",
            "Connector promotion is not eligible.",
            retryable=False,
        )
        assert response.content == pm.d33_canonical_bytes(response.json())
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_step5_route_first_call_and_replay_have_exact_redacted_schema(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_b_session_id = _seed_materializable_receipt(b1b_step3_runtime, monkeypatch, "step5-route")
    _configure_step5_proxy(monkeypatch)
    _enable_step5(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        first = client.post(
            _RESOLVE_PATH,
            json={"gate_b_session_id": gate_b_session_id},
            headers=_OPERATOR_HEADERS,
        )
        assert first.status_code == 200, first.text
        assert set(first.json()) == _RESOLVE_KEYS
        assert first.json()["disposition"] == "materialized"
        assert first.content == pm.d33_canonical_bytes(first.json())
        census = _materialization_census(b1b_step3_runtime)
        files = _lane_files(b1b_step3_runtime)

        replay = client.post(
            _RESOLVE_PATH,
            json={"gate_b_session_id": gate_b_session_id},
            headers=_OPERATOR_HEADERS,
        )
        assert replay.status_code == 200, replay.text
        assert replay.json() == {**first.json(), "disposition": "reused"}
        assert replay.content == pm.d33_canonical_bytes(replay.json())
        assert _materialization_census(b1b_step3_runtime) == census
        assert _lane_files(b1b_step3_runtime) == files
    finally:
        main.app.dependency_overrides.pop(get_db, None)
