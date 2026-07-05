from __future__ import annotations

import base64
import hashlib
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
    Dataset,
    DatasetVersion,
    L3SecXbrlAuthBindingReceipt,
    L3SecXbrlControlledValueRevealSubmitReceipt,
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketSet,
    L3SecXbrlValueRevealAuthorityReceipt,
)
from app.models.models import L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY
from app.services import layer3_sec_xbrl_auth_binding as auth_binding
from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy
from app.services import layer3_sec_xbrl_operator_review_workflow as workflow_service
from app.services import layer3_sec_xbrl_controlled_value_reveal_submit as submit_service
from app.services import layer3_sec_xbrl_projection_persistence as projection_persistence
from app.services import layer3_sec_xbrl_statement_assembly as assembly
from app.services import layer3_sec_xbrl_statement_packet_persistence as packet_persistence
from app.services import layer3_sec_xbrl_value_reveal_authority as authority_service
from main import app


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "backend" / "alembic" / "versions" / "0040_layer3_sec_xbrl_operator_review_workflow.py"
DECISION_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0042_layer3_sec_xbrl_operator_review_decision.py"
)
DECISION_SUBMIT_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit"
DECISION_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status"
AUTHORITY_PREPARE_ROUTE = "/api/v1/layer3/sec-xbrl/value-reveal/authority/prepare"
CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE = "/api/v1/layer3/sec-xbrl/value-reveal/submit"
WORKFLOW_OPEN_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open"
WORKFLOW_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/status"
WORKFLOW_STATUS_ROUTE_FAMILY = "sec_xbrl_operator_review_workflow_status_read"
WORKFLOW_OPEN_ROUTE_FAMILY = "sec_xbrl_operator_review_workflow_open_write"
DECISION_SUBMIT_ROUTE_FAMILY = "sec_xbrl_operator_review_decision_submit_write"
DECISION_STATUS_ROUTE_FAMILY = "sec_xbrl_operator_review_decision_status_read"
AUTHORITY_PREPARE_ROUTE_FAMILY = "sec_xbrl_value_reveal_authority_prepare_write"
CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE_FAMILY = "sec_xbrl_controlled_value_reveal_submit_write"
CONTROLLED_VALUE_REVEAL_STATUS_ROUTE_FAMILY = "sec_xbrl_controlled_value_reveal_submit_status_read"
AUTHORITY_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0044_layer3_sec_xbrl_value_reveal_authority_receipt.py"
)
SUBMIT_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0045_layer3_sec_xbrl_controlled_value_reveal_submit.py"
)
SUBMIT_HASH_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0053_layer3_sec_xbrl_controlled_submit_request_hash.py"
)
SUBMIT_PAGINATION_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0054_layer3_sec_xbrl_controlled_submit_pagination.py"
)


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


def _request_hash(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _projection_rows(
    *,
    sidecar_receipt_hash: str = _hash("b"),
    value_store_hash: str = _hash("c"),
    dataset_version_id: str = "dv-redacted-1",
) -> list[dict[str, Any]]:
    return [
        _projection_row(
            "Revenue",
            "income",
            sidecar_receipt_hash=sidecar_receipt_hash,
            value_store_hash=value_store_hash,
            dataset_version_id=dataset_version_id,
        ),
        _projection_row(
            "TotalAssets",
            "balance",
            sidecar_receipt_hash=sidecar_receipt_hash,
            value_store_hash=value_store_hash,
            dataset_version_id=dataset_version_id,
        ),
        _projection_row(
            "OperatingCashFlow",
            "cashflow",
            sidecar_receipt_hash=sidecar_receipt_hash,
            value_store_hash=value_store_hash,
            dataset_version_id=dataset_version_id,
        ),
    ]


def _projection_row(
    canonical_id: str,
    statement: str,
    *,
    family: str = "universal",
    sidecar_receipt_hash: str = _hash("b"),
    value_store_hash: str = _hash("c"),
    dataset_version_id: str = "dv-redacted-1",
) -> dict[str, Any]:
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
        "sidecar_receipt_hash": sidecar_receipt_hash,
        "value_store_hash": value_store_hash,
        "dataset_version_id": dataset_version_id,
    }


def _seed_dataset_version(db_session, *, dataset_version_id: str = "dv-redacted-1") -> None:
    dataset_id = "dataset-redacted-1"
    if db_session.get(Dataset, dataset_id) is None:
        db_session.add(
            Dataset(
                dataset_id=dataset_id,
                name="SEC XBRL redacted fixture dataset",
                description="Hash-only SEC XBRL authority fixture",
                domain_pack="sec-xbrl",
            )
        )
    if db_session.get(DatasetVersion, dataset_version_id) is None:
        db_session.add(
            DatasetVersion(
                dataset_version_id=dataset_version_id,
                dataset_id=dataset_id,
                version_label="redacted-fixture-v1",
                version_type="sec-xbrl-redacted",
                status="ready",
                storage_ref=None,
                row_count=3,
            )
        )
    db_session.flush()


def _persisted_projection(
    db_session,
    *,
    request_id: str = "projection-1",
    source_report_hash: str = _hash("a"),
    sidecar_receipt_hash: str = _hash("b"),
    value_store_hash: str = _hash("c"),
    dataset_version_id: str = "dv-redacted-1",
) -> dict[str, Any]:
    _seed_dataset_version(db_session, dataset_version_id=dataset_version_id)
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
                        "dataset_version_id": dataset_version_id,
                        "sidecar_receipt_hash": sidecar_receipt_hash,
                        "value_store_hash": value_store_hash,
                        "concepts": _projection_rows(
                            sidecar_receipt_hash=sidecar_receipt_hash,
                            value_store_hash=value_store_hash,
                            dataset_version_id=dataset_version_id,
                        ),
                    },
                }
            ],
        },
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=source_report_hash,
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
    projection_source_report_hash: str = _hash("a"),
    packet: dict[str, Any] | None = None,
    sidecar_receipt_hash: str = _hash("b"),
    value_store_hash: str = _hash("c"),
    dataset_version_id: str = "dv-redacted-1",
) -> dict[str, Any]:
    projection = _persisted_projection(
        db_session,
        request_id=projection_request_id,
        source_report_hash=projection_source_report_hash,
        sidecar_receipt_hash=sidecar_receipt_hash,
        value_store_hash=value_store_hash,
        dataset_version_id=dataset_version_id,
    )
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
    projection_source_report_hash: str = _hash("a"),
    sidecar_receipt_hash: str = _hash("b"),
    value_store_hash: str = _hash("c"),
    dataset_version_id: str = "dv-redacted-1",
) -> dict[str, Any]:
    packet_response = _materialized_packet(
        db_session,
        packet_request_id=packet_request_id,
        projection_request_id=projection_request_id,
        projection_source_report_hash=projection_source_report_hash,
        packet=packet,
        sidecar_receipt_hash=sidecar_receipt_hash,
        value_store_hash=value_store_hash,
        dataset_version_id=dataset_version_id,
    )
    return workflow_service.open_redacted_operator_review_workflow(
        db_session,
        client_request_id=request_id,
        sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
    )


def _policy(route_family: str, *, role: str = auth_policy.OWNER_ROLE) -> dict[str, Any]:
    return auth_policy.authorize_sec_xbrl_route(
        headers={},
        route_family=route_family,
        requested_role=role,
        request_fields={},
    )


def _bind_source(
    db_session,
    *,
    client_request_id: str,
    source_receipt_kind: str,
    source_receipt_id: str,
    source_receipt_basis_hash: str,
    route_family: str,
    role: str = auth_policy.OWNER_ROLE,
) -> dict[str, Any]:
    return auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id=auth_policy.binding_client_request_id(
            client_request_id=client_request_id,
            route_family=route_family,
        ),
        source_receipt_kind=source_receipt_kind,
        source_receipt_id=source_receipt_id,
        source_receipt_basis_hash=source_receipt_basis_hash,
        route_family=route_family,
        policy_decision=_policy(route_family, role=role),
    )


def _bind_workflow(
    db_session,
    workflow: dict[str, Any],
    *,
    route_family: str = DECISION_SUBMIT_ROUTE_FAMILY,
) -> dict[str, Any]:
    return _bind_source(
        db_session,
        client_request_id=f"{workflow['client_request_id']}-{route_family}",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow["sec_xbrl_operator_review_workflow_id"],
        source_receipt_basis_hash=workflow["workflow_basis_hash"],
        route_family=route_family,
    )


def _bind_decision(
    db_session,
    decision: dict[str, Any],
    *,
    route_family: str = DECISION_SUBMIT_ROUTE_FAMILY,
) -> dict[str, Any]:
    return _bind_source(
        db_session,
        client_request_id=f"{decision['client_request_id']}-{route_family}",
        source_receipt_kind="operator_review_decision",
        source_receipt_id=decision["sec_xbrl_operator_review_decision_id"],
        source_receipt_basis_hash=decision["decision_basis_hash"],
        route_family=route_family,
    )


def _bind_authority(
    db_session,
    authority: dict[str, Any],
    *,
    route_family: str = AUTHORITY_PREPARE_ROUTE_FAMILY,
) -> dict[str, Any]:
    return _bind_source(
        db_session,
        client_request_id=f"{authority['client_request_id']}-{route_family}",
        source_receipt_kind="value_reveal_authority",
        source_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        source_receipt_basis_hash=authority["authority_basis_hash"],
        route_family=route_family,
    )


def _bind_submit(
    db_session,
    submit: dict[str, Any],
    *,
    route_family: str = CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE_FAMILY,
) -> dict[str, Any]:
    return _bind_source(
        db_session,
        client_request_id=(
            f"controlled-submit-{submit['client_request_id_hash'][:24]}-{route_family}"
        ),
        source_receipt_kind="controlled_value_reveal_submit",
        source_receipt_id=submit["sec_xbrl_controlled_value_reveal_submit_receipt_id"],
        source_receipt_basis_hash=submit["submit_basis_hash"],
        route_family=route_family,
    )


def _force_auth_binding_failure(monkeypatch, *, source_receipt_kind: str) -> None:
    original = auth_binding.record_sec_xbrl_auth_binding

    def fail_for_source_kind(db_session, *args: Any, **kwargs: Any):
        if kwargs.get("source_receipt_kind") == source_receipt_kind:
            raise auth_binding.SecXbrlAuthBindingError(
                "sec_xbrl_auth_binding_forced_failure",
                "Forced auth-binding failure for atomic receipt rollback proof.",
                http_status=409,
            )
        return original(db_session, *args, **kwargs)

    monkeypatch.setattr(auth_binding, "record_sec_xbrl_auth_binding", fail_for_source_kind)


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


def _authority_payload(decision: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload = {
        "client_request_id": "value-reveal-authority-api",
        "authority_mode": authority_service.AUTHORITY_MODE,
        "operator_decision": authority_service.AUTHORITY_OPERATOR_DECISION,
        "sec_xbrl_operator_review_decision_id": decision["sec_xbrl_operator_review_decision_id"],
        "decision_basis_hash": decision["decision_basis_hash"],
    }
    payload.update(overrides)
    return payload


def _sidecar_authority() -> dict[str, str]:
    return {
        "sidecar_receipt_id_hash": _hash("d"),
        "sidecar_receipt_hash": _hash("b"),
        "value_store_hash": _hash("c"),
    }


def _enable_controlled_submit(monkeypatch) -> None:
    monkeypatch.setattr(
        submit_service.settings,
        "layer3_sec_xbrl_controlled_value_reveal_submit_enabled",
        True,
    )


def _submit_sidecar_and_value_store(
    *,
    effective_value: str = "123.45",
    lexical_value: str = "123.45",
) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar = {
        "sidecar_receipt_id": "sec-edgar-arelle-resolved-fact-authority-server-owned",
        "sidecar_receipt_hash": _hash("b"),
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_records": [
            {
                "resolved_fact_id": "resolved-fact-1",
                "source_order": 1,
                "entry_document_index": 1,
                "value_hash": _hash("v"),
                "concept": {
                    "qname": "us-gaap:Revenue",
                    "local_name": "Revenue",
                    "standard": True,
                    "extension": False,
                },
                "period": {"type": "duration", "start": "2026-01-01", "end": "2026-03-31"},
                "unit": {"currency": "USD", "resolved": True},
                "dimensions": {},
                "hidden": False,
                "continued": False,
            }
        ],
    }
    value_store = {
        "value_store_hash": _hash("c"),
        "value_records": [
            {
                "resolved_fact_id": "resolved-fact-1",
                "effective_value": effective_value,
                "lexical_value": lexical_value,
                "effective_value_hash": _hash("v"),
                "value_semantics": "arelle_effective_canonical_value_v1",
                "transform": {"scale": "0", "decimals": "2"},
            }
        ],
    }
    return sidecar, value_store


def _paginated_submit_sidecar_and_value_store(
    count: int,
    *,
    redacted_indices: set[int] | None = None,
    sidecar_receipt_id: str = "sec-edgar-arelle-resolved-fact-authority-server-owned",
    sidecar_receipt_hash: str = _hash("b"),
    value_store_hash: str = _hash("c"),
    record_prefix: str = "resolved-fact",
    concept_prefix: str = "PaginatedFact",
    value_hash_prefix: str = "value",
    value_base: int = 1000,
) -> tuple[dict[str, Any], dict[str, Any]]:
    redacted_indices = redacted_indices or set()
    sidecar_records: list[dict[str, Any]] = []
    value_records: list[dict[str, Any]] = []
    for index in range(count):
        resolved_fact_id = f"{record_prefix}-{index:04d}"
        value_hash = _request_hash(f"{value_hash_prefix}-{index}")
        source_order = count - index
        value = "0000123456-26-000001" if index in redacted_indices else f"{value_base + index}.01"
        sidecar_records.append(
            {
                "resolved_fact_id": resolved_fact_id,
                "source_order": source_order,
                "entry_document_index": index % 3,
                "value_hash": value_hash,
                "concept": {
                    "qname": f"us-gaap:{concept_prefix}{index:04d}",
                    "local_name": f"{concept_prefix}{index:04d}",
                    "standard": True,
                    "extension": False,
                },
                "period": {"type": "duration", "start": "2026-01-01", "end": "2026-12-31"},
                "unit": {"currency": "USD", "resolved": True},
                "dimensions": {},
                "hidden": False,
                "continued": False,
            }
        )
        value_records.append(
            {
                "resolved_fact_id": resolved_fact_id,
                "effective_value": value,
                "lexical_value": value,
                "effective_value_hash": value_hash,
                "value_semantics": "arelle_effective_canonical_value_v1",
                "transform": {"scale": "0", "decimals": "2"},
            }
        )
    return (
        {
            "sidecar_receipt_id": sidecar_receipt_id,
            "sidecar_receipt_hash": sidecar_receipt_hash,
            "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
            "resolved_fact_records": sidecar_records,
        },
        {
            "value_store_hash": value_store_hash,
            "value_records": value_records,
        },
    )


def _write_ready_sidecar_fixture(storage_dir: Path) -> tuple[str, str]:
    sidecar = authority_service.layer3_sec_xbrl_sidecar
    sidecar_hash = _hash("b")
    receipt_id = f"{sidecar.RECEIPT_PREFIX}-{sidecar_hash[:24]}"
    value_records = [
        {
            "resolved_fact_id": "resolved-fact-1",
            "effective_value": "123.45",
            "lexical_value": "123.45",
            "effective_value_hash": _hash("v"),
            "value_semantics": sidecar.VALUE_SEMANTICS_ID,
            "transform": {"decimals": "2", "scale": "0"},
        }
    ]
    value_store_hash = sidecar.stable_hash(value_records)
    receipt = {
        "schema_id": sidecar.SCHEMA_ID,
        "schema_version": sidecar.SCHEMA_VERSION,
        "sidecar_mode": sidecar.SIDECAR_MODE,
        "operator_decision": sidecar.OPERATOR_DECISION,
        "sidecar_state": sidecar.READY_STATE,
        "sidecar_receipt_id": receipt_id,
        "sidecar_receipt_ref": f"{sidecar.RECEIPT_PREFIX}:{sidecar_hash[:24]}",
        "sidecar_receipt_hash": sidecar_hash,
        "internal_value_store": {
            "schema_id": sidecar.INTERNAL_VALUE_STORE_SCHEMA_ID,
            "store_state": "persisted",
            "value_store_hash": value_store_hash,
            "value_record_count": len(value_records),
        },
        "resolved_fact_projection": [{"fact_ref_hash": _hash("e")}],
    }
    root = storage_dir / sidecar.RECEIPT_DIR
    receipt_path = root / "receipts" / f"{receipt_id}.json"
    value_store_path = root / sidecar.INTERNAL_VALUE_STORE_DIR / f"{receipt_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    value_store_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    value_store_path.write_text(
        json.dumps(
            {
                "schema_id": sidecar.INTERNAL_VALUE_STORE_SCHEMA_ID,
                "schema_version": sidecar.SCHEMA_VERSION,
                "sidecar_receipt_id": receipt_id,
                "sidecar_receipt_hash": sidecar_hash,
                "value_store_hash": value_store_hash,
                "value_record_count": len(value_records),
                "value_semantics": sidecar.VALUE_SEMANTICS_ID,
                "value_records": value_records,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sidecar_hash, value_store_hash


def _prepare_authority_receipt(db_session, monkeypatch, *, request_id: str = "controlled-submit-authority"):
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    decision = _record_decision(db_session, request_id=f"{request_id}-decision")
    return authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id=request_id,
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )


def _sidecar_receipt_id_for_hash(sidecar_receipt_hash: str) -> str:
    return f"{authority_service.layer3_sec_xbrl_sidecar.RECEIPT_PREFIX}-{sidecar_receipt_hash[:24]}"


def _sidecar_authority_for(sidecar_receipt_hash: str, value_store_hash: str) -> dict[str, str]:
    sidecar_receipt_id = _sidecar_receipt_id_for_hash(sidecar_receipt_hash)
    return {
        "sidecar_receipt_id_hash": authority_service.stable_hash(
            {
                "hash_version": "sec_xbrl_value_reveal_authority_sidecar_receipt_id_hash_v1",
                "sidecar_receipt_id": sidecar_receipt_id,
            }
        ),
        "sidecar_receipt_hash": sidecar_receipt_hash,
        "value_store_hash": value_store_hash,
    }


def _prepare_authority_receipt_with_projection(
    db_session,
    *,
    request_id: str,
    sidecar_receipt_hash: str,
    value_store_hash: str,
    dataset_version_id: str = "dv-redacted-1",
) -> dict[str, Any]:
    workflow = _open_workflow(
        db_session,
        request_id=f"{request_id}-workflow",
        packet_request_id=f"{request_id}-packet",
        projection_request_id=f"{request_id}-projection",
        projection_source_report_hash=_request_hash(f"{request_id}-source-report"),
        sidecar_receipt_hash=sidecar_receipt_hash,
        value_store_hash=value_store_hash,
        dataset_version_id=dataset_version_id,
    )
    decision = _record_decision(
        db_session,
        workflow=workflow,
        request_id=f"{request_id}-decision",
        decision_notes=f"approved synthetic reveal authority {request_id}",
    )
    return authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id=request_id,
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )


def _multi_authority_paginated_cases(
    db_session,
    monkeypatch,
    *,
    authority_count: int,
    records_per_authority: int,
) -> list[dict[str, Any]]:
    monkeypatch.setattr(
        authority_service,
        "_resolve_sidecar_authority",
        lambda sidecar_hash, value_hash: _sidecar_authority_for(sidecar_hash, value_hash),
    )
    payloads_by_authority_id: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    cases: list[dict[str, Any]] = []
    for authority_index in range(authority_count):
        prefix = f"controlled-submit-isolation-{authority_index:02d}"
        sidecar_receipt_hash = _request_hash(f"{prefix}-sidecar")
        value_store_hash = _request_hash(f"{prefix}-value-store")
        authority = _prepare_authority_receipt_with_projection(
            db_session,
            request_id=f"{prefix}-authority",
            sidecar_receipt_hash=sidecar_receipt_hash,
            value_store_hash=value_store_hash,
            dataset_version_id=f"dv-redacted-isolation-{authority_index:02d}",
        )
        value_base = 10000 + (authority_index * 100)
        sidecar, value_store = _paginated_submit_sidecar_and_value_store(
            records_per_authority,
            sidecar_receipt_id=_sidecar_receipt_id_for_hash(sidecar_receipt_hash),
            sidecar_receipt_hash=sidecar_receipt_hash,
            value_store_hash=value_store_hash,
            record_prefix=f"isolation-{authority_index:02d}-fact",
            concept_prefix=f"Isolation{authority_index:02d}Fact",
            value_hash_prefix=f"isolation-{authority_index:02d}-value",
            value_base=value_base,
        )
        authority_id = authority["sec_xbrl_value_reveal_authority_receipt_id"]
        payloads_by_authority_id[authority_id] = (sidecar, value_store)
        cases.append(
            {
                "authority": authority,
                "sidecar_receipt_hash": sidecar_receipt_hash,
                "value_store_hash": value_store_hash,
                "value_texts": {f"{value_base + index}.01" for index in range(records_per_authority)},
            }
        )

    def resolve_sidecar_and_value_store(row):
        return payloads_by_authority_id[row.sec_xbrl_value_reveal_authority_receipt_id]

    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", resolve_sidecar_and_value_store)
    return cases


def _submit_paginated_case_page(
    db_session,
    case: dict[str, Any],
    *,
    client_request_id: str,
    max_records: int,
    page_cursor: str | None = None,
) -> dict[str, Any]:
    authority = case["authority"]
    kwargs: dict[str, Any] = {}
    if page_cursor is not None:
        kwargs["page_cursor"] = page_cursor
    return submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id=client_request_id,
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
        max_records=max_records,
        **kwargs,
    )


def _controlled_submit_payload(authority: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    payload = {
        "client_request_id": "controlled-value-reveal-submit-api",
        "submit_mode": submit_service.SUBMIT_MODE,
        "operator_decision": submit_service.SUBMIT_OPERATOR_DECISION,
        "sec_xbrl_value_reveal_authority_receipt_id": authority[
            "sec_xbrl_value_reveal_authority_receipt_id"
        ],
        "authority_basis_hash": authority["authority_basis_hash"],
        "operator_reveal_confirmation": True,
    }
    payload.update(overrides)
    return payload


def test_value_reveal_authority_resolves_sidecar_and_internal_value_store(monkeypatch) -> None:
    calls: dict[str, bool] = {}

    def read_receipt(receipt_id: str, *, expected_sidecar_receipt_hash: str | None = None) -> dict[str, Any]:
        assert receipt_id == f"sec-edgar-arelle-resolved-fact-authority-{_hash('b')[:24]}"
        assert expected_sidecar_receipt_hash == _hash("b")
        calls["receipt"] = True
        return {
            "sidecar_receipt_id": receipt_id,
            "sidecar_receipt_hash": _hash("b"),
            "sidecar_state": authority_service.layer3_sec_xbrl_sidecar.READY_STATE,
            "internal_value_store": {"value_store_hash": _hash("c")},
            "resolved_fact_projection": [{"fact_ref_hash": _hash("e")}],
        }

    def read_value_store(receipt: dict[str, Any]) -> dict[str, Any]:
        assert receipt["sidecar_receipt_hash"] == _hash("b")
        calls["value_store"] = True
        return {"value_store_hash": _hash("c"), "value_records": [{"_value": "123.45"}]}

    monkeypatch.setattr(
        authority_service.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt",
        read_receipt,
    )
    monkeypatch.setattr(
        authority_service.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_internal_value_store",
        read_value_store,
    )

    response = authority_service._resolve_sidecar_authority(_hash("b"), _hash("c"))

    assert calls == {"receipt": True, "value_store": True}
    assert response["sidecar_receipt_hash"] == _hash("b")
    assert response["value_store_hash"] == _hash("c")
    assert "sidecar_receipt_id" not in response
    assert "_value" not in json.dumps(response)


def test_value_reveal_authority_accepts_real_sidecar_ready_state(tmp_path, monkeypatch) -> None:
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(authority_service.layer3_sec_xbrl_sidecar.settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        authority_service.layer3_sec_xbrl_sidecar.settings,
        "layer3_sec_xbrl_storage_root_hygiene_override_ack",
        True,
        raising=False,
    )
    sidecar_hash, value_store_hash = _write_ready_sidecar_fixture(storage_dir)

    response = authority_service._resolve_sidecar_authority(sidecar_hash, value_store_hash)

    assert response["sidecar_receipt_hash"] == sidecar_hash
    assert response["value_store_hash"] == value_store_hash
    assert "sidecar_receipt_id" not in response
    assert "_value" not in json.dumps(response)


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
    assert status["open_workflow_api_route_enabled"] is True
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
        _bind_workflow(session, workflow, route_family=WORKFLOW_STATUS_ROUTE_FAMILY)

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
    assert body["auth_binding_required"] is True
    assert body["auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["auth_binding_route_family"] == WORKFLOW_STATUS_ROUTE_FAMILY
    assert body["open_workflow_api_route_enabled"] is True
    assert body["rendered_ui_enabled"] is False
    assert body["operator_review_decision_recorded"] is False
    assert body["negative_invariants"]["raw_values_exposed"] is False
    assert "C:/" not in response.text
    assert "https://www.sec.gov" not in response.text


def test_operator_review_workflow_status_api_requires_auth_binding_for_existing_workflow(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-api-unbound")

    response = client.post(
        "/api/v1/layer3/sec-xbrl/operator-review/workflow/status",
        json={
            "client_request_id": "workflow-status-api-unbound",
            "status_mode": workflow_service.WORKFLOW_STATUS_MODE,
            "operator_decision": workflow_service.WORKFLOW_STATUS_OPERATOR_DECISION,
            "sec_xbrl_operator_review_workflow_id": workflow["sec_xbrl_operator_review_workflow_id"],
            "workflow_basis_hash": workflow["workflow_basis_hash"],
        },
    )

    assert response.status_code == 404, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_auth_binding_missing"
    assert body["status"] == "blocked"
    assert "C:/" not in response.text
    assert "https://www.sec.gov" not in response.text
    assert "123.45" not in response.text


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
        _bind_workflow(session, workflow)
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
    assert body["request_id"] == "decision-submit-api-success"
    assert body["status"] == "decision_recorded"
    assert body["review_decision"] == "approved"
    assert body["decision_reason_code"] == "ready_for_next_freeze"
    assert body["decision_submit_api_route_enabled"] is True
    assert body["auth_binding_required"] is True
    assert body["auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["auth_binding_route_family"] == DECISION_SUBMIT_ROUTE_FAMILY
    assert body["source_auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["api_route_enabled"] is False
    assert body["workflow_open_api_route_enabled"] is True
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
        assert session.query(L3SecXbrlAuthBindingReceipt).count() == 2
        assert _workflow_snapshot(session.query(L3SecXbrlOperatorReviewWorkflow).one()) == workflow_snapshot
        assert _packet_snapshot(session.query(L3SecXbrlStatementPacketSet).one()) == packet_snapshot
        assert _projection_snapshot(session.query(L3SecXbrlProjectionSet).one()) == projection_snapshot


def test_operator_review_decision_submit_api_rolls_back_source_receipt_when_binding_fails(
    api_client,
    monkeypatch,
) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-binding-fail")
        _bind_workflow(session, workflow)

    _force_auth_binding_failure(monkeypatch, source_receipt_kind="operator_review_decision")

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(workflow, client_request_id="decision-submit-api-binding-fail"),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "sec_xbrl_auth_binding_forced_failure"
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 0
        assert session.query(L3SecXbrlAuthBindingReceipt).count() == 1


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

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_operator_review_decision_request_fields_not_admitted"
    assert body["blocked_fields"] == []
    assert "123.45" not in response.text
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
        _bind_workflow(session, workflow)

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
        _bind_workflow(session, workflow)

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


def test_operator_review_decision_submit_api_rejects_raw_note_cik(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-raw-note-cik")
        _bind_workflow(session, workflow)

    response = client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(
            workflow,
            client_request_id="decision-submit-api-raw-note-cik",
            review_decision="rejected",
            decision_reason_code="authority_gap",
            decision_notes="See filer 0000123456 in local notes",
        ),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_operator_review_workflow_raw_reference_not_admitted"
    assert "0000123456" not in response.text
    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 0


def test_operator_review_decision_submit_api_replays_same_request_and_basis(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-replay")
        _bind_workflow(session, workflow)
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
        assert session.query(L3SecXbrlAuthBindingReceipt).count() == 2


def test_operator_review_decision_submit_api_rejects_second_decision_for_workflow(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        workflow = _open_workflow(session, request_id="workflow-decision-api-second")
        _bind_workflow(session, workflow)

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
        _bind_decision(session, decision)
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
    assert body["auth_binding_required"] is True
    assert body["auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["auth_binding_route_family"] == DECISION_SUBMIT_ROUTE_FAMILY
    assert body["decision_submit_api_route_enabled"] is False
    assert body["workflow_open_api_route_enabled"] is True
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
    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="workflow-same-basis",
            sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
        )

    assert second["idempotent_replay"] is True
    assert second["sec_xbrl_operator_review_workflow_id"] == first["sec_xbrl_operator_review_workflow_id"]
    assert exc.value.code == "sec_xbrl_operator_review_workflow_basis_replay_request_mismatch"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1


def test_operator_review_workflow_rejects_client_request_conflict(db_session) -> None:
    first_packet = _materialized_packet(db_session)
    changed_packet = _packet()
    changed_packet["organization_contract"]["a_role_unknown_count"] = 1
    second_packet = _materialized_packet(
        db_session,
        packet_request_id="packet-2",
        projection_request_id="projection-1",
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


def test_operator_review_workflow_rejects_local_ref_client_request_id(db_session) -> None:
    packet_response = _materialized_packet(db_session)

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.open_redacted_operator_review_workflow(
            db_session,
            client_request_id="/workspace/project/runtime/sec/workflow.json",
            sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_raw_reference_not_admitted"
    assert db_session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0


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


def test_operator_review_decision_rejects_reason_mismatch(db_session) -> None:
    workflow = _open_workflow(db_session)

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-reason-mismatch",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="approved",
            decision_reason_code="redaction_gap",
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_reason_mismatch"
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


def test_operator_review_decision_rejects_raw_note_local_path_and_cik(db_session) -> None:
    workflow = _open_workflow(db_session)

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-raw-note-local",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="blocked",
            decision_reason_code="operator_blocked",
            decision_notes="Review /workspace/project/sec and filer 0000123456",
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
    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-replay-different-request",
            **kwargs,
        )

    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert second["sec_xbrl_operator_review_decision_id"] == first["sec_xbrl_operator_review_decision_id"]
    assert exc.value.code == "sec_xbrl_operator_review_decision_basis_replay_request_mismatch"
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


def test_operator_review_decision_recomputes_workflow_basis_before_recording(db_session) -> None:
    workflow = _open_workflow(db_session)
    row = db_session.query(L3SecXbrlOperatorReviewWorkflow).one()
    row.row_count = row.row_count + 1
    row.review_summary_json = {**row.review_summary_json, "row_count": row.row_count}
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.record_redacted_operator_review_decision(
            db_session,
            client_request_id="decision-tampered-basis",
            sec_xbrl_operator_review_workflow_id=workflow["sec_xbrl_operator_review_workflow_id"],
            review_decision="approved",
            decision_reason_code="ready_for_next_freeze",
        )

    assert exc.value.code == "sec_xbrl_operator_review_workflow_status_basis_hash_invalid"
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


def test_operator_review_decision_status_rejects_reason_mismatch(db_session) -> None:
    decision = _record_decision(db_session, request_id="decision-status-reason-source")
    decision_row = db_session.query(L3SecXbrlOperatorReviewDecision).one()
    decision_row.decision_reason_code = "redaction_gap"
    decision_row.decision_summary_json = {
        **decision_row.decision_summary_json,
        "decision_reason_code": "redaction_gap",
    }
    db_session.commit()

    with pytest.raises(workflow_service.SecXbrlOperatorReviewWorkflowError) as exc:
        workflow_service.inspect_redacted_operator_review_decision_status(
            db_session,
            client_request_id="decision-status-reason-mismatch",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        )

    assert exc.value.code == "sec_xbrl_operator_review_decision_reason_mismatch"


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


def test_value_reveal_authority_prepares_hash_only_receipt(db_session, monkeypatch) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    decision = _record_decision(db_session, request_id="authority-decision-source")

    response = authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id="authority-prepare-1",
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )

    assert response["schema_id"] == authority_service.AUTHORITY_SCHEMA_ID
    assert response["authority_mode"] == authority_service.AUTHORITY_MODE
    assert response["eligible_for_explicit_value_reveal"] is True
    assert response["next_allowed_actions"] == [authority_service.NEXT_ALLOWED_ACTION]
    assert response["sidecar_receipt_id_hash"] == _hash("d")
    assert "sidecar_receipt_id" not in response
    assert response["value_reveal_performed"] is False
    assert response["runtime_default_enabled"] is False
    assert response["source_acquisition_performed"] is False
    assert response["arelle_invoked"] is False
    assert response["rendered_ui_enabled"] is False
    assert response["negative_invariants"]["raw_values_persisted"] is False

    row = db_session.query(L3SecXbrlValueRevealAuthorityReceipt).one()
    assert row.authority_basis_hash == response["authority_basis_hash"]
    assert row.sidecar_receipt_id_hash == _hash("d")
    assert row.sidecar_receipt_hash == _hash("b")
    assert row.value_store_hash == _hash("c")
    assert row.authority_summary_json["raw_sidecar_receipt_id_persisted"] is False


def test_value_reveal_authority_replays_same_authority_basis(db_session, monkeypatch) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    decision = _record_decision(db_session, request_id="authority-replay-decision-source")

    first = authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id="authority-replay-1",
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )
    second = authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id="authority-replay-2",
        sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=decision["decision_basis_hash"],
    )

    assert second["idempotent_replay"] is True
    assert second["sec_xbrl_value_reveal_authority_receipt_id"] == first["sec_xbrl_value_reveal_authority_receipt_id"]
    assert db_session.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 1


def test_value_reveal_authority_rejects_non_approved_decision(db_session, monkeypatch) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    decision = _record_decision(
        db_session,
        request_id="authority-blocked-decision-source",
        review_decision="blocked",
        decision_reason_code="operator_blocked",
        decision_notes="bounded blocked reason",
    )

    with pytest.raises(authority_service.SecXbrlValueRevealAuthorityError) as exc:
        authority_service.prepare_value_reveal_authority_receipt(
            db_session,
            client_request_id="authority-blocked-decision",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
            decision_basis_hash=decision["decision_basis_hash"],
        )

    assert exc.value.code == "sec_xbrl_value_reveal_authority_decision_not_approved"
    assert db_session.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 0


def test_value_reveal_authority_rejects_missing_dataset_version(db_session, monkeypatch) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    decision = _record_decision(db_session, request_id="authority-missing-dataset-source")
    db_session.query(DatasetVersion).delete()
    db_session.commit()

    with pytest.raises(authority_service.SecXbrlValueRevealAuthorityError) as exc:
        authority_service.prepare_value_reveal_authority_receipt(
            db_session,
            client_request_id="authority-missing-dataset",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
            decision_basis_hash=decision["decision_basis_hash"],
        )

    assert exc.value.code == "sec_xbrl_value_reveal_authority_dataset_version_missing"
    assert db_session.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 0


def test_value_reveal_authority_rejects_missing_sidecar_without_partial_row(db_session, monkeypatch) -> None:
    def missing_sidecar(*_args):
        raise authority_service.SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_sidecar_missing",
            "missing sidecar",
        )

    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", missing_sidecar)
    decision = _record_decision(db_session, request_id="authority-missing-sidecar-source")

    with pytest.raises(authority_service.SecXbrlValueRevealAuthorityError) as exc:
        authority_service.prepare_value_reveal_authority_receipt(
            db_session,
            client_request_id="authority-missing-sidecar",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
            decision_basis_hash=decision["decision_basis_hash"],
        )

    assert exc.value.code == "sec_xbrl_value_reveal_authority_sidecar_missing"
    assert db_session.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 0


def test_value_reveal_authority_rejects_raw_attestation(db_session, monkeypatch) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    decision = _record_decision(db_session, request_id="authority-raw-attestation-source")

    with pytest.raises(authority_service.SecXbrlValueRevealAuthorityError) as exc:
        authority_service.prepare_value_reveal_authority_receipt(
            db_session,
            client_request_id="authority-raw-attestation",
            sec_xbrl_operator_review_decision_id=decision["sec_xbrl_operator_review_decision_id"],
            decision_basis_hash=decision["decision_basis_hash"],
            operator_attestation="operator@example.com approved",
        )

    assert exc.value.code == "sec_xbrl_value_reveal_authority_raw_attestation_not_admitted"
    assert db_session.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 0


def test_value_reveal_authority_api_records_hash_only_receipt(api_client, monkeypatch) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    client, Session = api_client
    with Session() as db:
        decision = _record_decision(db, request_id="authority-api-decision-source")
        _bind_decision(db, decision)

    response = client.post(AUTHORITY_PREPARE_ROUTE, json=_authority_payload(decision))

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == authority_service.AUTHORITY_SCHEMA_ID
    assert body["sidecar_receipt_id_hash"] == _hash("d")
    assert body["auth_binding_required"] is True
    assert body["auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["auth_binding_route_family"] == AUTHORITY_PREPARE_ROUTE_FAMILY
    assert body["source_auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert "sidecar_receipt_id" not in body
    assert body["value_reveal_performed"] is False
    assert body["production_readiness_claimed"] is False


def test_value_reveal_authority_api_rolls_back_source_receipt_when_binding_fails(
    api_client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    client, Session = api_client
    with Session() as db:
        decision = _record_decision(db, request_id="authority-api-binding-fail-decision-source")
        _bind_decision(db, decision)

    _force_auth_binding_failure(monkeypatch, source_receipt_kind="value_reveal_authority")

    response = client.post(
        AUTHORITY_PREPARE_ROUTE,
        json=_authority_payload(decision, client_request_id="authority-api-binding-fail"),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "sec_xbrl_auth_binding_forced_failure"
    with Session() as db:
        assert db.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 0
        assert db.query(L3SecXbrlAuthBindingReceipt).count() == 1


def test_value_reveal_authority_api_rejects_extra_fields(api_client) -> None:
    client, Session = api_client
    with Session() as db:
        decision = _record_decision(db, request_id="authority-api-extra-source")

    response = client.post(
        AUTHORITY_PREPARE_ROUTE,
        json=_authority_payload(decision, sidecar_receipt_hash=_hash("b")),
    )

    assert response.status_code == 400
    assert _hash("b") not in response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_value_reveal_authority_request_fields_not_admitted"
    assert body["blocked_fields"] == ["sidecar_receipt_hash"]


def test_controlled_value_reveal_submit_returns_transient_values_and_hash_only_receipt(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-service-authority")
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: _submit_sidecar_and_value_store())
    client_request_id = "controlled-submit-service"
    client_request_id_hash = _request_hash(client_request_id)

    response = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id=client_request_id,
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )

    assert response["schema_id"] == submit_service.SUBMIT_SCHEMA_ID
    assert response["submit_mode"] == submit_service.SUBMIT_MODE
    assert response["transient_values_returned"] is True
    assert response["revealed_fact_count"] == 1
    assert response["total_record_count"] == 1
    assert response["page_record_count"] == 1
    assert response["page_index"] == 1
    assert response["next_page_cursor"] is None
    assert response["revealed_facts"][0]["effective_value"] == "123.45"
    assert response["revealed_facts"][0]["lexical_value"] == "123.45"
    assert "period" not in response["revealed_facts"][0]
    assert "sidecar_receipt_id" not in response
    assert response["raw_sidecar_receipt_id_persisted"] is False
    assert response["audit_receipt_raw_values_persisted"] is False
    assert response["runtime_default_enabled"] is False
    assert response["delivery_export_enabled"] is False
    assert response["rendered_ui_enabled"] is False
    assert response["client_request_id_hash"] == client_request_id_hash
    assert "client_request_id" not in response
    assert client_request_id not in json.dumps(response, sort_keys=True)

    row = db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).one()
    assert row.submit_basis_hash == response["submit_basis_hash"]
    assert row.client_request_id_hash == client_request_id_hash
    assert row.client_request_id == f"redacted-client-request-id:{client_request_id_hash}"
    assert row.revealed_fact_count == 1
    assert row.value_redacted_fact_count == 0
    assert row.sidecar_receipt_id_hash == _hash("d")
    assert client_request_id not in json.dumps(row.submit_summary_json, sort_keys=True)
    assert "123.45" not in json.dumps(row.submit_summary_json, sort_keys=True)
    assert row.negative_invariants_json["raw_values_persisted"] is False

    status = submit_service.inspect_controlled_value_reveal_submit_status(
        db_session,
        sec_xbrl_controlled_value_reveal_submit_receipt_id=(
            response["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
        ),
    )
    assert status["schema_id"] == submit_service.STATUS_SCHEMA_ID
    assert status["revealed_fact_count"] == 1
    assert status["total_record_count"] == 1
    assert status["page_record_count"] == 1
    assert status["page_index"] == 1
    assert status["next_page_cursor"] is None
    assert status["revealed_facts"] == []
    assert status["transient_values_returned"] is False
    assert status["client_request_id_hash"] == client_request_id_hash
    assert "client_request_id" not in status
    assert "dataset_version_id" not in status
    assert "sidecar_receipt_hash" not in status
    assert client_request_id not in json.dumps(status, sort_keys=True)


def test_controlled_value_reveal_submit_idempotency_uses_hash_without_raw_replay(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-idempotency-authority")
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: _submit_sidecar_and_value_store())
    client_request_id = "issuer-private-submit-request"
    client_request_id_hash = _request_hash(client_request_id)

    first = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id=client_request_id,
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )
    second = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id=client_request_id,
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )

    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert second["sec_xbrl_controlled_value_reveal_submit_receipt_id"] == (
        first["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
    )
    assert second["client_request_id_hash"] == client_request_id_hash
    assert "client_request_id" not in second
    assert client_request_id not in json.dumps(second, sort_keys=True)

    rows = db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.client_request_id_hash == client_request_id_hash
    assert row.client_request_id == f"redacted-client-request-id:{client_request_id_hash}"


def test_controlled_value_reveal_submit_redacts_identity_like_transient_values(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-redaction")
    monkeypatch.setattr(
        submit_service,
        "_resolve_sidecar_and_value_store",
        lambda *_args: _submit_sidecar_and_value_store(
            effective_value="0000123456-26-000001",
            lexical_value="0000123456-26-000001",
        ),
    )

    response = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-redacted-service",
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )

    revealed = response["revealed_facts"][0]
    assert revealed["effective_value"] == ""
    assert revealed["lexical_value"] == ""
    assert revealed["value_redacted"] is True
    assert revealed["value_redaction_reason"] == "sec_xbrl_controlled_value_reveal_identity_or_raw_reference_redacted"
    assert response["value_redacted_fact_count"] == 1

    row = db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).one()
    assert row.value_redacted_fact_count == 1
    assert "0000123456-26-000001" not in json.dumps(row.submit_summary_json, sort_keys=True)
    assert "0000123456-26-000001" not in json.dumps(row.negative_invariants_json, sort_keys=True)


def test_controlled_value_reveal_submit_paginates_large_result_set_without_dup_gap(
    db_session,
    monkeypatch,
) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-pagination-authority")
    sidecar, value_store = _paginated_submit_sidecar_and_value_store(submit_service.MAX_REVEAL_RECORDS + 3)
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: (sidecar, value_store))

    first = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-pagination-page-1",
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )

    assert first["total_record_count"] == submit_service.MAX_REVEAL_RECORDS + 3
    assert first["page_record_count"] == submit_service.MAX_REVEAL_RECORDS
    assert first["revealed_fact_count"] == submit_service.MAX_REVEAL_RECORDS
    assert first["page_index"] == 1
    assert first["next_page_cursor"]

    second = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-pagination-page-2",
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
        page_cursor=first["next_page_cursor"],
    )

    assert second["total_record_count"] == submit_service.MAX_REVEAL_RECORDS + 3
    assert second["page_record_count"] == 3
    assert second["revealed_fact_count"] == 3
    assert second["page_index"] == 2
    assert second["next_page_cursor"] is None

    traversed = first["revealed_facts"] + second["revealed_facts"]
    assert len(traversed) == submit_service.MAX_REVEAL_RECORDS + 3
    assert len({record["fact_identity_hash"] for record in traversed}) == len(traversed)
    assert [record["source_order"] for record in traversed] == sorted(
        record["source_order"] for record in traversed
    )
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 2

    status = submit_service.inspect_controlled_value_reveal_submit_status(
        db_session,
        sec_xbrl_controlled_value_reveal_submit_receipt_id=(
            second["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
        ),
    )
    assert status["revealed_facts"] == []
    assert status["total_record_count"] == second["total_record_count"]
    assert status["page_record_count"] == second["page_record_count"]
    assert status["page_index"] == second["page_index"]
    assert status["next_page_cursor"] is None


def test_controlled_value_reveal_submit_exact_cap_is_single_page_hash_only_and_replay(
    db_session,
    monkeypatch,
) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-exact-cap")
    sidecar, value_store = _paginated_submit_sidecar_and_value_store(submit_service.MAX_REVEAL_RECORDS)
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: (sidecar, value_store))
    client_request_id = "controlled-submit-exact-cap-page"

    first = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id=client_request_id,
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )
    replay = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id=client_request_id,
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
    )

    assert first["idempotent_replay"] is False
    assert first["total_record_count"] == submit_service.MAX_REVEAL_RECORDS
    assert first["page_record_count"] == submit_service.MAX_REVEAL_RECORDS
    assert first["revealed_fact_count"] == submit_service.MAX_REVEAL_RECORDS
    assert len(first["revealed_facts"]) == submit_service.MAX_REVEAL_RECORDS
    assert first["page_index"] == 1
    assert first["next_page_cursor"] is None
    assert replay["idempotent_replay"] is True
    assert replay["sec_xbrl_controlled_value_reveal_submit_receipt_id"] == (
        first["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
    )
    assert replay["submit_basis_hash"] == first["submit_basis_hash"]
    assert replay["page_record_count"] == first["page_record_count"]
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 1

    status = submit_service.inspect_controlled_value_reveal_submit_status(
        db_session,
        sec_xbrl_controlled_value_reveal_submit_receipt_id=(
            first["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
        ),
    )
    assert status["total_record_count"] == submit_service.MAX_REVEAL_RECORDS
    assert status["page_record_count"] == submit_service.MAX_REVEAL_RECORDS
    assert status["page_index"] == 1
    assert status["next_page_cursor"] is None
    assert status["revealed_facts"] == []
    assert status["transient_values_returned"] is False
    assert "1000.01" not in json.dumps(status, sort_keys=True)

    row = db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).one()
    assert row.submit_basis_hash == first["submit_basis_hash"]
    assert row.submit_summary_json["page_record_count"] == submit_service.MAX_REVEAL_RECORDS
    assert "1000.01" not in json.dumps(row.submit_summary_json, sort_keys=True)


def test_controlled_value_reveal_submit_rejects_tampered_page_cursor(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-cursor-tamper")
    sidecar, value_store = _paginated_submit_sidecar_and_value_store(5)
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: (sidecar, value_store))

    first = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-cursor-tamper-page-1",
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
        max_records=2,
    )

    cursor = first["next_page_cursor"]
    padded_cursor = cursor + ("=" * (-len(cursor) % 4))
    decoded_cursor = base64.urlsafe_b64decode(padded_cursor).decode("utf-8")
    payload = json.loads(decoded_cursor)
    payload["offset"] = 4
    unsigned_payload = dict(payload)
    unsigned_payload.pop("cursor_hash", None)
    unsigned_payload.pop("cursor_signature", None)
    payload["cursor_hash"] = submit_service.stable_hash(unsigned_payload)
    tampered_cursor_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tampered_cursor = base64.urlsafe_b64encode(tampered_cursor_body).decode("ascii").rstrip("=")
    with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
        submit_service.submit_controlled_value_reveal(
            db_session,
            client_request_id="controlled-submit-cursor-tamper-page-2",
            sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
            authority_basis_hash=authority["authority_basis_hash"],
            operator_reveal_confirmation=True,
            max_records=2,
            page_cursor=tampered_cursor,
        )

    assert exc.value.http_status == 400
    assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_page_cursor_invalid"
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 1


def test_controlled_value_reveal_submit_rejects_cross_authority_page_cursor(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    first_authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-cursor-a")
    second_workflow = _open_workflow(
        db_session,
        request_id="controlled-submit-cursor-b-workflow",
        packet_request_id="controlled-submit-cursor-b-packet",
        projection_request_id="controlled-submit-cursor-b-projection",
        projection_source_report_hash=_request_hash("controlled-submit-cursor-b-source"),
    )
    second_decision = _record_decision(
        db_session,
        workflow=second_workflow,
        request_id="controlled-submit-cursor-b-decision",
        decision_notes="distinct approved decision basis for cross-authority cursor test",
    )
    second_authority = authority_service.prepare_value_reveal_authority_receipt(
        db_session,
        client_request_id="controlled-submit-cursor-b",
        sec_xbrl_operator_review_decision_id=second_decision["sec_xbrl_operator_review_decision_id"],
        decision_basis_hash=second_decision["decision_basis_hash"],
    )
    sidecar, value_store = _paginated_submit_sidecar_and_value_store(5)
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: (sidecar, value_store))

    first = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-cursor-a-page-1",
        sec_xbrl_value_reveal_authority_receipt_id=first_authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=first_authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
        max_records=2,
    )

    with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
        submit_service.submit_controlled_value_reveal(
            db_session,
            client_request_id="controlled-submit-cursor-b-page-2",
            sec_xbrl_value_reveal_authority_receipt_id=second_authority["sec_xbrl_value_reveal_authority_receipt_id"],
            authority_basis_hash=second_authority["authority_basis_hash"],
            operator_reveal_confirmation=True,
            max_records=2,
            page_cursor=first["next_page_cursor"],
        )

    assert exc.value.http_status == 400
    assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_page_cursor_authority_mismatch"
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 1


def test_controlled_value_reveal_submit_isolates_interleaved_multi_authority_pages(
    db_session,
    monkeypatch,
) -> None:
    _enable_controlled_submit(monkeypatch)
    cases = _multi_authority_paginated_cases(
        db_session,
        monkeypatch,
        authority_count=3,
        records_per_authority=4,
    )

    first_pages = [
        _submit_paginated_case_page(
            db_session,
            case,
            client_request_id=f"controlled-submit-isolation-{index:02d}-page-1",
            max_records=2,
        )
        for index, case in enumerate(cases)
    ]
    assert all(page["page_record_count"] == 2 for page in first_pages)
    assert all(page["next_page_cursor"] for page in first_pages)

    with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
        _submit_paginated_case_page(
            db_session,
            cases[1],
            client_request_id="controlled-submit-isolation-cross-authority-cursor",
            max_records=2,
            page_cursor=first_pages[0]["next_page_cursor"],
        )
    assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_page_cursor_authority_mismatch"

    second_pages = [
        _submit_paginated_case_page(
            db_session,
            case,
            client_request_id=f"controlled-submit-isolation-{index:02d}-page-2",
            max_records=2,
            page_cursor=first_pages[index]["next_page_cursor"],
        )
        for index, case in enumerate(cases)
    ]
    assert all(page["page_record_count"] == 2 for page in second_pages)
    assert all(page["next_page_cursor"] is None for page in second_pages)

    all_pages = first_pages + second_pages
    assert len({page["sec_xbrl_controlled_value_reveal_submit_receipt_id"] for page in all_pages}) == len(all_pages)
    assert len({page["submit_basis_hash"] for page in all_pages}) == len(all_pages)
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == len(all_pages)

    authority_rows = db_session.query(L3SecXbrlValueRevealAuthorityReceipt).all()
    assert len(authority_rows) == len(cases)
    assert len({row.sidecar_receipt_hash for row in authority_rows}) == len(cases)
    assert len({row.value_store_hash for row in authority_rows}) == len(cases)

    fact_hashes_by_authority: list[set[str]] = []
    all_value_sets = [case["value_texts"] for case in cases]
    for index, case in enumerate(cases):
        pages = [first_pages[index], second_pages[index]]
        revealed_values = {
            record["effective_value"]
            for page in pages
            for record in page["revealed_facts"]
        }
        fact_hashes = {
            record["fact_identity_hash"]
            for page in pages
            for record in page["revealed_facts"]
        }
        fact_hashes_by_authority.append(fact_hashes)
        assert revealed_values == case["value_texts"]
        other_values = set().union(*(values for pos, values in enumerate(all_value_sets) if pos != index))
        assert not (revealed_values & other_values)
        page_json = json.dumps(pages, sort_keys=True)
        assert not any(value in page_json for value in other_values)
        for page in pages:
            status = submit_service.inspect_controlled_value_reveal_submit_status(
                db_session,
                sec_xbrl_controlled_value_reveal_submit_receipt_id=(
                    page["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
                ),
            )
            status_json = json.dumps(status, sort_keys=True)
            assert status["revealed_facts"] == []
            assert status["transient_values_returned"] is False
            assert not any(value in status_json for value in case["value_texts"])

    for index, fact_hashes in enumerate(fact_hashes_by_authority):
        other_fact_hashes = set().union(
            *(hashes for pos, hashes in enumerate(fact_hashes_by_authority) if pos != index)
        )
        assert fact_hashes.isdisjoint(other_fact_hashes)


def test_controlled_value_reveal_submit_scales_isolation_across_60_authorities(
    db_session,
    monkeypatch,
) -> None:
    _enable_controlled_submit(monkeypatch)
    authority_count = 60
    cases = _multi_authority_paginated_cases(
        db_session,
        monkeypatch,
        authority_count=authority_count,
        records_per_authority=3,
    )

    first_pages = [
        _submit_paginated_case_page(
            db_session,
            case,
            client_request_id=f"controlled-submit-scale-{index:02d}-page-1",
            max_records=2,
        )
        for index, case in enumerate(cases)
    ]
    second_pages = [
        _submit_paginated_case_page(
            db_session,
            case,
            client_request_id=f"controlled-submit-scale-{index:02d}-page-2",
            max_records=2,
            page_cursor=first_pages[index]["next_page_cursor"],
        )
        for index, case in enumerate(cases)
    ]

    all_pages = first_pages + second_pages
    assert len(all_pages) == authority_count * 2
    assert len({page["sec_xbrl_controlled_value_reveal_submit_receipt_id"] for page in all_pages}) == len(all_pages)
    assert len({page["submit_basis_hash"] for page in all_pages}) == len(all_pages)
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == len(all_pages)

    authority_rows = db_session.query(L3SecXbrlValueRevealAuthorityReceipt).all()
    assert len(authority_rows) == authority_count
    assert len({row.sec_xbrl_value_reveal_authority_receipt_id for row in authority_rows}) == authority_count
    assert len({row.sidecar_receipt_hash for row in authority_rows}) == authority_count
    assert len({row.value_store_hash for row in authority_rows}) == authority_count

    seen_fact_hashes: set[str] = set()
    for index, case in enumerate(cases):
        pages = [first_pages[index], second_pages[index]]
        assert pages[0]["page_record_count"] == 2
        assert pages[0]["next_page_cursor"]
        assert pages[1]["page_record_count"] == 1
        assert pages[1]["next_page_cursor"] is None
        revealed_values = {
            record["effective_value"]
            for page in pages
            for record in page["revealed_facts"]
        }
        fact_hashes = {
            record["fact_identity_hash"]
            for page in pages
            for record in page["revealed_facts"]
        }
        assert revealed_values == case["value_texts"]
        assert fact_hashes.isdisjoint(seen_fact_hashes)
        seen_fact_hashes.update(fact_hashes)
        for page in pages:
            status = submit_service.inspect_controlled_value_reveal_submit_status(
                db_session,
                sec_xbrl_controlled_value_reveal_submit_receipt_id=(
                    page["sec_xbrl_controlled_value_reveal_submit_receipt_id"]
                ),
            )
            status_json = json.dumps(status, sort_keys=True)
            assert status["revealed_facts"] == []
            assert status["transient_values_returned"] is False
            assert not any(value in status_json for value in case["value_texts"])

    assert len(seen_fact_hashes) == authority_count * 3


def test_controlled_value_reveal_submit_redacts_each_paginated_page(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-paged-redaction")
    sidecar, value_store = _paginated_submit_sidecar_and_value_store(4, redacted_indices={0, 2})
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: (sidecar, value_store))
    raw_value = "0000123456-26-000001"

    first = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-paged-redaction-page-1",
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
        max_records=2,
    )
    second = submit_service.submit_controlled_value_reveal(
        db_session,
        client_request_id="controlled-submit-paged-redaction-page-2",
        sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
        authority_basis_hash=authority["authority_basis_hash"],
        operator_reveal_confirmation=True,
        max_records=2,
        page_cursor=first["next_page_cursor"],
    )

    assert any(record["value_redacted"] is True for record in first["revealed_facts"])
    assert any(record["value_redacted"] is True for record in second["revealed_facts"])
    assert raw_value not in json.dumps(first, sort_keys=True)
    assert raw_value not in json.dumps(second, sort_keys=True)
    rows = db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).all()
    assert len(rows) == 2
    assert all(row.value_redacted_fact_count == 1 for row in rows)
    assert raw_value not in json.dumps([row.submit_summary_json for row in rows], sort_keys=True)
    assert raw_value not in json.dumps([row.negative_invariants_json for row in rows], sort_keys=True)


def test_controlled_value_reveal_submit_explicit_off_blocks_without_receipt(db_session, monkeypatch) -> None:
    monkeypatch.setattr(submit_service.settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)
    with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
        submit_service.submit_controlled_value_reveal(
            db_session,
            client_request_id="controlled-submit-default-off",
            sec_xbrl_value_reveal_authority_receipt_id="authority-receipt-id",
            authority_basis_hash=_hash("a"),
            operator_reveal_confirmation=True,
        )

    assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled"
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0


def test_controlled_value_reveal_submit_rejects_raw_authority_receipt_id(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)

    for raw_receipt_id in ("0000123456-26-000001", "file:///tmp/raw", "/workspace/raw"):
        with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
            submit_service.submit_controlled_value_reveal(
                db_session,
                client_request_id="controlled-submit-raw-authority-id",
                sec_xbrl_value_reveal_authority_receipt_id=raw_receipt_id,
                authority_basis_hash=_hash("a"),
                operator_reveal_confirmation=True,
            )

        assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_raw_reference_not_admitted"
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0


def test_controlled_value_reveal_submit_status_rejects_raw_receipt_id(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)

    for raw_receipt_id in ("0000123456-26-000001", "file:///tmp/raw", "/workspace/raw"):
        with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
            submit_service.inspect_controlled_value_reveal_submit_status(
                db_session,
                sec_xbrl_controlled_value_reveal_submit_receipt_id=raw_receipt_id,
            )

        assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_raw_reference_not_admitted"
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0


def test_controlled_value_reveal_submit_missing_sidecar_creates_no_partial_receipt(db_session, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    authority = _prepare_authority_receipt(db_session, monkeypatch, request_id="controlled-submit-missing-sidecar")

    def missing_sidecar(*_args):
        raise submit_service.SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_value_store_missing",
            "missing sidecar",
        )

    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", missing_sidecar)

    with pytest.raises(submit_service.SecXbrlControlledValueRevealSubmitError) as exc:
        submit_service.submit_controlled_value_reveal(
            db_session,
            client_request_id="controlled-submit-missing-sidecar-service",
            sec_xbrl_value_reveal_authority_receipt_id=authority["sec_xbrl_value_reveal_authority_receipt_id"],
            authority_basis_hash=authority["authority_basis_hash"],
            operator_reveal_confirmation=True,
        )

    assert exc.value.code == "sec_xbrl_controlled_value_reveal_submit_value_store_missing"
    assert db_session.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0


def test_controlled_value_reveal_submit_api_records_receipt_and_status_hash_count_only(
    api_client,
    monkeypatch,
) -> None:
    _enable_controlled_submit(monkeypatch)
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: _submit_sidecar_and_value_store())
    client, Session = api_client
    with Session() as db:
        decision = _record_decision(db, request_id="controlled-submit-api-decision-source")
        _bind_decision(db, decision)

    authority_response = client.post(AUTHORITY_PREPARE_ROUTE, json=_authority_payload(decision))
    assert authority_response.status_code == 200
    authority = authority_response.json()
    submit_payload = _controlled_submit_payload(authority)
    raw_client_request_id = submit_payload["client_request_id"]
    raw_client_request_id_hash = _request_hash(raw_client_request_id)

    submit_response = client.post(
        CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE,
        json=submit_payload,
    )

    assert submit_response.status_code == 200
    body = submit_response.json()
    assert body["schema_id"] == submit_service.SUBMIT_SCHEMA_ID
    assert body["request_id"] == f"sec-xbrl-controlled-value-reveal-submit-{raw_client_request_id_hash[:24]}"
    assert body["client_request_id_hash"] == raw_client_request_id_hash
    assert "client_request_id" not in body
    assert body["revealed_fact_count"] == 1
    assert body["total_record_count"] == 1
    assert body["page_record_count"] == 1
    assert body["page_index"] == 1
    assert body["next_page_cursor"] is None
    assert body["revealed_facts"][0]["effective_value"] == "123.45"
    assert body["auth_binding_required"] is True
    assert body["auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["auth_binding_route_family"] == CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE_FAMILY
    assert body["source_auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert "sidecar_receipt_id" not in body
    assert body["status_surface_hash_count_only"] is True
    assert raw_client_request_id not in json.dumps(body, sort_keys=True)

    with Session() as db:
        row = db.query(L3SecXbrlControlledValueRevealSubmitReceipt).one()
        assert row.client_request_id_hash == raw_client_request_id_hash
        assert row.client_request_id == f"redacted-client-request-id:{raw_client_request_id_hash}"
        binding = (
            db.query(L3SecXbrlAuthBindingReceipt)
            .filter(L3SecXbrlAuthBindingReceipt.source_receipt_kind == "controlled_value_reveal_submit")
            .one()
        )
        assert raw_client_request_id not in binding.client_request_id

    status_response = client.get(
        f"{CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE}/status/"
        f"{body['sec_xbrl_controlled_value_reveal_submit_receipt_id']}"
    )
    assert status_response.status_code == 200
    status = status_response.json()
    assert status["schema_id"] == submit_service.STATUS_SCHEMA_ID
    assert status["client_request_id_hash"] == raw_client_request_id_hash
    assert "client_request_id" not in status
    assert status["total_record_count"] == 1
    assert status["page_record_count"] == 1
    assert status["page_index"] == 1
    assert status["next_page_cursor"] is None
    assert status["revealed_facts"] == []
    assert status["auth_binding_required"] is True
    assert status["auth_binding_route_family"] == CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE_FAMILY
    assert status["transient_values_returned"] is False
    assert "dataset_version_id" not in status
    assert "sidecar_receipt_hash" not in status
    assert "123.45" not in json.dumps(status, sort_keys=True)
    assert raw_client_request_id not in json.dumps(status, sort_keys=True)


def test_controlled_value_reveal_submit_api_with_flag_enabled_returns_values_behind_owner_binding(
    api_client,
    monkeypatch,
) -> None:
    # Activation proof (doc 1353): flag is default-off; enable via monkeypatch to prove the full
    # lineage to revealed financial values behind the enforced owner-bound identity.
    # The sidecar/value-store monkeypatches only stand in for the on-disk Arelle value store; they do
    # not bypass the owner binding or the operator_reveal_confirmation gate.
    _enable_controlled_submit(monkeypatch)
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: _submit_sidecar_and_value_store())
    client, Session = api_client
    with Session() as db:
        decision = _record_decision(db, request_id="controlled-submit-default-on-decision-source")
        _bind_decision(db, decision)

    authority_response = client.post(
        AUTHORITY_PREPARE_ROUTE,
        json=_authority_payload(decision, client_request_id="controlled-submit-default-on-authority"),
    )
    assert authority_response.status_code == 200, authority_response.text
    authority = authority_response.json()

    submit_response = client.post(
        CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE,
        json=_controlled_submit_payload(authority, client_request_id="controlled-submit-default-on"),
    )

    assert submit_response.status_code == 200, submit_response.text
    body = submit_response.json()
    assert body["schema_id"] == submit_service.SUBMIT_SCHEMA_ID
    assert body["revealed_fact_count"] == 1
    assert body["total_record_count"] == 1
    assert body["page_record_count"] == 1
    assert body["page_index"] == 1
    assert body["next_page_cursor"] is None
    assert body["revealed_facts"][0]["effective_value"] == "123.45"
    assert body["auth_binding_required"] is True
    assert body["status_surface_hash_count_only"] is True
    assert body["client_request_id_hash"] == _request_hash("controlled-submit-default-on")
    assert "client_request_id" not in body

    # Revealed response carries financial figures only -- no authority artifacts leak.
    serialized = json.dumps(body, sort_keys=True)
    assert "123.45" in serialized
    assert "controlled-submit-default-on" not in serialized
    for forbidden in ("@", "http://", "https://", "file://", "0000123456"):
        assert forbidden not in serialized


def test_controlled_value_reveal_submit_api_rolls_back_source_receipt_when_binding_fails(
    api_client,
    monkeypatch,
) -> None:
    _enable_controlled_submit(monkeypatch)
    monkeypatch.setattr(authority_service, "_resolve_sidecar_authority", lambda *_args: _sidecar_authority())
    monkeypatch.setattr(submit_service, "_resolve_sidecar_and_value_store", lambda *_args: _submit_sidecar_and_value_store())
    client, Session = api_client
    with Session() as db:
        decision = _record_decision(db, request_id="controlled-submit-api-binding-fail-decision-source")
        _bind_decision(db, decision)

    authority_response = client.post(
        AUTHORITY_PREPARE_ROUTE,
        json=_authority_payload(decision, client_request_id="controlled-submit-api-binding-fail-authority"),
    )
    assert authority_response.status_code == 200, authority_response.text
    authority = authority_response.json()

    _force_auth_binding_failure(monkeypatch, source_receipt_kind="controlled_value_reveal_submit")

    submit_response = client.post(
        CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE,
        json=_controlled_submit_payload(authority, client_request_id="controlled-submit-api-binding-fail"),
    )

    assert submit_response.status_code == 409, submit_response.text
    assert submit_response.json()["error_code"] == "sec_xbrl_auth_binding_forced_failure"
    with Session() as db:
        assert db.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0
        assert db.query(L3SecXbrlValueRevealAuthorityReceipt).count() == 1
        assert db.query(L3SecXbrlAuthBindingReceipt).count() == 2


def test_controlled_value_reveal_submit_api_rejects_client_sidecar_fields(api_client) -> None:
    client, _Session = api_client

    response = client.post(
        CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE,
        json={
            "client_request_id": "controlled-submit-api-extra",
            "submit_mode": submit_service.SUBMIT_MODE,
            "operator_decision": submit_service.SUBMIT_OPERATOR_DECISION,
            "sec_xbrl_value_reveal_authority_receipt_id": "authority-receipt-id",
            "authority_basis_hash": _hash("a"),
            "operator_reveal_confirmation": True,
            "sidecar_receipt_hash": _hash("b"),
        },
    )

    assert response.status_code == 400
    assert _hash("b") not in response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_controlled_value_reveal_submit_request_fields_not_admitted"
    assert body["blocked_fields"] == ["sidecar_receipt_hash"]


def test_controlled_value_reveal_submit_api_rejects_raw_authority_receipt_id(api_client, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    client, Session = api_client

    for raw_receipt_id in ("0000123456-26-000001", "file:///tmp/raw", "/workspace/raw"):
        response = client.post(
            CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE,
            json={
                "client_request_id": "controlled-submit-api-raw-authority-id",
                "submit_mode": submit_service.SUBMIT_MODE,
                "operator_decision": submit_service.SUBMIT_OPERATOR_DECISION,
                "sec_xbrl_value_reveal_authority_receipt_id": raw_receipt_id,
                "authority_basis_hash": _hash("a"),
                "operator_reveal_confirmation": True,
            },
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "sec_xbrl_auth_binding_raw_reference_not_admitted"
        assert raw_receipt_id not in response.text
    with Session() as db:
        assert db.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0


def test_controlled_value_reveal_submit_api_status_rejects_raw_receipt_id(api_client, monkeypatch) -> None:
    _enable_controlled_submit(monkeypatch)
    client, Session = api_client

    response = client.get(f"{CONTROLLED_VALUE_REVEAL_SUBMIT_ROUTE}/status/0000123456-26-000001")

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "sec_xbrl_auth_binding_raw_reference_not_admitted"
    assert "0000123456-26-000001" not in response.text
    with Session() as db:
        assert db.query(L3SecXbrlControlledValueRevealSubmitReceipt).count() == 0


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
        assert "l3_sec_xbrl_value_reveal_authority_receipt" in inspector.get_table_names()
        authority_columns = {
            column["name"]
            for column in inspector.get_columns("l3_sec_xbrl_value_reveal_authority_receipt")
        }
        assert "authority_basis_hash" in authority_columns
        assert "dataset_version_hash" in authority_columns
        assert "sidecar_receipt_id_hash" in authority_columns
        assert "value_store_hash" in authority_columns
        assert "l3_sec_xbrl_controlled_value_reveal_submit_receipt" in inspector.get_table_names()
        submit_columns = {
            column["name"]
            for column in inspector.get_columns("l3_sec_xbrl_controlled_value_reveal_submit_receipt")
        }
        assert "client_request_id_hash" in submit_columns
        assert "submit_basis_hash" in submit_columns
        assert "sec_xbrl_value_reveal_authority_receipt_id" in submit_columns
        assert "revealed_fact_count" in submit_columns
        assert "response_inventory_hash" in submit_columns
        submit_unique_constraints = {
            constraint["name"]: tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("l3_sec_xbrl_controlled_value_reveal_submit_receipt")
        }
        assert submit_unique_constraints["uq_l3_sec_xbrl_controlled_value_reveal_client_request"] == (
            "client_request_id_hash",
        )
        assert submit_unique_constraints["uq_l3_sec_xbrl_controlled_value_reveal_basis_hash"] == (
            "submit_basis_hash",
        )
        assert "uq_l3_sec_xbrl_controlled_value_reveal_authority" not in submit_unique_constraints
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


def test_value_reveal_authority_migration_declares_additive_table() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0044_sec_xbrl_value_reveal_authority",
        AUTHORITY_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0044_layer3_sec_xbrl_value_reveal_authority_receipt"
    assert module.down_revision == "0043_layer3_sec_xbrl_statement_packet_row_period_unique"
    source = AUTHORITY_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_value_reveal_authority_receipt" in source
    assert "drop_table_idempotent(TABLE_NAME)" in source


def test_controlled_value_reveal_submit_migration_declares_additive_table() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0045_sec_xbrl_controlled_value_reveal_submit",
        SUBMIT_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0045_layer3_sec_xbrl_controlled_value_reveal_submit"
    assert module.down_revision == "0044_layer3_sec_xbrl_value_reveal_authority_receipt"
    source = SUBMIT_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_controlled_value_reveal_submit_receipt" in source
    assert "drop_table_idempotent(TABLE_NAME)" in source


def test_controlled_value_reveal_submit_request_hash_migration_declares_rekey() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0053_sec_xbrl_controlled_submit_request_hash",
        SUBMIT_HASH_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0053_layer3_sec_xbrl_controlled_submit_request_hash"
    assert module.down_revision == "0052_layer3_analysis_product_supersession"
    source = SUBMIT_HASH_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "client_request_id_hash" in source
    assert "redacted-client-request-id:" in source
    assert "hashlib.sha256" in source
    assert "batch_op.create_unique_constraint" in source


def test_controlled_value_reveal_submit_pagination_migration_drops_authority_uniqueness() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0054_sec_xbrl_controlled_submit_pagination",
        SUBMIT_PAGINATION_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0054_layer3_sec_xbrl_controlled_submit_pagination"
    assert module.down_revision == "0053_layer3_sec_xbrl_controlled_submit_request_hash"
    source = SUBMIT_PAGINATION_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "uq_l3_sec_xbrl_controlled_value_reveal_authority" in source
    assert "batch_op.drop_constraint" in source
    assert "batch_op.create_unique_constraint" in source
    assert "GROUP BY sec_xbrl_value_reveal_authority_receipt_id" in source


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


def _open_payload(packet_set_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "client_request_id": "workflow-open-api",
        "sec_xbrl_statement_packet_set_id": packet_set_id,
    }
    payload.update(overrides)
    return payload


def test_operator_review_workflow_open_api_opens_and_binds(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        packet = _materialized_packet(session, packet_request_id="open-api-packet")
        packet_set_id = packet["sec_xbrl_statement_packet_set_id"]

    response = client.post(
        WORKFLOW_OPEN_ROUTE,
        json=_open_payload(packet_set_id),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sec_xbrl_operator_review_workflow_id"]
    assert body["workflow_basis_hash"]
    assert len(body["workflow_basis_hash"]) == 64
    assert body["auth_binding_ref"].startswith("sec-xbrl-auth-binding:")
    assert body["auth_binding_route_family"] == WORKFLOW_OPEN_ROUTE_FAMILY
    assert body["auth_binding_required"] is True
    assert body["workflow_open_api_route_enabled"] is True
    assert body["status_api_route_enabled"] is True
    assert body["decision_submit_api_route_enabled"] is True
    assert body["value_reveal_performed"] is False
    assert body["idempotent_replay"] is False
    assert body["request_id"] == "workflow-open-api"
    assert "C:/" not in response.text
    assert "https://www.sec.gov" not in response.text

    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1
        assert session.query(L3SecXbrlAuthBindingReceipt).count() == 1


def test_operator_review_workflow_open_api_is_idempotent(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        packet = _materialized_packet(session, packet_request_id="open-api-idem-packet")
        packet_set_id = packet["sec_xbrl_statement_packet_set_id"]

    first = client.post(WORKFLOW_OPEN_ROUTE, json=_open_payload(packet_set_id, client_request_id="open-idem"))
    second = client.post(WORKFLOW_OPEN_ROUTE, json=_open_payload(packet_set_id, client_request_id="open-idem"))

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_body = first.json()
    second_body = second.json()
    assert second_body["idempotent_replay"] is True
    assert second_body["sec_xbrl_operator_review_workflow_id"] == first_body["sec_xbrl_operator_review_workflow_id"]
    assert second_body["workflow_basis_hash"] == first_body["workflow_basis_hash"]

    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1


def test_operator_review_workflow_open_api_cold_start_enters_chain(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        packet = _materialized_packet(session, packet_request_id="cold-start-packet")
        packet_set_id = packet["sec_xbrl_statement_packet_set_id"]

    # Step 1: open the workflow via HTTP — no manual binding seed
    open_resp = client.post(
        WORKFLOW_OPEN_ROUTE,
        json=_open_payload(packet_set_id, client_request_id="cold-open"),
    )
    assert open_resp.status_code == 200, open_resp.text
    open_body = open_resp.json()
    workflow_id = open_body["sec_xbrl_operator_review_workflow_id"]
    workflow_hash = open_body["workflow_basis_hash"]

    # Step 2: status read — the open_write binding must satisfy status_read
    status_resp = client.post(
        WORKFLOW_STATUS_ROUTE,
        json={
            "client_request_id": "cold-status",
            "status_mode": workflow_service.WORKFLOW_STATUS_MODE,
            "operator_decision": workflow_service.WORKFLOW_STATUS_OPERATOR_DECISION,
            "sec_xbrl_operator_review_workflow_id": workflow_id,
            "workflow_basis_hash": workflow_hash,
        },
    )
    assert status_resp.status_code == 200, status_resp.text
    status_body = status_resp.json()
    assert status_body["sec_xbrl_operator_review_workflow_id"] == workflow_id

    # Step 3: decision submit — the open_write binding must satisfy decision_submit
    decision_resp = client.post(
        DECISION_SUBMIT_ROUTE,
        json={
            "client_request_id": "cold-decision",
            "submit_mode": "sec_xbrl_operator_review_decision_submit_v1",
            "operator_decision": "submit_sec_xbrl_operator_review_decision",
            "sec_xbrl_operator_review_workflow_id": workflow_id,
            "workflow_basis_hash": workflow_hash,
            "review_decision": "approved",
            "decision_reason_code": "ready_for_next_freeze",
        },
    )
    assert decision_resp.status_code == 200, decision_resp.text
    decision_body = decision_resp.json()
    assert decision_body["sec_xbrl_operator_review_workflow_id"] == workflow_id
    assert decision_body["status"] == "decision_recorded"

    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewWorkflow).count() == 1
        assert session.query(L3SecXbrlOperatorReviewDecision).count() == 1


def test_operator_review_workflow_open_api_rejects_extra_fields(api_client) -> None:
    client, Session = api_client
    with Session() as session:
        packet = _materialized_packet(session, packet_request_id="open-extra-packet")
        packet_set_id = packet["sec_xbrl_statement_packet_set_id"]

    response = client.post(
        WORKFLOW_OPEN_ROUTE,
        json=_open_payload(packet_set_id, raw_value="123.45"),
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_operator_review_workflow_open_request_fields_not_admitted"
    assert body["status"] == "blocked"
    assert body["blocked_fields"] == []
    assert "123.45" not in response.text


def test_operator_review_workflow_open_api_rolls_back_on_binding_failure(api_client, monkeypatch) -> None:
    client, Session = api_client
    with Session() as session:
        packet = _materialized_packet(session, packet_request_id="open-rollback-packet")
        packet_set_id = packet["sec_xbrl_statement_packet_set_id"]

    _force_auth_binding_failure(monkeypatch, source_receipt_kind="operator_review_workflow")

    response = client.post(
        WORKFLOW_OPEN_ROUTE,
        json=_open_payload(packet_set_id, client_request_id="open-rollback"),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "sec_xbrl_auth_binding_forced_failure"

    with Session() as session:
        assert session.query(L3SecXbrlOperatorReviewWorkflow).count() == 0
        assert session.query(L3SecXbrlAuthBindingReceipt).count() == 0
