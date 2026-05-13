"""Add Layer 3 source intake record.

Revision ID: 0024_layer3_source_intake_record
Revises: 0023_layer3_provider_private_signed_url_recipient_scope
Create Date: 2026-05-13 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_layer3_source_intake_record"
down_revision = "0023_layer3_provider_private_signed_url_recipient_scope"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_source_intake_record"


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
            sa.Column("source_intake_record_id", sa.String(length=36), nullable=False),
            sa.Column("client_request_id", sa.String(length=255), nullable=False),
            sa.Column("operator_decision", sa.String(length=64), nullable=False),
            sa.Column("source_family", sa.String(length=64), nullable=False),
            sa.Column("source_label", sa.String(length=255), nullable=False),
            sa.Column("source_description", sa.Text(), nullable=True),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("media_type", sa.String(length=128), nullable=True),
            sa.Column("content_size_bytes", sa.Integer(), nullable=False),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("metadata_hash", sa.String(length=64), nullable=False),
            sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
            sa.Column("storage_ref", sa.String(length=1024), nullable=False),
            sa.Column("freshness_timestamp", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provenance_json", sa.JSON(), nullable=False),
            sa.Column("downstream_eligibility_json", sa.JSON(), nullable=False),
            sa.Column("summary_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "operator_decision = 'record_operator_uploaded_source'",
                name="ck_l3_source_intake_operator_decision",
            ),
            sa.CheckConstraint(
                "status IN ('recorded', 'already_recorded')",
                name="ck_l3_source_intake_status",
            ),
            sa.PrimaryKeyConstraint("source_intake_record_id"),
            sa.UniqueConstraint("client_request_id", name="uq_l3_source_intake_client_request"),
            sa.UniqueConstraint("authority_basis_hash", name="uq_l3_source_intake_authority_basis"),
        )
    _create_index_once("ix_l3_source_intake_content_sha256", ["content_sha256"])
    _create_index_once("ix_l3_source_intake_source_family", ["source_family"])
    _create_index_once("ix_l3_source_intake_status", ["status"])


def downgrade() -> None:
    if _table_exists(TABLE_NAME):
        op.drop_table(TABLE_NAME)
