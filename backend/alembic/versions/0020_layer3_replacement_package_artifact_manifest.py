"""Add Layer 3 replacement package artifact manifest table.

Revision ID: 0020_layer3_replacement_package_artifact_manifest
Revises: 0019_layer3_package_supersession_commit
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


revision = "0020_layer3_replacement_package_artifact_manifest"
down_revision = "0019_layer3_package_supersession_commit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_replacement_package_artifact_manifest",
        sa.Column("replacement_package_artifact_manifest_id", sa.String(length=36), nullable=False),
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
            "replacement_package_set_authority_id",
            sa.String(length=36),
            sa.ForeignKey("l3_replacement_package_set_authority.replacement_package_set_authority_id"),
            nullable=False,
        ),
        sa.Column(
            "package_supersession_commit_id",
            sa.String(length=36),
            sa.ForeignKey("l3_package_supersession_commit.package_supersession_commit_id"),
            nullable=False,
        ),
        sa.Column("replacement_authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("package_supersession_commit_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("replacement_package_set_id", sa.String(length=128), nullable=False),
        sa.Column("replacement_package_set_hash", sa.String(length=64), nullable=False),
        sa.Column("replacement_package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("replacement_payload_refs_json", sa.JSON(), nullable=False),
        sa.Column("replacement_payload_hashes_json", sa.JSON(), nullable=False),
        sa.Column("verified_artifact_refs_json", sa.JSON(), nullable=False),
        sa.Column("verified_artifact_hashes_json", sa.JSON(), nullable=False),
        sa.Column("verified_artifact_byte_sizes_json", sa.JSON(), nullable=False),
        sa.Column("hash_algorithm", sa.String(length=32), nullable=False),
        sa.Column("artifact_namespace", sa.String(length=128), nullable=False),
        sa.Column("artifact_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("manifest_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("operator_decision", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("replacement_package_artifact_manifest_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_replacement_artifact_manifest_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_replacement_artifact_manifest_basis_hash"),
        sa.CheckConstraint(
            "operator_decision = 'record_replacement_package_artifact_manifest'",
            name="ck_l3_replacement_artifact_manifest_operator_decision",
        ),
        sa.CheckConstraint(
            "status = 'verified'",
            name="ck_l3_replacement_artifact_manifest_status",
        ),
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_manifest_session",
        "l3_replacement_package_artifact_manifest",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_manifest_reconciliation",
        "l3_replacement_package_artifact_manifest",
        ["reconciliation_record_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_manifest_replacement_authority",
        "l3_replacement_package_artifact_manifest",
        ["replacement_package_set_authority_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_artifact_manifest_supersession_commit",
        "l3_replacement_package_artifact_manifest",
        ["package_supersession_commit_id"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_replacement_artifact_manifest_supersession_commit",
        table_name="l3_replacement_package_artifact_manifest",
    )
    drop_index_idempotent(
        "ix_l3_replacement_artifact_manifest_replacement_authority",
        table_name="l3_replacement_package_artifact_manifest",
    )
    drop_index_idempotent(
        "ix_l3_replacement_artifact_manifest_reconciliation",
        table_name="l3_replacement_package_artifact_manifest",
    )
    drop_index_idempotent(
        "ix_l3_replacement_artifact_manifest_session",
        table_name="l3_replacement_package_artifact_manifest",
    )
    drop_table_idempotent("l3_replacement_package_artifact_manifest")
