from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import DatasetSourceProvenance, DatasetVersion
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_xbrl_sidecar,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_arelle_value_reveal.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_arelle_value_reveal_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_arelle_value_reveal_status.v1"
SCHEMA_VERSION = 1
REVEAL_MODE = "sec_edgar_arelle_governed_value_reveal_v1"
READY_STATE = "sec_edgar_arelle_value_reveal_ready"
BLOCKED_STATE = "sec_edgar_arelle_value_reveal_blocked"
RECEIPT_PREFIX = "sec-edgar-arelle-value-reveal"
RECEIPT_DIR = "layer3-sec-edgar-arelle-value-reveal"
REDACTION_POLICY_ID = "sec_edgar_arelle_value_reveal_redaction_v1"
VALUE_SEMANTICS_ID = "arelle_effective_canonical_value_v1"
VALUE_REVEAL_POLICY_ID = "sec_edgar_arelle_governed_value_reveal_v1"
VALUE_REVEAL_SCOPE = "resolved_fact_authority_bound_filing_values_with_identity_redaction"
CURRENT_RECEIPT_HASH_BASIS = "post_1966_value_reveal_receipt_hash_basis_v2"
LEGACY_RECEIPT_HASH_BASIS = "pre_1966_value_reveal_receipt_hash_basis_v1"
LEGACY_VALUE_REVEAL_POLICY_ID = "legacy_pre_1966_policy_not_recorded"
LEGACY_VALUE_REVEAL_SCOPE = "legacy_pre_1966_scope_not_recorded"

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "actor",
    "operator_reveal_confirmation",
    "sidecar_receipt_id",
    "sidecar_receipt_hash",
    "dataset_version_id",
    "dataset_version_hash",
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
    "cik",
    "company_name",
    "ticker",
    "contact",
    "user_agent",
    "source_bytes",
}

_FORBIDDEN_OUTPUT_KEYS = {
    "actor",
    "raw_url",
    "source_url",
    "filing_url",
    "provider_url",
    "connector_url",
    "download_url",
    "public_url",
    "signed_url",
    "raw_path",
    "local_path",
    "storage_dir",
    "storage_root",
    "accession",
    "accession_number",
    "cik",
    "ticker",
    "company_name",
    "contact",
    "user_agent",
}
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_IDENTITY_VALUE_CONCEPT_MARKERS = (
    "registrant",
    "companyname",
    "entityname",
    "trading",
    "ticker",
    "symbol",
    "centralindexkey",
    "taxidentification",
    "address",
    "phone",
    "telephone",
    "email",
    "contact",
    "website",
    "webaddress",
    "url",
)


def reveal_sec_edgar_arelle_values(fields: Mapping[str, Any], db: Session) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = str(request.get("client_request_id") or "sec-edgar-arelle-value-reveal-blocked")
    if not settings.layer3_sec_edgar_arelle_value_reveal_enabled:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_arelle_value_reveal_feature_flag_disabled")],
        )
    schema_id = str(request.get("schema_id") or "").strip()
    if schema_id != REQUEST_SCHEMA_ID:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_arelle_value_reveal_schema_id_required", blocked_fields=["schema_id"])],
        )
    request_id = _required(request, "client_request_id")
    actor = _required(request, "actor")
    if request.get("operator_reveal_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    "sec_edgar_arelle_value_reveal_operator_confirmation_required",
                    blocked_fields=["operator_reveal_confirmation"],
                )
            ],
        )
    sidecar_receipt_id = _required(request, "sidecar_receipt_id")
    sidecar_receipt_hash = _required_hash(request, "sidecar_receipt_hash")
    dataset_version_id = _required(request, "dataset_version_id")
    dataset_version_hash = _required_hash(request, "dataset_version_hash")

    sidecar = _read_sidecar(sidecar_receipt_id, sidecar_receipt_hash)
    if sidecar.get("blocked_reasons"):
        return _blocked_response(request_id=request_id, reasons=list(sidecar["blocked_reasons"]))
    if sidecar.get("sidecar_state") != layer3_sec_xbrl_sidecar.READY_STATE:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_arelle_value_reveal_sidecar_not_ready")],
        )
    try:
        value_store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(
            sidecar
        )
    except Layer3WorkbenchError as exc:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason(exc.error_code, message=exc.message, blocked_fields=list(exc.blocked_fields))],
        )

    dataset_context = _dataset_context(db, dataset_version_id, dataset_version_hash)
    if dataset_context.get("blocked_reasons"):
        return _blocked_response(request_id=request_id, reasons=list(dataset_context["blocked_reasons"]))
    bridge_response = dict(dataset_context["bridge_response"])
    lineage_mismatches = _lineage_mismatches(sidecar, bridge_response, dataset_version_id, dataset_version_hash)
    if lineage_mismatches:
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    "sec_edgar_arelle_value_reveal_lineage_mismatch",
                    blocked_fields=lineage_mismatches,
                )
            ],
        )

    reveal_records = _reveal_records(sidecar, value_store, dataset_version_hash=dataset_version_hash)
    if not reveal_records:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_arelle_value_reveal_no_resolved_values")],
        )
    audit_receipt = _audit_receipt(
        request_id=request_id,
        actor=actor,
        sidecar=sidecar,
        bridge_response=bridge_response,
        dataset_version_hash=dataset_version_hash,
        reveal_records=reveal_records,
    )
    prospective_response = _ready_response(
        request_id=request_id,
        receipt=audit_receipt,
        reveal_records=reveal_records,
        idempotent_replay=False,
    )
    if _projection_has_redaction_violation(prospective_response):
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_arelle_value_reveal_response_redaction_violation")],
        )
    try:
        persisted = _write_receipt(audit_receipt)
    except Layer3WorkbenchError as exc:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason(exc.error_code, message=exc.message, blocked_fields=list(exc.blocked_fields))],
        )
    response = _ready_response(
        request_id=request_id,
        receipt=persisted["receipt"],
        reveal_records=reveal_records,
        idempotent_replay=bool(persisted["idempotent_replay"]),
    )
    if _projection_has_redaction_violation(response):
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_arelle_value_reveal_response_redaction_violation")],
        )
    return response


def inspect_sec_edgar_arelle_value_reveal_status(reveal_receipt_id: str) -> dict[str, Any]:
    if not settings.layer3_sec_edgar_arelle_value_reveal_enabled:
        return _blocked_response(
            request_id=f"sec-edgar-arelle-value-reveal-status-{_sha256_text(reveal_receipt_id)[:12]}",
            reasons=[_reason("sec_edgar_arelle_value_reveal_feature_flag_disabled")],
        )
    receipt = _read_verified_receipt(reveal_receipt_id)
    return {
        **base_response(
            STATUS_SCHEMA_ID,
            request_id=f"sec-edgar-arelle-value-reveal-status-{receipt['reveal_receipt_hash'][:12]}",
            status="ready",
        ),
        "reveal_mode": REVEAL_MODE,
        "reveal_state": READY_STATE,
        **_receipt_projection(receipt),
        "revealed_fact_count": 0,
        "revealed_facts": [],
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "raw_values_returned": False,
            "raw_identity_returned": False,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
    }


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in FORBIDDEN_REQUEST_FIELDS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_arelle_value_reveal_forbidden_request_fields",
            "SEC EDGAR Arelle value reveal rejects caller paths, URLs, bytes, credentials, identity, raw provider fields, connector dispatch, source expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_arelle_value_reveal_unknown_field",
            "SEC EDGAR Arelle value reveal fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    return request


def _read_sidecar(receipt_id: str, receipt_hash: str) -> dict[str, Any]:
    try:
        return layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
            receipt_id,
            expected_sidecar_receipt_hash=receipt_hash,
        )
    except Layer3WorkbenchError as exc:
        return {
            "blocked_reasons": [
                _reason(exc.error_code, message=exc.message, blocked_fields=list(exc.blocked_fields))
            ]
        }


def _dataset_context(db: Session, dataset_version_id: str, dataset_version_hash: str) -> dict[str, Any]:
    version = db.get(DatasetVersion, dataset_version_id)
    if version is None:
        return {"blocked_reasons": [_reason("sec_edgar_arelle_value_reveal_dataset_version_missing")]}
    if version.status != "ready":
        return {"blocked_reasons": [_reason("sec_edgar_arelle_value_reveal_dataset_version_not_ready")]}
    provenance = (
        db.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .first()
    )
    if provenance is None:
        return {"blocked_reasons": [_reason("sec_edgar_arelle_value_reveal_dataset_provenance_missing")]}
    source_reference = provenance.source_reference_json if isinstance(provenance.source_reference_json, Mapping) else {}
    if str(source_reference.get("dataset_version_hash") or "") != dataset_version_hash:
        return {
            "blocked_reasons": [
                _reason(
                    "sec_edgar_arelle_value_reveal_dataset_version_hash_mismatch",
                    blocked_fields=["dataset_version_hash"],
                )
            ]
        }
    bridge_response = _bridge_response_for_dataset(dataset_version_id, dataset_version_hash)
    if bridge_response is None:
        return {"blocked_reasons": [_reason("sec_edgar_arelle_value_reveal_dataset_bridge_receipt_missing")]}
    return {"version": version, "provenance": provenance, "bridge_response": bridge_response}


def _bridge_response_for_dataset(dataset_version_id: str, dataset_version_hash: str) -> dict[str, Any] | None:
    receipts_dir = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge._root() / "receipts"
    if not receipts_dir.exists():
        return None
    for path in sorted(receipts_dir.glob(f"{layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.RECEIPT_PREFIX}-*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        response = receipt.get("response") if isinstance(receipt, Mapping) else None
        if not isinstance(response, Mapping):
            continue
        if str(response.get("dataset_version_id") or "") == dataset_version_id:
            if str(response.get("dataset_version_hash") or "") == dataset_version_hash:
                return dict(response)
            return {
                "dataset_version_id": dataset_version_id,
                "dataset_version_hash_mismatch": True,
            }
    return None


def _lineage_mismatches(
    sidecar: Mapping[str, Any],
    bridge_response: Mapping[str, Any],
    dataset_version_id: str,
    dataset_version_hash: str,
) -> list[str]:
    mismatches: list[str] = []
    if bridge_response.get("dataset_version_hash_mismatch"):
        return ["dataset_version_hash"]
    if str(bridge_response.get("dataset_version_id") or "") != dataset_version_id:
        mismatches.append("dataset_version_id")
    if str(bridge_response.get("dataset_version_hash") or "") != dataset_version_hash:
        mismatches.append("dataset_version_hash")
    if (
        str(bridge_response.get("fact_authority_input_mode") or "")
        != layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.ARELLE_FACT_AUTHORITY_INPUT_MODE
    ):
        mismatches.append("fact_authority_input_mode")
    if str(bridge_response.get("arelle_sidecar_receipt_hash") or "") != str(sidecar.get("sidecar_receipt_hash") or ""):
        mismatches.append("arelle_sidecar_receipt_hash")
    authority_hashes = bridge_response.get("authority_hashes") if isinstance(bridge_response.get("authority_hashes"), Mapping) else {}
    for key in (
        "parser_receipt_hash",
        "connector_receipt_hash",
        "live_source_artifact_receipt_hash",
        "source_artifact_receipt_hash",
        "content_sha256",
        "primary_document_hash",
        "document_inventory_hash",
        "content_order_hash",
        "table_candidate_inventory_hash",
        "inline_xbrl_marker_inventory_hash",
    ):
        bridge_value = str(bridge_response.get(key) or authority_hashes.get(key) or "")
        sidecar_value = str(sidecar.get(key) or "")
        if bridge_value != sidecar_value:
            mismatches.append(key)
    materialization = bridge_response.get("materialization_summary")
    if isinstance(materialization, Mapping):
        if int(materialization.get("fact_count") or -1) != int(sidecar.get("resolved_fact_count") or -2):
            mismatches.append("resolved_fact_count")
    return sorted(set(mismatches))


def _reveal_records(
    sidecar: Mapping[str, Any],
    value_store: Mapping[str, Any],
    *,
    dataset_version_hash: str,
) -> list[dict[str, Any]]:
    records = [item for item in list(sidecar.get("resolved_fact_records") or []) if isinstance(item, Mapping)]
    value_records = [item for item in list(value_store.get("value_records") or []) if isinstance(item, Mapping)]
    values_by_id = {str(item.get("resolved_fact_id") or ""): item for item in value_records}
    reveal_records: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        resolved_fact_id = str(record.get("resolved_fact_id") or "")
        value_record = values_by_id.get(resolved_fact_id)
        if value_record is None:
            continue
        concept = dict(record.get("concept") or {})
        period = dict(record.get("period") or {})
        unit = dict(record.get("unit") or {})
        dimensions = dict(record.get("dimensions") or {})
        transform = dict(value_record.get("transform") or {})
        value_hash = str(value_record.get("effective_value_hash") or record.get("value_hash") or "")
        redact_value = _value_requires_identity_redaction(record, value_record)
        reveal_records.append(
            {
                "fact_identity_hash": stable_hash(
                    {
                        "sidecar_receipt_hash": sidecar["sidecar_receipt_hash"],
                        "dataset_version_hash": dataset_version_hash,
                        "resolved_fact_id": resolved_fact_id,
                        "source_order": record.get("source_order"),
                        "entry_document_index": record.get("entry_document_index"),
                    }
                ),
                "resolved_fact_id_hash": stable_hash({"resolved_fact_id": resolved_fact_id}),
                "source_order": int(record.get("source_order") or index),
                "entry_document_index": int(record.get("entry_document_index") or 1),
                "effective_value": "" if redact_value else str(value_record.get("effective_value") or ""),
                "lexical_value": "" if redact_value else str(value_record.get("lexical_value") or ""),
                "value_redacted": redact_value,
                "value_redaction_reason": (
                    "sec_edgar_arelle_value_reveal_raw_identity_value_redacted" if redact_value else None
                ),
                "value_hash": value_hash,
                "value_semantics": str(value_record.get("value_semantics") or VALUE_SEMANTICS_ID),
                "transform_inputs": {
                    "sign": str(transform.get("sign") or record.get("sign") or ""),
                    "scale": str(transform.get("scale") or record.get("scale") or ""),
                    "decimals": str(transform.get("decimals") or record.get("decimals") or ""),
                    "precision": str(transform.get("precision") or record.get("precision") or ""),
                    "format": str(transform.get("format") or record.get("format") or ""),
                },
                "period": {
                    "type": str(period.get("type") or ""),
                    "start": str(period.get("start") or ""),
                    "end": str(period.get("end") or ""),
                    "instant": str(period.get("instant") or ""),
                    "forever": bool(period.get("forever")),
                    "resolved": bool(period.get("resolved")),
                },
                "unit": {
                    "currency": str(unit.get("currency") or ""),
                    "measures": list(unit.get("measures") or []),
                    "numerator": list(unit.get("numerator") or []),
                    "denominator": list(unit.get("denominator") or []),
                    "resolved": bool(unit.get("resolved")),
                },
                "dimensions": {
                    "explicit": list(dimensions.get("explicit") or []),
                    "typed": list(dimensions.get("typed") or []),
                },
                "concept": {
                    "qname": str(concept.get("qname") or ""),
                    "namespace": str(concept.get("namespace") or ""),
                    "local_name": str(concept.get("local_name") or ""),
                    "standard": bool(concept.get("standard")),
                    "extension": bool(concept.get("extension")),
                    "resolved_from_dts": bool(concept.get("resolved_from_dts")),
                },
                "hidden": bool(record.get("hidden")),
                "continued": bool(record.get("continued")),
            }
        )
    return reveal_records


def _value_requires_identity_redaction(record: Mapping[str, Any], value_record: Mapping[str, Any]) -> bool:
    concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
    concept_text = " ".join(
        str(concept.get(key) or "")
        for key in ("qname", "namespace", "local_name")
    ).lower()
    if any(marker in concept_text for marker in _IDENTITY_VALUE_CONCEPT_MARKERS):
        return True
    value_text = " ".join(
        str(value_record.get(key) or "")
        for key in ("effective_value", "lexical_value")
    ).lower()
    if "@" in value_text or "www." in value_text or "http://" in value_text or "https://" in value_text:
        return True
    return False


def _audit_receipt(
    *,
    request_id: str,
    actor: str,
    sidecar: Mapping[str, Any],
    bridge_response: Mapping[str, Any],
    dataset_version_hash: str,
    reveal_records: list[dict[str, Any]],
) -> dict[str, Any]:
    fact_identity_hashes = [str(record["fact_identity_hash"]) for record in reveal_records]
    value_hashes = [str(record.get("value_hash") or "") for record in reveal_records]
    fact_inventory_hash = stable_hash(fact_identity_hashes)
    value_inventory_hash = stable_hash(value_hashes)
    client_request_id_hash = _sha256_text(request_id)
    actor_hash = _sha256_text(actor)
    idempotency_key_hash = stable_hash(
        {
            "client_request_id_hash": client_request_id_hash,
            "sidecar_receipt_hash": sidecar["sidecar_receipt_hash"],
            "dataset_version_hash": dataset_version_hash,
            "actor_hash": actor_hash,
        }
    )
    receipt_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "client_request_id_hash": client_request_id_hash,
            "idempotency_key_hash": idempotency_key_hash,
            "sidecar_receipt_hash": sidecar["sidecar_receipt_hash"],
            "dataset_version_hash": dataset_version_hash,
            "actor_hash": actor_hash,
            "fact_count": len(reveal_records),
            "fact_inventory_hash": fact_inventory_hash,
            "value_inventory_hash": value_inventory_hash,
            "value_reveal_policy_id": VALUE_REVEAL_POLICY_ID,
            "value_reveal_scope": VALUE_REVEAL_SCOPE,
            "value_semantics": VALUE_SEMANTICS_ID,
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )
    authority_hashes = bridge_response.get("authority_hashes") if isinstance(bridge_response.get("authority_hashes"), Mapping) else {}
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "reveal_mode": REVEAL_MODE,
        "reveal_state": READY_STATE,
        "reveal_receipt_id": f"{RECEIPT_PREFIX}-{receipt_hash[:24]}",
        "reveal_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "reveal_receipt_hash": receipt_hash,
        "client_request_id_hash": client_request_id_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "actor_hash": actor_hash,
        "server_time": _server_time(),
        "sidecar_receipt_id": sidecar["sidecar_receipt_id"],
        "sidecar_receipt_hash": sidecar["sidecar_receipt_hash"],
        "dataset_version_id": bridge_response["dataset_version_id"],
        "dataset_version_hash": dataset_version_hash,
        "lineage_hashes": {
            "sidecar_receipt_hash": sidecar["sidecar_receipt_hash"],
            "dataset_version_hash": dataset_version_hash,
            "parser_receipt_hash": sidecar["parser_receipt_hash"],
            "connector_receipt_hash": sidecar["connector_receipt_hash"],
            "live_source_artifact_receipt_hash": sidecar["live_source_artifact_receipt_hash"],
            "source_artifact_receipt_hash": sidecar["source_artifact_receipt_hash"],
            "primary_document_hash": sidecar["primary_document_hash"],
            "content_sha256": sidecar["content_sha256"],
            "fact_material_bridge_receipt_hash": authority_hashes.get("fact_material_bridge_receipt_hash")
            or bridge_response.get("fact_material_bridge_receipt_hash"),
        },
        "fact_count": len(reveal_records),
        "fact_inventory_hash": fact_inventory_hash,
        "value_inventory_hash": value_inventory_hash,
        "value_reveal_policy_id": VALUE_REVEAL_POLICY_ID,
        "value_reveal_scope": VALUE_REVEAL_SCOPE,
        "value_semantics": VALUE_SEMANTICS_ID,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "raw_values_persisted_in_audit_receipt": False,
        "raw_identity_persisted_in_audit_receipt": False,
    }


def _ready_response(
    *,
    request_id: str,
    receipt: Mapping[str, Any],
    reveal_records: list[dict[str, Any]],
    idempotent_replay: bool,
) -> dict[str, Any]:
    return {
        **base_response(SCHEMA_ID, request_id=request_id, status="ready"),
        "reveal_mode": REVEAL_MODE,
        "reveal_state": READY_STATE,
        **_receipt_projection(receipt),
        "idempotent_replay": idempotent_replay,
        "revealed_fact_count": len(reveal_records),
        "revealed_facts": reveal_records,
        "status_projection": {
            "ready": True,
            "redacted_projection": False,
            "raw_values_returned": True,
            "raw_identity_returned": False,
            "audit_receipt_raw_values_persisted": False,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "inspect_sec_edgar_arelle_value_reveal_audit_receipt",
        ],
    }


def _receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    receipt_hash_basis = _receipt_hash_basis_id(receipt)
    value_reveal_policy_id = str(receipt.get("value_reveal_policy_id") or LEGACY_VALUE_REVEAL_POLICY_ID)
    value_reveal_scope = str(receipt.get("value_reveal_scope") or LEGACY_VALUE_REVEAL_SCOPE)
    return {
        "reveal_receipt_id": receipt["reveal_receipt_id"],
        "reveal_receipt_ref": receipt["reveal_receipt_ref"],
        "reveal_receipt_hash": receipt["reveal_receipt_hash"],
        "receipt_hash_basis": receipt_hash_basis,
        "actor_hash": receipt["actor_hash"],
        "audit_server_time": receipt["server_time"],
        "sidecar_receipt_id": receipt["sidecar_receipt_id"],
        "sidecar_receipt_hash": receipt["sidecar_receipt_hash"],
        "dataset_version_id": receipt["dataset_version_id"],
        "dataset_version_hash": receipt["dataset_version_hash"],
        "lineage_hashes": dict(receipt["lineage_hashes"]),
        "fact_count": receipt["fact_count"],
        "fact_inventory_hash": receipt["fact_inventory_hash"],
        "value_inventory_hash": receipt["value_inventory_hash"],
        "value_reveal_policy_id": value_reveal_policy_id,
        "value_reveal_scope": value_reveal_scope,
        "value_semantics": receipt["value_semantics"],
        "audit_receipt": {
            "schema_id": receipt["schema_id"],
            "reveal_receipt_id": receipt["reveal_receipt_id"],
            "reveal_receipt_hash": receipt["reveal_receipt_hash"],
            "receipt_hash_basis": receipt_hash_basis,
            "actor_hash": receipt["actor_hash"],
            "server_time": receipt["server_time"],
            "lineage_hashes": dict(receipt["lineage_hashes"]),
            "fact_count": receipt["fact_count"],
            "fact_inventory_hash": receipt["fact_inventory_hash"],
            "value_inventory_hash": receipt["value_inventory_hash"],
            "value_reveal_policy_id": value_reveal_policy_id,
            "value_reveal_scope": value_reveal_scope,
            "redaction_policy_id": receipt["redaction_policy_id"],
            "raw_values_persisted": False,
            "raw_identity_persisted": False,
        },
    }


def _write_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    target = _receipt_path(str(receipt["reveal_receipt_id"]))
    if target.exists():
        existing = _read_verified_receipt(str(receipt["reveal_receipt_id"]))
        if existing["reveal_receipt_hash"] != receipt["reveal_receipt_hash"]:
            _blocked(
                "sec_edgar_arelle_value_reveal_receipt_conflict",
                "SEC EDGAR Arelle value reveal receipt conflicts with existing authority.",
                http_status=409,
                blocked_fields=["reveal_receipt_hash"],
            )
        return {"receipt": existing, "idempotent_replay": True}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_verified_receipt(str(receipt["reveal_receipt_id"]))
        return {"receipt": existing, "idempotent_replay": True}
    except OSError as exc:
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_write_failed",
            "SEC EDGAR Arelle value reveal receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    return {"receipt": dict(receipt), "idempotent_replay": False}


def _read_verified_receipt(reveal_receipt_id: str) -> dict[str, Any]:
    receipt_id = str(reveal_receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_id_invalid",
            "SEC EDGAR Arelle value reveal status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["reveal_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_missing",
            "SEC EDGAR Arelle value reveal receipt was not found.",
            http_status=404,
            blocked_fields=["reveal_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_unreadable",
            "SEC EDGAR Arelle value reveal receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("reveal_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_invalid",
            "SEC EDGAR Arelle value reveal receipt is invalid.",
            http_status=409,
        )
    _validate_receipt_hash_binding(receipt_id, receipt)
    return receipt


def _validate_receipt_hash_binding(receipt_id: str, receipt: Mapping[str, Any]) -> None:
    receipt_hash = str(receipt.get("reveal_receipt_hash") or "")
    if not _is_hash(receipt_hash):
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_hash_invalid",
            "SEC EDGAR Arelle value reveal receipt hash is invalid.",
            http_status=409,
        )
    expected_hash = _receipt_hash_basis(receipt)
    if receipt_hash != expected_hash:
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_hash_mismatch",
            "SEC EDGAR Arelle value reveal receipt hash does not match the persisted receipt basis.",
            http_status=409,
            blocked_fields=["reveal_receipt_hash"],
        )
    if not receipt_id.endswith(expected_hash[:24]):
        _blocked(
            "sec_edgar_arelle_value_reveal_receipt_id_hash_mismatch",
            "SEC EDGAR Arelle value reveal receipt id is not bound to the persisted receipt hash.",
            http_status=409,
            blocked_fields=["reveal_receipt_id", "reveal_receipt_hash"],
        )


def _receipt_hash_basis(receipt: Mapping[str, Any]) -> str:
    if _receipt_hash_basis_id(receipt) == LEGACY_RECEIPT_HASH_BASIS:
        return _legacy_receipt_hash_basis(receipt)
    return _current_receipt_hash_basis(receipt)


def _receipt_hash_basis_id(receipt: Mapping[str, Any]) -> str:
    legacy_only_fields_missing = all(
        not receipt.get(key)
        for key in ("idempotency_key_hash", "value_reveal_policy_id", "value_reveal_scope")
    )
    return LEGACY_RECEIPT_HASH_BASIS if legacy_only_fields_missing else CURRENT_RECEIPT_HASH_BASIS


def _current_receipt_hash_basis(receipt: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "client_request_id_hash": receipt.get("client_request_id_hash"),
            "idempotency_key_hash": receipt.get("idempotency_key_hash"),
            "sidecar_receipt_hash": receipt.get("sidecar_receipt_hash"),
            "dataset_version_hash": receipt.get("dataset_version_hash"),
            "actor_hash": receipt.get("actor_hash"),
            "fact_count": receipt.get("fact_count"),
            "fact_inventory_hash": receipt.get("fact_inventory_hash"),
            "value_inventory_hash": receipt.get("value_inventory_hash"),
            "value_reveal_policy_id": receipt.get("value_reveal_policy_id"),
            "value_reveal_scope": receipt.get("value_reveal_scope"),
            "value_semantics": receipt.get("value_semantics"),
            "redaction_policy_id": receipt.get("redaction_policy_id"),
        }
    )


def _legacy_receipt_hash_basis(receipt: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "client_request_id_hash": receipt.get("client_request_id_hash"),
            "sidecar_receipt_hash": receipt.get("sidecar_receipt_hash"),
            "dataset_version_hash": receipt.get("dataset_version_hash"),
            "actor_hash": receipt.get("actor_hash"),
            "fact_count": receipt.get("fact_count"),
            "fact_inventory_hash": receipt.get("fact_inventory_hash"),
            "value_inventory_hash": receipt.get("value_inventory_hash"),
            "redaction_policy_id": receipt.get("redaction_policy_id"),
        }
    )


def _blocked_response(*, request_id: str, reasons: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **base_response(SCHEMA_ID, request_id=request_id, status="blocked"),
        "reveal_mode": REVEAL_MODE,
        "reveal_state": BLOCKED_STATE,
        "reveal_receipt_id": None,
        "reveal_receipt_hash": None,
        "reveal_receipt_ref": None,
        "revealed_fact_count": 0,
        "revealed_facts": [],
        "blocked_reasons": reasons,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "raw_values_returned": False,
            "raw_identity_returned": False,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [],
    }


def _reason(
    reason: str,
    *,
    message: str | None = None,
    blocked_fields: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"reason": reason}
    if message:
        payload["message"] = message
    if blocked_fields:
        payload["blocked_fields"] = list(blocked_fields)
    return payload


def _required(request: Mapping[str, Any], key: str) -> str:
    value = str(request.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_arelle_value_reveal_{key}_required",
            f"SEC EDGAR Arelle value reveal requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(request: Mapping[str, Any], key: str) -> str:
    value = _required(request, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_arelle_value_reveal_{key}_invalid",
            f"SEC EDGAR Arelle value reveal requires {key} to be a sha256 hash.",
            blocked_fields=[key],
        )
    return value


def _find_forbidden_nested_fields(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in FORBIDDEN_REQUEST_FIELDS:
                found.append(path)
            found.extend(_find_forbidden_nested_fields(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_nested_fields(child, prefix=f"{prefix}[{index}]"))
    return found


def _projection_has_redaction_violation(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _FORBIDDEN_OUTPUT_KEYS:
                return True
            if _projection_has_redaction_violation(child):
                return True
        return False
    if isinstance(value, list):
        return any(_projection_has_redaction_violation(item) for item in value)
    if isinstance(value, str):
        return bool(_LOCAL_PATH_RE.match(value))
    return False


def _negative_invariants() -> dict[str, bool]:
    return {
        "feature_flag_default_enabled": False,
        "cutover_flag_changed_by_value_reveal": False,
        "synchronous_arelle_invocation_performed": False,
        "raw_sec_url_exposed": False,
        "raw_local_path_exposed": False,
        "raw_storage_root_exposed": False,
        "raw_issuer_identity_exposed": False,
        "raw_actor_exposed": False,
        "raw_values_committed": False,
        "raw_actor_committed": False,
        "raw_identity_committed": False,
        "raw_values_persisted_in_audit_receipt": False,
        "default_operator_product_surface_mutated": False,
        "candidate_b_routing_used_for_sec": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_admitted": False,
        "cross_company_comparability_claimed": False,
        "rag_vector_model_provider_auth_behavior_added": False,
        "frontend_durable_authority_enabled": False,
    }


def _root() -> Path:
    root = Path(settings.storage_dir) / RECEIPT_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _is_hash(value: str) -> bool:
    return len(str(value or "")) == 64 and _is_hex(str(value or ""))


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in str(value or ""))


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
