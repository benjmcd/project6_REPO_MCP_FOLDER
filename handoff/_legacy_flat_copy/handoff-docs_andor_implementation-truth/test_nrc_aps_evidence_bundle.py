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
from app.services import nrc_aps_evidence_bundle_contract as contract  # noqa: E402


def _seed_index_rows(db, *, reports_dir: Path, run_id: str = "run-evidence-1") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-evidence-1",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    db.add(run)
    db.add(target)

    refs_dir = reports_dir / "evidence_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    content_units_ref = refs_dir / "content_units.json"
    normalized_text_ref = refs_dir / "normalized.txt"
    blob_ref = refs_dir / "blob.bin"
    download_exchange_ref = refs_dir / "download_exchange.json"
    discovery_ref = refs_dir / "discovery_exchange.json"
    selection_ref = refs_dir / "selection_manifest.json"
    for path, value in (
        (content_units_ref, "{}"),
        (normalized_text_ref, "alpha beta gamma"),
        (blob_ref, "blob-bytes"),
        (download_exchange_ref, "{}"),
        (discovery_ref, "{}"),
        (selection_ref, "{}"),
    ):
        path.write_text(value, encoding="utf-8")

    document = ApsContentDocument(
        content_id="content-evidence-1",
        content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
        normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
        normalized_text_sha256="norm-sha",
        normalized_char_count=32,
        chunk_count=2,
        content_status="indexed",
    )
    db.add(document)

    db.add(
        ApsContentChunk(
            content_id="content-evidence-1",
            chunk_id="chunk-evidence-1",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=12,
            chunk_text="alpha beta",
            chunk_text_sha256="sha-chunk-1",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-evidence-1",
            chunk_id="chunk-evidence-2",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=1,
            start_char=13,
            end_char=24,
            chunk_text="gamma delta",
            chunk_text_sha256="sha-chunk-2",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-evidence-1",
            run_id=run_id,
            target_id="target-evidence-1",
            accession_number="MLTEST-1",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=str(content_units_ref),
            normalized_text_ref=str(normalized_text_ref),
            normalized_text_sha256="norm-sha",
            blob_ref=str(blob_ref),
            blob_sha256="blob-sha",
            download_exchange_ref=str(download_exchange_ref),
            discovery_ref=str(discovery_ref),
            selection_ref=str(selection_ref),
        )
    )
    db.commit()


def test_assemble_query_and_browse_modes(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        _seed_index_rows(db, reports_dir=tmp_path)

        query_response = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-1", "query": "alpha", "persist_bundle": False},
        )
        assert query_response["mode"] == contract.APS_MODE_QUERY
        assert query_response["total_hits"] == 1
        assert query_response["items"][0]["chunk_id"] == "chunk-evidence-1"
        assert query_response["items"][0]["highlight_spans"]

        browse_response = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-1", "query": None, "persist_bundle": False},
        )
        assert browse_response["mode"] == contract.APS_MODE_BROWSE
        assert browse_response["total_hits"] == 2
        assert browse_response["total_groups"] == 1
    finally:
        db.close()
        engine.dispose()


def test_persisted_bundle_is_immutable_and_snapshot_sensitive(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        _seed_index_rows(db, reports_dir=tmp_path)

        first = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-1", "persist_bundle": True},
        )
        second = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-1", "persist_bundle": True, "limit": 1, "offset": 1},
        )
        assert first["bundle_id"] == second["bundle_id"]
        assert first["bundle_ref"] == second["bundle_ref"]
        assert Path(first["bundle_ref"]).exists()
        run = db.get(ConnectorRun, "run-evidence-1")
        refs = dict((run.query_plan_json or {}).get("aps_evidence_bundle_report_refs") or {})
        assert refs.get("aps_evidence_bundles") == [first["bundle_ref"]]
        assert refs.get("aps_evidence_bundle_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_evidence_bundle_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["bundle_id"] == first["bundle_id"]

        db.add(
            ApsContentChunk(
                content_id="content-evidence-1",
                chunk_id="chunk-evidence-3",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=2,
                start_char=25,
                end_char=35,
                chunk_text="alpha zeta",
                chunk_text_sha256="sha-chunk-3",
            )
        )
        db.commit()

        changed = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-1", "persist_bundle": True},
        )
        assert changed["bundle_id"] != first["bundle_id"]
    finally:
        db.close()
        engine.dispose()


def test_persisted_failure_artifact_is_request_scoped(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        _seed_index_rows(db, reports_dir=tmp_path)

        linkage = db.query(ApsContentLinkage).filter(ApsContentLinkage.run_id == "run-evidence-1").first()
        assert linkage is not None
        linkage.selection_ref = None
        db.commit()

        with pytest.raises(nrc_aps_evidence_bundle.EvidenceBundleError) as exc_info:
            nrc_aps_evidence_bundle.assemble_evidence_bundle(
                db,
                request_payload={"run_id": "run-evidence-1", "persist_bundle": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_PROVENANCE_MISSING

        run = db.get(ConnectorRun, "run-evidence-1")
        refs = dict((run.query_plan_json or {}).get("aps_evidence_bundle_report_refs") or {})
        assert refs.get("aps_evidence_bundles") == []
        failure_refs = list(refs.get("aps_evidence_bundle_failures") or [])
        assert len(failure_refs) == 1
        failure_ref = str(failure_refs[0] or "")
        assert failure_ref
        failure_payload = json.loads(Path(failure_ref).read_text(encoding="utf-8"))
        assert failure_payload["schema_id"] == contract.APS_EVIDENCE_BUNDLE_FAILURE_SCHEMA_ID
        assert run.status == "completed"
    finally:
        db.close()
        engine.dispose()
