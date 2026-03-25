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
from app.services import nrc_aps_evidence_citation_pack_contract as citation_pack_contract  # noqa: E402
from app.services import nrc_aps_evidence_report_contract as contract  # noqa: E402


def _sample_citation_pack() -> dict:
    return {
        "schema_id": citation_pack_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
        "schema_version": citation_pack_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
        "citation_pack_id": "pack-1",
        "citation_pack_checksum": "pack-checksum-1",
        "derivation_contract_id": citation_pack_contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
        "source_bundle": {
            "schema_id": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
            "schema_version": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "bundle_id": "bundle-1",
            "bundle_checksum": "bundle-checksum-1",
            "bundle_ref": "C:/bundle.json",
            "request_identity_hash": "request-1",
            "mode": bundle_contract.APS_MODE_QUERY,
            "run_id": "run-1",
            "query": "alpha",
            "query_tokens": ["alpha"],
            "snapshot": {"snapshot_contract_id": bundle_contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID},
            "total_hits": 3,
            "total_groups": 2,
        },
        "total_citations": 3,
        "total_groups": 2,
        "citations": [
            {
                "citation_id": "citation-1",
                "citation_label": "APS-CIT-00001",
                "citation_ordinal": 1,
                "group_id": "group-a",
                "chunk_id": "chunk-a-1",
                "content_id": "content-a",
                "run_id": "run-1",
                "target_id": "target-a",
                "accession_number": "ML-ALPHA-1",
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
            },
            {
                "citation_id": "citation-2",
                "citation_label": "APS-CIT-00002",
                "citation_ordinal": 2,
                "group_id": "group-b",
                "chunk_id": "chunk-b-1",
                "content_id": "content-b",
                "run_id": "run-1",
                "target_id": "target-b",
                "accession_number": None,
                "content_contract_id": bundle_contract.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": bundle_contract.APS_CHUNKING_CONTRACT_ID,
                "normalization_contract_id": bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
                "chunk_ordinal": 0,
                "start_char": 0,
                "end_char": 11,
                "snippet_text": "alpha gamma",
                "snippet_start_char": 0,
                "snippet_end_char": 11,
                "highlight_spans": [{"chunk_start": 0, "chunk_end": 5, "snippet_start": 0, "snippet_end": 5}],
            },
            {
                "citation_id": "citation-3",
                "citation_label": "APS-CIT-00003",
                "citation_ordinal": 3,
                "group_id": "group-a",
                "chunk_id": "chunk-a-2",
                "content_id": "content-a",
                "run_id": "run-1",
                "target_id": "target-a",
                "accession_number": "ML-ALPHA-1",
                "content_contract_id": bundle_contract.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": bundle_contract.APS_CHUNKING_CONTRACT_ID,
                "normalization_contract_id": bundle_contract.APS_NORMALIZATION_CONTRACT_ID,
                "chunk_ordinal": 1,
                "start_char": 11,
                "end_char": 22,
                "snippet_text": "alpha delta",
                "snippet_start_char": 0,
                "snippet_end_char": 11,
                "highlight_spans": [{"chunk_start": 11, "chunk_end": 16, "snippet_start": 0, "snippet_end": 5}],
            },
        ],
    }


def test_request_normalization_requires_exactly_one_source():
    with pytest.raises(ValueError) as no_source:
        contract.normalize_request_payload({"persist_report": True})
    assert str(no_source.value) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    with pytest.raises(ValueError) as both_sources:
        contract.normalize_request_payload({"citation_pack_id": "pack-1", "citation_pack_ref": "C:/pack.json"})
    assert str(both_sources.value) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST


def test_evidence_report_id_is_independent_of_pagination_and_persist():
    request_a = contract.normalize_request_payload({"citation_pack_id": "pack-1", "limit": 10, "offset": 0, "persist_report": False})
    request_b = contract.normalize_request_payload({"citation_pack_id": "pack-1", "limit": 200, "offset": 50, "persist_report": True})
    assert request_a["citation_pack_id"] == request_b["citation_pack_id"]
    report_id_a = contract.derive_evidence_report_id(citation_pack_id="pack-1", citation_pack_checksum="checksum-1")
    report_id_b = contract.derive_evidence_report_id(citation_pack_id="pack-1", citation_pack_checksum="checksum-1")
    assert report_id_a == report_id_b


def test_checksum_is_stable_across_preview_and_persisted_fields():
    citation_pack = _sample_citation_pack()
    payload_a = {
        "schema_id": contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
        "generated_at_utc": "2026-03-11T10:00:00Z",
        "evidence_report_id": "report-1",
        "assembly_contract_id": contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
        "sectioning_contract_id": contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
        "source_citation_pack": {
            **contract.source_citation_pack_summary_payload(citation_pack),
            "_citation_pack_ref": "C:/internal-pack.json",
            "_persisted": True,
        },
        "total_sections": 2,
        "total_citations": 3,
        "total_groups": 2,
        "sections": contract.build_sections_from_citation_pack(citation_pack),
    }
    payload_b = {
        **payload_a,
        "generated_at_utc": "2026-03-12T11:00:00Z",
        "_evidence_report_ref": "C:/report.json",
        "_persisted": True,
    }
    assert contract.compute_evidence_report_checksum(payload_a) == contract.compute_evidence_report_checksum(payload_b)


def test_section_order_and_titles_are_deterministic():
    citation_pack = _sample_citation_pack()
    sections_a = contract.build_sections_from_citation_pack(citation_pack)
    sections_b = contract.build_sections_from_citation_pack(citation_pack)

    assert sections_a == sections_b
    assert sections_a[0]["group_id"] == "group-a"
    assert sections_a[0]["title"] == "Accession ML-ALPHA-1 / Content content-a"
    assert sections_a[1]["group_id"] == "group-b"
    assert sections_a[1]["title"] == "Content content-b"
    assert [item["citation_ordinal"] for item in sections_a[0]["citations"]] == [1, 3]
