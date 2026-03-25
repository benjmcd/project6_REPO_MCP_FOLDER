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
from app.services import nrc_aps_evidence_report  # noqa: E402
from app.services import nrc_aps_evidence_report_export  # noqa: E402
from app.services import nrc_aps_evidence_report_export_contract as contract  # noqa: E402
from app.services import nrc_aps_evidence_report_export_gate  # noqa: E402


def _write_refs(base_dir: Path, prefix: str, text_value: str) -> dict[str, str]:
    refs_dir = base_dir / prefix
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
        (paths["normalized_text_ref"], text_value),
        (paths["blob_ref"], "blob"),
        (paths["download_exchange_ref"], "{}"),
        (paths["discovery_ref"], "{}"),
        (paths["selection_ref"], "{}"),
    ):
        path.write_text(value, encoding="utf-8")
    return {name: str(path) for name, path in paths.items()}


def _seed_report_index_rows(db, *, reports_dir: Path, run_id: str = "run-evidence-report-export-gate") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target_a = ConnectorRunTarget(
        connector_run_target_id="target-evidence-report-export-gate-1",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    target_b = ConnectorRunTarget(
        connector_run_target_id="target-evidence-report-export-gate-2",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=1,
    )
    db.add(run)
    db.add(target_a)
    db.add(target_b)

    refs_a = _write_refs(reports_dir, "report_export_gate_refs_a", "alpha alpha beta alpha gamma")
    refs_b = _write_refs(reports_dir, "report_export_gate_refs_b", "alpha delta")

    db.add(
        ApsContentDocument(
            content_id="content-report-export-gate-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-report-export-gate-1",
            normalized_char_count=28,
            chunk_count=2,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-report-export-gate-1",
            chunk_id="chunk-report-export-gate-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=16,
            chunk_text="alpha alpha beta",
            chunk_text_sha256="sha-report-export-gate-1",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-report-export-gate-1",
            chunk_id="chunk-report-export-gate-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=1,
            start_char=17,
            end_char=28,
            chunk_text="alpha gamma",
            chunk_text_sha256="sha-report-export-gate-2",
        )
    )
    db.add(
        ApsContentDocument(
            content_id="content-report-export-gate-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-report-export-gate-2",
            normalized_char_count=11,
            chunk_count=1,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-report-export-gate-2",
            chunk_id="chunk-report-export-gate-3",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=11,
            chunk_text="alpha delta",
            chunk_text_sha256="sha-report-export-gate-3",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-report-export-gate-1",
            run_id=run_id,
            target_id="target-evidence-report-export-gate-1",
            accession_number="ML-REPORT-EXPORT-GATE-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=refs_a["content_units_ref"],
            normalized_text_ref=refs_a["normalized_text_ref"],
            normalized_text_sha256="norm-report-export-gate-1",
            blob_ref=refs_a["blob_ref"],
            blob_sha256="blob-report-export-gate-1",
            download_exchange_ref=refs_a["download_exchange_ref"],
            discovery_ref=refs_a["discovery_ref"],
            selection_ref=refs_a["selection_ref"],
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-report-export-gate-2",
            run_id=run_id,
            target_id="target-evidence-report-export-gate-2",
            accession_number=None,
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=refs_b["content_units_ref"],
            normalized_text_ref=refs_b["normalized_text_ref"],
            normalized_text_sha256="norm-report-export-gate-2",
            blob_ref=refs_b["blob_ref"],
            blob_sha256="blob-report-export-gate-2",
            download_exchange_ref=refs_b["download_exchange_ref"],
            discovery_ref=refs_b["discovery_ref"],
            selection_ref=refs_b["selection_ref"],
        )
    )
    db.commit()


def test_evidence_report_export_gate_pass_and_fail_closed_on_rendered_markdown_drift(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_report, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_report_export, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_report_export_gate, "settings", _Settings())
        monkeypatch.setattr(
            nrc_aps_evidence_report_export_gate,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": "run-evidence-report-export-gate"}],
        )

        _seed_report_index_rows(db, reports_dir=tmp_path)
        bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-report-export-gate", "query": "alpha", "persist_bundle": True},
        )
        citation_pack = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
            db,
            request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
        )
        report = nrc_aps_evidence_report.assemble_evidence_report(
            db,
            request_payload={"citation_pack_id": citation_pack["citation_pack_id"], "persist_report": True},
        )
        export = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
        )

        pass_report = nrc_aps_evidence_report_export_gate.validate_evidence_report_export_gate(
            run_ids=["run-evidence-report-export-gate"],
            limit=1,
            report_path=tmp_path / "pass_report.json",
            require_runs=True,
        )
        assert pass_report["passed"] is True

        export_path = Path(export["evidence_report_export_ref"])
        tampered = json.loads(export_path.read_text(encoding="utf-8"))
        tampered["rendered_markdown"] = tampered["rendered_markdown"].replace("Source Evidence Report ID: ", "Source Evidence Report ID: drift-")
        tampered["rendered_markdown_sha256"] = contract.compute_rendered_markdown_sha256(tampered["rendered_markdown"])
        tampered["evidence_report_export_checksum"] = contract.compute_evidence_report_export_checksum(tampered)
        export_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8-sig")

        fail_report = nrc_aps_evidence_report_export_gate.validate_evidence_report_export_gate(
            run_ids=["run-evidence-report-export-gate"],
            limit=1,
            report_path=tmp_path / "fail_report.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_RENDERED_MARKDOWN_DRIFT in reasons
    finally:
        db.close()
        engine.dispose()


def test_evidence_report_export_gate_fails_closed_on_source_report_mismatch(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_report, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_report_export, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_report_export_gate, "settings", _Settings())
        monkeypatch.setattr(
            nrc_aps_evidence_report_export_gate,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": "run-evidence-report-export-gate"}],
        )

        _seed_report_index_rows(db, reports_dir=tmp_path)
        bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-report-export-gate", "query": "alpha", "persist_bundle": True},
        )
        citation_pack = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
            db,
            request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
        )
        report = nrc_aps_evidence_report.assemble_evidence_report(
            db,
            request_payload={"citation_pack_id": citation_pack["citation_pack_id"], "persist_report": True},
        )
        export = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
        )

        export_path = Path(export["evidence_report_export_ref"])
        tampered = json.loads(export_path.read_text(encoding="utf-8"))
        tampered["source_evidence_report"]["evidence_report_id"] = "tampered-report-id"
        tampered["evidence_report_export_checksum"] = contract.compute_evidence_report_export_checksum(tampered)
        export_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8-sig")

        fail_report = nrc_aps_evidence_report_export_gate.validate_evidence_report_export_gate(
            run_ids=["run-evidence-report-export-gate"],
            limit=1,
            report_path=tmp_path / "fail_report_source.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_SOURCE_REPORT_MISMATCH in reasons
    finally:
        db.close()
        engine.dispose()
