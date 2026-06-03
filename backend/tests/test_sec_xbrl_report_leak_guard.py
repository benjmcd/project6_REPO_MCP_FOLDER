from __future__ import annotations

import re

import pytest

from app.services.layer3_sec_xbrl_report_leak_guard import (
    diagnostic_resolved_fact_redaction_scan_payload,
    raw_value_key_found,
    reject_report_public_text_references,
    reject_report_leaks,
    report_leak_flags,
    report_public_text_reference_found,
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


def test_reject_report_leaks_uses_service_exception_factory() -> None:
    class GuardError(ValueError):
        pass

    reject_report_leaks({"safe": "hash-only"}, exception_factory=lambda: GuardError("leaked"))
    with pytest.raises(GuardError, match="leaked"):
        reject_report_leaks(
            {"local_path": "file://operator/raw.json"},
            exception_factory=lambda: GuardError("leaked"),
        )


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
