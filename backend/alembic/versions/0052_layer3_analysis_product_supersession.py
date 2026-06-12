"""Add supersession lifecycle state and decision values for L3 analysis product.

Revision ID: 0052_layer3_analysis_product_supersession
Revises: 0051_layer3_working_set
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from migration_compat import table_exists


revision = "0052_layer3_analysis_product_supersession"
down_revision = "0051_layer3_working_set"
branch_labels = None
depends_on = None

_PRODUCT_TABLE = "l3_analysis_product"
_DECISION_TABLE = "l3_analysis_product_review_decision"

# Constraint names
_CK_LIFECYCLE = "ck_l3_analysis_product_lifecycle"
_CK_DECISION_FROM = "ck_l3_aprod_review_decision_from_status"
_CK_DECISION_TO = "ck_l3_aprod_review_decision_to_status"
_CK_DECISION_VALUE = "ck_l3_aprod_review_decision_value"
_CK_DECISION_REASON = "ck_l3_aprod_review_decision_reason"

# Old value lists (matching 0051 state)
_OLD_LIFECYCLE_VALUES = (
    "draft",
    "proposed",
    "validated",
    "accepted",
    "rejected",
    "package_eligible",
    "packaged",
)
_OLD_DECISION_VALUES = (
    "promote",
    "accept",
    "mark_package_eligible",
    "reject",
    "revise",
)
_OLD_REASON_CODES = (
    "proposed_ready",
    "validation_passed",
    "grounded_accept",
    "package_ready",
    "insufficient_grounding",
    "evidence_gap",
    "operator_rejected",
    "revision_requested",
)

# New value lists (adds supersession values)
_NEW_LIFECYCLE_VALUES = (
    "draft",
    "proposed",
    "validated",
    "accepted",
    "rejected",
    "package_eligible",
    "packaged",
    "superseded",
)
_NEW_DECISION_VALUES = (
    "promote",
    "accept",
    "mark_package_eligible",
    "reject",
    "revise",
    "supersede",
)
_NEW_REASON_CODES = (
    "proposed_ready",
    "validation_passed",
    "grounded_accept",
    "package_ready",
    "insufficient_grounding",
    "evidence_gap",
    "operator_rejected",
    "revision_requested",
    "superseded_by_successor",
    "stale_basis",
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
    # 1. Widen ck_l3_analysis_product_lifecycle to include "superseded"
    if table_exists(_PRODUCT_TABLE):
        if _constraint_exists(_PRODUCT_TABLE, _CK_LIFECYCLE):
            with op.batch_alter_table(_PRODUCT_TABLE) as batch_op:
                batch_op.drop_constraint(_CK_LIFECYCLE, type_="check")
        with op.batch_alter_table(_PRODUCT_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _CK_LIFECYCLE,
                _in_list("lifecycle_status", _NEW_LIFECYCLE_VALUES),
            )

    # 2. Widen decision table constraints for new lifecycle + decision + reason values
    if table_exists(_DECISION_TABLE):
        for constraint_name in (_CK_DECISION_FROM, _CK_DECISION_TO):
            if _constraint_exists(_DECISION_TABLE, constraint_name):
                with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                    batch_op.drop_constraint(constraint_name, type_="check")
        for constraint_name, col, values in (
            (_CK_DECISION_FROM, "from_status", _NEW_LIFECYCLE_VALUES),
            (_CK_DECISION_TO, "to_status", _NEW_LIFECYCLE_VALUES),
        ):
            with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                batch_op.create_check_constraint(
                    constraint_name,
                    _in_list(col, values),
                )

        if _constraint_exists(_DECISION_TABLE, _CK_DECISION_VALUE):
            with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                batch_op.drop_constraint(_CK_DECISION_VALUE, type_="check")
        with op.batch_alter_table(_DECISION_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _CK_DECISION_VALUE,
                _in_list("review_decision", _NEW_DECISION_VALUES),
            )

        if _constraint_exists(_DECISION_TABLE, _CK_DECISION_REASON):
            with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                batch_op.drop_constraint(_CK_DECISION_REASON, type_="check")
        with op.batch_alter_table(_DECISION_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _CK_DECISION_REASON,
                _in_list("decision_reason_code", _NEW_REASON_CODES),
            )


def downgrade() -> None:
    # 1. Restore old lifecycle CHECK on product table
    if table_exists(_PRODUCT_TABLE):
        if _constraint_exists(_PRODUCT_TABLE, _CK_LIFECYCLE):
            with op.batch_alter_table(_PRODUCT_TABLE) as batch_op:
                batch_op.drop_constraint(_CK_LIFECYCLE, type_="check")
        with op.batch_alter_table(_PRODUCT_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _CK_LIFECYCLE,
                _in_list("lifecycle_status", _OLD_LIFECYCLE_VALUES),
            )

    # 2. Restore old decision table constraints
    if table_exists(_DECISION_TABLE):
        for constraint_name in (_CK_DECISION_FROM, _CK_DECISION_TO):
            if _constraint_exists(_DECISION_TABLE, constraint_name):
                with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                    batch_op.drop_constraint(constraint_name, type_="check")
        for constraint_name, col, values in (
            (_CK_DECISION_FROM, "from_status", _OLD_LIFECYCLE_VALUES),
            (_CK_DECISION_TO, "to_status", _OLD_LIFECYCLE_VALUES),
        ):
            with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                batch_op.create_check_constraint(
                    constraint_name,
                    _in_list(col, values),
                )

        if _constraint_exists(_DECISION_TABLE, _CK_DECISION_VALUE):
            with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                batch_op.drop_constraint(_CK_DECISION_VALUE, type_="check")
        with op.batch_alter_table(_DECISION_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _CK_DECISION_VALUE,
                _in_list("review_decision", _OLD_DECISION_VALUES),
            )

        if _constraint_exists(_DECISION_TABLE, _CK_DECISION_REASON):
            with op.batch_alter_table(_DECISION_TABLE) as batch_op:
                batch_op.drop_constraint(_CK_DECISION_REASON, type_="check")
        with op.batch_alter_table(_DECISION_TABLE) as batch_op:
            batch_op.create_check_constraint(
                _CK_DECISION_REASON,
                _in_list("decision_reason_code", _OLD_REASON_CODES),
            )
