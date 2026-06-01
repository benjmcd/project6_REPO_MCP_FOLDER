"""Constrain SEC XBRL persisted row redaction flags.

Revision ID: 0041_layer3_sec_xbrl_redaction_constraints
Revises: 0040_layer3_sec_xbrl_operator_review_workflow
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import table_exists


revision = "0041_layer3_sec_xbrl_redaction_constraints"
down_revision = "0040_layer3_sec_xbrl_operator_review_workflow"
branch_labels = None
depends_on = None


CONSTRAINTS = (
    (
        "l3_sec_xbrl_projection_fact",
        "ck_l3_sec_xbrl_projection_fact_value_redacted",
    ),
    (
        "l3_sec_xbrl_statement_packet_row",
        "ck_l3_sec_xbrl_statement_packet_row_value_redacted",
    ),
)
CHECK_SQL = "value_redacted = true"


def _check_constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    try:
        constraints = inspector.get_check_constraints(table_name)
    except NotImplementedError:
        return False
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _create_check_constraint(table_name: str, constraint_name: str) -> None:
    if not table_exists(table_name) or _check_constraint_exists(table_name, constraint_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_check_constraint(constraint_name, CHECK_SQL)


def _drop_check_constraint(table_name: str, constraint_name: str) -> None:
    if not _check_constraint_exists(table_name, constraint_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="check")


def upgrade() -> None:
    for table_name, constraint_name in CONSTRAINTS:
        _create_check_constraint(table_name, constraint_name)


def downgrade() -> None:
    for table_name, constraint_name in reversed(CONSTRAINTS):
        _drop_check_constraint(table_name, constraint_name)
