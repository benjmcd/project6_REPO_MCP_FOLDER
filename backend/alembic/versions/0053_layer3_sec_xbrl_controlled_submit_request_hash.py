"""Hash SEC XBRL controlled-submit request ids before persistence.

Revision ID: 0053_layer3_sec_xbrl_controlled_submit_request_hash
Revises: 0052_layer3_analysis_product_supersession
Create Date: 2026-06-19
"""

from __future__ import annotations

import hashlib

from alembic import op
import sqlalchemy as sa

from migration_compat import column_exists, table_exists


revision = "0053_layer3_sec_xbrl_controlled_submit_request_hash"
down_revision = "0052_layer3_analysis_product_supersession"
branch_labels = None
depends_on = None


TABLE_NAME = "l3_sec_xbrl_controlled_value_reveal_submit_receipt"
REQUEST_ID_HASH_COLUMN = "client_request_id_hash"
REQUEST_ID_COLUMN = "client_request_id"
REQUEST_UNIQUE_CONSTRAINT = "uq_l3_sec_xbrl_controlled_value_reveal_client_request"
SURROGATE_PREFIX = "redacted-client-request-id:"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _valid_hash(value: str | None) -> bool:
    if value is None:
        return False
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _request_id_hash(raw_request_id: str, existing_hash: str | None) -> str:
    if _valid_hash(existing_hash):
        return str(existing_hash)
    if raw_request_id.startswith(SURROGATE_PREFIX):
        embedded_hash = raw_request_id.removeprefix(SURROGATE_PREFIX)
        if _valid_hash(embedded_hash):
            return embedded_hash
    return _sha256_text(raw_request_id)


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


def _add_hash_column() -> None:
    if not table_exists(TABLE_NAME) or column_exists(TABLE_NAME, REQUEST_ID_HASH_COLUMN):
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.add_column(sa.Column(REQUEST_ID_HASH_COLUMN, sa.String(length=64), nullable=True))


def _drop_hash_column() -> None:
    if not table_exists(TABLE_NAME) or not column_exists(TABLE_NAME, REQUEST_ID_HASH_COLUMN):
        return
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.drop_column(REQUEST_ID_HASH_COLUMN)


def _backfill_hashes_and_redact_raw_ids() -> None:
    if not table_exists(TABLE_NAME) or not column_exists(TABLE_NAME, REQUEST_ID_HASH_COLUMN):
        return
    conn = op.get_bind()
    rows = list(
        conn.execute(
            sa.text(
                f"""
                SELECT sec_xbrl_controlled_value_reveal_submit_receipt_id,
                       {REQUEST_ID_COLUMN},
                       {REQUEST_ID_HASH_COLUMN}
                FROM {TABLE_NAME}
                """  # noqa: S608
            )
        ).mappings()
    )
    for row in rows:
        request_hash = _request_id_hash(
            str(row[REQUEST_ID_COLUMN] or ""),
            row[REQUEST_ID_HASH_COLUMN],
        )
        conn.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET {REQUEST_ID_COLUMN} = :redacted_request_id,
                    {REQUEST_ID_HASH_COLUMN} = :request_hash
                WHERE sec_xbrl_controlled_value_reveal_submit_receipt_id = :receipt_id
                """  # noqa: S608
            ),
            {
                "redacted_request_id": f"{SURROGATE_PREFIX}{request_hash}",
                "request_hash": request_hash,
                "receipt_id": row["sec_xbrl_controlled_value_reveal_submit_receipt_id"],
            },
        )


def _hash_column_has_nulls() -> bool:
    if not table_exists(TABLE_NAME) or not column_exists(TABLE_NAME, REQUEST_ID_HASH_COLUMN):
        return False
    result = op.get_bind().execute(
        sa.text(
            f"SELECT 1 FROM {TABLE_NAME} WHERE {REQUEST_ID_HASH_COLUMN} IS NULL LIMIT 1"  # noqa: S608
        )
    )
    return result.first() is not None


def _make_hash_column_non_nullable() -> None:
    if not table_exists(TABLE_NAME) or not column_exists(TABLE_NAME, REQUEST_ID_HASH_COLUMN):
        return
    if _hash_column_has_nulls():
        raise RuntimeError(
            "Cannot make client_request_id_hash non-null: at least one controlled-submit row "
            "still lacks a request-id hash."
        )
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.alter_column(
            REQUEST_ID_HASH_COLUMN,
            existing_type=sa.String(length=64),
            nullable=False,
        )


def _old_constraint_would_conflict() -> bool:
    if not table_exists(TABLE_NAME):
        return False
    result = op.get_bind().execute(
        sa.text(
            f"""
            SELECT 1
            FROM {TABLE_NAME}
            GROUP BY {REQUEST_ID_COLUMN}
            HAVING COUNT(*) > 1
            LIMIT 1
            """  # noqa: S608
        )
    )
    return result.first() is not None


def upgrade() -> None:
    if not table_exists(TABLE_NAME):
        return
    _add_hash_column()
    _backfill_hashes_and_redact_raw_ids()
    _drop_unique_constraint(TABLE_NAME, REQUEST_UNIQUE_CONSTRAINT)
    _create_unique_constraint(TABLE_NAME, REQUEST_UNIQUE_CONSTRAINT, [REQUEST_ID_HASH_COLUMN])
    _make_hash_column_non_nullable()


def downgrade() -> None:
    if not table_exists(TABLE_NAME):
        return
    if _old_constraint_would_conflict():
        raise RuntimeError(
            "Cannot safely downgrade SEC XBRL controlled-submit request-id hashing: "
            "current legacy client_request_id values are not unique."
        )
    _drop_unique_constraint(TABLE_NAME, REQUEST_UNIQUE_CONSTRAINT)
    _create_unique_constraint(TABLE_NAME, REQUEST_UNIQUE_CONSTRAINT, [REQUEST_ID_COLUMN])
    _drop_hash_column()
