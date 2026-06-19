"""Allow paginated SEC XBRL controlled-submit receipts per authority.

Revision ID: 0054_layer3_sec_xbrl_controlled_submit_pagination
Revises: 0053_layer3_sec_xbrl_controlled_submit_request_hash
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import table_exists


revision = "0054_layer3_sec_xbrl_controlled_submit_pagination"
down_revision = "0053_layer3_sec_xbrl_controlled_submit_request_hash"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_controlled_value_reveal_submit_receipt"
AUTHORITY_COLUMN = "sec_xbrl_value_reveal_authority_receipt_id"
AUTHORITY_UNIQUE_CONSTRAINT = "uq_l3_sec_xbrl_controlled_value_reveal_authority"


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


def _authority_constraint_would_conflict() -> bool:
    if not table_exists(TABLE_NAME):
        return False
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT 1
            FROM {TABLE_NAME}
            GROUP BY sec_xbrl_value_reveal_authority_receipt_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """  # noqa: S608
        )
    )
    return result.first() is not None


def upgrade() -> None:
    _drop_unique_constraint(TABLE_NAME, AUTHORITY_UNIQUE_CONSTRAINT)


def downgrade() -> None:
    if _authority_constraint_would_conflict():
        raise RuntimeError(
            "Cannot safely downgrade SEC XBRL controlled-submit pagination: multiple submit "
            "receipts exist for at least one value-reveal authority receipt."
        )
    _create_unique_constraint(TABLE_NAME, AUTHORITY_UNIQUE_CONSTRAINT, [AUTHORITY_COLUMN])
