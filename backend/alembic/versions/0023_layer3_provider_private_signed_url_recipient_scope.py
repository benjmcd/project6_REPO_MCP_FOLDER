"""Add provider-private signed URL receipt recipient scope.

Revision ID: 0023_layer3_provider_private_signed_url_recipient_scope
Revises: 0022_layer3_provider_private_signed_url_state
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa

from migration_compat import add_column_idempotent, drop_column_idempotent


revision = "0023_layer3_provider_private_signed_url_recipient_scope"
down_revision = "0022_layer3_provider_private_signed_url_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column_idempotent(
        "l3_provider_private_signed_url_receipt",
        sa.Column(
            "recipient_scope",
            sa.String(length=255),
            nullable=False,
            server_default="external-recipient:unspecified",
        ),
    )


def downgrade() -> None:
    drop_column_idempotent("l3_provider_private_signed_url_receipt", "recipient_scope")
