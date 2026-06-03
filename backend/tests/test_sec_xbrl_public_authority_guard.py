from __future__ import annotations

from app.services.layer3_sec_xbrl_public_authority_guard import (
    any_url_reference_found,
    blocked_authority_keys,
    blocked_authority_keys_violation,
    raw_or_local_authority_violation,
    raw_accession_reference_found,
    reject_raw_or_local_authority_with_blocked_keys,
    report_text_reference_flags,
    unadmitted_keys,
    windows_local_path_reference_found,
    windows_local_path_start_reference_found,
)


def test_public_authority_guard_detects_raw_value_and_authority_keys() -> None:
    value_violation = raw_or_local_authority_violation({"amount": "100"})
    authority_violation = raw_or_local_authority_violation({"Company_Name": "Example Corp"})

    assert value_violation is not None
    assert value_violation.kind == "raw_authority"
    assert value_violation.field == "amount"
    assert authority_violation is not None
    assert authority_violation.kind == "raw_authority"
    assert authority_violation.field == "Company_Name"


def test_public_authority_guard_detects_raw_reference_text_patterns() -> None:
    assert raw_or_local_authority_violation("0000000000-00-000000").kind == "raw_reference"
    assert raw_or_local_authority_violation("https://www.sec.gov/Archives/example").kind == "raw_reference"
    assert raw_or_local_authority_violation("C:/raw/filing.json").kind == "raw_reference"
    assert raw_or_local_authority_violation("file:///workspace/raw/filing.json").kind == "raw_reference"
    assert raw_or_local_authority_violation("2024-12-31").kind == "raw_reference"


def test_public_authority_guard_can_disable_period_date_scan() -> None:
    assert raw_or_local_authority_violation("2024-12-31", scan_raw_period_dates=False) is None


def test_public_authority_guard_supports_value_reveal_text_variants() -> None:
    assert raw_or_local_authority_violation("operator@example.com", scan_operator_contact=True).kind == (
        "raw_reference"
    )
    assert raw_or_local_authority_violation("prefix 0000000000 suffix", scan_cik=True).kind == "raw_reference"
    assert raw_or_local_authority_violation("prefix 0000000000 suffix", scan_cik_fullmatch=True) is None
    assert raw_or_local_authority_violation("0000000000", scan_cik_fullmatch=True).kind == "raw_reference"


def test_public_authority_guard_supports_auth_binding_text_variants() -> None:
    assert raw_or_local_authority_violation("sec.gov") is None
    assert raw_or_local_authority_violation("sec.gov", scan_bare_sec_domain=True).kind == "raw_reference"
    assert raw_or_local_authority_violation("\\\\server\\share\\id", scan_standard_local_refs=False) is None
    assert raw_or_local_authority_violation("/opt/release", scan_standard_local_refs=False) is None
    assert raw_or_local_authority_violation("prefixC:/raw", scan_windows_abs_path_anywhere=True).kind == (
        "raw_reference"
    )
    assert raw_or_local_authority_violation("root/workspace/raw", scan_local_ref_segment=True).kind == (
        "raw_reference"
    )
    assert raw_or_local_authority_violation("2024-12-31", scan_raw_period_dates=False) is None


def test_public_authority_guard_reports_report_text_reference_flags() -> None:
    assert report_text_reference_flags("0000000000-00-000000") == {
        "raw_accession_found": True,
        "sec_url_found": False,
        "local_path_found": False,
    }
    assert report_text_reference_flags("https://www.sec.gov/Archives/example")["sec_url_found"] is True
    assert report_text_reference_flags("C:/Users/example/raw.json")["local_path_found"] is True


def test_public_authority_guard_exposes_report_reference_predicate_variants() -> None:
    assert raw_accession_reference_found("prefix 0000000000-00-000000 suffix") is True
    assert any_url_reference_found("https://example.com/archive") is True
    assert report_text_reference_flags("https://example.com/archive")["sec_url_found"] is False
    assert windows_local_path_reference_found("prefixC:/raw/filing.json") is True
    assert windows_local_path_start_reference_found("prefixC:/raw/filing.json") is False
    assert windows_local_path_start_reference_found("C:/raw/filing.json") is True
    assert windows_local_path_reference_found("/Users/example/raw.json") is False


def test_public_authority_guard_detects_residual_magnitude_keys_when_configured() -> None:
    absent = raw_or_local_authority_violation({"relative_magnitude": "1E+0"})
    present = raw_or_local_authority_violation(
        {"relative_magnitude": "1E+0"},
        residual_magnitude_keys={"relative_magnitude"},
    )

    assert absent is None
    assert present is not None
    assert present.kind == "residual_magnitude"
    assert present.field == "relative_magnitude"


def test_blocked_authority_keys_returns_current_mapping_inventory_without_value_filter() -> None:
    assert blocked_authority_keys(
        {"sidecar_receipt_id": None, "raw_path": "", "allowed": True},
        raw_value_keys=frozenset(),
        raw_authority_keys={"sidecar_receipt_id", "raw_path"},
    ) == ["raw_path", "sidecar_receipt_id"]


def test_blocked_authority_keys_violation_recurses_without_value_filter() -> None:
    assert blocked_authority_keys_violation(
        {"outer": [{"sidecar_receipt_id": None, "raw_path": "", "allowed": True}]},
        raw_value_keys=frozenset(),
        raw_authority_keys={"sidecar_receipt_id", "raw_path"},
    ) == ["raw_path", "sidecar_receipt_id"]
    assert (
        raw_or_local_authority_violation(
            {"values": {"2024-12-31"}},
            raw_value_keys=frozenset(),
            raw_authority_keys=frozenset(),
        ).kind
        == "raw_reference"
    )


def test_reject_raw_or_local_authority_with_blocked_keys_preserves_value_reveal_error_shape() -> None:
    class GuardError(ValueError):
        def __init__(
            self,
            code: str,
            message: str,
            *,
            details: dict[str, object] | None = None,
            http_status: int = 409,
        ) -> None:
            self.code = code
            self.message = message
            self.details = dict(details or {})
            self.http_status = http_status

    try:
        reject_raw_or_local_authority_with_blocked_keys(
            {"nested": {"sidecar_receipt_id": "raw"}},
            error_type=GuardError,
            raw_authority_code="raw_authority",
            raw_authority_message="raw authority blocked",
            raw_reference_code="raw_reference",
            raw_reference_message="raw reference blocked",
            blocked_raw_value_keys=frozenset(),
            blocked_raw_authority_keys={"sidecar_receipt_id"},
        )
    except GuardError as exc:
        assert exc.code == "raw_authority"
        assert exc.message == "raw authority blocked"
        assert exc.details == {"blocked_keys": ["sidecar_receipt_id"]}
        assert exc.http_status == 400
    else:
        raise AssertionError("expected blocked-key guard error")

    try:
        reject_raw_or_local_authority_with_blocked_keys(
            "operator@example.com",
            error_type=GuardError,
            raw_authority_code="raw_authority",
            raw_authority_message="raw authority blocked",
            raw_reference_code="raw_reference",
            raw_reference_message="raw reference blocked",
            blocked_raw_value_keys=frozenset(),
            blocked_raw_authority_keys=frozenset(),
            scan_operator_contact=True,
        )
    except GuardError as exc:
        assert exc.code == "raw_reference"
        assert exc.message == "raw reference blocked"
        assert exc.details == {}
        assert exc.http_status == 400
    else:
        raise AssertionError("expected raw-reference guard error")


def test_unadmitted_keys_returns_sorted_public_key_inventory() -> None:
    assert unadmitted_keys({"known": True, "zeta": True, "alpha": True}, admitted={"known"}) == [
        "alpha",
        "zeta",
    ]
