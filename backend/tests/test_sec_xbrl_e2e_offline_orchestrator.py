from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketRow,
    L3SecXbrlStatementPacketSet,
)
from app.services import layer3_sec_xbrl_e2e_offline_orchestrator as orchestrator
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


def test_offline_orchestrator_opens_redacted_review_workflow_from_governed_evidence(db_session) -> None:
    response = orchestrator.open_redacted_operator_review_from_offline_evidence(
        db_session,
        client_request_id="offline-orchestrator-redacted-flow",
        evidence=_evidence(),
        period_limit=2,
    )
    text = json.dumps(response, sort_keys=True)

    assert response["status"] == "review_ready"
    assert response["summary"]["period_count"] == 2
    assert response["summary"]["row_count"] == 6
    assert response["controls"] == {
        "offline_evidence_input_only": True,
        "file_read_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "api_route_enabled": False,
        "production_readiness_claimed": False,
    }
    assert response["containment"]["single_transaction_claimed"] is False
    assert "100" not in text
    assert "200" not in text
    assert "start-2" not in text

    persisted_cashflow_rows = (
        db_session.query(L3SecXbrlStatementPacketRow)
        .filter(L3SecXbrlStatementPacketRow.statement == "cashflow")
        .order_by(L3SecXbrlStatementPacketRow.period_index)
        .all()
    )
    assert [(row.period_ref, row.period_index, row.value_redacted) for row in persisted_cashflow_rows] == [
        ("fy-period-1", 1, True),
        ("fy-period-2", 2, True),
    ]
    assert db_session.query(L3SecXbrlProjectionSet).count() == 1
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 1
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1


def test_offline_orchestrator_requires_governed_sidecar_projection_before_persistence(db_session) -> None:
    evidence = _evidence()
    del evidence["sidecar_receipt"]["resolved_fact_projection"]

    with pytest.raises(orchestrator.SecXbrlE2EOfflineOrchestratorError) as exc:
        orchestrator.open_redacted_operator_review_from_offline_evidence(
            db_session,
            client_request_id="offline-orchestrator-missing-sidecar-projection",
            evidence=evidence,
            period_limit=2,
        )

    assert exc.value.code == "sec_xbrl_e2e_offline_orchestrator_required_sequence_missing"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


def test_offline_orchestrator_rejects_stale_value_store_hash_before_persistence(db_session) -> None:
    evidence = _evidence()
    evidence["value_store"]["value_store_hash"] = _hash("9")

    with pytest.raises(orchestrator.SecXbrlE2EOfflineOrchestratorError) as exc:
        orchestrator.open_redacted_operator_review_from_offline_evidence(
            db_session,
            client_request_id="offline-orchestrator-stale-value-store",
            evidence=evidence,
            period_limit=2,
        )

    assert exc.value.code == "sec_xbrl_e2e_offline_orchestrator_value_store_hash_mismatch"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0


def test_offline_orchestrator_rejects_unbound_statement_roles_before_persistence(db_session) -> None:
    evidence = _evidence()
    evidence["statement_role_view_records"] = [
        {"fact_id_or_order_key": "unbound-fact", "statement_candidate_role": "income_statement"}
    ]

    with pytest.raises(orchestrator.SecXbrlE2EOfflineOrchestratorError) as exc:
        orchestrator.open_redacted_operator_review_from_offline_evidence(
            db_session,
            client_request_id="offline-orchestrator-unbound-statement-roles",
            evidence=evidence,
            period_limit=2,
        )

    assert exc.value.code == "sec_xbrl_e2e_offline_orchestrator_statement_packet_blocked"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def _evidence() -> dict[str, Any]:
    sidecar_records = [
        _record(
            "rf-revenue-old",
            "us-gaap",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            start="start-1",
            end="end-1",
        ),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", end="end-1", instant=True),
        _record(
            "rf-cashflow-old",
            "us-gaap",
            "NetCashProvidedByUsedInOperatingActivities",
            "USD",
            start="start-1",
            end="end-1",
        ),
        _record(
            "rf-revenue-fy",
            "us-gaap",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            start="start-2",
            end="end-2",
        ),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
        _record(
            "rf-cashflow-fy",
            "us-gaap",
            "NetCashProvidedByUsedInOperatingActivities",
            "USD",
            start="start-2",
            end="end-2",
        ),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", end="end-2", instant=True),
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
        "companyfacts": _companyfacts_periods(
            [
                ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
                ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
                ("us-gaap", "Assets", "180", "USD", "", "end-1", True),
                ("us-gaap", "Assets", "200", "USD", "", "end-2", True),
                ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "30", "USD", "start-1", "end-1", False),
                ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "40", "USD", "start-2", "end-2", False),
            ]
        ),
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
        "statement_role_view_records": _statement_role_records(),
        "dataset_version_id": "dataset-redacted",
    }


def _companyfacts_periods(entries: list[tuple[str, str, str, str, str, str, bool]]) -> dict[str, Any]:
    facts: dict[str, dict[str, Any]] = {}
    for taxonomy, local_name, value, unit, start, end, instant in entries:
        facts.setdefault(taxonomy, {}).setdefault(local_name, {"units": {}})
        fact: dict[str, Any] = {"fp": "FY", "fy": "", "val": value, "end": end}
        if not instant:
            fact["start"] = start
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    start: str = "start-2",
    end: str = "end-2",
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


def _value(fact_id: str, effective_value: str) -> dict[str, Any]:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


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


def _statement_role_records() -> list[dict[str, str]]:
    return [
        {"fact_id_or_order_key": "rf-revenue-old", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-old", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-cashflow-old", "statement_candidate_role": "cash_flow_statement"},
        {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-cashflow-fy", "statement_candidate_role": "cash_flow_statement"},
    ]


def _hash(char: str) -> str:
    return char * 64
