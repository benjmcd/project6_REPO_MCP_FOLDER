import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_evidence_bundle_contract as contract  # noqa: E402


def test_request_identity_excludes_pagination_and_persist():
    payload_a = {
        "run_id": "run-1",
        "query": "NRC   content!",
        "accession_numbers": ["ML1", "ML2"],
        "limit": 20,
        "offset": 0,
        "persist_bundle": False,
    }
    payload_b = {
        "run_id": "run-1",
        "query": "content nrc",
        "accession_numbers": ["ML2", "ML1"],
        "limit": 100,
        "offset": 40,
        "persist_bundle": True,
    }
    normalized_a = contract.normalize_request_payload(payload_a)
    normalized_b = contract.normalize_request_payload(payload_b)
    assert normalized_a["mode"] == contract.APS_MODE_QUERY
    assert normalized_b["mode"] == contract.APS_MODE_QUERY

    identity_a = contract.request_identity_hash(normalized_a)
    identity_b = contract.request_identity_hash(normalized_b)
    assert identity_a == identity_b


def test_bundle_id_is_snapshot_sensitive():
    payload = {"run_id": "run-1", "query": "nrc content"}
    normalized = contract.normalize_request_payload(payload)
    identity = contract.request_identity_hash(normalized)
    bundle_a = contract.derive_bundle_id(request_identity_hash_value=identity, index_state_hash="state-a")
    bundle_b = contract.derive_bundle_id(request_identity_hash_value=identity, index_state_hash="state-b")
    assert bundle_a != bundle_b


def test_snippet_highlight_bounds_are_deterministic():
    chunk_text = "alpha beta alpha gamma"
    snippet = contract.build_snippet(
        chunk_text=chunk_text,
        mode=contract.APS_MODE_QUERY,
        query_tokens=["alpha", "beta"],
    )
    assert snippet["snippet_text"]
    assert snippet["highlight_spans"]
    row = {
        "chunk_text": chunk_text,
        "snippet_text": snippet["snippet_text"],
        "snippet_start_char": snippet["snippet_start_char"],
        "snippet_end_char": snippet["snippet_end_char"],
        "highlight_spans": snippet["highlight_spans"],
    }
    assert contract.validate_snippet_bounds(row)


def test_grouping_and_ordering_contracts():
    items = [
        {
            "content_id": "c2",
            "run_id": "run-1",
            "target_id": "t2",
            "accession_number": "ML2",
            "content_contract_id": contract.APS_CONTENT_CONTRACT_ID,
            "chunking_contract_id": contract.APS_CHUNKING_CONTRACT_ID,
            "chunk_id": "chunk-1",
            "chunk_ordinal": 1,
            "matched_unique_query_terms": 2,
            "summed_term_frequency": 2,
            "chunk_length": 20,
        },
        {
            "content_id": "c1",
            "run_id": "run-1",
            "target_id": "t1",
            "accession_number": "ML1",
            "content_contract_id": contract.APS_CONTENT_CONTRACT_ID,
            "chunking_contract_id": contract.APS_CHUNKING_CONTRACT_ID,
            "chunk_id": "chunk-0",
            "chunk_ordinal": 0,
            "matched_unique_query_terms": 2,
            "summed_term_frequency": 3,
            "chunk_length": 25,
        },
    ]
    ordered = contract.ordered_items(items, mode=contract.APS_MODE_QUERY)
    assert ordered[0]["content_id"] == "c1"
    assert contract.is_ordering_deterministic(ordered, mode=contract.APS_MODE_QUERY)
    groups = contract.grouped_page(ordered, mode=contract.APS_MODE_QUERY)
    assert len(groups) == 2
    assert groups[0]["chunk_count"] == 1

