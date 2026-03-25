import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_deterministic_challenge_artifact_contract as contract  # noqa: E402
from app.services import nrc_aps_deterministic_insight_artifact_contract as insight_contract  # noqa: E402


def _source_dossier_payload(*, owner_run_id: str, context_dossier_ref: str, source_packets: list[dict]) -> dict:
    total_facts = sum(int(item.get("total_facts") or 0) for item in source_packets)
    total_caveats = sum(int(item.get("total_caveats") or 0) for item in source_packets)
    total_constraints = sum(int(item.get("total_constraints") or 0) for item in source_packets)
    total_unresolved_questions = sum(int(item.get("total_unresolved_questions") or 0) for item in source_packets)
    return {
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


def _source_insight_payload(*, owner_run_id: str, context_dossier_ref: str, source_packets: list[dict]) -> dict:
    return insight_contract.build_deterministic_insight_artifact_payload(
        _source_dossier_payload(owner_run_id=owner_run_id, context_dossier_ref=context_dossier_ref, source_packets=source_packets),
        generated_at_utc="2026-03-12T00:00:00Z",
    )


def test_normalize_request_requires_exactly_one_selector_mode():
    for payload in ({}, {"deterministic_insight_artifact_id": "a", "deterministic_insight_artifact_ref": "C:/tmp/a.json"}):
        try:
            contract.normalize_request_payload(payload)
            assert False, "expected invalid request"
        except ValueError as exc:
            assert str(exc) == contract.APS_RUNTIME_FAILURE_INVALID_REQUEST

    normalized = contract.normalize_request_payload(
        {"deterministic_insight_artifact_id": "insight-1", "persist_challenge_artifact": True}
    )
    assert normalized == {
        "deterministic_insight_artifact_id": "insight-1",
        "deterministic_insight_artifact_ref": None,
        "persist_challenge_artifact": True,
    }


def test_identity_excludes_run_bearing_fields_and_checksums_vary_by_provenance():
    source_packets = [
        {"packet_ordinal": 1, "context_packet_id": "packet-1", "total_facts": 1, "total_caveats": 0, "total_constraints": 0, "total_unresolved_questions": 0},
        {"packet_ordinal": 2, "context_packet_id": "packet-2", "total_facts": 0, "total_caveats": 1, "total_constraints": 1, "total_unresolved_questions": 1},
    ]
    run_a = contract.build_deterministic_challenge_artifact_payload(
        _source_insight_payload(owner_run_id="run-a", context_dossier_ref="C:/tmp/run-a-dossier.json", source_packets=source_packets),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    run_b = contract.build_deterministic_challenge_artifact_payload(
        _source_insight_payload(owner_run_id="run-b", context_dossier_ref="C:/tmp/run-b-dossier.json", source_packets=source_packets),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert run_a["deterministic_challenge_artifact_id"] == run_b["deterministic_challenge_artifact_id"]
    assert run_a["deterministic_challenge_artifact_checksum"] != run_b["deterministic_challenge_artifact_checksum"]
    assert run_a["challenges"] == run_b["challenges"]


def test_one_challenge_per_check_aggregates_multiple_matching_findings():
    source_payload = {
        "schema_id": insight_contract.APS_DETERMINISTIC_INSIGHT_ARTIFACT_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": "2026-03-12T00:00:00Z",
        "deterministic_insight_artifact_id": "insight-shared-id",
        "deterministic_insight_artifact_checksum": "insight-sum",
        "_deterministic_insight_artifact_ref": "C:/tmp/insight.json",
        **insight_contract.ruleset_identity_payload(),
        "insight_mode": insight_contract.APS_DETERMINISTIC_INSIGHT_MODE,
        "source_context_dossier": {
            "schema_id": "aps.context_dossier.v1",
            "schema_version": 1,
            "context_dossier_id": "dossier-id",
            "context_dossier_checksum": "dossier-sum",
            "context_dossier_ref": "C:/tmp/dossier.json",
            "composition_contract_id": "aps_context_dossier_manifest_v1",
            "dossier_mode": "manifest_only",
            "owner_run_id": "run-agg",
            "projection_contract_id": "aps_context_packet_projection_v1",
            "fact_grammar_contract_id": "aps_context_packet_fact_grammar_v1",
            "objective": "normalize_persisted_source_for_downstream_consumption",
            "source_family": "evidence_report_export_package",
            "source_packet_count": 2,
            "ordered_source_packets_sha256": "ordered",
            "total_facts": 4,
            "total_caveats": 1,
            "total_constraints": 2,
            "total_unresolved_questions": 1,
            "source_packets": [],
        },
        "total_findings": 4,
        "finding_counts": {"info": 1, "warning": 3, "critical": 0},
        "findings": [
            {"finding_id": "finding-a", "rule_id": insight_contract.APS_RULE_ID_DOSSIER_CONSTRAINTS_PRESENT, "rule_version": 1, "category": "constraint", "severity": "warning", "matched_source_packet_count": 1},
            {"finding_id": "finding-b", "rule_id": insight_contract.APS_RULE_ID_DOSSIER_CONSTRAINTS_PRESENT, "rule_version": 1, "category": "constraint", "severity": "warning", "matched_source_packet_count": 2},
            {"finding_id": "finding-c", "rule_id": insight_contract.APS_RULE_ID_DOSSIER_UNRESOLVED_QUESTIONS_PRESENT, "rule_version": 1, "category": "uncertainty", "severity": "warning", "matched_source_packet_count": 1},
            {"finding_id": "finding-d", "rule_id": insight_contract.APS_RULE_ID_DOSSIER_CAVEATS_PRESENT, "rule_version": 1, "category": "qualification", "severity": "info", "matched_source_packet_count": 1},
        ],
    }
    payload = contract.build_deterministic_challenge_artifact_payload(source_payload, generated_at_utc="2026-03-12T00:00:00Z")
    by_check = {item["check_id"]: item for item in payload["challenges"]}
    constraints = by_check[contract.APS_CHECK_ID_CONSTRAINTS_PRESENT]
    assert constraints["matched_finding_count"] == 2
    assert constraints["source_finding_ids"] == ["finding-a", "finding-b"]
    assert len(constraints["evidence_pointers"]) == 2
    assert contract.APS_CHECK_ID_UNRESOLVED_QUESTIONS_PRESENT in by_check
    assert payload["challenge_counts"] == {"info": 1, "warning": 2, "critical": 0}
    assert payload["disposition_counts"] == {"block": 0, "review": 2, "acknowledge": 1}


def test_empty_challenges_payload_is_valid():
    payload = contract.build_deterministic_challenge_artifact_payload(
        _source_insight_payload(
            owner_run_id="run-clean",
            context_dossier_ref="C:/tmp/run-clean-dossier.json",
            source_packets=[
                {"packet_ordinal": 1, "context_packet_id": "packet-1", "total_facts": 2, "total_caveats": 0, "total_constraints": 0, "total_unresolved_questions": 0},
                {"packet_ordinal": 2, "context_packet_id": "packet-2", "total_facts": 1, "total_caveats": 0, "total_constraints": 0, "total_unresolved_questions": 0},
            ],
        ),
        generated_at_utc="2026-03-12T00:00:00Z",
    )
    assert payload["challenges"] == []
    assert payload["total_challenges"] == 0
    assert payload["challenge_counts"] == {"info": 0, "warning": 0, "critical": 0}
    assert payload["disposition_counts"] == {"block": 0, "review": 0, "acknowledge": 0}
