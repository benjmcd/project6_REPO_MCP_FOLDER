"""Runtime DB session management for NRC APS review/document-trace.

This module is the single authority for opening per-run runtime database
sessions in the review/document-trace consumption plane.

Contract:
    runtime_db_session_for_run(run_id)
        -> context manager yielding (ReviewRuntimeBinding, Session)
    runtime_db_session_for_binding(binding)
        -> context manager yielding Session

Safety guarantees:
    - Runtime DBs are opened in read-only mode (SQLite URI mode=ro).
    - Required review/document-trace tables must exist before a session is yielded.
    - The database file must exist and be a regular file before a session opens.
    - Sessions are scoped to the context manager lifetime and always closed.
    - No migrations are ever run against runtime DBs.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding, find_runtime_binding_for_run


# Tables that must exist in a runtime DB for review/document-trace to function.
# Derived from the actual queries in review_nrc_aps_document_trace.py and
# review_nrc_aps_catalog.py.
REQUIRED_REVIEW_TABLES: frozenset[str] = frozenset({
    "connector_run_target",
    "aps_content_linkage",
    "aps_content_document",
    "aps_content_chunk",
    "connector_run",
})


@lru_cache(maxsize=32)
def _session_factory_for_database(database_path_str: str):
    database_path = Path(database_path_str).resolve()
    uri_path = f"file:{database_path.as_posix()}?mode=ro"

    def _connect() -> sqlite3.Connection:
        return sqlite3.connect(uri_path, uri=True, check_same_thread=False)

    engine = create_engine("sqlite://", creator=_connect, future=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def _validate_schema_compatibility(session: Session, run_id: str) -> None:
    """Verify that the runtime DB contains the tables needed for review/document-trace.

    Raises RuntimeError with a descriptive message if required tables are missing.
    """
    rows = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    present_tables = frozenset(row[0] for row in rows)
    missing = REQUIRED_REVIEW_TABLES - present_tables
    if missing:
        raise RuntimeError(
            f"Runtime DB for run {run_id} is missing required tables: "
            f"{', '.join(sorted(missing))}. "
            f"This database is not compatible with the review/document-trace surface."
        )


def get_runtime_binding_for_run(run_id: str) -> ReviewRuntimeBinding:
    binding = find_runtime_binding_for_run(run_id)
    if binding is None:
        raise KeyError(f"Review root not found for run {run_id}")
    return binding


@contextmanager
def runtime_db_session_for_binding(binding: ReviewRuntimeBinding) -> Iterator[Session]:
    if binding.database_path is None:
        raise FileNotFoundError(f"Review database path missing for run {binding.run_id}")
    database_path = binding.database_path.resolve()
    if not database_path.exists():
        raise FileNotFoundError(f"Review database missing on disk for run {binding.run_id}: {database_path}")
    if not database_path.is_file():
        raise FileNotFoundError(f"Review database path is not a file for run {binding.run_id}: {database_path}")

    SessionLocal = _session_factory_for_database(str(database_path))
    session = SessionLocal()
    try:
        _validate_schema_compatibility(session, binding.run_id)
        yield session
    finally:
        session.close()


@contextmanager
def runtime_db_session_for_run(run_id: str) -> Iterator[tuple[ReviewRuntimeBinding, Session]]:
    binding = get_runtime_binding_for_run(run_id)
    with runtime_db_session_for_binding(binding) as session:
        yield binding, session
