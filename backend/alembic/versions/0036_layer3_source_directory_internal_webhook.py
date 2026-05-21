"""Add Layer 3 source-directory internal webhook receipt tables.

Revision ID: 0036_layer3_source_directory_internal_webhook
Revises: 0035_layer3_internal_webhook_connector
Create Date: 2026-05-21
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0036_layer3_source_directory_internal_webhook"
down_revision = "0035_layer3_internal_webhook_connector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_source_directory_internal_webhook_dispatch_receipt",
        sa.Column(
            "source_directory_internal_webhook_dispatch_receipt_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("l3_session.session_id"), nullable=False),
        sa.Column(
            "reconciliation_record_id",
            sa.String(length=36),
            sa.ForeignKey("l3_reconciliation_record.reconciliation_record_id"),
            nullable=False,
        ),
        sa.Column(
            "material_snapshot_id",
            sa.String(length=36),
            sa.ForeignKey("l3_material_snapshot.material_snapshot_id"),
            nullable=False,
        ),
        sa.Column("source_ingestion_batch_id", sa.String(length=128), nullable=False),
        sa.Column("source_ingestion_file_id", sa.String(length=128), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("external_export_download_record_ref", sa.String(length=255), nullable=False),
        sa.Column("export_download_descriptor_ref", sa.String(length=255), nullable=False),
        sa.Column("package_review_submit_record_ref", sa.String(length=255), nullable=False),
        sa.Column("handoff_export_prepare_ref", sa.String(length=255), nullable=False),
        sa.Column("handoff_export_envelope_ref", sa.String(length=255), nullable=False),
        sa.Column("target_identity", sa.String(length=128), nullable=False),
        sa.Column("target_class", sa.String(length=128), nullable=False),
        sa.Column("dispatch_mode", sa.String(length=128), nullable=False),
        sa.Column("redacted_destination_display_name", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("dispatch_status", sa.String(length=64), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("redacted_response_summary_json", sa.JSON(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("output_package_ids_json", sa.JSON(), nullable=False),
        sa.Column("package_kinds_json", sa.JSON(), nullable=False),
        sa.Column("payload_hashes_json", sa.JSON(), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_by_request_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_directory_internal_webhook_dispatch_receipt_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_srcdir_internal_webhook_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_srcdir_internal_webhook_authority_basis"),
        sa.UniqueConstraint("request_basis_hash", name="uq_l3_srcdir_internal_webhook_request_basis"),
    )
    create_index_idempotent(
        "ix_l3_srcdir_internal_webhook_session",
        "l3_source_directory_internal_webhook_dispatch_receipt",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_srcdir_internal_webhook_reconciliation",
        "l3_source_directory_internal_webhook_dispatch_receipt",
        ["reconciliation_record_id"],
    )
    create_index_idempotent(
        "ix_l3_srcdir_internal_webhook_status",
        "l3_source_directory_internal_webhook_dispatch_receipt",
        ["dispatch_status"],
    )
    create_table_idempotent(
        "l3_source_directory_internal_webhook_dispatch_audit_event",
        sa.Column(
            "source_directory_internal_webhook_dispatch_audit_event_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_directory_internal_webhook_dispatch_receipt_id",
            sa.String(length=36),
            sa.ForeignKey(
                "l3_source_directory_internal_webhook_dispatch_receipt."
                "source_directory_internal_webhook_dispatch_receipt_id"
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
        sa.PrimaryKeyConstraint("source_directory_internal_webhook_dispatch_audit_event_id"),
    )
    create_index_idempotent(
        "ix_l3_srcdir_internal_webhook_audit_receipt",
        "l3_source_directory_internal_webhook_dispatch_audit_event",
        ["source_directory_internal_webhook_dispatch_receipt_id"],
    )
    create_index_idempotent(
        "ix_l3_srcdir_internal_webhook_audit_type_created",
        "l3_source_directory_internal_webhook_dispatch_audit_event",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_srcdir_internal_webhook_audit_type_created",
        table_name="l3_source_directory_internal_webhook_dispatch_audit_event",
    )
    drop_index_idempotent(
        "ix_l3_srcdir_internal_webhook_audit_receipt",
        table_name="l3_source_directory_internal_webhook_dispatch_audit_event",
    )
    drop_table_idempotent("l3_source_directory_internal_webhook_dispatch_audit_event")
    drop_index_idempotent(
        "ix_l3_srcdir_internal_webhook_status",
        table_name="l3_source_directory_internal_webhook_dispatch_receipt",
    )
    drop_index_idempotent(
        "ix_l3_srcdir_internal_webhook_reconciliation",
        table_name="l3_source_directory_internal_webhook_dispatch_receipt",
    )
    drop_index_idempotent(
        "ix_l3_srcdir_internal_webhook_session",
        table_name="l3_source_directory_internal_webhook_dispatch_receipt",
    )
    drop_table_idempotent("l3_source_directory_internal_webhook_dispatch_receipt")
