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
from app.services import nrc_aps_evidence_report  # noqa: E402
from app.services import nrc_aps_evidence_report_export  # noqa: E402
from app.services import nrc_aps_evidence_report_export_contract as contract  # noqa: E402


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


def _seed_report_index_rows(db, *, reports_dir: Path, run_id: str = "run-evidence-report-export-1") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target_a = ConnectorRunTarget(
        connector_run_target_id="target-evidence-report-export-1",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    target_b = ConnectorRunTarget(
        connector_run_target_id="target-evidence-report-export-2",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=1,
    )
    db.add(run)
    db.add(target_a)
    db.add(target_b)

    refs_a = _write_refs(reports_dir, "report_export_refs_a", "alpha alpha beta alpha gamma")
    refs_b = _write_refs(reports_dir, "report_export_refs_b", "alpha delta")

    db.add(
        ApsContentDocument(
            content_id="content-report-export-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-report-export-1",
            normalized_char_count=28,
            chunk_count=2,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-report-export-1",
            chunk_id="chunk-report-export-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=16,
            chunk_text="alpha alpha beta",
            chunk_text_sha256="sha-report-export-1",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-report-export-1",
            chunk_id="chunk-report-export-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=1,
            start_char=17,
            end_char=28,
            chunk_text="alpha gamma",
            chunk_text_sha256="sha-report-export-2",
        )
    )
    db.add(
        ApsContentDocument(
            content_id="content-report-export-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-report-export-2",
            normalized_char_count=11,
            chunk_count=1,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-report-export-2",
            chunk_id="chunk-report-export-3",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=11,
            chunk_text="alpha delta",
            chunk_text_sha256="sha-report-export-3",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-report-export-1",
            run_id=run_id,
            target_id="target-evidence-report-export-1",
            accession_number="ML-REPORT-EXPORT-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=refs_a["content_units_ref"],
            normalized_text_ref=refs_a["normalized_text_ref"],
            normalized_text_sha256="norm-report-export-1",
            blob_ref=refs_a["blob_ref"],
            blob_sha256="blob-report-export-1",
            download_exchange_ref=refs_a["download_exchange_ref"],
            discovery_ref=refs_a["discovery_ref"],
            selection_ref=refs_a["selection_ref"],
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-report-export-2",
            run_id=run_id,
            target_id="target-evidence-report-export-2",
            accession_number=None,
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=refs_b["content_units_ref"],
            normalized_text_ref=refs_b["normalized_text_ref"],
            normalized_text_sha256="norm-report-export-2",
            blob_ref=refs_b["blob_ref"],
            blob_sha256="blob-report-export-2",
            download_exchange_ref=refs_b["download_exchange_ref"],
            discovery_ref=refs_b["discovery_ref"],
            selection_ref=refs_b["selection_ref"],
        )
    )
    db.commit()


def _persisted_report(db, run_id: str) -> dict:
    bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
        db,
        request_payload={"run_id": run_id, "query": "alpha", "persist_bundle": True},
    )
    citation_pack = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
        db,
        request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
    )
    return nrc_aps_evidence_report.assemble_evidence_report(
        db,
        request_payload={"citation_pack_id": citation_pack["citation_pack_id"], "persist_report": True},
    )


def test_persisted_evidence_report_export_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
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
        _seed_report_index_rows(db, reports_dir=tmp_path)

        report = _persisted_report(db, "run-evidence-report-export-1")
        preview = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": False},
        )
        first = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
        )
        second = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_ref": report["evidence_report_ref"], "persist_export": True},
        )

        assert first["evidence_report_export_id"] == second["evidence_report_export_id"]
        assert first["evidence_report_export_ref"] == second["evidence_report_export_ref"]
        assert first["evidence_report_export_checksum"] == second["evidence_report_export_checksum"] == preview["evidence_report_export_checksum"]
        assert Path(first["evidence_report_export_ref"]).exists()
        assert first["rendered_markdown"].startswith("# NRC ADAMS APS Evidence Report Export\n")
        assert "## Section 00001: Accession ML\\-REPORT\\-EXPORT\\-1 / Content content\\-report\\-export\\-1" in first["rendered_markdown"]
        assert "1. APS\\-CIT\\-00001" in first["rendered_markdown"]

        persisted = nrc_aps_evidence_report_export.get_persisted_evidence_report_export(
            evidence_report_export_id=first["evidence_report_export_id"],
        )
        assert persisted["evidence_report_export_id"] == first["evidence_report_export_id"]
        assert persisted["persisted"] is True
        assert persisted["rendered_markdown"] == first["rendered_markdown"]

        run = db.get(ConnectorRun, "run-evidence-report-export-1")
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
        assert refs.get("aps_evidence_report_exports") == [first["evidence_report_export_ref"]]
        assert refs.get("aps_evidence_report_export_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_evidence_report_export_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["evidence_report_export_id"] == first["evidence_report_export_id"]
    finally:
        db.close()
        engine.dispose()


def test_persisted_same_id_invalid_export_artifact_fails_closed_without_overwrite(monkeypatch, tmp_path: Path):
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
        run_id = "run-er-export-conflict-a"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)

        report = _persisted_report(db, run_id)
        first = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
        )

        export_path = Path(first["evidence_report_export_ref"])
        tampered = json.loads(export_path.read_text(encoding="utf-8"))
        tampered["rendered_markdown"] = tampered["rendered_markdown"] + "tampered without checksum update\n"
        tampered_text = json.dumps(tampered, indent=2, sort_keys=True)
        export_path.write_text(tampered_text, encoding="utf-8")

        with pytest.raises(nrc_aps_evidence_report_export.EvidenceReportExportError) as exc_info:
            nrc_aps_evidence_report_export.assemble_evidence_report_export(
                db,
                request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert exc_info.value.status_code == 409
        assert export_path.read_text(encoding="utf-8") == tampered_text

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
        assert refs.get("aps_evidence_report_exports") == [first["evidence_report_export_ref"]]
    finally:
        db.close()
        engine.dispose()


def test_persisted_same_id_valid_but_drifted_export_artifact_fails_closed_without_overwrite(monkeypatch, tmp_path: Path):
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
        run_id = "run-er-export-conflict-b"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)

        report = _persisted_report(db, run_id)
        first = nrc_aps_evidence_report_export.assemble_evidence_report_export(
            db,
            request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
        )

        export_path = Path(first["evidence_report_export_ref"])
        tampered = json.loads(export_path.read_text(encoding="utf-8"))
        tampered["rendered_markdown"] = tampered["rendered_markdown"].replace("Source Evidence Report ID: ", "Source Evidence Report ID: tampered-")
        tampered["rendered_markdown_sha256"] = contract.compute_rendered_markdown_sha256(tampered["rendered_markdown"])
        tampered["evidence_report_export_checksum"] = contract.compute_evidence_report_export_checksum(tampered)
        tampered_text = json.dumps(tampered, indent=2, sort_keys=True)
        export_path.write_text(tampered_text, encoding="utf-8")

        validated_payload, _validated_path = nrc_aps_evidence_report_export.load_persisted_evidence_report_export_artifact(
            evidence_report_export_ref=export_path,
        )
        assert validated_payload["rendered_markdown"] == tampered["rendered_markdown"]

        with pytest.raises(nrc_aps_evidence_report_export.EvidenceReportExportError) as exc_info:
            nrc_aps_evidence_report_export.assemble_evidence_report_export(
                db,
                request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert exc_info.value.status_code == 409
        assert export_path.read_text(encoding="utf-8") == tampered_text

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
        assert refs.get("aps_evidence_report_exports") == [first["evidence_report_export_ref"]]
    finally:
        db.close()
        engine.dispose()


def test_persisted_failure_artifact_is_source_report_scoped(monkeypatch, tmp_path: Path):
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
        run_id = "run-er-exp-fail"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)

        report = _persisted_report(db, run_id)
        report_path = Path(report["evidence_report_ref"])
        tampered = json.loads(report_path.read_text(encoding="utf-8"))
        tampered["sections"][0]["title"] = "Tampered report title"
        tampered["evidence_report_checksum"] = nrc_aps_evidence_report.contract.compute_evidence_report_checksum(tampered)
        report_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8")

        with pytest.raises(nrc_aps_evidence_report_export.EvidenceReportExportError) as exc_info:
            nrc_aps_evidence_report_export.assemble_evidence_report_export(
                db,
                request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_REPORT_INVALID

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
        assert refs.get("aps_evidence_report_exports") == []
        failure_refs = list(refs.get("aps_evidence_report_export_failures") or [])
        assert len(failure_refs) == 1
        failure_payload = json.loads(Path(failure_refs[0]).read_text(encoding="utf-8"))
        assert failure_payload["schema_id"] == contract.APS_EVIDENCE_REPORT_EXPORT_FAILURE_SCHEMA_ID
        assert failure_payload["error_code"] == contract.APS_RUNTIME_FAILURE_SOURCE_REPORT_INVALID
        assert run.status == "completed"
    finally:
        db.close()
        engine.dispose()


def test_hidden_run_persist_export_fails_closed_without_shared_refs(monkeypatch, tmp_path: Path):
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
        run_id = "run-er-export-hidden"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)

        report = _persisted_report(db, run_id)
        run = db.get(ConnectorRun, run_id)
        run.request_config_json = {"visual_lane_mode": "variant_hidden"}
        db.commit()

        with pytest.raises(nrc_aps_evidence_report_export.EvidenceReportExportError) as exc_info:
            nrc_aps_evidence_report_export.assemble_evidence_report_export(
                db,
                request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        assert exc_info.value.status_code == 422

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_report_refs") or {})
        assert refs.get("aps_evidence_report_exports") in (None, [])
        assert refs.get("aps_evidence_report_export_failures") in (None, [])
        assert list(tmp_path.glob("*_aps_evidence_report_export_v1.json")) == []
        assert list(tmp_path.glob("*_aps_evidence_report_export_failure_v1.json")) == []
    finally:
        db.close()
        engine.dispose()
