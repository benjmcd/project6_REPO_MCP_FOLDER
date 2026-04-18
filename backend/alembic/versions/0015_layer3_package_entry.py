"""Add Layer 3 Gate D package-entry tables.

Revision ID: 0015_layer3_package_entry
Revises: 0014_layer3_pass_entry
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import create_table_idempotent, drop_table_idempotent


revision = "0015_layer3_package_entry"
down_revision = "0014_layer3_pass_entry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_reconciliation_record",
        sa.Column("reconciliation_record_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("reconciliation_record_id"),
        sa.UniqueConstraint("session_id", name="uq_l3_reconciliation_record_session"),
    )
    create_table_idempotent(
        "l3_output_package",
        sa.Column("output_package_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "reconciliation_record_id",
            sa.String(length=36),
            sa.ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
            nullable=False,
        ),
        sa.Column("package_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("payload_ref", sa.String(length=1024), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("output_package_id"),
        sa.UniqueConstraint("session_id", "package_kind", name="uq_l3_output_package_session_kind"),
    )


def downgrade() -> None:
    drop_table_idempotent("l3_output_package")
    drop_table_idempotent("l3_reconciliation_record")
