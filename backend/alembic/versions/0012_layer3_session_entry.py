"""Add Layer 3 Phase 1A session-entry tables.

Revision ID: 0012_layer3_session_entry
Revises: 0011_aps_retrieval_chunk_v1
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import create_table_idempotent, drop_table_idempotent


revision = "0012_layer3_session_entry"
down_revision = "0011_aps_retrieval_chunk_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_session",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("selection_manifest_id", sa.String(length=36), nullable=False),
        sa.Column("entry_route_context_json", sa.JSON(), nullable=False),
        sa.Column("operator_context_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )
    create_table_idempotent(
        "l3_selection_manifest",
        sa.Column("selection_manifest_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("source_plane_hints_json", sa.JSON(), nullable=False),
        sa.Column("selection_hash", sa.String(length=64), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("commit_reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("selection_manifest_id"),
        sa.UniqueConstraint("session_id", name="uq_l3_selection_manifest_session"),
    )
    create_table_idempotent(
        "l3_descriptor",
        sa.Column("descriptor_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "selection_manifest_id",
            sa.String(length=36),
            sa.ForeignKey("l3_selection_manifest.selection_manifest_id"),
            nullable=False,
        ),
        sa.Column("source_plane", sa.String(length=64), nullable=False),
        sa.Column("descriptor_type", sa.String(length=100), nullable=False),
        sa.Column("selector_payload_json", sa.JSON(), nullable=False),
        sa.Column("selection_basis_json", sa.JSON(), nullable=False),
        sa.Column("expansion_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("descriptor_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("descriptor_id"),
        sa.UniqueConstraint("session_id", "descriptor_hash", name="uq_l3_descriptor_session_hash"),
    )
    create_table_idempotent(
        "l3_retrieval_event",
        sa.Column("retrieval_event_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("descriptor_id", sa.String(length=36), sa.ForeignKey("l3_descriptor.descriptor_id"), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("material_snapshot_ids_json", sa.JSON(), nullable=False),
        sa.Column("event_payload_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("retrieval_event_id"),
    )
    create_table_idempotent(
        "l3_material_snapshot",
        sa.Column("material_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("descriptor_id", sa.String(length=36), sa.ForeignKey("l3_descriptor.descriptor_id"), nullable=False),
        sa.Column("source_plane", sa.String(length=64), nullable=False),
        sa.Column("source_shape", sa.String(length=64), nullable=False),
        sa.Column("payload_ref", sa.String(length=1024), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("source_identity_json", sa.JSON(), nullable=False),
        sa.Column("source_provenance_json", sa.JSON(), nullable=False),
        sa.Column("co_retrieval_group_id", sa.String(length=64), nullable=True),
        sa.Column("load_summary_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("material_snapshot_id"),
    )


def downgrade() -> None:
    drop_table_idempotent("l3_material_snapshot")
    drop_table_idempotent("l3_retrieval_event")
    drop_table_idempotent("l3_descriptor")
    drop_table_idempotent("l3_selection_manifest")
    drop_table_idempotent("l3_session")
