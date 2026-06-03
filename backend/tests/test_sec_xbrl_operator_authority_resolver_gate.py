from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_operator_authority_resolver_gate as gate


def test_operator_authority_resolver_gate_blocks_by_default() -> None:
    report = gate.inspect_sec_xbrl_operator_authority_resolver_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["operator_authority_resolver_enabled"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_operator_authority_resolver_gate_requires_ready_api_and_multi_filing_authority() -> None:
    report = gate.inspect_sec_xbrl_operator_authority_resolver_gate(
        operator_api_gate=_api_gate(ready=False),
        evidence_authority_matrix=_evidence_gate(ready=False),
        resolver_spec=_resolver_spec(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_operator_api_contract_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_multi_filing_authority_unproven"
        for item in report["blocked_reasons"]
    )


def test_operator_authority_resolver_gate_rejects_unbacked_or_raw_handles_without_echoing_raw_refs() -> None:
    report = gate.inspect_sec_xbrl_operator_authority_resolver_gate(
        operator_api_gate=_api_gate(),
        evidence_authority_matrix=_evidence_gate(),
        resolver_spec={
            **_resolver_spec(),
            "resolver_authority_handles": [
                "fizz-10k-proof",
                "unknown-proof",
            ],
            "local_path": r"C:\raw\resolver",
        },
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_handles_not_backed_by_multi_filing_authority"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\resolver" not in text


def test_operator_authority_resolver_gate_requires_default_empty_registry_and_hash_mismatch_rejection() -> None:
    spec = {
        **_resolver_spec(),
        "resolver_registry_default_empty": False,
        "resolver_rejects_source_hash_mismatch": False,
    }

    report = gate.inspect_sec_xbrl_operator_authority_resolver_gate(
        operator_api_gate=_api_gate(),
        evidence_authority_matrix=_evidence_gate(),
        resolver_spec=spec,
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_resolver_registry_default_empty_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_resolver_rejects_source_hash_mismatch_unproven"
        for item in report["blocked_reasons"]
    )


def test_operator_authority_resolver_gate_requires_named_s1_scope() -> None:
    report = gate.inspect_sec_xbrl_operator_authority_resolver_gate(
        operator_api_gate=_api_gate(),
        evidence_authority_matrix=_evidence_gate(
            ready_handles=[
                "other-10k-proof",
                "other-10q-proof",
                "other-8k-proof",
            ],
            ready_required_handles=[],
        ),
        resolver_spec={
            **_resolver_spec(),
            "resolver_authority_handles": [
                "other-10k-proof",
                "other-10q-proof",
                "other-8k-proof",
            ],
        },
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_required_s1_scope_not_ready"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_authority_resolver_required_s1_handles_not_declared"
        for item in report["blocked_reasons"]
    )
    assert report["summary"]["required_s1_filing_handles"] == [
        "ccj-10k-proof",
        "fizz-10k-proof",
        "fizz-10q-proof",
    ]


def test_operator_authority_resolver_gate_reports_ready_without_enabling_runtime_resolver() -> None:
    report = gate.inspect_sec_xbrl_operator_authority_resolver_gate(
        operator_api_gate=_api_gate(),
        evidence_authority_matrix=_evidence_gate(),
        resolver_spec=_resolver_spec(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["summary"]["resolver_authority_handles"] == [
        "ccj-10k-proof",
        "fizz-10k-proof",
        "fizz-10q-proof",
    ]
    assert report["summary"]["ready_required_s1_filing_handles"] == [
        "ccj-10k-proof",
        "fizz-10k-proof",
        "fizz-10q-proof",
    ]
    assert report["public_surface"]["server_owned_authority_handles_only"] is True
    assert report["public_surface"]["client_supplied_evidence_admitted"] is False
    assert report["controls"]["operator_authority_resolver_enabled"] is False
    assert report["controls"]["source_acquisition_performed"] is False
    assert report["controls"]["network_performed"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False


def _api_gate(*, ready: bool = True) -> dict[str, object]:
    return {
        "status": "sec_xbrl_operator_api_contract_ready" if ready else "sec_xbrl_operator_api_contract_blocked",
        "ready": ready,
        "authority_refs": {
            "operator_api_contract_basis_hash": _hash("a"),
            "proof_source_report_hash": _hash("b"),
            "proof_result_hash": _hash("c"),
        },
    }


def _evidence_gate(
    *,
    ready: bool = True,
    ready_handles: list[str] | None = None,
    ready_required_handles: list[str] | None = None,
) -> dict[str, object]:
    handles = ready_handles or [
        "ccj-10k-proof",
        "fizz-10k-proof",
        "fizz-10q-proof",
    ]
    required_handles = ready_required_handles if ready_required_handles is not None else list(handles)
    return {
        "status": "sec_xbrl_multi_filing_evidence_authority_ready" if ready else "sec_xbrl_multi_filing_evidence_authority_blocked",
        "ready": ready,
        "raw_evidence_committed": False,
        "authority_refs": {
            "ready_filing_authority_inventory_hash": _hash("d"),
        },
        "summary": {
            "ready_filing_handles": handles,
            "ready_required_filing_handles": required_handles,
        },
    }


def _resolver_spec() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_RESOLVER_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_RESOLVER_FLAGS})
    value["resolver_authority_handles"] = [
        "fizz-10k-proof",
        "fizz-10q-proof",
        "ccj-10k-proof",
    ]
    return value


def _hash(char: str) -> str:
    return char * 64
