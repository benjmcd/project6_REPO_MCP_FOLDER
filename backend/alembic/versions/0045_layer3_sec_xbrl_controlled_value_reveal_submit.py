"""Add Layer 3 SEC XBRL controlled value-reveal submit receipt table.

Revision ID: 0045_layer3_sec_xbrl_controlled_value_reveal_submit
Revises: 0044_layer3_sec_xbrl_value_reveal_authority_receipt
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


revision = "0045_layer3_sec_xbrl_controlled_value_reveal_submit"
down_revision = "0044_layer3_sec_xbrl_value_reveal_authority_receipt"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_controlled_value_reveal_submit_receipt"


def upgrade() -> None:
    create_table_idempotent(
        TABLE_NAME,
        sa.Column("sec_xbrl_controlled_value_reveal_submit_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("submit_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("submit_schema_id", sa.String(length=128), nullable=False),
        sa.Column("sec_xbrl_value_reveal_authority_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
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
        sa.Column("submit_state", sa.String(length=64), nullable=False),
        sa.Column("submit_policy_id", sa.String(length=128), nullable=False),
        sa.Column("redaction_policy", sa.String(length=128), nullable=False),
        sa.Column("revealed_fact_count", sa.Integer(), nullable=False),
        sa.Column("value_redacted_fact_count", sa.Integer(), nullable=False),
        sa.Column("fact_inventory_hash", sa.String(length=64), nullable=False),
        sa.Column("value_inventory_hash", sa.String(length=64), nullable=False),
        sa.Column("response_inventory_hash", sa.String(length=64), nullable=False),
        sa.Column("submit_summary_json", sa.JSON(), nullable=False),
        sa.Column("negative_invariants_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["sec_xbrl_value_reveal_authority_receipt_id"],
            ["l3_sec_xbrl_value_reveal_authority_receipt.sec_xbrl_value_reveal_authority_receipt_id"],
        ),
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
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_version.dataset_version_id"]),
        sa.PrimaryKeyConstraint("sec_xbrl_controlled_value_reveal_submit_receipt_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_controlled_value_reveal_client_request"),
        sa.UniqueConstraint("submit_basis_hash", name="uq_l3_sec_xbrl_controlled_value_reveal_basis_hash"),
        sa.UniqueConstraint(
            "sec_xbrl_value_reveal_authority_receipt_id",
            name="uq_l3_sec_xbrl_controlled_value_reveal_authority",
        ),
        sa.CheckConstraint(
            "submit_state = 'controlled_values_revealed_transiently'",
            name="ck_l3_sec_xbrl_controlled_value_reveal_state",
        ),
        sa.CheckConstraint(
            "submit_policy_id = 'sec_xbrl_authority_receipt_bound_controlled_value_reveal_submit_v1'",
            name="ck_l3_sec_xbrl_controlled_value_reveal_policy",
        ),
        sa.CheckConstraint(
            "redaction_policy = 'sec_xbrl_controlled_value_reveal_submit_hash_count_receipt_v1'",
            name="ck_l3_sec_xbrl_controlled_value_reveal_redaction",
        ),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_controlled_value_reveal_authority",
        TABLE_NAME,
        ["sec_xbrl_value_reveal_authority_receipt_id"],
    )
    create_index_idempotent("ix_l3_sec_xbrl_controlled_value_reveal_basis", TABLE_NAME, ["submit_basis_hash"])
    create_index_idempotent(
        "ix_l3_sec_xbrl_controlled_value_reveal_projection",
        TABLE_NAME,
        ["projection_basis_hash"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_controlled_value_reveal_dataset",
        TABLE_NAME,
        ["dataset_version_id"],
    )


def downgrade() -> None:
    drop_index_idempotent("ix_l3_sec_xbrl_controlled_value_reveal_dataset", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_controlled_value_reveal_projection", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_controlled_value_reveal_basis", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_controlled_value_reveal_authority", table_name=TABLE_NAME)
    drop_table_idempotent(TABLE_NAME)
