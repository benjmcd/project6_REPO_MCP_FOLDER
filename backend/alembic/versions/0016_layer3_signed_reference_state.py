"""Add Layer 3 signed-reference durable state tables.

Revision ID: 0016_layer3_signed_reference_state
Revises: 0015_layer3_package_entry
Create Date: 2026-05-03
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0016_layer3_signed_reference_state"
down_revision = "0015_layer3_package_entry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_signed_reference_token",
        sa.Column("signed_reference_token_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "reconciliation_record_id",
            sa.String(length=36),
            sa.ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("replay_policy", sa.String(length=32), nullable=False),
        sa.Column("max_use_count", sa.Integer(), nullable=False),
        sa.Column("use_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authority_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("request_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_request_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("signed_reference_token_id"),
        sa.UniqueConstraint("token_hash", name="uq_l3_signed_reference_token_hash"),
        sa.UniqueConstraint("request_basis_hash", name="uq_l3_signed_reference_request_basis"),
    )
    create_index_idempotent("ix_l3_signed_reference_token_session", "l3_signed_reference_token", ["session_id"])
    create_index_idempotent(
        "ix_l3_signed_reference_token_reconciliation",
        "l3_signed_reference_token",
        ["reconciliation_record_id"],
    )
    create_index_idempotent(
        "ix_l3_signed_reference_token_state_expiry",
        "l3_signed_reference_token",
        ["state", "expires_at"],
    )

    create_table_idempotent(
        "l3_signed_reference_receipt",
        sa.Column("signed_reference_receipt_id", sa.String(length=36), nullable=False),
        sa.Column(
            "signed_reference_token_id",
            sa.String(length=36),
            sa.ForeignKey("l3_signed_reference_token.signed_reference_token_id"),
            nullable=False,
        ),
        sa.Column("receipt_type", sa.String(length=32), nullable=False),
        sa.Column("receipt_status", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("authority_hash", sa.String(length=64), nullable=False),
        sa.Column("artifact_ref", sa.String(length=1024), nullable=True),
        sa.Column("artifact_hash", sa.String(length=64), nullable=True),
        sa.Column("artifact_size_bytes", sa.Integer(), nullable=True),
        sa.Column("receipt_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("signed_reference_receipt_id"),
    )
    create_index_idempotent(
        "ix_l3_signed_reference_receipt_token",
        "l3_signed_reference_receipt",
        ["signed_reference_token_id"],
    )

    create_table_idempotent(
        "l3_signed_reference_revocation",
        sa.Column("signed_reference_revocation_id", sa.String(length=36), nullable=False),
        sa.Column(
            "signed_reference_token_id",
            sa.String(length=36),
            sa.ForeignKey("l3_signed_reference_token.signed_reference_token_id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("revoked_by", sa.String(length=255), nullable=False),
        sa.Column("revocation_reason", sa.String(length=128), nullable=False),
        sa.Column("revocation_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("signed_reference_revocation_id"),
        sa.UniqueConstraint(
            "signed_reference_token_id",
            "idempotency_key",
            name="uq_l3_signed_reference_revoke_token_key",
        ),
    )
    create_index_idempotent(
        "ix_l3_signed_reference_revocation_token",
        "l3_signed_reference_revocation",
        ["signed_reference_token_id"],
    )

    create_table_idempotent(
        "l3_signed_reference_audit_event",
        sa.Column("signed_reference_audit_event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "signed_reference_token_id",
            sa.String(length=36),
            sa.ForeignKey("l3_signed_reference_token.signed_reference_token_id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_status", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("authority_hash", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("event_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("signed_reference_audit_event_id"),
    )
    create_index_idempotent(
        "ix_l3_signed_reference_audit_token",
        "l3_signed_reference_audit_event",
        ["signed_reference_token_id"],
    )
    create_index_idempotent(
        "ix_l3_signed_reference_audit_type_created",
        "l3_signed_reference_audit_event",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    drop_index_idempotent("ix_l3_signed_reference_audit_type_created", table_name="l3_signed_reference_audit_event")
    drop_index_idempotent("ix_l3_signed_reference_audit_token", table_name="l3_signed_reference_audit_event")
    drop_table_idempotent("l3_signed_reference_audit_event")
    drop_index_idempotent("ix_l3_signed_reference_revocation_token", table_name="l3_signed_reference_revocation")
    drop_table_idempotent("l3_signed_reference_revocation")
    drop_index_idempotent("ix_l3_signed_reference_receipt_token", table_name="l3_signed_reference_receipt")
    drop_table_idempotent("l3_signed_reference_receipt")
    drop_index_idempotent("ix_l3_signed_reference_token_state_expiry", table_name="l3_signed_reference_token")
    drop_index_idempotent("ix_l3_signed_reference_token_reconciliation", table_name="l3_signed_reference_token")
    drop_index_idempotent("ix_l3_signed_reference_token_session", table_name="l3_signed_reference_token")
    drop_table_idempotent("l3_signed_reference_token")
