"""Add APS retrieval-plane derived table.

Revision ID: 0011_aps_retrieval_chunk_v1
Revises: 0010_visual_page_refs_json
Create Date: 2026-03-27
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0011_aps_retrieval_chunk_v1"
down_revision = "0010_visual_page_refs_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "aps_retrieval_chunk_v1",
        sa.Column("aps_retrieval_chunk_id", sa.String(length=64), nullable=False),
        sa.Column("retrieval_contract_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("target_id", sa.String(length=36), sa.ForeignKey("connector_run_target.connector_run_target_id"), nullable=False),
        sa.Column("content_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("content_contract_id", sa.String(length=64), nullable=False),
        sa.Column("chunking_contract_id", sa.String(length=64), nullable=False),
        sa.Column("normalization_contract_id", sa.String(length=64), nullable=True),
        sa.Column("accession_number", sa.String(length=255), nullable=True),
        sa.Column("chunk_ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_char", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("end_char", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_text_sha256", sa.String(length=64), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("content_status", sa.String(length=64), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=True),
        sa.Column("document_class", sa.String(length=64), nullable=True),
        sa.Column("media_type", sa.String(length=128), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_units_ref", sa.String(length=1024), nullable=True),
        sa.Column("normalized_text_ref", sa.String(length=1024), nullable=True),
        sa.Column("blob_ref", sa.String(length=1024), nullable=True),
        sa.Column("download_exchange_ref", sa.String(length=1024), nullable=True),
        sa.Column("discovery_ref", sa.String(length=1024), nullable=True),
        sa.Column("selection_ref", sa.String(length=1024), nullable=True),
        sa.Column("diagnostics_ref", sa.String(length=1024), nullable=True),
        sa.Column("visual_page_refs_json", sa.Text(), nullable=True),
        sa.Column("source_signature_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rebuilt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("aps_retrieval_chunk_id"),
        sa.UniqueConstraint(
            "retrieval_contract_id",
            "run_id",
            "target_id",
            "content_id",
            "chunk_id",
            name="uq_aps_retrieval_chunk_v1_lookup",
        ),
    )
    create_index_idempotent(
        "ix_aps_retrieval_chunk_v1_run_filters",
        "aps_retrieval_chunk_v1",
        ["run_id", "quality_status", "document_class"],
    )
    create_index_idempotent(
        "ix_aps_retrieval_chunk_v1_run_content",
        "aps_retrieval_chunk_v1",
        ["run_id", "content_id", "chunk_ordinal"],
    )
    create_index_idempotent(
        "ix_aps_retrieval_chunk_v1_content_chunk",
        "aps_retrieval_chunk_v1",
        ["content_id", "chunk_id"],
    )


def downgrade() -> None:
    drop_index_idempotent("ix_aps_retrieval_chunk_v1_content_chunk", table_name="aps_retrieval_chunk_v1")
    drop_index_idempotent("ix_aps_retrieval_chunk_v1_run_content", table_name="aps_retrieval_chunk_v1")
    drop_index_idempotent("ix_aps_retrieval_chunk_v1_run_filters", table_name="aps_retrieval_chunk_v1")
    drop_table_idempotent("aps_retrieval_chunk_v1")
