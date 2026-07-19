"""B1b connector promotion bridge — B1b-01 schema-foundation tests.

Covers the owner-bound Option II receipt DDL and the bridge feature flag:
- LAYER3_CONNECTOR_PROMOTION_BRIDGE_ENABLED defaults to False
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

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.exc import IntegrityError

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from alembic.config import Config  # noqa: E402
from alembic import command  # noqa: E402

ALEMBIC_INI = BACKEND / "alembic.ini"

TABLE = "l3_connector_promotion_receipt"
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


def _run_upgrade(url: str) -> None:
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
        command.upgrade(cfg, "head")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev
        for name, lg in manager.loggerDict.items():
            if isinstance(lg, logging.Logger):
                lg.disabled = disabled_before.get(name, False)


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


# ---------------------------------------------------------------------------
# Migrated DDL shape
# ---------------------------------------------------------------------------


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
