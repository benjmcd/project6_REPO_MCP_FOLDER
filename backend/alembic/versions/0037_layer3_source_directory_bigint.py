"""Widen Layer 3 source-directory size and mtime columns.

Revision ID: 0037_layer3_source_directory_bigint
Revises: 0036_layer3_source_directory_internal_webhook
Create Date: 2026-05-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import table_exists


revision = "0037_layer3_source_directory_bigint"
down_revision = "0036_layer3_source_directory_internal_webhook"
branch_labels = None
depends_on = None


BATCH_TABLE = "l3_source_directory_ingestion_batch"
FILE_TABLE = "l3_source_directory_ingestion_file"


def _widen_column(table_name: str, column_name: str) -> None:
    if not table_exists(table_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def _narrow_column(table_name: str, column_name: str) -> None:
    if not table_exists(table_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )


def upgrade() -> None:
    _widen_column(BATCH_TABLE, "total_size_bytes")
    _widen_column(FILE_TABLE, "content_size_bytes")
    _widen_column(FILE_TABLE, "mtime_ns")


def downgrade() -> None:
    _narrow_column(FILE_TABLE, "mtime_ns")
    _narrow_column(FILE_TABLE, "content_size_bytes")
    _narrow_column(BATCH_TABLE, "total_size_bytes")
