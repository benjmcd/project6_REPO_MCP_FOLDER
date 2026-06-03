from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
import sys
from typing import Any

from app.services import layer3_sec_xbrl_offline_evidence_proof_capability as proof
from app.services.layer3_sec_xbrl_canonical_concepts import report_redaction_scan_payload


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = ROOT / "diagnostics" / "assessment"
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))

from sec_xbrl_report_redaction import strip_residual_magnitude_fields  # noqa: E402


HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
READY_PROOF_SNAPSHOTS = (
    ASSESSMENT / "sec-xbrl-s1-ccj-10k-proof.json",
    ASSESSMENT / "sec-xbrl-s1-fizz-10k-proof.json",
    ASSESSMENT / "sec-xbrl-s1-fizz-10q-proof.json",
)
ORACLE_SNAPSHOT = ASSESSMENT / "sec-xbrl-s1-fizz-10q-oracle.json"
AGGREGATE_REPORT = ASSESSMENT / "sec-xbrl-s1-real-evidence-proof-report.json"
ALL_S1_ARTIFACTS = READY_PROOF_SNAPSHOTS + (ORACLE_SNAPSHOT, AGGREGATE_REPORT)
REQUIRED_AUTHORITY_HASHES = (
    "companyfacts_payload_hash",
    "proof_result_hash",
    "proof_source_report_hash",
    "sidecar_receipt_hash",
    "value_store_hash",
)
RAW_IDENTITY_KEYS = frozenset(
    {
        "accession",
        "accession_number",
        "cik",
        "company_name",
        "entity_name",
        "issuer_hash",
        "issuer_name",
        "issuer_ref",
        "raw_accession",
        "raw_cik",
    }
)


def test_committed_s1_ready_proof_snapshots_match_current_proof_invariants() -> None:
    checked = []
    for path in READY_PROOF_SNAPSHOTS:
        payload = _load(path)
        _assert_public_payload_redacted(path=path, payload=payload)
        _assert_ready_proof_payload(path=path, payload=payload)
        checked.append(path.relative_to(ROOT).as_posix())

    assert checked == [
        "diagnostics/assessment/sec-xbrl-s1-ccj-10k-proof.json",
        "diagnostics/assessment/sec-xbrl-s1-fizz-10k-proof.json",
        "diagnostics/assessment/sec-xbrl-s1-fizz-10q-proof.json",
    ]


def test_committed_s1_oracle_snapshot_remains_historical_blocked_context() -> None:
    payload = _load(ORACLE_SNAPSHOT)

    _assert_public_payload_redacted(path=ORACLE_SNAPSHOT, payload=payload)
    assert payload["schema_id"] == "diagnostics.sec_xbrl_offline_companyfacts_oracle_packet.v1"
    assert payload["schema_version"] == 1
    assert payload["status"] == "offline_companyfacts_oracle_packet_blocked"
    assert payload["paths_redacted"] is True
    assert payload["summary"]["companyfacts_oracle_supplied"] is True
    assert payload["summary"]["oracle_confirmed_count"] == 0
    assert payload["readiness"]["operator_review_creation_ready"] is False
    assert payload["readiness"]["production_admission_ready"] is False
    assert payload["controls"]["offline_storage_read_only"] is True
    assert payload["controls"]["source_acquisition_performed"] is False
    assert payload["controls"]["arelle_invoked"] is False
    assert payload["controls"]["network_performed"] is False
    assert payload["controls"]["value_reveal_performed"] is False
    assert payload["controls"]["production_readiness_claimed"] is False
    assert "proof_source_report_hash" not in payload["authority_refs"]
    assert "proof_result_hash" not in payload["authority_refs"]


def test_committed_s1_aggregate_report_matches_ready_proof_snapshots() -> None:
    aggregate = _load(AGGREGATE_REPORT)
    proofs_by_result_hash = {
        _load(path)["authority_refs"]["proof_result_hash"]: _load(path) for path in READY_PROOF_SNAPSHOTS
    }

    _assert_public_payload_redacted(path=AGGREGATE_REPORT, payload=aggregate)
    assert aggregate["schema_id"] == "diagnostics.sec_xbrl_s1_real_evidence_proof.v1"
    assert aggregate["schema_version"] == 1
    assert aggregate["status"] == "s1_real_evidence_proof_ready"
    assert HEX64_RE.fullmatch(aggregate["aggregate_proof_hash"])
    assert aggregate["scope"]["proof_slot_count"] == 3
    assert aggregate["scope"]["raw_accessions_redacted"] is True
    assert aggregate["scope"]["raw_company_identities_redacted"] is True
    assert aggregate["scope"]["raw_storage_paths_redacted"] is True
    assert aggregate["scope"]["raw_values_redacted"] is True
    assert aggregate["controls"]["validate_only"] is True
    assert aggregate["controls"]["source_acquisition_performed_by_proof"] is False
    assert aggregate["controls"]["arelle_invoked_by_proof"] is False
    assert aggregate["controls"]["production_database_touched"] is False
    assert aggregate["controls"]["value_reveal_performed"] is False
    assert aggregate["controls"]["production_admission_ready"] is False

    filings = aggregate["filings"]
    assert len(filings) == len(proofs_by_result_hash)
    for filing in filings:
        refs = filing["authority_hashes"]
        _assert_ready_authority_refs(path=AGGREGATE_REPORT, authority_refs=refs)
        proof_payload = proofs_by_result_hash[refs["proof_result_hash"]]

        assert refs == proof_payload["authority_refs"]
        assert filing["status"] == proof_payload["status"]
        assert filing["operator_review_creation_ready"] is True
        assert filing["production_admission_ready"] is False
        assert filing["containment"] == proof_payload["containment"]
        assert filing["redaction_scan"] == proof_payload["redaction_scan"]
        _assert_ready_redaction_scan(path=AGGREGATE_REPORT, redaction_scan=filing["redaction_scan"])
        for key, value in filing["counts"].items():
            assert proof_payload["summary"][key] == value

    assert aggregate["aggregate_counts"] == {
        "total_operator_review_workflow_count": sum(
            item["counts"]["isolated_persistence_operator_review_workflow_count"] for item in filings
        ),
        "total_oracle_confirmed_count": sum(item["counts"]["oracle_oracle_confirmed_count"] for item in filings),
        "total_orchestrator_review_exception_count": sum(
            item["counts"]["orchestrator_review_exception_count"] for item in filings
        ),
        "total_projected_count": sum(item["counts"]["oracle_projected_count"] for item in filings),
        "total_provenance_complete_count": sum(item["counts"]["oracle_provenance_complete_count"] for item in filings),
        "total_statement_packet_row_count": sum(
            item["counts"]["isolated_persistence_statement_packet_row_count"] for item in filings
        ),
    }


def test_committed_s1_artifacts_all_remain_redacted_and_residual_free() -> None:
    checked = []
    for path in ALL_S1_ARTIFACTS:
        payload = _load(path)
        _assert_public_payload_redacted(path=path, payload=payload)
        checked.append(path.relative_to(ROOT).as_posix())

    assert checked == [
        "diagnostics/assessment/sec-xbrl-s1-ccj-10k-proof.json",
        "diagnostics/assessment/sec-xbrl-s1-fizz-10k-proof.json",
        "diagnostics/assessment/sec-xbrl-s1-fizz-10q-proof.json",
        "diagnostics/assessment/sec-xbrl-s1-fizz-10q-oracle.json",
        "diagnostics/assessment/sec-xbrl-s1-real-evidence-proof-report.json",
    ]


def _assert_ready_proof_payload(*, path: Path, payload: Mapping[str, Any]) -> None:
    assert payload["schema_id"] == proof.REPORT_SCHEMA_ID, path
    assert payload["schema_version"] == 1, path
    assert payload["status"] == "offline_evidence_proof_capability_ready", path
    assert payload["blocked_reasons"] == [], path
    assert payload["paths_redacted"] is True, path
    _assert_ready_authority_refs(path=path, authority_refs=payload["authority_refs"])
    assert payload["summary"]["loader_status"] == "offline_evidence_bundle_ready", path
    assert payload["summary"]["oracle_status"] == "offline_companyfacts_oracle_packet_ready", path
    assert payload["summary"]["orchestrator_status"] == "review_ready", path
    assert payload["summary"]["proof_source_report_hash_bound"] is True, path
    assert payload["summary"]["isolated_persistence_projection_set_count"] == 1, path
    assert payload["summary"]["isolated_persistence_statement_packet_set_count"] == 1, path
    assert payload["summary"]["isolated_persistence_operator_review_workflow_count"] == 1, path
    assert payload["summary"]["isolated_persistence_projection_fact_count"] > 0, path
    assert payload["summary"]["isolated_persistence_statement_packet_row_count"] > 0, path
    assert payload["readiness"]["operator_review_creation_ready"] is True, path
    assert payload["readiness"]["production_admission_ready"] is False, path
    assert payload["readiness"]["production_admission_blocked_reason"] == (
        "diagnostic_validate_only_not_production_admission"
    ), path
    assert payload["containment"]["isolated_in_memory_db_used"] is True, path
    assert payload["containment"]["production_database_touched"] is False, path
    assert payload["containment"]["single_transaction_claimed"] is True, path
    assert payload["containment"]["existing_materializers_commit_per_stage"] is False, path
    assert payload["controls"] == proof._controls(
        operator_evidence_files_read=True,
        isolated_db_persistence_performed=True,
    ), path
    assert payload["proof_artifact_policy"] == proof._proof_artifact_policy(), path
    _assert_ready_redaction_scan(path=path, redaction_scan=payload["redaction_scan"])


def _assert_ready_authority_refs(*, path: Path, authority_refs: Mapping[str, Any]) -> None:
    for key in REQUIRED_AUTHORITY_HASHES:
        assert HEX64_RE.fullmatch(str(authority_refs.get(key) or "")), f"{path}:{key}"
    assert authority_refs["proof_source_report_hash"] != authority_refs["proof_result_hash"], path


def _assert_ready_redaction_scan(*, path: Path, redaction_scan: Mapping[str, Any]) -> None:
    assert redaction_scan["public_response_raw_accession_found"] is False, path
    assert redaction_scan["public_response_sec_url_found"] is False, path
    assert redaction_scan["public_response_local_path_found"] is False, path
    assert redaction_scan["public_response_raw_value_key_found"] is False, path
    assert redaction_scan["projection_facts_all_value_redacted"] is True, path
    assert redaction_scan["statement_rows_all_value_redacted"] is True, path


def _assert_public_payload_redacted(*, path: Path, payload: Mapping[str, Any]) -> None:
    proof._reject_report_leaks(payload)
    redaction_scan = report_redaction_scan_payload(payload)
    assert redaction_scan["passed"] is True, (path, redaction_scan)
    assert strip_residual_magnitude_fields(payload) == payload, path
    assert _raw_identity_key_paths(payload) == [], path


def _raw_identity_key_paths(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, Mapping):
        findings: list[str] = []
        for key, item in value.items():
            key_text = str(key)
            if key_text in RAW_IDENTITY_KEYS:
                findings.append(f"{path}.{key_text}")
            findings.extend(_raw_identity_key_paths(item, f"{path}.{key_text}"))
        return findings
    if isinstance(value, list):
        findings = []
        for index, item in enumerate(value):
            findings.extend(_raw_identity_key_paths(item, f"{path}[{index}]"))
        return findings
    return []


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))
