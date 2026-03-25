import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_deterministic_insight_artifact_contract as contract  # noqa: E402


def _source_dossier_payload(*, owner_run_id: str, context_dossier_ref: str, source_packets: list[dict]) -> dict:
    total_facts = sum(int(item.get("total_facts") or 0) for item in source_packets)
    total_caveats = sum(int(item.get("total_caveats") or 0) for item in source_packets)
    total_constraints = sum(int(item.get("total_constraints") or 0) for item in source_packets)
    total_unresolved_questions = sum(int(item.get("total_unresolved_questions") or 0) for item in source_packets)
    payload = {
        "schema_id": "aps.context_dossier.v1",
        "schema_version": 1,
        "generated_at_utc": "2026-03-12T00:00:00Z",
        "context_dossier_id": "dossier-shared-id",
        "context_dossier_checksum": f"checksum-{owner_run_id}",
        "_context_dossier_ref": context_dossier_ref,
        "composition_contract_id": "aps_context_dossier_manifest_v1",
        "dossier_mode": "manifest_only",
        "owner_run_id": owner_run_id,
        "projection_contract_id": "aps_context_packet_projection_v1",
        "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
        "objective": "normalize_persisted_source_for_downstream_consumption",
        "source_family": "evidence_report_export_package",
        "source_packet_count": len(source_packets),
        "ordered_source_packets_sha256": f"ordered-{owner_run_id}",
        "total_facts": total_facts,
        "total_caveats": total_caveats,
        "total_constraints": total_constraints,
        "total_unresolved_questions": total_unresolved_questions,
        "source_packets": source_packets,
    }
    return payload


def test_normalize_request_requires_exactly_one_selector_mode():
    for payload in (
        {},
        {"context_dossier_id": "a", "context_dossier_ref": "C:/tmp/a.json"},
    ):
        try:
            contract.normalize_request_payload(payload)
            assert False, "expected invalid request"
        except ValueError as exc:
            assert str(exc) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    normalized = contract.normalize_request_payload(
        {"context_dossier_id": "dossier-1", "persist_insight_artifact": True}
    )
    assert normalized == {
        "context_dossier_id": "dossier-1",
        "context_dossier_ref": None,
        "persist_insight_artifact": True,
    }


def test_identity_excludes_run_bearing_fields_and_rules_ignore_forbidden_fields():
    source_packets = [
        {
            "packet_ordinal": 1,
            "context_packet_id": "packet-1",
            "total_facts": 1,
            "total_caveats": 0,
            "total_constraints": 0,
            "total_unresolved_questions": 0,
        },
        {
            "packet_ordinal": 2,
            "context_packet_id": "packet-2",
            "total_facts": 0,
            "total_caveats": 1,
            "total_constraints": 1,
            "total_unresolved_questions": 1,
        },
    ]
    run_a = contract.build_deterministic_insight_artifact_payload(
        _source_dossier_payload(
            owner_run_id="run-a",
            context_dossier_ref="C:/tmp/run-a-dossier.json",
            source_packets=source_packets,
        ),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    run_b = contract.build_deterministic_insight_artifact_payload(
        _source_dossier_payload(
            owner_run_id="run-b",
            context_dossier_ref="C:/tmp/run-b-dossier.json",
            source_packets=source_packets,
        ),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert run_a["deterministic_insight_artifact_id"] == run_b["deterministic_insight_artifact_id"]
    assert run_a["deterministic_insight_artifact_checksum"] != run_b["deterministic_insight_artifact_checksum"]
    assert run_a["source_context_dossier"]["context_dossier_ref"] != run_b["source_context_dossier"]["context_dossier_ref"]
    assert run_a["findings"] == run_b["findings"]


def test_one_finding_per_rule_aggregates_multiple_matching_packets():
    payload = contract.build_deterministic_insight_artifact_payload(
        _source_dossier_payload(
            owner_run_id="run-agg",
            context_dossier_ref="C:/tmp/run-agg-dossier.json",
            source_packets=[
                {
                    "packet_ordinal": 1,
                    "context_packet_id": "packet-1",
                    "total_facts": 0,
                    "total_caveats": 1,
                    "total_constraints": 0,
                    "total_unresolved_questions": 0,
                },
                {
                    "packet_ordinal": 2,
                    "context_packet_id": "packet-2",
                    "total_facts": 0,
                    "total_caveats": 1,
                    "total_constraints": 2,
                    "total_unresolved_questions": 1,
                },
                {
                    "packet_ordinal": 3,
                    "context_packet_id": "packet-3",
                    "total_facts": 4,
                    "total_caveats": 0,
                    "total_constraints": 0,
                    "total_unresolved_questions": 0,
                },
            ],
        ),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    by_rule = {item["rule_id"]: item for item in payload["findings"]}
    zero_facts = by_rule[contract.APS_RULE_ID_SOURCE_PACKET_ZERO_FACTS_PARTIAL]
    assert zero_facts["matched_source_packet_count"] == 2
    assert len(zero_facts["evidence_pointers"]) == 3
    assert payload["total_findings"] == 4
    assert payload["finding_counts"] == {"info": 1, "warning": 3, "critical": 0}


def test_empty_findings_payload_is_valid():
    payload = contract.build_deterministic_insight_artifact_payload(
        _source_dossier_payload(
            owner_run_id="run-clean",
            context_dossier_ref="C:/tmp/run-clean-dossier.json",
            source_packets=[
                {
                    "packet_ordinal": 1,
                    "context_packet_id": "packet-1",
                    "total_facts": 2,
                    "total_caveats": 0,
                    "total_constraints": 0,
                    "total_unresolved_questions": 0,
                },
                {
                    "packet_ordinal": 2,
                    "context_packet_id": "packet-2",
                    "total_facts": 1,
                    "total_caveats": 0,
                    "total_constraints": 0,
                    "total_unresolved_questions": 0,
                },
            ],
        ),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert payload["findings"] == []
    assert payload["total_findings"] == 0
    assert payload["finding_counts"] == {"info": 0, "warning": 0, "critical": 0}
