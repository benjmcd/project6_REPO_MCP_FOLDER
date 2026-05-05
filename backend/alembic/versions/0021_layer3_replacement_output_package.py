"""Add Layer 3 replacement output package namespace table.

Revision ID: 0021_layer3_replacement_output_package
Revises: 0020_layer3_replacement_package_artifact_manifest
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


revision = "0021_layer3_replacement_output_package"
down_revision = "0020_layer3_replacement_package_artifact_manifest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_replacement_output_package",
        sa.Column("replacement_output_package_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "source_output_package_id",
            sa.String(length=36),
            sa.ForeignKey("l3_output_package.output_package_id"),
            nullable=False,
        ),
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
        sa.Column("package_kind", sa.String(length=64), nullable=False),
        sa.Column("package_schema_id", sa.String(length=128), nullable=False),
        sa.Column("artifact_ref", sa.String(length=1024), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("operator_decision", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("replacement_output_package_id"),
        sa.UniqueConstraint(
            "replacement_artifact_manifest_id",
            "package_kind",
            name="uq_l3_replacement_output_package_manifest_kind",
        ),
        sa.UniqueConstraint("client_request_id", name="uq_l3_replacement_output_package_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_replacement_output_package_basis_hash"),
        sa.CheckConstraint(
            "operator_decision = 'record_replacement_package_namespace'",
            name="ck_l3_replacement_output_package_operator_decision",
        ),
        sa.CheckConstraint(
            "status = 'recorded'",
            name="ck_l3_replacement_output_package_status",
        ),
    )
    create_index_idempotent("ix_l3_replacement_output_package_session", "l3_replacement_output_package", ["session_id"])
    create_index_idempotent(
        "ix_l3_replacement_output_package_source",
        "l3_replacement_output_package",
        ["source_output_package_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_output_package_manifest",
        "l3_replacement_output_package",
        ["replacement_artifact_manifest_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_output_package_replacement_set",
        "l3_replacement_output_package",
        ["replacement_package_set_authority_id"],
    )
    create_index_idempotent(
        "ix_l3_replacement_output_package_supersession_commit",
        "l3_replacement_output_package",
        ["package_supersession_commit_id"],
    )
    create_index_idempotent("ix_l3_replacement_output_package_kind", "l3_replacement_output_package", ["package_kind"])


def downgrade() -> None:
    drop_index_idempotent("ix_l3_replacement_output_package_kind", table_name="l3_replacement_output_package")
    drop_index_idempotent(
        "ix_l3_replacement_output_package_supersession_commit",
        table_name="l3_replacement_output_package",
    )
    drop_index_idempotent(
        "ix_l3_replacement_output_package_replacement_set",
        table_name="l3_replacement_output_package",
    )
    drop_index_idempotent("ix_l3_replacement_output_package_manifest", table_name="l3_replacement_output_package")
    drop_index_idempotent("ix_l3_replacement_output_package_source", table_name="l3_replacement_output_package")
    drop_index_idempotent("ix_l3_replacement_output_package_session", table_name="l3_replacement_output_package")
    drop_table_idempotent("l3_replacement_output_package")
