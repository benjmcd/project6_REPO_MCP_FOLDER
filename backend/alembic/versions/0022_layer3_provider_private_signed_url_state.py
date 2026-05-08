"""Add Layer 3 provider-private signed URL durable state tables.

Revision ID: 0022_layer3_provider_private_signed_url_state
Revises: 0021_layer3_replacement_output_package
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0022_layer3_provider_private_signed_url_state"
down_revision = "0021_layer3_replacement_output_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_provider_private_signed_url_object_authority",
        sa.Column("provider_private_signed_url_object_authority_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "reconciliation_record_id",
            sa.String(length=36),
            sa.ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
            nullable=False,
        ),
        sa.Column("external_export_download_record_ref", sa.String(length=255), nullable=False),
        sa.Column("export_download_descriptor_ref", sa.String(length=255), nullable=False),
        sa.Column("source_artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("source_artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("authority_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("provider_object_identity_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_private_signed_url_object_authority_id"),
        sa.UniqueConstraint("authority_hash", name="uq_l3_provider_private_signed_url_authority_hash"),
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_authority_session",
        "l3_provider_private_signed_url_object_authority",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_authority_reconciliation",
        "l3_provider_private_signed_url_object_authority",
        ["reconciliation_record_id"],
    )

    create_table_idempotent(
        "l3_provider_private_signed_url_receipt",
        sa.Column("provider_private_signed_url_receipt_id", sa.String(length=36), nullable=False),
        sa.Column(
            "provider_private_signed_url_object_authority_id",
            sa.String(length=36),
            sa.ForeignKey(
                "l3_provider_private_signed_url_object_authority.provider_private_signed_url_object_authority_id"
            ),
            nullable=False,
        ),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("provider_private_signed_url_state", sa.String(length=64), nullable=False),
        sa.Column("provider_private_signed_url_replay_policy", sa.String(length=32), nullable=False),
        sa.Column("provider_private_signed_url_max_use_count", sa.Integer(), nullable=False),
        sa.Column("provider_private_signed_url_use_count", sa.Integer(), nullable=False),
        sa.Column("provider_private_signed_url_token_hash", sa.String(length=64), nullable=False),
        sa.Column("provider_private_signed_url_token_prefix", sa.String(length=16), nullable=False),
        sa.Column("provider_private_signed_url_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authority_hash", sa.String(length=64), nullable=False),
        sa.Column("request_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_request_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("provider_private_signed_url_receipt_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_provider_private_signed_url_receipt_client_request",
        ),
        sa.UniqueConstraint(
            "request_basis_hash",
            name="uq_l3_provider_private_signed_url_receipt_request_basis",
        ),
        sa.UniqueConstraint(
            "provider_private_signed_url_token_hash",
            name="uq_l3_provider_private_signed_url_token_hash",
        ),
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_receipt_authority",
        "l3_provider_private_signed_url_receipt",
        ["provider_private_signed_url_object_authority_id"],
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_receipt_state_expiry",
        "l3_provider_private_signed_url_receipt",
        ["provider_private_signed_url_state", "provider_private_signed_url_expires_at"],
    )

    create_table_idempotent(
        "l3_provider_private_signed_url_revocation",
        sa.Column("provider_private_signed_url_revocation_id", sa.String(length=36), nullable=False),
        sa.Column(
            "provider_private_signed_url_receipt_id",
            sa.String(length=36),
            sa.ForeignKey("l3_provider_private_signed_url_receipt.provider_private_signed_url_receipt_id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("revoked_by", sa.String(length=255), nullable=False),
        sa.Column("revocation_reason_hash", sa.String(length=64), nullable=False),
        sa.Column("revocation_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_private_signed_url_revocation_id"),
        sa.UniqueConstraint(
            "provider_private_signed_url_receipt_id",
            "idempotency_key",
            name="uq_l3_provider_private_signed_url_revoke_receipt_key",
        ),
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_revoke_receipt",
        "l3_provider_private_signed_url_revocation",
        ["provider_private_signed_url_receipt_id"],
    )

    create_table_idempotent(
        "l3_provider_private_signed_url_audit_event",
        sa.Column("provider_private_signed_url_audit_event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "provider_private_signed_url_receipt_id",
            sa.String(length=36),
            sa.ForeignKey("l3_provider_private_signed_url_receipt.provider_private_signed_url_receipt_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_status", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("authority_hash", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("event_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_private_signed_url_audit_event_id"),
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_audit_receipt",
        "l3_provider_private_signed_url_audit_event",
        ["provider_private_signed_url_receipt_id"],
    )
    create_index_idempotent(
        "ix_l3_provider_private_signed_url_audit_type_created",
        "l3_provider_private_signed_url_audit_event",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_audit_type_created",
        table_name="l3_provider_private_signed_url_audit_event",
    )
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_audit_receipt",
        table_name="l3_provider_private_signed_url_audit_event",
    )
    drop_table_idempotent("l3_provider_private_signed_url_audit_event")
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_revoke_receipt",
        table_name="l3_provider_private_signed_url_revocation",
    )
    drop_table_idempotent("l3_provider_private_signed_url_revocation")
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_receipt_state_expiry",
        table_name="l3_provider_private_signed_url_receipt",
    )
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_receipt_authority",
        table_name="l3_provider_private_signed_url_receipt",
    )
    drop_table_idempotent("l3_provider_private_signed_url_receipt")
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_authority_reconciliation",
        table_name="l3_provider_private_signed_url_object_authority",
    )
    drop_index_idempotent(
        "ix_l3_provider_private_signed_url_authority_session",
        table_name="l3_provider_private_signed_url_object_authority",
    )
    drop_table_idempotent("l3_provider_private_signed_url_object_authority")
