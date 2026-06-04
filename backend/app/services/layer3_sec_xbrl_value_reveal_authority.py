from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    DatasetVersion,
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlValueRevealAuthorityReceipt,
)
from app.models.models import (
    L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED,
    L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
    L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
    L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
    L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
)
from app.services import layer3_sec_xbrl_operator_review_workflow, layer3_sec_xbrl_sidecar
from app.services.layer3_sec_xbrl_public_authority_guard import (
    RAW_AUTHORITY_KEYS as PUBLIC_RAW_AUTHORITY_KEYS,
    RAW_VALUE_KEYS,
    reject_raw_or_local_authority_with_blocked_keys,
)
from app.services.layer3_utils import json_clone, stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


AUTHORITY_SCHEMA_ID = "layer3.sec_xbrl_value_reveal_authority_receipt.v1"
AUTHORITY_MODE = "sec_xbrl_value_reveal_authority_receipt_v1"
AUTHORITY_OPERATOR_DECISION = "prepare_sec_xbrl_value_reveal_authority"
NEXT_ALLOWED_ACTION = "submit_explicit_sec_xbrl_value_reveal_from_authority_receipt"
AUTHORITY_RECEIPT_REF_PREFIX = "sec-xbrl-value-reveal-authority"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
OPERATOR_CONTACT_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
RAW_DECIMAL_RE = re.compile(r"(?<![A-Za-z0-9_])-?\d+\.\d+(?![A-Za-z0-9_])")
VALUE_REVEAL_RAW_AUTHORITY_KEYS = PUBLIC_RAW_AUTHORITY_KEYS | frozenset(
    {
        "sidecar_receipt_id",
        "raw_sidecar_receipt_id",
        "operator_contact",
        "operator_email",
        "operator_name",
    }
)


class SecXbrlValueRevealAuthorityError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        http_status: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.http_status = http_status


def prepare_value_reveal_authority_receipt(
    db: Session,
    *,
    client_request_id: str,
    sec_xbrl_operator_review_decision_id: str,
    decision_basis_hash: str,
    operator_attestation: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    request_id = _required_text(client_request_id, "client_request_id")
    _reject_raw_or_local_authority(request_id)
    decision_id = _required_text(
        sec_xbrl_operator_review_decision_id,
        "sec_xbrl_operator_review_decision_id",
    )
    basis_hash = _required_hash(decision_basis_hash, "decision_basis_hash")
    operator_actor_hash = _operator_attestation_hash(operator_attestation)

    decision = (
        db.query(L3SecXbrlOperatorReviewDecision)
        .filter(
            L3SecXbrlOperatorReviewDecision.sec_xbrl_operator_review_decision_id == decision_id,
            L3SecXbrlOperatorReviewDecision.decision_basis_hash == basis_hash,
        )
        .one_or_none()
    )
    if decision is None:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_decision_not_found",
            "SEC XBRL value-reveal authority requires an existing matching operator-review decision.",
            details={
                "sec_xbrl_operator_review_decision_id": decision_id,
                "decision_basis_hash": basis_hash,
            },
            http_status=404,
        )

    try:
        decision_status = layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_decision_status(
            db,
            client_request_id=f"sec-xbrl-value-authority-{stable_hash(decision_id)[:16]}",
            sec_xbrl_operator_review_decision_id=decision_id,
            decision_basis_hash=basis_hash,
        )
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_decision_status_invalid",
            "SEC XBRL value-reveal authority requires a clean operator-review decision status projection.",
            details={"decision_status_error_code": exc.code},
            http_status=exc.http_status,
        ) from exc
    _validate_approved_decision(decision)

    workflow = decision.operator_review_workflow
    packet_set = workflow.statement_packet_set if workflow is not None else None
    projection_set = packet_set.projection_set if packet_set is not None else None
    if workflow is None or packet_set is None or projection_set is None:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_lineage_missing",
            "SEC XBRL value-reveal authority requires complete decision, workflow, packet, and projection lineage.",
        )

    _validate_packet_and_projection(
        workflow=workflow,
        packet_set=packet_set,
        projection_set=projection_set,
    )
    dataset_version_hash = _dataset_version_hash(db, projection_set.dataset_version_id)
    sidecar_authority = _resolve_sidecar_authority(
        projection_set.sidecar_receipt_hash,
        projection_set.value_store_hash,
    )
    authority_summary = _authority_summary(
        decision=decision,
        decision_status=decision_status,
        workflow=workflow,
        packet_set=packet_set,
        projection_set=projection_set,
        sidecar_authority=sidecar_authority,
    )
    negative_invariants = _negative_invariants()

    authority_basis = {
        "schema_id": AUTHORITY_SCHEMA_ID,
        "authority_mode": AUTHORITY_MODE,
        "sec_xbrl_operator_review_decision_id": decision.sec_xbrl_operator_review_decision_id,
        "decision_basis_hash": decision.decision_basis_hash,
        "sec_xbrl_operator_review_workflow_id": workflow.sec_xbrl_operator_review_workflow_id,
        "workflow_basis_hash": workflow.workflow_basis_hash,
        "sec_xbrl_statement_packet_set_id": packet_set.sec_xbrl_statement_packet_set_id,
        "statement_packet_basis_hash": packet_set.packet_basis_hash,
        "sec_xbrl_projection_set_id": projection_set.sec_xbrl_projection_set_id,
        "projection_basis_hash": projection_set.projection_basis_hash,
        "dataset_version_id": projection_set.dataset_version_id,
        "dataset_version_hash": dataset_version_hash,
        "sidecar_receipt_id_hash": sidecar_authority["sidecar_receipt_id_hash"],
        "sidecar_receipt_hash": projection_set.sidecar_receipt_hash,
        "value_store_hash": projection_set.value_store_hash,
        "authority_state": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
        "authority_policy_id": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
        "redaction_policy": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
        "operator_actor_hash": operator_actor_hash,
        "authority_summary": authority_summary,
        "negative_invariants": negative_invariants,
    }
    _reject_raw_or_local_authority(authority_basis)
    authority_basis_hash = stable_hash(authority_basis)

    existing_by_request = (
        db.query(L3SecXbrlValueRevealAuthorityReceipt)
        .filter(L3SecXbrlValueRevealAuthorityReceipt.client_request_id == request_id)
        .one_or_none()
    )
    existing_by_basis = (
        db.query(L3SecXbrlValueRevealAuthorityReceipt)
        .filter(L3SecXbrlValueRevealAuthorityReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    existing_by_decision = (
        db.query(L3SecXbrlValueRevealAuthorityReceipt)
        .filter(
            L3SecXbrlValueRevealAuthorityReceipt.sec_xbrl_operator_review_decision_id
            == decision.sec_xbrl_operator_review_decision_id
        )
        .one_or_none()
    )
    if existing_by_request is not None:
        if existing_by_request.authority_basis_hash != authority_basis_hash:
            raise SecXbrlValueRevealAuthorityError(
                "sec_xbrl_value_reveal_authority_client_request_conflict",
                "client_request_id already prepared a different SEC XBRL value-reveal authority basis.",
                details={"client_request_id": request_id},
            )
        return _response(existing_by_request, idempotent_replay=True)
    if existing_by_basis is not None:
        return _response(existing_by_basis, idempotent_replay=True)
    if existing_by_decision is not None:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_decision_already_prepared",
            "SEC XBRL operator-review decision already has an immutable value-reveal authority receipt.",
            details={
                "sec_xbrl_operator_review_decision_id": decision.sec_xbrl_operator_review_decision_id,
                "sec_xbrl_value_reveal_authority_receipt_id": (
                    existing_by_decision.sec_xbrl_value_reveal_authority_receipt_id
                ),
            },
        )

    receipt = L3SecXbrlValueRevealAuthorityReceipt(
        client_request_id=request_id,
        authority_basis_hash=authority_basis_hash,
        authority_schema_id=AUTHORITY_SCHEMA_ID,
        sec_xbrl_operator_review_decision_id=decision.sec_xbrl_operator_review_decision_id,
        decision_basis_hash=decision.decision_basis_hash,
        sec_xbrl_operator_review_workflow_id=workflow.sec_xbrl_operator_review_workflow_id,
        workflow_basis_hash=workflow.workflow_basis_hash,
        sec_xbrl_statement_packet_set_id=packet_set.sec_xbrl_statement_packet_set_id,
        statement_packet_basis_hash=packet_set.packet_basis_hash,
        sec_xbrl_projection_set_id=projection_set.sec_xbrl_projection_set_id,
        projection_basis_hash=projection_set.projection_basis_hash,
        dataset_version_id=_required_text(projection_set.dataset_version_id, "dataset_version_id"),
        dataset_version_hash=dataset_version_hash,
        sidecar_receipt_id_hash=sidecar_authority["sidecar_receipt_id_hash"],
        sidecar_receipt_hash=projection_set.sidecar_receipt_hash,
        value_store_hash=projection_set.value_store_hash,
        authority_state=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
        authority_policy_id=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
        redaction_policy=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
        operator_actor_hash=operator_actor_hash,
        authority_summary_json=json_clone(authority_summary),
        negative_invariants_json=json_clone(negative_invariants),
    )
    try:
        db.add(receipt)
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_integrity_error",
            "SEC XBRL value-reveal authority persistence failed without admitting a partial receipt.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(receipt)
    return _response(receipt, idempotent_replay=False)


def _validate_approved_decision(decision: L3SecXbrlOperatorReviewDecision) -> None:
    if decision.review_decision != "approved":
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_decision_not_approved",
            "SEC XBRL value-reveal authority requires an approved operator-review decision.",
            details={"review_decision": decision.review_decision},
            http_status=400,
        )
    if decision.decision_reason_code != "ready_for_next_freeze":
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_reason_not_ready",
            "SEC XBRL value-reveal authority requires the ready-for-next-freeze decision reason.",
            details={"decision_reason_code": decision.decision_reason_code},
            http_status=400,
        )
    if decision.decision_status != L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_decision_status_invalid",
            "SEC XBRL value-reveal authority requires a recorded decision receipt.",
            details={"decision_status": decision.decision_status},
        )


def _validate_packet_and_projection(*, workflow: Any, packet_set: Any, projection_set: Any) -> None:
    if workflow.review_exception_count != 0 or packet_set.review_exception_count != 0:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_review_exceptions_present",
            "SEC XBRL value-reveal authority v1 requires zero review exceptions.",
            details={
                "workflow_review_exception_count": workflow.review_exception_count,
                "packet_review_exception_count": packet_set.review_exception_count,
            },
            http_status=400,
        )
    if packet_set.status != L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_packet_not_materialized",
            "SEC XBRL value-reveal authority requires a materialized statement packet.",
        )
    if packet_set.value_policy != L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_packet_redaction_invalid",
            "SEC XBRL value-reveal authority requires redacted statement-packet authority.",
        )
    if projection_set.status != L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_projection_not_materialized",
            "SEC XBRL value-reveal authority requires a materialized projection set.",
        )
    if projection_set.redaction_policy != L3_SEC_XBRL_PROJECTION_REDACTION_POLICY:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_projection_redaction_invalid",
            "SEC XBRL value-reveal authority requires redacted projection authority.",
        )
    facts = list(projection_set.facts)
    rows = [row for statement in packet_set.statements for row in statement.rows]
    if not facts or not rows:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_empty_runtime",
            "SEC XBRL value-reveal authority requires existing redacted projection facts and packet rows.",
        )
    if any(fact.value_redacted is not True for fact in facts) or any(row.value_redacted is not True for row in rows):
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_value_redaction_invalid",
            "SEC XBRL value-reveal authority requires every projection fact and packet row to remain value-redacted.",
        )
    if any(row.review_exception is True for row in rows):
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_review_exceptions_present",
            "SEC XBRL value-reveal authority v1 requires zero review-exception rows.",
            http_status=400,
        )
    if {fact.sidecar_receipt_hash for fact in facts} != {projection_set.sidecar_receipt_hash}:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_sidecar_hash_mismatch",
            "SEC XBRL value-reveal authority requires one projection-bound sidecar hash.",
        )
    if {fact.value_store_hash for fact in facts} != {projection_set.value_store_hash}:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_value_store_hash_mismatch",
            "SEC XBRL value-reveal authority requires one projection-bound value-store hash.",
        )


def _dataset_version_hash(db: Session, dataset_version_id: str | None) -> str:
    version_id = _required_text(dataset_version_id, "dataset_version_id")
    version = db.query(DatasetVersion).filter(DatasetVersion.dataset_version_id == version_id).one_or_none()
    if version is None:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_dataset_version_missing",
            "SEC XBRL value-reveal authority requires existing server-owned dataset-version authority.",
            details={"dataset_version_id": version_id},
            http_status=404,
        )
    variables = sorted(version.variables, key=lambda item: item.ordinal_position)
    return stable_hash(
        {
            "dataset_id": version.dataset_id,
            "dataset_version_id": version.dataset_version_id,
            "dataset_name": version.dataset.name if version.dataset is not None else None,
            "version_label": version.version_label,
            "version_type": version.version_type,
            "status": version.status,
            "row_count": int(version.row_count or 0),
            "storage_ref_present": bool(str(version.storage_ref or "").strip()),
            "variables": [
                {
                    "variable_name": item.variable_name,
                    "dtype": item.dtype,
                    "role": item.role,
                    "is_numeric": bool(item.is_numeric),
                    "is_time_index": bool(item.is_time_index),
                    "ordinal_position": item.ordinal_position,
                }
                for item in variables
            ],
        }
    )


def _resolve_sidecar_authority(sidecar_receipt_hash: str, value_store_hash: str) -> dict[str, str]:
    receipt_hash = _required_hash(sidecar_receipt_hash, "sidecar_receipt_hash")
    expected_value_store_hash = _required_hash(value_store_hash, "value_store_hash")
    receipt_id = f"{layer3_sec_xbrl_sidecar.RECEIPT_PREFIX}-{receipt_hash[:24]}"
    try:
        receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
            receipt_id,
            expected_sidecar_receipt_hash=receipt_hash,
        )
    except Layer3WorkbenchError as exc:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_sidecar_missing",
            "SEC XBRL value-reveal authority requires existing matching server-owned sidecar authority.",
            details={"sidecar_receipt_hash": receipt_hash, "sidecar_error_code": exc.error_code},
            http_status=exc.http_status,
        ) from exc
    value_store = receipt.get("internal_value_store")
    if not isinstance(value_store, Mapping):
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_value_store_missing",
            "SEC XBRL value-reveal authority requires a sidecar-bound internal value store.",
        )
    if value_store.get("value_store_hash") != expected_value_store_hash:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_value_store_hash_mismatch",
            "SEC XBRL value-reveal authority requires the sidecar value-store hash to match projection authority.",
        )
    try:
        value_store_payload = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(
            receipt
        )
    except Layer3WorkbenchError as exc:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_value_store_missing",
            "SEC XBRL value-reveal authority requires existing matching server-owned internal value-store authority.",
            details={"value_store_hash": expected_value_store_hash, "value_store_error_code": exc.error_code},
            http_status=exc.http_status,
        ) from exc
    if value_store_payload.get("value_store_hash") != expected_value_store_hash:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_value_store_hash_mismatch",
            "SEC XBRL value-reveal authority requires the persisted internal value-store hash to match projection authority.",
        )
    if receipt.get("sidecar_state") != "ready":
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_sidecar_not_ready",
            "SEC XBRL value-reveal authority requires a READY sidecar receipt.",
        )
    if not isinstance(receipt.get("resolved_fact_projection"), list) or not receipt.get("resolved_fact_projection"):
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_sidecar_projection_missing",
            "SEC XBRL value-reveal authority requires governed resolved-fact projection evidence.",
        )
    raw_receipt_id = _required_text(receipt.get("sidecar_receipt_id"), "sidecar_receipt_id")
    return {
        "sidecar_receipt_id_hash": stable_hash(
            {
                "hash_version": "sec_xbrl_value_reveal_authority_sidecar_receipt_id_hash_v1",
                "sidecar_receipt_id": raw_receipt_id,
            }
        ),
        "sidecar_receipt_hash": receipt_hash,
        "value_store_hash": expected_value_store_hash,
    }


def _authority_summary(
    *,
    decision: L3SecXbrlOperatorReviewDecision,
    decision_status: Mapping[str, Any],
    workflow: Any,
    packet_set: Any,
    projection_set: Any,
    sidecar_authority: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "authority_policy_id": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
        "redaction_policy": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
        "authority_mode": AUTHORITY_MODE,
        "decision_approved": decision.review_decision == "approved",
        "decision_reason_ready": decision.decision_reason_code == "ready_for_next_freeze",
        "decision_status": decision.decision_status,
        "workflow_review_ready": bool(workflow.review_ready),
        "workflow_review_exception_count": int(workflow.review_exception_count),
        "packet_review_exception_count": int(packet_set.review_exception_count),
        "statement_count": int(workflow.statement_count),
        "row_count": int(workflow.row_count),
        "projection_fact_count": len(projection_set.facts),
        "statement_packet_row_count": sum(len(statement.rows) for statement in packet_set.statements),
        "dataset_version_hash_present": True,
        "sidecar_receipt_hash_present": bool(sidecar_authority["sidecar_receipt_hash"]),
        "sidecar_receipt_id_hashed": True,
        "raw_sidecar_receipt_id_persisted": False,
        "value_store_hash_present": bool(sidecar_authority["value_store_hash"]),
        "decision_status_surface_value_reveal_performed": bool(decision_status["value_reveal_performed"]),
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "raw_values_returned": False,
        "raw_values_persisted": False,
        "raw_resolved_fact_authorities_exposed": False,
        "raw_identity_exposed": False,
        "raw_accessions_exposed": False,
        "raw_period_dates_exposed": False,
        "local_paths_exposed": False,
        "sec_urls_exposed": False,
        "operator_contact_exposed": False,
        "residual_magnitudes_exposed": False,
        "runtime_default_changed": False,
        "value_reveal_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "rendered_ui_enabled": False,
        "frontend_durable_authority_used": False,
        "production_readiness_claimed": False,
    }


def _response(row: L3SecXbrlValueRevealAuthorityReceipt, *, idempotent_replay: bool) -> dict[str, Any]:
    return {
        "status": row.authority_state,
        "schema_id": row.authority_schema_id,
        "sec_xbrl_value_reveal_authority_receipt_id": row.sec_xbrl_value_reveal_authority_receipt_id,
        "value_reveal_authority_receipt_ref": (
            f"{AUTHORITY_RECEIPT_REF_PREFIX}:{row.authority_basis_hash[:24]}"
        ),
        "client_request_id": row.client_request_id,
        "authority_basis_hash": row.authority_basis_hash,
        "authority_mode": AUTHORITY_MODE,
        "authority_policy_id": row.authority_policy_id,
        "redaction_policy": row.redaction_policy,
        "sec_xbrl_operator_review_decision_id": row.sec_xbrl_operator_review_decision_id,
        "decision_basis_hash": row.decision_basis_hash,
        "sec_xbrl_operator_review_workflow_id": row.sec_xbrl_operator_review_workflow_id,
        "workflow_basis_hash": row.workflow_basis_hash,
        "sec_xbrl_statement_packet_set_id": row.sec_xbrl_statement_packet_set_id,
        "statement_packet_basis_hash": row.statement_packet_basis_hash,
        "sec_xbrl_projection_set_id": row.sec_xbrl_projection_set_id,
        "projection_basis_hash": row.projection_basis_hash,
        "dataset_version_id": row.dataset_version_id,
        "dataset_version_hash": row.dataset_version_hash,
        "sidecar_receipt_id_hash": row.sidecar_receipt_id_hash,
        "sidecar_receipt_hash": row.sidecar_receipt_hash,
        "value_store_hash": row.value_store_hash,
        "operator_actor_hash": row.operator_actor_hash,
        "authority_summary": json_clone(row.authority_summary_json),
        "negative_invariants": json_clone(row.negative_invariants_json),
        "eligible_for_explicit_value_reveal": True,
        "idempotent_replay": idempotent_replay,
        "next_allowed_actions": [NEXT_ALLOWED_ACTION],
        "runtime_default_enabled": False,
        "value_reveal_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "rendered_ui_enabled": False,
        "production_readiness_claimed": False,
    }


def _operator_attestation_hash(value: str | None) -> str | None:
    if value is None:
        return None
    text = _required_text(value, "operator_attestation")
    if OPERATOR_CONTACT_RE.search(text) or RAW_DECIMAL_RE.search(text):
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_raw_attestation_not_admitted",
            "SEC XBRL value-reveal authority cannot store raw contact or value strings in operator attestation.",
            http_status=400,
        )
    _reject_raw_or_local_authority({"operator_attestation": text})
    return stable_hash({"operator_attestation_present": True, "operator_attestation": text})


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_required_field_missing",
            f"SEC XBRL value-reveal authority requires {field}.",
            details={"field": field},
            http_status=400,
        )
    return text


def _required_hash(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not HASH_RE.fullmatch(text):
        raise SecXbrlValueRevealAuthorityError(
            "sec_xbrl_value_reveal_authority_hash_invalid",
            f"SEC XBRL value-reveal authority requires a 64-character lowercase hex {field}.",
            details={"field": field},
            http_status=400,
        )
    return text


def _reject_raw_or_local_authority(value: Any) -> None:
    reject_raw_or_local_authority_with_blocked_keys(
        value,
        error_type=SecXbrlValueRevealAuthorityError,
        raw_authority_code="sec_xbrl_value_reveal_authority_raw_authority_not_admitted",
        raw_authority_message="SEC XBRL value-reveal authority only admits server-owned hash authority.",
        raw_reference_code="sec_xbrl_value_reveal_authority_raw_reference_not_admitted",
        raw_reference_message=(
            "SEC XBRL value-reveal authority cannot expose raw identities, paths, SEC URLs, accessions, or period dates."
        ),
        blocked_raw_value_keys=RAW_VALUE_KEYS,
        blocked_raw_authority_keys=VALUE_REVEAL_RAW_AUTHORITY_KEYS,
        scan_cik=True,
        scan_contextual_cik=True,
        scan_operator_contact=True,
    )
