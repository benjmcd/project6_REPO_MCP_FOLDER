from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_authority_envelope,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_material_bridge,
    layer3_sec_edgar_source_acquisition,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_material_authority_bridge.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_material_authority_bridge_request.v1"
SCHEMA_VERSION = 1
BRIDGE_MODE = "sec_edgar_text_table_live_source_artifact_to_layer3_material_authority_v1"
READY_STATE = "sec_edgar_text_table_live_source_artifact_material_authority_bridge_ready"
BLOCKED_STATE = "sec_edgar_text_table_live_source_artifact_material_authority_bridge_blocked"
SOURCE_FAMILY = layer3_sec_edgar_authority_envelope.SOURCE_FAMILY
PARSER_FAMILY = layer3_sec_edgar_authority_envelope.PARSER_FAMILY
PARSER_CONTRACT_ID = "aps_sec_edgar_filing_parser_v1"
TYPED_CONTENT_CONTRACT_ID = layer3_sec_edgar_authority_envelope.TYPED_CONTENT_CONTRACT_ID
LIVE_ACQUISITION_MODE = layer3_sec_edgar_live_source_artifact.ACQUISITION_MODE
SOURCE_ACQUISITION_MODE = layer3_sec_edgar_source_acquisition.ACQUISITION_MODE
EXISTING_MATERIAL_BRIDGE_MODE = layer3_sec_edgar_material_bridge.BRIDGE_MODE
LIVE_SOURCE_ARTIFACT_FAMILY = layer3_sec_edgar_live_source_artifact.SOURCE_ARTIFACT_FAMILY
RECEIPT_PREFIX = "sec-edgar-text-table-live-source-artifact-l3-material-bridge"
RECEIPT_DIR = "layer3-sec-edgar-live-source-artifact-material-bridge"
REDACTION_POLICY_ID = "sec_edgar_text_table_live_source_artifact_material_bridge_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_text_table_live_source_artifact_material_bridge_hash_v1"

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "bridge_mode",
    "live_source_artifact_receipt_id",
    "live_source_artifact_receipt_hash",
    "source_acquisition_receipt_id",
    "source_acquisition_receipt_hash",
    "dataset_version_id",
    "authority_envelope_hash",
    "expected_materialization_receipt_hash",
    "expected_material_preview_hash",
    "expected_gate_b_decision_manifest_id",
    "rollback_confirmed",
    "operator_confirmed",
    "actor",
}
_FORBIDDEN_INPUT_KEYS = {
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
def prepare_sec_edgar_text_table_live_source_artifact_material_authority_bridge(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "bridge_mode", BRIDGE_MODE)

    dataset_version_id = _required(request, "dataset_version_id")
    authority_envelope_hash = _required_hash(request, "authority_envelope_hash")
    rollback_confirmed = request.get("rollback_confirmed") is True
    operator_confirmed = request.get("operator_confirmed") is True
    if not rollback_confirmed or not operator_confirmed:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            reasons=[
                *([] if rollback_confirmed else [_reason("missing_rollback_confirmation")]),
                *([] if operator_confirmed else [_reason("missing_operator_confirmation")]),
            ],
        )

    live_receipt = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_receipt(
        _required(request, "live_source_artifact_receipt_id"),
        expected_live_source_artifact_receipt_hash=_required_hash(request, "live_source_artifact_receipt_hash"),
    )
    source_acquisition_receipt = (
        layer3_sec_edgar_source_acquisition.read_sec_edgar_text_table_source_acquisition_receipt(
            _required(request, "source_acquisition_receipt_id"),
            expected_source_acquisition_receipt_hash=_required_hash(request, "source_acquisition_receipt_hash"),
        )
    )
    live_source_artifact = _live_source_artifact_authority(live_receipt)
    source_acquisition_artifact = _source_acquisition_artifact_authority(source_acquisition_receipt)
    mismatches = _source_artifact_mismatches(live_source_artifact, source_acquisition_artifact)
    if mismatches:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_source_artifact_mismatch",
            "SEC EDGAR live source-artifact material bridge requires the live receipt and source-acquisition receipt to bind the same source artifact authority.",
            http_status=409,
            blocked_fields=mismatches,
        )
    if str(source_acquisition_artifact.get("dataset_version_id") or "") != dataset_version_id:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_dataset_version_mismatch",
            "SEC EDGAR live source-artifact material bridge requires source-acquisition authority for the selected DatasetVersion.",
            http_status=409,
            blocked_fields=["dataset_version_id"],
        )
    if str(source_acquisition_artifact.get("authority_envelope_hash") or "") != authority_envelope_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_authority_envelope_mismatch",
            "SEC EDGAR live source-artifact material bridge requires matching authority envelope hash.",
            http_status=409,
            blocked_fields=["authority_envelope_hash"],
        )

    expected_materialization_hash = str(
        request.get("expected_materialization_receipt_hash")
        or source_acquisition_artifact.get("materialization_receipt_hash")
        or ""
    ).strip()
    material_bridge = layer3_sec_edgar_material_bridge.prepare_sec_edgar_text_table_material_authority_bridge(
        {
            "client_request_id": f"{request_id}:material-authority",
            "bridge_mode": EXISTING_MATERIAL_BRIDGE_MODE,
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": authority_envelope_hash,
            "expected_materialization_receipt_hash": expected_materialization_hash,
            "expected_material_preview_hash": str(request.get("expected_material_preview_hash") or "").strip()
            or None,
            "rollback_confirmed": True,
            "operator_confirmed": True,
            "actor": str(request.get("actor") or "operator").strip() or "operator",
        },
        db,
    )
    if material_bridge.get("bridge_state") != layer3_sec_edgar_material_bridge.READY_STATE:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            reasons=[
                _reason("material_authority_bridge_not_ready"),
                *list((material_bridge.get("status_projection") or {}).get("blocked_reasons") or []),
            ],
            live_source_artifact=live_source_artifact,
            source_acquisition_artifact=source_acquisition_artifact,
        )

    expected_gate_b_manifest = str(request.get("expected_gate_b_decision_manifest_id") or "").strip()
    if expected_gate_b_manifest and expected_gate_b_manifest != str(
        material_bridge.get("gate_b_decision_manifest_id") or ""
    ):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_gate_b_decision_basis_mismatch",
            "SEC EDGAR live source-artifact material bridge Gate B decision basis is stale or mismatched.",
            http_status=409,
            blocked_fields=["expected_gate_b_decision_manifest_id"],
        )

    receipt_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "bridge_mode": BRIDGE_MODE,
            "live_source_artifact_receipt_hash": live_receipt["live_source_artifact_receipt_hash"],
            "source_acquisition_receipt_hash": source_acquisition_receipt["source_acquisition_receipt_hash"],
            "source_artifact_receipt_hash": live_source_artifact["source_artifact_receipt_hash"],
            "source_artifact_ref_hash": live_source_artifact["source_artifact_ref_hash"],
            "content_sha256": live_source_artifact["content_sha256"],
            "dataset_version_id": dataset_version_id,
            "dataset_version_hash": source_acquisition_artifact["dataset_version_hash"],
            "materialization_receipt_hash": source_acquisition_artifact["materialization_receipt_hash"],
            "authority_envelope_hash": authority_envelope_hash,
            "material_preview_hash": material_bridge["material_preview_hash"],
            "gate_b_decision_manifest_id": material_bridge["gate_b_decision_manifest_id"],
            "material_bridge_receipt_hash": material_bridge["bridge_receipt_hash"],
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt_ref, idempotent_replay = _write_receipt(
        receipt_id=receipt_id,
        receipt_hash=receipt_hash,
        request_id=request_id,
        live_source_artifact=live_source_artifact,
        source_acquisition_artifact=source_acquisition_artifact,
        material_bridge=material_bridge,
    )
    response = {
        **_base_response(request_id=request_id, status="ready"),
        "mode": BRIDGE_MODE,
        "bridge_state": READY_STATE,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "bridge_receipt_ref": receipt_ref,
        "idempotent_replay": idempotent_replay,
        "dataset_version_id": dataset_version_id,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "live_acquisition_mode": LIVE_ACQUISITION_MODE,
        "source_acquisition_mode": SOURCE_ACQUISITION_MODE,
        "existing_material_bridge_mode": EXISTING_MATERIAL_BRIDGE_MODE,
        "live_source_artifact_receipt_id": live_receipt["live_source_artifact_receipt_id"],
        "live_source_artifact_receipt_hash": live_receipt["live_source_artifact_receipt_hash"],
        "source_acquisition_receipt_id": source_acquisition_receipt["source_acquisition_receipt_id"],
        "source_acquisition_receipt_hash": source_acquisition_receipt["source_acquisition_receipt_hash"],
        "source_artifact_authority": _redacted_source_artifact_authority(live_source_artifact),
        "material_authority_bridge": _material_bridge_summary(material_bridge),
        "material_preview_request_basis": material_bridge["material_preview_request_basis"],
        "material_preview_hash": material_bridge["material_preview_hash"],
        "gate_b_decision_manifest_id": material_bridge["gate_b_decision_manifest_id"],
        "gate_b_decision_payload": material_bridge["gate_b_decision_payload"],
        "authority_hashes": {
            "live_source_artifact_receipt_hash": live_receipt["live_source_artifact_receipt_hash"],
            "source_acquisition_receipt_hash": source_acquisition_receipt["source_acquisition_receipt_hash"],
            "source_artifact_receipt_hash": live_source_artifact["source_artifact_receipt_hash"],
            "source_artifact_ref_hash": live_source_artifact["source_artifact_ref_hash"],
            "content_sha256": live_source_artifact["content_sha256"],
            "dataset_version_hash": source_acquisition_artifact["dataset_version_hash"],
            "materialization_receipt_hash": source_acquisition_artifact["materialization_receipt_hash"],
            "authority_envelope_hash": authority_envelope_hash,
            "material_preview_hash": material_bridge["material_preview_hash"],
            "gate_b_decision_manifest_id": material_bridge["gate_b_decision_manifest_id"],
            "material_bridge_receipt_hash": material_bridge["bridge_receipt_hash"],
            "bridge_receipt_hash": receipt_hash,
        },
        "compatibility": {
            "live_source_artifact_receipt_bound": True,
            "source_acquisition_authority_reused": True,
            "material_authority_bridge_reused": True,
            "material_preview_schema_id": layer3_sec_edgar_material_bridge.MATERIAL_PREVIEW_SCHEMA_ID,
            "gate_b_decision_schema_id": layer3_sec_edgar_material_bridge.GATE_B_DECISION_SCHEMA_ID,
            "source_class": layer3_sec_edgar_material_bridge.SOURCE_CLASS,
            "direct_live_artifact_to_material_without_source_acquisition_admitted": False,
            "direct_raw_artifact_parse_or_materialization_admitted": False,
            "dataset_version_creation_admitted": False,
            "gate_b_mutation_admitted_in_bridge": False,
        },
        "operator_visible_status": {
            "selected_status_states": ["not_recorded", "ready", "blocked"],
            "redacted_receipt_available": True,
            "retained_source_artifact_available": True,
            "material_preview_gate_b_compatible": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_live_source_artifact_receipt_rejected": True,
            "stale_live_source_artifact_receipt_hash_rejected": True,
            "retained_artifact_content_hash_mismatch_rejected": True,
            "missing_source_acquisition_receipt_rejected": True,
            "source_acquisition_receipt_hash_mismatch_rejected": True,
            "source_artifact_receipt_hash_mismatch_rejected": True,
            "missing_materialization_linkage_rejected": True,
            "parser_contract_mismatch_rejected": True,
            "typed_content_contract_mismatch_rejected": True,
            "dataset_version_hash_mismatch_rejected": True,
            "authority_envelope_hash_mismatch_rejected": True,
            "material_preview_hash_mismatch_rejected": True,
            "gate_b_decision_basis_mismatch_rejected": True,
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
            "submit_sec_edgar_material_bridge_gate_b_decision_payload",
            "continue_sec_edgar_text_table_downstream_layer3_proof",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_raw_authority_exposed",
            "SEC EDGAR live source-artifact material bridge would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def read_sec_edgar_text_table_live_source_artifact_material_authority_bridge_receipt(
    bridge_receipt_id: str,
    *,
    expected_bridge_receipt_hash: str | None = None,
    live_source_artifact_receipt_hash: str | None = None,
    source_acquisition_receipt_hash: str | None = None,
) -> dict[str, Any]:
    receipt_id = str(bridge_receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if (
        not receipt_id.startswith(f"{RECEIPT_PREFIX}-")
        or len(suffix) != 24
        or any(ch not in "0123456789abcdefABCDEF" for ch in suffix)
    ):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_id_invalid",
            "SEC EDGAR live source-artifact material bridge receipt id is not admitted.",
            http_status=400,
            blocked_fields=["bridge_receipt_id"],
        )
    receipt = _read_receipt(_receipt_root() / f"{receipt_id}.json")
    if str(receipt.get("bridge_receipt_id") or "") != receipt_id:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_id_mismatch",
            "SEC EDGAR live source-artifact material bridge receipt id does not match its payload.",
            http_status=409,
            blocked_fields=["bridge_receipt_id"],
        )
    receipt_hash = str(receipt.get("bridge_receipt_hash") or "").strip()
    if not _is_hash(receipt_hash):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_hash_invalid",
            "SEC EDGAR live source-artifact material bridge receipt hash is invalid.",
            http_status=409,
            blocked_fields=["bridge_receipt_hash"],
        )
    expected_hash = str(expected_bridge_receipt_hash or "").strip()
    if expected_hash and receipt_hash != expected_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_hash_mismatch",
            "SEC EDGAR live source-artifact material bridge receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["bridge_receipt_hash"],
        )
    if live_source_artifact_receipt_hash or source_acquisition_receipt_hash:
        _verify_receipt_hash_payload(
            receipt,
            live_source_artifact_receipt_hash=str(live_source_artifact_receipt_hash or ""),
            source_acquisition_receipt_hash=str(source_acquisition_receipt_hash or ""),
        )
    return receipt


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in _FORBIDDEN_INPUT_KEYS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_forbidden_request_fields",
            "SEC EDGAR live source-artifact material bridge does not admit caller paths, URLs, bytes, commands, credentials, connector, model, browser, source-expansion, parser-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_unknown_field",
            "SEC EDGAR live source-artifact material bridge fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_schema_not_admitted",
            "SEC EDGAR live source-artifact material bridge requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    for key in (
        "live_source_artifact_receipt_hash",
        "source_acquisition_receipt_hash",
        "authority_envelope_hash",
        "expected_materialization_receipt_hash",
        "expected_material_preview_hash",
    ):
        value = str(request.get(key) or "").strip()
        if value and not _is_hash(value):
            _blocked(
                f"sec_edgar_text_table_live_source_artifact_material_bridge_{key}_invalid",
                f"SEC EDGAR live source-artifact material bridge requires a 64-character hash for {key}.",
                blocked_fields=[key],
            )
    return request


def _live_source_artifact_authority(receipt: Mapping[str, Any]) -> dict[str, Any]:
    source_artifact = receipt.get("source_artifact_receipt")
    source_identity = receipt.get("source_identity")
    if not isinstance(source_artifact, Mapping) or not isinstance(source_identity, Mapping):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_live_receipt_incomplete",
            "SEC EDGAR live source-artifact material bridge requires a complete live source-artifact receipt.",
            http_status=409,
        )
    return {
        "source_artifact_receipt_id": str(source_artifact.get("source_artifact_receipt_id") or ""),
        "source_artifact_receipt_hash": str(source_artifact.get("source_artifact_receipt_hash") or ""),
        "source_artifact_ref_hash": str(source_artifact.get("source_artifact_ref_hash") or ""),
        "content_sha256": str(source_artifact.get("content_sha256") or ""),
        "content_length": int(source_artifact.get("content_length") or 0),
        "accession_or_submission_id_hash": str(source_identity.get("accession_or_submission_id_hash") or ""),
        "cik_or_filer_ref_hash": str(source_identity.get("cik_or_filer_ref_hash") or ""),
        "form_type": str(source_identity.get("form_type") or ""),
        "filing_date": str(source_identity.get("filing_date") or ""),
        "parser_family": str(source_artifact.get("parser_family") or ""),
        "parser_contract_id": str(source_artifact.get("parser_contract_id") or ""),
        "typed_content_contract_id": str(source_artifact.get("typed_content_contract_id") or ""),
        "source_mode": str(source_artifact.get("source_mode") or ""),
        "source_artifact_family": LIVE_SOURCE_ARTIFACT_FAMILY,
    }


def _source_acquisition_artifact_authority(receipt: Mapping[str, Any]) -> dict[str, Any]:
    source_artifact = receipt.get("source_artifact_authority")
    if not isinstance(source_artifact, Mapping):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_source_acquisition_receipt_incomplete",
            "SEC EDGAR live source-artifact material bridge requires source-acquisition source-artifact authority.",
            http_status=409,
        )
    return dict(source_artifact)


def _source_artifact_mismatches(
    live_source_artifact: Mapping[str, Any],
    source_acquisition_artifact: Mapping[str, Any],
) -> list[str]:
    fields = (
        "source_artifact_receipt_id",
        "source_artifact_receipt_hash",
        "source_artifact_ref_hash",
        "content_sha256",
        "accession_or_submission_id_hash",
        "cik_or_filer_ref_hash",
        "form_type",
        "filing_date",
        "parser_family",
        "parser_contract_id",
        "typed_content_contract_id",
        "source_mode",
    )
    mismatches = [
        field
        for field in fields
        if str(live_source_artifact.get(field) or "")
        != str(source_acquisition_artifact.get(field) or "")
    ]
    if int(live_source_artifact.get("content_length") or 0) != int(
        source_acquisition_artifact.get("content_length") or 0
    ):
        mismatches.append("content_length")
    return mismatches


def _redacted_source_artifact_authority(source_artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_artifact_receipt_id": str(source_artifact.get("source_artifact_receipt_id") or ""),
        "source_artifact_receipt_hash": str(source_artifact.get("source_artifact_receipt_hash") or ""),
        "source_artifact_ref_hash": str(source_artifact.get("source_artifact_ref_hash") or ""),
        "content_sha256": str(source_artifact.get("content_sha256") or ""),
        "content_length": int(source_artifact.get("content_length") or 0),
        "accession_or_submission_id_hash": str(source_artifact.get("accession_or_submission_id_hash") or ""),
        "cik_or_filer_ref_hash": str(source_artifact.get("cik_or_filer_ref_hash") or ""),
        "form_type": str(source_artifact.get("form_type") or ""),
        "filing_date": str(source_artifact.get("filing_date") or ""),
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "source_artifact_family": LIVE_SOURCE_ARTIFACT_FAMILY,
        "server_owned_source_artifact_authority": True,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }


def _material_bridge_summary(material_bridge: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bridge_state": material_bridge.get("bridge_state"),
        "bridge_receipt_id": material_bridge.get("bridge_receipt_id"),
        "bridge_receipt_hash": material_bridge.get("bridge_receipt_hash"),
        "dataset_version_id": material_bridge.get("dataset_version_id"),
        "authority_envelope_hash": material_bridge.get("authority_envelope_hash"),
        "materialization_receipt_hash": material_bridge.get("materialization_receipt_hash"),
        "material_preview_hash": material_bridge.get("material_preview_hash"),
        "gate_b_decision_manifest_id": material_bridge.get("gate_b_decision_manifest_id"),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }


def _write_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    live_source_artifact: Mapping[str, Any],
    source_acquisition_artifact: Mapping[str, Any],
    material_bridge: Mapping[str, Any],
) -> tuple[str, bool]:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "bridge_mode": BRIDGE_MODE,
        "bridge_state": READY_STATE,
        "request_id_hash": stable_hash(
            {
                "hash_version": "sec_edgar_live_source_artifact_material_bridge_request_hash_v1",
                "client_request_id": request_id,
            }
        ),
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "live_source_artifact_authority": _redacted_source_artifact_authority(live_source_artifact),
        "source_acquisition_authority": {
            "dataset_version_id": source_acquisition_artifact.get("dataset_version_id"),
            "dataset_version_hash": source_acquisition_artifact.get("dataset_version_hash"),
            "materialization_receipt_hash": source_acquisition_artifact.get("materialization_receipt_hash"),
            "authority_envelope_hash": source_acquisition_artifact.get("authority_envelope_hash"),
            "source_artifact_receipt_hash": source_acquisition_artifact.get("source_artifact_receipt_hash"),
        },
        "material_authority_bridge": _material_bridge_summary(material_bridge),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "recorded_at": _server_time(),
    }
    target = _receipt_root() / f"{receipt_id}.json"
    if target.exists():
        existing = _read_receipt(target)
        if existing.get("bridge_receipt_hash") != receipt_hash:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_conflict",
                "A SEC EDGAR live source-artifact material bridge receipt already exists for this authority.",
                http_status=409,
            )
        return f"{RECEIPT_PREFIX}:{receipt_hash[:24]}", True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_receipt(target)
        if existing.get("bridge_receipt_hash") != receipt_hash:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_conflict",
                "A SEC EDGAR live source-artifact material bridge receipt already exists for this authority.",
                http_status=409,
            )
        return f"{RECEIPT_PREFIX}:{receipt_hash[:24]}", True
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_write_failed",
            "SEC EDGAR live source-artifact material bridge receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    return f"{RECEIPT_PREFIX}:{receipt_hash[:24]}", False


def _verify_receipt_hash_payload(
    receipt: Mapping[str, Any],
    *,
    live_source_artifact_receipt_hash: str,
    source_acquisition_receipt_hash: str,
) -> None:
    if not _is_hash(live_source_artifact_receipt_hash) or not _is_hash(source_acquisition_receipt_hash):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_binding_hash_missing",
            "SEC EDGAR live source-artifact material bridge receipt hash verification requires live and source-acquisition receipt hashes.",
            http_status=400,
            blocked_fields=["live_source_artifact_receipt_hash", "source_acquisition_receipt_hash"],
        )
    live_authority = receipt.get("live_source_artifact_authority")
    source_authority = receipt.get("source_acquisition_authority")
    material_bridge = receipt.get("material_authority_bridge")
    if not isinstance(live_authority, Mapping) or not isinstance(source_authority, Mapping):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_authority_missing",
            "SEC EDGAR live source-artifact material bridge receipt is missing live/source authority.",
            http_status=409,
        )
    if not isinstance(material_bridge, Mapping):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_material_bridge_missing",
            "SEC EDGAR live source-artifact material bridge receipt is missing material bridge authority.",
            http_status=409,
        )
    recomputed = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "bridge_mode": BRIDGE_MODE,
            "live_source_artifact_receipt_hash": live_source_artifact_receipt_hash,
            "source_acquisition_receipt_hash": source_acquisition_receipt_hash,
            "source_artifact_receipt_hash": str(live_authority.get("source_artifact_receipt_hash") or ""),
            "source_artifact_ref_hash": str(live_authority.get("source_artifact_ref_hash") or ""),
            "content_sha256": str(live_authority.get("content_sha256") or ""),
            "dataset_version_id": str(source_authority.get("dataset_version_id") or ""),
            "dataset_version_hash": str(source_authority.get("dataset_version_hash") or ""),
            "materialization_receipt_hash": str(source_authority.get("materialization_receipt_hash") or ""),
            "authority_envelope_hash": str(source_authority.get("authority_envelope_hash") or ""),
            "material_preview_hash": str(material_bridge.get("material_preview_hash") or ""),
            "gate_b_decision_manifest_id": str(material_bridge.get("gate_b_decision_manifest_id") or ""),
            "material_bridge_receipt_hash": str(material_bridge.get("bridge_receipt_hash") or ""),
        }
    )
    if recomputed != str(receipt.get("bridge_receipt_hash") or ""):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_hash_invalid",
            "SEC EDGAR live source-artifact material bridge receipt payload no longer matches its hash.",
            http_status=409,
            blocked_fields=["bridge_receipt_hash"],
        )


def _read_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_missing",
            "SEC EDGAR live source-artifact material bridge receipt was not found.",
            http_status=404,
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_unreadable",
            "SEC EDGAR live source-artifact material bridge receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_receipt_invalid",
            "SEC EDGAR live source-artifact material bridge receipts must be JSON objects.",
            http_status=409,
        )
    return receipt


def _receipt_root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_storage_root_unavailable",
            "SEC EDGAR live source-artifact material bridge requires the existing Layer 3 storage root for append-only receipts.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _blocked_response(
    *,
    request_id: str,
    dataset_version_id: str,
    authority_envelope_hash: str,
    reasons: list[dict[str, Any]],
    live_source_artifact: Mapping[str, Any] | None = None,
    source_acquisition_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked"),
        "mode": BRIDGE_MODE,
        "bridge_state": BLOCKED_STATE,
        "dataset_version_id": dataset_version_id,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "authority_envelope_hash": authority_envelope_hash,
        "live_source_artifact_receipt_hash": (
            live_source_artifact.get("source_artifact_receipt_hash")
            if isinstance(live_source_artifact, Mapping)
            else None
        ),
        "source_acquisition_dataset_version_hash": (
            source_acquisition_artifact.get("dataset_version_hash")
            if isinstance(source_acquisition_artifact, Mapping)
            else None
        ),
        "material_preview_request_basis": None,
        "material_preview_hash": None,
        "gate_b_decision_manifest_id": None,
        "status_projection": {
            "ready": False,
            "blocked_reasons": reasons,
            "next_allowed_actions": [
                "refresh_live_source_artifact_receipt",
                "refresh_source_acquisition_authority_receipt",
                "refresh_sec_edgar_text_table_authority_envelope",
            ],
        },
        "negative_invariants": _negative_invariants(),
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_material_bridge_blocked_response_raw_authority_exposed",
            "SEC EDGAR live source-artifact material bridge blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _base_response(*, request_id: str, status: str) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": status,
    }


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_text_table_live_source_artifact_material_bridge_{key}_missing",
            f"SEC EDGAR live source-artifact material bridge requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_text_table_live_source_artifact_material_bridge_{key}_invalid",
            f"SEC EDGAR live source-artifact material bridge requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    received = str(fields.get(key) or "").strip()
    if received != expected:
        _blocked(
            f"sec_edgar_text_table_live_source_artifact_material_bridge_{key}_mismatch",
            f"SEC EDGAR live source-artifact material bridge requires {key}={expected}.",
            blocked_fields=[key],
        )


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=_FORBIDDEN_INPUT_KEYS, prefix=prefix)


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        return contains_forbidden_ref(value)
    return False


def _is_hash(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _negative_invariants() -> dict[str, bool]:
    return {
        "live_sec_network_fetch_admitted_for_bridge": False,
        "sec_network_cache_or_rate_behavior_admitted_for_bridge": False,
        "raw_sec_filing_url_as_authority_admitted_for_bridge": False,
        "sec_edgar_parser_expansion_admitted": False,
        "xml_html_inline_xbrl_admitted": False,
        "direct_raw_artifact_parse_or_materialization_admitted": False,
        "dataset_version_creation_admitted": False,
        "gate_b_mutation_admitted_in_bridge": False,
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
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_local_path_admitted": False,
        "browser_supplied_artifact_bytes_admitted": False,
        "browser_supplied_command_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "provider_token_exposed": False,
    }
