from __future__ import annotations

from app.services.layer3_sec_xbrl_public_authority_guard import (
    any_url_reference_found,
    blocked_authority_keys,
    blocked_authority_keys_violation,
    raw_or_local_authority_violation,
    raw_accession_reference_found,
    reject_e2e_public_output_policy,
    reject_e2e_public_text_references,
    reject_public_output_policy,
    reject_raw_or_local_authority_with_blocked_keys,
    reject_unadmitted_keys,
    reject_value_reveal_raw_or_local_authority,
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
    assert raw_or_local_authority_violation("issuer 0000000000", scan_contextual_cik=True).kind == "raw_reference"
    assert raw_or_local_authority_violation("CIK0000000000", scan_contextual_cik=True).kind == "raw_reference"
    assert raw_or_local_authority_violation("1000000000", scan_contextual_cik=True) is None


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
    assert raw_or_local_authority_violation("CIK0000000000", scan_contextual_cik=True).kind == "raw_reference"
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


def test_reject_value_reveal_raw_or_local_authority_preserves_family_policy() -> None:
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
        reject_value_reveal_raw_or_local_authority(
            {"sidecar_receipt_id": "raw-sidecar"},
            error_type=GuardError,
            raw_authority_code="value_raw_authority",
            raw_authority_message="value raw authority",
            raw_reference_code="value_raw_reference",
            raw_reference_message="value raw reference",
            blocked_raw_value_keys=frozenset(),
            blocked_raw_authority_keys={"sidecar_receipt_id"},
        )
    except GuardError as exc:
        assert exc.code == "value_raw_authority"
        assert exc.message == "value raw authority"
        assert exc.details == {"blocked_keys": ["sidecar_receipt_id"]}
        assert exc.http_status == 400
    else:
        raise AssertionError("expected value-reveal raw-authority guard error")

    try:
        reject_value_reveal_raw_or_local_authority(
            "issuer 0000123456 packet",
            error_type=GuardError,
            raw_authority_code="value_raw_authority",
            raw_authority_message="value raw authority",
            raw_reference_code="value_raw_reference",
            raw_reference_message="value raw reference",
            blocked_raw_value_keys=frozenset(),
            blocked_raw_authority_keys={"sidecar_receipt_id"},
        )
    except GuardError as exc:
        assert exc.code == "value_raw_reference"
        assert exc.message == "value raw reference"
        assert exc.details == {}
        assert exc.http_status == 400
    else:
        raise AssertionError("expected value-reveal raw-reference guard error")

    try:
        reject_value_reveal_raw_or_local_authority(
            "operator@example.com",
            error_type=GuardError,
            raw_authority_code="value_raw_authority",
            raw_authority_message="value raw authority",
            raw_reference_code="value_raw_reference",
            raw_reference_message="value raw reference",
            blocked_raw_value_keys=frozenset(),
            blocked_raw_authority_keys={"sidecar_receipt_id"},
        )
    except GuardError as exc:
        assert exc.code == "value_raw_reference"
        assert exc.message == "value raw reference"
        assert exc.details == {}
        assert exc.http_status == 400
    else:
        raise AssertionError("expected value-reveal operator-contact guard error")

    reject_value_reveal_raw_or_local_authority(
        "redacted public label",
        error_type=GuardError,
        raw_authority_code="value_raw_authority",
        raw_authority_message="value raw authority",
        raw_reference_code="value_raw_reference",
        raw_reference_message="value raw reference",
        blocked_raw_value_keys=frozenset(),
        blocked_raw_authority_keys={"sidecar_receipt_id"},
    )


def test_reject_public_output_policy_preserves_e2e_policy_variants() -> None:
    class GuardError(ValueError):
        def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None) -> None:
            self.code = code
            self.message = message
            self.details = dict(details or {})

    reject_public_output_policy(
        {"public_text": "period 2024-12-31 is allowed in offline mode"},
        error_type=GuardError,
        raw_output_code="offline_raw_output",
        raw_output_message="offline raw output",
        raw_reference_code="offline_raw_reference",
        raw_reference_message="offline raw reference",
        raw_output_keys={"issuer_name"},
        scan_raw_period_dates=False,
    )

    try:
        reject_public_output_policy(
            {"public_text": "period 2024-12-31 is blocked in integration mode"},
            error_type=GuardError,
            raw_output_code="integration_raw_output",
            raw_output_message="integration raw output",
            raw_reference_code="integration_raw_reference",
            raw_reference_message="integration raw reference",
            raw_output_keys={"issuer_name"},
        )
    except GuardError as exc:
        assert exc.code == "integration_raw_reference"
        assert exc.message == "integration raw reference"
        assert exc.details == {"field": "value"}
    else:
        raise AssertionError("expected integration raw-reference guard error")

    try:
        reject_public_output_policy(
            {"identity_rollup": {"relative_magnitude": None}},
            error_type=GuardError,
            raw_output_code="integration_raw_output",
            raw_output_message="integration raw output",
            raw_reference_code="integration_raw_reference",
            raw_reference_message="integration raw reference",
            raw_output_keys={"issuer_name"},
            residual_magnitude_keys={"relative_magnitude"},
            residual_magnitude_message="integration residual magnitude",
        )
    except GuardError as exc:
        assert exc.code == "integration_raw_output"
        assert exc.message == "integration residual magnitude"
        assert exc.details == {"field": "relative_magnitude"}
    else:
        raise AssertionError("expected residual-magnitude guard error")

    try:
        reject_public_output_policy(
            {"issuer_name": "Example Corp"},
            error_type=GuardError,
            raw_output_code="offline_raw_output",
            raw_output_message="offline raw output",
            raw_reference_code="offline_raw_reference",
            raw_reference_message="offline raw reference",
            raw_output_keys={"issuer_name"},
            scan_raw_period_dates=False,
        )
    except GuardError as exc:
        assert exc.code == "offline_raw_output"
        assert exc.message == "offline raw output"
        assert exc.details == {"field": "issuer_name"}
    else:
        raise AssertionError("expected raw-output guard error")


def test_reject_public_output_policy_can_opt_into_cik_text_references() -> None:
    class GuardError(ValueError):
        def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None) -> None:
            self.code = code
            self.message = message
            self.details = dict(details or {})

    reject_public_output_policy(
        {"public_text": "batch 1000000000 archived"},
        error_type=GuardError,
        raw_output_code="raw_output",
        raw_output_message="raw output",
        raw_reference_code="raw_reference",
        raw_reference_message="raw reference",
        raw_output_keys={"issuer_name"},
        scan_cik_fullmatch=True,
        scan_contextual_cik=True,
    )

    for raw_reference in ("0000123456", "issuer 0000123456 packet", "CIK0000123456"):
        try:
            reject_public_output_policy(
                {"public_text": raw_reference},
                error_type=GuardError,
                raw_output_code="raw_output",
                raw_output_message="raw output",
                raw_reference_code="raw_reference",
                raw_reference_message="raw reference",
                raw_output_keys={"issuer_name"},
                scan_cik_fullmatch=True,
                scan_contextual_cik=True,
            )
        except GuardError as exc:
            assert exc.code == "raw_reference"
            assert exc.message == "raw reference"
            assert exc.details == {"field": "value"}
        else:
            raise AssertionError("expected CIK raw-reference guard error")


def test_reject_e2e_public_policy_adapters_preserve_family_scan_posture() -> None:
    class GuardError(ValueError):
        def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None) -> None:
            self.code = code
            self.message = message
            self.details = dict(details or {})

    reject_e2e_public_output_policy(
        {"public_text": "period 2025-12-31 is allowed offline"},
        error_type=GuardError,
        raw_output_code="offline_raw_output",
        raw_output_message="offline raw output",
        raw_reference_code="offline_raw_reference",
        raw_reference_message="offline raw reference",
        raw_output_keys={"issuer_name"},
        scan_raw_period_dates=False,
    )

    try:
        reject_e2e_public_output_policy(
            {"period": "2025-12-31"},
            error_type=GuardError,
            raw_output_code="integration_raw_output",
            raw_output_message="integration raw output",
            raw_reference_code="integration_raw_reference",
            raw_reference_message="integration raw reference",
            raw_output_keys={"issuer_name"},
        )
    except GuardError as exc:
        assert exc.code == "integration_raw_reference"
        assert exc.message == "integration raw reference"
        assert exc.details == {"field": "value"}
    else:
        raise AssertionError("expected e2e period-date raw-reference guard error")

    try:
        reject_e2e_public_output_policy(
            {"identity_rollup": {"relative_magnitude": None}},
            error_type=GuardError,
            raw_output_code="integration_raw_output",
            raw_output_message="integration raw output",
            raw_reference_code="integration_raw_reference",
            raw_reference_message="integration raw reference",
            raw_output_keys={"issuer_name"},
            residual_magnitude_keys={"relative_magnitude"},
            residual_magnitude_message="integration residual magnitude",
        )
    except GuardError as exc:
        assert exc.code == "integration_raw_output"
        assert exc.message == "integration residual magnitude"
        assert exc.details == {"field": "relative_magnitude"}
    else:
        raise AssertionError("expected e2e residual-magnitude guard error")

    for raw_reference in ("0000123456", "issuer 0000123456 packet", "CIK0000123456"):
        try:
            reject_e2e_public_output_policy(
                {"public_text": raw_reference},
                error_type=GuardError,
                raw_output_code="raw_output",
                raw_output_message="raw output",
                raw_reference_code="raw_reference",
                raw_reference_message="raw reference",
                raw_output_keys={"issuer_name"},
            )
        except GuardError as exc:
            assert exc.code == "raw_reference"
            assert exc.message == "raw reference"
            assert exc.details == {"field": "value"}
        else:
            raise AssertionError("expected e2e CIK raw-reference guard error")

    try:
        reject_e2e_public_text_references(
            "issuer 0000123456 packet",
            error_type=GuardError,
            raw_reference_code="text_raw_reference",
            raw_reference_message="text raw reference",
            field="receipt",
            scan_raw_period_dates=False,
        )
    except GuardError as exc:
        assert exc.code == "text_raw_reference"
        assert exc.message == "text raw reference"
        assert exc.details == {"field": "receipt"}
    else:
        raise AssertionError("expected e2e text CIK raw-reference guard error")

    reject_e2e_public_text_references(
        "period 2025-12-31 is allowed offline",
        error_type=GuardError,
        raw_reference_code="text_raw_reference",
        raw_reference_message="text raw reference",
        field="receipt",
        scan_raw_period_dates=False,
    )


def test_unadmitted_keys_returns_sorted_public_key_inventory() -> None:
    assert unadmitted_keys({"known": True, "zeta": True, "alpha": True}, admitted={"known"}) == [
        "alpha",
        "zeta",
    ]


def test_reject_unadmitted_keys_preserves_service_error_shape() -> None:
    class GuardError(ValueError):
        def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None) -> None:
            self.code = code
            self.message = message
            self.details = dict(details or {})

    reject_unadmitted_keys(
        {"known": True},
        admitted={"known"},
        error_type=GuardError,
        error_code="invalid_fields",
        message="Only public fields are admitted.",
    )

    try:
        reject_unadmitted_keys(
            {"known": True, "zeta": True, "alpha": True},
            admitted={"known"},
            error_type=GuardError,
            error_code="invalid_fields",
            message="Only public fields are admitted.",
        )
    except GuardError as exc:
        assert exc.code == "invalid_fields"
        assert exc.message == "Only public fields are admitted."
        assert exc.details == {"fields": ["alpha", "zeta"]}
    else:
        raise AssertionError("expected unadmitted-key guard error")
