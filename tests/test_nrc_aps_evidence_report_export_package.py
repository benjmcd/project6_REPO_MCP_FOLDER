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
from app.services import nrc_aps_evidence_report_export_package  # noqa: E402
from app.services import nrc_aps_evidence_report_export_package_contract as contract  # noqa: E402


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


def _seed_report_index_rows(db, *, reports_dir: Path, run_id: str) -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target_a = ConnectorRunTarget(
        connector_run_target_id=f"target-{run_id}-1",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    target_b = ConnectorRunTarget(
        connector_run_target_id=f"target-{run_id}-2",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=1,
    )
    db.add(run)
    db.add(target_a)
    db.add(target_b)

    refs_a = _write_refs(reports_dir, f"{run_id}_refs_a", "alpha alpha beta alpha gamma")
    refs_b = _write_refs(reports_dir, f"{run_id}_refs_b", "alpha delta")

    db.add(
        ApsContentDocument(
            content_id=f"content-{run_id}-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256=f"norm-{run_id}-1",
            normalized_char_count=28,
            chunk_count=2,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id=f"content-{run_id}-1",
            chunk_id=f"chunk-{run_id}-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=16,
            chunk_text="alpha alpha beta",
            chunk_text_sha256=f"sha-{run_id}-1",
        )
    )
    db.add(
        ApsContentChunk(
            content_id=f"content-{run_id}-1",
            chunk_id=f"chunk-{run_id}-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=1,
            start_char=17,
            end_char=28,
            chunk_text="alpha gamma",
            chunk_text_sha256=f"sha-{run_id}-2",
        )
    )
    db.add(
        ApsContentDocument(
            content_id=f"content-{run_id}-2",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256=f"norm-{run_id}-2",
            normalized_char_count=11,
            chunk_count=1,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id=f"content-{run_id}-2",
            chunk_id=f"chunk-{run_id}-3",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=11,
            chunk_text="alpha delta",
            chunk_text_sha256=f"sha-{run_id}-3",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id=f"content-{run_id}-1",
            run_id=run_id,
            target_id=f"target-{run_id}-1",
            accession_number=f"ML-{run_id}-1",
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=refs_a["content_units_ref"],
            normalized_text_ref=refs_a["normalized_text_ref"],
            normalized_text_sha256=f"norm-{run_id}-1",
            blob_ref=refs_a["blob_ref"],
            blob_sha256=f"blob-{run_id}-1",
            download_exchange_ref=refs_a["download_exchange_ref"],
            discovery_ref=refs_a["discovery_ref"],
            selection_ref=refs_a["selection_ref"],
        )
    )
    db.add(
        ApsContentLinkage(
            content_id=f"content-{run_id}-2",
            run_id=run_id,
            target_id=f"target-{run_id}-2",
            accession_number=None,
            content_contract_id=bundle_contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=bundle_contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=refs_b["content_units_ref"],
            normalized_text_ref=refs_b["normalized_text_ref"],
            normalized_text_sha256=f"norm-{run_id}-2",
            blob_ref=refs_b["blob_ref"],
            blob_sha256=f"blob-{run_id}-2",
            download_exchange_ref=refs_b["download_exchange_ref"],
            discovery_ref=refs_b["discovery_ref"],
            selection_ref=refs_b["selection_ref"],
        )
    )
    db.commit()


def _persisted_export(db, *, run_id: str, query: str) -> dict:
    bundle = nrc_aps_evidence_bundle.assemble_evidence_bundle(
        db,
        request_payload={"run_id": run_id, "query": query, "persist_bundle": True},
    )
    citation_pack = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
        db,
        request_payload={"bundle_id": bundle["bundle_id"], "persist_pack": True},
    )
    report = nrc_aps_evidence_report.assemble_evidence_report(
        db,
        request_payload={"citation_pack_id": citation_pack["citation_pack_id"], "persist_report": True},
    )
    return nrc_aps_evidence_report_export.assemble_evidence_report_export(
        db,
        request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
    )


def test_persisted_export_package_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_report_export_package, "settings", _Settings())

        run_id = "run-er-export-package-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        export_a = _persisted_export(db, run_id=run_id, query="alpha")
        export_b = _persisted_export(db, run_id=run_id, query="delta")

        preview = nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
            db,
            request_payload={
                "evidence_report_export_ids": [
                    export_a["evidence_report_export_id"],
                    export_b["evidence_report_export_id"],
                ],
                "persist_package": False,
            },
        )
        first = nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
            db,
            request_payload={
                "evidence_report_export_ids": [
                    export_a["evidence_report_export_id"],
                    export_b["evidence_report_export_id"],
                ],
                "persist_package": True,
            },
        )
        second = nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
            db,
            request_payload={
                "evidence_report_export_refs": [
                    export_a["evidence_report_export_ref"],
                    export_b["evidence_report_export_ref"],
                ],
                "persist_package": True,
            },
        )

        assert first["evidence_report_export_package_id"] == second["evidence_report_export_package_id"]
        assert first["evidence_report_export_package_ref"] == second["evidence_report_export_package_ref"]
        assert first["evidence_report_export_package_checksum"] == second["evidence_report_export_package_checksum"]
        assert first["evidence_report_export_package_checksum"] == preview["evidence_report_export_package_checksum"]
        assert first["source_export_count"] == 2
        assert first["owner_run_id"] == run_id
        assert Path(first["evidence_report_export_package_ref"]).exists()

        persisted = nrc_aps_evidence_report_export_package.get_persisted_evidence_report_export_package(
            evidence_report_export_package_id=first["evidence_report_export_package_id"]
        )
        assert persisted["persisted"] is True
        assert persisted["ordered_source_exports_sha256"] == first["ordered_source_exports_sha256"]

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_package_report_refs") or {})
        assert refs.get("aps_evidence_report_export_packages") == [first["evidence_report_export_package_ref"]]
        assert refs.get("aps_evidence_report_export_package_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_evidence_report_export_package_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["evidence_report_export_package_id"] == first["evidence_report_export_package_id"]
    finally:
        db.close()
        engine.dispose()


def test_cross_run_package_is_rejected_as_operational_policy(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_report_export_package, "settings", _Settings())

        _seed_report_index_rows(db, reports_dir=tmp_path, run_id="run-er-export-package-2a")
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id="run-er-export-package-2b")
        export_a = _persisted_export(db, run_id="run-er-export-package-2a", query="alpha")
        export_b = _persisted_export(db, run_id="run-er-export-package-2b", query="alpha")

        with pytest.raises(nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError) as exc_info:
            nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
                db,
                request_payload={
                    "evidence_report_export_refs": [
                        export_a["evidence_report_export_ref"],
                        export_b["evidence_report_export_ref"],
                    ],
                    "persist_package": True,
                },
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED
        assert exc_info.value.status_code == 409
    finally:
        db.close()
        engine.dispose()


def test_persisted_same_id_drifted_package_artifact_fails_closed_without_overwrite(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_report_export_package, "settings", _Settings())

        run_id = "run-er-export-package-3"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        export_a = _persisted_export(db, run_id=run_id, query="alpha")
        export_b = _persisted_export(db, run_id=run_id, query="delta")
        package = nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
            db,
            request_payload={
                "evidence_report_export_ids": [
                    export_a["evidence_report_export_id"],
                    export_b["evidence_report_export_id"],
                ],
                "persist_package": True,
            },
        )

        package_path = Path(package["evidence_report_export_package_ref"])
        tampered = json.loads(package_path.read_text(encoding="utf-8"))
        tampered["source_exports"][0], tampered["source_exports"][1] = tampered["source_exports"][1], tampered["source_exports"][0]
        for index, row in enumerate(tampered["source_exports"], start=1):
            row["export_ordinal"] = index
        tampered["ordered_source_exports_sha256"] = contract.ordered_source_exports_sha256(tampered["source_exports"])
        tampered["evidence_report_export_package_checksum"] = contract.compute_evidence_report_export_package_checksum(tampered)
        tampered_text = json.dumps(tampered, indent=2, sort_keys=True) + "\n"
        package_path.write_text(tampered_text, encoding="utf-8")

        with pytest.raises(nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError) as exc_info:
            nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
                db,
                request_payload={
                    "evidence_report_export_ids": [
                        export_a["evidence_report_export_id"],
                        export_b["evidence_report_export_id"],
                    ],
                    "persist_package": True,
                },
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert exc_info.value.status_code == 409
        assert package_path.read_text(encoding="utf-8") == tampered_text
    finally:
        db.close()
        engine.dispose()


def test_hidden_run_persist_package_fails_closed_without_shared_refs(monkeypatch, tmp_path: Path):
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
        monkeypatch.setattr(nrc_aps_evidence_report_export_package, "settings", _Settings())

        run_id = "run-er-export-package-hidden"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        export_a = _persisted_export(db, run_id=run_id, query="alpha")
        export_b = _persisted_export(db, run_id=run_id, query="delta")

        run = db.get(ConnectorRun, run_id)
        run.request_config_json = {"visual_lane_mode": "variant_hidden"}
        db.commit()

        with pytest.raises(nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError) as exc_info:
            nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
                db,
                request_payload={
                    "evidence_report_export_ids": [
                        export_a["evidence_report_export_id"],
                        export_b["evidence_report_export_id"],
                    ],
                    "persist_package": True,
                },
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST
        assert exc_info.value.status_code == 422

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_evidence_report_export_package_report_refs") or {})
        assert refs.get("aps_evidence_report_export_packages") in (None, [])
        assert refs.get("aps_evidence_report_export_package_failures") in (None, [])
        assert list(tmp_path.glob("*_aps_evidence_report_export_package_v1.json")) == []
        assert list(tmp_path.glob("*_aps_evidence_report_export_package_failure_v1.json")) == []
    finally:
        db.close()
        engine.dispose()
