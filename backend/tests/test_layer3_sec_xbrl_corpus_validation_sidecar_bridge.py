"""Unit tests for find_corpus_validation_verdict_by_sidecar_hash.

Hermetic: no DB, no network.  Uses tmp_path + monkeypatch on settings.storage_dir.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from app.core.config import settings
from app.services.layer3_sec_edgar_real_company_corpus_validation import (
    READY_STATE,
    RECEIPT_DIR,
    RECEIPT_PREFIX,
    find_corpus_validation_verdict_by_sidecar_hash,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _receipts_dir(tmp: Path) -> Path:
    d = tmp / RECEIPT_DIR / "receipts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_receipt(receipts_dir: Path, receipt: dict[str, Any]) -> None:
    rid = receipt["validation_receipt_id"]
    path = receipts_dir / f"{rid}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")


def _make_receipt(
    *,
    receipt_id: str,
    sidecar_hash: str,
    validation_state: str = READY_STATE,
    supported_degraded_blocked: str = "supported",
    blocked_reasons: list | None = None,
) -> dict[str, Any]:
    """Minimal corpus receipt with one filing record containing the sidecar hash."""
    record: dict[str, Any] = {
        "record_index": 1,
        "authority_hashes": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
        },
        "supported_degraded_blocked": supported_degraded_blocked,
    }
    if blocked_reasons is not None:
        record["blocked_reasons"] = blocked_reasons
    return {
        "schema_id": "layer3.sec_edgar_real_company_corpus_validation.v1",
        "validation_state": validation_state,
        "validation_receipt_id": receipt_id,
        "validation_receipt_hash": "a" * 64,
        "filing_validation_records": [record],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_finds_match_and_returns_corpus_validation_passed_true(tmp_path, monkeypatch):
    """When a receipt contains the matching sidecar hash and is READY+supported,
    returns corpus_validation_passed=True."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    receipts = _receipts_dir(tmp_path)
    sidecar_hash = "b" * 64
    receipt_id = f"{RECEIPT_PREFIX}-{'c' * 24}"
    _write_receipt(receipts, _make_receipt(
        receipt_id=receipt_id,
        sidecar_hash=sidecar_hash,
    ))

    verdict = find_corpus_validation_verdict_by_sidecar_hash(sidecar_hash)

    assert verdict is not None
    assert verdict["corpus_validation_passed"] is True
    assert verdict["validation_receipt_id"] == receipt_id
    assert verdict["validation_state"] == READY_STATE
    assert verdict["filing_status"] == "supported"


def test_no_match_returns_none(tmp_path, monkeypatch):
    """When no receipt contains the sidecar hash, returns None."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    receipts = _receipts_dir(tmp_path)
    _write_receipt(receipts, _make_receipt(
        receipt_id=f"{RECEIPT_PREFIX}-{'d' * 24}",
        sidecar_hash="e" * 64,
    ))

    verdict = find_corpus_validation_verdict_by_sidecar_hash("f" * 64)
    assert verdict is None


def test_non_ready_receipt_returns_corpus_validation_passed_false(tmp_path, monkeypatch):
    """A receipt whose validation_state is not READY_STATE returns
    corpus_validation_passed=False even if the sidecar hash matches."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    receipts = _receipts_dir(tmp_path)
    sidecar_hash = "g" * 64
    _write_receipt(receipts, _make_receipt(
        receipt_id=f"{RECEIPT_PREFIX}-{'h' * 24}",
        sidecar_hash=sidecar_hash,
        validation_state="sec_edgar_real_company_corpus_validation_blocked",
    ))

    verdict = find_corpus_validation_verdict_by_sidecar_hash(sidecar_hash)
    assert verdict is not None
    assert verdict["corpus_validation_passed"] is False
    assert verdict["validation_state"] == "sec_edgar_real_company_corpus_validation_blocked"


def test_filing_with_blocked_reasons_returns_false(tmp_path, monkeypatch):
    """READY receipt but filing record has non-empty blocked_reasons =>
    corpus_validation_passed=False."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    receipts = _receipts_dir(tmp_path)
    sidecar_hash = "i" * 64
    _write_receipt(receipts, _make_receipt(
        receipt_id=f"{RECEIPT_PREFIX}-{'j' * 24}",
        sidecar_hash=sidecar_hash,
        blocked_reasons=[{"reason": "arelle_parse_error"}],
    ))

    verdict = find_corpus_validation_verdict_by_sidecar_hash(sidecar_hash)
    assert verdict is not None
    assert verdict["corpus_validation_passed"] is False


def test_missing_receipts_dir_returns_none(tmp_path, monkeypatch):
    """When the receipts directory doesn't exist, returns None gracefully."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    # Do NOT create the receipts dir.
    verdict = find_corpus_validation_verdict_by_sidecar_hash("k" * 64)
    assert verdict is None


def test_empty_storage_dir_returns_none(monkeypatch):
    """When storage_dir is empty/unset, returns None gracefully."""
    monkeypatch.setattr(settings, "storage_dir", "")
    verdict = find_corpus_validation_verdict_by_sidecar_hash("l" * 64)
    assert verdict is None


def test_empty_sidecar_hash_returns_none(tmp_path, monkeypatch):
    """An empty sidecar hash returns None without scanning."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    _receipts_dir(tmp_path)
    verdict = find_corpus_validation_verdict_by_sidecar_hash("")
    assert verdict is None


def test_filing_not_supported_returns_false(tmp_path, monkeypatch):
    """READY receipt but supported_degraded_blocked != 'supported' =>
    corpus_validation_passed=False."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    receipts = _receipts_dir(tmp_path)
    sidecar_hash = "m" * 64
    _write_receipt(receipts, _make_receipt(
        receipt_id=f"{RECEIPT_PREFIX}-{'n' * 24}",
        sidecar_hash=sidecar_hash,
        supported_degraded_blocked="degraded",
    ))

    verdict = find_corpus_validation_verdict_by_sidecar_hash(sidecar_hash)
    assert verdict is not None
    assert verdict["corpus_validation_passed"] is False
    assert verdict["filing_status"] == "degraded"
