"""Add Layer 3 analysis product review decision table (append-only audit trail).

Revision ID: 0050_layer3_analysis_product_review_decision
Revises: 0049_layer3_analysis_product_authoring
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
)


revision = "0050_layer3_analysis_product_review_decision"
down_revision = "0049_layer3_analysis_product_authoring"
branch_labels = None
depends_on = None

_LIFECYCLE_VALUES = (
    "draft",
    "proposed",
    "validated",
    "accepted",
    "rejected",
    "package_eligible",
    "packaged",
)
_REVIEW_DECISION_VALUES = (
    "promote",
    "accept",
    "mark_package_eligible",
    "reject",
    "revise",
)
_REVIEW_REASON_CODES = (
    "proposed_ready",
    "validation_passed",
    "grounded_accept",
    "package_ready",
    "insufficient_grounding",
    "evidence_gap",
    "operator_rejected",
    "revision_requested",
)
_DECISION_STATUS_RECORDED = "decision_recorded"


def _in_list(col: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{col} IN ({quoted})"


def upgrade() -> None:
    create_table_idempotent(
        "l3_analysis_product_review_decision",
        sa.Column(
            "analysis_product_review_decision_id", sa.String(length=36), nullable=False
        ),
        sa.Column("analysis_product_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("from_status", sa.String(length=64), nullable=False),
        sa.Column("to_status", sa.String(length=64), nullable=False),
        sa.Column("review_decision", sa.String(length=64), nullable=False),
        sa.Column("decision_reason_code", sa.String(length=64), nullable=False),
        sa.Column(
            "decision_status",
            sa.String(length=64),
            nullable=False,
            server_default=_DECISION_STATUS_RECORDED,
        ),
        sa.Column("decision_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("decision_schema_id", sa.String(length=128), nullable=False),
        sa.Column("product_basis_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "grounding_asserted", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("operator_identity", sa.String(length=255), nullable=True),
        sa.Column(
            "decision_notes_present",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("decision_notes_hash", sa.String(length=64), nullable=True),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("decision_provenance_json", sa.JSON(), nullable=False),
        sa.Column("decision_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("analysis_product_review_decision_id"),
        sa.ForeignKeyConstraint(
            ["analysis_product_id"], ["l3_analysis_product.analysis_product_id"]
        ),
        sa.ForeignKeyConstraint(["session_id"], ["l3_session.session_id"]),
        sa.UniqueConstraint(
            "client_request_id", name="uq_l3_aprod_review_decision_client_request"
        ),
        # decision_basis_hash intentionally NOT unique — append-only trail repeats
        # identical transitions (e.g. revise->re-promote). Idempotency is on client_request_id.
        sa.CheckConstraint(
            _in_list("from_status", _LIFECYCLE_VALUES),
            name="ck_l3_aprod_review_decision_from_status",
        ),
        sa.CheckConstraint(
            _in_list("to_status", _LIFECYCLE_VALUES),
            name="ck_l3_aprod_review_decision_to_status",
        ),
        sa.CheckConstraint(
            _in_list("review_decision", _REVIEW_DECISION_VALUES),
            name="ck_l3_aprod_review_decision_value",
        ),
        sa.CheckConstraint(
            _in_list("decision_reason_code", _REVIEW_REASON_CODES),
            name="ck_l3_aprod_review_decision_reason",
        ),
        sa.CheckConstraint(
            f"decision_status = '{_DECISION_STATUS_RECORDED}'",
            name="ck_l3_aprod_review_decision_status",
        ),
    )
    create_index_idempotent(
        "ix_l3_aprod_review_decision_product",
        "l3_analysis_product_review_decision",
        ["analysis_product_id"],
    )
    create_index_idempotent(
        "ix_l3_aprod_review_decision_session",
        "l3_analysis_product_review_decision",
        ["session_id"],
    )


def downgrade() -> None:
    drop_index_idempotent(
        "ix_l3_aprod_review_decision_session",
        "l3_analysis_product_review_decision",
    )
    drop_index_idempotent(
        "ix_l3_aprod_review_decision_product",
        "l3_analysis_product_review_decision",
    )
    drop_table_idempotent("l3_analysis_product_review_decision")
