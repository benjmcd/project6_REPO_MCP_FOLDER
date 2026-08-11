"""Add Layer 3 connector-promotion identity receipt.

Revision ID: 0057_layer3_b1b_connector_promotion
Revises: 0056_layer3_connector_source_intake_record
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0057_layer3_b1b_connector_promotion"
down_revision = "0056_layer3_connector_source_intake_record"
branch_labels = None
depends_on = None

RECEIPT_TABLE = "l3_connector_promotion_receipt"
INTAKE_TABLE = "l3_connector_source_intake_record"
IDENTITY_CHECK = "ck_l3_connector_source_intake_identity_metadata_joint_null"
IDENTITY_INDEX = "ix_l3_connector_intake_material_identity"


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _column_exists(table: str, name: str) -> bool:
    return _table_exists(table) and any(
        column["name"] == name for column in sa.inspect(op.get_bind()).get_columns(table)
    )


def _index_exists(table: str, name: str) -> bool:
    return _table_exists(table) and any(
        index["name"] == name for index in sa.inspect(op.get_bind()).get_indexes(table)
    )


def _check_exists(table: str, name: str) -> bool:
    if not _table_exists(table):
        return False
    try:
        return any(
            check.get("name") == name
            for check in sa.inspect(op.get_bind()).get_check_constraints(table)
        )
    except NotImplementedError:
        return False


def upgrade() -> None:
    missing = [
        name
        for name in ("identity_metadata_hash_version", "identity_metadata_hash")
        if not _column_exists(INTAKE_TABLE, name)
    ]
    if missing or not _check_exists(INTAKE_TABLE, IDENTITY_CHECK):
        with op.batch_alter_table(INTAKE_TABLE) as batch:
            for name in missing:
                batch.add_column(sa.Column(name, sa.String(64), nullable=True))
            if not _check_exists(INTAKE_TABLE, IDENTITY_CHECK):
                batch.create_check_constraint(
                    IDENTITY_CHECK,
                    "(identity_metadata_hash_version IS NULL AND identity_metadata_hash IS NULL)"
                    " OR (identity_metadata_hash_version IS NOT NULL AND identity_metadata_hash IS NOT NULL)",
                )
    if not _index_exists(INTAKE_TABLE, IDENTITY_INDEX):
        op.create_index(
            IDENTITY_INDEX,
            INTAKE_TABLE,
            [
                "identity_metadata_hash_version",
                "source_family",
                "content_sha256",
                "identity_metadata_hash",
            ],
        )
    if not _table_exists(RECEIPT_TABLE):
        op.create_table(
            RECEIPT_TABLE,
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
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "identity_metadata_hash_version",
                "source_family",
                "content_sha256",
                "identity_metadata_hash",
                name="uq_l3_connector_promotion_identity_tuple",
            ),
            sa.UniqueConstraint(
                "canonical_identity_key_hash",
                name="uq_l3_connector_promotion_canonical_identity",
            ),
            sa.CheckConstraint(
                "receipt_schema_version = 'layer3.connector_promotion_receipt.v1'",
                name="ck_l3_connector_promotion_receipt_schema",
            ),
        )
    for name, columns in (
        ("ix_l3_connector_promotion_intake", ["connector_source_intake_record_id"]),
        ("ix_l3_connector_promotion_gate_b_session", ["gate_b_session_id"]),
        ("ix_l3_connector_promotion_selection_manifest", ["gate_b_selection_manifest_id"]),
        ("ix_l3_connector_promotion_material_snapshot", ["gate_b_material_snapshot_id"]),
    ):
        if not _index_exists(RECEIPT_TABLE, name):
            op.create_index(name, RECEIPT_TABLE, columns)


def downgrade() -> None:
    if _table_exists(RECEIPT_TABLE):
        bind = op.get_bind()
        if bind.dialect.name == "postgresql":
            bind.execute(sa.text(f"LOCK TABLE {RECEIPT_TABLE} IN SHARE ROW EXCLUSIVE MODE"))
        elif bind.dialect.name == "sqlite":
            bind.execute(
                sa.text(
                    f"UPDATE {RECEIPT_TABLE} "
                    "SET connector_promotion_receipt_id = connector_promotion_receipt_id WHERE 0"
                )
            )
        else:
            raise RuntimeError("Cannot safely downgrade connector promotion on this database dialect.")
        if bind.execute(sa.text(f"SELECT 1 FROM {RECEIPT_TABLE} LIMIT 1")).first() is not None:
            raise RuntimeError("Cannot downgrade connector promotion while receipt rows exist.")
        op.drop_table(RECEIPT_TABLE)
    if _index_exists(INTAKE_TABLE, IDENTITY_INDEX):
        op.drop_index(IDENTITY_INDEX, table_name=INTAKE_TABLE)
    with op.batch_alter_table(INTAKE_TABLE) as batch:
        if _check_exists(INTAKE_TABLE, IDENTITY_CHECK):
            batch.drop_constraint(IDENTITY_CHECK, type_="check")
        for name in ("identity_metadata_hash", "identity_metadata_hash_version"):
            if _column_exists(INTAKE_TABLE, name):
                batch.drop_column(name)
