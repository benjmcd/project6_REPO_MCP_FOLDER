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
    assert submit._response_has_forbidden_reference({"public": ["redacted public label"]}) is False
