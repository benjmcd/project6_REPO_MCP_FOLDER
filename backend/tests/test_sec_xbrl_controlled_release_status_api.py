from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.layer3 import router as layer3_router
from app.services import layer3_sec_xbrl_controlled_release_activation_gate as activation_gate
from app.services import layer3_sec_xbrl_production_release_decision_gate as release_gate


RELEASE_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/production-release/decision/status"
ACTIVATION_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/controlled-release/activation/status"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(layer3_router, prefix="/api/v1/layer3")
    return TestClient(app)


def test_production_release_decision_status_api_reports_review_ready_without_release() -> None:
    response = _client().post(
        RELEASE_STATUS_ROUTE,
        json={
            "client_request_id": "release-decision-status-1",
            "status_mode": "sec_xbrl_production_release_decision_status_v1",
            "operator_decision": "inspect_sec_xbrl_production_release_decision_gate",
            "production_admission_gate": _admission_gate(),
            "release_decision_spec": _release_decision(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == release_gate.STATUS_REVIEW_READY
    assert body["ready"] is True
    assert body["release_decision_status_api_route_enabled"] is True
    assert body["readiness"]["production_release_decision_review_ready"] is True
    assert body["readiness"]["production_release_executed"] is False
    assert body["controls"]["release_executed_by_gate"] is False
    assert body["controls"]["runtime_default_enabled"] is False
    assert body["controls"]["production_database_touched"] is False
    assert body["runtime_default_enabled"] is False
    assert body["api_route_enabled"] is False
    assert body["rendered_ui_enabled"] is False
    assert body["production_readiness_claimed"] is False


def test_production_release_decision_status_api_returns_blocked_report_without_echoing_raw_input() -> None:
    response = _client().post(
        RELEASE_STATUS_ROUTE,
        json={
            "client_request_id": "release-decision-status-raw",
            "status_mode": "sec_xbrl_production_release_decision_status_v1",
            "operator_decision": "inspect_sec_xbrl_production_release_decision_gate",
            "production_admission_gate": _admission_gate(),
            "release_decision_spec": {
                **_release_decision(),
                "auto_release_enabled": True,
                "local_path": r"C:\raw\release",
            },
        },
    )
    text = response.text

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == release_gate.STATUS_BLOCKED
    assert body["readiness"]["production_release_executed"] is False
    assert r"C:\raw\release" not in text


def test_controlled_release_activation_status_api_reports_preflight_ready_without_activation() -> None:
    response = _client().post(
        ACTIVATION_STATUS_ROUTE,
        json={
            "client_request_id": "activation-status-1",
            "status_mode": "sec_xbrl_controlled_release_activation_status_v1",
            "operator_decision": "inspect_sec_xbrl_controlled_release_activation_gate",
            "production_release_decision_gate": _release_gate(),
            "activation_spec": _activation_spec(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == activation_gate.STATUS_PREFLIGHT_READY
    assert body["ready"] is True
    assert body["controlled_release_activation_status_api_route_enabled"] is True
    assert body["readiness"]["controlled_release_activation_preflight_ready"] is True
    assert body["readiness"]["controlled_release_activation_executed"] is False
    assert body["readiness"]["production_release_executed"] is False
    assert body["controls"]["activation_executed_by_gate"] is False
    assert body["controls"]["runtime_default_enabled"] is False
    assert body["controls"]["production_database_touched"] is False
    assert body["runtime_default_enabled"] is False
    assert body["api_route_enabled"] is False
    assert body["rendered_ui_enabled"] is False
    assert body["production_readiness_claimed"] is False


def test_controlled_release_activation_status_api_blocks_stale_or_auto_activation_without_execution() -> None:
    response = _client().post(
        ACTIVATION_STATUS_ROUTE,
        json={
            "client_request_id": "activation-status-stale",
            "status_mode": "sec_xbrl_controlled_release_activation_status_v1",
            "operator_decision": "inspect_sec_xbrl_controlled_release_activation_gate",
            "production_release_decision_gate": _release_gate(),
            "activation_spec": {
                **_activation_spec(),
                "production_release_decision_basis_hash": _hash("9"),
                "auto_activation_enabled": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == activation_gate.STATUS_BLOCKED
    assert body["summary"]["release_decision_basis_bound"] is False
    assert body["readiness"]["controlled_release_activation_executed"] is False
    assert body["controls"]["activation_executed_by_gate"] is False
    assert body["controls"]["runtime_default_enabled"] is False


def _admission_gate() -> dict[str, object]:
    return {
        "status": "layer3_sec_xbrl_production_admission_review_ready",
        "readiness": {
            "production_admission_review_ready": True,
            "production_admission_admitted": False,
            "production_admission_blocked": False,
        },
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "admission_basis_hash": _hash("c"),
        },
        "controls": {
            "validate_only": True,
            "runtime_default_enabled": False,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
    }


def _release_decision() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in release_gate.REQUIRED_RELEASE_FLAGS
    }
    value.update({key: False for key in release_gate.NEGATIVE_RELEASE_FLAGS})
    value["admission_basis_hash"] = _hash("c")
    return value


def _release_gate() -> dict[str, object]:
    return {
        "status": release_gate.STATUS_REVIEW_READY,
        "readiness": {
            "production_release_decision_review_ready": True,
            "production_release_executed": False,
            "production_release_blocked": False,
        },
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "admission_basis_hash": _hash("c"),
            "production_release_decision_basis_hash": _hash("d"),
        },
        "controls": {
            "validate_only": True,
            "release_executed_by_gate": False,
            "runtime_default_enabled": False,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
    }


def _activation_spec() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in activation_gate.REQUIRED_ACTIVATION_FLAGS
    }
    value.update({key: False for key in activation_gate.NEGATIVE_ACTIVATION_FLAGS})
    value["production_release_decision_basis_hash"] = _hash("d")
    return value


def _hash(char: str) -> str:
    return char * 64
