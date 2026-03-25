"""Add visual_page_refs_json column to aps_content_document.

Revision ID: 0010_visual_page_refs_json
Revises: 0009_aps_document_processing_metadata
Create Date: 2026-03-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_visual_page_refs_json"
down_revision = "0009_aps_document_processing_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("aps_content_document", sa.Column("visual_page_refs_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("aps_content_document", "visual_page_refs_json")
