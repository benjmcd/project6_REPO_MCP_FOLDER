from __future__ import annotations

import pytest

from app.services import layer3_sec_xbrl_controlled_value_reveal_submit as submit
from app.services import layer3_sec_xbrl_value_reveal_authority as authority


def test_value_reveal_authority_rejects_raw_authority_keys_with_service_contract() -> None:
    with pytest.raises(authority.SecXbrlValueRevealAuthorityError) as exc_info:
        authority._reject_raw_or_local_authority({"sidecar_receipt_id": "raw-sidecar"})

    exc = exc_info.value
    assert exc.code == "sec_xbrl_value_reveal_authority_raw_authority_not_admitted"
    assert exc.message == "SEC XBRL value-reveal authority only admits server-owned hash authority."
    assert exc.details == {"blocked_keys": ["sidecar_receipt_id"]}
    assert exc.http_status == 400


@pytest.mark.parametrize(
    "raw_reference",
    [
        "operator@example.com",
        "issuer 0000123456 packet",
        "CIK0000123456",
    ],
)
def test_value_reveal_authority_rejects_raw_reference_text_with_service_contract(
    raw_reference: str,
) -> None:
    with pytest.raises(authority.SecXbrlValueRevealAuthorityError) as exc_info:
        authority._reject_raw_or_local_authority(raw_reference)

    exc = exc_info.value
    assert exc.code == "sec_xbrl_value_reveal_authority_raw_reference_not_admitted"
    assert (
        exc.message
        == "SEC XBRL value-reveal authority cannot expose raw identities, paths, SEC URLs, accessions, or period dates."
    )
    assert exc.details == {}
    assert exc.http_status == 400


def test_controlled_value_reveal_submit_rejects_raw_authority_keys_with_service_contract() -> None:
    with pytest.raises(submit.SecXbrlControlledValueRevealSubmitError) as exc_info:
        submit._reject_raw_or_local_authority({"sidecar_receipt_hash": "raw-hash"})

    exc = exc_info.value
    assert exc.code == "sec_xbrl_controlled_value_reveal_submit_raw_authority_not_admitted"
    assert exc.message == "SEC XBRL controlled value reveal only admits authority-receipt fields from the browser."
    assert exc.details == {"blocked_keys": ["sidecar_receipt_hash"]}
    assert exc.http_status == 400


@pytest.mark.parametrize(
    "raw_reference",
    [
        "operator@example.com",
        "issuer 0000123456 packet",
        "CIK0000123456",
    ],
)
def test_controlled_value_reveal_submit_rejects_raw_reference_text_with_service_contract(
    raw_reference: str,
) -> None:
    with pytest.raises(submit.SecXbrlControlledValueRevealSubmitError) as exc_info:
        submit._reject_raw_or_local_authority(raw_reference)

    exc = exc_info.value
    assert exc.code == "sec_xbrl_controlled_value_reveal_submit_raw_reference_not_admitted"
    assert (
        exc.message
        == "SEC XBRL controlled value reveal rejects raw identities, paths, SEC URLs, accessions, and period dates."
    )
    assert exc.details == {}
    assert exc.http_status == 400


def test_controlled_value_reveal_submit_response_scan_blocks_nested_raw_keys_and_text() -> None:
    assert submit._response_has_forbidden_reference({"public": [{"sidecar_receipt_id": "raw"}]}) is True
    assert submit._response_has_forbidden_reference({"public": ["operator@example.com"]}) is True
    assert submit._response_has_forbidden_reference({"public": ["issuer 0000123456 packet"]}) is True
    assert submit._response_has_forbidden_reference({"public": ["CIK0000123456"]}) is True
    assert submit._response_has_forbidden_reference({"public": ["1000000000"]}) is False
    assert submit._response_has_forbidden_reference({"public": ["redacted public label"]}) is False


def test_controlled_value_reveal_records_preserve_plain_ten_digit_fact_values(monkeypatch) -> None:
    monkeypatch.setattr(
        submit.layer3_sec_edgar_arelle_value_reveal,
        "_reveal_records",
        lambda *_args, **_kwargs: [
            _raw_reveal_record("1000000000"),
            _raw_reveal_record("issuer 0000123456 packet", source_order=2),
            _raw_reveal_record("CIK0000123456", source_order=3),
        ],
    )

    records = submit._controlled_reveal_records({}, {}, dataset_version_hash="a" * 64)

    assert records[0]["effective_value"] == "1000000000"
    assert records[0]["lexical_value"] == "1000000000"
    assert records[0]["value_redacted"] is False
    assert records[0]["value_redaction_reason"] is None
    assert records[1]["effective_value"] == ""
    assert records[1]["lexical_value"] == ""
    assert records[1]["value_redacted"] is True
    assert records[1]["value_redaction_reason"] == "sec_xbrl_controlled_value_reveal_identity_or_raw_reference_redacted"
    assert records[2]["effective_value"] == ""
    assert records[2]["lexical_value"] == ""
    assert records[2]["value_redacted"] is True
    assert records[2]["value_redaction_reason"] == "sec_xbrl_controlled_value_reveal_identity_or_raw_reference_redacted"


def _raw_reveal_record(value: str, *, source_order: int = 1) -> dict[str, object]:
    return {
        "fact_identity_hash": f"fact-{source_order}",
        "resolved_fact_id_hash": f"resolved-{source_order}",
        "source_order": source_order,
        "entry_document_index": source_order,
        "effective_value": value,
        "lexical_value": value,
        "value_redacted": False,
        "value_hash": f"value-{source_order}",
        "value_semantics": "inline_xbrl_transformed_value_v1",
        "concept": {
            "qname": "us-gaap:Revenue",
            "local_name": "Revenue",
            "standard": True,
            "extension": False,
        },
        "transform_inputs": {},
        "hidden": False,
        "continued": False,
    }
