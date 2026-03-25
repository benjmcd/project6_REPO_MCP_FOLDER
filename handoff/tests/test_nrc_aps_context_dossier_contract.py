import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_context_dossier_contract as contract  # noqa: E402


def _context_packet_payload(
    *,
    context_packet_id: str,
    context_packet_checksum: str,
    owner_run_id: str,
    context_packet_ref: str,
) -> dict:
    return {
        "schema_id": "aps.context_packet.v1",
        "schema_version": 1,
        "generated_at_utc": "2026-03-12T00:00:00Z",
        "context_packet_id": context_packet_id,
        "context_packet_checksum": context_packet_checksum,
        "_context_packet_ref": context_packet_ref,
        "projection_contract_id": "aps_context_packet_projection_v1",
        "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
        "source_family": "evidence_report_export_package",
        "source_descriptor": {
            "source_id": f"source-{context_packet_id}",
            "source_checksum": f"source-sum-{context_packet_id}",
            "owner_run_id": owner_run_id,
        },
        "objective": "normalize_persisted_source_for_downstream_consumption",
        "total_facts": 3,
        "total_caveats": 2,
        "total_constraints": 1,
        "total_unresolved_questions": 1,
    }


def test_normalize_request_requires_exactly_one_selector_mode_and_bounds():
    for payload, expected in (
        ({}, contract.APS_RUNTIME_FAILURE_INVALID_REQUEST),
        (
            {"context_packet_ids": ["a", "b"], "context_packet_refs": ["/tmp/a.json", "/tmp/b.json"]},
            contract.APS_RUNTIME_FAILURE_INVALID_REQUEST,
        ),
        ({"context_packet_ids": ["a"]}, contract.APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_PACKETS),
        ({"context_packet_ids": ["a", "a"]}, contract.APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_PACKET),
        (
            {"context_packet_ids": [f"id-{i}" for i in range(contract.APS_CONTEXT_DOSSIER_MAX_SOURCES + 1)]},
            contract.APS_RUNTIME_FAILURE_TOO_MANY_SOURCE_PACKETS,
        ),
    ):
        try:
            contract.normalize_request_payload(payload)
            assert False, "expected normalize request failure"
        except ValueError as exc:
            assert str(exc) == expected

    normalized = contract.normalize_request_payload(
        {
            "context_packet_ids": ["packet-a", "packet-b"],
            "persist_dossier": True,
        }
    )
    assert normalized["context_packet_ids"] == ["packet-a", "packet-b"]
    assert normalized["context_packet_refs"] is None
    assert normalized["persist_dossier"] is True


def test_ordered_source_digest_is_order_sensitive_and_ignores_ref_fields():
    left = [
        {
            "context_packet_id": "packet-a",
            "context_packet_checksum": "sum-a",
            "context_packet_ref": "/tmp/a.json",
        },
        {
            "context_packet_id": "packet-b",
            "context_packet_checksum": "sum-b",
            "context_packet_ref": "/tmp/b.json",
        },
    ]
    right = [left[1], left[0]]
    left_digest = contract.ordered_source_packets_sha256(left)
    right_digest = contract.ordered_source_packets_sha256(right)
    assert left_digest != right_digest

    left_with_different_refs = [
        {
            "context_packet_id": "packet-a",
            "context_packet_checksum": "sum-a",
            "context_packet_ref": "/other/a.json",
        },
        {
            "context_packet_id": "packet-b",
            "context_packet_checksum": "sum-b",
            "context_packet_ref": "/other/b.json",
        },
    ]
    assert contract.ordered_source_packets_sha256(left) == contract.ordered_source_packets_sha256(left_with_different_refs)


def test_identity_excludes_owner_run_but_checksum_changes_with_run_scoped_refs():
    run_a_payload = contract.build_context_dossier_payload(
        [
            _context_packet_payload(
                context_packet_id="packet-1",
                context_packet_checksum="sum-1",
                owner_run_id="run-a",
                context_packet_ref="/tmp/run-a-packet-1.json",
            ),
            _context_packet_payload(
                context_packet_id="packet-2",
                context_packet_checksum="sum-2",
                owner_run_id="run-a",
                context_packet_ref="/tmp/run-a-packet-2.json",
            ),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    run_b_payload = contract.build_context_dossier_payload(
        [
            _context_packet_payload(
                context_packet_id="packet-1",
                context_packet_checksum="sum-1",
                owner_run_id="run-b",
                context_packet_ref="/tmp/run-b-packet-1.json",
            ),
            _context_packet_payload(
                context_packet_id="packet-2",
                context_packet_checksum="sum-2",
                owner_run_id="run-b",
                context_packet_ref="/tmp/run-b-packet-2.json",
            ),
        ],
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert run_a_payload["context_dossier_id"] == run_b_payload["context_dossier_id"]
    assert run_a_payload["context_dossier_checksum"] != run_b_payload["context_dossier_checksum"]
    assert run_a_payload["source_packets"][0]["context_packet_ref"] != run_b_payload["source_packets"][0]["context_packet_ref"]
    assert "context_packet_ref" in contract.logical_context_dossier_payload(run_a_payload)["source_packets"][0]
