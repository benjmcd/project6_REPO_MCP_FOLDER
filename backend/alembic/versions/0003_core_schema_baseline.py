"""Create baseline core tables for migration-first startup."""

from __future__ import annotations

from alembic import op

from app.models import Base


revision = "0003_core_schema_baseline"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


CORE_TABLES = [
    "source_connector",
    "dataset",
    "dataset_version",
    "variable_definition",
    "variable_profile",
    "transformation_run",
    "transformation_step",
    "annotation_window",
    "analysis_run",
    "assumption_check",
    "caveat_note",
    "analysis_artifact",
    "saved_query",
    "query_run",
    "dataset_row",
]


def upgrade() -> None:
    bind = op.get_bind()
    metadata = Base.metadata
    tables = [metadata.tables[name] for name in CORE_TABLES if name in metadata.tables]
    metadata.create_all(bind=bind, tables=tables, checkfirst=True)


def downgrade() -> None:
    # Baseline compatibility revision: keep core tables on downgrade to avoid data loss.
    # Connector subsystem downgrade remains handled in 0002.
    pass
