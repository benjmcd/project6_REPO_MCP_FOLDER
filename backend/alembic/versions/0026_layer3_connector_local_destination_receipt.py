"""Add Layer 3 connector local destination receipt table.

Revision ID: 0026_layer3_connector_local_destination_receipt
Revises: 0025_layer3_merge_source_intake_provider_public_url_heads
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
)


revision = "0026_layer3_connector_local_destination_receipt"
down_revision = "0025_layer3_merge_source_intake_provider_public_url_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_idempotent(
        "l3_connector_local_destination_receipt",
        sa.Column("connector_local_destination_receipt_id", sa.String(length=36), nullable=False),
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
        sa.Column("destination_target", sa.String(length=128), nullable=False),
        sa.Column("dispatch_mode", sa.String(length=128), nullable=False),
        sa.Column("receipt_state", sa.String(length=64), nullable=False),
        sa.Column("accepted_artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("accepted_artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_by_request_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("connector_local_destination_receipt_id"),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_connector_local_destination_receipt_client_request",
        ),
        sa.UniqueConstraint(
            "authority_basis_hash",
            name="uq_l3_connector_local_destination_receipt_authority_basis",
        ),
    )
    create_index_idempotent(
        "ix_l3_connector_local_destination_receipt_session",
        "l3_connector_local_destination_receipt",
        ["session_id"],
    )
    create_index_idempotent(
        "ix_l3_connector_local_destination_receipt_reconciliation",
        "l3_connector_local_destination_receipt",
        ["reconciliation_record_id"],
    )
    create_index_idempotent(
        "ix_l3_connector_local_destination_receipt_state",
        "l3_connector_local_destination_receipt",
        ["receipt_state"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_connector_local_destination_receipt_state",
        table_name="l3_connector_local_destination_receipt",
    )
    drop_index_idempotent(
        "ix_l3_connector_local_destination_receipt_reconciliation",
        table_name="l3_connector_local_destination_receipt",
    )
    drop_index_idempotent(
        "ix_l3_connector_local_destination_receipt_session",
        table_name="l3_connector_local_destination_receipt",
    )
    drop_table_idempotent("l3_connector_local_destination_receipt")
