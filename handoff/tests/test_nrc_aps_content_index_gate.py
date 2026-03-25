import hashlib
import json
import os
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget  # noqa: E402
from app.services import nrc_aps_content_index  # noqa: E402
from app.services import nrc_aps_content_index_gate  # noqa: E402


def test_validate_content_index_gate_fail_closed_and_pass(tmp_path: Path, monkeypatch):
    Base.metadata.create_all(bind=engine)
    run_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    content_id = f"content-{uuid.uuid4().hex}"
    chunk_id = f"chunk-{uuid.uuid4().hex}"

    class _Settings:
        connector_reports_dir = str(tmp_path)

    monkeypatch.setattr(nrc_aps_content_index_gate, "settings", _Settings())
    monkeypatch.setattr(
        nrc_aps_content_index_gate,
        "_load_candidate_runs",
        lambda run_ids, limit: [{"run_id": run_id, "status": "completed"}],
    )

    fail_report = nrc_aps_content_index_gate.validate_content_index_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "fail.json",
        require_runs=True,
    )
    assert fail_report["passed"] is False

    content_payload = {
        "schema_id": nrc_aps_content_index.APS_CONTENT_UNITS_SCHEMA_ID,
        "schema_version": 1,
        "run_id": run_id,
        "target_id": target_id,
        "accession_number": "MLTEST",
        "pipeline_mode": "download_only",
        "artifact_outcome_status": "downloaded",
        "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
        "content_id": content_id,
        "content_status": "indexed",
        "chunk_size_chars": 100,
        "chunk_overlap_chars": 10,
        "min_chunk_chars": 50,
        "normalized_char_count": 11,
        "normalized_text_ref": "/tmp/norm.txt",
        "normalized_text_sha256": "sha-norm",
        "effective_content_type": "application/pdf",
        "document_class": "born_digital_pdf",
        "quality_status": "limited",
        "page_count": 1,
        "diagnostics_ref": "/tmp/diag.json",
        "source_metadata_ref": "/tmp/meta.json",
        "blob_ref": "/tmp/blob.bin",
        "blob_sha256": "sha-blob",
        "download_exchange_ref": "/tmp/download.json",
        "discovery_ref": "/tmp/discovery.json",
        "selection_ref": "/tmp/selection.json",
        "chunk_count": 1,
        "chunks": [
            {
                "chunk_id": chunk_id,
                "chunk_ordinal": 0,
                "start_char": 0,
                "end_char": 11,
                "chunk_text": "hello world",
                "chunk_text_sha256": "sha-chunk-1",
                "page_start": 1,
                "page_end": 1,
                "unit_kind": "pdf_text_block",
            }
        ],
    }
    content_payload["payload_sha256"] = hashlib.sha256(
        json.dumps(content_payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    content_ref = nrc_aps_content_index.content_units_artifact_path(
        run_id=run_id,
        target_id=target_id,
        reports_dir=tmp_path,
    )
    nrc_aps_content_index.write_json_atomic(content_ref, content_payload)
    content_sha = hashlib.sha256(content_ref.read_bytes()).hexdigest()

    run_payload = nrc_aps_content_index.build_run_artifact_payload(
        run_id=run_id,
        run_status="completed",
        selected_targets=1,
        content_units_artifacts=[
            {
                "target_id": target_id,
                "status": "recommended",
                "ref": str(content_ref),
                "sha256": content_sha,
                "content_id": content_id,
                "content_status": "indexed",
                "chunk_count": 1,
            }
        ],
        indexing_failures=[],
    )
    nrc_aps_content_index.write_json_atomic(
        nrc_aps_content_index.run_artifact_path(run_id=run_id, reports_dir=tmp_path),
        run_payload,
    )

    db = SessionLocal()
    try:
        db.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system="nrc_adams_aps",
                source_mode="public_api",
                status="completed",
            )
        )
        db.add(
            ConnectorRunTarget(
                connector_run_target_id=target_id,
                connector_run_id=run_id,
                status="recommended",
                artifact_surface="files",
            )
        )
        db.add(
            ApsContentDocument(
                content_id=content_id,
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="sha-norm",
                normalized_char_count=11,
                chunk_count=1,
                content_status="indexed",
                media_type="application/pdf",
                document_class="born_digital_pdf",
                quality_status="limited",
                page_count=1,
                diagnostics_ref=None,
            )
        )
        db.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=chunk_id,
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=11,
                chunk_text="hello world",
                chunk_text_sha256="sha-chunk-1",
                page_start=1,
                page_end=1,
                unit_kind="pdf_text_block",
                quality_status="limited",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id=content_id,
                run_id=run_id,
                target_id=target_id,
                accession_number="MLTEST",
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=str(content_ref),
                normalized_text_ref="/tmp/norm.txt",
                normalized_text_sha256="sha-norm",
                blob_ref="/tmp/blob.bin",
                blob_sha256="sha-blob",
                download_exchange_ref="/tmp/download.json",
                discovery_ref="/tmp/discovery.json",
                selection_ref="/tmp/selection.json",
                diagnostics_ref="/tmp/diag.json",
            )
        )
        db.commit()
    finally:
        db.close()

    pass_report = nrc_aps_content_index_gate.validate_content_index_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "pass.json",
        require_runs=True,
    )
    assert pass_report["passed"] is True
