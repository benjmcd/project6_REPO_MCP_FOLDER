from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import layer3_sec_edgar_real_company_corpus_validation
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_delivery_status_provenance.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_delivery_status_provenance_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_delivery_status_provenance_status.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "sec_edgar_delivery_status_provenance_v1"
OPERATOR_DECISION = "inspect_sec_edgar_real_company_delivery_status_provenance"
READY_STATE = "sec_edgar_delivery_status_provenance_ready"
BLOCKED_STATE = "sec_edgar_delivery_status_provenance_blocked"
RECEIPT_PREFIX = "sec-edgar-delivery-status-provenance"
RECEIPT_DIR = "layer3-sec-edgar-delivery-status-provenance"
REDACTION_POLICY_ID = "sec_edgar_delivery_status_provenance_redaction_v1"
EXPECTED_COMPANY_MATRIX = ("MSFT", "STLD", "SONY", "CCJ")
EXPECTED_FILING_COUNT = 8
REQUIRED_OUTPUT = "handoff_export_prepare"

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "status_mode",
    "operator_decision",
    "sec_edgar_real_company_corpus_validation_receipt_id",
    "sec_edgar_real_company_corpus_validation_receipt_hash",
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
PROVENANCE_HASH_KEYS = (
    "validation_receipt_hash",
    "connector_receipt_hash",
    "parser_receipt_hash",
    "fact_authority_receipt_hash",
    "fact_material_bridge_receipt_hash",
    "statement_classification_receipt_hash",
    "statement_candidate_product_receipt_hash",
    "package_review_preview_receipt_hash",
    "package_construction_receipt_hash",
    "package_review_submit_receipt_hash",
    "handoff_export_prepare_receipt_hash",
    "record_hash",
)
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def inspect_sec_edgar_real_company_delivery_status_provenance(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    _ = db
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "status_mode", STATUS_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_delivery_status_provenance_operator_confirmation_missing")],
        )

    validation_receipt_id = _required(request, "sec_edgar_real_company_corpus_validation_receipt_id")
    expected_validation_hash = _required(request, "sec_edgar_real_company_corpus_validation_receipt_hash")
    if not _is_sha256(expected_validation_hash):
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    "sec_edgar_delivery_status_provenance_validation_hash_invalid",
                    blocked_fields=["sec_edgar_real_company_corpus_validation_receipt_hash"],
                )
            ],
        )
    try:
        validation = layer3_sec_edgar_real_company_corpus_validation._read_verified_receipt(validation_receipt_id)
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
    if str(validation.get("validation_receipt_hash") or "") != expected_validation_hash:
        return _blocked_response(
            request_id=request_id,
            validation=validation,
            reasons=[
                _reason(
                    "sec_edgar_delivery_status_provenance_validation_hash_mismatch",
                    blocked_fields=[
                        "sec_edgar_real_company_corpus_validation_receipt_id",
                        "sec_edgar_real_company_corpus_validation_receipt_hash",
                    ],
                )
            ],
        )

    readiness_reasons = _validation_readiness_reasons(validation)
    if readiness_reasons:
        return _blocked_response(request_id=request_id, validation=validation, reasons=readiness_reasons)

    records = _delivery_status_records(validation)
    provenance_matrix = _provenance_hash_matrix(records)
    blocked_or_degraded = _blocked_or_degraded_delivery_gaps(records)
    diagnostics = _diagnostics(validation, records, blocked_or_degraded)
    receipt_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "status_mode": STATUS_MODE,
            "validation_receipt_hash": validation["validation_receipt_hash"],
            "record_hashes": [record["delivery_status_record_hash"] for record in records],
            "provenance_hash_matrix_hash": stable_hash(provenance_matrix),
            "diagnostics_hash": stable_hash(diagnostics),
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("delivery_status_provenance_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_delivery_status_provenance_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR delivery/status/provenance basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["delivery_status_provenance_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "status_mode": STATUS_MODE,
        "operator_decision": OPERATOR_DECISION,
        "delivery_status_provenance_state": READY_STATE,
        "delivery_status_provenance_receipt_id": f"{RECEIPT_PREFIX}-{receipt_hash[:24]}",
        "delivery_status_provenance_receipt_hash": receipt_hash,
        "delivery_status_provenance_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "validation_receipt_id": validation["validation_receipt_id"],
        "validation_receipt_hash": validation["validation_receipt_hash"],
        "connector_receipt_hash": validation["connector_receipt_hash"],
        "company_matrix": list(validation["company_matrix"]),
        "filing_count": len(records),
        "validation_receipt_status": "ready",
        "handoff_export_prepare_status": "ready",
        "delivery_readiness_status": "ready",
        "delivery_status_records": records,
        "provenance_hash_matrix": provenance_matrix,
        "blocked_or_degraded_delivery_gaps": blocked_or_degraded,
        "diagnostics": diagnostics,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt["delivery_status_provenance_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_delivery_status_provenance_status(
    delivery_status_provenance_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(delivery_status_provenance_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-delivery-status-provenance-status-{receipt['delivery_status_provenance_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _validation_readiness_reasons(validation: Mapping[str, Any]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    if validation.get("validation_state") != layer3_sec_edgar_real_company_corpus_validation.READY_STATE:
        reasons.append(_reason("sec_edgar_delivery_status_provenance_validation_not_ready"))
    if tuple(validation.get("company_matrix") or ()) != EXPECTED_COMPANY_MATRIX:
        reasons.append(_reason("sec_edgar_delivery_status_provenance_company_matrix_mismatch"))
    records = [item for item in validation.get("filing_validation_records") or [] if isinstance(item, Mapping)]
    if len(records) != EXPECTED_FILING_COUNT:
        reasons.append(_reason("sec_edgar_delivery_status_provenance_filing_count_mismatch"))
    for record in records:
        outputs = set(str(item) for item in record.get("outputs_produced") or [])
        handoff_hash = str((record.get("authority_hashes") or {}).get("handoff_export_prepare_receipt_hash") or "")
        if REQUIRED_OUTPUT not in outputs or not _is_sha256(handoff_hash):
            reasons.append(
                _reason(
                    "sec_edgar_delivery_status_provenance_missing_handoff_export_prepare_output",
                    record_index=record.get("record_index"),
                )
            )
    return reasons


def _delivery_status_records(validation: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in validation.get("filing_validation_records") or []:
        if not isinstance(source, Mapping):
            continue
        authority_hashes = dict(source.get("authority_hashes") or {})
        delivery_record = {
            "record_index": source.get("record_index"),
            "example_id": str(source.get("example_id") or ""),
            "ticker_hash": source.get("ticker_hash"),
            "cik_hash": source.get("cik_hash"),
            "company_name_hash": source.get("company_name_hash"),
            "form_type": str(source.get("form_type") or ""),
            "filing_date": str(source.get("filing_date") or ""),
            "source_family": str(source.get("source_family") or ""),
            "supported_degraded_blocked": str(source.get("supported_degraded_blocked") or ""),
            "validation_record_hash": source.get("record_hash"),
            "validation_receipt_hash": validation.get("validation_receipt_hash"),
            "connector_receipt_hash": validation.get("connector_receipt_hash"),
            "handoff_export_prepare_status": (
                "ready"
                if REQUIRED_OUTPUT in set(str(item) for item in source.get("outputs_produced") or [])
                and _is_sha256(str(authority_hashes.get("handoff_export_prepare_receipt_hash") or ""))
                else "blocked"
            ),
            "delivery_readiness_status": "ready" if source.get("supported_degraded_blocked") == "supported" else "blocked",
            "provenance_hashes": _record_provenance_hashes(validation, source),
            "order_evidence": dict(source.get("order_evidence") or {}),
            "gaps_found": list(source.get("gaps_found") or []),
            "operator_usefulness": source.get("operator_usefulness"),
        }
        delivery_record["delivery_status_record_hash"] = stable_hash(delivery_record)
        records.append(delivery_record)
    return records


def _record_provenance_hashes(validation: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, str]:
    hashes = {
        "validation_receipt_hash": str(validation.get("validation_receipt_hash") or ""),
        "connector_receipt_hash": str(validation.get("connector_receipt_hash") or ""),
        "record_hash": str(record.get("record_hash") or ""),
    }
    authority_hashes = dict(record.get("authority_hashes") or {})
    for key in PROVENANCE_HASH_KEYS:
        if key in {"validation_receipt_hash", "connector_receipt_hash", "record_hash"}:
            continue
        if key == "statement_candidate_product_receipt_hash":
            value = str(authority_hashes.get("statement_candidate_product_receipt_hash") or authority_hashes.get("downstream_product_receipt_hash") or "")
        else:
            value = str(authority_hashes.get(key) or "")
        hashes[key] = value
    return hashes


def _provenance_hash_matrix(records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_index": record["record_index"],
            "example_id": record["example_id"],
            "form_type": record["form_type"],
            "delivery_readiness_status": record["delivery_readiness_status"],
            "handoff_export_prepare_status": record["handoff_export_prepare_status"],
            "provenance_hashes": dict(record["provenance_hashes"]),
            "delivery_status_record_hash": record["delivery_status_record_hash"],
        }
        for record in records
    ]


def _blocked_or_degraded_delivery_gaps(records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for record in records:
        if record.get("delivery_readiness_status") == "ready" and record.get("handoff_export_prepare_status") == "ready":
            continue
        gaps.append(
            {
                "record_index": record.get("record_index"),
                "example_id": record.get("example_id"),
                "form_type": record.get("form_type"),
                "delivery_readiness_status": record.get("delivery_readiness_status"),
                "handoff_export_prepare_status": record.get("handoff_export_prepare_status"),
                "gaps_found": list(record.get("gaps_found") or []),
            }
        )
    return gaps


def _diagnostics(
    validation: Mapping[str, Any],
    records: list[Mapping[str, Any]],
    blocked_or_degraded: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "validation_receipt_bound": True,
        "validation_receipt_hash": validation["validation_receipt_hash"],
        "real_company_count": len(validation.get("company_matrix") or []),
        "filing_count": len(records),
        "delivery_ready_count": sum(1 for record in records if record.get("delivery_readiness_status") == "ready"),
        "handoff_export_prepare_ready_count": sum(
            1 for record in records if record.get("handoff_export_prepare_status") == "ready"
        ),
        "blocked_or_degraded_delivery_gap_count": len(blocked_or_degraded),
        "delivery_file_response_served": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "sec_network_fetch_performed": False,
        "parser_rerun_performed": False,
        "package_mutation_performed": False,
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
        "status_mode": STATUS_MODE,
        "operator_decision": OPERATOR_DECISION,
        "delivery_status_provenance_state": receipt["delivery_status_provenance_state"],
        "delivery_status_provenance_receipt_id": receipt["delivery_status_provenance_receipt_id"],
        "delivery_status_provenance_receipt_hash": receipt["delivery_status_provenance_receipt_hash"],
        "delivery_status_provenance_receipt_ref": receipt["delivery_status_provenance_receipt_ref"],
        "validation_receipt_id": receipt["validation_receipt_id"],
        "validation_receipt_hash": receipt["validation_receipt_hash"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "company_matrix": list(receipt["company_matrix"]),
        "filing_count": receipt["filing_count"],
        "validation_receipt_status": receipt["validation_receipt_status"],
        "handoff_export_prepare_status": receipt["handoff_export_prepare_status"],
        "delivery_readiness_status": receipt["delivery_readiness_status"],
        "delivery_status_records": list(receipt["delivery_status_records"]),
        "provenance_hash_matrix": list(receipt["provenance_hash_matrix"]),
        "blocked_or_degraded_delivery_gaps": list(receipt["blocked_or_degraded_delivery_gaps"]),
        "diagnostics": dict(receipt["diagnostics"]),
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made_by_delivery_status": False,
            "file_response_served_by_delivery_status": False,
            "provider_object_created_by_delivery_status": False,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "inspect SEC delivery/status/provenance status",
            "select SEC real-company operator inspection over delivery provenance",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_delivery_status_provenance_raw_authority_exposed",
            "SEC EDGAR delivery/status/provenance would expose raw path, URL, token, accession, company name, raw value, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _blocked_response(
    *,
    request_id: str,
    reasons: list[dict[str, Any]],
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "blocked",
        "status_mode": STATUS_MODE,
        "operator_decision": OPERATOR_DECISION,
        "delivery_status_provenance_state": BLOCKED_STATE,
        "validation_receipt_id": validation.get("validation_receipt_id") if validation else None,
        "validation_receipt_hash": validation.get("validation_receipt_hash") if validation else None,
        "delivery_readiness_status": "blocked",
        "blocked_reasons": reasons,
        "diagnostics": {
            "validation_receipt_bound": bool(validation),
            "delivery_file_response_served": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "sec_network_fetch_performed": False,
            "parser_rerun_performed": False,
            "package_mutation_performed": False,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["repair_or_refresh_sec_edgar_real_company_corpus_validation_receipt"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_delivery_status_provenance_blocked_response_raw_authority_exposed",
            "Blocked SEC EDGAR delivery/status/provenance response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_delivery_status_provenance_forbidden_request_fields",
            "SEC EDGAR delivery/status/provenance does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, frontend authority, accessions, company names, or raw fact values.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_delivery_status_provenance_unknown_field",
            "SEC EDGAR delivery/status/provenance fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_delivery_status_provenance_schema_not_admitted",
            "SEC EDGAR delivery/status/provenance requires the admitted request schema.",
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
            "sec_edgar_delivery_status_provenance_receipt_id_invalid",
            "SEC EDGAR delivery/status/provenance status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_delivery_status_provenance_receipt_id"],
        )
    path = _receipt_path(receipt_id)
    if not path.exists():
        _blocked(
            "sec_edgar_delivery_status_provenance_receipt_missing",
            "SEC EDGAR delivery/status/provenance receipt was not found.",
            http_status=404,
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_delivery_status_provenance_receipt_unreadable",
            "SEC EDGAR delivery/status/provenance receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("delivery_status_provenance_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_delivery_status_provenance_receipt_invalid",
            "SEC EDGAR delivery/status/provenance receipt is invalid or mismatched.",
            http_status=409,
        )
    if receipt.get("delivery_status_provenance_receipt_hash") != suffix + receipt.get(
        "delivery_status_provenance_receipt_hash", ""
    )[24:]:
        _blocked(
            "sec_edgar_delivery_status_provenance_receipt_hash_mismatch",
            "SEC EDGAR delivery/status/provenance receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["delivery_status_provenance_receipt_id"]))
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
            "sec_edgar_delivery_status_provenance_request_binding_unreadable",
            "SEC EDGAR delivery/status/provenance request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_delivery_status_provenance_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "delivery_status_provenance_basis_hash": basis_hash,
        "delivery_status_provenance_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("delivery_status_provenance_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_delivery_status_provenance_request_binding_conflict",
                "SEC EDGAR delivery/status/provenance request binding conflicts with existing authority.",
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
            "sec_edgar_delivery_status_provenance_storage_root_unavailable",
            "SEC EDGAR delivery/status/provenance requires the existing Layer 3 storage root.",
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
            "sec_edgar_delivery_status_provenance_required_field_missing",
            "A required SEC EDGAR delivery/status/provenance field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_delivery_status_provenance_{key}_not_admitted",
            "SEC EDGAR delivery/status/provenance request does not match the admitted runtime contract.",
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
