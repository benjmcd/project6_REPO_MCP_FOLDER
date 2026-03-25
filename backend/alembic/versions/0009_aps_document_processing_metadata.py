"""Add APS document-processing metadata columns.

Revision ID: 0009_aps_document_processing_metadata
Revises: 0008_aps_content_index_tables
Create Date: 2026-03-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import add_column_idempotent, drop_column_idempotent


revision = "0009_aps_document_processing_metadata"
down_revision = "0008_aps_content_index_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column_idempotent("aps_content_document", sa.Column("media_type", sa.String(length=128), nullable=True))
    add_column_idempotent("aps_content_document", sa.Column("document_class", sa.String(length=64), nullable=True))
    add_column_idempotent("aps_content_document", sa.Column("quality_status", sa.String(length=32), nullable=True))
    add_column_idempotent("aps_content_document", sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"))
    add_column_idempotent("aps_content_document", sa.Column("diagnostics_ref", sa.String(length=1024), nullable=True))

    add_column_idempotent("aps_content_chunk", sa.Column("page_start", sa.Integer(), nullable=True))
    add_column_idempotent("aps_content_chunk", sa.Column("page_end", sa.Integer(), nullable=True))
    add_column_idempotent("aps_content_chunk", sa.Column("unit_kind", sa.String(length=64), nullable=True))
    add_column_idempotent("aps_content_chunk", sa.Column("quality_status", sa.String(length=32), nullable=True))

    add_column_idempotent("aps_content_linkage", sa.Column("diagnostics_ref", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    drop_column_idempotent("aps_content_linkage", "diagnostics_ref")

    drop_column_idempotent("aps_content_chunk", "quality_status")
    drop_column_idempotent("aps_content_chunk", "unit_kind")
    drop_column_idempotent("aps_content_chunk", "page_end")
    drop_column_idempotent("aps_content_chunk", "page_start")

    drop_column_idempotent("aps_content_document", "diagnostics_ref")
    drop_column_idempotent("aps_content_document", "page_count")
    drop_column_idempotent("aps_content_document", "quality_status")
    drop_column_idempotent("aps_content_document", "document_class")
    drop_column_idempotent("aps_content_document", "media_type")
