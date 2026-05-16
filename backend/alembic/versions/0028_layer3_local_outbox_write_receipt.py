"""Add Layer 3 server-owned local outbox write receipt table.

Revision ID: 0028_layer3_local_outbox_write_receipt
Revises: 0027_layer3_local_outbox_target_receipt
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


revision = "0028_layer3_local_outbox_write_receipt"
down_revision = "0027_layer3_local_outbox_target_receipt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_server_owned_local_outbox_write_receipt",
        sa.Column("server_owned_local_outbox_write_receipt_id", sa.String(length=36), nullable=False),
        sa.Column(
            "server_owned_local_outbox_target_receipt_id",
            sa.String(length=36),
            sa.ForeignKey(
                "l3_server_owned_local_outbox_target_receipt.server_owned_local_outbox_target_receipt_id"
            ),
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
        sa.Column(
            "connector_local_destination_receipt_id",
            sa.String(length=36),
            sa.ForeignKey("l3_connector_local_destination_receipt.connector_local_destination_receipt_id"),
            nullable=False,
        ),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("connector_dispatch_record_ref", sa.String(length=255), nullable=False),
        sa.Column("external_export_download_record_ref", sa.String(length=255), nullable=False),
        sa.Column("target_identity", sa.String(length=128), nullable=False),
        sa.Column("dispatch_mode", sa.String(length=128), nullable=False),
        sa.Column("write_state", sa.String(length=64), nullable=False),
        sa.Column("outbox_artifact_ref", sa.String(length=255), nullable=False),
        sa.Column("outbox_manifest_ref", sa.String(length=255), nullable=False),
        sa.Column("outbox_artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("outbox_artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("accepted_artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("accepted_artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_by_request_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("server_owned_local_outbox_write_receipt_id"),
        sa.UniqueConstraint("client_request_id", name="uq_l3_local_outbox_write_client_request"),
        sa.UniqueConstraint("authority_basis_hash", name="uq_l3_local_outbox_write_authority_basis"),
    )
    create_index_idempotent(
        "ix_l3_local_outbox_write_session",
        "l3_server_owned_local_outbox_write_receipt",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_local_outbox_write_target_receipt",
        "l3_server_owned_local_outbox_write_receipt",
        ["server_owned_local_outbox_target_receipt_id"],
    )
    create_index_idempotent(
        "ix_l3_local_outbox_write_state",
        "l3_server_owned_local_outbox_write_receipt",
        ["write_state"],
    )


def downgrade() -> None:
    drop_index_idempotent("ix_l3_local_outbox_write_state", table_name="l3_server_owned_local_outbox_write_receipt")
    drop_index_idempotent(
        "ix_l3_local_outbox_write_target_receipt",
        table_name="l3_server_owned_local_outbox_write_receipt",
    )
    drop_index_idempotent("ix_l3_local_outbox_write_session", table_name="l3_server_owned_local_outbox_write_receipt")
    drop_table_idempotent("l3_server_owned_local_outbox_write_receipt")
