from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_live_downstream_status,
    layer3_sec_edgar_live_material_bridge,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_edgar_source_acquisition,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_real_filing_downstream_validation.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_real_filing_downstream_validation_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_real_filing_downstream_validation_status.v1"
SCHEMA_VERSION = 1
VALIDATION_MODE = "sec_edgar_real_filing_acquisition_connector_downstream_validation_v1"
OPERATOR_DECISION = "record_sec_edgar_real_filing_connector_downstream_validation"
VALIDATION_STATE = "sec_edgar_real_filing_acquisition_connector_downstream_validation_ready"
RECEIPT_PREFIX = "sec-edgar-real-filing-downstream-validation"
RECEIPT_DIR = "layer3-sec-edgar-real-filing-downstream-validation"
REDACTION_POLICY_ID = "sec_edgar_real_filing_downstream_validation_redaction_v1"

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "validation_mode",
    "operator_decision",
    "connector_receipt_id",
    "connector_receipt_hash",
    "connector_example_id",
    "live_source_artifact_receipt_id",
    "live_source_artifact_receipt_hash",
    "source_acquisition_receipt_id",
    "source_acquisition_receipt_hash",
    "live_source_artifact_material_bridge_receipt_id",
    "live_source_artifact_material_bridge_receipt_hash",
    "material_bridge_receipt_hash",
    "gate_b_decision_manifest_id",
    "live_downstream_proof_hash",
    "downstream_proof_hash",
    "operator_status_request",
    "operator_status_hash",
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
}
RECEIPT_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "validation_mode",
    "connector_receipt_hash",
    "connector_example_id",
    "live_source_artifact_receipt_hash",
    "source_acquisition_receipt_hash",
    "live_source_artifact_material_bridge_receipt_hash",
    "material_bridge_receipt_hash",
    "gate_b_decision_manifest_id",
    "live_downstream_proof_hash",
    "downstream_proof_hash",
    "operator_status_hash",
    "identity_binding_hash",
    "diagnostics_hash",
)
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def record_sec_edgar_real_filing_connector_downstream_validation(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "validation_mode", VALIDATION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_operator_confirmation_required",
            "operator_confirmation=true is required before recording SEC EDGAR connector downstream validation.",
            blocked_fields=["operator_confirmation"],
        )

    connector_receipt_hash = _required_hash(request, "connector_receipt_hash")
    connector_receipt = (
        layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
            _required(request, "connector_receipt_id"),
            expected_connector_receipt_hash=connector_receipt_hash,
        )
    )
    connector_example_id = _required(request, "connector_example_id")
    connector_example, connector_acquisition = _connector_example_authority(
        connector_receipt,
        connector_example_id=connector_example_id,
    )
    live_receipt = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_receipt(
        _required(request, "live_source_artifact_receipt_id"),
        expected_live_source_artifact_receipt_hash=_required_hash(request, "live_source_artifact_receipt_hash"),
    )
    source_acquisition_receipt = layer3_sec_edgar_source_acquisition.read_sec_edgar_text_table_source_acquisition_receipt(
        _required(request, "source_acquisition_receipt_id"),
        expected_source_acquisition_receipt_hash=_required_hash(request, "source_acquisition_receipt_hash"),
    )
    live_bridge_receipt = (
        layer3_sec_edgar_live_material_bridge.read_sec_edgar_text_table_live_source_artifact_material_authority_bridge_receipt(
            _required(request, "live_source_artifact_material_bridge_receipt_id"),
            expected_bridge_receipt_hash=_required_hash(request, "live_source_artifact_material_bridge_receipt_hash"),
            live_source_artifact_receipt_hash=_required_hash(request, "live_source_artifact_receipt_hash"),
            source_acquisition_receipt_hash=_required_hash(request, "source_acquisition_receipt_hash"),
        )
    )
    _validate_connector_to_downstream_bindings(
        request,
        connector_example=connector_example,
        connector_acquisition=connector_acquisition,
        live_receipt=live_receipt,
        source_acquisition_receipt=source_acquisition_receipt,
        live_bridge_receipt=live_bridge_receipt,
    )
    operator_status = _revalidate_operator_status(request, db)
    identity_binding = _identity_binding(
        connector_example=connector_example,
        connector_acquisition=connector_acquisition,
        live_receipt=live_receipt,
        operator_status=operator_status,
    )
    diagnostics = _diagnostics(connector_receipt, connector_example=connector_example, operator_status=operator_status)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_mode": VALIDATION_MODE,
        "connector_receipt_hash": connector_receipt_hash,
        "connector_example_id": connector_example_id,
        "live_source_artifact_receipt_hash": _required_hash(request, "live_source_artifact_receipt_hash"),
        "source_acquisition_receipt_hash": _required_hash(request, "source_acquisition_receipt_hash"),
        "live_source_artifact_material_bridge_receipt_hash": _required_hash(
            request,
            "live_source_artifact_material_bridge_receipt_hash",
        ),
        "material_bridge_receipt_hash": _required_hash(request, "material_bridge_receipt_hash"),
        "gate_b_decision_manifest_id": _required(request, "gate_b_decision_manifest_id"),
        "live_downstream_proof_hash": _required_hash(request, "live_downstream_proof_hash"),
        "downstream_proof_hash": _required_hash(request, "downstream_proof_hash"),
        "operator_status_hash": _required_hash(request, "operator_status_hash"),
        "identity_binding_hash": stable_hash(identity_binding),
        "diagnostics_hash": stable_hash(diagnostics),
    }
    validation_hash = stable_hash({key: receipt_input[key] for key in RECEIPT_HASH_KEYS})
    request_binding = _read_request_binding(request_id)
    if request_binding and request_binding.get("validation_basis_hash") != validation_hash:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR connector downstream validation basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(validation_hash)
    if existing is not None:
        _write_request_binding(request_id, validation_hash, str(existing["validation_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, idempotent_replay=True, schema_id=SCHEMA_ID)

    receipt = {
        **receipt_input,
        "operator_decision": OPERATOR_DECISION,
        "validation_state": VALIDATION_STATE,
        "validation_receipt_hash": validation_hash,
        "validation_receipt_id": f"{RECEIPT_PREFIX}-{validation_hash[:24]}",
        "validation_receipt_ref": f"{RECEIPT_PREFIX}:{validation_hash[:24]}",
        "connector_receipt_id": _required(request, "connector_receipt_id"),
        "live_source_artifact_receipt_id": _required(request, "live_source_artifact_receipt_id"),
        "source_acquisition_receipt_id": _required(request, "source_acquisition_receipt_id"),
        "live_source_artifact_material_bridge_receipt_id": _required(
            request,
            "live_source_artifact_material_bridge_receipt_id",
        ),
        "identity_binding": identity_binding,
        "diagnostics": diagnostics,
        "operator_status_summary": _operator_status_summary(operator_status),
        "negative_invariants": _negative_invariants(),
        "request_id_hash": _sha256_text(request_id),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, validation_hash, receipt["validation_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, idempotent_replay=False, schema_id=SCHEMA_ID)


def inspect_sec_edgar_real_filing_downstream_validation_status(
    validation_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(validation_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-real-filing-downstream-validation-status-{receipt['validation_receipt_hash'][:12]}",
        idempotent_replay=False,
        schema_id=STATUS_SCHEMA_ID,
    )


def _connector_example_authority(
    receipt: Mapping[str, Any],
    *,
    connector_example_id: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    manifest = receipt.get("corpus_manifest") if isinstance(receipt.get("corpus_manifest"), Mapping) else {}
    examples = [item for item in manifest.get("example_records") or [] if isinstance(item, Mapping)]
    acquisitions = [item for item in receipt.get("acquisition_receipts") or [] if isinstance(item, Mapping)]
    example = next((item for item in examples if str(item.get("example_id") or "") == connector_example_id), None)
    acquisition = next((item for item in acquisitions if str(item.get("example_id") or "") == connector_example_id), None)
    if example is None or acquisition is None:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_connector_example_missing",
            "SEC EDGAR downstream validation requires an example id present in both connector manifest and acquisition receipts.",
            http_status=409,
            blocked_fields=["connector_example_id"],
        )
    if str(example.get("source_family") or "") != "complete_submission_text":
        _blocked(
            "sec_edgar_real_filing_downstream_validation_connector_example_not_supported_text",
            "Only connector-acquired complete-submission text examples are admitted for this downstream validation slice.",
            http_status=409,
            blocked_fields=["connector_example_id"],
        )
    return example, acquisition


def _validate_connector_to_downstream_bindings(
    request: Mapping[str, Any],
    *,
    connector_example: Mapping[str, Any],
    connector_acquisition: Mapping[str, Any],
    live_receipt: Mapping[str, Any],
    source_acquisition_receipt: Mapping[str, Any],
    live_bridge_receipt: Mapping[str, Any],
) -> None:
    if str(request.get("live_source_artifact_receipt_hash") or "") != str(
        connector_acquisition.get("live_source_artifact_receipt_hash") or ""
    ):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_authority_mismatch",
            "SEC EDGAR connector downstream validation authority is stale or mismatched.",
            http_status=409,
            blocked_fields=["live_source_artifact_receipt_hash"],
        )
    live_artifact = _mapping(live_receipt, "source_artifact_receipt")
    connector_artifact = _mapping(connector_acquisition, "source_artifact_receipt")
    source_artifact = _mapping(source_acquisition_receipt, "source_artifact_authority")
    bridge_live = _mapping(live_bridge_receipt, "live_source_artifact_authority")
    bridge_source = _mapping(live_bridge_receipt, "source_acquisition_authority")
    bridge_material = _mapping(live_bridge_receipt, "material_authority_bridge")
    for field in ("source_artifact_receipt_hash", "source_artifact_ref_hash", "content_sha256", "content_length"):
        expected = str(connector_artifact.get(field) or "")
        if str(live_artifact.get(field) or "") != expected or str(source_artifact.get(field) or "") != expected:
            _blocked(
                "sec_edgar_real_filing_downstream_validation_source_artifact_mismatch",
                "Connector, live artifact, and source-acquisition authority must bind the same source artifact.",
                http_status=409,
                blocked_fields=[field],
            )
    if str(bridge_live.get("source_artifact_receipt_hash") or "") != str(connector_artifact.get("source_artifact_receipt_hash") or ""):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_live_bridge_source_artifact_mismatch",
            "Live material bridge does not bind the connector-acquired source artifact.",
            http_status=409,
            blocked_fields=["live_source_artifact_material_bridge_receipt_id"],
        )
    for field in ("source_acquisition_receipt_hash", "authority_envelope_hash"):
        if field in bridge_source and not str(bridge_source.get(field) or ""):
            _blocked(
                "sec_edgar_real_filing_downstream_validation_live_bridge_authority_incomplete",
                "Live material bridge receipt is missing downstream authority fields.",
                http_status=409,
                blocked_fields=[field],
            )
    if str(bridge_material.get("bridge_receipt_hash") or "") != _required_hash(request, "material_bridge_receipt_hash"):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_material_bridge_hash_mismatch",
            "Material bridge receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["material_bridge_receipt_hash"],
        )
    if str(bridge_material.get("gate_b_decision_manifest_id") or "") != _required(request, "gate_b_decision_manifest_id"):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_gate_b_mismatch",
            "Gate B decision manifest id is stale or mismatched.",
            http_status=409,
            blocked_fields=["gate_b_decision_manifest_id"],
        )


def _revalidate_operator_status(request: Mapping[str, Any], db: Session) -> Mapping[str, Any]:
    status_request = request.get("operator_status_request")
    if not isinstance(status_request, Mapping):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_operator_status_request_missing",
            "Structured live downstream operator status request is required.",
            blocked_fields=["operator_status_request"],
        )
    status = layer3_sec_edgar_live_downstream_status.inspect_sec_edgar_text_table_live_source_artifact_downstream_operator_status(
        dict(status_request),
        db,
    )
    if status.get("operator_status_state") != "available":
        _blocked(
            "sec_edgar_real_filing_downstream_validation_operator_status_not_available",
            "SEC EDGAR connector downstream validation requires an available live downstream operator status.",
            http_status=409,
            blocked_fields=["operator_status_request"],
        )
    comparisons = {
        "operator_status_hash": status.get("operator_status_hash"),
        "live_source_artifact_receipt_hash": status.get("live_source_artifact_receipt_hash"),
        "source_acquisition_receipt_hash": status.get("source_acquisition_receipt_hash"),
        "live_source_artifact_material_bridge_receipt_hash": status.get(
            "live_source_artifact_material_bridge_receipt_hash"
        ),
        "material_bridge_receipt_hash": status.get("material_bridge_receipt_hash"),
        "gate_b_decision_manifest_id": status.get("gate_b_decision_manifest_id"),
        "live_downstream_proof_hash": status.get("proof_hash"),
        "downstream_proof_hash": status.get("downstream_proof_hash"),
    }
    for field, expected in comparisons.items():
        if str(request.get(field) or "") != str(expected or ""):
            _blocked(
                "sec_edgar_real_filing_downstream_validation_operator_status_authority_mismatch",
                "SEC EDGAR connector downstream validation requires operator status over the same downstream authority.",
                http_status=409,
                blocked_fields=[field],
            )
    return status


def _identity_binding(
    *,
    connector_example: Mapping[str, Any],
    connector_acquisition: Mapping[str, Any],
    live_receipt: Mapping[str, Any],
    operator_status: Mapping[str, Any],
) -> dict[str, Any]:
    live_identity = _mapping(live_receipt, "source_identity")
    connector_artifact = _mapping(connector_acquisition, "source_artifact_receipt")
    return {
        "connector_example_id": str(connector_example.get("example_id") or ""),
        "form_type": str(connector_example.get("form_type") or live_identity.get("form_type") or ""),
        "filing_date": str(connector_example.get("filing_date") or live_identity.get("filing_date") or ""),
        "source_family": str(connector_example.get("source_family") or ""),
        "source_family_roles": list(connector_example.get("source_family_roles") or []),
        "expected_support_status": str(connector_example.get("expected_support_status") or ""),
        "source_artifact_receipt_hash": str(connector_artifact.get("source_artifact_receipt_hash") or ""),
        "source_artifact_ref_hash": str(connector_artifact.get("source_artifact_ref_hash") or ""),
        "content_sha256": str(connector_artifact.get("content_sha256") or ""),
        "live_downstream_proof_hash": str(operator_status.get("proof_hash") or ""),
        "operator_status_hash": str(operator_status.get("operator_status_hash") or ""),
    }


def _diagnostics(
    connector_receipt: Mapping[str, Any],
    *,
    connector_example: Mapping[str, Any],
    operator_status: Mapping[str, Any],
) -> dict[str, Any]:
    connector_diagnostics = connector_receipt.get("diagnostics") if isinstance(connector_receipt.get("diagnostics"), Mapping) else {}
    return {
        "complete_submission_text_supported_path_validated": True,
        "html_inline_xbrl_classified_not_parsed": "html_inline_xbrl_classified_not_parsed"
        in list(connector_example.get("source_family_roles") or []),
        "generic_text_downgrade_performed": False,
        "full_sec_support_claimed": False,
        "connector_html_inline_xbrl_explicitly_classified": bool(
            connector_diagnostics.get("html_inline_xbrl_explicitly_classified")
        ),
        "operator_status_available": operator_status.get("operator_status_state") == "available",
        "layer3_downstream_execution_performed_by_validation_runtime": False,
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    idempotent_replay: bool,
    schema_id: str,
) -> dict[str, Any]:
    response = {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready",
        "validation_mode": VALIDATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "validation_state": receipt["validation_state"],
        "validation_receipt_id": receipt["validation_receipt_id"],
        "validation_receipt_hash": receipt["validation_receipt_hash"],
        "validation_receipt_ref": receipt["validation_receipt_ref"],
        "idempotent_replay": idempotent_replay,
        "connector_receipt_id": receipt["connector_receipt_id"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "connector_example_id": receipt["connector_example_id"],
        "authority_bindings": {
            "live_source_artifact_receipt_id": receipt["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": receipt["live_source_artifact_receipt_hash"],
            "source_acquisition_receipt_id": receipt["source_acquisition_receipt_id"],
            "source_acquisition_receipt_hash": receipt["source_acquisition_receipt_hash"],
            "live_source_artifact_material_bridge_receipt_id": receipt[
                "live_source_artifact_material_bridge_receipt_id"
            ],
            "live_source_artifact_material_bridge_receipt_hash": receipt[
                "live_source_artifact_material_bridge_receipt_hash"
            ],
            "material_bridge_receipt_hash": receipt["material_bridge_receipt_hash"],
            "gate_b_decision_manifest_id": receipt["gate_b_decision_manifest_id"],
            "live_downstream_proof_hash": receipt["live_downstream_proof_hash"],
            "downstream_proof_hash": receipt["downstream_proof_hash"],
            "operator_status_hash": receipt["operator_status_hash"],
        },
        "identity_binding": dict(receipt["identity_binding"]),
        "identity_binding_hash": receipt["identity_binding_hash"],
        "diagnostics": dict(receipt["diagnostics"]),
        "diagnostics_hash": receipt["diagnostics_hash"],
        "operator_status_summary": dict(receipt["operator_status_summary"]),
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "connector_authority_bound": True,
            "live_source_artifact_authority_bound": True,
            "source_acquisition_authority_bound": True,
            "live_material_bridge_authority_bound": True,
            "operator_status_authority_bound": True,
            "next_html_inline_xbrl_parser_gap": True,
        },
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made": False,
            "cache_hit_avoids_network_request": True,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "use this receipt as connector-acquired SEC filing downstream validation evidence",
            "select SEC HTML/iXBRL parser-source-family runtime after current-main sync",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_raw_authority_exposed",
            "SEC EDGAR connector downstream validation would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _operator_status_summary(status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "operator_status_state": str(status.get("operator_status_state") or ""),
        "proof_available": bool(status.get("proof_available")),
        "proof_hash": str(status.get("proof_hash") or ""),
        "downstream_proof_hash": str(status.get("downstream_proof_hash") or ""),
        "coverage": list((status.get("proof_summary") or {}).get("coverage") or []),
        "raw_url_rendered": False,
        "raw_local_path_rendered": False,
        "artifact_bytes_rendered": False,
    }


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_forbidden_request_fields",
            "SEC EDGAR connector downstream validation does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_unknown_field",
            "SEC EDGAR connector downstream validation fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_schema_not_admitted",
            "SEC EDGAR connector downstream validation requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _read_receipt_by_hash(validation_hash: str) -> dict[str, Any] | None:
    path = _receipts_dir() / f"{RECEIPT_PREFIX}-{validation_hash[:24]}.json"
    if not path.exists():
        return None
    return _read_verified_receipt(path.stem)


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_receipt_id_invalid",
            "SEC EDGAR connector downstream validation status requires a server-issued validation receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_real_filing_downstream_validation_receipt_id"],
        )
    path = _receipts_dir() / f"{receipt_id}.json"
    if not path.exists():
        _blocked(
            "sec_edgar_real_filing_downstream_validation_receipt_missing",
            "SEC EDGAR connector downstream validation receipt was not found.",
            http_status=404,
            blocked_fields=["sec_edgar_real_filing_downstream_validation_receipt_id"],
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_receipt_unreadable",
            "SEC EDGAR connector downstream validation receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("validation_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_receipt_invalid",
            "SEC EDGAR connector downstream validation receipt is invalid or mismatched.",
            http_status=409,
        )
    expected_hash = stable_hash({key: receipt[key] for key in RECEIPT_HASH_KEYS})
    if receipt.get("validation_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_receipt_hash_mismatch",
            "SEC EDGAR connector downstream validation receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipts_dir() / f"{receipt['validation_receipt_id']}.json"
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
            "sec_edgar_real_filing_downstream_validation_request_binding_unreadable",
            "SEC EDGAR connector downstream validation request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, validation_basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_real_filing_downstream_validation_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "validation_basis_hash": validation_basis_hash,
        "validation_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("validation_basis_hash") != validation_basis_hash:
            _blocked(
                "sec_edgar_real_filing_downstream_validation_request_binding_conflict",
                "SEC EDGAR connector downstream validation request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_authority_missing",
            f"SEC EDGAR connector downstream validation requires {key}.",
            http_status=409,
            blocked_fields=[key],
        )
    return item


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in FORBIDDEN_REQUEST_FIELDS and item is not None:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_forbidden_nested_fields(item, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith(("http://", "https://", "file://", "\\\\", "/tmp/", "/var/", "/home/")) or _LOCAL_PATH_RE.match(text):
            found.append(prefix or "request_body")
    return sorted(set(found))


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_changed": False,
        "sec_edgar_live_network_fetch_performed_by_validation": False,
        "sec_edgar_parser_expansion_admitted": False,
        "html_inline_xbrl_parser_runtime_admitted": False,
        "xml_xbrl_fact_authority_runtime_admitted": False,
        "raw_sec_filing_url_authority_admitted": False,
        "direct_live_artifact_to_material_without_source_acquisition_admitted": False,
        "direct_raw_artifact_parse_or_materialization_admitted": False,
        "dataset_version_creation_admitted": False,
        "gate_b_mutation_admitted_in_validation": False,
        "package_or_delivery_mutation_admitted": False,
        "candidate_b_general_sec_parser_admitted": False,
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
        text = value.strip()
        return text.startswith(("http://", "https://", "file://", "\\\\", "/tmp/", "/var/", "/home/")) or bool(
            _LOCAL_PATH_RE.match(text)
        )
    return False


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_required_field_missing",
            "A required SEC EDGAR connector downstream validation field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            "sec_edgar_real_filing_downstream_validation_hash_invalid",
            "SEC EDGAR connector downstream validation hash fields must be SHA-256 hex strings.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_real_filing_downstream_validation_{key}_not_admitted",
            "SEC EDGAR connector downstream validation request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_real_filing_downstream_validation_storage_root_unavailable",
            "SEC EDGAR connector downstream validation requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _receipts_dir() -> Path:
    return _root() / "receipts"


def _request_bindings_dir() -> Path:
    return _root() / "requests"


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
