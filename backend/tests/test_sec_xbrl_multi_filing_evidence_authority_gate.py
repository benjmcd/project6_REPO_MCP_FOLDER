from __future__ import annotations

import json
from decimal import Decimal

from app.services import layer3_sec_xbrl_multi_filing_evidence_authority_gate as gate


def test_multi_filing_evidence_authority_gate_blocks_without_filings() -> None:
    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["ready_filing_count"] == 0
    assert report["raw_evidence_committed"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["production_readiness_claimed"] is False


def test_multi_filing_evidence_authority_gate_blocks_when_only_fizz_10k_is_ready() -> None:
    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                _ready_filing("fizz-10k-proof"),
                _blocked_filing("fizz-10q-authority-gap"),
                _blocked_filing("ccj-authority-gap"),
            ]
        }
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["ready_filing_count"] == 1
    assert report["summary"]["blocked_filing_count"] == 2
    assert any(
        item["reason"] == "sec_xbrl_multi_filing_evidence_authority_ready_count_insufficient"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["production_database_touched"] is False


def test_multi_filing_evidence_authority_gate_rejects_raw_filing_input_without_echoing_it() -> None:
    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                {
                    **_ready_filing("fizz-10k-proof"),
                    "accession": "0000123456-26-000001",
                    "local_path": r"C:\raw\filing",
                },
                _ready_filing("fizz-10q-proof", char="2"),
                _ready_filing("ccj-10k-proof", char="3"),
            ]
        }
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_multi_filing_evidence_authority_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert "0000123456-26-000001" not in text
    assert r"C:\raw\filing" not in text


def test_multi_filing_evidence_authority_gate_requires_hash_authority_handles() -> None:
    filing = _ready_filing("fizz-10k-proof")
    filing["proof_result_hash"] = "not-a-hash"

    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={"filings": [filing, _ready_filing("fizz-10q-proof", char="2"), _ready_filing("ccj-10k-proof", char="3")]}
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_multi_filing_evidence_authority_proof_result_hash_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["ready_filing_count"] == 2


def test_multi_filing_evidence_authority_gate_rejects_ready_but_wrong_scope() -> None:
    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                _ready_filing("other-10k-proof"),
                _ready_filing("other-10q-proof", char="2"),
                _ready_filing("other-8k-proof", char="3"),
            ]
        }
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["ready_filing_count"] == 3
    assert report["summary"]["required_filing_handles"] == [
        "ccj-10k-proof",
        "fizz-10k-proof",
        "fizz-10q-proof",
    ]
    assert sorted(report["summary"]["missing_required_filing_handles"]) == [
        "ccj-10k-proof",
        "fizz-10k-proof",
        "fizz-10q-proof",
    ]
    assert any(
        item["reason"] == "sec_xbrl_multi_filing_evidence_authority_required_scope_incomplete"
        for item in report["blocked_reasons"]
    )


def test_multi_filing_evidence_authority_gate_reports_ready_for_three_redacted_ready_filings() -> None:
    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                _ready_filing("fizz-10k-proof"),
                _ready_filing("fizz-10q-proof", char="2"),
                _ready_filing("ccj-10k-proof", char="3"),
            ]
        }
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["ready_filing_count"] == 3
    assert report["summary"]["ready_filing_handles"] == ["ccj-10k-proof", "fizz-10k-proof", "fizz-10q-proof"]
    assert report["summary"]["ready_required_filing_handles"] == ["ccj-10k-proof", "fizz-10k-proof", "fizz-10q-proof"]
    assert report["raw_evidence_committed"] is False
    assert report["public_surface"]["hash_count_state_only"] is True
    assert report["controls"]["source_acquisition_performed"] is False
    assert report["controls"]["arelle_invoked"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_multi_filing_response_leak_guard_allows_period_dates_but_rejects_accessions() -> None:
    gate._reject_response_leaks({"period_label": "2024-12-31"})

    try:
        gate._reject_response_leaks({"accession_ref": "0000000000-00-000000"})
    except ValueError as exc:
        assert str(exc) == "SEC XBRL multi-filing evidence authority gate leaked raw authority references."
    else:
        raise AssertionError("expected multi-filing response leak rejection")


def test_multi_filing_response_leak_guard_preserves_scan_for_mixed_key_payloads() -> None:
    gate._reject_response_leaks({1: "metadata", "payload": {"amount": Decimal("1.23")}})

    try:
        gate._reject_response_leaks(
            {
                1: "metadata",
                "payload": {
                    "accession_ref": "0000000000-00-000000",
                    "amount": Decimal("1.23"),
                },
            }
        )
    except ValueError as exc:
        assert str(exc) == "SEC XBRL multi-filing evidence authority gate leaked raw authority references."
    else:
        raise AssertionError("expected multi-filing response leak rejection")


def test_multi_filing_evidence_authority_gate_accepts_nested_proof_hashes() -> None:
    report = gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                _ready_nested_filing("fizz-10k-proof"),
                _ready_nested_filing("fizz-10q-proof", char="2"),
                _ready_nested_filing("ccj-10k-proof", char="3"),
            ]
        }
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["summary"]["ready_filing_handles"] == ["ccj-10k-proof", "fizz-10k-proof", "fizz-10q-proof"]
    assert report["summary"]["filings"] == [
        {
            "filing_handle": "ccj-10k-proof",
            "ready": True,
            "authority_hash_count": len(gate.REQUIRED_AUTHORITY_HASHES),
            "blocked_reason_count": 0,
        },
        {
            "filing_handle": "fizz-10k-proof",
            "ready": True,
            "authority_hash_count": len(gate.REQUIRED_AUTHORITY_HASHES),
            "blocked_reason_count": 0,
        },
        {
            "filing_handle": "fizz-10q-proof",
            "ready": True,
            "authority_hash_count": len(gate.REQUIRED_AUTHORITY_HASHES),
            "blocked_reason_count": 0,
        },
    ]


def _ready_filing(handle: str, *, char: str = "1") -> dict[str, object]:
    value: dict[str, object] = {
        "filing_handle": handle,
        "status": "filing_evidence_authority_ready",
    }
    for key in gate.REQUIRED_AUTHORITY_HASHES:
        value[key] = _hash(char)
    value.update({key: True for key in gate.REQUIRED_READY_FLAGS})
    value.update({key: False for key in gate.NEGATIVE_READY_FLAGS})
    return value


def _ready_nested_filing(handle: str, *, char: str = "1") -> dict[str, object]:
    value: dict[str, object] = {
        "filing_handle": handle,
        "status": "filing_evidence_authority_ready",
        "authority_refs": {
            "proof_source_report_hash": _hash(char),
            "proof_result_hash": _hash(char),
        },
        "authority_hashes": {
            "sidecar_receipt_hash": _hash(char),
            "value_store_hash": _hash(char),
            "companyfacts_payload_hash": _hash(char),
        },
    }
    value.update({key: True for key in gate.REQUIRED_READY_FLAGS})
    value.update({key: False for key in gate.NEGATIVE_READY_FLAGS})
    return value


def _blocked_filing(handle: str) -> dict[str, object]:
    return {
        "filing_handle": handle,
        "status": "filing_evidence_authority_blocked",
        "operator_evidence_files_read": True,
        "raw_evidence_committed": False,
        "raw_companyfacts_committed": False,
        "raw_storage_committed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "network_performed": False,
        "value_reveal_performed": False,
        "production_database_touched": False,
        "production_readiness_claimed": False,
    }


def _hash(char: str) -> str:
    return char * 64
