"""Add Layer 3 source directory ingestion authority.

Revision ID: 0034_layer3_source_directory_ingestion
Revises: 0033_layer3_corrected_package_artifact_set
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0034_layer3_source_directory_ingestion"
down_revision = "0033_layer3_corrected_package_artifact_set"
branch_labels = None
depends_on = None


BATCH_TABLE = "l3_source_directory_ingestion_batch"
FILE_TABLE = "l3_source_directory_ingestion_file"


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not _table_exists(BATCH_TABLE):
        op.create_table(
            BATCH_TABLE,
            sa.Column("source_ingestion_batch_id", sa.String(length=36), nullable=False),
            sa.Column("client_request_id", sa.String(length=255), nullable=False),
            sa.Column("source_family", sa.String(length=96), nullable=False),
            sa.Column("ingestion_mode", sa.String(length=96), nullable=False),
            sa.Column("config_authority", sa.String(length=96), nullable=False),
            sa.Column("directory_fingerprint_hash", sa.String(length=64), nullable=False),
            sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
            sa.Column("eligible_file_count", sa.Integer(), nullable=False),
            sa.Column("total_size_bytes", sa.Integer(), nullable=False),
            sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
            sa.Column("summary_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "source_family = 'server_configured_operator_directory_text_table_source_family'",
                name="ck_l3_source_directory_batch_source_family",
            ),
            sa.CheckConstraint(
                "ingestion_mode = 'server_configured_operator_directory_text_table_ingestion'",
                name="ck_l3_source_directory_batch_ingestion_mode",
            ),
            sa.CheckConstraint(
                "status IN ('recorded', 'already_recorded')",
                name="ck_l3_source_directory_batch_status",
            ),
            sa.PrimaryKeyConstraint("source_ingestion_batch_id"),
            sa.UniqueConstraint("client_request_id", name="uq_l3_source_directory_batch_client_request"),
            sa.UniqueConstraint("authority_basis_hash", name="uq_l3_source_directory_batch_authority_basis"),
            sa.UniqueConstraint("directory_fingerprint_hash", name="uq_l3_source_directory_batch_fingerprint"),
        )
    if not _table_exists(FILE_TABLE):
        op.create_table(
            FILE_TABLE,
            sa.Column("source_ingestion_file_id", sa.String(length=36), nullable=False),
            sa.Column("source_ingestion_batch_id", sa.String(length=36), nullable=False),
            sa.Column("relative_name", sa.String(length=255), nullable=False),
            sa.Column("extension", sa.String(length=16), nullable=False),
            sa.Column("media_type", sa.String(length=128), nullable=False),
            sa.Column("content_size_bytes", sa.Integer(), nullable=False),
            sa.Column("mtime_ns", sa.Integer(), nullable=False),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("file_identity_hash", sa.String(length=64), nullable=False),
            sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
            sa.Column("summary_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("status = 'recorded'", name="ck_l3_source_directory_file_status"),
            sa.ForeignKeyConstraint(
                ["source_ingestion_batch_id"],
                [f"{BATCH_TABLE}.source_ingestion_batch_id"],
            ),
            sa.PrimaryKeyConstraint("source_ingestion_file_id"),
            sa.UniqueConstraint(
                "source_ingestion_batch_id",
                "relative_name",
                name="uq_l3_source_directory_file_batch_relative_name",
            ),
            sa.UniqueConstraint("authority_basis_hash", name="uq_l3_source_directory_file_authority_basis"),
        )
    _create_index_once(BATCH_TABLE, "ix_l3_source_directory_batch_source_family", ["source_family"])
    _create_index_once(BATCH_TABLE, "ix_l3_source_directory_batch_status", ["status"])
    _create_index_once(FILE_TABLE, "ix_l3_source_directory_file_batch", ["source_ingestion_batch_id"])
    _create_index_once(FILE_TABLE, "ix_l3_source_directory_file_extension", ["extension"])
    _create_index_once(FILE_TABLE, "ix_l3_source_directory_file_sha256", ["content_sha256"])


def downgrade() -> None:
    if _table_exists(FILE_TABLE):
        op.drop_table(FILE_TABLE)
    if _table_exists(BATCH_TABLE):
        op.drop_table(BATCH_TABLE)
