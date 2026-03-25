from __future__ import annotations

"""
PROVISIONAL PHASE 8 HANDOFF BRIDGE (index_builder.py)
Status: PROVISIONAL / BOOTSTRAP ONLY
Milestone: Phase 8 (Extraction -> Insight)
Authority: Phase 8 Provisional Baseline

Notes: 
- This bridge is used for bootstrapping the Evidence Layer from Phase 7A artifacts.
- Implements a 'Synthetic Run' strategy to satisfy referential integrity in standalone environments.
- Mapping contract defined in: docs/nrc_adams/phase_8_contract.md
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    Base,
    ConnectorRun,
    ConnectorRunTarget,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants matching Phase 8 Contract



def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_synthetic_run(db: Session, run_id: str) -> ConnectorRun:
    run = db.get(ConnectorRun, run_id)
    if not run:
        logger.info(f"Creating synthetic ConnectorRun: {run_id}")
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            source_system="nrc_adams_aps",
            source_mode="advanced_validation",
            status="accepted-state",
            submitted_at=_utc_now(),
            started_at=_utc_now(),
            completed_at=_utc_now(),
            query_plan_json={"note": "Synthetic run created by index_builder.py"},
        )
        db.add(run)
        db.commit()
        db.refresh(run)
    return run


def ensure_synthetic_target(db: Session, run_id: str, target_key: str) -> ConnectorRunTarget:
    # Deterministic UUID based on run_id and a unique target key (full directory name)
    target_id_seed = f"{run_id}:{target_key}"
    target_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, target_id_seed))
    
    target = db.get(ConnectorRunTarget, target_id)
    if not target:
        logger.info(f"Creating synthetic ConnectorRunTarget: {target_id} for {target_key}")
        target = ConnectorRunTarget(
            connector_run_target_id=target_id,
            connector_run_id=run_id,
            stable_release_key=target_key,
            source_artifact_key=target_key,
            status="ingested",
            discovered_at=_utc_now(),
            selected_at=_utc_now(),
            downloaded_at=_utc_now(),
            ingested_at=_utc_now(),
        )
        db.add(target)
        db.commit()
        db.refresh(target)
    return target


def ingest_phase_7a_result(
    db: Session,
    result_path: Path,
    run_id: str,
) -> str:
    with result_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    accession_number = data.get("accession_number")
    if not accession_number:
        accession_number = data.get("metadata", {}).get("accession_number")
    
    if not accession_number:
        accession_number = result_path.parent.name.split("_")[-1]

    logger.info(f"Ingesting accession: {accession_number}")

    ensure_synthetic_run(db, run_id)
    if accession_number:
        target_key = f"{accession_number}_{result_path.parent.name}"
    else:
        target_key = result_path.parent.name
    target = ensure_synthetic_target(db, run_id, target_key)

    # Use strict canonical functions instead of custom logic.
    from app.services import nrc_aps_content_index
    
    chunking_policy = nrc_aps_content_index.normalize_chunking_policy({
        "content_chunk_size_chars": nrc_aps_content_index.APS_CONTENT_INDEX_DEFAULT_CHUNK_SIZE,
        "content_chunk_overlap_chars": nrc_aps_content_index.APS_CONTENT_INDEX_DEFAULT_CHUNK_OVERLAP,
        "content_chunk_min_chars": nrc_aps_content_index.APS_CONTENT_INDEX_DEFAULT_MIN_CHUNK,
    })

    # Since we are natively standalone, we bypass pipeline extraction routing entirely 
    # and directly construct the materialization arguments required for Canonical DB Upserting.
    
    text = str(data.get("normalized_text") or "")
    normalized_text_sha256 = data.get("normalized_text_sha256") or hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    content_id = nrc_aps_content_index._content_id(
        normalized_text_sha256=normalized_text_sha256,
        accession_number=accession_number,
        content_status=nrc_aps_content_index.APS_CONTENT_STATUS_INDEXED,
        availability_reason=None
    )
    
    base_chunks = nrc_aps_content_index.chunk_document_units(
        ordered_units=data.get("ordered_units", []),
        chunk_size_chars=int(chunking_policy["chunk_size_chars"]),
        chunk_overlap_chars=int(chunking_policy["chunk_overlap_chars"]),
        min_chunk_chars=int(chunking_policy["min_chunk_chars"]),
    )
    
    chunks = [
        {
            **item,
            "chunk_id": nrc_aps_content_index._chunk_id(
                content_id=content_id,
                chunk_ordinal=int(item["chunk_ordinal"]),
                start_char=int(item["start_char"]),
                end_char=int(item["end_char"]),
                chunk_text_sha256=str(item["chunk_text_sha256"]),
            ),
        }
        for item in base_chunks
    ]

    payload = {
        "run_id": run_id,
        "target_id": target.connector_run_target_id,
        "accession_number": accession_number,
        "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": data.get("normalization_contract_id", nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID),
        "content_id": content_id,
        "content_status": nrc_aps_content_index.APS_CONTENT_STATUS_INDEXED,
        "normalized_char_count": data.get("normalized_char_count") or len(text),
        "normalized_text_sha256": normalized_text_sha256,
        "effective_content_type": str(data.get("effective_content_type") or ""),
        "document_class": str(data.get("document_class") or ""),
        "quality_status": str(data.get("quality_status") or ""),
        "page_count": int(data.get("page_count") or 0),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "content_units_ref": result_path.relative_to(result_path.parent.parent.parent).as_posix(),
    }
    
    text_path = result_path.parent / "text.md"
    if text_path.exists():
        payload["normalized_text_ref"] = str(text_path)

    # 2. Upsert using canonical DB logic
    nrc_aps_content_index.upsert_content_units_payload(db, payload=payload)
    
    return accession_number


def run_bridge(report_dir: Path, run_id: str):
    logger.info(f"Starting Phase 8 Bridge for directory: {report_dir}")
    from app.core.config import settings
    logger.info(f"Using Database URL: {settings.database_url}")
    
    # Initialize DB schema
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        results_found = 0
        # Iterate over per_file directories
        per_file_dir = report_dir / "per_file"
        if not per_file_dir.exists():
            logger.error(f"Directory {per_file_dir} does not exist.")
            return

        for result_dir in per_file_dir.iterdir():
            if result_dir.is_dir():
                result_json = result_dir / "result.json"
                if result_json.exists():
                    try:
                        ingest_phase_7a_result(db, result_json, run_id)
                        results_found += 1
                    except Exception as e:
                        logger.error(f"Failed to ingest {result_json}: {e}")
                        db.rollback()
        # Explicitly commit the transaction to make materialization durable
        db.commit()
        logger.info(f"Handoff Bridge complete. Ingested {results_found} documents.")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python nrc_adams_index_builder.py <report_dir> <run_id>")
        sys.exit(1)
        
    run_bridge(Path(sys.argv[1]), sys.argv[2])
