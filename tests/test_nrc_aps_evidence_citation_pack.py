import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base  # noqa: E402
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget  # noqa: E402
from app.services import nrc_aps_evidence_bundle  # noqa: E402
from app.services import nrc_aps_evidence_bundle_contract as bundle_contract  # noqa: E402
from app.services import nrc_aps_evidence_citation_pack  # noqa: E402
from app.services import nrc_aps_evidence_citation_pack_contract as contract  # noqa: E402


def _seed_index_rows(db, *, reports_dir: Path, run_id: str = "run-citation-pack-1") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-citation-pack-1",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    db.add(run)
    db.add(target)

    refs_dir = reports_dir / "citation_pack_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    content_units_ref = refs_dir / "content_units.json"
    normalized_text_ref = refs_dir / "normalized.txt"
    blob_ref = refs_dir / "blob.bin"
    download_exchange_ref = refs_dir / "download_exchange.json"
    discovery_ref = refs_dir / "discovery_exchange.json"
    selection_ref = refs_dir / "selection_manifest.json"
    for path, value in (
        (content_units_ref, "{}"),
        (normalized_text_ref, "alpha beta alpha gamma"),
        (blob_ref, "blob-bytes"),
        (download_exchange_ref, "{}"),
        (discovery_ref, "{}"),
        (selection_ref, "{}"),
    ):
        path.write_text(value, encoding="utf-8")

    document = ApsContentDocument(
        content_id="content-citation-pack-1",
        content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
        normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
        normalized_text_sha256="norm-citation-sha",
        normalized_char_count=22,
        chunk_count=2,
        content_status="indexed",
    )
    db.add(document)
    db.add(
        ApsContentChunk(
            content_id="content-citation-pack-1",
            chunk_id="chunk-citation-pack-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=10,
            chunk_text="alpha beta",
            chunk_text_sha256="sha-citation-1",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-citation-pack-1",
            chunk_id="chunk-citation-pack-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=1,
            start_char=11,
            end_char=22,
            chunk_text="alpha gamma",
            chunk_text_sha256="sha-citation-2",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-citation-pack-1",
            run_id=run_id,
            target_id="target-citation-pack-1",
            accession_number="ML-CITATION-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=str(content_units_ref),
            normalized_text_ref=str(normalized_text_ref),
            normalized_text_sha256="norm-citation-sha",
            blob_ref=str(blob_ref),
            blob_sha256="blob-citation-sha",
            download_exchange_ref=str(download_exchange_ref),
            discovery_ref=str(discovery_ref),
            selection_ref=str(selection_ref),
        )
    )
    db.commit()


def test_persisted_citation_pack_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_citation_pack, "settings", _Settings())
        _seed_index_rows(db, reports_dir=tmp_path)

        bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-citation-pack-1", "query": "alpha", "persist_bundle": True},
        )
        first = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
            db,
            request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
        )
        second = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
            db,
            request_payload={"bundle_ref": bundle["bundle_ref"], "persist_pack": True, "limit": 1, "offset": 1},
        )

        assert first["citation_pack_id"] == second["citation_pack_id"]
        assert first["citation_pack_ref"] == second["citation_pack_ref"]
        assert Path(first["citation_pack_ref"]).exists()
        assert first["source_bundle"]["bundle_id"] == bundle["bundle_id"]
        assert first["total_citations"] == 2
        assert first["citations"][0]["citation_label"] == "APS-CIT-00001"

        persisted = nrc_aps_evidence_citation_pack.get_persisted_citation_pack_page(
            citation_pack_id=first["citation_pack_id"],
            limit=1,
            offset=1,
        )
        assert persisted["citation_pack_id"] == first["citation_pack_id"]
        assert persisted["persisted"] is True
        assert persisted["citations"][0]["citation_label"] == "APS-CIT-00002"

        run = db.get(ConnectorRun, "run-citation-pack-1")
        refs = dict((run.query_plan_json or {}).get("aps_evidence_citation_pack_report_refs") or {})
        assert refs.get("aps_evidence_citation_packs") == [first["citation_pack_ref"]]
        assert refs.get("aps_evidence_citation_pack_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_evidence_citation_pack_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["citation_pack_id"] == first["citation_pack_id"]
    finally:
        db.close()
        engine.dispose()


def test_persisted_failure_artifact_is_source_bundle_scoped(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_citation_pack, "settings", _Settings())
        _seed_index_rows(db, reports_dir=tmp_path, run_id="run-citation-pack-failure")

        bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-citation-pack-failure", "query": "alpha", "persist_bundle": True},
        )
        bundle_path = Path(bundle["bundle_ref"])
        tampered = json.loads(bundle_path.read_text(encoding="utf-8"))
        tampered["results"][0]["content_units_ref"] = None
        tampered["bundle_checksum"] = bundle_contract.compute_bundle_checksum(tampered)
        bundle_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(nrc_aps_evidence_citation_pack.EvidenceCitationPackError) as exc_info:
            nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
                db,
                request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_PROVENANCE_MISSING

        run = db.get(ConnectorRun, "run-citation-pack-failure")
        refs = dict((run.query_plan_json or {}).get("aps_evidence_citation_pack_report_refs") or {})
        assert refs.get("aps_evidence_citation_packs") == []
        failure_refs = list(refs.get("aps_evidence_citation_pack_failures") or [])
        assert len(failure_refs) == 1
        failure_payload = json.loads(Path(failure_refs[0]).read_text(encoding="utf-8"))
        assert failure_payload["schema_id"] == contract.APS_EVIDENCE_CITATION_PACK_FAILURE_SCHEMA_ID
        assert failure_payload["error_code"] == contract.APS_RUNTIME_FAILURE_SOURCE_BUNDLE_PROVENANCE_MISSING
        assert run.status == "completed"
    finally:
        db.close()
        engine.dispose()
