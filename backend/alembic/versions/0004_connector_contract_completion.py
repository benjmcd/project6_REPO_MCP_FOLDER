"""Add v1.3.2 connector contract completion schema updates."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_connector_contract_completion"
down_revision = "0002_connector_subsystem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("connector_run", sa.Column("effective_search_params_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("connector_run", sa.Column("effective_filters_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("connector_run", sa.Column("effective_sort", sa.String(length=100), nullable=True))
    op.add_column("connector_run", sa.Column("effective_order", sa.String(length=20), nullable=True))
    op.add_column("connector_run", sa.Column("effective_page_size", sa.Integer(), nullable=True))
    op.add_column("connector_run", sa.Column("search_exhaustion_reason", sa.String(length=100), nullable=True))
    op.add_column("connector_run", sa.Column("page_count_completed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("partition_count_completed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("next_page_available", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("connector_run", sa.Column("last_offset_committed", sa.Integer(), nullable=True))
    op.add_column("connector_run", sa.Column("deduped_within_run_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("not_modified_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("reconciliation_only_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("budget_blocked_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("policy_skipped_count_by_reason_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("connector_run", sa.Column("consumed_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("connector_run", sa.Column("budget_exhausted", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.add_column("connector_run_target", sa.Column("selection_source", sa.String(length=50), nullable=True))
    op.add_column("connector_run_target", sa.Column("selection_scope", sa.String(length=50), nullable=True))
    op.add_column("connector_run_target", sa.Column("selection_match_basis", sa.String(length=100), nullable=True))
    op.add_column("connector_run_target", sa.Column("permission_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("connector_run_target", sa.Column("access_level_summary", sa.String(length=100), nullable=True))
    op.add_column("connector_run_target", sa.Column("public_read_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.create_index("ix_connector_run_target_run_status", "connector_run_target", ["connector_run_id", "status"])

    op.create_table(
        "connector_run_partition_cursor",
        sa.Column("connector_run_partition_cursor_id", sa.String(length=36), nullable=False),
        sa.Column("connector_run_id", sa.String(length=36), sa.ForeignKey("connector_run.connector_run_id"), nullable=False),
        sa.Column("partition_id", sa.String(length=255), nullable=False),
        sa.Column("partition_type", sa.String(length=100), nullable=False),
        sa.Column("partition_bounds_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_offset", sa.Integer(), nullable=True),
        sa.Column("last_item_sort_key", sa.String(length=255), nullable=True),
        sa.Column("last_page_link", sa.String(length=1024), nullable=True),
        sa.Column("partition_exhausted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("connector_run_partition_cursor_id"),
        sa.UniqueConstraint("connector_run_id", "partition_id", name="uq_run_partition_cursor"),
    )
    op.create_index("ix_connector_run_partition_cursor_run_partition", "connector_run_partition_cursor", ["connector_run_id", "partition_id"])


def downgrade() -> None:
    op.drop_index("ix_connector_run_partition_cursor_run_partition", table_name="connector_run_partition_cursor")
    op.drop_table("connector_run_partition_cursor")
    op.drop_index("ix_connector_run_target_run_status", table_name="connector_run_target")

    op.drop_column("connector_run_target", "public_read_confirmed")
    op.drop_column("connector_run_target", "access_level_summary")
    op.drop_column("connector_run_target", "permission_snapshot_json")
    op.drop_column("connector_run_target", "selection_match_basis")
    op.drop_column("connector_run_target", "selection_scope")
    op.drop_column("connector_run_target", "selection_source")

    op.drop_column("connector_run", "budget_exhausted")
    op.drop_column("connector_run", "consumed_bytes")
    op.drop_column("connector_run", "policy_skipped_count_by_reason_json")
    op.drop_column("connector_run", "budget_blocked_count")
    op.drop_column("connector_run", "reconciliation_only_count")
    op.drop_column("connector_run", "not_modified_count")
    op.drop_column("connector_run", "deduped_within_run_count")
    op.drop_column("connector_run", "last_offset_committed")
    op.drop_column("connector_run", "next_page_available")
    op.drop_column("connector_run", "partition_count_completed")
    op.drop_column("connector_run", "page_count_completed")
    op.drop_column("connector_run", "search_exhaustion_reason")
    op.drop_column("connector_run", "effective_page_size")
    op.drop_column("connector_run", "effective_order")
    op.drop_column("connector_run", "effective_sort")
    op.drop_column("connector_run", "effective_filters_json")
    op.drop_column("connector_run", "effective_search_params_json")
