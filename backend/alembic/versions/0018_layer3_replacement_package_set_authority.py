"""Add Layer 3 replacement package set authority table.

Revision ID: 0018_layer3_replacement_package_set_authority
Revises: 0017_layer3_gate_b_idempotency
Create Date: 2026-05-05
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0018_layer3_replacement_package_set_authority"
down_revision = "0017_layer3_gate_b_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_replacement_package_set_authority",
        sa.Column("replacement_package_set_authority_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "analysis_plan_id",
            sa.String(length=36),
            sa.ForeignKey("l3_analysis_plan.analysis_plan_id"),
            nullable=False,
        ),
        sa.Column("pass_run_id", sa.String(length=36), sa.ForeignKey("l3_pass_run.pass_run_id"), nullable=False),
        sa.Column(
            "reconciliation_record_id",
            sa.String(length=36),
            sa.ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
            nullable=False,
        ),
        sa.Column("source_package_set_hash", sa.String(length=64), nullable=False),
        sa.Column("source_output_package_ids_json", sa.JSON(), nullable=False),
        sa.Column("source_package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("source_payload_refs_json", sa.JSON(), nullable=False),
        sa.Column("source_payload_hashes_json", sa.JSON(), nullable=False),
        sa.Column("replacement_package_set_id", sa.String(length=128), nullable=False),
        sa.Column("replacement_package_set_hash", sa.String(length=64), nullable=False),
        sa.Column("replacement_package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("replacement_payload_refs_json", sa.JSON(), nullable=False),
        sa.Column("replacement_payload_hashes_json", sa.JSON(), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("operator_decision", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("replacement_package_set_authority_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_replacement_package_set_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_replacement_package_set_basis_hash"),
        sa.CheckConstraint(
            "operator_decision = 'record_replacement_package_set_authority'",
            name="ck_l3_replacement_package_set_operator_decision",
        ),
    )
    create_index_idempotent(
        "ix_l3_replacement_package_set_session",
        "l3_replacement_package_set_authority",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_package_set_reconciliation",
        "l3_replacement_package_set_authority",
        ["reconciliation_record_id"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_replacement_package_set_reconciliation",
        table_name="l3_replacement_package_set_authority",
    )
    drop_index_idempotent(
        "ix_l3_replacement_package_set_session",
        table_name="l3_replacement_package_set_authority",
    )
    drop_table_idempotent("l3_replacement_package_set_authority")
