from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from app.models.models import ApsContentLinkage


TESTS_ROOT = Path(__file__).resolve().parent
RUNTIME_PARENT = TESTS_ROOT.parent / "app" / "storage_test_runtime" / "lc_e2e"


@dataclass(frozen=True)
class AuditedReviewRuntime:
    runtime_dir: Path
    summary: dict
    run_id: str
    db_path: Path
    storage_dir: Path


def discover_passed_runtimes() -> list[AuditedReviewRuntime]:
    runtimes: list[AuditedReviewRuntime] = []
    if not RUNTIME_PARENT.exists():
        return runtimes

    for runtime_dir in sorted((p for p in RUNTIME_PARENT.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
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
        database_path = Path(str(summary.get("database_path") or "")).resolve()
        storage_dir = Path(str(summary.get("storage_dir") or "")).resolve()
        if not run_id or not database_path.exists() or not storage_dir.exists():
            continue

        runtimes.append(
            AuditedReviewRuntime(
                runtime_dir=runtime_dir.resolve(),
                summary=summary,
                run_id=run_id,
                db_path=database_path,
                storage_dir=storage_dir,
            )
        )
    return runtimes


def latest_passed_runtime() -> AuditedReviewRuntime:
    runtimes = discover_passed_runtimes()
    assert runtimes, f"No passed local-corpus runtime found under {RUNTIME_PARENT}"
    return runtimes[0]


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
