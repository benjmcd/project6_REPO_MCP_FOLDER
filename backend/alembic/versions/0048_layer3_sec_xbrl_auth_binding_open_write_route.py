"""Extend SEC XBRL auth binding route family check to include open_write.

Revision ID: 0048_layer3_sec_xbrl_auth_binding_open_write_route
Revises: 0047_layer3_sec_xbrl_auth_binding_route_actor_scope
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from migration_compat import table_exists


revision = "0048_layer3_sec_xbrl_auth_binding_open_write_route"
down_revision = "0047_layer3_sec_xbrl_auth_binding_route_actor_scope"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_auth_binding_receipt"
OLD_CONSTRAINT = "ck_l3_sec_xbrl_auth_binding_route_family"
OLD_VALUES = (
    "sec_xbrl_operator_review_workflow_status_read",
    "sec_xbrl_operator_review_decision_submit_write",
    "sec_xbrl_operator_review_decision_status_read",
    "sec_xbrl_value_reveal_authority_prepare_write",
    "sec_xbrl_controlled_value_reveal_submit_write",
    "sec_xbrl_controlled_value_reveal_submit_status_read",
)
NEW_VALUES = (
    "sec_xbrl_operator_review_workflow_open_write",
    *OLD_VALUES,
)


def _check_constraint_expr(values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"route_family IN ({quoted})"


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    try:
        constraints = inspector.get_check_constraints(table_name)
    except NotImplementedError:
        return False
    return any(c.get("name") == constraint_name for c in constraints)


def upgrade() -> None:
    if not table_exists(TABLE_NAME):
        return
    if _constraint_exists(TABLE_NAME, OLD_CONSTRAINT):
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.drop_constraint(OLD_CONSTRAINT, type_="check")
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.create_check_constraint(OLD_CONSTRAINT, _check_constraint_expr(NEW_VALUES))


def downgrade() -> None:
    if not table_exists(TABLE_NAME):
        return
    # Fail early if any open_write rows exist — the old constraint forbids them.
    # On PostgreSQL, creating a CHECK constraint against violating rows raises a
    # constraint violation; on SQLite, batch_alter_table rebuilds the table but
    # would silently leave the old rows against the narrower constraint.
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {TABLE_NAME}"  # noqa: S608
            " WHERE route_family = 'sec_xbrl_operator_review_workflow_open_write'"
        )
    )
    count = result.scalar()
    if count:
        raise RuntimeError(
            f"Cannot downgrade: {count} row(s) in {TABLE_NAME!r} use "
            f"route_family='sec_xbrl_operator_review_workflow_open_write', "
            f"which is not permitted by the old constraint. "
            f"Reconcile or remove those rows before downgrading."
        )
    if _constraint_exists(TABLE_NAME, OLD_CONSTRAINT):
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.drop_constraint(OLD_CONSTRAINT, type_="check")
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.create_check_constraint(OLD_CONSTRAINT, _check_constraint_expr(OLD_VALUES))
