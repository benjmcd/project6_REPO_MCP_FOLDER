from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services import nrc_aps_evidence_report_export_contract as export_contract


APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID = "aps.evidence_report_export_package.v1"
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_FAILURE_SCHEMA_ID = "aps.evidence_report_export_package_failure.v1"
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_GATE_SCHEMA_ID = "aps.evidence_report_export_package_gate.v1"
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION = 1

APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID = "aps_evidence_report_export_package_manifest_v1"
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE = "manifest_only"
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MIN_SOURCES = 2
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MAX_SOURCES = 100
APS_EVIDENCE_REPORT_EXPORT_PACKAGE_ARTIFACT_ID_TOKEN_LEN = export_contract.APS_EVIDENCE_REPORT_EXPORT_ARTIFACT_ID_TOKEN_LEN

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_EXPORT = "duplicate_source_export"
APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_EXPORTS = "too_few_source_exports"
APS_RUNTIME_FAILURE_TOO_MANY_SOURCE_EXPORTS = "too_many_source_exports"
APS_RUNTIME_FAILURE_SOURCE_EXPORT_NOT_FOUND = "source_export_not_found"
APS_RUNTIME_FAILURE_SOURCE_EXPORT_INVALID = "source_export_invalid"
APS_RUNTIME_FAILURE_SOURCE_EXPORT_INCOMPATIBLE = "source_export_incompatible"
APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED = "cross_run_package_not_supported_v1"
APS_RUNTIME_FAILURE_PACKAGE_NOT_FOUND = "evidence_report_export_package_not_found"
APS_RUNTIME_FAILURE_PACKAGE_INVALID = "evidence_report_export_package_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "evidence_report_export_package_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "evidence_report_export_package_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_evidence_report_export_package_error"

APS_GATE_FAILURE_MISSING_REF = "missing_evidence_report_export_package_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_evidence_report_export_package_ref"
APS_GATE_FAILURE_PACKAGE_SCHEMA = "evidence_report_export_package_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "evidence_report_export_package_failure_schema_mismatch"
APS_GATE_FAILURE_COMPOSITION_CONTRACT = "composition_contract_mismatch"
APS_GATE_FAILURE_PACKAGE_MODE = "package_mode_mismatch"
APS_GATE_FAILURE_SOURCE_EXPORT_REF = "source_export_ref_mismatch"
APS_GATE_FAILURE_SOURCE_EXPORT_MISMATCH = "source_export_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_ORDERED_DIGEST = "ordered_source_exports_sha256_mismatch"
APS_GATE_FAILURE_DERIVATION_DRIFT = "package_derivation_drift"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_evidence_report_export_package_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("evidence_report_export_package_checksum", None)
    clean.pop("_evidence_report_export_package_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_evidence_report_export_package_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_evidence_report_export_package_payload(payload))


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    export_ids = [str(item).strip() for item in list(payload.get("evidence_report_export_ids") or []) if str(item).strip()]
    export_refs = [str(item).strip() for item in list(payload.get("evidence_report_export_refs") or []) if str(item).strip()]
    if bool(export_ids) == bool(export_refs):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    source_refs = export_ids or export_refs
    if len(source_refs) < APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MIN_SOURCES:
        raise ValueError(APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_EXPORTS)
    if len(source_refs) > APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MAX_SOURCES:
        raise ValueError(APS_RUNTIME_FAILURE_TOO_MANY_SOURCE_EXPORTS)
    if len(set(source_refs)) != len(source_refs):
        raise ValueError(APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_EXPORT)
    return {
        "evidence_report_export_ids": export_ids or None,
        "evidence_report_export_refs": export_refs or None,
        "persist_package": bool(payload.get("persist_package", False)),
    }


def safe_path_token(value: str) -> str:
    return export_contract.safe_path_token(value)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_EVIDENCE_REPORT_EXPORT_PACKAGE_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_package_file_name(*, scope: str, evidence_report_export_package_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(evidence_report_export_package_id)}"
        "_aps_evidence_report_export_package_v1.json"
    )


def expected_failure_file_name(*, scope: str, evidence_report_export_package_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(evidence_report_export_package_id)}"
        "_aps_evidence_report_export_package_failure_v1.json"
    )


def derive_failure_package_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_REPORT_EXPORT_PACKAGE_FAILURE_SCHEMA_ID,
            APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ordered_source_exports_sha256(source_exports: list[dict[str, Any]]) -> str:
    ordered = []
    for item in source_exports:
        row = dict(item or {})
        ordered.append(
            {
                "evidence_report_export_id": str(row.get("evidence_report_export_id") or ""),
                "evidence_report_export_checksum": str(row.get("evidence_report_export_checksum") or ""),
            }
        )
    return stable_hash({"source_exports": ordered})


def derive_evidence_report_export_package_id(
    *,
    format_id: str,
    render_contract_id: str,
    template_contract_id: str,
    ordered_source_exports_sha256_value: str,
) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID,
            APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID,
            APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE,
            str(format_id or ""),
            str(render_contract_id or ""),
            str(template_contract_id or ""),
            str(ordered_source_exports_sha256_value or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def owner_run_id_for_export_payload(export_payload: dict[str, Any]) -> str | None:
    source_report = dict(export_payload.get("source_evidence_report") or {})
    source_citation_pack = dict(source_report.get("source_citation_pack") or {})
    source_bundle = dict(source_citation_pack.get("source_bundle") or {})
    run_id = str(source_bundle.get("run_id") or "").strip()
    return run_id or None


def export_descriptor_payload(export_payload: dict[str, Any], *, export_ordinal: int) -> dict[str, Any]:
    source_report = dict(export_payload.get("source_evidence_report") or {})
    return {
        "export_ordinal": int(export_ordinal),
        "evidence_report_export_id": str(export_payload.get("evidence_report_export_id") or ""),
        "evidence_report_export_checksum": str(export_payload.get("evidence_report_export_checksum") or ""),
        "evidence_report_export_ref": str(
            export_payload.get("_evidence_report_export_ref") or export_payload.get("evidence_report_export_ref") or ""
        )
        or None,
        "rendered_markdown_sha256": str(export_payload.get("rendered_markdown_sha256") or ""),
        "source_evidence_report_id": str(source_report.get("evidence_report_id") or ""),
        "source_evidence_report_checksum": str(source_report.get("evidence_report_checksum") or ""),
        "source_evidence_report_ref": str(source_report.get("evidence_report_ref") or "") or None,
        "total_sections": int(export_payload.get("total_sections") or 0),
        "total_citations": int(export_payload.get("total_citations") or 0),
        "total_groups": int(export_payload.get("total_groups") or 0),
    }


def validate_export_family_compatibility(export_payloads: list[dict[str, Any]]) -> dict[str, str]:
    if not export_payloads:
        return {
            "format_id": "",
            "media_type": "",
            "file_extension": "",
            "render_contract_id": "",
            "template_contract_id": "",
        }
    first = dict(export_payloads[0] or {})
    expected = {
        "format_id": str(first.get("format_id") or ""),
        "media_type": str(first.get("media_type") or ""),
        "file_extension": str(first.get("file_extension") or ""),
        "render_contract_id": str(first.get("render_contract_id") or ""),
        "template_contract_id": str(first.get("template_contract_id") or ""),
        "source_report_schema_id": str(dict(first.get("source_evidence_report") or {}).get("schema_id") or ""),
        "source_report_schema_version": str(dict(first.get("source_evidence_report") or {}).get("schema_version") or ""),
    }
    for export_payload in export_payloads[1:]:
        source_report = dict(export_payload.get("source_evidence_report") or {})
        actual = {
            "format_id": str(export_payload.get("format_id") or ""),
            "media_type": str(export_payload.get("media_type") or ""),
            "file_extension": str(export_payload.get("file_extension") or ""),
            "render_contract_id": str(export_payload.get("render_contract_id") or ""),
            "template_contract_id": str(export_payload.get("template_contract_id") or ""),
            "source_report_schema_id": str(source_report.get("schema_id") or ""),
            "source_report_schema_version": str(source_report.get("schema_version") or ""),
        }
        if actual != expected:
            raise ValueError(APS_RUNTIME_FAILURE_SOURCE_EXPORT_INCOMPATIBLE)
    return {
        "format_id": expected["format_id"],
        "media_type": expected["media_type"],
        "file_extension": expected["file_extension"],
        "render_contract_id": expected["render_contract_id"],
        "template_contract_id": expected["template_contract_id"],
    }


def build_evidence_report_export_package_payload(
    export_payloads: list[dict[str, Any]],
    *,
    generated_at_utc: str,
    owner_run_id: str,
) -> dict[str, Any]:
    compatibility = validate_export_family_compatibility(export_payloads)
    source_exports = [
        export_descriptor_payload(export_payload, export_ordinal=index)
        for index, export_payload in enumerate(export_payloads, start=1)
    ]
    source_export_count = len(source_exports)
    ordered_digest = ordered_source_exports_sha256(source_exports)
    payload = {
        "schema_id": APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_ID,
        "schema_version": APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        "composition_contract_id": APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID,
        "package_mode": APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE,
        "owner_run_id": str(owner_run_id or ""),
        "format_id": str(compatibility.get("format_id") or ""),
        "media_type": str(compatibility.get("media_type") or ""),
        "file_extension": str(compatibility.get("file_extension") or ""),
        "render_contract_id": str(compatibility.get("render_contract_id") or ""),
        "template_contract_id": str(compatibility.get("template_contract_id") or ""),
        "source_export_count": int(source_export_count),
        "total_sections": sum(int(item.get("total_sections") or 0) for item in source_exports),
        "total_citations": sum(int(item.get("total_citations") or 0) for item in source_exports),
        "total_groups": sum(int(item.get("total_groups") or 0) for item in source_exports),
        "ordered_source_exports_sha256": ordered_digest,
        "source_exports": source_exports,
    }
    payload["evidence_report_export_package_id"] = derive_evidence_report_export_package_id(
        format_id=str(payload.get("format_id") or ""),
        render_contract_id=str(payload.get("render_contract_id") or ""),
        template_contract_id=str(payload.get("template_contract_id") or ""),
        ordered_source_exports_sha256_value=ordered_digest,
    )
    payload["evidence_report_export_package_checksum"] = compute_evidence_report_export_package_checksum(payload)
    return payload
