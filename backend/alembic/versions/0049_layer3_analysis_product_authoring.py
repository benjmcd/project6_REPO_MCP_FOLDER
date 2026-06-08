"""Add Layer 3 analysis product authoring tables (draft write-path).

Revision ID: 0049_layer3_analysis_product_authoring
Revises: 0048_layer3_sec_xbrl_auth_binding_open_write_route
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


revision = "0049_layer3_analysis_product_authoring"
down_revision = "0048_layer3_sec_xbrl_auth_binding_open_write_route"
branch_labels = None
depends_on = None

_PRODUCT_KIND_VALUES = (
    "analyst_note",
    "fact",
    "metric",
    "finding",
    "insight",
    "diagnostic",
    "summary",
    "hypothesis",
    "recommendation",
)
_EXECUTOR_TYPE_VALUES = (
    "human",
    "deterministic",
    "agent",
    "external_api",
)
_LIFECYCLE_VALUES = (
    "draft",
    "proposed",
    "validated",
    "accepted",
    "rejected",
    "package_eligible",
    "packaged",
)
_EVIDENCE_ROLE_VALUES = (
    "observation",
    "measurement",
    "claim",
    "interpretation",
    "context",
    "counterpoint",
)
_EVIDENCE_REF_KIND_VALUES = (
    "material_snapshot",
    "pass_run",
    "output_package",
    "analysis_set",
    "prior_product",
)


def _in_list(col: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{col} IN ({quoted})"


def upgrade() -> None:
    create_table_idempotent(
        "l3_analysis_product",
        sa.Column("analysis_product_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("product_kind", sa.String(length=64), nullable=False),
        sa.Column("executor_type", sa.String(length=64), nullable=False, server_default="human"),
        sa.Column("lifecycle_status", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_non_evidentiary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("executor_identity", sa.String(length=255), nullable=True),
        sa.Column("output_schema_validation_status", sa.String(length=64), nullable=True),
        sa.Column("basis_hash", sa.String(length=64), nullable=False),
        sa.Column("spec_hash", sa.String(length=64), nullable=False),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("authoring_provenance_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("analysis_product_id"),
        sa.ForeignKeyConstraint(["session_id"], ["l3_session.session_id"]),
        sa.UniqueConstraint(
            "session_id", "client_request_id", name="uq_l3_analysis_product_session_request"
        ),
        sa.CheckConstraint(
            _in_list("product_kind", _PRODUCT_KIND_VALUES),
            name="ck_l3_analysis_product_kind",
        ),
        sa.CheckConstraint(
            _in_list("executor_type", _EXECUTOR_TYPE_VALUES),
            name="ck_l3_analysis_product_executor_type",
        ),
        sa.CheckConstraint(
            _in_list("lifecycle_status", _LIFECYCLE_VALUES),
            name="ck_l3_analysis_product_lifecycle",
        ),
    )
    create_index_idempotent(
        "ix_l3_analysis_product_session",
        "l3_analysis_product",
        ["session_id"],
    )

    create_table_idempotent(
        "l3_analysis_product_evidence_link",
        sa.Column("evidence_link_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_product_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("ref_kind", sa.String(length=64), nullable=False),
        sa.Column("ref_id", sa.String(length=255), nullable=False),
        sa.Column("evidence_role", sa.String(length=64), nullable=False),
        sa.Column("locator_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("evidence_link_id"),
        sa.ForeignKeyConstraint(
            ["analysis_product_id"], ["l3_analysis_product.analysis_product_id"]
        ),
        sa.ForeignKeyConstraint(["session_id"], ["l3_session.session_id"]),
        sa.CheckConstraint(
            _in_list("ref_kind", _EVIDENCE_REF_KIND_VALUES),
            name="ck_l3_aprod_evlink_ref_kind",
        ),
        sa.CheckConstraint(
            _in_list("evidence_role", _EVIDENCE_ROLE_VALUES),
            name="ck_l3_aprod_evlink_role",
        ),
    )
    create_index_idempotent(
        "ix_l3_aprod_evlink_product",
        "l3_analysis_product_evidence_link",
        ["analysis_product_id"],
    )


def downgrade() -> None:
    drop_index_idempotent("ix_l3_aprod_evlink_product", "l3_analysis_product_evidence_link")
    drop_table_idempotent("l3_analysis_product_evidence_link")
    drop_index_idempotent("ix_l3_analysis_product_session", "l3_analysis_product")
    drop_table_idempotent("l3_analysis_product")
