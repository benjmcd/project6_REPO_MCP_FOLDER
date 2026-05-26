from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import layer3_sec_edgar_delivery_status_provenance
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_operator_inspection.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_operator_inspection_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_operator_inspection_status.v1"
SCHEMA_VERSION = 1
INSPECTION_MODE = "sec_edgar_operator_inspection_v1"
OPERATOR_DECISION = "inspect_sec_edgar_real_company_operator_surface"
READY_STATE = "sec_edgar_operator_inspection_ready"
BLOCKED_STATE = "sec_edgar_operator_inspection_blocked"
RECEIPT_PREFIX = "sec-edgar-operator-inspection"
RECEIPT_DIR = "layer3-sec-edgar-operator-inspection"
REDACTION_POLICY_ID = "sec_edgar_operator_inspection_redaction_v1"
OPERATOR_INSPECTION_BREADTH_SELECTION_VERSION = "sec_edgar_operator_inspection_breadth_selection_v1"
OPERATOR_INSPECTION_BREADTH_SELECTED_MATRIX = ("XOM", "PFE", "UAL", "T")
OPERATOR_INSPECTION_BREADTH_SELECTED_PROFILE_TAGS = (
    "energy_major",
    "pharmaceutical_life_sciences",
    "airline_transport",
    "telecom_media",
    "debt_intensive",
    "commodity_exposure",
)
OPERATOR_INSPECTION_BREADTH_RUNTIME_ENABLED = False

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "inspection_mode",
    "operator_decision",
    "sec_edgar_delivery_status_provenance_receipt_id",
    "sec_edgar_delivery_status_provenance_receipt_hash",
    "operator_confirmation",
    "actor",
}
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
    "download_url",
    "public_url",
    "signed_url",
    "command",
    "process",
    "stdout",
    "stderr",
    "file",
    "files",
    "file_bytes",
    "artifact_bytes",
    "provider_credentials",
    "connector_credentials",
    "provider_public_url",
    "provider_private_url",
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
    "accession",
    "accession_number",
    "company_name",
    "value",
    "value_text",
    "fact_value",
    "raw_fact_value",
}
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def inspect_sec_edgar_real_company_operator_surface(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    _ = db
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "inspection_mode", INSPECTION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_operator_inspection_operator_confirmation_missing")],
        )

    provenance_receipt_id = _required(request, "sec_edgar_delivery_status_provenance_receipt_id")
    expected_provenance_hash = _required(request, "sec_edgar_delivery_status_provenance_receipt_hash")
    if not _is_sha256(expected_provenance_hash):
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    "sec_edgar_operator_inspection_delivery_status_provenance_hash_invalid",
                    blocked_fields=["sec_edgar_delivery_status_provenance_receipt_hash"],
                )
            ],
        )
    try:
        provenance = layer3_sec_edgar_delivery_status_provenance._read_verified_receipt(provenance_receipt_id)
    except Layer3WorkbenchError as exc:
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    exc.error_code,
                    message=exc.message,
                    blocked_fields=list(exc.blocked_fields),
                )
            ],
        )
    if str(provenance.get("delivery_status_provenance_receipt_hash") or "") != expected_provenance_hash:
        return _blocked_response(
            request_id=request_id,
            provenance=provenance,
            reasons=[
                _reason(
                    "sec_edgar_operator_inspection_delivery_status_provenance_hash_mismatch",
                    blocked_fields=[
                        "sec_edgar_delivery_status_provenance_receipt_id",
                        "sec_edgar_delivery_status_provenance_receipt_hash",
                    ],
                )
            ],
        )

    readiness_reasons = _provenance_readiness_reasons(provenance)
    if readiness_reasons:
        return _blocked_response(request_id=request_id, provenance=provenance, reasons=readiness_reasons)

    matrix = _company_filing_inspection_matrix(provenance)
    rollup = _readiness_rollup(provenance, matrix)
    provenance_status = _provenance_status(provenance, matrix)
    receipt_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "inspection_mode": INSPECTION_MODE,
            "delivery_status_provenance_receipt_hash": provenance["delivery_status_provenance_receipt_hash"],
            "inspection_matrix_hash": stable_hash(matrix),
            "readiness_rollup_hash": stable_hash(rollup),
            "provenance_status_hash": stable_hash(provenance_status),
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("operator_inspection_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_operator_inspection_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR operator inspection basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["operator_inspection_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "inspection_mode": INSPECTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_inspection_state": READY_STATE,
        "operator_inspection_receipt_id": f"{RECEIPT_PREFIX}-{receipt_hash[:24]}",
        "operator_inspection_receipt_hash": receipt_hash,
        "operator_inspection_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "delivery_status_provenance_receipt_id": provenance["delivery_status_provenance_receipt_id"],
        "delivery_status_provenance_receipt_hash": provenance["delivery_status_provenance_receipt_hash"],
        "validation_receipt_hash": provenance["validation_receipt_hash"],
        "connector_receipt_hash": provenance["connector_receipt_hash"],
        "filing_count": provenance["filing_count"],
        "inspection_status": "available",
        "company_filing_inspection_matrix": matrix,
        "readiness_rollup": rollup,
        "provenance_status": provenance_status,
        "blocked_or_degraded_delivery_gaps": list(provenance["blocked_or_degraded_delivery_gaps"]),
        "operator_inspection_summary": _operator_inspection_summary(provenance, rollup),
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt["operator_inspection_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_operator_inspection_status(operator_inspection_receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(operator_inspection_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-operator-inspection-status-{receipt['operator_inspection_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _provenance_readiness_reasons(provenance: Mapping[str, Any]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    if provenance.get("delivery_status_provenance_state") != layer3_sec_edgar_delivery_status_provenance.READY_STATE:
        reasons.append(_reason("sec_edgar_operator_inspection_delivery_status_provenance_not_ready"))
    if provenance.get("delivery_readiness_status") != "ready":
        reasons.append(_reason("sec_edgar_operator_inspection_delivery_readiness_not_ready"))
    if provenance.get("handoff_export_prepare_status") != "ready":
        reasons.append(_reason("sec_edgar_operator_inspection_handoff_export_prepare_not_ready"))
    return reasons


def _company_filing_inspection_matrix(provenance: Mapping[str, Any]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for record in provenance.get("delivery_status_records") or []:
        if not isinstance(record, Mapping):
            continue
        inspection_status = "inspectable" if record.get("delivery_readiness_status") == "ready" else "blocked"
        inspection_record = {
            "record_index": record.get("record_index"),
            "example_id_hash": stable_hash({"example_id": str(record.get("example_id") or "")}),
            "ticker_hash": record.get("ticker_hash"),
            "cik_hash": record.get("cik_hash"),
            "company_name_hash": record.get("company_name_hash"),
            "form_type": str(record.get("form_type") or ""),
            "filing_date": str(record.get("filing_date") or ""),
            "source_family": str(record.get("source_family") or ""),
            "validation_record_hash": record.get("validation_record_hash"),
            "delivery_status_record_hash": record.get("delivery_status_record_hash"),
            "handoff_export_prepare_status": record.get("handoff_export_prepare_status"),
            "delivery_readiness_status": record.get("delivery_readiness_status"),
            "operator_usefulness": record.get("operator_usefulness"),
            "gaps_found": list(record.get("gaps_found") or []),
            "quality_assessment_status": record.get("quality_assessment_status"),
            "quality_dimensions": dict(record.get("quality_dimensions") or {}),
            "quality_gaps": list(record.get("quality_gaps") or []),
            "quality_evidence_hash": record.get("quality_evidence_hash"),
            "provenance_available": bool((record.get("provenance_hashes") or {}).get("handoff_export_prepare_receipt_hash")),
            "inspection_status": inspection_status,
            "redacted_operator_projection": True,
        }
        inspection_record["operator_inspection_record_hash"] = stable_hash(inspection_record)
        matrix.append(inspection_record)
    return matrix


def _readiness_rollup(provenance: Mapping[str, Any], matrix: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "company_count": len(provenance.get("company_matrix") or []),
        "filing_count": len(matrix),
        "inspectable_count": sum(1 for record in matrix if record.get("inspection_status") == "inspectable"),
        "blocked_count": sum(1 for record in matrix if record.get("inspection_status") == "blocked"),
        "ready_filing_count": sum(1 for record in matrix if record.get("delivery_readiness_status") == "ready"),
        "handoff_export_prepare_ready_count": sum(
            1 for record in matrix if record.get("handoff_export_prepare_status") == "ready"
        ),
        "blocked_or_degraded_count": len(provenance.get("blocked_or_degraded_delivery_gaps") or []),
        "operator_inspection_available": True,
        "validation_ready": provenance.get("validation_receipt_status") == "ready",
        "delivery_ready": provenance.get("delivery_readiness_status") == "ready",
        "handoff_ready": provenance.get("handoff_export_prepare_status") == "ready",
        "read_only_status_inspection": True,
        "delivery_status_provenance_bound": True,
        "provenance_hash_matrix_bound": True,
    }


def _provenance_status(provenance: Mapping[str, Any], matrix: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "delivery_status_provenance_receipt_hash": provenance["delivery_status_provenance_receipt_hash"],
        "validation_receipt_hash": provenance["validation_receipt_hash"],
        "connector_receipt_hash": provenance["connector_receipt_hash"],
        "provenance_hash_matrix_hash": stable_hash(provenance.get("provenance_hash_matrix") or []),
        "inspection_matrix_hash": stable_hash(matrix),
        "company_filing_inspection_matrix_hash": stable_hash(matrix),
        "redacted_projection": True,
        "server_revalidated": True,
    }


def _operator_inspection_summary(provenance: Mapping[str, Any], rollup: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "inspection_scope": "sec_edgar_real_company_delivery_status_provenance",
        "delivery_readiness_status": provenance["delivery_readiness_status"],
        "filing_count": rollup["filing_count"],
        "inspectable_count": rollup["inspectable_count"],
        "blocked_count": rollup["blocked_count"],
        "ready_filing_count": rollup["ready_filing_count"],
        "blocked_or_degraded_count": rollup["blocked_or_degraded_count"],
        "operator_next_action": "use_redacted_operator_inspection_as_sec_real_company_closeout_evidence",
        "raw_authority_rendered": False,
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready",
        "inspection_mode": INSPECTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_inspection_state": receipt["operator_inspection_state"],
        "operator_inspection_receipt_id": receipt["operator_inspection_receipt_id"],
        "operator_inspection_receipt_hash": receipt["operator_inspection_receipt_hash"],
        "operator_inspection_receipt_ref": receipt["operator_inspection_receipt_ref"],
        "delivery_status_provenance_receipt_id": receipt["delivery_status_provenance_receipt_id"],
        "delivery_status_provenance_receipt_hash": receipt["delivery_status_provenance_receipt_hash"],
        "validation_receipt_hash": receipt["validation_receipt_hash"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "filing_count": receipt["filing_count"],
        "inspection_status": receipt["inspection_status"],
        "company_filing_inspection_matrix": list(receipt["company_filing_inspection_matrix"]),
        "readiness_rollup": dict(receipt["readiness_rollup"]),
        "provenance_status": dict(receipt["provenance_status"]),
        "blocked_or_degraded_delivery_gaps": list(receipt["blocked_or_degraded_delivery_gaps"]),
        "operator_inspection_summary": dict(receipt["operator_inspection_summary"]),
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made_by_operator_inspection": False,
            "file_response_served_by_operator_inspection": False,
            "provider_object_created_by_operator_inspection": False,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "use SEC real-company operator inspection as closeout evidence",
            "perform final SEC real-company path completion audit",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_operator_inspection_raw_authority_exposed",
            "SEC EDGAR operator inspection would expose raw path, URL, token, accession, company name, raw value, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _blocked_response(
    *,
    request_id: str,
    reasons: list[dict[str, Any]],
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "blocked",
        "inspection_mode": INSPECTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_inspection_state": BLOCKED_STATE,
        "delivery_status_provenance_receipt_id": provenance.get("delivery_status_provenance_receipt_id") if provenance else None,
        "delivery_status_provenance_receipt_hash": provenance.get("delivery_status_provenance_receipt_hash") if provenance else None,
        "inspection_status": "blocked",
        "blocked_reasons": reasons,
        "operator_inspection_summary": {
            "inspection_scope": "sec_edgar_real_company_delivery_status_provenance",
            "operator_inspection_available": False,
            "raw_authority_rendered": False,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["repair_or_refresh_sec_edgar_delivery_status_provenance_receipt"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_operator_inspection_blocked_response_raw_authority_exposed",
            "Blocked SEC EDGAR operator inspection response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_operator_inspection_forbidden_request_fields",
            "SEC EDGAR operator inspection does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, frontend authority, accessions, company names, or raw fact values.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_operator_inspection_unknown_field",
            "SEC EDGAR operator inspection fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_operator_inspection_schema_not_admitted",
            "SEC EDGAR operator inspection requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _read_receipt_by_hash(receipt_hash: str) -> dict[str, Any] | None:
    path = _receipt_path(f"{RECEIPT_PREFIX}-{receipt_hash[:24]}")
    if not path.exists():
        return None
    return _read_verified_receipt(path.stem)


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_operator_inspection_receipt_id_invalid",
            "SEC EDGAR operator inspection status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_operator_inspection_receipt_id"],
        )
    path = _receipt_path(receipt_id)
    if not path.exists():
        _blocked(
            "sec_edgar_operator_inspection_receipt_missing",
            "SEC EDGAR operator inspection receipt was not found.",
            http_status=404,
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_operator_inspection_receipt_unreadable",
            "SEC EDGAR operator inspection receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("operator_inspection_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_operator_inspection_receipt_invalid",
            "SEC EDGAR operator inspection receipt is invalid or mismatched.",
            http_status=409,
        )
    if receipt.get("operator_inspection_receipt_hash") != suffix + receipt.get("operator_inspection_receipt_hash", "")[24:]:
        _blocked(
            "sec_edgar_operator_inspection_receipt_hash_mismatch",
            "SEC EDGAR operator inspection receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["operator_inspection_receipt_id"]))
    if target.exists():
        _read_verified_receipt(target.stem)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_operator_inspection_request_binding_unreadable",
            "SEC EDGAR operator inspection request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_operator_inspection_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "operator_inspection_basis_hash": basis_hash,
        "operator_inspection_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("operator_inspection_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_operator_inspection_request_binding_conflict",
                "SEC EDGAR operator inspection request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _negative_invariants() -> dict[str, bool]:
    return {
        "raw_url_exposed": False,
        "raw_local_path_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
        "accession_exposed": False,
        "company_name_exposed": False,
        "sec_network_fetch_performed": False,
        "parser_rerun_performed": False,
        "package_mutation_performed": False,
        "delivery_file_response_served": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "candidate_b_pdf_only_routing_performed": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in FORBIDDEN_REQUEST_FIELDS:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_forbidden_nested_fields(item, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        text = value.strip()
        if _is_forbidden_ref(text):
            found.append(prefix or "request_body")
    return sorted(set(found))


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
        or "storage://" in text
        or bool(_LOCAL_PATH_RE.match(value.strip()))
    )


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "requests"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_operator_inspection_storage_root_unavailable",
            "SEC EDGAR operator inspection requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_operator_inspection_required_field_missing",
            "A required SEC EDGAR operator inspection field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_operator_inspection_{key}_not_admitted",
            "SEC EDGAR operator inspection request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _blocked(
    code: str,
    message: str,
    *,
    http_status: int = 400,
    blocked_fields: list[str] | None = None,
) -> None:
    raise Layer3WorkbenchError(
        code,
        message,
        status="blocked",
        http_status=http_status,
        blocked_fields=blocked_fields or [],
    )
