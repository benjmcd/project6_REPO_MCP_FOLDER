"""Allow the flag-gated adopted-external intake decision.

Revision ID: 0058_layer3_adopted_external_source_intake
Revises: 0057_layer3_b1b_connector_promotion
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


revision = "0058_layer3_adopted_external_source_intake"
down_revision = "0057_layer3_b1b_connector_promotion"
branch_labels = None
depends_on = None

INTAKE_TABLE = "l3_connector_source_intake_record"
RECEIPT_TABLE = "l3_connector_promotion_receipt"
OPERATOR_CHECK = "ck_l3_connector_source_intake_operator_decision"
CONNECTOR_OPERATOR = "record_connector_produced_source"
ADOPTED_OPERATOR = "record_adopted_external_source"
OLD_OPERATOR_SQL = f"operator_decision = '{CONNECTOR_OPERATOR}'"
NEW_OPERATOR_SQL = (
    f"operator_decision IN ('{CONNECTOR_OPERATOR}', "
    f"'{ADOPTED_OPERATOR}')"
)
CHECK_NAMES = {
    OPERATOR_CHECK,
    "ck_l3_connector_source_intake_status",
    "ck_l3_connector_source_intake_identity_metadata_joint_null",
}
UNIQUE_NAMES = {
    "uq_l3_connector_source_intake_client_request",
    "uq_l3_connector_source_intake_authority_basis",
}
INDEX_NAMES = {
    "ix_l3_connector_intake_material_identity",
    "ix_l3_connector_source_intake_content_sha256",
    "ix_l3_connector_source_intake_run_target",
    "ix_l3_connector_source_intake_source_family",
    "ix_l3_connector_source_intake_status",
}


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _operator_check_sql() -> str | None:
    if not _table_exists(INTAKE_TABLE):
        return None
    for check in sa.inspect(op.get_bind()).get_check_constraints(INTAKE_TABLE):
        if check.get("name") == OPERATOR_CHECK:
            return str(check.get("sqltext") or "")
    return None


def _operator_check_state(sqltext: str) -> str:
    normalized = " ".join(str(sqltext).casefold().split())
    if (
        "operator_decision" not in normalized
        or " not " in f" {normalized} "
        or " or " in f" {normalized} "
        or "!=" in normalized
        or "<>" in normalized
    ):
        return "unknown"
    admitted_values = set(re.findall(r"'(record_[a-z0-9_]+)'", normalized))
    if admitted_values == {CONNECTOR_OPERATOR} and "=" in normalized:
        return "connector_only"
    if admitted_values == {CONNECTOR_OPERATOR, ADOPTED_OPERATOR} and (
        " in " in f" {normalized} " or " any " in f" {normalized} "
    ):
        return "connector_and_adopted"
    return "unknown"


def _copy_from_table(operator_sql: str) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(
        INTAKE_TABLE,
        metadata,
        sa.Column(
            "connector_source_intake_record_id", sa.String(length=36), nullable=False
        ),
        sa.Column("client_request_id", sa.String(length=255), nullable=False),
        sa.Column("operator_decision", sa.String(length=64), nullable=False),
        sa.Column("source_family", sa.String(length=64), nullable=False),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=True),
        sa.Column("content_size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "identity_metadata_hash_version", sa.String(length=64), nullable=True
        ),
        sa.Column("identity_metadata_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_hash", sa.String(length=64), nullable=False),
        sa.Column("authority_basis_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_ref", sa.String(length=1024), nullable=False),
        sa.Column("freshness_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("downstream_eligibility_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connector_key", sa.String(length=100), nullable=False),
        sa.Column("connector_run_id", sa.String(length=36), nullable=False),
        sa.Column("connector_run_target_id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint(
            "connector_source_intake_record_id",
            name="pk_l3_connector_source_intake_record",
        ),
        sa.UniqueConstraint(
            "client_request_id",
            name="uq_l3_connector_source_intake_client_request",
        ),
        sa.UniqueConstraint(
            "authority_basis_hash",
            name="uq_l3_connector_source_intake_authority_basis",
        ),
        sa.CheckConstraint(operator_sql, name=OPERATOR_CHECK),
        sa.CheckConstraint(
            "status IN ('recorded', 'already_recorded')",
            name="ck_l3_connector_source_intake_status",
        ),
        sa.CheckConstraint(
            "(identity_metadata_hash_version IS NULL AND identity_metadata_hash IS NULL)"
            " OR (identity_metadata_hash_version IS NOT NULL AND identity_metadata_hash IS NOT NULL)",
            name="ck_l3_connector_source_intake_identity_metadata_joint_null",
        ),
    )
    sa.Index(
        "ix_l3_connector_intake_material_identity",
        table.c.identity_metadata_hash_version,
        table.c.source_family,
        table.c.content_sha256,
        table.c.identity_metadata_hash,
    )
    sa.Index(
        "ix_l3_connector_source_intake_content_sha256", table.c.content_sha256
    )
    sa.Index(
        "ix_l3_connector_source_intake_run_target",
        table.c.connector_run_target_id,
    )
    sa.Index(
        "ix_l3_connector_source_intake_source_family", table.c.source_family
    )
    sa.Index("ix_l3_connector_source_intake_status", table.c.status)
    return table


def _sqlite_replace_operator_check(*, old_sql: str, new_sql: str) -> None:
    copy_from = _copy_from_table(old_sql)
    with op.batch_alter_table(
        INTAKE_TABLE,
        copy_from=copy_from,
        recreate="always",
    ) as batch:
        batch.drop_constraint(OPERATOR_CHECK, type_="check")
        batch.create_check_constraint(OPERATOR_CHECK, new_sql)


def _replace_operator_check(*, old_sql: str, new_sql: str) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        _sqlite_replace_operator_check(old_sql=old_sql, new_sql=new_sql)
        return
    if dialect == "postgresql":
        op.drop_constraint(OPERATOR_CHECK, INTAKE_TABLE, type_="check")
        op.create_check_constraint(OPERATOR_CHECK, INTAKE_TABLE, new_sql)
        return
    raise RuntimeError(
        "Cannot safely alter adopted-external intake authority on this database dialect."
    )


def _assert_preserved_shape() -> None:
    inspector = sa.inspect(op.get_bind())
    checks = {
        check.get("name")
        for check in inspector.get_check_constraints(INTAKE_TABLE)
    }
    uniques = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints(INTAKE_TABLE)
    }
    indexes = {
        index.get("name")
        for index in inspector.get_indexes(INTAKE_TABLE)
        if not index.get("duplicates_constraint")
    }
    if checks != CHECK_NAMES or uniques != UNIQUE_NAMES or indexes != INDEX_NAMES:
        raise RuntimeError(
            "Adopted-external intake migration did not preserve the complete sibling constraint/index shape."
        )
    if _table_exists(RECEIPT_TABLE):
        foreign_keys = inspector.get_foreign_keys(RECEIPT_TABLE)
        incoming_preserved = any(
            tuple(foreign_key.get("constrained_columns") or ())
            == ("connector_source_intake_record_id",)
            and foreign_key.get("referred_table") == INTAKE_TABLE
            and tuple(foreign_key.get("referred_columns") or ())
            == ("connector_source_intake_record_id",)
            for foreign_key in foreign_keys
        )
        if not incoming_preserved:
            raise RuntimeError(
                "Adopted-external intake migration did not preserve the incoming promotion-receipt foreign key."
            )


def upgrade() -> None:
    if not _table_exists(INTAKE_TABLE):
        return
    current_sql = _operator_check_sql()
    if current_sql is None:
        raise RuntimeError("The intake operator-decision constraint is missing.")
    state = _operator_check_state(current_sql)
    if state == "connector_and_adopted":
        _assert_preserved_shape()
        return
    if state != "connector_only":
        raise RuntimeError("The intake operator-decision constraint is not recognized.")
    _replace_operator_check(old_sql=OLD_OPERATOR_SQL, new_sql=NEW_OPERATOR_SQL)
    _assert_preserved_shape()


def downgrade() -> None:
    if not _table_exists(INTAKE_TABLE):
        return
    bind = op.get_bind()
    adopted_row = bind.execute(
        sa.text(
            f"SELECT 1 FROM {INTAKE_TABLE} "
            "WHERE operator_decision = :decision LIMIT 1"
        ),
        {"decision": ADOPTED_OPERATOR},
    ).first()
    if adopted_row is not None:
        raise RuntimeError(
            "Cannot downgrade adopted-external intake while adopted rows exist."
        )
    current_sql = _operator_check_sql()
    if current_sql is None:
        raise RuntimeError("The intake operator-decision constraint is missing.")
    state = _operator_check_state(current_sql)
    if state == "connector_only":
        _assert_preserved_shape()
        return
    if state != "connector_and_adopted":
        raise RuntimeError("The intake operator-decision constraint is not recognized.")
    _replace_operator_check(old_sql=NEW_OPERATOR_SQL, new_sql=OLD_OPERATOR_SQL)
    _assert_preserved_shape()
