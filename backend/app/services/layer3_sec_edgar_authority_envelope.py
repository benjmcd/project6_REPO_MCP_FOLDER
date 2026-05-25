from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.models import (
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    VariableDefinition,
    uuid_str,
)
from app.services.layer3_aps_source_family import source_family_for_parser
from app.services.layer3_workbench_error import Layer3WorkbenchError

SCHEMA_ID = "layer3.sec_edgar_text_table_authority_envelope_validation.v1"
MODE = "sec_edgar_text_table_authority_envelope_validation_runtime_v1"
READY_STATE = "sec_edgar_text_table_authority_envelope_ready"
BLOCKED_STATE = "sec_edgar_text_table_authority_envelope_blocked"
SOURCE_FAMILY = "sec_edgar_text_table"
PARSER_FAMILY = "sec_edgar_filing"
TYPED_CONTENT_CONTRACT_ID = "aps_sec_edgar_filing_units_v1"
AUTHORITY_ENVELOPE_REF_PREFIX = "sec-edgar-text-table-authority-envelope"

_FORBIDDEN_INPUT_KEYS = {
    "path",
    "raw_path",
    "local_path",
    "file_path",
    "url",
    "raw_url",
    "source_url",
    "filing_url",
    "provider_url",
    "connector_url",
    "command",
    "args",
    "provider_credentials",
    "connector_credentials",
    "browser_storage",
}
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def validate_sec_edgar_text_table_authority_envelope(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    _reject_forbidden_input_authority(fields)
    dataset_version_id = _required_str(fields, "dataset_version_id")
    mode = str(fields.get("authority_envelope_mode") or MODE).strip()
    if mode != MODE:
        raise Layer3WorkbenchError(
            "sec_edgar_text_table_authority_envelope_mode_not_admitted",
            "SEC EDGAR text-table authority envelope validation requires the admitted runtime mode.",
            status="blocked",
            http_status=400,
            blocked_fields=["authority_envelope_mode"],
            details={"expected_authority_envelope_mode": MODE, "received_authority_envelope_mode": mode},
        )

    version = db.get(DatasetVersion, dataset_version_id)
    dataset = db.get(Dataset, version.dataset_id) if version is not None else None
    variables = _dataset_version_variables(db, dataset_version_id=dataset_version_id) if version is not None else []
    provenance_rows = _source_provenance_rows(db, dataset_version_id=dataset_version_id) if version is not None else []
    provenance = [_serialize_provenance(row) for row in provenance_rows]
    primary = provenance[0] if provenance else {}
    source_family = source_family_for_parser(primary.get("parser_family")) if provenance else {}

    blocked: list[dict[str, Any]] = []
    if version is None:
        blocked.append(_reason("sec_edgar_text_table_authority_dataset_version_missing"))
    if not provenance:
        blocked.append(_reason("sec_edgar_text_table_authority_materialization_missing"))
    if version is not None and str(version.status or "") != "ready":
        blocked.append(_reason("sec_edgar_text_table_authority_dataset_version_not_ready"))
    _require_expected(fields, "expected_parser_family", PARSER_FAMILY, blocked)
    _require_expected(fields, "expected_source_family", SOURCE_FAMILY, blocked)
    _require_expected(fields, "expected_typed_content_contract_id", TYPED_CONTENT_CONTRACT_ID, blocked)
    if provenance:
        if primary.get("parser_family") != PARSER_FAMILY:
            blocked.append(_reason("sec_edgar_text_table_authority_parser_family_mismatch"))
        if primary.get("typed_content_contract_id") != TYPED_CONTENT_CONTRACT_ID:
            blocked.append(_reason("sec_edgar_text_table_authority_typed_content_contract_mismatch"))
        if source_family.get("source_family") != SOURCE_FAMILY:
            blocked.append(_reason("sec_edgar_text_table_authority_source_family_mismatch"))
        if source_family.get("admission_state") != "admitted_materialized_dataset_version":
            blocked.append(_reason("sec_edgar_text_table_authority_source_family_not_admitted"))
        if _contains_raw_url_authority(provenance):
            blocked.append(_reason("sec_edgar_text_table_authority_raw_url_or_path_authority_present"))

    if fields.get("rollback_confirmed") is not True:
        blocked.append(_reason("sec_edgar_text_table_authority_rollback_confirmation_missing"))
    if fields.get("operator_confirmed") is not True:
        blocked.append(_reason("sec_edgar_text_table_authority_operator_confirmation_missing"))

    dataset_version_hash = _dataset_version_hash(version, dataset, variables) if version is not None else None
    materialization_receipt_hash = _materialization_hash(dataset_version_id, provenance) if provenance else None
    materialization_receipt_id = (
        f"sec-edgar-text-table-materialization-{materialization_receipt_hash[:24]}"
        if materialization_receipt_hash
        else None
    )
    authority_hash = (
        _authority_hash(
            dataset_version_id=dataset_version_id,
            dataset_version_hash=dataset_version_hash,
            materialization_receipt_hash=materialization_receipt_hash,
            source_family=source_family,
        )
        if dataset_version_hash and materialization_receipt_hash and source_family
        else None
    )
    expected_hash = str(fields.get("expected_authority_envelope_hash") or "").strip()
    if expected_hash and authority_hash and expected_hash != authority_hash:
        blocked.append(_reason("sec_edgar_text_table_authority_stale_envelope_hash"))

    ready = not blocked
    authority_envelope_id = (
        f"sec-edgar-text-table-authority-envelope-{authority_hash[:24]}" if ready and authority_hash else None
    )
    return {
        **_base_response(status="ready" if ready else "blocked"),
        "authority_envelope_mode": MODE,
        "authority_envelope_state": READY_STATE if ready else BLOCKED_STATE,
        "dataset_version_id": dataset_version_id,
        "dataset_version_hash": dataset_version_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "authority_envelope_id": authority_envelope_id,
        "authority_envelope_hash": authority_hash,
        "authority_envelope_ref": (
            f"{AUTHORITY_ENVELOPE_REF_PREFIX}://{authority_envelope_id}/{authority_hash[:24]}"
            if authority_envelope_id and authority_hash
            else None
        ),
        "materialization_receipt_model": "deterministic_validation_projection_no_new_write",
        "materialization_receipt_id": materialization_receipt_id,
        "materialization_receipt_hash": materialization_receipt_hash,
        "material_analysis_payload": {
            "payload_shape": "mixed_narrative_table",
            "payload_source": "existing_aps_sec_edgar_filing_units_v1_materialization",
            "text_filing_narrative_units_admitted": ready,
            "table_units_admitted": ready,
            "layer3_material_bridge_admitted_now": False,
        },
        "provenance_summary": _provenance_summary(
            dataset=dataset,
            version=version,
            variables=variables,
            primary=primary,
            source_family=source_family,
        ),
        "status_projection": {
            "ready": ready,
            "blocked_reasons": blocked,
            "next_allowed_actions": (
                ["implement_sec_edgar_text_table_material_authority_bridge_v1"]
                if ready
                else ["revise_sec_edgar_text_table_authority_envelope_input"]
            ),
        },
        "negative_invariants": {
            "sec_edgar_network_fetch_admitted": False,
            "sec_edgar_parser_expansion_admitted": False,
            "xml_html_inline_xbrl_admitted": False,
            "raw_sec_filing_url_authority_admitted": False,
            "source_expansion_admitted": False,
            "runtime_db_or_storage_expansion_admitted": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "auth_security_expansion_enabled": False,
            "full_mockup_activation_enabled": False,
            "frontend_durable_authority_enabled": False,
            "browser_storage_authority_enabled": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
    }


def _base_response(*, status: str) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": uuid_str(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }


def _required_str(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise Layer3WorkbenchError(
            f"sec_edgar_text_table_authority_{key}_missing",
            f"SEC EDGAR text-table authority envelope validation requires {key}.",
            status="blocked",
            http_status=400,
            blocked_fields=[key],
        )
    return value


def _require_expected(fields: Mapping[str, Any], key: str, expected: str, blocked: list[dict[str, Any]]) -> None:
    received = str(fields.get(key) or expected).strip()
    if received != expected:
        blocked.append(
            _reason(
                f"sec_edgar_text_table_authority_{key}_mismatch",
                expected=expected,
                received=received,
            )
        )


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _dataset_version_variables(db: Session, *, dataset_version_id: str) -> list[VariableDefinition]:
    return (
        db.query(VariableDefinition)
        .filter(VariableDefinition.dataset_version_id == dataset_version_id)
        .order_by(VariableDefinition.ordinal_position.asc(), VariableDefinition.variable_name.asc())
        .all()
    )


def _source_provenance_rows(db: Session, *, dataset_version_id: str) -> list[DatasetSourceProvenance]:
    return (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .order_by(DatasetSourceProvenance.dataset_source_provenance_id.asc())
        .all()
    )


def _serialize_provenance(row: DatasetSourceProvenance) -> dict[str, Any]:
    source_reference = row.source_reference_json or {}
    return {
        "dataset_source_provenance_id": row.dataset_source_provenance_id,
        "source_system": row.source_system,
        "source_mode": row.source_mode,
        "source_artifact_key_hash": _sha256_text(row.source_artifact_key),
        "downloaded_sha256": row.downloaded_sha256,
        "raw_storage_ref_present": bool(str(row.raw_storage_ref or "").strip()),
        "parser_family": source_reference.get("parser_family"),
        "parser_contract_id": source_reference.get("parser_contract_id"),
        "typed_content_contract_id": source_reference.get("typed_content_contract_id"),
        "target_id": source_reference.get("target_id"),
        "accession_or_submission_id": source_reference.get("accession_or_submission_id")
        or source_reference.get("accession_number"),
        "form_type": source_reference.get("form_type"),
        "filer_or_cik": source_reference.get("filer_or_cik") or source_reference.get("cik"),
        "filing_date": source_reference.get("filing_date"),
        "table_index": source_reference.get("table_index"),
        "table_hash": source_reference.get("table_hash"),
        "diagnostics_ref_hash": _sha256_text(str(source_reference.get("diagnostics_ref") or "")),
        "raw_authority_scan": {
            "source_artifact_key": row.source_artifact_key,
            "raw_storage_ref": row.raw_storage_ref,
            "source_reference_json": source_reference,
        },
    }


def _provenance_summary(
    *,
    dataset: Dataset | None,
    version: DatasetVersion | None,
    variables: list[VariableDefinition],
    primary: Mapping[str, Any],
    source_family: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source_family": source_family.get("source_family") or SOURCE_FAMILY,
        "source_family_label": source_family.get("source_family_label") or "SEC/EDGAR text table",
        "source_admission_state": source_family.get("admission_state"),
        "source_family_scope": source_family.get("scope"),
        "dataset_identity": {
            "dataset_id": version.dataset_id if version is not None else None,
            "dataset_version_id": version.dataset_version_id if version is not None else None,
            "dataset_name": dataset.name if dataset is not None else None,
            "version_label": version.version_label if version is not None else None,
            "version_type": version.version_type if version is not None else None,
            "status": version.status if version is not None else None,
        },
        "variable_summary": {
            "variable_count": len(variables),
            "numeric_variable_count": len([item for item in variables if item.is_numeric]),
            "time_variable_count": len([item for item in variables if item.is_time_index]),
        },
        "sec_edgar_identity": {
            "form_type": primary.get("form_type"),
            "accession_or_submission_id": primary.get("accession_or_submission_id"),
            "filer_or_cik": primary.get("filer_or_cik"),
            "filing_date": primary.get("filing_date"),
        },
        "redaction": {
            "raw_source_artifact_key_exposed": False,
            "raw_storage_ref_exposed": False,
            "diagnostics_ref_exposed": False,
            "raw_url_exposed": False,
        },
    }


def _dataset_version_hash(
    version: DatasetVersion,
    dataset: Dataset | None,
    variables: list[VariableDefinition],
) -> str:
    return _sha256_json(
        {
            "dataset_id": version.dataset_id,
            "dataset_version_id": version.dataset_version_id,
            "dataset_name": dataset.name if dataset is not None else None,
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


def _materialization_hash(dataset_version_id: str, provenance: list[Mapping[str, Any]]) -> str:
    redacted = []
    for item in provenance:
        redacted.append({key: value for key, value in item.items() if key != "raw_authority_scan"})
    return _sha256_json({"dataset_version_id": dataset_version_id, "provenance": redacted})


def _authority_hash(
    *,
    dataset_version_id: str,
    dataset_version_hash: str | None,
    materialization_receipt_hash: str | None,
    source_family: Mapping[str, Any],
) -> str:
    return _sha256_json(
        {
            "hash_version": "sec_edgar_text_table_authority_envelope_hash_v1",
            "dataset_version_id": dataset_version_id,
            "dataset_version_hash": dataset_version_hash,
            "materialization_receipt_hash": materialization_receipt_hash,
            "parser_family": PARSER_FAMILY,
            "source_family": source_family.get("source_family"),
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "authority_envelope_mode": MODE,
        }
    )


def _sha256_json(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reject_forbidden_input_authority(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_INPUT_KEYS:
                raise Layer3WorkbenchError(
                    "sec_edgar_text_table_authority_forbidden_input_authority",
                    "SEC EDGAR text-table authority envelope validation rejects caller-supplied raw paths, URLs, commands, credentials, connectors, providers, and browser authority.",
                    status="blocked",
                    http_status=400,
                    blocked_fields=[child_path],
                )
            _reject_forbidden_input_authority(nested, child_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_input_authority(nested, f"{path}[{index}]")
    elif isinstance(value, str) and (_RAW_URL_RE.search(value) or _LOCAL_PATH_RE.search(value)):
        raise Layer3WorkbenchError(
            "sec_edgar_text_table_authority_forbidden_input_ref",
            "SEC EDGAR text-table authority envelope validation rejects caller-supplied raw paths and URLs.",
            status="blocked",
            http_status=400,
            blocked_fields=[path or "request_body"],
        )


def _contains_raw_url_authority(provenance: list[Mapping[str, Any]]) -> bool:
    for item in provenance:
        raw = item.get("raw_authority_scan")
        if _scan_raw_authority(raw):
            return True
    return False


def _scan_raw_authority(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).lower()
            if key_text in {"source_url", "filing_url", "raw_url", "provider_url", "connector_url", "local_path"}:
                return True
            if _scan_raw_authority(nested):
                return True
    elif isinstance(value, list):
        return any(_scan_raw_authority(nested) for nested in value)
    elif isinstance(value, str):
        text = value.strip()
        if _RAW_URL_RE.search(text) or _LOCAL_PATH_RE.search(text):
            return True
    return False
