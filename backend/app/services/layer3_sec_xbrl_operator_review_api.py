"""Validate-only SEC XBRL operator-review open API service.

This module is intentionally a thin API boundary around the offline atomic
operator-review workflow. It accepts only server-owned authority handles, not
raw filings, accession numbers, storage paths, URLs, or extracted evidence
payloads supplied by an API caller.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.services import layer3_sec_xbrl_e2e_offline_orchestrator
from app.services.layer3_sec_xbrl_operator_review_workflow import (
    SecXbrlOperatorReviewWorkflowError,
)


_LOWER_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_HANDLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")
_ACCESSION_HANDLE_RE = re.compile(r"^(?:\d{10}-\d{2}-\d{6}|\d{18})$")
_RAW_HANDLE_MARKERS = (
    "\\",
    "/",
    "..",
    "file:",
    "http:",
    "https:",
    "s3:",
    "gs:",
    ".htm",
    ".html",
    ".xml",
    ".json",
)
_REQUIRED_EVIDENCE_MAPPING_FIELDS = (
    "companyfacts",
    "sidecar_receipt",
    "value_store",
)
_REQUIRED_EVIDENCE_SEQUENCE_FIELDS = (
    "statement_role_view_records",
)
_SERVER_OWNED_AUTHORITY_EVIDENCE: dict[str, dict[str, Any]] = {}


def _raise_invalid_request(code: str, message: str, **details: Any) -> None:
    raise SecXbrlOperatorReviewWorkflowError(
        code,
        message,
        details=details,
        http_status=400,
    )


def _validate_source_report_hash(source_report_hash: str) -> str:
    if not _LOWER_HEX_64_RE.fullmatch(source_report_hash or ""):
        _raise_invalid_request(
            "sec_xbrl_operator_review_open_source_report_hash_not_admitted",
            "proof_source_report_hash must be a redacted 64-character lowercase hex authority hash.",
        )
    return source_report_hash


def _validate_authority_handle(handle: str) -> str:
    normalized = (handle or "").strip()
    lowered = normalized.lower()
    if not _PUBLIC_HANDLE_RE.fullmatch(normalized):
        _raise_invalid_request(
            "sec_xbrl_operator_review_open_authority_handle_not_admitted",
            "operator_review_authority_handle must be a compact server-owned public handle.",
        )
    if any(marker in lowered for marker in _RAW_HANDLE_MARKERS):
        _raise_invalid_request(
            "sec_xbrl_operator_review_open_raw_authority_not_admitted",
            "operator_review_authority_handle must not contain raw filing, path, URL, storage, or extracted evidence markers.",
            authority_handle=normalized,
        )
    if _ACCESSION_HANDLE_RE.fullmatch(normalized):
        _raise_invalid_request(
            "sec_xbrl_operator_review_open_accession_handle_not_admitted",
            "operator_review_authority_handle must be a server-owned authority handle, not an accession identifier.",
            authority_handle=normalized,
        )
    return normalized


def _validate_offline_evidence_mapping(evidence: Mapping[str, Any]) -> Mapping[str, Any]:
    for field in _REQUIRED_EVIDENCE_MAPPING_FIELDS:
        if not isinstance(evidence.get(field), Mapping):
            raise SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_open_authority_evidence_field_missing",
                "Registered SEC XBRL operator-review authority evidence is missing a required mapping field.",
                details={"field": field},
                http_status=409,
            )
    for field in _REQUIRED_EVIDENCE_SEQUENCE_FIELDS:
        value = evidence.get(field)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise SecXbrlOperatorReviewWorkflowError(
                "sec_xbrl_operator_review_open_authority_evidence_field_missing",
                "Registered SEC XBRL operator-review authority evidence is missing a required sequence field.",
                details={"field": field},
                http_status=409,
            )
    return evidence


def clear_sec_xbrl_operator_review_authority_registry() -> None:
    """Clear the process-local server-owned authority registry.

    This is a test/runtime lifecycle helper, not an API surface. Clearing the
    registry returns the resolver to its fail-closed unconfigured state.
    """

    _SERVER_OWNED_AUTHORITY_EVIDENCE.clear()


def register_sec_xbrl_operator_review_authority_evidence(
    operator_review_authority_handle: str,
    evidence: Mapping[str, Any],
    *,
    proof_source_report_hash: str,
    replace: bool = False,
) -> dict[str, str]:
    """Register trusted offline evidence behind a server-owned public handle.

    Registration is intentionally code-owned. The API route still receives only
    the public handle plus proof source hash, and never accepts the evidence
    payload, local paths, accessions, SEC URLs, or raw CompanyFacts from a
    client request.
    """

    authority_handle = _validate_authority_handle(operator_review_authority_handle)
    source_hash = _validate_source_report_hash(proof_source_report_hash)
    if not isinstance(evidence, Mapping):
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_evidence_invalid",
            "Registered SEC XBRL operator-review authority evidence must be a mapping.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=409,
        )
    validated_evidence = _validate_offline_evidence_mapping(evidence)
    if authority_handle in _SERVER_OWNED_AUTHORITY_EVIDENCE and not replace:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_handle_already_registered",
            "SEC XBRL operator-review authority handle is already registered.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=409,
        )
    _SERVER_OWNED_AUTHORITY_EVIDENCE[authority_handle] = {
        "proof_source_report_hash": source_hash,
        "evidence": validated_evidence,
    }
    return {
        "operator_review_authority_handle": authority_handle,
        "proof_source_report_hash": source_hash,
    }


def _registered_source_report_hash(authority_handle: str) -> str | None:
    entry = _SERVER_OWNED_AUTHORITY_EVIDENCE.get(authority_handle)
    if not entry:
        return None
    return str(entry.get("proof_source_report_hash") or "")


def resolve_sec_xbrl_operator_review_authority_handle(
    operator_review_authority_handle: str,
) -> Mapping[str, Any]:
    """Resolve a server-owned evidence handle into offline evidence.

    The default resolver is a process-local server-owned registry. Empty or
    unknown registries fail closed; API callers cannot populate the registry.
    """

    authority_handle = _validate_authority_handle(operator_review_authority_handle)
    if not _SERVER_OWNED_AUTHORITY_EVIDENCE:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_resolver_unconfigured",
            "No server-owned SEC XBRL operator-review authority resolver is configured.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=409,
        )
    entry = _SERVER_OWNED_AUTHORITY_EVIDENCE.get(authority_handle)
    if not entry:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_handle_unknown",
            "SEC XBRL operator-review authority handle is not registered with the server-owned resolver.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=404,
        )
    evidence = entry.get("evidence")
    if not isinstance(evidence, Mapping):
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_evidence_invalid",
            "Registered SEC XBRL operator-review authority evidence must be a mapping.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=409,
        )
    return _validate_offline_evidence_mapping(evidence)


def open_atomic_sec_xbrl_operator_review_from_authority(
    db: Session,
    *,
    client_request_id: str,
    operator_review_authority_handle: str,
    source_report_hash: str,
    period_limit: int = 3,
    commit: bool = True,
) -> dict[str, Any]:
    authority_handle = _validate_authority_handle(operator_review_authority_handle)
    validated_source_hash = _validate_source_report_hash(source_report_hash)
    evidence = resolve_sec_xbrl_operator_review_authority_handle(authority_handle)
    registered_source_hash = _registered_source_report_hash(authority_handle)
    if registered_source_hash and registered_source_hash != validated_source_hash:
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_hash_mismatch",
            "SEC XBRL operator-review authority handle is not bound to the requested proof source hash.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=409,
        )
    if not isinstance(evidence, Mapping):
        raise SecXbrlOperatorReviewWorkflowError(
            "sec_xbrl_operator_review_open_authority_evidence_invalid",
            "Resolved SEC XBRL operator-review authority evidence must be a mapping.",
            details={"operator_review_authority_handle": authority_handle},
            http_status=409,
        )

    try:
        response = layer3_sec_xbrl_e2e_offline_orchestrator.open_redacted_operator_review_from_offline_evidence(
            db,
            client_request_id=client_request_id,
            evidence=evidence,
            period_limit=period_limit,
            source_report_hash=validated_source_hash,
            single_transaction=True,
            commit=commit,
        )
    except layer3_sec_xbrl_e2e_offline_orchestrator.SecXbrlE2EOfflineOrchestratorError as exc:
        raise SecXbrlOperatorReviewWorkflowError(
            exc.code,
            exc.message,
            details=exc.details,
            http_status=getattr(exc, "http_status", 409),
        ) from exc

    response["operator_review_authority_handle"] = authority_handle
    response["operator_review_authority_resolved"] = True
    response["operator_review_authority_registered"] = registered_source_hash is not None
    response["operator_review_authority_source_hash_matched"] = (
        registered_source_hash == validated_source_hash if registered_source_hash else None
    )
    response["operator_review_open_api_runtime"] = "server_owned_authority_handle_only"
    return response
