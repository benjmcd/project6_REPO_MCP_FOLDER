from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services import layer3_sec_edgar_html_inline_xbrl_downstream_proof
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_downstream_operator_status.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_downstream_operator_status_request.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "sec_edgar_html_inline_xbrl_downstream_operator_status_v1"
OPERATOR_DECISION = "inspect_sec_edgar_html_inline_xbrl_downstream_operator_status"
STATUS_PROJECTION_PREFIX = "sec-edgar-html-inline-xbrl-downstream-operator-status"
STATUS_STATES = ("not_recorded", "available", "blocked")

FORBIDDEN_REQUEST_FIELDS = {
    "args",
    "path",
    "paths",
    "directory",
    "file_path",
    "local_directory",
    "local_path",
    "raw_path",
    "url",
    "urls",
    "raw_url",
    "source_url",
    "filing_url",
    "provider_url",
    "connector_url",
    "command",
    "file",
    "files",
    "file_bytes",
    "provider_credentials",
    "connector_credentials",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
    "frontend_authority",
    "full_mockup_activation",
    "source_upload",
    "source_expansion",
    "parser_expansion",
    "runtime_db_write",
    "storage_dir",
    "stdout",
    "stderr",
}
ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "status_mode",
    "operator_decision",
    "html_inline_xbrl_downstream_proof_request",
    "expected_proof_hash",
    "actor",
}
STATUS_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "operator_status_state",
    "expected_proof_hash",
    "proof_hash",
    "proof_state",
    "dataset_version_id",
    "dataset_version_hash",
    "source_family",
    "parser_family",
    "typed_content_contract_id",
    "parser_receipt_hash",
    "connector_receipt_hash",
    "live_source_artifact_receipt_hash",
    "source_artifact_receipt_hash",
    "content_sha256",
    "primary_document_hash",
    "content_order_hash",
    "materialization_receipt_hash",
    "material_bridge_receipt_hash",
    "material_preview_hash",
    "gate_b_decision_manifest_id",
    "session_id",
    "selection_manifest_id",
    "material_snapshot_payload_hash",
    "coverage_evidence_hash",
    "negative_invariants_hash",
    "blocked_reason_codes",
)

_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def inspect_sec_edgar_html_inline_xbrl_downstream_operator_status(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "status_mode", STATUS_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)

    proof_request = request.get("html_inline_xbrl_downstream_proof_request")
    expected_proof_hash = str(request.get("expected_proof_hash") or "").strip()
    if proof_request is None:
        if expected_proof_hash:
            return _blocked_status(
                request_id=request_id,
                code="sec_edgar_html_inline_xbrl_downstream_operator_status_ambiguous_proof_authority",
                message="Expected proof hash was supplied without HTML/iXBRL downstream proof authority to revalidate.",
                expected_proof_hash=expected_proof_hash,
                blocked_fields=["html_inline_xbrl_downstream_proof_request", "expected_proof_hash"],
            )
        return _not_recorded_status(request_id=request_id)

    if not isinstance(proof_request, Mapping):
        return _blocked_status(
            request_id=request_id,
            code="sec_edgar_html_inline_xbrl_downstream_operator_status_proof_request_invalid",
            message="HTML/iXBRL downstream proof authority must be supplied as a structured proof request.",
            blocked_fields=["html_inline_xbrl_downstream_proof_request"],
        )
    if not expected_proof_hash:
        return _blocked_status(
            request_id=request_id,
            code="sec_edgar_html_inline_xbrl_downstream_operator_status_expected_proof_hash_missing",
            message="Expected proof hash is required when HTML/iXBRL downstream proof authority is supplied.",
            blocked_fields=["expected_proof_hash"],
        )
    if not _is_sha256(expected_proof_hash):
        return _blocked_status(
            request_id=request_id,
            code="sec_edgar_html_inline_xbrl_downstream_operator_status_expected_proof_hash_invalid",
            message="Expected proof hash must be a SHA-256 hex string.",
            expected_proof_hash=expected_proof_hash,
            blocked_fields=["expected_proof_hash"],
        )

    try:
        proof = (
            layer3_sec_edgar_html_inline_xbrl_downstream_proof.record_sec_edgar_html_inline_xbrl_downstream_layer3_proof(
                dict(proof_request),
                db,
            )
        )
    except Layer3WorkbenchError as exc:
        return _blocked_status(
            request_id=request_id,
            code=exc.error_code,
            message=exc.message,
            expected_proof_hash=expected_proof_hash,
            blocked_fields=list(exc.blocked_fields),
            next_allowed_actions=list(exc.next_allowed_actions),
        )

    if str(proof.get("proof_hash") or "") != expected_proof_hash:
        return _blocked_status(
            request_id=request_id,
            code="sec_edgar_html_inline_xbrl_downstream_operator_status_proof_hash_mismatch",
            message="Revalidated HTML/iXBRL downstream proof hash does not match the expected proof hash.",
            expected_proof_hash=expected_proof_hash,
            proof=proof,
            blocked_fields=["expected_proof_hash", "html_inline_xbrl_downstream_proof_request"],
            next_allowed_actions=["refresh_sec_edgar_html_inline_xbrl_downstream_proof"],
        )
    response = _available_status(
        request_id=request_id,
        expected_proof_hash=expected_proof_hash,
        proof=proof,
    )
    if _contains_forbidden_output_ref(response):
        return _blocked_status(
            request_id=request_id,
            code="sec_edgar_html_inline_xbrl_downstream_operator_status_raw_authority_exposed",
            message="SEC EDGAR HTML/iXBRL downstream status projection would expose raw path, URL, token, or artifact-byte authority.",
            expected_proof_hash=expected_proof_hash,
            proof=proof,
            blocked_fields=["html_inline_xbrl_downstream_proof_request"],
        )
    return response


def _not_recorded_status(*, request_id: str) -> dict[str, Any]:
    status_input = _status_input(operator_status_state="not_recorded")
    return _status_response(
        request_id=request_id,
        status_input=status_input,
        blocked_reasons=[],
        proof_summary={},
        next_allowed_actions=["record_sec_edgar_html_inline_xbrl_downstream_proof_before_status_available"],
    )


def _available_status(*, request_id: str, expected_proof_hash: str, proof: Mapping[str, Any]) -> dict[str, Any]:
    proof_summary = _proof_summary(proof)
    status_input = _status_input(
        operator_status_state="available",
        expected_proof_hash=expected_proof_hash,
        proof=proof,
    )
    return _status_response(
        request_id=request_id,
        status_input=status_input,
        blocked_reasons=[],
        proof_summary=proof_summary,
        next_allowed_actions=[
            "use_sec_edgar_html_inline_xbrl_downstream_status_as_operator_visible_e2e_evidence",
            "select_sec_edgar_html_inline_xbrl_downstream_rendered_status_projection",
        ],
    )


def _blocked_status(
    *,
    request_id: str,
    code: str,
    message: str,
    expected_proof_hash: str = "",
    proof: Mapping[str, Any] | None = None,
    blocked_fields: list[str] | None = None,
    next_allowed_actions: list[str] | None = None,
) -> dict[str, Any]:
    blocked_reasons = [
        {
            "reason": code,
            "message": message,
            "blocked_fields": list(blocked_fields or []),
        }
    ]
    status_input = _status_input(
        operator_status_state="blocked",
        expected_proof_hash=expected_proof_hash,
        proof=proof or {},
        blocked_reason_codes=[code],
    )
    return _status_response(
        request_id=request_id,
        status_input=status_input,
        blocked_reasons=blocked_reasons,
        proof_summary=_proof_summary(proof or {}),
        next_allowed_actions=next_allowed_actions
        or ["repair_or_refresh_sec_edgar_html_inline_xbrl_downstream_proof_authority"],
    )


def _status_response(
    *,
    request_id: str,
    status_input: Mapping[str, Any],
    blocked_reasons: list[dict[str, Any]],
    proof_summary: dict[str, Any],
    next_allowed_actions: list[str],
) -> dict[str, Any]:
    operator_status_hash = stable_hash({key: status_input[key] for key in STATUS_HASH_KEYS})
    state = str(status_input["operator_status_state"])
    return {
        **status_input,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": state,
        "operator_status_hash": operator_status_hash,
        "operator_status_projection_ref": f"{STATUS_PROJECTION_PREFIX}:{operator_status_hash[:24]}",
        "selected_status_states": list(STATUS_STATES),
        "proof_available": state == "available",
        "proof_summary": proof_summary,
        "status_projection": {
            "state": state,
            "available": state == "available",
            "blocked_reasons": blocked_reasons,
            "redacted_projection": True,
            "server_revalidated": state == "available",
            "parser_authority_bound": bool(status_input.get("parser_receipt_hash")),
            "material_bridge_authority_bound": bool(status_input.get("material_bridge_receipt_hash")),
        },
        "blocked_reasons": blocked_reasons,
        "raw_proof_request_rendered": False,
        "raw_proof_receipt_path_rendered": False,
        "raw_local_path_rendered": False,
        "raw_url_rendered": False,
        "artifact_bytes_rendered": False,
        "provider_private_token_rendered": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "runtime_db_or_storage_expansion_admitted": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "full_mockup_activation_enabled": False,
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": next_allowed_actions,
    }


def _status_input(
    *,
    operator_status_state: str,
    expected_proof_hash: str = "",
    proof: Mapping[str, Any] | None = None,
    blocked_reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    proof = proof or {}
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": STATUS_MODE,
        "operator_status_state": operator_status_state,
        "expected_proof_hash": expected_proof_hash if _is_sha256(expected_proof_hash) else "",
        "proof_hash": str(proof.get("proof_hash") or ""),
        "proof_state": str(proof.get("proof_state") or ""),
        "dataset_version_id": str(proof.get("dataset_version_id") or ""),
        "dataset_version_hash": str(proof.get("dataset_version_hash") or ""),
        "source_family": str(proof.get("source_family") or ""),
        "parser_family": str(proof.get("parser_family") or ""),
        "typed_content_contract_id": str(proof.get("typed_content_contract_id") or ""),
        "parser_receipt_hash": str(proof.get("parser_receipt_hash") or ""),
        "connector_receipt_hash": str(proof.get("connector_receipt_hash") or ""),
        "live_source_artifact_receipt_hash": str(proof.get("live_source_artifact_receipt_hash") or ""),
        "source_artifact_receipt_hash": str(proof.get("source_artifact_receipt_hash") or ""),
        "content_sha256": str(proof.get("content_sha256") or ""),
        "primary_document_hash": str(proof.get("primary_document_hash") or ""),
        "content_order_hash": str(proof.get("content_order_hash") or ""),
        "materialization_receipt_hash": str(proof.get("materialization_receipt_hash") or ""),
        "material_bridge_receipt_hash": str(
            proof.get("material_bridge_receipt_hash") or proof.get("bridge_receipt_hash") or ""
        ),
        "material_preview_hash": str(proof.get("material_preview_hash") or ""),
        "gate_b_decision_manifest_id": str(proof.get("gate_b_decision_manifest_id") or ""),
        "session_id": str(proof.get("session_id") or ""),
        "selection_manifest_id": str(proof.get("selection_manifest_id") or ""),
        "material_snapshot_payload_hash": str(proof.get("material_snapshot_payload_hash") or ""),
        "coverage_evidence_hash": str(proof.get("coverage_evidence_hash") or ""),
        "negative_invariants_hash": str(proof.get("negative_invariants_hash") or ""),
        "blocked_reason_codes": list(blocked_reason_codes or []),
    }


def _proof_summary(proof: Mapping[str, Any]) -> dict[str, Any]:
    if not proof:
        return {}
    return {
        "proof_hash": str(proof.get("proof_hash") or ""),
        "proof_state": str(proof.get("proof_state") or ""),
        "dataset_version_id": str(proof.get("dataset_version_id") or ""),
        "dataset_version_hash": str(proof.get("dataset_version_hash") or ""),
        "source_family": str(proof.get("source_family") or ""),
        "parser_family": str(proof.get("parser_family") or ""),
        "typed_content_contract_id": str(proof.get("typed_content_contract_id") or ""),
        "parser_receipt_hash": str(proof.get("parser_receipt_hash") or ""),
        "connector_receipt_hash": str(proof.get("connector_receipt_hash") or ""),
        "live_source_artifact_receipt_hash": str(proof.get("live_source_artifact_receipt_hash") or ""),
        "source_artifact_receipt_hash": str(proof.get("source_artifact_receipt_hash") or ""),
        "content_sha256": str(proof.get("content_sha256") or ""),
        "primary_document_hash": str(proof.get("primary_document_hash") or ""),
        "content_order_hash": str(proof.get("content_order_hash") or ""),
        "materialization_receipt_hash": str(proof.get("materialization_receipt_hash") or ""),
        "material_bridge_receipt_hash": str(
            proof.get("material_bridge_receipt_hash") or proof.get("bridge_receipt_hash") or ""
        ),
        "material_preview_hash": str(proof.get("material_preview_hash") or ""),
        "gate_b_decision_manifest_id": str(proof.get("gate_b_decision_manifest_id") or ""),
        "session_id": str(proof.get("session_id") or ""),
        "selection_manifest_id": str(proof.get("selection_manifest_id") or ""),
        "material_snapshot_payload_hash": str(proof.get("material_snapshot_payload_hash") or ""),
        "coverage_evidence_hash": str(proof.get("coverage_evidence_hash") or ""),
        "negative_invariants_hash": str(proof.get("negative_invariants_hash") or ""),
        "coverage": list(proof.get("coverage") or []),
        "redacted_projection": True,
    }


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    if blocked:
        _blocked(
            "sec_edgar_html_inline_xbrl_downstream_operator_status_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL downstream status does not admit caller paths, URLs, bytes, credentials, connector, model, browser, source-expansion, or frontend authority.",
            blocked_fields=blocked,
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_downstream_operator_status_unknown_field",
            "SEC EDGAR HTML/iXBRL downstream status fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_downstream_operator_status_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL downstream status requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_changed": False,
        "sec_edgar_network_fetch_admitted": False,
        "submissions_lookup_runtime_admitted": False,
        "html_inline_xbrl_reparse_or_materialization_admitted": False,
        "xml_xbrl_fact_authority_admitted": False,
        "financial_statement_semantics_admitted": False,
        "raw_sec_filing_url_authority_admitted": False,
        "source_expansion_enabled": False,
        "runtime_db_or_storage_expansion_enabled": False,
        "pdf_or_image_text_material_ingestion_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        return _is_forbidden_ref(value)
    return False


def _is_forbidden_ref(value: str) -> bool:
    text = value.strip().lower()
    return (
        text.startswith(("http://", "https://", "file://", "\\\\", "/tmp/", "/var/", "/home/"))
        or "aps-target-artifacts/" in text
        or bool(_LOCAL_PATH_RE.match(value.strip()))
    )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_html_inline_xbrl_downstream_operator_status_required_field_missing",
            "A required SEC EDGAR HTML/iXBRL downstream status field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_downstream_operator_status_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL downstream status request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _blocked(code: str, message: str, *, blocked_fields: list[str] | None = None) -> None:
    raise Layer3WorkbenchError(
        code,
        message,
        status="blocked",
        http_status=400,
        blocked_fields=blocked_fields or [],
    )


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
