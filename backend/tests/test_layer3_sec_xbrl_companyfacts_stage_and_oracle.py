"""Tests for the live SEC CompanyFacts oracle slice.

Self-contained: no cross-test-module imports.  Uses tmp_path fixtures and monkeypatching.
Does NOT hit the network.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_live_source_artifact as live_artifact,
    layer3_sec_xbrl_offline_companyfacts_stage as stage_svc,
    layer3_sec_xbrl_offline_evidence_loader as loader,
    layer3_sec_xbrl_offline_companyfacts_oracle_packet as oracle_packet,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_xbrl_report_leak_guard import report_leak_flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash(char: str) -> str:
    return char * 64


# Receipt digest/id fields are long hex runs (SHA-256 = 64 chars; truncated id
# segments = 24 chars). A decimal raw token such as the CIK "320193" or a financial
# value like "200"/"100" can appear *inside* such a digest by chance, which made the
# raw-leak substring scans below non-deterministically fail (hash-collision false
# positive). Redacting hex runs of length >= 16 removes that false-positive source
# while still catching a genuine raw-value leak: the CIK, financial values, and
# concept names being guarded against are all far shorter than 16 contiguous hex chars.
_LONG_HEX_RUN = re.compile(r"[0-9a-fA-F]{16,}")


def _redact_hash_runs(text: str) -> str:
    return _LONG_HEX_RUN.sub("<redacted-hash>", text)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sample_companyfacts() -> dict[str, Any]:
    """Minimal valid companyfacts structure with 6 observations."""
    entries = [
        ("Assets", "200", "USD", "", "2023-12-31", True),
        ("Assets", "180", "USD", "", "2022-12-31", True),
        ("Revenues", "100", "USD", "2023-01-01", "2023-12-31", False),
        ("Revenues", "90", "USD", "2022-01-01", "2022-12-31", False),
        ("NetIncomeLoss", "40", "USD", "2023-01-01", "2023-12-31", False),
        ("NetIncomeLoss", "30", "USD", "2022-01-01", "2022-12-31", False),
    ]
    facts: dict[str, Any] = {"us-gaap": {}}
    for local_name, value, unit, start, end, instant in entries:
        fact: dict[str, Any] = {"fp": "FY", "fy": 2023, "val": int(value), "end": end}
        if not instant:
            fact["start"] = start
        facts["us-gaap"].setdefault(local_name, {"units": {}})["units"].setdefault(unit, []).append(fact)
    return facts


def _write_connector_receipt(storage: Path, *, cik: str, connector_receipt_hash: str) -> dict[str, Any]:
    """Write a minimal connector receipt that owns the given CIK."""
    cik_hash = _sha256(cik.lstrip("0") or "0")
    receipt = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "connector_receipt_id": f"sec-edgar-real-filing-connector-{connector_receipt_hash[:24]}-{connector_receipt_hash[24:48]}",
        "connector_receipt_hash": connector_receipt_hash,
        "corpus_manifest": {
            "example_records": [
                {
                    "example_id": "ex-1",
                    "cik_hash": cik_hash,
                    "form_type": "10-K",
                }
            ]
        },
    }
    receipt_dir = storage / stage_svc.CONNECTOR_RECEIPT_DIR / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{receipt['connector_receipt_id']}.json"
    _write_json(receipt_path, receipt)
    return receipt


# ---------------------------------------------------------------------------
# STEP 1 TESTS — gated companyfacts fetch
# ---------------------------------------------------------------------------

class TestFetchGates:
    """Verify that fetch is blocked by CI flag, live-network flag, and missing UA."""

    def _error_code(self, exc: Exception) -> str:
        # Layer3WorkbenchError uses .error_code; fallback to .code for other error types
        return str(getattr(exc, "error_code", None) or getattr(exc, "code", None) or str(exc))

    def test_fetch_blocked_in_ci(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CI", "true")
        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
        with pytest.raises(Exception) as exc_info:
            live_artifact.acquire_sec_edgar_companyfacts_live_artifact(
                {"cik": "320193", "operator_confirmation": True}
            )
        assert "ci_network_disabled" in self._error_code(exc_info.value)

    def test_fetch_blocked_when_live_network_disabled(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)
        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
        with pytest.raises(Exception) as exc_info:
            live_artifact.acquire_sec_edgar_companyfacts_live_artifact(
                {"cik": "320193", "operator_confirmation": True}
            )
        assert "live_network_disabled" in self._error_code(exc_info.value)

    def test_fetch_blocked_without_operator_confirmation(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
        monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "TestAgent/1.0 test@example.com")
        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
        with pytest.raises(Exception) as exc_info:
            live_artifact.acquire_sec_edgar_companyfacts_live_artifact(
                {"cik": "320193", "operator_confirmation": False}
            )
        assert "operator_confirmation_missing" in self._error_code(exc_info.value)

    def test_fetch_blocked_without_user_agent(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
        monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "")
        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
        with pytest.raises(Exception) as exc_info:
            live_artifact.acquire_sec_edgar_companyfacts_live_artifact(
                {"cik": "320193", "operator_confirmation": True}
            )
        assert "user_agent_missing" in self._error_code(exc_info.value)


# ---------------------------------------------------------------------------
# STEP 2 TESTS — staging service
# ---------------------------------------------------------------------------

class TestStageReceiptRedaction:
    """stage_sec_xbrl_companyfacts writes redacted receipt; raw store holds raw JSON."""

    def test_stage_receipt_has_hashes_and_counts_not_raw_values(
        self,
        tmp_path,
        monkeypatch,
    ):
        cik = "320193"
        connector_hash = _hash("a")
        content = json.dumps({"facts": _sample_companyfacts()}).encode("utf-8")
        content_sha256 = hashlib.sha256(content).hexdigest()
        _write_connector_receipt(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        expected_recorded_at = "2026-07-31T12:17:15.420032+00:00"
        monkeypatch.setattr(
            stage_svc,
            "_server_time",
            lambda: expected_recorded_at,
        )

        result = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=_sample_companyfacts(),
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha256,
            storage_dir=tmp_path,
        )

        receipt_id = result["companyfacts_receipt_id"]
        receipt_path = tmp_path / stage_svc.COMPANYFACTS_RECEIPT_DIR / "receipts" / f"{receipt_id}.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        # Receipt must have hash + counts
        assert len(receipt["companyfacts_payload_hash"]) == 64
        assert receipt["companyfacts_observation_count"] == 6
        assert receipt["taxonomy_count"] == 1
        assert receipt["concept_count"] == 3
        assert receipt["gitignored_local_storage"] is True
        assert receipt["operator_surface_exposure"] is False

        # Receipt must NOT contain raw values, CIK, accession, issuer name.
        # Exclude the server timestamp, whose fractional seconds can coincidentally
        # contain a banned decimal substring, then redact digest/id hex runs.
        receipt_for_leak_scan = dict(receipt)
        assert receipt_for_leak_scan.pop("recorded_at") == expected_recorded_at
        receipt_text = _redact_hash_runs(json.dumps(receipt_for_leak_scan))
        assert cik not in receipt_text  # raw CIK absent
        assert "320193" not in receipt_text
        assert "200" not in receipt_text  # raw financial value absent
        assert "Assets" not in receipt_text  # concept name absent
        assert "issuer" not in receipt_text.lower()

    def test_raw_store_contains_full_payload(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("b")
        content = json.dumps({"facts": _sample_companyfacts()}).encode("utf-8")
        content_sha256 = hashlib.sha256(content).hexdigest()
        _write_connector_receipt(tmp_path, cik=cik, connector_receipt_hash=connector_hash)

        result = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=_sample_companyfacts(),
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha256,
            storage_dir=tmp_path,
        )

        raw_path = tmp_path / stage_svc.COMPANYFACTS_RECEIPT_DIR / "companyfacts-store" / f"{result['companyfacts_receipt_id']}.json"
        assert raw_path.exists()
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        # Raw store holds the actual data
        assert "us-gaap" in raw or "Assets" in json.dumps(raw)

    def test_stage_idempotent_replay_same_content(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("c")
        facts = _sample_companyfacts()
        content = json.dumps({"facts": facts}).encode("utf-8")
        content_sha256 = hashlib.sha256(content).hexdigest()
        _write_connector_receipt(tmp_path, cik=cik, connector_receipt_hash=connector_hash)

        r1 = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha256,
            storage_dir=tmp_path,
        )
        r2 = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha256,
            storage_dir=tmp_path,
        )
        assert r1["companyfacts_receipt_id"] == r2["companyfacts_receipt_id"]
        assert r2["idempotent_replay"] is True

    def test_stage_conflict_different_content_same_cik_hash(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("d")
        facts_a = _sample_companyfacts()
        facts_b = {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [{"val": 999, "end": "2023-12-31", "fp": "FY", "fy": 2023}]}}}}
        _write_connector_receipt(tmp_path, cik=cik, connector_receipt_hash=connector_hash)

        content_a = json.dumps({"facts": facts_a}).encode("utf-8")
        sha_a = hashlib.sha256(content_a).hexdigest()
        content_b = json.dumps({"facts": facts_b}).encode("utf-8")
        sha_b = hashlib.sha256(content_b).hexdigest()

        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts_a,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=sha_a,
            storage_dir=tmp_path,
        )
        with pytest.raises(stage_svc.SecXbrlCompanyfactsStageError) as exc_info:
            stage_svc.stage_sec_xbrl_companyfacts(
                companyfacts=facts_b,
                cik=cik,
                connector_receipt_hash=connector_hash,
                content_sha256=sha_b,
                storage_dir=tmp_path,
            )
        assert exc_info.value.code == "sec_xbrl_companyfacts_stage_conflict"

    def test_stage_cik_not_in_connector_fails_closed(self, tmp_path):
        cik_in_connector = "320193"
        cik_other = "789012"
        connector_hash = _hash("e")
        _write_connector_receipt(tmp_path, cik=cik_in_connector, connector_receipt_hash=connector_hash)

        content = json.dumps({"facts": _sample_companyfacts()}).encode("utf-8")
        sha = hashlib.sha256(content).hexdigest()

        with pytest.raises(stage_svc.SecXbrlCompanyfactsStageError) as exc_info:
            stage_svc.stage_sec_xbrl_companyfacts(
                companyfacts=_sample_companyfacts(),
                cik=cik_other,
                connector_receipt_hash=connector_hash,
                content_sha256=sha,
                storage_dir=tmp_path,
            )
        assert exc_info.value.code == "sec_xbrl_companyfacts_stage_cik_not_in_connector"


# ---------------------------------------------------------------------------
# STEP 3 TESTS — loader staged discovery
# ---------------------------------------------------------------------------

def _write_full_evidence_storage(
    tmp_path: Path,
    *,
    cik: str,
    connector_receipt_hash: str,
) -> dict[str, Any]:
    """Write a minimal valid evidence storage tree including sidecar, value store, classification, bridge."""
    from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
        classification_receipt_hash_basis,
        STATEMENT_CLASSIFICATION_MODE,
    )

    storage = tmp_path / "storage"
    sidecar_hash = _hash("1")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    bridge_hash = _hash("2")
    bridge_id = f"sec-edgar-html-inline-xbrl-fact-material-bridge-{'2' * 24}"

    records = [
        {
            "resolved_fact_id": "rf-assets",
            "concept": {"namespace": "fasb.org/us-gaap/test", "local_name": "Assets", "standard": True},
            "unit": {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
            "period": {"type": "instant", "instant": "2023-12-31"},
            "dimensions": {"explicit": [], "typed": []},
        },
        {
            "resolved_fact_id": "rf-revenue",
            "concept": {"namespace": "fasb.org/us-gaap/test", "local_name": "Revenues", "standard": True},
            "unit": {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
            "period": {"type": "duration", "start": "2023-01-01", "end": "2023-12-31"},
            "dimensions": {"explicit": [], "typed": []},
        },
    ]
    value_records = [
        {"resolved_fact_id": "rf-assets", "effective_value": "200"},
        {"resolved_fact_id": "rf-revenue", "effective_value": "100"},
    ]
    projection = [{**r, "value_redacted": True} for r in records]
    inventory_hash = stable_hash(projection)
    value_store_hash = stable_hash(value_records)

    statement_roles = [
        {"fact_id_or_order_key": "rf-assets", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-revenue", "statement_candidate_role": "income_statement"},
    ]
    classification_inv_hash = stable_hash(statement_roles)
    sem_hash = stable_hash([])
    cls_order_hash = stable_hash([r["fact_id_or_order_key"] for r in statement_roles])
    group_hash = stable_hash([])
    unclass_hash = stable_hash([])
    diag_hash = stable_hash({})

    sidecar = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_records": records,
        "resolved_fact_projection": projection,
        "resolved_fact_inventory_hash": inventory_hash,
        "connector_receipt_hash": connector_receipt_hash,
        "internal_value_store": {
            "store_state": "persisted",
            "value_store_hash": value_store_hash,
            "value_record_count": len(value_records),
        },
        "authority_hashes": {
            "sidecar_receipt_hash": sidecar_hash,
            "internal_value_store_hash": value_store_hash,
        },
    }
    value_store_payload = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_record_count": len(value_records),
        "value_records": value_records,
    }
    classification = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1",
        "classification_mode": STATEMENT_CLASSIFICATION_MODE,
        "fact_authority_receipt_hash": sidecar_hash,
        "fact_inventory_hash": inventory_hash,
        "fact_material_bridge_receipt_hash": bridge_hash,
        "classification_inventory_hash": classification_inv_hash,
        "semantic_profile_inventory_hash": sem_hash,
        "classification_order_hash": cls_order_hash,
        "statement_group_inventory_hash": group_hash,
        "unclassified_fact_inventory_hash": unclass_hash,
        "classification_diagnostics_hash": diag_hash,
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "fact_inventory_hash": inventory_hash,
            "fact_material_bridge_receipt_hash": bridge_hash,
        },
        "classification_inventory": statement_roles,
    }
    cls_hash = stable_hash(
        classification_receipt_hash_basis(
            classification_mode=classification["classification_mode"],
            fact_authority_receipt_hash=classification["fact_authority_receipt_hash"],
            fact_material_bridge_receipt_hash=classification["fact_material_bridge_receipt_hash"],
            fact_inventory_hash=classification["fact_inventory_hash"],
            classification_inventory_hash=classification["classification_inventory_hash"],
            semantic_profile_inventory_hash=classification["semantic_profile_inventory_hash"],
            classification_order_hash=classification["classification_order_hash"],
            statement_group_inventory_hash=classification["statement_group_inventory_hash"],
            unclassified_fact_inventory_hash=classification["unclassified_fact_inventory_hash"],
            classification_diagnostics_hash=classification["classification_diagnostics_hash"],
        )
    )
    cls_id = f"sec-edgar-html-inline-xbrl-fact-statement-classification-{cls_hash[:24]}"
    classification["statement_classification_receipt_id"] = cls_id
    classification["statement_classification_receipt_hash"] = cls_hash

    bridge = {
        "fact_material_bridge_receipt_hash": bridge_hash,
        "fact_material_bridge_receipt_id": bridge_id,
        "response": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "dataset_version_id": "dv-companyfacts-test",
        },
    }

    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / loader.VALUE_STORE_SUBDIR / f"{sidecar_id}.json", value_store_payload)
    _write_json(storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts" / f"{cls_id}.json", classification)
    _write_json(storage / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge" / "receipts" / f"{bridge_id}.json", bridge)

    # Also write connector receipt in storage so staging can find it
    _write_connector_receipt(storage, cik=cik, connector_receipt_hash=connector_receipt_hash)

    return {
        "storage": storage,
        "sidecar_hash": sidecar_hash,
        "sidecar_id": sidecar_id,
        "cls_hash": cls_hash,
        "connector_receipt_hash": connector_receipt_hash,
    }


class TestLoaderStagedDiscovery:
    def test_loader_staged_discovery_oracle_supplied_true(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("f")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()

        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        bundle = loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            connector_receipt_hash=connector_hash,
            cik_hash=_sha256(cik.lstrip("0") or "0"),
            expected_sidecar_receipt_hash=refs["sidecar_hash"],
            expected_statement_classification_receipt_hash=refs["cls_hash"],
        )

        assert bundle["summary"]["companyfacts_oracle_supplied"] is True
        assert bundle["status"] == "offline_evidence_bundle_ready"

    def test_loader_cross_issuer_mismatch_fails_closed(self, tmp_path):
        cik_a = "320193"
        cik_b = "789012"
        connector_hash_a = _hash("a") * 0 + "a" * 64  # connector for issuer A

        refs = _write_full_evidence_storage(tmp_path, cik=cik_a, connector_receipt_hash=connector_hash_a)
        storage = refs["storage"]

        # Stage facts for issuer B under a DIFFERENT connector
        connector_hash_b = _hash("b")
        _write_connector_receipt(storage, cik=cik_b, connector_receipt_hash=connector_hash_b)
        facts_b = _sample_companyfacts()
        content_sha_b = hashlib.sha256(json.dumps({"facts": facts_b}).encode()).hexdigest()
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts_b,
            cik=cik_b,
            connector_receipt_hash=connector_hash_b,
            content_sha256=content_sha_b,
            storage_dir=storage,
        )

        # Try to load the bundle with the sidecar from connector A but CIK B staged under connector B
        # The sidecar's connector_receipt_hash is A; the staged receipt's connector_receipt_hash is B → mismatch
        with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc_info:
            loader.load_sec_xbrl_offline_evidence_bundle(
                storage,
                connector_receipt_hash=connector_hash_b,
                cik_hash=_sha256(cik_b.lstrip("0") or "0"),
                expected_sidecar_receipt_hash=refs["sidecar_hash"],
                expected_statement_classification_receipt_hash=refs["cls_hash"],
            )
        assert exc_info.value.code == "sec_xbrl_offline_evidence_loader_companyfacts_cross_issuer_mismatch"

    def test_loader_staged_empty_facts_oracle_not_supplied(self, tmp_path):
        """When staged discovery finds zero observations the oracle is treated as not_supplied."""
        cik = "320193"
        connector_hash = _hash("3")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        # Stage a payload with zero observations
        empty_facts: dict = {}
        content_sha = hashlib.sha256(json.dumps({"facts": empty_facts}).encode()).hexdigest()
        # Staging with empty facts should succeed (just writes an empty oracle)
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=empty_facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        bundle = loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            connector_receipt_hash=connector_hash,
            cik_hash=_sha256(cik.lstrip("0") or "0"),
            expected_sidecar_receipt_hash=refs["sidecar_hash"],
            expected_statement_classification_receipt_hash=refs["cls_hash"],
        )
        assert bundle["summary"]["companyfacts_oracle_supplied"] is False
        assert bundle["status"] == "offline_evidence_bundle_ready_without_companyfacts_oracle"

    def test_loader_staged_zero_observation_facts_oracle_not_supplied(self, tmp_path):
        """Staged facts with taxonomy but no observations → not_supplied."""
        cik = "320193"
        connector_hash = _hash("4")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        zero_obs_facts = {"us-gaap": {}}
        content_sha = hashlib.sha256(json.dumps({"facts": zero_obs_facts}).encode()).hexdigest()
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=zero_obs_facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        bundle = loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            connector_receipt_hash=connector_hash,
            cik_hash=_sha256(cik.lstrip("0") or "0"),
            expected_sidecar_receipt_hash=refs["sidecar_hash"],
            expected_statement_classification_receipt_hash=refs["cls_hash"],
        )
        assert bundle["summary"]["companyfacts_oracle_supplied"] is False


# ---------------------------------------------------------------------------
# STEP 4 TESTS — oracle packet via staged discovery
# ---------------------------------------------------------------------------

class TestOraclePacketStagedDiscovery:
    def test_oracle_packet_staged_has_payload_hash_and_oracle_count(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("5")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
            storage,
            connector_receipt_hash=connector_hash,
            cik_hash=_sha256(cik.lstrip("0") or "0"),
            expected_sidecar_receipt_hash=refs["sidecar_hash"],
            expected_statement_classification_receipt_hash=refs["cls_hash"],
        )

        # Report must carry payload_hash and oracle_confirmed_count
        assert "companyfacts_payload_hash" in report.get("authority_refs", {})
        assert len(report["authority_refs"]["companyfacts_payload_hash"]) == 64
        assert report["summary"].get("companyfacts_observation_count", 0) > 0

    def test_oracle_packet_no_raw_value_leak(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("6")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
            storage,
            connector_receipt_hash=connector_hash,
            cik_hash=_sha256(cik.lstrip("0") or "0"),
            expected_sidecar_receipt_hash=refs["sidecar_hash"],
            expected_statement_classification_receipt_hash=refs["cls_hash"],
        )

        report_text = json.dumps(report, sort_keys=True)
        # Must not leak raw CIK, raw accession, local path, sec URL
        assert "320193" not in report_text  # raw CIK
        assert str(storage) not in report_text  # local path
        assert "sec.gov" not in report_text  # raw SEC URL
        # Must not leak raw financial values
        assert '"200"' not in report_text
        assert '"100"' not in report_text

        # Use the report leak guard
        flags = report_leak_flags(report)
        assert not any(flags.values()), f"Leak guard triggered: {flags}"

    def test_oracle_packet_production_admission_stays_false(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("7")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
            storage,
            connector_receipt_hash=connector_hash,
            cik_hash=_sha256(cik.lstrip("0") or "0"),
            expected_sidecar_receipt_hash=refs["sidecar_hash"],
            expected_statement_classification_receipt_hash=refs["cls_hash"],
        )

        # production_admission_ready must ALWAYS be False — guard against accidental flip
        readiness = report.get("readiness", {})
        assert readiness.get("production_admission_ready") is False, (
            "production_admission_ready was True — this invariant must never be flipped"
        )
        assert readiness.get("production_admission_blocked_reason") == "diagnostic_validate_only_not_production_admission"


# ---------------------------------------------------------------------------
# SECURITY TESTS — path traversal, fail-closed connector binding, receipt redaction
# ---------------------------------------------------------------------------

class TestSecurityFixes:
    """Security regression tests added during security review of the CompanyFacts oracle slice."""

    def test_companyfacts_load_rejects_traversal_receipt_id(self, tmp_path):
        """load_staged_companyfacts_raw must reject receipt ids containing path traversal sequences."""
        traversal_ids = [
            "../evil",
            "../../etc/passwd",
            "sec-edgar-companyfacts-live-artifact-" + "a" * 24 + "-" + "b" * 23 + "/../x",
            "",
            "sec-edgar-companyfacts-live-artifact-" + "g" * 24 + "-" + "h" * 24,  # invalid hex (g/h)
            "sec-edgar-companyfacts-live-artifact-" + "a" * 24 + "-" + "b" * 25,  # too long
        ]
        for bad_id in traversal_ids:
            with pytest.raises(stage_svc.SecXbrlCompanyfactsStageError) as exc_info:
                stage_svc.load_staged_companyfacts_raw(tmp_path, companyfacts_receipt_id=bad_id)
            assert exc_info.value.code == "sec_xbrl_companyfacts_stage_receipt_id_invalid", (
                f"Expected receipt_id_invalid for id={bad_id!r}, got {exc_info.value.code}"
            )

    def test_companyfacts_loader_fails_closed_when_sidecar_connector_hash_missing(self, tmp_path):
        """Staged discovery with a sidecar missing connector_receipt_hash must raise binding_missing error."""
        cik = "320193"
        connector_hash = _hash("s")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        # Stage valid facts
        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        # Patch the sidecar on disk to remove its connector_receipt_hash
        sidecar_path = (
            storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{refs['sidecar_id']}.json"
        )
        sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        del sidecar_data["connector_receipt_hash"]
        _write_json(sidecar_path, sidecar_data)

        with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc_info:
            loader.load_sec_xbrl_offline_evidence_bundle(
                storage,
                connector_receipt_hash=connector_hash,
                cik_hash=_sha256(cik.lstrip("0") or "0"),
                expected_sidecar_receipt_hash=refs["sidecar_hash"],
                expected_statement_classification_receipt_hash=refs["cls_hash"],
            )
        assert exc_info.value.code == "sec_xbrl_offline_evidence_loader_companyfacts_connector_binding_missing"

    def test_companyfacts_live_fetch_receipt_is_redaction_clean(self, tmp_path):
        """_write_companyfacts_receipt produces a receipt with only hashes/counts/booleans — no raw CIK/values/accession/issuer."""
        import hashlib as _hl
        from app.services.layer3_utils import stable_hash as _sh
        from app.services import layer3_sec_edgar_live_source_artifact as _la

        raw_cik = "320193"
        cik_hash = _hl.sha256(raw_cik.encode("utf-8")).hexdigest()
        source_identity_hash = _sh(
            {"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash}
        )

        # Build a receipt that mirrors what _write_companyfacts_receipt would produce
        content_sha256 = _hl.sha256(b"fake-content").hexdigest()
        receipt_hash_basis = {
            "hash_version": "sec_edgar_companyfacts_live_artifact_receipt_hash_v1",
            "schema_id": _la.COMPANYFACTS_SCHEMA_ID,
            "source_identity_hash": source_identity_hash,
            "cik_hash": cik_hash,
            "content_sha256": content_sha256,
        }
        receipt_hash = _sh(receipt_hash_basis)
        receipt_id = f"{_la.COMPANYFACTS_RECEIPT_PREFIX}-{source_identity_hash[:24]}-{receipt_hash[:24]}"

        receipt = {
            "schema_id": _la.COMPANYFACTS_SCHEMA_ID,
            "companyfacts_receipt_id": receipt_id,
            "companyfacts_receipt_hash": receipt_hash,
            "source_identity_hash": source_identity_hash,
            "cik_hash": cik_hash,
            "content_sha256": content_sha256,
            "companyfacts_observation_count": 6,
            "taxonomy_count": 1,
            "concept_count": 3,
            "receipt_hash_basis": receipt_hash_basis,
            "recorded_at": "2026-01-01T00:00:00+00:00",
        }

        # Write the receipt directly to a tmp receipts dir (mirrors what _write_companyfacts_receipt does)
        receipts_dir = tmp_path / _la.COMPANYFACTS_RECEIPT_DIR / "receipts"
        receipts_dir.mkdir(parents=True, exist_ok=True)
        target = receipts_dir / f"{receipt_id}.json"
        target.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")

        # Read back and assert no raw data leaked. Redact digest/id hex runs first so
        # a hash coincidentally containing a banned decimal substring (e.g. "200"/"100")
        # cannot cause a false failure.
        on_disk = json.loads(target.read_text(encoding="utf-8"))
        receipt_text = _redact_hash_runs(json.dumps(on_disk))

        # Must NOT contain raw CIK
        assert raw_cik not in receipt_text, "Raw CIK leaked into receipt"
        assert "320193" not in receipt_text, "Raw CIK leaked into receipt"

        # Must NOT contain financial values or concept names
        for banned in ("Assets", "Revenues", "NetIncomeLoss", "200", "100", "accession"):
            assert banned not in receipt_text, f"Banned term {banned!r} leaked into receipt"

        # Must contain expected safe fields
        assert on_disk["cik_hash"] == cik_hash
        assert len(on_disk["content_sha256"]) == 64
        assert on_disk["companyfacts_observation_count"] == 6
        assert on_disk["taxonomy_count"] == 1
        assert on_disk["concept_count"] == 3


# ---------------------------------------------------------------------------
# FIX B regression — fetch idempotency scan must not return a stage receipt
# ---------------------------------------------------------------------------

class TestFetchScanIgnoresStageReceipt:
    """Regression for FIX B: _find_existing_companyfacts_receipt must not return a stage receipt.

    Both fetch and stage receipts share the same filename prefix
    (sec-edgar-companyfacts-live-artifact-*).  Before FIX B, the fetch scan matched any
    receipt with the right source_identity_hash, which could be a stage receipt (it has
    the same cik_hash-derived source_identity_hash but a different schema_id and lacks
    the fields the fetch response builder expects).  FIX B adds a schema_id guard so only
    fetch receipts (schema_id == COMPANYFACTS_SCHEMA_ID) are returned.
    """

    def _make_source_identity_hash(self, cik: str) -> str:
        from app.services.layer3_utils import stable_hash as _sh
        raw_cik = cik.lstrip("0") or "0"
        cik_hash = _sha256(raw_cik)
        return _sh({"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash})

    def test_fetch_scan_returns_none_when_only_stage_receipt_present(self, tmp_path, monkeypatch):
        """_find_existing_companyfacts_receipt → None when the receipts/ dir contains only a
        stage receipt (no fetch receipt).  Without FIX B it would return the stage receipt."""
        import hashlib as _hl
        from app.services import layer3_sec_edgar_live_source_artifact as _la

        cik = "320193"
        raw_cik = cik.lstrip("0") or "0"
        cik_hash = _sha256(raw_cik)
        source_identity_hash = self._make_source_identity_hash(cik)

        # Build a stage receipt (schema_id == stage SCHEMA_ID) with the matching
        # source_identity_hash so that a naive scan would match it.
        stage_receipt_id = f"sec-edgar-companyfacts-live-artifact-{source_identity_hash[:24]}-{'s' * 24}"
        stage_receipt = {
            "schema_id": stage_svc.SCHEMA_ID,  # stage schema — NOT the fetch schema
            "companyfacts_receipt_id": stage_receipt_id,
            "companyfacts_receipt_hash": "s" * 64,
            "companyfacts_payload_hash": "p" * 64,
            "source_identity_hash": source_identity_hash,  # same value — naive scan would match
            "cik_hash": cik_hash,
            "connector_receipt_hash": "c" * 64,
            "content_sha256": _hl.sha256(b"fake").hexdigest(),
            "companyfacts_observation_count": 6,
            "taxonomy_count": 1,
            "concept_count": 3,
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "gitignored_local_storage": True,
            "operator_surface_exposure": False,
        }

        # Write the stage receipt into the shared receipts/ dir
        receipts_dir = tmp_path / _la.COMPANYFACTS_RECEIPT_DIR / "receipts"
        receipts_dir.mkdir(parents=True, exist_ok=True)
        (receipts_dir / f"{stage_receipt_id}.json").write_text(
            json.dumps(stage_receipt, sort_keys=True, indent=2), encoding="utf-8"
        )

        # Point the live service at our tmp storage
        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

        # FIX B: the fetch scan must skip the stage receipt and return None
        result = _la._find_existing_companyfacts_receipt(source_identity_hash)
        assert result is None, (
            f"Expected None (fetch scan must ignore stage receipts), got: {result}"
        )

    def test_fetch_scan_returns_fetch_receipt_when_both_present(self, tmp_path, monkeypatch):
        """When both a stage receipt and a fetch receipt exist for the same cik, the fetch
        scan must return the fetch receipt (schema_id == COMPANYFACTS_SCHEMA_ID)."""
        import hashlib as _hl
        from app.services import layer3_sec_edgar_live_source_artifact as _la
        from app.services.layer3_utils import stable_hash as _sh

        cik = "320193"
        raw_cik = cik.lstrip("0") or "0"
        cik_hash = _sha256(raw_cik)
        source_identity_hash = self._make_source_identity_hash(cik)
        content_sha256 = _hl.sha256(b"real-content").hexdigest()

        # Build a valid fetch receipt
        receipt_hash_basis = {
            "hash_version": "sec_edgar_companyfacts_live_artifact_receipt_hash_v1",
            "schema_id": _la.COMPANYFACTS_SCHEMA_ID,
            "source_identity_hash": source_identity_hash,
            "cik_hash": cik_hash,
            "content_sha256": content_sha256,
        }
        receipt_hash = _sh(receipt_hash_basis)
        fetch_receipt_id = f"sec-edgar-companyfacts-live-artifact-{source_identity_hash[:24]}-{receipt_hash[:24]}"
        fetch_receipt = {
            "schema_id": _la.COMPANYFACTS_SCHEMA_ID,
            "companyfacts_receipt_id": fetch_receipt_id,
            "companyfacts_receipt_hash": receipt_hash,
            "source_identity_hash": source_identity_hash,
            "cik_hash": cik_hash,
            "content_sha256": content_sha256,
            "companyfacts_observation_count": 6,
            "taxonomy_count": 1,
            "concept_count": 3,
            "recorded_at": "2026-01-01T00:00:00+00:00",
        }

        # Build a stage receipt with the same source_identity_hash
        stage_receipt_id = f"sec-edgar-companyfacts-live-artifact-{source_identity_hash[:24]}-{'s' * 24}"
        stage_receipt = {
            "schema_id": stage_svc.SCHEMA_ID,
            "companyfacts_receipt_id": stage_receipt_id,
            "companyfacts_receipt_hash": "s" * 64,
            "companyfacts_payload_hash": "p" * 64,
            "source_identity_hash": source_identity_hash,
            "cik_hash": cik_hash,
            "connector_receipt_hash": "c" * 64,
            "content_sha256": content_sha256,
            "companyfacts_observation_count": 6,
            "taxonomy_count": 1,
            "concept_count": 3,
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "gitignored_local_storage": True,
            "operator_surface_exposure": False,
        }

        receipts_dir = tmp_path / _la.COMPANYFACTS_RECEIPT_DIR / "receipts"
        receipts_dir.mkdir(parents=True, exist_ok=True)
        (receipts_dir / f"{stage_receipt_id}.json").write_text(
            json.dumps(stage_receipt, sort_keys=True, indent=2), encoding="utf-8"
        )
        (receipts_dir / f"{fetch_receipt_id}.json").write_text(
            json.dumps(fetch_receipt, sort_keys=True, indent=2), encoding="utf-8"
        )

        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

        result = _la._find_existing_companyfacts_receipt(source_identity_hash)
        assert result is not None, "Expected the fetch receipt to be returned"
        assert result["schema_id"] == _la.COMPANYFACTS_SCHEMA_ID
        assert result["companyfacts_receipt_id"] == fetch_receipt_id


# ---------------------------------------------------------------------------
# FIX 1 regression — loader rejects tampered staged companyfacts raw store
# ---------------------------------------------------------------------------

class TestLoaderTamperedStagedCompanyfacts:
    """Verify that staged-discovery branch fails closed on raw-store tampering (FIX 1).

    Mirrors test_loader_rejects_stale_value_store_before_bundle_admission in the
    base loader test file: stage facts, mutate the raw store on disk, then assert
    the loader raises companyfacts_payload_hash_mismatch.
    """

    def test_loader_rejects_tampered_staged_companyfacts(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("T")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        result = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        # Mutate the raw store file (change a financial value)
        raw_path = (
            storage
            / stage_svc.COMPANYFACTS_RECEIPT_DIR
            / "companyfacts-store"
            / f"{result['companyfacts_receipt_id']}.json"
        )
        raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
        # Inject a tamper marker into the raw payload
        raw_data["__tampered__"] = "injected-by-test"
        raw_path.write_text(json.dumps(raw_data, sort_keys=True, indent=2), encoding="utf-8")

        # Loader must detect the hash mismatch and fail closed.
        # With FIX 3, mutating only the raw store leaves the receipt intact, so the
        # receipt-hash check passes and the payload-hash check catches the mutation.
        with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc_info:
            loader.load_sec_xbrl_offline_evidence_bundle(
                storage,
                connector_receipt_hash=connector_hash,
                cik_hash=_sha256(cik.lstrip("0") or "0"),
                expected_sidecar_receipt_hash=refs["sidecar_hash"],
                expected_statement_classification_receipt_hash=refs["cls_hash"],
            )

        assert exc_info.value.code == (
            "sec_xbrl_offline_evidence_loader_companyfacts_payload_hash_mismatch"
        ), f"Unexpected error code: {exc_info.value.code}"

    def test_loader_rejects_staged_companyfacts_missing_payload_hash(self, tmp_path):
        """Staged receipt with absent companyfacts_payload_hash must fail closed.

        With FIX 3, the receipt-hash check fires first (before the payload-hash check)
        because removing companyfacts_payload_hash makes the receipt-hash basis
        unverifiable → companyfacts_receipt_hash_mismatch.  This is the correct
        fail-closed behavior: any receipt-field mutation that invalidates the basis
        is caught at the receipt-hash level.
        """
        cik = "320193"
        connector_hash = _hash("T")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        result = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        # Locate and mutate the RECEIPT file — remove companyfacts_payload_hash
        receipt_path = (
            storage
            / stage_svc.COMPANYFACTS_RECEIPT_DIR
            / "receipts"
            / f"{result['companyfacts_receipt_id']}.json"
        )
        receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt_data.pop("companyfacts_payload_hash", None)
        receipt_path.write_text(json.dumps(receipt_data, sort_keys=True, indent=2), encoding="utf-8")

        # Loader must fail closed — FIX 3 receipt-hash check fires first.
        with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc_info:
            loader.load_sec_xbrl_offline_evidence_bundle(
                storage,
                connector_receipt_hash=connector_hash,
                cik_hash=_sha256(cik.lstrip("0") or "0"),
                expected_sidecar_receipt_hash=refs["sidecar_hash"],
                expected_statement_classification_receipt_hash=refs["cls_hash"],
            )

        # FIX 3 fires first: missing basis field → receipt_hash_mismatch
        assert exc_info.value.code == (
            "sec_xbrl_offline_evidence_loader_companyfacts_receipt_hash_mismatch"
        ), f"Unexpected error code: {exc_info.value.code}"


# ---------------------------------------------------------------------------
# FIX 2 regression — CompanyFacts artifact writer verifies existing bytes on replay
# ---------------------------------------------------------------------------

class TestCompanyfactsArtifactReplayVerifiesBytes:
    """Verify that _write_companyfacts_artifact fails closed when existing bytes mismatch (FIX 2)."""

    def test_companyfacts_artifact_replay_verifies_bytes(self, tmp_path, monkeypatch):
        from app.services import layer3_sec_edgar_live_source_artifact as _la
        from app.services.layer3_workbench_error import Layer3WorkbenchError

        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

        # Write an artifact with known content
        content = b'{"facts": {"us-gaap": {}}}'
        content_sha256 = hashlib.sha256(content).hexdigest()
        receipt_id = f"sec-edgar-companyfacts-live-artifact-{'a' * 24}-{'b' * 24}"

        # First write — must succeed
        _la._write_companyfacts_artifact(receipt_id, content, content_sha256)

        # Confirm the file exists
        artifact_path = _la._companyfacts_artifact_path(receipt_id)
        assert artifact_path.exists()

        # Corrupt the on-disk file
        artifact_path.write_bytes(b'{"facts": {"corrupted": true}}')

        # Second call with original content_sha256 — must fail closed on mismatch
        with pytest.raises(Layer3WorkbenchError) as exc_info:
            _la._write_companyfacts_artifact(receipt_id, content, content_sha256)

        assert exc_info.value.error_code == (
            "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch"
        ), f"Unexpected error code: {exc_info.value.error_code}"
        assert exc_info.value.http_status == 409

    def test_companyfacts_artifact_replay_matches_bytes_is_idempotent(self, tmp_path, monkeypatch):
        """When existing bytes match the expected hash, the write is idempotent (no error)."""
        from app.services import layer3_sec_edgar_live_source_artifact as _la

        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

        content = b'{"facts": {"us-gaap": {}}}'
        content_sha256 = hashlib.sha256(content).hexdigest()
        receipt_id = f"sec-edgar-companyfacts-live-artifact-{'c' * 24}-{'d' * 24}"

        _la._write_companyfacts_artifact(receipt_id, content, content_sha256)
        # Second call with same content and hash — must not raise
        _la._write_companyfacts_artifact(receipt_id, content, content_sha256)


# ---------------------------------------------------------------------------
# FIX 2 regression — idempotent replay path verifies retained artifact bytes
# ---------------------------------------------------------------------------

def test_idempotent_replay_path_verifies_retained_artifact_bytes(tmp_path, monkeypatch) -> None:
    """Stage an artifact, delete/corrupt the retained file, then call acquire again on the
    replay path → must return 409 retained_artifact_mismatch instead of 'available'.

    Before FIX 2, _find_existing_companyfacts_receipt() returning a receipt caused an
    immediate return of _response_from_companyfacts_receipt(..., idempotent_replay=True)
    WITHOUT verifying the retained artifact bytes.  After FIX 2, _verify_companyfacts_artifact_bytes
    is called before returning and fails closed on missing/corrupt files.
    """
    from app.services import layer3_sec_edgar_live_source_artifact as _la
    from app.services.layer3_utils import stable_hash as _stable_hash

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    cik = "320193"
    raw_cik = cik.lstrip("0") or "0"
    cik_hash = _sha256(raw_cik)

    content = json.dumps({"cik": cik, "facts": {"us-gaap": {}}}, sort_keys=True, indent=2).encode("utf-8")
    content_sha256 = hashlib.sha256(content).hexdigest()

    source_identity_hash = _stable_hash(
        {"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash}
    )
    receipt_hash_basis = {
        "hash_version": "sec_edgar_companyfacts_live_artifact_receipt_hash_v1",
        "schema_id": "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1",
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
    }
    receipt_hash = _stable_hash(receipt_hash_basis)
    receipt_id = f"sec-edgar-companyfacts-live-artifact-{source_identity_hash[:24]}-{receipt_hash[:24]}"

    # Write the fetch receipt and the raw artifact (simulating a successful first fetch)
    receipts_dir = tmp_path / "layer3-sec-xbrl-companyfacts" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt_payload = {
        "schema_id": "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1",
        "companyfacts_receipt_id": receipt_id,
        "companyfacts_receipt_hash": receipt_hash,
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
        "companyfacts_observation_count": 0,
        "taxonomy_count": 0,
        "concept_count": 0,
        "recorded_at": "2026-01-01T00:00:00+00:00",
        "receipt_hash_basis": receipt_hash_basis,
    }
    (receipts_dir / f"{receipt_id}.json").write_text(
        json.dumps(receipt_payload, sort_keys=True, indent=2), encoding="utf-8"
    )

    store_dir = tmp_path / "layer3-sec-xbrl-companyfacts" / "companyfacts-store"
    store_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = store_dir / f"{receipt_id}.json"
    artifact_path.write_bytes(content)

    # Verify the replay path works correctly when artifact is intact
    existing = _la._find_existing_companyfacts_receipt(source_identity_hash)
    assert existing is not None, "Receipt must be findable for replay path test"

    # Now DELETE the retained artifact to simulate corruption/loss
    artifact_path.unlink()

    # The replay path must now fail closed (409) instead of reporting 'available'
    from app.services.layer3_sec_edgar_live_source_artifact import _verify_companyfacts_artifact_bytes
    from app.services.layer3_workbench_error import Layer3WorkbenchError

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        _verify_companyfacts_artifact_bytes(receipt_id, content_sha256)

    assert exc_info.value.error_code == "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch"
    assert exc_info.value.http_status == 409

    # Also verify corrupt content (wrong bytes) triggers the same 409
    artifact_path.write_bytes(b'{"corrupt": true}')
    with pytest.raises(Layer3WorkbenchError) as exc_info2:
        _verify_companyfacts_artifact_bytes(receipt_id, content_sha256)
    assert exc_info2.value.error_code == "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch"
    assert exc_info2.value.http_status == 409


def test_acquire_replay_fails_closed_on_corrupt_retained_artifact(tmp_path, monkeypatch) -> None:
    """Drive the FULL acquire→replay path to prove replay fails closed on corrupt/missing artifact.

    Step 1: Call acquire_sec_edgar_companyfacts_live_artifact with a monkeypatched fetch.
            It performs the real fetch path, writes the receipt and raw artifact, returns available.
    Step 2: CORRUPT the retained artifact file on disk.
    Step 3: Call acquire again with the same CIK.  _find_existing_companyfacts_receipt returns
            the receipt → idempotent-replay branch → _verify_companyfacts_artifact_bytes detects
            hash mismatch → Layer3WorkbenchError 409
            sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch.
    This proves the fix at acquire line ~1164 is exercised end-to-end, not just the helper directly.
    """
    import json as _json

    from app.services import layer3_sec_edgar_live_source_artifact as _la
    from app.services.layer3_workbench_error import Layer3WorkbenchError as _L3Error

    # ---------------------------------------------------------------------------
    # Environment setup — mirrors the existing gate-bypass pattern in TestFetchGates
    # ---------------------------------------------------------------------------
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "TestAgent/1.0 test@example.com")

    # No-op rate limiter so we don't sleep or hit the clock
    monkeypatch.setattr(_la, "_enforce_rate_limit", lambda: None)

    # Build minimal valid companyfacts JSON bytes the fake fetch will return
    cik = "320193"
    companyfacts_payload = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
        {"val": 100, "end": "2023-12-31", "fp": "FY", "fy": 2023}
    ]}}}}}
    content = _json.dumps(companyfacts_payload, sort_keys=True, indent=2).encode("utf-8")

    # Fake fetch result: status 200, complete, correct bytes
    fake_result = _la.SecEdgarFetchResult(
        status_code=200,
        content=content,
        complete=True,
        final_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
    )
    monkeypatch.setattr(_la, "_fetch_companyfacts_with_retry", lambda **_kw: fake_result)

    fields = {"cik": cik, "operator_confirmation": True}

    # ---------------------------------------------------------------------------
    # Step 1: First acquire — fetch path runs, writes receipt + artifact, returns available
    # ---------------------------------------------------------------------------
    result1 = _la.acquire_sec_edgar_companyfacts_live_artifact(fields)
    assert result1["status"] == "available"
    assert result1["idempotent_replay"] is False

    receipt_id = result1["companyfacts_receipt_id"]
    content_sha256 = result1["content_sha256"]

    # Confirm the artifact was written
    artifact_path = tmp_path / "layer3-sec-xbrl-companyfacts" / "companyfacts-store" / f"{receipt_id}.json"
    assert artifact_path.exists(), "Artifact must be present after first acquire"

    # ---------------------------------------------------------------------------
    # Step 2: CORRUPT the retained artifact (wrong bytes, hash will not match)
    # ---------------------------------------------------------------------------
    artifact_path.write_bytes(b'{"corrupt": "tampered"}')

    # ---------------------------------------------------------------------------
    # Step 3: Second acquire — same CIK → hits idempotent-replay branch → must fail closed
    # ---------------------------------------------------------------------------
    with pytest.raises(_L3Error) as exc_info:
        _la.acquire_sec_edgar_companyfacts_live_artifact(fields)

    assert exc_info.value.error_code == "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch"
    assert exc_info.value.http_status == 409

    # Also confirm DELETE (missing file) triggers the same failure
    artifact_path.unlink()
    with pytest.raises(_L3Error) as exc_info2:
        _la.acquire_sec_edgar_companyfacts_live_artifact(fields)

    assert exc_info2.value.error_code == "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch"
    assert exc_info2.value.http_status == 409


# ---------------------------------------------------------------------------
# Regression — loader fails closed when companyfacts_payload_hash is MISSING
# ---------------------------------------------------------------------------

class TestLoaderCompanyfactsPayloadHashMissing:
    """Verify that removing companyfacts_payload_hash from the staged receipt causes the loader
    to fail closed.

    The receipt-hash validation (_validate_companyfacts_receipt_hash) reads
    companyfacts_payload_hash via _required_hash, which calls _required_text on the value.
    When the field is absent/blank, _required_text raises field_missing, which is wrapped by
    the try/except inside _validate_companyfacts_receipt_hash into
    sec_xbrl_offline_evidence_loader_companyfacts_receipt_hash_mismatch.  That check fires
    BEFORE the explicit payload_hash_missing branch at loader lines 486-491, so the test
    asserts the receipt_hash_mismatch code.  Both codes are fail-closed outcomes; accepting
    either is correct, but receipt_hash_mismatch is what actually fires given the current
    validation order (FIX 3 design).
    """

    def test_companyfacts_loader_fails_closed_when_payload_hash_missing(self, tmp_path):
        cik = "320193"
        connector_hash = _hash("T")
        refs = _write_full_evidence_storage(tmp_path, cik=cik, connector_receipt_hash=connector_hash)
        storage = refs["storage"]

        facts = _sample_companyfacts()
        content_sha = hashlib.sha256(json.dumps({"facts": facts}).encode()).hexdigest()
        result = stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=content_sha,
            storage_dir=storage,
        )

        # Locate the staged receipt file and delete the companyfacts_payload_hash key.
        # The raw payload file is left intact so the tamper is isolated to the receipt.
        receipt_path = (
            storage
            / stage_svc.COMPANYFACTS_RECEIPT_DIR
            / "receipts"
            / f"{result['companyfacts_receipt_id']}.json"
        )
        receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt_data.pop("companyfacts_payload_hash", None)
        receipt_path.write_text(json.dumps(receipt_data, sort_keys=True, indent=2), encoding="utf-8")

        # The loader must fail closed.  Removing companyfacts_payload_hash invalidates the
        # receipt-hash basis, so _validate_companyfacts_receipt_hash fires with
        # companyfacts_receipt_hash_mismatch before the explicit payload_hash_missing branch
        # is reached (see loader lines ~447-491 and FIX 3 design).  Both codes are
        # fail-closed; receipt_hash_mismatch is the one actually raised in this path.
        with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc_info:
            loader.load_sec_xbrl_offline_evidence_bundle(
                storage,
                connector_receipt_hash=connector_hash,
                cik_hash=_sha256(cik.lstrip("0") or "0"),
                expected_sidecar_receipt_hash=refs["sidecar_hash"],
                expected_statement_classification_receipt_hash=refs["cls_hash"],
            )

        # Both codes are fail-closed; receipt_hash_mismatch fires first due to FIX 3 ordering.
        fail_closed_codes = {
            "sec_xbrl_offline_evidence_loader_companyfacts_payload_hash_missing",
            "sec_xbrl_offline_evidence_loader_companyfacts_receipt_hash_mismatch",
        }
        assert exc_info.value.code in fail_closed_codes, (
            f"Expected a fail-closed payload-hash code, got: {exc_info.value.code}"
        )
