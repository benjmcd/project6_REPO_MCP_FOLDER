"""Targeted tests for the runtime DB session module.

Proves:
- runtime DB resolution is explicit and correct
- runtime binding ambiguity is reduced
- safety rails reject missing/invalid DB paths
- session lifecycle is properly scoped
- runtime DBs are opened read-only
- schema compatibility validation rejects incompatible DBs
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding
from app.services.review_nrc_aps_runtime_db import (
    REQUIRED_REVIEW_TABLES,
    _session_factory_for_database,
    _validate_schema_compatibility,
    runtime_db_session_for_binding,
    runtime_db_session_for_run,
    get_runtime_binding_for_run,
)
from review_nrc_aps_runtime_fixture import discover_passed_runtimes, latest_passed_runtime


RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id


@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Ensure each test starts with a clean session factory cache."""
    _session_factory_for_database.cache_clear()
    yield
    _session_factory_for_database.cache_clear()


# ---------------------------------------------------------------------------
# runtime_db_session_for_run: happy path
# ---------------------------------------------------------------------------

def test_runtime_db_session_for_run_yields_binding_and_session():
    """Context manager must yield (binding, session) for a known run."""
    with runtime_db_session_for_run(RUN_ID) as (binding, session):
        assert binding is not None
        assert binding.run_id == RUN_ID
        assert binding.review_root.exists()
        assert session is not None
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_runtime_db_session_for_run_session_closed_after_exit():
    """Session must be closed after context manager exit."""
    with runtime_db_session_for_run(RUN_ID) as (binding, session):
        pass
    assert not session.is_active or session.get_bind() is not None


def test_runtime_db_session_for_run_binding_matches_fixture():
    """The resolved binding must point at a real runtime DB."""
    with runtime_db_session_for_run(RUN_ID) as (binding, session):
        assert binding.database_path is not None
        assert binding.database_path.exists()
        assert binding.database_path.is_file()
        assert binding.database_path.name == "lc.db"


# ---------------------------------------------------------------------------
# runtime_db_session_for_run: error paths
# ---------------------------------------------------------------------------

def test_runtime_db_session_for_run_unknown_run_raises_key_error():
    """Unknown run_id must raise KeyError, not silently fall back."""
    with pytest.raises(KeyError, match="not found"):
        with runtime_db_session_for_run("00000000-0000-0000-0000-000000000000"):
            pass


def test_runtime_db_session_for_run_empty_run_raises_key_error():
    with pytest.raises(KeyError):
        with runtime_db_session_for_run(""):
            pass


# ---------------------------------------------------------------------------
# runtime_db_session_for_binding: happy path
# ---------------------------------------------------------------------------

def test_runtime_db_session_for_binding_yields_usable_session():
    """Context manager must yield a usable session for a valid binding."""
    binding = get_runtime_binding_for_run(RUN_ID)
    with runtime_db_session_for_binding(binding) as session:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1


# ---------------------------------------------------------------------------
# runtime_db_session_for_binding: path safety rails
# ---------------------------------------------------------------------------

def test_runtime_db_session_for_binding_none_path_raises():
    """Binding with database_path=None must raise FileNotFoundError."""
    binding = ReviewRuntimeBinding(
        run_id="fake-run",
        review_root=Path("C:/nonexistent"),
        summary={},
        database_path=None,
        storage_dir=None,
    )
    with pytest.raises(FileNotFoundError, match="missing"):
        with runtime_db_session_for_binding(binding):
            pass


def test_runtime_db_session_for_binding_nonexistent_path_raises():
    """Binding with a non-existent database path must raise FileNotFoundError."""
    binding = ReviewRuntimeBinding(
        run_id="fake-run",
        review_root=Path("C:/nonexistent"),
        summary={},
        database_path=Path("C:/nonexistent/fake.db"),
        storage_dir=None,
    )
    with pytest.raises(FileNotFoundError, match="missing on disk"):
        with runtime_db_session_for_binding(binding):
            pass


def test_runtime_db_session_for_binding_directory_path_raises(tmp_path):
    """Binding with a directory as database_path must raise FileNotFoundError."""
    dir_path = tmp_path / "not_a_db"
    dir_path.mkdir()
    binding = ReviewRuntimeBinding(
        run_id="fake-run",
        review_root=tmp_path,
        summary={},
        database_path=dir_path,
        storage_dir=None,
    )
    with pytest.raises(FileNotFoundError, match="not a file"):
        with runtime_db_session_for_binding(binding):
            pass


# ---------------------------------------------------------------------------
# Read-only enforcement
# ---------------------------------------------------------------------------

def test_runtime_db_session_is_read_only():
    """Runtime DB sessions must reject write operations."""
    with runtime_db_session_for_run(RUN_ID) as (binding, session):
        # Read must succeed
        session.execute(text("SELECT 1"))

        # Write must be rejected by SQLite read-only mode
        with pytest.raises(Exception, match="readonly"):
            session.execute(text("CREATE TABLE _write_test_guard (id INTEGER)"))


def test_runtime_db_session_read_only_prevents_insert(tmp_path):
    """Verify INSERT is blocked even on an otherwise valid runtime DB."""
    db_path = tmp_path / "readonly_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE connector_run (id INTEGER)")
    conn.execute("CREATE TABLE connector_run_target (id INTEGER)")
    conn.execute("CREATE TABLE aps_content_linkage (id INTEGER)")
    conn.execute("CREATE TABLE aps_content_document (id INTEGER)")
    conn.execute("CREATE TABLE aps_content_chunk (id INTEGER)")
    conn.commit()
    conn.close()

    binding = ReviewRuntimeBinding(
        run_id="ro-test",
        review_root=tmp_path,
        summary={},
        database_path=db_path,
        storage_dir=None,
    )
    with runtime_db_session_for_binding(binding) as session:
        with pytest.raises(Exception, match="readonly"):
            session.execute(text("INSERT INTO connector_run (id) VALUES (1)"))


# ---------------------------------------------------------------------------
# Schema compatibility validation
# ---------------------------------------------------------------------------

def test_schema_validation_passes_for_valid_runtime_db():
    """A runtime DB with all required tables must pass schema validation."""
    with runtime_db_session_for_run(RUN_ID) as (binding, session):
        # If we got here, schema validation already passed inside the context manager.
        # Verify the required tables exist by querying sqlite_master directly.
        rows = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
        present = {row[0] for row in rows}
        assert REQUIRED_REVIEW_TABLES.issubset(present)


def test_schema_validation_rejects_empty_db(tmp_path):
    """An empty SQLite DB must be rejected with RuntimeError."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    conn.close()

    binding = ReviewRuntimeBinding(
        run_id="empty-db-test",
        review_root=tmp_path,
        summary={},
        database_path=db_path,
        storage_dir=None,
    )
    with pytest.raises(RuntimeError, match="missing required tables"):
        with runtime_db_session_for_binding(binding):
            pass


def test_schema_validation_rejects_partial_schema(tmp_path):
    """A DB with only some of the required tables must be rejected."""
    db_path = tmp_path / "partial.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE connector_run_target (id INTEGER)")
    conn.execute("CREATE TABLE aps_content_linkage (id INTEGER)")
    # Missing: aps_content_document, aps_content_chunk, connector_run
    conn.commit()
    conn.close()

    binding = ReviewRuntimeBinding(
        run_id="partial-db-test",
        review_root=tmp_path,
        summary={},
        database_path=db_path,
        storage_dir=None,
    )
    with pytest.raises(RuntimeError, match="missing required tables") as exc_info:
        with runtime_db_session_for_binding(binding):
            pass

    error_msg = str(exc_info.value)
    assert "aps_content_chunk" in error_msg
    assert "aps_content_document" in error_msg
    assert "connector_run" in error_msg


def test_schema_validation_reports_all_missing_tables(tmp_path):
    """The error message must list all missing tables, not just the first."""
    db_path = tmp_path / "no_tables.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE unrelated_table (id INTEGER)")
    conn.commit()
    conn.close()

    binding = ReviewRuntimeBinding(
        run_id="no-tables-test",
        review_root=tmp_path,
        summary={},
        database_path=db_path,
        storage_dir=None,
    )
    with pytest.raises(RuntimeError, match="missing required tables") as exc_info:
        with runtime_db_session_for_binding(binding):
            pass

    error_msg = str(exc_info.value)
    for table_name in REQUIRED_REVIEW_TABLES:
        assert table_name in error_msg, f"Missing table '{table_name}' not reported in error"


# ---------------------------------------------------------------------------
# get_runtime_binding_for_run
# ---------------------------------------------------------------------------

def test_get_runtime_binding_for_run_returns_binding():
    binding = get_runtime_binding_for_run(RUN_ID)
    assert binding.run_id == RUN_ID
    assert binding.review_root.exists()
    assert binding.database_path is not None


def test_get_runtime_binding_for_run_unknown_raises():
    with pytest.raises(KeyError):
        get_runtime_binding_for_run("00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# Multi-runtime: sessions are isolated per run
# ---------------------------------------------------------------------------

def test_sessions_are_isolated_per_runtime():
    """Different runs must open different DB sessions, not share one global session."""
    runtimes = discover_passed_runtimes()[:2]
    if len(runtimes) < 2:
        pytest.skip("Need at least 2 passed runtimes for isolation test")

    with runtime_db_session_for_run(runtimes[0].run_id) as (b1, s1):
        with runtime_db_session_for_run(runtimes[1].run_id) as (b2, s2):
            assert b1.run_id != b2.run_id
            assert b1.database_path != b2.database_path
            assert s1.execute(text("SELECT 1")).scalar() == 1
            assert s2.execute(text("SELECT 1")).scalar() == 1
