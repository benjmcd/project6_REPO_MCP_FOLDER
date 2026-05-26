from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html as html_lib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_authority.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_authority_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_authority_status.v1"
SCHEMA_VERSION = 1
FACT_AUTHORITY_MODE = "sec_edgar_html_inline_xbrl_parser_to_fact_authority_v1"
OPERATOR_DECISION = "derive_sec_edgar_html_inline_xbrl_fact_authority"
READY_STATE = "sec_edgar_html_inline_xbrl_fact_authority_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_fact_authority_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
PARSER_FAMILY = "sec_edgar_html_inline_xbrl_source_family_parser_v1"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-fact-authority"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-fact-authority"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_fact_authority_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_fact_authority_hash_v1"

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "fact_authority_mode",
    "operator_decision",
    "parser_receipt_id",
    "parser_receipt_hash",
    "expected_connector_receipt_hash",
    "expected_live_source_artifact_receipt_hash",
    "expected_source_artifact_receipt_hash",
    "expected_content_sha256",
    "expected_primary_document_hash",
    "expected_document_inventory_hash",
    "expected_content_order_hash",
    "expected_table_candidate_inventory_hash",
    "expected_inline_xbrl_marker_inventory_hash",
    "operator_confirmation",
    "actor",
}
_FORBIDDEN_INPUT_KEYS = {
    "args",
    "artifact_bytes",
    "browser_storage",
    "command",
    "connector_credentials",
    "connector_dispatch",
    "connector_url",
    "directory",
    "file",
    "file_bytes",
    "file_path",
    "files",
    "filing_url",
    "frontend_authority",
    "full_mockup_activation",
    "html",
    "local_path",
    "path",
    "paths",
    "process",
    "provider_credentials",
    "provider_url",
    "rag_vector_index",
    "raw_html",
    "raw_path",
    "raw_url",
    "runtime_db_write",
    "sec_companyfacts_api",
    "source_expansion",
    "source_upload",
    "source_url",
    "standalone_xml_xbrl",
    "stderr",
    "stdout",
    "storage_dir",
    "taxonomy_network_resolution",
    "url",
    "urls",
}
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_IX_FACT_RE = re.compile(
    r"<\s*(?P<tag>ix:(?:nonFraction|nonNumeric|fraction))\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)</\s*(?P=tag)\s*>",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(
    r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+))"
)
_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)


def derive_sec_edgar_html_inline_xbrl_fact_authority(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "fact_authority_mode", FACT_AUTHORITY_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    parser_receipt_id = _required(request, "parser_receipt_id")
    parser_receipt_hash = _required_hash(request, "parser_receipt_hash")
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )

    parser_receipt = layer3_sec_edgar_html_inline_xbrl_parser.read_sec_edgar_html_inline_xbrl_source_family_parser_receipt(
        parser_receipt_id,
        expected_parser_receipt_hash=parser_receipt_hash,
    )
    expected_hashes = _expected_hashes(request, parser_receipt)
    connector_receipt = layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
        str(parser_receipt["connector_receipt_id"]),
        expected_connector_receipt_hash=expected_hashes["connector_receipt_hash"],
    )
    live_receipt, content = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_bytes(
        str(parser_receipt["live_source_artifact_receipt_id"]),
        expected_live_source_artifact_receipt_hash=expected_hashes["live_source_artifact_receipt_hash"],
    )
    _validate_live_source_binding(parser_receipt, live_receipt, content, expected_hashes=expected_hashes)
    reparsed = layer3_sec_edgar_html_inline_xbrl_parser.reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge(
        connector_receipt,
        connector_example_id=str(parser_receipt["connector_example_id"]),
        retained_complete_submission_text=content,
    )
    parsed = reparsed.get("parsed") if isinstance(reparsed.get("parsed"), Mapping) else {}
    _validate_reparse_binding(parser_receipt, parsed, expected_hashes=expected_hashes)
    primary_document = str(reparsed.get("primary_document_text") or "")
    facts, diagnostics = _fact_inventory(primary_document, parser_receipt=parser_receipt, parsed=parsed)
    fact_inventory_hash = stable_hash(facts)
    diagnostics_hash = stable_hash(diagnostics)
    receipt_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "fact_authority_mode": FACT_AUTHORITY_MODE,
            "parser_receipt_hash": parser_receipt_hash,
            "connector_receipt_hash": expected_hashes["connector_receipt_hash"],
            "live_source_artifact_receipt_hash": expected_hashes["live_source_artifact_receipt_hash"],
            "source_artifact_receipt_hash": expected_hashes["source_artifact_receipt_hash"],
            "content_sha256": expected_hashes["content_sha256"],
            "primary_document_hash": expected_hashes["primary_document_hash"],
            "document_inventory_hash": expected_hashes["document_inventory_hash"],
            "content_order_hash": expected_hashes["content_order_hash"],
            "table_candidate_inventory_hash": expected_hashes["table_candidate_inventory_hash"],
            "inline_xbrl_marker_inventory_hash": expected_hashes["inline_xbrl_marker_inventory_hash"],
            "fact_inventory_hash": fact_inventory_hash,
            "diagnostics_hash": diagnostics_hash,
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    binding = _read_request_binding(request_id)
    if binding and binding.get("fact_authority_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL fact authority basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["fact_authority_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "fact_authority_mode": FACT_AUTHORITY_MODE,
        "operator_decision": OPERATOR_DECISION,
        "fact_authority_state": READY_STATE,
        "fact_authority_receipt_id": receipt_id,
        "fact_authority_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "fact_authority_receipt_hash": receipt_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_receipt_id": parser_receipt_id,
        "parser_receipt_hash": parser_receipt_hash,
        "connector_receipt_hash": expected_hashes["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": expected_hashes["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": expected_hashes["source_artifact_receipt_hash"],
        "content_sha256": expected_hashes["content_sha256"],
        "primary_document_hash": expected_hashes["primary_document_hash"],
        "document_inventory_hash": expected_hashes["document_inventory_hash"],
        "content_order_hash": expected_hashes["content_order_hash"],
        "table_candidate_inventory_hash": expected_hashes["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": expected_hashes["inline_xbrl_marker_inventory_hash"],
        "fact_inventory": facts,
        "fact_count": len(facts),
        "fact_inventory_hash": fact_inventory_hash,
        "diagnostics": diagnostics,
        "diagnostics_hash": diagnostics_hash,
        "authority_hashes": {
            "parser_receipt_hash": parser_receipt_hash,
            **expected_hashes,
            "fact_inventory_hash": fact_inventory_hash,
            "diagnostics_hash": diagnostics_hash,
            "fact_authority_receipt_hash": receipt_hash,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_fact_authority_status(receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-fact-authority-status-{receipt['fact_authority_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def read_sec_edgar_html_inline_xbrl_fact_authority_receipt(
    receipt_id: str,
    *,
    expected_fact_authority_receipt_hash: str | None = None,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    expected_hash = str(expected_fact_authority_receipt_hash or "").strip()
    if expected_hash and receipt["fact_authority_receipt_hash"] != expected_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact authority receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["fact_authority_receipt_hash"],
        )
    return receipt


def _fact_inventory(
    primary_document: str,
    *,
    parser_receipt: Mapping[str, Any],
    parsed: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    marker_inventory = list(parser_receipt.get("inline_xbrl_marker_inventory") or [])
    if not marker_inventory:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_no_inline_xbrl_markers",
            "SEC EDGAR HTML/iXBRL fact authority requires parser marker inventory.",
            http_status=409,
            blocked_fields=["inline_xbrl_marker_inventory_hash"],
        )
    table_ranges = _table_ranges(parsed)
    facts: list[dict[str, Any]] = []
    diagnostics = {
        "marker_inventory_count": len(marker_inventory),
        "fact_element_count": 0,
        "unsupported_marker_shape": 0,
        "missing_context_ref": 0,
        "missing_unit_ref": 0,
        "continued_fact_unresolved": 0,
        "html_parse_warning": 0,
        "empty_fact_value": 0,
        "duplicate_fact_key": 0,
        "non_inline_xbrl_primary_document": False,
        "raw_authority_rejected": True,
        "financial_statement_semantics_assigned": False,
        "taxonomy_network_resolution_performed": False,
    }
    seen_keys: set[str] = set()
    for index, match in enumerate(_IX_FACT_RE.finditer(primary_document), start=1):
        attrs = _attrs(match.group("attrs"))
        qname = str(attrs.get("name") or "").strip()
        prefix, local = _split_qname(qname)
        value = _normalise_text(match.group("body"))
        if not value:
            diagnostics["empty_fact_value"] += 1
        if not attrs.get("contextRef"):
            diagnostics["missing_context_ref"] += 1
        if match.group("tag").lower() in {"ix:nonfraction", "ix:fraction"} and not attrs.get("unitRef"):
            diagnostics["missing_unit_ref"] += 1
        if attrs.get("continuedAt"):
            diagnostics["continued_fact_unresolved"] += 1
        table_anchor = _table_anchor(match.start(), table_ranges)
        fact_key = stable_hash(
            {
                "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
                "marker_order_index": index,
                "source_start": match.start(),
                "source_end": match.end(),
                "qualified_name": qname,
                "value_hash": _sha256_text(value),
            }
        )
        if fact_key in seen_keys:
            diagnostics["duplicate_fact_key"] += 1
        seen_keys.add(fact_key)
        facts.append(
            {
                "fact_id_or_order_key": fact_key,
                "marker_order_index": index,
                "element_name": match.group("tag").lower(),
                "qualified_name": qname,
                "namespace_prefix": prefix,
                "local_name": local,
                "context_ref_hash": _optional_hash(attrs.get("contextRef")),
                "unit_ref_hash": _optional_hash(attrs.get("unitRef")),
                "decimals_or_precision": str(attrs.get("decimals") or attrs.get("precision") or ""),
                "scale_or_format": str(attrs.get("scale") or attrs.get("format") or ""),
                "continued_fact_hash_if_present": _optional_hash(attrs.get("continuedAt")),
                "source_order_hash": stable_hash(
                    {
                        "primary_document_hash": parser_receipt["primary_document_hash"],
                        "marker_order_index": index,
                        "source_start": match.start(),
                        "source_end": match.end(),
                    }
                ),
                "source_artifact_receipt_hash": str(parser_receipt["source_artifact_receipt_hash"]),
                "primary_document_hash": str(parser_receipt["primary_document_hash"]),
                "value_hash": _sha256_text(value),
                "value_length": len(value),
                "value_redacted": True,
                "table_candidate_anchor_hash": table_anchor,
                "financial_statement_semantics": None,
            }
        )
    diagnostics["fact_element_count"] = len(facts)
    diagnostics["unsupported_marker_shape"] = max(len(marker_inventory) - len(facts), 0)
    if not facts:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_no_extractable_facts",
            "SEC EDGAR HTML/iXBRL fact authority found no inline XBRL fact elements in the primary document.",
            http_status=409,
            blocked_fields=["primary_document_hash"],
        )
    return facts, diagnostics


def _expected_hashes(request: Mapping[str, Any], parser_receipt: Mapping[str, Any]) -> dict[str, str]:
    mapping = {
        "connector_receipt_hash": "expected_connector_receipt_hash",
        "live_source_artifact_receipt_hash": "expected_live_source_artifact_receipt_hash",
        "source_artifact_receipt_hash": "expected_source_artifact_receipt_hash",
        "content_sha256": "expected_content_sha256",
        "primary_document_hash": "expected_primary_document_hash",
        "document_inventory_hash": "expected_document_inventory_hash",
        "content_order_hash": "expected_content_order_hash",
        "table_candidate_inventory_hash": "expected_table_candidate_inventory_hash",
        "inline_xbrl_marker_inventory_hash": "expected_inline_xbrl_marker_inventory_hash",
    }
    return {authority_key: _expected_or_authority(request, request_key, parser_receipt, authority_key) for authority_key, request_key in mapping.items()}


def _validate_live_source_binding(
    parser_receipt: Mapping[str, Any],
    live_receipt: Mapping[str, Any],
    content: bytes,
    *,
    expected_hashes: Mapping[str, str],
) -> None:
    artifact = _source_artifact(live_receipt)
    checks = {
        "source_artifact_receipt_hash": str(artifact.get("source_artifact_receipt_hash") or ""),
        "content_sha256": hashlib.sha256(content).hexdigest(),
    }
    for key, received in checks.items():
        if received != expected_hashes[key] or str(parser_receipt.get(key) or "") != expected_hashes[key]:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_authority_source_artifact_mismatch",
                "SEC EDGAR HTML/iXBRL fact authority requires parser and live source-artifact authority to match.",
                http_status=409,
                blocked_fields=[key],
            )


def _validate_reparse_binding(
    parser_receipt: Mapping[str, Any],
    parsed: Mapping[str, Any],
    *,
    expected_hashes: Mapping[str, str],
) -> None:
    received = {
        "primary_document_hash": str(parsed.get("primary_document_hash") or ""),
        "document_inventory_hash": stable_hash(parsed.get("document_inventory") or []),
        "content_order_hash": stable_hash(parsed.get("content_order") or []),
        "table_candidate_inventory_hash": stable_hash(parsed.get("table_candidate_inventory") or []),
        "inline_xbrl_marker_inventory_hash": stable_hash(parsed.get("inline_xbrl_marker_inventory") or []),
    }
    mismatches = [
        key
        for key, value in received.items()
        if value != expected_hashes[key] or str(parser_receipt.get(key) or "") != expected_hashes[key]
    ]
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_parser_reparse_mismatch",
            "SEC EDGAR HTML/iXBRL fact authority requires retained content to reparse to the parser receipt.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=schema_id),
        "mode": FACT_AUTHORITY_MODE,
        "fact_authority_mode": FACT_AUTHORITY_MODE,
        "operator_decision": OPERATOR_DECISION,
        "fact_authority_state": receipt["fact_authority_state"],
        "fact_authority_receipt_id": receipt["fact_authority_receipt_id"],
        "fact_authority_receipt_ref": receipt["fact_authority_receipt_ref"],
        "fact_authority_receipt_hash": receipt["fact_authority_receipt_hash"],
        "idempotent_replay": idempotent_replay,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_receipt_id": receipt["parser_receipt_id"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": receipt["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": receipt["source_artifact_receipt_hash"],
        "content_sha256": receipt["content_sha256"],
        "primary_document_hash": receipt["primary_document_hash"],
        "document_inventory_hash": receipt["document_inventory_hash"],
        "content_order_hash": receipt["content_order_hash"],
        "table_candidate_inventory_hash": receipt["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": receipt["inline_xbrl_marker_inventory_hash"],
        "fact_inventory": list(receipt["fact_inventory"]),
        "fact_count": receipt["fact_count"],
        "fact_inventory_hash": receipt["fact_inventory_hash"],
        "diagnostics": dict(receipt["diagnostics"]),
        "diagnostics_hash": receipt["diagnostics_hash"],
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "fact_count": receipt["fact_count"],
            "fact_inventory_hash": receipt["fact_inventory_hash"],
            "diagnostics_hash": receipt["diagnostics_hash"],
            "source_order_preserved": True,
            "marker_order_preserved": True,
            "raw_values_returned": False,
            "financial_statement_semantics_assigned": False,
            "next_allowed_actions": [
                "select_sec_edgar_html_inline_xbrl_fact_authority_to_layer3_material_or_evidence_authority",
                "inspect_sec_edgar_html_inline_xbrl_fact_authority_status",
            ],
        },
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made": False,
            "cache_hit_avoids_network_request": True,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "select SEC HTML/iXBRL fact-authority-to-Layer-3 material or evidence bridge",
            "inspect this fact authority receipt status",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL fact authority would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _blocked_response(*, request_id: str, parser_receipt_hash: str, reasons: list[dict[str, Any]]) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": FACT_AUTHORITY_MODE,
        "fact_authority_mode": FACT_AUTHORITY_MODE,
        "operator_decision": OPERATOR_DECISION,
        "fact_authority_state": BLOCKED_STATE,
        "fact_authority_receipt_id": None,
        "fact_authority_receipt_ref": None,
        "fact_authority_receipt_hash": None,
        "idempotent_replay": False,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_receipt_hash": parser_receipt_hash,
        "fact_count": 0,
        "fact_inventory_hash": None,
        "diagnostics_hash": None,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "next_allowed_actions": ["refresh_sec_edgar_html_inline_xbrl_parser_receipt"],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["refresh SEC HTML/iXBRL parser receipt"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_blocked_response_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL fact authority blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL fact authority rejects caller paths, URLs, HTML, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_unknown_field",
            "SEC EDGAR HTML/iXBRL fact authority fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL fact authority requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _expected_or_authority(request: Mapping[str, Any], request_key: str, authority: Mapping[str, Any], authority_key: str) -> str:
    value = str(request.get(request_key) or authority.get(authority_key) or "").strip()
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_authority_{request_key}_invalid",
            "SEC EDGAR HTML/iXBRL fact authority requires SHA-256 authority hashes.",
            blocked_fields=[request_key],
        )
    if str(authority.get(authority_key) or "") != value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_authority_{authority_key}_mismatch",
            "SEC EDGAR HTML/iXBRL fact authority hash is stale or mismatched.",
            http_status=409,
            blocked_fields=[request_key],
        )
    return value


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["fact_authority_receipt_id"]))
    if target.exists():
        _read_verified_receipt(target.stem)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")


def _read_receipt_by_hash(receipt_hash: str) -> dict[str, Any] | None:
    path = _receipt_path(f"{RECEIPT_PREFIX}-{receipt_hash[:24]}")
    if not path.exists():
        return None
    return _read_verified_receipt(path.stem)


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL fact authority status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["fact_authority_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_receipt_missing",
            "SEC EDGAR HTML/iXBRL fact authority receipt was not found.",
            http_status=404,
            blocked_fields=["fact_authority_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL fact authority receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("fact_authority_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_receipt_invalid",
            "SEC EDGAR HTML/iXBRL fact authority receipt is invalid or mismatched.",
            http_status=409,
        )
    if not _is_hash(str(receipt.get("fact_authority_receipt_hash") or "")):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_receipt_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact authority receipt hash is invalid.",
            http_status=409,
        )
    return receipt


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL fact authority request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_authority_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "fact_authority_basis_hash": basis_hash,
        "fact_authority_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("fact_authority_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_authority_request_binding_conflict",
                "SEC EDGAR HTML/iXBRL fact authority request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _source_artifact(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    artifact = receipt.get("source_artifact_receipt")
    if not isinstance(artifact, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_source_artifact_missing",
            "SEC EDGAR HTML/iXBRL fact authority requires live source-artifact authority.",
            http_status=409,
        )
    return artifact


def _table_ranges(parsed: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in parsed.get("table_candidate_inventory") or []
        if isinstance(item, Mapping) and "source_start" in item and "source_end" in item
    ]


def _table_anchor(position: int, table_ranges: list[dict[str, Any]]) -> str | None:
    for item in table_ranges:
        if int(item.get("source_start") or -1) <= position <= int(item.get("source_end") or -1):
            return str(item.get("table_candidate_hash") or "") or None
    return None


def _attrs(text: str) -> dict[str, str]:
    return {match.group(1): next(group for group in match.groups()[1:] if group is not None) for match in _ATTR_RE.finditer(text)}


def _normalise_text(text: str) -> str:
    stripped = _TAG_RE.sub(" ", str(text or ""))
    return re.sub(r"\s+", " ", html_lib.unescape(stripped)).strip()


def _split_qname(qname: str) -> tuple[str, str]:
    if ":" in qname:
        prefix, local = qname.split(":", 1)
        return prefix, local
    return "", qname


def _optional_hash(value: Any) -> str | None:
    text = str(value or "").strip()
    return _sha256_text(text) if text else None


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in _FORBIDDEN_INPUT_KEYS:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(nested, child))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_find_forbidden_nested_fields(nested, f"{prefix}[{index}]"))
    elif isinstance(value, str) and (_RAW_URL_RE.search(value) or _LOCAL_PATH_RE.search(value)):
        found.append(prefix or "request_body")
    return found


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return bool(_LOCAL_PATH_RE.search(text) or text.startswith(("http://", "https://", "file://", "\\\\")))
    return False


def _negative_invariants() -> dict[str, bool]:
    return {
        "live_sec_network_fetch_performed_by_fact_authority": False,
        "submissions_lookup_runtime_performed_by_fact_authority": False,
        "browser_supplied_html_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_local_path_admitted": False,
        "artifact_bytes_admitted": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_enabled": False,
        "fact_to_statement_classification_enabled": False,
        "material_bridge_mutated": False,
        "gate_b_mutated": False,
        "downstream_proof_mutated": False,
        "candidate_b_default_scope_changed": False,
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "source_expansion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
    }


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_authority_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL fact authority requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _base_response(*, request_id: str, status: str, schema_id: str) -> dict[str, Any]:
    return {"schema_id": schema_id, "schema_version": SCHEMA_VERSION, "request_id": request_id, "server_time": _server_time(), "status": status}


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_authority_{key}_missing",
            f"SEC EDGAR HTML/iXBRL fact authority requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_authority_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL fact authority requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_authority_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL fact authority request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


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
