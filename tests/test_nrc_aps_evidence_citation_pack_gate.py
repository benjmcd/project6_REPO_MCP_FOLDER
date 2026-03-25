import json
import os
import sys
from pathlib import Path

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
from app.services import nrc_aps_evidence_citation_pack_gate  # noqa: E402


def _seed_gate_data(db, *, reports_dir: Path, run_id: str = "run-citation-pack-gate") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-citation-pack-gate",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    db.add(run)
    db.add(target)

    refs_dir = reports_dir / "citation_pack_gate_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "content_units_ref": refs_dir / "content_units.json",
        "normalized_text_ref": refs_dir / "normalized.txt",
        "blob_ref": refs_dir / "blob.bin",
        "download_exchange_ref": refs_dir / "download_exchange.json",
        "discovery_ref": refs_dir / "discovery.json",
        "selection_ref": refs_dir / "selection.json",
    }
    for path, value in (
        (paths["content_units_ref"], "{}"),
        (paths["normalized_text_ref"], "alpha beta alpha gamma"),
        (paths["blob_ref"], "blob"),
        (paths["download_exchange_ref"], "{}"),
        (paths["discovery_ref"], "{}"),
        (paths["selection_ref"], "{}"),
    ):
        path.write_text(value, encoding="utf-8")

    db.add(
        ApsContentDocument(
            content_id="content-citation-pack-gate",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-gate",
            normalized_char_count=22,
            chunk_count=2,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-citation-pack-gate",
            chunk_id="chunk-citation-pack-gate-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=10,
            chunk_text="alpha beta",
            chunk_text_sha256="sha-gate-1",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-citation-pack-gate",
            chunk_id="chunk-citation-pack-gate-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=1,
            start_char=11,
            end_char=22,
            chunk_text="alpha gamma",
            chunk_text_sha256="sha-gate-2",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-citation-pack-gate",
            run_id=run_id,
            target_id="target-citation-pack-gate",
            accession_number="ML-CITATION-GATE",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=str(paths["content_units_ref"]),
            normalized_text_ref=str(paths["normalized_text_ref"]),
            normalized_text_sha256="norm-gate",
            blob_ref=str(paths["blob_ref"]),
            blob_sha256="blob-gate",
            download_exchange_ref=str(paths["download_exchange_ref"]),
            discovery_ref=str(paths["discovery_ref"]),
            selection_ref=str(paths["selection_ref"]),
        )
    )
    db.commit()


def test_evidence_citation_pack_gate_pass_and_fail_closed(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_citation_pack_gate, "settings", _Settings())
        monkeypatch.setattr(
            nrc_aps_evidence_citation_pack_gate,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": "run-citation-pack-gate", "status": "completed"}],
        )

        _seed_gate_data(db, reports_dir=tmp_path)
        bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-citation-pack-gate", "query": "alpha", "persist_bundle": True},
        )
        pack = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
            db,
            request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
        )

        pass_report = nrc_aps_evidence_citation_pack_gate.validate_evidence_citation_pack_gate(
            run_ids=["run-citation-pack-gate"],
            limit=1,
            report_path=tmp_path / "pass_report.json",
            require_runs=True,
        )
        assert pass_report["passed"] is True

        pack_path = Path(pack["citation_pack_ref"])
        tampered = json.loads(pack_path.read_text(encoding="utf-8"))
        tampered["citations"][0]["citation_label"] = "APS-CIT-99999"
        tampered["citation_pack_checksum"] = contract.compute_citation_pack_checksum(tampered)
        pack_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8-sig")

        fail_report = nrc_aps_evidence_citation_pack_gate.validate_evidence_citation_pack_gate(
            run_ids=["run-citation-pack-gate"],
            limit=1,
            report_path=tmp_path / "fail_report.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_DERIVATION_DRIFT in reasons
    finally:
        db.close()
        engine.dispose()
