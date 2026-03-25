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
from app.services import nrc_aps_evidence_report_contract as report_contract  # noqa: E402
from app.services import nrc_aps_evidence_report_export_contract as contract  # noqa: E402


def _sample_source_report() -> dict:
    return {
        "schema_id": report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID,
        "schema_version": report_contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
        "evidence_report_id": "report1",
        "evidence_report_checksum": "reportchecksum1",
        "assembly_contract_id": report_contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
        "sectioning_contract_id": report_contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
        "source_citation_pack": {
            "schema_id": citation_pack_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
            "schema_version": citation_pack_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
            "citation_pack_id": "pack1",
            "citation_pack_checksum": "packchecksum1",
            "citation_pack_ref": "C:/pack.json",
            "derivation_contract_id": citation_pack_contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
            "total_citations": 2,
            "total_groups": 1,
            "source_bundle": {
                "schema_id": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID,
                "schema_version": bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
                "bundle_id": "bundle1",
                "bundle_checksum": "bundlechecksum1",
                "bundle_ref": "C:/bundle.json",
                "request_identity_hash": "request1",
                "mode": bundle_contract.APS_MODE_QUERY,
                "run_id": "run1",
                "query": "alpha",
                "query_tokens": ["alpha"],
                "snapshot": {"snapshot_contract_id": bundle_contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID},
                "total_hits": 2,
                "total_groups": 1,
            },
        },
        "total_sections": 1,
        "total_citations": 2,
        "total_groups": 1,
        "_evidence_report_ref": "C:/report.json",
        "sections": [
            {
                "section_id": "section1",
                "section_ordinal": 1,
                "section_type": report_contract.APS_REPORT_SECTION_TYPE,
                "group_id": "group1",
                "accession_number": "ML1",
                "content_id": "content1",
                "run_id": "run1",
                "target_id": "target1",
                "content_contract_id": "content_contract_1",
                "chunking_contract_id": "chunking_contract_1",
                "title": "Accession ML1 / Content content1",
                "citation_count": 2,
                "citations": [
                    {
                        "citation_id": "citation1",
                        "citation_label": "APS-CIT-00001",
                        "citation_ordinal": 1,
                        "chunk_id": "chunk1",
                        "chunk_ordinal": 0,
                        "start_char": 0,
                        "end_char": 10,
                        "snippet_text": "alpha\nbeta",
                        "snippet_start_char": 0,
                        "snippet_end_char": 10,
                        "highlight_spans": [],
                    },
                    {
                        "citation_id": "citation2",
                        "citation_label": "APS-CIT-00002",
                        "citation_ordinal": 2,
                        "chunk_id": "chunk2",
                        "chunk_ordinal": 1,
                        "start_char": 11,
                        "end_char": 21,
                        "snippet_text": "gamma\tdelta",
                        "snippet_start_char": 0,
                        "snippet_end_char": 11,
                        "highlight_spans": [],
                    },
                ],
            }
        ],
    }


def test_request_normalization_requires_exactly_one_source():
    with pytest.raises(ValueError) as no_source:
        contract.normalize_request_payload({"persist_export": True})
    assert str(no_source.value) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    with pytest.raises(ValueError) as both_sources:
        contract.normalize_request_payload({"evidence_report_id": "report1", "evidence_report_ref": "C:/report.json"})
    assert str(both_sources.value) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST


def test_export_id_is_independent_of_persist_choice():
    request_a = contract.normalize_request_payload({"evidence_report_id": "report1", "persist_export": False})
    request_b = contract.normalize_request_payload({"evidence_report_ref": "C:/report.json", "persist_export": True})
    assert request_a["persist_export"] is False
    assert request_b["persist_export"] is True
    export_id_a = contract.derive_evidence_report_export_id(
        evidence_report_id="report1",
        evidence_report_checksum="checksum1",
    )
    export_id_b = contract.derive_evidence_report_export_id(
        evidence_report_id="report1",
        evidence_report_checksum="checksum1",
    )
    assert export_id_a == export_id_b


def test_export_checksum_is_stable_across_preview_and_persisted_fields():
    source_report = _sample_source_report()
    payload_a = contract.build_evidence_report_export_payload(source_report, generated_at_utc="2026-03-11T10:00:00Z")
    payload_b = {
        **payload_a,
        "generated_at_utc": "2026-03-12T11:00:00Z",
        "_evidence_report_export_ref": "C:/export.json",
        "_persisted": True,
    }
    assert contract.compute_evidence_report_export_checksum(payload_a) == contract.compute_evidence_report_export_checksum(payload_b)


def test_rendered_markdown_is_deterministic_and_exact():
    source_report = _sample_source_report()
    payload_a = contract.build_evidence_report_export_payload(source_report, generated_at_utc="2026-03-11T10:00:00Z")
    payload_b = contract.build_evidence_report_export_payload(source_report, generated_at_utc="2026-03-11T12:00:00Z")

    assert payload_a["evidence_report_export_id"] == payload_b["evidence_report_export_id"]
    assert payload_a["rendered_markdown"] == payload_b["rendered_markdown"]
    assert payload_a["rendered_markdown_sha256"] == payload_b["rendered_markdown_sha256"]
    expected = (
        "# NRC ADAMS APS Evidence Report Export\n"
        "\n"
        f"- Export ID: {payload_a['evidence_report_export_id']}\n"
        "- Format: markdown\n"
        "- Render Contract: aps\\_evidence\\_report\\_export\\_render\\_v1\n"
        "- Template Contract: aps\\_evidence\\_report\\_export\\_markdown\\_template\\_v1\n"
        "- Source Evidence Report ID: report1\n"
        "- Source Evidence Report Checksum: reportchecksum1\n"
        "- Source Citation Pack ID: pack1\n"
        "- Source Citation Pack Checksum: packchecksum1\n"
        "- Total Sections: 1\n"
        "- Total Citations: 2\n"
        "- Total Groups: 1\n"
        "\n"
        "## Section 00001: Accession ML1 / Content content1\n"
        "\n"
        "- Group ID: group1\n"
        "- Run ID: run1\n"
        "- Target ID: target1\n"
        "- Content ID: content1\n"
        "- Accession Number: ML1\n"
        "- Content Contract ID: content\\_contract\\_1\n"
        "- Chunking Contract ID: chunking\\_contract\\_1\n"
        "- Citation Count: 2\n"
        "\n"
        "1. APS\\-CIT\\-00001 | citation1\n"
        "   - Chunk ID: chunk1\n"
        "   - Chunk Ordinal: 0\n"
        "   - Character Span: 0:10\n"
        "   - Snippet: alpha\\\\nbeta\n"
        "\n"
        "2. APS\\-CIT\\-00002 | citation2\n"
        "   - Chunk ID: chunk2\n"
        "   - Chunk Ordinal: 1\n"
        "   - Character Span: 11:21\n"
        "   - Snippet: gamma\\\\tdelta\n"
    )
    assert payload_a["rendered_markdown"] == expected
    assert payload_a["rendered_markdown_sha256"] == contract.compute_rendered_markdown_sha256(expected)
