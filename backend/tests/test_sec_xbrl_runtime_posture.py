from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services.layer3_sec_xbrl_posture import (
    POSTURE_SCHEMA_ID,
    build_sec_xbrl_runtime_posture,
)
from main import app


@pytest.fixture(autouse=True)
def default_sec_xbrl_posture_flags(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_corpus_validation_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_value_reveal_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "")
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _capabilities(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["capability"]): item for item in items}


def _surfaces(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["surface_id"]): item for item in items}


def test_runtime_posture_default_reports_controlled_reveal_and_live_paths_gated() -> None:
    posture = build_sec_xbrl_runtime_posture()

    assert posture["schema_id"] == POSTURE_SCHEMA_ID
    assert posture["posture_state"] == "sec_xbrl_controlled_value_reveal_submit_blocked_by_feature_flag"
    assert len(posture["posture_basis_hash"]) == 64

    flags = posture["runtime_flags"]
    assert flags["controlled_value_reveal_submit_enabled"] is False
    assert flags["arelle_fact_authority_cutover_enabled"] is True
    assert flags["arelle_fact_authority_nonlocal_authorized"] is False
    assert flags["live_sec_edgar_network_enabled"] is False
    assert flags["sec_edgar_user_agent_configured"] is False

    activated = _capabilities(posture["activated_capabilities"])
    assert "controlled_value_reveal_submit" not in activated
    assert activated["arelle_fact_authority_cutover"]["runtime_state"] == (
        "local_cutover_enabled_nonlocal_requires_explicit_authorization"
    )

    gated = _capabilities(posture["gated_capabilities"])
    assert "live_sec_edgar_network_source_acquisition" in gated
    assert "legacy_arelle_governed_sibling_value_reveal" in gated
    assert "nonlocal_arelle_fact_authority_cutover" in gated
    assert gated["controlled_value_reveal_submit"]["runtime_state"] == (
        "blocked_by_controlled_submit_feature_flag"
    )
    assert "production_readiness_claim" in gated
    assert len(posture["activation_surface_hash"]) == 64

    surfaces = _surfaces(posture["activation_surfaces"])
    assert set(surfaces) == {
        "controlled_value_reveal_submit",
        "live_sec_edgar_network_source_acquisition",
        "arelle_invocation_and_governed_sibling_value_reveal",
        "multi_filing_evidence_authority_gate",
        "delivery_export_package_status",
        "nonlocal_operator_auth_hardening",
    }
    assert surfaces["controlled_value_reveal_submit"]["runtime_enabled"] is False
    assert surfaces["controlled_value_reveal_submit"]["required_flags"] == [
        "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED"
    ]
    assert surfaces["controlled_value_reveal_submit"]["rendered_panel_id"] == (
        "sec-xbrl-controlled-value-reveal-panel"
    )
    live_source = surfaces["live_sec_edgar_network_source_acquisition"]
    assert live_source["surface_state"] == "gated_by_live_network_feature_flag"
    assert live_source["runtime_enabled"] is False
    assert live_source["operator_surface_rendered"] is True
    assert live_source["rendered_panel_id"] == "sec-edgar-live-source-artifact-acquisition-panel"
    assert live_source["browser_supplied_url_allowed"] is False
    assert live_source["sec_edgar_user_agent_configured"] is False
    assert "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED" in live_source["required_flags"]
    assert "LAYER3_SEC_EDGAR_USER_AGENT" in live_source["required_configuration"]
    assert "POST /api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire" in live_source[
        "api_routes"
    ]
    for surface in surfaces.values():
        assert surface["current_posture_performs_side_effect"] is False
        assert surface["source_acquisition_performed"] is False
        assert surface["arelle_invoked"] is False
        assert surface["delivery_export_performed"] is False
        assert surface["runtime_db_write"] is False
        assert surface["frontend_durable_authority"] is False
        assert surface["raw_authority_exposed"] is False
        assert surface["production_readiness_claimed"] is False

    route_families = {item["route_family"] for item in posture["protected_route_families"]}
    assert "sec_xbrl_operator_review_workflow_status_read" in route_families
    assert "sec_xbrl_controlled_value_reveal_submit_status_read" in route_families

    assert posture["source_acquisition_performed"] is False
    assert posture["arelle_invoked"] is False
    assert posture["value_reveal_performed"] is False
    assert posture["runtime_db_write"] is False
    assert posture["production_readiness_claimed"] is False
    assert posture["raw_operator_identity_exposed"] is False
    assert posture["raw_proxy_header_exposed"] is False
    assert posture["raw_workspace_identity_exposed"] is False
    assert posture["raw_value_exposed"] is False
    assert posture["residual_magnitude_exposed"] is False


def test_runtime_posture_controlled_submit_feature_flag_reports_available(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", True)

    posture = build_sec_xbrl_runtime_posture()

    assert posture["posture_state"] == "sec_xbrl_controlled_value_reveal_available_with_runtime_gates"
    assert "controlled_value_reveal_submit" in _capabilities(posture["activated_capabilities"])
    assert "controlled_value_reveal_submit" not in _capabilities(posture["gated_capabilities"])

    surfaces = _surfaces(posture["activation_surfaces"])
    assert surfaces["controlled_value_reveal_submit"]["runtime_enabled"] is True
    assert surfaces["controlled_value_reveal_submit"]["required_flags"] == []
    assert surfaces["controlled_value_reveal_submit"]["next_operator_action"] == (
        "submit_controlled_value_reveal_from_authority_receipt"
    )


def test_runtime_posture_controlled_submit_feature_flag_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)

    posture = build_sec_xbrl_runtime_posture()

    assert posture["posture_state"] == "sec_xbrl_controlled_value_reveal_submit_blocked_by_feature_flag"
    assert "controlled_value_reveal_submit" not in _capabilities(posture["activated_capabilities"])
    assert "controlled_value_reveal_submit" in _capabilities(posture["gated_capabilities"])
    assert "enable_controlled_value_reveal_submit_before_browser_value_reveal" in posture[
        "operator_next_actions"
    ]
    assert posture["production_readiness_claimed"] is False
    assert posture["value_reveal_performed"] is False


def test_arelle_activation_surface_reports_cutover_flag_when_cutover_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_corpus_validation_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_value_reveal_enabled", True)

    posture = build_sec_xbrl_runtime_posture()

    surfaces = _surfaces(posture["activation_surfaces"])
    arelle_surface = surfaces["arelle_invocation_and_governed_sibling_value_reveal"]
    assert arelle_surface["runtime_enabled"] is False
    assert arelle_surface["surface_state"] == "gated_by_arelle_runtime_flags"
    assert arelle_surface["required_flags"] == [
        "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED"
    ]
    assert posture["arelle_invoked"] is False


def test_live_activation_surface_requires_user_agent_without_exposing_user_agent(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "")

    posture = build_sec_xbrl_runtime_posture()

    surfaces = _surfaces(posture["activation_surfaces"])
    live_source = surfaces["live_sec_edgar_network_source_acquisition"]
    assert live_source["runtime_enabled"] is False
    assert live_source["surface_state"] == "gated_by_sec_edgar_user_agent_configuration"
    assert live_source["required_flags"] == []
    assert live_source["required_configuration"] == ["LAYER3_SEC_EDGAR_USER_AGENT"]
    assert live_source["next_operator_action"] == "configure_sec_edgar_user_agent_before_source_acquisition"


def test_runtime_posture_reflects_enabled_runtime_flags_without_side_effect_claims(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "Layer3 Test contact@example.com")
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_corpus_validation_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_value_reveal_enabled", True)

    posture = build_sec_xbrl_runtime_posture()

    flags = posture["runtime_flags"]
    assert flags["live_sec_edgar_network_enabled"] is True
    assert flags["sec_edgar_user_agent_configured"] is True
    assert flags["arelle_fact_authority_nonlocal_authorized"] is True
    assert flags["arelle_internal_value_store_enabled"] is True
    assert flags["arelle_corpus_validation_enabled"] is True
    assert flags["arelle_governed_sibling_value_reveal_enabled"] is True

    gated = _capabilities(posture["gated_capabilities"])
    assert "live_sec_edgar_network_source_acquisition" not in gated
    assert "legacy_arelle_governed_sibling_value_reveal" not in gated
    assert "nonlocal_arelle_fact_authority_cutover" not in gated
    assert "production_readiness_claim" in gated

    activated = _capabilities(posture["activated_capabilities"])
    assert activated["arelle_fact_authority_cutover"]["runtime_state"] == (
        "local_cutover_enabled_nonlocal_authorized"
    )
    surfaces = _surfaces(posture["activation_surfaces"])
    live_source = surfaces["live_sec_edgar_network_source_acquisition"]
    assert live_source["surface_state"] == "operator_surface_available_when_live_network_authorized"
    assert live_source["runtime_enabled"] is True
    assert live_source["required_flags"] == []
    assert live_source["required_configuration"] == []
    assert "Layer3 Test contact@example.com" not in json.dumps(posture)
    arelle_surface = surfaces["arelle_invocation_and_governed_sibling_value_reveal"]
    assert arelle_surface["runtime_enabled"] is True
    assert arelle_surface["surface_state"] == "gated_until_explicit_arelle_invocation_proof"
    assert arelle_surface["required_flags"] == []
    assert posture["source_acquisition_performed"] is False
    assert posture["arelle_invoked"] is False
    assert posture["value_reveal_performed"] is False
    assert posture["production_readiness_claimed"] is False


def test_runtime_posture_endpoint_returns_redacted_response(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)

    response = client.get(
        "/api/v1/layer3/sec-xbrl/runtime/posture",
        headers={
            "X-Forwarded-User": "raw-operator@example.invalid",
            "X-Forwarded-Groups": "raw-workspace-group",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == POSTURE_SCHEMA_ID
    assert body["request_id"] == "sec-xbrl-runtime-posture"
    assert "sec_xbrl_runtime_posture" in body
    posture = body["sec_xbrl_runtime_posture"]
    assert posture["identity_authority"]["identity_authority_state"] == "proxy_identity_authority_admitted"
    assert posture["raw_operator_identity_exposed"] is False
    assert posture["raw_proxy_header_exposed"] is False
    assert posture["raw_workspace_identity_exposed"] is False
    assert posture["raw_value_exposed"] is False

    serialized = json.dumps(body)
    assert "raw-operator@example.invalid" not in serialized
    assert "raw-workspace-group" not in serialized
    assert "X-Forwarded" not in serialized
    assert "12345.67" not in serialized
    assert "http://" not in serialized.lower()
    assert "C:\\" not in serialized
