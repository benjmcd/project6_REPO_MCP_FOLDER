from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Mapping, Protocol
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings
from app.services import layer3_sec_edgar_authority_envelope
from app.services.layer3_sec_edgar_ref_safety import (
    contains_forbidden_ref_tree,
    find_forbidden_ref_paths,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_acquisition.v1"
COMPANYFACTS_SCHEMA_ID = "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1"
COMPANYFACTS_RECEIPT_PREFIX = "sec-edgar-companyfacts-live-artifact"
COMPANYFACTS_RECEIPT_DIR = "layer3-sec-xbrl-companyfacts"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_acquisition_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_acquisition_status.v1"
SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID = "layer3.sec_edgar_text_table_source_artifact_receipt.v1"
SCHEMA_VERSION = 1
ACQUISITION_MODE = "sec_edgar_text_table_live_source_artifact_acquisition_v1"
OPERATOR_DECISION = "acquire_sec_edgar_text_table_live_source_artifact"
SOURCE_ARTIFACT_FAMILY = "complete_submission_text_filing_artifact"
SOURCE_FAMILY = layer3_sec_edgar_authority_envelope.SOURCE_FAMILY
PARSER_FAMILY = layer3_sec_edgar_authority_envelope.PARSER_FAMILY
PARSER_CONTRACT_ID = "aps_sec_edgar_filing_parser_v1"
TYPED_CONTENT_CONTRACT_ID = layer3_sec_edgar_authority_envelope.TYPED_CONTENT_CONTRACT_ID
SOURCE_MODE = "artifact_sec_edgar_filing_parser"
RECEIPT_PREFIX = "sec-edgar-text-table-live-source-artifact"
SOURCE_ARTIFACT_RECEIPT_PREFIX = "sec-edgar-text-table-source-artifact"
RECEIPT_DIR = "layer3-sec-edgar-live-source-artifact-acquisition"
REDACTION_POLICY_ID = "sec_edgar_text_table_live_source_artifact_acquisition_redaction_v1"
RATE_POLICY_ID = "sec_edgar_text_table_live_source_artifact_default_1rps_max_10rps_v1"
SEC_RATE_LIMIT_CEILING_PER_SECOND = 10
RETRYABLE_STATUS_CODES = {408, 403, 429, 500, 502, 503, 504}

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "acquisition_mode",
    "operator_decision",
    "cik_or_filer_ref",
    "accession_or_submission_id",
    "form_type",
    "filing_date",
    "expected_content_sha256",
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
_CIK_RE = re.compile(r"^\d{1,10}$")
_ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_FORM_TYPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,31}$")
_RECEIPT_ID_RE = re.compile(r"^sec-edgar-text-table-live-source-artifact-[a-f0-9]{24}-[a-f0-9]{24}$")


@dataclass(frozen=True)
class SecEdgarFetchResult:
    status_code: int
    content: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)
    final_url: str = ""
    complete: bool = True


class SecEdgarClient(Protocol):
    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ) -> SecEdgarFetchResult:
        ...


class SecEdgarHttpClient:
    def fetch_complete_submission_text(
        self,
        *,
        url: str,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
    ) -> SecEdgarFetchResult:
        if os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_ci_network_disabled",
                "Live SEC EDGAR network acquisition is disabled in CI; use the fake SEC client contract double.",
                http_status=409,
            )
        if not bool(getattr(settings, "layer3_sec_edgar_live_network_enabled", False)):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_live_network_disabled",
                "Live SEC EDGAR network acquisition requires server configuration before the real HTTP client may run.",
                http_status=409,
                blocked_fields=["layer3_sec_edgar_live_network_enabled"],
            )
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/plain,*/*;q=0.1",
                "Accept-Encoding": "identity",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                final_url = str(response.geturl() or "")
                if not _is_allowed_sec_url(final_url):
                    _blocked(
                        "sec_edgar_text_table_live_source_artifact_redirect_not_admitted",
                        "SEC EDGAR live source-artifact acquisition does not admit redirects outside sec.gov.",
                        http_status=409,
                    )
                content = _read_bounded_bytes(response, max_bytes)
                return SecEdgarFetchResult(
                    status_code=int(getattr(response, "status", 200) or 200),
                    content=content,
                    headers=dict(response.headers.items()),
                    final_url=final_url,
                    complete=len(content) <= max_bytes,
                )
        except urllib.error.HTTPError as exc:
            error_bytes = b""
            try:
                error_bytes = _read_bounded_bytes(exc, min(max_bytes, 4096))
            except Exception:
                error_bytes = b""
            return SecEdgarFetchResult(
                status_code=int(exc.code),
                content=error_bytes,
                headers=dict(exc.headers.items()) if exc.headers else {},
                final_url=str(exc.url or url),
                complete=True,
            )
        except TimeoutError:
            return SecEdgarFetchResult(status_code=408, complete=False)
        except OSError:
            return SecEdgarFetchResult(status_code=503, complete=False)


SEC_EDGAR_CLIENT: SecEdgarClient = SecEdgarHttpClient()
SEC_EDGAR_SLEEP = time.sleep


def acquire_sec_edgar_text_table_live_source_artifact(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "acquisition_mode", ACQUISITION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    _require_live_network_enabled()
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_operator_confirmation_missing",
            "operator_confirmation=true is required before live SEC EDGAR source-artifact acquisition.",
            http_status=409,
            blocked_fields=["operator_confirmation"],
        )
    user_agent = _server_configured_user_agent()
    source_identity = _source_identity(request)
    source_identity_hash = stable_hash(
        {"hash_version": "sec_edgar_live_source_identity_hash_v1", **source_identity}
    )
    request_binding = _read_request_binding(request_id)
    if request_binding and request_binding.get("source_identity_hash") != source_identity_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_client_request_id_conflict",
            "The client_request_id is already bound to a different SEC EDGAR source identity.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _find_existing_receipt(source_identity_hash)
    if existing is not None:
        _verify_expected_content_hash_for_receipt(request, existing)
        _write_request_binding(request_id, source_identity_hash, existing["live_source_artifact_receipt_id"])
        return _response_from_receipt(
            existing,
            request_id=request_id,
            cache_status="hit",
            idempotent_replay=True,
            network_request_made=False,
        )

    url = _server_derived_complete_submission_text_url(request)
    url_hash = _sha256_text(url)
    _enforce_rate_limit()
    fetch_result = _fetch_with_retry(
        url=url,
        user_agent=user_agent,
        timeout_seconds=_timeout_seconds(),
        max_bytes=_max_bytes(),
    )
    if fetch_result.final_url and not _is_allowed_sec_url(fetch_result.final_url):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_redirect_not_admitted",
            "SEC EDGAR live source-artifact acquisition does not admit redirects outside sec.gov.",
            http_status=409,
        )
    if fetch_result.status_code != 200:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_fetch_failed",
            "SEC EDGAR live source-artifact acquisition did not return a complete HTTP 200 text artifact.",
            http_status=409,
            blocked_fields=[f"http_status:{fetch_result.status_code}"],
        )
    if not fetch_result.complete:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_partial_download_blocked",
            "Partial SEC EDGAR downloads do not create source-artifact authority.",
            http_status=409,
            blocked_fields=["content"],
        )
    content = bytes(fetch_result.content or b"")
    if len(content) > _max_bytes():
        _blocked(
            "sec_edgar_text_table_live_source_artifact_partial_download_blocked",
            "SEC EDGAR responses larger than the configured byte limit do not create source-artifact authority.",
            http_status=409,
            blocked_fields=["content"],
        )
    if not content:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_empty_content_blocked",
            "Empty SEC EDGAR responses do not create source-artifact authority.",
            http_status=409,
            blocked_fields=["content"],
        )
    content_sha256 = hashlib.sha256(content).hexdigest()
    expected_content_sha256 = str(request.get("expected_content_sha256") or "").strip()
    if expected_content_sha256 and expected_content_sha256.lower() != content_sha256:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_content_hash_mismatch",
            "SEC EDGAR live source-artifact acquisition content hash did not match expected authority.",
            http_status=409,
            blocked_fields=["expected_content_sha256"],
        )
    receipt = _build_available_receipt(
        request_id=request_id,
        source_identity=source_identity,
        source_identity_hash=source_identity_hash,
        server_derived_url_hash=url_hash,
        user_agent_hash=_sha256_text(user_agent),
        content_sha256=content_sha256,
        content_length=len(content),
    )
    _write_artifact(receipt["live_source_artifact_receipt_id"], content, content_sha256)
    _write_receipt(receipt)
    _write_request_binding(request_id, source_identity_hash, receipt["live_source_artifact_receipt_id"])
    return _response_from_receipt(
        receipt,
        request_id=request_id,
        cache_status="miss",
        idempotent_replay=False,
        network_request_made=True,
    )


def inspect_sec_edgar_text_table_live_source_artifact_status(
    live_source_artifact_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(live_source_artifact_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-live-source-artifact-status-{receipt['live_source_artifact_receipt_hash'][:12]}",
        cache_status="status",
        idempotent_replay=False,
        network_request_made=False,
        schema_id=STATUS_SCHEMA_ID,
    )


def read_sec_edgar_text_table_live_source_artifact_receipt(
    live_source_artifact_receipt_id: str,
    *,
    expected_live_source_artifact_receipt_hash: str | None = None,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(live_source_artifact_receipt_id)
    expected_hash = str(expected_live_source_artifact_receipt_hash or "").strip()
    if expected_hash and receipt.get("live_source_artifact_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_hash_mismatch",
            "SEC EDGAR live source-artifact receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["live_source_artifact_receipt_hash"],
        )
    _verify_artifact_bytes(receipt)
    return receipt


def read_sec_edgar_text_table_live_source_artifact_bytes(
    live_source_artifact_receipt_id: str,
    *,
    expected_live_source_artifact_receipt_hash: str | None = None,
) -> tuple[dict[str, Any], bytes]:
    receipt = read_sec_edgar_text_table_live_source_artifact_receipt(
        live_source_artifact_receipt_id,
        expected_live_source_artifact_receipt_hash=expected_live_source_artifact_receipt_hash,
    )
    path = _artifact_path(receipt["live_source_artifact_receipt_id"])
    try:
        content = path.read_bytes()
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_retained_artifact_unreadable",
            "SEC EDGAR live source artifact could not be read for server-side parser use.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    expected_hash = str((receipt.get("source_artifact_receipt") or {}).get("content_sha256") or "")
    if hashlib.sha256(content).hexdigest() != expected_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_retained_artifact_hash_mismatch",
            "SEC EDGAR retained source artifact no longer matches its receipt hash.",
            http_status=409,
        )
    return receipt, content


def _fetch_with_retry(
    *,
    url: str,
    user_agent: str,
    timeout_seconds: int,
    max_bytes: int,
) -> SecEdgarFetchResult:
    attempts = 0
    result = SecEdgarFetchResult(status_code=503, complete=False)
    while attempts < 3:
        if attempts:
            _enforce_rate_limit()
        result = SEC_EDGAR_CLIENT.fetch_complete_submission_text(
            url=url,
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        if result.status_code not in RETRYABLE_STATUS_CODES:
            return result
        attempts += 1
        if attempts >= 3:
            return result
        SEC_EDGAR_SLEEP(min(_retry_after_seconds(result.headers), 1.0))
    return result


def _build_available_receipt(
    *,
    request_id: str,
    source_identity: Mapping[str, str],
    source_identity_hash: str,
    server_derived_url_hash: str,
    user_agent_hash: str,
    content_sha256: str,
    content_length: int,
) -> dict[str, Any]:
    artifact_ref_hash = stable_hash(
        {
            "hash_version": "sec_edgar_live_source_artifact_ref_hash_v1",
            "source_identity_hash": source_identity_hash,
            "content_sha256": content_sha256,
            "content_length": content_length,
        }
    )
    source_artifact_receipt_id = f"{SOURCE_ARTIFACT_RECEIPT_PREFIX}-{artifact_ref_hash[:24]}"
    source_artifact_receipt_hash = stable_hash(
        {
            "schema_id": SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "source_artifact_receipt_id": source_artifact_receipt_id,
            "source_artifact_ref_hash": artifact_ref_hash,
            "content_sha256": content_sha256,
            "content_length": content_length,
            "accession_or_submission_id_hash": source_identity["accession_or_submission_id_hash"],
            "cik_or_filer_ref_hash": source_identity["cik_or_filer_ref_hash"],
            "form_type": source_identity["form_type"],
            "filing_date": source_identity["filing_date"],
            "parser_family": PARSER_FAMILY,
            "parser_contract_id": PARSER_CONTRACT_ID,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "source_mode": SOURCE_MODE,
        }
    )
    receipt_hash_basis = {
        "hash_version": "sec_edgar_live_source_artifact_receipt_hash_v1",
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "acquisition_mode": ACQUISITION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "source_artifact_family": SOURCE_ARTIFACT_FAMILY,
        "source_identity_hash": source_identity_hash,
        "server_derived_url_hash": server_derived_url_hash,
        "source_artifact_receipt_hash": source_artifact_receipt_hash,
        "artifact_ref_hash": artifact_ref_hash,
        "content_sha256": content_sha256,
        "content_length": content_length,
        "rate_policy_id": RATE_POLICY_ID,
        "user_agent_hash": user_agent_hash,
    }
    receipt_hash = stable_hash(receipt_hash_basis)
    receipt_id = f"{RECEIPT_PREFIX}-{source_identity_hash[:24]}-{receipt_hash[:24]}"
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "acquisition_mode": ACQUISITION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "live_source_artifact_receipt_id": receipt_id,
        "live_source_artifact_receipt_hash": receipt_hash,
        "live_source_artifact_receipt_status": "available",
        "source_identity_hash": source_identity_hash,
        "source_identity": dict(source_identity),
        "server_derived_url_hash": server_derived_url_hash,
        "source_artifact_receipt": {
            "schema_id": SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "source_artifact_receipt_id": source_artifact_receipt_id,
            "source_artifact_receipt_hash": source_artifact_receipt_hash,
            "source_artifact_ref_hash": artifact_ref_hash,
            "content_sha256": content_sha256,
            "content_length": content_length,
            "parser_family": PARSER_FAMILY,
            "parser_contract_id": PARSER_CONTRACT_ID,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "source_mode": SOURCE_MODE,
            "server_owned_source_artifact_authority": True,
            "raw_source_artifact_ref_exposed": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "retained_source_artifact_manifest": {
            "source_artifact_family": SOURCE_ARTIFACT_FAMILY,
            "artifact_ref_hash": artifact_ref_hash,
            "content_sha256": content_sha256,
            "content_length": content_length,
            "retained_source_artifact_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "receipt_hash_basis": receipt_hash_basis,
        "request_id_hash": _sha256_text(request_id),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    cache_status: str,
    idempotent_replay: bool,
    network_request_made: bool,
    schema_id: str = SCHEMA_ID,
) -> dict[str, Any]:
    _verify_artifact_bytes(receipt)
    source_identity = dict(receipt["source_identity"])
    response = {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "mode": ACQUISITION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "source_artifact_family": SOURCE_ARTIFACT_FAMILY,
        "live_source_artifact_receipt_id": receipt["live_source_artifact_receipt_id"],
        "live_source_artifact_receipt_hash": receipt["live_source_artifact_receipt_hash"],
        "live_source_artifact_receipt_status": receipt["live_source_artifact_receipt_status"],
        "source_artifact_receipt": dict(receipt["source_artifact_receipt"]),
        "retained_source_artifact_manifest": dict(receipt["retained_source_artifact_manifest"]),
        "source_identity": {
            "source_identity_hash": receipt["source_identity_hash"],
            "cik_or_filer_ref_hash": source_identity["cik_or_filer_ref_hash"],
            "accession_or_submission_id_hash": source_identity["accession_or_submission_id_hash"],
            "form_type": source_identity["form_type"],
            "filing_date": source_identity["filing_date"],
        },
        "sec_request_policy": {
            "server_configured_user_agent_required": True,
            "server_configured_user_agent_hash": receipt["receipt_hash_basis"]["user_agent_hash"],
            "server_derived_url_hash": receipt["server_derived_url_hash"],
            "raw_sec_filing_url_exposed": False,
            "rate_policy_id": RATE_POLICY_ID,
            "selected_sec_rate_limit_ceiling": "no_more_than_10_requests_per_second_total_per_user",
            "configured_requests_per_second": _configured_rate_per_second(),
            "default_requests_per_second_until_configured": 1,
            "ci_live_network_disabled": True,
            "fake_sec_client_contract_double_supported": True,
        },
        "cache": {
            "cache_status": cache_status,
            "network_request_made": network_request_made,
            "cache_hit_avoids_network_request": cache_status in {"hit", "status"},
        },
        "idempotency": {
            "idempotent_replay": idempotent_replay,
            "same_client_request_id_same_source_identity_returns_same_receipt": True,
            "same_client_request_id_different_source_identity_fails_closed": True,
            "same_source_identity_new_client_request_id_returns_existing_receipt_status": True,
        },
        "compatibility": {
            "source_acquisition_authority_compatible": True,
            "source_artifact_receipt_schema_id": SOURCE_ARTIFACT_RECEIPT_SCHEMA_ID,
            "no_dataset_version_or_gate_b_mutation_in_acquisition_runtime": True,
            "parser_expansion_admitted": False,
        },
        "operator_visible_live_source_artifact_status": {
            "redacted_receipt_available": True,
            "retained_source_artifact_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_user_agent_configuration_fails_closed": True,
            "browser_supplied_raw_url_rejected": True,
            "browser_supplied_local_path_rejected": True,
            "browser_supplied_command_rejected": True,
            "content_hash_mismatch_rejected": True,
            "partial_download_rejected_without_authority": True,
            "cache_receipt_hash_mismatch_rejected": True,
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
            "record SEC EDGAR text-table source-acquisition authority from retained source-artifact evidence",
            "validate SEC EDGAR text-table authority envelope after separate parser/materialization authority exists",
            "bridge SEC EDGAR authority envelope into Layer 3 material authority when separately admitted",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_raw_authority_exposed",
            "SEC EDGAR live source-artifact acquisition would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_forbidden_request_fields",
            "SEC EDGAR live source-artifact acquisition does not admit caller paths, URLs, bytes, commands, credentials, connector, model, browser, source-expansion, parser-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_unknown_field",
            "SEC EDGAR live source-artifact acquisition fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_schema_not_admitted",
            "SEC EDGAR live source-artifact acquisition requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    expected_hash = str(request.get("expected_content_sha256") or "").strip()
    if expected_hash and not _is_hash(expected_hash):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_expected_content_sha256_invalid",
            "expected_content_sha256 must be a 64-character hash when supplied.",
            blocked_fields=["expected_content_sha256"],
        )
    return request


def _source_identity(request: Mapping[str, Any]) -> dict[str, str]:
    cik = _required(request, "cik_or_filer_ref").lstrip("0") or "0"
    accession = _required(request, "accession_or_submission_id")
    form_type = _required(request, "form_type").upper()
    filing_date = _required(request, "filing_date")
    if not _CIK_RE.fullmatch(cik):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_cik_not_admitted",
            "SEC EDGAR live source-artifact acquisition requires a numeric CIK.",
            blocked_fields=["cik_or_filer_ref"],
        )
    if not _ACCESSION_RE.fullmatch(accession):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_accession_not_admitted",
            "SEC EDGAR live source-artifact acquisition requires an accession formatted as ##########-##-######.",
            blocked_fields=["accession_or_submission_id"],
        )
    if not _FORM_TYPE_RE.fullmatch(form_type):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_form_type_not_admitted",
            "SEC EDGAR live source-artifact acquisition requires a bounded SEC form type.",
            blocked_fields=["form_type"],
        )
    try:
        date.fromisoformat(filing_date)
    except ValueError:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_filing_date_not_admitted",
            "SEC EDGAR live source-artifact acquisition requires filing_date in YYYY-MM-DD format.",
            blocked_fields=["filing_date"],
        )
    return {
        "cik_or_filer_ref_hash": _sha256_text(cik),
        "accession_or_submission_id_hash": _sha256_text(accession),
        "form_type": form_type,
        "filing_date": filing_date,
    }


def _server_derived_complete_submission_text_url(request: Mapping[str, Any]) -> str:
    cik = _required(request, "cik_or_filer_ref").lstrip("0") or "0"
    accession = _required(request, "accession_or_submission_id")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{accession}.txt"


def _find_existing_receipt(source_identity_hash: str) -> dict[str, Any] | None:
    receipts_dir = _receipts_dir()
    if not receipts_dir.exists():
        return None
    for path in sorted(receipts_dir.glob(f"{RECEIPT_PREFIX}-*.json")):
        receipt = _read_verified_receipt(path.stem)
        if receipt.get("source_identity_hash") == source_identity_hash:
            return receipt
    return None


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    if not _RECEIPT_ID_RE.fullmatch(receipt_id):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_id_invalid",
            "SEC EDGAR live source-artifact status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["live_source_artifact_receipt_id"],
        )
    path = _receipts_dir() / f"{receipt_id}.json"
    if not path.exists():
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_missing",
            "SEC EDGAR live source-artifact receipt was not found.",
            http_status=404,
            blocked_fields=["live_source_artifact_receipt_id"],
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_unreadable",
            "SEC EDGAR live source-artifact receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_invalid",
            "SEC EDGAR live source-artifact receipts must be JSON objects.",
            http_status=409,
        )
    if receipt.get("live_source_artifact_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_id_mismatch",
            "SEC EDGAR live source-artifact receipt id is stale or mismatched.",
            http_status=409,
        )
    expected_hash = stable_hash(receipt.get("receipt_hash_basis") or {})
    if receipt.get("live_source_artifact_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_hash_mismatch",
            "SEC EDGAR live source-artifact receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipts_dir() / f"{receipt['live_source_artifact_receipt_id']}.json"
    if target.exists():
        existing = _read_verified_receipt(target.stem)
        if existing.get("live_source_artifact_receipt_hash") != receipt.get("live_source_artifact_receipt_hash"):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_receipt_conflict",
                "A SEC EDGAR live source-artifact receipt already exists for this authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_verified_receipt(target.stem)
        if existing.get("live_source_artifact_receipt_hash") != receipt.get("live_source_artifact_receipt_hash"):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_receipt_conflict",
                "A SEC EDGAR live source-artifact receipt already exists for this authority.",
                http_status=409,
            )
        return
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_receipt_write_failed",
            "SEC EDGAR live source-artifact receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _write_artifact(receipt_id: str, content: bytes, content_sha256: str) -> None:
    target = _artifact_path(receipt_id)
    if target.exists():
        _verify_artifact_bytes({"live_source_artifact_receipt_id": receipt_id, "source_artifact_receipt": {"content_sha256": content_sha256}})
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(content)
    except FileExistsError:
        _verify_artifact_bytes({"live_source_artifact_receipt_id": receipt_id, "source_artifact_receipt": {"content_sha256": content_sha256}})
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_write_failed",
            "SEC EDGAR live source artifact could not be retained under the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _verify_artifact_bytes(receipt: Mapping[str, Any]) -> None:
    path = _artifact_path(str(receipt.get("live_source_artifact_receipt_id") or ""))
    if not path.exists():
        _blocked(
            "sec_edgar_text_table_live_source_artifact_retained_artifact_missing",
            "SEC EDGAR live source-artifact receipt no longer has a retained source artifact.",
            http_status=409,
        )
    try:
        content = path.read_bytes()
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_retained_artifact_unreadable",
            "SEC EDGAR live source artifact could not be read for hash verification.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    expected_hash = str((receipt.get("source_artifact_receipt") or {}).get("content_sha256") or "")
    if hashlib.sha256(content).hexdigest() != expected_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_retained_artifact_hash_mismatch",
            "SEC EDGAR retained source artifact no longer matches its receipt hash.",
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
            "sec_edgar_text_table_live_source_artifact_request_binding_unreadable",
            "SEC EDGAR live source-artifact request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, source_identity_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_text_table_live_source_artifact_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "source_identity_hash": source_identity_hash,
        "live_source_artifact_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("source_identity_hash") != source_identity_hash:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_request_binding_conflict",
                "SEC EDGAR live source-artifact request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_request_binding(request_id) or {}
        if existing.get("source_identity_hash") != source_identity_hash:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_request_binding_conflict",
                "SEC EDGAR live source-artifact request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    except OSError as exc:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_request_binding_write_failed",
            "SEC EDGAR live source-artifact request binding could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _enforce_rate_limit() -> None:
    limit = _configured_rate_per_second()
    min_interval = 1.0 / limit
    marker = _root() / "rate-limit-state.json"
    now = time.time()
    if marker.exists():
        try:
            state = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
        last_request_at = float(state.get("last_network_request_at") or 0)
        if last_request_at and now - last_request_at < min_interval:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_rate_limit_deferred",
                "SEC EDGAR live source-artifact acquisition is rate limited by server policy.",
                http_status=409,
                blocked_fields=["rate_limit"],
            )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({"last_network_request_at": now, "rate_policy_id": RATE_POLICY_ID}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _server_configured_user_agent() -> str:
    value = str(getattr(settings, "layer3_sec_edgar_user_agent", "") or "").strip()
    if not value:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_user_agent_missing",
            "SEC EDGAR live source-artifact acquisition requires a server-configured identifying User-Agent.",
            http_status=409,
            blocked_fields=["layer3_sec_edgar_user_agent"],
        )
    return value


def _require_live_network_enabled() -> None:
    if not bool(getattr(settings, "layer3_sec_edgar_live_network_enabled", False)):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_live_network_disabled",
            "Live SEC EDGAR network acquisition requires server configuration before any acquisition client may run.",
            http_status=409,
            blocked_fields=["layer3_sec_edgar_live_network_enabled"],
        )


def _configured_rate_per_second() -> int:
    value = int(getattr(settings, "layer3_sec_edgar_rate_limit_per_second", 1) or 1)
    if value <= 0 or value > SEC_RATE_LIMIT_CEILING_PER_SECOND:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_rate_limit_not_admitted",
            "SEC EDGAR live source-artifact acquisition rate must be between 1 and 10 requests per second.",
            http_status=409,
            blocked_fields=["layer3_sec_edgar_rate_limit_per_second"],
        )
    return value


def _max_bytes() -> int:
    value = int(getattr(settings, "layer3_sec_edgar_max_bytes", 25_000_000) or 0)
    if value <= 0:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_max_bytes_missing",
            "SEC EDGAR live source-artifact acquisition requires an explicit positive max byte limit.",
            http_status=409,
            blocked_fields=["layer3_sec_edgar_max_bytes"],
        )
    return value


def _timeout_seconds() -> int:
    return max(1, int(getattr(settings, "layer3_sec_edgar_timeout_seconds", 20) or 20))


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_storage_root_unavailable",
            "SEC EDGAR live source-artifact acquisition requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _receipts_dir() -> Path:
    return _root() / "receipts"


def _request_bindings_dir() -> Path:
    return _root() / "requests"


def _artifact_path(receipt_id: str) -> Path:
    return _root() / "artifacts" / f"{receipt_id}.txt"


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=FORBIDDEN_REQUEST_FIELDS, prefix=prefix)


def _read_bounded_bytes(response: Any, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining > 0:
        chunk = response.read(min(65536, remaining))
        if not chunk:
            break
        chunks.append(bytes(chunk))
        remaining -= len(chunk)
    content = b"".join(chunks)
    return content[: max_bytes + 1]


def _is_allowed_sec_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "sec.gov" or host.endswith(".sec.gov"))


def _retry_after_seconds(headers: Mapping[str, str]) -> float:
    value = str(headers.get("Retry-After") or headers.get("retry-after") or "").strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value) if value else None
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
        return 0.1


def _verify_expected_content_hash_for_receipt(request: Mapping[str, Any], receipt: Mapping[str, Any]) -> None:
    expected_content_sha256 = str(request.get("expected_content_sha256") or "").strip().lower()
    if not expected_content_sha256:
        return
    observed = str((receipt.get("source_artifact_receipt") or {}).get("content_sha256") or "").strip().lower()
    if observed != expected_content_sha256:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_content_hash_mismatch",
            "SEC EDGAR cached source-artifact acquisition content hash did not match expected authority.",
            http_status=409,
            blocked_fields=["expected_content_sha256"],
        )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_text_table_live_source_artifact_{key}_missing",
            f"SEC EDGAR live source-artifact acquisition requires {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    received = str(fields.get(key) or "").strip()
    if received != expected:
        _blocked(
            f"sec_edgar_text_table_live_source_artifact_{key}_mismatch",
            f"SEC EDGAR live source-artifact acquisition requires {key}={expected}.",
            blocked_fields=[key],
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_forbidden_output_ref(value: Any) -> bool:
    return contains_forbidden_ref_tree(value)


def _negative_invariants() -> dict[str, bool]:
    return {
        "browser_supplied_local_path_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_sec_url_admitted": False,
        "browser_supplied_artifact_bytes_admitted": False,
        "browser_supplied_command_admitted": False,
        "sec_edgar_parser_expansion_admitted": False,
        "xml_html_inline_xbrl_admitted": False,
        "dataset_version_or_gate_b_mutation_admitted": False,
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
) -> None:
    raise Layer3WorkbenchError(
        code,
        message,
        status="blocked",
        http_status=http_status,
        blocked_fields=blocked_fields or [],
    )


# ---------------------------------------------------------------------------
# CompanyFacts live oracle fetch
# ---------------------------------------------------------------------------

def acquire_sec_edgar_companyfacts_live_artifact(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Fetch SEC CompanyFacts JSON for a CIK through all existing gates and return a redacted receipt.

    Result carries ONLY: status, schema_id, receipt id/hash, content_sha256, cik_hash,
    observation/taxonomy/concept counts, and live_network flags.  Raw CIK, raw values,
    and raw accession are NEVER present in the returned dict.
    """
    if fields.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_operator_confirmation_missing",
            "operator_confirmation=true is required before live SEC EDGAR CompanyFacts acquisition.",
            http_status=409,
            blocked_fields=["operator_confirmation"],
        )
    # CI guard: mirrors SecEdgarHttpClient's gate so CI never reaches the network
    if os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_ci_network_disabled",
            "Live SEC EDGAR CompanyFacts acquisition is disabled in CI; use a fake client or offline file.",
            http_status=409,
        )
    _require_live_network_enabled()
    user_agent = _server_configured_user_agent()

    raw_cik = str(fields.get("cik") or "").strip().lstrip("0") or "0"
    if not _CIK_RE.fullmatch(raw_cik):
        _blocked(
            "sec_edgar_companyfacts_live_artifact_cik_not_admitted",
            "SEC EDGAR CompanyFacts acquisition requires a numeric CIK (1-10 digits).",
            http_status=409,
            blocked_fields=["cik"],
        )
    cik_hash = _sha256_text(raw_cik)
    padded_cik = raw_cik.zfill(10)

    # Idempotent replay keyed on cik_hash
    source_identity_hash = stable_hash(
        {"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash}
    )
    existing = _find_existing_companyfacts_receipt(source_identity_hash)
    if existing is not None:
        return _response_from_companyfacts_receipt(existing, idempotent_replay=True, network_request_made=False)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
    if not _is_allowed_sec_url(url):
        _blocked(
            "sec_edgar_companyfacts_live_artifact_url_not_admitted",
            "SEC EDGAR CompanyFacts URL is not within admitted sec.gov host space.",
            http_status=409,
        )

    _enforce_rate_limit()
    fetch_result = _fetch_companyfacts_with_retry(
        url=url,
        user_agent=user_agent,
        timeout_seconds=_timeout_seconds(),
        max_bytes=_max_bytes(),
    )

    if fetch_result.status_code != 200:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_fetch_failed",
            "SEC EDGAR CompanyFacts acquisition did not return HTTP 200.",
            http_status=409,
            blocked_fields=[f"http_status:{fetch_result.status_code}"],
        )
    if not fetch_result.complete:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_partial_download_blocked",
            "Partial SEC EDGAR CompanyFacts downloads do not create oracle authority.",
            http_status=409,
            blocked_fields=["content"],
        )
    content = bytes(fetch_result.content or b"")
    if len(content) > _max_bytes():
        _blocked(
            "sec_edgar_companyfacts_live_artifact_size_exceeded",
            "SEC EDGAR CompanyFacts response exceeds the configured byte limit.",
            http_status=409,
            blocked_fields=["content"],
        )
    if not content:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_empty_content_blocked",
            "Empty SEC EDGAR CompanyFacts responses do not create oracle authority.",
            http_status=409,
            blocked_fields=["content"],
        )
    content_sha256 = hashlib.sha256(content).hexdigest()

    try:
        payload = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_json_invalid",
            "SEC EDGAR CompanyFacts response is not valid JSON.",
            http_status=409,
            blocked_fields=["content"],
        )
    if not isinstance(payload, dict):
        _blocked(
            "sec_edgar_companyfacts_live_artifact_json_not_object",
            "SEC EDGAR CompanyFacts response must be a JSON object.",
            http_status=409,
            blocked_fields=["content"],
        )

    facts = payload.get("facts") if isinstance(payload.get("facts"), Mapping) else {}
    taxonomy_count = 0
    concept_count = 0
    observation_count = 0
    for concepts in facts.values():
        if not isinstance(concepts, Mapping):
            continue
        taxonomy_count += 1
        for concept in concepts.values():
            if not isinstance(concept, Mapping):
                continue
            units = concept.get("units") if isinstance(concept.get("units"), Mapping) else {}
            concept_count += 1
            for observations in units.values():
                if isinstance(observations, list):
                    observation_count += len(observations)

    receipt_hash_basis = {
        "hash_version": "sec_edgar_companyfacts_live_artifact_receipt_hash_v1",
        "schema_id": COMPANYFACTS_SCHEMA_ID,
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
    }
    receipt_hash = stable_hash(receipt_hash_basis)
    receipt_id = f"{COMPANYFACTS_RECEIPT_PREFIX}-{source_identity_hash[:24]}-{receipt_hash[:24]}"

    receipt = {
        "schema_id": COMPANYFACTS_SCHEMA_ID,
        "companyfacts_receipt_id": receipt_id,
        "companyfacts_receipt_hash": receipt_hash,
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
        "companyfacts_observation_count": observation_count,
        "taxonomy_count": taxonomy_count,
        "concept_count": concept_count,
        "receipt_hash_basis": receipt_hash_basis,
        "recorded_at": _server_time(),
    }

    _write_companyfacts_receipt(receipt)
    _write_companyfacts_artifact(receipt_id, content, content_sha256)

    return _response_from_companyfacts_receipt(receipt, idempotent_replay=False, network_request_made=True)


def _fetch_companyfacts_with_retry(
    *,
    url: str,
    user_agent: str,
    timeout_seconds: int,
    max_bytes: int,
) -> SecEdgarFetchResult:
    """Fetch CompanyFacts JSON reusing the same client/retry/rate-limit infrastructure."""
    # We cannot reuse fetch_complete_submission_text directly (different Accept header + URL),
    # so we implement the identical retry loop using the same SEC_EDGAR_CLIENT transport but
    # with a JSON Accept header by temporarily wrapping the client call.
    attempts = 0
    result = SecEdgarFetchResult(status_code=503, complete=False)
    while attempts < 3:
        if attempts:
            _enforce_rate_limit()
        # The underlying HTTP client gate is identical; we pass Accept:application/json by
        # reusing _fetch_companyfacts_once which calls the client's method with the JSON URL.
        result = _fetch_companyfacts_once(url=url, user_agent=user_agent, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
        if result.status_code not in RETRYABLE_STATUS_CODES:
            return result
        attempts += 1
        if attempts >= 3:
            return result
        SEC_EDGAR_SLEEP(min(_retry_after_seconds(result.headers), 1.0))
    return result


def _fetch_companyfacts_once(
    *,
    url: str,
    user_agent: str,
    timeout_seconds: int,
    max_bytes: int,
) -> SecEdgarFetchResult:
    """Direct HTTP fetch through the same CI/live-network guards as the text-table client.

    The CI and live-network checks live inside SecEdgarHttpClient.fetch_complete_submission_text,
    so we use a sibling request that goes through the same urllib stack with an application/json
    Accept header.  The guard logic is identical; we replicate it here to avoid coupling the
    JSON Accept header to the text-table-specific method signature.
    """
    import os as _os
    if _os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_ci_network_disabled",
            "Live SEC EDGAR CompanyFacts acquisition is disabled in CI; use a fake client or offline file.",
            http_status=409,
        )
    if not bool(getattr(settings, "layer3_sec_edgar_live_network_enabled", False)):
        _blocked(
            "sec_edgar_companyfacts_live_artifact_live_network_disabled",
            "Live SEC EDGAR CompanyFacts acquisition requires server configuration before the HTTP client may run.",
            http_status=409,
            blocked_fields=["layer3_sec_edgar_live_network_enabled"],
        )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json,*/*;q=0.1",
            "Accept-Encoding": "identity",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            final_url = str(response.geturl() or "")
            if not _is_allowed_sec_url(final_url):
                _blocked(
                    "sec_edgar_companyfacts_live_artifact_redirect_not_admitted",
                    "SEC EDGAR CompanyFacts acquisition does not admit redirects outside sec.gov.",
                    http_status=409,
                )
            content = _read_bounded_bytes(response, max_bytes)
            return SecEdgarFetchResult(
                status_code=int(getattr(response, "status", 200) or 200),
                content=content,
                headers=dict(response.headers.items()),
                final_url=final_url,
                complete=len(content) <= max_bytes,
            )
    except urllib.error.HTTPError as exc:
        error_bytes = b""
        try:
            error_bytes = _read_bounded_bytes(exc, min(max_bytes, 4096))
        except Exception:
            error_bytes = b""
        return SecEdgarFetchResult(
            status_code=int(exc.code),
            content=error_bytes,
            headers=dict(exc.headers.items()) if exc.headers else {},
            final_url=str(exc.url or url),
            complete=True,
        )
    except TimeoutError:
        return SecEdgarFetchResult(status_code=408, complete=False)
    except OSError:
        return SecEdgarFetchResult(status_code=503, complete=False)


def _find_existing_companyfacts_receipt(source_identity_hash: str) -> dict[str, Any] | None:
    receipts_dir = _companyfacts_receipts_dir()
    if not receipts_dir.exists():
        return None
    for path in sorted(receipts_dir.glob(f"{COMPANYFACTS_RECEIPT_PREFIX}-*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        # Skip non-fetch receipts (e.g. stage receipts share the same filename prefix).
        if receipt.get("schema_id") != COMPANYFACTS_SCHEMA_ID:
            continue
        if receipt.get("source_identity_hash") == source_identity_hash:
            return receipt
    return None


def _write_companyfacts_receipt(receipt: Mapping[str, Any]) -> None:
    target = _companyfacts_receipts_dir() / f"{receipt['companyfacts_receipt_id']}.json"
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        return
    except OSError as exc:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_receipt_write_failed",
            "SEC EDGAR CompanyFacts receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _write_companyfacts_artifact(receipt_id: str, content: bytes, content_sha256: str) -> None:
    target = _companyfacts_artifact_path(receipt_id)
    if target.exists():
        try:
            existing = target.read_bytes()
        except OSError as exc:
            _blocked(
                "sec_edgar_companyfacts_live_artifact_retained_artifact_unreadable",
                "SEC EDGAR retained CompanyFacts artifact could not be read for hash verification.",
                http_status=409,
                blocked_fields=[exc.__class__.__name__],
            )
        if hashlib.sha256(existing).hexdigest() != content_sha256:
            _blocked(
                "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch",
                "Retained CompanyFacts artifact bytes do not match the expected content hash.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(content)
    except FileExistsError:
        try:
            existing = target.read_bytes()
        except OSError as exc:
            _blocked(
                "sec_edgar_companyfacts_live_artifact_retained_artifact_unreadable",
                "SEC EDGAR retained CompanyFacts artifact could not be read for hash verification.",
                http_status=409,
                blocked_fields=[exc.__class__.__name__],
            )
        if hashlib.sha256(existing).hexdigest() != content_sha256:
            _blocked(
                "sec_edgar_companyfacts_live_artifact_retained_artifact_mismatch",
                "Retained CompanyFacts artifact bytes do not match the expected content hash.",
                http_status=409,
            )
    except OSError as exc:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_write_failed",
            "SEC EDGAR CompanyFacts artifact could not be retained.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _response_from_companyfacts_receipt(
    receipt: Mapping[str, Any],
    *,
    idempotent_replay: bool,
    network_request_made: bool,
) -> dict[str, Any]:
    return {
        "schema_id": COMPANYFACTS_SCHEMA_ID,
        "status": "available",
        "companyfacts_receipt_id": receipt["companyfacts_receipt_id"],
        "companyfacts_receipt_hash": receipt["companyfacts_receipt_hash"],
        "cik_hash": receipt["cik_hash"],
        "content_sha256": receipt["content_sha256"],
        "companyfacts_observation_count": receipt["companyfacts_observation_count"],
        "taxonomy_count": receipt["taxonomy_count"],
        "concept_count": receipt["concept_count"],
        "live_network_flags": {
            "live_network_fetch_performed": network_request_made,
            "ci_live_network_disabled": True,
            "server_configured_user_agent_required": True,
            "rate_limit_enforced": True,
            "host_allowlist_enforced": True,
        },
        "idempotent_replay": idempotent_replay,
        "raw_cik_exposed": False,
        "raw_values_exposed": False,
        "raw_accession_exposed": False,
    }


def _companyfacts_root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_companyfacts_live_artifact_storage_root_unavailable",
            "SEC EDGAR CompanyFacts acquisition requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / COMPANYFACTS_RECEIPT_DIR


def _companyfacts_receipts_dir() -> Path:
    return _companyfacts_root() / "receipts"


def _companyfacts_artifact_path(receipt_id: str) -> Path:
    return _companyfacts_root() / "companyfacts-store" / f"{receipt_id}.json"
