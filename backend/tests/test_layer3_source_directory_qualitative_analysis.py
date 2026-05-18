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
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
)
from app.services import layer3_source_directory_qualitative_analysis as qual_service
from app.services.layer3_source_directory_context_packet import CONTEXT_PACKET_CONTRACT_ID, CONTEXT_PACKET_MODE
from app.services.layer3_source_directory_text_index import (
    SourceDirectoryTextIndexError,
    source_directory_material_text_index,
)
from app.services.layer3_source_directory_text_retrieval import SourceDirectoryTextRetrievalError
from app.services.layer3_source_directory_qualitative_analysis import (
    SourceDirectoryQualitativeAnalysisError,
    source_directory_material_context_packet_qualitative_hybrid_analysis,
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


def _scan_payload(client_request_id: str = "source-directory-qualitative-analysis-scan") -> dict[str, str]:
    return {
        "client_request_id": client_request_id,
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _write_analysis_source_dir(root: Path) -> None:
    root.mkdir()
    lines = ["alpha beta beta lead\n"]
    lines.extend(f"context filler line {index}\n" for index in range(1, 42))
    lines.append("alpha beta tail\n")
    (root / "analysis.txt").write_text("".join(lines), encoding="utf-8")


def _material_preview_payload(scan_body: dict, relative_name: str = "analysis.txt") -> dict[str, str]:
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
            "client_request_id": "source-directory-qualitative-analysis-gate-b",
            "preflight_id": "preflight-source-directory-qualitative-analysis",
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


def _analysis_payload(
    snapshot_info: dict[str, str],
    index_authority_hash: str,
    query_text: str,
) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-qualitative-analysis-{snapshot_info['source_ingestion_file_id']}",
        "analysis_question": "What does the alpha beta evidence support?",
        "analysis_focus": "deterministic context packet evidence",
        **snapshot_info,
        "index_authority_hash": index_authority_hash,
        "query_text": query_text,
    }


def _admitted_material(client: TestClient, tmp_path, monkeypatch) -> tuple[Path, dict[str, str], str]:
    source_dir = tmp_path / "operator-source-dir"
    _write_analysis_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))
    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json())
    db = client.layer3_session_factory()
    try:
        index_body = source_directory_material_text_index(db, _text_index_payload(snapshot_info))
    finally:
        db.close()
    return source_dir, snapshot_info, index_body["index_authority_hash"]


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


def test_source_directory_qualitative_analysis_returns_deterministic_extract_without_side_effects(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        payload = {
            **_analysis_payload(snapshot_info, index_authority_hash, "BETA alpha alpha"),
            "limit": 2,
            "offset": 0,
        }
        body = source_directory_material_context_packet_qualitative_hybrid_analysis(db, payload)
        replay = source_directory_material_context_packet_qualitative_hybrid_analysis(db, payload)

        assert body["schema_id"] == "layer3.source_directory_qualitative_analysis.v1"
        assert body["mode"] == "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
        assert body["status"] == "available"
        assert body["analysis_contract_id"] == "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
        assert body["analysis_mode"] == "context_packet_grounded_qualitative_hybrid_analysis"
        assert body["context_packet_contract_id"] == CONTEXT_PACKET_CONTRACT_ID
        assert body["context_packet_mode"] == CONTEXT_PACKET_MODE
        assert body["qualitative_analysis_hash"] == replay["qualitative_analysis_hash"]
        assert body["context_packet_hash"] == replay["context_packet_hash"]
        assert body["source_directory_package_review_preview_enabled"] is True
        assert (
            body["source_directory_package_review_preview_hash"]
            == replay["source_directory_package_review_preview_hash"]
        )
        package_preview = body["source_directory_package_review_preview"]
        assert package_preview["schema_id"] == (
            "layer3.source_directory_qualitative_analysis_package_review_preview.v1"
        )
        assert package_preview["mode"] == "read_only_source_directory_qualitative_analysis_package_review_preview"
        assert package_preview["source_gate"] == (
            "802_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE"
        )
        assert package_preview["source_authority"]["qualitative_analysis_hash"] == body["qualitative_analysis_hash"]
        assert package_preview["candidate_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
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
        assert package_preview["negative_invariants"]["package_payload_written"] is False
        assert package_preview["negative_invariants"]["source_package_row_mutation_enabled"] is False
        assert body["candidate_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
        assert body["package_commit_enabled"] is False
        assert body["package_review_submit_enabled"] is False
        assert body["handoff_enabled"] is False
        assert body["external_export_download_enabled"] is False
        assert body["query_tokens"] == ["alpha", "beta"]
        assert body["total"] == 2
        assert body["limit"] == 2
        assert body["offset"] == 0
        assert body["evidence_summary"]["coverage_label"] == "complete_context_matches"
        assert body["evidence_summary"]["context_segments_considered"] == 2
        assert [term["term"] for term in body["salient_terms"]] == ["alpha", "beta"]
        assert body["supporting_segments"][0]["rank_position"] == 1
        assert body["supporting_segments"][0]["support_label"] == "primary_context_segment"
        assert "quote_excerpt" in body["supporting_segments"][0]
        assert "text" not in body["supporting_segments"][0]
        assert body["supporting_segments"][0]["summed_term_frequency"] > body["supporting_segments"][1]["summed_term_frequency"]
        assert body["source_index_rows_written"] is False
        assert body["retrieval_rows_written"] is False
        assert body["context_packet_rows_written"] is False
        assert body["qualitative_analysis_rows_written"] is False
        assert body["qualitative_generation_rows_written"] is False
        assert body["analysis_run_rows_written"] is False
        assert body["package_rows_written"] is False
        assert body["connector_rows_written"] is False
        assert body["negative_invariants"]["vector_index_enabled"] is False
        assert body["negative_invariants"]["embedding_generation_enabled"] is False
        assert body["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
        assert body["negative_invariants"]["qualitative_generation_runtime_enabled"] is False
        assert body["negative_invariants"]["connector_dispatch_enabled"] is False
        assert body["negative_invariants"]["provider_public_delivery_enabled"] is False
        assert str(source_dir) not in str(body)
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_qualitative_analysis_rejects_stale_authority_through_context_packet_path(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextRetrievalError) as stale_index:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                _analysis_payload(snapshot_info, "0" * 64, "alpha beta"),
            )
        assert stale_index.value.code == "source_directory_text_retrieval_stale_index_authority"

        (source_dir / "analysis.txt").write_text("alpha beta drift\n", encoding="utf-8")
        with pytest.raises(SourceDirectoryTextIndexError) as stale_source:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                _analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
            )
        assert stale_source.value.code == "source_directory_text_index_file_identity_mismatch"
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_qualitative_analysis_validates_request_fields_and_no_match(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        no_match = source_directory_material_context_packet_qualitative_hybrid_analysis(
            db,
            _analysis_payload(snapshot_info, index_authority_hash, "notpresent"),
        )
        no_match_replay = source_directory_material_context_packet_qualitative_hybrid_analysis(
            db,
            _analysis_payload(snapshot_info, index_authority_hash, "notpresent"),
        )
        assert no_match["total"] == 0
        assert no_match["supporting_segments"] == []
        assert no_match["evidence_summary"]["coverage_label"] == "no_context_matches"
        assert no_match["qualitative_analysis_hash"] == no_match_replay["qualitative_analysis_hash"]
        assert any(limit["code"] == "no_supporting_segments" for limit in no_match["analysis_limits"])

        page = source_directory_material_context_packet_qualitative_hybrid_analysis(
            db,
            {
                **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
                "limit": 1,
                "offset": 1,
            },
        )
        assert page["total"] == 2
        assert page["limit"] == 1
        assert page["offset"] == 1
        assert page["supporting_segments"][0]["rank_position"] == 2
        assert page["evidence_summary"]["coverage_label"] == "paged_context_matches"

        with pytest.raises(SourceDirectoryQualitativeAnalysisError) as empty_question:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                {
                    **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "analysis_question": "  ",
                },
            )
        assert empty_question.value.code == "source_directory_qualitative_analysis_required_field_missing"
        assert empty_question.value.details["field"] == "analysis_question"

        with pytest.raises(SourceDirectoryTextRetrievalError) as empty_query:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                _analysis_payload(snapshot_info, index_authority_hash, " , "),
            )
        assert empty_query.value.code == "source_directory_text_retrieval_empty_query"

        with pytest.raises(SourceDirectoryQualitativeAnalysisError) as forbidden:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                {
                    **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "prompt": "not-admitted",
                    "vector_index": "not-admitted",
                    "runtime_db_write": True,
                },
            )
        assert forbidden.value.code == "source_directory_qualitative_analysis_forbidden_field_not_admitted"
        assert forbidden.value.details["forbidden_fields"] == ["prompt", "runtime_db_write", "vector_index"]

        with pytest.raises(SourceDirectoryQualitativeAnalysisError) as unknown:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                {
                    **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "result_shape": "not-admitted",
                },
            )
        assert unknown.value.code == "source_directory_qualitative_analysis_unknown_field"
        assert unknown.value.details["unknown_fields"] == ["result_shape"]

        with pytest.raises(SourceDirectoryTextRetrievalError) as bad_limit:
            source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                {
                    **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "limit": 51,
                },
            )
        assert bad_limit.value.code == "source_directory_text_retrieval_limit_out_of_bounds"
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_qualitative_analysis_validates_context_packet_authority(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_context_packet(db, payload):
        return {
            "schema_id": "wrong.schema",
            "context_packet_contract_id": "wrong_contract",
            "context_packet_mode": "wrong_mode",
        }

    monkeypatch.setattr(
        qual_service,
        "source_directory_material_retrieval_augmented_context_packet",
        fake_context_packet,
    )
    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryQualitativeAnalysisError) as exc_info:
            qual_service.source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                {
                    "client_request_id": "source-directory-qualitative-analysis-authority-mismatch",
                    "analysis_question": "What does the evidence support?",
                    "analysis_focus": "authority validation",
                    "material_snapshot_id": "mat",
                    "source_ingestion_batch_id": "batch",
                    "source_ingestion_file_id": "file",
                    "content_sha256": "content",
                    "file_identity_hash": "filehash",
                    "authority_basis_hash": "authority",
                    "payload_hash": "payload",
                    "index_authority_hash": "index",
                    "query_text": "alpha beta",
                },
            )
        assert exc_info.value.code == "source_directory_qualitative_analysis_context_packet_authority_mismatch"
        assert exc_info.value.http_status == 409
        assert exc_info.value.details["blocked_fields"] == [
            "context_packet_contract_id",
            "context_packet_mode",
            "schema_id",
        ]
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_qualitative_hybrid_analysis_api_route_is_bounded_and_redacted(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "BETA alpha alpha"),
        "limit": 2,
        "offset": 0,
    }

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_qualitative_analysis.v1"
    assert body["mode"] == "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
    assert body["status"] == "available"
    assert body["analysis_contract_id"] == "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
    assert body["analysis_mode"] == "context_packet_grounded_qualitative_hybrid_analysis"
    assert body["context_packet_contract_id"] == CONTEXT_PACKET_CONTRACT_ID
    assert body["context_packet_mode"] == CONTEXT_PACKET_MODE
    assert body["source_directory_package_review_preview_enabled"] is True
    assert body["source_directory_package_review_preview_hash"]
    assert body["source_directory_package_review_preview"]["schema_id"] == (
        "layer3.source_directory_qualitative_analysis_package_review_preview.v1"
    )
    assert body["source_directory_package_review_preview"]["package_commit_enabled"] is False
    assert body["source_directory_package_review_preview"]["negative_invariants"]["package_rows_written"] is False
    assert body["candidate_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["package_commit_enabled"] is False
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["query_tokens"] == ["alpha", "beta"]
    assert body["total"] == 2
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["evidence_summary"]["coverage_label"] == "complete_context_matches"
    assert body["supporting_segments"][0]["support_label"] == "primary_context_segment"
    assert "quote_excerpt" in body["supporting_segments"][0]
    assert "text" not in body["supporting_segments"][0]
    assert body["source_index_rows_written"] is False
    assert body["retrieval_rows_written"] is False
    assert body["context_packet_rows_written"] is False
    assert body["qualitative_analysis_rows_written"] is False
    assert body["qualitative_generation_rows_written"] is False
    assert body["analysis_run_rows_written"] is False
    assert body["package_rows_written"] is False
    assert body["connector_rows_written"] is False
    assert body["negative_invariants"]["vector_index_enabled"] is False
    assert body["negative_invariants"]["embedding_generation_enabled"] is False
    assert body["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
    assert body["negative_invariants"]["qualitative_generation_runtime_enabled"] is False
    assert body["negative_invariants"]["connector_dispatch_enabled"] is False
    assert body["negative_invariants"]["provider_public_delivery_enabled"] is False
    assert body["negative_invariants"]["network_egress_enabled"] is False
    assert str(source_dir) not in response.text

    status_response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/status",
        json=payload,
    )
    assert status_response.status_code == 200, status_response.text
    status_body = status_response.json()
    assert status_body["schema_id"] == "layer3.source_directory_qualitative_analysis_status.v1"
    assert status_body["mode"] == "source_directory_qualitative_hybrid_analysis_status_authority"
    assert status_body["status"] == "available"
    assert status_body["analysis_status"] == "source_directory_qualitative_hybrid_analysis_available"
    assert status_body["source_gate"] == (
        "818_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_STATUS_RUNTIME_ENTRY_FREEZE"
    )
    assert status_body["validated_analysis_schema_id"] == "layer3.source_directory_qualitative_analysis.v1"
    assert status_body["validated_analysis_mode"] == (
        "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
    )
    assert status_body["qualitative_analysis_hash"] == body["qualitative_analysis_hash"]
    assert status_body["context_packet_hash"] == body["context_packet_hash"]
    assert (
        status_body["source_directory_package_review_preview_hash"]
        == body["source_directory_package_review_preview_hash"]
    )
    assert status_body["source_directory_package_review_preview_available"] is True
    assert status_body["source_directory_package_review_preview_payload_redacted"] is True
    assert status_body["supporting_segments_redacted"] is True
    assert status_body["analysis_result_redacted"] is True
    assert status_body["query_tokens"] == ["alpha", "beta"]
    assert status_body["coverage_label"] == "complete_context_matches"
    assert status_body["supporting_segment_count"] == len(body["supporting_segments"])
    assert status_body["salient_term_count"] == len(body["salient_terms"])
    assert status_body["coverage_note_count"] == len(body["coverage_notes"])
    assert status_body["analysis_limit_count"] == len(body["analysis_limits"])
    assert status_body["source_index_rows_written"] is False
    assert status_body["retrieval_rows_written"] is False
    assert status_body["context_packet_rows_written"] is False
    assert status_body["qualitative_analysis_rows_written"] is False
    assert status_body["qualitative_generation_rows_written"] is False
    assert status_body["analysis_run_rows_written"] is False
    assert status_body["package_rows_written"] is False
    assert status_body["connector_rows_written"] is False
    assert status_body["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
    assert status_body["negative_invariants"]["qualitative_generation_runtime_enabled"] is False
    assert status_body["negative_invariants"]["connector_dispatch_enabled"] is False
    assert status_body["negative_invariants"]["provider_public_delivery_enabled"] is False
    assert status_body["negative_invariants"]["network_egress_enabled"] is False
    assert "source_directory_package_review_preview" not in status_body
    assert "supporting_segments" not in status_body
    assert "evidence_summary" not in status_body
    assert "quote_excerpt" not in status_response.text
    assert str(source_dir) not in status_response.text

    stale = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json={**payload, "index_authority_hash": "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "source_directory_text_retrieval_stale_index_authority"

    stale_status = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/status",
        json={**payload, "index_authority_hash": "0" * 64},
    )
    assert stale_status.status_code == 409
    assert stale_status.json()["error"]["code"] == "source_directory_text_retrieval_stale_index_authority"

    forbidden = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
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


def test_source_directory_qualitative_analysis_package_commit_writes_bounded_packages(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_qualitative_analysis_package_commit.v1"
    assert body["status"] == "committed"
    assert body["mode"] == "source_directory_qualitative_analysis_package_commit_authority"
    assert body["package_construction_source_gate"] == (
        "804_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["qualitative_analysis_hash"] == analysis_body["qualitative_analysis_hash"]
    assert body["source_directory_package_review_preview_hash"] == (
        analysis_body["source_directory_package_review_preview_hash"]
    )
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["package_rows_written"] is True
    assert body["package_payloads_written"] is True
    assert body["payload_refs_redacted"] is True
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert str(source_dir) not in response.text
    assert str(Path(settings.storage_dir)) not in response.text

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert reconciliation.reconciliation_record_id == body["reconciliation_record_id"]
        commit_summary = reconciliation.summary_json["source_directory_qualitative_package_commit"]
        assert commit_summary["package_review_submit_enabled"] is False
        assert commit_summary["handoff_enabled"] is False
        assert commit_summary["external_export_download_enabled"] is False
        assert commit_summary["connector_dispatch_enabled"] is False
        assert commit_summary["provider_public_delivery_enabled"] is False
        assert commit_summary["network_egress_enabled"] is False
        packages = db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        assert [package.package_kind for package in packages] == [
            "canonical_internal",
            "review_facing",
            "user_facing",
        ]
        assert {package.output_package_id for package in packages} == set(body["output_package_ids"])
        for package in packages:
            payload_path = Path(package.payload_ref)
            assert payload_path.exists()
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            assert payload["package_header"]["session_id"] == body["session_id"]
            assert payload["package_header"]["package_status"] == "package_complete"
            assert package.payload_hash in body["payload_hashes"]
    finally:
        db.close()

    replay = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "source_directory_package_commit_existing_package_state"


def test_source_directory_qualitative_analysis_package_review_submit_records_bounded_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    commit = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()
    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": (
            analysis_body["source_directory_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
    }

    response = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/review/submit"
        ),
        json=submit_payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_qualitative_analysis_package_review_submit.v1"
    assert body["mode"] == "source_directory_qualitative_analysis_package_review_submit_authority"
    assert body["status"] == "submitted"
    assert body["operator_decision"] == "approved"
    assert body["package_review_state"] == "package_review_approved"
    assert body["source_gate"] == (
        "806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_construction_source_gate"] == (
        "804_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["qualitative_analysis_hash"] == analysis_body["qualitative_analysis_hash"]
    assert body["source_directory_package_review_preview_hash"] == (
        analysis_body["source_directory_package_review_preview_hash"]
    )
    assert body["construction_basis_hash"] == commit_body["construction_basis_hash"]
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["output_package_ids"] == commit_body["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["payload_refs_redacted"] is True
    assert body["submit_record_ref"].startswith("l3-source-directory-package-review-submit-")
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is False
    assert body["export_enabled"] is False
    assert body["aps_handoff_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert "handoff" in body["downstream_unavailable"]
    assert "connector_dispatch" in body["downstream_unavailable"]
    assert str(source_dir) not in response.text
    assert str(Path(settings.storage_dir)) not in response.text

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        assert db.query(L3OutputPackage).count() == 3
        reconciliation = db.query(L3ReconciliationRecord).one()
        submit_state = reconciliation.summary_json["package_review_submit"]
        assert submit_state["schema_id"] == "layer3.package_review_submit_state.v1"
        assert submit_state["package_review_submit_schema_id"] == (
            "layer3.source_directory_qualitative_analysis_package_review_submit.v1"
        )
        assert submit_state["state"] == "package_review_approved"
        assert submit_state["package_review_state"] == "package_review_approved"
        assert submit_state["submit_record_ref"] == body["submit_record_ref"]
        assert submit_state["payload_refs"] is None
        assert submit_state["payload_refs_redacted"] is True
        assert reconciliation.summary_json["source_directory_qualitative_package_commit"][
            "package_review_submit_enabled"
        ] is False
    finally:
        db.close()

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["status"] == "already_submitted"
    assert replay_body["submit_record_ref"] == body["submit_record_ref"]


def test_source_directory_qualitative_analysis_handoff_export_prepare_records_bounded_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    commit = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()
    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": (
            analysis_body["source_directory_package_review_preview_hash"]
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
            "qualitative-hybrid-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    submit_body = submit.json()
    supersession_preview_payload = {
        **submit_payload,
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "operator_decision": "preview_source_directory_package_supersession",
    }
    supersession_preview = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/supersession/preview"
        ),
        json=supersession_preview_payload,
    )
    assert supersession_preview.status_code == 200, supersession_preview.text
    preview_body = supersession_preview.json()
    assert preview_body["schema_id"] == (
        "layer3.source_directory_qualitative_analysis_package_supersession_preview.v1"
    )
    assert preview_body["mode"] == (
        "source_directory_qualitative_analysis_package_supersession_preview_authority"
    )
    assert preview_body["status"] == "previewed"
    assert preview_body["source_gate"] == "820_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_ENTRY_FREEZE"
    assert preview_body["package_review_submit_source_gate"] == (
        "806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert preview_body["package_construction_source_gate"] == (
        "804_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert preview_body["output_package_ids"] == commit_body["output_package_ids"]
    assert preview_body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert preview_body["payload_hashes"] == commit_body["payload_hashes"]
    assert preview_body["payload_refs_redacted"] is True
    assert preview_body["source_package_set_hash"]
    assert preview_body["package_supersession_preview_hash"]
    assert preview_body["downstream_dependency_hash"]
    assert preview_body["downstream_dependencies"] == [
        {
            "state_key": "package_review_submit",
            "package_review_state": "package_review_approved",
            "schema_id": "layer3.package_review_submit_state.v1",
            "source_gate": "806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE",
            "submit_record_ref": submit_body["submit_record_ref"],
            "payload_refs_redacted": True,
        }
    ]
    assert preview_body["replacement_package_set_authority_enabled"] is False
    assert preview_body["package_supersession_commit_enabled"] is False
    assert preview_body["package_row_mutation_enabled"] is False
    assert preview_body["package_payload_rewrite_enabled"] is False
    assert preview_body["source_package_row_mutation_enabled"] is False
    assert preview_body["connector_dispatch_enabled"] is False
    assert preview_body["provider_public_delivery_enabled"] is False
    assert preview_body["network_egress_enabled"] is False
    assert preview_body["frontend_durable_authority_enabled"] is False
    assert preview_body["negative_invariants"]["package_row_mutation_enabled"] is False
    assert str(source_dir) not in supersession_preview.text
    assert str(Path(settings.storage_dir)) not in supersession_preview.text

    stale_supersession_preview = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/supersession/preview"
        ),
        json={
            **supersession_preview_payload,
            "payload_hashes": ["0" * 64, *commit_body["payload_hashes"][1:]],
        },
    )
    assert stale_supersession_preview.status_code == 409, stale_supersession_preview.text
    assert stale_supersession_preview.json()["error"]["code"] == (
        "source_directory_package_supersession_preview_package_set_mismatch"
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(ConnectorRun).count() == 0
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert "package_supersession_preview" not in reconciliation.summary_json
    finally:
        db.close()

    prepare_payload = {
        **submit_payload,
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": "authorize_prepare",
    }

    response = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/prepare"
        ),
        json=prepare_payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_qualitative_analysis_handoff_export_prepare.v1"
    assert body["mode"] == "source_directory_qualitative_analysis_handoff_export_prepare_authority"
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
        "808_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_review_submit_source_gate"] == (
        "806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
    )
    assert body["package_construction_source_gate"] == (
        "804_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_ENTRY_FREEZE"
    )
    assert body["handoff_enabled"] is False
    assert body["export_enabled"] is False
    assert body["aps_handoff_enabled"] is False
    assert body["external_export_download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["prompt_model_provider_runtime_enabled"] is False
    assert "external_export_download" in body["downstream_unavailable"]
    assert body["handoff_export_envelope"]["payload_refs"] is None
    assert body["handoff_export_envelope"]["payload_refs_redacted"] is True
    assert str(source_dir) not in response.text
    assert str(Path(settings.storage_dir)) not in response.text

    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        assert db.query(L3OutputPackage).count() == 3
        reconciliation = db.query(L3ReconciliationRecord).one()
        prepare_state = reconciliation.summary_json["handoff_export_prepare"]
        assert prepare_state["schema_id"] == "layer3.handoff_export_prepare_state.v1"
        assert prepare_state["handoff_export_prepare_schema_id"] == (
            "layer3.source_directory_qualitative_analysis_handoff_export_prepare.v1"
        )
        assert prepare_state["state"] == "handoff_export_prepared"
        assert prepare_state["handoff_export_state"] == "handoff_export_prepared"
        assert prepare_state["prepare_record_ref"] == body["prepare_record_ref"]
        assert prepare_state["payload_refs"] is None
        assert prepare_state["payload_refs_redacted"] is True
    finally:
        db.close()

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/prepare"
        ),
        json=prepare_payload,
    )
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["status"] == "already_prepared"
    assert replay_body["prepare_record_ref"] == body["prepare_record_ref"]


def test_source_directory_qualitative_analysis_external_export_download_prepare_records_readiness(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    commit = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()
    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": (
            analysis_body["source_directory_package_review_preview_hash"]
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
            "qualitative-hybrid-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    submit_body = submit.json()
    handoff_payload = {
        **submit_payload,
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": "authorize_prepare",
    }
    handoff = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_body = handoff.json()
    readiness_payload = {
        **handoff_payload,
        "operator_decision": "prepare_source_directory_external_export_download",
        "prepare_record_ref": handoff_body["prepare_record_ref"],
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": handoff_body["handoff_export_envelope"]["envelope_ref"],
        "external_export_download_target": "source_directory_qualitative_analysis_package_download_reference",
        "download_mode": "reference_only_prepare",
    }

    readiness = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/prepare"
        ),
        json=readiness_payload,
    )

    assert readiness.status_code == 200, readiness.text
    body = readiness.json()
    assert body["schema_id"] == "layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1"
    assert body["mode"] == "source_directory_qualitative_analysis_external_export_download_prepare_authority"
    assert body["status"] == "prepared"
    assert body["external_export_download_state"] == "external_export_download_prepared"
    assert body["external_export_download_target"] == (
        "source_directory_qualitative_analysis_package_download_reference"
    )
    assert body["download_mode"] == "reference_only_prepare"
    assert body["prepare_record_ref"] == handoff_body["prepare_record_ref"]
    assert body["handoff_export_envelope_ref"] == handoff_body["handoff_export_envelope"]["envelope_ref"]
    assert body["payload_refs_redacted"] is True
    assert body["same_origin_delivery_enabled"] is False
    assert body["provider_public_delivery_enabled"] is False
    assert body["provider_private_signed_url_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["network_egress_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert "same_origin_delivery" in body["downstream_unavailable"]
    assert body["source_gate"] == "812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE"
    assert str(source_dir) not in readiness.text
    assert str(Path(settings.storage_dir)) not in readiness.text

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 3
        reconciliation = db.query(L3ReconciliationRecord).one()
        readiness_state = reconciliation.summary_json["external_export_download_prepare"]
        assert readiness_state["schema_id"] == "layer3.external_export_download_prepare_state.v1"
        assert readiness_state["external_export_download_prepare_schema_id"] == (
            "layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1"
        )
        assert readiness_state["external_export_download_state"] == "external_export_download_prepared"
        assert readiness_state["external_export_download_record_ref"] == body["external_export_download_record_ref"]
        assert readiness_state["payload_refs"] is None
        assert readiness_state["payload_refs_redacted"] is True
        assert readiness_state["same_origin_delivery_enabled"] is False
    finally:
        db.close()

    replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/prepare"
        ),
        json=readiness_payload,
    )
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["status"] == "already_prepared"
    assert replay_body["external_export_download_record_ref"] == body["external_export_download_record_ref"]

    db = client.layer3_session_factory()
    try:
        selected_package = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id == body["output_package_ids"][1])
            .one()
        )
        expected_payload = Path(selected_package.payload_ref).read_bytes()
        expected_payload_hash = selected_package.payload_hash
    finally:
        db.close()

    delivery_payload = {
        **readiness_payload,
        "operator_decision": "deliver_source_directory_external_export_download",
        "external_export_download_record_ref": body["external_export_download_record_ref"],
        "export_download_descriptor_ref": body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
        "output_package_id": body["output_package_ids"][1],
        "package_kind": body["package_kinds"][1],
        "package_payload_hash": body["payload_hashes"][1],
    }
    delivery_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/deliver/status"
        ),
        json=delivery_payload,
    )
    assert delivery_status.status_code == 200, delivery_status.text
    status_body = delivery_status.json()
    assert status_body["schema_id"] == (
        "layer3.source_directory_qualitative_analysis_external_export_download_delivery_status.v1"
    )
    assert status_body["status"] == "ready"
    assert status_body["delivery_status"] == "source_directory_external_export_download_delivery_ready"
    assert status_body["delivery_available"] is True
    assert status_body["delivery_streaming_performed"] is False
    assert status_body["delivery_state"] == "external_export_download_delivered"
    assert status_body["source_gate"] == (
        "816_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_RUNTIME_ENTRY_FREEZE"
    )
    assert status_body["validated_delivery_source_gate"] == (
        "814_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE"
    )
    assert (
        status_body["external_export_download_record_ref"]
        == body["external_export_download_record_ref"]
    )
    assert status_body["export_download_descriptor_ref"] == body["export_download_descriptor_ref"]
    assert status_body["output_package_id"] == body["output_package_ids"][1]
    assert status_body["package_kind"] == body["package_kinds"][1]
    assert status_body["package_payload_hash"] == expected_payload_hash
    assert status_body["payload_ref_redacted"] is True
    assert status_body["raw_local_path_exposed"] is False
    assert status_body["same_origin_delivery_enabled"] is True
    assert status_body["provider_public_delivery_enabled"] is False
    assert status_body["provider_private_signed_url_enabled"] is False
    assert status_body["connector_dispatch_enabled"] is False
    assert status_body["network_egress_enabled"] is False
    assert status_body["frontend_durable_authority_enabled"] is False
    assert status_body["package_payload_rewrite_enabled"] is False
    assert status_body["source_package_row_mutation_enabled"] is False
    assert status_body["delivery_headers"]["X-Layer3-Delivery-State"] == "external_export_download_delivered"
    assert status_body["delivery_headers"]["X-Layer3-Source-Artifact-Hash"] == expected_payload_hash
    assert status_body["delivery_authority"]["payload_ref_redacted"] is True
    assert "artifact_path" not in status_body
    assert "filename" not in status_body
    assert str(source_dir) not in delivery_status.text
    assert str(Path(settings.storage_dir)) not in delivery_status.text

    stale_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/deliver/status"
        ),
        json={**delivery_payload, "package_payload_hash": "0" * 64},
    )
    assert stale_status.status_code == 409, stale_status.text
    assert stale_status.json()["error"]["code"] == (
        "source_directory_external_export_download_delivery_payload_hash_mismatch"
    )

    delivery = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/deliver"
        ),
        json=delivery_payload,
    )
    assert delivery.status_code == 200, delivery.text
    assert delivery.content == expected_payload
    assert delivery.headers["x-layer3-schema-id"] == (
        "layer3.source_directory_qualitative_analysis_external_export_download_delivery.v1"
    )
    assert delivery.headers["x-layer3-delivery-state"] == "external_export_download_delivered"
    assert delivery.headers["x-layer3-source-artifact-hash"] == expected_payload_hash
    assert (
        delivery.headers["x-layer3-external-export-download-record-ref"]
        == body["external_export_download_record_ref"]
    )
    assert delivery.headers["x-layer3-source-directory-package-kind"] == body["package_kinds"][1]
    assert "download_url" not in delivery.headers
    assert "public_url" not in delivery.headers
    assert "signed_url" not in delivery.headers
    assert "connector_run_id" not in delivery.headers
    assert str(source_dir) not in str(delivery.headers)
    assert str(Path(settings.storage_dir)) not in str(delivery.headers)

    delivery_replay = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/deliver"
        ),
        json=delivery_payload,
    )
    assert delivery_replay.status_code == 200, delivery_replay.text
    assert delivery_replay.content == expected_payload

    stale_hash = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/download/deliver"
        ),
        json={**delivery_payload, "package_payload_hash": "0" * 64},
    )
    assert stale_hash.status_code == 409, stale_hash.text
    assert stale_hash.json()["error"]["code"] == (
        "source_directory_external_export_download_delivery_payload_hash_mismatch"
    )


def test_source_directory_qualitative_analysis_handoff_export_prepare_requires_approved_submit(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    commit = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()
    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": (
            analysis_body["source_directory_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "changes_requested",
        "decision_notes": "Needs operator correction before handoff/export prepare.",
    }
    submit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    submit_body = submit.json()

    blocked = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/handoff/export/prepare"
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
    assert blocked.json()["error"]["code"] == "source_directory_handoff_export_prepare_submit_not_approved"
    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert "handoff_export_prepare" not in reconciliation.summary_json
    finally:
        db.close()


def test_source_directory_qualitative_analysis_package_review_submit_rejects_stale_construction(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    commit = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()

    stale = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "qualitative-hybrid-analysis/package/review/submit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": (
                analysis_body["source_directory_package_review_preview_hash"]
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
    assert stale.json()["error"]["code"] == "source_directory_package_review_submit_construction_mismatch"
    db = client.layer3_session_factory()
    try:
        _assert_no_forbidden_package_commit_downstream(db)
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert "package_review_submit" not in reconciliation.summary_json
    finally:
        db.close()


def test_source_directory_qualitative_analysis_package_commit_rejects_stale_preview_hash(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    analysis_payload = {
        **_analysis_payload(snapshot_info, index_authority_hash, "alpha beta"),
        "limit": 2,
        "offset": 0,
    }
    analysis = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text

    stale = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis.json()["qualitative_analysis_hash"],
            "source_directory_package_review_preview_hash": "0" * 64,
            "operator_decision": "commit_source_directory_qualitative_analysis_package",
        },
    )

    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "source_directory_package_commit_preview_hash_mismatch"
    db = client.layer3_session_factory()
    try:
        _assert_no_downstream_side_effects(db)
        assert db.query(L3ReconciliationRecord).count() == 0
    finally:
        db.close()
