from __future__ import annotations

from app.services.layer3_sec_xbrl_public_authority_guard import (
    blocked_authority_keys,
    raw_or_local_authority_violation,
    unadmitted_keys,
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


def test_unadmitted_keys_returns_sorted_public_key_inventory() -> None:
    assert unadmitted_keys({"known": True, "zeta": True, "alpha": True}, admitted={"known"}) == [
        "alpha",
        "zeta",
    ]
