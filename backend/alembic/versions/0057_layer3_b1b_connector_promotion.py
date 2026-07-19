"""Add Layer 3 B1b intake identity pair and promotion receipt.

Revision ID: 0057_layer3_b1b_connector_promotion
Revises: 0056_layer3_connector_source_intake_record
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0057_layer3_b1b_connector_promotion"
down_revision = "0056_layer3_connector_source_intake_record"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_connector_promotion_receipt"
INTAKE_TABLE_NAME = "l3_connector_source_intake_record"
INTAKE_IDENTITY_VERSION_COLUMN = "identity_metadata_hash_version"
INTAKE_IDENTITY_HASH_COLUMN = "identity_metadata_hash"
INTAKE_IDENTITY_CHECK = "ck_l3_connector_source_intake_identity_metadata_joint_null"
INTAKE_IDENTITY_INDEX = "ix_l3_connector_intake_material_identity"

INTAKE_IDENTITY_CHECK_SQL = (
    "(identity_metadata_hash_version IS NULL AND identity_metadata_hash IS NULL)"
    " OR (identity_metadata_hash_version IS NOT NULL AND identity_metadata_hash IS NOT NULL)"
)

RECEIPT_INDEXES = (
    ("ix_l3_connector_promotion_intake", ["connector_source_intake_record_id"]),
    ("ix_l3_connector_promotion_gate_b_session", ["gate_b_session_id"]),
    ("ix_l3_connector_promotion_selection_manifest", ["gate_b_selection_manifest_id"]),
    ("ix_l3_connector_promotion_material_snapshot", ["gate_b_material_snapshot_id"]),
    ("ix_l3_connector_promotion_dataset", ["dataset_id"]),
    ("ix_l3_connector_promotion_dataset_version", ["dataset_version_id"]),
    ("ix_l3_connector_promotion_promoted_session", ["promoted_session_id"]),
)

JOINT_STATE_SQL = (
    "("
    "materialization_status IS NULL"
    " AND dataset_id IS NULL AND dataset_version_id IS NULL"
    " AND promoted_session_id IS NULL"
    " AND materialization_basis_hash IS NULL AND materialized_at IS NULL"
    ") OR ("
    "materialization_status IS NOT NULL AND materialization_status = 'materializing'"
    " AND materialization_basis_hash IS NOT NULL"
    " AND dataset_id IS NULL AND dataset_version_id IS NULL"
    " AND promoted_session_id IS NULL AND materialized_at IS NULL"
    ") OR ("
    "materialization_status IS NOT NULL AND materialization_status = 'materialized'"
    " AND materialization_basis_hash IS NOT NULL"
    " AND dataset_id IS NOT NULL AND dataset_version_id IS NOT NULL"
    " AND promoted_session_id IS NOT NULL AND materialized_at IS NOT NULL"
    ")"
)


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _check_constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    try:
        constraints = inspector.get_check_constraints(table_name)
    except NotImplementedError:
        return False
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_once(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _add_intake_identity_schema() -> None:
    if not _table_exists(INTAKE_TABLE_NAME):
        return
    missing_columns = [
        column_name
        for column_name in (INTAKE_IDENTITY_VERSION_COLUMN, INTAKE_IDENTITY_HASH_COLUMN)
        if not _column_exists(INTAKE_TABLE_NAME, column_name)
    ]
    check_missing = not _check_constraint_exists(INTAKE_TABLE_NAME, INTAKE_IDENTITY_CHECK)
    if missing_columns or check_missing:
        with op.batch_alter_table(INTAKE_TABLE_NAME) as batch_op:
            for column_name in missing_columns:
                batch_op.add_column(sa.Column(column_name, sa.String(length=64), nullable=True))
            if check_missing:
                batch_op.create_check_constraint(INTAKE_IDENTITY_CHECK, INTAKE_IDENTITY_CHECK_SQL)
    _create_index_once(
        INTAKE_TABLE_NAME,
        INTAKE_IDENTITY_INDEX,
        [
            INTAKE_IDENTITY_VERSION_COLUMN,
            "source_family",
            "content_sha256",
            INTAKE_IDENTITY_HASH_COLUMN,
        ],
    )


def _lock_receipt_table_for_downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text(f"LOCK TABLE {TABLE_NAME} IN SHARE ROW EXCLUSIVE MODE"))  # noqa: S608
        return
    if bind.dialect.name == "sqlite":
        # SQLite has one writer. A zero-row write statement upgrades Alembic's
        # transaction before the emptiness check without rewriting any value.
        bind.execute(
            sa.text(
                f"UPDATE {TABLE_NAME} "  # noqa: S608
                "SET connector_promotion_receipt_id = connector_promotion_receipt_id WHERE 0"
            )
        )
        return
    raise RuntimeError(
        f"Cannot safely downgrade Layer 3 B1b connector promotion on unsupported dialect "
        f"{bind.dialect.name!r}."
    )


def _receipt_has_rows() -> bool:
    if not _table_exists(TABLE_NAME):
        return False
    _lock_receipt_table_for_downgrade()
    return (
        op.get_bind().execute(sa.text(f"SELECT 1 FROM {TABLE_NAME} LIMIT 1"))  # noqa: S608
        .first()
        is not None
    )


def _drop_receipt_table() -> None:
    if not _table_exists(TABLE_NAME):
        return
    for index_name, _ in reversed(RECEIPT_INDEXES):
        _drop_index_once(TABLE_NAME, index_name)

    # PostgreSQL supports dependency teardown directly. SQLite owns checks and
    # unnamed foreign keys inside the table definition, so DROP TABLE removes
    # those local constraints atomically after the explicit indexes are gone.
    if op.get_bind().dialect.name != "sqlite":
        inspector = sa.inspect(op.get_bind())
        checks = sorted(
            (constraint for constraint in inspector.get_check_constraints(TABLE_NAME) if constraint.get("name")),
            key=lambda constraint: str(constraint["name"]),
        )
        for constraint in checks:
            op.drop_constraint(str(constraint["name"]), TABLE_NAME, type_="check")
        foreign_keys = sorted(
            (foreign_key for foreign_key in inspector.get_foreign_keys(TABLE_NAME) if foreign_key.get("name")),
            key=lambda foreign_key: str(foreign_key["name"]),
        )
        for foreign_key in foreign_keys:
            op.drop_constraint(str(foreign_key["name"]), TABLE_NAME, type_="foreignkey")
    op.drop_table(TABLE_NAME)


def _drop_intake_identity_schema() -> None:
    if not _table_exists(INTAKE_TABLE_NAME):
        return
    _drop_index_once(INTAKE_TABLE_NAME, INTAKE_IDENTITY_INDEX)
    check_exists = _check_constraint_exists(INTAKE_TABLE_NAME, INTAKE_IDENTITY_CHECK)
    present_columns = [
        column_name
        for column_name in (INTAKE_IDENTITY_VERSION_COLUMN, INTAKE_IDENTITY_HASH_COLUMN)
        if _column_exists(INTAKE_TABLE_NAME, column_name)
    ]
    if check_exists or present_columns:
        with op.batch_alter_table(INTAKE_TABLE_NAME) as batch_op:
            if check_exists:
                batch_op.drop_constraint(INTAKE_IDENTITY_CHECK, type_="check")
            for column_name in reversed(present_columns):
                batch_op.drop_column(column_name)


def upgrade() -> None:
    _add_intake_identity_schema()
    if not _table_exists(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("connector_promotion_receipt_id", sa.String(36), primary_key=True),
            sa.Column("receipt_schema_version", sa.String(64), nullable=False),
            sa.Column("identity_metadata_hash_version", sa.String(64), nullable=False),
            sa.Column("source_family", sa.String(64), nullable=False),
            sa.Column("content_sha256", sa.String(64), nullable=False),
            sa.Column("identity_metadata_hash", sa.String(64), nullable=False),
            sa.Column("canonical_identity_key_hash", sa.String(64), nullable=False),
            sa.Column(
                "connector_source_intake_record_id",
                sa.String(36),
                sa.ForeignKey(
                    "l3_connector_source_intake_record.connector_source_intake_record_id",
                    ondelete="RESTRICT",
                ),
                nullable=False,
            ),
            sa.Column(
                "gate_b_session_id",
                sa.String(36),
                sa.ForeignKey("l3_session.session_id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "gate_b_selection_manifest_id",
                sa.String(36),
                sa.ForeignKey("l3_selection_manifest.selection_manifest_id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "gate_b_material_snapshot_id",
                sa.String(36),
                sa.ForeignKey("l3_material_snapshot.material_snapshot_id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("gate_b_decision_manifest_id", sa.String(64), nullable=False),
            sa.Column("gate_b_decision_manifest_hash", sa.String(64), nullable=False),
            sa.Column("material_preview_hash", sa.String(64), nullable=False),
            sa.Column("approval_hash", sa.String(64), nullable=False),
            sa.Column("promotion_basis_hash", sa.String(64), nullable=False),
            sa.Column(
                "dataset_id",
                sa.String(36),
                sa.ForeignKey("dataset.dataset_id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column(
                "dataset_version_id",
                sa.String(36),
                sa.ForeignKey("dataset_version.dataset_version_id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column(
                "promoted_session_id",
                sa.String(36),
                sa.ForeignKey("l3_session.session_id", ondelete="RESTRICT"),
                nullable=True,
            ),
            sa.Column("materialization_status", sa.String(32), nullable=True),
            sa.Column("materialization_basis_hash", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("materialized_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "identity_metadata_hash_version",
                "source_family",
                "content_sha256",
                "identity_metadata_hash",
                name="uq_l3_connector_promotion_identity_tuple",
            ),
            sa.CheckConstraint(
                "receipt_schema_version = 'layer3.connector_promotion_receipt.v1'",
                name="ck_l3_connector_promotion_receipt_schema",
            ),
            sa.CheckConstraint(JOINT_STATE_SQL, name="ck_l3_connector_promotion_joint_state"),
        )
    for index_name, columns in RECEIPT_INDEXES:
        _create_index_once(TABLE_NAME, index_name, columns)


def downgrade() -> None:
    if _receipt_has_rows():
        raise RuntimeError(
            "Cannot downgrade Layer 3 B1b connector promotion while promotion receipt rows exist; "
            "export or disposition requires separate owner authorization."
        )
    _drop_receipt_table()
    _drop_intake_identity_schema()
