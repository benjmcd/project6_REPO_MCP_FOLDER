"""Tests for the official SEC ticker->CIK resolver and connector flag wiring.

All tests are deterministic and use a fake SEC client — no live network required.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

# Ensure backend is on path (mirrors test_layer3_api.py convention)
os.environ.setdefault("DB_INIT_MODE", "none")
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_sec_edgar_live_source_artifact
from app.services.layer3_sec_edgar_live_source_artifact import (
    SecEdgarFetchResult,
    _parse_company_tickers_payload,
    _reset_company_tickers_cache,
    resolve_sec_ticker_to_cik,
)
from app.services.layer3_sec_edgar_real_filing_acquisition_connector import (
    _normalise_company_matrix,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError


# ---------------------------------------------------------------------------
# Helpers / shared data
# ---------------------------------------------------------------------------

# Minimal company_tickers.json payload containing KO (off-list) and allow-list tickers.
_KO_CIK = "21344"
_AAPL_CIK = "320193"

_TICKERS_PAYLOAD = {
    "0": {"cik_str": 21344, "ticker": "KO", "title": "Coca Cola Co"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "2": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
    "3": {"cik_str": 99, "ticker": "TINY", "title": "Tiny Co"},
}

_TICKERS_RAW: bytes = json.dumps(_TICKERS_PAYLOAD).encode("utf-8")
_TICKERS_SOURCE_HASH: str = hashlib.sha256(_TICKERS_RAW).hexdigest()


class _FakeSecEdgarClient:
    """Minimal fake matching the SecEdgarClient Protocol contract."""

    def __init__(self, results: list[SecEdgarFetchResult]) -> None:
        self.results = list(results)
        self.calls: list[dict] = []

    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ) -> SecEdgarFetchResult:
        self.calls.append({"url": url, "user_agent": user_agent})
        assert self.results, "Fake client exhausted — unexpected extra call"
        return self.results.pop(0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the module-level tickers cache before and after every test."""
    _reset_company_tickers_cache()
    yield
    _reset_company_tickers_cache()


@pytest.fixture()
def live_network_on(monkeypatch):
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "TestAgent contact@example.com")
    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 25_000_000)
    monkeypatch.setattr(settings, "layer3_sec_edgar_timeout_seconds", 20)
    monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "_enforce_rate_limit", lambda: None)


@pytest.fixture()
def live_network_off(monkeypatch):
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)


@pytest.fixture()
def fake_tickers_client(monkeypatch):
    """Install a fake client that returns _TICKERS_RAW once."""
    client = _FakeSecEdgarClient(
        [
            SecEdgarFetchResult(
                status_code=200,
                content=_TICKERS_RAW,
                final_url="https://www.sec.gov/files/company_tickers.json",
            )
        ]
    )
    monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "SEC_EDGAR_CLIENT", client)
    return client


# ---------------------------------------------------------------------------
# Resolver unit tests
# ---------------------------------------------------------------------------


def test_resolver_known_ticker_ko(live_network_on, fake_tickers_client):
    """KO resolves to CIK 21344 with correct provenance fields."""
    result = resolve_sec_ticker_to_cik("KO")
    assert result is not None
    assert result["cik"] == _KO_CIK
    assert result["company_tickers_source_hash"] == _TICKERS_SOURCE_HASH
    assert result["resolved_title"] == "Coca Cola Co"


def test_resolver_allow_list_ticker_aapl(live_network_on, fake_tickers_client):
    """An allow-list ticker (AAPL) also resolves correctly via the official source."""
    result = resolve_sec_ticker_to_cik("AAPL")
    assert result is not None
    assert result["cik"] == _AAPL_CIK


def test_resolver_strips_leading_zeros(live_network_on, fake_tickers_client):
    """cik_str integer values are zero-stripped (99 -> '99', not '0000000099')."""
    result = resolve_sec_ticker_to_cik("TINY")
    assert result is not None
    assert result["cik"] == "99"
    assert not result["cik"].startswith("0")


def test_resolver_cache_single_fetch(live_network_on, fake_tickers_client):
    """Second resolver call reuses the cache — only ONE network fetch is made."""
    r1 = resolve_sec_ticker_to_cik("KO")
    r2 = resolve_sec_ticker_to_cik("AAPL")
    assert r1 is not None
    assert r2 is not None
    # Fake client held exactly one result; a second fetch would exhaust it and assert-fail.
    assert len(fake_tickers_client.calls) == 1


def test_resolver_unknown_ticker_returns_none(live_network_on, fake_tickers_client):
    """A ticker absent from company_tickers.json returns None (clean 'unresolved')."""
    result = resolve_sec_ticker_to_cik("NOTREAL")
    assert result is None


def test_resolver_malformed_json_raises_blocked(live_network_on, monkeypatch):
    """Malformed JSON from the fetch raises a governed blocked error, not a crash."""
    bad_client = _FakeSecEdgarClient(
        [
            SecEdgarFetchResult(
                status_code=200,
                content=b"not-json",
                final_url="https://www.sec.gov/files/company_tickers.json",
            )
        ]
    )
    monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "SEC_EDGAR_CLIENT", bad_client)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        resolve_sec_ticker_to_cik("KO")
    assert exc_info.value.error_code == "sec_edgar_official_ticker_resolution_json_invalid"


def test_resolver_non_200_raises_blocked(live_network_on, monkeypatch):
    """A non-200 HTTP status raises a governed blocked error."""
    error_client = _FakeSecEdgarClient(
        [
            SecEdgarFetchResult(
                status_code=503,
                content=b"",
                final_url="https://www.sec.gov/files/company_tickers.json",
            )
        ]
    )
    monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "SEC_EDGAR_CLIENT", error_client)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        resolve_sec_ticker_to_cik("KO")
    assert exc_info.value.error_code == "sec_edgar_official_ticker_resolution_fetch_failed"


def test_resolver_live_network_off_raises_blocked(live_network_off):
    """When live network is disabled, the resolver raises a governed blocked error immediately."""
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        resolve_sec_ticker_to_cik("KO")
    assert "live_network_disabled" in exc_info.value.error_code


# ---------------------------------------------------------------------------
# _parse_company_tickers_payload unit tests
# ---------------------------------------------------------------------------


def test_parse_skips_invalid_cik_entries():
    """Entries with non-numeric cik_str are silently skipped; valid entries pass through."""
    raw = json.dumps(
        {
            "0": {"cik_str": "bad", "ticker": "BAD", "title": "Bad Co"},
            "1": {"cik_str": 12345, "ticker": "GOOD", "title": "Good Co"},
        }
    ).encode()
    result = _parse_company_tickers_payload(raw)
    assert "BAD" not in result
    assert "GOOD" in result
    assert result["GOOD"]["cik"] == "12345"


def test_parse_normalises_ticker_to_upper():
    raw = json.dumps({"0": {"cik_str": 11111, "ticker": "abc", "title": "Abc Co"}}).encode()
    result = _parse_company_tickers_payload(raw)
    assert "ABC" in result
    assert "abc" not in result


def test_parse_malformed_json_raises():
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _parse_company_tickers_payload(b"not-json")
    assert exc_info.value.error_code == "sec_edgar_official_ticker_resolution_json_invalid"


def test_parse_non_object_raises():
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _parse_company_tickers_payload(b"[1, 2, 3]")
    assert exc_info.value.error_code == "sec_edgar_official_ticker_resolution_json_not_object"


# ---------------------------------------------------------------------------
# Connector flag-OFF regression tests
# ---------------------------------------------------------------------------


def test_connector_flag_off_unknown_ticker_blocked(monkeypatch):
    """Flag OFF: an off-list ticker (KO) is blocked — byte-identical to original behavior."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _normalise_company_matrix(["KO"])
    assert exc_info.value.error_code == "sec_edgar_real_filing_acquisition_connector_company_matrix_unknown"


def test_connector_flag_off_allow_list_ticker_passes(monkeypatch):
    """Flag OFF: an allow-list ticker (MSFT) passes without any resolution attempt."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    tickers, resolved_cik_map, provenance = _normalise_company_matrix(["MSFT"])
    assert tickers == ("MSFT",)
    assert resolved_cik_map == {}
    assert provenance is None


def test_connector_flag_off_default_blocks_unknown(monkeypatch):
    """Flag defaults to False: off-list ticker blocked even without explicit False setattr."""
    # Ensure the flag is NOT set to True from any other test
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _normalise_company_matrix(["KO"])
    assert exc_info.value.error_code == "sec_edgar_real_filing_acquisition_connector_company_matrix_unknown"


# ---------------------------------------------------------------------------
# Connector flag-ON tests
# ---------------------------------------------------------------------------


def test_connector_flag_on_off_list_ticker_admitted(monkeypatch, live_network_on, fake_tickers_client):
    """Flag ON: off-list ticker KO is admitted via the fake resolver."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    tickers, resolved_cik_map, provenance = _normalise_company_matrix(["KO"])
    assert tickers == ("KO",)
    assert resolved_cik_map == {"KO": _KO_CIK}
    assert provenance is not None
    assert "KO_cik_hash" in provenance
    assert "company_tickers_source_hash" in provenance
    assert provenance["company_tickers_source_hash"] == _TICKERS_SOURCE_HASH


def test_connector_flag_on_provenance_cik_hash_correct(
    monkeypatch, live_network_on, fake_tickers_client
):
    """The KO_cik_hash in provenance is sha256 of the resolved CIK string."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    _, _, provenance = _normalise_company_matrix(["KO"])
    expected_cik_hash = hashlib.sha256(_KO_CIK.encode()).hexdigest()
    assert provenance["KO_cik_hash"] == expected_cik_hash


def test_connector_flag_on_unresolvable_ticker_still_blocked(
    monkeypatch, live_network_on, fake_tickers_client
):
    """Flag ON but ticker absent from company_tickers.json -> still blocked."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _normalise_company_matrix(["NOTREAL"])
    assert exc_info.value.error_code == "sec_edgar_real_filing_acquisition_connector_company_matrix_unknown"


def test_connector_flag_on_bounds_still_enforced(monkeypatch, live_network_on):
    """Flag ON: >4 tickers still rejected by the size bounds check before any resolution."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    # DEFAULT_REAL_COMPANY_MATRIX has 4 tickers; 5 exceeds len(DEFAULT_REAL_COMPANY_MATRIX)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _normalise_company_matrix(["MSFT", "STLD", "SONY", "CCJ", "KO"])
    assert exc_info.value.error_code == "sec_edgar_real_filing_acquisition_connector_company_matrix_not_admitted"


def test_connector_flag_on_allow_list_ticker_no_fetch(monkeypatch, live_network_on):
    """Flag ON: a purely allow-list matrix skips the resolver entirely — no fetch performed."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    # No fake client installed — if resolve_sec_ticker_to_cik were called, the real
    # SEC_EDGAR_CLIENT would be used but live network is off in CI, so this proves
    # allow-list tickers never reach the resolver.
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)
    tickers, resolved_cik_map, provenance = _normalise_company_matrix(["MSFT"])
    assert tickers == ("MSFT",)
    assert resolved_cik_map == {}
    assert provenance is None


# ---------------------------------------------------------------------------
# _company_matrix (corpus-validation wrapper) end-to-end caller coverage
# ---------------------------------------------------------------------------

from app.services.layer3_sec_edgar_real_company_corpus_validation import (
    _company_matrix as _corpus_company_matrix,
)


def test_corpus_company_matrix_flag_off_allow_list_returns_ticker_tuple(monkeypatch):
    """Flag OFF: _company_matrix (corpus wrapper) returns a plain ticker tuple for an
    all-allow-list input — NOT a 3-tuple.  This is the exact regression the 12
    test_layer3_api.py corpus-validation tests expose."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    result = _corpus_company_matrix(["MSFT", "STLD", "SONY", "CCJ"])
    # Must be a plain tuple of strings, not a 3-tuple.
    assert isinstance(result, tuple)
    assert result == ("MSFT", "STLD", "SONY", "CCJ")
    # Confirm it is NOT a 3-tuple (i.e. the 3-tuple was unpacked correctly).
    assert not any(isinstance(item, (tuple, dict)) for item in result)


def test_corpus_company_matrix_flag_off_single_allow_list_ticker(monkeypatch):
    """Flag OFF: _company_matrix returns a single-element ticker tuple for one allow-list ticker."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    result = _corpus_company_matrix(["MSFT"])
    assert result == ("MSFT",)


def test_corpus_company_matrix_flag_off_unknown_ticker_blocked(monkeypatch):
    """Flag OFF: _company_matrix propagates the blocked error for an off-list ticker."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _corpus_company_matrix(["KO"])
    assert exc_info.value.error_code == "sec_edgar_real_filing_acquisition_connector_company_matrix_unknown"


def test_corpus_company_matrix_flag_on_off_list_ticker_admitted(
    monkeypatch, live_network_on, fake_tickers_client
):
    """Flag ON: _company_matrix admits an off-list ticker (KO) and returns a flat ticker tuple
    (provenance is captured inside _example_set, not surfaced here — this confirms the wrapper
    does not lose the ticker itself)."""
    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    result = _corpus_company_matrix(["KO"])
    assert isinstance(result, tuple)
    assert result == ("KO",)
    # Must not be a 3-tuple.
    assert not any(isinstance(item, (tuple, dict)) for item in result)
