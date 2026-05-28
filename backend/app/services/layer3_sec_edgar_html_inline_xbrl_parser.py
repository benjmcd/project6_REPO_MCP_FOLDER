from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_source_family_parse_receipt.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_source_family_parser_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_source_family_parser_status.v1"
SCHEMA_VERSION = 1
PARSER_MODE = "sec_edgar_html_inline_xbrl_source_family_parser_v1"
OPERATOR_DECISION = "parse_sec_edgar_html_inline_xbrl_source_family"
PARSER_STATE = "sec_edgar_html_inline_xbrl_source_family_parsed"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-parser"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-parser"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_source_family_parser_redaction_v1"

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "parser_mode",
    "operator_decision",
    "connector_receipt_id",
    "connector_receipt_hash",
    "connector_example_id",
    "live_source_artifact_receipt_id",
    "live_source_artifact_receipt_hash",
    "expected_source_artifact_receipt_hash",
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
    "parser_mode",
    "connector_receipt_hash",
    "connector_example_id",
    "live_source_artifact_receipt_hash",
    "source_artifact_receipt_hash",
    "content_sha256",
    "primary_document_hash",
    "document_inventory_hash",
    "content_order_hash",
    "table_candidate_inventory_hash",
    "inline_xbrl_marker_inventory_hash",
    "diagnostics_hash",
)
_DOCUMENT_RE = re.compile(r"<DOCUMENT>(?P<body>.*?)</DOCUMENT>", re.IGNORECASE | re.DOTALL)
_TEXT_RE = re.compile(r"<TEXT>(?P<text>.*?)</TEXT>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<([A-Z0-9-]+)>\s*([^\r\n<]*)", re.IGNORECASE)
_TABLE_RE = re.compile(r"<table\b(?P<body>.*?)</table>", re.IGNORECASE | re.DOTALL)
_IX_RE = re.compile(r"<\s*(ix:[A-Za-z0-9_.:-]+)\b[^>]*>", re.IGNORECASE)


def parse_sec_edgar_html_inline_xbrl_source_family(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "parser_mode", PARSER_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_operator_confirmation_required",
            "operator_confirmation=true is required before SEC EDGAR HTML/iXBRL source-family parsing.",
            blocked_fields=["operator_confirmation"],
        )

    connector_receipt_hash = _required_hash(request, "connector_receipt_hash")
    connector_receipt = (
        layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
            _required(request, "connector_receipt_id"),
            expected_connector_receipt_hash=connector_receipt_hash,
        )
    )
    connector_example, connector_acquisition = _connector_html_example(
        connector_receipt,
        connector_example_id=_required(request, "connector_example_id"),
    )
    live_receipt, content = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_bytes(
        _required(request, "live_source_artifact_receipt_id"),
        expected_live_source_artifact_receipt_hash=_required_hash(request, "live_source_artifact_receipt_hash"),
    )
    _validate_live_artifact_binding(request, connector_acquisition=connector_acquisition, live_receipt=live_receipt)
    text, encoding = _decode_content(content)
    parsed = _parse_complete_submission_text(text, connector_example=connector_example)
    diagnostics = _diagnostics(
        connector_example=connector_example,
        parsed=parsed,
        encoding=encoding,
        content_length=len(content),
    )
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "parser_mode": PARSER_MODE,
        "connector_receipt_hash": connector_receipt_hash,
        "connector_example_id": _required(request, "connector_example_id"),
        "live_source_artifact_receipt_hash": _required_hash(request, "live_source_artifact_receipt_hash"),
        "source_artifact_receipt_hash": _source_artifact(live_receipt)["source_artifact_receipt_hash"],
        "content_sha256": _source_artifact(live_receipt)["content_sha256"],
        "primary_document_hash": parsed["primary_document_hash"],
        "document_inventory_hash": stable_hash(parsed["document_inventory"]),
        "content_order_hash": stable_hash(parsed["content_order"]),
        "table_candidate_inventory_hash": stable_hash(parsed["table_candidate_inventory"]),
        "inline_xbrl_marker_inventory_hash": stable_hash(parsed["inline_xbrl_marker_inventory"]),
        "diagnostics_hash": stable_hash(diagnostics),
    }
    parser_hash = stable_hash({key: receipt_input[key] for key in RECEIPT_HASH_KEYS})
    request_binding = _read_request_binding(request_id)
    if request_binding and request_binding.get("parser_basis_hash") != parser_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL parser basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(parser_hash)
    if existing is not None:
        _write_request_binding(request_id, parser_hash, str(existing["parser_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, idempotent_replay=True, schema_id=SCHEMA_ID)

    receipt = {
        **receipt_input,
        "operator_decision": OPERATOR_DECISION,
        "parser_state": PARSER_STATE,
        "parser_receipt_hash": parser_hash,
        "parser_receipt_id": f"{RECEIPT_PREFIX}-{parser_hash[:24]}",
        "parser_receipt_ref": f"{RECEIPT_PREFIX}:{parser_hash[:24]}",
        "connector_receipt_id": _required(request, "connector_receipt_id"),
        "live_source_artifact_receipt_id": _required(request, "live_source_artifact_receipt_id"),
        "identity_binding": _identity_binding(connector_example=connector_example, live_receipt=live_receipt),
        "document_inventory": parsed["document_inventory"],
        "content_order": parsed["content_order"],
        "table_candidate_inventory": parsed["table_candidate_inventory"],
        "inline_xbrl_marker_inventory": parsed["inline_xbrl_marker_inventory"],
        "diagnostics": diagnostics,
        "negative_invariants": _negative_invariants(),
        "request_id_hash": _sha256_text(request_id),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, parser_hash, receipt["parser_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, idempotent_replay=False, schema_id=SCHEMA_ID)


def inspect_sec_edgar_html_inline_xbrl_source_family_parser_status(
    parser_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(parser_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-parser-status-{receipt['parser_receipt_hash'][:12]}",
        idempotent_replay=False,
        schema_id=STATUS_SCHEMA_ID,
    )


def read_sec_edgar_html_inline_xbrl_source_family_parser_receipt(
    parser_receipt_id: str,
    *,
    expected_parser_receipt_hash: str | None = None,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(parser_receipt_id)
    expected_hash = str(expected_parser_receipt_hash or "").strip()
    if expected_hash and receipt["parser_receipt_hash"] != expected_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL parser receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["parser_receipt_hash"],
        )
    return receipt


def reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge(
    connector_receipt: Mapping[str, Any],
    *,
    connector_example_id: str,
    retained_complete_submission_text: bytes,
) -> dict[str, Any]:
    connector_example, _connector_acquisition = _connector_html_example(
        connector_receipt,
        connector_example_id=connector_example_id,
    )
    text, encoding = _decode_content(retained_complete_submission_text)
    parsed = _parse_complete_submission_text(text, connector_example=connector_example)
    return {
        "connector_example": dict(connector_example),
        "encoding": encoding,
        "primary_document_text": _primary_document_text(
            text,
            primary_document_hash=str(connector_example.get("primary_document_hash") or ""),
        ),
        "parsed": parsed,
    }


def _connector_html_example(
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
            "sec_edgar_html_inline_xbrl_parser_connector_example_missing",
            "SEC EDGAR HTML/iXBRL parser requires an example present in connector manifest and acquisition receipts.",
            http_status=409,
            blocked_fields=["connector_example_id"],
        )
    roles = list(example.get("source_family_roles") or [])
    if "html_inline_xbrl_classified_not_parsed" not in roles:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_example_not_classified_html_inline_xbrl",
            "SEC EDGAR HTML/iXBRL parser only admits connector examples already classified as HTML/iXBRL.",
            http_status=409,
            blocked_fields=["connector_example_id"],
        )
    return example, acquisition


def _validate_live_artifact_binding(
    request: Mapping[str, Any],
    *,
    connector_acquisition: Mapping[str, Any],
    live_receipt: Mapping[str, Any],
) -> None:
    if str(connector_acquisition.get("live_source_artifact_receipt_hash") or "") != _required_hash(
        request,
        "live_source_artifact_receipt_hash",
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_live_artifact_hash_mismatch",
            "SEC EDGAR HTML/iXBRL parser requires the connector-acquired live source artifact.",
            http_status=409,
            blocked_fields=["live_source_artifact_receipt_hash"],
        )
    connector_artifact = _mapping(connector_acquisition, "source_artifact_receipt")
    live_artifact = _source_artifact(live_receipt)
    expected_source_hash = str(request.get("expected_source_artifact_receipt_hash") or "").strip()
    if expected_source_hash and expected_source_hash != str(live_artifact.get("source_artifact_receipt_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_source_artifact_hash_mismatch",
            "SEC EDGAR HTML/iXBRL parser source artifact hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["expected_source_artifact_receipt_hash"],
        )
    for field in ("source_artifact_receipt_hash", "source_artifact_ref_hash", "content_sha256", "content_length"):
        if str(connector_artifact.get(field) or "") != str(live_artifact.get(field) or ""):
            _blocked(
                "sec_edgar_html_inline_xbrl_parser_source_artifact_mismatch",
                "Connector and live source-artifact authority must bind the same retained source artifact.",
                http_status=409,
                blocked_fields=[field],
            )


def _parse_complete_submission_text(text: str, *, connector_example: Mapping[str, Any]) -> dict[str, Any]:
    document_inventory: list[dict[str, Any]] = []
    primary_document_hash = str(connector_example.get("primary_document_hash") or "")
    primary_matches: list[tuple[int, str]] = []
    for index, match in enumerate(_DOCUMENT_RE.finditer(text), start=1):
        body = match.group("body")
        metadata, doc_text = _document_metadata(body)
        filename_hash = _sha256_text(metadata["filename"]) if metadata["filename"] else ""
        text_hash = _sha256_text(doc_text)
        family = _document_family(doc_text, metadata)
        record = {
            "document_index": index,
            "document_type": metadata["type"],
            "sequence": metadata["sequence"],
            "filename_hash": filename_hash,
            "description_hash": _sha256_text(metadata["description"]) if metadata["description"] else "",
            "text_hash": text_hash,
            "text_length": len(doc_text),
            "source_start": match.start(),
            "source_end": match.end(),
            "source_end_semantics": "exclusive",
            "source_order_preserved": True,
            "document_family": family,
            "primary_document_match": filename_hash == primary_document_hash,
        }
        if record["primary_document_match"]:
            primary_matches.append((index, doc_text))
        document_inventory.append(record)
    if not document_inventory:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_document_inventory_missing",
            "SEC EDGAR HTML/iXBRL parser requires retained complete-submission text with DOCUMENT blocks.",
            http_status=409,
        )
    if len(primary_matches) != 1:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_primary_document_ambiguous",
            "SEC EDGAR HTML/iXBRL parser requires exactly one primary HTML/iXBRL document match.",
            http_status=409,
            blocked_fields=["primary_document_hash"],
        )
    primary_index, primary_text = primary_matches[0]
    if _document_family(primary_text, {}) not in {"filing_html", "inline_xbrl"}:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_primary_document_not_html_inline_xbrl",
            "SEC EDGAR HTML/iXBRL parser requires the primary document to be HTML or inline XBRL.",
            http_status=409,
            blocked_fields=["primary_document_hash"],
        )
    content_order = _text_segment_inventory(primary_text, primary_document_index=primary_index)
    table_inventory = _table_inventory(primary_text, primary_document_index=primary_index)
    marker_inventory = _inline_xbrl_marker_inventory(primary_text, primary_document_index=primary_index)
    return {
        "primary_document_hash": primary_document_hash,
        "document_inventory": document_inventory,
        "content_order": content_order,
        "table_candidate_inventory": table_inventory,
        "inline_xbrl_marker_inventory": marker_inventory,
    }


def _document_metadata(document_body: str) -> tuple[dict[str, str], str]:
    text_match = _TEXT_RE.search(document_body)
    tag_region = document_body[: text_match.start()] if text_match else document_body
    tags: dict[str, str] = {}
    for match in _TAG_RE.finditer(tag_region):
        key = match.group(1).strip().upper()
        value = match.group(2).strip()
        if key and value and key not in tags:
            tags[key] = value
    return (
        {
            "type": tags.get("TYPE", ""),
            "sequence": tags.get("SEQUENCE", ""),
            "filename": tags.get("FILENAME", ""),
            "description": tags.get("DESCRIPTION", ""),
        },
        text_match.group("text") if text_match else "",
    )


def _document_family(text: str, metadata: Mapping[str, Any]) -> str:
    lower = str(text or "").lstrip()[:2048].lower()
    filename = str(metadata.get("filename") or "").lower()
    if "xmlns:ix" in lower or "<ix:" in lower:
        return "inline_xbrl"
    if lower.startswith("<!doctype html") or lower.startswith("<html") or filename.endswith((".htm", ".html")):
        return "filing_html"
    if lower.startswith("<?xml") or lower.startswith("<xbrl") or filename.endswith(".xml"):
        return "xml_xbrl"
    return "other_document"


def _text_segment_inventory(text: str, *, primary_document_index: int) -> list[dict[str, Any]]:
    collector = _HtmlTextCollector()
    collector.feed(text)
    segments: list[dict[str, Any]] = []
    for index, item in enumerate(collector.segments[:100], start=1):
        normalized = re.sub(r"\s+", " ", item).strip()
        if not normalized:
            continue
        segments.append(
            {
                "primary_document_index": primary_document_index,
                "segment_index": index,
                "segment_hash": _sha256_text(normalized),
                "segment_length": len(normalized),
                "source_order_preserved": True,
            }
        )
    return segments


def _table_inventory(text: str, *, primary_document_index: int) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for index, match in enumerate(_TABLE_RE.finditer(text), start=1):
        table_text = match.group(0)
        tables.append(
            {
                "primary_document_index": primary_document_index,
                "table_candidate_index": index,
                "table_candidate_hash": _sha256_text(table_text),
                "source_start": match.start(),
                "source_end": match.end(),
                "source_end_semantics": "exclusive",
                "source_order_preserved": True,
                "dataset_version_materialized": False,
            }
        )
    return tables


def _inline_xbrl_marker_inventory(text: str, *, primary_document_index: int) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for index, match in enumerate(_IX_RE.finditer(text), start=1):
        markers.append(
            {
                "primary_document_index": primary_document_index,
                "marker_index": index,
                "marker_name_hash": _sha256_text(match.group(1).lower()),
                "marker_hash": _sha256_text(match.group(0)),
                "source_start": match.start(),
                "source_end": match.end(),
                "source_end_semantics": "exclusive",
                "source_order_preserved": True,
                "xbrl_fact_authority_created": False,
            }
        )
    return markers


class _HtmlTextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[str] = []

    def handle_data(self, data: str) -> None:
        text = str(data or "").strip()
        if text:
            self.segments.append(text)


def _identity_binding(*, connector_example: Mapping[str, Any], live_receipt: Mapping[str, Any]) -> dict[str, Any]:
    artifact = _source_artifact(live_receipt)
    return {
        "connector_example_id": str(connector_example.get("example_id") or ""),
        "cik_hash": str(connector_example.get("cik_hash") or ""),
        "accession_or_submission_id_hash": str(connector_example.get("accession_or_submission_id_hash") or ""),
        "form_type": str(connector_example.get("form_type") or ""),
        "filing_date": str(connector_example.get("filing_date") or ""),
        "report_period_present": bool(connector_example.get("report_period_present")),
        "company_name_hash": str(connector_example.get("company_name_hash") or ""),
        "source_family": str(connector_example.get("source_family") or ""),
        "source_family_roles": list(connector_example.get("source_family_roles") or []),
        "primary_document_hash": str(connector_example.get("primary_document_hash") or ""),
        "source_artifact_receipt_hash": str(artifact.get("source_artifact_receipt_hash") or ""),
        "source_artifact_ref_hash": str(artifact.get("source_artifact_ref_hash") or ""),
        "content_sha256": str(artifact.get("content_sha256") or ""),
    }


def _primary_document_text(text: str, *, primary_document_hash: str) -> str:
    matches: list[str] = []
    for match in _DOCUMENT_RE.finditer(text):
        metadata, doc_text = _document_metadata(match.group("body"))
        filename_hash = _sha256_text(metadata["filename"]) if metadata["filename"] else ""
        if filename_hash == primary_document_hash:
            matches.append(doc_text)
    if len(matches) != 1:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_primary_document_ambiguous",
            "SEC EDGAR HTML/iXBRL parser requires exactly one primary document for material bridge use.",
            http_status=409,
            blocked_fields=["primary_document_hash"],
        )
    return matches[0]


def _diagnostics(
    *,
    connector_example: Mapping[str, Any],
    parsed: Mapping[str, Any],
    encoding: str,
    content_length: int,
) -> dict[str, Any]:
    return {
        "encoding": encoding,
        "content_length": content_length,
        "html_inline_xbrl_classified_before_parser": "html_inline_xbrl_classified_not_parsed"
        in list(connector_example.get("source_family_roles") or []),
        "document_inventory_count": len(parsed["document_inventory"]),
        "ordered_text_segment_count": len(parsed["content_order"]),
        "html_table_candidate_count": len(parsed["table_candidate_inventory"]),
        "inline_xbrl_marker_count": len(parsed["inline_xbrl_marker_inventory"]),
        "generic_text_downgrade_performed": False,
        "dataset_version_created": False,
        "gate_b_mutated": False,
        "xbrl_fact_authority_created": False,
        "full_sec_support_claimed": False,
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
        "parser_mode": PARSER_MODE,
        "operator_decision": OPERATOR_DECISION,
        "parser_state": receipt["parser_state"],
        "parser_receipt_id": receipt["parser_receipt_id"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "parser_receipt_ref": receipt["parser_receipt_ref"],
        "idempotent_replay": idempotent_replay,
        "connector_receipt_id": receipt["connector_receipt_id"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "connector_example_id": receipt["connector_example_id"],
        "live_source_artifact_receipt_id": receipt["live_source_artifact_receipt_id"],
        "live_source_artifact_receipt_hash": receipt["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": receipt["source_artifact_receipt_hash"],
        "identity_binding": dict(receipt["identity_binding"]),
        "document_inventory": list(receipt["document_inventory"]),
        "document_inventory_hash": receipt["document_inventory_hash"],
        "content_order": list(receipt["content_order"]),
        "content_order_hash": receipt["content_order_hash"],
        "table_candidate_inventory": list(receipt["table_candidate_inventory"]),
        "table_candidate_inventory_hash": receipt["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory": list(receipt["inline_xbrl_marker_inventory"]),
        "inline_xbrl_marker_inventory_hash": receipt["inline_xbrl_marker_inventory_hash"],
        "diagnostics": dict(receipt["diagnostics"]),
        "diagnostics_hash": receipt["diagnostics_hash"],
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "retained_artifact_parsed_server_side": True,
            "source_order_preserved": True,
            "materialization_deferred": True,
            "next_material_bridge_gap": True,
        },
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made": False,
            "cache_hit_avoids_network_request": True,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "use this receipt as SEC HTML/iXBRL source-family parse authority",
            "select SEC HTML/iXBRL material bridge or XBRL fact authority after current-main sync",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL parser would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL parser does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_unknown_field",
            "SEC EDGAR HTML/iXBRL parser fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL parser requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _read_receipt_by_hash(parser_hash: str) -> dict[str, Any] | None:
    path = _receipts_dir() / f"{RECEIPT_PREFIX}-{parser_hash[:24]}.json"
    if not path.exists():
        return None
    return _read_verified_receipt(path.stem)


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL parser status requires a server-issued parser receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_html_inline_xbrl_parser_receipt_id"],
        )
    path = _receipts_dir() / f"{receipt_id}.json"
    if not path.exists():
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_receipt_missing",
            "SEC EDGAR HTML/iXBRL parser receipt was not found.",
            http_status=404,
            blocked_fields=["sec_edgar_html_inline_xbrl_parser_receipt_id"],
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL parser receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("parser_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_receipt_invalid",
            "SEC EDGAR HTML/iXBRL parser receipt is invalid or mismatched.",
            http_status=409,
        )
    expected_hash = stable_hash({key: receipt[key] for key in RECEIPT_HASH_KEYS})
    if receipt.get("parser_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL parser receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipts_dir() / f"{receipt['parser_receipt_id']}.json"
    if target.exists():
        existing = _read_verified_receipt(target.stem)
        if existing.get("parser_receipt_hash") != receipt.get("parser_receipt_hash"):
            _blocked(
                "sec_edgar_html_inline_xbrl_parser_receipt_write_race_conflict",
                "Concurrent SEC EDGAR HTML/iXBRL parser receipt write produced a conflicting authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_verified_receipt(target.stem)
        if existing.get("parser_receipt_hash") != receipt.get("parser_receipt_hash"):
            _blocked(
                "sec_edgar_html_inline_xbrl_parser_receipt_write_race_conflict",
                "Concurrent SEC EDGAR HTML/iXBRL parser receipt write produced a conflicting authority.",
                http_status=409,
            )


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL parser request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, parser_basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_parser_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "parser_basis_hash": parser_basis_hash,
        "parser_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("parser_basis_hash") != parser_basis_hash or existing.get("parser_receipt_id") != receipt_id:
            _blocked(
                "sec_edgar_html_inline_xbrl_parser_request_binding_conflict",
                "SEC EDGAR HTML/iXBRL parser request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_request_binding(request_id) or {}
        if existing.get("parser_basis_hash") != parser_basis_hash or existing.get("parser_receipt_id") != receipt_id:
            _blocked(
                "sec_edgar_html_inline_xbrl_parser_request_binding_write_race_conflict",
                "Concurrent SEC EDGAR HTML/iXBRL parser request binding write produced a conflicting authority.",
                http_status=409,
            )


def _source_artifact(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(receipt, "source_artifact_receipt")


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_authority_missing",
            f"SEC EDGAR HTML/iXBRL parser requires {key}.",
            http_status=409,
            blocked_fields=[key],
        )
    return item


def _decode_content(content: bytes) -> tuple[str, str]:
    try:
        return content.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        try:
            return content.decode("cp1252"), "cp1252"
        except UnicodeDecodeError as exc:
            _blocked(
                "sec_edgar_html_inline_xbrl_parser_decode_failed",
                "SEC EDGAR retained artifact could not be decoded as supported filing text.",
                http_status=409,
                blocked_fields=[exc.__class__.__name__],
            )
    return "", ""


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=FORBIDDEN_REQUEST_FIELDS, prefix=prefix)


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_changed": False,
        "sec_edgar_live_network_fetch_performed_by_parser": False,
        "submissions_lookup_performed_by_parser": False,
        "arbitrary_url_or_upload_parse_admitted": False,
        "generic_text_downgrade_performed": False,
        "complete_submission_text_downstream_mutation_enabled": False,
        "dataset_version_creation_admitted": False,
        "gate_b_mutation_admitted": False,
        "material_bridge_admitted": False,
        "xml_xbrl_fact_authority_created": False,
        "financial_statement_semantics_enabled": False,
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
        return contains_forbidden_ref(value)
    return False


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_required_field_missing",
            "A required SEC EDGAR HTML/iXBRL parser field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_hash_invalid",
            "SEC EDGAR HTML/iXBRL parser hash fields must be SHA-256 hex strings.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_parser_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL parser request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_parser_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL parser requires the existing Layer 3 storage root.",
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
