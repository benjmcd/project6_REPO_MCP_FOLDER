from __future__ import annotations

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
)
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


def _assert_no_downstream_side_effects(db) -> None:
    assert db.query(L3PassRun).count() == 0
    assert db.query(AnalysisRun).count() == 0
    assert db.query(L3OutputPackage).count() == 0
    assert db.query(ConnectorRun).count() == 0
    assert db.query(ConnectorRunTarget).count() == 0


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
