"""Scope SEC XBRL auth binding uniqueness by route and actor.

Revision ID: 0047_layer3_sec_xbrl_auth_binding_route_actor_scope
Revises: 0046_layer3_sec_xbrl_auth_binding_receipt
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from migration_compat import table_exists


revision = "0047_layer3_sec_xbrl_auth_binding_route_actor_scope"
down_revision = "0046_layer3_sec_xbrl_auth_binding_receipt"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_auth_binding_receipt"
OLD_CONSTRAINT = "uq_l3_sec_xbrl_auth_binding_source_receipt"
NEW_CONSTRAINT = "uq_l3_sec_xbrl_auth_binding_source_route_actor_role"
OLD_COLUMNS = ["source_receipt_kind", "source_receipt_id"]
NEW_COLUMNS = [
    "source_receipt_kind",
    "source_receipt_id",
    "route_family",
    "actor_ref_hash",
    "workspace_ref_hash",
    "role",
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
            FROM l3_sec_xbrl_auth_binding_receipt
            GROUP BY source_receipt_kind, source_receipt_id
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
            "Cannot safely downgrade SEC XBRL auth binding route/actor uniqueness: current rows contain "
            "multiple route, actor, workspace, or role bindings for the same source receipt. Preserve the "
            "upgraded constraint or reconcile duplicate old-key rows before recreating the old source-only "
            "uniqueness constraint."
        )
    _drop_unique_constraint(TABLE_NAME, NEW_CONSTRAINT)
    _create_unique_constraint(TABLE_NAME, OLD_CONSTRAINT, OLD_COLUMNS)
