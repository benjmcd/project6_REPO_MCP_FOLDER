from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import L3SecXbrlOperatorReviewWorkflow, L3SecXbrlStatementPacketSet
from app.models.models import (
    L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
    L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
    L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
    L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
    L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
)
from app.services.layer3_utils import json_clone, stable_hash


WORKFLOW_SCHEMA_ID = "layer3.sec_xbrl_operator_review_workflow.v1"
PERMITTED_CONTROLS = (
    "inspect_redacted_statement_packet_counts",
    "inspect_review_exceptions",
    "inspect_statement_packet_authority",
    "defer_review_decision",
)
BLOCKED_CONTROLS = (
    ("submit_operator_review_decision", "requires_separate_decision_submit_freeze"),
    ("reveal_values", "value_reveal_not_admitted"),
    ("export_statement_packet", "delivery_export_not_admitted"),
    ("deliver_statement_packet", "delivery_export_not_admitted"),
    ("refresh_from_sec_source", "source_acquisition_not_admitted"),
    ("invoke_arelle", "arelle_not_admitted"),
    ("edit_statement_packet", "packet_mutation_not_admitted"),
    ("change_runtime_default", "default_on_not_admitted"),
)
RAW_VALUE_KEYS = {"_value", "value", "effective_value", "amount"}
RAW_AUTHORITY_KEYS = {
    "resolved_fact_id",
    "resolved_fact_ids",
    "derived_from_resolved_fact_ids",
    "raw_resolved_fact_authority",
    "raw_resolved_fact_authorities",
    "cik",
    "cik_or_filer_ref",
    "filer_or_cik",
    "accession",
    "accession_number",
    "company_name",
    "issuer_name",
    "registrant",
    "registrant_name",
    "ticker",
    "contact",
    "operator_contact",
    "operator_email",
    "operator_name",
    "user_agent",
    "local_path",
    "raw_path",
    "storage_dir",
    "storage_root",
    "sec_url",
}
RESIDUAL_MAGNITUDE_KEYS = {"relative_magnitude", "residual_abs", "residual", "magnitude"}
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
RAW_PERIOD_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class SecXbrlOperatorReviewWorkflowError(ValueError):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "blocked",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": dict(self.details),
            },
        }


def open_redacted_operator_review_workflow(
    db: Session,
    *,
    client_request_id: str,
    sec_xbrl_statement_packet_set_id: str,
) -> dict[str, Any]:
    request_id = _required_text(client_request_id, "client_request_id")
    packet_set_id = _required_text(sec_xbrl_statement_packet_set_id, "sec_xbrl_statement_packet_set_id")
    packet_set = (
        db.query(L3SecXbrlStatementPacketSet)
        .filter(L3SecXbrlStatementPacketSet.sec_xbrl_statement_packet_set_id == packet_set_id)
        .one_or_none()
    )
    if packet_set is None:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_packet_set_missing",
            "Operator review workflow requires an existing persisted SEC XBRL statement packet set.",
            details={"sec_xbrl_statement_packet_set_id": packet_set_id},
        )

    _validate_packet_set(packet_set)
    statement_count = _positive_int(packet_set.statement_count, "statement_count")
    row_count = _positive_int(packet_set.total_review_rows, "total_review_rows")
    review_exception_count = _non_negative_int(packet_set.review_exception_count, "review_exception_count")
    permitted_controls = list(PERMITTED_CONTROLS)
    blocked_controls = [
        {"control": control, "reason": reason}
        for control, reason in BLOCKED_CONTROLS
    ]
    authority_refs = _authority_refs(packet_set)
    review_summary = {
        "statement_count": statement_count,
        "row_count": row_count,
        "review_exception_count": review_exception_count,
        "review_ready": True,
        "redaction_policy": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
        "control_mode": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
    }
    envelope = {
        "schema_id": WORKFLOW_SCHEMA_ID,
        "sec_xbrl_statement_packet_set_id": packet_set.sec_xbrl_statement_packet_set_id,
        "statement_packet_basis_hash": packet_set.packet_basis_hash,
        "source_projection_basis_hash": packet_set.source_projection_basis_hash,
        "control_mode": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
        "review_status": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
        "redaction_policy": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
        "review_summary": review_summary,
        "permitted_controls": permitted_controls,
        "blocked_controls": blocked_controls,
        "authority_refs": authority_refs,
    }
    _reject_raw_or_local_authority(envelope)
    workflow_basis_hash = stable_hash(envelope)

    existing_by_request = (
        db.query(L3SecXbrlOperatorReviewWorkflow)
        .filter(L3SecXbrlOperatorReviewWorkflow.client_request_id == request_id)
        .one_or_none()
    )
    existing_by_basis = (
        db.query(L3SecXbrlOperatorReviewWorkflow)
        .filter(L3SecXbrlOperatorReviewWorkflow.workflow_basis_hash == workflow_basis_hash)
        .one_or_none()
    )
    if existing_by_request is not None:
        if existing_by_request.workflow_basis_hash != workflow_basis_hash:
            raise SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_workflow_client_request_conflict",
                "client_request_id already opened a different SEC XBRL operator review workflow basis.",
                details={"client_request_id": request_id},
            )
        return _response(existing_by_request, idempotent_replay=True)
    if existing_by_basis is not None:
        return _response(existing_by_basis, idempotent_replay=True)

    workflow = L3SecXbrlOperatorReviewWorkflow(
        sec_xbrl_statement_packet_set_id=packet_set.sec_xbrl_statement_packet_set_id,
        client_request_id=request_id,
        workflow_basis_hash=workflow_basis_hash,
        workflow_schema_id=WORKFLOW_SCHEMA_ID,
        statement_packet_basis_hash=packet_set.packet_basis_hash,
        source_projection_basis_hash=packet_set.source_projection_basis_hash,
        control_mode=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
        review_status=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
        redaction_policy=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
        statement_count=statement_count,
        row_count=row_count,
        review_exception_count=review_exception_count,
        review_ready=True,
        permitted_controls_json=json_clone(permitted_controls),
        blocked_controls_json=json_clone(blocked_controls),
        authority_refs_json=json_clone(authority_refs),
        review_summary_json=json_clone(review_summary),
    )
    try:
        db.add(workflow)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_integrity_error",
            "SEC XBRL operator review workflow persistence failed without admitting partial workflow rows.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(workflow)
    return _response(workflow, idempotent_replay=False)


def _validate_packet_set(packet_set: L3SecXbrlStatementPacketSet) -> None:
    if packet_set.status != L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_packet_set_not_materialized",
            "Operator review workflow requires a materialized statement packet set.",
            details={"status": packet_set.status},
        )
    if packet_set.value_policy != L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_redaction_policy_invalid",
            "Operator review workflow requires redacted statement packet authority.",
            details={"value_policy": packet_set.value_policy},
        )
    if packet_set.review_ready is not True:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_packet_set_not_ready",
            "Operator review workflow requires review-ready statement packet authority.",
        )
    if _non_negative_int(packet_set.total_review_rows, "total_review_rows") <= 0:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_empty_packet",
            "Operator review workflow requires at least one redacted review row.",
        )
    if not packet_set.statements:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_empty_packet",
            "Operator review workflow requires persisted statement packet rows.",
        )
    row_count = sum(len(statement.rows) for statement in packet_set.statements)
    if row_count <= 0:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_empty_packet",
            "Operator review workflow requires persisted statement packet rows.",
        )
    for value in (
        packet_set.identity_rollup_json,
        packet_set.organization_contract_json,
        packet_set.packet_summary_json,
    ):
        _reject_raw_or_local_authority(value)


def _authority_refs(packet_set: L3SecXbrlStatementPacketSet) -> dict[str, Any]:
    refs = {
        "sec_xbrl_statement_packet_set_id": packet_set.sec_xbrl_statement_packet_set_id,
        "sec_xbrl_projection_set_id": packet_set.sec_xbrl_projection_set_id,
        "statement_packet_basis_hash": packet_set.packet_basis_hash,
        "statement_packet_schema_id": packet_set.packet_schema_id,
        "source_projection_basis_hash": packet_set.source_projection_basis_hash,
        "source_projection_schema_id": packet_set.source_projection_schema_id,
        "statement_organization_authority": packet_set.statement_organization_authority,
    }
    _reject_raw_or_local_authority(refs)
    return refs


def _response(row: L3SecXbrlOperatorReviewWorkflow, *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "status": row.review_status,
        "schema_id": row.workflow_schema_id,
        "sec_xbrl_operator_review_workflow_id": row.sec_xbrl_operator_review_workflow_id,
        "sec_xbrl_statement_packet_set_id": row.sec_xbrl_statement_packet_set_id,
        "client_request_id": row.client_request_id,
        "workflow_basis_hash": row.workflow_basis_hash,
        "statement_packet_basis_hash": row.statement_packet_basis_hash,
        "source_projection_basis_hash": row.source_projection_basis_hash,
        "control_mode": row.control_mode,
        "redaction_policy": row.redaction_policy,
        "statement_count": row.statement_count,
        "row_count": row.row_count,
        "review_exception_count": row.review_exception_count,
        "review_ready": row.review_ready,
        "permitted_controls": json_clone(row.permitted_controls_json),
        "blocked_controls": json_clone(row.blocked_controls_json),
        "authority_refs": json_clone(row.authority_refs_json),
        "review_summary": json_clone(row.review_summary_json),
        "idempotent_replay": idempotent_replay,
        "runtime_default_enabled": False,
        "value_reveal_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "api_route_enabled": False,
        "rendered_ui_enabled": False,
        "operator_review_decision_recorded": False,
    }


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_required_field_missing",
            f"SEC XBRL operator review workflow requires {field}.",
            details={"field": field},
        )
    return text


def _positive_int(value: Any, field: str) -> int:
    number = _non_negative_int(value, field)
    if number <= 0:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_integer_invalid",
            f"SEC XBRL operator review workflow requires a positive {field}.",
            details={"field": field},
        )
    return number


def _non_negative_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_integer_invalid",
            f"SEC XBRL operator review workflow requires an integer {field}.",
            details={"field": field},
        ) from exc
    if number < 0:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_workflow_integer_invalid",
            f"SEC XBRL operator review workflow requires a non-negative {field}.",
            details={"field": field},
        )
    return number


def _reject_raw_or_local_authority(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_match = key_text.strip().lower()
            if key_match in RAW_VALUE_KEYS or key_match in RAW_AUTHORITY_KEYS:
                if item is not None:
                    raise SecXbrlOperatorReviewWorkflowError(
                        "sec_xbrl_operator_review_workflow_raw_authority_not_admitted",
                        "SEC XBRL operator review workflow cannot store raw values or raw authority identifiers.",
                        details={"field": key_text},
                    )
            if key_match in RESIDUAL_MAGNITUDE_KEYS and item is not None:
                raise SecXbrlOperatorReviewWorkflowError(
                    "sec_xbrl_operator_review_workflow_residual_magnitudes_not_admitted",
                    "SEC XBRL operator review workflow cannot store residual magnitude fields.",
                    details={"field": key_text},
                )
            _reject_raw_or_local_authority(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_raw_or_local_authority(item)
        return
    if isinstance(value, str):
        if (
            ACCESSION_RE.search(value)
            or SEC_URL_RE.search(value)
            or WINDOWS_ABS_PATH_RE.search(value)
            or RAW_PERIOD_DATE_RE.search(value)
        ):
            raise SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_workflow_raw_reference_not_admitted",
                "SEC XBRL operator review workflow cannot store raw accession, SEC URL, period date, or local path strings.",
            )
