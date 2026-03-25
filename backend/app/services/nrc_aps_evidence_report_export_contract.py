from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_evidence_report_contract as report_contract


APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID = "aps.evidence_report_export.v1"
APS_EVIDENCE_REPORT_EXPORT_FAILURE_SCHEMA_ID = "aps.evidence_report_export_failure.v1"
APS_EVIDENCE_REPORT_EXPORT_GATE_SCHEMA_ID = "aps.evidence_report_export_gate.v1"
APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION = 1

APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID = "aps_evidence_report_export_render_v1"
APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID = "aps_evidence_report_export_markdown_template_v1"

APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID = "markdown"
APS_EVIDENCE_REPORT_EXPORT_MEDIA_TYPE = "text/markdown; charset=utf-8"
APS_EVIDENCE_REPORT_EXPORT_FILE_EXTENSION = ".md"
APS_EVIDENCE_REPORT_EXPORT_ARTIFACT_ID_TOKEN_LEN = report_contract.APS_REPORT_ARTIFACT_ID_TOKEN_LEN
APS_EVIDENCE_REPORT_EXPORT_ROOT_HEADING = "# NRC ADAMS APS Evidence Report Export"

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_EXPORT_NOT_FOUND = "evidence_report_export_not_found"
APS_RUNTIME_FAILURE_EXPORT_INVALID = "evidence_report_export_invalid"
APS_RUNTIME_FAILURE_SOURCE_REPORT_NOT_FOUND = "source_evidence_report_not_found"
APS_RUNTIME_FAILURE_SOURCE_REPORT_INVALID = "source_evidence_report_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "evidence_report_export_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "evidence_report_export_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_evidence_report_export_error"

APS_GATE_FAILURE_MISSING_REF = "missing_evidence_report_export_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_evidence_report_export_ref"
APS_GATE_FAILURE_EXPORT_SCHEMA = "evidence_report_export_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "evidence_report_export_failure_schema_mismatch"
APS_GATE_FAILURE_RENDER_CONTRACT = "render_contract_mismatch"
APS_GATE_FAILURE_TEMPLATE_CONTRACT = "template_contract_mismatch"
APS_GATE_FAILURE_SOURCE_REPORT_REF = "source_evidence_report_ref_mismatch"
APS_GATE_FAILURE_SOURCE_REPORT_MISMATCH = "source_evidence_report_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_RENDERED_MARKDOWN_HASH = "rendered_markdown_hash_mismatch"
APS_GATE_FAILURE_RENDERED_MARKDOWN_DRIFT = "rendered_markdown_drift"
APS_GATE_FAILURE_DERIVATION_DRIFT = "export_derivation_drift"

_ESCAPABLE_MARKDOWN_CHARS = {"\\", "`", "*", "_", "[", "]", "(", ")", "#", ">", "+", "-", "!", "|"}


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def stable_text_hash(text: str) -> str:
    return hashlib.sha256(normalize_rendered_markdown_body(text).encode("utf-8")).hexdigest()


def logical_evidence_report_export_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("evidence_report_export_checksum", None)
    clean.pop("_evidence_report_export_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_evidence_report_export_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_evidence_report_export_payload(payload))


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    evidence_report_id = str(payload.get("evidence_report_id") or "").strip() or None
    evidence_report_ref = str(payload.get("evidence_report_ref") or "").strip() or None
    if bool(evidence_report_id) == bool(evidence_report_ref):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    return {
        "evidence_report_id": evidence_report_id,
        "evidence_report_ref": evidence_report_ref,
        "persist_export": bool(payload.get("persist_export", False)),
    }


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_EVIDENCE_REPORT_EXPORT_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_export_file_name(*, scope: str, evidence_report_export_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(evidence_report_export_id)}_aps_evidence_report_export_v1.json"


def expected_failure_file_name(*, scope: str, evidence_report_export_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(evidence_report_export_id)}_aps_evidence_report_export_failure_v1.json"


def derive_evidence_report_export_id(*, evidence_report_id: str, evidence_report_checksum: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID,
            APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID,
            APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID,
            APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID,
            str(evidence_report_id or ""),
            str(evidence_report_checksum or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_failure_export_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_REPORT_EXPORT_FAILURE_SCHEMA_ID,
            APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_line_endings(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def _escape_markdown_text(text: str) -> str:
    escaped: list[str] = []
    for char in normalize_line_endings(text):
        if char in _ESCAPABLE_MARKDOWN_CHARS:
            escaped.append("\\")
        escaped.append(char)
    return "".join(escaped)


def normalize_rendered_markdown_body(text: str) -> str:
    normalized = normalize_line_endings(text)
    lines = [line.rstrip(" ") for line in normalized.split("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def _render_scalar_text(value: Any) -> str:
    return _escape_markdown_text(str(value if value is not None else ""))


def _render_inline_snippet(value: Any) -> str:
    normalized = normalize_line_endings(str(value if value is not None else ""))
    normalized = normalized.replace("\t", "\\t").replace("\n", "\\n")
    return _escape_markdown_text(normalized)


def optional_text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text.strip() else None


def source_evidence_report_summary_payload(report_payload: dict[str, Any]) -> dict[str, Any]:
    source_citation_pack = dict(report_payload.get("source_citation_pack") or {})
    return {
        "schema_id": str(report_payload.get("schema_id") or report_contract.APS_EVIDENCE_REPORT_SCHEMA_ID),
        "schema_version": int(report_payload.get("schema_version") or report_contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION),
        "evidence_report_id": str(report_payload.get("evidence_report_id") or ""),
        "evidence_report_checksum": str(report_payload.get("evidence_report_checksum") or ""),
        "evidence_report_ref": str(report_payload.get("_evidence_report_ref") or report_payload.get("evidence_report_ref") or "") or None,
        "assembly_contract_id": str(
            report_payload.get("assembly_contract_id") or report_contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID
        ),
        "sectioning_contract_id": str(
            report_payload.get("sectioning_contract_id") or report_contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID
        ),
        "total_sections": int(report_payload.get("total_sections") or 0),
        "total_citations": int(report_payload.get("total_citations") or 0),
        "total_groups": int(report_payload.get("total_groups") or 0),
        "source_citation_pack": {
            **source_citation_pack,
            "citation_pack_ref": str(source_citation_pack.get("citation_pack_ref") or "") or None,
        },
    }


def render_markdown_document(
    *,
    evidence_report_export_id: str,
    source_evidence_report: dict[str, Any],
    total_sections: int,
    total_citations: int,
    total_groups: int,
    sections: list[dict[str, Any]],
) -> str:
    source_citation_pack = dict(source_evidence_report.get("source_citation_pack") or {})
    header_lines = [
        APS_EVIDENCE_REPORT_EXPORT_ROOT_HEADING,
        "",
        f"- Export ID: {_render_scalar_text(evidence_report_export_id)}",
        f"- Format: {_render_scalar_text(APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID)}",
        f"- Render Contract: {_render_scalar_text(APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID)}",
        f"- Template Contract: {_render_scalar_text(APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID)}",
        f"- Source Evidence Report ID: {_render_scalar_text(source_evidence_report.get('evidence_report_id'))}",
        f"- Source Evidence Report Checksum: {_render_scalar_text(source_evidence_report.get('evidence_report_checksum'))}",
        f"- Source Citation Pack ID: {_render_scalar_text(source_citation_pack.get('citation_pack_id'))}",
        f"- Source Citation Pack Checksum: {_render_scalar_text(source_citation_pack.get('citation_pack_checksum'))}",
        f"- Total Sections: {int(total_sections)}",
        f"- Total Citations: {int(total_citations)}",
        f"- Total Groups: {int(total_groups)}",
    ]

    section_blocks: list[str] = []
    for section in [dict(item or {}) for item in sections if isinstance(item, dict)]:
        section_lines = [
            f"## Section {int(section.get('section_ordinal') or 0):05d}: {_render_scalar_text(section.get('title'))}",
            "",
            f"- Group ID: {_render_scalar_text(section.get('group_id'))}",
            f"- Run ID: {_render_scalar_text(section.get('run_id'))}",
            f"- Target ID: {_render_scalar_text(section.get('target_id'))}",
        ]
        content_id = optional_text_or_none(section.get("content_id"))
        if content_id is not None:
            section_lines.append(f"- Content ID: {_render_scalar_text(content_id)}")
        accession_number = optional_text_or_none(section.get("accession_number"))
        if accession_number is not None:
            section_lines.append(f"- Accession Number: {_render_scalar_text(accession_number)}")
        section_lines.extend(
            [
                f"- Content Contract ID: {_render_scalar_text(section.get('content_contract_id'))}",
                f"- Chunking Contract ID: {_render_scalar_text(section.get('chunking_contract_id'))}",
                f"- Citation Count: {int(section.get('citation_count') or 0)}",
            ]
        )

        citation_blocks: list[str] = []
        citations = [dict(item or {}) for item in list(section.get("citations") or []) if isinstance(item, dict)]
        for citation_index, citation in enumerate(citations, start=1):
            citation_blocks.append(
                "\n".join(
                    [
                        f"{citation_index}. {_render_scalar_text(citation.get('citation_label'))} | {_render_scalar_text(citation.get('citation_id'))}",
                        f"   - Chunk ID: {_render_scalar_text(citation.get('chunk_id'))}",
                        f"   - Chunk Ordinal: {int(citation.get('chunk_ordinal') or 0)}",
                        f"   - Character Span: {int(citation.get('start_char') or 0)}:{int(citation.get('end_char') or 0)}",
                        f"   - Snippet: {_render_inline_snippet(citation.get('snippet_text'))}",
                    ]
                )
            )
        section_block = "\n".join(section_lines)
        if citation_blocks:
            section_block = section_block + "\n\n" + "\n\n".join(citation_blocks)
        section_blocks.append(section_block)

    document = "\n\n".join(["\n".join(header_lines)] + section_blocks if section_blocks else ["\n".join(header_lines)])
    return normalize_rendered_markdown_body(document)


def compute_rendered_markdown_sha256(rendered_markdown: str) -> str:
    return stable_text_hash(rendered_markdown)


def build_evidence_report_export_payload(
    source_report_payload: dict[str, Any],
    *,
    generated_at_utc: str,
) -> dict[str, Any]:
    source_evidence_report = source_evidence_report_summary_payload(source_report_payload)
    evidence_report_export_id = derive_evidence_report_export_id(
        evidence_report_id=str(source_evidence_report.get("evidence_report_id") or ""),
        evidence_report_checksum=str(source_evidence_report.get("evidence_report_checksum") or ""),
    )
    sections = [dict(item or {}) for item in list(source_report_payload.get("sections") or []) if isinstance(item, dict)]
    payload = {
        "schema_id": APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID,
        "schema_version": APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        "evidence_report_export_id": evidence_report_export_id,
        "render_contract_id": APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID,
        "template_contract_id": APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID,
        "format_id": APS_EVIDENCE_REPORT_EXPORT_FORMAT_ID,
        "media_type": APS_EVIDENCE_REPORT_EXPORT_MEDIA_TYPE,
        "file_extension": APS_EVIDENCE_REPORT_EXPORT_FILE_EXTENSION,
        "source_evidence_report": source_evidence_report,
        "total_sections": int(source_evidence_report.get("total_sections") or 0),
        "total_citations": int(source_evidence_report.get("total_citations") or 0),
        "total_groups": int(source_evidence_report.get("total_groups") or 0),
        "rendered_markdown": "",
        "rendered_markdown_sha256": "",
    }
    rendered_markdown = render_markdown_document(
        evidence_report_export_id=evidence_report_export_id,
        source_evidence_report=source_evidence_report,
        total_sections=int(payload["total_sections"]),
        total_citations=int(payload["total_citations"]),
        total_groups=int(payload["total_groups"]),
        sections=sections,
    )
    payload["rendered_markdown"] = rendered_markdown
    payload["rendered_markdown_sha256"] = compute_rendered_markdown_sha256(rendered_markdown)
    payload["evidence_report_export_checksum"] = compute_evidence_report_export_checksum(payload)
    return payload
