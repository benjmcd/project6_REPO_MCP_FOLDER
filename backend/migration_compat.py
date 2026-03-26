"""Idempotency helpers for Alembic migrations.

These guards let migrations survive a database that was partially set up by
``Base.metadata.create_all()`` (DB_INIT_MODE=create_all) before Alembic took
over.  Each helper is a no-op when the object already exists / is already
absent, so ``alembic upgrade head`` becomes safe to re-run at any point.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


def table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return name in inspector.get_table_names()


def column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def index_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    for table_name in inspector.get_table_names():
        for idx in inspector.get_indexes(table_name):
            if idx["name"] == name:
                return True
    return False


def create_table_idempotent(name: str, *args, **kwargs) -> None:
    if not table_exists(name):
        op.create_table(name, *args, **kwargs)


def create_index_idempotent(name: str, table: str, columns: list[str], **kwargs) -> None:
    if not index_exists(name):
        op.create_index(name, table, columns, **kwargs)


def add_column_idempotent(table: str, column: sa.Column) -> None:
    if not column_exists(table, column.name):
        op.add_column(table, column)


def drop_column_idempotent(table: str, column_name: str) -> None:
    if column_exists(table, column_name):
        op.drop_column(table, column_name)


def drop_table_idempotent(name: str) -> None:
    if table_exists(name):
        op.drop_table(name)


def drop_index_idempotent(name: str, table_name: str) -> None:
    if index_exists(name):
        op.drop_index(name, table_name=table_name)
