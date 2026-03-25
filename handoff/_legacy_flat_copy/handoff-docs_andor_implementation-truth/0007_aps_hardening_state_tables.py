"""Add APS capability and sync cursor state tables.

Revision ID: 0007_aps_hardening_state_tables
Revises: 0006_connector_run_core_counters
Create Date: 2026-03-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_aps_hardening_state_tables"
down_revision = "0006_connector_run_core_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aps_dialect_capability",
        sa.Column("aps_dialect_capability_id", sa.String(length=36), nullable=False),
        sa.Column("subscription_key_hash", sa.String(length=64), nullable=False),
        sa.Column("api_host", sa.String(length=255), nullable=False),
        sa.Column("dialect", sa.String(length=64), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_status", sa.Integer(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_envelope_keys_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("observed_count_keys_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("observed_page_cap", sa.Integer(), nullable=True),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("aps_dialect_capability_id"),
        sa.UniqueConstraint("subscription_key_hash", "api_host", "dialect", name="uq_aps_capability_key_host_dialect"),
    )
    op.create_index("ix_aps_capability_key_host", "aps_dialect_capability", ["subscription_key_hash", "api_host"])
    op.create_index("ix_aps_capability_cooldown", "aps_dialect_capability", ["cooldown_until"])

    op.create_table(
        "aps_sync_cursor",
        sa.Column("aps_sync_cursor_id", sa.String(length=36), nullable=False),
        sa.Column("source_system", sa.String(length=100), nullable=False),
        sa.Column("logical_query_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("watermark_field", sa.String(length=100), nullable=False, server_default="DateAddedTimestamp"),
        sa.Column("last_watermark_iso", sa.String(length=64), nullable=True),
        sa.Column("overlap_seconds", sa.Integer(), nullable=False, server_default="259200"),
        sa.Column("last_run_connector_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=True),
        sa.Column("last_run_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reconciliation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciliation_window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("aps_sync_cursor_id"),
        sa.UniqueConstraint("source_system", "logical_query_fingerprint", name="uq_aps_sync_cursor_query"),
    )
    op.create_index("ix_aps_sync_cursor_source_query", "aps_sync_cursor", ["source_system", "logical_query_fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_aps_sync_cursor_source_query", table_name="aps_sync_cursor")
    op.drop_table("aps_sync_cursor")
    op.drop_index("ix_aps_capability_cooldown", table_name="aps_dialect_capability")
    op.drop_index("ix_aps_capability_key_host", table_name="aps_dialect_capability")
    op.drop_table("aps_dialect_capability")
