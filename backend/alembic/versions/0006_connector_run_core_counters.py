"""Add persisted core target counters on connector_run.

Revision ID: 0006_connector_run_core_counters
Revises: 0005_connector_run_events
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_connector_run_core_counters"
down_revision = "0005_connector_run_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("connector_run", sa.Column("retryable_target_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("terminal_target_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("nonterminal_target_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("connector_run", "nonterminal_target_count")
    op.drop_column("connector_run", "terminal_target_count")
    op.drop_column("connector_run", "retryable_target_count")
