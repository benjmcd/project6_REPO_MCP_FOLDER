from __future__ import annotations

import json
import os
from decimal import Decimal
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.db.session import Base
from app.models import (
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketSet,
)
from app.models.models import L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY
from app.services import layer3_sec_xbrl_operator_review_workflow as workflow_service
from app.services import layer3_sec_xbrl_projection_persistence as projection_persistence
from app.services import layer3_sec_xbrl_statement_assembly as assembly
from app.services import layer3_sec_xbrl_statement_packet_persistence as packet_persistence
from main import app


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "backend" / "alembic" / "versions" / "0040_layer3_sec_xbrl_operator_review_workflow.py"
DECISION_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0042_layer3_sec_xbrl_operator_review_decision.py"
)
DECISION_SUBMIT_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit"
DECISION_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status"


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


@pytest.fixture()
def api_client():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, Session
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


def _hash(char: str) -> str:
    return char * 64


def _projection_rows() -> list[dict[str, Any]]:
    return [
        _projection_row("Revenue", "income"),
        _projection_row("TotalAssets", "balance"),
        _projection_row("OperatingCashFlow", "cashflow"),
    ]


def _projection_row(canonical_id: str, statement: str, *, family: str = "universal") -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": family,
        "status": "projected_oracle_confirmed",
        "source_qname": f"us-gaap:{canonical_id}",
        "oracle_confirmed": True,
        "mapping_method": "fixture",
        "mapping_confidence": "fixture",
        "unit_class": "monetary",
        "provenance_complete": True,
        "value_redacted": True,
        "resolved_fact_provenance_present": True,
        "sidecar_receipt_hash": _hash("b"),
        "value_store_hash": _hash("c"),
        "dataset_version_id": "dv-redacted-1",
    }


def _persisted_projection(db_session, *, request_id: str = "projection-1") -> dict[str, Any]:
    return projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id=request_id,
        projection={
            "status": "canonical_multi_period_projection_ready",
            "sector_family_presence": {"activation_rule": "concept_presence_not_sic_gated"},
            "periods": [
                {
                    "period_ref": "fy-period-1",
                    "period_index": 1,
                    "projection": {
                        "status": "canonical_projection_ready",
                        "dataset_version_id": "dv-redacted-1",
                        "sidecar_receipt_hash": _hash("b"),
                        "value_store_hash": _hash("c"),
                        "concepts": _projection_rows(),
                    },
                }
            ],
        },
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )


def _packet(*, review_exception_count: int = 0) -> dict[str, Any]:
    projection_items = [
        _assembly_row("Revenue", "income"),
        _assembly_row("TotalAssets", "balance"),
        _assembly_row("OperatingCashFlow", "cashflow"),
    ]
    packet = assembly.assemble_reviewable_statement_packet(
        projection_items=projection_items,
        organization_result={
            "contract_passed": True,
            "contract_b_authoritative_organization": True,
            "contract_every_fact_id_bound": True,
            "contract_derived_inputs_bound_and_corroborated": True,
            "normalized_fact_count": 3,
            "organized_count": 3,
            "unjoined_count": 0,
            "a_divergent_count": 0,
            "a_role_unknown_count": 0,
        },
    )
    packet["review_exception_count"] = review_exception_count
    return packet


def _assembly_row(canonical_id: str, statement: str) -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": "universal",
        "status": "projected_oracle_confirmed",
        "source_qname": f"us-gaap:{canonical_id}",
        "oracle_confirmed": True,
        "mapping_method": "fixture",
        "mapping_confidence": "fixture",
        "unit_class": "monetary",
        "provenance_complete": True,
        "_value": Decimal("1"),
    }


def _materialized_packet(
    db_session,
    *,
    packet_request_id: str = "packet-1",
    projection_request_id: str = "projection-1",
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    projection = _persisted_projection(db_session, request_id=projection_request_id)
    return packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id=packet_request_id,
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        packet=packet or _packet(),
    )


def _open_workflow(
    db_session,
    *,
    request_id: str = "workflow-1",
    packet: dict[str, Any] | None = None,
    packet_request_id: str = "packet-1",
    projection_request_id: str = "projection-1",
) -> dict[str, Any]:
    packet_response = _materialized_packet(
        db_session,
        packet_request_id=packet_request_id,
        projection_request_id=projection_request_id,
        packet=packet,
    )
    return workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id=request_id,
        sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
    )


def _decision_submit_payload(workflow: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload = {
        "client_request_id": "decision-submit-api",
        "submit_mode": "sec_xbrl_operator_review_decision_submit_v1",
        "operator_decision": "submit_sec_xbrl_operator_review_decision",
        "sec_xbrl_operator_review_workflow_id": workflow["sec_xbrl_operator_review_workflow_id"],
        "workflow_basis_hash": workflow["workflow_basis_hash"],
        "review_decision": "approved",
        "decision_reason_code": "ready_for_next_freeze",
    }
    payload.update(overrides)
    return payload


def _decision_status_payload(decision: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload = {
        "client_request_id": "decision-status-api",
        "status_mode": workflow_service.DECISION_STATUS_MODE,
        "operator_decision": workflow_service.DECISION_STATUS_OPERATOR_DECISION,
        "sec_xbrl_operator_review_decision_id": decision["sec_xbrl_operator_review_decision_id"],
        "decision_basis_hash": decision["decision_basis_hash"],
    }
    payload.update(overrides)
    return payload


def _record_decision(
    db_session,
    *,
    workflow: dict[str, Any] | None = None,
    request_id: str = "decision-1",
    **overrides: Any,
) -> dict[str, Any]:
    workflow = workflow or _open_workflow(db_session)
    kwargs = {
        "client_request_id": request_id,
        "sec_xbrl_operator_review_workflow_id": workflow["sec_xbrl_operator_review_workflow_id"],
        "workflow_basis_hash": workflow["workflow_basis_hash"],
        "review_decision": "approved",
        "decision_reason_code": "ready_for_next_freeze",
    }
    kwargs.update(overrides)
    return workflow_service.record_redacted_operator_review_decision(db_session, **kwargs)


def _workflow_snapshot(row: L3SecXbrlOperatorReviewWorkflow) -> dict[str, Any]:
    return {
        "workflow_basis_hash": row.workflow_basis_hash,
        "review_status": row.review_status,
        "statement_count": row.statement_count,
        "row_count": row.row_count,
        "review_exception_count": row.review_exception_count,
        "permitted_controls_json": json.dumps(row.permitted_controls_json, sort_keys=True),
        "blocked_controls_json": json.dumps(row.blocked_controls_json, sort_keys=True),
        "authority_refs_json": json.dumps(row.authority_refs_json, sort_keys=True),
        "review_summary_json": json.dumps(row.review_summary_json, sort_keys=True),
    }


def _packet_snapshot(row: L3SecXbrlStatementPacketSet) -> dict[str, Any]:
    return {
        "packet_basis_hash": row.packet_basis_hash,
        "source_projection_basis_hash": row.source_projection_basis_hash,
        "statement_count": row.statement_count,
        "total_review_rows": row.total_review_rows,
        "review_exception_count": row.review_exception_count,
        "review_ready": row.review_ready,
        "identity_rollup_json": json.dumps(row.identity_rollup_json, sort_keys=True),
        "organization_contract_json": json.dumps(row.organization_contract_json, sort_keys=True),
        "packet_summary_json": json.dumps(row.packet_summary_json, sort_keys=True),
        "status": row.status,
    }


def _projection_snapshot(row: L3SecXbrlProjectionSet) -> dict[str, Any]:
    return {
        "projection_basis_hash": row.projection_basis_hash,
        "source_report_hash": row.source_report_hash,
        "dataset_version_id": row.dataset_version_id,
        "sidecar_receipt_hash": row.sidecar_receipt_hash,
        "value_store_hash": row.value_store_hash,
        "sector_family_presence_json": json.dumps(row.sector_family_presence_json, sort_keys=True),
        "period_refs_json": json.dumps(row.period_refs_json, sort_keys=True),
        "projection_summary_json": json.dumps(row.projection_summary_json, sort_keys=True),
        "redaction_policy": row.redaction_policy,
        "status": row.status,
    }


def _decision_snapshot(row: L3SecXbrlOperatorReviewDecision) -> dict[str, Any]:
    return {
        "decision_basis_hash": row.decision_basis_hash,
        "workflow_basis_hash": row.workflow_basis_hash,
        "statement_packet_basis_hash": row.statement_packet_basis_hash,
        "source_projection_basis_hash": row.source_projection_basis_hash,
        "decision_mode": row.decision_mode,
        "review_decision": row.review_decision,
        "decision_status": row.decision_status,
        "redaction_policy": row.redaction_policy,
        "decision_reason_code": row.decision_reason_code,
        "decision_notes_present": row.decision_notes_present,
        "decision_notes_hash": row.decision_notes_hash,
        "decision_summary_json": json.dumps(row.decision_summary_json, sort_keys=True),
        "authority_refs_json": json.dumps(row.authority_refs_json, sort_keys=True),
        "permitted_controls_after_decision_json": json.dumps(
            row.permitted_controls_after_decision_json,
            sort_keys=True,
        ),
        "blocked_controls_after_decision_json": json.dumps(
            row.blocked_controls_after_decision_json,
            sort_keys=True,
        ),
    }


def test_operator_review_workflow_opens_redacted_control_envelope(db_session) -> None:
    response = _open_workflow(db_session)

    assert response["status"] == "review_ready"
    assert response["schema_id"] == workflow_service.WORKFLOW_SCHEMA_ID
    assert response["control_mode"] == "redacted_statement_packet_review_only"
    assert response["redaction_policy"] == "redacted_no_values"
    assert response["statement_count"] == 3
    assert response["row_count"] == 3
    assert response["review_exception_count"] == 0
    assert response["runtime_default_enabled"] is False
    assert response["value_reveal_performed"] is False
    assert response["source_acquisition_performed"] is False
    assert response["arelle_invoked"] is False
    assert response["delivery_export_enabled"] is False
    assert response["api_route_enabled"] is False
    assert response["rendered_ui_enabled"] is False
    assert response["operator_review_decision_recorded"] is False
    assert "inspect_statement_packet_authority" in response["permitted_controls"]
    assert {item["control"] for item in response["blocked_controls"]} >= {
        "reveal_values",
        "submit_operator_review_decision",
        "export_statement_packet",
    }

    workflow = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    assert workflow.workflow_schema_id == workflow_service.WORKFLOW_SCHEMA_ID
    assert workflow.authority_refs_json["statement_packet_basis_hash"] == response["statement_packet_basis_hash"]
    assert workflow.review_summary_json["row_count"] == 3


def test_operator_review_workflow_status_projection_is_read_only(db_session) -> None:
    workflow = _open_workflow(db_session)

    status = workflow_service.inspect_redacted_operator_review_workflow_status(
        db_session,
        client_request_id="workflow-status-1",
        sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        workflow_basis_hash=workflow["workflow_basis_hash"],
    )

    assert status["schema_id"] == workflow_service.WORKFLOW_STATUS_SCHEMA_ID
    assert status["request_id"] == "workflow-status-1"
    assert status["status"] == "review_ready"
    assert status["mode"] == workflow_service.WORKFLOW_STATUS_MODE
    assert status["operator_decision"] == workflow_service.WORKFLOW_STATUS_OPERATOR_DECISION
    assert status["workflow_schema_id"] == workflow_service.WORKFLOW_SCHEMA_ID
    assert status["read_only_status_surface"] is True
    assert status["durable_workflow_authority_used"] is True
    assert status["status_api_route_enabled"] is True
    assert status["open_workflow_api_route_enabled"] is False
    assert status["runtime_default_enabled"] is False
    assert status["value_reveal_performed"] is False
    assert status["source_acquisition_performed"] is False
    assert status["arelle_invoked"] is False
    assert status["delivery_export_enabled"] is False
    assert status["rendered_ui_enabled"] is False
    assert status["operator_review_decision_recorded"] is False
    assert status["negative_invariants"]["raw_values_exposed"] is False
    assert status["negative_invariants"]["residual_magnitudes_exposed"] is False
    assert "inspect_statement_packet_authority" in status["next_allowed_actions"]
    assert "reveal_values" in {item["control"] for item in status["blocked_controls"]}
    response_text = json.dumps(status, sort_keys=True)
    assert "C:/" not in response_text
    assert "https://www.sec.gov" not in response_text


def test_operator_review_workflow_status_rejects_missing_authority(db_session) -> None:
    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_workflow_status(
            db_session,
            client_request_id="workflow-status-missing-authority",
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_status_authority_missing"
    assert exc.value.http_status == 400


def test_operator_review_workflow_status_rejects_tampered_raw_status_json(db_session) -> None:
    workflow = _open_workflow(db_session)
    workflow_row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    workflow_row.review_summary_json = {"local_path": "C:/raw/workflow.json"}
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_workflow_status(
            db_session,
            client_request_id="workflow-status-raw-json",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_raw_authority_not_admitted"


def test_operator_review_workflow_status_rejects_unadmitted_review_summary_numeric_alias(db_session) -> None:
    workflow = _open_workflow(db_session)
    workflow_row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    workflow_row.review_summary_json = {
        **workflow_row.review_summary_json,
        "mean": "12345.67",
    }
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_workflow_status(
            db_session,
            client_request_id="workflow-status-review-summary-mean",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_residual_magnitudes_not_admitted"
    assert exc.value.details == {"field": "mean"}


def test_operator_review_workflow_status_rejects_unadmitted_review_summary_field(db_session) -> None:
    workflow = _open_workflow(db_session)
    workflow_row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    workflow_row.review_summary_json = {
        **workflow_row.review_summary_json,
        "unexpected_public_field": "not admitted",
    }
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_workflow_status(
            db_session,
            client_request_id="workflow-status-review-summary-unadmitted",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_status_review_summary_invalid"
    assert exc.value.details == {"fields": ["unexpected_public_field"]}


def test_operator_review_workflow_status_api_returns_read_only_projection(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-api")

    response = client.post(
        "/api/v1/layer3/sec-xbrl/operator-review/workflow/status",
        json={
            "client_request_id": "workflow-status-api",
            "status_mode": workflow_service.WORKFLOW_STATUS_MODE,
            "operator_decision": workflow_service.WORKFLOW_STATUS_OPERATOR_DECISION,
            "sec_xbrl_operator_review_workflow_id": workflow["sec_xbrl_operator_review_workflow_id"],
            "workflow_basis_hash": workflow["workflow_basis_hash"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == workflow_service.WORKFLOW_STATUS_SCHEMA_ID
    assert body["request_id"] == "workflow-status-api"
    assert body["status"] == "review_ready"
    assert body["sec_xbrl_operator_review_workflow_id"] == workflow["sec_xbrl_operator_review_workflow_id"]
    assert body["workflow_basis_hash"] == workflow["workflow_basis_hash"]
    assert body["status_api_route_enabled"] is True
    assert body["open_workflow_api_route_enabled"] is False
    assert body["rendered_ui_enabled"] is False
    assert body["operator_review_decision_recorded"] is False
    assert body["negative_invariants"]["raw_values_exposed"] is False
    assert "C:/" not in response.text
    assert "https://www.sec.gov" not in response.text


def test_operator_review_workflow_status_api_fails_closed_without_authority(api_client) -> None:
    client, _Session = api_client

    response = client.post(
        "/api/v1/layer3/sec-xbrl/operator-review/workflow/status",
        json={
            "client_request_id": "workflow-status-api-missing-authority",
            "status_mode": workflow_service.WORKFLOW_STATUS_MODE,
            "operator_decision": workflow_service.WORKFLOW_STATUS_OPERATOR_DECISION,
        },
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_operator_review_workflow_status_authority_missing"
    assert body["status"] == "blocked"


def test_operator_review_decision_submit_api_records_redacted_receipt(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api")
        workflow_row = session.query(L3SecXbrlOperatorReviewWorkflow).one()
        packet_row = session.query(L3SecXbrlStatementPacketSet).one()
        projection_row = session.query(L3SecXbrlProjectionSet).one()
        workflow_snapshot = _workflow_snapshot(workflow_row)
        packet_snapshot = _packet_snapshot(packet_row)
        projection_snapshot = _projection_snapshot(projection_row)

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(workflow, client_request_id="decision-submit-api-success"),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == workflow_service.DECISION_SCHEMA_ID
    assert body["status"] == "decision_recorded"
    assert body["review_decision"] == "approved"
    assert body["decision_reason_code"] == "ready_for_next_freeze"
    assert body["decision_submit_api_route_enabled"] is True
    assert body["api_route_enabled"] is False
    assert body["workflow_open_api_route_enabled"] is False
    assert body["rendered_ui_enabled"] is False
    assert body["runtime_default_enabled"] is False
    assert body["value_reveal_performed"] is False
    assert body["delivery_export_enabled"] is False
    assert body["source_acquisition_performed"] is False
    assert body["arelle_invoked"] is False
    assert body["production_readiness_claimed"] is False
    assert body["operator_review_decision_recorded"] is True
    assert body["workflow_mutated"] is False
    assert body["statement_packet_mutated"] is False
    assert body["projection_mutated"] is False
    assert body["decision_notes_present"] is False
    assert body["decision_notes_hash"] is None
    assert "inspect_operator_review_decision_status" in body["permitted_controls_after_decision"]
    assert {item["control"] for item in body["blocked_controls_after_decision"]} >= {
        "reveal_values",
        "export_statement_packet",
        "deliver_statement_packet",
        "refresh_from_sec_source",
        "invoke_arelle",
        "change_runtime_default",
        "render_operator_review_decision_submit_control",
    }
    response_text = json.dumps(body, sort_keys=True)
    for forbidden in ("C:/", "https://www.sec.gov", "operator@example.com", "123.45"):
        assert forbidden not in response_text

    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 1
        assert _workflow_snapshot(session.query(L3SecXbrlOperatorReviewWorkflow).one()) == workflow_snapshot
        assert _packet_snapshot(session.query(L3SecXbrlStatementPacketSet).one()) == packet_snapshot
        assert _projection_snapshot(session.query(L3SecXbrlProjectionSet).one()) == projection_snapshot


def test_operator_review_decision_submit_api_rejects_extra_fields(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-extra")

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(
            workflow,
            client_request_id="decision-submit-api-extra",
            raw_value="123.45",
        ),
    )

    assert response.status_code == 422, response.text
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_submit_api_fails_closed_without_authority(api_client) -> None:
    client, _Session = api_client

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json={
            "client_request_id": "decision-submit-api-missing-authority",
            "submit_mode": "sec_xbrl_operator_review_decision_submit_v1",
            "operator_decision": "submit_sec_xbrl_operator_review_decision",
            "review_decision": "approved",
            "decision_reason_code": "ready_for_next_freeze",
        },
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_operator_review_decision_authority_missing"
    assert body["status"] == "blocked"


def test_operator_review_decision_submit_api_requires_notes_for_non_approved(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-notes")

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(
            workflow,
            client_request_id="decision-submit-api-missing-notes",
            review_decision="blocked",
            decision_reason_code="operator_blocked",
        ),
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_operator_review_decision_notes_required"
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_submit_api_rejects_raw_note_reference(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-raw-note")

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(
            workflow,
            client_request_id="decision-submit-api-raw-note",
            review_decision="rejected",
            decision_reason_code="redaction_gap",
            decision_notes="Contact operator@example.com about 123.45",
        ),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_operator_review_workflow_raw_reference_not_admitted"
    assert "operator@example.com" not in response.text
    assert "123.45" not in response.text
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_submit_api_replays_same_request_and_basis(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-replay")
    payload = _decision_submit_payload(
        workflow,
        client_request_id="decision-submit-api-replay",
    )

    first = client.post(DECISION_SUBMIT_ROUTE, json=payload)
    second = client.post(DECISION_SUBMIT_ROUTE, json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_body = first.json()
    second_body = second.json()
    assert first_body["idempotent_replay"] is False
    assert second_body["idempotent_replay"] is True
    assert (
        second_body["sec_xbrl_operator_review_decision_id"]
        == first_body["sec_xbrl_operator_review_decision_id"]
    )
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 1


def test_operator_review_decision_submit_api_rejects_second_decision_for_workflow(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-second")

    first = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(workflow, client_request_id="decision-submit-api-first"),
    )
    second = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(
            workflow,
            client_request_id="decision-submit-api-second",
            review_decision="blocked",
            decision_reason_code="operator_blocked",
            decision_notes="bounded blocked reason",
        ),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    body = second.json()
    assert body["error_code"] == "sec_xbrl_operator_review_decision_workflow_already_decided"
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 1


def test_operator_review_decision_status_api_returns_read_only_projection(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-status-api")
        decision = _record_decision(
            session,
            workflow=workflow,
            request_id="decision-status-api-source",
        )
        workflow_snapshot = _workflow_snapshot(session.query(L3SecXbrlOperatorReviewWorkflow).one())
        packet_snapshot = _packet_snapshot(session.query(L3SecXbrlStatementPacketSet).one())
        projection_snapshot = _projection_snapshot(session.query(L3SecXbrlProjectionSet).one())
        decision_snapshot = _decision_snapshot(session.query(L3SecXbrlOperatorReviewDecision).one())

    response = client.post(
        DECISION_STATUS_ROUTE,
        json=_decision_status_payload(
            decision,
            client_request_id="decision-status-api-success",
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == workflow_service.DECISION_STATUS_SCHEMA_ID
    assert body["request_id"] == "decision-status-api-success"
    assert body["status"] == "decision_recorded"
    assert body["mode"] == workflow_service.DECISION_STATUS_MODE
    assert body["operator_decision"] == workflow_service.DECISION_STATUS_OPERATOR_DECISION
    assert body["sec_xbrl_operator_review_decision_id"] == decision["sec_xbrl_operator_review_decision_id"]
    assert body["decision_basis_hash"] == decision["decision_basis_hash"]
    assert body["read_only_status_surface"] is True
    assert body["durable_decision_authority_used"] is True
    assert body["decision_status_api_route_enabled"] is True
    assert body["decision_submit_api_route_enabled"] is False
    assert body["workflow_open_api_route_enabled"] is False
    assert body["rendered_ui_enabled"] is False
    assert body["runtime_default_enabled"] is False
    assert body["value_reveal_performed"] is False
    assert body["delivery_export_enabled"] is False
    assert body["source_acquisition_performed"] is False
    assert body["arelle_invoked"] is False
    assert body["operator_review_decision_recorded"] is True
    assert body["workflow_mutated"] is False
    assert body["statement_packet_mutated"] is False
    assert body["projection_mutated"] is False
    assert body["negative_invariants"]["raw_values_exposed"] is False
    assert body["negative_invariants"]["raw_operator_notes_exposed"] is False
    assert body["negative_invariants"]["residual_magnitudes_exposed"] is False
    assert "inspect_operator_review_decision_status" in body["next_allowed_actions"]
    response_text = json.dumps(body, sort_keys=True)
    for forbidden in ("C:/", "https://www.sec.gov", "operator@example.com", "123.45"):
        assert forbidden not in response_text

    with Session() as session:
        assert _workflow_snapshot(session.query(L3SecXbrlOperatorReviewWorkflow).one()) == workflow_snapshot
        assert _packet_snapshot(session.query(L3SecXbrlStatementPacketSet).one()) == packet_snapshot
        assert _projection_snapshot(session.query(L3SecXbrlProjectionSet).one()) == projection_snapshot
        assert _decision_snapshot(session.query(L3SecXbrlOperatorReviewDecision).one()) == decision_snapshot


def test_operator_review_decision_status_api_rejects_extra_fields(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        decision = _record_decision(session, request_id="decision-status-api-extra-source")

    response = client.post(
        DECISION_STATUS_ROUTE,
        json=_decision_status_payload(
            decision,
            client_request_id="decision-status-api-extra",
            raw_value="123.45",
        ),
    )

    assert response.status_code == 422, response.text
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 1


def test_operator_review_decision_status_api_fails_closed_without_authority(api_client) -> None:
    client, _Session = api_client

    response = client.post(
        DECISION_STATUS_ROUTE,
        json={
            "client_request_id": "decision-status-api-missing-authority",
            "status_mode": workflow_service.DECISION_STATUS_MODE,
            "operator_decision": workflow_service.DECISION_STATUS_OPERATOR_DECISION,
        },
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_operator_review_decision_status_authority_missing"
    assert body["status"] == "blocked"


def test_operator_review_workflow_replays_same_request_and_basis(db_session) -> None:
    packet_response = _materialized_packet(db_session)

    first = workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id="workflow-replay",
        sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
    )
    second = workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id="workflow-replay",
        sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
    )
    third = workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id="workflow-same-basis",
        sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
    )

    assert second["idempotent_replay"] is True
    assert third["idempotent_replay"] is True
    assert second["sec_xbrl_operator_review_workflow_id"] == first["sec_xbrl_operator_review_workflow_id"]
    assert third["sec_xbrl_operator_review_workflow_id"] == first["sec_xbrl_operator_review_workflow_id"]
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1


def test_operator_review_workflow_rejects_client_request_conflict(db_session) -> None:
    first_packet = _materialized_packet(db_session)
    changed_packet = _packet()
    changed_packet["organization_contract"]["a_role_unknown_count"] = 1
    second_packet = _materialized_packet(
        db_session,
        packet_request_id="packet-2",
        projection_request_id="projection-2",
        packet=changed_packet,
    )
    workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id="workflow-conflict",
        sec_xbrl_statement_packet_set_id=first_packet["sec_xbrl_statement_packet_set_id"],
    )

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-conflict",
            sec_xbrl_statement_packet_set_id=second_packet["sec_xbrl_statement_packet_set_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_client_request_conflict"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1


def test_operator_review_workflow_rejects_missing_statement_packet_set(db_session) -> None:
    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-missing",
            sec_xbrl_statement_packet_set_id="missing-packet-set",
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_packet_set_missing"


def test_operator_review_workflow_rejects_empty_packet_set(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet_set = _direct_packet_set(
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        source_projection_basis_hash=projection["projection_basis_hash"],
        total_review_rows=0,
    )
    db_session.add(packet_set)
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-empty",
            sec_xbrl_statement_packet_set_id=packet_set.sec_xbrl_statement_packet_set_id,
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_empty_packet"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


def test_operator_review_workflow_rejects_not_ready_packet_set(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet_set = _direct_packet_set(
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        source_projection_basis_hash=projection["projection_basis_hash"],
        review_ready=False,
    )
    db_session.add(packet_set)
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-not-ready",
            sec_xbrl_statement_packet_set_id=packet_set.sec_xbrl_statement_packet_set_id,
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_packet_set_not_ready"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


def test_operator_review_workflow_rejects_raw_local_path_in_packet_summary(db_session) -> None:
    packet_response = _materialized_packet(db_session)
    packet_set = db_session.query(L3SecXbrlStatementPacketSet).filter(
        L3SecXbrlStatementPacketSet.sec_xbrl_statement_packet_set_id
        == packet_response["sec_xbrl_statement_packet_set_id"]
    ).one()
    packet_set.packet_summary_json = {"local_path": "C:/raw/filing.json"}
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-raw-path",
            sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_raw_authority_not_admitted"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


def test_operator_review_workflow_rejects_residual_magnitude_in_packet_summary(db_session) -> None:
    packet_response = _materialized_packet(db_session)
    packet_set = db_session.query(L3SecXbrlStatementPacketSet).filter(
        L3SecXbrlStatementPacketSet.sec_xbrl_statement_packet_set_id
        == packet_response["sec_xbrl_statement_packet_set_id"]
    ).one()
    packet_set.packet_summary_json = {"relative_magnitude": "1E+0"}
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-residual",
            sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_residual_magnitudes_not_admitted"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


def test_operator_review_workflow_rejects_unadmitted_organization_contract_numeric_alias(db_session) -> None:
    packet_response = _materialized_packet(db_session)
    packet_set = db_session.query(L3SecXbrlStatementPacketSet).filter(
        L3SecXbrlStatementPacketSet.sec_xbrl_statement_packet_set_id
        == packet_response["sec_xbrl_statement_packet_set_id"]
    ).one()
    packet_set.organization_contract_json = {
        **packet_set.organization_contract_json,
        "mean": "12345.67",
    }
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-organization-contract-mean",
            sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_residual_magnitudes_not_admitted"
    assert exc.value.details == {"field": "mean"}
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


def test_operator_review_decision_records_redacted_receipt(db_session) -> None:
    workflow = _open_workflow(db_session)
    workflow_row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    workflow_snapshot = {
        "workflow_basis_hash": workflow_row.workflow_basis_hash,
        "review_status": workflow_row.review_status,
        "statement_count": workflow_row.statement_count,
        "row_count": workflow_row.row_count,
        "review_exception_count": workflow_row.review_exception_count,
        "permitted_controls_json": json.dumps(
            workflow_row.permitted_controls_json,
            sort_keys=True,
        ),
        "blocked_controls_json": json.dumps(
            workflow_row.blocked_controls_json,
            sort_keys=True,
        ),
        "authority_refs_json": json.dumps(
            workflow_row.authority_refs_json,
            sort_keys=True,
        ),
        "review_summary_json": json.dumps(
            workflow_row.review_summary_json,
            sort_keys=True,
        ),
    }

    response = workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-1",
        sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        workflow_basis_hash=workflow["workflow_basis_hash"],
        review_decision="approved",
        decision_reason_code="ready_for_next_freeze",
    )

    assert response["status"] == "decision_recorded"
    assert response["schema_id"] == workflow_service.DECISION_SCHEMA_ID
    assert response["review_decision"] == "approved"
    assert response["decision_reason_code"] == "ready_for_next_freeze"
    assert response["decision_notes_present"] is False
    assert response["decision_notes_hash"] is None
    assert response["operator_review_decision_recorded"] is True
    assert response["value_reveal_performed"] is False
    assert response["delivery_export_enabled"] is False
    assert response["api_route_enabled"] is False
    assert response["rendered_ui_enabled"] is False
    assert response["workflow_mutated"] is False
    assert response["statement_packet_mutated"] is False
    assert response["projection_mutated"] is False
    assert response["authority_refs"]["workflow_basis_hash"] == workflow["workflow_basis_hash"]
    assert "inspect_operator_review_decision_status" in response["permitted_controls_after_decision"]
    assert {item["control"] for item in response["blocked_controls_after_decision"]} >= {
        "reveal_values",
        "export_statement_packet",
        "deliver_statement_packet",
        "refresh_from_sec_source",
        "invoke_arelle",
        "change_runtime_default",
        "render_operator_review_decision_submit_control",
    }
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 1
    db_session.refresh(workflow_row)
    assert workflow_snapshot == {
        "workflow_basis_hash": workflow_row.workflow_basis_hash,
        "review_status": workflow_row.review_status,
        "statement_count": workflow_row.statement_count,
        "row_count": workflow_row.row_count,
        "review_exception_count": workflow_row.review_exception_count,
        "permitted_controls_json": json.dumps(
            workflow_row.permitted_controls_json,
            sort_keys=True,
        ),
        "blocked_controls_json": json.dumps(
            workflow_row.blocked_controls_json,
            sort_keys=True,
        ),
        "authority_refs_json": json.dumps(
            workflow_row.authority_refs_json,
            sort_keys=True,
        ),
        "review_summary_json": json.dumps(
            workflow_row.review_summary_json,
            sort_keys=True,
        ),
    }


def test_operator_review_decision_hashes_notes_without_persisting_raw_notes(db_session) -> None:
    workflow = _open_workflow(db_session)
    notes = "bounded redacted issue summary"

    response = workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-notes",
        sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        review_decision="changes_requested",
        decision_reason_code="needs_packet_revision",
        decision_notes=notes,
    )

    assert response["decision_notes_present"] is True
    assert isinstance(response["decision_notes_hash"], str)
    assert len(response["decision_notes_hash"]) == 64
    assert notes not in json.dumps(response, sort_keys=True)
    row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    assert row.decision_notes_hash == response["decision_notes_hash"]
    assert notes not in json.dumps(row.decision_summary_json, sort_keys=True)


def test_operator_review_decision_requires_notes_for_non_approved(db_session) -> None:
    workflow = _open_workflow(db_session)

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-missing-notes",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="blocked",
            decision_reason_code="operator_blocked",
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_notes_required"
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_rejects_raw_note_reference(db_session) -> None:
    workflow = _open_workflow(db_session)

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-raw-note",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="rejected",
            decision_reason_code="redaction_gap",
            decision_notes="Contact operator@example.com about 123.45",
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_raw_reference_not_admitted"
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_replays_same_request_and_basis(db_session) -> None:
    workflow = _open_workflow(db_session)
    kwargs = {
        "sec_xbrl_operator_review_workflow_id": workflow["sec_xbrl_operator_review_workflow_id"],
        "review_decision": "approved",
        "decision_reason_code": "ready_for_next_freeze",
    }

    first = workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-replay",
        **kwargs,
    )
    second = workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-replay",
        **kwargs,
    )
    third = workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-replay-different-request",
        **kwargs,
    )

    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert third["idempotent_replay"] is True
    assert second["sec_xbrl_operator_review_decision_id"] == first["sec_xbrl_operator_review_decision_id"]
    assert third["sec_xbrl_operator_review_decision_id"] == first["sec_xbrl_operator_review_decision_id"]
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 1


def test_operator_review_decision_rejects_client_request_conflict(db_session) -> None:
    workflow = _open_workflow(db_session)
    workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-conflict",
        sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        review_decision="approved",
        decision_reason_code="ready_for_next_freeze",
    )

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-conflict",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="blocked",
            decision_reason_code="operator_blocked",
            decision_notes="bounded blocked reason",
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_client_request_conflict"


def test_operator_review_decision_rejects_second_decision_for_workflow(db_session) -> None:
    workflow = _open_workflow(db_session)
    workflow_service.record_redacted_operator_review_decision(
        db_session,
        client_request_id="decision-first",
        sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
        review_decision="approved",
        decision_reason_code="ready_for_next_freeze",
    )

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-second",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="blocked",
            decision_reason_code="operator_blocked",
            decision_notes="bounded blocked reason",
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_workflow_already_decided"
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 1


def test_operator_review_decision_rejects_mismatched_workflow_hash(db_session) -> None:
    workflow = _open_workflow(db_session)

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-mismatch",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            workflow_basis_hash=_hash("z"),
            review_decision="approved",
            decision_reason_code="ready_for_next_freeze",
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_workflow_not_found"
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_rejects_tampered_workflow_without_partial_row(db_session) -> None:
    workflow = _open_workflow(db_session)
    row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    row.review_summary_json = {**row.review_summary_json, "local_path": "C:\\\\raw\\\\packet.json"}
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-tampered",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="approved",
            decision_reason_code="ready_for_next_freeze",
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_raw_authority_not_admitted"
    assert db_session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_status_projection_is_read_only(db_session) -> None:
    decision = _record_decision(db_session, request_id="decision-status-source")
    workflow_row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    packet_row = db_session.query(L3SecXbrlStatementPacketSet).one()
    projection_row = db_session.query(L3SecXbrlProjectionSet).one()
    decision_row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    workflow_snapshot = _workflow_snapshot(workflow_row)
    packet_snapshot = _packet_snapshot(packet_row)
    projection_snapshot = _projection_snapshot(projection_row)
    decision_snapshot = _decision_snapshot(decision_row)

    status = workflow_service.inspect_redacted_operator_review_decision_status(
        db_session,
        client_request_id="decision-status-1",
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )

    assert status["schema_id"] == workflow_service.DECISION_STATUS_SCHEMA_ID
    assert status["request_id"] == "decision-status-1"
    assert status["status"] == "decision_recorded"
    assert status["mode"] == workflow_service.DECISION_STATUS_MODE
    assert status["operator_decision"] == workflow_service.DECISION_STATUS_OPERATOR_DECISION
    assert status["read_only_status_surface"] is True
    assert status["durable_decision_authority_used"] is True
    assert status["decision_status_api_route_enabled"] is True
    assert status["decision_submit_api_route_enabled"] is False
    assert status["runtime_default_enabled"] is False
    assert status["value_reveal_performed"] is False
    assert status["source_acquisition_performed"] is False
    assert status["arelle_invoked"] is False
    assert status["delivery_export_enabled"] is False
    assert status["rendered_ui_enabled"] is False
    assert status["operator_review_decision_recorded"] is True
    assert status["workflow_mutated"] is False
    assert status["statement_packet_mutated"] is False
    assert status["projection_mutated"] is False
    assert status["negative_invariants"]["raw_values_exposed"] is False
    assert status["negative_invariants"]["raw_operator_notes_exposed"] is False
    assert status["negative_invariants"]["residual_magnitudes_exposed"] is False
    assert status["decision_summary"]["review_decision"] == "approved"
    assert status["authority_refs"]["workflow_basis_hash"] == decision["workflow_basis_hash"]
    assert "inspect_operator_review_decision_status" in status["next_allowed_actions"]
    response_text = json.dumps(status, sort_keys=True)
    for forbidden in ("C:/", "https://www.sec.gov", "operator@example.com", "123.45"):
        assert forbidden not in response_text

    db_session.refresh(workflow_row)
    db_session.refresh(packet_row)
    db_session.refresh(projection_row)
    db_session.refresh(decision_row)
    assert _workflow_snapshot(workflow_row) == workflow_snapshot
    assert _packet_snapshot(packet_row) == packet_snapshot
    assert _projection_snapshot(projection_row) == projection_snapshot
    assert _decision_snapshot(decision_row) == decision_snapshot


def test_operator_review_decision_status_rejects_missing_authority(db_session) -> None:
    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-missing-authority",
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_status_authority_missing"
    assert exc.value.http_status == 400


def test_operator_review_decision_status_rejects_mismatched_decision_hash(db_session) -> None:
    decision = _record_decision(db_session, request_id="decision-status-mismatch-source")

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-mismatch",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
            decision_basis_hash=_hash("z"),
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_status_not_found"
    assert exc.value.http_status == 404


def test_operator_review_decision_status_rejects_tampered_raw_decision_summary(db_session) -> None:
    decision = _record_decision(db_session, request_id="decision-status-raw-summary-source")
    decision_row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    decision_row.decision_summary_json = {
        **decision_row.decision_summary_json,
        "local_path": "C:/raw/decision.json",
    }
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-raw-summary",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_raw_authority_not_admitted"


def test_operator_review_decision_status_rejects_residual_alias_in_decision_summary(db_session) -> None:
    decision = _record_decision(db_session, request_id="decision-status-mean-summary-source")
    decision_row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    decision_row.decision_summary_json = {
        **decision_row.decision_summary_json,
        "mean": "12345.67",
    }
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-mean-summary",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_residual_magnitudes_not_admitted"
    assert exc.value.details == {"field": "mean"}


def test_operator_review_decision_status_rejects_tampered_controls(db_session) -> None:
    decision = _record_decision(db_session, request_id="decision-status-control-source")
    decision_row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    decision_row.permitted_controls_after_decision_json = [
        *decision_row.permitted_controls_after_decision_json,
        "reveal_values",
    ]
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-control",
            decision_basis_hash=decision["decision_basis_hash"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_status_permitted_controls_invalid"


def test_operator_review_decision_status_rejects_invalid_notes_hash(db_session) -> None:
    decision = _record_decision(
        db_session,
        request_id="decision-status-notes-source",
        review_decision="blocked",
        decision_reason_code="operator_blocked",
        decision_notes="bounded blocked reason",
    )
    decision_row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    decision_row.decision_notes_hash = "short"
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-notes",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_status_notes_hash_invalid"


def test_operator_review_workflow_tables_are_registered_in_metadata() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    try:
        assert "l3_sec_xbrl_operator_review_workflow" in inspector.get_table_names()
        columns = {column["name"] for column in inspector.get_columns("l3_sec_xbrl_operator_review_workflow")}
        assert "sec_xbrl_statement_packet_set_id" in columns
        assert "workflow_basis_hash" in columns
        assert "permitted_controls_json" in columns
        assert "blocked_controls_json" in columns
        assert "l3_sec_xbrl_operator_review_decision" in inspector.get_table_names()
        decision_columns = {
            column["name"]
            for column in inspector.get_columns("l3_sec_xbrl_operator_review_decision")
        }
        assert "sec_xbrl_operator_review_workflow_id" in decision_columns
        assert "decision_basis_hash" in decision_columns
        assert "decision_notes_hash" in decision_columns
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_operator_review_workflow_migration_declares_additive_table() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location("migration_0040_sec_xbrl_operator_review", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0040_layer3_sec_xbrl_operator_review_workflow"
    assert module.down_revision == "0039_layer3_sec_xbrl_statement_packet_persistence"
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_operator_review_workflow" in source
    assert "drop_table_idempotent(\"l3_sec_xbrl_operator_review_workflow\")" in source


def test_operator_review_decision_migration_declares_additive_table() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0042_sec_xbrl_operator_review_decision",
        DECISION_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0042_layer3_sec_xbrl_operator_review_decision"
    assert module.down_revision == "0041_layer3_sec_xbrl_redaction_constraints"
    source = DECISION_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_operator_review_decision" in source
    assert "drop_table_idempotent(\"l3_sec_xbrl_operator_review_decision\")" in source


def _direct_packet_set(
    *,
    sec_xbrl_projection_set_id: str,
    source_projection_basis_hash: str,
    total_review_rows: int = 1,
    review_ready: bool = True,
) -> L3SecXbrlStatementPacketSet:
    return L3SecXbrlStatementPacketSet(
        sec_xbrl_projection_set_id=sec_xbrl_projection_set_id,
        client_request_id=f"direct-packet-{total_review_rows}-{review_ready}",
        packet_basis_hash=_hash("d"),
        packet_schema_id=assembly.STATEMENT_ASSEMBLY_SCHEMA_ID,
        source_projection_basis_hash=source_projection_basis_hash,
        source_projection_schema_id=projection_persistence.PROJECTION_SET_SCHEMA_ID,
        statement_organization_authority="canonical_statement_organization_contract_v1",
        value_policy=L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
        statement_count=1,
        total_review_rows=total_review_rows,
        provenance_complete_count=total_review_rows,
        review_exception_count=0,
        review_ready=review_ready,
        identity_rollup_json={},
        organization_contract_json={"contract_passed": True},
        packet_summary_json={"total_review_rows": total_review_rows},
        status="materialized",
    )
