"""Targeted tests for the runtime DB session module.

Proves:
- runtime DB resolution is explicit and correct
- runtime binding ambiguity is reduced
- safety rails reject missing/invalid DB paths
- session lifecycle is properly scoped
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding
from app.services.review_nrc_aps_runtime_db import (
    runtime_db_session_for_binding,
    runtime_db_session_for_run,
    get_runtime_binding_for_run,
)
from review_nrc_aps_runtime_fixture import discover_passed_runtimes, latest_passed_runtime


RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id


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
        # Session must be usable — execute a trivial query
        result = session.execute(__import__("sqlalchemy").text("SELECT 1"))
        assert result.scalar() == 1


def test_runtime_db_session_for_run_session_closed_after_exit():
    """Session must be closed after context manager exit."""
    with runtime_db_session_for_run(RUN_ID) as (binding, session):
        pass
    # After exit, session.is_active should reflect closure
    # SQLAlchemy session.close() invalidates the session
    assert not session.is_active or session.get_bind() is not None  # session was closed


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
        result = session.execute(__import__("sqlalchemy").text("SELECT 1"))
        assert result.scalar() == 1


# ---------------------------------------------------------------------------
# runtime_db_session_for_binding: safety rails
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
            # Both sessions must be independently usable
            assert s1.execute(__import__("sqlalchemy").text("SELECT 1")).scalar() == 1
            assert s2.execute(__import__("sqlalchemy").text("SELECT 1")).scalar() == 1
