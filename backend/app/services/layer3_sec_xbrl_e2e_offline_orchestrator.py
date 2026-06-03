from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.services.layer3_sec_xbrl_canonical_concepts import (
    project_issuer_canonical_facts_by_periods,
)
from app.services.layer3_sec_xbrl_e2e_integration import (
    build_reviewable_statement_packet_from_projection,
    redacted_projection_persistence_payload,
)
from app.services.layer3_sec_xbrl_operator_review_workflow import (
    open_redacted_operator_review_workflow,
)
from app.services.layer3_sec_xbrl_projection_persistence import (
    materialize_redacted_projection_set,
)
from app.services.layer3_sec_xbrl_statement_packet_persistence import (
    materialize_redacted_statement_packet,
)
from app.services.layer3_utils import json_clone, stable_hash


SCHEMA_ID = "layer3.sec_xbrl_e2e_offline_evidence_orchestrator.v1"
SOURCE_REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_e2e_offline_evidence_authority.v1"
ATOMIC_FAULT_AFTER_PROJECTION = "after_projection_flush"
ATOMIC_FAULT_AFTER_STATEMENT_PACKET = "after_statement_packet_flush"
ATOMIC_FAULT_AFTER_OPERATOR_REVIEW_WORKFLOW = "after_operator_review_workflow_flush"
ATOMIC_FAULT_INJECTION_POINTS = {
    ATOMIC_FAULT_AFTER_PROJECTION,
    ATOMIC_FAULT_AFTER_STATEMENT_PACKET,
    ATOMIC_FAULT_AFTER_OPERATOR_REVIEW_WORKFLOW,
}

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
LOCAL_REF_RE = re.compile(
    r"(?i)(?:"
    r"file://"
    r"|\\\\[^\\/]+[\\/]"
    r"|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$)"
    r")"
)
RAW_PUBLIC_KEYS = {
    "accession",
    "accession_number",
    "cik",
    "company_name",
    "issuer_name",
    "local_path",
    "raw_path",
    "registrant",
    "registrant_name",
    "sec_url",
    "storage_dir",
    "storage_root",
    "ticker",
}


class SecXbrlE2EOfflineOrchestratorError(ValueError):
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


def open_redacted_operator_review_from_offline_evidence(
    db: Session,
    *,
    client_request_id: str,
    evidence: Mapping[str, Any],
    source_report_schema_id: str = SOURCE_REPORT_SCHEMA_ID,
    source_report_hash: str | None = None,
    period_limit: int = 3,
    include_sector_families: bool = False,
    single_transaction: bool = False,
    commit: bool = True,
    fault_injection_point: str | None = None,
) -> dict[str, Any]:
    """Compose already-loaded offline SEC XBRL evidence into an open redacted review workflow."""

    request_id = _required_public_text(client_request_id, "client_request_id")
    evidence_map = _required_mapping(evidence, "evidence")
    limit = _positive_int(period_limit, "period_limit")
    atomic = bool(single_transaction)
    fault = _normalise_fault_injection_point(fault_injection_point)
    if fault is not None and not atomic:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_fault_requires_atomic_transaction",
            "SEC XBRL offline orchestration fault injection is only admitted for single-transaction mode.",
            details={"fault_injection_point": fault},
        )
    if not atomic and commit is False:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_commit_false_requires_atomic_transaction",
            "SEC XBRL offline orchestration commit=false is only admitted for single-transaction mode.",
            details={"single_transaction": False, "commit": False},
        )
    companyfacts = _required_mapping(evidence_map.get("companyfacts"), "companyfacts")
    sidecar_receipt = _required_mapping(evidence_map.get("sidecar_receipt"), "sidecar_receipt")
    value_store = _required_mapping(evidence_map.get("value_store"), "value_store")
    statement_roles = _required_sequence(
        evidence_map.get("statement_role_view_records"),
        "statement_role_view_records",
    )
    if not statement_roles:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_statement_role_authority_missing",
            "SEC XBRL offline orchestration requires statement-role authority records.",
        )

    source_schema = _required_public_text(source_report_schema_id, "source_report_schema_id")
    sidecar_receipt_id = _required_public_text(
        sidecar_receipt.get("sidecar_receipt_id"),
        "sidecar_receipt_id",
    )
    sidecar_receipt_hash = _required_hash(sidecar_receipt.get("sidecar_receipt_hash"), "sidecar_receipt_hash")
    sidecar_records = _required_sequence(sidecar_receipt.get("resolved_fact_records"), "resolved_fact_records")
    resolved_fact_projection = _required_sequence(
        sidecar_receipt.get("resolved_fact_projection"),
        "resolved_fact_projection",
    )
    _validate_resolved_projection(
        sidecar_records=sidecar_records,
        resolved_fact_projection=resolved_fact_projection,
        sidecar_receipt=sidecar_receipt,
    )

    value_records = _required_sequence(value_store.get("value_records"), "value_records")
    value_store_hash = _value_store_hash(value_store=value_store, value_records=value_records, sidecar_receipt=sidecar_receipt)
    dataset_version_id = _optional_public_text(evidence_map.get("dataset_version_id") or sidecar_receipt.get("dataset_version_id"))
    normalised_statement_roles = [_normalise_statement_role_record(record) for record in statement_roles]
    statement_role_view_hash = stable_hash(normalised_statement_roles)

    report_hash = _required_hash(
        source_report_hash
        or stable_hash(
            {
                "schema_id": SCHEMA_ID,
                "source_report_schema_id": source_schema,
                "sidecar_receipt_hash": sidecar_receipt_hash,
                "value_store_hash": value_store_hash,
                "statement_role_view_hash": statement_role_view_hash,
                "dataset_version_id": dataset_version_id,
                "period_limit": limit,
                "include_sector_families": bool(include_sector_families),
            }
        ),
        "source_report_hash",
    )

    canonical_projection = project_issuer_canonical_facts_by_periods(
        companyfacts=companyfacts,
        sidecar_records=list(sidecar_records),
        value_records=list(value_records),
        sidecar_receipt_id=sidecar_receipt_id,
        sidecar_receipt_hash=sidecar_receipt_hash,
        value_store_hash=value_store_hash,
        dataset_version_id=dataset_version_id,
        period_limit=limit,
        include_sector_families=bool(include_sector_families),
    )
    if canonical_projection.get("status") != "canonical_multi_period_projection_ready":
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_canonical_projection_not_ready",
            "SEC XBRL offline orchestration requires ready multi-period canonical projection output.",
            details={"status": str(canonical_projection.get("status") or "")},
        )

    canonical_projection = _canonical_projection_with_authority(
        canonical_projection,
        sidecar_receipt_hash=sidecar_receipt_hash,
        value_store_hash=value_store_hash,
        dataset_version_id=dataset_version_id,
    )
    projection_payload = redacted_projection_persistence_payload(canonical_projection)
    statement_packet = build_reviewable_statement_packet_from_projection(
        canonical_projection=canonical_projection,
        statement_role_view_records=normalised_statement_roles,
        identity_residuals=_identity_residuals(canonical_projection),
    )
    if statement_packet.get("status") != "statement_assembly_ready" or statement_packet.get("review_ready") is not True:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_statement_packet_blocked",
            "SEC XBRL offline orchestration requires review-ready statement packet assembly before persistence.",
            details={
                "status": str(statement_packet.get("status") or ""),
                "review_ready": statement_packet.get("review_ready") is True,
                "blocking_reasons": list(statement_packet.get("blocking_reasons") or []),
            },
        )

    try:
        projection_response = materialize_redacted_projection_set(
            db,
            client_request_id=f"{request_id}:projection",
            projection=projection_payload,
            source_report_schema_id=source_schema,
            source_report_hash=report_hash,
            commit=not atomic,
        )
        _raise_if_atomic_fault(fault, ATOMIC_FAULT_AFTER_PROJECTION)
        packet_response = materialize_redacted_statement_packet(
            db,
            client_request_id=f"{request_id}:statement-packet",
            sec_xbrl_projection_set_id=projection_response["sec_xbrl_projection_set_id"],
            packet=statement_packet,
            commit=not atomic,
        )
        _raise_if_atomic_fault(fault, ATOMIC_FAULT_AFTER_STATEMENT_PACKET)
        workflow_response = open_redacted_operator_review_workflow(
            db,
            client_request_id=f"{request_id}:operator-review",
            sec_xbrl_statement_packet_set_id=packet_response["sec_xbrl_statement_packet_set_id"],
            commit=not atomic,
        )
        _raise_if_atomic_fault(fault, ATOMIC_FAULT_AFTER_OPERATOR_REVIEW_WORKFLOW)
        if atomic:
            _raise_if_partial_atomic_replay(
                projection_response=projection_response,
                packet_response=packet_response,
                workflow_response=workflow_response,
            )
            if commit:
                db.commit()
            else:
                db.flush()
    except Exception:
        if atomic:
            db.rollback()
        raise
    examined_absent_period_refs = _examined_absent_period_refs(canonical_projection)
    response = {
        "schema_id": SCHEMA_ID,
        "status": workflow_response["status"],
        "client_request_id": request_id,
        "sec_xbrl_projection_set_id": projection_response["sec_xbrl_projection_set_id"],
        "sec_xbrl_statement_packet_set_id": packet_response["sec_xbrl_statement_packet_set_id"],
        "sec_xbrl_operator_review_workflow_id": workflow_response["sec_xbrl_operator_review_workflow_id"],
        "workflow_basis_hash": workflow_response.get("workflow_basis_hash"),
        "statement_packet_basis_hash": workflow_response.get("statement_packet_basis_hash"),
        "source_projection_basis_hash": workflow_response.get("source_projection_basis_hash"),
        "source_report_schema_id": source_schema,
        "source_report_hash": report_hash,
        "authority_refs": {
            "sidecar_receipt_hash": sidecar_receipt_hash,
            "value_store_hash": value_store_hash,
            "statement_role_view_hash": statement_role_view_hash,
        },
        "summary": {
            "period_count": int(canonical_projection.get("period_count") or 0),
            "ready_period_count": int(canonical_projection.get("ready_period_count") or 0),
            "projected_count": int(canonical_projection.get("projected_count") or 0),
            "empty_period_count": len(examined_absent_period_refs),
            "examined_absent_period_refs": examined_absent_period_refs,
            "statement_count": packet_response["statement_count"],
            "row_count": workflow_response["row_count"],
            "review_exception_count": workflow_response["review_exception_count"],
        },
        "containment": {
            "existing_materializers_commit_per_stage": not atomic,
            "single_transaction_claimed": atomic,
            "transaction_boundary": "caller_owned_session" if atomic else "stage_owned_commits",
            "pre_persistence_projection_and_packet_preflight_passed": True,
        },
        "controls": {
            "offline_evidence_input_only": True,
            "file_read_performed": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "value_reveal_performed": False,
            "api_route_enabled": False,
            "production_readiness_claimed": False,
        },
    }
    _reject_public_raw_or_local_authority(response)
    return response


def _normalise_fault_injection_point(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text not in ATOMIC_FAULT_INJECTION_POINTS:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_fault_point_invalid",
            "SEC XBRL offline orchestration received an unknown transaction fault injection point.",
            details={"fault_injection_point": text},
        )
    return text


def _raise_if_atomic_fault(actual: str | None, expected: str) -> None:
    if actual != expected:
        return
    raise SecXbrlE2EOfflineOrchestratorError(
        "sec_xbrl_e2e_offline_orchestrator_atomic_fault_injected",
        "Injected SEC XBRL offline orchestration fault for transaction rollback proof.",
        details={"fault_injection_point": expected},
    )


def _raise_if_partial_atomic_replay(
    *,
    projection_response: Mapping[str, Any],
    packet_response: Mapping[str, Any],
    workflow_response: Mapping[str, Any],
) -> None:
    replay_flags = {
        "projection": projection_response.get("idempotent_replay") is True,
        "statement_packet": packet_response.get("idempotent_replay") is True,
        "operator_review_workflow": workflow_response.get("idempotent_replay") is True,
    }
    if any(replay_flags.values()) and not all(replay_flags.values()):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_partial_atomic_replay_not_admitted",
            "SEC XBRL offline orchestration cannot claim an atomic transaction from a partial idempotent replay.",
            details={"idempotent_replay": replay_flags},
        )


def _examined_absent_period_refs(canonical_projection: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    periods = canonical_projection.get("periods")
    if not isinstance(periods, Sequence) or isinstance(periods, (str, bytes)):
        return refs
    for period in periods:
        if not isinstance(period, Mapping):
            continue
        projection = period.get("projection")
        if not isinstance(projection, Mapping) or int(projection.get("projected_count") or 0) != 0:
            continue
        period_ref = str(period.get("period_ref") or "").strip()
        if period_ref:
            refs.append(period_ref)
    return refs


def _validate_resolved_projection(
    *,
    sidecar_records: Sequence[Mapping[str, Any]],
    resolved_fact_projection: Sequence[Mapping[str, Any]],
    sidecar_receipt: Mapping[str, Any],
) -> None:
    if not sidecar_records or not resolved_fact_projection:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_sidecar_projection_missing",
            "SEC XBRL offline orchestration requires sidecar records and resolved_fact_projection.",
        )
    expected_hash = str(sidecar_receipt.get("resolved_fact_inventory_hash") or "").strip()
    if expected_hash and stable_hash(list(resolved_fact_projection)) != expected_hash:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_sidecar_projection_hash_mismatch",
            "SEC XBRL offline sidecar resolved_fact_projection is stale or hash-mismatched.",
        )
    projection_by_id = {
        str(item.get("resolved_fact_id") or "").strip(): item
        for item in resolved_fact_projection
        if isinstance(item, Mapping) and str(item.get("resolved_fact_id") or "").strip()
    }
    missing_ids: list[str] = []
    for record in sidecar_records:
        if not isinstance(record, Mapping):
            continue
        fact_id = str(record.get("resolved_fact_id") or "").strip()
        if fact_id and fact_id not in projection_by_id:
            missing_ids.append(fact_id)
    if missing_ids:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_sidecar_projection_unbound",
            "SEC XBRL offline sidecar projection does not bind every resolved fact id.",
            details={"missing_count": len(missing_ids)},
        )
    for item in resolved_fact_projection:
        if not isinstance(item, Mapping):
            raise SecXbrlE2EOfflineOrchestratorError(
                "sec_xbrl_e2e_offline_orchestrator_sidecar_projection_invalid",
                "SEC XBRL offline sidecar projection entries must be objects.",
            )
        for key in ("value", "effective_value", "lexical_value"):
            if item.get(key) is not None:
                raise SecXbrlE2EOfflineOrchestratorError(
                    "sec_xbrl_e2e_offline_orchestrator_sidecar_projection_not_redacted",
                    "SEC XBRL offline sidecar projection must not expose raw values.",
                    details={"field": key},
                )
        if item.get("value_redacted") is not True:
            raise SecXbrlE2EOfflineOrchestratorError(
                "sec_xbrl_e2e_offline_orchestrator_sidecar_projection_not_redacted",
                "SEC XBRL offline sidecar projection must explicitly mark values redacted.",
                details={"field": "value_redacted"},
            )


def _value_store_hash(
    *,
    value_store: Mapping[str, Any],
    value_records: Sequence[Mapping[str, Any]],
    sidecar_receipt: Mapping[str, Any],
) -> str:
    computed = stable_hash(list(value_records))
    declared = _required_hash(value_store.get("value_store_hash"), "value_store_hash")
    if declared != computed:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_value_store_hash_mismatch",
            "SEC XBRL offline value store hash is stale or mismatched.",
        )
    metadata = sidecar_receipt.get("internal_value_store")
    if isinstance(metadata, Mapping):
        metadata_hash = str(metadata.get("value_store_hash") or "").strip()
        if metadata_hash and metadata_hash != declared:
            raise SecXbrlE2EOfflineOrchestratorError(
                "sec_xbrl_e2e_offline_orchestrator_value_store_sidecar_hash_mismatch",
                "SEC XBRL offline value store hash does not match sidecar metadata.",
            )
    authority = sidecar_receipt.get("authority_hashes")
    if isinstance(authority, Mapping):
        authority_hash = str(authority.get("internal_value_store_hash") or "").strip()
        if authority_hash and authority_hash != declared:
            raise SecXbrlE2EOfflineOrchestratorError(
                "sec_xbrl_e2e_offline_orchestrator_value_store_authority_hash_mismatch",
                "SEC XBRL offline value store hash does not match sidecar authority hashes.",
            )
    return declared


def _identity_residuals(canonical_projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    for period in canonical_projection.get("periods") or []:
        if not isinstance(period, Mapping):
            continue
        projection = period.get("projection")
        if isinstance(projection, Mapping):
            residuals.extend(json_clone(projection.get("statement_identity_residuals") or []))
    return residuals


def _canonical_projection_with_authority(
    canonical_projection: Mapping[str, Any],
    *,
    sidecar_receipt_hash: str,
    value_store_hash: str,
    dataset_version_id: str | None,
) -> dict[str, Any]:
    value = copy.deepcopy(canonical_projection)
    periods = value.get("periods") if isinstance(value.get("periods"), Sequence) else []
    for period in periods:
        if not isinstance(period, dict):
            continue
        projection = period.get("projection")
        if not isinstance(projection, dict):
            continue
        projection.setdefault("sidecar_receipt_hash", sidecar_receipt_hash)
        projection.setdefault("value_store_hash", value_store_hash)
        if dataset_version_id is not None:
            projection.setdefault("dataset_version_id", dataset_version_id)
    return value


def _normalise_statement_role_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_statement_role_record_invalid",
            "SEC XBRL statement-role authority records must be objects.",
        )
    fact_id = _required_public_text(
        record.get("fact_id_or_order_key") or record.get("resolved_fact_id"),
        "fact_id_or_order_key",
    )
    role = _required_public_text(record.get("statement_candidate_role"), "statement_candidate_role")
    output = json_clone(dict(record))
    output["fact_id_or_order_key"] = fact_id
    output["statement_candidate_role"] = role
    _reject_public_raw_or_local_authority(output)
    return output


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_required_mapping_missing",
            f"SEC XBRL offline orchestration requires {field}.",
            details={"field": field},
        )
    return value


def _required_sequence(value: Any, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_required_sequence_missing",
            f"SEC XBRL offline orchestration requires a list for {field}.",
            details={"field": field},
        )
    items = list(value)
    if any(not isinstance(item, Mapping) for item in items):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_required_sequence_invalid",
            f"SEC XBRL offline orchestration requires object entries for {field}.",
            details={"field": field},
        )
    return items


def _required_hash(value: Any, field: str) -> str:
    text = _required_public_text(value, field).lower()
    if not HASH_RE.fullmatch(text):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_hash_invalid",
            f"SEC XBRL offline orchestration requires a 64-character lowercase hex hash for {field}.",
            details={"field": field},
        )
    return text


def _required_public_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_required_field_missing",
            f"SEC XBRL offline orchestration requires {field}.",
            details={"field": field},
        )
    _reject_public_text_patterns(text, field=field)
    return text


def _optional_public_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    _reject_public_text_patterns(text, field="public_text")
    return text


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_integer_invalid",
            f"SEC XBRL offline orchestration requires an integer {field}.",
            details={"field": field},
        ) from exc
    if number <= 0:
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_integer_invalid",
            f"SEC XBRL offline orchestration requires a positive {field}.",
            details={"field": field},
        )
    return number


def _reject_public_raw_or_local_authority(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text.strip().lower() in RAW_PUBLIC_KEYS and item is not None:
                raise SecXbrlE2EOfflineOrchestratorError(
                    "sec_xbrl_e2e_offline_orchestrator_raw_public_authority_not_admitted",
                    "SEC XBRL offline orchestration output cannot carry raw identity, path, or source references.",
                    details={"field": key_text},
                )
            _reject_public_raw_or_local_authority(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_public_raw_or_local_authority(item)
        return
    _reject_public_text_patterns(value, field="value")


def _reject_public_text_patterns(value: Any, *, field: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_public_text_patterns(item, field=str(key))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_public_text_patterns(item, field=field)
        return
    if not isinstance(value, str):
        return
    if ACCESSION_RE.search(value) or SEC_URL_RE.search(value) or WINDOWS_ABS_PATH_RE.search(value) or LOCAL_REF_RE.search(value):
        raise SecXbrlE2EOfflineOrchestratorError(
            "sec_xbrl_e2e_offline_orchestrator_raw_reference_not_admitted",
            "SEC XBRL offline orchestration public output cannot carry raw accession, SEC URL, or local path strings.",
            details={"field": field},
        )
