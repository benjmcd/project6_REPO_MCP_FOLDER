from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.services.layer3_sec_xbrl_report_leak_guard import (
    diagnostic_authority_redaction_scan_payload,
    diagnostic_resolved_fact_redaction_scan_payload,
    diagnostic_sector_family_redaction_scan_payload,
    raw_value_key_found,
    reject_report_public_text_references,
    reject_report_leaks,
    reject_report_leaks_with_error,
    report_leak_flags,
    report_public_text_reference_found,
    report_scan_text,
    report_text_leak_flags,
)


def test_report_leak_flags_detect_raw_authority_patterns() -> None:
    flags = report_leak_flags(
        {
            "accession_ref": "0000000000-00-000000",
            "source_url": "https://www.sec.gov/Archives/example",
            "local_path": "C:/Users/example/raw.json",
        }
    )

    assert flags == {
        "raw_accession_found": True,
        "sec_url_found": True,
        "local_path_found": True,
    }


def test_report_leak_flags_can_include_raw_value_keys() -> None:
    assert report_leak_flags({"raw_value": "123"}) == {
        "raw_accession_found": False,
        "sec_url_found": False,
        "local_path_found": False,
    }
    assert report_leak_flags({"raw_value": "123"}, include_raw_value_keys=True)["raw_value_key_found"] is True
    assert report_leak_flags({"value": "123"}, include_raw_value_keys=True)["raw_value_key_found"] is True
    assert report_leak_flags({"amount": "123"}, include_raw_value_keys=True)["raw_value_key_found"] is True
    assert report_leak_flags({"field": "value"}, include_raw_value_keys=True)["raw_value_key_found"] is False


def test_report_leak_flags_preserves_scan_semantics_for_decimal_values() -> None:
    flags = report_leak_flags({"raw_value": Decimal("123.45")}, include_raw_value_keys=True)

    assert flags == {
        "raw_accession_found": False,
        "sec_url_found": False,
        "local_path_found": False,
        "raw_value_key_found": True,
    }


def test_report_leak_flags_preserves_raw_key_scan_for_mixed_key_payloads() -> None:
    flags = report_leak_flags({1: "meta", "raw_value": Decimal("123.45")}, include_raw_value_keys=True)

    assert flags["raw_value_key_found"] is True


def test_report_scan_text_preserves_mixed_key_decimal_payloads() -> None:
    text = report_scan_text({1: "meta", "payload": {"amount": Decimal("123.45")}})

    assert '"1": "meta"' in text
    assert '"amount": "123.45"' in text


def test_diagnostic_authority_redaction_scan_payload_preserves_mixed_key_scan_semantics() -> None:
    scan = diagnostic_authority_redaction_scan_payload(
        {
            1: "metadata",
            "effective_value": Decimal("123.45"),
            "resolved_fact_id": "rf-authority",
            "issuer_name": "Example Corp",
        }
    )

    assert scan["passed"] is False
    assert scan["raw_value_key_found"] is True
    assert scan["raw_resolved_fact_authority_key_found"] is True
    assert scan["raw_issuer_identity_found"] is True


def test_report_text_leak_flags_preserves_text_scan_semantics() -> None:
    assert report_text_leak_flags("0000000000-00-000000") == {
        "raw_accession_found": True,
        "sec_url_found": False,
        "local_path_found": False,
    }
    assert report_text_leak_flags("C:/Users/example/raw.json")["local_path_found"] is True
    assert report_text_leak_flags('{"value": "123"}', include_raw_value_keys=True)["raw_value_key_found"] is True


def test_report_public_text_reference_scan_can_disable_raw_period_dates() -> None:
    assert report_public_text_reference_found("period 2024-12-31") is True
    assert report_public_text_reference_found("period 2024-12-31", scan_raw_period_dates=False) is False
    assert report_public_text_reference_found("0000000000-00-000000", scan_raw_period_dates=False) is True


def test_report_leak_flags_can_preserve_diagnostic_raw_value_key_variants() -> None:
    assert raw_value_key_found(
        '{"_VALUE": "123"}',
        raw_value_keys=("_value", "value", "effective_value", "amount"),
        ignore_case=True,
    )
    assert not raw_value_key_found(
        '{"raw_value": "123"}',
        raw_value_keys=("_value", "value", "effective_value", "amount"),
        ignore_case=True,
    )


def test_diagnostic_resolved_fact_redaction_scan_payload_supports_extra_patterns() -> None:
    safe = diagnostic_resolved_fact_redaction_scan_payload(
        {"redacted": True},
        raw_resolved_fact_id_pattern=re.compile(r"\brf[-_][A-Za-z0-9]"),
        extra_patterns={"raw_total_fact_counts_found": re.compile(r'"total_fact_count"')},
    )
    unsafe = diagnostic_resolved_fact_redaction_scan_payload(
        {"summary": {"total_fact_count": 3}, "ref": "rf-example"},
        raw_resolved_fact_id_pattern=re.compile(r"\brf[-_][A-Za-z0-9]"),
        extra_patterns={"raw_total_fact_counts_found": re.compile(r'"total_fact_count"')},
    )

    assert safe["passed"] is True
    assert safe["raw_resolved_fact_ids_found"] is False
    assert safe["raw_total_fact_counts_found"] is False
    assert unsafe["passed"] is False
    assert unsafe["raw_resolved_fact_ids_found"] is True
    assert unsafe["raw_total_fact_counts_found"] is True


def test_diagnostic_resolved_fact_redaction_scan_payload_handles_decimal_values() -> None:
    scan = diagnostic_resolved_fact_redaction_scan_payload(
        {"summary": {"total_fact_count": Decimal("3")}},
        raw_resolved_fact_id_pattern=re.compile(r"\brf[-_][A-Za-z0-9]"),
        extra_patterns={"raw_total_fact_counts_found": re.compile(r'"total_fact_count"')},
    )

    assert scan["passed"] is False
    assert scan["raw_resolved_fact_ids_found"] is False
    assert scan["raw_total_fact_counts_found"] is True


def test_diagnostic_sector_family_redaction_scan_payload_preserves_custom_flags() -> None:
    safe = diagnostic_sector_family_redaction_scan_payload({"redacted": True})
    unsafe = diagnostic_sector_family_redaction_scan_payload(
        {
            "primary_sic": "3651",
            "issuer_hash": "hash-only",
            "val": "123",
            "source_path": "C:/operator/raw.json",
        }
    )

    assert safe["passed"] is True
    assert safe["raw_sic_found"] is False
    assert safe["raw_issuer_identity_found"] is False
    assert safe["raw_value_found"] is False
    assert safe["raw_path_or_accession_found"] is False
    assert unsafe["passed"] is False
    assert unsafe["raw_sic_found"] is True
    assert unsafe["raw_issuer_identity_found"] is True
    assert unsafe["raw_value_found"] is True
    assert unsafe["raw_path_or_accession_found"] is True


def test_diagnostic_sector_family_redaction_scan_payload_handles_decimal_values() -> None:
    scan = diagnostic_sector_family_redaction_scan_payload({"safe": Decimal("1")})

    assert scan["passed"] is True
    assert scan["raw_value_found"] is False


def test_reject_report_leaks_uses_service_exception_factory() -> None:
    class GuardError(ValueError):
        pass

    reject_report_leaks({"safe": "hash-only"}, exception_factory=lambda: GuardError("leaked"))
    with pytest.raises(GuardError, match="leaked"):
        reject_report_leaks(
            {"local_path": "file://operator/raw.json"},
            exception_factory=lambda: GuardError("leaked"),
        )


def test_reject_report_leaks_with_error_preserves_service_error_shape() -> None:
    class GuardError(ValueError):
        def __init__(self, code: str, message: str) -> None:
            super().__init__(message)
            self.code = code
            self.message = message

    reject_report_leaks_with_error(
        {"safe": "hash-only"},
        error_type=GuardError,
        error_code="report_redaction_failed",
        message="Report leaked raw authority references.",
    )

    with pytest.raises(GuardError) as exc:
        reject_report_leaks_with_error(
            {"local_path": "file://operator/raw.json"},
            error_type=GuardError,
            error_code="report_redaction_failed",
            message="Report leaked raw authority references.",
        )

    assert exc.value.code == "report_redaction_failed"
    assert exc.value.message == "Report leaked raw authority references."
    assert str(exc.value) == "Report leaked raw authority references."


def test_reject_report_public_text_references_uses_service_exception_factory() -> None:
    class GuardError(ValueError):
        pass

    reject_report_public_text_references(
        "period 2024-12-31",
        exception_factory=lambda: GuardError("leaked"),
        scan_raw_period_dates=False,
    )
    with pytest.raises(GuardError, match="leaked"):
        reject_report_public_text_references(
            "0000000000-00-000000",
            exception_factory=lambda: GuardError("leaked"),
            scan_raw_period_dates=False,
        )
