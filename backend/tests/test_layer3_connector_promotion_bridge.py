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

import base64
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
from urllib.parse import quote

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
from app.services import layer3_response_contract  # noqa: E402
from app.services import layer3_workbench  # noqa: E402
from app.services.layer3_session_entry import (  # noqa: E402
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import materialize_typing_entry  # noqa: E402
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


def _prepare_result_review_subject(
    runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    stem: str,
) -> tuple[dict, dict, dict, dict]:
    _gate_b_session_id, resolved = _materialize_replay_subject(runtime, monkeypatch, stem)
    with runtime["factory"]() as db:
        preview, approval = _approve_replay_subject(db, resolved["promoted_session_id"], stem)
        selection = _select_replay_subject(
            db,
            resolved["promoted_session_id"],
            stem,
            preview,
            approval,
        )
        start = _start_replay_subject(
            db,
            resolved["promoted_session_id"],
            stem,
            preview,
            approval,
            selection,
        )
    return resolved, preview, approval, start


def _prepare_ordinary_result_review_subject(
    runtime: dict,
    stem: str,
) -> tuple[str, dict, dict, dict]:
    dataset_id = str(uuid.uuid4())
    dataset_version_id = str(uuid.uuid4())
    csv_bytes = b"site_id,value\nordinary-a,1\nordinary-b,2\n"
    csv_path = runtime["storage_dir"] / "ordinary" / f"{dataset_version_id}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_bytes(csv_bytes)

    with runtime["factory"]() as db:
        db.add_all(
            [
                Dataset(
                    dataset_id=dataset_id,
                    source_id=None,
                    name="Ordinary parity dataset",
                    description="Non-connector result-review parity fixture",
                    domain_pack="parity",
                    frequency_hint=None,
                    time_column=None,
                ),
                DatasetVersion(
                    dataset_version_id=dataset_version_id,
                    dataset_id=dataset_id,
                    parent_version_id=None,
                    version_label="v1",
                    version_type="baseline",
                    status="ready",
                    storage_ref=str(csv_path),
                    row_count=2,
                    content_hash=hashlib.sha256(csv_bytes).hexdigest(),
                    source_row_count=2,
                    dropped_row_count=0,
                    notes="ordinary non-connector parity fixture",
                ),
                VariableDefinition(
                    dataset_version_id=dataset_version_id,
                    variable_name="site_id",
                    dtype="string",
                    role="dimension",
                    is_numeric=False,
                    is_time_index=False,
                    ordinal_position=0,
                ),
                VariableDefinition(
                    dataset_version_id=dataset_version_id,
                    variable_name="value",
                    dtype="int64",
                    role="measure",
                    is_numeric=True,
                    is_time_index=False,
                    ordinal_position=1,
                ),
            ]
        )
        session, manifest = commit_selection(
            db,
            SessionEntryRequest(
                manifest_items=[
                    {
                        "source_plane": "plane_a",
                        "descriptor_type": "dataset_version",
                        "selector_payload": {"dataset_version_id": dataset_version_id},
                        "selection_basis": {"selection_id": f"{stem}-selection"},
                        "expansion_reason": "committed_selection",
                    }
                ],
                source_plane_hints={"plane_a": ["dataset_version"]},
                commit_reason="ordinary_result_review_parity",
                entry_route_context={"entrypoint": "pytest"},
                operator_context={"operator": "pytest"},
                summary={"fixture": "ordinary_non_connector"},
            ),
        )
        descriptor = expand_descriptors(db, session=session, manifest=manifest)[0]
        record_retrieval_event(
            db,
            session=session,
            descriptor=descriptor,
            outcome="loaded",
            reason_code="loaded",
            loaded_materials=[
                SnapshotMaterial(
                    source_shape="dataset_version",
                    source_identity={
                        "dataset_id": dataset_id,
                        "dataset_version_id": dataset_version_id,
                    },
                    source_provenance={"storage_ref": str(csv_path)},
                    payload={"dataset_version_id": dataset_version_id},
                    load_summary={"loaded_records": 2, "failed_records": 0},
                )
            ],
            storage_root=runtime["storage_dir"] / "artifacts" / "layer3" / "ordinary",
        )
        finalize_session(db, session=session)
        materialize_typing_entry(db, session_id=session.session_id)
        db.commit()
        preview, approval = _approve_replay_subject(db, session.session_id, stem)
        selection = _select_replay_subject(db, session.session_id, stem, preview, approval)
        start = _start_replay_subject(
            db,
            session.session_id,
            stem,
            preview,
            approval,
            selection,
        )
        return session.session_id, preview, approval, start


def _b1b_04_review_payload(
    resolved: dict,
    preview: dict,
    approval: dict,
    start: dict,
    *,
    decision: str = "approved",
    review_notes: str = "",
) -> dict:
    basis = {
        "session_id": resolved["promoted_session_id"],
        "analysis_plan_id": approval["analysis_plan_id"],
        "pass_run_id": start["pass_run_id"],
        "preview_id": preview["preview_id"],
        "preview_hash": preview["preview_hash"],
        "analysis_run_id": start["analysis_run_id"],
        "operator_decision": decision,
        "review_notes": review_notes,
    }
    return {
        "client_request_id": f"b1b-result-review-{pm.d33_sha256(basis)}",
        **basis,
    }


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
    evidence = pm._b1b_result_artifact_evidence(
        db,
        receipt=receipt,
        analysis_run=analysis_run,
    )
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
        "result_payload_sha256": evidence["result_payload_sha256"],
        "analysis_artifact_id": evidence["analysis_artifact_id"],
        "analysis_artifact_sha256": evidence["analysis_artifact_sha256"],
        "assumption_check_ids": evidence["assumption_check_ids"],
        "caveat_note_id": evidence["caveat_note_id"],
        "reviewed_output_items": evidence["reviewed_output_items"],
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


@pytest.mark.parametrize(
    ("decision", "raw_notes", "stored_notes"),
    (
        ("approved", "", None),
        ("changes_requested", "  revise the bounded finding  ", "revise the bounded finding"),
        ("rejected", "  reject the bounded finding  ", "reject the bounded finding"),
        ("blocked", "  blocked by bounded evidence  ", "blocked by bounded evidence"),
    ),
)
def test_b1b_04_result_review_persists_exact_closed_projection_for_all_decisions(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    raw_notes: str,
    stored_notes: str | None,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        f"b1b-04-{decision}",
    )
    pass_run_id = start["pass_run_id"]
    request_basis = {
        "session_id": resolved["promoted_session_id"],
        "analysis_plan_id": approval["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview["preview_id"],
        "preview_hash": preview["preview_hash"],
        "analysis_run_id": start["analysis_run_id"],
        "operator_decision": decision,
        "review_notes": raw_notes,
    }
    basis_hash = pm.d33_sha256(request_basis)
    payload = {
        "client_request_id": f"b1b-result-review-{basis_hash}",
        **request_basis,
    }

    with b1b_step3_runtime["factory"]() as db:
        response = layer3_workbench.execution_result_review(db, payload)
    assert isinstance(response, pm.B1BClosedApiResponse)
    assert response.http_status == 200, response.body_bytes

    with b1b_step3_runtime["factory"]() as db:
        receipt = db.query(L3ConnectorPromotionReceipt).filter_by(
            promoted_session_id=resolved["promoted_session_id"]
        ).one()
        promoted = db.get(L3Session, resolved["promoted_session_id"])
        pass_run = db.get(L3PassRun, pass_run_id)
        artifact = db.query(AnalysisArtifact).filter_by(
            analysis_run_id=start["analysis_run_id"]
        ).one()
        checks = db.query(AssumptionCheck).filter_by(
            analysis_run_id=start["analysis_run_id"]
        ).all()
        caveat = db.query(CaveatNote).filter_by(
            analysis_run_id=start["analysis_run_id"]
        ).one()
        assert promoted is not None
        assert pass_run is not None
        artifact_bytes = (Path(settings.artifact_storage_dir) / Path(artifact.storage_ref).name).read_bytes()
        result_payload = _json.loads(artifact_bytes)
        ordered_check_ids = [
            next(row.assumption_check_id for row in checks if row.assumption_name == name)
            for name in (
                "data_availability",
                "column_classification",
                "missingness_scan",
                "time_column_coverage",
            )
        ]
        reviewed_items = [
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
        ]
        record = {
            "schema_id": "layer3.b1b_result_review_record.v1",
            "promotion_receipt_id": receipt.connector_promotion_receipt_id,
            "promoted_session_id": promoted.session_id,
            "analysis_plan_id": approval["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "analysis_run_id": start["analysis_run_id"],
            "result_payload_sha256": pm.d33_sha256(result_payload),
            "analysis_artifact_id": artifact.artifact_id,
            "analysis_artifact_sha256": _hashlib.sha256(artifact_bytes).hexdigest(),
            "assumption_check_ids": ordered_check_ids,
            "caveat_note_id": caveat.caveat_note_id,
            "reviewed_output_items": reviewed_items,
            "unresolved_trace_count": 0,
            "operator_decision": decision,
            "review_notes": stored_notes,
            "result_review_request_basis_hash": basis_hash,
        }
        result_review_hash = pm.d33_sha256(record)
        review_record_ref = f"b1b-result-review-{result_review_hash}"
        review_state = _RESULT_REVIEW_STATE_BY_DECISION[decision]
        expected_closed_review = {
            **record,
            "review_record_ref": review_record_ref,
            "review_state": review_state,
            "result_review_hash": result_review_hash,
        }
        assert pass_run.summary_json["execution_result_review"] == expected_closed_review
        assert promoted.summary_json == {
            "schema_id": "layer3.b1b_session_state.v1",
            "review_record_ref": review_record_ref,
            "review_state": review_state,
            "result_review_hash": result_review_hash,
            "analysis_plan_id": approval["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "analysis_run_id": start["analysis_run_id"],
            "package_review_state": None,
            "package_review_hash": None,
            "reconciliation_record_id": None,
            "packages": None,
            "connector_dataset_handoff_basis_hash": None,
        }
        assert _replay_summary_contract_valid(db, promoted.session_id) is True

    expected_response = {
        "schema_id": "layer3.b1b_result_review_response.v1",
        "promotion_receipt_id": resolved["connector_promotion_receipt_id"],
        "promoted_session_id": resolved["promoted_session_id"],
        "analysis_plan_id": approval["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "analysis_run_id": start["analysis_run_id"],
        "operator_decision": decision,
        "review_state": review_state,
        "result_review_hash": result_review_hash,
        "review_notes_present": stored_notes is not None,
        "review_notes_sha256": (
            _hashlib.sha256(stored_notes.encode("utf-8")).hexdigest()
            if stored_notes is not None
            else None
        ),
        "package_review_preview_enabled": decision == "approved",
    }
    assert isinstance(response, pm.B1BClosedApiResponse)
    assert response.http_status == 200
    assert response.body_bytes == pm.d33_canonical_bytes(expected_response)
    assert _json.loads(response.body_bytes) == expected_response


def test_b1b_04_exact_replay_and_both_conflict_classes_are_zero_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-04-replay",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)

    with b1b_step3_runtime["factory"]() as db:
        first = layer3_workbench.execution_result_review(db, payload)
    assert isinstance(first, pm.B1BClosedApiResponse)
    assert first.http_status == 200
    frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
    frozen_files = _all_storage_files(b1b_step3_runtime)
    assert frozen_rows["L3ReconciliationRecord"] == []
    assert frozen_rows["L3OutputPackage"] == []

    with b1b_step3_runtime["factory"]() as db:
        replay = layer3_workbench.execution_result_review(db, payload)
    assert isinstance(replay, pm.B1BClosedApiResponse)
    assert replay.http_status == 200
    assert replay.body_bytes == first.body_bytes
    assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
    assert _all_storage_files(b1b_step3_runtime) == frozen_files

    malformed_replay_id = {**payload, "client_request_id": "b1b-result-review-wrong"}
    with b1b_step3_runtime["factory"]() as db:
        with pytest.raises(pm.B1BClosedApiError) as malformed_replay:
            layer3_workbench.execution_result_review(db, malformed_replay_id)
    assert (malformed_replay.value.code, malformed_replay.value.http_status) == (
        "b1b_request_validation_failed",
        422,
    )
    assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
    assert _all_storage_files(b1b_step3_runtime) == frozen_files

    unequal_basis = {
        **payload,
        "operator_decision": "changes_requested",
        "review_notes": "revise bounded result",
    }
    second_decision = _b1b_04_review_payload(
        resolved,
        preview,
        approval,
        start,
        decision="changes_requested",
        review_notes="revise bounded result",
    )
    for conflict_payload in (unequal_basis, second_decision):
        with b1b_step3_runtime["factory"]() as db:
            with pytest.raises(pm.B1BClosedApiError) as conflict:
                layer3_workbench.execution_result_review(db, conflict_payload)
        assert (conflict.value.code, conflict.value.http_status) == (
            "connector_result_review_decision_conflict",
            409,
        )
        assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
        assert _all_storage_files(b1b_step3_runtime) == frozen_files


def test_b1b_04_closed_request_profile_rejects_notes_and_all_evidence_widening_without_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-04-profile",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)
    generic_optional_fields = (
        "package",
        "package_review",
        "handoff",
        "export",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
        "runtime_db_write",
        "artifact_manifest",
        "package_variant",
        "aps_handoff",
        "edited_findings",
        "rewrite_output",
    )
    invalid_payloads = [
        {**payload, "reviewed_output_items": []},
        {**payload, "connector_b1_evidence": {}},
        {**payload, "review_notes": "not empty"},
        {**payload, "operator_decision": "changes_requested", "review_notes": "   "},
        {**payload, "operator_decision": "other"},
        {**payload, "client_request_id": "b1b-result-review-wrong"},
        {**payload, "review_notes": None},
        *({**payload, field: None} for field in generic_optional_fields),
    ]
    frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
    frozen_files = _all_storage_files(b1b_step3_runtime)

    for invalid_payload in invalid_payloads:
        with b1b_step3_runtime["factory"]() as db:
            with pytest.raises(pm.B1BClosedApiError) as response:
                layer3_workbench.execution_result_review(db, invalid_payload)
        assert (response.value.code, response.value.http_status) == (
            "b1b_request_validation_failed",
            422,
        )
        assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
        assert _all_storage_files(b1b_step3_runtime) == frozen_files


@pytest.mark.parametrize(
    "leaking_value",
    (
        {"Proxy Authorization": "sentinel"},
        {"\uff30\uff21\uff33\uff33\uff37\uff2f\uff32\uff24": "sentinel"},
        {"note": r"C:\temp\sentinel.txt"},
        {"note": r"\\server\share\sentinel.txt"},
        {"note": "/tmp/sentinel.txt"},
        {"note": "file:///tmp/sentinel.txt"},
        {"note": "safe/%252e%252e/sentinel"},
        {"note": "https://user:password@example.test/resource"},
        {"note": "https://example.test/resource?access-token=sentinel"},
        {"note": "Bearer sentinel"},
        {"note": "Cookie: session=sentinel"},
    ),
)
def test_b1b_04_closed_transport_recursive_no_leak_rejects_key_and_value_evasions(
    leaking_value: object,
) -> None:
    with pytest.raises(pm.PromotionIdentityError):
        pm._assert_b1b04_closed_body_no_leak(leaking_value)

    pm._assert_b1b04_closed_body_no_leak(
        {
            "storage_ref_hash": "a" * 64,
            "message": "Benign status text contains no raw reference.",
        }
    )


def test_b1b_04_reader_extension_accepts_only_exact_closed_state_and_preserves_native_reader(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-04-reader",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with b1b_step3_runtime["factory"]() as db:
        response = layer3_workbench.execution_result_review(db, payload)
    assert isinstance(response, pm.B1BClosedApiResponse)
    assert response.http_status == 200

    with b1b_step3_runtime["factory"]() as db:
        pass_run = db.get(L3PassRun, start["pass_run_id"])
        assert pass_run is not None
        original_summary = copy.deepcopy(pass_run.summary_json)
        closed_state = pm.b1b_result_review_from_pass_run(db, pass_run)
        assert closed_state is not None
        assert closed_state["source_preview_id"] == preview["preview_id"]
        assert closed_state["source_preview_hash"] == preview["preview_hash"]
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) == closed_state

        malformed_fields = (
            ("promotion_receipt_id", str(uuid.uuid4())),
            ("promoted_session_id", str(uuid.uuid4())),
            ("analysis_plan_id", str(uuid.uuid4())),
            ("pass_run_id", str(uuid.uuid4())),
            ("preview_id", ""),
            ("preview_hash", "A" * 64),
            ("analysis_run_id", str(uuid.uuid4())),
            ("result_payload_sha256", "short"),
            ("analysis_artifact_id", str(uuid.uuid4())),
            ("analysis_artifact_sha256", "B" * 64),
            ("assumption_check_ids", [str(uuid.uuid4()) for _index in range(4)]),
            ("caveat_note_id", str(uuid.uuid4())),
            ("unresolved_trace_count", False),
            ("result_review_request_basis_hash", "C" * 64),
        )
        for field, malformed_value in malformed_fields:
            malformed_review = copy.deepcopy(original_summary["execution_result_review"])
            malformed_review[field] = malformed_value
            malformed_record = {
                key: malformed_review[key] for key in pm._RESULT_REVIEW_RECORD_KEYS
            }
            malformed_hash = pm.d33_sha256(malformed_record)
            malformed_review["result_review_hash"] = malformed_hash
            malformed_review["review_record_ref"] = f"b1b-result-review-{malformed_hash}"
            pass_run.summary_json = {
                **original_summary,
                "execution_result_review": malformed_review,
            }
            assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None

        mismatched_preview_summary = copy.deepcopy(original_summary)
        mismatched_preview_summary["source_preview_id"] = "different-preview"
        pass_run.summary_json = mismatched_preview_summary
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None

        malformed_review = copy.deepcopy(original_summary["execution_result_review"])
        malformed_review["trace_summary"] = {}
        pass_run.summary_json = {**original_summary, "execution_result_review": malformed_review}
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None

        pass_run.summary_json = {
            **original_summary,
            "execution_result_review": {"schema_id": "layer3.unrecognized_review_state.v1"},
        }
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None

        native_state = {
            "schema_id": "layer3.execution_result_review_state.v1",
            "operator_decision": "approved",
            "review_state": "execution_result_review_approved",
        }
        pass_run.summary_json = {**original_summary, "execution_result_review": native_state}
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None

        mixed_native_state = {
            **native_state,
            "promotion_receipt_id": str(uuid.uuid4()),
        }
        pass_run.summary_json = {**original_summary, "execution_result_review": mixed_native_state}
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None

        promoted = db.get(L3Session, resolved["promoted_session_id"])
        assert promoted is not None
        original_promoted_summary = copy.deepcopy(promoted.summary_json)
        promoted.summary_json = {**original_promoted_summary, "result_review_hash": "d" * 64}
        pass_run.summary_json = original_summary
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None
        promoted.summary_json = original_promoted_summary

        pass_run.summary_json = original_summary
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None
        assert pm.side_effect_free_b1b_result_review_scope(db.get_bind(), str(uuid.uuid4())) is False

        pass_run.summary_json = {**original_summary, "execution_result_review": mixed_native_state}
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) == mixed_native_state
        db.rollback()


@pytest.mark.parametrize(
    "corruption",
    ("artifact", "check_order", "check_content", "caveat"),
)
def test_b1b_04_reader_rejects_rehashed_post_record_authority_drift(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        f"b1b-04-post-record-{corruption}",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with b1b_step3_runtime["factory"]() as db:
        response = layer3_workbench.execution_result_review(db, payload)
    assert isinstance(response, pm.B1BClosedApiResponse)
    assert response.http_status == 200

    with b1b_step3_runtime["factory"]() as db:
        pass_run = db.get(L3PassRun, start["pass_run_id"])
        promoted = db.get(L3Session, resolved["promoted_session_id"])
        assert pass_run is not None and promoted is not None
        pass_summary = copy.deepcopy(pass_run.summary_json)
        review = copy.deepcopy(pass_summary["execution_result_review"])
        if corruption == "artifact":
            artifact = db.query(AnalysisArtifact).filter_by(
                analysis_run_id=start["analysis_run_id"]
            ).one()
            path = Path(settings.artifact_storage_dir) / Path(artifact.storage_ref).name
            document = _json.loads(path.read_bytes())
            document["method_id"] = "drifted_method"
            drifted_bytes = pm.d33_canonical_bytes(document)
            path.write_bytes(drifted_bytes)
            review["result_payload_sha256"] = pm.d33_sha256(document)
            review["analysis_artifact_sha256"] = hashlib.sha256(drifted_bytes).hexdigest()
        elif corruption == "check_order":
            review["assumption_check_ids"] = list(reversed(review["assumption_check_ids"]))
        elif corruption == "check_content":
            check = db.query(AssumptionCheck).filter_by(
                analysis_run_id=start["analysis_run_id"],
                assumption_name="missingness_scan",
            ).one()
            check.notes = "drifted after review"
        else:
            caveat = db.query(CaveatNote).filter_by(
                analysis_run_id=start["analysis_run_id"]
            ).one()
            caveat.message = "drifted after review"

        record = {key: review[key] for key in pm._RESULT_REVIEW_RECORD_KEYS}
        result_hash = pm.d33_sha256(record)
        review_record_ref = f"b1b-result-review-{result_hash}"
        review["result_review_hash"] = result_hash
        review["review_record_ref"] = review_record_ref
        pass_run.summary_json = {
            **pass_summary,
            "execution_result_review": review,
        }
        promoted.summary_json = {
            **copy.deepcopy(promoted.summary_json),
            "review_record_ref": review_record_ref,
            "result_review_hash": result_hash,
        }
        db.commit()

    frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
    frozen_files = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        pass_run = db.get(L3PassRun, start["pass_run_id"])
        promoted = db.get(L3Session, resolved["promoted_session_id"])
        receipt = db.query(L3ConnectorPromotionReceipt).filter_by(
            promoted_session_id=resolved["promoted_session_id"]
        ).one()
        assert pass_run is not None and promoted is not None
        assert pm.b1b_result_review_from_pass_run(db, pass_run) is None
        assert layer3_workbench._downstream_execution_result_review_from_pass_run(db, pass_run) is None
        assert not pm._materialized_replay_summary_is_valid(
            db,
            receipt=receipt,
            promoted=promoted,
        )
    assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
    assert _all_storage_files(b1b_step3_runtime) == frozen_files


@pytest.mark.parametrize("corruption", ("artifact", "check", "caveat"))
def test_b1b_04_corrupt_authoritative_evidence_fails_closed_without_review_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        f"b1b-04-corrupt-{corruption}",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with b1b_step3_runtime["factory"]() as db:
        if corruption == "artifact":
            artifact = db.query(AnalysisArtifact).filter_by(
                analysis_run_id=start["analysis_run_id"]
            ).one()
            path = Path(settings.artifact_storage_dir) / Path(artifact.storage_ref).name
            document = _json.loads(path.read_bytes())
            document["method_id"] = "drifted_method"
            path.write_text(_json.dumps(document, indent=2), encoding="utf-8")
        elif corruption == "check":
            check = db.query(AssumptionCheck).filter_by(
                analysis_run_id=start["analysis_run_id"],
                assumption_name="missingness_scan",
            ).one()
            check.notes = "drifted check"
            db.commit()
        else:
            caveat = db.query(CaveatNote).filter_by(
                analysis_run_id=start["analysis_run_id"]
            ).one()
            caveat.message = "drifted caveat"
            db.commit()
    frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
    frozen_files = _all_storage_files(b1b_step3_runtime)

    with b1b_step3_runtime["factory"]() as db:
        with pytest.raises(pm.B1BClosedApiError) as response:
            layer3_workbench.execution_result_review(db, payload)
    assert (response.value.code, response.value.http_status) == (
        "connector_materialization_basis_conflict",
        409,
    )
    assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
    assert _all_storage_files(b1b_step3_runtime) == frozen_files


def test_b1b_04_flag_false_keeps_receipt_session_on_unchanged_native_review_path(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-04-flag-false",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
    monkeypatch.setattr(pm, "record_b1b_result_review", _boom)

    with b1b_step3_runtime["factory"]() as db:
        response = layer3_workbench.execution_result_review(db, payload)
        pass_run = db.get(L3PassRun, start["pass_run_id"])
        assert pass_run is not None
        native_state = layer3_workbench._execution_result_review_from_pass_run(pass_run)
    assert isinstance(response, dict)
    assert response["status"] == "recorded"
    assert native_state is not None
    assert native_state["schema_id"] == "layer3.execution_result_review_state.v1"


def test_b1b_04_scope_checks_full_process_precondition_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
    monkeypatch.setattr(pm, "attestation_precondition_available", lambda _candidate=None: False)
    monkeypatch.setattr(pm, "OrmSession", _boom)

    assert pm.side_effect_free_b1b_result_review_scope(object(), str(uuid.uuid4())) is False


def test_b1b_04_ordinary_validation_error_preserves_native_bytes_when_bridge_enabled(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id, _, _, _ = _prepare_ordinary_result_review_subject(
        b1b_step3_runtime,
        "b1b-04-native-validation-parity",
    )
    payload = {"session_id": session_id, "unknown_evidence": "ordinary-native-sentinel"}
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        native = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert native.status_code == 422
        assert native.json() != pm.b1b_error_body("b1b_request_validation_failed")

        _enable_step5(monkeypatch)
        enabled = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert enabled.status_code == native.status_code
        assert enabled.content == native.content
        assert enabled.headers["content-type"] == native.headers["content-type"]
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_04_unparseable_shared_route_body_preserves_native_validation_bytes(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        native = client.post(_RESULT_REVIEW_PATH, content="{not-json", headers=_OPERATOR_HEADERS)
        assert native.status_code == 422
        assert native.json() != pm.b1b_error_body("b1b_request_validation_failed")

        classifier = main._b1b_shared_validation_is_receipt_bound
        monkeypatch.setattr(main, "_b1b_shared_validation_is_receipt_bound", _boom)
        flag_off = client.post(_RESULT_REVIEW_PATH, content="{not-json", headers=_OPERATOR_HEADERS)
        assert flag_off.status_code == native.status_code
        assert flag_off.content == native.content
        assert flag_off.headers["content-type"] == native.headers["content-type"]
        monkeypatch.setattr(main, "_b1b_shared_validation_is_receipt_bound", classifier)

        original_request_body = main.Request.body
        body_call_counts: dict[int, int] = {}

        async def fail_on_handler_body_reread(request):
            request_key = id(request)
            body_call_counts[request_key] = body_call_counts.get(request_key, 0) + 1
            if body_call_counts[request_key] > 2:
                raise AssertionError("validation handler must classify from RequestValidationError.body")
            return await original_request_body(request)

        monkeypatch.setattr(main.Request, "body", fail_on_handler_body_reread)
        _enable_step5(monkeypatch)
        enabled = client.post(_RESULT_REVIEW_PATH, content="{not-json", headers=_OPERATOR_HEADERS)
        assert enabled.status_code == native.status_code
        assert enabled.content == native.content
        assert enabled.headers["content-type"] == native.headers["content-type"]
        assert max(body_call_counts.values()) == 2
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_04_shared_validation_classifier_errors_preserve_native_bytes(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"session_id": str(uuid.uuid4()), "unknown_evidence": "native-error-sentinel"}
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        native = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert native.status_code == 422

        _enable_step5(monkeypatch)
        for error_type in (RecursionError, MemoryError, AttributeError, TypeError):
            def raise_classifier_error(*_args, _error_type=error_type, **_kwargs):
                raise _error_type("classifier failure")

            monkeypatch.setattr(
                pm,
                "side_effect_free_b1b_result_review_scope",
                raise_classifier_error,
            )
            response = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
            assert response.status_code == native.status_code
            assert response.content == native.content
            assert response.headers["content-type"] == native.headers["content-type"]
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_04_ordinary_route_preserves_exact_native_bytes_and_state_flag_off_and_no_receipt(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id, preview, approval, start = _prepare_ordinary_result_review_subject(
        b1b_step3_runtime,
        "b1b-04-native-route-parity",
    )
    payload = {
        "client_request_id": "ordinary-native-result-review-parity",
        "session_id": session_id,
        "analysis_plan_id": approval["analysis_plan_id"],
        "pass_run_id": start["pass_run_id"],
        "preview_id": preview["preview_id"],
        "preview_hash": preview["preview_hash"],
        "analysis_run_id": start["analysis_run_id"],
        "operator_decision": "approved",
        "review_notes": "",
    }
    fixed_time = "2026-07-21T12:00:00.000000Z"
    monkeypatch.setattr(layer3_workbench, "_utcnow_iso", lambda: fixed_time)
    monkeypatch.setattr(layer3_response_contract, "utcnow_iso_z", lambda: fixed_time)
    monkeypatch.setattr(pm, "record_b1b_result_review", _boom)
    _enable_step5(monkeypatch)
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    files_before = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        pass_run = db.get(L3PassRun, start["pass_run_id"])
        session = db.get(L3Session, session_id)
        assert pass_run is not None and session is not None
        assert db.query(L3ConnectorPromotionReceipt).filter_by(promoted_session_id=session_id).count() == 0
        pass_summary_before = copy.deepcopy(pass_run.summary_json)
        session_summary_before = copy.deepcopy(session.summary_json)
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        flag_off = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert flag_off.status_code == 200, flag_off.text
        assert flag_off.json()["schema_id"] == "layer3.execution_result_review.v1"
        assert flag_off.json()["status"] == "recorded"
        assert flag_off.content == _json.dumps(
            flag_off.json(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")

        oracle_projection = _b1b_03_row_projection(b1b_step3_runtime)
        with b1b_step3_runtime["factory"]() as db:
            pass_run = db.get(L3PassRun, start["pass_run_id"])
            session = db.get(L3Session, session_id)
            assert pass_run is not None and session is not None
            pass_run.summary_json = pass_summary_before
            session.summary_json = session_summary_before
            db.commit()

        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", True)
        no_receipt = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert no_receipt.status_code == 200, no_receipt.text
        assert no_receipt.content == flag_off.content
        assert no_receipt.json() == flag_off.json()
        assert "promotion_receipt_id" not in no_receipt.json()
        assert "result_review_hash" not in no_receipt.json()
    finally:
        main.app.dependency_overrides.pop(get_db, None)

    assert _b1b_03_row_projection(b1b_step3_runtime) == oracle_projection
    assert _all_storage_files(b1b_step3_runtime) == files_before


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
_RESULT_REVIEW_PATH = "/api/v1/layer3/execution/result/review"
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


def test_b1b_04_route_preserves_auth_precedence_and_canonical_closed_transport(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-04-route",
    )
    payload = _b1b_04_review_payload(resolved, preview, approval, start)
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        absent = client.post(
            _RESULT_REVIEW_PATH,
            content="{not-json",
            headers={"content-type": "application/json"},
        )
        assert absent.status_code == 401
        assert absent.json()["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
        assert "b1b_request_validation_failed" not in absent.text

        auditor = client.post(
            _RESULT_REVIEW_PATH,
            content="{not-json",
            headers={
                "content-type": "application/json",
                "x-forwarded-groups": "b1b-workspace",
                "x-forwarded-user": "auditor-1",
                "x-forwarded-roles": "auditor",
            },
        )
        assert auditor.status_code == 403
        assert auditor.json()["error_code"] == "sec_xbrl_in_app_auth_policy_role_access_forbidden"
        assert "b1b_request_validation_failed" not in auditor.text

        first = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert first.status_code == 200, first.text
        assert set(first.json()) == pm._B1B_RESULT_REVIEW_RESPONSE_KEYS
        assert first.content == pm.d33_canonical_bytes(first.json())
        assert first.json()["package_review_preview_enabled"] is True
        frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
        frozen_files = _all_storage_files(b1b_step3_runtime)

        replay = client.post(_RESULT_REVIEW_PATH, json=payload, headers=_OPERATOR_HEADERS)
        assert replay.status_code == 200
        assert replay.content == first.content

        second_decision = _b1b_04_review_payload(
            resolved,
            preview,
            approval,
            start,
            decision="rejected",
            review_notes="bounded rejection",
        )
        conflict = client.post(
            _RESULT_REVIEW_PATH,
            json=second_decision,
            headers=_OPERATOR_HEADERS,
        )
        assert conflict.status_code == 409
        assert conflict.json() == pm.b1b_error_body("connector_result_review_decision_conflict")
        assert conflict.content == pm.d33_canonical_bytes(conflict.json())

        malformed_responses = (
            client.post(
                _RESULT_REVIEW_PATH,
                json={**payload, "unknown_evidence": "do-not-echo"},
                headers=_OPERATOR_HEADERS,
            ),
            client.post(
                _RESULT_REVIEW_PATH,
                json={**payload, "reviewed_output_items": []},
                headers=_OPERATOR_HEADERS,
            ),
            client.post(
                _RESULT_REVIEW_PATH,
                json={**payload, "package": None},
                headers=_OPERATOR_HEADERS,
            ),
        )
        for malformed in malformed_responses:
            assert malformed.status_code == 422
            assert malformed.json() == pm.b1b_error_body("b1b_request_validation_failed")
            assert malformed.content == pm.d33_canonical_bytes(malformed.json())
            assert "do-not-echo" not in malformed.text
        assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
        assert _all_storage_files(b1b_step3_runtime) == frozen_files
    finally:
        main.app.dependency_overrides.pop(get_db, None)


_PACKAGE_PREVIEW_PATH = "/api/v1/layer3/package/review/preview"
_PACKAGE_COMMIT_PATH = "/api/v1/layer3/package/review/commit"
_PACKAGE_SUBMIT_PATH = "/api/v1/layer3/package/review/submit"
_B1B05_AUTHORITY = {
    "packet_full_sha256": "1" * 64,
    "packet_canonical_sha256": "2" * 64,
    "correction_full_sha256": "3" * 64,
    "owner_decision_full_sha256": "4" * 64,
    "owner_decision_canonical_sha256": "5" * 64,
    "owner_bound_main_sha": "6" * 40,
    "implementation_head_sha": "7" * 40,
    "pass_to_launch_sha256": "8" * 64,
    "profile": "sqlite_authorized",
}


def _extract_frozen_b1b05_construction_vector() -> bytes:
    spec = (
        BACKEND.parent
        / "next_milestone_plans"
        / "Layer3_planning_docs"
        / "b1b-dispatch-correction.md"
    ).read_bytes()
    marker = b"The normative construction-basis golden vector is 1,447 bytes"
    fenced = spec.split(marker, 1)[1].split(b"```json", 1)[1].split(b"```", 1)[0]
    return fenced.strip()


def _b1b05_preview_payload(
    resolved: dict,
    preview: dict,
    approval: dict,
    start: dict,
    review: dict,
) -> dict:
    return {
        "session_id": resolved["promoted_session_id"],
        "analysis_plan_id": approval["analysis_plan_id"],
        "pass_run_id": start["pass_run_id"],
        "preview_id": preview["preview_id"],
        "preview_hash": preview["preview_hash"],
        "analysis_run_id": start["analysis_run_id"],
        "result_review_record_ref": f"b1b-result-review-{review['result_review_hash']}",
    }


def _b1b05_commit_payload(preview_payload: dict, package_preview: dict) -> dict:
    return {
        "client_request_id": f"b1b-package-construction-{package_preview['package_review_preview_hash']}",
        **preview_payload,
        "package_review_preview_hash": package_preview["package_review_preview_hash"],
        "expected_package_kinds": list(_PACKAGE_ORDER),
    }


def _b1b05_submit_payload(
    preview_payload: dict,
    package_preview: dict,
    package_commit: dict,
    *,
    decision: str,
    notes: str,
) -> dict:
    packages = package_commit["packages"]
    basis = {
        "session_id": preview_payload["session_id"],
        "analysis_plan_id": preview_payload["analysis_plan_id"],
        "pass_run_id": preview_payload["pass_run_id"],
        "preview_id": preview_payload["preview_id"],
        "preview_hash": preview_payload["preview_hash"],
        "analysis_run_id": preview_payload["analysis_run_id"],
        "result_review_record_ref": preview_payload["result_review_record_ref"],
        "package_review_preview_hash": package_preview["package_review_preview_hash"],
        "construction_basis_hash": package_commit["construction_basis_hash"],
        "reconciliation_record_id": package_commit["reconciliation_record_id"],
        "output_package_ids": [item["output_package_id"] for item in packages],
        "payload_hashes": [item["payload_sha256"] for item in packages],
        "operator_decision": decision,
        "decision_notes": notes,
        "expected_package_kinds": list(_PACKAGE_ORDER),
    }
    return {
        "client_request_id": f"b1b-package-review-{pm.d33_sha256(basis)}",
        **basis,
    }


def _with_b1b05_submit_identity(payload: dict) -> dict:
    basis = {key: value for key, value in payload.items() if key != "client_request_id"}
    return {"client_request_id": f"b1b-package-review-{pm.d33_sha256(basis)}", **basis}


def _committed_b1b05_subject(
    runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> dict:
    resolved, preview, approval, start = _prepare_result_review_subject(
        runtime,
        monkeypatch,
        suffix,
    )
    monkeypatch.setattr(pm, "_read_b1b_package_authority", lambda: dict(_B1B05_AUTHORITY))
    review_payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with runtime["factory"]() as db:
        review = json.loads(pm.record_b1b_result_review(db, review_payload).body_bytes)
    preview_payload = _b1b05_preview_payload(
        resolved,
        preview,
        approval,
        start,
        review,
    )
    with runtime["factory"]() as db:
        package_preview = json.loads(pm.preview_b1b_package_review(db, preview_payload).body_bytes)
    commit_payload = _b1b05_commit_payload(preview_payload, package_preview)
    with runtime["factory"]() as db:
        package_commit_response = pm.commit_b1b_packages(db, commit_payload)
    package_commit = json.loads(package_commit_response.body_bytes)
    return {
        "resolved": resolved,
        "review_payload": review_payload,
        "preview_payload": preview_payload,
        "package_preview": package_preview,
        "commit_payload": commit_payload,
        "package_commit": package_commit,
        "package_commit_bytes": package_commit_response.body_bytes,
        "submit_payload": _b1b05_submit_payload(
            preview_payload,
            package_preview,
            package_commit,
            decision="approved",
            notes="",
        ),
    }


def test_b1b_05_committed_replay_censuses_and_contains_package_orphans(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _committed_b1b05_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-05-replay-census",
    )
    paths = pm._b1b_package_lane_paths()
    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        package_rows = db.query(L3OutputPackage).filter_by(
            session_id=subject["resolved"]["promoted_session_id"]
        ).all()
        authoritative_before = {
            Path(row.payload_ref).resolve(): pm._file_facts(Path(row.payload_ref).resolve())
            for row in package_rows
        }

    stage_basis = "a" * 64
    final_basis = "b" * 64
    stage_orphan = paths["stage"] / f"{stage_basis}-orphan-canonical_internal.json"
    final_orphan = paths["final"] / final_basis[:2] / final_basis / "orphan.json"
    stage_orphan.parent.mkdir(parents=True, exist_ok=True)
    final_orphan.parent.mkdir(parents=True, exist_ok=True)
    stage_orphan.write_bytes(b"staged package orphan")
    final_orphan.write_bytes(b"published package orphan")
    orphan_facts = {
        stage_basis: pm._file_facts(stage_orphan),
        final_basis: pm._file_facts(final_orphan),
    }

    with b1b_step3_runtime["factory"]() as db:
        replay = pm.commit_b1b_packages(db, subject["commit_payload"])

    assert replay.body_bytes == subject["package_commit_bytes"]
    assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
    assert not stage_orphan.exists()
    assert not final_orphan.exists()
    assert {
        path: pm._file_facts(path) for path in authoritative_before
    } == authoritative_before

    containment_files = {
        path for path in paths["containment"].rglob("*") if path.is_file()
    }
    contained = {
        path
        for path in containment_files
        if not path.name.endswith(pm._CONTAINMENT_RECORD_SUFFIX)
    }
    records = containment_files - contained
    assert len(contained) == 2
    assert records == {pm._containment_record_path(path) for path in contained}
    observed: dict[str, tuple[int, str]] = {}
    for artifact in contained:
        record = json.loads(pm._containment_record_path(artifact).read_bytes())
        facts = pm._file_facts(artifact)
        assert set(record) == {
            "artifact_bytes",
            "artifact_sha256",
            "basis_hash",
            "namespace_hash",
            "status",
        }
        assert record["artifact_bytes"] == facts[0]
        assert record["artifact_sha256"] == facts[1]
        assert record["basis_hash"] == artifact.parent.name
        assert pm._is_lower_hex64(record["namespace_hash"])
        assert record["status"] == "non_authoritative_non_reusable"
        observed[record["basis_hash"]] = facts
    assert observed == orphan_facts
    files_after = _all_storage_files(b1b_step3_runtime)
    for relative_path, facts in files_before.items():
        assert files_after[relative_path] == facts
    containment_relatives = {
        path.relative_to(b1b_step3_runtime["storage_dir"]).as_posix()
        for path in containment_files
    }
    assert set(files_after) == set(files_before) | containment_relatives


def test_b1b_05_all_closed_errors_are_canonical_at_all_four_routes(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _committed_b1b05_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-05-closed-errors",
    )
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    routes = (
        (_RESULT_REVIEW_PATH, "execution_result_review", subject["review_payload"]),
        (_PACKAGE_PREVIEW_PATH, "package_review_preview", subject["preview_payload"]),
        (_PACKAGE_COMMIT_PATH, "package_construction_commit", subject["commit_payload"]),
        (_PACKAGE_SUBMIT_PATH, "package_review_submit", subject["submit_payload"]),
    )
    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    observed: set[tuple[str, str]] = set()
    try:
        for error_code, (http_status, _message, _retryable) in pm._B1B_ERROR_SPECS.items():
            assert isinstance(pm._closed_b1b_error(error_code), pm.B1BClosedApiError)
            for path, handler_name, payload in routes:
                def fail_closed(*_args, _error_code=error_code, **_kwargs):
                    raise pm._closed_b1b_error(_error_code)

                with monkeypatch.context() as route_patch:
                    route_patch.setattr(layer3_workbench, handler_name, fail_closed)
                    response = client.post(path, json=payload, headers=_OPERATOR_HEADERS)
                expected = pm.b1b_error_body(error_code)
                assert response.status_code == http_status
                assert response.json() == expected
                assert response.content == pm.d33_canonical_bytes(expected)
                observed.add((error_code, path))
        assert observed == {
            (error_code, path)
            for error_code in pm._B1B_ERROR_SPECS
            for path, _handler_name, _payload in routes
        }
        assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
        assert _all_storage_files(b1b_step3_runtime) == files_before
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_05_base_lock_failure_is_typed_by_services_and_intercepted_by_routes(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _committed_b1b05_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-05-lock-error",
    )
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    code = "promotion_identity_lock_unavailable"
    http_status, message, retryable = pm._B1B_ERROR_SPECS[code]

    def fail_lock(*_args, **_kwargs):
        raise pm.ConnectorPromotionError(
            code,
            message,
            http_status=http_status,
            retryable=retryable,
        )

    monkeypatch.setattr(pm, "acquire_promotion_identity_lock", fail_lock)
    routes = (
        (_RESULT_REVIEW_PATH, "execution_result_review", subject["review_payload"]),
        (_PACKAGE_PREVIEW_PATH, "package_review_preview", subject["preview_payload"]),
        (_PACKAGE_COMMIT_PATH, "package_construction_commit", subject["commit_payload"]),
        (_PACKAGE_SUBMIT_PATH, "package_review_submit", subject["submit_payload"]),
    )
    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    for _path, handler_name, payload in routes:
        with b1b_step3_runtime["factory"]() as db:
            with pytest.raises(pm.B1BClosedApiError) as caught:
                getattr(layer3_workbench, handler_name)(db, payload)
        assert (caught.value.code, caught.value.http_status) == (code, http_status)

    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        expected = pm.b1b_error_body(code)
        for path, _handler_name, payload in routes:
            response = client.post(path, json=payload, headers=_OPERATOR_HEADERS)
            assert response.status_code == http_status
            assert response.json() == expected
            assert response.content == pm.d33_canonical_bytes(expected)
        assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
        assert _all_storage_files(b1b_step3_runtime) == files_before
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_05_unmapped_route_faults_remain_generic_and_zero_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _committed_b1b05_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-05-unmapped-errors",
    )
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    routes = (
        (_RESULT_REVIEW_PATH, "execution_result_review", subject["review_payload"]),
        (_PACKAGE_PREVIEW_PATH, "package_review_preview", subject["preview_payload"]),
        (_PACKAGE_COMMIT_PATH, "package_construction_commit", subject["commit_payload"]),
        (_PACKAGE_SUBMIT_PATH, "package_review_submit", subject["submit_payload"]),
    )
    rows_before = _b1b_03_row_projection(b1b_step3_runtime)
    files_before = _all_storage_files(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        for path, handler_name, payload in routes:
            def fail_unmapped(*_args, **_kwargs):
                raise RuntimeError("unmapped-b1b-sentinel")

            with monkeypatch.context() as route_patch:
                route_patch.setattr(layer3_workbench, handler_name, fail_unmapped)
                response = client.post(path, json=payload, headers=_OPERATOR_HEADERS)
            assert response.status_code == 500
            assert "unmapped-b1b-sentinel" not in response.text
            assert "layer3.b1b_error.v1" not in response.text
        assert _b1b_03_row_projection(b1b_step3_runtime) == rows_before
        assert _all_storage_files(b1b_step3_runtime) == files_before
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_05_golden_vector_extraction_does_not_require_git_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(*_args, **_kwargs):
        raise subprocess.CalledProcessError(128, ["git", "show"])

    monkeypatch.setattr(subprocess, "check_output", unavailable)

    frozen_bytes = _extract_frozen_b1b05_construction_vector()
    assert len(frozen_bytes) == 1447
    assert hashlib.sha256(frozen_bytes).hexdigest() == (
        "2c3bca8c8b3e40b625c8a70878e57a37e4e97a5d3a7c6ab28f07c921bfbf7aa9"
    )


def test_b1b_05_construction_basis_matches_mechanically_extracted_golden_vector() -> None:
    frozen_bytes = _extract_frozen_b1b05_construction_vector()
    frozen = json.loads(frozen_bytes)
    built = pm.build_b1b_package_construction_basis(
        authority=frozen["authority"],
        bundle=frozen["bundle"],
        packages=frozen["packages"],
    )
    assert pm.d33_canonical_bytes(built) == frozen_bytes
    assert len(frozen_bytes) == 1447
    assert hashlib.sha256(frozen_bytes).hexdigest() == (
        "2c3bca8c8b3e40b625c8a70878e57a37e4e97a5d3a7c6ab28f07c921bfbf7aa9"
    )
    assert pm.d33_sha256(pm._b1b_battery_expected_census("sqlite_authorized")) == (
        "0ecc091a19ee41b4a704a36b4fea9ee32b3bacac2aa342a175fc0addae0eb6ea"
    )
    assert pm.d33_sha256(pm._b1b_battery_expected_census("postgresql_authorized")) == (
        "87b5c9dd9d3c436a106aa86604462794461f0cd9b0b0e22181f49a482da76454"
    )
    assert pm.d33_sha256(pm._b1b_replay_contract()) == (
        "f2005da248be2c49c41c0b55d5b84afb3e27593c4c30dc495f9214def3769568"
    )
    assert pm._b1b_fixture_disclosure() == {
        "source_fixture_id": "F07",
        "proof_cell_id": "C01",
        "synthetic": True,
        "byte_length": 34,
        "content_sha256": pm.F07_CONTENT_SHA256,
        "official_public_read_evidence": False,
        "f20_status": "NOT-ESTABLISHED",
    }
    assert pm._b1b_lineage_fixture() == {
        **pm._b1b_fixture_disclosure(),
        "media_type": "text/csv",
    }


def test_b1b_05_package_leak_registry_is_reference_scoped_and_encoding_complete() -> None:
    def fullwidth(value: str) -> str:
        return "".join(
            chr(ord(character) + 0xFEE0) if "!" <= character <= "~" else character
            for character in value
        )

    for forbidden_key in pm._b1b04_forbidden_normalized_keys():
        evasions = {
            forbidden_key,
            forbidden_key.upper(),
            forbidden_key.replace("_", "-"),
            forbidden_key.replace("_", " "),
            fullwidth(forbidden_key),
        }
        for evasion in evasions:
            with pytest.raises(pm.PromotionIdentityError):
                pm._assert_b1b_package_no_leak({evasion: "sentinel"}, set())
    pm._assert_b1b_package_no_leak(
        {
            "storage_ref_hash": "a" * 64,
            "status": "tokenized benign nonclaim",
            "value": [*pm._B1B_MEMBER_PATHS, "application/json"],
        },
        set(),
    )

    registry: set[str] = set()
    pm._add_b1b_nested_reference_strings(
        registry,
        {
            "dataset_version_id": "public-version-id",
            "source_artifact_key": "bounded-logical-key",
            "nested": {"storage_ref": "datasets/private/payload.parquet"},
        },
    )
    assert registry == {"datasets/private/payload.parquet"}
    for leaking_value in pm._b1b_sensitive_encodings("datasets/private/payload.parquet"):
        with pytest.raises(pm.PromotionIdentityError):
            pm._assert_b1b_package_no_leak({"note": leaking_value}, registry)

    encoded_sources = {
        "credential": "credential-\u00ff\u00ff\u00ff",
        "cookie": "cookie-\u00ff\u00ff\u00ff",
        "identity": "identity-\u00ff\u00ff\u00ff",
        "storage_ref": "connectors/raw/private-\u00ff\u00ff\u00ff.csv",
    }
    encoded_registry = set(encoded_sources.values())
    for source in encoded_sources.values():
        raw = source.encode("utf-8")
        standard = base64.b64encode(raw).decode("ascii")
        urlsafe = base64.urlsafe_b64encode(raw).decode("ascii")
        assert standard != urlsafe
        evasions = {
            standard,
            standard.rstrip("="),
            urlsafe,
            urlsafe.rstrip("="),
            quote(source, safe=""),
            quote(quote(source, safe=""), safe=""),
        }
        for evasion in evasions:
            with pytest.raises(pm.PromotionIdentityError):
                pm._assert_b1b_package_no_leak({"value": evasion}, encoded_registry)

    fixture_lf = b"site_id,value\nSB-001,42\nSB-002,43\n"
    fixture_variants = (
        fixture_lf.decode("utf-8").rstrip("\n"),
        fixture_lf.decode("utf-8"),
        fixture_lf.decode("utf-8").replace("\n", "\r\n"),
        base64.b64encode(fixture_lf.rstrip(b"\n")).decode("ascii"),
        base64.b64encode(fixture_lf).decode("ascii"),
    )
    for leaking_value in fixture_variants:
        with pytest.raises(pm.PromotionIdentityError):
            pm._assert_b1b_package_no_leak({"note": leaking_value}, set())

    request_sentinels = {
        "authorization": "request-authorization-sentinel",
        "cookie": "request-cookie-sentinel",
        settings.proxy_identity_header: "request-identity-sentinel",
        settings.proxy_email_header: "request-email-sentinel",
        settings.proxy_groups_header: "request-workspace-sentinel",
    }
    request_headers = {
        **request_sentinels,
        settings.proxy_roles_header: "owner",
    }
    with pm.b1b_request_sensitive_scope(request_headers):
        registered = pm._b1b_runtime_sensitive_values()
        assert set(request_sentinels.values()) <= registered
        assert "owner" not in registered
        for sentinel in request_sentinels.values():
            for encoding in pm._b1b_sensitive_encodings(sentinel):
                with pytest.raises(pm.PromotionIdentityError):
                    pm._assert_b1b_package_no_leak({"note": encoding}, registered)
        pm._assert_b1b_package_no_leak(
            {
                "owner_bound_main_sha": "6" * 40,
                "approved_by_operator": True,
                "note": "owner requested changes from the operator",
            },
            registered,
        )
    assert not set(request_sentinels.values()) & pm._b1b_runtime_sensitive_values()


def test_b1b_05_package_commit_rejects_artifact_drift_after_locked_review_revalidation(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-05-artifact-race",
    )
    monkeypatch.setattr(pm, "_read_b1b_package_authority", lambda: dict(_B1B05_AUTHORITY))
    review_payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with b1b_step3_runtime["factory"]() as db:
        review = json.loads(pm.record_b1b_result_review(db, review_payload).body_bytes)
    preview_payload = _b1b05_preview_payload(
        resolved,
        preview,
        approval,
        start,
        review,
    )
    with b1b_step3_runtime["factory"]() as db:
        package_preview = json.loads(pm.preview_b1b_package_review(db, preview_payload).body_bytes)
        artifact = db.query(AnalysisArtifact).filter_by(
            analysis_run_id=start["analysis_run_id"]
        ).one()
    artifact_path = (Path(settings.artifact_storage_dir) / Path(artifact.storage_ref).name).resolve()
    actual_file_facts = pm._file_facts

    def drifted_file_facts(path: Path) -> tuple[int, str]:
        facts = actual_file_facts(path)
        return (facts[0], "0" * 64) if Path(path).resolve() == artifact_path else facts

    monkeypatch.setattr(pm, "_file_facts", drifted_file_facts)
    before_rows = _b1b_03_row_projection(b1b_step3_runtime)
    before_files = _all_storage_files(b1b_step3_runtime)
    with b1b_step3_runtime["factory"]() as db:
        with pytest.raises(pm.ConnectorPromotionError) as caught:
            pm.commit_b1b_packages(
                db,
                _b1b05_commit_payload(preview_payload, package_preview),
            )
    assert (caught.value.code, caught.value.http_status) == (
        "connector_package_basis_conflict",
        409,
    )
    assert _b1b_03_row_projection(b1b_step3_runtime) == before_rows
    assert _all_storage_files(b1b_step3_runtime) == before_files


@pytest.mark.parametrize("commit_mode", ("fail_before_commit", "commit_then_raise"))
def test_b1b_05_commit_exception_is_classified_from_fresh_locked_exact_state(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    commit_mode: str,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        f"b1b-05-{commit_mode}",
    )
    monkeypatch.setattr(pm, "_read_b1b_package_authority", lambda: dict(_B1B05_AUTHORITY))
    review_payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with b1b_step3_runtime["factory"]() as db:
        review = json.loads(pm.record_b1b_result_review(db, review_payload).body_bytes)
    preview_payload = _b1b05_preview_payload(
        resolved,
        preview,
        approval,
        start,
        review,
    )
    with b1b_step3_runtime["factory"]() as db:
        package_preview = json.loads(pm.preview_b1b_package_review(db, preview_payload).body_bytes)
    commit_payload = _b1b05_commit_payload(preview_payload, package_preview)
    actual_commit = pm._commit_b1b_packages

    def failed_commit(db) -> None:
        if commit_mode == "commit_then_raise":
            db.commit()
        raise OSError(f"simulated {commit_mode}")

    monkeypatch.setattr(pm, "_commit_b1b_packages", failed_commit)
    committed_response: bytes | None = None
    with b1b_step3_runtime["factory"]() as db:
        if commit_mode == "fail_before_commit":
            with pytest.raises(pm.ConnectorPromotionError) as caught:
                pm.commit_b1b_packages(db, commit_payload)
            assert (caught.value.code, caught.value.http_status) == (
                "connector_promotion_bridge_unavailable",
                503,
            )
        else:
            committed_response = pm.commit_b1b_packages(db, commit_payload).body_bytes

    monkeypatch.setattr(pm, "_commit_b1b_packages", actual_commit)
    with b1b_step3_runtime["factory"]() as db:
        replay = pm.commit_b1b_packages(db, commit_payload).body_bytes
        assert db.query(L3ReconciliationRecord).filter_by(
            session_id=resolved["promoted_session_id"]
        ).count() == 1
        assert db.query(L3OutputPackage).filter_by(
            session_id=resolved["promoted_session_id"]
        ).count() == 3
    if committed_response is not None:
        assert replay == committed_response
    files = _all_storage_files(b1b_step3_runtime)
    assert not any("b1b-packages-staging" in path for path in files)
    assert len(
        [path for path in files if "/b1b-packages/" in path and path.endswith(".json")]
    ) == 3


@pytest.mark.parametrize(
    ("decision", "notes", "state", "eligible"),
    [
        ("approved", "", "package_review_approved", True),
        (
            "changes_requested",
            "  owner requested bounded change  ",
            "package_review_changes_requested",
            False,
        ),
        ("rejected", " bounded operator rejection ", "package_review_rejected", False),
        ("blocked", " bounded block ", "package_review_blocked", False),
    ],
)
def test_b1b_05_routes_commit_closed_immutable_packages_and_exact_review(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    notes: str,
    state: str,
    eligible: bool,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        f"b1b-05-{decision}",
    )
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    monkeypatch.setattr(pm, "_read_b1b_package_authority", lambda: dict(_B1B05_AUTHORITY))
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        review_payload = _b1b_04_review_payload(resolved, preview, approval, start)
        review = client.post(_RESULT_REVIEW_PATH, json=review_payload, headers=_OPERATOR_HEADERS)
        assert review.status_code == 200, review.text

        preview_payload = _b1b05_preview_payload(
            resolved,
            preview,
            approval,
            start,
            review.json(),
        )
        package_preview = client.post(
            _PACKAGE_PREVIEW_PATH,
            json=preview_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert package_preview.status_code == 200, package_preview.text
        assert set(package_preview.json()) == pm._B1B_PACKAGE_PREVIEW_RESPONSE_KEYS
        assert package_preview.content == pm.d33_canonical_bytes(package_preview.json())
        assert package_preview.json()["candidate_package_kinds"] == list(_PACKAGE_ORDER)
        assert package_preview.json()["member_count"] == 9
        assert client.post(
            _PACKAGE_PREVIEW_PATH,
            json=preview_payload,
            headers=_OPERATOR_HEADERS,
        ).content == package_preview.content

        commit_payload = _b1b05_commit_payload(preview_payload, package_preview.json())
        package_commit = client.post(
            _PACKAGE_COMMIT_PATH,
            json=commit_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert package_commit.status_code == 200, package_commit.text
        assert set(package_commit.json()) == pm._B1B_PACKAGE_COMMIT_RESPONSE_KEYS
        assert package_commit.content == pm.d33_canonical_bytes(package_commit.json())
        assert [item["package_kind"] for item in package_commit.json()["packages"]] == list(_PACKAGE_ORDER)
        assert package_commit.json()["package_count"] == 3
        assert package_commit.json()["member_count"] == 9
        assert package_commit.json()["persistence_status"] == "committed"

        frozen_rows = _b1b_03_row_projection(b1b_step3_runtime)
        frozen_files = _all_storage_files(b1b_step3_runtime)
        commit_replay = client.post(
            _PACKAGE_COMMIT_PATH,
            json=commit_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert commit_replay.content == package_commit.content
        assert _b1b_03_row_projection(b1b_step3_runtime) == frozen_rows
        assert _all_storage_files(b1b_step3_runtime) == frozen_files

        with b1b_step3_runtime["factory"]() as db:
            rows = {
                row.package_kind: row
                for row in db.query(L3OutputPackage).filter_by(
                    session_id=resolved["promoted_session_id"]
                )
            }
            assert list(sorted(rows)) == sorted(_PACKAGE_ORDER)
            outer = {
                kind: json.loads(Path(rows[kind].payload_ref).read_bytes())
                for kind in _PACKAGE_ORDER
            }
            assert set(outer["canonical_internal"]) == {
                "package_header",
                "b1_evidence_bundle",
                "b1_evidence_bundle_index",
            }
            assert set(outer["review_facing"]) == {
                "package_header",
                "b1_evidence_bundle",
                "b1_evidence_bundle_index",
                "canonical_package_binding",
            }
            assert set(outer["user_facing"]) == {
                "package_header",
                "b1_public_disclosure",
                "b1_evidence_bundle_index",
                "canonical_package_binding",
            }
            assert outer["canonical_internal"]["b1_evidence_bundle"] == outer["review_facing"][
                "b1_evidence_bundle"
            ]
            assert [
                item["logical_path"]
                for item in outer["canonical_internal"]["b1_evidence_bundle"]["members"]
            ] == list(pm._B1B_MEMBER_PATHS)
            members_by_path = {
                item["logical_path"]: item["content"]
                for item in outer["canonical_internal"]["b1_evidence_bundle"]["members"]
            }
            assert members_by_path["dataset-lineage.json"]["fixture"] == (
                pm._b1b_lineage_fixture()
            )
            assert members_by_path["result-review.json"]["connector_b1_evidence"][
                "fixture_disclosure_sha256"
            ] == pm.d33_sha256(pm._b1b_fixture_disclosure())
            assert len(outer["canonical_internal"]["b1_evidence_bundle_index"]["members"]) == 9
            assert outer["user_facing"]["b1_public_disclosure"]["fixture_disclosure"] == (
                pm._b1b_fixture_disclosure()
            )

            index = outer["canonical_internal"]["b1_evidence_bundle_index"]
            index_by_path = {item["logical_path"]: item for item in index["members"]}
            aliases = {
                "bundle_index_order_hash": index["package_order_hash"],
                "package_manifest_sha256": index_by_path["package-manifest.json"]["sha256"],
                "package_rehash_sha256": index_by_path["package-rehash.json"]["sha256"],
            }
            stored_packages = [
                {
                    "package_kind": item["package_kind"],
                    "output_package_id": item["output_package_id"],
                    "payload_bytes": item["byte_length"],
                    "payload_sha256": item["payload_sha256"],
                }
                for item in package_commit.json()["packages"]
            ]
            reconciliation = db.query(L3ReconciliationRecord).filter_by(
                session_id=resolved["promoted_session_id"]
            ).one()
            assert reconciliation.summary_json == {
                "schema_id": "layer3.b1b_reconciliation_summary.v1",
                "profile": "receipt_bound_b1b",
                "source_gate": "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE",
                "promotion_receipt_id": package_commit.json()["promotion_receipt_id"],
                "promoted_session_id": resolved["promoted_session_id"],
                "result_review_hash": review.json()["result_review_hash"],
                "package_review_preview_hash": package_preview.json()[
                    "package_review_preview_hash"
                ],
                "package_set": {
                    "construction_basis_hash": package_commit.json()["construction_basis_hash"],
                    "member_count": 9,
                    **aliases,
                    "packages": stored_packages,
                },
                "package_review_submit": None,
                "package_review_hash": None,
                "connector_dataset_handoff_basis": None,
                "connector_dataset_handoff_basis_hash": None,
            }
            for index_number, kind in enumerate(_PACKAGE_ORDER):
                assert rows[kind].output_package_id == stored_packages[index_number][
                    "output_package_id"
                ]
                assert rows[kind].status == "package_complete"
                assert rows[kind].payload_hash == stored_packages[index_number]["payload_sha256"]
                assert rows[kind].summary_json == {
                    "schema_id": "layer3.b1b_output_package_summary.v1",
                    "profile": "receipt_bound_b1b",
                    "package_kind": kind,
                    "member_count": 0 if kind == "user_facing" else 9,
                    **aliases,
                    "canonical_binding_present": kind != "canonical_internal",
                }
            package_rows_before_submit = _project_query_rows(
                db.query(L3OutputPackage).filter_by(session_id=resolved["promoted_session_id"]),
                L3OutputPackage,
            )
            package_bytes_before_submit = {
                kind: Path(rows[kind].payload_ref).read_bytes() for kind in _PACKAGE_ORDER
            }

        submit_payload = _b1b05_submit_payload(
            preview_payload,
            package_preview.json(),
            package_commit.json(),
            decision=decision,
            notes=notes,
        )
        submitted = client.post(_PACKAGE_SUBMIT_PATH, json=submit_payload, headers=_OPERATOR_HEADERS)
        assert submitted.status_code == 200, submitted.text
        assert set(submitted.json()) == (
            pm._B1B_PACKAGE_SUBMIT_APPROVED_RESPONSE_KEYS
            if eligible
            else pm._B1B_PACKAGE_SUBMIT_RESPONSE_KEYS
        )
        assert submitted.content == pm.d33_canonical_bytes(submitted.json())
        assert submitted.json()["package_review_state"] == state
        assert submitted.json()["handoff_eligibility_status"] == (
            "eligible" if eligible else "ineligible"
        )
        assert submitted.json()["decision_notes_present"] is (not eligible)
        assert ("connector_dataset_handoff_basis_hash" in submitted.json()) is eligible
        assert client.post(
            _PACKAGE_SUBMIT_PATH,
            json=submit_payload,
            headers=_OPERATOR_HEADERS,
        ).content == submitted.content
        assert _all_storage_files(b1b_step3_runtime) == frozen_files
        with b1b_step3_runtime["factory"]() as db:
            rows_after_submit = {
                row.package_kind: row
                for row in db.query(L3OutputPackage).filter_by(
                    session_id=resolved["promoted_session_id"]
                )
            }
            assert _project_query_rows(
                db.query(L3OutputPackage).filter_by(session_id=resolved["promoted_session_id"]),
                L3OutputPackage,
            ) == package_rows_before_submit
            assert {
                kind: Path(rows_after_submit[kind].payload_ref).read_bytes()
                for kind in _PACKAGE_ORDER
            } == package_bytes_before_submit
            assert _replay_summary_contract_valid(db, resolved["promoted_session_id"])
    finally:
        main.app.dependency_overrides.pop(get_db, None)


def test_b1b_05_package_basis_and_second_decision_conflicts_are_distinct_and_zero_delta(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        "b1b-05-conflicts",
    )
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    monkeypatch.setattr(pm, "_read_b1b_package_authority", lambda: dict(_B1B05_AUTHORITY))
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        def assert_closed_validation(response, sentinel: str) -> None:
            assert response.status_code == 422
            assert response.json() == pm.b1b_error_body("b1b_request_validation_failed")
            assert response.content == pm.d33_canonical_bytes(response.json())
            assert sentinel not in response.text

        review = client.post(
            _RESULT_REVIEW_PATH,
            json=_b1b_04_review_payload(resolved, preview, approval, start),
            headers=_OPERATOR_HEADERS,
        )
        assert review.status_code == 200, review.text
        preview_payload = _b1b05_preview_payload(
            resolved,
            preview,
            approval,
            start,
            review.json(),
        )
        initial_rows = _b1b_03_row_projection(b1b_step3_runtime)
        initial_files = _all_storage_files(b1b_step3_runtime)
        preview_sentinel = "preview-rejected-sentinel"
        malformed_preview = client.post(
            _PACKAGE_PREVIEW_PATH,
            json={**preview_payload, "unexpected": preview_sentinel},
            headers=_OPERATOR_HEADERS,
        )
        assert_closed_validation(malformed_preview, preview_sentinel)
        assert _b1b_03_row_projection(b1b_step3_runtime) == initial_rows
        assert _all_storage_files(b1b_step3_runtime) == initial_files
        package_preview = client.post(
            _PACKAGE_PREVIEW_PATH,
            json=preview_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert package_preview.status_code == 200, package_preview.text

        before_rows = _b1b_03_row_projection(b1b_step3_runtime)
        before_files = _all_storage_files(b1b_step3_runtime)
        commit_sentinel = "commit-rejected-sentinel"
        malformed_commit = client.post(
            _PACKAGE_COMMIT_PATH,
            json={
                **_b1b05_commit_payload(preview_payload, package_preview.json()),
                "unexpected": commit_sentinel,
            },
            headers=_OPERATOR_HEADERS,
        )
        assert_closed_validation(malformed_commit, commit_sentinel)
        assert _b1b_03_row_projection(b1b_step3_runtime) == before_rows
        assert _all_storage_files(b1b_step3_runtime) == before_files
        changed_preview = _b1b05_commit_payload(preview_payload, package_preview.json())
        changed_preview["package_review_preview_hash"] = "0" * 64
        changed_preview["client_request_id"] = f"b1b-package-construction-{'0' * 64}"
        commit_conflict = client.post(
            _PACKAGE_COMMIT_PATH,
            json=changed_preview,
            headers=_OPERATOR_HEADERS,
        )
        assert commit_conflict.status_code == 409
        assert commit_conflict.json() == pm.b1b_error_body("connector_package_basis_conflict")
        assert _b1b_03_row_projection(b1b_step3_runtime) == before_rows
        assert _all_storage_files(b1b_step3_runtime) == before_files

        commit_payload = _b1b05_commit_payload(preview_payload, package_preview.json())
        package_commit = client.post(
            _PACKAGE_COMMIT_PATH,
            json=commit_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert package_commit.status_code == 200, package_commit.text
        submit_payload = _b1b05_submit_payload(
            preview_payload,
            package_preview.json(),
            package_commit.json(),
            decision="approved",
            notes="",
        )
        committed_rows = _b1b_03_row_projection(b1b_step3_runtime)
        committed_files = _all_storage_files(b1b_step3_runtime)
        with b1b_step3_runtime["factory"]() as db:
            package_ref = db.query(L3OutputPackage).filter_by(
                session_id=resolved["promoted_session_id"]
            ).first().payload_ref
        request_secret = "submit-request-secret-sentinel"
        encoded_package_ref = base64.urlsafe_b64encode(package_ref.encode("utf-8")).decode(
            "ascii"
        ).rstrip("=")
        for leaking_note, headers in (
            (request_secret, {**_OPERATOR_HEADERS, "authorization": request_secret}),
            (encoded_package_ref, _OPERATOR_HEADERS),
        ):
            leaking_submit = _b1b05_submit_payload(
                preview_payload,
                package_preview.json(),
                package_commit.json(),
                decision="rejected",
                notes=leaking_note,
            )
            rejected_leak = client.post(
                _PACKAGE_SUBMIT_PATH,
                json=leaking_submit,
                headers=headers,
            )
            assert rejected_leak.status_code == 422
            assert rejected_leak.json() == pm.b1b_error_body("b1b_request_validation_failed")
            assert rejected_leak.content == pm.d33_canonical_bytes(rejected_leak.json())
            assert _b1b_03_row_projection(b1b_step3_runtime) == committed_rows
            assert _all_storage_files(b1b_step3_runtime) == committed_files

        authority_reader = pm._read_b1b_package_authority

        def unavailable_authority() -> dict[str, str]:
            raise OSError("simulated attestation reopen failure")

        monkeypatch.setattr(pm, "_read_b1b_package_authority", unavailable_authority)
        unavailable_submit = client.post(
            _PACKAGE_SUBMIT_PATH,
            json=submit_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert unavailable_submit.status_code == 503
        assert unavailable_submit.json() == pm.b1b_error_body(
            "connector_promotion_bridge_unavailable"
        )
        assert unavailable_submit.content == pm.d33_canonical_bytes(unavailable_submit.json())
        assert _b1b_03_row_projection(b1b_step3_runtime) == committed_rows
        assert _all_storage_files(b1b_step3_runtime) == committed_files
        monkeypatch.setattr(pm, "_read_b1b_package_authority", authority_reader)

        submit_sentinel = "submit-payload-ref-sentinel"
        malformed_submit = client.post(
            _PACKAGE_SUBMIT_PATH,
            json={**submit_payload, "payload_refs": [submit_sentinel]},
            headers=_OPERATOR_HEADERS,
        )
        assert_closed_validation(malformed_submit, submit_sentinel)
        assert _b1b_03_row_projection(b1b_step3_runtime) == committed_rows
        assert _all_storage_files(b1b_step3_runtime) == committed_files
        unequal_bases = (
            {**submit_payload, "construction_basis_hash": "0" * 64},
            {**submit_payload, "reconciliation_record_id": str(uuid.uuid4())},
            {
                **submit_payload,
                "output_package_ids": [
                    str(uuid.uuid4()),
                    *submit_payload["output_package_ids"][1:],
                ],
            },
            {
                **submit_payload,
                "payload_hashes": ["0" * 64, *submit_payload["payload_hashes"][1:]],
            },
        )
        for unequal_basis in unequal_bases:
            conflict = client.post(
                _PACKAGE_SUBMIT_PATH,
                json=_with_b1b05_submit_identity(unequal_basis),
                headers=_OPERATOR_HEADERS,
            )
            assert conflict.status_code == 409
            assert conflict.json() == pm.b1b_error_body("connector_package_basis_conflict")
            assert conflict.content == pm.d33_canonical_bytes(conflict.json())
            assert _b1b_03_row_projection(b1b_step3_runtime) == committed_rows
            assert _all_storage_files(b1b_step3_runtime) == committed_files

        submitted = client.post(
            _PACKAGE_SUBMIT_PATH,
            json=submit_payload,
            headers=_OPERATOR_HEADERS,
        )
        assert submitted.status_code == 200, submitted.text
        reviewed_rows = _b1b_03_row_projection(b1b_step3_runtime)
        reviewed_files = _all_storage_files(b1b_step3_runtime)
        second_decision = _with_b1b05_submit_identity(
            {
                **submit_payload,
                "operator_decision": "rejected",
                "decision_notes": "bounded rejection",
            }
        )
        decision_conflict = client.post(
            _PACKAGE_SUBMIT_PATH,
            json=second_decision,
            headers=_OPERATOR_HEADERS,
        )
        assert decision_conflict.status_code == 409
        assert decision_conflict.json() == pm.b1b_error_body(
            "connector_package_review_decision_conflict"
        )
        assert decision_conflict.content == pm.d33_canonical_bytes(decision_conflict.json())
        assert _b1b_03_row_projection(b1b_step3_runtime) == reviewed_rows
        assert _all_storage_files(b1b_step3_runtime) == reviewed_files
    finally:
        main.app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    "path",
    (_PACKAGE_PREVIEW_PATH, _PACKAGE_COMMIT_PATH, _PACKAGE_SUBMIT_PATH),
)
def test_b1b_05_shared_package_routes_preserve_flag_false_and_nonreceipt_validation_bytes(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    _configure_step5_proxy(monkeypatch)
    _install_step5_db_override(b1b_step3_runtime)
    monkeypatch.setattr(main, "engine", b1b_step3_runtime["engine"])
    payload = {"session_id": str(uuid.uuid4()), "unexpected": "ordinary-sentinel"}
    before_rows = _b1b_03_row_projection(b1b_step3_runtime)
    before_files = _all_storage_files(b1b_step3_runtime)
    client = TestClient(main.app, raise_server_exceptions=False)
    try:
        monkeypatch.setattr(settings, "layer3_connector_promotion_bridge_enabled", False)
        flag_false = client.post(path, json=payload, headers=_OPERATOR_HEADERS)
        assert flag_false.status_code == 422
        assert flag_false.json() != pm.b1b_error_body("b1b_request_validation_failed")

        _enable_step5(monkeypatch)
        nonreceipt = client.post(path, json=payload, headers=_OPERATOR_HEADERS)
        assert nonreceipt.status_code == flag_false.status_code
        assert nonreceipt.content == flag_false.content
        assert nonreceipt.headers["content-type"] == flag_false.headers["content-type"]
        assert _b1b_03_row_projection(b1b_step3_runtime) == before_rows
        assert _all_storage_files(b1b_step3_runtime) == before_files
    finally:
        main.app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize("publish_ordinal", [1, 2, 3])
def test_b1b_05_kill_after_each_publish_contains_all_orphans_then_retries(
    b1b_step3_runtime: dict,
    monkeypatch: pytest.MonkeyPatch,
    publish_ordinal: int,
) -> None:
    resolved, preview, approval, start = _prepare_result_review_subject(
        b1b_step3_runtime,
        monkeypatch,
        f"b1b-05-kill-{publish_ordinal}",
    )
    monkeypatch.setattr(pm, "_read_b1b_package_authority", lambda: dict(_B1B05_AUTHORITY))
    review_payload = _b1b_04_review_payload(resolved, preview, approval, start)
    with b1b_step3_runtime["factory"]() as db:
        review_body = json.loads(pm.record_b1b_result_review(db, review_payload).body_bytes)
    preview_payload = _b1b05_preview_payload(
        resolved,
        preview,
        approval,
        start,
        review_body,
    )
    with b1b_step3_runtime["factory"]() as db:
        package_preview = json.loads(pm.preview_b1b_package_review(db, preview_payload).body_bytes)
    commit_payload = _b1b05_commit_payload(preview_payload, package_preview)
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
            "settings.layer3_connector_promotion_bridge_enabled = True",
            "pm.attestation_precondition_available = lambda _candidate=None: True",
            f"pm._read_b1b_package_authority = lambda: {_B1B05_AUTHORITY!r}",
            f"pm._after_b1b_package_publish = lambda ordinal: os._exit({80 + publish_ordinal}) if ordinal == {publish_ordinal} else None",
            "with factory() as db:",
            f"    pm.commit_b1b_packages(db, {commit_payload!r})",
        ]
    )
    child = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=BACKEND.parent,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert child.returncode == 80 + publish_ordinal, (child.stdout, child.stderr)
    with b1b_step3_runtime["factory"]() as db:
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    orphans = {
        path: facts
        for path, facts in _all_storage_files(b1b_step3_runtime).items()
        if "b1b-packages-staging" in path or "/b1b-packages/" in path
    }
    assert len(orphans) == 3

    retry_code = "\n".join(
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
            "settings.layer3_connector_promotion_bridge_enabled = True",
            "pm.attestation_precondition_available = lambda _candidate=None: True",
            f"pm._read_b1b_package_authority = lambda: {_B1B05_AUTHORITY!r}",
            "with factory() as db:",
            f"    response = pm.commit_b1b_packages(db, {commit_payload!r})",
            "    print('B1B_RETRY:' + response.body_bytes.decode('utf-8'))",
        ]
    )
    retry_child = subprocess.run(
        [sys.executable, "-c", retry_code],
        cwd=BACKEND.parent,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert retry_child.returncode == 0, (retry_child.stdout, retry_child.stderr)
    retry_line = next(
        line for line in retry_child.stdout.splitlines() if line.startswith("B1B_RETRY:")
    )
    retry = json.loads(retry_line.removeprefix("B1B_RETRY:"))
    assert retry["package_count"] == 3
    with b1b_step3_runtime["factory"]() as db:
        assert db.query(L3ReconciliationRecord).count() == 1
        assert db.query(L3OutputPackage).count() == 3
    files = _all_storage_files(b1b_step3_runtime)
    assert not any("b1b-packages-staging" in path for path in files)
    authoritative = {
        path: facts
        for path, facts in files.items()
        if "/b1b-packages/" in path and path.endswith(".json")
    }
    contained = {
        path: facts
        for path, facts in files.items()
        if "b1b-packages-containment" in path
        and path.endswith(".json")
        and not path.endswith(".containment.json")
    }
    ledgers = {
        path for path in files if path.endswith(".containment.json")
    }
    assert len(authoritative) == 3
    assert len(contained) == 3
    assert len(ledgers) == 3
    assert sorted(contained.values()) == sorted(orphans.values())
