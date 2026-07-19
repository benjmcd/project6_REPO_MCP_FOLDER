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

import hashlib
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from alembic.config import Config  # noqa: E402
from alembic import command  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.models import (  # noqa: E402
    ConnectorRun,
    ConnectorRunTarget,
    L3ConnectorSourceIntakeRecord,
)
from app.services.layer3_connector_source_intake import (  # noqa: E402
    record_connector_produced_source_intake,
)

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
        dataframe_io_git_blob="1" * 40,
        implementation_commit="2" * 40,
        ingest_git_blob="3" * 40,
        promotion_git_blob="4" * 40,
        input_storage_ref_hash="5" * 64,
        connector_run_id="run-1",
        connector_run_target_id="target-1",
        connector_source_intake_record_id="intake-1",
        gate_b_material_snapshot_id="snap-1",
        gate_b_selection_manifest_id="manifest-1",
        gate_b_session_id="session-1",
        canonical_identity_key_hash=pm.F07_CANONICAL_IDENTITY_KEY_HASH,
        connector_promotion_receipt_id="receipt-1",
        promotion_basis_hash="6" * 64,
    )
    bh = pm.materialization_basis_hash(basis)
    assert len(bh) == 64
    # Embedded fixed sections are exact.
    assert basis["code"]["metadata_contract_sha256"] == pm.METADATA_CONTRACT_SHA256
    assert basis["transformation"]["contract_sha256"] == pm.TRANSFORM_CONTRACT_SHA256
    assert basis["input"]["bytes"] == 34

    record = pm.build_materialization_record(
        basis_hash=bh,
        dataset_file_bytes=1234,
        dataset_file_sha256="7" * 64,
        dataset_id="ds-1",
        dataset_source_provenance_id="prov-1",
        dataset_storage_ref_hash="8" * 64,
        dataset_version_content_sha256=pm.F07_CONTENT_SHA256,
        dataset_version_id="dsv-1",
        promoted_session_id="promoted-1",
        source_connector_id="conn-1",
    )
    wrapper = pm.build_materialization_wrapper(record)
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
