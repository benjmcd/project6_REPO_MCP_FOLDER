from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.models import ApsContentLinkage
from app.services.review_nrc_aps_runtime_roots import candidate_review_runtime_roots
from app.services.review_nrc_aps_runtime import (
    resolve_runtime_database_path,
    resolve_runtime_storage_dir,
)


TESTS_ROOT = Path(__file__).resolve().parent
INITIAL_STORAGE_DIR = str(os.environ.get("STORAGE_DIR") or "").strip()


def _candidate_shared_runtime_parent() -> Path | None:
    for ancestor in TESTS_ROOT.parents:
        if ancestor.name != "worktrees":
            continue
        candidate = ancestor.parent / "backend" / "app" / "storage_test_runtime" / "lc_e2e"
        try:
            return candidate.resolve()
        except OSError:
            return None
    return None


def _resolve_runtime_parents() -> list[Path]:
    candidates = candidate_review_runtime_roots(
        app_root=TESTS_ROOT.parent / "app",
        backend_root=TESTS_ROOT.parent,
        storage_dir=os.environ.get("STORAGE_DIR"),
    )

    shared_candidate = _candidate_shared_runtime_parent()
    if shared_candidate is not None:
        candidates.append(shared_candidate)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(resolved)

    return deduped


RUNTIME_PARENTS = _resolve_runtime_parents()
RUNTIME_PARENT = next((candidate for candidate in RUNTIME_PARENTS if candidate.exists()), RUNTIME_PARENTS[0])

if not INITIAL_STORAGE_DIR and RUNTIME_PARENT.exists():
    default_storage_root = RUNTIME_PARENT.parent.resolve()
    os.environ["STORAGE_DIR"] = str(default_storage_root)
    settings.storage_dir = str(default_storage_root)


@dataclass(frozen=True)
class AuditedReviewRuntime:
    runtime_dir: Path
    summary: dict
    run_id: str
    db_path: Path
    storage_dir: Path


def _runtime_has_accession_prefix(runtime: AuditedReviewRuntime, prefix: str) -> bool:
    database_uri = f"{runtime.db_path.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(database_uri, uri=True)
    except sqlite3.DatabaseError:
        return False

    try:
        row = connection.execute(
            """
            SELECT 1
            FROM aps_content_linkage
            WHERE run_id = ? AND accession_number LIKE ?
            LIMIT 1
            """,
            (runtime.run_id, f"{prefix}%"),
        ).fetchone()
    except sqlite3.DatabaseError:
        return False
    finally:
        connection.close()

    return row is not None


def discover_passed_runtimes() -> list[AuditedReviewRuntime]:
    runtimes: list[AuditedReviewRuntime] = []
    runtime_parents = [candidate for candidate in RUNTIME_PARENTS if candidate.exists()]
    if not runtime_parents:
        return runtimes

    seen_runtime_dirs: set[str] = set()
    for runtime_parent in runtime_parents:
        for runtime_dir in sorted((p for p in runtime_parent.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
            resolved_runtime_dir = runtime_dir.resolve()
            runtime_key = str(resolved_runtime_dir)
            if runtime_key in seen_runtime_dirs:
                continue
            seen_runtime_dirs.add(runtime_key)

            summary_path = runtime_dir / "local_corpus_e2e_summary.json"
            if not summary_path.exists():
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if summary.get("passed") is not True:
                continue

            run_id = str(summary.get("run_id") or "").strip()
            database_path = resolve_runtime_database_path(runtime_dir, summary)
            storage_dir = resolve_runtime_storage_dir(runtime_dir, summary)
            if not run_id or database_path is None or storage_dir is None:
                continue

            runtimes.append(
                AuditedReviewRuntime(
                    runtime_dir=resolved_runtime_dir,
                    summary=summary,
                    run_id=run_id,
                    db_path=database_path,
                    storage_dir=storage_dir,
                )
            )
    preferred_runtimes = [runtime for runtime in runtimes if _runtime_has_accession_prefix(runtime, "LOCALAPS")]
    return preferred_runtimes or runtimes


def latest_passed_runtime() -> AuditedReviewRuntime:
    runtimes = discover_passed_runtimes()
    assert runtimes, f"No passed local-corpus runtime found under {RUNTIME_PARENT}"
    selected_runtime = runtimes[0]
    if not INITIAL_STORAGE_DIR:
        selected_storage_root = selected_runtime.runtime_dir.parent.resolve()
        os.environ["STORAGE_DIR"] = str(selected_storage_root)
        settings.storage_dir = str(selected_storage_root)
    return selected_runtime


def _runtime_has_document_targets(runtime: AuditedReviewRuntime) -> bool:
    database_uri = f"{runtime.db_path.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(database_uri, uri=True)
    except sqlite3.DatabaseError:
        return False

    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM connector_run_target WHERE connector_run_id = ?",
            (runtime.run_id,),
        ).fetchone()
    except sqlite3.DatabaseError:
        return False
    finally:
        connection.close()

    target_count = int(row[0] or 0) if row else 0
    return target_count > 0


def discover_document_trace_ready_runtimes() -> list[AuditedReviewRuntime]:
    return [runtime for runtime in discover_passed_runtimes() if _runtime_has_document_targets(runtime)]


def latest_document_trace_ready_runtime() -> AuditedReviewRuntime:
    runtimes = discover_document_trace_ready_runtimes()
    assert runtimes, f"No document-trace-ready local-corpus runtime found under {RUNTIME_PARENT}"
    selected_runtime = runtimes[0]
    if not INITIAL_STORAGE_DIR:
        selected_storage_root = selected_runtime.runtime_dir.parent.resolve()
        os.environ["STORAGE_DIR"] = str(selected_storage_root)
        settings.storage_dir = str(selected_storage_root)
    return selected_runtime


def make_session(runtime: AuditedReviewRuntime) -> Session:
    engine = create_engine(f"sqlite:///{runtime.db_path.as_posix()}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def resolve_target_for_accession(session: Session, run_id: str, accession_number: str = "LOCALAPS00001") -> tuple[str, str]:
    linkage = (
        session.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == run_id,
            ApsContentLinkage.accession_number == accession_number,
        )
        .order_by(ApsContentLinkage.target_id.asc())
        .first()
    )
    assert linkage is not None, f"Could not find target for accession {accession_number} in run {run_id}"
    return linkage.target_id, accession_number


def resolve_deduplicated_target_pair(session: Session, run_id: str) -> tuple[str, str]:
    shared_content_id = (
        session.query(ApsContentLinkage.content_id)
        .filter(ApsContentLinkage.run_id == run_id)
        .group_by(ApsContentLinkage.content_id)
        .having(func.count(ApsContentLinkage.target_id) > 1)
        .order_by(ApsContentLinkage.content_id.asc())
        .first()
    )
    assert shared_content_id is not None, f"Could not find deduplicated content in run {run_id}"

    target_ids = [
        row[0]
        for row in (
            session.query(ApsContentLinkage.target_id)
            .filter(
                ApsContentLinkage.run_id == run_id,
                ApsContentLinkage.content_id == shared_content_id[0],
            )
            .order_by(ApsContentLinkage.target_id.asc())
            .all()
        )
    ]
    assert len(target_ids) >= 2, f"Expected at least two targets for deduplicated content in run {run_id}"
    return target_ids[0], target_ids[1]
