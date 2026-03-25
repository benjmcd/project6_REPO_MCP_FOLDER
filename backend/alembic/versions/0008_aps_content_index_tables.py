"""Add APS content indexing derived tables.

Revision ID: 0008_aps_content_index_tables
Revises: 0007_aps_hardening_state_tables
Create Date: 2026-03-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_aps_content_index_tables"
down_revision = "0007_aps_hardening_state_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aps_content_document",
        sa.Column("aps_content_document_id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=64), nullable=False),
        sa.Column("content_contract_id", sa.String(length=64), nullable=False),
        sa.Column("chunking_contract_id", sa.String(length=64), nullable=False),
        sa.Column("normalization_contract_id", sa.String(length=64), nullable=True),
        sa.Column("normalized_text_sha256", sa.String(length=64), nullable=True),
        sa.Column("normalized_char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_status", sa.String(length=64), nullable=False, server_default="indexed"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("aps_content_document_id"),
        sa.UniqueConstraint(
            "content_id",
            "content_contract_id",
            "chunking_contract_id",
            name="uq_aps_content_document_contract",
        ),
    )
    op.create_index(
        "ix_aps_content_document_content",
        "aps_content_document",
        ["content_id", "content_contract_id", "chunking_contract_id"],
    )

    op.create_table(
        "aps_content_chunk",
        sa.Column("aps_content_chunk_id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("content_contract_id", sa.String(length=64), nullable=False),
        sa.Column("chunking_contract_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_char", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("end_char", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_text_sha256", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("aps_content_chunk_id"),
        sa.UniqueConstraint(
            "content_id",
            "chunk_id",
            "content_contract_id",
            "chunking_contract_id",
            name="uq_aps_content_chunk_key",
        ),
    )
    op.create_index(
        "ix_aps_content_chunk_lookup",
        "aps_content_chunk",
        ["content_id", "content_contract_id", "chunking_contract_id", "chunk_ordinal"],
    )

    op.create_table(
        "aps_content_linkage",
        sa.Column("aps_content_linkage_id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("target_id", sa.String(length=36), sa.ForeignKey("connector_run_target.connector_run_target_id"), nullable=False),
        sa.Column("accession_number", sa.String(length=255), nullable=True),
        sa.Column("content_contract_id", sa.String(length=64), nullable=False),
        sa.Column("chunking_contract_id", sa.String(length=64), nullable=False),
        sa.Column("content_units_ref", sa.String(length=1024), nullable=True),
        sa.Column("normalized_text_ref", sa.String(length=1024), nullable=True),
        sa.Column("normalized_text_sha256", sa.String(length=64), nullable=True),
        sa.Column("blob_ref", sa.String(length=1024), nullable=True),
        sa.Column("blob_sha256", sa.String(length=64), nullable=True),
        sa.Column("download_exchange_ref", sa.String(length=1024), nullable=True),
        sa.Column("discovery_ref", sa.String(length=1024), nullable=True),
        sa.Column("selection_ref", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("aps_content_linkage_id"),
        sa.UniqueConstraint(
            "content_id",
            "run_id",
            "target_id",
            "content_contract_id",
            "chunking_contract_id",
            name="uq_aps_content_linkage",
        ),
    )
    op.create_index(
        "ix_aps_content_linkage_run",
        "aps_content_linkage",
        ["run_id", "content_id", "target_id"],
    )
    op.create_index(
        "ix_aps_content_linkage_content",
        "aps_content_linkage",
        ["content_id", "content_contract_id", "chunking_contract_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_aps_content_linkage_content", table_name="aps_content_linkage")
    op.drop_index("ix_aps_content_linkage_run", table_name="aps_content_linkage")
    op.drop_table("aps_content_linkage")
    op.drop_index("ix_aps_content_chunk_lookup", table_name="aps_content_chunk")
    op.drop_table("aps_content_chunk")
    op.drop_index("ix_aps_content_document_content", table_name="aps_content_document")
    op.drop_table("aps_content_document")
