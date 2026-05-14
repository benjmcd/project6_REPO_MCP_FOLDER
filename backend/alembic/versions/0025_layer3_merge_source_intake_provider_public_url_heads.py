"""Merge Layer 3 source-intake and provider-public URL heads.

Revision ID: 0025_layer3_merge_source_intake_provider_public_url_heads
Revises: 0024_layer3_source_intake_record, 0024_layer3_provider_public_url_state
Create Date: 2026-05-14
"""

from __future__ import annotations


revision = "0025_layer3_merge_source_intake_provider_public_url_heads"
down_revision = (
    "0024_layer3_source_intake_record",
    "0024_layer3_provider_public_url_state",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
