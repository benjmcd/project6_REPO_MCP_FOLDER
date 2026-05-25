from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import DatasetSourceProvenance
from app.services import layer3_sec_edgar_authority_envelope
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_text_table_source_acquisition_authority.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_text_table_source_acquisition_authority_request.v1"
SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID = "layer3.sec_edgar_text_table_source_artifact_receipt.v1"
SCHEMA_VERSION = 1
ACQUISITION_MODE = "sec_edgar_text_table_source_acquisition_authority_v1"
OPERATOR_DECISION = "record_sec_edgar_text_table_source_acquisition_authority"
AVAILABLE_STATE = "available"
RECEIPT_PREFIX = "sec-edgar-text-table-source-acquisition"
SOURCE_ARTIFACT_RECEIPT_PREFIX = "sec-edgar-text-table-source-artifact"
RECEIPT_DIR = "layer3-sec-edgar-source-acquisition"
SOURCE_FAMILY = layer3_sec_edgar_authority_envelope.SOURCE_FAMILY
PARSER_FAMILY = layer3_sec_edgar_authority_envelope.PARSER_FAMILY
TYPED_CONTENT_CONTRACT_ID = layer3_sec_edgar_authority_envelope.TYPED_CONTENT_CONTRACT_ID
PARSER_CONTRACT_ID = "aps_sec_edgar_filing_parser_v1"
SOURCE_MODE = "artifact_sec_edgar_filing_parser"
REDACTION_POLICY_ID = "sec_edgar_text_table_source_acquisition_authority_redaction_v1"

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "acquisition_mode",
    "operator_decision",
    "dataset_version_id",
    "source_artifact_receipt_id",
    "source_artifact_receipt_hash",
    "source_artifact_ref_hash",
    "accession_or_submission_id_hash",
    "cik_or_filer_ref_hash",
    "form_type",
    "filing_date",
    "content_sha256",
    "content_length",
    "parser_family",
    "parser_contract_id",
    "typed_content_contract_id",
    "materialization_receipt_hash",
    "dataset_version_hash",
    "authority_envelope_hash",
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
    "process_id",
    "pid",
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
ACCESSION_KEYS = ("accession_or_submission_id", "accession_number", "submission_id")
CIK_KEYS = ("cik_or_filer_ref", "filer_or_cik", "cik")
CONTENT_LENGTH_KEYS = ("content_length", "content_length_bytes", "byte_length", "size_bytes")
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def record_sec_edgar_text_table_source_acquisition_authority(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "acquisition_mode", ACQUISITION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    _require_exact(request, "parser_family", PARSER_FAMILY)
    _require_exact(request, "parser_contract_id", PARSER_CONTRACT_ID)
    _require_exact(request, "typed_content_contract_id", TYPED_CONTENT_CONTRACT_ID)
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_text_table_source_acquisition_operator_confirmation_missing",
            "operator_confirmation=true is required before recording SEC EDGAR source-acquisition authority.",
            http_status=409,
            blocked_fields=["operator_confirmation"],
        )

    dataset_version_id = _required(request, "dataset_version_id")
    envelope = _load_ready_authority_envelope(request=request, dataset_version_id=dataset_version_id, db=db)
    source_artifact = _load_source_artifact_authority(
        request=request,
        dataset_version_id=dataset_version_id,
        envelope=envelope,
        db=db,
    )
    mismatches = _source_artifact_mismatches(request, source_artifact)
    if mismatches:
        _blocked(
            "sec_edgar_text_table_source_acquisition_stale_or_mismatched_source_artifact_authority",
            "The supplied SEC EDGAR source-artifact authority is stale or does not match server-owned materialization provenance.",
            http_status=409,
            blocked_fields=mismatches,
        )

    acquisition_authority_hash = stable_hash(
        {
            "hash_version": "sec_edgar_text_table_source_acquisition_authority_hash_v1",
            "schema_id": SCHEMA_ID,
            "acquisition_mode": ACQUISITION_MODE,
            "operator_decision": OPERATOR_DECISION,
            "dataset_version_id": dataset_version_id,
            "dataset_version_hash": source_artifact["dataset_version_hash"],
            "materialization_receipt_hash": source_artifact["materialization_receipt_hash"],
            "authority_envelope_hash": source_artifact["authority_envelope_hash"],
            "source_artifact_receipt_hash": source_artifact["source_artifact_receipt_hash"],
            "source_artifact_ref_hash": source_artifact["source_artifact_ref_hash"],
            "parser_family": PARSER_FAMILY,
            "parser_contract_id": PARSER_CONTRACT_ID,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "source_mode": SOURCE_MODE,
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{acquisition_authority_hash[:24]}"
    receipt_ref, idempotent_replay = _write_receipt(
        receipt_id=receipt_id,
        receipt_hash=acquisition_authority_hash,
        request_id=request_id,
        source_artifact=source_artifact,
    )
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": AVAILABLE_STATE,
        "mode": ACQUISITION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "source_acquisition_authority_state": AVAILABLE_STATE,
        "source_acquisition_receipt_id": receipt_id,
        "source_acquisition_receipt_hash": acquisition_authority_hash,
        "source_acquisition_receipt_ref": receipt_ref,
        "source_acquisition_receipt_status": "recorded",
        "idempotent_replay": idempotent_replay,
        "append_only_source_acquisition_authority_receipt": True,
        "exclusive_receipt_per_source_artifact_authority": True,
        "dataset_version_id": dataset_version_id,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "source_mode": SOURCE_MODE,
        "dataset_version_hash": source_artifact["dataset_version_hash"],
        "materialization_receipt_hash": source_artifact["materialization_receipt_hash"],
        "authority_envelope_hash": source_artifact["authority_envelope_hash"],
        "source_artifact_authority": source_artifact,
        "authority_bindings": {
            "source_artifact_receipt_hash": source_artifact["source_artifact_receipt_hash"],
            "source_artifact_ref_hash": source_artifact["source_artifact_ref_hash"],
            "content_sha256": source_artifact["content_sha256"],
            "content_length": source_artifact["content_length"],
            "accession_or_submission_id_hash": source_artifact["accession_or_submission_id_hash"],
            "cik_or_filer_ref_hash": source_artifact["cik_or_filer_ref_hash"],
            "form_type": source_artifact["form_type"],
            "filing_date": source_artifact["filing_date"],
            "parser_family": PARSER_FAMILY,
            "parser_contract_id": PARSER_CONTRACT_ID,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "source_mode": SOURCE_MODE,
            "dataset_version_hash": source_artifact["dataset_version_hash"],
            "materialization_receipt_hash": source_artifact["materialization_receipt_hash"],
            "authority_envelope_hash": source_artifact["authority_envelope_hash"],
        },
        "compatibility": {
            "existing_sec_edgar_text_table_authority_envelope_validation_runtime": True,
            "material_preview_gate_b_compatibility_preserved": True,
            "source_artifact_receipt_bound_to_materialized_dataset_version": True,
            "dataset_source_provenance_revalidated": True,
        },
        "operator_visible_source_acquisition_status": {
            "selected_status_states": ["not_recorded", "available", "blocked"],
            "server_owned_source_artifact_receipt_available": True,
            "redacted_receipt_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_source_artifact_receipt_blocks_acquisition": True,
            "stale_source_artifact_hash_blocks_acquisition": True,
            "missing_materialization_linkage_blocks_acquisition": True,
            "parser_contract_mismatch_blocks_acquisition": True,
            "typed_content_contract_mismatch_blocks_acquisition": True,
            "dataset_version_hash_mismatch_blocks_acquisition": True,
            "authority_envelope_hash_mismatch_blocks_acquisition": True,
            "operator_confirmation_required": True,
        },
        "baseline_rollback": {"preserved": True},
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_default_scope": {
            "preserved": True,
            "scope": "eligible_effective_pdfs_plus_receipt_bound_selected_classes_only",
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "validate SEC EDGAR text-table authority envelope",
            "prepare SEC EDGAR material authority bridge",
            "drive Layer 3 material preview and Gate B",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_text_table_source_acquisition_raw_authority_exposed",
            "SEC EDGAR source-acquisition authority would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _load_ready_authority_envelope(
    *,
    request: Mapping[str, Any],
    dataset_version_id: str,
    db: Session,
) -> dict[str, Any]:
    authority_envelope_hash = _required_hash(request, "authority_envelope_hash")
    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "expected_authority_envelope_hash": authority_envelope_hash,
            "expected_parser_family": PARSER_FAMILY,
            "expected_source_family": SOURCE_FAMILY,
            "expected_typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    blocked: list[str] = []
    if envelope.get("authority_envelope_state") != layer3_sec_edgar_authority_envelope.READY_STATE:
        blocked.append("authority_envelope_hash")
    for field in ("dataset_version_hash", "materialization_receipt_hash", "authority_envelope_hash"):
        if str(envelope.get(field) or "") != _required_hash(request, field):
            blocked.append(field)
    if blocked:
        _blocked(
            "sec_edgar_text_table_source_acquisition_authority_envelope_not_ready_or_stale",
            "SEC EDGAR source-acquisition authority requires a current ready authority envelope.",
            http_status=409,
            blocked_fields=sorted(set(blocked)),
        )
    return envelope


def _load_source_artifact_authority(
    *,
    request: Mapping[str, Any],
    dataset_version_id: str,
    envelope: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    rows = (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .order_by(DatasetSourceProvenance.dataset_source_provenance_id.asc())
        .all()
    )
    if not rows:
        _blocked(
            "sec_edgar_text_table_source_acquisition_materialization_linkage_missing",
            "SEC EDGAR source-acquisition authority requires materialized DatasetSourceProvenance rows.",
            http_status=409,
            blocked_fields=["dataset_version_id"],
        )
    blocked = []
    refs = _unique_text(row.source_artifact_key for row in rows)
    if len(refs) != 1:
        blocked.append("source_artifact_ref_hash")
    content_hashes = _unique_text(row.downloaded_sha256 for row in rows)
    if len(content_hashes) != 1 or not _is_hash(content_hashes[0]):
        blocked.append("content_sha256")

    references = [dict(row.source_reference_json or {}) for row in rows]
    source_modes = _unique_text(row.source_mode for row in rows)
    if source_modes != [SOURCE_MODE]:
        blocked.append("source_mode")
    if _unique_reference_text(references, ("parser_family",)) != [PARSER_FAMILY]:
        blocked.append("parser_family")
    if _unique_reference_text(references, ("parser_contract_id",)) != [PARSER_CONTRACT_ID]:
        blocked.append("parser_contract_id")
    if _unique_reference_text(references, ("typed_content_contract_id",)) != [TYPED_CONTENT_CONTRACT_ID]:
        blocked.append("typed_content_contract_id")

    content_lengths = _unique_reference_int(references, CONTENT_LENGTH_KEYS)
    accession_values = _unique_reference_text(references, ACCESSION_KEYS)
    cik_values = _unique_reference_text(references, CIK_KEYS)
    form_types = _unique_reference_text(references, ("form_type",))
    filing_dates = _unique_reference_text(references, ("filing_date",))
    if len(content_lengths) != 1 or content_lengths[0] <= 0:
        blocked.append("content_length")
    if len(accession_values) != 1:
        blocked.append("accession_or_submission_id_hash")
    if len(cik_values) != 1:
        blocked.append("cik_or_filer_ref_hash")
    if len(form_types) != 1:
        blocked.append("form_type")
    if len(filing_dates) != 1:
        blocked.append("filing_date")
    if blocked:
        _blocked(
            "sec_edgar_text_table_source_acquisition_source_artifact_manifest_incomplete",
            "SEC EDGAR source-acquisition authority requires one server-owned SEC filing source-artifact manifest bound to the materialization.",
            http_status=409,
            blocked_fields=sorted(set(blocked)),
        )

    source_artifact_ref_hash = _sha256_text(refs[0])
    content_sha256 = content_hashes[0]
    source_artifact_receipt_id = f"{SOURCE_ARTIFACT_RECEIPT_PREFIX}-{source_artifact_ref_hash[:24]}"
    accession_hash = _sha256_text(accession_values[0])
    cik_hash = _sha256_text(cik_values[0])
    source_artifact_receipt_hash = stable_hash(
        {
            "schema_id": SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "source_artifact_receipt_id": source_artifact_receipt_id,
            "dataset_version_id": dataset_version_id,
            "source_artifact_ref_hash": source_artifact_ref_hash,
            "content_sha256": content_sha256,
            "content_length": content_lengths[0],
            "accession_or_submission_id_hash": accession_hash,
            "cik_or_filer_ref_hash": cik_hash,
            "form_type": form_types[0],
            "filing_date": filing_dates[0],
            "parser_family": PARSER_FAMILY,
            "parser_contract_id": PARSER_CONTRACT_ID,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "source_mode": SOURCE_MODE,
            "dataset_version_hash": envelope.get("dataset_version_hash"),
            "materialization_receipt_hash": envelope.get("materialization_receipt_hash"),
            "authority_envelope_hash": envelope.get("authority_envelope_hash"),
        }
    )
    return {
        "source_artifact_receipt_id": source_artifact_receipt_id,
        "source_artifact_receipt_hash": source_artifact_receipt_hash,
        "source_artifact_ref_hash": source_artifact_ref_hash,
        "content_sha256": content_sha256,
        "content_length": content_lengths[0],
        "accession_or_submission_id_hash": accession_hash,
        "cik_or_filer_ref_hash": cik_hash,
        "form_type": form_types[0],
        "filing_date": filing_dates[0],
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "source_mode": SOURCE_MODE,
        "dataset_version_hash": envelope.get("dataset_version_hash"),
        "materialization_receipt_hash": envelope.get("materialization_receipt_hash"),
        "authority_envelope_hash": envelope.get("authority_envelope_hash"),
        "server_owned_source_artifact_authority": True,
        "raw_source_artifact_ref_exposed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }


def _write_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    source_artifact: Mapping[str, Any],
) -> tuple[str, bool]:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "acquisition_mode": ACQUISITION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "source_acquisition_authority_state": AVAILABLE_STATE,
        "request_id": request_id,
        "source_acquisition_receipt_id": receipt_id,
        "source_acquisition_receipt_hash": receipt_hash,
        "source_artifact_authority": dict(source_artifact),
        "append_only_source_acquisition_authority_receipt": True,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "recorded_at": _server_time(),
    }
    target = _receipt_root() / f"{receipt_id}.json"
    if target.exists():
        existing = _read_receipt(target)
        if existing.get("source_acquisition_receipt_hash") != receipt_hash:
            _blocked(
                "sec_edgar_text_table_source_acquisition_receipt_conflict",
                "A SEC EDGAR source-acquisition receipt already exists for this authority.",
                http_status=409,
            )
        return f"{RECEIPT_PREFIX}:{receipt_hash[:24]}", True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_receipt(target)
        if existing.get("source_acquisition_receipt_hash") != receipt_hash:
            _blocked(
                "sec_edgar_text_table_source_acquisition_receipt_conflict",
                "A SEC EDGAR source-acquisition receipt already exists for this authority.",
                http_status=409,
            )
        return f"{RECEIPT_PREFIX}:{receipt_hash[:24]}", True
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_source_acquisition_receipt_write_failed",
            "SEC EDGAR source-acquisition authority receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    return f"{RECEIPT_PREFIX}:{receipt_hash[:24]}", False


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_text_table_source_acquisition_forbidden_request_fields",
            "SEC EDGAR source-acquisition authority does not admit caller paths, URLs, bytes, credentials, commands, process state, connector, model, browser, source-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_text_table_source_acquisition_unknown_field",
            "SEC EDGAR source-acquisition authority fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_text_table_source_acquisition_schema_not_admitted",
            "SEC EDGAR source-acquisition authority requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _source_artifact_mismatches(request: Mapping[str, Any], source_artifact: Mapping[str, Any]) -> list[str]:
    fields = (
        "source_artifact_receipt_id",
        "source_artifact_receipt_hash",
        "source_artifact_ref_hash",
        "accession_or_submission_id_hash",
        "cik_or_filer_ref_hash",
        "form_type",
        "filing_date",
        "content_sha256",
        "parser_family",
        "parser_contract_id",
        "typed_content_contract_id",
        "materialization_receipt_hash",
        "dataset_version_hash",
        "authority_envelope_hash",
    )
    mismatches = [field for field in fields if str(request.get(field) or "") != str(source_artifact.get(field) or "")]
    if int(request.get("content_length") or 0) != int(source_artifact.get("content_length") or 0):
        mismatches.append("content_length")
    return mismatches


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in FORBIDDEN_REQUEST_FIELDS:
                found.append(child_path)
            found.extend(_find_forbidden_nested_fields(nested, child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_find_forbidden_nested_fields(nested, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        text = value.strip()
        if _RAW_URL_RE.search(text) or _LOCAL_PATH_RE.search(text):
            found.append(prefix or "request_body")
    return found


def _unique_reference_text(references: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: set[str] = set()
    for reference in references:
        for key in keys:
            text = str(reference.get(key) or "").strip()
            if text:
                values.add(text)
                break
    return sorted(values)


def _unique_reference_int(references: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[int]:
    values: set[int] = set()
    for reference in references:
        for key in keys:
            if reference.get(key) is None:
                continue
            try:
                value = int(reference.get(key))
            except (TypeError, ValueError):
                continue
            values.add(value)
            break
    return sorted(values)


def _unique_text(values: Any) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value or "").strip()})


def _receipt_root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_text_table_source_acquisition_storage_root_unavailable",
            "SEC EDGAR source-acquisition authority requires the existing Layer 3 storage root for append-only receipts.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _read_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_text_table_source_acquisition_receipt_unreadable",
            "SEC EDGAR source-acquisition authority receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict):
        _blocked(
            "sec_edgar_text_table_source_acquisition_receipt_invalid",
            "SEC EDGAR source-acquisition authority receipts must be JSON objects.",
            http_status=409,
        )
    return receipt


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_text_table_source_acquisition_{key}_missing",
            f"SEC EDGAR source-acquisition authority requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_text_table_source_acquisition_{key}_invalid",
            f"SEC EDGAR source-acquisition authority requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    received = str(fields.get(key) or "").strip()
    if received != expected:
        _blocked(
            f"sec_edgar_text_table_source_acquisition_{key}_mismatch",
            f"SEC EDGAR source-acquisition authority requires {key}={expected}.",
            blocked_fields=[key],
            details={"expected": expected, "received": received},
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return bool(_LOCAL_PATH_RE.search(text) or text.startswith("http://") or text.startswith("https://"))
    return False


def _negative_invariants() -> dict[str, bool]:
    return {
        "sec_edgar_network_fetch_admitted": False,
        "sec_network_cache_or_rate_behavior_admitted": False,
        "raw_sec_filing_url_authority_admitted": False,
        "sec_edgar_parser_expansion_admitted": False,
        "xml_html_inline_xbrl_admitted": False,
        "source_expansion_admitted": False,
        "runtime_db_or_storage_expansion_admitted": False,
        "new_runtime_storage_root_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "browser_supplied_local_path_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_sec_url_admitted": False,
        "browser_supplied_artifact_bytes_admitted": False,
        "browser_supplied_command_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "provider_token_exposed": False,
    }


def _blocked(
    code: str,
    message: str,
    *,
    http_status: int = 400,
    blocked_fields: list[str] | None = None,
    details: Mapping[str, Any] | None = None,
) -> None:
    raise Layer3WorkbenchError(
        code,
        message,
        status="blocked",
        http_status=http_status,
        blocked_fields=blocked_fields or [],
    )
