"""Scope SEC XBRL packet row uniqueness by period.

Revision ID: 0043_layer3_sec_xbrl_statement_packet_row_period_unique
Revises: 0042_layer3_sec_xbrl_operator_review_decision
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import table_exists


revision = "0043_layer3_sec_xbrl_statement_packet_row_period_unique"
down_revision = "0042_layer3_sec_xbrl_operator_review_decision"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_statement_packet_row"
OLD_CONSTRAINT = "uq_l3_sec_xbrl_statement_packet_row_statement_index"
NEW_CONSTRAINT = "uq_l3_sec_xbrl_statement_packet_row_statement_period_index"
OLD_COLUMNS = ["sec_xbrl_statement_packet_statement_id", "statement_row_index"]
NEW_COLUMNS = [
    "sec_xbrl_statement_packet_statement_id",
    "period_ref",
    "period_index",
    "statement_row_index",
]


def _unique_constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    try:
        constraints = inspector.get_unique_constraints(table_name)
    except NotImplementedError:
        return False
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _drop_unique_constraint(table_name: str, constraint_name: str) -> None:
    if not _unique_constraint_exists(table_name, constraint_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="unique")


def _create_unique_constraint(table_name: str, constraint_name: str, columns: list[str]) -> None:
    if not table_exists(table_name) or _unique_constraint_exists(table_name, constraint_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_unique_constraint(constraint_name, columns)


def _old_constraint_would_conflict() -> bool:
    if not table_exists(TABLE_NAME):
        return False
    result = op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM l3_sec_xbrl_statement_packet_row
            GROUP BY sec_xbrl_statement_packet_statement_id, statement_row_index
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    )
    return result.first() is not None


def upgrade() -> None:
    _drop_unique_constraint(TABLE_NAME, OLD_CONSTRAINT)
    _create_unique_constraint(TABLE_NAME, NEW_CONSTRAINT, NEW_COLUMNS)


def downgrade() -> None:
    if _old_constraint_would_conflict():
        raise RuntimeError(
            "Cannot safely downgrade SEC XBRL packet row period uniqueness: current rows contain "
            "multiple periods for the same statement and row index. Preserve the upgraded constraint "
            "or reconcile duplicate old-key rows before recreating the old uniqueness constraint."
        )
    _drop_unique_constraint(TABLE_NAME, NEW_CONSTRAINT)
    _create_unique_constraint(TABLE_NAME, OLD_CONSTRAINT, OLD_COLUMNS)
