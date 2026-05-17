"""Add Layer 3 package replacement activation table.

Revision ID: 0032_layer3_package_replacement_activation
Revises: 0031_layer3_replacement_package_materialization
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


revision = "0032_layer3_package_replacement_activation"
down_revision = "0031_layer3_replacement_package_materialization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_package_replacement_activation",
        sa.Column("package_replacement_activation_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "replacement_artifact_manifest_id",
            sa.String(length=36),
            sa.ForeignKey("l3_replacement_package_artifact_manifest.replacement_package_artifact_manifest_id"),
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
        sa.Column("replacement_output_package_ids_json", sa.JSON(), nullable=False),
        sa.Column("source_output_package_ids_json", sa.JSON(), nullable=False),
        sa.Column("package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("active_artifact_refs_json", sa.JSON(), nullable=False),
        sa.Column("active_artifact_hashes_json", sa.JSON(), nullable=False),
        sa.Column("replacement_activation_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("activation_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("operator_decision", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("package_replacement_activation_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_package_replacement_activation_client_request"),
        sa.UniqueConstraint(
            "replacement_activation_basis_hash",
            name="uq_l3_package_replacement_activation_basis_hash",
        ),
        sa.UniqueConstraint("session_id", name="uq_l3_package_replacement_activation_session"),
        sa.CheckConstraint(
            "operator_decision = 'activate_replacement_output_package_namespace'",
            name="ck_l3_package_replacement_activation_operator_decision",
        ),
        sa.CheckConstraint("status = 'activated'", name="ck_l3_package_replacement_activation_status"),
    )
    create_index_idempotent(
        "ix_l3_package_replacement_activation_manifest",
        "l3_package_replacement_activation",
        ["replacement_artifact_manifest_id"],
    )
    create_index_idempotent(
        "ix_l3_package_replacement_activation_replacement_set",
        "l3_package_replacement_activation",
        ["replacement_package_set_authority_id"],
    )
    create_index_idempotent(
        "ix_l3_package_replacement_activation_supersession_commit",
        "l3_package_replacement_activation",
        ["package_supersession_commit_id"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_package_replacement_activation_supersession_commit",
        table_name="l3_package_replacement_activation",
    )
    drop_index_idempotent(
        "ix_l3_package_replacement_activation_replacement_set",
        table_name="l3_package_replacement_activation",
    )
    drop_index_idempotent(
        "ix_l3_package_replacement_activation_manifest",
        table_name="l3_package_replacement_activation",
    )
    drop_table_idempotent("l3_package_replacement_activation")
