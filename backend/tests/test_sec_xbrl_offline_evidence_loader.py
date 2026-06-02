from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import L3SecXbrlOperatorReviewWorkflow, L3SecXbrlProjectionSet
from app.services import (
    layer3_sec_xbrl_e2e_offline_orchestrator as orchestrator,
    layer3_sec_xbrl_offline_companyfacts_oracle_packet as oracle_packet,
    layer3_sec_xbrl_offline_evidence_loader as loader,
)
from app.services.layer3_utils import json_clone, stable_hash


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_loader_builds_bundle_that_opens_redacted_review_workflow(tmp_path, db_session) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)

    bundle = loader.load_sec_xbrl_offline_evidence_bundle(
        storage,
        companyfacts_path=companyfacts_path,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )
    assert bundle["status"] == "offline_evidence_bundle_ready"
    assert bundle["summary"]["companyfacts_oracle_supplied"] is True

    response = orchestrator.open_redacted_operator_review_from_offline_evidence(
        db_session,
        client_request_id="offline-loader-to-review",
        evidence=bundle["evidence"],
        period_limit=2,
    )

    assert response["status"] == "review_ready"
    assert response["controls"]["source_acquisition_performed"] is False
    assert response["controls"]["arelle_invoked"] is False
    assert response["controls"]["value_reveal_performed"] is False
    assert db_session.query(L3SecXbrlProjectionSet).count() == 1
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1


def test_loader_report_is_redacted_and_blocks_production_without_companyfacts(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=False)

    report = loader.inspect_sec_xbrl_offline_evidence_storage(
        storage,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == "offline_evidence_bundle_ready_without_companyfacts_oracle"
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["readiness"]["operator_review_creation_blocked_reason"] == "companyfacts_oracle_not_supplied"
    assert report["readiness"]["production_admission_ready"] is False
    assert report["readiness"]["production_admission_blocked_reason"] == "companyfacts_oracle_not_supplied"
    assert report["paths_redacted"] is True
    assert str(storage) not in text
    assert "rf-revenue-fy" not in text
    assert "rf-assets-fy" not in text


def test_loader_rejects_stale_value_store_before_bundle_admission(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    value_store_path = (
        storage
        / loader.SIDECAR_RECEIPT_DIR
        / loader.VALUE_STORE_SUBDIR
        / f"{refs['sidecar_receipt_id']}.json"
    )
    payload = json.loads(value_store_path.read_text(encoding="utf-8"))
    payload["value_records"][0]["effective_value"] = "999"
    value_store_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc:
        loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
            expected_statement_classification_receipt_hash=refs["classification_hash"],
        )

    assert exc.value.code == "sec_xbrl_offline_evidence_loader_value_store_hash_mismatch"


def test_loader_requires_expected_hash_when_sidecar_candidates_are_ambiguous(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    receipt_dir = storage / loader.SIDECAR_RECEIPT_DIR / "receipts"
    first = receipt_dir / f"{refs['sidecar_receipt_id']}.json"
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["sidecar_receipt_id"] = "sec-edgar-arelle-resolved-fact-authority-" + "c" * 24
    payload["sidecar_receipt_hash"] = _hash("c")
    (receipt_dir / f"{payload['sidecar_receipt_id']}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc:
        loader.load_sec_xbrl_offline_evidence_bundle(storage)

    assert exc.value.code == "sec_xbrl_offline_evidence_loader_sidecar_ambiguous"


def test_companyfacts_oracle_packet_reports_missing_oracle_without_overclaiming(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=False)

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        storage,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == "offline_companyfacts_oracle_packet_blocked"
    assert report["blocked_reasons"][0]["reason"] == "companyfacts_oracle_packet_missing"
    assert report["readiness"]["operator_review_creation_ready"] is False
    assert report["readiness"]["production_admission_ready"] is False
    assert report["controls"]["source_acquisition_performed"] is False
    assert report["controls"]["arelle_invoked"] is False
    assert report["paths_redacted"] is True
    assert str(storage) not in text
    assert "rf-revenue-fy" not in text


def test_companyfacts_oracle_packet_validates_supplied_oracle_without_production_claim(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        storage,
        companyfacts_path=companyfacts_path,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == "offline_companyfacts_oracle_packet_ready"
    assert report["blocked_reasons"] == []
    assert report["readiness"]["operator_review_creation_ready"] is True
    assert report["readiness"]["production_admission_ready"] is False
    assert report["readiness"]["production_admission_blocked_reason"] == "diagnostic_validate_only_not_production_admission"
    assert report["summary"]["companyfacts_observation_count"] == 6
    assert report["summary"]["projected_count"] > 0
    assert report["controls"]["db_persistence_performed"] is False
    assert "effective_value" not in text
    assert "rf-revenue-fy" not in text


def test_companyfacts_oracle_packet_preserves_base_storage_blocker_before_oracle_missing(tmp_path) -> None:
    missing_storage = tmp_path / "missing-storage"

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(missing_storage)

    assert report["status"] == "offline_companyfacts_oracle_packet_blocked"
    assert report["base_evidence_status"] == "offline_evidence_bundle_blocked"
    assert report["blocked_reasons"][0]["reason"] == "sec_xbrl_offline_evidence_loader_storage_missing"
    assert report["readiness"]["operator_review_creation_blocked_reason"] == "sec_xbrl_offline_evidence_loader_storage_missing"
    assert report["readiness"]["production_admission_blocked_reason"] == "sec_xbrl_offline_evidence_loader_storage_missing"


def test_companyfacts_oracle_packet_requires_oracle_confirmed_projection(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=False)
    empty_companyfacts = tmp_path / "empty-companyfacts.json"
    _write_json(empty_companyfacts, {"facts": {"us-gaap": {}}})

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        storage,
        companyfacts_path=empty_companyfacts,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )

    assert report["status"] == "offline_companyfacts_oracle_packet_blocked"
    assert report["blocked_reasons"][0]["reason"] == "companyfacts_oracle_packet_oracle_confirmation_missing"
    assert report["summary"]["companyfacts_observation_count"] == 0
    assert report["summary"]["oracle_confirmed_count"] == 0
    assert report["readiness"]["operator_review_creation_ready"] is False


def test_companyfacts_oracle_packet_preserves_projection_blocker_before_oracle_confirmation(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    assert companyfacts_path is not None
    sidecar_path = (
        storage
        / loader.SIDECAR_RECEIPT_DIR
        / "receipts"
        / f"{refs['sidecar_receipt_id']}.json"
    )
    classification_path = next(
        (storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts").glob("*.json")
    )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    for record in sidecar["resolved_fact_records"]:
        record["period"] = {"type": "forever"}
    sidecar["resolved_fact_projection"] = [_redacted_fact(record) for record in sidecar["resolved_fact_records"]]
    inventory_hash = stable_hash(sidecar["resolved_fact_projection"])
    sidecar["resolved_fact_inventory_hash"] = inventory_hash
    _write_json(sidecar_path, sidecar)

    classification = json.loads(classification_path.read_text(encoding="utf-8"))
    classification["authority_hashes"]["fact_inventory_hash"] = inventory_hash
    _write_json(classification_path, classification)

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        storage,
        companyfacts_path=companyfacts_path,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )

    assert report["status"] == "offline_companyfacts_oracle_packet_blocked"
    assert report["blocked_reasons"][0]["reason"] == "companyfacts_oracle_packet_projection_not_ready"
    assert report["summary"]["companyfacts_observation_count"] == 6
    assert report["summary"]["projection_status"] == "canonical_multi_period_projection_blocked"
    assert report["summary"]["projected_count"] == 0
    assert report["summary"]["oracle_confirmed_count"] == 0
    assert report["summary"]["projection_blocking_reasons"][0]["reason"] == (
        "canonical_multi_period_projection_periods_missing"
    )
    assert report["readiness"]["operator_review_creation_ready"] is False


def _write_storage(tmp_path: Path, *, include_companyfacts: bool) -> tuple[Path, Path | None, dict[str, str]]:
    storage = tmp_path / "storage"
    sidecar_hash = _hash("b")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    classification_hash = _hash("d")
    classification_id = f"sec-edgar-html-inline-xbrl-fact-statement-classification-{classification_hash[:24]}"
    sidecar_records = _sidecar_records()
    value_records = _value_records()
    value_store_hash = stable_hash(value_records)
    resolved_projection = [_redacted_fact(record) for record in sidecar_records]
    resolved_projection_hash = stable_hash(resolved_projection)

    sidecar = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_records": sidecar_records,
        "resolved_fact_projection": resolved_projection,
        "resolved_fact_inventory_hash": resolved_projection_hash,
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
    value_store = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_record_count": len(value_records),
        "value_records": value_records,
    }
    classification = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1",
        "statement_classification_receipt_id": classification_id,
        "statement_classification_receipt_hash": classification_hash,
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "fact_inventory_hash": resolved_projection_hash,
        },
        "classification_inventory": _statement_roles(),
    }
    bridge = {
        "fact_material_bridge_receipt_hash": _hash("e"),
        "fact_material_bridge_receipt_id": "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "e" * 24,
        "response": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "dataset_version_id": "dv-sec-ixbrl-facts-redacted",
        },
    }
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / loader.VALUE_STORE_SUBDIR / f"{sidecar_id}.json", value_store)
    _write_json(
        storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts" / f"{classification_id}.json",
        classification,
    )
    _write_json(
        storage
        / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
        / "receipts"
        / f"{bridge['fact_material_bridge_receipt_id']}.json",
        bridge,
    )
    companyfacts_path = tmp_path / "companyfacts.json"
    if include_companyfacts:
        _write_json(companyfacts_path, {"facts": _companyfacts()})
    return storage, companyfacts_path if include_companyfacts else None, {
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_receipt_id": sidecar_id,
        "classification_hash": classification_hash,
    }


def _sidecar_records() -> list[dict[str, Any]]:
    return [
        _record("rf-revenue-old", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "start-1", "end-1"),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", "", "end-1", instant=True),
        _record("rf-cashflow-old", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", "start-1", "end-1"),
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "start-2", "end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", "", "end-2", instant=True),
        _record("rf-cashflow-fy", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", "start-2", "end-2"),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", "", "end-2", instant=True),
    ]


def _value_records() -> list[dict[str, str]]:
    return [
        {"resolved_fact_id": "rf-revenue-old", "effective_value": "90"},
        {"resolved_fact_id": "rf-assets-old", "effective_value": "180"},
        {"resolved_fact_id": "rf-cashflow-old", "effective_value": "30"},
        {"resolved_fact_id": "rf-revenue-fy", "effective_value": "100"},
        {"resolved_fact_id": "rf-assets-fy", "effective_value": "200"},
        {"resolved_fact_id": "rf-cashflow-fy", "effective_value": "40"},
        {"resolved_fact_id": "rf-period-end", "effective_value": "end-2"},
    ]


def _statement_roles() -> list[dict[str, Any]]:
    return [
        {"fact_id_or_order_key": "rf-revenue-old", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-old", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-cashflow-old", "statement_candidate_role": "cash_flow_statement"},
        {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-cashflow-fy", "statement_candidate_role": "cash_flow_statement"},
    ]


def _companyfacts() -> dict[str, Any]:
    entries = [
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
        ("Assets", "180", "USD", "", "end-1", True),
        ("Assets", "200", "USD", "", "end-2", True),
        ("NetCashProvidedByUsedInOperatingActivities", "30", "USD", "start-1", "end-1", False),
        ("NetCashProvidedByUsedInOperatingActivities", "40", "USD", "start-2", "end-2", False),
    ]
    facts: dict[str, Any] = {"us-gaap": {}}
    for local_name, value, unit, start, end, instant in entries:
        fact = {"fp": "FY", "fy": "", "val": value, "end": end}
        if not instant:
            fact["start"] = start
        facts["us-gaap"].setdefault(local_name, {"units": {}})["units"].setdefault(unit, []).append(fact)
    return facts


def _record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    start: str,
    end: str,
    *,
    instant: bool = False,
) -> dict[str, Any]:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    return {
        "resolved_fact_id": fact_id,
        "concept": {"namespace": _namespace(taxonomy), "local_name": local_name, "standard": True},
        "unit": _unit(unit_name),
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _redacted_fact(record: dict[str, Any]) -> dict[str, Any]:
    value = json_clone(record)
    value["value_redacted"] = True
    return value


def _namespace(taxonomy: str) -> str:
    if taxonomy == "dei":
        return "xbrl.sec.gov/dei/test"
    return "fasb.org/us-gaap/test"


def _unit(unit_name: str) -> dict[str, Any]:
    if unit_name == "unitless":
        return {"measures": []}
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}


def _hash(char: str) -> str:
    return char * 64


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
