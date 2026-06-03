"""Admit SEC XBRL operator review open auth binding route.

Revision ID: 0048_layer3_sec_xbrl_auth_binding_open_route_family
Revises: 0047_layer3_sec_xbrl_auth_binding_route_actor_scope
Create Date: 2026-06-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import table_exists


revision = "0048_layer3_sec_xbrl_auth_binding_open_route_family"
down_revision = "0047_layer3_sec_xbrl_auth_binding_route_actor_scope"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_auth_binding_receipt"
CONSTRAINT_NAME = "ck_l3_sec_xbrl_auth_binding_route_family"
OLD_CHECK_SQL = (
    "route_family IN ('sec_xbrl_operator_review_workflow_status_read', "
    "'sec_xbrl_operator_review_decision_submit_write', "
    "'sec_xbrl_operator_review_decision_status_read', "
    "'sec_xbrl_value_reveal_authority_prepare_write', "
    "'sec_xbrl_controlled_value_reveal_submit_write', "
    "'sec_xbrl_controlled_value_reveal_submit_status_read')"
)
NEW_CHECK_SQL = (
    "route_family IN ('sec_xbrl_operator_review_workflow_open_write', "
    "'sec_xbrl_operator_review_workflow_status_read', "
    "'sec_xbrl_operator_review_decision_submit_write', "
    "'sec_xbrl_operator_review_decision_status_read', "
    "'sec_xbrl_value_reveal_authority_prepare_write', "
    "'sec_xbrl_controlled_value_reveal_submit_write', "
    "'sec_xbrl_controlled_value_reveal_submit_status_read')"
)


def _check_constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    try:
        constraints = inspector.get_check_constraints(table_name)
    except NotImplementedError:
        return False
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _drop_check_constraint(table_name: str, constraint_name: str) -> None:
    if not _check_constraint_exists(table_name, constraint_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="check")


def _create_check_constraint(table_name: str, constraint_name: str, check_sql: str) -> None:
    if not table_exists(table_name) or _check_constraint_exists(table_name, constraint_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_check_constraint(constraint_name, check_sql)


def _open_route_rows_exist() -> bool:
    if not table_exists(TABLE_NAME):
        return False
    result = op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM l3_sec_xbrl_auth_binding_receipt
            WHERE route_family = 'sec_xbrl_operator_review_workflow_open_write'
            LIMIT 1
            """
        )
    )
    return result.first() is not None


def upgrade() -> None:
    _drop_check_constraint(TABLE_NAME, CONSTRAINT_NAME)
    _create_check_constraint(TABLE_NAME, CONSTRAINT_NAME, NEW_CHECK_SQL)


def downgrade() -> None:
    if _open_route_rows_exist():
        raise RuntimeError(
            "Cannot safely downgrade SEC XBRL auth binding route-family constraint: current rows contain "
            "operator-review open route bindings."
        )
    _drop_check_constraint(TABLE_NAME, CONSTRAINT_NAME)
    _create_check_constraint(TABLE_NAME, CONSTRAINT_NAME, OLD_CHECK_SQL)
