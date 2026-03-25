import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_evidence_report_export_package_contract as contract  # noqa: E402


def _source_row(export_id: str, checksum: str) -> dict:
    return {
        "export_ordinal": 1,
        "evidence_report_export_id": export_id,
        "evidence_report_export_checksum": checksum,
        "evidence_report_export_ref": f"/tmp/{export_id}.json",
        "rendered_markdown_sha256": f"hash-{export_id}",
        "source_evidence_report_id": f"report-{export_id}",
        "source_evidence_report_checksum": f"report-sum-{export_id}",
        "source_evidence_report_ref": f"/tmp/report-{export_id}.json",
        "total_sections": 1,
        "total_citations": 2,
        "total_groups": 1,
    }


def test_normalize_request_requires_exactly_one_source_list_and_bounds():
    try:
        contract.normalize_request_payload({})
        assert False, "expected invalid request"
    except ValueError as exc:
        assert str(exc) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    try:
        contract.normalize_request_payload({"evidence_report_export_ids": ["a"]})
        assert False, "expected too few"
    except ValueError as exc:
        assert str(exc) == contract.APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_EXPORTS

    try:
        contract.normalize_request_payload({"evidence_report_export_ids": ["a", "a"]})
        assert False, "expected duplicate"
    except ValueError as exc:
        assert str(exc) == contract.APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_EXPORT


def test_ordered_source_digest_and_package_id_are_order_sensitive():
    left = [_source_row("export-a", "sum-a"), _source_row("export-b", "sum-b")]
    right = [_source_row("export-b", "sum-b"), _source_row("export-a", "sum-a")]

    left_digest = contract.ordered_source_exports_sha256(left)
    right_digest = contract.ordered_source_exports_sha256(right)

    assert left_digest != right_digest
    assert (
        contract.derive_evidence_report_export_package_id(
            format_id="markdown",
            render_contract_id="render-v1",
            template_contract_id="template-v1",
            ordered_source_exports_sha256_value=left_digest,
        )
        != contract.derive_evidence_report_export_package_id(
            format_id="markdown",
            render_contract_id="render-v1",
            template_contract_id="template-v1",
            ordered_source_exports_sha256_value=right_digest,
        )
    )


def test_logical_package_payload_excludes_only_persistence_fields():
    payload = {
        "evidence_report_export_package_checksum": "checksum",
        "_evidence_report_export_package_ref": "/tmp/package.json",
        "_persisted": True,
        "generated_at_utc": "2026-03-11T00:00:00Z",
        "owner_run_id": "run-1",
        "ordered_source_exports_sha256": "ordered",
        "source_exports": [_source_row("export-a", "sum-a")],
    }
    logical = contract.logical_evidence_report_export_package_payload(payload)
    assert "evidence_report_export_package_checksum" not in logical
    assert "_evidence_report_export_package_ref" not in logical
    assert "_persisted" not in logical
    assert "generated_at_utc" not in logical
    assert logical["owner_run_id"] == "run-1"
    assert logical["ordered_source_exports_sha256"] == "ordered"
