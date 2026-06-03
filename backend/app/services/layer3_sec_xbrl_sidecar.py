from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
)
from app.services.layer3_sec_xbrl_public_authority_guard import (
    any_url_reference_found,
    windows_local_path_start_reference_found,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar_status.v1"
SCHEMA_VERSION = 1
SIDECAR_MODE = "sec_edgar_arelle_resolved_fact_authority_sidecar_v1"
OPERATOR_DECISION = "derive_sec_edgar_arelle_resolved_fact_authority_sidecar"
READY_STATE = "sec_edgar_arelle_resolved_fact_authority_sidecar_ready"
BLOCKED_STATE = "sec_edgar_arelle_resolved_fact_authority_sidecar_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
ADAPTER_ID = "arelle_resolved_fact_authority_adapter"
ARELLE_PACKAGE = "arelle-release"
ARELLE_VERSION = "2.41.3"
ADAPTER_VERSION = f"{ADAPTER_ID}:{ARELLE_PACKAGE}=={ARELLE_VERSION}"
RECEIPT_PREFIX = "sec-edgar-arelle-resolved-fact-authority"
RECEIPT_DIR = "layer3-sec-edgar-arelle-resolved-fact-authority"
INTERNAL_VALUE_STORE_SCHEMA_ID = "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1"
INTERNAL_VALUE_STORE_DIR = "internal-value-stores"
VALUE_SEMANTICS_ID = "arelle_effective_canonical_value_v1"
REDACTION_POLICY_ID = "sec_edgar_arelle_resolved_fact_authority_sidecar_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_arelle_resolved_fact_authority_sidecar_hash_v1"
DEFAULT_TIMEOUT_SECONDS = 120
MIN_MAX_FACTS = 100_000
DEFAULT_MAX_FACTS = 100_000

ARELLE_SUBPROCESS_RUNNER: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "sidecar_mode",
    "operator_decision",
    "parser_receipt_id",
    "parser_receipt_hash",
    "regex_fact_authority_receipt_id",
    "regex_fact_authority_receipt_hash",
    "companyfacts_standard_fact_count",
    "companyfacts_oracle_confidence",
    "expected_connector_receipt_hash",
    "expected_live_source_artifact_receipt_hash",
    "expected_source_artifact_receipt_hash",
    "expected_content_sha256",
    "expected_primary_document_hash",
    "expected_document_inventory_hash",
    "expected_content_order_hash",
    "expected_table_candidate_inventory_hash",
    "expected_inline_xbrl_marker_inventory_hash",
    "max_facts",
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
    "source_expansion",
    "source_upload",
    "source_url",
    "standalone_xml_xbrl",
    "stderr",
    "stdout",
    "storage_dir",
    "url",
    "urls",
}
_DOCUMENT_RE = re.compile(r"<DOCUMENT>(?P<body>.*?)</DOCUMENT>", re.IGNORECASE | re.DOTALL)
_TEXT_RE = re.compile(r"<TEXT>(?P<text>.*?)</TEXT>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<([A-Z0-9-]+)>\s*([^\r\n<]*)", re.IGNORECASE)
_SEC_XBRL_WRAPPER_RE = re.compile(r"^\s*<XBRL>\s*(?P<text>.*?)(?:\s*</XBRL>\s*)?$", re.IGNORECASE | re.DOTALL)
_XMLNS_RE = re.compile(r"xmlns:([A-Za-z_][\w.-]*)\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
_INLINE_XBRL_NAMESPACES = frozenset({"http://www.xbrl.org/2013/inlineXBRL", "http://www.xbrl.org/2008/inlineXBRL"})
_SAFE_ARELLE_ERROR_RE = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")


def derive_sec_edgar_arelle_resolved_fact_authority_sidecar(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "sidecar_mode", SIDECAR_MODE)
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
    if not primary_document.strip():
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("primary_document_empty")],
        )

    max_facts = _max_facts(request)
    regex_fact = _optional_regex_fact_authority(request)
    submission_documents = _submission_documents(content, primary_document_hash=expected_hashes["primary_document_hash"])
    independent_inline_facts = _independent_inline_fact_tally(submission_documents)
    arelle = _run_arelle(primary_document=primary_document, max_facts=max_facts, submission_documents=submission_documents)
    if arelle.get("status") != "ready":
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=list(arelle.get("reasons") or [_reason("arelle_unavailable")]),
        )
    independent_count = int(independent_inline_facts.get("inline_fact_count") or 0)
    arelle_count = int(arelle.get("fact_count") or 0)
    if independent_count > arelle_count:
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                _reason(
                    "arelle_independent_inline_fact_count_mismatch",
                    independent_inline_fact_count=independent_count,
                    arelle_fact_count=arelle_count,
                    independent_inline_fact_tally_hash=stable_hash(independent_inline_facts.get("document_tally") or []),
                )
            ],
        )

    local_facts, value_records = _local_facts(arelle["facts"], parser_receipt=parser_receipt)
    redacted_facts = [_redacted_fact(fact) for fact in local_facts]
    coverage = _coverage_stats(redacted_facts)
    internal_value_store_enabled = _arelle_internal_value_store_enabled()
    internal_value_store_hash = stable_hash(value_records) if internal_value_store_enabled else None
    internal_value_store = _internal_value_store_metadata(
        enabled=internal_value_store_enabled,
        value_store_hash=internal_value_store_hash,
        value_record_count=len(value_records) if internal_value_store_enabled else 0,
    )
    diagnostics = _diagnostics(
        arelle=arelle,
        coverage=coverage,
        max_facts=max_facts,
        independent_inline_facts=independent_inline_facts,
        internal_value_store_enabled=internal_value_store_enabled,
    )
    resolved_fact_inventory_hash = stable_hash(redacted_facts)
    local_value_inventory_hash = stable_hash([fact["value_hash"] for fact in redacted_facts])
    diagnostics_hash = stable_hash(diagnostics)
    regex_count = _regex_count(regex_fact)
    parity = _parity(
        regex_count=regex_count,
        arelle_count=len(redacted_facts),
        companyfacts_count=request.get("companyfacts_standard_fact_count"),
        confidence=str(request.get("companyfacts_oracle_confidence") or ""),
    )
    receipt_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "sidecar_mode": SIDECAR_MODE,
            "adapter_version": ADAPTER_VERSION,
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
            "resolved_fact_inventory_hash": resolved_fact_inventory_hash,
            "local_value_inventory_hash": local_value_inventory_hash,
            "internal_value_store_enabled": internal_value_store_enabled,
            "internal_value_store_hash": internal_value_store_hash,
            "diagnostics_hash": diagnostics_hash,
            "parity_hash": stable_hash(parity),
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    binding = _read_request_binding(request_id)
    if binding and binding.get("sidecar_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_arelle_sidecar_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR Arelle sidecar basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["sidecar_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "sidecar_mode": SIDECAR_MODE,
        "operator_decision": OPERATOR_DECISION,
        "sidecar_state": READY_STATE,
        "sidecar_receipt_id": receipt_id,
        "sidecar_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "sidecar_receipt_hash": receipt_hash,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "adapter_dependency": {"package": ARELLE_PACKAGE, "version": ARELLE_VERSION, "license": "Apache-2.0"},
        "source_family": SOURCE_FAMILY,
        "parser_family": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
        "parser_receipt_id": parser_receipt_id,
        "parser_receipt_hash": parser_receipt_hash,
        "regex_fact_authority_receipt_hash": regex_fact.get("fact_authority_receipt_hash") if regex_fact else None,
        "connector_receipt_hash": expected_hashes["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": expected_hashes["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": expected_hashes["source_artifact_receipt_hash"],
        "content_sha256": expected_hashes["content_sha256"],
        "primary_document_hash": expected_hashes["primary_document_hash"],
        "document_inventory_hash": expected_hashes["document_inventory_hash"],
        "content_order_hash": expected_hashes["content_order_hash"],
        "table_candidate_inventory_hash": expected_hashes["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": expected_hashes["inline_xbrl_marker_inventory_hash"],
        "resolved_fact_records": local_facts,
        "resolved_fact_count": len(local_facts),
        "resolved_fact_projection": redacted_facts,
        "resolved_fact_inventory_hash": resolved_fact_inventory_hash,
        "local_value_inventory_hash": local_value_inventory_hash,
        "internal_value_store": internal_value_store,
        "coverage": coverage,
        "parity": parity,
        "diagnostics": diagnostics,
        "diagnostics_hash": diagnostics_hash,
        "authority_hashes": {
            "parser_receipt_hash": parser_receipt_hash,
            **expected_hashes,
            "resolved_fact_inventory_hash": resolved_fact_inventory_hash,
            "local_value_inventory_hash": local_value_inventory_hash,
            "internal_value_store_hash": internal_value_store_hash,
            "diagnostics_hash": diagnostics_hash,
            "sidecar_receipt_hash": receipt_hash,
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    if internal_value_store_enabled:
        _write_internal_value_store(receipt, value_records)
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_arelle_resolved_fact_authority_sidecar_status(receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-arelle-sidecar-status-{receipt['sidecar_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
    receipt_id: str,
    *,
    expected_sidecar_receipt_hash: str | None = None,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    expected_hash = str(expected_sidecar_receipt_hash or "").strip()
    if expected_hash and receipt["sidecar_receipt_hash"] != expected_hash:
        _blocked(
            "sec_edgar_arelle_sidecar_receipt_hash_mismatch",
            "SEC EDGAR Arelle resolved-fact sidecar receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["sidecar_receipt_hash"],
        )
    return receipt


def read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = receipt.get("internal_value_store") if isinstance(receipt.get("internal_value_store"), Mapping) else {}
    if metadata.get("store_state") != "persisted":
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_not_persisted",
            "SEC EDGAR Arelle sidecar internal value store is required for governed value materialization.",
            http_status=409,
            blocked_fields=["internal_value_store"],
        )
    receipt_id = str(receipt.get("sidecar_receipt_id") or "")
    receipt_hash = str(receipt.get("sidecar_receipt_hash") or "")
    try:
        value_store = json.loads(_value_store_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_missing",
            "SEC EDGAR Arelle sidecar internal value store was not found.",
            http_status=404,
            blocked_fields=["internal_value_store"],
        )
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_unreadable",
            "SEC EDGAR Arelle sidecar internal value store could not be read.",
            http_status=409,
            blocked_fields=["internal_value_store"],
        )
    records = value_store.get("value_records") if isinstance(value_store, Mapping) else None
    if not isinstance(records, list):
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_invalid",
            "SEC EDGAR Arelle sidecar internal value store is invalid.",
            http_status=409,
            blocked_fields=["internal_value_store"],
        )
    expected_hash = str(metadata.get("value_store_hash") or "")
    checks = {
        "sidecar_receipt_id": str(value_store.get("sidecar_receipt_id") or ""),
        "sidecar_receipt_hash": str(value_store.get("sidecar_receipt_hash") or ""),
        "value_store_hash": stable_hash(records),
        "value_record_count": len(records),
    }
    if checks["sidecar_receipt_id"] != receipt_id or checks["sidecar_receipt_hash"] != receipt_hash:
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_lineage_mismatch",
            "SEC EDGAR Arelle sidecar internal value store lineage does not match its sidecar receipt.",
            http_status=409,
            blocked_fields=["sidecar_receipt_hash"],
        )
    if checks["value_store_hash"] != expected_hash or checks["value_record_count"] != int(metadata.get("value_record_count") or -1):
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_hash_mismatch",
            "SEC EDGAR Arelle sidecar internal value store hash or count is stale.",
            http_status=409,
            blocked_fields=["internal_value_store_hash"],
        )
    return dict(value_store)


def _run_arelle(*, primary_document: str, max_facts: int, submission_documents: list[dict[str, str]]) -> dict[str, Any]:
    helper = _repo_root() / "tools" / "sec-xbrl-arelle.py"
    if not helper.exists():
        return {"status": "blocked", "reasons": [_reason("arelle_helper_missing")]}
    taxonomy_packages = _taxonomy_package_files()
    if not taxonomy_packages:
        return {"status": "blocked", "reasons": [_reason("taxonomy_package_unavailable")]}
    cache_dir = _taxonomy_cache_dir()
    if cache_dir is None:
        return {"status": "blocked", "reasons": [_reason("taxonomy_cache_unavailable")]}
    with tempfile.TemporaryDirectory(prefix="sec-xbrl-sidecar-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        entry, inline_entries = _write_submission_documents(
            temp_dir,
            primary_document=primary_document,
            submission_documents=submission_documents,
        )
        env = dict(os.environ)
        env["XDG_CONFIG_HOME"] = str(temp_dir / "xdg")
        env["XDG_CACHE_HOME"] = str(cache_dir)
        env["ARELLE_CACHE_DIR"] = str(cache_dir)
        env["TMP"] = str(temp_dir / "tmp")
        env["TEMP"] = str(temp_dir / "tmp")
        (temp_dir / "tmp").mkdir(parents=True, exist_ok=True)
        command = [
            _arelle_python(),
            str(helper),
            "--max-facts",
            str(max_facts),
            "--cache-dir",
            str(cache_dir),
            "--internet-connectivity",
            _taxonomy_internet_connectivity(),
        ]
        for input_path in inline_entries or [entry]:
            command.extend(["--input", str(input_path)])
        for package in taxonomy_packages:
            command.extend(["--taxonomy-package", str(package)])
        try:
            completed = ARELLE_SUBPROCESS_RUNNER(
                command,
                cwd=str(temp_dir),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=_timeout_seconds(),
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "blocked", "reasons": [_reason("arelle_timeout", timeout_seconds=_timeout_seconds())]}
        except Exception as exc:  # pragma: no cover - environment-specific subprocess failure
            return {
                "status": "blocked",
                "reasons": [_reason("arelle_invocation_failed", error_class=exc.__class__.__name__)],
            }
    if completed.returncode != 0:
        error_projection = _arelle_error_projection(completed.stdout)
        return {
            "status": "blocked",
            "reasons": [
                _reason(
                    "arelle_nonzero_exit",
                    return_code=completed.returncode,
                    stdout_hash=_sha256_text(completed.stdout),
                    stderr_hash=_sha256_text(completed.stderr),
                    **error_projection,
                )
            ],
        }
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {
            "status": "blocked",
            "reasons": [_reason("arelle_malformed_output", stdout_hash=_sha256_text(completed.stdout))],
        }
    if not isinstance(payload, dict) or payload.get("schema_id") != "tools.sec_xbrl_arelle_extract.v1":
        return {"status": "blocked", "reasons": [_reason("arelle_output_schema_invalid")]}
    facts = payload.get("facts")
    if not isinstance(facts, list):
        return {"status": "blocked", "reasons": [_reason("arelle_fact_list_missing")]}
    fact_count = payload.get("fact_count")
    if not isinstance(fact_count, int) or len(facts) != fact_count:
        return {"status": "blocked", "reasons": [_reason("arelle_fact_count_mismatch")]}
    if len(facts) > max_facts:
        return {"status": "blocked", "reasons": [_reason("arelle_fact_count_exceeds_limit", max_facts=max_facts)]}
    semantic_reasons = _semantic_resolution_blockers(payload)
    if semantic_reasons:
        return {"status": "blocked", "reasons": semantic_reasons}
    return {"status": "ready", **payload}


def _semantic_resolution_blockers(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, Mapping):
        return [_reason("arelle_semantic_resolution_diagnostics_missing")]
    checks = [
        (
            "period_unresolved_with_context_ref_count",
            "arelle_context_period_unresolved",
        ),
        (
            "unit_unresolved_with_unit_ref_count",
            "arelle_unit_ref_unresolved",
        ),
    ]
    reasons: list[dict[str, Any]] = []
    for field, reason in checks:
        count = diagnostics.get(field)
        if not isinstance(count, int):
            reasons.append(_reason("arelle_semantic_resolution_diagnostics_missing", missing_field=field))
        elif count > 0:
            reasons.append(_reason(reason, unresolved_count=count))
    return reasons


def _write_submission_documents(
    temp_dir: Path,
    *,
    primary_document: str,
    submission_documents: list[dict[str, str]],
) -> tuple[Path, list[Path]]:
    entry: Path | None = None
    inline_entries: list[Path] = []
    inline_hashes: set[str] = set()
    seen: set[str] = set()
    for index, document in enumerate(submission_documents, start=1):
        filename = _safe_document_filename(document.get("filename") or f"document-{index}.txt")
        if filename.lower() in seen:
            filename = f"{index}-{filename}"
        seen.add(filename.lower())
        path = temp_dir / filename
        text = str(document.get("text") or "")
        path.write_text(text, encoding="utf-8")
        prefixes = _inline_prefixes(text)
        if _inline_fact_count_for_prefixes(text, prefixes):
            inline_entries.append(path)
            inline_hashes.add(_sha256_text(text))
        if document.get("primary") == "true":
            entry = path
    if entry is None and inline_entries:
        entry = inline_entries[0]
    if entry is None:
        entry = temp_dir / "filing.htm"
        entry.write_text(primary_document, encoding="utf-8")
        prefixes = _inline_prefixes(primary_document)
        primary_hash = _sha256_text(primary_document)
        if _inline_fact_count_for_prefixes(primary_document, prefixes) and primary_hash not in inline_hashes:
            inline_entries.append(entry)
    return entry, inline_entries


def _submission_documents(content: bytes, *, primary_document_hash: str) -> list[dict[str, str]]:
    text = content.decode("utf-8", errors="ignore")
    documents: list[dict[str, str]] = []
    for match in _DOCUMENT_RE.finditer(text):
        metadata, doc_text = _document_metadata(match.group("body"))
        filename = metadata.get("filename") or ""
        documents.append(
            {
                "filename": filename,
                "type": metadata.get("type") or "",
                "text": doc_text,
                "primary": "true" if _document_matches_primary(filename=filename, text=doc_text, primary_document_hash=primary_document_hash) else "false",
            }
        )
    return documents


def _document_matches_primary(*, filename: str, text: str, primary_document_hash: str) -> bool:
    expected = str(primary_document_hash or "").strip()
    if not expected:
        return False
    return (bool(filename) and _sha256_text(filename) == expected) or (bool(text) and _sha256_text(text) == expected)


def _document_metadata(document_body: str) -> tuple[dict[str, str], str]:
    text_match = _TEXT_RE.search(document_body)
    tag_region = document_body[: text_match.start()] if text_match else document_body
    tags: dict[str, str] = {}
    for match in _TAG_RE.finditer(tag_region):
        key = match.group(1).strip().upper()
        value = match.group(2).strip()
        if key and value and key not in tags:
            tags[key] = value
    doc_text = text_match.group("text") if text_match else ""
    wrapper_match = _SEC_XBRL_WRAPPER_RE.match(doc_text)
    if wrapper_match and wrapper_match.group("text").lstrip().startswith("<?xml"):
        doc_text = wrapper_match.group("text").lstrip()
    elif doc_text.lstrip().startswith("<?xml"):
        doc_text = doc_text.lstrip()
    return {"filename": tags.get("FILENAME", ""), "type": tags.get("TYPE", "")}, doc_text


def _safe_document_filename(filename: str) -> str:
    name = Path(str(filename or "")).name.strip()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name)[:160].strip(".-")
    return safe or "document.txt"


def _independent_inline_fact_tally(submission_documents: list[dict[str, str]]) -> dict[str, Any]:
    tally: list[dict[str, Any]] = []
    total = 0
    scanned = 0
    for index, document in enumerate(submission_documents, start=1):
        text = str(document.get("text") or "")
        scanned += 1
        prefixes = _inline_prefixes(text)
        count = _inline_fact_count_for_prefixes(text, prefixes)
        total += count
        if count or prefixes:
            tally.append(
                {
                    "document_index": index,
                    "document_type": str(document.get("type") or ""),
                    "document_filename_hash": _sha256_text(str(document.get("filename") or ""))[:24] if document.get("filename") else None,
                    "document_text_hash": _sha256_text(text)[:24],
                    "inline_prefixes": prefixes,
                    "inline_fact_count": count,
                    "primary_document": document.get("primary") == "true",
                }
            )
    return {
        "schema_id": "layer3.sec_edgar_arelle_independent_inline_fact_tally.v1",
        "method": "namespace_bound_raw_inline_xbrl_start_tag_count",
        "scanned_document_count": scanned,
        "inline_document_count": len(tally),
        "inline_fact_count": total,
        "document_tally": tally,
        "values_inspected_or_emitted": False,
    }


def _inline_fact_count_for_prefixes(text: str, prefixes: list[str]) -> int:
    if not prefixes:
        return 0
    pattern = re.compile(
        r"<\s*(?:"
        + "|".join(re.escape(prefix) for prefix in prefixes)
        + r"):(?:nonFraction|nonNumeric|fraction)\b",
        re.IGNORECASE,
    )
    return len(pattern.findall(text))


def _inline_prefixes(text: str) -> list[str]:
    return sorted({prefix for prefix, namespace in _XMLNS_RE.findall(text) if namespace in _INLINE_XBRL_NAMESPACES})


def _local_facts(facts: list[Any], *, parser_receipt: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    value_records: list[dict[str, Any]] = []
    for index, item in enumerate(facts, start=1):
        if not isinstance(item, Mapping):
            continue
        effective_value = str(item.get("effective_value") if item.get("effective_value") is not None else item.get("value") or "")
        lexical_value = str(item.get("lexical_value") or "")
        concept = dict(item.get("concept") or {})
        period = dict(item.get("period") or {})
        unit = dict(item.get("unit") or {})
        dimensions = dict(item.get("dimensions") or {})
        transform = {
            "sign": _optional_str(item.get("sign")),
            "scale": _optional_str(item.get("scale")),
            "decimals": _optional_str(item.get("decimals")),
            "precision": _optional_str(item.get("precision")),
            "format": _optional_str(item.get("format")),
        }
        fact_key = stable_hash(
            {
                "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
                "source_order": int(item.get("source_order") or index),
                "entry_document_index": int(item.get("entry_document_index") or 1),
                "concept_qname": concept.get("qname"),
                "context_id": item.get("context_id"),
                "unit_id": item.get("unit_id"),
                "period": period,
                "unit": unit,
                "dimensions": dimensions,
                "effective_value_hash": _sha256_text(effective_value),
            }
        )
        value_hash = _sha256_text(effective_value)
        lexical_value_hash = _sha256_text(lexical_value)
        output.append(
            {
                "resolved_fact_id": fact_key,
                "source_order": int(item.get("source_order") or index),
                "entry_document_index": int(item.get("entry_document_index") or 1),
                "concept": concept,
                "context_id": str(item.get("context_id") or ""),
                "unit_id": str(item.get("unit_id") or ""),
                "period": period,
                "unit": unit,
                "dimensions": dimensions,
                "decimals": transform["decimals"],
                "precision": transform["precision"],
                "scale": transform["scale"],
                "format": transform["format"],
                "sign": transform["sign"],
                "hidden": bool(item.get("hidden")),
                "continued": bool(item.get("continued")),
                "continued_at": _optional_str(item.get("continued_at")),
                "footnote_count": int(item.get("footnote_count") or 0),
                "value_hash": value_hash,
                "value_length": len(effective_value),
                "effective_value_hash": value_hash,
                "effective_value_length": len(effective_value),
                "lexical_value_hash": lexical_value_hash,
                "lexical_value_length": len(lexical_value),
                "value_semantics": VALUE_SEMANTICS_ID,
                "value_redacted_in_projection": True,
                "source_artifact_receipt_hash": str(parser_receipt["source_artifact_receipt_hash"]),
                "primary_document_hash": str(parser_receipt["primary_document_hash"]),
            }
        )
        value_records.append(
            {
                "resolved_fact_id": fact_key,
                "source_order": int(item.get("source_order") or index),
                "entry_document_index": int(item.get("entry_document_index") or 1),
                "effective_value": effective_value,
                "effective_value_hash": value_hash,
                "effective_value_length": len(effective_value),
                "lexical_value": lexical_value,
                "lexical_value_hash": lexical_value_hash,
                "lexical_value_length": len(lexical_value),
                "transform": transform,
                "value_semantics": VALUE_SEMANTICS_ID,
            }
        )
    return output, value_records


def _redacted_fact(fact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in fact.items()
        if key not in {"value", "effective_value", "lexical_value"}
    } | {"value_redacted": True}


def _coverage_stats(facts: list[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(facts)
    explicit_dim_facts = 0
    typed_dim_facts = 0
    for fact in facts:
        dims = fact.get("dimensions") if isinstance(fact.get("dimensions"), Mapping) else {}
        if list(dims.get("explicit") or []):
            explicit_dim_facts += 1
        if list(dims.get("typed") or []):
            typed_dim_facts += 1
    return {
        "resolved_fact_count": total,
        "period_resolved_count": sum(1 for fact in facts if (fact.get("period") or {}).get("resolved") is True),
        "unit_resolved_count": sum(1 for fact in facts if (fact.get("unit") or {}).get("resolved") is True),
        "explicit_dimension_fact_count": explicit_dim_facts,
        "typed_dimension_fact_count": typed_dim_facts,
        "hidden_fact_count": sum(1 for fact in facts if fact.get("hidden") is True),
        "continued_fact_count": sum(1 for fact in facts if fact.get("continued") is True),
        "standard_concept_count": sum(1 for fact in facts if (fact.get("concept") or {}).get("standard") is True),
        "extension_concept_count": sum(1 for fact in facts if (fact.get("concept") or {}).get("extension") is True),
        "concept_resolved_from_dts_count": sum(1 for fact in facts if (fact.get("concept") or {}).get("resolved_from_dts") is True),
        "concept_unresolved_from_dts_count": sum(1 for fact in facts if (fact.get("concept") or {}).get("resolved_from_dts") is not True),
        "actual_period_unit_dimension_values_emitted": True,
        "period_unit_dimension_hash_only_projection": False,
        "silent_fact_truncation_performed": False,
    }


def _diagnostics(
    *,
    arelle: Mapping[str, Any],
    coverage: Mapping[str, Any],
    max_facts: int,
    independent_inline_facts: Mapping[str, Any],
    internal_value_store_enabled: bool,
) -> dict[str, Any]:
    document_tally = list(independent_inline_facts.get("document_tally") or [])
    return {
        "adapter_execution": "isolated_subprocess_cli",
        "app_runtime_imported_arelle": False,
        "optional_dependency_required_for_sidecar_only": True,
        "arelle_package": ARELLE_PACKAGE,
        "arelle_version": str(arelle.get("arelle_version") or ""),
        "arelle_version_pinned": str(arelle.get("arelle_version") or "") == ARELLE_VERSION,
        "max_facts": max_facts,
        "max_facts_fail_closed": True,
        "max_facts_silent_slice": False,
        "taxonomy_package_loaded": bool(arelle.get("taxonomy_package_loaded")),
        "taxonomy_package_count": int(arelle.get("taxonomy_package_count") or 0),
        "taxonomy_package_hashes": list(arelle.get("taxonomy_package_hashes") or []),
        "taxonomy_package_invalid_count": int(arelle.get("taxonomy_package_invalid_count") or 0),
        "taxonomy_package_invalid_hashes": list(arelle.get("taxonomy_package_invalid_hashes") or []),
        "taxonomy_network_resolution_enabled": bool(arelle.get("taxonomy_network_resolution_enabled")),
        "document_set": dict(arelle.get("document_set") or {}),
        "dts_unresolved_diagnostics": dict(arelle.get("diagnostics") or {}),
        "independent_inline_fact_count": int(independent_inline_facts.get("inline_fact_count") or 0),
        "independent_inline_fact_scanned_document_count": int(independent_inline_facts.get("scanned_document_count") or 0),
        "independent_inline_fact_document_count": int(independent_inline_facts.get("inline_document_count") or 0),
        "independent_inline_fact_tally_hash": stable_hash(document_tally),
        "independent_inline_fact_document_tally": document_tally,
        "independent_inline_fact_count_reconciled": int(independent_inline_facts.get("inline_fact_count") or 0) <= int(coverage.get("resolved_fact_count") or 0),
        "source_order_preserved": True,
        "resolved_structural_semantics": dict(coverage),
        "raw_fact_values_exposed_in_response": False,
        "raw_fact_values_retained_local_receipt": False,
        "raw_fact_values_retained_internal_value_store": internal_value_store_enabled,
        "internal_value_store_retention_policy": (
            "tied_to_sidecar_receipt_lifecycle"
            if internal_value_store_enabled
            else "not_created_without_internal_value_store_flag"
        ),
        "bridge_gate_b_product_package_ui_mutated": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
    }


def _parity(*, regex_count: int | None, arelle_count: int, companyfacts_count: Any, confidence: str) -> dict[str, Any]:
    standard_count = int(companyfacts_count) if isinstance(companyfacts_count, int) else None
    return {
        "regex_fact_authority_count": regex_count,
        "arelle_resolved_fact_count": arelle_count,
        "recovered_vs_regex": arelle_count - regex_count if regex_count is not None else None,
        "companyfacts_standard_fact_count": standard_count,
        "companyfacts_oracle_confidence": confidence or None,
        "companyfacts_scope": "standard_taxonomy_accession_crosscheck_only" if standard_count is not None else "not_recorded",
    }


def _arelle_error_projection(stdout: str) -> dict[str, str]:
    try:
        payload = json.loads(str(stdout or "").strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    reason = str(payload.get("reason") or "").strip()
    error_class = str(payload.get("error_class") or "").strip()
    projection: dict[str, str] = {}
    if reason and _SAFE_ARELLE_ERROR_RE.match(reason):
        projection["arelle_error_reason"] = reason
    if error_class and _SAFE_ARELLE_ERROR_RE.match(error_class):
        projection["arelle_error_class"] = error_class
    return projection


def _optional_regex_fact_authority(request: Mapping[str, Any]) -> dict[str, Any] | None:
    receipt_id = str(request.get("regex_fact_authority_receipt_id") or "").strip()
    receipt_hash = str(request.get("regex_fact_authority_receipt_hash") or "").strip()
    if not receipt_id and not receipt_hash:
        return None
    if not receipt_id or not _is_hash(receipt_hash):
        _blocked(
            "sec_edgar_arelle_sidecar_regex_fact_authority_ref_invalid",
            "SEC EDGAR Arelle sidecar requires both regex fact-authority receipt id and hash when provided.",
            blocked_fields=["regex_fact_authority_receipt_id", "regex_fact_authority_receipt_hash"],
        )
    return layer3_sec_edgar_html_inline_xbrl_fact_authority.read_sec_edgar_html_inline_xbrl_fact_authority_receipt(
        receipt_id,
        expected_fact_authority_receipt_hash=receipt_hash,
    )


def _regex_count(receipt: Mapping[str, Any] | None) -> int | None:
    if receipt is None:
        return None
    return int(receipt.get("fact_count") or 0)


def _max_facts(request: Mapping[str, Any]) -> int:
    raw = request.get("max_facts")
    if raw in (None, ""):
        return DEFAULT_MAX_FACTS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        _blocked("sec_edgar_arelle_sidecar_max_facts_invalid", "max_facts must be an integer.", blocked_fields=["max_facts"])
    if value < MIN_MAX_FACTS:
        _blocked(
            "sec_edgar_arelle_sidecar_max_facts_too_low",
            "SEC EDGAR Arelle sidecar max_facts must be at least 100000 or omitted.",
            blocked_fields=["max_facts"],
        )
    return value


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=schema_id),
        "mode": SIDECAR_MODE,
        "sidecar_mode": SIDECAR_MODE,
        "operator_decision": OPERATOR_DECISION,
        "sidecar_state": receipt["sidecar_state"],
        "sidecar_receipt_id": receipt["sidecar_receipt_id"],
        "sidecar_receipt_ref": receipt["sidecar_receipt_ref"],
        "sidecar_receipt_hash": receipt["sidecar_receipt_hash"],
        "idempotent_replay": idempotent_replay,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "source_family": SOURCE_FAMILY,
        "parser_family": receipt["parser_family"],
        "parser_receipt_id": receipt["parser_receipt_id"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "regex_fact_authority_receipt_hash": receipt.get("regex_fact_authority_receipt_hash"),
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": receipt["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": receipt["source_artifact_receipt_hash"],
        "content_sha256": receipt["content_sha256"],
        "primary_document_hash": receipt["primary_document_hash"],
        "document_inventory_hash": receipt["document_inventory_hash"],
        "content_order_hash": receipt["content_order_hash"],
        "table_candidate_inventory_hash": receipt["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": receipt["inline_xbrl_marker_inventory_hash"],
        "resolved_fact_count": receipt["resolved_fact_count"],
        "resolved_fact_inventory_hash": receipt["resolved_fact_inventory_hash"],
        "local_value_inventory_hash": receipt["local_value_inventory_hash"],
        "internal_value_store": dict(receipt.get("internal_value_store") or {}),
        "coverage": dict(receipt["coverage"]),
        "parity": dict(receipt["parity"]),
        "diagnostics": dict(receipt["diagnostics"]),
        "diagnostics_hash": receipt["diagnostics_hash"],
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "resolved_fact_count": receipt["resolved_fact_count"],
            "structural_semantics_resolved": True,
            "fact_values_returned": False,
            "local_receipt_retains_fact_values": False,
            "internal_value_store_state": (receipt.get("internal_value_store") or {}).get("store_state"),
            "internal_value_store_retention_policy": (receipt.get("internal_value_store") or {}).get("retention_policy"),
            "bridge_mutated": False,
            "gate_b_mutated": False,
            "product_mutated": False,
            "package_mutated": False,
            "runtime_default_changed": False,
            "next_allowed_actions": [
                "run parity diagnostics",
                "select gated production cutover only after sidecar parity proof",
            ],
        },
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made": False,
            "cache_hit_avoids_network_request": idempotent_replay,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "run SEC Arelle sidecar parity diagnostic report",
            "prepare gated production cutover after parity proof",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_arelle_sidecar_raw_authority_exposed",
            "SEC EDGAR Arelle resolved-fact sidecar would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _blocked_response(*, request_id: str, parser_receipt_hash: str, reasons: list[dict[str, Any]]) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": SIDECAR_MODE,
        "sidecar_mode": SIDECAR_MODE,
        "operator_decision": OPERATOR_DECISION,
        "sidecar_state": BLOCKED_STATE,
        "sidecar_receipt_id": None,
        "sidecar_receipt_ref": None,
        "sidecar_receipt_hash": None,
        "idempotent_replay": False,
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "source_family": SOURCE_FAMILY,
        "parser_receipt_hash": parser_receipt_hash,
        "resolved_fact_count": 0,
        "resolved_fact_inventory_hash": None,
        "diagnostics_hash": None,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "bridge_mutated": False,
            "gate_b_mutated": False,
            "product_mutated": False,
            "runtime_default_changed": False,
            "next_allowed_actions": ["install optional Arelle dependency or refresh parser receipt"],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["install optional Arelle dependency or refresh parser receipt"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_arelle_sidecar_blocked_response_raw_authority_exposed",
            "SEC EDGAR Arelle sidecar blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_arelle_sidecar_forbidden_request_fields",
            "SEC EDGAR Arelle sidecar rejects caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_arelle_sidecar_unknown_field",
            "SEC EDGAR Arelle sidecar fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_arelle_sidecar_schema_not_admitted",
            "SEC EDGAR Arelle sidecar requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


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
    artifact = live_receipt.get("source_artifact_receipt") if isinstance(live_receipt.get("source_artifact_receipt"), Mapping) else {}
    checks = {
        "source_artifact_receipt_hash": str(artifact.get("source_artifact_receipt_hash") or ""),
        "content_sha256": hashlib.sha256(content).hexdigest(),
    }
    for key, received in checks.items():
        if received != expected_hashes[key] or str(parser_receipt.get(key) or "") != expected_hashes[key]:
            _blocked(
                "sec_edgar_arelle_sidecar_source_artifact_mismatch",
                "SEC EDGAR Arelle sidecar requires parser and retained live source-artifact authority to match.",
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
            "sec_edgar_arelle_sidecar_parser_reparse_mismatch",
            "SEC EDGAR Arelle sidecar requires retained content to reparse to the parser receipt.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["sidecar_receipt_id"]))
    if target.exists():
        _read_verified_receipt(target.stem)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")


def _write_internal_value_store(receipt: Mapping[str, Any], value_records: list[dict[str, Any]]) -> None:
    metadata = receipt.get("internal_value_store") if isinstance(receipt.get("internal_value_store"), Mapping) else {}
    expected_hash = str(metadata.get("value_store_hash") or "")
    payload = {
        "schema_id": INTERNAL_VALUE_STORE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "sidecar_receipt_id": receipt["sidecar_receipt_id"],
        "sidecar_receipt_hash": receipt["sidecar_receipt_hash"],
        "value_store_hash": expected_hash,
        "value_record_count": len(value_records),
        "value_semantics": VALUE_SEMANTICS_ID,
        "retention_policy": "tied_to_sidecar_receipt_lifecycle",
        "gitignored_local_storage": True,
        "operator_surface_exposure": False,
        "committed_artifact_exposure": False,
        "created_by_cutover_flag": True,
        "recorded_at": _server_time(),
        "value_records": value_records,
    }
    if stable_hash(value_records) != expected_hash:
        _blocked(
            "sec_edgar_arelle_sidecar_internal_value_store_hash_invalid",
            "SEC EDGAR Arelle sidecar internal value store basis is invalid.",
            http_status=409,
            blocked_fields=["internal_value_store_hash"],
        )
    target = _value_store_path(str(receipt["sidecar_receipt_id"]))
    if target.exists():
        read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, indent=2) + "\n")


def _internal_value_store_metadata(
    *,
    enabled: bool,
    value_store_hash: str | None,
    value_record_count: int,
) -> dict[str, Any]:
    if not enabled:
        return {
            "schema_id": INTERNAL_VALUE_STORE_SCHEMA_ID,
            "store_state": "not_created_internal_value_store_flag_off",
            "creation_gated_by_internal_value_store_flag": True,
            "consumption_gated_by_internal_value_store_flag": True,
            "value_record_count": 0,
            "values_exposed_in_status_projection": False,
            "retention_policy": "not_created_without_internal_value_store_flag",
        }
    return {
        "schema_id": INTERNAL_VALUE_STORE_SCHEMA_ID,
        "store_state": "persisted",
        "creation_gated_by_internal_value_store_flag": True,
        "consumption_gated_by_internal_value_store_flag": True,
        "value_store_hash": value_store_hash,
        "value_record_count": value_record_count,
        "value_semantics": VALUE_SEMANTICS_ID,
        "retention_policy": "tied_to_sidecar_receipt_lifecycle",
        "gitignored_local_storage": True,
        "operator_surface_exposure": False,
        "committed_artifact_exposure": False,
    }


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
            "sec_edgar_arelle_sidecar_receipt_id_invalid",
            "SEC EDGAR Arelle sidecar status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["sidecar_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_arelle_sidecar_receipt_missing",
            "SEC EDGAR Arelle sidecar receipt was not found.",
            http_status=404,
            blocked_fields=["sidecar_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_arelle_sidecar_receipt_unreadable",
            "SEC EDGAR Arelle sidecar receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("sidecar_receipt_id") != receipt_id:
        _blocked("sec_edgar_arelle_sidecar_receipt_invalid", "SEC EDGAR Arelle sidecar receipt is invalid.", http_status=409)
    if not _is_hash(str(receipt.get("sidecar_receipt_hash") or "")):
        _blocked(
            "sec_edgar_arelle_sidecar_receipt_hash_invalid",
            "SEC EDGAR Arelle sidecar receipt hash is invalid.",
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
        _blocked("sec_edgar_arelle_sidecar_request_binding_unreadable", "SEC EDGAR Arelle sidecar request binding could not be read.", http_status=409)
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "sidecar_basis_hash": basis_hash,
        "sidecar_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("sidecar_basis_hash") != basis_hash:
            _blocked("sec_edgar_arelle_sidecar_request_binding_conflict", "SEC EDGAR Arelle sidecar request binding conflicts with existing authority.", http_status=409)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _negative_invariants() -> dict[str, bool]:
    return {
        "live_sec_network_fetch_performed_by_sidecar": False,
        "submissions_lookup_runtime_performed_by_sidecar": False,
        "companyfacts_runtime_fetch_performed_by_sidecar": False,
        "browser_supplied_html_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_local_path_admitted": False,
        "artifact_bytes_admitted": False,
        "standalone_xml_xbrl_sidecar_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "arelle_imported_into_app_runtime": False,
        "financial_statement_semantics_enabled": False,
        "cross_company_comparability_enabled": False,
        "material_bridge_mutated": False,
        "gate_b_mutated": False,
        "product_mutated": False,
        "package_mutated": False,
        "ui_mutated": False,
        "candidate_b_default_scope_changed": False,
        "baseline_default_changed": False,
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
    elif isinstance(value, str) and (
        any_url_reference_found(value) or windows_local_path_start_reference_found(value)
    ):
        found.append(prefix or "request_body")
    return found


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return bool(
            windows_local_path_start_reference_found(text)
            or text.startswith(("http://", "https://", "file://", "\\\\"))
        )
    return False


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _value_store_path(receipt_id: str) -> Path:
    return _root() / INTERNAL_VALUE_STORE_DIR / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked("sec_edgar_arelle_sidecar_storage_root_unavailable", "SEC EDGAR Arelle sidecar requires the existing Layer 3 storage root.", http_status=409)
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _arelle_python() -> str:
    return str(os.environ.get("SEC_XBRL_ARELLE_PYTHON") or os.environ.get("ARELLE_PYTHON") or sys.executable)


def _taxonomy_package_files() -> list[Path]:
    raw = str(os.environ.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES") or "").strip()
    if not raw:
        return []
    paths: list[Path] = []
    for item in raw.split(os.pathsep):
        if not item.strip():
            continue
        path = Path(item).resolve()
        if not path.exists() or not path.is_file() or _path_inside_repo_or_onedrive(path):
            return []
        paths.append(path)
    return paths


def _taxonomy_cache_dir() -> Path | None:
    raw = str(os.environ.get("SEC_XBRL_ARELLE_CACHE_DIR") or "").strip()
    if not raw:
        return None
    path = Path(raw).resolve()
    if _path_inside_repo_or_onedrive(path):
        return None
    path.mkdir(parents=True, exist_ok=True)
    return path


def _taxonomy_internet_connectivity() -> str:
    value = str(os.environ.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY") or "offline").strip().lower()
    return "online" if value == "online" else "offline"


def _arelle_fact_authority_cutover_enabled() -> bool:
    return bool(getattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False))


def _arelle_internal_value_store_enabled() -> bool:
    return bool(getattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", False))


def _path_inside_repo_or_onedrive(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    repo = _repo_root().resolve(strict=False)
    try:
        resolved.relative_to(repo)
        return True
    except ValueError:
        return any(part.lower() == "onedrive" for part in resolved.parts)


def _timeout_seconds() -> int:
    try:
        return max(int(os.environ.get("SEC_XBRL_ARELLE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)), 1)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _base_response(*, request_id: str, status: str, schema_id: str) -> dict[str, Any]:
    return {"schema_id": schema_id, "schema_version": SCHEMA_VERSION, "request_id": request_id, "server_time": _server_time(), "status": status}


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(f"sec_edgar_arelle_sidecar_{key}_missing", f"SEC EDGAR Arelle sidecar requires {key}.", blocked_fields=[key])
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(f"sec_edgar_arelle_sidecar_{key}_invalid", f"SEC EDGAR Arelle sidecar requires a 64-character hash for {key}.", blocked_fields=[key])
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(f"sec_edgar_arelle_sidecar_{key}_not_admitted", "SEC EDGAR Arelle sidecar request does not match the admitted runtime contract.", blocked_fields=[key])


def _expected_or_authority(request: Mapping[str, Any], request_key: str, authority: Mapping[str, Any], authority_key: str) -> str:
    value = str(request.get(request_key) or authority.get(authority_key) or "").strip()
    if not _is_hash(value):
        _blocked(f"sec_edgar_arelle_sidecar_{request_key}_invalid", "SEC EDGAR Arelle sidecar requires SHA-256 authority hashes.", blocked_fields=[request_key])
    if str(authority.get(authority_key) or "") != value:
        _blocked(f"sec_edgar_arelle_sidecar_{authority_key}_mismatch", "SEC EDGAR Arelle sidecar hash is stale or mismatched.", http_status=409, blocked_fields=[request_key])
    return value


def _optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


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
