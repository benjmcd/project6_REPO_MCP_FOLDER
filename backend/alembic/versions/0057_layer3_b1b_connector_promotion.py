"""Add Layer 3 B1b connector promotion receipt (Option II, inert additive schema).

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


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_once(index_name: str, columns: list[str]) -> None:
    if not _index_exists(TABLE_NAME, index_name):
        op.create_index(index_name, TABLE_NAME, columns)


def upgrade() -> None:
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
    _create_index_once("ix_l3_connector_promotion_intake", ["connector_source_intake_record_id"])
    _create_index_once("ix_l3_connector_promotion_gate_b_session", ["gate_b_session_id"])
    _create_index_once("ix_l3_connector_promotion_selection_manifest", ["gate_b_selection_manifest_id"])
    _create_index_once("ix_l3_connector_promotion_material_snapshot", ["gate_b_material_snapshot_id"])
    _create_index_once("ix_l3_connector_promotion_dataset", ["dataset_id"])
    _create_index_once("ix_l3_connector_promotion_dataset_version", ["dataset_version_id"])
    _create_index_once("ix_l3_connector_promotion_promoted_session", ["promoted_session_id"])


def downgrade() -> None:
    if _table_exists(TABLE_NAME):
        op.drop_table(TABLE_NAME)
