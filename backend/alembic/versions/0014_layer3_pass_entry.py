"""Add Layer 3 Gate C pass-entry tables.

Revision ID: 0014_layer3_pass_entry
Revises: 0013_layer3_typing_entry
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import create_table_idempotent, drop_table_idempotent


revision = "0014_layer3_pass_entry"
down_revision = "0013_layer3_typing_entry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_analysis_plan",
        sa.Column("analysis_plan_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("analysis_set_ids_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("approved_by_operator", sa.Boolean(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("analysis_plan_id"),
    )
    create_table_idempotent(
        "l3_pass_run",
        sa.Column("pass_run_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "analysis_plan_id",
            sa.String(length=36),
            sa.ForeignKey("l3_analysis_plan.analysis_plan_id"),
            nullable=False,
        ),
        sa.Column(
            "analysis_set_id",
            sa.String(length=36),
            sa.ForeignKey("l3_analysis_set.analysis_set_id"),
            nullable=False,
        ),
        sa.Column("pass_type", sa.String(length=64), nullable=False),
        sa.Column("engine_family", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_payload_ref", sa.String(length=1024), nullable=False),
        sa.Column("output_payload_ref", sa.String(length=1024), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("pass_run_id"),
    )


def downgrade() -> None:
    drop_table_idempotent("l3_pass_run")
    drop_table_idempotent("l3_analysis_plan")
