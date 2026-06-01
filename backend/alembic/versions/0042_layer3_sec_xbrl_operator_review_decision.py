"""Add Layer 3 SEC XBRL operator review decision table.

Revision ID: 0042_layer3_sec_xbrl_operator_review_decision
Revises: 0041_layer3_sec_xbrl_redaction_constraints
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


revision = "0042_layer3_sec_xbrl_operator_review_decision"
down_revision = "0041_layer3_sec_xbrl_redaction_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_sec_xbrl_operator_review_decision",
        sa.Column("sec_xbrl_operator_review_decision_id", sa.String(length=36), nullable=False),
        sa.Column("sec_xbrl_operator_review_workflow_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("decision_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("decision_schema_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("statement_packet_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("source_projection_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("decision_mode", sa.String(length=64), nullable=False),
        sa.Column("review_decision", sa.String(length=32), nullable=False),
        sa.Column("decision_status", sa.String(length=64), nullable=False),
        sa.Column("redaction_policy", sa.String(length=64), nullable=False),
        sa.Column("decision_reason_code", sa.String(length=64), nullable=False),
        sa.Column("decision_notes_present", sa.Boolean(), nullable=False),
        sa.Column("decision_notes_hash", sa.String(length=64), nullable=True),
        sa.Column("decision_summary_json", sa.JSON(), nullable=False),
        sa.Column("authority_refs_json", sa.JSON(), nullable=False),
        sa.Column("permitted_controls_after_decision_json", sa.JSON(), nullable=False),
        sa.Column("blocked_controls_after_decision_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_operator_review_workflow_id"],
            ["l3_sec_xbrl_operator_review_workflow.sec_xbrl_operator_review_workflow_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_operator_review_decision_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_sec_xbrl_operator_review_decision_client_request",
        ),
        sa.UniqueConstraint(
            "decision_basis_hash",
            name="uq_l3_sec_xbrl_operator_review_decision_basis_hash",
        ),
        sa.UniqueConstraint(
            "sec_xbrl_operator_review_workflow_id",
            name="uq_l3_sec_xbrl_operator_review_decision_workflow",
        ),
        sa.CheckConstraint(
            "redaction_policy = 'redacted_no_values'",
            name="ck_l3_sec_xbrl_operator_review_decision_redaction_policy",
        ),
        sa.CheckConstraint(
            "decision_mode = 'redacted_statement_packet_operator_review_decision'",
            name="ck_l3_sec_xbrl_operator_review_decision_mode",
        ),
        sa.CheckConstraint(
            "decision_status = 'decision_recorded'",
            name="ck_l3_sec_xbrl_operator_review_decision_status",
        ),
        sa.CheckConstraint(
            "review_decision IN ('approved', 'changes_requested', 'rejected', 'blocked')",
            name="ck_l3_sec_xbrl_operator_review_decision_value",
        ),
        sa.CheckConstraint(
            "decision_reason_code IN ('ready_for_next_freeze', 'needs_packet_revision', 'authority_gap', 'redaction_gap', 'operator_blocked')",
            name="ck_l3_sec_xbrl_operator_review_decision_reason",
        ),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_decision_workflow",
        "l3_sec_xbrl_operator_review_decision",
        ["sec_xbrl_operator_review_workflow_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_decision_workflow_basis",
        "l3_sec_xbrl_operator_review_decision",
        ["workflow_basis_hash"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_decision_workflow_basis",
        table_name="l3_sec_xbrl_operator_review_decision",
    )
    drop_index_idempotent(
        "ix_l3_sec_xbrl_operator_review_decision_workflow",
        table_name="l3_sec_xbrl_operator_review_decision",
    )
    drop_table_idempotent("l3_sec_xbrl_operator_review_decision")
