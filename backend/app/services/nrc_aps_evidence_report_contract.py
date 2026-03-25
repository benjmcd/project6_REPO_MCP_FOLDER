from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_evidence_citation_pack_contract as citation_pack_contract


APS_EVIDENCE_REPORT_SCHEMA_ID = "aps.evidence_report.v1"
APS_EVIDENCE_REPORT_FAILURE_SCHEMA_ID = "aps.evidence_report_failure.v1"
APS_EVIDENCE_REPORT_GATE_SCHEMA_ID = "aps.evidence_report_gate.v1"
APS_EVIDENCE_REPORT_SCHEMA_VERSION = 1

APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID = "aps_evidence_report_assembly_v1"
APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID = "aps_evidence_report_sectioning_v1"

# Report pagination intentionally matches citation-pack v1 paging policy.
APS_REPORT_DEFAULT_LIMIT = citation_pack_contract.APS_CITATION_DEFAULT_LIMIT
APS_REPORT_MAX_LIMIT = citation_pack_contract.APS_CITATION_MAX_LIMIT
APS_REPORT_ARTIFACT_ID_TOKEN_LEN = citation_pack_contract.APS_CITATION_ARTIFACT_ID_TOKEN_LEN
APS_REPORT_SECTION_TYPE = "evidence_group"

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_REPORT_NOT_FOUND = "evidence_report_not_found"
APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_NOT_FOUND = "source_citation_pack_not_found"
APS_RUNTIME_FAILURE_SOURCE_CITATION_PACK_INVALID = "source_citation_pack_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "evidence_report_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "evidence_report_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_evidence_report_error"

APS_GATE_FAILURE_MISSING_REF = "missing_evidence_report_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_evidence_report_ref"
APS_GATE_FAILURE_REPORT_SCHEMA = "evidence_report_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "evidence_report_failure_schema_mismatch"
APS_GATE_FAILURE_ASSEMBLY_CONTRACT = "assembly_contract_mismatch"
APS_GATE_FAILURE_SECTIONING_CONTRACT = "sectioning_contract_mismatch"
APS_GATE_FAILURE_SOURCE_CITATION_PACK_REF = "source_citation_pack_ref_mismatch"
APS_GATE_FAILURE_SOURCE_CITATION_PACK_MISMATCH = "source_citation_pack_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_SECTION_ORDER_DRIFT = "section_order_drift"
APS_GATE_FAILURE_SECTION_TITLE_DRIFT = "section_title_drift"
APS_GATE_FAILURE_CITATION_LINKAGE_DRIFT = "citation_linkage_drift"
APS_GATE_FAILURE_DERIVATION_DRIFT = "report_derivation_drift"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_evidence_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("evidence_report_checksum", None)
    clean.pop("_evidence_report_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    source_pack = dict(clean.get("source_citation_pack") or {})
    source_pack.pop("_citation_pack_ref", None)
    source_pack.pop("_persisted", None)
    source_bundle = dict(source_pack.get("source_bundle") or {})
    source_bundle.pop("_bundle_ref", None)
    source_bundle.pop("_persisted", None)
    source_pack["source_bundle"] = source_bundle
    clean["source_citation_pack"] = source_pack
    return clean


def compute_evidence_report_checksum(payload: dict[str, Any]) -> str:
    clean = logical_evidence_report_payload(payload)
    return stable_hash(clean)


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_REPORT_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_report_file_name(*, scope: str, evidence_report_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(evidence_report_id)}_aps_evidence_report_v1.json"


def expected_failure_file_name(*, scope: str, evidence_report_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(evidence_report_id)}_aps_evidence_report_failure_v1.json"


def resolve_limit_offset(*, limit_value: Any, offset_value: Any) -> tuple[int, int]:
    raw_limit = APS_REPORT_DEFAULT_LIMIT if limit_value is None else limit_value
    raw_offset = 0 if offset_value is None else offset_value

    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ValueError("invalid_limit") from None
    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        raise ValueError("invalid_offset") from None

    if limit < 1 or limit > APS_REPORT_MAX_LIMIT:
        raise ValueError("invalid_limit")
    if offset < 0:
        raise ValueError("invalid_offset")
    return limit, offset


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    citation_pack_id = str(payload.get("citation_pack_id") or "").strip() or None
    citation_pack_ref = str(payload.get("citation_pack_ref") or "").strip() or None
    if bool(citation_pack_id) == bool(citation_pack_ref):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)

    try:
        limit, offset = resolve_limit_offset(limit_value=payload.get("limit"), offset_value=payload.get("offset", 0))
    except ValueError as exc:
        raise ValueError(str(exc)) from None

    return {
        "citation_pack_id": citation_pack_id,
        "citation_pack_ref": citation_pack_ref,
        "limit": limit,
        "offset": offset,
        "persist_report": bool(payload.get("persist_report", False)),
    }


def derive_evidence_report_id(*, citation_pack_id: str, citation_pack_checksum: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_REPORT_SCHEMA_ID,
            APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
            APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
            str(citation_pack_id or ""),
            str(citation_pack_checksum or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_failure_report_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_REPORT_FAILURE_SCHEMA_ID,
            APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_section_id(*, citation_pack_id: str, citation_pack_checksum: str, group_id: str) -> str:
    return stable_hash(
        {
            "schema_id": APS_EVIDENCE_REPORT_SCHEMA_ID,
            "sectioning_contract_id": APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID,
            "citation_pack_id": str(citation_pack_id or ""),
            "citation_pack_checksum": str(citation_pack_checksum or ""),
            "group_id": str(group_id or ""),
        }
    )


def source_citation_pack_summary_payload(citation_pack_payload: dict[str, Any]) -> dict[str, Any]:
    source_bundle = dict(citation_pack_payload.get("source_bundle") or {})
    return {
        "schema_id": str(citation_pack_payload.get("schema_id") or citation_pack_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID),
        "schema_version": int(citation_pack_payload.get("schema_version") or citation_pack_contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION),
        "citation_pack_id": str(citation_pack_payload.get("citation_pack_id") or ""),
        "citation_pack_checksum": str(citation_pack_payload.get("citation_pack_checksum") or ""),
        "citation_pack_ref": str(citation_pack_payload.get("_citation_pack_ref") or citation_pack_payload.get("citation_pack_ref") or "") or None,
        "derivation_contract_id": str(
            citation_pack_payload.get("derivation_contract_id") or citation_pack_contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID
        ),
        "total_citations": int(citation_pack_payload.get("total_citations") or 0),
        "total_groups": int(citation_pack_payload.get("total_groups") or 0),
        "source_bundle": {
            **source_bundle,
            "bundle_ref": str(source_bundle.get("bundle_ref") or "") or None,
        },
    }


def section_title(*, section_ordinal: int, accession_number: str | None, content_id: str | None) -> str:
    normalized_accession = str(accession_number or "").strip() or None
    normalized_content_id = str(content_id or "").strip() or None
    if normalized_accession and normalized_content_id:
        return f"Accession {normalized_accession} / Content {normalized_content_id}"
    if normalized_accession:
        return f"Accession {normalized_accession}"
    if normalized_content_id:
        return f"Content {normalized_content_id}"
    return f"Evidence Group {int(section_ordinal):05d}"


def build_section_entry(citation: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation_id": str(citation.get("citation_id") or ""),
        "citation_label": str(citation.get("citation_label") or ""),
        "citation_ordinal": int(citation.get("citation_ordinal") or 0),
        "chunk_id": str(citation.get("chunk_id") or ""),
        "chunk_ordinal": int(citation.get("chunk_ordinal") or 0),
        "start_char": int(citation.get("start_char") or 0),
        "end_char": int(citation.get("end_char") or 0),
        "snippet_text": str(citation.get("snippet_text") or ""),
        "snippet_start_char": int(citation.get("snippet_start_char") or 0),
        "snippet_end_char": int(citation.get("snippet_end_char") or 0),
        "highlight_spans": [dict(item or {}) for item in list(citation.get("highlight_spans") or []) if isinstance(item, dict)],
    }


def build_sections_from_citation_pack(citation_pack_payload: dict[str, Any]) -> list[dict[str, Any]]:
    citations = [dict(item or {}) for item in list(citation_pack_payload.get("citations") or []) if isinstance(item, dict)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for citation in citations:
        group_id = str(citation.get("group_id") or "").strip()
        grouped.setdefault(group_id, []).append(citation)

    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: min(int(citation.get("citation_ordinal") or 0) for citation in item[1]),
    )
    citation_pack_id = str(citation_pack_payload.get("citation_pack_id") or "")
    citation_pack_checksum = str(citation_pack_payload.get("citation_pack_checksum") or "")
    sections: list[dict[str, Any]] = []
    for section_ordinal, (group_id, group_citations) in enumerate(ordered_groups, start=1):
        ordered_citations = sorted(group_citations, key=lambda item: int(item.get("citation_ordinal") or 0))
        first = ordered_citations[0] if ordered_citations else {}
        content_id = str(first.get("content_id") or "") or None
        accession_number = str(first.get("accession_number") or "").strip() or None
        sections.append(
            {
                "section_id": derive_section_id(
                    citation_pack_id=citation_pack_id,
                    citation_pack_checksum=citation_pack_checksum,
                    group_id=group_id,
                ),
                "section_ordinal": int(section_ordinal),
                "section_type": APS_REPORT_SECTION_TYPE,
                "group_id": group_id,
                "accession_number": accession_number,
                "content_id": content_id,
                "run_id": str(first.get("run_id") or ""),
                "target_id": str(first.get("target_id") or ""),
                "content_contract_id": str(first.get("content_contract_id") or ""),
                "chunking_contract_id": str(first.get("chunking_contract_id") or ""),
                "title": section_title(
                    section_ordinal=section_ordinal,
                    accession_number=accession_number,
                    content_id=content_id,
                ),
                "citation_count": len(ordered_citations),
                "citations": [build_section_entry(citation) for citation in ordered_citations],
            }
        )
    return sections
