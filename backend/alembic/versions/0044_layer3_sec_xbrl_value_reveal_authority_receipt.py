"""Add Layer 3 SEC XBRL value-reveal authority receipt table.

Revision ID: 0044_layer3_sec_xbrl_value_reveal_authority_receipt
Revises: 0043_layer3_sec_xbrl_statement_packet_row_period_unique
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


revision = "0044_layer3_sec_xbrl_value_reveal_authority_receipt"
down_revision = "0043_layer3_sec_xbrl_statement_packet_row_period_unique"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_value_reveal_authority_receipt"


def upgrade() -> None:
    create_table_idempotent(
        TABLE_NAME,
        sa.Column("sec_xbrl_value_reveal_authority_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_schema_id", sa.String(length=128), nullable=False),
        sa.Column("sec_xbrl_operator_review_decision_id", sa.String(length=36), nullable=False),
        sa.Column("decision_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("sec_xbrl_operator_review_workflow_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("sec_xbrl_statement_packet_set_id", sa.String(length=36), nullable=False),
        sa.Column("statement_packet_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("sec_xbrl_projection_set_id", sa.String(length=36), nullable=False),
        sa.Column("projection_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_version_hash", sa.String(length=64), nullable=False),
        sa.Column("sidecar_receipt_id_hash", sa.String(length=64), nullable=False),
        sa.Column("sidecar_receipt_hash", sa.String(length=64), nullable=False),
        sa.Column("value_store_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_state", sa.String(length=64), nullable=False),
        sa.Column("authority_policy_id", sa.String(length=128), nullable=False),
        sa.Column("redaction_policy", sa.String(length=128), nullable=False),
        sa.Column("operator_actor_hash", sa.String(length=64), nullable=True),
        sa.Column("authority_summary_json", sa.JSON(), nullable=False),
        sa.Column("negative_invariants_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_operator_review_decision_id"],
            ["l3_sec_xbrl_operator_review_decision.sec_xbrl_operator_review_decision_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_operator_review_workflow_id"],
            ["l3_sec_xbrl_operator_review_workflow.sec_xbrl_operator_review_workflow_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_statement_packet_set_id"],
            ["l3_sec_xbrl_statement_packet_set.sec_xbrl_statement_packet_set_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_projection_set_id"],
            ["l3_sec_xbrl_projection_set.sec_xbrl_projection_set_id"],
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["dataset_version.dataset_version_id"],
        ),
        sa.PrimaryKeyConstraint("sec_xbrl_value_reveal_authority_receipt_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_value_reveal_authority_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_sec_xbrl_value_reveal_authority_basis_hash"),
        sa.UniqueConstraint(
            "sec_xbrl_operator_review_decision_id",
            name="uq_l3_sec_xbrl_value_reveal_authority_decision",
        ),
        sa.CheckConstraint(
            "authority_state = 'ready_for_explicit_value_reveal'",
            name="ck_l3_sec_xbrl_value_reveal_authority_state",
        ),
        sa.CheckConstraint(
            "authority_policy_id = 'sec_xbrl_approved_decision_bound_value_reveal_authority_v1'",
            name="ck_l3_sec_xbrl_value_reveal_authority_policy",
        ),
        sa.CheckConstraint(
            "redaction_policy = 'sec_xbrl_value_reveal_authority_hashes_only_v1'",
            name="ck_l3_sec_xbrl_value_reveal_authority_redaction",
        ),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_value_reveal_authority_decision",
        TABLE_NAME,
        ["sec_xbrl_operator_review_decision_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_value_reveal_authority_basis",
        TABLE_NAME,
        ["authority_basis_hash"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_value_reveal_authority_dataset",
        TABLE_NAME,
        ["dataset_version_id"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_value_reveal_authority_sidecar",
        TABLE_NAME,
        ["sidecar_receipt_hash"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_value_reveal_authority_projection_basis",
        TABLE_NAME,
        ["projection_basis_hash"],
    )


def downgrade() -> None:
    drop_index_idempotent("ix_l3_sec_xbrl_value_reveal_authority_projection_basis", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_value_reveal_authority_sidecar", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_value_reveal_authority_dataset", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_value_reveal_authority_basis", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_value_reveal_authority_decision", table_name=TABLE_NAME)
    drop_table_idempotent(TABLE_NAME)
