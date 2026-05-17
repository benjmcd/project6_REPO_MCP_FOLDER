"""Add Layer 3 corrected package artifact set table.

Revision ID: 0033_layer3_corrected_package_artifact_set
Revises: 0032_layer3_package_replacement_activation
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0033_layer3_corrected_package_artifact_set"
down_revision = "0032_layer3_package_replacement_activation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_corrected_package_artifact_set",
        sa.Column("corrected_package_artifact_set_id", sa.String(length=36), nullable=False),
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
        sa.Column(
            "replacement_artifact_materialization_id",
            sa.String(length=36),
            sa.ForeignKey("l3_replacement_package_artifact_materialization.replacement_artifact_materialization_id"),
            nullable=False,
        ),
        sa.Column("materialization_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("source_package_set_hash", sa.String(length=64), nullable=False),
        sa.Column("source_output_package_ids_json", sa.JSON(), nullable=False),
        sa.Column("source_package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("source_payload_refs_json", sa.JSON(), nullable=False),
        sa.Column("source_payload_hashes_json", sa.JSON(), nullable=False),
        sa.Column("result_review_record_ref", sa.String(length=512), nullable=False),
        sa.Column("reviewed_output_items_hash", sa.String(length=64), nullable=False),
        sa.Column("package_review_preview_hash", sa.String(length=64), nullable=False),
        sa.Column("corrected_package_set_id", sa.String(length=128), nullable=False),
        sa.Column("corrected_package_set_hash", sa.String(length=64), nullable=False),
        sa.Column("corrected_package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("corrected_artifact_refs_json", sa.JSON(), nullable=False),
        sa.Column("corrected_artifact_hashes_json", sa.JSON(), nullable=False),
        sa.Column("corrected_artifact_byte_sizes_json", sa.JSON(), nullable=False),
        sa.Column("artifact_namespace", sa.String(length=128), nullable=False),
        sa.Column("artifact_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("corrected_artifact_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("audit_history_json", sa.JSON(), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("operator_decision", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("corrected_package_artifact_set_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_corrected_artifact_set_client_request"),
        sa.UniqueConstraint(
            "corrected_artifact_basis_hash",
            name="uq_l3_corrected_artifact_set_basis_hash",
        ),
        sa.CheckConstraint(
            "operator_decision = 'record_corrected_package_artifact_set_from_review_corrections'",
            name="ck_l3_corrected_artifact_set_operator_decision",
        ),
        sa.CheckConstraint("status = 'recorded'", name="ck_l3_corrected_artifact_set_status"),
    )
    create_index_idempotent(
        "ix_l3_corrected_artifact_set_session",
        "l3_corrected_package_artifact_set",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_corrected_artifact_set_reconciliation",
        "l3_corrected_package_artifact_set",
        ["reconciliation_record_id"],
    )
    create_index_idempotent(
        "ix_l3_corrected_artifact_set_materialization",
        "l3_corrected_package_artifact_set",
        ["replacement_artifact_materialization_id"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_corrected_artifact_set_materialization",
        table_name="l3_corrected_package_artifact_set",
    )
    drop_index_idempotent(
        "ix_l3_corrected_artifact_set_reconciliation",
        table_name="l3_corrected_package_artifact_set",
    )
    drop_index_idempotent(
        "ix_l3_corrected_artifact_set_session",
        table_name="l3_corrected_package_artifact_set",
    )
    drop_table_idempotent("l3_corrected_package_artifact_set")
