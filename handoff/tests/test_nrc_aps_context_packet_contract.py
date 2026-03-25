import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_context_packet_contract as contract  # noqa: E402


def _report_payload(*, run_id: str = "run-context-contract-1") -> dict:
    return {
        "schema_id": "aps.evidence_report.v1",
        "schema_version": 1,
        "evidence_report_id": "report-1",
        "evidence_report_checksum": "report-sum-1",
        "_evidence_report_ref": "/tmp/report-1.json",
        "assembly_contract_id": "assembly-v1",
        "sectioning_contract_id": "sectioning-v1",
        "total_sections": 1,
        "total_citations": 1,
        "total_groups": 1,
        "source_citation_pack": {
            "citation_pack_id": "pack-1",
            "citation_pack_checksum": "pack-sum-1",
            "citation_pack_ref": "/tmp/pack-1.json",
            "source_bundle": {"run_id": run_id},
        },
        "sections": [
            {
                "section_id": "section-1",
                "section_ordinal": 1,
                "section_type": "evidence_group",
                "group_id": "group-1",
                "accession_number": "ML100",
                "content_id": "content-1",
                "run_id": run_id,
                "target_id": "target-1",
                "content_contract_id": "content-v1",
                "chunking_contract_id": "chunk-v1",
                "title": "Section 1",
                "citation_count": 1,
                "citations": [
                    {
                        "citation_id": "citation-1",
                        "citation_label": "[1]",
                        "citation_ordinal": 1,
                        "chunk_id": "chunk-1",
                        "chunk_ordinal": 0,
                        "start_char": 0,
                        "end_char": 10,
                        "snippet_text": "alpha",
                    }
                ],
            }
        ],
    }


def _export_payload(*, run_id: str = "run-context-contract-1") -> dict:
    return {
        "schema_id": "aps.evidence_report_export.v1",
        "schema_version": 1,
        "evidence_report_export_id": "export-1",
        "evidence_report_export_checksum": "export-sum-1",
        "_evidence_report_export_ref": "/tmp/export-1.json",
        "render_contract_id": "render-v1",
        "template_contract_id": "template-v1",
        "format_id": "markdown",
        "media_type": "text/markdown; charset=utf-8",
        "file_extension": ".md",
        "total_sections": 1,
        "total_citations": 1,
        "total_groups": 1,
        "rendered_markdown_sha256": "md-sha-1",
        "rendered_markdown": "# Report",
        "source_evidence_report": {
            "schema_id": "aps.evidence_report.v1",
            "schema_version": 1,
            "evidence_report_id": "report-1",
            "evidence_report_checksum": "report-sum-1",
            "evidence_report_ref": "/tmp/report-1.json",
            "assembly_contract_id": "assembly-v1",
            "sectioning_contract_id": "sectioning-v1",
            "total_sections": 1,
            "total_citations": 1,
            "total_groups": 1,
            "source_citation_pack": {
                "citation_pack_id": "pack-1",
                "citation_pack_checksum": "pack-sum-1",
                "citation_pack_ref": "/tmp/pack-1.json",
                "source_bundle": {"run_id": run_id},
            },
        },
    }


def _package_payload(*, run_id: str = "run-context-contract-1") -> dict:
    return {
        "schema_id": "aps.evidence_report_export_package.v1",
        "schema_version": 1,
        "evidence_report_export_package_id": "package-1",
        "evidence_report_export_package_checksum": "package-sum-1",
        "_evidence_report_export_package_ref": "/tmp/package-1.json",
        "composition_contract_id": "manifest-v1",
        "package_mode": "manifest_only",
        "owner_run_id": run_id,
        "format_id": "markdown",
        "media_type": "text/markdown; charset=utf-8",
        "file_extension": ".md",
        "render_contract_id": "render-v1",
        "template_contract_id": "template-v1",
        "source_export_count": 1,
        "total_sections": 1,
        "total_citations": 1,
        "total_groups": 1,
        "ordered_source_exports_sha256": "ordered-1",
        "source_exports": [
            {
                "export_ordinal": 1,
                "evidence_report_export_id": "export-1",
                "evidence_report_export_checksum": "export-sum-1",
                "evidence_report_export_ref": "/tmp/export-1.json",
                "rendered_markdown_sha256": "md-sha-1",
                "source_evidence_report_id": "report-1",
                "source_evidence_report_checksum": "report-sum-1",
                "source_evidence_report_ref": "/tmp/report-1.json",
                "total_sections": 1,
                "total_citations": 1,
                "total_groups": 1,
            }
        ],
    }


def test_normalize_request_requires_exactly_one_source_family_selector():
    try:
        contract.normalize_request_payload({})
        assert False, "expected invalid request"
    except ValueError as exc:
        assert str(exc) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    try:
        contract.normalize_request_payload(
            {
                "evidence_report_id": "report-1",
                "evidence_report_export_id": "export-1",
            }
        )
        assert False, "expected invalid request"
    except ValueError as exc:
        assert str(exc) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    normalized = contract.normalize_request_payload(
        {
            "evidence_report_export_package_ref": "/tmp/package-1.json",
            "persist_context_packet": True,
        }
    )
    assert normalized["source_family"] == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE
    assert normalized["evidence_report_export_package_ref"] == "/tmp/package-1.json"
    assert normalized["persist_context_packet"] is True


def test_context_packet_identity_uses_source_family_id_checksum_only():
    report_payload_run_a = _report_payload(run_id="run-a")
    report_payload_run_b = _report_payload(run_id="run-b")

    packet_a = contract.build_context_packet_payload(
        source_family=contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT,
        source_payload=report_payload_run_a,
        generated_at_utc="2026-03-11T00:00:00Z",
    )
    packet_b = contract.build_context_packet_payload(
        source_family=contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT,
        source_payload=report_payload_run_b,
        generated_at_utc="2026-03-11T00:00:00Z",
    )

    assert packet_a["context_packet_id"] == packet_b["context_packet_id"]
    assert packet_a["context_packet_checksum"] != packet_b["context_packet_checksum"]


def test_logical_context_packet_payload_excludes_only_persistence_fields():
    payload = {
        "context_packet_checksum": "checksum",
        "_context_packet_ref": "/tmp/context-1.json",
        "_persisted": True,
        "generated_at_utc": "2026-03-11T00:00:00Z",
        "source_descriptor": {"source_id": "report-1", "owner_run_id": "run-1"},
        "facts": [],
    }
    logical = contract.logical_context_packet_payload(payload)
    assert "context_packet_checksum" not in logical
    assert "_context_packet_ref" not in logical
    assert "_persisted" not in logical
    assert "generated_at_utc" not in logical
    assert logical["source_descriptor"]["owner_run_id"] == "run-1"


def test_fact_grammars_are_deterministic_for_all_allowed_source_families():
    report_packet = contract.build_context_packet_payload(
        source_family=contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT,
        source_payload=_report_payload(),
        generated_at_utc="2026-03-11T00:00:00Z",
    )
    export_packet = contract.build_context_packet_payload(
        source_family=contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
        source_payload=_export_payload(),
        generated_at_utc="2026-03-11T00:00:00Z",
    )
    package_packet = contract.build_context_packet_payload(
        source_family=contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE,
        source_payload=_package_payload(),
        generated_at_utc="2026-03-11T00:00:00Z",
    )

    assert [row["fact_type"] for row in report_packet["facts"]] == ["report_summary", "section_summary", "citation_link"]
    assert [row["fact_type"] for row in export_packet["facts"]] == [
        "export_summary",
        "source_report_summary",
        "render_fingerprint",
    ]
    assert [row["fact_type"] for row in package_packet["facts"]] == [
        "package_summary",
        "source_export_summary",
    ]
