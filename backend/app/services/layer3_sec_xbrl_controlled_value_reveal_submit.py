from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from collections.abc import Mapping
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import L3SecXbrlControlledValueRevealSubmitReceipt, L3SecXbrlValueRevealAuthorityReceipt
from app.models.models import (
    L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_POLICY_ID,
    L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_REDACTION_POLICY,
    L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
)
from app.services import (
    layer3_sec_edgar_arelle_value_reveal,
    layer3_sec_xbrl_operator_review_workflow,
    layer3_sec_xbrl_sidecar,
    layer3_sec_xbrl_value_reveal_authority,
)
from app.services.layer3_sec_xbrl_public_authority_guard import (
    raw_or_local_authority_violation,
    reject_value_reveal_raw_or_local_authority,
)
from app.services.layer3_utils import json_clone, stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SUBMIT_SCHEMA_ID = "layer3.sec_xbrl_controlled_value_reveal_submit.v1"
STATUS_SCHEMA_ID = "layer3.sec_xbrl_controlled_value_reveal_submit_status.v1"
PAGE_CURSOR_SCHEMA_ID = "layer3.sec_xbrl_controlled_value_reveal_submit_page_cursor.v1"
PAGE_CURSOR_VERSION = 1
PAGE_CURSOR_SIGNATURE_SECRET_ENV_VAR = "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_CURSOR_SECRET"
PAGE_CURSOR_PROCESS_SECRET = secrets.token_bytes(32)
SUBMIT_MODE = "sec_xbrl_controlled_value_reveal_submit_v1"
SUBMIT_OPERATOR_DECISION = "submit_explicit_sec_xbrl_value_reveal_from_authority_receipt"
SUBMIT_RECEIPT_REF_PREFIX = "sec-xbrl-controlled-value-reveal-submit"
MAX_REVEAL_RECORDS = 1000
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RAW_REQUEST_KEYS = {
    "sidecar_receipt_id",
    "sidecar_receipt_hash",
    "dataset_version_id",
    "dataset_version_hash",
    "value_store_hash",
    "raw_sidecar_receipt_id",
    "resolved_fact_id",
    "resolved_fact_ids",
    "accession",
    "accession_number",
    "cik",
    "ticker",
    "company_name",
    "issuer_name",
    "registrant",
    "contact",
    "operator_contact",
    "operator_email",
    "local_path",
    "raw_path",
    "storage_dir",
    "source_url",
    "sec_url",
    "arelle",
    "delivery",
    "export",
    "default_on",
}


class SecXbrlControlledValueRevealSubmitError(ValueError):
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


def submit_controlled_value_reveal(
    db: Session,
    *,
    client_request_id: str,
    sec_xbrl_value_reveal_authority_receipt_id: str,
    authority_basis_hash: str,
    operator_reveal_confirmation: bool,
    max_records: int | None = None,
    page_cursor: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    request_id = _required_text(client_request_id, "client_request_id")
    _reject_raw_or_local_authority(request_id)
    if not settings.layer3_sec_xbrl_controlled_value_reveal_submit_enabled:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled",
            "SEC XBRL controlled value-reveal submit is feature-flagged and currently disabled.",
        )
    if operator_reveal_confirmation is not True:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_confirmation_required",
            "SEC XBRL controlled value-reveal submit requires explicit operator confirmation.",
            details={"blocked_keys": ["operator_reveal_confirmation"]},
            http_status=400,
        )
    cap = _max_records(max_records)
    receipt_id = _required_text(
        sec_xbrl_value_reveal_authority_receipt_id,
        "sec_xbrl_value_reveal_authority_receipt_id",
    )
    _reject_raw_or_local_authority(receipt_id)
    basis_hash = _required_hash(authority_basis_hash, "authority_basis_hash")

    authority = _load_authority_receipt(db, receipt_id, basis_hash)
    _validate_authority_receipt(authority)
    decision_status = _decision_status(db, authority)
    workflow = authority.operator_review_decision.operator_review_workflow
    packet_set = workflow.statement_packet_set if workflow is not None else None
    projection_set = packet_set.projection_set if packet_set is not None else None
    if workflow is None or packet_set is None or projection_set is None:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_lineage_missing",
            "SEC XBRL controlled value reveal requires complete authority lineage.",
        )
    try:
        layer3_sec_xbrl_value_reveal_authority._validate_approved_decision(authority.operator_review_decision)
        layer3_sec_xbrl_value_reveal_authority._validate_packet_and_projection(
            workflow=workflow,
            packet_set=packet_set,
            projection_set=projection_set,
        )
    except layer3_sec_xbrl_value_reveal_authority.SecXbrlValueRevealAuthorityError as exc:
        raise SecXbrlControlledValueRevealSubmitError(
            exc.code.replace("sec_xbrl_value_reveal_authority", "sec_xbrl_controlled_value_reveal_submit"),
            exc.message,
            details=exc.details,
            http_status=exc.http_status,
        ) from exc

    sidecar, value_store = _resolve_sidecar_and_value_store(authority)
    reveal_records = _controlled_reveal_records(
        sidecar,
        value_store,
        dataset_version_hash=authority.dataset_version_hash,
    )
    if not reveal_records:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_no_resolved_values",
            "SEC XBRL controlled value reveal found no sidecar-bound values to reveal.",
        )
    page = _page_reveal_records(
        authority=authority,
        reveal_records=reveal_records,
        page_size=cap,
        page_cursor=page_cursor,
    )
    receipt_basis = _receipt_basis(authority=authority, reveal_records=page["reveal_records"], page=page)
    submit_basis_hash = stable_hash(receipt_basis)
    existing = _existing_receipt(db, request_id, submit_basis_hash)
    if existing is not None:
        _validate_existing_receipt(existing, submit_basis_hash, receipt_basis)
        return _submit_response(existing, reveal_records=page["reveal_records"], idempotent_replay=True)

    submit_receipt = _new_receipt(
        request_id=request_id,
        submit_basis_hash=submit_basis_hash,
        authority=authority,
        receipt_basis=receipt_basis,
        decision_status=decision_status,
    )
    try:
        db.add(submit_receipt)
        if commit:
            db.commit()
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_integrity_error",
            "SEC XBRL controlled value reveal receipt persistence failed without admitting a partial receipt.",
        ) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(submit_receipt)
    return _submit_response(submit_receipt, reveal_records=page["reveal_records"], idempotent_replay=False)


def inspect_controlled_value_reveal_submit_status(
    db: Session,
    *,
    sec_xbrl_controlled_value_reveal_submit_receipt_id: str,
) -> dict[str, Any]:
    if not settings.layer3_sec_xbrl_controlled_value_reveal_submit_enabled:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled",
            "SEC XBRL controlled value-reveal submit status is feature-flagged and currently disabled.",
        )
    receipt_id = _required_text(
        sec_xbrl_controlled_value_reveal_submit_receipt_id,
        "sec_xbrl_controlled_value_reveal_submit_receipt_id",
    )
    _reject_raw_or_local_authority(receipt_id)
    row = db.get(L3SecXbrlControlledValueRevealSubmitReceipt, receipt_id)
    if row is None:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_receipt_missing",
            "SEC XBRL controlled value reveal submit receipt was not found.",
            http_status=404,
        )
    return _status_response(row)


def _load_authority_receipt(
    db: Session,
    receipt_id: str,
    authority_basis_hash: str,
) -> L3SecXbrlValueRevealAuthorityReceipt:
    row = (
        db.query(L3SecXbrlValueRevealAuthorityReceipt)
        .filter(
            L3SecXbrlValueRevealAuthorityReceipt.sec_xbrl_value_reveal_authority_receipt_id == receipt_id,
            L3SecXbrlValueRevealAuthorityReceipt.authority_basis_hash == authority_basis_hash,
        )
        .one_or_none()
    )
    if row is None:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_authority_missing",
            "SEC XBRL controlled value reveal requires an existing matching authority receipt.",
            details={
                "sec_xbrl_value_reveal_authority_receipt_id": receipt_id,
                "authority_basis_hash": authority_basis_hash,
            },
            http_status=404,
        )
    return row


def _validate_authority_receipt(row: L3SecXbrlValueRevealAuthorityReceipt) -> None:
    expected = {
        "authority_state": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
        "authority_policy_id": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
        "redaction_policy": L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
    }
    actual = {
        "authority_state": row.authority_state,
        "authority_policy_id": row.authority_policy_id,
        "redaction_policy": row.redaction_policy,
    }
    mismatches = sorted(key for key, value in expected.items() if actual[key] != value)
    if mismatches:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_authority_policy_invalid",
            "SEC XBRL controlled value reveal requires a ready authority receipt with the governed policy.",
            details={"blocked_keys": mismatches},
        )


def _decision_status(db: Session, row: L3SecXbrlValueRevealAuthorityReceipt) -> Mapping[str, Any]:
    try:
        status = layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_decision_status(
            db,
            client_request_id=f"sec-xbrl-controlled-value-reveal-{stable_hash(row.authority_basis_hash)[:16]}",
            sec_xbrl_operator_review_decision_id=row.sec_xbrl_operator_review_decision_id,
            decision_basis_hash=row.decision_basis_hash,
        )
    except layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError as exc:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_decision_status_invalid",
            "SEC XBRL controlled value reveal requires a clean operator-review decision status projection.",
            details={"decision_status_error_code": exc.code},
            http_status=exc.http_status,
        ) from exc
    if status.get("review_decision") != "approved" or status.get("decision_reason_code") != "ready_for_next_freeze":
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_decision_not_ready",
            "SEC XBRL controlled value reveal requires an approved ready-for-next-freeze decision.",
            details={
                "review_decision": status.get("review_decision"),
                "decision_reason_code": status.get("decision_reason_code"),
            },
            http_status=400,
        )
    return status


def _resolve_sidecar_and_value_store(
    row: L3SecXbrlValueRevealAuthorityReceipt,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    receipt_id = f"{layer3_sec_xbrl_sidecar.RECEIPT_PREFIX}-{row.sidecar_receipt_hash[:24]}"
    try:
        sidecar = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
            receipt_id,
            expected_sidecar_receipt_hash=row.sidecar_receipt_hash,
        )
        value_store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(
            sidecar
        )
    except Layer3WorkbenchError as exc:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_value_store_missing",
            "SEC XBRL controlled value reveal requires existing server-owned sidecar and value-store authority.",
            details={"sidecar_error_code": exc.error_code, "blocked_keys": list(exc.blocked_fields)},
            http_status=exc.http_status,
        ) from exc
    if sidecar.get("sidecar_state") != layer3_sec_xbrl_sidecar.READY_STATE:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_sidecar_not_ready",
            "SEC XBRL controlled value reveal requires a READY sidecar receipt.",
        )
    if sidecar.get("sidecar_receipt_hash") != row.sidecar_receipt_hash:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_sidecar_hash_mismatch",
            "SEC XBRL controlled value reveal sidecar hash does not match authority.",
        )
    if value_store.get("value_store_hash") != row.value_store_hash:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_value_store_hash_mismatch",
            "SEC XBRL controlled value reveal value-store hash does not match authority.",
        )
    sidecar_id_hash = stable_hash(
        {
            "hash_version": "sec_xbrl_value_reveal_authority_sidecar_receipt_id_hash_v1",
            "sidecar_receipt_id": _required_text(sidecar.get("sidecar_receipt_id"), "sidecar_receipt_id"),
        }
    )
    if sidecar_id_hash != row.sidecar_receipt_id_hash:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_sidecar_receipt_id_hash_mismatch",
            "SEC XBRL controlled value reveal sidecar receipt id hash does not match authority.",
        )
    return sidecar, value_store


def _controlled_reveal_records(
    sidecar: Mapping[str, Any],
    value_store: Mapping[str, Any],
    *,
    dataset_version_hash: str,
) -> list[dict[str, Any]]:
    raw_records = layer3_sec_edgar_arelle_value_reveal._reveal_records(
        sidecar,
        value_store,
        dataset_version_hash=dataset_version_hash,
    )
    records: list[dict[str, Any]] = []
    for record in raw_records:
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        transform = record.get("transform_inputs") if isinstance(record.get("transform_inputs"), Mapping) else {}
        effective_value = str(record.get("effective_value") or "")
        lexical_value = str(record.get("lexical_value") or "")
        value_redacted = bool(record.get("value_redacted")) or _value_text_requires_redaction(
            effective_value,
            lexical_value,
        )
        records.append(
            {
                "fact_identity_hash": str(record.get("fact_identity_hash") or ""),
                "resolved_fact_id_hash": str(record.get("resolved_fact_id_hash") or ""),
                "source_order": int(record.get("source_order") or 0),
                "entry_document_index": int(record.get("entry_document_index") or 0),
                "effective_value": "" if value_redacted else effective_value,
                "lexical_value": "" if value_redacted else lexical_value,
                "value_redacted": value_redacted,
                "value_redaction_reason": (
                    "sec_xbrl_controlled_value_reveal_identity_or_raw_reference_redacted"
                    if value_redacted
                    else None
                ),
                "value_hash": str(record.get("value_hash") or ""),
                "value_semantics": str(
                    record.get("value_semantics")
                    or layer3_sec_edgar_arelle_value_reveal.VALUE_SEMANTICS_ID
                ),
                "concept": {
                    "qname": str(concept.get("qname") or ""),
                    "local_name": str(concept.get("local_name") or ""),
                    "standard": bool(concept.get("standard")),
                    "extension": bool(concept.get("extension")),
                },
                "transform_inputs": {
                    "sign": str(transform.get("sign") or ""),
                    "scale": str(transform.get("scale") or ""),
                    "decimals": str(transform.get("decimals") or ""),
                    "precision": str(transform.get("precision") or ""),
                    "format": str(transform.get("format") or ""),
                },
                "hidden": bool(record.get("hidden")),
                "continued": bool(record.get("continued")),
            }
        )
    records = sorted(records, key=_controlled_reveal_sort_key)
    if _response_has_forbidden_reference(records):
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_response_redaction_violation",
            "SEC XBRL controlled value reveal response failed redaction/reference checks.",
        )
    return records


def _controlled_reveal_sort_key(record: Mapping[str, Any]) -> tuple[int, int, str, str, str, str]:
    return (
        int(record.get("source_order") or 0),
        int(record.get("entry_document_index") or 0),
        str((record.get("concept") or {}).get("qname") or ""),
        str(record.get("fact_identity_hash") or ""),
        str(record.get("resolved_fact_id_hash") or ""),
        str(record.get("value_hash") or ""),
    )


def _page_reveal_records(
    *,
    authority: L3SecXbrlValueRevealAuthorityReceipt,
    reveal_records: list[dict[str, Any]],
    page_size: int,
    page_cursor: str | None,
) -> dict[str, Any]:
    total_record_count = len(reveal_records)
    result_set_identity_hash = _result_set_identity_hash(authority=authority, reveal_records=reveal_records)
    if page_cursor is None:
        page_offset = 0
    else:
        page_offset = _decode_page_cursor(
            page_cursor,
            authority=authority,
            result_set_identity_hash=result_set_identity_hash,
            page_size=page_size,
            total_record_count=total_record_count,
        )
    if page_offset >= total_record_count:
        _raise_invalid_page_cursor("page cursor offset exceeds current result set")
    page_records = reveal_records[page_offset : page_offset + page_size]
    page_record_count = len(page_records)
    next_offset = page_offset + page_record_count
    binding_hash = _page_cursor_binding_hash(
        authority=authority,
        result_set_identity_hash=result_set_identity_hash,
        page_size=page_size,
    )
    next_page_cursor = (
        _encode_page_cursor(
            offset=next_offset,
            result_set_identity_hash=result_set_identity_hash,
            page_size=page_size,
            binding_hash=binding_hash,
        )
        if next_offset < total_record_count
        else None
    )
    return {
        "reveal_records": page_records,
        "total_record_count": total_record_count,
        "page_record_count": page_record_count,
        "page_index": (page_offset // page_size) + 1,
        "page_offset": page_offset,
        "page_size": page_size,
        "result_set_identity_hash": result_set_identity_hash,
        "page_cursor_binding_hash": binding_hash,
        "next_page_cursor": next_page_cursor,
    }


def _result_set_identity_hash(
    *,
    authority: L3SecXbrlValueRevealAuthorityReceipt,
    reveal_records: list[dict[str, Any]],
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.sec_xbrl_controlled_value_reveal_submit_result_set_identity.v1",
            "sec_xbrl_value_reveal_authority_receipt_id": (
                authority.sec_xbrl_value_reveal_authority_receipt_id
            ),
            "authority_basis_hash": authority.authority_basis_hash,
            "dataset_version_hash": authority.dataset_version_hash,
            "sidecar_receipt_hash": authority.sidecar_receipt_hash,
            "value_store_hash": authority.value_store_hash,
            "record_count": len(reveal_records),
            "record_identities": [
                {
                    "source_order": int(record.get("source_order") or 0),
                    "entry_document_index": int(record.get("entry_document_index") or 0),
                    "fact_identity_hash": str(record.get("fact_identity_hash") or ""),
                    "resolved_fact_id_hash": str(record.get("resolved_fact_id_hash") or ""),
                    "value_hash": str(record.get("value_hash") or ""),
                    "value_redacted": bool(record.get("value_redacted")),
                }
                for record in reveal_records
            ],
        }
    )


def _page_cursor_binding_hash(
    *,
    authority: L3SecXbrlValueRevealAuthorityReceipt,
    result_set_identity_hash: str,
    page_size: int,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.sec_xbrl_controlled_value_reveal_submit_page_cursor_binding.v1",
            "sec_xbrl_value_reveal_authority_receipt_id": (
                authority.sec_xbrl_value_reveal_authority_receipt_id
            ),
            "authority_basis_hash": authority.authority_basis_hash,
            "result_set_identity_hash": result_set_identity_hash,
            "page_size": page_size,
        }
    )


def _encode_page_cursor(
    *,
    offset: int,
    result_set_identity_hash: str,
    page_size: int,
    binding_hash: str,
) -> str:
    payload: dict[str, Any] = {
        "schema_id": PAGE_CURSOR_SCHEMA_ID,
        "version": PAGE_CURSOR_VERSION,
        "offset": offset,
        "page_size": page_size,
        "result_set_identity_hash": result_set_identity_hash,
        "binding_hash": binding_hash,
    }
    payload["cursor_hash"] = stable_hash(payload)
    payload["cursor_signature"] = _page_cursor_signature(payload)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_page_cursor(
    page_cursor: str,
    *,
    authority: L3SecXbrlValueRevealAuthorityReceipt,
    result_set_identity_hash: str,
    page_size: int,
    total_record_count: int,
) -> int:
    token = _required_text(page_cursor, "page_cursor")
    if len(token) > 4096:
        _raise_invalid_page_cursor("page cursor is too long")
    try:
        raw = base64.urlsafe_b64decode(token + ("=" * (-len(token) % 4)))
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        _raise_invalid_page_cursor("page cursor is not decodable")
    if not isinstance(payload, Mapping):
        _raise_invalid_page_cursor("page cursor payload is invalid")
    cursor_hash = payload.get("cursor_hash")
    unsigned_payload = dict(payload)
    unsigned_payload.pop("cursor_hash", None)
    unsigned_payload.pop("cursor_signature", None)
    if cursor_hash != stable_hash(unsigned_payload):
        _raise_invalid_page_cursor("page cursor payload hash mismatch")
    signed_payload = dict(unsigned_payload)
    signed_payload["cursor_hash"] = cursor_hash
    cursor_signature = str(payload.get("cursor_signature") or "")
    if not hmac.compare_digest(cursor_signature, _page_cursor_signature(signed_payload)):
        _raise_invalid_page_cursor("page cursor signature mismatch")
    if payload.get("schema_id") != PAGE_CURSOR_SCHEMA_ID or payload.get("version") != PAGE_CURSOR_VERSION:
        _raise_invalid_page_cursor("page cursor schema is invalid")
    expected_binding_hash = _page_cursor_binding_hash(
        authority=authority,
        result_set_identity_hash=result_set_identity_hash,
        page_size=page_size,
    )
    try:
        cursor_page_size = int(payload.get("page_size"))
    except (TypeError, ValueError):
        _raise_invalid_page_cursor("page cursor page size is invalid")
    if (
        payload.get("binding_hash") != expected_binding_hash
        or payload.get("result_set_identity_hash") != result_set_identity_hash
        or cursor_page_size != page_size
    ):
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_page_cursor_authority_mismatch",
            "SEC XBRL controlled value reveal page cursor does not match the current authority, result set, or page size.",
            details={"blocked_keys": ["page_cursor"]},
            http_status=400,
        )
    try:
        offset = int(payload.get("offset"))
    except (TypeError, ValueError):
        _raise_invalid_page_cursor("page cursor offset is invalid")
    if offset < 0 or offset >= total_record_count or offset % page_size != 0:
        _raise_invalid_page_cursor("page cursor offset is outside the current result set")
    return offset


def _raise_invalid_page_cursor(reason: str) -> None:
    raise SecXbrlControlledValueRevealSubmitError(
        "sec_xbrl_controlled_value_reveal_submit_page_cursor_invalid",
        "SEC XBRL controlled value reveal page cursor is invalid or tampered.",
        details={"blocked_keys": ["page_cursor"], "reason": reason},
        http_status=400,
    )


def _page_cursor_signature(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(_page_cursor_signing_key(), raw, hashlib.sha256).hexdigest()


def _page_cursor_signing_key() -> bytes:
    configured_secret = (
        os.environ.get(PAGE_CURSOR_SIGNATURE_SECRET_ENV_VAR, "").strip().encode("utf-8")
    )
    if configured_secret:
        return hashlib.sha256(configured_secret).digest()
    return PAGE_CURSOR_PROCESS_SECRET


def _value_text_requires_redaction(*values: str) -> bool:
    text = " ".join(str(value or "") for value in values)
    return (
        raw_or_local_authority_violation(
            text,
            raw_value_keys=frozenset(),
            raw_authority_keys=frozenset(),
            scan_contextual_cik=True,
            scan_operator_contact=True,
        )
        is not None
    )


def _response_has_forbidden_reference(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in RAW_REQUEST_KEYS:
                return True
            if _response_has_forbidden_reference(child):
                return True
        return False
    if isinstance(value, list):
        return any(_response_has_forbidden_reference(item) for item in value)
    if isinstance(value, str):
        return _value_text_requires_redaction(value)
    return False


def _receipt_basis(
    *,
    authority: L3SecXbrlValueRevealAuthorityReceipt,
    reveal_records: list[dict[str, Any]],
    page: Mapping[str, Any],
) -> dict[str, Any]:
    fact_identity_hashes = [str(record["fact_identity_hash"]) for record in reveal_records]
    value_hashes = [str(record.get("value_hash") or "") for record in reveal_records]
    response_inventory = [
        {
            "fact_identity_hash": record["fact_identity_hash"],
            "resolved_fact_id_hash": record["resolved_fact_id_hash"],
            "value_hash": record.get("value_hash"),
            "value_redacted": bool(record.get("value_redacted")),
        }
        for record in reveal_records
    ]
    return {
        "schema_id": SUBMIT_SCHEMA_ID,
        "submit_mode": SUBMIT_MODE,
        "sec_xbrl_value_reveal_authority_receipt_id": (
            authority.sec_xbrl_value_reveal_authority_receipt_id
        ),
        "authority_basis_hash": authority.authority_basis_hash,
        "authority_policy_id": authority.authority_policy_id,
        "sec_xbrl_operator_review_decision_id": authority.sec_xbrl_operator_review_decision_id,
        "decision_basis_hash": authority.decision_basis_hash,
        "sec_xbrl_operator_review_workflow_id": authority.sec_xbrl_operator_review_workflow_id,
        "workflow_basis_hash": authority.workflow_basis_hash,
        "sec_xbrl_statement_packet_set_id": authority.sec_xbrl_statement_packet_set_id,
        "statement_packet_basis_hash": authority.statement_packet_basis_hash,
        "sec_xbrl_projection_set_id": authority.sec_xbrl_projection_set_id,
        "projection_basis_hash": authority.projection_basis_hash,
        "dataset_version_id": authority.dataset_version_id,
        "dataset_version_hash": authority.dataset_version_hash,
        "sidecar_receipt_id_hash": authority.sidecar_receipt_id_hash,
        "sidecar_receipt_hash": authority.sidecar_receipt_hash,
        "value_store_hash": authority.value_store_hash,
        "submit_state": L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
        "submit_policy_id": L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_POLICY_ID,
        "redaction_policy": L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_REDACTION_POLICY,
        "revealed_fact_count": len(reveal_records),
        "value_redacted_fact_count": sum(1 for record in reveal_records if record.get("value_redacted") is True),
        "total_record_count": int(page["total_record_count"]),
        "page_record_count": int(page["page_record_count"]),
        "page_index": int(page["page_index"]),
        "page_offset": int(page["page_offset"]),
        "page_size": int(page["page_size"]),
        "result_set_identity_hash": str(page["result_set_identity_hash"]),
        "page_cursor_binding_hash": str(page["page_cursor_binding_hash"]),
        "next_page_cursor": page.get("next_page_cursor"),
        "fact_inventory_hash": stable_hash(fact_identity_hashes),
        "value_inventory_hash": stable_hash(value_hashes),
        "response_inventory_hash": stable_hash(response_inventory),
    }


def _existing_receipt(
    db: Session,
    request_id: str,
    submit_basis_hash: str,
) -> L3SecXbrlControlledValueRevealSubmitReceipt | None:
    request_id_hash = _sha256_text(request_id)
    existing_by_request = (
        db.query(L3SecXbrlControlledValueRevealSubmitReceipt)
        .filter(L3SecXbrlControlledValueRevealSubmitReceipt.client_request_id_hash == request_id_hash)
        .one_or_none()
    )
    existing_by_basis = (
        db.query(L3SecXbrlControlledValueRevealSubmitReceipt)
        .filter(L3SecXbrlControlledValueRevealSubmitReceipt.submit_basis_hash == submit_basis_hash)
        .one_or_none()
    )
    if existing_by_request is not None and existing_by_request.submit_basis_hash != submit_basis_hash:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_client_request_conflict",
            "client_request_id already submitted a different SEC XBRL controlled value-reveal basis.",
            details={"client_request_id_hash": request_id_hash},
        )
    return existing_by_request or existing_by_basis


def _validate_existing_receipt(
    row: L3SecXbrlControlledValueRevealSubmitReceipt,
    submit_basis_hash: str,
    receipt_basis: Mapping[str, Any],
) -> None:
    if row.submit_basis_hash != submit_basis_hash:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_basis_conflict",
            "SEC XBRL controlled value reveal submit receipt conflicts with current authority.",
        )
    if row.response_inventory_hash != receipt_basis["response_inventory_hash"]:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_inventory_conflict",
            "SEC XBRL controlled value reveal inventory no longer matches the persisted submit receipt.",
        )


def _new_receipt(
    *,
    request_id: str,
    submit_basis_hash: str,
    authority: L3SecXbrlValueRevealAuthorityReceipt,
    receipt_basis: Mapping[str, Any],
    decision_status: Mapping[str, Any],
) -> L3SecXbrlControlledValueRevealSubmitReceipt:
    summary = {
        "submit_mode": SUBMIT_MODE,
        "operator_decision": SUBMIT_OPERATOR_DECISION,
        "authority_receipt_bound": True,
        "authority_policy_id": authority.authority_policy_id,
        "authority_redaction_policy": authority.redaction_policy,
        "decision_status": decision_status.get("decision_status"),
        "decision_approved": decision_status.get("review_decision") == "approved",
        "decision_reason_ready": decision_status.get("decision_reason_code") == "ready_for_next_freeze",
        "revealed_fact_count": receipt_basis["revealed_fact_count"],
        "value_redacted_fact_count": receipt_basis["value_redacted_fact_count"],
        "total_record_count": receipt_basis["total_record_count"],
        "page_record_count": receipt_basis["page_record_count"],
        "page_index": receipt_basis["page_index"],
        "page_offset": receipt_basis["page_offset"],
        "page_size": receipt_basis["page_size"],
        "result_set_identity_hash": receipt_basis["result_set_identity_hash"],
        "page_cursor_binding_hash": receipt_basis["page_cursor_binding_hash"],
        "next_page_cursor": receipt_basis["next_page_cursor"],
        "transient_values_returned": True,
        "audit_receipt_raw_values_persisted": False,
        "raw_sidecar_receipt_id_persisted": False,
        "status_surface_hash_count_only": True,
    }
    request_id_hash = _sha256_text(request_id)
    return L3SecXbrlControlledValueRevealSubmitReceipt(
        client_request_id=_redacted_client_request_id_surrogate(request_id_hash),
        client_request_id_hash=request_id_hash,
        submit_basis_hash=submit_basis_hash,
        submit_schema_id=SUBMIT_SCHEMA_ID,
        sec_xbrl_value_reveal_authority_receipt_id=authority.sec_xbrl_value_reveal_authority_receipt_id,
        authority_basis_hash=authority.authority_basis_hash,
        sec_xbrl_operator_review_decision_id=authority.sec_xbrl_operator_review_decision_id,
        decision_basis_hash=authority.decision_basis_hash,
        sec_xbrl_operator_review_workflow_id=authority.sec_xbrl_operator_review_workflow_id,
        workflow_basis_hash=authority.workflow_basis_hash,
        sec_xbrl_statement_packet_set_id=authority.sec_xbrl_statement_packet_set_id,
        statement_packet_basis_hash=authority.statement_packet_basis_hash,
        sec_xbrl_projection_set_id=authority.sec_xbrl_projection_set_id,
        projection_basis_hash=authority.projection_basis_hash,
        dataset_version_id=authority.dataset_version_id,
        dataset_version_hash=authority.dataset_version_hash,
        sidecar_receipt_id_hash=authority.sidecar_receipt_id_hash,
        sidecar_receipt_hash=authority.sidecar_receipt_hash,
        value_store_hash=authority.value_store_hash,
        submit_state=L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
        submit_policy_id=L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_POLICY_ID,
        redaction_policy=L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_REDACTION_POLICY,
        revealed_fact_count=int(receipt_basis["revealed_fact_count"]),
        value_redacted_fact_count=int(receipt_basis["value_redacted_fact_count"]),
        fact_inventory_hash=str(receipt_basis["fact_inventory_hash"]),
        value_inventory_hash=str(receipt_basis["value_inventory_hash"]),
        response_inventory_hash=str(receipt_basis["response_inventory_hash"]),
        submit_summary_json=json_clone(summary),
        negative_invariants_json=_negative_invariants(),
    )


def _submit_response(
    row: L3SecXbrlControlledValueRevealSubmitReceipt,
    *,
    reveal_records: list[dict[str, Any]],
    idempotent_replay: bool,
) -> dict[str, Any]:
    return {
        **_receipt_projection(row, include_status_schema=False),
        "revealed_fact_count": len(reveal_records),
        "revealed_facts": json_clone(reveal_records),
        "transient_values_returned": True,
        "idempotent_replay": idempotent_replay,
        "next_allowed_actions": ["inspect_sec_xbrl_controlled_value_reveal_submit_status"],
    }


def _status_response(row: L3SecXbrlControlledValueRevealSubmitReceipt) -> dict[str, Any]:
    return {
        "status": row.submit_state,
        "schema_id": STATUS_SCHEMA_ID,
        "submit_mode": SUBMIT_MODE,
        "submit_state": row.submit_state,
        "sec_xbrl_controlled_value_reveal_submit_receipt_id": (
            row.sec_xbrl_controlled_value_reveal_submit_receipt_id
        ),
        "value_reveal_submit_receipt_ref": f"{SUBMIT_RECEIPT_REF_PREFIX}:{row.submit_basis_hash[:24]}",
        "client_request_id_hash": row.client_request_id_hash,
        "submit_basis_hash": row.submit_basis_hash,
        "sec_xbrl_value_reveal_authority_receipt_id": row.sec_xbrl_value_reveal_authority_receipt_id,
        "authority_basis_hash": row.authority_basis_hash,
        "submit_policy_id": row.submit_policy_id,
        "redaction_policy": row.redaction_policy,
        "revealed_fact_count": int(row.revealed_fact_count),
        **_receipt_page_projection(row),
        "revealed_facts": [],
        "value_redacted_fact_count": int(row.value_redacted_fact_count),
        "fact_inventory_hash": row.fact_inventory_hash,
        "value_inventory_hash": row.value_inventory_hash,
        "response_inventory_hash": row.response_inventory_hash,
        "submit_summary": json_clone(row.submit_summary_json),
        "negative_invariants": json_clone(row.negative_invariants_json),
        "status_surface_hash_count_only": True,
        "audit_receipt_raw_values_persisted": False,
        "raw_sidecar_receipt_id_persisted": False,
        "runtime_default_enabled": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "rendered_ui_enabled": False,
        "production_readiness_claimed": False,
        "transient_values_returned": False,
        "idempotent_replay": True,
        "next_allowed_actions": [],
    }


def _receipt_projection(
    row: L3SecXbrlControlledValueRevealSubmitReceipt,
    *,
    include_status_schema: bool,
) -> dict[str, Any]:
    schema_id = STATUS_SCHEMA_ID if include_status_schema else row.submit_schema_id
    return {
        "status": row.submit_state,
        "schema_id": schema_id,
        "submit_mode": SUBMIT_MODE,
        "submit_state": row.submit_state,
        "sec_xbrl_controlled_value_reveal_submit_receipt_id": (
            row.sec_xbrl_controlled_value_reveal_submit_receipt_id
        ),
        "value_reveal_submit_receipt_ref": f"{SUBMIT_RECEIPT_REF_PREFIX}:{row.submit_basis_hash[:24]}",
        "client_request_id_hash": row.client_request_id_hash,
        "submit_basis_hash": row.submit_basis_hash,
        "sec_xbrl_value_reveal_authority_receipt_id": row.sec_xbrl_value_reveal_authority_receipt_id,
        "authority_basis_hash": row.authority_basis_hash,
        "submit_policy_id": row.submit_policy_id,
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
        **_receipt_page_projection(row),
        "value_redacted_fact_count": int(row.value_redacted_fact_count),
        "fact_inventory_hash": row.fact_inventory_hash,
        "value_inventory_hash": row.value_inventory_hash,
        "response_inventory_hash": row.response_inventory_hash,
        "submit_summary": json_clone(row.submit_summary_json),
        "negative_invariants": json_clone(row.negative_invariants_json),
        "status_surface_hash_count_only": True,
        "audit_receipt_raw_values_persisted": False,
        "raw_sidecar_receipt_id_persisted": False,
        "runtime_default_enabled": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "rendered_ui_enabled": False,
        "production_readiness_claimed": False,
    }


def _receipt_page_projection(row: L3SecXbrlControlledValueRevealSubmitReceipt) -> dict[str, Any]:
    summary = row.submit_summary_json if isinstance(row.submit_summary_json, Mapping) else {}
    next_page_cursor = summary.get("next_page_cursor")
    if next_page_cursor is not None and not isinstance(next_page_cursor, str):
        next_page_cursor = None
    return {
        "next_page_cursor": next_page_cursor,
        "total_record_count": _summary_int(summary, "total_record_count", int(row.revealed_fact_count)),
        "page_record_count": _summary_int(summary, "page_record_count", int(row.revealed_fact_count)),
        "page_index": _summary_int(summary, "page_index", 1),
    }


def _summary_int(summary: Mapping[str, Any], key: str, default: int) -> int:
    try:
        return int(summary.get(key))
    except (TypeError, ValueError):
        return default


def _negative_invariants() -> dict[str, bool]:
    return {
        "raw_values_persisted": False,
        "raw_identity_persisted": False,
        "raw_sidecar_receipt_id_persisted": False,
        "raw_accessions_persisted": False,
        "raw_period_dates_persisted": False,
        "local_paths_persisted": False,
        "operator_contact_persisted": False,
        "status_surface_replays_raw_values": False,
        "runtime_default_changed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "rendered_ui_enabled": False,
        "production_readiness_claimed": False,
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _redacted_client_request_id_surrogate(client_request_id_hash: str) -> str:
    return f"redacted-client-request-id:{client_request_id_hash}"


def _max_records(value: int | None) -> int:
    if value is None:
        return MAX_REVEAL_RECORDS
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_max_records_invalid",
            "SEC XBRL controlled value reveal requires max_records to be a positive integer.",
            details={"blocked_keys": ["max_records"]},
            http_status=400,
        ) from exc
    if parsed < 1 or parsed > MAX_REVEAL_RECORDS:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_max_records_not_admitted",
            "SEC XBRL controlled value reveal max_records exceeds the server-owned cap.",
            details={"blocked_keys": ["max_records"], "max_records_cap": MAX_REVEAL_RECORDS},
            http_status=400,
        )
    return parsed


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_required_field_missing",
            f"SEC XBRL controlled value reveal requires {field}.",
            details={"blocked_keys": [field]},
            http_status=400,
        )
    return text


def _required_hash(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not HASH_RE.fullmatch(text):
        raise SecXbrlControlledValueRevealSubmitError(
            "sec_xbrl_controlled_value_reveal_submit_hash_invalid",
            f"SEC XBRL controlled value reveal requires a 64-character lowercase hex {field}.",
            details={"blocked_keys": [field]},
            http_status=400,
        )
    return text


def _reject_raw_or_local_authority(value: Any) -> None:
    reject_value_reveal_raw_or_local_authority(
        value,
        error_type=SecXbrlControlledValueRevealSubmitError,
        raw_authority_code="sec_xbrl_controlled_value_reveal_submit_raw_authority_not_admitted",
        raw_authority_message="SEC XBRL controlled value reveal only admits authority-receipt fields from the browser.",
        raw_reference_code="sec_xbrl_controlled_value_reveal_submit_raw_reference_not_admitted",
        raw_reference_message="SEC XBRL controlled value reveal rejects raw identities, paths, SEC URLs, accessions, and period dates.",
        blocked_raw_value_keys=frozenset(),
        blocked_raw_authority_keys=RAW_REQUEST_KEYS,
    )
