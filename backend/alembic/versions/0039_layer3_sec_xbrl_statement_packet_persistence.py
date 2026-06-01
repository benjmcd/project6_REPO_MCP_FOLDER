"""Add Layer 3 SEC XBRL statement packet persistence tables.

Revision ID: 0039_layer3_sec_xbrl_statement_packet_persistence
Revises: 0038_layer3_sec_xbrl_projection_persistence
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


revision = "0039_layer3_sec_xbrl_statement_packet_persistence"
down_revision = "0038_layer3_sec_xbrl_projection_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_sec_xbrl_statement_packet_set",
        sa.Column("sec_xbrl_statement_packet_set_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_projection_set_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("packet_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("packet_schema_id", sa.String(length=128), nullable=False),
        sa.Column("source_projection_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("source_projection_schema_id", sa.String(length=128), nullable=False),
        sa.Column("statement_organization_authority", sa.String(length=128), nullable=False),
        sa.Column("value_policy", sa.String(length=64), nullable=False),
        sa.Column("statement_count", sa.Integer(), nullable=False),
        sa.Column("total_review_rows", sa.Integer(), nullable=False),
        sa.Column("provenance_complete_count", sa.Integer(), nullable=False),
        sa.Column("review_exception_count", sa.Integer(), nullable=False),
        sa.Column("review_ready", sa.Boolean(), nullable=False),
        sa.Column("identity_rollup_json", sa.JSON(), nullable=False),
        sa.Column("organization_contract_json", sa.JSON(), nullable=False),
        sa.Column("packet_summary_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_projection_set_id"],
            ["l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_statement_packet_set_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_sec_xbrl_statement_packet_set_client_request",
        ),
        sa.UniqueConstraint(
            "packet_basis_hash",
            name="uq_l3_sec_xbrl_statement_packet_set_basis_hash",
        ),
        sa.CheckConstraint(
            "value_policy = 'redacted_no_values'",
            name="ck_l3_sec_xbrl_statement_packet_set_value_policy",
        ),
        sa.CheckConstraint(
            "status = 'materialized'",
            name="ck_l3_sec_xbrl_statement_packet_set_status",
        ),
    )
    create_table_idempotent(
        "l3_sec_xbrl_statement_packet_statement",
        sa.Column("sec_xbrl_statement_packet_statement_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_statement_packet_set_id", sa.String(length=36), nullable=False),
        sa.Column("statement", sa.String(length=32), nullable=False),
        sa.Column("statement_index", sa.Integer(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("projected_count", sa.Integer(), nullable=False),
        sa.Column("derived_count", sa.Integer(), nullable=False),
        sa.Column("provenance_complete_count", sa.Integer(), nullable=False),
        sa.Column("review_exception_count", sa.Integer(), nullable=False),
        sa.Column("status_counts_json", sa.JSON(), nullable=False),
        sa.Column("family_counts_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_statement_packet_set_id"],
            ["l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_statement_packet_statement_id"),
        sa.UniqueConstraint(
            "sec_xbrl_statement_packet_set_id",
            "statement",
            name="uq_l3_sec_xbrl_statement_packet_statement_name",
        ),
        sa.UniqueConstraint(
            "sec_xbrl_statement_packet_set_id",
            "statement_index",
            name="uq_l3_sec_xbrl_statement_packet_statement_index",
        ),
    )
    create_table_idempotent(
        "l3_sec_xbrl_statement_packet_row",
        sa.Column("sec_xbrl_statement_packet_row_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_statement_packet_statement_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_projection_fact_id", sa.String(length=36), nullable=False),
        sa.Column("statement", sa.String(length=32), nullable=False),
        sa.Column("statement_row_index", sa.Integer(), nullable=False),
        sa.Column("source_index", sa.Integer(), nullable=False),
        sa.Column("period_ref", sa.String(length=64), nullable=False),
        sa.Column("period_index", sa.Integer(), nullable=False),
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
        sa.Column("review_exception", sa.Boolean(), nullable=False),
        sa.Column("derived_from_concepts_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_statement_packet_statement_id"],
            ["l3_sec_xbrl_statement_packet_statement.sec_xbrl_statement_packet_statement_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_projection_fact_id"],
            ["l3_sec_xbrl_projection_fact.sec_xbrl_projection_fact_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_statement_packet_row_id"),
        sa.UniqueConstraint(
            "sec_xbrl_statement_packet_statement_id",
            "statement_row_index",
            name="uq_l3_sec_xbrl_statement_packet_row_statement_index",
        ),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_set_projection",
        "l3_sec_xbrl_statement_packet_set",
        ["sec_xbrl_projection_set_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_set_projection_basis",
        "l3_sec_xbrl_statement_packet_set",
        ["source_projection_basis_hash"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_statement_set",
        "l3_sec_xbrl_statement_packet_statement",
        ["sec_xbrl_statement_packet_set_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_row_statement",
        "l3_sec_xbrl_statement_packet_row",
        ["sec_xbrl_statement_packet_statement_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_row_projection_fact",
        "l3_sec_xbrl_statement_packet_row",
        ["sec_xbrl_projection_fact_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_row_canonical",
        "l3_sec_xbrl_statement_packet_row",
        ["canonical_id"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_row_canonical",
        table_name="l3_sec_xbrl_statement_packet_row",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_row_projection_fact",
        table_name="l3_sec_xbrl_statement_packet_row",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_row_statement",
        table_name="l3_sec_xbrl_statement_packet_row",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_statement_set",
        table_name="l3_sec_xbrl_statement_packet_statement",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_set_projection_basis",
        table_name="l3_sec_xbrl_statement_packet_set",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_statement_packet_set_projection",
        table_name="l3_sec_xbrl_statement_packet_set",
    )
    drop_table_idempotent("l3_sec_xbrl_statement_packet_row")
    drop_table_idempotent("l3_sec_xbrl_statement_packet_statement")
    drop_table_idempotent("l3_sec_xbrl_statement_packet_set")
