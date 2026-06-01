"""Add Layer 3 SEC XBRL projection persistence tables.

Revision ID: 0038_layer3_sec_xbrl_projection_persistence
Revises: 0037_layer3_source_directory_bigint
Create Date: 2026-06-01
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0038_layer3_sec_xbrl_projection_persistence"
down_revision = "0037_layer3_source_directory_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_sec_xbrl_projection_set",
        sa.Column("sec_xbrl_projection_set_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("projection_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("projection_schema_id", sa.String(length=128), nullable=False),
        sa.Column("source_report_schema_id", sa.String(length=128), nullable=False),
        sa.Column("source_report_hash", sa.String(length=64), nullable=False),
        sa.Column("dataset_version_id", sa.String(length=36), nullable=True),
        sa.Column("sidecar_receipt_hash", sa.String(length=64), nullable=False),
        sa.Column("value_store_hash", sa.String(length=64), nullable=False),
        sa.Column("sector_family_presence_json", sa.JSON(), nullable=False),
        sa.Column("period_refs_json", sa.JSON(), nullable=False),
        sa.Column("projection_summary_json", sa.JSON(), nullable=False),
        sa.Column("redaction_policy", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sec_xbrl_projection_set_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_sec_xbrl_projection_set_client_request",
        ),
        sa.UniqueConstraint(
            "projection_basis_hash",
            name="uq_l3_sec_xbrl_projection_set_basis_hash",
        ),
        sa.CheckConstraint(
            "redaction_policy = 'redacted_no_values'",
            name="ck_l3_sec_xbrl_projection_set_redaction_policy",
        ),
        sa.CheckConstraint(
            "status = 'materialized'",
            name="ck_l3_sec_xbrl_projection_set_status",
        ),
    )
    create_table_idempotent(
        "l3_sec_xbrl_projection_fact",
        sa.Column("sec_xbrl_projection_fact_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_projection_set_id", sa.String(length=36), nullable=False),
        sa.Column("period_ref", sa.String(length=64), nullable=False),
        sa.Column("period_index", sa.Integer(), nullable=False),
        sa.Column("statement", sa.String(length=32), nullable=False),
        sa.Column("statement_row_index", sa.Integer(), nullable=False),
        sa.Column("canonical_id", sa.String(length=128), nullable=False),
        sa.Column("basis", sa.String(length=64), nullable=False),
        sa.Column("requested_basis", sa.String(length=64), nullable=False),
        sa.Column("family", sa.String(length=64), nullable=False),
        sa.Column("source_qname", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("oracle_confirmed", sa.String(length=32), nullable=False),
        sa.Column("mapping_method", sa.String(length=128), nullable=True),
        sa.Column("mapping_confidence", sa.String(length=128), nullable=True),
        sa.Column("unit_class", sa.String(length=64), nullable=True),
        sa.Column("provenance_complete", sa.Boolean(), nullable=False),
        sa.Column("value_redacted", sa.Boolean(), nullable=False),
        sa.Column("resolved_fact_provenance_present", sa.Boolean(), nullable=False),
        sa.Column("sidecar_receipt_hash", sa.String(length=64), nullable=False),
        sa.Column("value_store_hash", sa.String(length=64), nullable=False),
        sa.Column("derived_from_concepts_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_projection_set_id"],
            ["l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_projection_fact_id"),
        sa.UniqueConstraint(
            "sec_xbrl_projection_set_id",
            "period_ref",
            "statement",
            "statement_row_index",
            name="uq_l3_sec_xbrl_projection_fact_statement_row",
        ),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_projection_set_dataset_version",
        "l3_sec_xbrl_projection_set",
        ["dataset_version_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_projection_set_source_report",
        "l3_sec_xbrl_projection_set",
        ["source_report_hash"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_projection_fact_set",
        "l3_sec_xbrl_projection_fact",
        ["sec_xbrl_projection_set_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_projection_fact_canonical",
        "l3_sec_xbrl_projection_fact",
        ["canonical_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_projection_fact_statement",
        "l3_sec_xbrl_projection_fact",
        ["statement"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_sec_xbrl_projection_fact_statement",
        table_name="l3_sec_xbrl_projection_fact",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_projection_fact_canonical",
        table_name="l3_sec_xbrl_projection_fact",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_projection_fact_set",
        table_name="l3_sec_xbrl_projection_fact",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_projection_set_source_report",
        table_name="l3_sec_xbrl_projection_set",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_projection_set_dataset_version",
        table_name="l3_sec_xbrl_projection_set",
    )
    drop_table_idempotent("l3_sec_xbrl_projection_fact")
    drop_table_idempotent("l3_sec_xbrl_projection_set")
