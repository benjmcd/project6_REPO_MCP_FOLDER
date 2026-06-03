from __future__ import annotations

import pytest

from app.services.layer3_sec_xbrl_report_leak_guard import report_leak_flags, reject_report_leaks


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


def test_reject_report_leaks_uses_service_exception_factory() -> None:
    class GuardError(ValueError):
        pass

    reject_report_leaks({"safe": "hash-only"}, exception_factory=lambda: GuardError("leaked"))
    with pytest.raises(GuardError, match="leaked"):
        reject_report_leaks(
            {"local_path": "file://operator/raw.json"},
            exception_factory=lambda: GuardError("leaked"),
        )
