"""Add Layer 3 local outbox provider-private handoff tables.

Revision ID: 0029_layer3_local_outbox_provider_private_handoff
Revises: 0028_layer3_local_outbox_write_receipt
Create Date: 2026-05-16
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0029_layer3_local_outbox_provider_private_handoff"
down_revision = "0028_layer3_local_outbox_write_receipt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_local_outbox_provider_private_handoff_receipt",
        sa.Column("provider_private_handoff_receipt_id", sa.String(length=36), nullable=False),
        sa.Column(
            "server_owned_local_outbox_write_receipt_id",
            sa.String(length=36),
            sa.ForeignKey(
                "l3_server_owned_local_outbox_write_receipt.server_owned_local_outbox_write_receipt_id"
            ),
            nullable=False,
        ),
        sa.Column(
            "server_owned_local_outbox_target_receipt_id",
            sa.String(length=36),
            sa.ForeignKey(
                "l3_server_owned_local_outbox_target_receipt.server_owned_local_outbox_target_receipt_id"
            ),
            nullable=False,
        ),
        sa.Column(
            "connector_local_destination_receipt_id",
            sa.String(length=36),
            sa.ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column("pass_run_id", sa.String(length=36), sa.ForeignKey("l3_pass_run.pass_run_id"), nullable=False),
        sa.Column(
            "reconciliation_record_id",
            sa.String(length=36),
            sa.ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
            nullable=False,
        ),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("connector_dispatch_record_ref", sa.String(length=255), nullable=False),
        sa.Column("external_export_download_record_ref", sa.String(length=255), nullable=False),
        sa.Column("target_identity", sa.String(length=128), nullable=False),
        sa.Column("dispatch_mode", sa.String(length=128), nullable=False),
        sa.Column("recipient_scope", sa.String(length=255), nullable=False),
        sa.Column("requested_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("handoff_state", sa.String(length=64), nullable=False),
        sa.Column("provider_private_marker", sa.String(length=128), nullable=False),
        sa.Column("provider_private_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_private_replay_policy", sa.String(length=64), nullable=False),
        sa.Column("fake_provider_object_identity_hash", sa.String(length=64), nullable=False),
        sa.Column("fake_provider_token_hash", sa.String(length=64), nullable=False),
        sa.Column("source_artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("source_artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("outbox_artifact_ref", sa.String(length=255), nullable=False),
        sa.Column("outbox_manifest_ref", sa.String(length=255), nullable=False),
        sa.Column("outbox_artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("outbox_artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("request_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_by_request_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_private_handoff_receipt_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_local_outbox_provider_private_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_local_outbox_provider_private_authority_basis"),
        sa.UniqueConstraint("request_basis_hash", name="uq_l3_local_outbox_provider_private_request_basis"),
    )
    create_index_idempotent(
        "ix_l3_local_outbox_provider_private_session",
        "l3_local_outbox_provider_private_handoff_receipt",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_local_outbox_provider_private_write_receipt",
        "l3_local_outbox_provider_private_handoff_receipt",
        ["server_owned_local_outbox_write_receipt_id"],
    )
    create_index_idempotent(
        "ix_l3_local_outbox_provider_private_state",
        "l3_local_outbox_provider_private_handoff_receipt",
        ["handoff_state"],
    )
    create_table_idempotent(
        "l3_local_outbox_provider_private_handoff_audit_event",
        sa.Column("provider_private_handoff_audit_event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "provider_private_handoff_receipt_id",
            sa.String(length=36),
            sa.ForeignKey(
                "l3_local_outbox_provider_private_handoff_receipt.provider_private_handoff_receipt_id"
            ),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_status", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("event_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_private_handoff_audit_event_id"),
    )
    create_index_idempotent(
        "ix_l3_local_outbox_provider_private_audit_receipt",
        "l3_local_outbox_provider_private_handoff_audit_event",
        ["provider_private_handoff_receipt_id"],
    )
    create_index_idempotent(
        "ix_l3_local_outbox_provider_private_audit_type_created",
        "l3_local_outbox_provider_private_handoff_audit_event",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_local_outbox_provider_private_audit_type_created",
        table_name="l3_local_outbox_provider_private_handoff_audit_event",
    )
    drop_index_idempotent(
        "ix_l3_local_outbox_provider_private_audit_receipt",
        table_name="l3_local_outbox_provider_private_handoff_audit_event",
    )
    drop_table_idempotent("l3_local_outbox_provider_private_handoff_audit_event")
    drop_index_idempotent(
        "ix_l3_local_outbox_provider_private_state",
        table_name="l3_local_outbox_provider_private_handoff_receipt",
    )
    drop_index_idempotent(
        "ix_l3_local_outbox_provider_private_write_receipt",
        table_name="l3_local_outbox_provider_private_handoff_receipt",
    )
    drop_index_idempotent(
        "ix_l3_local_outbox_provider_private_session",
        table_name="l3_local_outbox_provider_private_handoff_receipt",
    )
    drop_table_idempotent("l3_local_outbox_provider_private_handoff_receipt")
