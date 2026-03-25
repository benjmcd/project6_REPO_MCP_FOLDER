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
from app.services import nrc_aps_context_dossier  # noqa: E402
from app.services import nrc_aps_context_dossier_contract as contract  # noqa: E402
from app.services import nrc_aps_context_packet  # noqa: E402
from app.services import nrc_aps_evidence_bundle  # noqa: E402
from app.services import nrc_aps_evidence_bundle_contract as bundle_contract  # noqa: E402
from app.services import nrc_aps_evidence_citation_pack  # noqa: E402
from app.services import nrc_aps_evidence_report  # noqa: E402
from app.services import nrc_aps_evidence_report_export  # noqa: E402
from app.services import nrc_aps_evidence_report_export_package  # noqa: E402


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
    db.add(run)
    db.add(
        ConnectorRunTarget(
            connector_run_target_id=f"target-{run_id}-1",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=0,
        )
    )
    db.add(
        ConnectorRunTarget(
            connector_run_target_id=f"target-{run_id}-2",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=1,
        )
    )

    refs_a = _write_refs(reports_dir, f"{run_id}_ctx_dossier_refs_a", "alpha alpha beta alpha gamma")
    refs_b = _write_refs(reports_dir, f"{run_id}_ctx_dossier_refs_b", "alpha delta")

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


def _persisted_artifacts(db, *, run_id: str, query: str) -> dict:
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
    export = nrc_aps_evidence_report_export.assemble_evidence_report_export(
        db,
        request_payload={"evidence_report_id": report["evidence_report_id"], "persist_export": True},
    )
    return {
        "bundle": bundle,
        "citation_pack": citation_pack,
        "report": report,
        "export": export,
    }


def _patch_runtime_settings(monkeypatch, tmp_path: Path) -> None:
    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_evidence_citation_pack, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_evidence_report, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_evidence_report_export, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_evidence_report_export_package, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_context_packet, "settings", _Settings())
    monkeypatch.setattr(nrc_aps_context_dossier, "settings", _Settings())


def test_persisted_context_dossier_is_immutable_and_updates_run_refs(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings(monkeypatch, tmp_path)
        run_id = "run-context-dossier-service-1"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        export_a = _persisted_artifacts(db, run_id=run_id, query="alpha")["export"]
        export_b = _persisted_artifacts(db, run_id=run_id, query="delta")["export"]
        packet_a = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={
                "evidence_report_export_id": export_a["evidence_report_export_id"],
                "persist_context_packet": True,
            },
        )
        packet_b = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={
                "evidence_report_export_id": export_b["evidence_report_export_id"],
                "persist_context_packet": True,
            },
        )

        preview = nrc_aps_context_dossier.assemble_context_dossier(
            db,
            request_payload={
                "context_packet_ids": [packet_a["context_packet_id"], packet_b["context_packet_id"]],
                "persist_dossier": False,
            },
        )
        first = nrc_aps_context_dossier.assemble_context_dossier(
            db,
            request_payload={
                "context_packet_ids": [packet_a["context_packet_id"], packet_b["context_packet_id"]],
                "persist_dossier": True,
            },
        )
        second = nrc_aps_context_dossier.assemble_context_dossier(
            db,
            request_payload={
                "context_packet_refs": [packet_a["context_packet_ref"], packet_b["context_packet_ref"]],
                "persist_dossier": True,
            },
        )

        assert first["context_dossier_id"] == second["context_dossier_id"]
        assert first["context_dossier_ref"] == second["context_dossier_ref"]
        assert first["context_dossier_checksum"] == second["context_dossier_checksum"]
        assert first["context_dossier_checksum"] == preview["context_dossier_checksum"]
        assert first["source_packet_count"] == 2
        assert first["owner_run_id"] == run_id
        assert Path(first["context_dossier_ref"]).exists()

        persisted = nrc_aps_context_dossier.get_persisted_context_dossier(
            context_dossier_id=first["context_dossier_id"]
        )
        assert persisted["persisted"] is True
        assert persisted["ordered_source_packets_sha256"] == first["ordered_source_packets_sha256"]

        run = db.get(ConnectorRun, run_id)
        refs = dict((run.query_plan_json or {}).get("aps_context_dossier_report_refs") or {})
        assert refs.get("aps_context_dossiers") == [first["context_dossier_ref"]]
        assert refs.get("aps_context_dossier_failures") == []
        summaries = list((run.query_plan_json or {}).get("aps_context_dossier_summaries") or [])
        assert len(summaries) == 1
        assert summaries[0]["context_dossier_id"] == first["context_dossier_id"]
    finally:
        db.close()
        engine.dispose()


def test_cross_run_dossier_rejected_and_failure_artifact_only_when_persist_true(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings(monkeypatch, tmp_path)
        run_a = "run-context-dossier-service-2a"
        run_b = "run-context-dossier-service-2b"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_a)
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_b)
        report_a = _persisted_artifacts(db, run_id=run_a, query="alpha")["report"]
        report_b = _persisted_artifacts(db, run_id=run_b, query="alpha")["report"]
        packet_a = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={"evidence_report_id": report_a["evidence_report_id"], "persist_context_packet": True},
        )
        packet_b = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={"evidence_report_id": report_b["evidence_report_id"], "persist_context_packet": True},
        )

        with pytest.raises(nrc_aps_context_dossier.ContextDossierError) as preview_exc:
            nrc_aps_context_dossier.assemble_context_dossier(
                db,
                request_payload={
                    "context_packet_refs": [packet_a["context_packet_ref"], packet_b["context_packet_ref"]],
                    "persist_dossier": False,
                },
            )
        assert preview_exc.value.code == contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED
        assert preview_exc.value.status_code == 409
        assert list(Path(tmp_path).glob("run_*_aps_context_dossier_failure_v1.json")) == []

        with pytest.raises(nrc_aps_context_dossier.ContextDossierError) as persist_exc:
            nrc_aps_context_dossier.assemble_context_dossier(
                db,
                request_payload={
                    "context_packet_refs": [packet_a["context_packet_ref"], packet_b["context_packet_ref"]],
                    "persist_dossier": True,
                },
            )
        assert persist_exc.value.code == contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED
        assert persist_exc.value.status_code == 409
        failure_paths = sorted(Path(tmp_path).glob(f"run_{run_a}_*_aps_context_dossier_failure_v1.json"))
        assert len(failure_paths) == 1
        failure_payload = json.loads(failure_paths[0].read_text(encoding="utf-8"))
        assert failure_payload["error_code"] == contract.APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED
        assert failure_payload["source_request"]["persist_dossier"] is True
        assert "_context_dossier_ref" not in failure_payload
        assert "_persisted" not in failure_payload
    finally:
        db.close()
        engine.dispose()


def test_run_scoped_persistence_prevents_collisions_across_runs(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings(monkeypatch, tmp_path)
        run_a = "run-context-dossier-service-3a"
        run_b = "run-context-dossier-service-3b"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_a)
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_b)

        def _build_two_packets(run_id: str) -> tuple[dict, dict]:
            export_a = _persisted_artifacts(db, run_id=run_id, query="alpha")["export"]
            export_b = _persisted_artifacts(db, run_id=run_id, query="delta")["export"]
            packet_a = nrc_aps_context_packet.assemble_context_packet(
                db,
                request_payload={
                    "evidence_report_export_ref": export_a["evidence_report_export_ref"],
                    "persist_context_packet": True,
                },
            )
            packet_b = nrc_aps_context_packet.assemble_context_packet(
                db,
                request_payload={
                    "evidence_report_export_ref": export_b["evidence_report_export_ref"],
                    "persist_context_packet": True,
                },
            )
            return packet_a, packet_b

        run_a_packet_1, run_a_packet_2 = _build_two_packets(run_a)
        run_b_packet_1, run_b_packet_2 = _build_two_packets(run_b)
        dossier_a = nrc_aps_context_dossier.assemble_context_dossier(
            db,
            request_payload={
                "context_packet_refs": [run_a_packet_1["context_packet_ref"], run_a_packet_2["context_packet_ref"]],
                "persist_dossier": True,
            },
        )
        dossier_b = nrc_aps_context_dossier.assemble_context_dossier(
            db,
            request_payload={
                "context_packet_refs": [run_b_packet_1["context_packet_ref"], run_b_packet_2["context_packet_ref"]],
                "persist_dossier": True,
            },
        )
        assert dossier_a["context_dossier_id"] != ""
        assert dossier_b["context_dossier_id"] != ""
        assert dossier_a["context_dossier_ref"] != dossier_b["context_dossier_ref"]
        assert Path(dossier_a["context_dossier_ref"]).exists()
        assert Path(dossier_b["context_dossier_ref"]).exists()
        assert Path(dossier_a["context_dossier_ref"]).name.startswith(f"run_{run_a}_")
        assert Path(dossier_b["context_dossier_ref"]).name.startswith(f"run_{run_b}_")
    finally:
        db.close()
        engine.dispose()


def test_incompatible_source_family_is_rejected_with_reason_and_failure_artifact(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings(monkeypatch, tmp_path)
        run_id = "run-context-dossier-service-4"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        pipeline_a = _persisted_artifacts(db, run_id=run_id, query="alpha")
        pipeline_b = _persisted_artifacts(db, run_id=run_id, query="delta")
        package = nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
            db,
            request_payload={
                "evidence_report_export_ids": [
                    pipeline_a["export"]["evidence_report_export_id"],
                    pipeline_b["export"]["evidence_report_export_id"],
                ],
                "persist_package": True,
            },
        )
        report_packet = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={
                "evidence_report_id": pipeline_a["report"]["evidence_report_id"],
                "persist_context_packet": True,
            },
        )
        package_packet = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={
                "evidence_report_export_package_id": package["evidence_report_export_package_id"],
                "persist_context_packet": True,
            },
        )
        with pytest.raises(nrc_aps_context_dossier.ContextDossierError) as exc_info:
            nrc_aps_context_dossier.assemble_context_dossier(
                db,
                request_payload={
                    "context_packet_refs": [report_packet["context_packet_ref"], package_packet["context_packet_ref"]],
                    "persist_dossier": True,
                },
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE
        assert exc_info.value.status_code == 409
        failure_paths = sorted(Path(tmp_path).glob(f"run_{run_id}_*_aps_context_dossier_failure_v1.json"))
        assert len(failure_paths) == 1
        failure_payload = json.loads(failure_paths[0].read_text(encoding="utf-8"))
        assert failure_payload["error_code"] == contract.APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE
        assert failure_payload["incompatibility_reason"] == contract.APS_RUNTIME_INCOMPAT_REASON_SOURCE_FAMILY
    finally:
        db.close()
        engine.dispose()


def test_malformed_existing_dossier_conflicts_without_overwrite(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        _patch_runtime_settings(monkeypatch, tmp_path)
        run_id = "run-context-dossier-service-5"
        _seed_report_index_rows(db, reports_dir=tmp_path, run_id=run_id)
        export_a = _persisted_artifacts(db, run_id=run_id, query="alpha")["export"]
        export_b = _persisted_artifacts(db, run_id=run_id, query="delta")["export"]
        packet_a = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={
                "evidence_report_export_id": export_a["evidence_report_export_id"],
                "persist_context_packet": True,
            },
        )
        packet_b = nrc_aps_context_packet.assemble_context_packet(
            db,
            request_payload={
                "evidence_report_export_id": export_b["evidence_report_export_id"],
                "persist_context_packet": True,
            },
        )
        dossier = nrc_aps_context_dossier.assemble_context_dossier(
            db,
            request_payload={
                "context_packet_ids": [packet_a["context_packet_id"], packet_b["context_packet_id"]],
                "persist_dossier": True,
            },
        )
        dossier_path = Path(dossier["context_dossier_ref"])
        tampered = json.loads(dossier_path.read_text(encoding="utf-8"))
        tampered["total_facts"] = 999
        tampered["context_dossier_checksum"] = contract.compute_context_dossier_checksum(tampered)
        tampered_text = json.dumps(tampered, indent=2, sort_keys=True) + "\n"
        dossier_path.write_text(tampered_text, encoding="utf-8")

        with pytest.raises(nrc_aps_context_dossier.ContextDossierError) as exc_info:
            nrc_aps_context_dossier.assemble_context_dossier(
                db,
                request_payload={
                    "context_packet_ids": [packet_a["context_packet_id"], packet_b["context_packet_id"]],
                    "persist_dossier": True,
                },
            )
        assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
        assert exc_info.value.status_code == 409
        assert contract.APS_RUNTIME_FAILURE_DOSSIER_INVALID in exc_info.value.message
        assert dossier_path.read_text(encoding="utf-8") == tampered_text
    finally:
        db.close()
        engine.dispose()


def test_id_only_retrieval_fails_closed_when_multiple_run_scoped_matches_exist(monkeypatch, tmp_path: Path):
    class _Settings:
        connector_reports_dir = str(tmp_path)
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr(nrc_aps_context_dossier, "settings", _Settings())

    def _synthetic_context_packet(*, run_id: str, packet_id: str, packet_checksum: str, packet_ref: str) -> dict:
        return {
            "schema_id": "aps.context_packet.v1",
            "schema_version": 1,
            "generated_at_utc": "2026-03-12T00:00:00Z",
            "context_packet_id": packet_id,
            "context_packet_checksum": packet_checksum,
            "_context_packet_ref": packet_ref,
            "projection_contract_id": "aps_context_packet_projection_v1",
            "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
            "source_family": "evidence_report_export_package",
            "source_descriptor": {
                "source_id": f"source-{packet_id}",
                "source_checksum": f"source-sum-{packet_id}",
                "owner_run_id": run_id,
            },
            "objective": "normalize_persisted_source_for_downstream_consumption",
            "total_facts": 3,
            "total_caveats": 2,
            "total_constraints": 1,
            "total_unresolved_questions": 1,
        }

    run_a_payload = contract.build_context_dossier_payload(
        [
            _synthetic_context_packet(
                run_id="run-id-only-ambig-a",
                packet_id="packet-1",
                packet_checksum="sum-1",
                packet_ref="C:/tmp/run-a-packet-1.json",
            ),
            _synthetic_context_packet(
                run_id="run-id-only-ambig-a",
                packet_id="packet-2",
                packet_checksum="sum-2",
                packet_ref="C:/tmp/run-a-packet-2.json",
            ),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    run_b_payload = contract.build_context_dossier_payload(
        [
            _synthetic_context_packet(
                run_id="run-id-only-ambig-b",
                packet_id="packet-1",
                packet_checksum="sum-1",
                packet_ref="C:/tmp/run-b-packet-1.json",
            ),
            _synthetic_context_packet(
                run_id="run-id-only-ambig-b",
                packet_id="packet-2",
                packet_checksum="sum-2",
                packet_ref="C:/tmp/run-b-packet-2.json",
            ),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert run_a_payload["context_dossier_id"] == run_b_payload["context_dossier_id"]

    dossier_id = str(run_a_payload["context_dossier_id"])
    path_a = tmp_path / contract.expected_context_dossier_file_name(scope="run_aaa", context_dossier_id=dossier_id)
    path_b = tmp_path / contract.expected_context_dossier_file_name(scope="run_zzz", context_dossier_id=dossier_id)
    path_a.write_text(json.dumps(run_a_payload, indent=2, sort_keys=True), encoding="utf-8")
    path_b.write_text(json.dumps(run_b_payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(nrc_aps_context_dossier.ContextDossierError) as exc_info:
        nrc_aps_context_dossier.get_persisted_context_dossier(context_dossier_id=dossier_id)
    assert exc_info.value.code == contract.APS_RUNTIME_FAILURE_CONFLICT
    assert exc_info.value.status_code == 409
