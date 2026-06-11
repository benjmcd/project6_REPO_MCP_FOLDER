"""Migration validation suite for Layer 3 alembic migrations.

Covers:
- SQLite: alembic upgrade head succeeds
- SQLite: exactly one head in the script directory
- SQLite: idempotent re-run (upgrade head twice without error)
- SQLite: ORM metadata match (all Base tables/columns present after upgrade)
- Postgres variants: guarded by pytest.mark.skipif when psycopg2 or
  LAYER3_MIGRATION_TEST_DATABASE_URL env var is absent
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text

# ---------------------------------------------------------------------------
# Path bootstrap — replicate the pattern used by the other test_layer3_*.py
# files: set DB_INIT_MODE before importing app modules so the app startup
# does not attempt a migrate-on-boot against the default SQLite path.
# ---------------------------------------------------------------------------
os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from alembic.config import Config  # noqa: E402
from alembic import command  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402

# Import Base (and trigger model registration) after path/env setup.
from app.db.session import Base  # noqa: E402
import app.models.models  # noqa: E402,F401  — registers all ORM classes


# ---------------------------------------------------------------------------
# Known-allowlist for live-vs-metadata table differences.
# Add entries here (with comments) if a legitimate drift is ever introduced.
# ---------------------------------------------------------------------------
EXTRA_LIVE_TABLES_ALLOWLIST: frozenset[str] = frozenset(
    {
        "alembic_version",  # Alembic's internal tracking table — always present
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALEMBIC_INI = BACKEND / "alembic.ini"


def _make_alembic_config(url: str) -> Config:
    """Return an Alembic Config pointed at alembic.ini with the given DB URL."""
    cfg = Config(str(ALEMBIC_INI))
    # alembic.ini declares script_location relative to the backend/ directory;
    # pin it absolutely so the suite passes regardless of pytest's cwd.
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _run_upgrade(url: str) -> None:
    """Run alembic upgrade head against *url*.

    env.py's ``_database_url()`` checks ``os.environ["DATABASE_URL"]`` first,
    so we must set that env var — not just the alembic config option — to
    ensure the online migration path targets the correct database file.
    The previous value (if any) is restored after the upgrade completes.
    """
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        cfg = _make_alembic_config(url)
        command.upgrade(cfg, "head")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev


def _check_schema_match(url: str) -> None:
    """Assert that all ORM metadata tables/columns are present in the live DB.

    Extra tables in the live DB that are present in EXTRA_LIVE_TABLES_ALLOWLIST
    are ignored.  Any unlisted extra tables are reported but do NOT cause a
    failure (they may be created by future migrations not yet reflected in the
    ORM metadata — that is acceptable drift in the forward direction).

    Missing tables (tables in metadata but absent from the live DB) always
    fail the assertion.
    """
    engine = create_engine(url, future=True)
    inspector = sa_inspect(engine)
    live_tables = set(inspector.get_table_names())
    meta_tables = set(Base.metadata.tables.keys())

    missing_tables = meta_tables - live_tables
    assert not missing_tables, (
        f"ORM metadata tables missing from live schema after alembic upgrade head: "
        f"{sorted(missing_tables)}"
    )

    # Check columns for every table that exists in both places.
    missing_columns: dict[str, list[str]] = {}
    for table_name in meta_tables:
        if table_name not in live_tables:
            continue  # already reported above
        live_cols = {c["name"] for c in inspector.get_columns(table_name)}
        meta_cols = {
            col.name for col in Base.metadata.tables[table_name].columns
        }
        absent = meta_cols - live_cols
        if absent:
            missing_columns[table_name] = sorted(absent)

    assert not missing_columns, (
        f"ORM metadata columns missing from live schema after alembic upgrade head: "
        f"{missing_columns}"
    )

    engine.dispose()


# ---------------------------------------------------------------------------
# Postgres skip guard
# ---------------------------------------------------------------------------

_POSTGRES_URL = os.environ.get("LAYER3_MIGRATION_TEST_DATABASE_URL", "")


def _psycopg2_available() -> bool:
    try:
        import psycopg2  # noqa: F401
        return True
    except ImportError:
        return False


_skip_postgres = pytest.mark.skipif(
    not (_psycopg2_available() and bool(_POSTGRES_URL)),
    reason=(
        "Postgres migration tests require psycopg2 and "
        "LAYER3_MIGRATION_TEST_DATABASE_URL to be set"
    ),
)


# ---------------------------------------------------------------------------
# SQLite tests (always run)
# ---------------------------------------------------------------------------


def test_alembic_single_head(tmp_path):
    """The alembic script directory must expose exactly one current head."""
    cfg = _make_alembic_config(f"sqlite:///{tmp_path / 'single_head.db'}")
    scripts = ScriptDirectory.from_config(cfg)
    heads = scripts.get_heads()
    assert len(heads) == 1, (
        f"Expected exactly one alembic head; found {len(heads)}: {heads}. "
        "A merge migration may be missing."
    )


def test_alembic_upgrade_head_sqlite(tmp_path):
    """alembic upgrade head completes without error against a fresh SQLite db."""
    db_url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    _run_upgrade(db_url)
    # Verify the alembic_version table records the single head revision.
    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = [row[0] for row in result]
    engine.dispose()
    assert len(rows) == 1, f"Expected one version row, got {rows}"


def test_alembic_upgrade_head_idempotent_sqlite(tmp_path):
    """Running alembic upgrade head twice on the same SQLite db must not error."""
    db_url = f"sqlite:///{tmp_path / 'idempotent.db'}"
    _run_upgrade(db_url)
    # Second run — should be a no-op and should not raise.
    _run_upgrade(db_url)


def test_alembic_orm_metadata_match_sqlite(tmp_path):
    """After upgrade head, every ORM table and column must exist in the live schema."""
    db_url = f"sqlite:///{tmp_path / 'metadata_match.db'}"
    _run_upgrade(db_url)
    _check_schema_match(db_url)


# ---------------------------------------------------------------------------
# Postgres tests (skipped when driver or URL absent)
# ---------------------------------------------------------------------------


@_skip_postgres
def test_alembic_upgrade_head_postgres():
    """alembic upgrade head completes against the Postgres test database."""
    _run_upgrade(_POSTGRES_URL)


@_skip_postgres
def test_alembic_upgrade_head_idempotent_postgres():
    """Running alembic upgrade head twice on Postgres must not error."""
    _run_upgrade(_POSTGRES_URL)
    _run_upgrade(_POSTGRES_URL)


@_skip_postgres
def test_alembic_orm_metadata_match_postgres():
    """After upgrade head, every ORM table and column must exist in Postgres live schema."""
    _run_upgrade(_POSTGRES_URL)
    _check_schema_match(_POSTGRES_URL)
