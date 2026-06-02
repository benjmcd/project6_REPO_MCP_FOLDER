from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-nonlocal-production-readiness-gate.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_nonlocal_production_readiness_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_authority_packet(module) -> dict[str, object]:
    return {
        "deployment_mode": "nonlocal",
        "deployment_owner_ref": "deployment-owner-ref-alpha",
        "approval_record_ref": "approval-record-ref-alpha",
        "approval_record_hash": "a" * 64,
        "proxy_boundary_mode": "trusted_external_proxy",
        "proxy_identity_header": "X-Forwarded-User",
        "allowed_origins_policy_hash": "b" * 64,
        "storage_exposure_policy": "auto",
        "arelle_fact_authority_nonlocal_authorized": True,
        "rollback_owner_ref": "rollback-owner-ref-alpha",
        "incident_owner_ref": "incident-owner-ref-alpha",
        "redaction_policy_id": module.REDACTION_POLICY_ID,
        "verification_run_ref": "verification-run-ref-alpha",
        "deployment_authority_provenance_ref": "deployment-authority-provenance-ref-alpha",
        "deployment_authority_provenance_hash": "c" * 64,
    }


def test_sec_xbrl_nonlocal_readiness_gate_blocks_without_authority_packet() -> None:
    report = _gate_module().build_report()

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert report["production_readiness_claimed"] is False
    assert "nonlocal_production_readiness_authority_packet_missing" in report["blocking_reasons"]
    assert report["authority_packet_summary"]["authority_packet_present"] is False
    assert report["inherited_default_on_runtime_evidence"]["decision"] == "default_on_runtime_enabled"


def test_sec_xbrl_nonlocal_readiness_gate_accepts_redacted_authority_packet(tmp_path: Path) -> None:
    module = _gate_module()
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_valid_authority_packet(module)), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_authority_admitted"
    assert report["blocking_reasons"] == []
    assert report["production_readiness_claimed"] is False
    assert report["authority_packet_summary"]["admissible"] is True
    assert report["authority_packet_summary"]["redaction_scan"] == {
        "status": "passed",
        "hit_classes": [],
    }
    assert str(packet_path) not in json.dumps(report, sort_keys=True)


def test_sec_xbrl_nonlocal_readiness_gate_rejects_raw_authority_packet(tmp_path: Path) -> None:
    module = _gate_module()
    packet = _valid_authority_packet(module)
    packet["deployment_owner_ref"] = "owner@example.com"
    packet["accession"] = "0000000000-26-000001"
    packet["raw_value"] = "123.45"
    packet["local_path"] = "C:/Users/benny/raw-sidecar.json"
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert report["production_readiness_claimed"] is False
    assert "nonlocal_production_readiness_raw_authority_not_admitted" in report["blocking_reasons"]
    assert report["authority_packet_summary"]["redaction_scan"]["status"] == "failed_closed"
    assert set(report["authority_packet_summary"]["redaction_scan"]["hit_classes"]) >= {
        "raw_accession",
        "raw_decimal_or_residual_magnitude",
        "raw_operator_email",
        "raw_or_local_authority_key",
        "local_path",
    }


def test_sec_xbrl_nonlocal_readiness_gate_rejects_bare_cik_refs(tmp_path: Path) -> None:
    module = _gate_module()
    packet = _valid_authority_packet(module)
    packet["deployment_owner_ref"] = "0000320193"
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert "nonlocal_production_readiness_raw_authority_not_admitted" in report["blocking_reasons"]
    assert "raw_cik" in report["authority_packet_summary"]["redaction_scan"]["hit_classes"]
    assert "deployment_owner_ref" in report["authority_packet_summary"]["invalid_required_fields"]


def test_sec_xbrl_nonlocal_readiness_gate_rejects_unreduced_authority_ref(tmp_path: Path) -> None:
    module = _gate_module()
    packet = _valid_authority_packet(module)
    packet["deployment_owner_ref"] = "Acme Operator"
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert "nonlocal_production_readiness_raw_authority_not_admitted" in report["blocking_reasons"]
    assert "raw_or_unreduced_authority_ref" in report["authority_packet_summary"]["redaction_scan"]["hit_classes"]
    assert "deployment_owner_ref" in report["authority_packet_summary"]["invalid_required_fields"]


def test_sec_xbrl_nonlocal_readiness_gate_rejects_extra_unreduced_authority_ref(tmp_path: Path) -> None:
    module = _gate_module()
    packet = _valid_authority_packet(module)
    packet["operator_ref"] = "Acme Operator"
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert "nonlocal_production_readiness_raw_authority_not_admitted" in report["blocking_reasons"]
    assert "raw_or_unreduced_authority_ref" in report["authority_packet_summary"]["redaction_scan"]["hit_classes"]
    assert "operator_ref" in report["authority_packet_summary"]["invalid_required_fields"]


def test_sec_xbrl_nonlocal_readiness_gate_requires_deployment_provenance(tmp_path: Path) -> None:
    module = _gate_module()
    packet = _valid_authority_packet(module)
    packet.pop("deployment_authority_provenance_ref")
    packet.pop("deployment_authority_provenance_hash")
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert "nonlocal_production_readiness_authority_packet_missing_required_fields" in report["blocking_reasons"]
    assert set(report["authority_packet_summary"]["required_fields_missing"]) >= {
        "deployment_authority_provenance_ref",
        "deployment_authority_provenance_hash",
    }


def test_sec_xbrl_nonlocal_readiness_gate_rejects_repo_owned_auth_packet_mode(tmp_path: Path) -> None:
    module = _gate_module()
    packet = _valid_authority_packet(module)
    packet["proxy_boundary_mode"] = "repo_owned_in_app_auth"
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    report = module.build_report(authority_packet_path=packet_path)

    assert report["decision"] == "nonlocal_production_readiness_blocked"
    assert "nonlocal_production_readiness_authority_packet_invalid_required_fields" in report["blocking_reasons"]
    assert report["authority_packet_summary"]["proxy_boundary_mode"] is None
    assert "proxy_boundary_mode" in report["authority_packet_summary"]["invalid_required_fields"]


def test_sec_xbrl_nonlocal_readiness_report_hash_is_line_ending_stable(tmp_path: Path) -> None:
    module = _gate_module()
    lf_report = tmp_path / "report-lf.json"
    crlf_report = tmp_path / "report-crlf.json"
    payload = '{\n  "decision": "default_on_runtime_enabled"\n}\n'
    lf_report.write_text(payload, encoding="utf-8", newline="\n")
    crlf_report.write_text(payload, encoding="utf-8", newline="\r\n")

    assert module._file_hash(lf_report) == module._file_hash(crlf_report)
