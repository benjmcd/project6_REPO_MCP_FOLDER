"""Add Layer 3 Gate B idempotency claim table.

Revision ID: 0017_layer3_gate_b_idempotency
Revises: 0016_layer3_signed_reference_state
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


revision = "0017_layer3_gate_b_idempotency"
down_revision = "0016_layer3_signed_reference_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_gate_b_idempotency_key",
        sa.Column("gate_b_idempotency_key_id", sa.String(length=36), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("request_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("preflight_id", sa.String(length=64), nullable=False),
        sa.Column("source_set_id", sa.String(length=64), nullable=False),
        sa.Column("material_preview_id", sa.String(length=64), nullable=False),
        sa.Column("material_preview_hash", sa.String(length=64), nullable=False),
        sa.Column("gate_b_decision_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=True),
        sa.Column(
            "selection_manifest_id",
            sa.String(length=36),
            sa.ForeignKey("l3_selection_manifest.selection_manifest_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("gate_b_idempotency_key_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_gate_b_idempotency_client_request"),
        sa.CheckConstraint("status IN ('claimed', 'committed')", name="ck_l3_gate_b_idempotency_status"),
    )
    create_index_idempotent("ix_l3_gate_b_idempotency_session", "l3_gate_b_idempotency_key", ["session_id"])
    create_index_idempotent("ix_l3_gate_b_idempotency_status", "l3_gate_b_idempotency_key", ["status"])


def downgrade() -> None:
    drop_index_idempotent("ix_l3_gate_b_idempotency_status", table_name="l3_gate_b_idempotency_key")
    drop_index_idempotent("ix_l3_gate_b_idempotency_session", table_name="l3_gate_b_idempotency_key")
    drop_table_idempotent("l3_gate_b_idempotency_key")
