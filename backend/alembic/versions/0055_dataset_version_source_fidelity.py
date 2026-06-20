"""Add CSV source-fidelity metadata to dataset versions.

Revision ID: 0055_dataset_version_source_fidelity
Revises: 0054_layer3_sec_xbrl_controlled_submit_pagination
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import column_exists, table_exists


revision = "0055_dataset_version_source_fidelity"
down_revision = "0054_layer3_sec_xbrl_controlled_submit_pagination"
branch_labels = None
depends_on = None


TABLE_NAME = "dataset_version"
CONTENT_HASH_COLUMN = "content_hash"
SOURCE_ROW_COUNT_COLUMN = "source_row_count"
DROPPED_ROW_COUNT_COLUMN = "dropped_row_count"


def _add_column_if_missing(column: sa.Column) -> None:
    if not table_exists(TABLE_NAME) or column_exists(TABLE_NAME, column.name):
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.add_column(column)


def _drop_column_if_present(column_name: str) -> None:
    if not table_exists(TABLE_NAME) or not column_exists(TABLE_NAME, column_name):
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.drop_column(column_name)


def upgrade() -> None:
    _add_column_if_missing(sa.Column(CONTENT_HASH_COLUMN, sa.String(length=64), nullable=True))
    _add_column_if_missing(sa.Column(SOURCE_ROW_COUNT_COLUMN, sa.Integer(), nullable=True))
    _add_column_if_missing(sa.Column(DROPPED_ROW_COUNT_COLUMN, sa.Integer(), nullable=True))


def downgrade() -> None:
    _drop_column_if_present(DROPPED_ROW_COUNT_COLUMN)
    _drop_column_if_present(SOURCE_ROW_COUNT_COLUMN)
    _drop_column_if_present(CONTENT_HASH_COLUMN)
