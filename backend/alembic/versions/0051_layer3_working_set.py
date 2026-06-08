"""Add Layer 3 working set table and widen evidence ref_kind CHECK.

Revision ID: 0051_layer3_working_set
Revises: 0050_layer3_analysis_product_review_decision
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from migration_compat import (
    create_index_idempotent,
    create_table_idempotent,
    drop_index_idempotent,
    drop_table_idempotent,
    table_exists,
)


revision = "0051_layer3_working_set"
down_revision = "0050_layer3_analysis_product_review_decision"
branch_labels = None
depends_on = None

_EVLINK_TABLE = "l3_analysis_product_evidence_link"
_EVLINK_CONSTRAINT = "ck_l3_aprod_evlink_ref_kind"

_OLD_REF_KIND_VALUES = (
    "material_snapshot",
    "pass_run",
    "output_package",
    "analysis_set",
    "prior_product",
)
_NEW_REF_KIND_VALUES = (
    "material_snapshot",
    "pass_run",
    "output_package",
    "analysis_set",
    "prior_product",
    "working_set",
)


def _in_list(col: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{col} IN ({quoted})"


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
    # 1. Create l3_working_set table
    create_table_idempotent(
        "l3_working_set",
        sa.Column("working_set_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("member_refs_json", sa.JSON(), nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("basis_hash", sa.String(length=64), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("working_set_id"),
        sa.ForeignKeyConstraint(["session_id"], ["l3_session.session_id"]),
        sa.UniqueConstraint(
            "session_id", "client_request_id", name="uq_l3_working_set_session_request"
        ),
    )
    create_index_idempotent(
        "ix_l3_working_set_session",
        "l3_working_set",
        ["session_id"],
    )

    # 2. Widen the ck_l3_aprod_evlink_ref_kind CHECK to include "working_set"
    if table_exists(_EVLINK_TABLE):
        if _constraint_exists(_EVLINK_TABLE, _EVLINK_CONSTRAINT):
            with op.batch_alter_table(_EVLINK_TABLE) as batch_op:
                batch_op.drop_constraint(_EVLINK_CONSTRAINT, type_="check")
        with op.batch_alter_table(_EVLINK_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _EVLINK_CONSTRAINT,
                _in_list("ref_kind", _NEW_REF_KIND_VALUES),
            )


def downgrade() -> None:
    # 1. Restore the OLD ref_kind CHECK (without "working_set")
    if table_exists(_EVLINK_TABLE):
        if _constraint_exists(_EVLINK_TABLE, _EVLINK_CONSTRAINT):
            with op.batch_alter_table(_EVLINK_TABLE) as batch_op:
                batch_op.drop_constraint(_EVLINK_CONSTRAINT, type_="check")
        with op.batch_alter_table(_EVLINK_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _EVLINK_CONSTRAINT,
                _in_list("ref_kind", _OLD_REF_KIND_VALUES),
            )

    # 2. Drop l3_working_set (reverse order)
    drop_index_idempotent("ix_l3_working_set_session", "l3_working_set")
    drop_table_idempotent("l3_working_set")
