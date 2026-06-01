"""Add Layer 3 SEC XBRL auth binding receipt table.

Revision ID: 0046_layer3_sec_xbrl_auth_binding_receipt
Revises: 0045_layer3_sec_xbrl_controlled_value_reveal_submit
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


revision = "0046_layer3_sec_xbrl_auth_binding_receipt"
down_revision = "0045_layer3_sec_xbrl_controlled_value_reveal_submit"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_auth_binding_receipt"


def upgrade() -> None:
    create_table_idempotent(
        TABLE_NAME,
        sa.Column("sec_xbrl_auth_binding_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("binding_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("binding_schema_id", sa.String(length=128), nullable=False),
        sa.Column("binding_policy_id", sa.String(length=128), nullable=False),
        sa.Column("binding_state", sa.String(length=64), nullable=False),
        sa.Column("source_receipt_kind", sa.String(length=64), nullable=False),
        sa.Column("source_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("source_receipt_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("route_family", sa.String(length=96), nullable=False),
        sa.Column("actor_ref_hash", sa.String(length=64), nullable=False),
        sa.Column("workspace_ref_hash", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("policy_hash", sa.String(length=64), nullable=False),
        sa.Column("redaction_policy", sa.String(length=128), nullable=False),
        sa.Column("binding_summary_json", sa.JSON(), nullable=False),
        sa.Column("negative_invariants_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sec_xbrl_auth_binding_receipt_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_sec_xbrl_auth_binding_client_request"),
        sa.UniqueConstraint("binding_basis_hash", name="uq_l3_sec_xbrl_auth_binding_basis_hash"),
        sa.UniqueConstraint(
            "source_receipt_kind",
            "source_receipt_id",
            name="uq_l3_sec_xbrl_auth_binding_source_receipt",
        ),
        sa.CheckConstraint(
            "binding_policy_id = 'sec_xbrl_repo_owned_in_app_auth_owner_binding_v1'",
            name="ck_l3_sec_xbrl_auth_binding_policy",
        ),
        sa.CheckConstraint("binding_state = 'owner_bound'", name="ck_l3_sec_xbrl_auth_binding_state"),
        sa.CheckConstraint(
            "redaction_policy = 'hash_only_actor_workspace_policy_refs_v1'",
            name="ck_l3_sec_xbrl_auth_binding_redaction",
        ),
        sa.CheckConstraint(
            "source_receipt_kind IN ('operator_review_workflow', 'operator_review_decision', 'value_reveal_authority', 'controlled_value_reveal_submit')",
            name="ck_l3_sec_xbrl_auth_binding_source_kind",
        ),
        sa.CheckConstraint(
            "route_family IN ('sec_xbrl_operator_review_workflow_status_read', 'sec_xbrl_operator_review_decision_submit_write', 'sec_xbrl_operator_review_decision_status_read', 'sec_xbrl_value_reveal_authority_prepare_write', 'sec_xbrl_controlled_value_reveal_submit_write', 'sec_xbrl_controlled_value_reveal_submit_status_read')",
            name="ck_l3_sec_xbrl_auth_binding_route_family",
        ),
        sa.CheckConstraint("role IN ('owner', 'auditor')", name="ck_l3_sec_xbrl_auth_binding_role"),
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_auth_binding_source_basis",
        TABLE_NAME,
        ["source_receipt_kind", "source_receipt_basis_hash"],
    )
    create_index_idempotent(
        "ix_l3_sec_xbrl_auth_binding_actor_workspace",
        TABLE_NAME,
        ["actor_ref_hash", "workspace_ref_hash"],
    )
    create_index_idempotent("ix_l3_sec_xbrl_auth_binding_policy", TABLE_NAME, ["policy_hash"])
    create_index_idempotent("ix_l3_sec_xbrl_auth_binding_route_family", TABLE_NAME, ["route_family"])


def downgrade() -> None:
    drop_index_idempotent("ix_l3_sec_xbrl_auth_binding_route_family", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_auth_binding_policy", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_auth_binding_actor_workspace", table_name=TABLE_NAME)
    drop_index_idempotent("ix_l3_sec_xbrl_auth_binding_source_basis", table_name=TABLE_NAME)
    drop_table_idempotent(TABLE_NAME)
