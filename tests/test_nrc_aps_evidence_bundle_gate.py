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
from app.services import nrc_aps_evidence_bundle_contract as contract  # noqa: E402
from app.services import nrc_aps_evidence_bundle_gate  # noqa: E402


def _seed_gate_data(db, *, reports_dir: Path, run_id: str = "run-evidence-gate") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id="target-evidence-gate",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    db.add(run)
    db.add(target)

    refs_dir = reports_dir / "gate_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "content_units_ref": refs_dir / "content_units.json",
        "normalized_text_ref": refs_dir / "normalized.txt",
        "blob_ref": refs_dir / "blob.bin",
        "download_exchange_ref": refs_dir / "download_exchange.json",
        "discovery_ref": refs_dir / "discovery.json",
        "selection_ref": refs_dir / "selection.json",
    }
    for path in paths.values():
        path.write_text("{}", encoding="utf-8")

    db.add(
        ApsContentDocument(
            content_id="content-evidence-gate",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-gate",
            normalized_char_count=10,
            chunk_count=1,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-evidence-gate",
            chunk_id="chunk-evidence-gate",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=10,
            chunk_text="alpha beta",
            chunk_text_sha256="sha-gate",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-evidence-gate",
            run_id=run_id,
            target_id="target-evidence-gate",
            accession_number="ML-GATE",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
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


def test_evidence_bundle_gate_pass_and_fail_closed(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_bundle_gate, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_bundle_gate, "SessionLocal", Session)
        monkeypatch.setattr(
            nrc_aps_evidence_bundle_gate,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": "run-evidence-gate", "status": "completed"}],
        )

        _seed_gate_data(db, reports_dir=tmp_path)
        assembled = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": "run-evidence-gate", "persist_bundle": True},
        )
        assert assembled["bundle_ref"]
        bundle_path = Path(assembled["bundle_ref"])
        bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle_path.write_text(json.dumps(bundle_payload, indent=2, sort_keys=True), encoding="utf-8-sig")
        pass_report = nrc_aps_evidence_bundle_gate.validate_evidence_bundle_gate(
            run_ids=["run-evidence-gate"],
            limit=1,
            report_path=tmp_path / "pass_report.json",
            require_runs=True,
        )
        assert pass_report["passed"] is True

        tampered_payload = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
        tampered_payload["results"][0]["start_char"] = 2
        to_checksum = dict(tampered_payload)
        to_checksum.pop("bundle_checksum", None)
        tampered_payload["bundle_checksum"] = contract.compute_bundle_checksum(to_checksum)
        bundle_path.write_text(json.dumps(tampered_payload, indent=2, sort_keys=True), encoding="utf-8-sig")

        fail_report = nrc_aps_evidence_bundle_gate.validate_evidence_bundle_gate(
            run_ids=["run-evidence-gate"],
            limit=1,
            report_path=tmp_path / "fail_report.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE in reasons
    finally:
        db.close()
        engine.dispose()


def _seed_minimal_synthetic_data(db, *, run_id: str = "run-synthetic-minimal") -> None:
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="public_api",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id=f"target-{run_id}",
        connector_run_id=run_id,
        artifact_surface="documents",
        status="recommended",
        ordinal=0,
    )
    db.add(run)
    db.add(target)
    db.add(
        ApsContentDocument(
            content_id=f"content-{run_id}",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-synthetic",
            normalized_char_count=5,
            chunk_count=1,
            content_status="indexed",
        )
    )
    db.add(
        ApsContentChunk(
            content_id=f"content-{run_id}",
            chunk_id=f"chunk-{run_id}",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            chunk_ordinal=0,
            start_char=0,
            end_char=5,
            chunk_text="test",
            chunk_text_sha256="sha-synthetic",
        )
    )
    db.add(
        ApsContentLinkage(
            content_id=f"content-{run_id}",
            run_id=run_id,
            target_id=f"target-{run_id}",
            accession_number="ML-SYNTHETIC",
            content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
            content_units_ref="synthetic-content-units-ref",
            normalized_text_ref=None,
            normalized_text_sha256="norm-synthetic",
            blob_ref=None,
            blob_sha256=None,
            download_exchange_ref=None,
            discovery_ref=None,
            selection_ref=None,
        )
    )
    db.commit()


def test_synthetic_row_with_only_content_units_ref_succeeds_at_assembly(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        run_id = "run-synthetic-minimal"
        _seed_minimal_synthetic_data(db, run_id=run_id)
        assembled = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": run_id, "persist_bundle": False, "accession_numbers": ["ML-SYNTHETIC"]},
        )
        assert assembled["bundle_id"]
        assert assembled.get("_persisted") in (False, None)
        groups = assembled.get("groups", [])
        assert len(groups) == 1
        chunks = groups[0].get("chunks", [])
        assert len(chunks) == 1
        row = chunks[0]
        assert row.get("content_units_ref") == "synthetic-content-units-ref"
        assert row.get("normalized_text_ref") is None
        assert row.get("blob_ref") is None
        assert row.get("download_exchange_ref") is None
        assert row.get("discovery_ref") is None
        assert row.get("selection_ref") is None
    finally:
        db.close()
        engine.dispose()


def test_missing_content_units_ref_fails_at_assembly(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        run_id = "run-missing-provenance"
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            source_system="nrc_adams_aps",
            source_mode="public_api",
            status="completed",
        )
        target = ConnectorRunTarget(
            connector_run_target_id=f"target-{run_id}",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=0,
        )
        db.add(run)
        db.add(target)
        db.add(
            ApsContentDocument(
                content_id=f"content-{run_id}",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-missing",
                normalized_char_count=5,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id=f"content-{run_id}",
                chunk_id=f"chunk-{run_id}",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=5,
                chunk_text="test",
                chunk_text_sha256="sha-missing",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id=f"content-{run_id}",
                run_id=run_id,
                target_id=f"target-{run_id}",
                accession_number="ML-MISSING",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref=None,
                normalized_text_ref=None,
                normalized_text_sha256="norm-missing",
                blob_ref=None,
                blob_sha256=None,
                download_exchange_ref=None,
                discovery_ref=None,
                selection_ref=None,
            )
        )
        db.commit()

        try:
            nrc_aps_evidence_bundle.assemble_evidence_bundle(
                db,
                request_payload={"run_id": run_id, "persist_bundle": False, "accession_numbers": ["ML-MISSING"]},
            )
            raise AssertionError("expected EvidenceBundleError for missing content_units_ref")
        except nrc_aps_evidence_bundle.EvidenceBundleError as exc:
            assert exc.code == contract.APS_RUNTIME_FAILURE_PROVENANCE_MISSING
            assert "content_units_ref" in exc.message
    finally:
        db.close()
        engine.dispose()


def test_structural_divergence_fails_at_gate(monkeypatch, tmp_path: Path):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        class _Settings:
            connector_reports_dir = str(tmp_path)
            database_url = "sqlite:///:memory:"

        monkeypatch.setattr(nrc_aps_evidence_bundle, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_bundle_gate, "settings", _Settings())
        monkeypatch.setattr(nrc_aps_evidence_bundle_gate, "SessionLocal", Session)
        monkeypatch.setattr(
            nrc_aps_evidence_bundle_gate,
            "_load_candidate_runs",
            lambda run_ids, limit: [{"run_id": "run-structural-diverge", "status": "completed"}],
        )
        run_id = "run-structural-diverge"
        run = ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            source_system="nrc_adams_aps",
            source_mode="public_api",
            status="completed",
        )
        target = ConnectorRunTarget(
            connector_run_target_id=f"target-{run_id}",
            connector_run_id=run_id,
            artifact_surface="documents",
            status="recommended",
            ordinal=0,
        )
        db.add(run)
        db.add(target)
        db.add(
            ApsContentDocument(
                content_id=f"content-{run_id}",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=contract.APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256="norm-diverge",
                normalized_char_count=10,
                chunk_count=1,
                content_status="indexed",
            )
        )
        db.add(
            ApsContentChunk(
                content_id=f"content-{run_id}",
                chunk_id=f"chunk-{run_id}",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=10,
                chunk_text="diverge",
                chunk_text_sha256="sha-diverge",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id=f"content-{run_id}",
                run_id=run_id,
                target_id=f"target-{run_id}",
                accession_number="ML-DIVERGE",
                content_contract_id=contract.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=contract.APS_CHUNKING_CONTRACT_ID,
                content_units_ref="structural-content-units-ref",
                normalized_text_ref=None,
                normalized_text_sha256="norm-diverge",
                blob_ref=None,
                blob_sha256=None,
                download_exchange_ref=None,
                discovery_ref=None,
                selection_ref=None,
            )
        )
        db.commit()

        assembled = nrc_aps_evidence_bundle.assemble_evidence_bundle(
            db,
            request_payload={"run_id": run_id, "persist_bundle": True},
        )
        assert assembled["bundle_ref"]
        bundle_path = Path(assembled["bundle_ref"])
        bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle_path.write_text(json.dumps(bundle_payload, indent=2, sort_keys=True), encoding="utf-8-sig")

        tampered = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
        tampered["results"][0]["chunk_text_sha256"] = "tampered_sha256"
        to_checksum = dict(tampered)
        to_checksum.pop("bundle_checksum", None)
        tampered["bundle_checksum"] = contract.compute_bundle_checksum(to_checksum)
        bundle_path.write_text(json.dumps(tampered, indent=2, sort_keys=True), encoding="utf-8-sig")

        fail_report = nrc_aps_evidence_bundle_gate.validate_evidence_bundle_gate(
            run_ids=[run_id],
            limit=1,
            report_path=tmp_path / "fail_structural_report.json",
            require_runs=True,
        )
        assert fail_report["passed"] is False
        reasons = fail_report["checks"][0]["reasons"]
        assert contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE in reasons
        assert contract.APS_GATE_FAILURE_MISSING_PROVENANCE not in reasons
    finally:
        db.close()
        engine.dispose()
