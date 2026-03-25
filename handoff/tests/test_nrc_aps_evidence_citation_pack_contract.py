import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_evidence_bundle_contract as bundle_contract  # noqa: E402
from app.services import nrc_aps_evidence_citation_pack_contract as contract  # noqa: E402


def test_request_normalization_requires_exactly_one_source():
    with pytest.raises(ValueError) as no_source:
        contract.normalize_request_payload({"persist_pack": True})
    assert str(no_source.value) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    with pytest.raises(ValueError) as both_sources:
        contract.normalize_request_payload({"bundle_id": "bundle-1", "bundle_ref": "C:/bundle.json"})
    assert str(both_sources.value) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST


def test_citation_pack_id_is_independent_of_pagination_and_persist():
    request_a = contract.normalize_request_payload({"bundle_id": "bundle-1", "limit": 10, "offset": 0, "persist_pack": False})
    request_b = contract.normalize_request_payload({"bundle_id": "bundle-1", "limit": 200, "offset": 50, "persist_pack": True})
    assert request_a["bundle_id"] == request_b["bundle_id"]
    citation_pack_a = contract.derive_citation_pack_id(source_bundle_id="bundle-1", source_bundle_checksum="checksum-1")
    citation_pack_b = contract.derive_citation_pack_id(source_bundle_id="bundle-1", source_bundle_checksum="checksum-1")
    assert citation_pack_a == citation_pack_b


def test_citation_labels_and_ids_are_deterministic():
    source_bundle = {
        "schema_id": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
        "schema_version": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "bundle_id": "bundle-1",
        "bundle_checksum": "checksum-1",
        "request_identity_hash": "request-1",
        "mode": bundle_contract.APS_MODE_QUERY,
        "run_id": "run-1",
        "query": "alpha",
        "query_tokens": ["alpha"],
        "snapshot": {"snapshot_contract_id": bundle_contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID},
        "total_hits": 2,
        "total_groups": 1,
        "results": [
            {
                "group_id": "group-1",
                "chunk_id": "chunk-1",
                "content_id": "content-1",
                "run_id": "run-1",
                "target_id": "target-1",
                "accession_number": "ML-1",
                "content_contract_id": bundle_contract.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": bundle_contract.APS_CHUNKING_CONTRACT_ID,
                "normalization_contract_id": bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
                "chunk_ordinal": 0,
                "start_char": 0,
                "end_char": 10,
                "snippet_text": "alpha beta",
                "snippet_start_char": 0,
                "snippet_end_char": 10,
                "highlight_spans": [{"chunk_start": 0, "chunk_end": 5, "snippet_start": 0, "snippet_end": 5}],
                "matched_unique_query_terms": 1,
                "summed_term_frequency": 1,
                "chunk_text_sha256": "chunk-sha-1",
                "normalized_text_sha256": "norm-sha-1",
                "blob_sha256": "blob-sha-1",
                "content_units_ref": "C:/content_units.json",
                "normalized_text_ref": "C:/normalized.txt",
                "blob_ref": "C:/blob.bin",
                "download_exchange_ref": "C:/download_exchange.json",
                "discovery_ref": "C:/discovery.json",
                "selection_ref": "C:/selection.json",
            },
            {
                "group_id": "group-1",
                "chunk_id": "chunk-2",
                "content_id": "content-1",
                "run_id": "run-1",
                "target_id": "target-1",
                "accession_number": "ML-1",
                "content_contract_id": bundle_contract.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": bundle_contract.APS_CHUNKING_CONTRACT_ID,
                "normalization_contract_id": bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
                "chunk_ordinal": 1,
                "start_char": 11,
                "end_char": 22,
                "snippet_text": "alpha gamma",
                "snippet_start_char": 0,
                "snippet_end_char": 11,
                "highlight_spans": [{"chunk_start": 11, "chunk_end": 16, "snippet_start": 0, "snippet_end": 5}],
                "matched_unique_query_terms": 1,
                "summed_term_frequency": 1,
                "chunk_text_sha256": "chunk-sha-2",
                "normalized_text_sha256": "norm-sha-1",
                "blob_sha256": "blob-sha-1",
                "content_units_ref": "C:/content_units.json",
                "normalized_text_ref": "C:/normalized.txt",
                "blob_ref": "C:/blob.bin",
                "download_exchange_ref": "C:/download_exchange.json",
                "discovery_ref": "C:/discovery.json",
                "selection_ref": "C:/selection.json",
            },
        ],
    }

    citations_a = contract.build_citations_from_bundle(source_bundle)
    citations_b = contract.build_citations_from_bundle(source_bundle)

    assert citations_a == citations_b
    assert citations_a[0]["citation_label"] == "APS-CIT-00001"
    assert citations_a[1]["citation_label"] == "APS-CIT-00002"
    assert citations_a[0]["citation_id"] != citations_a[1]["citation_id"]
