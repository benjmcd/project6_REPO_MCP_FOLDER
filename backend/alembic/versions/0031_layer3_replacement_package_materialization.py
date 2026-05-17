"""Add Layer 3 replacement package artifact materialization table.

Revision ID: 0031_layer3_replacement_package_materialization
Revises: 0030_layer3_external_local_export
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


revision = "0031_layer3_replacement_package_materialization"
down_revision = "0030_layer3_external_local_export"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_replacement_package_artifact_materialization",
        sa.Column("replacement_artifact_materialization_id", sa.String(length=36), nullable=False),
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
        sa.Column("package_supersession_preview_hash", sa.String(length=64), nullable=False),
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
        sa.Column("materialization_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("materialization_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("operator_decision", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("replacement_artifact_materialization_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_replacement_artifact_materialization_client_request",
        ),
        sa.UniqueConstraint(
            "materialization_basis_hash",
            name="uq_l3_replacement_artifact_materialization_basis_hash",
        ),
        sa.CheckConstraint(
            "operator_decision = 'materialize_replacement_package_artifacts_from_supersession_preview'",
            name="ck_l3_replacement_artifact_materialization_operator_decision",
        ),
        sa.CheckConstraint(
            "status = 'materialized'",
            name="ck_l3_replacement_artifact_materialization_status",
        ),
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_materialization_session",
        "l3_replacement_package_artifact_materialization",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_materialization_reconciliation",
        "l3_replacement_package_artifact_materialization",
        ["reconciliation_record_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_materialization_preview",
        "l3_replacement_package_artifact_materialization",
        ["package_supersession_preview_hash"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_replacement_artifact_materialization_preview",
        table_name="l3_replacement_package_artifact_materialization",
    )
    drop_index_idempotent(
        "ix_l3_replacement_artifact_materialization_reconciliation",
        table_name="l3_replacement_package_artifact_materialization",
    )
    drop_index_idempotent(
        "ix_l3_replacement_artifact_materialization_session",
        table_name="l3_replacement_package_artifact_materialization",
    )
    drop_table_idempotent("l3_replacement_package_artifact_materialization")
