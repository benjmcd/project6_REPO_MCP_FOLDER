from __future__ import annotations

import hashlib
import json
import socket
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, settings
from app.db.session import Base
from app.services import layer3_egress_policy as egress_policy
from app.services import layer3_sec_edgar_arelle_value_reveal as legacy_value_reveal
from app.services import layer3_sec_edgar_live_source_artifact as live_source
from app.services import layer3_sec_xbrl_controlled_value_reveal_submit as controlled_submit
from app.services import layer3_sec_xbrl_e2e_offline_orchestrator as orchestrator
from app.services import layer3_sec_xbrl_offline_companyfacts_oracle_packet as oracle_packet
from app.services import layer3_sec_xbrl_offline_companyfacts_stage as companyfacts_stage
from app.services import layer3_sec_xbrl_offline_evidence_loader as loader
from app.services import layer3_sec_xbrl_offline_evidence_proof_capability as proof_capability
from app.services import layer3_sec_xbrl_production_admission as production_admission
from app.services.layer3_sec_xbrl_posture import build_sec_xbrl_runtime_posture
from app.services.layer3_utils import json_clone, stable_hash
from scripts.support_matrix_check import _settings_defaults


REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORT_MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"

PINNED_FALSE_FLAGS = [
    "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "LAYER3_MODEL_EGRESS_ENABLED",
    "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
    "LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
]

UNSUPPORTED_CAPABILITIES = {
    "real_provider_delivery",
    "model_agent_egress",
    "nonlocal_multi_trust_multi_identity",
    "high_availability",
    "keyed_connectors",
    "signed_reference_export",
}

SEC_EXPERIMENTAL_DEFAULT_OFF_FLAGS = {
    "sec_live_network_egress": "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "sec_value_reveal": "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "sec_controlled_value_reveal_submit": "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "arelle_internal_value_store": "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "arelle_corpus_validation": "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "sec_xbrl_production_admission_evaluator": "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
}

SEC_XBRL_SIMULATION_CAPABILITIES = {
    "sec_offline_replay_path",
    "layer3_sec_xbrl_offline_evidence_loader",
    "layer3_sec_xbrl_offline_companyfacts_stage",
    "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
    "layer3_sec_xbrl_e2e_offline_orchestrator",
    "layer3_sec_xbrl_offline_evidence_proof_capability",
    "offline_staged_redaction_value_store_resolution",
}

CONTROL_FALSE_KEYS = {
    "source_acquisition_performed",
    "arelle_invoked",
    "value_reveal_performed",
    "api_route_enabled",
    "production_readiness_claimed",
}


def _matrix() -> dict[str, Any]:
    return json.loads(SUPPORT_MATRIX_PATH.read_text(encoding="utf-8"))


def _capabilities_by_id() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in _matrix()["capabilities"]}


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


@pytest.mark.parametrize("capability", _matrix()["capabilities"], ids=lambda item: item["id"])
def test_support_matrix_evidence_pointers_resolve_for_every_declared_capability(
    capability: dict[str, Any],
) -> None:
    for pointer in _evidence_file_pointers(str(capability["evidence"])):
        assert (REPO_ROOT / pointer).exists(), f"{capability['id']} evidence pointer missing: {pointer}"


def test_support_matrix_statuses_preserve_rc3_honesty_floor() -> None:
    matrix = _matrix()
    by_id = _capabilities_by_id()

    assert matrix["profile"] == "local_expert"
    assert matrix["overlays"] == ["public_connectors", "sec_xbrl_offline"]
    for token in ("live SEC egress explicit default-off", "no value-reveal default-on", "no agent egress", "no nonlocal"):
        assert token in matrix["boundary_note"]

    for capability_id in UNSUPPORTED_CAPABILITIES:
        assert by_id[capability_id]["status"] == "unsupported"
    for capability_id in SEC_EXPERIMENTAL_DEFAULT_OFF_FLAGS:
        assert by_id[capability_id]["status"] == "experimental_default_off"
    for capability_id in SEC_XBRL_SIMULATION_CAPABILITIES:
        assert by_id[capability_id]["status"] == "simulation"

    forbidden_supported = UNSUPPORTED_CAPABILITIES | set(SEC_EXPERIMENTAL_DEFAULT_OFF_FLAGS)
    forbidden_supported |= SEC_XBRL_SIMULATION_CAPABILITIES
    assert [
        capability_id
        for capability_id in sorted(forbidden_supported)
        if by_id[capability_id]["status"] == "supported"
    ] == []


def test_pinned_false_flags_are_complete_and_default_false() -> None:
    matrix = _matrix()
    defaults = _settings_defaults(REPO_ROOT)

    assert matrix["pinned_false_flags"] == PINNED_FALSE_FLAGS
    assert {flag: defaults.get(flag) for flag in PINNED_FALSE_FLAGS} == {
        flag: False for flag in PINNED_FALSE_FLAGS
    }
    assert defaults["DEPLOYMENT_MODE"] == "local"
    assert defaults["AUTH_OWNER"] == "none"
    assert defaults["TRUSTED_PROXY_MODE"] is False
    assert defaults["NRC_ADAMS_APS_SUBSCRIPTION_KEY"] == ""
    assert defaults["SENATE_LDA_API_KEY"] == ""


def test_sec_xbrl_experimental_defaults_are_reflected_in_runtime_posture(monkeypatch) -> None:
    defaults = _settings_defaults(REPO_ROOT)
    for capability_id, flag in SEC_EXPERIMENTAL_DEFAULT_OFF_FLAGS.items():
        assert _capabilities_by_id()[capability_id]["status"] == "experimental_default_off"
        assert defaults[flag] is False

    _force_sec_xbrl_flag_defaults(monkeypatch)
    posture = build_sec_xbrl_runtime_posture()
    gated_by_flag = {
        item["required_flag"]: item
        for item in posture["gated_capabilities"]
        if "required_flag" in item
    }
    for flag in {
        "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
        "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    }:
        assert flag in gated_by_flag
    assert posture["source_acquisition_performed"] is False
    assert posture["arelle_invoked"] is False
    assert posture["value_reveal_performed"] is False
    assert posture["production_readiness_claimed"] is False


def test_experimental_value_reveal_paths_block_when_flags_are_off(monkeypatch) -> None:
    _force_sec_xbrl_flag_defaults(monkeypatch)

    reveal_response = legacy_value_reveal.reveal_sec_edgar_arelle_values(
        {"client_request_id": "legacy-reveal-disabled"},
        db=None,  # type: ignore[arg-type]
    )
    assert reveal_response["reveal_state"] == "sec_edgar_arelle_value_reveal_blocked"
    assert reveal_response["blocked_reasons"][0]["reason"] == (
        "sec_edgar_arelle_value_reveal_feature_flag_disabled"
    )

    with pytest.raises(controlled_submit.SecXbrlControlledValueRevealSubmitError) as exc_info:
        controlled_submit.submit_controlled_value_reveal(
            None,  # type: ignore[arg-type]
            client_request_id="controlled-reveal-disabled",
            sec_xbrl_value_reveal_authority_receipt_id="sec-xbrl-value-reveal-authority-" + "a" * 24,
            authority_basis_hash="a" * 64,
            operator_reveal_confirmation=True,
        )
    assert exc_info.value.code == "sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled"

    admission = production_admission.evaluate_production_admission(
        evidence={"companyfacts_oracle_supplied": True},
        admission_flag_enabled=False,
    )
    assert admission["production_admission_ready"] is False
    assert admission["production_admission_blocked_reason"] == "production_admission_flag_disabled"


def test_unsupported_boundary_paths_fail_closed(monkeypatch, tmp_path) -> None:
    _force_sec_xbrl_flag_defaults(monkeypatch)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    with pytest.raises(Exception) as exc_info:
        live_source.acquire_sec_edgar_companyfacts_live_artifact(
            {"cik": "320193", "operator_confirmation": True}
        )
    assert "live_network_disabled" in _error_code(exc_info.value)

    decision = egress_policy.evaluate_executor_egress(
        "agent",
        model_egress_enabled=settings.layer3_model_egress_enabled,
    )
    assert decision.allowed is False
    assert decision.reason == "model_egress_requires_explicit_policy"
    with pytest.raises(egress_policy.EgressPolicyError) as egress_exc:
        egress_policy.assert_executor_egress_allowed(
            "agent",
            model_egress_enabled=settings.layer3_model_egress_enabled,
        )
    assert egress_exc.value.error_code == "model_egress_not_permitted"

    with pytest.raises(ValueError, match="AUTH_OWNER=proxy is required"):
        Settings(
            _env_file=None,
            DEPLOYMENT_MODE="nonlocal",
            ALLOWED_ORIGINS="https://example.com",
            DATABASE_URL="postgresql://user:pass@localhost/db",
            LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=False,
        )


def test_offline_simulation_services_preserve_zero_egress_controls(
    monkeypatch,
    tmp_path,
    db_session,
) -> None:
    _force_sec_xbrl_flag_defaults(monkeypatch)
    _block_network(monkeypatch)

    loader_report = loader.inspect_sec_xbrl_offline_evidence_storage(tmp_path / "missing-storage")
    assert loader_report["status"] == "offline_evidence_bundle_blocked"
    _assert_false_controls(loader_report["controls"])

    oracle_report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        tmp_path / "missing-storage"
    )
    assert oracle_report["status"] == "offline_companyfacts_oracle_packet_blocked"
    _assert_false_controls(oracle_report["controls"])

    proof_report = proof_capability.inspect_sec_xbrl_offline_evidence_proof_capability()
    assert proof_report["status"] == "offline_evidence_proof_capability_blocked"
    _assert_false_controls(proof_report["controls"])

    orchestrator_response = orchestrator.open_redacted_operator_review_from_offline_evidence(
        db_session,
        client_request_id="harden-offline-controls",
        evidence=_offline_evidence(),
        period_limit=2,
    )
    assert orchestrator_response["status"] == "review_ready"
    assert orchestrator_response["controls"]["offline_evidence_input_only"] is True
    _assert_false_controls(orchestrator_response["controls"])

    connector_hash = _hash("c")
    _write_connector_receipt(tmp_path, cik="320193", connector_receipt_hash=connector_hash)
    content = json.dumps({"facts": _sample_companyfacts()}).encode("utf-8")
    staged = companyfacts_stage.stage_sec_xbrl_companyfacts(
        companyfacts=_sample_companyfacts(),
        cik="320193",
        connector_receipt_hash=connector_hash,
        content_sha256=hashlib.sha256(content).hexdigest(),
        storage_dir=tmp_path,
    )
    assert staged["status"] == "staged"
    assert staged["operator_surface_exposure"] is False
    assert staged["raw_cik_exposed"] is False
    assert staged["raw_values_exposed"] is False


def _evidence_file_pointers(evidence: str) -> list[Path]:
    pointers: list[Path] = []
    for part in [item.strip() for item in evidence.split(";") if item.strip()]:
        token = part.split("::", 1)[0].strip()
        if token.startswith("PR-"):
            continue
        if ":" in token:
            token = token.split(":", 1)[0].strip()
        path = Path(token)
        if path.suffix in {".py", ".md", ".json", ".yaml", ".yml", ".html", ".js", ".css", ".ps1", ".example"}:
            pointers.append(path)
    return pointers


def _force_sec_xbrl_flag_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_corpus_validation_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_value_reveal_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)
    monkeypatch.setattr(settings, "layer3_model_egress_enabled", False)
    monkeypatch.setattr(settings, "sec_xbrl_production_admission_evaluator_enabled", False)
    monkeypatch.setattr(settings, "layer3_analysis_product_package_inventory_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "")
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("offline honesty test attempted network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)


def _assert_false_controls(controls: dict[str, Any]) -> None:
    for key in CONTROL_FALSE_KEYS:
        assert controls[key] is False
    assert controls.get("network_performed", False) is False


def _error_code(exc: Exception) -> str:
    return str(getattr(exc, "error_code", None) or getattr(exc, "code", None) or exc)


def _offline_evidence() -> dict[str, Any]:
    sidecar_records = [
        _record("rf-revenue-old", "RevenueFromContractWithCustomerExcludingAssessedTax", start="start-1", end="end-1"),
        _record("rf-assets-old", "Assets", end="end-1", instant=True),
        _record("rf-cashflow-old", "NetCashProvidedByUsedInOperatingActivities", start="start-1", end="end-1"),
        _record("rf-revenue-fy", "RevenueFromContractWithCustomerExcludingAssessedTax", start="start-2", end="end-2"),
        _record("rf-assets-fy", "Assets", end="end-2", instant=True),
        _record("rf-cashflow-fy", "NetCashProvidedByUsedInOperatingActivities", start="start-2", end="end-2"),
        _record("rf-period-end", "DocumentPeriodEndDate", taxonomy="dei", unit="unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-revenue-old", "90"),
        _value("rf-assets-old", "180"),
        _value("rf-cashflow-old", "30"),
        _value("rf-revenue-fy", "100"),
        _value("rf-assets-fy", "200"),
        _value("rf-cashflow-fy", "40"),
        _value("rf-period-end", "end-2"),
    ]
    value_store_hash = stable_hash(value_records)
    resolved_fact_projection = [_redacted_fact(record) for record in sidecar_records]
    return {
        "companyfacts": _companyfacts_periods(),
        "sidecar_receipt": {
            "sidecar_receipt_id": "sidecar-receipt-redacted",
            "sidecar_receipt_hash": _hash("b"),
            "resolved_fact_records": sidecar_records,
            "resolved_fact_projection": resolved_fact_projection,
            "resolved_fact_inventory_hash": stable_hash(resolved_fact_projection),
            "internal_value_store": {"value_store_hash": value_store_hash, "value_record_count": len(value_records)},
            "authority_hashes": {"internal_value_store_hash": value_store_hash, "sidecar_receipt_hash": _hash("b")},
        },
        "value_store": {"value_records": value_records, "value_store_hash": value_store_hash},
        "statement_role_view_records": [
            {"fact_id_or_order_key": "rf-revenue-old", "statement_candidate_role": "income_statement"},
            {"fact_id_or_order_key": "rf-assets-old", "statement_candidate_role": "balance_sheet"},
            {"fact_id_or_order_key": "rf-cashflow-old", "statement_candidate_role": "cash_flow_statement"},
            {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
            {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
            {"fact_id_or_order_key": "rf-cashflow-fy", "statement_candidate_role": "cash_flow_statement"},
        ],
        "dataset_version_id": "dataset-redacted",
    }


def _companyfacts_periods() -> dict[str, Any]:
    entries = [
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
        ("Assets", "180", "USD", "", "end-1", True),
        ("Assets", "200", "USD", "", "end-2", True),
        ("NetCashProvidedByUsedInOperatingActivities", "30", "USD", "start-1", "end-1", False),
        ("NetCashProvidedByUsedInOperatingActivities", "40", "USD", "start-2", "end-2", False),
    ]
    facts: dict[str, dict[str, Any]] = {}
    for local_name, value, unit, start, end, instant in entries:
        facts.setdefault("us-gaap", {}).setdefault(local_name, {"units": {}})
        fact: dict[str, Any] = {"fp": "FY", "fy": "", "val": value, "end": end}
        if not instant:
            fact["start"] = start
        facts["us-gaap"][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _sample_companyfacts() -> dict[str, Any]:
    return {"facts": _companyfacts_periods()}


def _record(
    fact_id: str,
    local_name: str,
    *,
    taxonomy: str = "us-gaap",
    unit: str = "USD",
    start: str = "start-2",
    end: str = "end-2",
    instant: bool = False,
) -> dict[str, Any]:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    namespace = "xbrl.sec.gov/dei/test" if taxonomy == "dei" else "fasb.org/us-gaap/test"
    unit_payload = {"measures": []} if unit == "unitless" else {"currency": f"iso4217:{unit}", "measures": [f"iso4217:{unit}"]}
    return {
        "resolved_fact_id": fact_id,
        "concept": {"namespace": namespace, "local_name": local_name, "standard": True},
        "unit": unit_payload,
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _value(fact_id: str, effective_value: str) -> dict[str, Any]:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _redacted_fact(record: dict[str, Any]) -> dict[str, Any]:
    value = json_clone(record)
    value["value_redacted"] = True
    return value


def _write_connector_receipt(storage: Path, *, cik: str, connector_receipt_hash: str) -> None:
    cik_hash = hashlib.sha256((cik.lstrip("0") or "0").encode("utf-8")).hexdigest()
    receipt = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "connector_receipt_id": f"sec-edgar-real-filing-connector-{connector_receipt_hash[:24]}-{connector_receipt_hash[24:48]}",
        "connector_receipt_hash": connector_receipt_hash,
        "corpus_manifest": {"example_records": [{"example_id": "ex-1", "cik_hash": cik_hash, "form_type": "10-K"}]},
    }
    path = storage / companyfacts_stage.CONNECTOR_RECEIPT_DIR / "receipts" / f"{receipt['connector_receipt_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")


def _hash(char: str) -> str:
    return char * 64
