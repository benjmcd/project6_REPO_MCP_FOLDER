from __future__ import annotations

from decimal import Decimal
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlStatementPacketSet,
)
from app.models.models import L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY
from app.services import layer3_sec_xbrl_operator_review_workflow as workflow_service
from app.services import layer3_sec_xbrl_projection_persistence as projection_persistence
from app.services import layer3_sec_xbrl_statement_assembly as assembly
from app.services import layer3_sec_xbrl_statement_packet_persistence as packet_persistence


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "backend" / "alembic" / "versions" / "0040_layer3_sec_xbrl_operator_review_workflow.py"


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
    second_packet = _materialized_packet(
        db_session,
        packet_request_id="packet-2",
        projection_request_id="projection-2",
        packet=_packet(review_exception_count=1),
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
