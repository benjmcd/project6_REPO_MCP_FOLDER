from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding, find_runtime_binding_for_run


@lru_cache(maxsize=32)
def _session_factory_for_database(database_path_str: str):
    database_path = Path(database_path_str).resolve()
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


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

    SessionLocal = _session_factory_for_database(str(database_path))
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def runtime_db_session_for_run(run_id: str) -> Iterator[tuple[ReviewRuntimeBinding, Session]]:
    binding = get_runtime_binding_for_run(run_id)
    with runtime_db_session_for_binding(binding) as session:
        yield binding, session
