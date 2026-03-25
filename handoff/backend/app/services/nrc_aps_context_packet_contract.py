from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_evidence_report_contract as report_contract
from app.services import nrc_aps_evidence_report_export_package_contract as package_contract


APS_CONTEXT_PACKET_SCHEMA_ID = "aps.context_packet.v1"
APS_CONTEXT_PACKET_FAILURE_SCHEMA_ID = "aps.context_packet_failure.v1"
APS_CONTEXT_PACKET_GATE_SCHEMA_ID = "aps.context_packet_gate.v1"
APS_CONTEXT_PACKET_SCHEMA_VERSION = 1

APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID = "aps_context_packet_projection_v1"
APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID = "aps_context_packet_fact_grammar_v1"
APS_CONTEXT_PACKET_OBJECTIVE = "normalize_persisted_source_for_downstream_consumption"
APS_CONTEXT_PACKET_ARTIFACT_ID_TOKEN_LEN = report_contract.APS_REPORT_ARTIFACT_ID_TOKEN_LEN

APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT = "evidence_report"
APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT = "evidence_report_export"
APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE = "evidence_report_export_package"
APS_CONTEXT_PACKET_ALLOWED_SOURCE_FAMILIES = {
    APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT,
    APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
    APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE,
}

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_SOURCE_NOT_FOUND = "context_packet_source_not_found"
APS_RUNTIME_FAILURE_SOURCE_INVALID = "context_packet_source_invalid"
APS_RUNTIME_FAILURE_NOT_FOUND = "context_packet_not_found"
APS_RUNTIME_FAILURE_INVALID = "context_packet_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "context_packet_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "context_packet_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_context_packet_error"

APS_GATE_FAILURE_MISSING_REF = "missing_context_packet_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_context_packet_ref"
APS_GATE_FAILURE_CONTEXT_SCHEMA = "context_packet_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "context_packet_failure_schema_mismatch"
APS_GATE_FAILURE_PROJECTION_CONTRACT = "projection_contract_mismatch"
APS_GATE_FAILURE_FACT_GRAMMAR_CONTRACT = "fact_grammar_contract_mismatch"
APS_GATE_FAILURE_SOURCE_REF = "source_ref_mismatch"
APS_GATE_FAILURE_SOURCE_DESCRIPTOR = "source_descriptor_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_FACT_DRIFT = "fact_drift"
APS_GATE_FAILURE_CAVEAT_DRIFT = "caveat_drift"
APS_GATE_FAILURE_CONSTRAINT_DRIFT = "constraint_drift"
APS_GATE_FAILURE_UNRESOLVED_QUESTION_DRIFT = "unresolved_question_drift"
APS_GATE_FAILURE_DERIVATION_DRIFT = "context_packet_derivation_drift"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_context_packet_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("context_packet_checksum", None)
    clean.pop("_context_packet_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_context_packet_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_context_packet_payload(payload))


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_CONTEXT_PACKET_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_context_packet_file_name(*, scope: str, context_packet_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(context_packet_id)}_aps_context_packet_v1.json"


def expected_failure_file_name(*, scope: str, context_packet_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(context_packet_id)}_aps_context_packet_failure_v1.json"


def derive_failure_context_packet_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_CONTEXT_PACKET_FAILURE_SCHEMA_ID,
            APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_context_packet_id(*, source_family: str, source_id: str, source_checksum: str) -> str:
    raw = ":".join(
        [
            APS_CONTEXT_PACKET_SCHEMA_ID,
            APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID,
            APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID,
            str(source_family or ""),
            str(source_id or ""),
            str(source_checksum or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _selector_family(payload: dict[str, Any]) -> tuple[str | None, dict[str, str | None]]:
    family_inputs = [
        (
            APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT,
            {
                "id": _as_clean_text(payload.get("evidence_report_id")),
                "ref": _as_clean_text(payload.get("evidence_report_ref")),
            },
        ),
        (
            APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
            {
                "id": _as_clean_text(payload.get("evidence_report_export_id")),
                "ref": _as_clean_text(payload.get("evidence_report_export_ref")),
            },
        ),
        (
            APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE,
            {
                "id": _as_clean_text(payload.get("evidence_report_export_package_id")),
                "ref": _as_clean_text(payload.get("evidence_report_export_package_ref")),
            },
        ),
    ]
    active = [(family, selector) for family, selector in family_inputs if bool(selector["id"]) or bool(selector["ref"])]
    if len(active) != 1:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    family, selector = active[0]
    if bool(selector["id"]) == bool(selector["ref"]):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    return family, selector


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    source_family, selector = _selector_family(payload)
    if source_family is None or source_family not in APS_CONTEXT_PACKET_ALLOWED_SOURCE_FAMILIES:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    normalized = {
        "source_family": source_family,
        "evidence_report_id": None,
        "evidence_report_ref": None,
        "evidence_report_export_id": None,
        "evidence_report_export_ref": None,
        "evidence_report_export_package_id": None,
        "evidence_report_export_package_ref": None,
        "persist_context_packet": bool(payload.get("persist_context_packet", False)),
    }
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        normalized["evidence_report_id"] = selector["id"]
        normalized["evidence_report_ref"] = selector["ref"]
    elif source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        normalized["evidence_report_export_id"] = selector["id"]
        normalized["evidence_report_export_ref"] = selector["ref"]
    elif source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        normalized["evidence_report_export_package_id"] = selector["id"]
        normalized["evidence_report_export_package_ref"] = selector["ref"]
    return normalized


def _clean_object(values: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, str) and not value.strip():
            continue
        if value is None:
            continue
        cleaned[str(key)] = value
    return cleaned


def source_descriptor_for_report(report_payload: dict[str, Any]) -> dict[str, Any]:
    source_pack = dict(report_payload.get("source_citation_pack") or {})
    source_bundle = dict(source_pack.get("source_bundle") or {})
    return _clean_object(
        {
            "source_family": APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT,
            "source_id": str(report_payload.get("evidence_report_id") or ""),
            "source_checksum": str(report_payload.get("evidence_report_checksum") or ""),
            "source_ref": str(report_payload.get("_evidence_report_ref") or report_payload.get("evidence_report_ref") or "") or None,
            "owner_run_id": str(source_bundle.get("run_id") or "") or None,
            "total_sections": int(report_payload.get("total_sections") or 0),
            "total_citations": int(report_payload.get("total_citations") or 0),
            "total_groups": int(report_payload.get("total_groups") or 0),
            "assembly_contract_id": str(report_payload.get("assembly_contract_id") or ""),
            "sectioning_contract_id": str(report_payload.get("sectioning_contract_id") or ""),
            "source_citation_pack_id": str(source_pack.get("citation_pack_id") or ""),
            "source_citation_pack_checksum": str(source_pack.get("citation_pack_checksum") or ""),
            "source_citation_pack_ref": str(source_pack.get("citation_pack_ref") or "") or None,
        }
    )


def source_descriptor_for_export(export_payload: dict[str, Any]) -> dict[str, Any]:
    source_report = dict(export_payload.get("source_evidence_report") or {})
    return _clean_object(
        {
            "source_family": APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT,
            "source_id": str(export_payload.get("evidence_report_export_id") or ""),
            "source_checksum": str(export_payload.get("evidence_report_export_checksum") or ""),
            "source_ref": str(
                export_payload.get("_evidence_report_export_ref") or export_payload.get("evidence_report_export_ref") or ""
            )
            or None,
            "owner_run_id": package_contract.owner_run_id_for_export_payload(export_payload),
            "total_sections": int(export_payload.get("total_sections") or 0),
            "total_citations": int(export_payload.get("total_citations") or 0),
            "total_groups": int(export_payload.get("total_groups") or 0),
            "format_id": str(export_payload.get("format_id") or ""),
            "media_type": str(export_payload.get("media_type") or ""),
            "file_extension": str(export_payload.get("file_extension") or ""),
            "render_contract_id": str(export_payload.get("render_contract_id") or ""),
            "template_contract_id": str(export_payload.get("template_contract_id") or ""),
            "source_evidence_report_id": str(source_report.get("evidence_report_id") or ""),
            "source_evidence_report_checksum": str(source_report.get("evidence_report_checksum") or ""),
            "source_evidence_report_ref": str(source_report.get("evidence_report_ref") or "") or None,
            "rendered_markdown_sha256": str(export_payload.get("rendered_markdown_sha256") or ""),
        }
    )


def source_descriptor_for_package(package_payload: dict[str, Any]) -> dict[str, Any]:
    return _clean_object(
        {
            "source_family": APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE,
            "source_id": str(package_payload.get("evidence_report_export_package_id") or ""),
            "source_checksum": str(package_payload.get("evidence_report_export_package_checksum") or ""),
            "source_ref": str(
                package_payload.get("_evidence_report_export_package_ref")
                or package_payload.get("evidence_report_export_package_ref")
                or ""
            )
            or None,
            "owner_run_id": str(package_payload.get("owner_run_id") or "") or None,
            "total_sections": int(package_payload.get("total_sections") or 0),
            "total_citations": int(package_payload.get("total_citations") or 0),
            "total_groups": int(package_payload.get("total_groups") or 0),
            "source_export_count": int(package_payload.get("source_export_count") or 0),
            "composition_contract_id": str(package_payload.get("composition_contract_id") or ""),
            "package_mode": str(package_payload.get("package_mode") or ""),
            "format_id": str(package_payload.get("format_id") or ""),
            "media_type": str(package_payload.get("media_type") or ""),
            "file_extension": str(package_payload.get("file_extension") or ""),
            "render_contract_id": str(package_payload.get("render_contract_id") or ""),
            "template_contract_id": str(package_payload.get("template_contract_id") or ""),
            "ordered_source_exports_sha256": str(package_payload.get("ordered_source_exports_sha256") or ""),
        }
    )


def source_descriptor_payload(source_family: str, source_payload: dict[str, Any]) -> dict[str, Any]:
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        return source_descriptor_for_report(source_payload)
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        return source_descriptor_for_export(source_payload)
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        return source_descriptor_for_package(source_payload)
    raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)


def _base_fact_row(
    *,
    fact_type: str,
    source_pointer: str,
    source_ref: str | None,
    source_id: str,
    source_checksum: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    return {
        "fact_ordinal": 0,
        "fact_type": str(fact_type or ""),
        "source_pointer": str(source_pointer or ""),
        "source_ref": str(source_ref or "") or None,
        "source_id": str(source_id or ""),
        "source_checksum": str(source_checksum or ""),
        "fields": _clean_object(dict(fields or {})),
    }


def _renumber_facts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        next_row = dict(row or {})
        next_row["fact_ordinal"] = int(index)
        ordered.append(next_row)
    return ordered


def _report_facts(report_payload: dict[str, Any], descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    source_ref = str(descriptor.get("source_ref") or "") or None
    source_id = str(descriptor.get("source_id") or "")
    source_checksum = str(descriptor.get("source_checksum") or "")
    rows: list[dict[str, Any]] = []
    rows.append(
        _base_fact_row(
            fact_type="report_summary",
            source_pointer="report",
            source_ref=source_ref,
            source_id=source_id,
            source_checksum=source_checksum,
            fields={
                "schema_id": str(report_payload.get("schema_id") or ""),
                "schema_version": int(report_payload.get("schema_version") or 0),
                "assembly_contract_id": str(report_payload.get("assembly_contract_id") or ""),
                "sectioning_contract_id": str(report_payload.get("sectioning_contract_id") or ""),
                "total_sections": int(report_payload.get("total_sections") or 0),
                "total_citations": int(report_payload.get("total_citations") or 0),
                "total_groups": int(report_payload.get("total_groups") or 0),
            },
        )
    )
    sections = [dict(item or {}) for item in list(report_payload.get("sections") or []) if isinstance(item, dict)]
    sections.sort(key=lambda item: int(item.get("section_ordinal") or 0))
    for section in sections:
        section_ordinal = int(section.get("section_ordinal") or 0)
        section_id = str(section.get("section_id") or "")
        section_pointer = f"section:{section_ordinal:05d}"
        rows.append(
            _base_fact_row(
                fact_type="section_summary",
                source_pointer=section_pointer,
                source_ref=source_ref,
                source_id=source_id,
                source_checksum=source_checksum,
                fields={
                    "section_id": section_id,
                    "section_ordinal": section_ordinal,
                    "section_type": str(section.get("section_type") or ""),
                    "group_id": str(section.get("group_id") or ""),
                    "accession_number": _as_clean_text(section.get("accession_number")),
                    "content_id": _as_clean_text(section.get("content_id")),
                    "run_id": str(section.get("run_id") or ""),
                    "target_id": str(section.get("target_id") or ""),
                    "content_contract_id": str(section.get("content_contract_id") or ""),
                    "chunking_contract_id": str(section.get("chunking_contract_id") or ""),
                    "title": str(section.get("title") or ""),
                    "citation_count": int(section.get("citation_count") or 0),
                },
            )
        )
        citations = [dict(item or {}) for item in list(section.get("citations") or []) if isinstance(item, dict)]
        citations.sort(key=lambda item: int(item.get("citation_ordinal") or 0))
        for citation in citations:
            citation_ordinal = int(citation.get("citation_ordinal") or 0)
            rows.append(
                _base_fact_row(
                    fact_type="citation_link",
                    source_pointer=f"{section_pointer}:citation:{citation_ordinal:05d}",
                    source_ref=source_ref,
                    source_id=source_id,
                    source_checksum=source_checksum,
                    fields={
                        "section_id": section_id,
                        "citation_id": str(citation.get("citation_id") or ""),
                        "citation_label": str(citation.get("citation_label") or ""),
                        "citation_ordinal": citation_ordinal,
                        "chunk_id": str(citation.get("chunk_id") or ""),
                        "chunk_ordinal": int(citation.get("chunk_ordinal") or 0),
                        "start_char": int(citation.get("start_char") or 0),
                        "end_char": int(citation.get("end_char") or 0),
                        "snippet_text": str(citation.get("snippet_text") or ""),
                    },
                )
            )
    return _renumber_facts(rows)


def _export_facts(export_payload: dict[str, Any], descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    source_report = dict(export_payload.get("source_evidence_report") or {})
    source_ref = str(descriptor.get("source_ref") or "") or None
    source_id = str(descriptor.get("source_id") or "")
    source_checksum = str(descriptor.get("source_checksum") or "")
    rows = [
        _base_fact_row(
            fact_type="export_summary",
            source_pointer="export",
            source_ref=source_ref,
            source_id=source_id,
            source_checksum=source_checksum,
            fields={
                "schema_id": str(export_payload.get("schema_id") or ""),
                "schema_version": int(export_payload.get("schema_version") or 0),
                "render_contract_id": str(export_payload.get("render_contract_id") or ""),
                "template_contract_id": str(export_payload.get("template_contract_id") or ""),
                "format_id": str(export_payload.get("format_id") or ""),
                "media_type": str(export_payload.get("media_type") or ""),
                "file_extension": str(export_payload.get("file_extension") or ""),
                "total_sections": int(export_payload.get("total_sections") or 0),
                "total_citations": int(export_payload.get("total_citations") or 0),
                "total_groups": int(export_payload.get("total_groups") or 0),
            },
        ),
        _base_fact_row(
            fact_type="source_report_summary",
            source_pointer="export.source_report",
            source_ref=str(source_report.get("evidence_report_ref") or "") or None,
            source_id=str(source_report.get("evidence_report_id") or ""),
            source_checksum=str(source_report.get("evidence_report_checksum") or ""),
            fields={
                "schema_id": str(source_report.get("schema_id") or ""),
                "schema_version": int(source_report.get("schema_version") or 0),
                "assembly_contract_id": str(source_report.get("assembly_contract_id") or ""),
                "sectioning_contract_id": str(source_report.get("sectioning_contract_id") or ""),
                "total_sections": int(source_report.get("total_sections") or 0),
                "total_citations": int(source_report.get("total_citations") or 0),
                "total_groups": int(source_report.get("total_groups") or 0),
                "source_citation_pack_id": str(dict(source_report.get("source_citation_pack") or {}).get("citation_pack_id") or ""),
                "source_citation_pack_checksum": str(
                    dict(source_report.get("source_citation_pack") or {}).get("citation_pack_checksum") or ""
                ),
                "source_citation_pack_ref": str(
                    dict(source_report.get("source_citation_pack") or {}).get("citation_pack_ref") or ""
                )
                or None,
            },
        ),
        _base_fact_row(
            fact_type="render_fingerprint",
            source_pointer="export.render",
            source_ref=source_ref,
            source_id=source_id,
            source_checksum=source_checksum,
            fields={
                "rendered_markdown_sha256": str(export_payload.get("rendered_markdown_sha256") or ""),
                "rendered_markdown_char_len": len(str(export_payload.get("rendered_markdown") or "")),
            },
        ),
    ]
    return _renumber_facts(rows)


def _package_facts(package_payload: dict[str, Any], descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    source_ref = str(descriptor.get("source_ref") or "") or None
    source_id = str(descriptor.get("source_id") or "")
    source_checksum = str(descriptor.get("source_checksum") or "")
    rows: list[dict[str, Any]] = [
        _base_fact_row(
            fact_type="package_summary",
            source_pointer="package",
            source_ref=source_ref,
            source_id=source_id,
            source_checksum=source_checksum,
            fields={
                "schema_id": str(package_payload.get("schema_id") or ""),
                "schema_version": int(package_payload.get("schema_version") or 0),
                "composition_contract_id": str(package_payload.get("composition_contract_id") or ""),
                "package_mode": str(package_payload.get("package_mode") or ""),
                "owner_run_id": str(package_payload.get("owner_run_id") or ""),
                "format_id": str(package_payload.get("format_id") or ""),
                "media_type": str(package_payload.get("media_type") or ""),
                "file_extension": str(package_payload.get("file_extension") or ""),
                "render_contract_id": str(package_payload.get("render_contract_id") or ""),
                "template_contract_id": str(package_payload.get("template_contract_id") or ""),
                "source_export_count": int(package_payload.get("source_export_count") or 0),
                "total_sections": int(package_payload.get("total_sections") or 0),
                "total_citations": int(package_payload.get("total_citations") or 0),
                "total_groups": int(package_payload.get("total_groups") or 0),
                "ordered_source_exports_sha256": str(package_payload.get("ordered_source_exports_sha256") or ""),
            },
        )
    ]
    source_exports = [dict(item or {}) for item in list(package_payload.get("source_exports") or []) if isinstance(item, dict)]
    source_exports.sort(key=lambda item: int(item.get("export_ordinal") or 0))
    for source_export in source_exports:
        export_ordinal = int(source_export.get("export_ordinal") or 0)
        rows.append(
            _base_fact_row(
                fact_type="source_export_summary",
                source_pointer=f"source_export:{export_ordinal:05d}",
                source_ref=str(source_export.get("evidence_report_export_ref") or "") or None,
                source_id=str(source_export.get("evidence_report_export_id") or ""),
                source_checksum=str(source_export.get("evidence_report_export_checksum") or ""),
                fields={
                    "export_ordinal": export_ordinal,
                    "rendered_markdown_sha256": str(source_export.get("rendered_markdown_sha256") or ""),
                    "source_evidence_report_id": str(source_export.get("source_evidence_report_id") or ""),
                    "source_evidence_report_checksum": str(source_export.get("source_evidence_report_checksum") or ""),
                    "source_evidence_report_ref": str(source_export.get("source_evidence_report_ref") or "") or None,
                    "total_sections": int(source_export.get("total_sections") or 0),
                    "total_citations": int(source_export.get("total_citations") or 0),
                    "total_groups": int(source_export.get("total_groups") or 0),
                },
            )
        )
    return _renumber_facts(rows)


def facts_payload(source_family: str, source_payload: dict[str, Any], descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        return _report_facts(source_payload, descriptor)
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        return _export_facts(source_payload, descriptor)
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        return _package_facts(source_payload, descriptor)
    raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)


def _sort_and_number_note_rows(
    rows: list[dict[str, Any]],
    *,
    ordinal_field: str,
) -> list[dict[str, Any]]:
    ordered = sorted(
        [dict(item or {}) for item in rows if isinstance(item, dict)],
        key=lambda item: (str(item.get("code") or ""), str(item.get("context_key") or "")),
    )
    finalized: list[dict[str, Any]] = []
    for index, row in enumerate(ordered, start=1):
        row[ordinal_field] = int(index)
        row["code"] = str(row.get("code") or "")
        row["context_key"] = str(row.get("context_key") or "")
        row["source_pointer"] = str(row.get("source_pointer") or "") or None
        row["fields"] = _clean_object(dict(row.get("fields") or {}))
        finalized.append(row)
    return finalized


def caveats_payload(source_family: str, source_payload: dict[str, Any], descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "code": "single_source_projection",
            "context_key": str(source_family or ""),
            "source_pointer": source_family,
            "fields": {"source_family": source_family},
        },
        {
            "code": "optional_fields_may_be_absent",
            "context_key": str(source_family or ""),
            "source_pointer": source_family,
            "fields": {},
        },
    ]
    if not str(descriptor.get("source_ref") or "").strip():
        rows.append(
            {
                "code": "source_ref_absent",
                "context_key": str(source_family or ""),
                "source_pointer": source_family,
                "fields": {},
            }
        )
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        sections = [dict(item or {}) for item in list(source_payload.get("sections") or []) if isinstance(item, dict)]
        for section in sections:
            section_id = str(section.get("section_id") or "")
            if not _as_clean_text(section.get("accession_number")):
                rows.append(
                    {
                        "code": "section_accession_number_absent",
                        "context_key": section_id,
                        "source_pointer": f"section:{int(section.get('section_ordinal') or 0):05d}",
                        "fields": {},
                    }
                )
            if not _as_clean_text(section.get("content_id")):
                rows.append(
                    {
                        "code": "section_content_id_absent",
                        "context_key": section_id,
                        "source_pointer": f"section:{int(section.get('section_ordinal') or 0):05d}",
                        "fields": {},
                    }
                )
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        source_report = dict(source_payload.get("source_evidence_report") or {})
        if not str(source_report.get("evidence_report_ref") or "").strip():
            rows.append(
                {
                    "code": "source_evidence_report_ref_absent",
                    "context_key": str(source_payload.get("evidence_report_export_id") or ""),
                    "source_pointer": "export.source_report",
                    "fields": {},
                }
            )
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        source_exports = [dict(item or {}) for item in list(source_payload.get("source_exports") or []) if isinstance(item, dict)]
        for source_export in source_exports:
            if not str(source_export.get("evidence_report_export_ref") or "").strip():
                rows.append(
                    {
                        "code": "source_export_ref_absent",
                        "context_key": str(source_export.get("evidence_report_export_id") or ""),
                        "source_pointer": f"source_export:{int(source_export.get('export_ordinal') or 0):05d}",
                        "fields": {},
                    }
                )
    return _sort_and_number_note_rows(rows, ordinal_field="caveat_ordinal")


def constraints_payload(source_family: str) -> list[dict[str, Any]]:
    rows = [
        {
            "code": "persisted_source_only",
            "context_key": str(source_family or ""),
            "source_pointer": str(source_family or ""),
            "fields": {},
        },
        {
            "code": "single_source_family_per_packet",
            "context_key": str(source_family or ""),
            "source_pointer": str(source_family or ""),
            "fields": {},
        },
        {
            "code": "no_lower_layer_regeneration",
            "context_key": str(source_family or ""),
            "source_pointer": str(source_family or ""),
            "fields": {},
        },
        {
            "code": "no_paraphrase_or_inference",
            "context_key": str(source_family or ""),
            "source_pointer": str(source_family or ""),
            "fields": {},
        },
        {
            "code": "deterministic_projection_ordering",
            "context_key": str(source_family or ""),
            "source_pointer": str(source_family or ""),
            "fields": {},
        },
    ]
    return _sort_and_number_note_rows(rows, ordinal_field="constraint_ordinal")


def unresolved_questions_payload(
    source_family: str,
    source_payload: dict[str, Any],
    descriptor: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not str(descriptor.get("source_ref") or "").strip():
        rows.append(
            {
                "code": "source_ref_unavailable",
                "context_key": str(source_family or ""),
                "source_pointer": str(source_family or ""),
                "fields": {},
            }
        )
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        sections = [dict(item or {}) for item in list(source_payload.get("sections") or []) if isinstance(item, dict)]
        for section in sections:
            section_ordinal = int(section.get("section_ordinal") or 0)
            section_id = str(section.get("section_id") or "")
            pointer = f"section:{section_ordinal:05d}"
            if not _as_clean_text(section.get("accession_number")):
                rows.append(
                    {
                        "code": "missing_accession_number",
                        "context_key": section_id,
                        "source_pointer": pointer,
                        "fields": {"section_ordinal": section_ordinal},
                    }
                )
            if not _as_clean_text(section.get("content_id")):
                rows.append(
                    {
                        "code": "missing_content_id",
                        "context_key": section_id,
                        "source_pointer": pointer,
                        "fields": {"section_ordinal": section_ordinal},
                    }
                )
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        source_report = dict(source_payload.get("source_evidence_report") or {})
        if not str(source_report.get("evidence_report_ref") or "").strip():
            rows.append(
                {
                    "code": "missing_source_report_ref",
                    "context_key": str(source_payload.get("evidence_report_export_id") or ""),
                    "source_pointer": "export.source_report",
                    "fields": {},
                }
            )
    if source_family == APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        source_exports = [dict(item or {}) for item in list(source_payload.get("source_exports") or []) if isinstance(item, dict)]
        for source_export in source_exports:
            if not str(source_export.get("evidence_report_export_ref") or "").strip():
                rows.append(
                    {
                        "code": "missing_source_export_ref",
                        "context_key": str(source_export.get("evidence_report_export_id") or ""),
                        "source_pointer": f"source_export:{int(source_export.get('export_ordinal') or 0):05d}",
                        "fields": {},
                    }
                )
    return _sort_and_number_note_rows(rows, ordinal_field="unresolved_question_ordinal")


def build_context_packet_payload(
    *,
    source_family: str,
    source_payload: dict[str, Any],
    generated_at_utc: str,
) -> dict[str, Any]:
    descriptor = source_descriptor_payload(source_family, source_payload)
    source_id = str(descriptor.get("source_id") or "")
    source_checksum = str(descriptor.get("source_checksum") or "")
    facts = facts_payload(source_family, source_payload, descriptor)
    caveats = caveats_payload(source_family, source_payload, descriptor)
    constraints = constraints_payload(source_family)
    unresolved_questions = unresolved_questions_payload(source_family, source_payload, descriptor)
    payload = {
        "schema_id": APS_CONTEXT_PACKET_SCHEMA_ID,
        "schema_version": APS_CONTEXT_PACKET_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        "context_packet_id": derive_context_packet_id(
            source_family=source_family,
            source_id=source_id,
            source_checksum=source_checksum,
        ),
        "projection_contract_id": APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID,
        "fact_grammar_contract_id": APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID,
        "source_family": str(source_family or ""),
        "source_descriptor": descriptor,
        "objective": APS_CONTEXT_PACKET_OBJECTIVE,
        "scope": {
            "source_family": str(source_family or ""),
            "source_id": source_id,
            "source_checksum": source_checksum,
        },
        "facts": facts,
        "caveats": caveats,
        "constraints": constraints,
        "unresolved_questions": unresolved_questions,
        "total_facts": len(facts),
        "total_caveats": len(caveats),
        "total_constraints": len(constraints),
        "total_unresolved_questions": len(unresolved_questions),
    }
    payload["context_packet_checksum"] = compute_context_packet_checksum(payload)
    return payload
