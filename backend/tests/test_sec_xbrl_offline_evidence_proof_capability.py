from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from typing import Any

from app.services import layer3_sec_xbrl_offline_evidence_proof_capability as proof


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "diagnostics" / "assessment" / "sec-xbrl-offline-evidence-proof-capability-report.json"
CLI_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-offline-evidence-proof-capability.py"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def test_proof_capability_blocks_without_operator_storage() -> None:
    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability()
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "offline_evidence_proof_operator_storage_missing"
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["readiness"]["production_admission_ready"] is False
    assert report["controls"]["operator_evidence_files_read"] is False
    assert report["controls"]["isolated_db_persistence_performed"] is False
    assert "proof_source_report_hash" not in report["authority_refs"]
    assert "proof_result_hash" not in report["authority_refs"]
    assert report["proof_artifact_policy"]["default_reports_remain_blocked_without_operator_evidence"] is True
    assert "C:" not in text
    assert "sec.gov" not in text


def test_committed_default_report_matches_no_operator_storage_service_output() -> None:
    generated = proof.inspect_sec_xbrl_offline_evidence_proof_capability()
    committed = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8-sig"))

    assert committed == generated


def test_cli_default_output_matches_no_operator_storage_service_output(tmp_path, monkeypatch) -> None:
    cli = _load_cli_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sec-xbrl-offline-evidence-proof-capability.py"])

    assert cli.main() == 0

    output = tmp_path / "diagnostics" / "assessment" / "sec-xbrl-offline-evidence-proof-capability-report.json"
    assert json.loads(output.read_text(encoding="utf-8")) == proof.inspect_sec_xbrl_offline_evidence_proof_capability()


def test_cli_fails_closed_without_reflecting_exception_text(tmp_path, monkeypatch) -> None:
    cli = _load_cli_module()

    def raise_with_raw_path(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ValueError(r"C:\raw\operator\path")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "inspect_sec_xbrl_offline_evidence_proof_capability", raise_with_raw_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sec-xbrl-offline-evidence-proof-capability.py",
            "--storage-dir",
            "operator-storage",
        ],
    )

    assert cli.main() == 0

    output = tmp_path / "diagnostics" / "assessment" / "sec-xbrl-offline-evidence-proof-capability-report.json"
    report = json.loads(output.read_text(encoding="utf-8"))
    text = json.dumps(report, sort_keys=True)
    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "offline_evidence_proof_diagnostic_exception"
    assert report["blocked_reasons"][0]["details"] == {"exception_type": "ValueError"}
    assert report["controls"]["operator_evidence_files_read"] is False
    assert "proof_source_report_hash" not in report["authority_refs"]
    assert "proof_result_hash" not in report["authority_refs"]
    assert r"C:\raw\operator\path" not in text


def test_proof_capability_blocks_on_loader_report_without_running_oracle(monkeypatch) -> None:
    calls: list[str] = []

    def fake_loader(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("loader")
        return {
            "status": "offline_evidence_bundle_blocked",
            "storage_marker": "a" * 24,
            "blocked_reasons": [
                {
                    "reason": "sec_xbrl_offline_evidence_loader_field_missing",
                    "message": "missing field",
                    "details": {"field": "fact_inventory_hash"},
                }
            ],
        }

    def fake_oracle(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("oracle")
        return {"status": "should_not_run"}

    monkeypatch.setattr(proof, "inspect_sec_xbrl_offline_evidence_storage", fake_loader)
    monkeypatch.setattr(proof, "inspect_sec_xbrl_offline_companyfacts_oracle_packet", fake_oracle)

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert calls == ["loader"]
    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "sec_xbrl_offline_evidence_loader_field_missing"
    assert report["summary"]["loader_status"] == "offline_evidence_bundle_blocked"
    assert report["summary"]["oracle_status"] == "not_run"
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["controls"]["operator_evidence_files_read"] is True


def test_proof_capability_reports_redacted_ready_path(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_loader_report(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "status": "offline_evidence_bundle_ready",
            "storage_marker": "b" * 24,
            "authority_refs": {
                "sidecar_receipt_hash": "1" * 64,
                "value_store_hash": "4" * 64,
            },
            "summary": {
                "resolved_fact_count": 2,
                "value_record_count": 2,
                "statement_role_record_count": 2,
            },
        }

    def fake_oracle_report(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "status": "offline_companyfacts_oracle_packet_ready",
            "storage_marker": "b" * 24,
            "authority_refs": {
                "companyfacts_payload_hash": "2" * 64,
            },
            "summary": {
                "projected_count": 2,
                "oracle_confirmed_count": 2,
                "companyfacts_observation_count": 5,
                "projection_ready_period_count": 1,
            },
        }

    def fake_load_bundle(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"evidence": {"redacted": True}}

    def fake_orchestrator(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        captured.update(_kwargs)
        return {
            "response": {
                "status": "review_ready",
                "source_report_hash": captured["source_report_hash"],
                "summary": {
                    "period_count": 1,
                    "ready_period_count": 1,
                    "row_count": 2,
                    "statement_count": 1,
                },
                "containment": {
                    "existing_materializers_commit_per_stage": False,
                    "single_transaction_claimed": True,
                },
            },
            "persisted_counts": {
                "projection_set_count": 1,
                "projection_fact_count": 2,
                "statement_packet_set_count": 1,
                "statement_packet_row_count": 2,
                "operator_review_workflow_count": 1,
            },
            "redaction_scan": {
                "public_response_raw_accession_found": False,
                "public_response_sec_url_found": False,
                "public_response_local_path_found": False,
                "public_response_raw_value_key_found": False,
                "projection_facts_all_value_redacted": True,
                "statement_rows_all_value_redacted": True,
            },
        }

    monkeypatch.setattr(proof, "inspect_sec_xbrl_offline_evidence_storage", fake_loader_report)
    monkeypatch.setattr(proof, "inspect_sec_xbrl_offline_companyfacts_oracle_packet", fake_oracle_report)
    monkeypatch.setattr(proof, "load_sec_xbrl_offline_evidence_bundle", fake_load_bundle)
    monkeypatch.setattr(proof, "_run_isolated_orchestrator", fake_orchestrator)

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability(
        "operator-storage",
        companyfacts_path="operator-companyfacts.json",
    )

    assert report["status"] == "offline_evidence_proof_capability_ready"
    assert report["readiness"]["operator_review_creation_ready"] is True
    assert report["readiness"]["production_admission_ready"] is False
    assert report["controls"]["operator_evidence_files_read"] is True
    assert report["controls"]["isolated_db_persistence_performed"] is True
    assert report["controls"]["offline_storage_read_only"] is True
    assert report["controls"]["source_acquisition_performed"] is False
    assert report["controls"]["arelle_invoked"] is False
    assert report["controls"]["network_performed"] is False
    assert report["controls"]["production_db_persistence_performed"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["production_readiness_claimed"] is False
    assert report["containment"]["production_database_touched"] is False
    assert report["summary"]["oracle_projected_count"] == 2
    assert report["summary"]["isolated_persistence_operator_review_workflow_count"] == 1
    assert report["summary"]["proof_source_report_hash_bound"] is True
    assert report["redaction_scan"]["projection_facts_all_value_redacted"] is True
    assert report["proof_artifact_policy"]["operator_supplied_evidence_required"] is True
    assert report["proof_artifact_policy"]["default_reports_remain_blocked_without_operator_evidence"] is True
    assert report["proof_artifact_policy"]["proof_lineage_hashes_are_redacted_authority_handles"] is True
    assert report["proof_artifact_policy"]["proof_lineage_hashes_are_raw_evidence_refs"] is False
    assert report["proof_artifact_policy"]["raw_storage_committed"] is False
    assert report["proof_artifact_policy"]["raw_companyfacts_committed"] is False
    assert report["proof_artifact_policy"]["production_admission_claimed"] is False
    assert captured["source_report_hash"] == proof._proof_source_report_hash(
        loader_report=fake_loader_report(),
        oracle_report=fake_oracle_report(),
        period_limit=2,
    )
    assert report["authority_refs"]["proof_source_report_hash"] == captured["source_report_hash"]
    assert HEX64_RE.fullmatch(report["authority_refs"]["proof_source_report_hash"])
    assert HEX64_RE.fullmatch(report["authority_refs"]["proof_result_hash"])
    assert report["authority_refs"]["proof_result_hash"] != report["authority_refs"]["proof_source_report_hash"]
    assert report["authority_refs"]["value_store_hash"] == "4" * 64
    assert report["authority_refs"]["companyfacts_payload_hash"] == "2" * 64


def test_proof_capability_rejects_report_leaks(monkeypatch) -> None:
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_evidence_storage",
        lambda *_args, **_kwargs: {"status": "offline_evidence_bundle_ready"},
    )
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_companyfacts_oracle_packet",
        lambda *_args, **_kwargs: {
            "status": "offline_companyfacts_oracle_packet_ready",
            "authority_refs": {"companyfacts_payload_hash": "2" * 64},
        },
    )
    monkeypatch.setattr(proof, "load_sec_xbrl_offline_evidence_bundle", lambda *_args, **_kwargs: {"evidence": {}})
    monkeypatch.setattr(
        proof,
        "_run_isolated_orchestrator",
        lambda *_args, **_kwargs: {
            "response": {
                "status": "review_ready",
                "source_report_hash": _kwargs["source_report_hash"],
                "summary": {"row_count": 1},
                "containment": {
                    "existing_materializers_commit_per_stage": False,
                    "single_transaction_claimed": True,
                },
            },
            "persisted_counts": {
                "projection_set_count": 1,
                "projection_fact_count": 1,
                "statement_packet_set_count": 1,
                "statement_packet_row_count": 1,
                "operator_review_workflow_count": 1,
            },
            "redaction_scan": {
                "public_response_raw_accession_found": False,
                "public_response_sec_url_found": False,
                "public_response_local_path_found": False,
                "public_response_raw_value_key_found": False,
                "projection_facts_all_value_redacted": True,
                "statement_rows_all_value_redacted": True,
            },
        },
    )

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert report["status"] == "offline_evidence_proof_capability_ready"
    assert "operator-storage" not in json.dumps(report, sort_keys=True)


def test_proof_capability_raw_value_key_scan_covers_common_value_fields() -> None:
    assert proof.RAW_VALUE_KEY_RE.search(json.dumps({"value": "123"}, sort_keys=True))
    assert proof.RAW_VALUE_KEY_RE.search(json.dumps({"amount": "123"}, sort_keys=True))
    assert proof.RAW_VALUE_KEY_RE.search(json.dumps({"effective_value": "123"}, sort_keys=True))


def test_proof_capability_blocks_when_single_transaction_is_unproven(monkeypatch) -> None:
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_evidence_storage",
        lambda *_args, **_kwargs: {"status": "offline_evidence_bundle_ready"},
    )
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_companyfacts_oracle_packet",
        lambda *_args, **_kwargs: {
            "status": "offline_companyfacts_oracle_packet_ready",
            "authority_refs": {"companyfacts_payload_hash": "2" * 64},
        },
    )
    monkeypatch.setattr(proof, "load_sec_xbrl_offline_evidence_bundle", lambda *_args, **_kwargs: {"evidence": {}})
    monkeypatch.setattr(
        proof,
        "_run_isolated_orchestrator",
        lambda *_args, **_kwargs: {
            "response": {
                "status": "review_ready",
                "source_report_hash": _kwargs["source_report_hash"],
                "summary": {"row_count": 1},
                "containment": {
                    "existing_materializers_commit_per_stage": True,
                    "single_transaction_claimed": False,
                },
            },
            "persisted_counts": {
                "projection_set_count": 1,
                "projection_fact_count": 1,
                "statement_packet_set_count": 1,
                "statement_packet_row_count": 1,
                "operator_review_workflow_count": 1,
            },
            "redaction_scan": {
                "public_response_raw_accession_found": False,
                "public_response_sec_url_found": False,
                "public_response_local_path_found": False,
                "public_response_raw_value_key_found": False,
                "projection_facts_all_value_redacted": True,
                "statement_rows_all_value_redacted": True,
            },
        },
    )

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "offline_evidence_proof_single_transaction_unproven"
    assert report["blocked_reasons"][0]["details"] == {
        "single_transaction_claimed": False,
        "existing_materializers_commit_per_stage": True,
    }
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["containment"]["isolated_in_memory_db_used"] is True
    assert report["controls"]["isolated_db_persistence_performed"] is True
    assert "proof_result_hash" not in report["authority_refs"]


def test_proof_capability_blocks_when_redaction_scan_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_evidence_storage",
        lambda *_args, **_kwargs: {"status": "offline_evidence_bundle_ready"},
    )
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_companyfacts_oracle_packet",
        lambda *_args, **_kwargs: {
            "status": "offline_companyfacts_oracle_packet_ready",
            "authority_refs": {"companyfacts_payload_hash": "2" * 64},
        },
    )
    monkeypatch.setattr(proof, "load_sec_xbrl_offline_evidence_bundle", lambda *_args, **_kwargs: {"evidence": {}})
    monkeypatch.setattr(
        proof,
        "_run_isolated_orchestrator",
        lambda *_args, **_kwargs: {
            "response": {
                "status": "review_ready",
                "source_report_hash": _kwargs["source_report_hash"],
                "summary": {"row_count": 1},
                "containment": {},
            },
            "persisted_counts": {"operator_review_workflow_count": 1},
            "redaction_scan": {
                "public_response_raw_accession_found": True,
                "public_response_sec_url_found": False,
                "public_response_local_path_found": False,
                "public_response_raw_value_key_found": False,
                "projection_facts_all_value_redacted": True,
                "statement_rows_all_value_redacted": True,
            },
        },
    )

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "offline_evidence_proof_redaction_scan_failed"
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["redaction_scan"]["public_response_raw_accession_found"] is True
    assert report["controls"]["operator_evidence_files_read"] is True
    assert report["containment"]["isolated_in_memory_db_used"] is True
    assert report["controls"]["isolated_db_persistence_performed"] is True


def test_proof_capability_blocks_when_isolated_persistence_is_incomplete(monkeypatch) -> None:
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_evidence_storage",
        lambda *_args, **_kwargs: {"status": "offline_evidence_bundle_ready"},
    )
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_companyfacts_oracle_packet",
        lambda *_args, **_kwargs: {
            "status": "offline_companyfacts_oracle_packet_ready",
            "authority_refs": {"companyfacts_payload_hash": "2" * 64},
        },
    )
    monkeypatch.setattr(proof, "load_sec_xbrl_offline_evidence_bundle", lambda *_args, **_kwargs: {"evidence": {}})
    monkeypatch.setattr(
        proof,
        "_run_isolated_orchestrator",
        lambda *_args, **_kwargs: {
            "response": {
                "status": "review_ready",
                "source_report_hash": _kwargs["source_report_hash"],
                "summary": {"row_count": 1},
                "containment": {},
            },
            "persisted_counts": {
                "projection_set_count": 1,
                "projection_fact_count": 1,
                "statement_packet_set_count": 1,
                "statement_packet_row_count": 1,
                "operator_review_workflow_count": 0,
            },
            "redaction_scan": {
                "public_response_raw_accession_found": False,
                "public_response_sec_url_found": False,
                "public_response_local_path_found": False,
                "public_response_raw_value_key_found": False,
                "projection_facts_all_value_redacted": True,
                "statement_rows_all_value_redacted": True,
            },
        },
    )

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "offline_evidence_proof_isolated_persistence_incomplete"
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["summary"]["isolated_persistence_operator_review_workflow_count"] == 0
    assert report["containment"]["isolated_in_memory_db_used"] is True
    assert report["controls"]["isolated_db_persistence_performed"] is True


def test_proof_capability_blocks_when_isolated_source_hash_is_unbound(monkeypatch) -> None:
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_evidence_storage",
        lambda *_args, **_kwargs: {"status": "offline_evidence_bundle_ready"},
    )
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_companyfacts_oracle_packet",
        lambda *_args, **_kwargs: {
            "status": "offline_companyfacts_oracle_packet_ready",
            "authority_refs": {"companyfacts_payload_hash": "2" * 64},
        },
    )
    monkeypatch.setattr(proof, "load_sec_xbrl_offline_evidence_bundle", lambda *_args, **_kwargs: {"evidence": {}})
    monkeypatch.setattr(
        proof,
        "_run_isolated_orchestrator",
        lambda *_args, **_kwargs: {
            "response": {"status": "review_ready", "source_report_hash": "3" * 64, "summary": {}, "containment": {}},
            "persisted_counts": {
                "projection_set_count": 1,
                "projection_fact_count": 1,
                "statement_packet_set_count": 1,
                "statement_packet_row_count": 1,
                "operator_review_workflow_count": 1,
            },
            "redaction_scan": {
                "public_response_raw_accession_found": False,
                "public_response_sec_url_found": False,
                "public_response_local_path_found": False,
                "public_response_raw_value_key_found": False,
                "projection_facts_all_value_redacted": True,
                "statement_rows_all_value_redacted": True,
            },
        },
    )

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "offline_evidence_proof_source_hash_unbound"
    assert report["blocked_reasons"][0]["details"] == {"source_report_hash_bound": False}
    assert report["containment"]["isolated_in_memory_db_used"] is True
    assert report["controls"]["isolated_db_persistence_performed"] is True
    assert "proof_source_report_hash" in report["authority_refs"]
    assert "proof_result_hash" not in report["authority_refs"]


def test_proof_capability_marks_operator_evidence_read_for_markerless_oracle_block(monkeypatch) -> None:
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_evidence_storage",
        lambda *_args, **_kwargs: {"status": "offline_evidence_bundle_ready"},
    )
    monkeypatch.setattr(
        proof,
        "inspect_sec_xbrl_offline_companyfacts_oracle_packet",
        lambda *_args, **_kwargs: {
            "status": "offline_companyfacts_oracle_packet_blocked",
            "blocked_reasons": [
                {
                    "reason": "companyfacts_oracle_packet_missing",
                    "message": "Offline CompanyFacts oracle JSON was not supplied.",
                }
            ],
        },
    )

    report = proof.inspect_sec_xbrl_offline_evidence_proof_capability("operator-storage")

    assert report["status"] == "offline_evidence_proof_capability_blocked"
    assert report["blocked_reasons"][0]["reason"] == "companyfacts_oracle_packet_missing"
    assert report["storage_marker"] == ""
    assert report["controls"]["operator_evidence_files_read"] is True
    assert HEX64_RE.fullmatch(report["authority_refs"]["proof_source_report_hash"])
    assert "proof_result_hash" not in report["authority_refs"]


def test_proof_source_report_hash_binds_loader_and_oracle_counts() -> None:
    loader_report = {
        "status": "offline_evidence_bundle_ready",
        "authority_refs": {"sidecar_receipt_hash": "1" * 64},
        "summary": {"resolved_fact_count": 1},
    }
    oracle_report = {
        "status": "offline_companyfacts_oracle_packet_ready",
        "authority_refs": {"companyfacts_payload_hash": "2" * 64},
        "summary": {"projected_count": 1},
    }

    original = proof._proof_source_report_hash(
        loader_report=loader_report,
        oracle_report=oracle_report,
        period_limit=2,
    )
    changed_loader = {
        **loader_report,
        "summary": {"resolved_fact_count": 2},
    }
    changed_oracle = {
        **oracle_report,
        "summary": {"projected_count": 2},
    }

    assert original != proof._proof_source_report_hash(
        loader_report=changed_loader,
        oracle_report=oracle_report,
        period_limit=2,
    )
    assert original != proof._proof_source_report_hash(
        loader_report=loader_report,
        oracle_report=changed_oracle,
        period_limit=2,
    )


def test_proof_result_hash_binds_isolated_persistence_and_redaction_output() -> None:
    response = {
        "status": "review_ready",
        "summary": {"row_count": 2},
    }
    counts = {
        "projection_set_count": 1,
        "projection_fact_count": 2,
        "statement_packet_set_count": 1,
        "statement_packet_row_count": 2,
        "operator_review_workflow_count": 1,
    }
    redaction_scan = {
        "public_response_raw_accession_found": False,
        "public_response_sec_url_found": False,
        "public_response_local_path_found": False,
        "public_response_raw_value_key_found": False,
        "projection_facts_all_value_redacted": True,
        "statement_rows_all_value_redacted": True,
    }
    original = proof._proof_result_hash(
        proof_source_hash="1" * 64,
        isolated_response=response,
        isolated_persistence_counts=counts,
        redaction_scan=redaction_scan,
    )

    assert original != proof._proof_result_hash(
        proof_source_hash="1" * 64,
        isolated_response=response,
        isolated_persistence_counts={**counts, "statement_packet_row_count": 3},
        redaction_scan=redaction_scan,
    )
    assert original != proof._proof_result_hash(
        proof_source_hash="1" * 64,
        isolated_response=response,
        isolated_persistence_counts=counts,
        redaction_scan={**redaction_scan, "statement_rows_all_value_redacted": False},
    )


def _load_cli_module() -> Any:
    spec = importlib.util.spec_from_file_location("sec_xbrl_offline_evidence_proof_capability_cli", CLI_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
