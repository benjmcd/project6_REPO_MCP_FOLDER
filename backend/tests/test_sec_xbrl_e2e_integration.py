from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import L3SecXbrlStatementPacketRow
from app.services import layer3_sec_xbrl_e2e_integration as integration
from app.services import layer3_sec_xbrl_operator_review_workflow as workflow_service
from app.services import layer3_sec_xbrl_projection_persistence as projection_persistence
from app.services import layer3_sec_xbrl_statement_packet_persistence as packet_persistence


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


def _private_projection(*, periods: int = 2, empty_periods: set[int] | None = None) -> dict[str, Any]:
    empty_periods = set(empty_periods or set())
    return {
        "status": "canonical_multi_period_projection_ready",
        "sector_family_presence": {
            "sector_class": "general",
            "present_family_ids": [],
            "present_family_count": 0,
            "presence_conditioned": True,
            "sic_used_as_gate": False,
            "activation_rule": "concept_presence_not_sic_gated",
            "reported_family_evidence": [],
        },
        "periods": [
            {
                "period_ref": f"fy-period-{period_index}",
                "period_index": period_index,
                "projection": {
                    "status": "canonical_projection_ready",
                    "dataset_version_id": "dv-redacted-1",
                    "sidecar_receipt_hash": _hash("b"),
                    "value_store_hash": _hash("c"),
                    "concepts": _private_period_rows(
                        period_index=period_index,
                        empty=period_index in empty_periods,
                    ),
                },
            }
            for period_index in range(1, periods + 1)
        ],
    }


def _private_period_rows(*, period_index: int, empty: bool = False) -> list[dict[str, Any]]:
    if empty:
        return [
            _absent_row("Revenue", "income"),
            _absent_row("TotalAssets", "balance"),
            _absent_row("OperatingCashFlow", "cashflow"),
        ]
    return [
        _private_row("Revenue", "income", period_index=period_index),
        _private_row("TotalAssets", "balance", period_index=period_index),
        _private_row("OperatingCashFlow", "cashflow", period_index=period_index),
    ]


def _private_row(canonical_id: str, statement: str, *, period_index: int) -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": "universal",
        "status": "projected_oracle_confirmed",
        "source_qname": f"us-gaap:{canonical_id}",
        "period_class": "FY",
        "oracle_confirmed": True,
        "mapping_method": "primary_taxonomy_sidecar_value_store_projection",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "unit_class": "monetary",
        "resolved_fact_id": f"fact-{canonical_id}-{period_index}",
        "sidecar_receipt_id": "sidecar-receipt-redacted",
        "sidecar_receipt_hash": _hash("b"),
        "value_store_hash": _hash("c"),
        "dataset_version_id": "dv-redacted-1",
        "provenance_complete": True,
        "_resolution_key": f"{canonical_id}[total]",
        "_value": Decimal("1"),
        "_unit": "USD",
        "_period_key": ("redacted-period-key", period_index),
    }


def _absent_row(canonical_id: str, statement: str) -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": "universal",
        "status": "legitimately_absent",
    }


def _statement_role_records(*, periods: int = 2) -> list[dict[str, Any]]:
    roles = {
        "Revenue": "income_statement",
        "TotalAssets": "balance_sheet",
        "OperatingCashFlow": "cash_flow_statement",
    }
    return [
        {
            "fact_id_or_order_key": f"fact-{canonical_id}-{period_index}",
            "statement_candidate_role": role,
        }
        for period_index in range(1, periods + 1)
        for canonical_id, role in roles.items()
    ]


def _identity_residuals_with_magnitudes() -> list[dict[str, Any]]:
    return [
        {
            "identity_id": f"identity-{index}",
            "status": "evaluated",
            "within_tolerance": True,
            "relative_magnitude": "0E+2",
            "residual_abs": "0",
        }
        for index in range(1, 5)
    ]


def test_redacted_projection_payload_strips_private_fields_and_materializes(db_session) -> None:
    payload = integration.redacted_projection_persistence_payload(_private_projection(periods=1))
    text = json.dumps(payload, sort_keys=True)

    assert not re.search(r'"(?:_value|_unit|_period_key|resolved_fact_id|sidecar_receipt_id)"\s*:', text)
    assert payload["periods"][0]["projection"]["concepts"][0]["value_redacted"] is True
    assert payload["periods"][0]["projection"]["concepts"][0]["resolved_fact_provenance_present"] is True

    response = projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id="projection-e2e-redacted",
        projection=payload,
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )

    assert response["status"] == "materialized"
    assert response["fact_count"] == 3
    assert response["source_acquisition_performed"] is False
    assert response["arelle_invoked"] is False


def test_redacted_projection_payload_skips_ready_empty_periods_and_fails_closed_when_all_empty(
    db_session,
) -> None:
    payload = integration.redacted_projection_persistence_payload(
        _private_projection(periods=2, empty_periods={2})
    )

    assert [(period["period_ref"], period["period_index"]) for period in payload["periods"]] == [
        ("fy-period-1", 1)
    ]

    response = projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id="projection-e2e-empty-period-skip",
        projection=payload,
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )

    assert response["status"] == "materialized"
    assert response["fact_count"] == 3

    with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
        integration.redacted_projection_persistence_payload(
            _private_projection(periods=2, empty_periods={1, 2})
        )

    assert exc.value.code == "sec_xbrl_e2e_integration_no_projected_facts"
    assert "at least one period with projected facts" in str(exc.value)
    assert exc.value.details == {"examined_absent_period_refs": ["fy-period-1", "fy-period-2"]}


def test_e2e_adapter_carries_multi_period_projection_to_workflow(db_session) -> None:
    private_projection = _private_projection(periods=2)
    projection_payload = integration.redacted_projection_persistence_payload(private_projection)
    projection_response = projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id="projection-e2e-flow",
        projection=projection_payload,
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )
    packet = integration.build_reviewable_statement_packet_from_projection(
        canonical_projection=private_projection,
        statement_role_view_records=_statement_role_records(periods=2),
    )

    assert packet["status"] == "statement_assembly_ready"
    assert packet["review_ready"] is True
    assert packet["total_review_rows"] == 6
    income_rows = next(item for item in packet["statements"] if item["statement"] == "income")["rows"]
    assert [(row["period_ref"], row["period_index"], row["statement_row_index"]) for row in income_rows] == [
        ("fy-period-1", 1, 1),
        ("fy-period-2", 2, 1),
    ]

    packet_response = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-e2e-flow",
        sec_xbrl_projection_set_id=projection_response["sec_xbrl_projection_set_id"],
        packet=packet,
    )
    workflow_response = workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id="workflow-e2e-flow",
        sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
    )

    persisted_income_rows = (
        db_session.query(L3SecXbrlStatementPacketRow)
        .filter(L3SecXbrlStatementPacketRow.statement == "income")
        .order_by(L3SecXbrlStatementPacketRow.period_index)
        .all()
    )
    assert [(row.period_ref, row.period_index, row.statement_row_index) for row in persisted_income_rows] == [
        ("fy-period-1", 1, 1),
        ("fy-period-2", 2, 1),
    ]
    assert packet_response["row_count"] == 6
    assert workflow_response["status"] == "review_ready"
    assert workflow_response["row_count"] == 6
    assert workflow_response["value_reveal_performed"] is False
    assert workflow_response["source_acquisition_performed"] is False
    assert workflow_response["arelle_invoked"] is False


def test_e2e_adapter_preserves_single_period_public_ref(db_session) -> None:
    private_projection = _private_projection(periods=1)["periods"][0]["projection"]
    private_projection["period_ref"] = "fy-2025"
    private_projection["period_index"] = 7

    projection_payload = integration.redacted_projection_persistence_payload(private_projection)
    assert [(period["period_ref"], period["period_index"]) for period in projection_payload["periods"]] == [
        ("fy-2025", 7)
    ]
    projection_response = projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id="projection-e2e-single-period-ref",
        projection=projection_payload,
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )

    packet = integration.build_reviewable_statement_packet_from_projection(
        canonical_projection=private_projection,
        statement_role_view_records=_statement_role_records(periods=1),
    )
    income_rows = next(item for item in packet["statements"] if item["statement"] == "income")["rows"]
    assert [(row["period_ref"], row["period_index"], row["statement_row_index"]) for row in income_rows] == [
        ("fy-2025", 7, 1)
    ]

    packet_response = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-e2e-single-period-ref",
        sec_xbrl_projection_set_id=projection_response["sec_xbrl_projection_set_id"],
        packet=packet,
    )

    assert packet_response["status"] == "materialized"
    assert packet_response["row_count"] == 3


def test_e2e_adapter_matches_projection_row_indexes_for_duplicate_period_refs(db_session) -> None:
    private_projection = _private_projection(periods=2)
    private_projection["periods"][1]["period_ref"] = "fy-period-1"
    projection_payload = integration.redacted_projection_persistence_payload(private_projection)
    projection_response = projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id="projection-e2e-duplicate-period-ref",
        projection=projection_payload,
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )

    packet = integration.build_reviewable_statement_packet_from_projection(
        canonical_projection=private_projection,
        statement_role_view_records=_statement_role_records(periods=2),
    )
    income_rows = next(item for item in packet["statements"] if item["statement"] == "income")["rows"]
    assert [(row["period_ref"], row["period_index"], row["statement_row_index"]) for row in income_rows] == [
        ("fy-period-1", 1, 1),
        ("fy-period-1", 2, 2),
    ]

    packet_response = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-e2e-duplicate-period-ref",
        sec_xbrl_projection_set_id=projection_response["sec_xbrl_projection_set_id"],
        packet=packet,
    )

    assert packet_response["status"] == "materialized"
    assert packet_response["row_count"] == 6


def test_statement_packet_bridge_redacts_residual_magnitudes_before_persistence(db_session) -> None:
    private_projection = _private_projection(periods=2)
    projection_payload = integration.redacted_projection_persistence_payload(private_projection)
    projection_response = projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id="projection-e2e-residuals-redacted",
        projection=projection_payload,
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )

    packet = integration.build_reviewable_statement_packet_from_projection(
        canonical_projection=private_projection,
        statement_role_view_records=_statement_role_records(periods=2),
        identity_residuals=_identity_residuals_with_magnitudes(),
    )
    text = json.dumps(packet, sort_keys=True)

    assert packet["status"] == "statement_assembly_ready"
    assert packet["review_ready"] is True
    assert packet["identity_rollup"] == {
        "identity_residual_count": 4,
        "identity_residual_evaluated_count": 4,
        "identity_residual_within_tolerance_count": 4,
        "identity_residual_failed_count": 0,
        "identity_residuals_within_tolerance": True,
    }
    assert "identity_residuals" not in packet["identity_rollup"]
    for key in integration.RESIDUAL_MAGNITUDE_KEYS:
        assert f'"{key}"' not in text

    packet_response = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-e2e-residuals-redacted",
        sec_xbrl_projection_set_id=projection_response["sec_xbrl_projection_set_id"],
        packet=packet,
    )

    assert packet_response["status"] == "materialized"
    assert packet_response["row_count"] == 6


def test_e2e_output_guard_rejects_residual_magnitude_keys() -> None:
    with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
        integration._reject_output_raw_or_local_authority({"identity_rollup": {"relative_magnitude": None}})

    assert exc.value.code == "sec_xbrl_e2e_integration_raw_output_not_admitted"
    assert exc.value.details == {"field": "relative_magnitude"}


def test_e2e_output_guard_preserves_raw_output_field_error_shape() -> None:
    with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
        integration._reject_output_raw_or_local_authority({"rows": [{"effective_value": "100"}]})

    assert exc.value.code == "sec_xbrl_e2e_integration_raw_output_not_admitted"
    assert exc.value.message == "SEC XBRL end-to-end integration output cannot carry raw values or raw authority."
    assert exc.value.details == {"field": "effective_value"}


def test_e2e_output_guard_rejects_period_date_strings() -> None:
    with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
        integration._reject_output_raw_or_local_authority({"period": "2025-12-31"})

    assert exc.value.code == "sec_xbrl_e2e_integration_raw_reference_not_admitted"
    assert exc.value.message == (
        "SEC XBRL end-to-end integration does not admit raw accession, SEC URL, period date, or local path strings."
    )
    assert exc.value.details == {"field": "value"}


def test_e2e_output_guard_rejects_cik_public_refs() -> None:
    for raw_reference in ("0000123456", "issuer 0000123456 packet", "CIK0000123456"):
        with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
            integration._reject_output_raw_or_local_authority({"summary": {"public_ref": raw_reference}})

        assert exc.value.code == "sec_xbrl_e2e_integration_raw_reference_not_admitted"
        assert exc.value.message == (
            "SEC XBRL end-to-end integration does not admit raw accession, SEC URL, period date, or local path strings."
        )
        assert exc.value.details == {"field": "value"}


def test_e2e_text_guard_rejects_contextual_cik_refs() -> None:
    with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
        integration._reject_public_text_patterns("issuer 0000123456 packet", field="receipt")

    assert exc.value.code == "sec_xbrl_e2e_integration_raw_reference_not_admitted"
    assert exc.value.details == {"field": "receipt"}


def test_e2e_text_guard_avoids_broad_cik_substring_match() -> None:
    integration._reject_public_text_patterns("batch 1000000000 archived", field="receipt")


def test_e2e_adapter_fails_closed_without_resolved_fact_authority(db_session) -> None:
    private_projection = _private_projection(periods=1)
    private_projection["periods"][0]["projection"]["concepts"][0]["resolved_fact_id"] = None

    with pytest.raises(integration.SecXbrlE2EIntegrationError) as exc:
        integration.redacted_projection_persistence_payload(private_projection)

    assert exc.value.code == "sec_xbrl_e2e_integration_resolved_fact_authority_missing"


def test_e2e_adapter_blocks_packet_when_statement_role_authority_missing() -> None:
    packet = integration.build_reviewable_statement_packet_from_projection(
        canonical_projection=_private_projection(periods=1),
        statement_role_view_records=[],
    )

    assert packet["status"] == "statement_assembly_blocked"
    assert packet["review_ready"] is False
    assert packet["blocking_reasons"] == [
        {
            "reason": "statement_organization_contract_not_passed",
            "contract_passed": False,
        }
    ]
