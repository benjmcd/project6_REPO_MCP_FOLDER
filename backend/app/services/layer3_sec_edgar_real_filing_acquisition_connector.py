from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_sec_edgar_live_source_artifact
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_real_filing_acquisition_connector.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_real_filing_acquisition_connector_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_real_filing_acquisition_connector_status.v1"
CORPUS_MANIFEST_SCHEMA_ID = "layer3.sec_edgar_real_filing_validation_corpus_manifest.v1"
SCHEMA_VERSION = 1
CONNECTOR_MODE = "sec_edgar_real_filing_acquisition_connector_v1"
OPERATOR_DECISION = "acquire_sec_edgar_real_filing_validation_corpus"
EXAMPLE_SET_MODE = "bounded_real_sec_validation_corpus_v1"
RECEIPT_PREFIX = "sec-edgar-real-filing-acquisition-connector"
RECEIPT_DIR = "layer3-sec-edgar-real-filing-acquisition-connector"
REDACTION_POLICY_ID = "sec_edgar_real_filing_acquisition_connector_redaction_v1"
SOURCE_FAMILY = "sec_edgar"
DEFAULT_CIK_REFS = ("0000320193",)
DEFAULT_FORM_TYPES = ("10-K", "10-Q", "8-K")
REAL_COMPANY_DISCOVERY_POLICY = "real_company_recent_annual_and_interim_or_current_v1"
DEFAULT_FILING_SELECTION_POLICY = "explicit_form_types_v1"
DEFAULT_REAL_COMPANY_MATRIX = ("MSFT", "STLD", "SONY", "CCJ")
VALIDATION_BREADTH_EXPANSION_SELECTION_VERSION = "sec_edgar_validation_breadth_expansion_selection_v1"
VALIDATION_BREADTH_EXPANSION_SELECTED_MATRIX = ("XOM", "PFE", "UAL", "T")
VALIDATION_BREADTH_EXPANSION_SELECTED_PROFILE_TAGS = (
    "energy_major",
    "pharmaceutical_life_sciences",
    "airline_transport",
    "telecom_media",
    "debt_intensive",
    "commodity_exposure",
)
VALIDATION_BREADTH_EXPANSION_RUNTIME_ENABLED = False
REAL_COMPANY_CIK_REFS = {
    "MSFT": "789019",
    "STLD": "1022671",
    "SONY": "313838",
    "CCJ": "1009001",
    "JPM": "19617",
    "MET": "1099219",
    "PLD": "1045609",
    "FIZZ": "69891",
}
REAL_COMPANY_PROFILE_TAGS = {
    "MSFT": ("domestic_large_cap", "technology"),
    "STLD": ("domestic_industrial", "materials"),
    "SONY": ("foreign_private_issuer", "foreign_form_family"),
    "CCJ": ("foreign_private_issuer", "resource_sector", "foreign_form_family"),
    "JPM": ("financial_institution", "domestic_large_cap"),
    "MET": ("insurance", "domestic_large_cap"),
    "PLD": ("reit", "domestic_large_cap"),
    "FIZZ": ("small_cap", "consumer_products"),
}
ANNUAL_FORM_TYPES = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
INTERIM_OR_CURRENT_FORM_TYPES = {"10-Q", "10-Q/A", "8-K", "8-K/A", "6-K", "6-K/A"}
MAX_CIK_REFS = 4
MAX_FORM_TYPES = 6
MAX_EXAMPLES = 8

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "connector_mode",
    "operator_decision",
    "example_set_mode",
    "cik_refs",
    "form_types",
    "company_matrix",
    "filing_selection_policy",
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
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_CIK_RE = re.compile(r"^\d{1,10}$")
_FORM_TYPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,31}$")
_RECEIPT_ID_RE = re.compile(r"^sec-edgar-real-filing-acquisition-connector-[a-f0-9]{24}-[a-f0-9]{24}$")


def acquire_sec_edgar_real_filing_validation_corpus(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "connector_mode", CONNECTOR_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_operator_confirmation_missing",
            "operator_confirmation=true is required before SEC EDGAR real-filing acquisition connector execution.",
            http_status=409,
            blocked_fields=["operator_confirmation"],
        )
    example_set = _example_set(request)
    example_set_hash = stable_hash({"hash_version": "sec_edgar_real_filing_example_set_hash_v1", **example_set})
    request_binding = _read_request_binding(request_id)
    if request_binding and request_binding.get("example_set_hash") != example_set_hash:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_client_request_id_conflict",
            "The client_request_id is already bound to a different SEC EDGAR real-filing example set.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _find_existing_receipt(example_set_hash)
    if existing is not None:
        _write_request_binding(request_id, example_set_hash, existing["connector_receipt_id"])
        return _response_from_receipt(
            existing,
            request_id=request_id,
            cache_status="hit",
            idempotent_replay=True,
            network_request_made=False,
        )

    user_agent = layer3_sec_edgar_live_source_artifact._server_configured_user_agent()
    submissions_records = _fetch_submissions_records(example_set["cik_refs"], user_agent=user_agent)
    selected_examples = _select_examples(submissions_records, example_set)
    acquisition_receipts = _acquire_complete_submission_text_examples(
        selected_examples,
        request_id=request_id,
    )
    receipt = _build_receipt(
        request_id=request_id,
        example_set=example_set,
        example_set_hash=example_set_hash,
        user_agent_hash=_sha256_text(user_agent),
        selected_examples=selected_examples,
        acquisition_receipts=acquisition_receipts,
    )
    _write_receipt(receipt)
    _write_request_binding(request_id, example_set_hash, receipt["connector_receipt_id"])
    return _response_from_receipt(
        receipt,
        request_id=request_id,
        cache_status="miss",
        idempotent_replay=False,
        network_request_made=True,
    )


def inspect_sec_edgar_real_filing_acquisition_connector_status(
    connector_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(connector_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-real-filing-connector-status-{receipt['connector_receipt_hash'][:12]}",
        cache_status="status",
        idempotent_replay=False,
        network_request_made=False,
        schema_id=STATUS_SCHEMA_ID,
    )


def read_sec_edgar_real_filing_acquisition_connector_receipt(
    connector_receipt_id: str,
    *,
    expected_connector_receipt_hash: str | None = None,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(connector_receipt_id)
    expected_hash = str(expected_connector_receipt_hash or "").strip()
    if expected_hash and receipt.get("connector_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_hash_mismatch",
            "SEC EDGAR real-filing acquisition connector receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["connector_receipt_hash"],
        )
    return receipt


def _fetch_submissions_records(cik_refs: tuple[str, ...], *, user_agent: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for index, cik in enumerate(cik_refs):
        if index:
            _sleep_for_rate_policy()
        url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        layer3_sec_edgar_live_source_artifact._enforce_rate_limit()
        result = layer3_sec_edgar_live_source_artifact._fetch_with_retry(
            url=url,
            user_agent=user_agent,
            timeout_seconds=layer3_sec_edgar_live_source_artifact._timeout_seconds(),
            max_bytes=min(layer3_sec_edgar_live_source_artifact._max_bytes(), 5_000_000),
        )
        if result.status_code != 200 or not result.complete:
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_submissions_fetch_failed",
                "SEC EDGAR submissions metadata fetch did not return a complete HTTP 200 response.",
                http_status=409,
                blocked_fields=[f"http_status:{result.status_code}"],
            )
        try:
            payload = json.loads(bytes(result.content or b"").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_submissions_json_invalid",
                "SEC EDGAR submissions metadata response was not valid JSON.",
                http_status=409,
            )
        if not isinstance(payload, dict):
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_submissions_json_invalid",
                "SEC EDGAR submissions metadata response must be a JSON object.",
                http_status=409,
            )
        records[cik] = payload
    return records


def _select_examples(
    submissions_records: Mapping[str, Mapping[str, Any]],
    example_set: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    form_types = tuple(str(item) for item in example_set.get("form_types") or ())
    policy = str(example_set.get("filing_selection_policy") or DEFAULT_FILING_SELECTION_POLICY)
    company_by_cik = {
        str(cik): str(ticker)
        for ticker, cik in zip(example_set.get("company_matrix") or (), example_set.get("cik_refs") or ())
    }
    for cik, payload in submissions_records.items():
        recent = ((payload.get("filings") or {}).get("recent") or {}) if isinstance(payload, Mapping) else {}
        forms = list(recent.get("form") or [])
        accessions = list(recent.get("accessionNumber") or [])
        filing_dates = list(recent.get("filingDate") or [])
        report_dates = list(recent.get("reportDate") or [])
        primary_documents = list(recent.get("primaryDocument") or [])
        primary_descriptions = list(recent.get("primaryDocDescription") or [])
        company_name = str(payload.get("name") or "").strip()
        if policy == REAL_COMPANY_DISCOVERY_POLICY:
            selected_indexes = _discovered_recent_filing_indexes(forms)
        else:
            selected_indexes = []
            for form_type in form_types:
                match_index = _first_form_index(forms, form_type)
                if match_index is None:
                    _blocked(
                        "sec_edgar_real_filing_acquisition_connector_required_form_missing",
                        "SEC EDGAR submissions metadata did not contain a required validation form.",
                        http_status=409,
                        blocked_fields=[form_type],
                    )
                selected_indexes.append(match_index)
        for match_index in selected_indexes:
            form_type = _list_value(forms, match_index).upper()
            accession = _list_value(accessions, match_index)
            filing_date = _list_value(filing_dates, match_index)
            primary_document = _list_value(primary_documents, match_index)
            example = {
                "example_id": f"sec-edgar-real-{_sha256_text(cik + form_type + accession)[:12]}",
                "cik": cik,
                "cik_hash": _sha256_text(cik),
                "ticker": company_by_cik.get(str(cik), ""),
                "ticker_hash": (
                    _sha256_text(company_by_cik[str(cik)])
                    if str(cik) in company_by_cik
                    else None
                ),
                "accession_or_submission_id": accession,
                "accession_or_submission_id_hash": _sha256_text(accession),
                "form_type": form_type,
                "filing_date": filing_date,
                "report_period": _list_value(report_dates, match_index) or None,
                "company_name_hash": _sha256_text(company_name) if company_name else None,
                "issuer_profile_tags": _issuer_profile_tags(company_by_cik.get(str(cik), ""), form_type),
                "primary_document_hash": _sha256_text(primary_document) if primary_document else None,
                "primary_document_family": _classify_primary_document(primary_document),
                "primary_document_description_hash": (
                    _sha256_text(_list_value(primary_descriptions, match_index))
                    if _list_value(primary_descriptions, match_index)
                    else None
                ),
                "source_family": "complete_submission_text",
                "source_family_roles": _source_family_roles(primary_document),
                "expected_support_status": "supported_complete_submission_text",
                "selection_policy": policy,
                "parser_family": "sec_edgar_filing",
                "parser_contract_id": "aps_sec_edgar_filing_parser_v1",
                "artifact_role_set": [
                    "source_evidence_artifact",
                    "parser_input_artifact",
                    "provenance_audit_artifact",
                    "operator_inspection_artifact",
                ],
                "diagnostics": _diagnostics_for_primary_document(primary_document),
            }
            _validate_selected_example(example)
            selected.append(example)
            if len(selected) >= MAX_EXAMPLES:
                return selected
    return selected


def _acquire_complete_submission_text_examples(
    selected_examples: list[dict[str, Any]],
    *,
    request_id: str,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for index, example in enumerate(selected_examples):
        if index:
            _sleep_for_rate_policy()
        response = layer3_sec_edgar_live_source_artifact.acquire_sec_edgar_text_table_live_source_artifact(
            {
                "client_request_id": f"{request_id}-source-artifact-{example['example_id']}",
                "acquisition_mode": layer3_sec_edgar_live_source_artifact.ACQUISITION_MODE,
                "operator_decision": layer3_sec_edgar_live_source_artifact.OPERATOR_DECISION,
                "cik_or_filer_ref": example["cik"],
                "accession_or_submission_id": example["accession_or_submission_id"],
                "form_type": example["form_type"],
                "filing_date": example["filing_date"],
                "operator_confirmation": True,
            }
        )
        receipts.append(_redacted_acquisition_receipt(response, example_id=str(example["example_id"])))
    return receipts


def _build_receipt(
    *,
    request_id: str,
    example_set: Mapping[str, Any],
    example_set_hash: str,
    user_agent_hash: str,
    selected_examples: list[dict[str, Any]],
    acquisition_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    redacted_examples = [_redact_example(example) for example in selected_examples]
    source_family_inventory = _source_family_inventory(redacted_examples)
    diagnostics = {
        "html_inline_xbrl_explicitly_classified": any(
            "html_inline_xbrl_classified_not_parsed" in item["source_family_roles"]
            for item in redacted_examples
        ),
        "generic_text_downgrade_performed": False,
        "full_sec_support_claimed": False,
        "unsupported_or_degraded_requires_future_parser_slice": True,
    }
    receipt_hash_basis = {
        "hash_version": "sec_edgar_real_filing_acquisition_connector_receipt_hash_v1",
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "connector_mode": CONNECTOR_MODE,
        "operator_decision": OPERATOR_DECISION,
        "example_set_hash": example_set_hash,
        "sec_user_agent_hash": user_agent_hash,
        "source_family_inventory_hash": stable_hash(source_family_inventory),
        "acquisition_receipt_hashes": [
            item["live_source_artifact_receipt_hash"] for item in acquisition_receipts
        ],
        "artifact_hashes": [
            item["source_artifact_receipt"]["content_sha256"] for item in acquisition_receipts
        ],
        "classification_hashes": [stable_hash(item) for item in redacted_examples],
        "diagnostics_hash": stable_hash(diagnostics),
    }
    receipt_hash = stable_hash(receipt_hash_basis)
    receipt_id = f"{RECEIPT_PREFIX}-{example_set_hash[:24]}-{receipt_hash[:24]}"
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "connector_mode": CONNECTOR_MODE,
        "operator_decision": OPERATOR_DECISION,
        "connector_receipt_id": receipt_id,
        "connector_receipt_hash": receipt_hash,
        "connector_state": "available",
        "example_set": {
            "example_set_mode": example_set["example_set_mode"],
            "example_set_hash": example_set_hash,
            "cik_ref_hashes": [_sha256_text(cik) for cik in example_set["cik_refs"]],
            "form_types": list(example_set["form_types"]),
            "company_matrix": list(example_set.get("company_matrix") or []),
            "filing_selection_policy": example_set["filing_selection_policy"],
        },
        "corpus_manifest": {
            "schema_id": CORPUS_MANIFEST_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "example_count": len(redacted_examples),
            "example_records": redacted_examples,
            "source_family_inventory": source_family_inventory,
            "manifest_hash": stable_hash(
                {
                    "examples": redacted_examples,
                    "acquisition_receipts": acquisition_receipts,
                    "diagnostics": diagnostics,
                }
            ),
        },
        "acquisition_receipts": acquisition_receipts,
        "diagnostics": diagnostics,
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
    response = {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "connector_mode": CONNECTOR_MODE,
        "operator_decision": OPERATOR_DECISION,
        "connector_state": receipt["connector_state"],
        "connector_receipt_id": receipt["connector_receipt_id"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "example_set": dict(receipt["example_set"]),
        "corpus_manifest": dict(receipt["corpus_manifest"]),
        "acquisition_receipts": list(receipt["acquisition_receipts"]),
        "diagnostics": dict(receipt["diagnostics"]),
        "sec_request_policy": {
            "server_configured_user_agent_required": True,
            "server_configured_user_agent_hash": receipt["receipt_hash_basis"]["sec_user_agent_hash"],
            "rate_policy_id": layer3_sec_edgar_live_source_artifact.RATE_POLICY_ID,
            "selected_sec_rate_limit_ceiling": "no_more_than_10_requests_per_second_total_per_user",
            "configured_requests_per_second": layer3_sec_edgar_live_source_artifact._configured_rate_per_second(),
            "ci_live_network_disabled": True,
            "fake_sec_client_contract_double_required_in_ci": True,
            "existing_live_source_artifact_client_reused": True,
            "duplicate_network_stack_created": False,
        },
        "cache": {
            "cache_status": cache_status,
            "network_request_made": network_request_made,
            "cache_hit_avoids_network_request": cache_status in {"hit", "status"},
        },
        "idempotency": {
            "idempotent_replay": idempotent_replay,
            "same_client_request_id_same_example_set_returns_same_connector_receipt": True,
            "same_client_request_id_different_example_set_fails_closed": True,
            "same_example_set_new_client_request_id_returns_existing_status": True,
        },
        "downstream_validation": {
            "supported_first_parser_path": "complete_submission_text_to_sec_text_table_authority_to_dataset_version_layer3_downstream",
            "layer3_downstream_execution_performed_by_connector": False,
            "next_allowed_action": "drive selected complete-submission text source artifacts through source acquisition, material bridge, Gate B, downstream proof, and status.",
        },
        "operator_visible_status": {
            "redacted_connector_receipt_available": True,
            "raw_sec_url_rendered": False,
            "raw_local_path_rendered": False,
            "artifact_bytes_rendered": False,
            "html_inline_xbrl_classified_not_parsed": receipt["diagnostics"][
                "html_inline_xbrl_explicitly_classified"
            ],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "inspect redacted SEC EDGAR real-filing acquisition connector status",
            "record SEC EDGAR source-acquisition authority for supported complete-submission text artifacts",
            "select a separate HTML/iXBRL/XML parser-source-family slice before parsing modern SEC filing HTML or XBRL facts",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_raw_authority_exposed",
            "SEC EDGAR real-filing acquisition connector would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_forbidden_request_fields",
            "SEC EDGAR real-filing acquisition connector does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_unknown_field",
            "SEC EDGAR real-filing acquisition connector fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_schema_not_admitted",
            "SEC EDGAR real-filing acquisition connector requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _example_set(request: Mapping[str, Any]) -> dict[str, Any]:
    example_set_mode = str(request.get("example_set_mode") or EXAMPLE_SET_MODE).strip()
    if example_set_mode != EXAMPLE_SET_MODE:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_example_set_mode_not_admitted",
            "SEC EDGAR real-filing acquisition connector requires the bounded validation corpus mode.",
            blocked_fields=["example_set_mode"],
        )
    filing_selection_policy = str(request.get("filing_selection_policy") or DEFAULT_FILING_SELECTION_POLICY).strip()
    if filing_selection_policy not in {DEFAULT_FILING_SELECTION_POLICY, REAL_COMPANY_DISCOVERY_POLICY}:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_selection_policy_not_admitted",
            "SEC EDGAR real-filing acquisition connector requires an admitted filing selection policy.",
            blocked_fields=["filing_selection_policy"],
        )
    company_matrix = _normalise_company_matrix(request.get("company_matrix") or ())
    if filing_selection_policy == REAL_COMPANY_DISCOVERY_POLICY:
        if not company_matrix:
            company_matrix = DEFAULT_REAL_COMPANY_MATRIX
        cik_refs = tuple(REAL_COMPANY_CIK_REFS[ticker] for ticker in company_matrix)
        form_types = ()
    else:
        cik_refs = _normalise_cik_refs(request.get("cik_refs") or DEFAULT_CIK_REFS)
        form_types = _normalise_form_types(request.get("form_types") or DEFAULT_FORM_TYPES)
    return {
        "example_set_mode": example_set_mode,
        "cik_refs": cik_refs,
        "form_types": form_types,
        "company_matrix": company_matrix,
        "filing_selection_policy": filing_selection_policy,
    }


def _normalise_company_matrix(value: Any) -> tuple[str, ...]:
    if value in (None, "", ()):
        return ()
    values = tuple(dict.fromkeys(str(item or "").strip().upper() for item in _as_list(value)))
    if not values or len(values) > len(DEFAULT_REAL_COMPANY_MATRIX):
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_company_matrix_not_admitted",
            "SEC EDGAR real-company validation admits only the selected bounded company matrix.",
            blocked_fields=["company_matrix"],
        )
    unknown = [item for item in values if item not in REAL_COMPANY_CIK_REFS]
    if unknown:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_company_matrix_unknown",
            "SEC EDGAR real-company validation company matrix contains an unadmitted ticker.",
            blocked_fields=["company_matrix"],
        )
    return values


def _issuer_profile_tags(ticker: str, form_type: str) -> list[str]:
    tags = list(REAL_COMPANY_PROFILE_TAGS.get(str(ticker or "").upper(), ()))
    form = str(form_type or "").upper()
    if form in ANNUAL_FORM_TYPES:
        tags.append("annual_form_family")
    if form in INTERIM_OR_CURRENT_FORM_TYPES:
        tags.append("interim_or_current_form_family")
    if form.endswith("/A"):
        tags.append("amended_filing")
    if form in {"20-F", "20-F/A", "40-F", "40-F/A", "6-K", "6-K/A"}:
        tags.append("foreign_form_family")
    return list(dict.fromkeys(tags))


def _normalise_cik_refs(value: Any) -> tuple[str, ...]:
    values = [str(item or "").strip().lstrip("0") or "0" for item in _as_list(value)]
    values = tuple(dict.fromkeys(values))
    if not values or len(values) > MAX_CIK_REFS:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_cik_refs_not_admitted",
            "SEC EDGAR real-filing acquisition connector requires one to four CIK refs.",
            blocked_fields=["cik_refs"],
        )
    for item in values:
        if not _CIK_RE.fullmatch(item):
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_cik_ref_invalid",
                "SEC EDGAR real-filing acquisition connector CIK refs must be numeric.",
                blocked_fields=["cik_refs"],
            )
    return values


def _normalise_form_types(value: Any) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(str(item or "").strip().upper() for item in _as_list(value)))
    if not values or len(values) > MAX_FORM_TYPES:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_form_types_not_admitted",
            "SEC EDGAR real-filing acquisition connector requires one to six form types.",
            blocked_fields=["form_types"],
        )
    for item in values:
        if not _FORM_TYPE_RE.fullmatch(item):
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_form_type_invalid",
                "SEC EDGAR real-filing acquisition connector form types must be bounded SEC form identifiers.",
                blocked_fields=["form_types"],
            )
    return values


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _redacted_acquisition_receipt(response: Mapping[str, Any], *, example_id: str) -> dict[str, Any]:
    return {
        "example_id": example_id,
        "live_source_artifact_receipt_id": response["live_source_artifact_receipt_id"],
        "live_source_artifact_receipt_hash": response["live_source_artifact_receipt_hash"],
        "live_source_artifact_receipt_status": response["live_source_artifact_receipt_status"],
        "source_artifact_receipt": dict(response["source_artifact_receipt"]),
        "retained_source_artifact_manifest": dict(response["retained_source_artifact_manifest"]),
    }


def _redact_example(example: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "example_id": example["example_id"],
        "cik_hash": example["cik_hash"],
        "ticker_hash": example.get("ticker_hash"),
        "accession_or_submission_id_hash": example["accession_or_submission_id_hash"],
        "form_type": example["form_type"],
        "filing_date": example["filing_date"],
        "report_period_present": bool(example.get("report_period")),
        "company_name_hash": example.get("company_name_hash"),
        "issuer_profile_tags": list(example.get("issuer_profile_tags") or []),
        "primary_document_hash": example.get("primary_document_hash"),
        "primary_document_family": example["primary_document_family"],
        "source_family": example["source_family"],
        "source_family_roles": list(example["source_family_roles"]),
        "expected_support_status": example["expected_support_status"],
        "selection_policy": example.get("selection_policy", DEFAULT_FILING_SELECTION_POLICY),
        "parser_family": example["parser_family"],
        "parser_contract_id": example["parser_contract_id"],
        "artifact_role_set": list(example["artifact_role_set"]),
        "diagnostics": dict(example["diagnostics"]),
    }


def _source_family_inventory(examples: list[dict[str, Any]]) -> dict[str, Any]:
    roles: dict[str, int] = {}
    for example in examples:
        for role in example.get("source_family_roles") or []:
            roles[str(role)] = roles.get(str(role), 0) + 1
    return {
        "source_family": SOURCE_FAMILY,
        "example_count": len(examples),
        "role_counts": roles,
        "complete_submission_text_examples": sum(
            1 for example in examples if example.get("source_family") == "complete_submission_text"
        ),
    }


def _first_form_index(forms: list[Any], form_type: str) -> int | None:
    for index, value in enumerate(forms):
        if str(value or "").strip().upper() == form_type:
            return index
    return None


def _discovered_recent_filing_indexes(forms: list[Any]) -> list[int]:
    annual_index = _first_form_family_index(forms, ANNUAL_FORM_TYPES)
    interim_index = _first_form_family_index(forms, INTERIM_OR_CURRENT_FORM_TYPES)
    selected = list(dict.fromkeys(index for index in (annual_index, interim_index) if index is not None))
    if not selected:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_no_discovered_validation_filing",
            "SEC EDGAR submissions metadata did not contain an annual, interim, or current filing for validation.",
            http_status=409,
            blocked_fields=["filing_selection_policy"],
        )
    return selected


def _first_form_family_index(forms: list[Any], allowed: set[str]) -> int | None:
    for index, value in enumerate(forms):
        if str(value or "").strip().upper() in allowed:
            return index
    return None


def _list_value(values: list[Any], index: int) -> str:
    if index >= len(values):
        return ""
    return str(values[index] or "").strip()


def _classify_primary_document(primary_document: str) -> str:
    lower = primary_document.lower()
    if lower.endswith((".htm", ".html")):
        return "filing_html_or_inline_xbrl"
    if lower.endswith(".xml"):
        return "xml_xbrl"
    if lower.endswith(".pdf"):
        return "pdf_candidate_b_page_evidence"
    return "complete_submission_text_related_artifact"


def _source_family_roles(primary_document: str) -> list[str]:
    roles = ["complete_submission_text", "filing_identity", "section_inventory_candidate", "table_inventory_candidate"]
    family = _classify_primary_document(primary_document)
    if family == "filing_html_or_inline_xbrl":
        roles.append("html_inline_xbrl_classified_not_parsed")
    elif family == "xml_xbrl":
        roles.append("xml_xbrl_classified_not_parsed")
    elif family == "pdf_candidate_b_page_evidence":
        roles.append("pdf_candidate_b_page_evidence")
    return roles


def _diagnostics_for_primary_document(primary_document: str) -> dict[str, Any]:
    family = _classify_primary_document(primary_document)
    return {
        "primary_document_family": family,
        "complete_submission_text_acquisition_supported": True,
        "html_inline_xbrl_parser_runtime_admitted": False,
        "xml_xbrl_fact_authority_runtime_admitted": False,
        "generic_text_downgrade_performed": False,
        "candidate_b_general_sec_parser_used": False,
    }


def _validate_selected_example(example: Mapping[str, Any]) -> None:
    accession = str(example.get("accession_or_submission_id") or "")
    filing_date = str(example.get("filing_date") or "")
    if not accession or not filing_date:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_selected_example_incomplete",
            "SEC EDGAR selected validation examples require accession and filing date metadata.",
            http_status=409,
        )


def _find_existing_receipt(example_set_hash: str) -> dict[str, Any] | None:
    receipts_dir = _receipts_dir()
    if not receipts_dir.exists():
        return None
    for path in sorted(receipts_dir.glob(f"{RECEIPT_PREFIX}-*.json")):
        receipt = _read_verified_receipt(path.stem)
        if receipt.get("example_set", {}).get("example_set_hash") == example_set_hash:
            return receipt
    return None


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    if not _RECEIPT_ID_RE.fullmatch(receipt_id):
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_id_invalid",
            "SEC EDGAR real-filing acquisition connector status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_real_filing_acquisition_connector_receipt_id"],
        )
    path = _receipts_dir() / f"{receipt_id}.json"
    if not path.exists():
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_missing",
            "SEC EDGAR real-filing acquisition connector receipt was not found.",
            http_status=404,
            blocked_fields=["sec_edgar_real_filing_acquisition_connector_receipt_id"],
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_unreadable",
            "SEC EDGAR real-filing acquisition connector receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict):
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_invalid",
            "SEC EDGAR real-filing acquisition connector receipts must be JSON objects.",
            http_status=409,
        )
    if receipt.get("connector_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_id_mismatch",
            "SEC EDGAR real-filing acquisition connector receipt id is stale or mismatched.",
            http_status=409,
        )
    expected_hash = stable_hash(receipt.get("receipt_hash_basis") or {})
    if receipt.get("connector_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_hash_mismatch",
            "SEC EDGAR real-filing acquisition connector receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipts_dir() / f"{receipt['connector_receipt_id']}.json"
    if target.exists():
        existing = _read_verified_receipt(target.stem)
        if existing.get("connector_receipt_hash") != receipt.get("connector_receipt_hash"):
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_receipt_conflict",
                "A SEC EDGAR real-filing acquisition connector receipt already exists for this authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        return
    except OSError as exc:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_receipt_write_failed",
            "SEC EDGAR real-filing acquisition connector receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_request_binding_unreadable",
            "SEC EDGAR real-filing acquisition connector request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, example_set_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "example_set_hash": example_set_hash,
        "connector_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("example_set_hash") != example_set_hash:
            _blocked(
                "sec_edgar_real_filing_acquisition_connector_request_binding_conflict",
                "SEC EDGAR real-filing acquisition connector request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        return


def _sleep_for_rate_policy() -> None:
    rate = layer3_sec_edgar_live_source_artifact._configured_rate_per_second()
    layer3_sec_edgar_live_source_artifact.SEC_EDGAR_SLEEP(1.0 / rate)


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_real_filing_acquisition_connector_storage_root_unavailable",
            "SEC EDGAR real-filing acquisition connector requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _receipts_dir() -> Path:
    return _root() / "receipts"


def _request_bindings_dir() -> Path:
    return _root() / "requests"


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in FORBIDDEN_REQUEST_FIELDS:
                found.append(child_path)
            found.extend(_find_forbidden_nested_fields(nested, child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_find_forbidden_nested_fields(nested, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        text = value.strip()
        if _RAW_URL_RE.search(text) or _LOCAL_PATH_RE.search(text):
            found.append(prefix or "request_body")
    return found


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return bool(_LOCAL_PATH_RE.search(text) or text.startswith("http://") or text.startswith("https://"))
    return False


def _negative_invariants() -> dict[str, bool]:
    return {
        "browser_supplied_local_path_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_sec_url_admitted": False,
        "browser_supplied_artifact_bytes_admitted": False,
        "browser_supplied_command_admitted": False,
        "duplicate_sec_network_stack_created": False,
        "sec_edgar_parser_expansion_admitted": False,
        "html_inline_xbrl_parser_runtime_admitted": False,
        "xml_xbrl_fact_authority_runtime_admitted": False,
        "candidate_b_general_sec_parser_admitted": False,
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


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_real_filing_acquisition_connector_{key}_missing",
            f"SEC EDGAR real-filing acquisition connector requires {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    received = str(fields.get(key) or "").strip()
    if received != expected:
        _blocked(
            f"sec_edgar_real_filing_acquisition_connector_{key}_mismatch",
            f"SEC EDGAR real-filing acquisition connector requires {key}={expected}.",
            blocked_fields=[key],
        )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
