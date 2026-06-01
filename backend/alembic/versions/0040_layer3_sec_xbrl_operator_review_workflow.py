"""Add Layer 3 SEC XBRL operator review workflow table.

Revision ID: 0040_layer3_sec_xbrl_operator_review_workflow
Revises: 0039_layer3_sec_xbrl_statement_packet_persistence
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


revision = "0040_layer3_sec_xbrl_operator_review_workflow"
down_revision = "0039_layer3_sec_xbrl_statement_packet_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_sec_xbrl_operator_review_workflow",
        sa.Column("sec_xbrl_operator_review_workflow_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_statement_packet_set_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("workflow_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("workflow_schema_id", sa.String(length=128), nullable=False),
        sa.Column("statement_packet_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("source_projection_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("control_mode", sa.String(length=64), nullable=False),
        sa.Column("review_status", sa.String(length=64), nullable=False),
        sa.Column("redaction_policy", sa.String(length=64), nullable=False),
        sa.Column("statement_count", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("review_exception_count", sa.Integer(), nullable=False),
        sa.Column("review_ready", sa.Boolean(), nullable=False),
        sa.Column("permitted_controls_json", sa.JSON(), nullable=False),
        sa.Column("blocked_controls_json", sa.JSON(), nullable=False),
        sa.Column("authority_refs_json", sa.JSON(), nullable=False),
        sa.Column("review_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_statement_packet_set_id"],
            ["l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_operator_review_workflow_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_sec_xbrl_operator_review_workflow_client_request",
        ),
        sa.UniqueConstraint(
            "workflow_basis_hash",
            name="uq_l3_sec_xbrl_operator_review_workflow_basis_hash",
        ),
        sa.CheckConstraint(
            "redaction_policy = 'redacted_no_values'",
            name="ck_l3_sec_xbrl_operator_review_workflow_redaction_policy",
        ),
        sa.CheckConstraint(
            "control_mode = 'redacted_statement_packet_review_only'",
            name="ck_l3_sec_xbrl_operator_review_workflow_control_mode",
        ),
        sa.CheckConstraint(
            "review_status = 'review_ready'",
            name="ck_l3_sec_xbrl_operator_review_workflow_status",
        ),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_workflow_packet",
        "l3_sec_xbrl_operator_review_workflow",
        ["sec_xbrl_statement_packet_set_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_workflow_packet_basis",
        "l3_sec_xbrl_operator_review_workflow",
        ["statement_packet_basis_hash"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_workflow_packet_basis",
        table_name="l3_sec_xbrl_operator_review_workflow",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_workflow_packet",
        table_name="l3_sec_xbrl_operator_review_workflow",
    )
    drop_table_idempotent("l3_sec_xbrl_operator_review_workflow")
