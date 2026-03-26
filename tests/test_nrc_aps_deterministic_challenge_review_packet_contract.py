import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(BACKEND / "app" / "storage_test_runtime"))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_deterministic_challenge_review_packet_contract as contract  # noqa: E402
from app.services import nrc_aps_deterministic_challenge_artifact_contract as challenge_contract  # noqa: E402


def _sample_challenge_artifact_payload() -> dict:
    source_insight = {
        "schema_id": "aps.deterministic_insight_artifact.v1",
        "schema_version": 1,
        "deterministic_insight_artifact_id": "insight-id-1",
        "deterministic_insight_artifact_checksum": "insight-checksum-1",
        "deterministic_insight_artifact_ref": "C:/tmp/insight.json",
        "ruleset_contract_id": "aps_deterministic_insight_ruleset_v1",
        "ruleset_id": "single_dossier_presence_rules",
        "ruleset_version": 1,
        "insight_mode": "deterministic_rules_only",
        "owner_run_id": "run-contract-1",
        "source_context_dossier_id": "dossier-id-1",
        "source_context_dossier_checksum": "dossier-checksum-1",
        "source_context_dossier_ref": "C:/tmp/dossier.json",
        "total_findings": 2,
        "finding_counts": {"info": 1, "warning": 1, "critical": 0},
    }
    challenge_id_1 = challenge_contract.derive_challenge_id(
        deterministic_challenge_artifact_id="challenge-art-id-1",
        check_id="blocking_coverage_absence",
        check_version=1,
    )
    challenge_id_2 = challenge_contract.derive_challenge_id(
        deterministic_challenge_artifact_id="challenge-art-id-1",
        check_id="partial_coverage_gap",
        check_version=1,
    )
    challenge_id_3 = challenge_contract.derive_challenge_id(
        deterministic_challenge_artifact_id="challenge-art-id-1",
        check_id="qualification_present",
        check_version=1,
    )
    return {
        "schema_id": "aps.deterministic_challenge_artifact.v1",
        "schema_version": 1,
        "generated_at_utc": "2026-03-20T00:00:00Z",
        "ruleset_contract_id": "aps_deterministic_challenge_ruleset_v1",
        "ruleset_id": "single_insight_challenge_checks",
        "ruleset_version": 1,
        "challenge_mode": "deterministic_checks_only",
        "deterministic_challenge_artifact_id": "challenge-art-id-1",
        "deterministic_challenge_artifact_checksum": "challenge-checksum-1",
        "_deterministic_challenge_artifact_ref": "C:/tmp/challenge.json",
        "source_deterministic_insight_artifact": source_insight,
        "total_challenges": 3,
        "challenge_counts": {"info": 1, "warning": 1, "critical": 1},
        "disposition_counts": {"block": 1, "review": 1, "acknowledge": 1},
        "challenges": [
            {
                "challenge_id": challenge_id_1,
                "check_id": "blocking_coverage_absence",
                "check_version": 1,
                "category": "coverage",
                "severity": "critical",
                "disposition": "block",
                "matched_finding_count": 1,
                "source_finding_ids": ["finding-1"],
                "message": "Insight reports zero factual coverage; downstream use is blocked until coverage exists.",
                "evidence_pointers": [{"pointer": "/source_deterministic_insight_artifact/findings/0", "source_finding_id": "finding-1", "source_rule_id": "dossier_zero_facts"}],
            },
            {
                "challenge_id": challenge_id_2,
                "check_id": "partial_coverage_gap",
                "check_version": 1,
                "category": "coverage",
                "severity": "warning",
                "disposition": "review",
                "matched_finding_count": 1,
                "source_finding_ids": ["finding-2"],
                "message": "Insight reports partial factual coverage gaps that require review before downstream use.",
                "evidence_pointers": [{"pointer": "/source_deterministic_insight_artifact/findings/1", "source_finding_id": "finding-2", "source_rule_id": "source_packet_zero_facts_partial"}],
            },
            {
                "challenge_id": challenge_id_3,
                "check_id": "qualification_present",
                "check_version": 1,
                "category": "qualification",
                "severity": "info",
                "disposition": "acknowledge",
                "matched_finding_count": 1,
                "source_finding_ids": ["finding-3"],
                "message": "Insight reports caveats that must accompany downstream use.",
                "evidence_pointers": [{"pointer": "/source_deterministic_insight_artifact/findings/2", "source_finding_id": "finding-3", "source_rule_id": "dossier_caveats_present"}],
            },
        ],
    }


def test_deterministic_id_is_stable():
    id_a = contract.derive_deterministic_challenge_review_packet_id(source_deterministic_challenge_artifact_id="challenge-art-id-1")
    id_b = contract.derive_deterministic_challenge_review_packet_id(source_deterministic_challenge_artifact_id="challenge-art-id-1")
    assert id_a == id_b
    id_c = contract.derive_deterministic_challenge_review_packet_id(source_deterministic_challenge_artifact_id="challenge-art-id-2")
    assert id_a != id_c


def test_checksum_is_stable():
    source = _sample_challenge_artifact_payload()
    packet_a = contract.build_deterministic_challenge_review_packet_payload(source, generated_at_utc="2026-03-20T00:00:00Z")
    packet_b = contract.build_deterministic_challenge_review_packet_payload(source, generated_at_utc="2026-03-20T01:00:00Z")
    assert packet_a["deterministic_challenge_review_packet_checksum"] == packet_b["deterministic_challenge_review_packet_checksum"]


def test_grouped_buckets_preserve_full_challenge_rows():
    source = _sample_challenge_artifact_payload()
    packet = contract.build_deterministic_challenge_review_packet_payload(source, generated_at_utc="2026-03-20T00:00:00Z")
    assert packet["total_challenges"] == 3
    assert packet["blocker_count"] == 1
    assert packet["review_item_count"] == 1
    assert packet["acknowledgement_count"] == 1
    assert len(packet["blockers"]) == 1
    assert len(packet["review_items"]) == 1
    assert len(packet["acknowledgements"]) == 1
    blocker = packet["blockers"][0]
    assert blocker["disposition"] == "block"
    assert blocker["check_id"] == "blocking_coverage_absence"
    assert blocker["severity"] == "critical"
    assert blocker["matched_finding_count"] == 1
    assert len(blocker["source_finding_ids"]) == 1
    assert len(blocker["evidence_pointers"]) == 1
    review_item = packet["review_items"][0]
    assert review_item["disposition"] == "review"
    acknowledgement = packet["acknowledgements"][0]
    assert acknowledgement["disposition"] == "acknowledge"


def test_source_summary_carries_upstream_lineage():
    source = _sample_challenge_artifact_payload()
    packet = contract.build_deterministic_challenge_review_packet_payload(source, generated_at_utc="2026-03-20T00:00:00Z")
    summary = packet["source_deterministic_challenge_artifact"]
    assert summary["deterministic_challenge_artifact_id"] == "challenge-art-id-1"
    assert summary["deterministic_challenge_artifact_ref"] == "C:/tmp/challenge.json"
    assert summary["source_deterministic_insight_artifact"]["deterministic_insight_artifact_id"] == "insight-id-1"


def test_normalize_request_payload_rejects_both_or_neither():
    import pytest
    with pytest.raises(ValueError):
        contract.normalize_request_payload({"deterministic_challenge_artifact_id": "id", "deterministic_challenge_artifact_ref": "ref"})
    with pytest.raises(ValueError):
        contract.normalize_request_payload({})
    result = contract.normalize_request_payload({"deterministic_challenge_artifact_id": "id"})
    assert result["deterministic_challenge_artifact_id"] == "id"
    assert result["deterministic_challenge_artifact_ref"] is None
    assert result["persist_review_packet"] is False


def test_failure_id_is_deterministic():
    id_a = contract.derive_failure_deterministic_challenge_review_packet_id(source_locator="loc-1", error_code="err-1")
    id_b = contract.derive_failure_deterministic_challenge_review_packet_id(source_locator="loc-1", error_code="err-1")
    assert id_a == id_b
    id_c = contract.derive_failure_deterministic_challenge_review_packet_id(source_locator="loc-1", error_code="err-2")
    assert id_a != id_c


def test_filename_helpers_are_path_safe():
    long_id = "a" * 200
    name = contract.expected_deterministic_challenge_review_packet_file_name(scope="run_test", deterministic_challenge_review_packet_id=long_id)
    assert len(name) < 150
    assert name.endswith("_aps_deterministic_challenge_review_packet_v1.json")
    failure_name = contract.expected_failure_file_name(scope="run_test", deterministic_challenge_review_packet_id=long_id)
    assert failure_name.endswith("_aps_deterministic_challenge_review_packet_failure_v1.json")


def test_empty_challenges_yield_empty_buckets():
    source = _sample_challenge_artifact_payload()
    source["challenges"] = []
    source["total_challenges"] = 0
    source["challenge_counts"] = {"info": 0, "warning": 0, "critical": 0}
    source["disposition_counts"] = {"block": 0, "review": 0, "acknowledge": 0}
    packet = contract.build_deterministic_challenge_review_packet_payload(source, generated_at_utc="2026-03-20T00:00:00Z")
    assert packet["total_challenges"] == 0
    assert packet["blocker_count"] == 0
    assert packet["review_item_count"] == 0
    assert packet["acknowledgement_count"] == 0
    assert packet["blockers"] == []
    assert packet["review_items"] == []
    assert packet["acknowledgements"] == []
