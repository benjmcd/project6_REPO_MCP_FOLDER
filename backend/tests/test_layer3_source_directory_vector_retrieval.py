from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisRun,
    ConnectorRun,
    ConnectorRunTarget,
    L3PackageSupersessionCommit,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ProviderPrivateSignedUrlAuditEvent,
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ProviderPublicUrlObjectAuthority,
    L3ProviderPublicUrlReceipt,
    L3ReconciliationRecord,
    L3ReplacementPackageSetAuthority,
    L3SourceDirectoryInternalWebhookDispatchAuditEvent,
    L3SourceDirectoryInternalWebhookDispatchReceipt,
)
from app.services import layer3_internal_webhook_connector
from app.services.layer3_source_directory_text_index import (
    SourceDirectoryTextIndexError,
    source_directory_material_text_index,
)
from app.services.layer3_source_directory_vector_index import (
    SourceDirectoryVectorIndexError,
    source_directory_material_embedding_vector_index,
)
from app.services.layer3_source_directory_hybrid_context import (
    source_directory_material_hybrid_retrieval_context_packet,
)
from app.services.layer3_source_directory_hybrid_analysis import (
    source_directory_hybrid_context_packet_qualitative_analysis,
)
from app.services.layer3_mockup_boundary import mockup_truth_state_contract
from app.services.layer3_source_directory_vector_retrieval import (
    SourceDirectoryVectorRetrievalError,
    source_directory_material_vector_retrieval,
)
from main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", "")
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.layer3_session_factory = session_local
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _scan_payload(client_request_id: str = "source-directory-vector-retrieval-scan") -> dict[str, str]:
    return {
        "client_request_id": client_request_id,
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _write_vector_retrieval_source_dir(root: Path) -> None:
    root.mkdir()
    lines = ["alpha beta beta lead\n"]
    lines.extend(f"context filler line {index}\n" for index in range(1, 42))
    lines.append("alpha gamma tail\n")
    (root / "vector-retrieval.txt").write_text("".join(lines), encoding="utf-8")


def _material_preview_payload(scan_body: dict, relative_name: str = "vector-retrieval.txt") -> dict[str, str]:
    file_record = next(item for item in scan_body["files"] if item["relative_name"] == relative_name)
    return {
        "client_request_id": f"source-directory-material-preview-{relative_name}",
        "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
        "source_ingestion_file_id": file_record["source_ingestion_file_id"],
        "file_identity_hash": file_record["file_identity_hash"],
        "authority_basis_hash": file_record["authority_basis_hash"],
    }


def _approve_source_directory_file(client: TestClient, scan_body: dict) -> dict[str, str]:
    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    candidate = preview_body["material_candidate"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "source-directory-vector-retrieval-gate-b",
            "preflight_id": "preflight-source-directory-vector-retrieval",
            "source_set_id": scan_body["source_ingestion_batch_id"],
            "material_preview_id": preview_body["material_preview_id"],
            "material_preview_hash": preview_body["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": candidate,
                }
            ],
        },
    )
    assert gate_b.status_code == 200
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == gate_b.json()["session_id"])
            .one()
        )
        return {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "payload_hash": snapshot.payload_hash,
            "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
            "source_ingestion_file_id": candidate["payload"]["source_ingestion_file_id"],
            "content_sha256": candidate["payload"]["content_sha256"],
            "file_identity_hash": candidate["payload"]["file_identity_hash"],
            "authority_basis_hash": candidate["payload"]["authority_basis_hash"],
        }
    finally:
        db.close()


def _text_index_payload(snapshot_info: dict[str, str]) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-text-index-{snapshot_info['source_ingestion_file_id']}",
        **snapshot_info,
    }


def _vector_index_payload(snapshot_info: dict[str, str], index_authority_hash: str) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-vector-index-{snapshot_info['source_ingestion_file_id']}",
        **snapshot_info,
        "index_authority_hash": index_authority_hash,
    }


def _vector_retrieval_payload(
    snapshot_info: dict[str, str],
    index_authority_hash: str,
    embedding_index_authority_hash: str,
    query_text: str,
) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-vector-retrieval-{snapshot_info['source_ingestion_file_id']}",
        **snapshot_info,
        "index_authority_hash": index_authority_hash,
        "embedding_index_authority_hash": embedding_index_authority_hash,
        "query_text": query_text,
    }


def _admitted_material(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> tuple[Path, dict[str, str], str, str]:
    source_dir = tmp_path / "operator-source-dir"
    _write_vector_retrieval_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))
    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json())
    db = client.layer3_session_factory()
    try:
        text_index = source_directory_material_text_index(db, _text_index_payload(snapshot_info))
        vector_index = source_directory_material_embedding_vector_index(
            db,
            _vector_index_payload(snapshot_info, text_index["index_authority_hash"]),
        )
    finally:
        db.close()
    return (
        source_dir,
        snapshot_info,
        text_index["index_authority_hash"],
        vector_index["embedding_index_authority_hash"],
    )


def _session_id_for_snapshot(client: TestClient, material_snapshot_id: str) -> str:
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.material_snapshot_id == material_snapshot_id)
            .one()
        )
        return snapshot.session_id
    finally:
        db.close()


def _assert_no_downstream_side_effects(db) -> None:
    assert db.query(L3PassRun).count() == 0
    assert db.query(AnalysisRun).count() == 0
    assert db.query(L3OutputPackage).count() == 0
    assert db.query(ConnectorRun).count() == 0
    assert db.query(ConnectorRunTarget).count() == 0


def _assert_no_forbidden_package_commit_downstream(db) -> None:
    assert db.query(L3PassRun).count() == 0
    assert db.query(AnalysisRun).count() == 0
    assert db.query(ConnectorRun).count() == 0
    assert db.query(ConnectorRunTarget).count() == 0


def _assert_disabled_authority_flags(body: dict) -> None:
    disabled_keys = {
        "browser_download_enabled",
        "connector_dispatch_enabled",
        "frontend_durable_authority_enabled",
        "network_egress_enabled",
        "package_payload_rewrite_enabled",
        "prompt_model_provider_runtime_enabled",
        "provider_private_signed_url_enabled",
        "provider_public_delivery_enabled",
        "provider_public_url_enabled",
        "raw_local_path_exposed",
        "source_package_row_mutation_enabled",
    }
    for key, value in body.items():
        if key in disabled_keys:
            assert value is False
        elif isinstance(value, dict):
            _assert_disabled_authority_flags(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _assert_disabled_authority_flags(item)


def test_source_directory_hybrid_authority_prepare_route_derives_index_authority_from_gate_b_session(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    session_id = _session_id_for_snapshot(client, snapshot_info["material_snapshot_id"])

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare",
        json={
            "client_request_id": "source-directory-hybrid-authority-prepare",
            "session_id": session_id,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_hybrid_authority_prepare.v1"
    assert body["status"] == "available"
    assert body["mode"] == "source_directory_hybrid_authority_generation_operator_bridge"
    assert body["session_id"] == session_id
    assert body["material_snapshot_id"] == snapshot_info["material_snapshot_id"]
    assert body["source_ingestion_batch_id"] == snapshot_info["source_ingestion_batch_id"]
    assert body["source_ingestion_file_id"] == snapshot_info["source_ingestion_file_id"]
    assert body["index_authority_hash"] == index_authority_hash
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["authority_prepare_hash"]
    authority_payload = body["authority_payload"]
    assert authority_payload == {
        **snapshot_info,
        "index_authority_hash": index_authority_hash,
        "embedding_index_authority_hash": embedding_index_authority_hash,
        "query_text": "BETA alpha alpha",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "rendered source-directory scan to hybrid handoff delivery proof",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    assert body["redaction_guards"]["absolute_path_exposed"] is False
    assert body["redaction_guards"]["frontend_durable_authority_enabled"] is False
    assert body["negative_invariants"]["source_index_rows_written"] is False
    assert body["negative_invariants"]["retrieval_rows_written"] is False
    assert body["negative_invariants"]["package_rows_written"] is False
    assert "submit_source_directory_hybrid_middle_lifecycle_from_server_authority" in body["next_allowed_actions"]
    assert str(source_dir) not in response.text

    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_hybrid_authority_prepare_fails_closed_for_missing_forbidden_and_stale_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    missing = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare",
        json={
            "client_request_id": "source-directory-hybrid-authority-prepare-missing",
            "session_id": "missing-source-directory-session",
        },
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "source_directory_hybrid_authority_material_snapshot_not_found"

    source_dir, snapshot_info, _index_authority_hash, _embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    session_id = _session_id_for_snapshot(client, snapshot_info["material_snapshot_id"])

    forbidden = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare",
        json={
            "client_request_id": "source-directory-hybrid-authority-prepare-forbidden",
            "session_id": session_id,
            "index_authority_hash": "0" * 64,
        },
    )
    assert forbidden.status_code == 422
    assert ("body", "index_authority_hash") in {
        tuple(error["loc"]) for error in forbidden.json()["detail"]
    }

    (source_dir / "vector-retrieval.txt").write_text("alpha beta drift\n", encoding="utf-8")
    stale = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare",
        json={
            "client_request_id": "source-directory-hybrid-authority-prepare-stale",
            "session_id": session_id,
        },
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "source_directory_text_index_file_identity_mismatch"
    assert str(source_dir) not in stale.text

    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def _hybrid_package_review_submit_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
    *,
    client_request_id: str,
    submit_decision: str = "approved",
    decision_notes: str | None = None,
) -> tuple[dict, dict, dict, dict, str]:
    _source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    analysis_payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": client_request_id,
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid handoff export evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()

    commit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()

    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": (
            analysis_body["source_directory_hybrid_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": submit_decision,
    }
    if decision_notes is not None:
        submit_payload["decision_notes"] = decision_notes
    submit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    return analysis_body, commit_body, submit.json(), submit_payload, embedding_index_authority_hash


def _hybrid_external_export_download_prepare_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
    *,
    client_request_id: str,
) -> tuple[dict, dict, dict]:
    analysis_body, _commit_body, submit_body, submit_payload, _embedding_index_authority_hash = (
        _hybrid_package_review_submit_authority(
            client,
            tmp_path,
            monkeypatch,
            client_request_id=client_request_id,
        )
    )
    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    handoff = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_body = handoff.json()
    prepare_payload = {
        **handoff_payload,
        "operator_decision": "prepare_source_directory_hybrid_external_export_download",
        "prepare_record_ref": handoff_body["prepare_record_ref"],
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": handoff_body["handoff_export_envelope"]["envelope_ref"],
        "external_export_download_target": (
            "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
        ),
        "download_mode": "reference_only_prepare",
    }
    prepare = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        json=prepare_payload,
    )
    assert prepare.status_code == 200, prepare.text
    return analysis_body, prepare.json(), prepare_payload


def _source_directory_internal_webhook_payload(
    prepare_body: dict,
    prepare_payload: dict,
    *,
    request_id: str,
) -> dict:
    return {
        **prepare_payload,
        "client_request_id": request_id,
        "operator_decision": "dispatch_source_directory_hybrid_internal_webhook",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "target_identity": "server_configured_internal_webhook_destination",
        "target_class": "real_connector_invocation",
        "dispatch_mode": "server_configured_allowlisted_internal_webhook_post",
    }


def test_source_directory_vector_retrieval_returns_deterministic_ranked_segments_without_side_effects(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )

    db = client.layer3_session_factory()
    try:
        body = source_directory_material_vector_retrieval(
            db,
            {
                **_vector_retrieval_payload(
                    snapshot_info,
                    index_authority_hash,
                    embedding_index_authority_hash,
                    "BETA alpha alpha",
                ),
                "top_k": 2,
            },
        )
        replay = source_directory_material_vector_retrieval(
            db,
            {
                **_vector_retrieval_payload(
                    snapshot_info,
                    index_authority_hash,
                    embedding_index_authority_hash,
                    "BETA alpha alpha",
                ),
                "top_k": 2,
            },
        )

        assert body["schema_id"] == "layer3.source_directory_vector_retrieval.v1"
        assert body["mode"] == "source_directory_material_deterministic_vector_retrieval_authority"
        assert body["status"] == "available"
        assert body["retrieval_contract_id"] == "source_directory_material_deterministic_vector_retrieval_authority"
        assert body["retrieval_mode"] == "deterministic_local_hash_vector_similarity_retrieval"
        assert body["embedding_contract_id"] == "source_directory_material_deterministic_embedding_vector_index_authority"
        assert body["embedding_mode"] == "deterministic_local_hashing_vector_embedding"
        assert body["vector_index_mode"] == "deterministic_source_directory_segment_vector_index"
        assert body["feature_hash_version"] == "source-directory-hash-vector-v1"
        assert body["vector_dimensions"] == 4096
        assert body["query_tokens"] == ["alpha", "beta"]
        assert body["top_k"] == 2
        assert body["index_authority_hash"] == index_authority_hash
        assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
        assert body["source_ingestion_file_id"] == snapshot_info["source_ingestion_file_id"]
        assert body["material_snapshot_id"] == snapshot_info["material_snapshot_id"]
        assert body["total"] >= 1
        assert len(body["items"]) == 2
        assert body["items"] == replay["items"]
        assert [float(item["vector_score"]) for item in body["items"]] == sorted(
            [float(item["vector_score"]) for item in body["items"]],
            reverse=True,
        )

        item = body["items"][0]
        assert item["matched_unique_query_terms"] >= 1
        assert item["summed_query_term_frequency"] >= 1
        assert item["vector_score"] == replay["items"][0]["vector_score"]
        assert float(item["vector_score"]) > 0
        assert len(item["embedding_vector_hash"]) == 64
        assert "vector" not in item
        assert "normalized_features" not in item
        assert "raw_vector" not in item

        assert body["source_index_rows_written"] is False
        assert body["embedding_vector_rows_written"] is False
        assert body["vector_index_rows_written"] is False
        assert body["retrieval_rows_written"] is False
        assert body["context_packet_rows_written"] is False
        assert body["qualitative_analysis_rows_written"] is False
        assert body["analysis_run_rows_written"] is False
        assert body["package_rows_written"] is False
        assert body["connector_rows_written"] is False
        assert body["negative_invariants"]["persistent_vector_store_enabled"] is False
        assert body["negative_invariants"]["durable_retrieval_rows_enabled"] is False
        assert body["negative_invariants"]["rag_execution_enabled"] is False
        assert body["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
        assert body["negative_invariants"]["connector_dispatch_enabled"] is False
        assert body["negative_invariants"]["provider_public_delivery_enabled"] is False
        assert body["negative_invariants"]["network_egress_enabled"] is False
        assert str(source_dir) not in str(body)
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_vector_retrieval_api_route_is_bounded_and_redacted(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "alpha beta",
        ),
        "top_k": 1,
    }

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval",
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_vector_retrieval.v1"
    assert body["mode"] == "source_directory_material_deterministic_vector_retrieval_authority"
    assert body["status"] == "available"
    assert body["retrieval_mode"] == "deterministic_local_hash_vector_similarity_retrieval"
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["index_authority_hash"] == index_authority_hash
    assert body["top_k"] == 1
    assert len(body["items"]) == 1
    assert body["source_index_rows_written"] is False
    assert body["embedding_vector_rows_written"] is False
    assert body["vector_index_rows_written"] is False
    assert body["retrieval_rows_written"] is False
    assert body["context_packet_rows_written"] is False
    assert body["qualitative_analysis_rows_written"] is False
    assert body["analysis_run_rows_written"] is False
    assert body["package_rows_written"] is False
    assert body["connector_rows_written"] is False
    assert body["negative_invariants"]["persistent_vector_store_enabled"] is False
    assert body["negative_invariants"]["rag_execution_enabled"] is False
    assert body["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
    assert body["negative_invariants"]["network_egress_enabled"] is False
    assert str(source_dir) not in response.text

    stale = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval",
        json={**payload, "embedding_index_authority_hash": "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == (
        "source_directory_vector_retrieval_stale_embedding_index_authority"
    )

    forbidden = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval",
        json={**payload, "prompt": "not-admitted", "provider_model": "not-admitted"},
    )
    assert forbidden.status_code == 422
    assert {tuple(error["loc"]) for error in forbidden.json()["detail"]} >= {
        ("body", "prompt"),
        ("body", "provider_model"),
    }

    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_fuses_lexical_and_vector_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "alpha beta",
        ),
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }

    db = client.layer3_session_factory()
    try:
        direct = source_directory_material_hybrid_retrieval_context_packet(db, payload)
        replay = source_directory_material_hybrid_retrieval_context_packet(db, payload)
    finally:
        db.close()
    assert direct["schema_id"] == "layer3.source_directory_hybrid_retrieval_context_packet.v1"
    assert direct["mode"] == "source_directory_hybrid_retrieval_context_packet_authority"
    assert direct["status"] == "available"
    assert direct["hybrid_context_packet_hash"] == replay["hybrid_context_packet_hash"]
    assert direct["lexical_context_packet_hash"] == replay["lexical_context_packet_hash"]
    assert direct["vector_retrieval_contract_id"] == (
        "source_directory_material_deterministic_vector_retrieval_authority"
    )
    assert direct["source_gate"] == "822_SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_RUNTIME_ENTRY_FREEZE"
    assert direct["index_authority_hash"] == index_authority_hash
    assert direct["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert direct["hybrid_total"] >= 1
    assert direct["items"] == replay["items"]
    assert direct["items"][0]["hybrid_rank"] == 1
    assert direct["items"][0]["included_by_lexical"] is True
    assert direct["items"][0]["included_by_vector"] is True
    assert "text_excerpt" in direct["items"][0]
    assert "text" not in direct["items"][0]
    assert "vector" not in direct["items"][0]
    assert "normalized_features" not in direct["items"][0]
    assert direct["source_index_rows_written"] is False
    assert direct["embedding_vector_rows_written"] is False
    assert direct["vector_index_rows_written"] is False
    assert direct["retrieval_rows_written"] is False
    assert direct["context_packet_rows_written"] is False
    assert direct["qualitative_analysis_rows_written"] is False
    assert direct["analysis_run_rows_written"] is False
    assert direct["package_rows_written"] is False
    assert direct["connector_rows_written"] is False
    assert direct["negative_invariants"]["persistent_vector_store_enabled"] is False
    assert direct["negative_invariants"]["rag_execution_enabled"] is False
    assert direct["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
    assert direct["negative_invariants"]["network_egress_enabled"] is False
    assert str(source_dir) not in str(direct)

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet",
        json=payload,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == direct["schema_id"]
    assert body["hybrid_context_packet_hash"] == direct["hybrid_context_packet_hash"]
    assert body["items"] == direct["items"]
    assert str(source_dir) not in response.text

    stale = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet",
        json={**payload, "embedding_index_authority_hash": "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == (
        "source_directory_vector_retrieval_stale_embedding_index_authority"
    )

    forbidden = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet",
        json={**payload, "prompt": "not-admitted", "provider_model": "not-admitted"},
    )
    assert forbidden.status_code == 422
    assert {tuple(error["loc"]) for error in forbidden.json()["detail"]} >= {
        ("body", "prompt"),
        ("body", "provider_model"),
    }

    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_uses_hybrid_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": "source-directory-hybrid-context-analysis",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid context packet evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }

    db = client.layer3_session_factory()
    try:
        direct = source_directory_hybrid_context_packet_qualitative_analysis(db, payload)
        replay = source_directory_hybrid_context_packet_qualitative_analysis(db, payload)
        hybrid_context = source_directory_material_hybrid_retrieval_context_packet(
            db,
            {
                key: value
                for key, value in payload.items()
                if key not in {"analysis_question", "analysis_focus"}
            },
        )

        assert direct["schema_id"] == (
            "layer3.source_directory_hybrid_context_packet_qualitative_analysis.v1"
        )
        assert direct["mode"] == "source_directory_hybrid_context_packet_qualitative_analysis_authority"
        assert direct["source_gate"] == (
            "824_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_RUNTIME_ENTRY_FREEZE"
        )
        assert direct["status"] == "available"
        assert direct["analysis_contract_id"] == (
            "source_directory_hybrid_context_packet_qualitative_analysis_authority"
        )
        assert direct["analysis_mode"] == "hybrid_context_packet_grounded_qualitative_analysis"
        assert direct["qualitative_analysis_hash"] == replay["qualitative_analysis_hash"]
        assert direct["hybrid_context_packet_hash"] == hybrid_context["hybrid_context_packet_hash"]
        assert direct["validated_hybrid_context_schema_id"] == hybrid_context["schema_id"]
        assert direct["validated_hybrid_context_mode"] == hybrid_context["mode"]
        assert direct["lexical_context_packet_hash"] == hybrid_context["lexical_context_packet_hash"]
        assert direct["vector_retrieval_contract_id"] == hybrid_context["vector_retrieval_contract_id"]
        assert direct["embedding_index_authority_hash"] == embedding_index_authority_hash
        assert direct["hybrid_total"] == hybrid_context["hybrid_total"]
        assert direct["supporting_segments"]
        assert direct["supporting_segments"][0]["hybrid_rank"] == 1
        assert direct["supporting_segments"][0]["included_by_lexical"] is True
        assert direct["supporting_segments"][0]["included_by_vector"] is True
        assert "quote_excerpt" in direct["supporting_segments"][0]
        assert "text" not in direct["supporting_segments"][0]
        assert "vector" not in direct["supporting_segments"][0]
        assert direct["evidence_summary"]["summary_kind"] == (
            "deterministic_hybrid_context_packet_evidence_summary"
        )
        assert direct["source_directory_package_review_preview_enabled"] is True
        assert direct["source_directory_hybrid_package_review_preview_hash"] == replay[
            "source_directory_hybrid_package_review_preview_hash"
        ]
        package_preview = direct["source_directory_hybrid_package_review_preview"]
        assert package_preview["schema_id"] == (
            "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview.v1"
        )
        assert package_preview["mode"] == (
            "read_only_source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview"
        )
        assert package_preview["source_gate"] == (
            "826_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE"
        )
        assert package_preview["source_authority"]["qualitative_analysis_hash"] == direct[
            "qualitative_analysis_hash"
        ]
        assert package_preview["source_authority"]["hybrid_context_packet_hash"] == direct[
            "hybrid_context_packet_hash"
        ]
        assert package_preview["source_authority"]["embedding_index_authority_hash"] == direct[
            "embedding_index_authority_hash"
        ]
        assert package_preview["candidate_package_kinds"] == [
            "canonical_internal",
            "user_facing",
            "review_facing",
        ]
        assert [item["package_kind"] for item in package_preview["candidate_packages"]] == [
            "canonical_internal",
            "user_facing",
            "review_facing",
        ]
        assert package_preview["package_review_preview_enabled"] is True
        assert package_preview["package_commit_enabled"] is False
        assert package_preview["package_review_submit_enabled"] is False
        assert package_preview["handoff_enabled"] is False
        assert package_preview["external_export_download_enabled"] is False
        assert package_preview["negative_invariants"]["package_rows_written"] is False
        assert package_preview["negative_invariants"]["package_payload_written"] is False
        assert package_preview["negative_invariants"]["source_package_row_mutation_enabled"] is False
        assert direct["candidate_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
        assert direct["package_commit_enabled"] is False
        assert direct["package_review_submit_enabled"] is False
        assert direct["handoff_enabled"] is False
        assert direct["external_export_download_enabled"] is False
        assert direct["source_index_rows_written"] is False
        assert direct["embedding_vector_rows_written"] is False
        assert direct["vector_index_rows_written"] is False
        assert direct["retrieval_rows_written"] is False
        assert direct["context_packet_rows_written"] is False
        assert direct["qualitative_analysis_rows_written"] is False
        assert direct["analysis_run_rows_written"] is False
        assert direct["package_rows_written"] is False
        assert direct["connector_rows_written"] is False
        assert direct["negative_invariants"]["rag_execution_enabled"] is False
        assert direct["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
        assert direct["negative_invariants"]["package_construction_enabled"] is False
        assert direct["negative_invariants"]["connector_dispatch_enabled"] is False
        assert direct["negative_invariants"]["raw_vector_exposed"] is False
        assert str(source_dir) not in str(direct)

        response = client.post(
            (
                "/api/v1/layer3/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis"
            ),
            json=payload,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["schema_id"] == direct["schema_id"]
        assert body["qualitative_analysis_hash"] == direct["qualitative_analysis_hash"]
        assert body["supporting_segments"] == direct["supporting_segments"]
        assert str(source_dir) not in response.text

        stale = client.post(
            (
                "/api/v1/layer3/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis"
            ),
            json={**payload, "embedding_index_authority_hash": "0" * 64},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == (
            "source_directory_vector_retrieval_stale_embedding_index_authority"
        )

        forbidden = client.post(
            (
                "/api/v1/layer3/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis"
            ),
            json={**payload, "prompt": "not-admitted", "provider_model": "not-admitted"},
        )
        assert forbidden.status_code == 422
        assert {tuple(error["loc"]) for error in forbidden.json()["detail"]} >= {
            ("body", "prompt"),
            ("body", "provider_model"),
        }

        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_status_is_read_only_before_package_commit(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": "source-directory-hybrid-analysis-status",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid status evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }

    response = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_status.v1"
    )
    assert body["mode"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_status_authority"
    )
    assert body["source_gate"] == (
        "834_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_STATUS_RUNTIME_ENTRY_FREEZE"
    )
    assert body["status"] == "available"
    assert body["analysis_status"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_available"
    )
    assert body["source_directory_package_review_preview_available"] is True
    assert body["source_directory_hybrid_package_commit_available"] is False
    assert body["source_directory_hybrid_package_review_submit_available"] is False
    assert body["source_directory_hybrid_handoff_export_prepare_available"] is False
    assert body["output_package_ids"] == []
    assert body["reconciliation_record_id"] is None
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is False
    assert body["export_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["provider_private_signed_url_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert body["supporting_segments_redacted"] is True
    assert body["analysis_result_redacted"] is True
    assert body["status_defects"] == []
    assert body["next_allowed_actions"] == [
        "commit_source_directory_hybrid_context_packet_qualitative_analysis_package"
    ]
    assert "supporting_segments" not in body
    assert "source_directory_hybrid_package_review_preview" not in body
    assert str(source_dir) not in response.text

    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_package_commit_writes_bounded_packages(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    analysis_payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": "source-directory-hybrid-package-commit-analysis",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid package construction evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()

    commit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    body = commit.json()
    assert body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_commit.v1"
    )
    assert body["status"] == "committed"
    assert body["mode"] == "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_authority"
    assert body["package_construction_source_gate"] == (
        "828_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["qualitative_analysis_hash"] == analysis_body["qualitative_analysis_hash"]
    assert body["source_directory_hybrid_package_review_preview_hash"] == (
        analysis_body["source_directory_hybrid_package_review_preview_hash"]
    )
    assert body["hybrid_context_packet_hash"] == analysis_body["hybrid_context_packet_hash"]
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["package_rows_written"] is True
    assert body["package_payloads_written"] is True
    assert body["payload_refs_redacted"] is True
    assert body["package_review_submit_enabled"] is True
    assert body["handoff_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert body["negative_invariants"]["package_review_submit_enabled"] is True

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert reconciliation.reconciliation_record_id == body["reconciliation_record_id"]
        commit_summary = reconciliation.summary_json["source_directory_hybrid_context_qualitative_package_commit"]
        assert commit_summary["schema_id"] == (
            "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_commit_summary.v1"
        )
        assert commit_summary["package_review_submit_enabled"] is True
        assert commit_summary["handoff_enabled"] is False
        assert commit_summary["external_export_download_enabled"] is False
        assert commit_summary["connector_dispatch_enabled"] is False
        assert commit_summary["provider_public_delivery_enabled"] is False
        assert commit_summary["network_egress_enabled"] is False
        assert commit_summary["authority_basis"]["hybrid_context_packet_hash"] == (
            analysis_body["hybrid_context_packet_hash"]
        )
        assert commit_summary["authority_basis"]["embedding_index_authority_hash"] == (
            embedding_index_authority_hash
        )
        packages = db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        assert {package.package_kind for package in packages} == {
            "canonical_internal",
            "user_facing",
            "review_facing",
        }
        assert {package.payload_hash for package in packages} == set(body["payload_hashes"])
        for package in packages:
            payload_path = Path(package.payload_ref)
            assert payload_path.exists()
            assert payload_path.is_file()
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            assert payload["package_header"]["source_gate"] == (
                "828_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
            )
            assert package.summary_json["construction_basis_hash"] == body["construction_basis_hash"]
    finally:
        db.close()

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "source_directory_hybrid_package_commit_existing_package_state"


def test_source_directory_hybrid_context_packet_qualitative_analysis_package_commit_rejects_stale_preview_hash(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    analysis_payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": "source-directory-hybrid-package-stale-preview-analysis",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid package construction evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text

    stale = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis.json()["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": "0" * 64,
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "source_directory_hybrid_package_commit_preview_hash_mismatch"

    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
        assert db.query(L3ReconciliationRecord).count() == 0
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_records_bounded_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    analysis_payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": "source-directory-hybrid-package-submit-analysis",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid package submit evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()

    commit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()

    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": (
            analysis_body["source_directory_hybrid_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
    }
    submit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    body = submit.json()
    assert body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit.v1"
    )
    assert body["status"] == "submitted"
    assert body["mode"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_authority"
    )
    assert body["operator_decision"] == "approved"
    assert body["package_review_state"] == "package_review_approved"
    assert body["submit_record_ref"].startswith("l3-source-directory-hybrid-package-review-submit-")
    assert body["source_gate"] == (
        "830_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_construction_source_gate"] == (
        "828_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["hybrid_context_packet_hash"] == analysis_body["hybrid_context_packet_hash"]
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["construction_basis_hash"] == commit_body["construction_basis_hash"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is True
    assert body["export_enabled"] is True
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert body["downstream_unavailable"] == [
        "external_export_download",
        "connector_dispatch",
        "provider_delivery",
    ]
    assert body["next_allowed_actions"] == ["prepare_handoff_export"]

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        reconciliation = db.query(L3ReconciliationRecord).one()
        submit_state = reconciliation.summary_json["package_review_submit"]
        assert submit_state["schema_id"] == "layer3.package_review_submit_state.v1"
        assert submit_state["package_review_submit_schema_id"] == body["schema_id"]
        assert submit_state["submit_record_ref"] == body["submit_record_ref"]
        assert submit_state["package_review_state"] == "package_review_approved"
        assert submit_state["handoff_enabled"] is True
        assert submit_state["export_enabled"] is True
        assert submit_state["authority_basis"]["hybrid_context_packet_hash"] == (
            analysis_body["hybrid_context_packet_hash"]
        )
        assert submit_state["authority_basis"]["embedding_index_authority_hash"] == (
            embedding_index_authority_hash
        )
        assert (
            reconciliation.summary_json["source_directory_hybrid_context_qualitative_package_commit"][
                "package_review_submit_enabled"
            ]
            is False
        )
    finally:
        db.close()

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "already_submitted"
    assert replay.json()["submit_record_ref"] == body["submit_record_ref"]

    conflict = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json={
            **submit_payload,
            "operator_decision": "rejected",
            "decision_notes": "not approved",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "source_directory_hybrid_package_review_submit_already_recorded"


def test_source_directory_hybrid_package_lifecycle_records_replacement_and_supersession(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    analysis_body, commit_body, submit_body, submit_payload, _embedding_index_authority_hash = (
        _hybrid_package_review_submit_authority(
            client,
            tmp_path,
            monkeypatch,
            client_request_id="source-directory-hybrid-package-lifecycle",
        )
    )
    preview_payload = {
        "client_request_id": "source-directory-hybrid-package-lifecycle-preview",
        "analysis_question": submit_payload["analysis_question"],
        "analysis_focus": submit_payload["analysis_focus"],
        "material_snapshot_id": submit_payload["material_snapshot_id"],
        "source_ingestion_batch_id": submit_payload["source_ingestion_batch_id"],
        "source_ingestion_file_id": submit_payload["source_ingestion_file_id"],
        "content_sha256": submit_payload["content_sha256"],
        "file_identity_hash": submit_payload["file_identity_hash"],
        "authority_basis_hash": submit_payload["authority_basis_hash"],
        "payload_hash": submit_payload["payload_hash"],
        "index_authority_hash": submit_payload["index_authority_hash"],
        "query_text": submit_payload["query_text"],
        "limit": submit_payload["limit"],
        "offset": submit_payload["offset"],
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": (
            analysis_body["source_directory_hybrid_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "operator_decision": "preview_source_directory_package_supersession",
    }
    preview = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/supersession/preview"
        ),
        json=preview_payload,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["status"] == "previewed"
    assert preview_body["context_packet_hash"] == analysis_body["hybrid_context_packet_hash"]
    assert preview_body["source_directory_package_review_preview_hash"] == (
        analysis_body["source_directory_hybrid_package_review_preview_hash"]
    )
    assert preview_body["package_construction_source_gate"] == (
        "828_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert preview_body["package_review_submit_source_gate"] == (
        "830_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert preview_body["output_package_ids"] == commit_body["output_package_ids"]
    assert preview_body["payload_hashes"] == commit_body["payload_hashes"]
    assert preview_body["payload_refs_redacted"] is True

    replacement = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/replacement-set/record-from-supersession-preview"
        ),
        json={
            "client_request_id": "source-directory-hybrid-package-lifecycle-replacement",
            "session_id": preview_body["session_id"],
            "reconciliation_record_id": preview_body["reconciliation_record_id"],
            "package_supersession_preview_hash": preview_body["package_supersession_preview_hash"],
            "source_package_set_hash": preview_body["source_package_set_hash"],
            "operator_decision": "record_replacement_package_set_authority",
        },
    )
    assert replacement.status_code == 200, replacement.text
    replacement_body = replacement.json()
    assert replacement_body["status"] == "recorded"
    assert replacement_body["source_directory_package_lifecycle_authority"] is True
    assert replacement_body["source_package_set_hash"] == preview_body["source_package_set_hash"]
    assert replacement_body["source_output_package_ids"] == commit_body["output_package_ids"]
    assert replacement_body["source_payload_hashes"] == commit_body["payload_hashes"]

    supersession = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/supersession/commit"
        ),
        json={
            "client_request_id": "source-directory-hybrid-package-lifecycle-commit",
            "session_id": replacement_body["session_id"],
            "analysis_plan_id": replacement_body["analysis_plan_id"],
            "pass_run_id": replacement_body["pass_run_id"],
            "reconciliation_record_id": replacement_body["reconciliation_record_id"],
            "package_supersession_preview_hash": preview_body["package_supersession_preview_hash"],
            "source_package_set_hash": preview_body["source_package_set_hash"],
            "replacement_package_set_authority_id": (
                replacement_body["replacement_package_set_authority_id"]
            ),
            "replacement_authority_basis_hash": replacement_body["authority_basis_hash"],
            "operator_decision": "commit_package_supersession",
        },
    )
    assert supersession.status_code == 200, supersession.text
    supersession_body = supersession.json()
    assert supersession_body["status"] == "committed"
    assert supersession_body["source_directory_package_lifecycle_authority"] is True
    assert supersession_body["replacement_package_set_authority_id"] == (
        replacement_body["replacement_package_set_authority_id"]
    )
    assert supersession_body["source_output_package_ids"] == commit_body["output_package_ids"]
    assert supersession_body["source_payload_hashes"] == commit_body["payload_hashes"]
    assert supersession_body["package_payload_write_enabled"] is False
    assert supersession_body["l3_output_package_write_enabled"] is False
    assert supersession_body["frontend_only_durable_state_enabled"] is False

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
        assert db.query(L3PackageSupersessionCommit).count() == 1
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_records_bounded_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    analysis_body, commit_body, submit_body, submit_payload, embedding_index_authority_hash = (
        _hybrid_package_review_submit_authority(
            client,
            tmp_path,
            monkeypatch,
            client_request_id="source-directory-hybrid-handoff-export-prepare-analysis",
        )
    )
    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    response = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare.v1"
    )
    assert body["mode"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_authority"
    )
    assert body["status"] == "prepared"
    assert body["handoff_export_state"] == "handoff_export_prepared"
    assert body["handoff_target"] == "internal_export_envelope"
    assert body["export_mode"] == "prepare_only"
    assert body["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
    assert body["output_package_ids"] == commit_body["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["payload_refs_redacted"] is True
    assert body["source_gate"] == (
        "832_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_review_submit_source_gate"] == (
        "830_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_construction_source_gate"] == (
        "828_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["hybrid_context_packet_hash"] == analysis_body["hybrid_context_packet_hash"]
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["handoff_export_envelope"]["payload_refs"] is None
    assert body["handoff_export_envelope"]["payload_refs_redacted"] is True
    assert body["handoff_export_envelope"]["output_package_ids"] == commit_body["output_package_ids"]
    assert body["handoff_enabled"] is False
    assert body["export_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["provider_private_signed_url_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert body["downstream_unavailable"] == [
        "external_export_download",
        "connector_dispatch",
        "provider_public_delivery",
        "provider_private_signed_url",
        "network_egress",
    ]

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        assert db.query(L3OutputPackage).count() == 3
        reconciliation = db.query(L3ReconciliationRecord).one()
        prepare_state = reconciliation.summary_json["handoff_export_prepare"]
        assert prepare_state["schema_id"] == "layer3.handoff_export_prepare_state.v1"
        assert prepare_state["handoff_export_prepare_schema_id"] == body["schema_id"]
        assert prepare_state["handoff_export_state"] == "handoff_export_prepared"
        assert prepare_state["prepare_record_ref"] == body["prepare_record_ref"]
        assert prepare_state["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
        assert prepare_state["payload_refs"] is None
        assert prepare_state["payload_refs_redacted"] is True
        assert prepare_state["source_gate"] == (
            "832_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE"
        )
    finally:
        db.close()

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "already_prepared"
    assert replay.json()["prepare_record_ref"] == body["prepare_record_ref"]

    conflict = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json={**handoff_payload, "operator_decision": "hold", "decision_notes": "wait"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "source_directory_hybrid_handoff_export_prepare_already_recorded"


def test_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare_records_readiness(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    analysis_body, commit_body, submit_body, submit_payload, embedding_index_authority_hash = (
        _hybrid_package_review_submit_authority(
            client,
            tmp_path,
            monkeypatch,
            client_request_id="source-directory-hybrid-external-export-download-prepare-analysis",
        )
    )
    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    handoff = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_body = handoff.json()

    prepare_payload = {
        **handoff_payload,
        "operator_decision": "prepare_source_directory_hybrid_external_export_download",
        "prepare_record_ref": handoff_body["prepare_record_ref"],
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": handoff_body["handoff_export_envelope"]["envelope_ref"],
        "external_export_download_target": (
            "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
        ),
        "download_mode": "reference_only_prepare",
    }
    response = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        json=prepare_payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare.v1"
    )
    assert body["mode"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare_authority"
    )
    assert body["status"] == "prepared"
    assert body["external_export_download_state"] == "external_export_download_prepared"
    assert body["external_export_download_target"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
    )
    assert body["download_mode"] == "reference_only_prepare"
    assert body["prepare_record_ref"] == handoff_body["prepare_record_ref"]
    assert body["handoff_export_envelope_ref"] == handoff_body["handoff_export_envelope"]["envelope_ref"]
    assert body["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
    assert body["output_package_ids"] == commit_body["output_package_ids"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["payload_refs_redacted"] is True
    assert body["source_gate"] == (
        "836_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_review_submit_source_gate"] == (
        "830_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_construction_source_gate"] == (
        "828_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["hybrid_context_packet_hash"] == analysis_body["hybrid_context_packet_hash"]
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["external_export_download_descriptor"]["payload_refs"] is None
    assert body["external_export_download_descriptor"]["payload_refs_redacted"] is True
    assert body["same_origin_delivery_enabled"] is False
    assert body["browser_download_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["provider_private_signed_url_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert body["downstream_unavailable"] == [
        "same_origin_delivery",
        "browser_download",
        "connector_dispatch",
        "provider_public_delivery",
        "provider_private_signed_url",
        "network_egress",
    ]

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        assert db.query(L3OutputPackage).count() == 3
        reconciliation = db.query(L3ReconciliationRecord).one()
        readiness = reconciliation.summary_json["external_export_download_prepare"]
        assert readiness["schema_id"] == "layer3.external_export_download_prepare_state.v1"
        assert readiness["external_export_download_prepare_schema_id"] == body["schema_id"]
        assert readiness["external_export_download_state"] == "external_export_download_prepared"
        assert readiness["external_export_download_record_ref"] == body["external_export_download_record_ref"]
        assert readiness["export_download_descriptor_ref"] == body["export_download_descriptor_ref"]
        assert readiness["payload_refs"] is None
        assert readiness["payload_refs_redacted"] is True
        assert readiness["source_gate"] == (
            "836_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE"
        )
    finally:
        db.close()

    status_payload = {
        key: value
        for key, value in submit_payload.items()
        if key
        not in {
            "qualitative_analysis_hash",
            "source_directory_hybrid_package_review_preview_hash",
            "construction_basis_hash",
            "reconciliation_record_id",
            "output_package_ids",
            "package_kinds",
            "payload_hashes",
            "operator_decision",
            "client_request_id",
        }
    }
    status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json={
            **status_payload,
            "client_request_id": "source-directory-hybrid-external-export-download-prepare-status",
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["source_directory_hybrid_handoff_export_prepare_available"] is True
    assert status_body["source_directory_hybrid_external_export_download_prepare_available"] is True
    assert (
        status_body["external_export_download_record_ref"]
        == body["external_export_download_record_ref"]
    )
    assert status_body["external_export_download_state"] == "external_export_download_prepared"
    assert status_body["external_export_download_target"] == (
        "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
    )
    assert status_body["export_download_descriptor_ref"] == body["export_download_descriptor_ref"]
    assert status_body["download_mode"] == "reference_only_prepare"
    assert status_body["external_export_download_enabled"] is False
    assert status_body["downstream_unavailable"] == [
        "same_origin_delivery",
        "browser_download",
        "connector_dispatch",
        "provider_public_delivery",
        "provider_private_signed_url",
        "network_egress",
    ]

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        json=prepare_payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "already_prepared"
    assert replay.json()["external_export_download_record_ref"] == body["external_export_download_record_ref"]

    stale = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        json={**prepare_payload, "payload_hashes": ["0" * 64, *prepare_payload["payload_hashes"][1:]]},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == (
        "source_directory_hybrid_external_export_download_prepare_package_authority_mismatch"
    )


def test_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivers_selected_package(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _analysis_body, prepare_body, prepare_payload = _hybrid_external_export_download_prepare_authority(
        client,
        tmp_path,
        monkeypatch,
        client_request_id="source-directory-hybrid-external-export-download-delivery",
    )
    selected_package = next(
        package for package in prepare_body["output_packages"] if package["package_kind"] == "user_facing"
    )
    delivery_payload = {
        **prepare_payload,
        "operator_decision": "deliver_source_directory_hybrid_external_export_download",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
        "output_package_id": selected_package["output_package_id"],
        "package_kind": selected_package["package_kind"],
        "package_payload_hash": selected_package["payload_hash"],
    }

    status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status"
        ),
        json=delivery_payload,
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status.v1"
    )
    assert status_body["delivery_available"] is True
    assert status_body["delivery_streaming_performed"] is False
    assert status_body["delivery_state"] == "external_export_download_delivered"
    assert status_body["same_origin_delivery_enabled"] is True
    assert status_body["browser_managed_same_origin_attachment_enabled"] is True
    assert status_body["provider_public_delivery_enabled"] is False
    assert status_body["provider_private_signed_url_enabled"] is False
    assert status_body["connector_dispatch_enabled"] is False
    assert status_body["network_egress_enabled"] is False
    assert status_body["frontend_durable_authority_enabled"] is False
    assert status_body["package_payload_rewrite_enabled"] is False
    assert status_body["source_package_row_mutation_enabled"] is False
    assert status_body["payload_ref_redacted"] is True
    assert status_body["raw_local_path_exposed"] is False
    assert status_body["output_package_id"] == selected_package["output_package_id"]
    assert status_body["package_payload_hash"] == selected_package["payload_hash"]

    delivery = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver"
        ),
        json=delivery_payload,
    )
    assert delivery.status_code == 200, delivery.text
    assert delivery.headers["X-Layer3-Schema-Id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery.v1"
    )
    assert delivery.headers["X-Layer3-Delivery-State"] == "external_export_download_delivered"
    assert (
        delivery.headers["X-Layer3-External-Export-Download-Record-Ref"]
        == prepare_body["external_export_download_record_ref"]
    )
    assert delivery.headers["X-Layer3-Source-Directory-Hybrid-Package-Kind"] == "user_facing"
    assert str(tmp_path) not in delivery.text

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(AnalysisRun).count() == 0
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        readiness = db.query(L3ReconciliationRecord).one().summary_json["external_export_download_prepare"]
        assert readiness["external_export_download_record_ref"] == prepare_body["external_export_download_record_ref"]
        assert "external_export_download_delivery" not in db.query(L3ReconciliationRecord).one().summary_json
    finally:
        db.close()

    stale = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status"
        ),
        json={**delivery_payload, "package_payload_hash": "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == (
        "source_directory_hybrid_external_export_download_delivery_payload_hash_mismatch"
    )


def test_source_directory_hybrid_context_packet_provider_private_to_public_redacted_use(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _analysis_body, prepare_body, prepare_payload = _hybrid_external_export_download_prepare_authority(
        client,
        tmp_path,
        monkeypatch,
        client_request_id="source-directory-hybrid-provider-private-redacted-delivery",
    )
    selected_package = next(
        package for package in prepare_body["output_packages"] if package["package_kind"] == "user_facing"
    )
    delivery_authority = {
        **prepare_payload,
        "operator_decision": "deliver_source_directory_hybrid_external_export_download",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
        "output_package_id": selected_package["output_package_id"],
        "package_kind": selected_package["package_kind"],
        "package_payload_hash": selected_package["payload_hash"],
    }
    provider_private = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/prepare"
        ),
        json={
            **delivery_authority,
            "client_request_id": "source-directory-provider-private-prepare",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "source-directory-redacted-delivery-test",
            "requested_ttl_seconds": 300,
        },
    )
    assert provider_private.status_code == 200, provider_private.text
    private_body = provider_private.json()
    assert private_body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url.prepare.v1"
    )
    assert private_body["status"] == "prepared"
    assert private_body["provider_signed_url_state"] == "provider_private_signed_url_prepared"
    assert private_body["provider_url_redacted"] == "provider-private-signed-url:redacted"
    assert private_body["source_artifact_hash"] == selected_package["payload_hash"]
    assert private_body["source_artifact_size_bytes"] > 0
    assert private_body["source_artifact_ref"] == "artifact://provider-private-signed-url-redacted"
    assert private_body["output_package_id"] == selected_package["output_package_id"]
    assert private_body["provider_private_signed_url_enabled"] is True
    assert private_body["provider_public_url_prepare_enabled"] is True
    assert private_body["provider_network_enabled"] is False
    assert private_body["provider_object_write_enabled"] is False
    assert private_body["connector_dispatch_enabled"] is False
    assert private_body["package_mutation_enabled"] is False
    assert private_body["source_expansion_enabled"] is False
    assert private_body["frontend_durable_authority_enabled"] is False
    assert private_body["raw_provider_private_signed_url_token_exposed"] is False
    assert str(tmp_path) not in json.dumps(private_body, sort_keys=True)

    forbidden_private = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/prepare"
        ),
        json={
            **delivery_authority,
            "client_request_id": "source-directory-provider-private-forbidden",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "source-directory-redacted-delivery-test",
            "requested_ttl_seconds": 300,
            "raw_provider_private_signed_url_token": "must-not-be-accepted",
        },
    )
    assert forbidden_private.status_code == 400, forbidden_private.text
    assert forbidden_private.json()["error"]["code"] == (
        "source_directory_hybrid_provider_private_signed_url_forbidden_field_not_admitted"
    )

    conflicting_private = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/prepare"
        ),
        json={
            **delivery_authority,
            "client_request_id": "source-directory-provider-private-prepare",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "source-directory-redacted-delivery-conflict",
            "requested_ttl_seconds": 300,
        },
    )
    assert conflicting_private.status_code == 409, conflicting_private.text
    assert conflicting_private.json()["error"]["code"] == (
        "provider_private_signed_url_state_idempotency_conflict"
    )

    provider_public = client.post(
        "/api/v1/layer3/handoff/export/download/provider-public-url/prepare",
        json={
            "client_request_id": "source-directory-provider-public-prepare",
            "provider_private_signed_url_receipt_id": private_body["provider_signed_url_receipt_id"],
            "recipient_scope": "source-directory-redacted-delivery-test",
            "requested_ttl_seconds": 300,
            "delivery_mode": "provider_public_url",
            "operator_decision": "prepare_provider_public_url",
        },
    )
    assert provider_public.status_code == 200, provider_public.text
    public_body = provider_public.json()
    assert public_body["status"] == "prepared"
    assert public_body["provider_public_url_state"] == "provider_public_url_prepared"
    assert public_body["provider_private_signed_url_receipt_id"] == (
        private_body["provider_signed_url_receipt_id"]
    )
    assert public_body["source_artifact_hash"] == private_body["source_artifact_hash"]
    assert public_body["source_artifact_size_bytes"] == private_body["source_artifact_size_bytes"]
    assert public_body["raw_public_url_exposed"] is False
    assert public_body["public_url_enabled"] is False

    delivery_use = client.post(
        "/api/v1/layer3/handoff/export/download/provider-public-url/use",
        json={
            "client_request_id": "source-directory-provider-public-use",
            "provider_public_url_receipt_id": public_body["provider_public_url_receipt_id"],
            "expected_source_artifact_hash": private_body["source_artifact_hash"],
            "expected_source_artifact_size_bytes": private_body["source_artifact_size_bytes"],
            "delivery_use_mode": "fake_provider_redacted_use_decision",
            "operator_decision": "use_provider_public_url_redacted_fake_provider",
        },
    )
    assert delivery_use.status_code == 200, delivery_use.text
    use_body = delivery_use.json()
    assert use_body["delivery_use_decision"] == "allowed"
    assert use_body["raw_public_url_exposed"] is False
    assert use_body["provider_network_enabled"] is False
    assert use_body["byte_streaming_enabled"] is False
    assert use_body["durable_use_row_created"] is False
    assert use_body["connector_dispatch_enabled"] is False
    assert use_body["package_mutation_enabled"] is False
    assert use_body["source_expansion_enabled"] is False
    assert use_body["frontend_durable_authority_enabled"] is False

    db = client.layer3_session_factory()
    try:
        assert db.query(L3ProviderPrivateSignedUrlObjectAuthority).count() == 1
        assert db.query(L3ProviderPrivateSignedUrlReceipt).count() == 1
        assert db.query(L3ProviderPrivateSignedUrlAuditEvent).count() == 1
        assert db.query(L3ProviderPublicUrlObjectAuthority).count() == 1
        assert db.query(L3ProviderPublicUrlReceipt).count() == 1
        assert db.query(AnalysisRun).count() == 0
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 3
    finally:
        db.close()


def test_representative_mockup_scenario_source_to_output_handoff_e2e_proof(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    mockup_contract = mockup_truth_state_contract()
    assert mockup_contract["mode"] == "mockups_target_state_only"
    assert mockup_contract["mockups_are_runtime_authority"] is False
    assert mockup_contract["full_mockup_activation_enabled"] is False
    assert mockup_contract["frontend_only_durable_state_enabled"] is False

    source_dir = tmp_path / "representative-source-dir"
    _write_vector_retrieval_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))
    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("representative-mockup-scenario-scan"),
    )
    assert scan.status_code == 201, scan.text
    scan_body = scan.json()
    assert scan_body["schema_id"] == "layer3.source_directory_ingestion_batch.v1"
    assert scan_body["mode"] == "server_configured_operator_directory_text_table_ingestion"
    assert scan_body["config_authority"] == "LAYER3_SOURCE_INGESTION_DIR"
    assert scan_body["source_root_ref"] == "server-configured://LAYER3_SOURCE_INGESTION_DIR"
    assert scan_body["source_root_absolute_path_exposed"] is False
    assert scan_body["caller_selected_recursive_flag_allowed"] is False
    assert scan_body["eligible_file_count"] == 1
    assert scan_body["negative_invariants"]["caller_supplied_paths_enabled"] is False
    assert scan_body["negative_invariants"]["caller_selected_recursive_flag_enabled"] is False
    assert scan_body["negative_invariants"]["browser_file_upload_enabled"] is False
    assert scan_body["negative_invariants"]["connector_dispatch_enabled"] is False
    assert str(source_dir) not in scan.text

    status = client.get(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/status/"
            f"{scan_body['source_ingestion_batch_id']}"
        )
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["schema_id"] == "layer3.source_directory_ingestion_status.v1"
    assert status_body["mode"] == "server_configured_operator_directory_text_table_ingestion_status"
    assert status_body["source_ingestion_batch_id"] == scan_body["source_ingestion_batch_id"]
    assert status_body["authority_basis_hash"] == scan_body["authority_basis_hash"]
    assert str(source_dir) not in status.text

    material_preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body),
    )
    assert material_preview.status_code == 200, material_preview.text
    preview_body = material_preview.json()
    candidate = preview_body["material_candidate"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "representative-mockup-scenario-gate-b",
            "preflight_id": "preflight-representative-mockup-scenario",
            "source_set_id": scan_body["source_ingestion_batch_id"],
            "material_preview_id": preview_body["material_preview_id"],
            "material_preview_hash": preview_body["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": candidate,
                }
            ],
        },
    )
    assert gate_b.status_code == 200, gate_b.text
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == gate_b.json()["session_id"])
            .one()
        )
        snapshot_info = {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "payload_hash": snapshot.payload_hash,
            "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
            "source_ingestion_file_id": candidate["payload"]["source_ingestion_file_id"],
            "content_sha256": candidate["payload"]["content_sha256"],
            "file_identity_hash": candidate["payload"]["file_identity_hash"],
            "authority_basis_hash": candidate["payload"]["authority_basis_hash"],
        }
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()

    db = client.layer3_session_factory()
    try:
        text_index = source_directory_material_text_index(db, _text_index_payload(snapshot_info))
        vector_index = source_directory_material_embedding_vector_index(
            db,
            _vector_index_payload(snapshot_info, text_index["index_authority_hash"]),
        )
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()

    analysis_payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            text_index["index_authority_hash"],
            vector_index["embedding_index_authority_hash"],
            "BETA alpha alpha",
        ),
        "client_request_id": "representative-mockup-scenario-analysis",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "representative mockup source to output handoff proof",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    assert analysis_body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis.v1"
    )
    assert analysis_body["status"] == "available"
    assert analysis_body["source_directory_package_review_preview_enabled"] is True
    assert analysis_body["package_commit_enabled"] is False
    assert analysis_body["package_review_submit_enabled"] is False
    assert analysis_body["handoff_enabled"] is False
    assert analysis_body["external_export_download_enabled"] is False
    _assert_disabled_authority_flags(analysis_body)
    assert str(source_dir) not in analysis.text

    precommit_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json=analysis_payload,
    )
    assert precommit_status.status_code == 200, precommit_status.text
    precommit_status_body = precommit_status.json()
    assert precommit_status_body["source_directory_hybrid_package_commit_available"] is False
    assert precommit_status_body["next_allowed_actions"] == [
        "commit_source_directory_hybrid_context_packet_qualitative_analysis_package"
    ]
    _assert_disabled_authority_flags(precommit_status_body)

    commit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()
    assert commit_body["status"] == "committed"
    assert commit_body["package_rows_written"] is True
    assert commit_body["package_payloads_written"] is True
    assert commit_body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert commit_body["payload_refs_redacted"] is True
    assert commit_body["external_export_download_enabled"] is False
    _assert_disabled_authority_flags(commit_body)
    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        assert db.query(L3OutputPackage).count() == 3
        summary = db.query(L3ReconciliationRecord).one().summary_json
        assert "source_directory_hybrid_context_qualitative_package_commit" in summary
    finally:
        db.close()

    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": (
            analysis_body["source_directory_hybrid_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
    }
    submit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    submit_body = submit.json()
    assert submit_body["status"] == "submitted"
    assert submit_body["package_review_state"] == "package_review_approved"
    assert submit_body["handoff_enabled"] is True
    assert submit_body["export_enabled"] is True
    assert submit_body["external_export_download_enabled"] is False
    _assert_disabled_authority_flags(submit_body)
    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        summary = db.query(L3ReconciliationRecord).one().summary_json
        assert summary["package_review_submit"]["submit_record_ref"] == submit_body["submit_record_ref"]
    finally:
        db.close()

    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    handoff = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_body = handoff.json()
    assert handoff_body["status"] == "prepared"
    assert handoff_body["handoff_export_state"] == "handoff_export_prepared"
    assert handoff_body["handoff_export_envelope"]["payload_refs"] is None
    assert handoff_body["handoff_export_envelope"]["payload_refs_redacted"] is True
    _assert_disabled_authority_flags(handoff_body)
    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        summary = db.query(L3ReconciliationRecord).one().summary_json
        assert summary["handoff_export_prepare"]["prepare_record_ref"] == handoff_body["prepare_record_ref"]
    finally:
        db.close()

    prepare_payload = {
        **handoff_payload,
        "operator_decision": "prepare_source_directory_hybrid_external_export_download",
        "prepare_record_ref": handoff_body["prepare_record_ref"],
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": handoff_body["handoff_export_envelope"]["envelope_ref"],
        "external_export_download_target": (
            "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
        ),
        "download_mode": "reference_only_prepare",
    }
    prepare = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        json=prepare_payload,
    )
    assert prepare.status_code == 200, prepare.text
    prepare_body = prepare.json()
    assert prepare_body["status"] == "prepared"
    assert prepare_body["external_export_download_state"] == "external_export_download_prepared"
    assert prepare_body["external_export_download_descriptor"]["payload_refs"] is None
    assert prepare_body["external_export_download_descriptor"]["payload_refs_redacted"] is True
    assert prepare_body["same_origin_delivery_enabled"] is False
    _assert_disabled_authority_flags(prepare_body)
    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        summary = db.query(L3ReconciliationRecord).one().summary_json
        readiness = summary["external_export_download_prepare"]
        assert readiness["external_export_download_record_ref"] == prepare_body["external_export_download_record_ref"]
        assert readiness["payload_refs"] is None
        assert readiness["payload_refs_redacted"] is True
    finally:
        db.close()

    status_payload = {
        key: value
        for key, value in submit_payload.items()
        if key
        not in {
            "qualitative_analysis_hash",
            "source_directory_hybrid_package_review_preview_hash",
            "construction_basis_hash",
            "reconciliation_record_id",
            "output_package_ids",
            "package_kinds",
            "payload_hashes",
            "operator_decision",
            "client_request_id",
        }
    }
    post_prepare_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json={**status_payload, "client_request_id": "representative-mockup-scenario-status-after-prepare"},
    )
    assert post_prepare_status.status_code == 200, post_prepare_status.text
    post_prepare_status_body = post_prepare_status.json()
    assert post_prepare_status_body["source_directory_hybrid_package_commit_available"] is True
    assert post_prepare_status_body["source_directory_hybrid_package_review_submit_available"] is True
    assert post_prepare_status_body["source_directory_hybrid_handoff_export_prepare_available"] is True
    assert post_prepare_status_body["source_directory_hybrid_external_export_download_prepare_available"] is True
    assert post_prepare_status_body["external_export_download_enabled"] is False
    _assert_disabled_authority_flags(post_prepare_status_body)

    selected_package = next(
        package for package in prepare_body["output_packages"] if package["package_kind"] == "user_facing"
    )
    delivery_payload = {
        **prepare_payload,
        "operator_decision": "deliver_source_directory_hybrid_external_export_download",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
        "output_package_id": selected_package["output_package_id"],
        "package_kind": selected_package["package_kind"],
        "package_payload_hash": selected_package["payload_hash"],
    }
    delivery_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status"
        ),
        json=delivery_payload,
    )
    assert delivery_status.status_code == 200, delivery_status.text
    delivery_status_body = delivery_status.json()
    assert delivery_status_body["delivery_available"] is True
    assert delivery_status_body["delivery_streaming_performed"] is False
    assert delivery_status_body["delivery_state"] == "external_export_download_delivered"
    assert delivery_status_body["same_origin_delivery_enabled"] is True
    assert delivery_status_body["browser_managed_same_origin_attachment_enabled"] is True
    assert delivery_status_body["payload_ref_redacted"] is True
    assert delivery_status_body["raw_local_path_exposed"] is False
    _assert_disabled_authority_flags(delivery_status_body)

    delivery = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver"
        ),
        json=delivery_payload,
    )
    assert delivery.status_code == 200, delivery.text
    assert delivery.headers["X-Layer3-Schema-Id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery.v1"
    )
    assert delivery.headers["X-Layer3-Delivery-State"] == "external_export_download_delivered"
    assert delivery.headers["X-Layer3-Source-Directory-Hybrid-Package-Kind"] == "user_facing"
    assert str(source_dir) not in delivery.text
    assert "http://" not in delivery.text
    assert "https://" not in delivery.text

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        summary = db.query(L3ReconciliationRecord).one().summary_json
        assert summary["external_export_download_prepare"]["external_export_download_record_ref"] == (
            prepare_body["external_export_download_record_ref"]
        )
        assert "external_export_download_delivery" not in summary
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch_success_idempotent_and_redacted(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/source-directory-webhook")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "source-directory-test-webhook")
    _analysis_body, prepare_body, prepare_payload = _hybrid_external_export_download_prepare_authority(
        client,
        tmp_path,
        monkeypatch,
        client_request_id="source-directory-internal-webhook-analysis",
    )
    dispatch_path = (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch"
    )
    calls: list[dict] = []

    def fake_transport(url, envelope, headers, timeout):
        calls.append({"url": url, "envelope": envelope, "headers": headers, "timeout": timeout})
        return 202, {"accepted": True, "receipt": "source-directory-ok"}

    monkeypatch.setattr(layer3_internal_webhook_connector, "INTERNAL_WEBHOOK_TRANSPORT", fake_transport)
    payload = _source_directory_internal_webhook_payload(
        prepare_body,
        prepare_payload,
        request_id="source-directory-internal-webhook-dispatch",
    )

    dispatch = client.post(dispatch_path, json=payload)
    assert dispatch.status_code == 200, dispatch.text
    body = dispatch.json()
    assert body["schema_id"] == "layer3.source_directory_internal_webhook.dispatch.v1"
    assert body["status"] == "dispatched"
    assert body["source_directory_internal_webhook_dispatch_state"] == (
        "source_directory_internal_webhook_dispatched"
    )
    assert body["source_directory_internal_webhook_post_performed"] is True
    assert body["internal_webhook_network_egress_enabled"] is True
    assert body["connector_dispatch_enabled"] is False
    assert body["connector_run_created"] is False
    assert body["provider_public_url_enabled"] is False
    assert body["provider_private_signed_url_enabled"] is False
    assert body["package_mutation_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["redacted_destination_display_name"] == "source-directory-test-webhook"
    assert body["redacted_response_summary"]["response_keys"] == ["accepted", "receipt"]
    assert len(calls) == 1
    assert calls[0]["url"] == "http://127.0.0.1/source-directory-webhook"
    assert calls[0]["timeout"] == 5.0
    assert calls[0]["headers"]["X-Layer3-Envelope-Schema"] == (
        "layer3.source_directory_internal_webhook.delivery_envelope.v1"
    )
    envelope = calls[0]["envelope"]
    assert envelope["schema_id"] == "layer3.source_directory_internal_webhook.delivery_envelope.v1"
    assert envelope["raw_package_bytes_included"] is False
    assert envelope["raw_package_payload_included"] is False
    assert envelope["raw_target_url_included"] is False
    envelope_text = json.dumps(envelope, sort_keys=True)
    assert "http://127.0.0.1/source-directory-webhook" not in envelope_text
    assert str(tmp_path) not in envelope_text

    status = client.get(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/status/"
            f"{body['source_directory_internal_webhook_dispatch_receipt_id']}"
        )
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["schema_id"] == "layer3.source_directory_internal_webhook.status.v1"
    assert status_body["source_directory_internal_webhook_dispatch_state"] == (
        "source_directory_internal_webhook_dispatched"
    )
    assert status_body["source_directory_internal_webhook_dispatch_receipt_id"] == (
        body["source_directory_internal_webhook_dispatch_receipt_id"]
    )

    summary = client.get(f"/api/v1/layer3/session/{body['session_id']}")
    assert summary.status_code == 200, summary.text
    dispatch_status = summary.json()["internal_webhook_dispatch"]
    assert dispatch_status["schema_id"] == "layer3.internal_webhook.status.v1"
    assert dispatch_status["state"] == "source_directory_internal_webhook_dispatched"
    assert dispatch_status["response_authority"] == "durable_source_directory_internal_webhook_dispatch_receipt_row"
    assert dispatch_status["source_directory_internal_webhook_dispatch_receipt_id"] == (
        body["source_directory_internal_webhook_dispatch_receipt_id"]
    )
    assert dispatch_status["source_directory_internal_webhook_post_performed"] is True
    assert dispatch_status["operator_destination_url_enabled"] is False
    assert dispatch_status["raw_target_url_exposed"] is False
    assert dispatch_status["raw_package_payload_exposed"] is False
    assert dispatch_status["raw_package_bytes_exposed"] is False
    assert dispatch_status["connector_run_created"] is False
    assert dispatch_status["connector_run_target_created"] is False
    assert dispatch_status["rendered_write_submit_control_enabled"] is False
    assert dispatch_status["source_directory_internal_webhook_dispatch_history_count"] == 1
    assert dispatch_status["audit_event_history_count"] == 2
    dispatch_status_text = json.dumps(dispatch_status, sort_keys=True)
    assert "http://127.0.0.1/source-directory-webhook" not in dispatch_status_text
    assert str(tmp_path) not in dispatch_status_text

    replay = client.post(dispatch_path, json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "already_recorded"
    assert replay.json()["source_directory_internal_webhook_dispatch_receipt_id"] == (
        body["source_directory_internal_webhook_dispatch_receipt_id"]
    )
    assert len(calls) == 1

    new_key_replay = client.post(
        dispatch_path,
        json={
            **payload,
            "client_request_id": "source-directory-internal-webhook-dispatch-second-key",
        },
    )
    assert new_key_replay.status_code == 200, new_key_replay.text
    assert new_key_replay.json()["status"] == "already_recorded"
    assert new_key_replay.json()["source_directory_internal_webhook_dispatch_receipt_id"] == (
        body["source_directory_internal_webhook_dispatch_receipt_id"]
    )
    assert len(calls) == 1

    db = client.layer3_session_factory()
    try:
        assert db.query(L3SourceDirectoryInternalWebhookDispatchReceipt).count() == 1
        assert db.query(L3SourceDirectoryInternalWebhookDispatchAuditEvent).count() == 4
        _assert_no_forbidden_package_commit_downstream(db)
        reconciliation = db.query(L3ReconciliationRecord).one()
        state = reconciliation.summary_json["source_directory_internal_webhook_dispatch"]
        assert state["state"] == "source_directory_internal_webhook_dispatched"
        assert state["source_directory_internal_webhook_post_performed"] is True
        assert state["connector_run_created"] is False
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch_fails_closed_on_stale_readiness(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/source-directory-webhook")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "source-directory-test-webhook")
    _analysis_body, prepare_body, prepare_payload = _hybrid_external_export_download_prepare_authority(
        client,
        tmp_path,
        monkeypatch,
        client_request_id="source-directory-internal-webhook-stale-analysis",
    )
    calls: list[dict] = []

    def fake_transport(url, envelope, headers, timeout):
        calls.append({"url": url, "envelope": envelope, "headers": headers, "timeout": timeout})
        return 202, {"accepted": True}

    monkeypatch.setattr(layer3_internal_webhook_connector, "INTERNAL_WEBHOOK_TRANSPORT", fake_transport)
    stale_payload = _source_directory_internal_webhook_payload(
        prepare_body,
        prepare_payload,
        request_id="source-directory-internal-webhook-stale",
    )
    stale_payload["external_export_download_record_ref"] = "stale-external-export-download-record"
    stale = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch"
        ),
        json=stale_payload,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error_code"] == "source_directory_internal_webhook_readiness_mismatch"
    assert "external_export_download_record_ref" in stale.json()["blocked_fields"]
    assert calls == []
    db = client.layer3_session_factory()
    try:
        assert db.query(L3SourceDirectoryInternalWebhookDispatchReceipt).count() == 0
        assert db.query(L3SourceDirectoryInternalWebhookDispatchAuditEvent).count() == 0
        _assert_no_forbidden_package_commit_downstream(db)
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert "source_directory_internal_webhook_dispatch" not in reconciliation.summary_json
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_status_reports_existing_review_and_handoff_state(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    analysis_body, commit_body, submit_body, submit_payload, embedding_index_authority_hash = (
        _hybrid_package_review_submit_authority(
            client,
            tmp_path,
            monkeypatch,
            client_request_id="source-directory-hybrid-status-existing-state-analysis",
        )
    )
    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    handoff = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_body = handoff.json()

    db = client.layer3_session_factory()
    try:
        package_count = db.query(L3OutputPackage).count()
        reconciliation_count = db.query(L3ReconciliationRecord).count()
    finally:
        db.close()

    status_payload = {
        key: value
        for key, value in submit_payload.items()
        if key
        not in {
            "qualitative_analysis_hash",
            "source_directory_hybrid_package_review_preview_hash",
            "construction_basis_hash",
            "reconciliation_record_id",
            "output_package_ids",
            "package_kinds",
            "payload_hashes",
            "operator_decision",
            "client_request_id",
        }
    }
    status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json=status_payload,
    )

    assert status.status_code == 200, status.text
    body = status.json()
    assert body["schema_id"] == (
        "layer3.source_directory_hybrid_context_packet_qualitative_analysis_status.v1"
    )
    assert body["qualitative_analysis_hash"] == analysis_body["qualitative_analysis_hash"]
    assert body["hybrid_context_packet_hash"] == analysis_body["hybrid_context_packet_hash"]
    assert body["embedding_index_authority_hash"] == embedding_index_authority_hash
    assert body["source_directory_hybrid_package_commit_available"] is True
    assert body["source_directory_hybrid_package_review_submit_available"] is True
    assert body["source_directory_hybrid_handoff_export_prepare_available"] is True
    assert body["source_directory_hybrid_external_export_download_prepare_available"] is False
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["construction_basis_hash"] == commit_body["construction_basis_hash"]
    assert body["output_package_ids"] == commit_body["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["payload_refs_redacted"] is True
    assert body["package_review_state"] == "package_review_approved"
    assert body["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
    assert body["handoff_export_state"] == "handoff_export_prepared"
    assert body["handoff_export_prepare_record_ref"] == handoff_body["prepare_record_ref"]
    assert body["handoff_target"] == "internal_export_envelope"
    assert body["export_mode"] == "prepare_only"
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is False
    assert body["export_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["provider_private_signed_url_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert body["downstream_unavailable"] == [
        "external_export_download",
        "connector_dispatch",
        "provider_public_delivery",
        "provider_private_signed_url",
        "network_egress",
    ]
    assert body["status_defects"] == []
    assert body["next_allowed_actions"] == []
    assert "source_directory_hybrid_package_review_preview" not in body
    assert "supporting_segments" not in body

    polling_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json={
            **status_payload,
            "client_request_id": "source-directory-hybrid-status-polling-read",
        },
    )
    assert polling_status.status_code == 200, polling_status.text
    polling_body = polling_status.json()
    assert polling_body["qualitative_analysis_hash"] == analysis_body["qualitative_analysis_hash"]
    assert polling_body["source_directory_hybrid_package_commit_available"] is True
    assert polling_body["source_directory_hybrid_package_review_submit_available"] is True
    assert polling_body["source_directory_hybrid_handoff_export_prepare_available"] is True

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == package_count
        assert db.query(L3ReconciliationRecord).count() == reconciliation_count
        _assert_no_forbidden_package_commit_downstream(db)
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_requires_approved_submit(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _analysis_body, _commit_body, submit_body, submit_payload, _embedding_hash = (
        _hybrid_package_review_submit_authority(
            client,
            tmp_path,
            monkeypatch,
            client_request_id="source-directory-hybrid-handoff-export-prepare-rejected-analysis",
            submit_decision="rejected",
            decision_notes="not ready",
        )
    )
    blocked = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json={
            **submit_payload,
            "operator_decision": "authorize_prepare",
            "package_review_submit_record_ref": submit_body["submit_record_ref"],
            "package_review_state": "package_review_approved",
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
        },
    )

    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "source_directory_hybrid_handoff_export_prepare_submit_not_approved"
    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert "handoff_export_prepare" not in reconciliation.summary_json
    finally:
        db.close()


def test_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_rejects_stale_construction(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    analysis_payload = {
        **_vector_retrieval_payload(
            snapshot_info,
            index_authority_hash,
            embedding_index_authority_hash,
            "BETA alpha alpha",
        ),
        "client_request_id": "source-directory-hybrid-package-submit-stale-analysis",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic hybrid package submit stale evidence",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()

    commit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()

    stale = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "construction_basis_hash": "0" * 64,
            "reconciliation_record_id": commit_body["reconciliation_record_id"],
            "output_package_ids": commit_body["output_package_ids"],
            "package_kinds": commit_body["package_kinds"],
            "payload_hashes": commit_body["payload_hashes"],
            "operator_decision": "approved",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == (
        "source_directory_hybrid_package_review_submit_construction_mismatch"
    )

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert "package_review_submit" not in reconciliation.summary_json
        _assert_no_forbidden_package_commit_downstream(db)
    finally:
        db.close()


def test_source_directory_vector_retrieval_rejects_stale_authority_hashes(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryVectorRetrievalError) as stale_embedding:
            source_directory_material_vector_retrieval(
                db,
                _vector_retrieval_payload(snapshot_info, index_authority_hash, "0" * 64, "alpha beta"),
            )
        assert stale_embedding.value.code == "source_directory_vector_retrieval_stale_embedding_index_authority"
        assert stale_embedding.value.details["blocked_fields"] == ["embedding_index_authority_hash"]

        with pytest.raises(SourceDirectoryVectorIndexError) as stale_index:
            source_directory_material_vector_retrieval(
                db,
                _vector_retrieval_payload(
                    snapshot_info,
                    "0" * 64,
                    embedding_index_authority_hash,
                    "alpha beta",
                ),
            )
        assert stale_index.value.code == "source_directory_vector_index_stale_index_authority"
        assert stale_index.value.details["blocked_fields"] == ["index_authority_hash"]
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_vector_retrieval_uses_vector_index_fail_closed_authority_path(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )
    (source_dir / "vector-retrieval.txt").write_text("alpha beta drift\n", encoding="utf-8")

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_vector_retrieval(
                db,
                _vector_retrieval_payload(
                    snapshot_info,
                    index_authority_hash,
                    embedding_index_authority_hash,
                    "alpha beta",
                ),
            )
        assert exc_info.value.code == "source_directory_text_index_file_identity_mismatch"
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_vector_retrieval_validates_query_top_k_and_contract_fields(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, index_authority_hash, embedding_index_authority_hash = _admitted_material(
        client,
        tmp_path,
        monkeypatch,
    )

    db = client.layer3_session_factory()
    try:
        no_match = source_directory_material_vector_retrieval(
            db,
            _vector_retrieval_payload(
                snapshot_info,
                index_authority_hash,
                embedding_index_authority_hash,
                "nohitbucketxqzv",
            ),
        )
        assert no_match["total"] == 0
        assert no_match["items"] == []
        assert no_match["top_k"] == 10

        page = source_directory_material_vector_retrieval(
            db,
            {
                **_vector_retrieval_payload(
                    snapshot_info,
                    index_authority_hash,
                    embedding_index_authority_hash,
                    "alpha beta",
                ),
                "top_k": "1",
            },
        )
        assert page["total"] >= 1
        assert page["top_k"] == 1
        assert len(page["items"]) == 1

        with pytest.raises(SourceDirectoryVectorRetrievalError) as empty_query:
            source_directory_material_vector_retrieval(
                db,
                _vector_retrieval_payload(
                    snapshot_info,
                    index_authority_hash,
                    embedding_index_authority_hash,
                    " , ",
                ),
            )
        assert empty_query.value.code == "source_directory_vector_retrieval_empty_query"

        with pytest.raises(SourceDirectoryVectorRetrievalError) as forbidden:
            source_directory_material_vector_retrieval(
                db,
                {
                    **_vector_retrieval_payload(
                        snapshot_info,
                        index_authority_hash,
                        embedding_index_authority_hash,
                        "alpha beta",
                    ),
                    "prompt": "not-admitted",
                    "provider_model": "not-admitted",
                    "rag_prompt": "not-admitted",
                    "vector": [1.0],
                },
            )
        assert forbidden.value.code == "source_directory_vector_retrieval_forbidden_field_not_admitted"
        assert forbidden.value.details["forbidden_fields"] == [
            "prompt",
            "provider_model",
            "rag_prompt",
            "vector",
        ]

        with pytest.raises(SourceDirectoryVectorRetrievalError) as unknown:
            source_directory_material_vector_retrieval(
                db,
                {
                    **_vector_retrieval_payload(
                        snapshot_info,
                        index_authority_hash,
                        embedding_index_authority_hash,
                        "alpha beta",
                    ),
                    "result_shape": "not-admitted",
                },
            )
        assert unknown.value.code == "source_directory_vector_retrieval_unknown_field"
        assert unknown.value.details["unknown_fields"] == ["result_shape"]

        with pytest.raises(SourceDirectoryVectorRetrievalError) as bad_top_k:
            source_directory_material_vector_retrieval(
                db,
                {
                    **_vector_retrieval_payload(
                        snapshot_info,
                        index_authority_hash,
                        embedding_index_authority_hash,
                        "alpha beta",
                    ),
                    "top_k": 21,
                },
            )
        assert bad_top_k.value.code == "source_directory_vector_retrieval_top_k_out_of_bounds"

        with pytest.raises(SourceDirectoryVectorRetrievalError) as bool_top_k:
            source_directory_material_vector_retrieval(
                db,
                {
                    **_vector_retrieval_payload(
                        snapshot_info,
                        index_authority_hash,
                        embedding_index_authority_hash,
                        "alpha beta",
                    ),
                    "top_k": True,
                },
            )
        assert bool_top_k.value.code == "source_directory_vector_retrieval_integer_field_invalid"
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()
