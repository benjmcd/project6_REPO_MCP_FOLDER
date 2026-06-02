from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-nonlocal-admission-disposition.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_nonlocal_admission_disposition", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_admission_packet(module) -> dict[str, object]:
    return {
        "admission_mode": "nonlocal_in_app_auth_final_admission",
        "admission_owner_ref": "admission-owner-ref-alpha",
        "approval_record_ref": "approval-record-ref-alpha",
        "approval_record_hash": "a" * 64,
        "in_app_auth_evidence_ref": "in-app-auth-evidence-ref-alpha",
        "in_app_auth_evidence_hash": "b" * 64,
        "auth_binding_evidence_ref": "auth-binding-evidence-ref-alpha",
        "auth_binding_evidence_hash": "c" * 64,
        "rollback_owner_ref": "rollback-owner-ref-alpha",
        "incident_owner_ref": "incident-owner-ref-alpha",
        "redaction_policy_id": module.REDACTION_POLICY_ID,
        "verification_run_ref": "verification-run-ref-alpha",
        "admission_provenance_ref": "admission-provenance-ref-alpha",
        "admission_provenance_hash": "d" * 64,
    }


def _valid_disposition_packet(module) -> dict[str, object]:
    return {
        "disposition_mode": "no_historical_unbound_receipts",
        "disposition_owner_ref": "disposition-owner-ref-alpha",
        "disposition_record_ref": "disposition-record-ref-alpha",
        "disposition_record_hash": "e" * 64,
        "historical_inventory_ref": "historical-inventory-ref-alpha",
        "historical_inventory_hash": "f" * 64,
        "unbound_receipt_count": 0,
        "backfill_required": False,
        "backfill_authority_ref": "backfill-authority-ref-none",
        "backfill_authority_hash": "0" * 64,
        "containment_policy_ref": "containment-policy-ref-alpha",
        "containment_policy_hash": "1" * 64,
        "redaction_policy_id": module.REDACTION_POLICY_ID,
        "verification_run_ref": "verification-run-ref-alpha",
        "disposition_provenance_ref": "disposition-provenance-ref-alpha",
        "disposition_provenance_hash": "2" * 64,
    }


def test_nonlocal_admission_disposition_blocks_without_packets() -> None:
    report = _gate_module().build_report()

    assert report["decision"] == "nonlocal_production_admission_disposition_blocked"
    assert report["production_readiness_claimed"] is False
    assert report["blocking_reasons"] == [
        "sec_xbrl_nonlocal_admission_packet_missing",
        "sec_xbrl_nonlocal_backfill_disposition_packet_missing",
    ]
    assert report["readiness_gate_summary"]["admissible"] is True
    assert report["route_and_backfill_evidence_summary"]["admissible"] is True
    assert report["final_admission_packet_summary"]["packet_present"] is False
    assert report["historical_backfill_disposition_summary"]["packet_present"] is False
    assert report["next_slice"] == "sec_xbrl_nonlocal_final_admission_packet_and_backfill_disposition_v1"


def test_nonlocal_admission_disposition_accepts_redacted_packets(tmp_path: Path) -> None:
    module = _gate_module()
    admission_path = tmp_path / "admission.json"
    disposition_path = tmp_path / "disposition.json"
    admission_path.write_text(json.dumps(_valid_admission_packet(module)), encoding="utf-8")
    disposition_path.write_text(json.dumps(_valid_disposition_packet(module)), encoding="utf-8")

    report = module.build_report(
        admission_packet_path=admission_path,
        backfill_disposition_path=disposition_path,
    )

    assert report["decision"] == "nonlocal_production_admission_disposition_ready_for_operator_review"
    assert report["blocking_reasons"] == []
    assert report["production_readiness_claimed"] is False
    assert report["final_admission_packet_summary"]["admissible"] is True
    assert report["historical_backfill_disposition_summary"]["admissible"] is True
    rendered = json.dumps(report, sort_keys=True)
    assert str(admission_path) not in rendered
    assert str(disposition_path) not in rendered


def test_nonlocal_admission_disposition_rejects_raw_packet_content(tmp_path: Path) -> None:
    module = _gate_module()
    admission = _valid_admission_packet(module)
    admission["admission_owner_ref"] = "owner@example.com"
    admission["raw_value"] = "123.45"
    disposition = _valid_disposition_packet(module)
    disposition["historical_inventory_ref"] = "C:/Users/benny/raw-inventory.json"
    admission_path = tmp_path / "admission.json"
    disposition_path = tmp_path / "disposition.json"
    admission_path.write_text(json.dumps(admission), encoding="utf-8")
    disposition_path.write_text(json.dumps(disposition), encoding="utf-8")

    report = module.build_report(
        admission_packet_path=admission_path,
        backfill_disposition_path=disposition_path,
    )

    assert report["decision"] == "nonlocal_production_admission_disposition_blocked"
    assert "sec_xbrl_nonlocal_admission_raw_authority_not_admitted" in report["blocking_reasons"]
    assert (
        "sec_xbrl_nonlocal_backfill_disposition_raw_authority_not_admitted"
        in report["blocking_reasons"]
    )
    assert set(report["final_admission_packet_summary"]["redaction_scan"]["hit_classes"]) >= {
        "raw_operator_email",
        "raw_decimal_or_residual_magnitude",
        "raw_or_local_authority_key",
        "raw_or_unreduced_authority_ref",
    }
    assert set(report["historical_backfill_disposition_summary"]["redaction_scan"]["hit_classes"]) >= {
        "local_path",
        "raw_or_unreduced_authority_ref",
    }


def test_nonlocal_admission_disposition_rejects_unknown_packet_fields(tmp_path: Path) -> None:
    module = _gate_module()
    admission = _valid_admission_packet(module)
    admission["deployment_notes"] = "cleared with operations for production admission"
    admission_path = tmp_path / "admission.json"
    disposition_path = tmp_path / "disposition.json"
    admission_path.write_text(json.dumps(admission), encoding="utf-8")
    disposition_path.write_text(json.dumps(_valid_disposition_packet(module)), encoding="utf-8")

    report = module.build_report(
        admission_packet_path=admission_path,
        backfill_disposition_path=disposition_path,
    )

    assert report["decision"] == "nonlocal_production_admission_disposition_blocked"
    assert "sec_xbrl_nonlocal_admission_packet_invalid_required_fields" in report["blocking_reasons"]
    assert "deployment_notes" in report["final_admission_packet_summary"]["invalid_required_fields"]


def test_nonlocal_admission_disposition_rejects_inconsistent_backfill_mode(tmp_path: Path) -> None:
    module = _gate_module()
    admission_path = tmp_path / "admission.json"
    disposition_path = tmp_path / "disposition.json"
    disposition = _valid_disposition_packet(module)
    disposition["unbound_receipt_count"] = 2
    disposition["backfill_required"] = False
    admission_path.write_text(json.dumps(_valid_admission_packet(module)), encoding="utf-8")
    disposition_path.write_text(json.dumps(disposition), encoding="utf-8")

    report = module.build_report(
        admission_packet_path=admission_path,
        backfill_disposition_path=disposition_path,
    )

    assert report["decision"] == "nonlocal_production_admission_disposition_blocked"
    assert (
        "sec_xbrl_nonlocal_backfill_disposition_packet_invalid_required_fields"
        in report["blocking_reasons"]
    )
    assert set(report["historical_backfill_disposition_summary"]["invalid_required_fields"]) >= {
        "backfill_required",
        "disposition_mode",
    }
