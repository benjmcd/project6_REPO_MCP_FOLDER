from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base
from app.models import L3SecXbrlOperatorReviewWorkflow, L3SecXbrlProjectionSet
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge as material_bridge,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification as classifier,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract as classification_contract,
    layer3_sec_xbrl_e2e_offline_orchestrator as orchestrator,
    layer3_sec_xbrl_offline_companyfacts_oracle_packet as oracle_packet,
    layer3_sec_xbrl_offline_evidence_loader as loader,
)
from app.services.layer3_utils import json_clone, stable_hash


NON_PRODUCTION_CONTROL_EXPECTATIONS = {
    "source_acquisition_performed": False,
    "arelle_invoked": False,
    "production_readiness_claimed": False,
    "api_route_enabled": False,
}


def _assert_non_production_controls(controls: dict[str, Any]) -> None:
    for key, expected in NON_PRODUCTION_CONTROL_EXPECTATIONS.items():
        assert controls[key] is expected


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
    _assert_non_production_controls(report["controls"])
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


def test_loader_binds_dataset_version_to_classification_bridge_hash(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    other_bridge = {
        "fact_material_bridge_receipt_hash": _hash("a"),
        "fact_material_bridge_receipt_id": "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "a" * 24,
        "response": {
            "arelle_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "dataset_version_id": "dv-wrong-bridge",
        },
    }
    _write_json(
        storage
        / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
        / "receipts"
        / f"{other_bridge['fact_material_bridge_receipt_id']}.json",
        other_bridge,
    )

    bundle = loader.load_sec_xbrl_offline_evidence_bundle(
        storage,
        companyfacts_path=companyfacts_path,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )

    assert bundle["evidence"]["dataset_version_id"] == "dv-sec-ixbrl-facts-redacted"


def test_loader_rejects_tampered_classification_bridge_hash_before_dataset_binding(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    classification_path = next((storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts").glob("*.json"))
    classification = json.loads(classification_path.read_text(encoding="utf-8"))
    classification["fact_material_bridge_receipt_hash"] = _hash("a")
    classification["authority_hashes"]["fact_material_bridge_receipt_hash"] = _hash("a")
    _write_json(classification_path, classification)

    with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc:
        loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
            expected_statement_classification_receipt_hash=refs["classification_hash"],
        )

    assert exc.value.code == "sec_xbrl_offline_evidence_loader_statement_classification_receipt_hash_mismatch"


def test_loader_rejects_mutable_authority_inventory_hash_before_role_admission(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    sidecar_path = (
        storage
        / loader.SIDECAR_RECEIPT_DIR
        / "receipts"
        / f"{refs['sidecar_receipt_id']}.json"
    )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["resolved_fact_projection"][0]["tamper_marker"] = "redacted-inventory-drift"
    tampered_inventory_hash = stable_hash(sidecar["resolved_fact_projection"])
    sidecar["resolved_fact_inventory_hash"] = tampered_inventory_hash
    _write_json(sidecar_path, sidecar)

    classification_path = next((storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts").glob("*.json"))
    classification = json.loads(classification_path.read_text(encoding="utf-8"))
    classification["authority_hashes"]["fact_inventory_hash"] = tampered_inventory_hash
    _write_json(classification_path, classification)

    with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc:
        loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
            expected_statement_classification_receipt_hash=refs["classification_hash"],
        )

    assert exc.value.code == "sec_xbrl_offline_evidence_loader_statement_classification_fact_inventory_hash_mismatch"


def test_loader_rejects_stale_statement_classification_inventory_hash(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    classification_path = next((storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts").glob("*.json"))
    classification = json.loads(classification_path.read_text(encoding="utf-8"))
    classification["classification_inventory"][0]["statement_candidate_role"] = "balance_sheet"
    _write_json(classification_path, classification)

    with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc:
        loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
            expected_statement_classification_receipt_hash=refs["classification_hash"],
        )

    assert exc.value.code == "sec_xbrl_offline_evidence_loader_statement_classification_inventory_hash_mismatch"


def test_loader_reports_malformed_value_count_as_blocked_report(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    sidecar_path = (
        storage
        / loader.SIDECAR_RECEIPT_DIR
        / "receipts"
        / f"{refs['sidecar_receipt_id']}.json"
    )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["internal_value_store"]["value_record_count"] = "not-a-number"
    _write_json(sidecar_path, sidecar)

    report = loader.inspect_sec_xbrl_offline_evidence_storage(
        storage,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )

    assert report["status"] == "offline_evidence_bundle_blocked"
    assert report["blocked_reasons"][0]["reason"] == "sec_xbrl_offline_evidence_loader_count_invalid"


def test_loader_rejects_sidecar_receipt_id_path_escape_before_value_store_read(tmp_path) -> None:
    storage, companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=True)
    sidecar_path = (
        storage
        / loader.SIDECAR_RECEIPT_DIR
        / "receipts"
        / f"{refs['sidecar_receipt_id']}.json"
    )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["sidecar_receipt_id"] = "../outside-value-store"
    _write_json(sidecar_path, sidecar)

    with pytest.raises(loader.SecXbrlOfflineEvidenceLoaderError) as exc:
        loader.load_sec_xbrl_offline_evidence_bundle(
            storage,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
            expected_statement_classification_receipt_hash=refs["classification_hash"],
        )

    assert exc.value.code == "sec_xbrl_offline_evidence_loader_receipt_id_invalid"


def test_loader_rejects_raw_dataset_version_text_before_readiness(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=False)
    bridge_path = storage / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge" / "receipts" / f"{refs['bridge_id']}.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge["response"]["dataset_version_id"] = "C:/Users/benny/raw-sec-xbrl"
    _write_json(bridge_path, bridge)

    report = loader.inspect_sec_xbrl_offline_evidence_storage(
        storage,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )

    assert report["status"] == "offline_evidence_bundle_blocked"
    assert report["blocked_reasons"][0]["reason"] == "sec_xbrl_offline_evidence_loader_raw_reference_not_admitted"


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
    _assert_non_production_controls(report["controls"])
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
    _assert_non_production_controls(report["controls"])
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


def test_companyfacts_oracle_packet_preserves_base_storage_blocker_details(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=False)
    classification_path = next((storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts").glob("*.json"))
    classification = json.loads(classification_path.read_text(encoding="utf-8"))
    classification.pop("fact_inventory_hash")
    _write_json(classification_path, classification)

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        storage,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=refs["classification_hash"],
    )

    assert report["status"] == "offline_companyfacts_oracle_packet_blocked"
    assert len(report["storage_marker"]) == 24
    assert report["blocked_reasons"][0]["reason"] == "sec_xbrl_offline_evidence_loader_field_missing"
    assert report["blocked_reasons"][0]["details"] == {"field": "fact_inventory_hash"}
    assert report["readiness"]["operator_review_creation_blocked_reason"] == (
        "sec_xbrl_offline_evidence_loader_field_missing"
    )
    assert report["readiness"]["production_admission_blocked_reason"] == (
        "sec_xbrl_offline_evidence_loader_field_missing"
    )


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
    classification["fact_inventory_hash"] = inventory_hash
    classification["authority_hashes"]["fact_inventory_hash"] = inventory_hash
    classification["statement_classification_receipt_hash"] = _classification_receipt_hash(classification)
    _write_json(classification_path, classification)

    report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        storage,
        companyfacts_path=companyfacts_path,
        expected_sidecar_receipt_hash=refs["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=classification["statement_classification_receipt_hash"],
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


def test_classification_contract_preserves_fizz_receipt_hash_anchor() -> None:
    basis = classification_contract.classification_receipt_hash_basis(
        classification_mode=classification_contract.STATEMENT_CLASSIFICATION_MODE,
        fact_authority_receipt_hash="16cdcfc6e5486ccfdb2991fac7f46a03f53d802d60841f2e0ff6c488cdf5bb9d",
        fact_material_bridge_receipt_hash="ad5d4612b97dd06099cde52368c123b851e9fe1fe7c19651338695a6913e488c",
        fact_inventory_hash="07028a77f5317b10e35305e0349d2a9c047f82b194e3d68821f157e8b6cb9174",
        classification_inventory_hash="38a067b8ba9da954125279221f83d641fdb7d5f95b7a2bf37626c400b9c5334b",
        semantic_profile_inventory_hash="909b91ae4e6684ae3d384be7768a9705e71bb92a8225fefa8b1b0a6402240092",
        classification_order_hash="a159654a9111579bcb7b7614b8dc4dbcbee090998e778d7d0f943ccf2bade55a",
        statement_group_inventory_hash="f9f1f0435171f9d7045c836dd4694bebcd45d12486ebcf12c2cd63f20fa07098",
        unclassified_fact_inventory_hash="df7880484351159cfc543788153298acb31c4ff2c2646517d2eb8c7badaa551c",
        classification_diagnostics_hash="986cba107555a8e023ba062597052d90226395f2ac34649d429442300830b68f",
    )

    assert tuple(basis) == classification_contract.CLASSIFICATION_RECEIPT_HASH_BASIS_KEYS
    assert stable_hash({"z": "last", "a": "first"}) == stable_hash({"a": "first", "z": "last"})
    assert stable_hash(basis) == "bd95ba6d396a7d645f11e8e0bc4f8e7ca5f6e12f2ec9f50a5f250f43ae938666"


def test_loader_and_generator_share_classification_receipt_hash_contract(tmp_path) -> None:
    storage, _companyfacts_path, refs = _write_storage(tmp_path, include_companyfacts=False)
    classification_path = next((storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts").glob("*.json"))
    classification = json.loads(classification_path.read_text(encoding="utf-8"))

    assert classifier.AUTHORITY_HASH_VERSION == classification_contract.STATEMENT_CLASSIFICATION_HASH_VERSION
    assert loader.STATEMENT_CLASSIFICATION_HASH_VERSION == classification_contract.STATEMENT_CLASSIFICATION_HASH_VERSION
    assert classifier.CLASSIFICATION_MODE == classification_contract.STATEMENT_CLASSIFICATION_MODE
    assert loader.STATEMENT_CLASSIFICATION_MODE == classification_contract.STATEMENT_CLASSIFICATION_MODE
    assert stable_hash(
        classification_contract.classification_receipt_hash_basis(
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
    ) == refs["classification_hash"]


def test_loader_accepts_real_generator_classification_receipt(tmp_path, monkeypatch) -> None:
    storage, sidecar, bridge = _write_generator_input_storage(tmp_path)
    monkeypatch.setattr(settings, "storage_dir", str(storage))

    response = classifier.classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates(
        {
            "client_request_id": "offline-loader-real-generator-contract",
            "classification_mode": classifier.CLASSIFICATION_MODE,
            "operator_decision": classifier.OPERATOR_DECISION,
            "fact_authority_receipt_id": sidecar["sidecar_receipt_id"],
            "fact_authority_receipt_hash": sidecar["sidecar_receipt_hash"],
            "fact_material_bridge_receipt_id": bridge["fact_material_bridge_receipt_id"],
            "fact_material_bridge_receipt_hash": bridge["fact_material_bridge_receipt_hash"],
            "expected_fact_inventory_hash": sidecar["resolved_fact_inventory_hash"],
            "expected_materialization_receipt_hash": bridge["response"]["materialization_receipt_hash"],
            "expected_dataset_version_hash": bridge["response"]["dataset_version_hash"],
            "expected_gate_b_decision_manifest_id": bridge["response"]["gate_b_decision_manifest_id"],
            "operator_confirmation": True,
        }
    )
    receipt_path = (
        storage
        / classifier.RECEIPT_DIR
        / "receipts"
        / f"{response['statement_classification_receipt_id']}.json"
    )
    persisted = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert response["fact_inventory_hash"] == sidecar["resolved_fact_inventory_hash"]
    assert persisted["fact_inventory_hash"] == persisted["authority_hashes"]["fact_inventory_hash"]
    assert persisted["fact_inventory_hash"] == sidecar["resolved_fact_inventory_hash"]

    bundle = loader.load_sec_xbrl_offline_evidence_bundle(
        storage,
        expected_sidecar_receipt_hash=sidecar["sidecar_receipt_hash"],
        expected_statement_classification_receipt_hash=response["statement_classification_receipt_hash"],
    )

    assert bundle["status"] == "offline_evidence_bundle_ready_without_companyfacts_oracle"
    assert bundle["authority_refs"]["statement_classification_receipt_hash"] == (
        response["statement_classification_receipt_hash"]
    )
    assert bundle["summary"]["statement_role_record_count"] == len(persisted["classification_inventory"])


def _write_generator_input_storage(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    storage = tmp_path / "storage"
    sidecar_id = "sec-edgar-arelle-resolved-fact-authority-" + "1" * 24
    sidecar_hash = _hash("1")
    bridge_id = "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "2" * 24
    bridge_hash = _hash("2")
    source_hashes = {
        "parser_receipt_hash": _hash("3"),
        "connector_receipt_hash": _hash("4"),
        "live_source_artifact_receipt_hash": _hash("5"),
        "source_artifact_receipt_hash": _hash("6"),
        "content_sha256": _hash("7"),
        "primary_document_hash": _hash("8"),
        "document_inventory_hash": _hash("9"),
        "content_order_hash": _hash("a"),
        "table_candidate_inventory_hash": _hash("b"),
        "inline_xbrl_marker_inventory_hash": _hash("c"),
        "diagnostics_hash": _hash("d"),
    }
    records = []
    for index, record in enumerate(_sidecar_records(), start=1):
        enriched = json_clone(record)
        concept = enriched["concept"]
        prefix = "dei" if "dei/" in str(concept.get("namespace") or "") else "us-gaap"
        concept["qname"] = f"{prefix}:{concept['local_name']}"
        enriched.update(
            {
                "source_order": index,
                "entry_document_index": 1,
                "context_id": f"context-{index}",
                "unit_id": f"unit-{index}",
                "decimals": "0",
                "source_artifact_receipt_hash": source_hashes["source_artifact_receipt_hash"],
                "primary_document_hash": source_hashes["primary_document_hash"],
                "value_hash": _hash(str(index)),
                "value_length": index,
                "table_candidate_anchor_hash": _hash("e"),
            }
        )
        records.append(enriched)
    projection = [_redacted_fact(record) for record in records]
    value_records = _value_records()
    value_store_hash = stable_hash(value_records)
    resolved_inventory_hash = stable_hash(projection)
    sidecar = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_count": len(records),
        "resolved_fact_records": records,
        "resolved_fact_projection": projection,
        "resolved_fact_inventory_hash": resolved_inventory_hash,
        "diagnostics_hash": source_hashes["diagnostics_hash"],
        "parser_receipt_id": "sec-edgar-html-inline-xbrl-parser-" + "3" * 24,
        **source_hashes,
        "internal_value_store": {
            "store_state": "persisted",
            "value_store_hash": value_store_hash,
            "value_record_count": len(value_records),
        },
        "authority_hashes": {
            "sidecar_receipt_hash": sidecar_hash,
            "resolved_fact_inventory_hash": resolved_inventory_hash,
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
    bridge = {
        "fact_material_bridge_receipt_hash": bridge_hash,
        "fact_material_bridge_receipt_id": bridge_id,
        "response": {
            "fact_material_bridge_receipt_hash": bridge_hash,
            "fact_authority_input_mode": material_bridge.ARELLE_FACT_AUTHORITY_INPUT_MODE,
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "dataset_version_hash": _hash("f"),
            "materialization_receipt_hash": _hash("0"),
            "gate_b_decision_manifest_id": "gate-b-redacted",
            "dataset_version_id": "dv-sec-ixbrl-facts-real-generator-test",
            "authority_hashes": {
                **source_hashes,
                "fact_inventory_hash": resolved_inventory_hash,
            },
        },
    }
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / loader.VALUE_STORE_SUBDIR / f"{sidecar_id}.json", value_store)
    _write_json(
        storage
        / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
        / "receipts"
        / f"{bridge_id}.json",
        bridge,
    )
    return storage, sidecar, bridge


def _write_storage(tmp_path: Path, *, include_companyfacts: bool) -> tuple[Path, Path | None, dict[str, str]]:
    storage = tmp_path / "storage"
    sidecar_hash = _hash("b")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    bridge_hash = _hash("e")
    bridge_id = "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "e" * 24
    sidecar_records = _sidecar_records()
    value_records = _value_records()
    value_store_hash = stable_hash(value_records)
    resolved_projection = [_redacted_fact(record) for record in sidecar_records]
    resolved_projection_hash = stable_hash(resolved_projection)
    statement_roles = _statement_roles()
    classification_inventory_hash = stable_hash(statement_roles)
    semantic_profile_inventory_hash = stable_hash([])
    classification_order_hash = stable_hash([item["fact_id_or_order_key"] for item in statement_roles])
    statement_group_inventory_hash = stable_hash([])
    unclassified_fact_inventory_hash = stable_hash([])
    classification_diagnostics_hash = stable_hash({})
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
        "classification_mode": "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1",
        "fact_authority_receipt_hash": sidecar_hash,
        "fact_inventory_hash": resolved_projection_hash,
        "fact_material_bridge_receipt_hash": bridge_hash,
        "classification_inventory_hash": classification_inventory_hash,
        "semantic_profile_inventory_hash": semantic_profile_inventory_hash,
        "classification_order_hash": classification_order_hash,
        "statement_group_inventory_hash": statement_group_inventory_hash,
        "unclassified_fact_inventory_hash": unclassified_fact_inventory_hash,
        "classification_diagnostics_hash": classification_diagnostics_hash,
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "fact_inventory_hash": resolved_projection_hash,
            "fact_material_bridge_receipt_hash": bridge_hash,
        },
        "classification_inventory": statement_roles,
    }
    classification_hash = _classification_receipt_hash(classification)
    classification_id = f"sec-edgar-html-inline-xbrl-fact-statement-classification-{classification_hash[:24]}"
    classification["statement_classification_receipt_id"] = classification_id
    classification["statement_classification_receipt_hash"] = classification_hash
    bridge = {
        "fact_material_bridge_receipt_hash": bridge_hash,
        "fact_material_bridge_receipt_id": bridge_id,
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
        "bridge_hash": bridge_hash,
        "bridge_id": bridge_id,
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


def _classification_receipt_hash(classification: dict[str, Any]) -> str:
    return stable_hash(
        classification_contract.classification_receipt_hash_basis(
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


def _hash(char: str) -> str:
    return char * 64


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# FIX 3 regression — loader validates companyfacts receipt hash before trusting it
# ---------------------------------------------------------------------------

def test_loader_staged_discovery_rejects_tampered_receipt_payload_hash(tmp_path) -> None:
    """Stage a companyfacts, then edit the staged receipt's companyfacts_payload_hash to match
    a tampered raw (without recomputing companyfacts_receipt_hash) → loader staged-discovery
    raises SecXbrlOfflineEvidenceLoaderError with code
    sec_xbrl_offline_evidence_loader_companyfacts_receipt_hash_mismatch.

    Before FIX 3 the loader trusted staged_receipt["companyfacts_payload_hash"] directly,
    so editing payload_hash + raw together bypassed integrity.  After FIX 3 the loader
    recomputes companyfacts_receipt_hash from the basis fields and requires it matches the
    declared hash — catching inconsistent/partial tampering.
    """
    import hashlib as _hashlib
    import json as _json
    from app.services.layer3_sec_xbrl_offline_companyfacts_stage import (
        stage_sec_xbrl_companyfacts,
        COMPANYFACTS_RECEIPT_DIR,
    )
    from app.services.layer3_sec_xbrl_offline_evidence_loader import (
        SecXbrlOfflineEvidenceLoaderError,
        _read_companyfacts,
    )
    from app.services.layer3_utils import stable_hash

    storage = tmp_path / "storage"

    # Write a connector receipt so stage can bind cik_hash
    cik = "320193"
    raw_cik = cik.lstrip("0") or "0"
    cik_hash_val = _hashlib.sha256(raw_cik.encode("utf-8")).hexdigest()
    connector_receipt_hash = "a" * 64
    connector_receipt = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "connector_receipt_id": f"sec-edgar-real-filing-connector-{'a' * 24}-{'a' * 24}",
        "connector_receipt_hash": connector_receipt_hash,
        "corpus_manifest": {
            "example_records": [{"example_id": "ex-1", "cik_hash": cik_hash_val, "form_type": "10-K"}]
        },
    }
    conn_dir = storage / "layer3-sec-edgar-real-filing-acquisition-connector" / "receipts"
    conn_dir.mkdir(parents=True, exist_ok=True)
    (conn_dir / f"{connector_receipt['connector_receipt_id']}.json").write_text(
        _json.dumps(connector_receipt, sort_keys=True, indent=2), encoding="utf-8"
    )

    # Stage a valid companyfacts
    facts = {"us-gaap": {"Assets": {"units": {"USD": [{"val": 200, "end": "2023-12-31", "fp": "FY", "fy": 2023}]}}}}
    content = _json.dumps(facts, sort_keys=True, indent=2).encode("utf-8")
    content_sha256 = _hashlib.sha256(content).hexdigest()

    result = stage_sec_xbrl_companyfacts(
        companyfacts=facts,
        cik=cik,
        connector_receipt_hash=connector_receipt_hash,
        content_sha256=content_sha256,
        storage_dir=storage,
    )
    receipt_id = result["companyfacts_receipt_id"]

    # Locate the staged receipt file on disk
    receipts_dir = storage / COMPANYFACTS_RECEIPT_DIR / "receipts"
    receipt_path = receipts_dir / f"{receipt_id}.json"
    assert receipt_path.exists(), "Staged receipt must have been written"

    staged = _json.loads(receipt_path.read_text(encoding="utf-8"))

    # Tamper: replace companyfacts_payload_hash with hash of a different payload
    #         WITHOUT recomputing companyfacts_receipt_hash.
    tampered_facts = {"us-gaap": {"Revenues": {"units": {"USD": [{"val": 999, "end": "2023-12-31", "fp": "FY", "fy": 2023}]}}}}
    tampered_payload_hash = stable_hash(tampered_facts)
    staged["companyfacts_payload_hash"] = tampered_payload_hash
    receipt_path.write_text(_json.dumps(staged, sort_keys=True, indent=2), encoding="utf-8")

    # Also write the tampered raw so payload_hash check would pass (if receipt_hash check were absent)
    raw_path = storage / COMPANYFACTS_RECEIPT_DIR / "companyfacts-store" / f"{receipt_id}.json"
    raw_path.write_text(_json.dumps(tampered_facts, sort_keys=True, indent=2), encoding="utf-8")

    # Loader staged-discovery must now raise receipt_hash_mismatch (not payload_hash_mismatch)
    # because the receipt_hash check fires first (FIX 3 runs before payload check).
    with pytest.raises(SecXbrlOfflineEvidenceLoaderError) as exc_info:
        _read_companyfacts(
            None,
            storage=storage,
            connector_receipt_hash=connector_receipt_hash,
            cik_hash=cik_hash_val,
        )

    assert exc_info.value.code == "sec_xbrl_offline_evidence_loader_companyfacts_receipt_hash_mismatch", (
        f"Expected receipt_hash_mismatch (FIX 3), got: {exc_info.value.code}"
    )


def test_loader_rejects_staged_companyfacts_wrong_schema_id(tmp_path) -> None:
    """Stage a valid companyfacts receipt, then corrupt its schema_id on disk to a wrong value.

    Loader staged-discovery must raise SecXbrlOfflineEvidenceLoaderError with code
    sec_xbrl_offline_evidence_loader_companyfacts_receipt_schema_mismatch (fail-closed),
    and must NOT admit the receipt.  The schema_id guard runs BEFORE receipt-hash and
    payload-hash checks so a wrong-schema receipt is rejected immediately.
    """
    import hashlib as _hashlib
    import json as _json
    from app.services.layer3_sec_xbrl_offline_companyfacts_stage import (
        stage_sec_xbrl_companyfacts,
        COMPANYFACTS_RECEIPT_DIR,
    )
    from app.services.layer3_sec_xbrl_offline_evidence_loader import (
        SecXbrlOfflineEvidenceLoaderError,
        _read_companyfacts,
    )

    storage = tmp_path / "storage"

    # Write a connector receipt so stage can bind cik_hash.
    cik = "320193"
    raw_cik = cik.lstrip("0") or "0"
    cik_hash_val = _hashlib.sha256(raw_cik.encode("utf-8")).hexdigest()
    connector_receipt_hash = "b" * 64
    connector_receipt = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "connector_receipt_id": f"sec-edgar-real-filing-connector-{'b' * 24}-{'b' * 24}",
        "connector_receipt_hash": connector_receipt_hash,
        "corpus_manifest": {
            "example_records": [{"example_id": "ex-1", "cik_hash": cik_hash_val, "form_type": "10-K"}]
        },
    }
    conn_dir = storage / "layer3-sec-edgar-real-filing-acquisition-connector" / "receipts"
    conn_dir.mkdir(parents=True, exist_ok=True)
    (conn_dir / f"{connector_receipt['connector_receipt_id']}.json").write_text(
        _json.dumps(connector_receipt, sort_keys=True, indent=2), encoding="utf-8"
    )

    # Stage a valid companyfacts.
    facts = {"us-gaap": {"Assets": {"units": {"USD": [{"val": 500, "end": "2023-12-31", "fp": "FY", "fy": 2023}]}}}}
    content = _json.dumps(facts, sort_keys=True, indent=2).encode("utf-8")
    content_sha256 = _hashlib.sha256(content).hexdigest()

    result = stage_sec_xbrl_companyfacts(
        companyfacts=facts,
        cik=cik,
        connector_receipt_hash=connector_receipt_hash,
        content_sha256=content_sha256,
        storage_dir=storage,
    )
    receipt_id = result["companyfacts_receipt_id"]

    # Locate the staged receipt file on disk and corrupt its schema_id.
    receipts_dir = storage / COMPANYFACTS_RECEIPT_DIR / "receipts"
    receipt_path = receipts_dir / f"{receipt_id}.json"
    assert receipt_path.exists(), "Staged receipt must have been written"

    staged = _json.loads(receipt_path.read_text(encoding="utf-8"))
    staged["schema_id"] = "layer3.some_other.v1"
    receipt_path.write_text(_json.dumps(staged, sort_keys=True, indent=2), encoding="utf-8")

    # Loader staged-discovery must reject immediately with schema_mismatch, not admit it.
    with pytest.raises(SecXbrlOfflineEvidenceLoaderError) as exc_info:
        _read_companyfacts(
            None,
            storage=storage,
            connector_receipt_hash=connector_receipt_hash,
            cik_hash=cik_hash_val,
        )

    assert exc_info.value.code == "sec_xbrl_offline_evidence_loader_companyfacts_receipt_schema_mismatch", (
        f"Expected schema_mismatch, got: {exc_info.value.code}"
    )
