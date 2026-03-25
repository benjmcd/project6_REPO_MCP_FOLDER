"""Add connector run event log table for observability endpoints."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_connector_run_events"
down_revision = "0004_connector_contract_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_run_event",
        sa.Column("connector_run_event_id", sa.String(length=36), nullable=False),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("connector_run_target_id", sa.String(length=36), sa.ForeignKey("connector_run_target.connector_run_target_id"), nullable=True),
        sa.Column("phase", sa.String(length=100), nullable=True),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("status_before", sa.String(length=50), nullable=True),
        sa.Column("status_after", sa.String(length=50), nullable=True),
        sa.Column("reason_code", sa.String(length=255), nullable=True),
        sa.Column("error_class", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("connector_run_event_id"),
    )
    op.create_index("ix_connector_run_event_run_created", "connector_run_event", ["connector_run_id", "created_at"])
    op.create_index("ix_connector_run_event_target", "connector_run_event", ["connector_run_target_id"])


def downgrade() -> None:
    op.drop_index("ix_connector_run_event_target", table_name="connector_run_event")
    op.drop_index("ix_connector_run_event_run_created", table_name="connector_run_event")
    op.drop_table("connector_run_event")
