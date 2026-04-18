"""Add Layer 3 Gate C typing-entry tables.

Revision ID: 0013_layer3_typing_entry
Revises: 0012_layer3_session_entry
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import create_table_idempotent, drop_table_idempotent


revision = "0013_layer3_typing_entry"
down_revision = "0012_layer3_session_entry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_typing_record",
        sa.Column("typing_record_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "material_snapshot_id",
            sa.String(length=36),
            sa.ForeignKey("l3_material_snapshot.material_snapshot_id"),
            nullable=False,
        ),
        sa.Column("candidate_modalities_json", sa.JSON(), nullable=False),
        sa.Column("chosen_modality", sa.String(length=64), nullable=False),
        sa.Column("typing_basis_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("overridden_by_operator", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("typing_record_id"),
        sa.UniqueConstraint("material_snapshot_id", name="uq_l3_typing_record_material_snapshot"),
    )
    create_table_idempotent(
        "l3_analysis_unit",
        sa.Column("analysis_unit_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("unit_kind", sa.String(length=64), nullable=False),
        sa.Column("analysis_modality", sa.String(length=64), nullable=False),
        sa.Column("member_snapshot_ids_json", sa.JSON(), nullable=False),
        sa.Column("member_ranges_json", sa.JSON(), nullable=False),
        sa.Column("must_remain_intact", sa.Boolean(), nullable=False),
        sa.Column("typing_record_ids_json", sa.JSON(), nullable=False),
        sa.Column("derived_view_ref", sa.String(length=1024), nullable=True),
        sa.Column("unit_hash", sa.String(length=64), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("analysis_unit_id"),
        sa.UniqueConstraint("session_id", "unit_hash", name="uq_l3_analysis_unit_session_hash"),
    )
    create_table_idempotent(
        "l3_analysis_group",
        sa.Column("analysis_group_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("analysis_modality", sa.String(length=64), nullable=False),
        sa.Column("typing_basis_json", sa.JSON(), nullable=False),
        sa.Column("analysis_unit_ids_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("analysis_group_id"),
    )
    create_table_idempotent(
        "l3_analysis_set",
        sa.Column("analysis_set_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("analysis_group_ids_json", sa.JSON(), nullable=False),
        sa.Column("analysis_unit_ids_json", sa.JSON(), nullable=False),
        sa.Column("set_type", sa.String(length=64), nullable=False),
        sa.Column("formation_basis_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("analysis_set_id"),
    )


def downgrade() -> None:
    drop_table_idempotent("l3_analysis_set")
    drop_table_idempotent("l3_analysis_group")
    drop_table_idempotent("l3_analysis_unit")
    drop_table_idempotent("l3_typing_record")
