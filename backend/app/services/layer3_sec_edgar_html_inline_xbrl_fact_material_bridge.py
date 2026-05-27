from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import html as html_lib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Dataset, DatasetSourceProvenance, DatasetVersion, VariableDefinition
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_xbrl_sidecar,
    layer3_workbench,
)
from app.services.layer3_gate_b_state import (
    candidate_decision_manifest,
    gate_b_decision_manifest_id as compute_gate_b_decision_manifest_id,
    material_candidate_basis_from_decision,
    material_candidate_basis_from_preview,
    material_preview_hash,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_material_bridge.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_material_bridge_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_material_bridge_status.v1"
SCHEMA_VERSION = 1
BRIDGE_MODE = "sec_edgar_html_inline_xbrl_fact_authority_to_layer3_fact_material_authority_v1"
OPERATOR_DECISION = "bridge_sec_edgar_html_inline_xbrl_fact_authority_to_layer3_fact_material_authority"
READY_STATE = "sec_edgar_html_inline_xbrl_fact_material_bridge_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_fact_material_bridge_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
PARSER_FAMILY = "sec_edgar_html_inline_xbrl_source_family_parser_v1"
PARSER_CONTRACT_ID = PARSER_FAMILY
TYPED_CONTENT_CONTRACT_ID = "sec_edgar_html_inline_xbrl_fact_material_units_v1"
MATERIAL_PREVIEW_SCHEMA_ID = "layer3.material_preview_request.v1"
GATE_B_DECISION_SCHEMA_ID = "layer3.gate_b_decision_request.v1"
SOURCE_CLASS = "dataset_version"
SOURCE_CANDIDATE_PREFIX = "src-dataset_version-"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-fact-material-bridge"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_fact_material_bridge_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_fact_material_bridge_hash_v1"
REGEX_FACT_AUTHORITY_INPUT_MODE = "regex_fact_authority_receipt"
ARELLE_FACT_AUTHORITY_INPUT_MODE = "arelle_resolved_fact_authority_sidecar_receipt"
MAX_FACT_UNITS = 1000
REGEX_FACT_FIELDNAMES = [
    "fact_order",
    "element_name",
    "qualified_name",
    "namespace_prefix",
    "local_name",
    "context_ref_hash",
    "unit_ref_hash",
    "decimals_or_precision",
    "scale_or_format",
    "continued_fact_hash_if_present",
    "source_order_hash",
    "source_artifact_receipt_hash",
    "primary_document_hash",
    "value_text",
    "value_hash",
    "value_length",
    "table_candidate_anchor_hash",
    "parser_receipt_hash",
    "fact_authority_receipt_hash",
]
ARELLE_FACT_FIELDNAMES = [
    *REGEX_FACT_FIELDNAMES,
    "resolved_fact_id",
    "entry_document_index",
    "concept_qname",
    "concept_namespace",
    "concept_local_name",
    "concept_standard",
    "concept_extension",
    "concept_resolved_from_dts",
    "context_id",
    "unit_id",
    "period_type",
    "period_start",
    "period_end",
    "period_instant",
    "period_forever",
    "period_resolved",
    "unit_measures_json",
    "unit_currency",
    "unit_numerator_json",
    "unit_denominator_json",
    "unit_resolved",
    "explicit_dimensions_json",
    "typed_dimensions_json",
    "explicit_dimension_count",
    "typed_dimension_count",
    "hidden",
    "continued",
    "footnote_count",
    "value_redacted",
    "value_semantics",
    "effective_value_text",
    "effective_value_hash",
    "effective_value_length",
    "lexical_value_text",
    "lexical_value_hash",
    "lexical_value_length",
    "transform_sign",
    "transform_scale",
    "transform_decimals",
    "transform_precision",
    "transform_format",
]
FACT_FIELDNAMES = REGEX_FACT_FIELDNAMES

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "bridge_mode",
    "operator_decision",
    "fact_authority_receipt_id",
    "fact_authority_receipt_hash",
    "arelle_sidecar_receipt_id",
    "arelle_sidecar_receipt_hash",
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
    "expected_fact_inventory_hash",
    "expected_diagnostics_hash",
    "expected_materialization_receipt_hash",
    "expected_material_preview_hash",
    "expected_gate_b_decision_manifest_id",
    "rollback_confirmed",
    "operator_confirmed",
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
_REDACT_KEYS = {"blob_ref", "content_units_ref", "diagnostics_ref", "download_exchange_ref", "raw_storage_ref", "source_artifact_key", "storage_ref"}
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_IX_FACT_RE = re.compile(
    r"<\s*(?P<tag>ix:(?:nonFraction|nonNumeric|fraction))\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)</\s*(?P=tag)\s*>",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+))")
_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)


def prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(fields: Mapping[str, Any], db: Session) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "bridge_mode", BRIDGE_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    fact_receipt_id = _required(request, "fact_authority_receipt_id")
    fact_receipt_hash = _required_hash(request, "fact_authority_receipt_hash")
    parser_receipt_id = _required(request, "parser_receipt_id")
    parser_receipt_hash = _required_hash(request, "parser_receipt_hash")
    if request.get("rollback_confirmed") is not True or request.get("operator_confirmed") is not True:
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=fact_receipt_hash,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                *([] if request.get("rollback_confirmed") is True else [_reason("missing_rollback_confirmation")]),
                *([] if request.get("operator_confirmed") is True else [_reason("missing_operator_confirmation")]),
            ],
        )

    regex_fact_receipt = layer3_sec_edgar_html_inline_xbrl_fact_authority.read_sec_edgar_html_inline_xbrl_fact_authority_receipt(
        fact_receipt_id,
        expected_fact_authority_receipt_hash=fact_receipt_hash,
    )
    fact_receipt: Mapping[str, Any] = regex_fact_receipt
    sidecar_receipt: Mapping[str, Any] | None = None
    sidecar_value_store: Mapping[str, Any] | None = None
    fact_authority_input_mode = REGEX_FACT_AUTHORITY_INPUT_MODE
    if _arelle_fact_authority_cutover_enabled():
        sidecar_check = _read_arelle_sidecar_authority(request, request_id=request_id, regex_fact_authority_receipt_hash=fact_receipt_hash, parser_receipt_hash=parser_receipt_hash)
        if isinstance(sidecar_check, dict) and sidecar_check.get("bridge_state") == BLOCKED_STATE:
            return sidecar_check
        sidecar_receipt = sidecar_check
        sidecar_value_store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(sidecar_receipt)
        _validate_regex_sidecar_binding(regex_fact_receipt, sidecar_receipt)
        fact_receipt = _sidecar_fact_authority_view(sidecar_receipt)
        fact_authority_input_mode = ARELLE_FACT_AUTHORITY_INPUT_MODE
    _validate_fact_authority_request(request, fact_receipt)
    parser_receipt = layer3_sec_edgar_html_inline_xbrl_parser.read_sec_edgar_html_inline_xbrl_source_family_parser_receipt(
        parser_receipt_id,
        expected_parser_receipt_hash=parser_receipt_hash,
    )
    _validate_parser_fact_binding(parser_receipt, fact_receipt)
    if sidecar_receipt is not None:
        _validate_parser_fact_binding(parser_receipt, regex_fact_receipt)
    expected = _expected_hashes(request, fact_receipt)
    connector_receipt = layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
        str(parser_receipt["connector_receipt_id"]),
        expected_connector_receipt_hash=expected["connector_receipt_hash"],
    )
    live_receipt, content = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_bytes(
        str(parser_receipt["live_source_artifact_receipt_id"]),
        expected_live_source_artifact_receipt_hash=expected["live_source_artifact_receipt_hash"],
    )
    _validate_live_source_binding(parser_receipt, fact_receipt, live_receipt, content, expected)
    reparsed = layer3_sec_edgar_html_inline_xbrl_parser.reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge(
        connector_receipt,
        connector_example_id=str(parser_receipt["connector_example_id"]),
        retained_complete_submission_text=content,
    )
    parsed = reparsed.get("parsed") if isinstance(reparsed.get("parsed"), Mapping) else {}
    _validate_reparse_binding(parser_receipt, fact_receipt, parsed, expected)
    if sidecar_receipt is None:
        units = _fact_material_units(str(reparsed["primary_document_text"]), parser_receipt=parser_receipt, fact_receipt=fact_receipt, parsed=parsed)
    else:
        units = _fact_material_units_from_sidecar(sidecar_receipt, parser_receipt=parser_receipt, value_store=sidecar_value_store)
    materialization = _materialization_basis(
        parser_receipt,
        fact_receipt,
        units,
        fact_authority_input_mode=fact_authority_input_mode,
        sidecar_receipt=sidecar_receipt,
        regex_fact_receipt=regex_fact_receipt,
    )
    materialization_hash = stable_hash(materialization)
    expected_materialization = str(request.get("expected_materialization_receipt_hash") or "").strip()
    if expected_materialization and expected_materialization != materialization_hash:
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=fact_receipt_hash,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("materialization_receipt_hash_mismatch", expected_materialization_receipt_hash=expected_materialization, received_materialization_receipt_hash=materialization_hash)],
        )

    ids = _dataset_ids(materialization_hash)
    selected_fact_authority_receipt_hash = str(fact_receipt["fact_authority_receipt_hash"])
    dataset_version_hash = stable_hash(
        {
            "dataset_version_id": ids["dataset_version_id"],
            "fact_authority_receipt_hash": selected_fact_authority_receipt_hash,
            "materialization_receipt_hash": materialization_hash,
            "admitted_subset_hash": materialization["admitted_subset_hash"],
            "fact_count": len(units),
        }
    )
    _materialize_dataset_version(
        db,
        ids=ids,
        units=units,
        parser_receipt=parser_receipt,
        materialization_hash=materialization_hash,
        dataset_version_hash=dataset_version_hash,
        fact_authority_input_mode=fact_authority_input_mode,
    )
    db.flush()
    actor = str(request.get("actor") or "operator").strip() or "operator"
    preview_request = _material_preview_request_basis(request_id=request_id, dataset_version_id=ids["dataset_version_id"], actor=actor)
    raw_preview = layer3_workbench.material_preview(preview_request, db)
    raw_candidates = raw_preview.get("material_candidates") if isinstance(raw_preview.get("material_candidates"), list) else []
    if len(raw_candidates) != 1:
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=fact_receipt_hash,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("material_preview_candidate_count_mismatch", candidate_count=len(raw_candidates))],
        )
    material_candidate = _redacted_material_candidate(raw_candidates[0], fact_receipt=fact_receipt, materialization_hash=materialization_hash)
    candidate_basis = material_candidate_basis_from_preview(material_candidate)
    bridged_preview_hash = material_preview_hash([candidate_basis])
    expected_preview_hash = str(request.get("expected_material_preview_hash") or "").strip()
    if expected_preview_hash and expected_preview_hash != bridged_preview_hash:
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=fact_receipt_hash,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("material_preview_hash_mismatch", expected_material_preview_hash=expected_preview_hash, received_material_preview_hash=bridged_preview_hash)],
        )
    gate_b_payload, gate_b_manifest_id = _gate_b_payload(
        request_id=request_id,
        raw_preview=raw_preview,
        material_candidate=material_candidate,
        candidate_basis=candidate_basis,
        material_preview_hash_value=bridged_preview_hash,
        actor=actor,
    )
    expected_gate_b = str(request.get("expected_gate_b_decision_manifest_id") or "").strip()
    if expected_gate_b and expected_gate_b != gate_b_manifest_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_gate_b_decision_basis_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge Gate B decision basis is stale or mismatched.",
            http_status=409,
            blocked_fields=["expected_gate_b_decision_manifest_id"],
        )
    bridge_hash = stable_hash(
        _bridge_hash_basis(
            fact_authority_input_mode=fact_authority_input_mode,
            fact_authority_receipt_hash=str(fact_receipt["fact_authority_receipt_hash"]),
            regex_fact_authority_receipt_hash=fact_receipt_hash,
            sidecar_receipt=sidecar_receipt,
            parser_receipt_hash=parser_receipt_hash,
            dataset_version_hash=dataset_version_hash,
            materialization_hash=materialization_hash,
            bridged_preview_hash=bridged_preview_hash,
            gate_b_manifest_id=gate_b_manifest_id,
        )
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("fact_material_bridge_basis_hash") != bridge_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL fact material bridge basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    bridge_receipt_id = f"{RECEIPT_PREFIX}-{bridge_hash[:24]}"
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=SCHEMA_ID),
        "mode": BRIDGE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "bridge_state": READY_STATE,
        "fact_material_bridge_receipt_id": bridge_receipt_id,
        "fact_material_bridge_receipt_ref": f"{RECEIPT_PREFIX}:{bridge_hash[:24]}",
        "fact_material_bridge_receipt_hash": bridge_hash,
        "bridge_receipt_id": bridge_receipt_id,
        "bridge_receipt_hash": bridge_hash,
        "idempotent_replay": _receipt_path(bridge_receipt_id).exists(),
        "dataset_id": ids["dataset_id"],
        "dataset_version_id": ids["dataset_version_id"],
        "dataset_version_hash": dataset_version_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "fact_authority_receipt_id": fact_receipt_id,
        "fact_authority_receipt_hash": str(fact_receipt["fact_authority_receipt_hash"]),
        "parser_receipt_id": parser_receipt_id,
        "parser_receipt_hash": parser_receipt_hash,
        "materialization_receipt_hash": materialization_hash,
        "material_preview_request_basis": preview_request,
        "material_preview_id": raw_preview["material_preview_id"],
        "material_preview_hash": bridged_preview_hash,
        "material_candidate": material_candidate,
        "gate_b_decision_manifest_id": gate_b_manifest_id,
        "gate_b_decision_payload": gate_b_payload,
        "authority_hashes": {
            **expected,
            "fact_authority_receipt_hash": str(fact_receipt["fact_authority_receipt_hash"]),
            "dataset_version_hash": dataset_version_hash,
            "materialization_receipt_hash": materialization_hash,
            "material_preview_hash": bridged_preview_hash,
            "gate_b_decision_manifest_id": gate_b_manifest_id,
            "fact_material_bridge_receipt_hash": bridge_hash,
        },
        "materialization_summary": {
            "fact_count": len(units),
            "bounded_fact_units": MAX_FACT_UNITS,
            "admitted_subset_hash": materialization["admitted_subset_hash"],
            "source_order_preserved": True,
            "marker_order_preserved": True,
            "server_owned_value_payload_stored": True,
            "raw_fact_values_returned": False,
            "raw_content_returned": False,
        },
        "compatibility": {
            "material_preview_schema_id": MATERIAL_PREVIEW_SCHEMA_ID,
            "gate_b_decision_schema_id": GATE_B_DECISION_SCHEMA_ID,
            "source_class": SOURCE_CLASS,
            "existing_layer3_dataset_version_material_preview_without_source_class_widening": True,
        },
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "blocked_reasons": [],
            "next_allowed_actions": [
                "submit_sec_edgar_html_inline_xbrl_fact_material_bridge_gate_b_decision_payload",
                "select_sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_proof",
            ],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
    }
    if sidecar_receipt is not None:
        response["fact_authority_receipt_id"] = str(fact_receipt["fact_authority_receipt_id"])
        response["fact_authority_input_mode"] = fact_authority_input_mode
        response["regex_fact_authority_receipt_id"] = fact_receipt_id
        response["regex_fact_authority_receipt_hash"] = fact_receipt_hash
        response["arelle_sidecar_receipt_id"] = str(sidecar_receipt["sidecar_receipt_id"])
        response["arelle_sidecar_receipt_hash"] = str(sidecar_receipt["sidecar_receipt_hash"])
        response["authority_hashes"].update(
            {
                "regex_fact_authority_receipt_hash": fact_receipt_hash,
                "arelle_sidecar_receipt_hash": str(sidecar_receipt["sidecar_receipt_hash"]),
                "resolved_fact_inventory_hash": str(sidecar_receipt["resolved_fact_inventory_hash"]),
                "local_value_inventory_hash": str(sidecar_receipt["local_value_inventory_hash"]),
            }
        )
        response["materialization_summary"].update(
            {
                "fact_authority_input_mode": fact_authority_input_mode,
                "sidecar_resolved_fact_count": int(sidecar_receipt["resolved_fact_count"]),
                "regex_fact_authority_count": int(regex_fact_receipt.get("fact_count") or 0),
                "resolved_period_unit_dimension_fields_materialized": True,
                "raw_fact_values_materialized": True,
                "internal_effective_values_materialized": True,
                "operator_surface_values_exposed": False,
            }
        )
        response["compatibility"]["existing_layer3_dataset_version_material_preview_without_source_class_widening"] = True
    if _contains_forbidden_output_ref(response):
        return _blocked_response(request_id=request_id, fact_authority_receipt_hash=str(fact_receipt["fact_authority_receipt_hash"]), parser_receipt_hash=parser_receipt_hash, reasons=[_reason("raw_path_or_url_authority")])
    db.commit()
    idempotent_replay = _write_receipt(response)
    _write_request_binding(request_id, bridge_hash, bridge_receipt_id)
    response["idempotent_replay"] = idempotent_replay
    return response


def inspect_sec_edgar_html_inline_xbrl_fact_material_bridge_status(fact_material_bridge_receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(fact_material_bridge_receipt_id)
    response = dict(receipt["response"])
    response.update(
        {
            "schema_id": STATUS_SCHEMA_ID,
            "request_id": f"sec-edgar-html-inline-xbrl-fact-material-bridge-status-{receipt['fact_material_bridge_receipt_hash'][:12]}",
            "server_time": _server_time(),
            "idempotent_replay": False,
        }
    )
    if _contains_forbidden_output_ref(response):
        _blocked("sec_edgar_html_inline_xbrl_fact_material_bridge_status_raw_authority_exposed", "SEC EDGAR HTML/iXBRL fact material bridge status would expose raw authority.", http_status=409)
    return response


def _materialize_dataset_version(
    db: Session,
    *,
    ids: Mapping[str, str],
    units: list[dict[str, Any]],
    parser_receipt: Mapping[str, Any],
    materialization_hash: str,
    dataset_version_hash: str,
    fact_authority_input_mode: str,
) -> None:
    csv_path = _datasets_dir() / f"{ids['dataset_version_id']}.csv"
    fieldnames = _fact_fieldnames(fact_authority_input_mode)
    if not csv_path.exists():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(units)
    if db.get(Dataset, ids["dataset_id"]) is None:
        db.add(Dataset(dataset_id=ids["dataset_id"], name="SEC EDGAR HTML iXBRL fact material units", description="Receipt-bound SEC EDGAR HTML/iXBRL fact units.", frequency_hint=None, time_column=None))
    if db.get(DatasetVersion, ids["dataset_version_id"]) is None:
        db.add(
            DatasetVersion(
                dataset_version_id=ids["dataset_version_id"],
                dataset_id=ids["dataset_id"],
                version_label="sec-html-ixbrl-fact-material-v1",
                version_type="sec_edgar_html_inline_xbrl_fact_material_units",
                status="ready",
                storage_ref=str(csv_path),
                row_count=len(units),
                notes=f"materialization_receipt_hash={materialization_hash}",
            )
        )
        for index, (name, dtype, role, numeric) in enumerate(_variable_definitions(fact_authority_input_mode)):
            db.add(
                VariableDefinition(
                    variable_id=f"var-{ids['dataset_version_id'][-12:]}-{index}",
                    dataset_version_id=ids["dataset_version_id"],
                    variable_name=name,
                    dtype=dtype,
                    role=role,
                    is_numeric=numeric,
                    is_time_index=False,
                    ordinal_position=index,
                )
            )
        db.add(
            DatasetSourceProvenance(
                dataset_version_id=ids["dataset_version_id"],
                connector_run_id=None,
                source_system="nrc_adams_aps",
                source_mode="sec_edgar_html_inline_xbrl_fact_material_bridge",
                source_artifact_key=f"sec-edgar-html-inline-xbrl-fact-material:{materialization_hash[:24]}",
                downloaded_sha256=str(parser_receipt["content_sha256"]),
                raw_storage_ref=None,
                artifact_locator_type="server_owned_ref",
                fetch_policy_mode="server_owned_receipt",
                source_reference_json={
                    "target_id": str(parser_receipt["connector_example_id"]),
                    "parser_family": PARSER_FAMILY,
                    "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
                    "materialization_receipt_hash": materialization_hash,
                    "dataset_version_hash": dataset_version_hash,
                },
            )
        )


def _fact_fieldnames(fact_authority_input_mode: str) -> list[str]:
    if fact_authority_input_mode == ARELLE_FACT_AUTHORITY_INPUT_MODE:
        return list(ARELLE_FACT_FIELDNAMES)
    return list(REGEX_FACT_FIELDNAMES)


def _variable_definitions(fact_authority_input_mode: str) -> tuple[tuple[str, str, str, bool], ...]:
    base = (
        ("fact_order", "int64", "ordinal", True),
        ("element_name", "string", "dimension", False),
        ("qualified_name", "string", "dimension", False),
        ("namespace_prefix", "string", "dimension", False),
        ("local_name", "string", "dimension", False),
        ("context_ref_hash", "string", "authority_hash", False),
        ("unit_ref_hash", "string", "authority_hash", False),
        ("decimals_or_precision", "string", "metadata", False),
        ("scale_or_format", "string", "metadata", False),
        ("source_order_hash", "string", "authority_hash", False),
        ("value_text", "string", "material_payload", False),
        ("value_hash", "string", "authority_hash", False),
        ("value_length", "int64", "measure", True),
        ("table_candidate_anchor_hash", "string", "authority_hash", False),
        ("parser_receipt_hash", "string", "authority_hash", False),
        ("fact_authority_receipt_hash", "string", "authority_hash", False),
    )
    if fact_authority_input_mode != ARELLE_FACT_AUTHORITY_INPUT_MODE:
        return base
    return (
        *base,
        ("resolved_fact_id", "string", "authority_hash", False),
        ("entry_document_index", "int64", "ordinal", True),
        ("concept_qname", "string", "dimension", False),
        ("concept_namespace", "string", "metadata", False),
        ("concept_local_name", "string", "dimension", False),
        ("concept_standard", "bool", "metadata", False),
        ("concept_extension", "bool", "metadata", False),
        ("concept_resolved_from_dts", "bool", "metadata", False),
        ("context_id", "string", "metadata", False),
        ("unit_id", "string", "metadata", False),
        ("period_type", "string", "metadata", False),
        ("period_start", "string", "time", False),
        ("period_end", "string", "time", False),
        ("period_instant", "string", "time", False),
        ("period_forever", "bool", "metadata", False),
        ("period_resolved", "bool", "metadata", False),
        ("unit_measures_json", "json", "metadata", False),
        ("unit_currency", "string", "dimension", False),
        ("unit_numerator_json", "json", "metadata", False),
        ("unit_denominator_json", "json", "metadata", False),
        ("unit_resolved", "bool", "metadata", False),
        ("explicit_dimensions_json", "json", "metadata", False),
        ("typed_dimensions_json", "json", "metadata", False),
        ("explicit_dimension_count", "int64", "measure", True),
        ("typed_dimension_count", "int64", "measure", True),
        ("hidden", "bool", "metadata", False),
        ("continued", "bool", "metadata", False),
        ("footnote_count", "int64", "measure", True),
        ("value_redacted", "bool", "metadata", False),
        ("value_semantics", "string", "metadata", False),
        ("effective_value_text", "string", "material_payload", False),
        ("effective_value_hash", "string", "authority_hash", False),
        ("effective_value_length", "int64", "measure", True),
        ("lexical_value_text", "string", "material_payload", False),
        ("lexical_value_hash", "string", "authority_hash", False),
        ("lexical_value_length", "int64", "measure", True),
        ("transform_sign", "string", "metadata", False),
        ("transform_scale", "string", "metadata", False),
        ("transform_decimals", "string", "metadata", False),
        ("transform_precision", "string", "metadata", False),
        ("transform_format", "string", "metadata", False),
    )


def _fact_material_units(
    primary_text: str,
    *,
    parser_receipt: Mapping[str, Any],
    fact_receipt: Mapping[str, Any],
    parsed: Mapping[str, Any],
) -> list[dict[str, Any]]:
    table_ranges = _table_ranges(parsed)
    expected_facts = list(fact_receipt.get("fact_inventory") or [])
    units: list[dict[str, Any]] = []
    for index, match in enumerate(_IX_FACT_RE.finditer(primary_text), start=1):
        if index > MAX_FACT_UNITS:
            break
        attrs = _attrs(match.group("attrs"))
        qname = str(attrs.get("name") or "").strip()
        prefix, local = _split_qname(qname)
        value = _normalise_text(match.group("body"))
        source_order_hash = stable_hash(
            {
                "primary_document_hash": parser_receipt["primary_document_hash"],
                "marker_order_index": index,
                "source_start": match.start(),
                "source_end": match.end(),
            }
        )
        unit = {
            "fact_order": index,
            "element_name": match.group("tag").lower(),
            "qualified_name": qname,
            "namespace_prefix": prefix,
            "local_name": local,
            "context_ref_hash": _optional_hash(attrs.get("contextRef")),
            "unit_ref_hash": _optional_hash(attrs.get("unitRef")),
            "decimals_or_precision": str(attrs.get("decimals") or attrs.get("precision") or ""),
            "scale_or_format": str(attrs.get("scale") or attrs.get("format") or ""),
            "continued_fact_hash_if_present": _optional_hash(attrs.get("continuedAt")),
            "source_order_hash": source_order_hash,
            "source_artifact_receipt_hash": str(parser_receipt["source_artifact_receipt_hash"]),
            "primary_document_hash": str(parser_receipt["primary_document_hash"]),
            "value_text": value,
            "value_hash": _sha256_text(value),
            "value_length": len(value),
            "table_candidate_anchor_hash": _table_anchor(match.start(), table_ranges),
            "parser_receipt_hash": str(parser_receipt["parser_receipt_hash"]),
            "fact_authority_receipt_hash": str(fact_receipt["fact_authority_receipt_hash"]),
        }
        _validate_unit_against_fact_authority(unit, expected_facts, order=index)
        units.append(unit)
    if len(units) != int(fact_receipt.get("fact_count") or -1):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_fact_count_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires reconstructed fact units to match fact authority count.",
            http_status=409,
            blocked_fields=["fact_inventory_hash"],
        )
    if not units:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_no_fact_units",
            "SEC EDGAR HTML/iXBRL fact material bridge found no fact units to materialize.",
            http_status=409,
            blocked_fields=["fact_inventory_hash"],
        )
    return units


def _fact_material_units_from_sidecar(
    sidecar_receipt: Mapping[str, Any],
    *,
    parser_receipt: Mapping[str, Any],
    value_store: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    records = list(sidecar_receipt.get("resolved_fact_records") or [])
    if len(records) != int(sidecar_receipt.get("resolved_fact_count") or -1):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_sidecar_fact_count_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires sidecar resolved records to match sidecar count.",
            http_status=409,
            blocked_fields=["arelle_sidecar_receipt_hash"],
        )
    projection = [_redacted_sidecar_fact(record) for record in records if isinstance(record, Mapping)]
    if stable_hash(projection) != str(sidecar_receipt.get("resolved_fact_inventory_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_sidecar_inventory_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires sidecar resolved fact inventory hash parity.",
            http_status=409,
            blocked_fields=["arelle_sidecar_receipt_hash"],
        )
    value_records = list((value_store or {}).get("value_records") or [])
    values_by_id = {str(item.get("resolved_fact_id") or ""): item for item in value_records if isinstance(item, Mapping)}
    if len(values_by_id) != len(records):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_sidecar_value_store_count_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires one internal value-store record for each resolved sidecar fact.",
            http_status=409,
            blocked_fields=["internal_value_store"],
        )
    units: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_bridge_sidecar_fact_record_invalid",
                "SEC EDGAR HTML/iXBRL fact material bridge requires structured sidecar fact records.",
                http_status=409,
                blocked_fields=["resolved_fact_records"],
            )
        concept = dict(record.get("concept") or {})
        period = dict(record.get("period") or {})
        unit = dict(record.get("unit") or {})
        dimensions = dict(record.get("dimensions") or {})
        qname = str(concept.get("qname") or "")
        prefix, local = _split_qname(qname)
        resolved_fact_id = str(record.get("resolved_fact_id") or "")
        source_order = int(record.get("source_order") or index)
        entry_document_index = int(record.get("entry_document_index") or 1)
        value_record = values_by_id.get(resolved_fact_id)
        if value_record is None:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_bridge_sidecar_value_record_missing",
                "SEC EDGAR HTML/iXBRL fact material bridge requires persisted internal values for each resolved sidecar fact.",
                http_status=409,
                blocked_fields=["resolved_fact_id"],
            )
        effective_value = str(value_record.get("effective_value") or "")
        lexical_value = str(value_record.get("lexical_value") or "")
        transform = dict(value_record.get("transform") or {})
        source_order_hash = stable_hash(
            {
                "sidecar_receipt_hash": sidecar_receipt["sidecar_receipt_hash"],
                "resolved_fact_id": resolved_fact_id,
                "source_order": source_order,
                "entry_document_index": entry_document_index,
            }
        )
        explicit_dimensions = list(dimensions.get("explicit") or [])
        typed_dimensions = list(dimensions.get("typed") or [])
        units.append(
            {
                "fact_order": index,
                "element_name": "arelle:resolved-fact",
                "qualified_name": qname,
                "namespace_prefix": prefix,
                "local_name": str(concept.get("local_name") or local),
                "context_ref_hash": _optional_hash(record.get("context_id")),
                "unit_ref_hash": _optional_hash(record.get("unit_id")),
                "decimals_or_precision": str(record.get("decimals") or record.get("precision") or ""),
                "scale_or_format": str(record.get("scale") or record.get("format") or ""),
                "continued_fact_hash_if_present": _optional_hash(record.get("continued_at")),
                "source_order_hash": source_order_hash,
                "source_artifact_receipt_hash": str(record.get("source_artifact_receipt_hash") or parser_receipt["source_artifact_receipt_hash"]),
                "primary_document_hash": str(record.get("primary_document_hash") or parser_receipt["primary_document_hash"]),
                "value_text": "",
                "value_hash": str(record.get("value_hash") or value_record.get("effective_value_hash") or _sha256_text(effective_value)),
                "value_length": int(record.get("value_length") or value_record.get("effective_value_length") or len(effective_value)),
                "table_candidate_anchor_hash": None,
                "parser_receipt_hash": str(parser_receipt["parser_receipt_hash"]),
                "fact_authority_receipt_hash": str(sidecar_receipt["sidecar_receipt_hash"]),
                "resolved_fact_id": resolved_fact_id,
                "entry_document_index": entry_document_index,
                "concept_qname": qname,
                "concept_namespace": str(concept.get("namespace") or ""),
                "concept_local_name": str(concept.get("local_name") or local),
                "concept_standard": bool(concept.get("standard")),
                "concept_extension": bool(concept.get("extension")),
                "concept_resolved_from_dts": bool(concept.get("resolved_from_dts")),
                "context_id": str(record.get("context_id") or ""),
                "unit_id": str(record.get("unit_id") or ""),
                "period_type": str(period.get("type") or ""),
                "period_start": str(period.get("start") or ""),
                "period_end": str(period.get("end") or ""),
                "period_instant": str(period.get("instant") or ""),
                "period_forever": bool(period.get("forever")),
                "period_resolved": bool(period.get("resolved")),
                "unit_measures_json": _json_compact(unit.get("measures") or []),
                "unit_currency": str(unit.get("currency") or ""),
                "unit_numerator_json": _json_compact(unit.get("numerator") or []),
                "unit_denominator_json": _json_compact(unit.get("denominator") or []),
                "unit_resolved": bool(unit.get("resolved")),
                "explicit_dimensions_json": _json_compact(explicit_dimensions),
                "typed_dimensions_json": _json_compact(typed_dimensions),
                "explicit_dimension_count": len(explicit_dimensions),
                "typed_dimension_count": len(typed_dimensions),
                "hidden": bool(record.get("hidden")),
                "continued": bool(record.get("continued")),
                "footnote_count": int(record.get("footnote_count") or 0),
                "value_redacted": False,
                "value_semantics": str(value_record.get("value_semantics") or record.get("value_semantics") or "arelle_effective_canonical_value_v1"),
                "effective_value_text": effective_value,
                "effective_value_hash": str(value_record.get("effective_value_hash") or _sha256_text(effective_value)),
                "effective_value_length": int(value_record.get("effective_value_length") or len(effective_value)),
                "lexical_value_text": lexical_value,
                "lexical_value_hash": str(value_record.get("lexical_value_hash") or _sha256_text(lexical_value)),
                "lexical_value_length": int(value_record.get("lexical_value_length") or len(lexical_value)),
                "transform_sign": str(transform.get("sign") or record.get("sign") or ""),
                "transform_scale": str(transform.get("scale") or record.get("scale") or ""),
                "transform_decimals": str(transform.get("decimals") or record.get("decimals") or ""),
                "transform_precision": str(transform.get("precision") or record.get("precision") or ""),
                "transform_format": str(transform.get("format") or record.get("format") or ""),
            }
        )
    if not units:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_no_fact_units",
            "SEC EDGAR HTML/iXBRL fact material bridge found no fact units to materialize.",
            http_status=409,
            blocked_fields=["resolved_fact_inventory_hash"],
        )
    return units


def _redacted_sidecar_fact(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dict(record).items() if key != "value"} | {"value_redacted": True}


def _validate_unit_against_fact_authority(unit: Mapping[str, Any], expected_facts: list[Any], *, order: int) -> None:
    try:
        expected = expected_facts[order - 1]
    except IndexError:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_fact_inventory_order_missing",
            "SEC EDGAR HTML/iXBRL fact material bridge requires fact authority order parity.",
            http_status=409,
            blocked_fields=["fact_inventory"],
        )
    if not isinstance(expected, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_fact_inventory_invalid",
            "SEC EDGAR HTML/iXBRL fact material bridge requires structured fact authority inventory.",
            http_status=409,
            blocked_fields=["fact_inventory"],
        )
    checks = {
        "marker_order_index": order,
        "element_name": unit["element_name"],
        "qualified_name": unit["qualified_name"],
        "namespace_prefix": unit["namespace_prefix"],
        "local_name": unit["local_name"],
        "context_ref_hash": unit["context_ref_hash"],
        "unit_ref_hash": unit["unit_ref_hash"],
        "decimals_or_precision": unit["decimals_or_precision"],
        "scale_or_format": unit["scale_or_format"],
        "continued_fact_hash_if_present": unit["continued_fact_hash_if_present"],
        "source_order_hash": unit["source_order_hash"],
        "source_artifact_receipt_hash": unit["source_artifact_receipt_hash"],
        "primary_document_hash": unit["primary_document_hash"],
        "value_hash": unit["value_hash"],
        "value_length": unit["value_length"],
        "table_candidate_anchor_hash": unit["table_candidate_anchor_hash"],
    }
    mismatches = [key for key, value in checks.items() if expected.get(key) != value]
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_fact_inventory_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires reconstructed fact units to match fact authority.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _materialization_basis(
    parser_receipt: Mapping[str, Any],
    fact_receipt: Mapping[str, Any],
    units: list[dict[str, Any]],
    *,
    fact_authority_input_mode: str,
    sidecar_receipt: Mapping[str, Any] | None,
    regex_fact_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    admitted_subset = _materialization_admitted_subset(units, fact_authority_input_mode=fact_authority_input_mode)
    basis = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_materialization_receipt.v1",
        "schema_version": SCHEMA_VERSION,
        "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
        "fact_authority_receipt_hash": fact_receipt["fact_authority_receipt_hash"],
        "document_inventory_hash": parser_receipt["document_inventory_hash"],
        "content_order_hash": parser_receipt["content_order_hash"],
        "table_candidate_inventory_hash": parser_receipt["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": parser_receipt["inline_xbrl_marker_inventory_hash"],
        "fact_inventory_hash": fact_receipt["fact_inventory_hash"],
        "diagnostics_hash": fact_receipt["diagnostics_hash"],
        "admitted_subset_hash": stable_hash(admitted_subset),
        "fact_count": len(units),
    }
    if fact_authority_input_mode == ARELLE_FACT_AUTHORITY_INPUT_MODE and sidecar_receipt is not None:
        basis.update(
            {
                "fact_authority_input_mode": fact_authority_input_mode,
                "arelle_sidecar_receipt_hash": sidecar_receipt["sidecar_receipt_hash"],
                "regex_fact_authority_receipt_hash": regex_fact_receipt["fact_authority_receipt_hash"],
                "resolved_fact_inventory_hash": sidecar_receipt["resolved_fact_inventory_hash"],
                "local_value_inventory_hash": sidecar_receipt["local_value_inventory_hash"],
                "internal_value_store_hash": (sidecar_receipt.get("internal_value_store") or {}).get("value_store_hash"),
                "resolved_structural_semantics_materialized": True,
                "raw_fact_values_materialized": True,
                "operator_surface_values_exposed": False,
            }
        )
    return basis


def _materialization_admitted_subset(units: list[dict[str, Any]], *, fact_authority_input_mode: str) -> list[dict[str, Any]]:
    if fact_authority_input_mode != ARELLE_FACT_AUTHORITY_INPUT_MODE:
        return [
            {
                "fact_order": unit["fact_order"],
                "qualified_name": unit["qualified_name"],
                "context_ref_hash": unit["context_ref_hash"],
                "unit_ref_hash": unit["unit_ref_hash"],
                "source_order_hash": unit["source_order_hash"],
                "value_hash": unit["value_hash"],
                "value_length": unit["value_length"],
                "table_candidate_anchor_hash": unit["table_candidate_anchor_hash"],
            }
            for unit in units
        ]
    return [
        {
            "fact_order": unit["fact_order"],
            "resolved_fact_id": unit["resolved_fact_id"],
            "entry_document_index": unit["entry_document_index"],
            "qualified_name": unit["qualified_name"],
            "concept_namespace": unit["concept_namespace"],
            "context_id": unit["context_id"],
            "unit_id": unit["unit_id"],
            "period_type": unit["period_type"],
            "period_start": unit["period_start"],
            "period_end": unit["period_end"],
            "period_instant": unit["period_instant"],
            "unit_currency": unit["unit_currency"],
            "explicit_dimensions_json": unit["explicit_dimensions_json"],
            "typed_dimensions_json": unit["typed_dimensions_json"],
            "source_order_hash": unit["source_order_hash"],
            "value_hash": unit["value_hash"],
            "value_length": unit["value_length"],
            "effective_value_hash": unit["effective_value_hash"],
            "effective_value_length": unit["effective_value_length"],
            "lexical_value_hash": unit["lexical_value_hash"],
            "lexical_value_length": unit["lexical_value_length"],
            "value_semantics": unit["value_semantics"],
            "transform_sign": unit["transform_sign"],
            "transform_scale": unit["transform_scale"],
            "transform_decimals": unit["transform_decimals"],
            "transform_format": unit["transform_format"],
        }
        for unit in units
    ]


def _material_preview_request_basis(*, request_id: str, dataset_version_id: str, actor: str) -> dict[str, Any]:
    return {
        "schema_id": MATERIAL_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "client_request_id": f"{request_id}:material-preview",
        "source_candidate_ids": [f"{SOURCE_CANDIDATE_PREFIX}sec-ixbrl-facts-{_sha256_text(dataset_version_id)[:16]}"],
        "dataset_version_ids": [dataset_version_id],
        "query_basis": {
            "terms": ["sec_edgar_html_inline_xbrl_fact_material_bridge"],
            "filters": {"dataset_version_ids": [dataset_version_id]},
        },
        "actor": actor,
    }


def _bridge_hash_basis(
    *,
    fact_authority_input_mode: str,
    fact_authority_receipt_hash: str,
    regex_fact_authority_receipt_hash: str,
    sidecar_receipt: Mapping[str, Any] | None,
    parser_receipt_hash: str,
    dataset_version_hash: str,
    materialization_hash: str,
    bridged_preview_hash: str,
    gate_b_manifest_id: str,
) -> dict[str, Any]:
    basis = {
        "hash_version": AUTHORITY_HASH_VERSION,
        "bridge_mode": BRIDGE_MODE,
        "fact_authority_receipt_hash": fact_authority_receipt_hash,
        "parser_receipt_hash": parser_receipt_hash,
        "dataset_version_hash": dataset_version_hash,
        "materialization_receipt_hash": materialization_hash,
        "material_preview_hash": bridged_preview_hash,
        "gate_b_decision_manifest_id": gate_b_manifest_id,
    }
    if fact_authority_input_mode == ARELLE_FACT_AUTHORITY_INPUT_MODE and sidecar_receipt is not None:
        basis.update(
            {
                "fact_authority_input_mode": fact_authority_input_mode,
                "arelle_sidecar_receipt_hash": sidecar_receipt["sidecar_receipt_hash"],
                "regex_fact_authority_receipt_hash": regex_fact_authority_receipt_hash,
                "resolved_fact_inventory_hash": sidecar_receipt["resolved_fact_inventory_hash"],
                "internal_value_store_hash": (sidecar_receipt.get("internal_value_store") or {}).get("value_store_hash"),
            }
        )
    return basis


def _gate_b_payload(
    *,
    request_id: str,
    raw_preview: Mapping[str, Any],
    material_candidate: Mapping[str, Any],
    candidate_basis: Mapping[str, Any],
    material_preview_hash_value: str,
    actor: str,
) -> tuple[dict[str, Any], str]:
    decision_basis = _gate_b_decision_basis(material_candidate)
    decision_material_basis = material_candidate_basis_from_decision(
        candidate_id=str(material_candidate["candidate_id"]),
        source_class=SOURCE_CLASS,
        decision_basis=decision_basis,
    )
    if decision_material_basis != candidate_basis:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_gate_b_decision_basis_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge Gate B decision basis no longer matches material preview.",
            http_status=409,
        )
    item = {
        "candidate_id": material_candidate["candidate_id"],
        "source_class": SOURCE_CLASS,
        "decision": "approved",
        "operator_reason": "",
        "decision_basis": decision_basis,
        "material_preview_basis": decision_material_basis,
        "source_identity": decision_basis["source_identity"],
        "source_provenance": decision_basis["source_provenance"],
        "payload": decision_basis["payload"],
        "load_summary": decision_basis["load_summary"],
    }
    manifest_id = compute_gate_b_decision_manifest_id(candidate_decision_manifest([item]))
    return (
        {
            "schema_id": GATE_B_DECISION_SCHEMA_ID,
            "schema_version": 1,
            "client_request_id": f"{request_id}:gate-b",
            "preflight_id": f"sec-edgar-html-inline-xbrl-fact-{_sha256_text(request_id)[:16]}",
            "source_set_id": f"sec-edgar-html-inline-xbrl-fact-material-{_sha256_text(str(material_candidate['source_ref']))[:16]}",
            "material_preview_id": raw_preview["material_preview_id"],
            "material_preview_hash": material_preview_hash_value,
            "candidate_decisions": [{"candidate_id": material_candidate["candidate_id"], "decision": "approved", "operator_reason": "", "decision_basis": decision_basis}],
            "commit_reason": "sec_edgar_html_inline_xbrl_fact_material_bridge",
            "actor": actor,
        },
        manifest_id,
    )


def _redacted_material_candidate(
    candidate: Mapping[str, Any],
    *,
    fact_receipt: Mapping[str, Any],
    materialization_hash: str,
) -> dict[str, Any]:
    source_identity = _redact_value(candidate.get("source_identity"))
    source_provenance = _redact_value(candidate.get("source_provenance"))
    source_trace = _redact_value(candidate.get("source_trace"))
    source_identity = source_identity if isinstance(source_identity, dict) else {}
    source_provenance = source_provenance if isinstance(source_provenance, dict) else {}
    source_trace = source_trace if isinstance(source_trace, dict) else {}
    source_provenance.update(
        {
            "fact_authority_receipt_hash": fact_receipt["fact_authority_receipt_hash"],
            "materialization_receipt_hash": materialization_hash,
            "redaction": {"raw_storage_ref_exposed": False, "raw_url_exposed": False, "artifact_bytes_exposed": False, "raw_fact_values_exposed": False},
        }
    )
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_label": "SEC EDGAR HTML/iXBRL Fact Dataset Version",
        "source_class": SOURCE_CLASS,
        "source_ref": str(candidate.get("source_ref") or ""),
        "owner_service_source_shape": SOURCE_CLASS,
        "planning_shape_family": "fact_material_units",
        "source_family": SOURCE_FAMILY,
        "source_family_label": "SEC/EDGAR HTML inline XBRL facts",
        "source_admission_state": str(candidate.get("source_admission_state") or "admitted_materialized_dataset_version"),
        "source_family_scope": str(candidate.get("source_family_scope") or ""),
        "source_trace": source_trace,
        "query_basis": BRIDGE_MODE,
        "validation_status": str(candidate.get("validation_status") or "valid"),
        "duplicate_status": str(candidate.get("duplicate_status") or "unique"),
        "size_or_unit_count": int(candidate.get("size_or_unit_count") or 0),
        "preview_payload_ref": None,
        "provenance_ref": f"{RECEIPT_PREFIX}:{str(fact_receipt['fact_authority_receipt_hash'])[:24]}",
        "source_identity": source_identity,
        "source_provenance": source_provenance,
        "payload": {
            "dataset_version_id": (candidate.get("payload") or {}).get("dataset_version_id") if isinstance(candidate.get("payload"), Mapping) else None,
            "source_family": SOURCE_FAMILY,
            "parser_family": PARSER_FAMILY,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "fact_authority_receipt_hash": fact_receipt["fact_authority_receipt_hash"],
            "materialization_receipt_hash": materialization_hash,
        },
        "load_summary": {
            "loaded_records": int((candidate.get("load_summary") or {}).get("loaded_records") or 0) if isinstance(candidate.get("load_summary"), Mapping) else 0,
            "failed_records": 0,
            "preview_material": True,
            "storage_available": bool((candidate.get("load_summary") or {}).get("storage_available")) if isinstance(candidate.get("load_summary"), Mapping) else False,
            "raw_refs_redacted": True,
            "raw_fact_values_redacted": True,
        },
        "current_decision_state": "candidate",
    }


def _gate_b_decision_basis(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": str(candidate.get("source_ref") or ""),
        "query_basis": str(candidate.get("query_basis") or BRIDGE_MODE),
        "provenance_ref": str(candidate.get("provenance_ref") or ""),
        "source_identity": dict(candidate.get("source_identity") or {}),
        "source_provenance": dict(candidate.get("source_provenance") or {}),
        "payload": dict(candidate.get("payload") or {}),
        "load_summary": dict(candidate.get("load_summary") or {}),
    }


def _validate_fact_authority_request(request: Mapping[str, Any], fact_receipt: Mapping[str, Any]) -> None:
    checks = {
        "parser_receipt_id": _required(request, "parser_receipt_id"),
        "parser_receipt_hash": _required_hash(request, "parser_receipt_hash"),
        "expected_connector_receipt_hash": _expected_or_authority(request, "expected_connector_receipt_hash", fact_receipt, "connector_receipt_hash"),
        "expected_live_source_artifact_receipt_hash": _expected_or_authority(request, "expected_live_source_artifact_receipt_hash", fact_receipt, "live_source_artifact_receipt_hash"),
        "expected_source_artifact_receipt_hash": _expected_or_authority(request, "expected_source_artifact_receipt_hash", fact_receipt, "source_artifact_receipt_hash"),
        "expected_content_sha256": _expected_or_authority(request, "expected_content_sha256", fact_receipt, "content_sha256"),
        "expected_primary_document_hash": _expected_or_authority(request, "expected_primary_document_hash", fact_receipt, "primary_document_hash"),
        "expected_document_inventory_hash": _expected_or_authority(request, "expected_document_inventory_hash", fact_receipt, "document_inventory_hash"),
        "expected_content_order_hash": _expected_or_authority(request, "expected_content_order_hash", fact_receipt, "content_order_hash"),
        "expected_table_candidate_inventory_hash": _expected_or_authority(request, "expected_table_candidate_inventory_hash", fact_receipt, "table_candidate_inventory_hash"),
        "expected_inline_xbrl_marker_inventory_hash": _expected_or_authority(request, "expected_inline_xbrl_marker_inventory_hash", fact_receipt, "inline_xbrl_marker_inventory_hash"),
        "expected_fact_inventory_hash": _expected_or_authority(request, "expected_fact_inventory_hash", fact_receipt, "fact_inventory_hash"),
        "expected_diagnostics_hash": _expected_or_authority(request, "expected_diagnostics_hash", fact_receipt, "diagnostics_hash"),
    }
    if checks["parser_receipt_id"] != str(fact_receipt.get("parser_receipt_id") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_parser_receipt_id_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires parser receipt id to match fact authority.",
            http_status=409,
            blocked_fields=["parser_receipt_id"],
        )


def _arelle_fact_authority_cutover_enabled() -> bool:
    return bool(getattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False))


def _read_arelle_sidecar_authority(
    request: Mapping[str, Any],
    *,
    request_id: str,
    regex_fact_authority_receipt_hash: str,
    parser_receipt_hash: str,
) -> Mapping[str, Any]:
    sidecar_receipt_id = str(request.get("arelle_sidecar_receipt_id") or "").strip()
    sidecar_receipt_hash = str(request.get("arelle_sidecar_receipt_hash") or "").strip()
    if not sidecar_receipt_id or not _is_hash(sidecar_receipt_hash):
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=regex_fact_authority_receipt_hash,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                _reason(
                    "arelle_sidecar_receipt_required",
                    persisted_sidecar_required=True,
                    synchronous_arelle_invocation_performed=False,
                    regex_fallback_performed=False,
                )
            ],
        )
    sidecar_receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        sidecar_receipt_id,
        expected_sidecar_receipt_hash=sidecar_receipt_hash,
    )
    if sidecar_receipt.get("sidecar_state") != layer3_sec_xbrl_sidecar.READY_STATE:
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=regex_fact_authority_receipt_hash,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                _reason(
                    "arelle_sidecar_receipt_not_ready",
                    sidecar_state=str(sidecar_receipt.get("sidecar_state") or ""),
                    regex_fallback_performed=False,
                )
            ],
        )
    return sidecar_receipt


def _sidecar_fact_authority_view(sidecar_receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(sidecar_receipt),
        "fact_authority_receipt_id": str(sidecar_receipt["sidecar_receipt_id"]),
        "fact_authority_receipt_hash": str(sidecar_receipt["sidecar_receipt_hash"]),
        "fact_count": int(sidecar_receipt["resolved_fact_count"]),
        "fact_inventory_hash": str(sidecar_receipt["resolved_fact_inventory_hash"]),
        "diagnostics_hash": str(sidecar_receipt["diagnostics_hash"]),
        "fact_inventory": list(sidecar_receipt.get("resolved_fact_projection") or []),
    }


def _validate_regex_sidecar_binding(regex_fact_receipt: Mapping[str, Any], sidecar_receipt: Mapping[str, Any]) -> None:
    keys = (
        "parser_receipt_id",
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
    )
    mismatches = [key for key in keys if str(regex_fact_receipt.get(key) or "") != str(sidecar_receipt.get(key) or "")]
    sidecar_regex_hash = str(sidecar_receipt.get("regex_fact_authority_receipt_hash") or "").strip()
    if sidecar_regex_hash and sidecar_regex_hash != str(regex_fact_receipt.get("fact_authority_receipt_hash") or ""):
        mismatches.append("regex_fact_authority_receipt_hash")
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_arelle_sidecar_lineage_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires sidecar, regex fact authority, and parser lineage to match.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _validate_parser_fact_binding(parser_receipt: Mapping[str, Any], fact_receipt: Mapping[str, Any]) -> None:
    keys = (
        "parser_receipt_id",
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
    )
    mismatches = [key for key in keys if str(parser_receipt.get(key) or "") != str(fact_receipt.get(key) or "")]
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_parser_fact_authority_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires parser and fact authority lineage to match.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _expected_hashes(request: Mapping[str, Any], fact_receipt: Mapping[str, Any]) -> dict[str, str]:
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
        "fact_inventory_hash": "expected_fact_inventory_hash",
        "diagnostics_hash": "expected_diagnostics_hash",
    }
    return {authority_key: _expected_or_authority(request, request_key, fact_receipt, authority_key) for authority_key, request_key in mapping.items()}


def _validate_live_source_binding(
    parser_receipt: Mapping[str, Any],
    fact_receipt: Mapping[str, Any],
    live_receipt: Mapping[str, Any],
    content: bytes,
    expected: Mapping[str, str],
) -> None:
    artifact = _source_artifact(live_receipt)
    checks = {
        "source_artifact_receipt_hash": str(artifact.get("source_artifact_receipt_hash") or ""),
        "content_sha256": hashlib.sha256(content).hexdigest(),
    }
    mismatches = [
        key
        for key, value in checks.items()
        if value != expected[key]
        or str(parser_receipt.get(key) or "") != expected[key]
        or str(fact_receipt.get(key) or "") != expected[key]
    ]
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_source_artifact_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires parser, fact, and live source-artifact authority to match.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _validate_reparse_binding(
    parser_receipt: Mapping[str, Any],
    fact_receipt: Mapping[str, Any],
    parsed: Mapping[str, Any],
    expected: Mapping[str, str],
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
        if value != expected[key]
        or str(parser_receipt.get(key) or "") != expected[key]
        or str(fact_receipt.get(key) or "") != expected[key]
    ]
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_parser_reparse_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge requires retained content to reparse to parser and fact authority.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _source_artifact(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    artifact = receipt.get("source_artifact_receipt")
    if not isinstance(artifact, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_source_artifact_missing",
            "SEC EDGAR HTML/iXBRL fact material bridge requires live source-artifact authority.",
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


def _json_compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _split_qname(qname: str) -> tuple[str, str]:
    if ":" in qname:
        prefix, local = qname.split(":", 1)
        return prefix, local
    return "", qname


def _optional_hash(value: Any) -> str | None:
    text = str(value or "").strip()
    return _sha256_text(text) if text else None


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL fact material bridge rejects caller paths, URLs, HTML, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_unknown_field",
            "SEC EDGAR HTML/iXBRL fact material bridge fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL fact material bridge requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _blocked_response(*, request_id: str, fact_authority_receipt_hash: str, parser_receipt_hash: str, reasons: list[dict[str, Any]]) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": BRIDGE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "bridge_state": BLOCKED_STATE,
        "fact_material_bridge_receipt_id": None,
        "fact_material_bridge_receipt_hash": None,
        "bridge_receipt_id": None,
        "bridge_receipt_hash": None,
        "fact_authority_receipt_hash": fact_authority_receipt_hash,
        "parser_receipt_hash": parser_receipt_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "material_preview_request_basis": None,
        "material_preview_hash": None,
        "gate_b_decision_manifest_id": None,
        "status_projection": {"ready": False, "redacted_projection": True, "blocked_reasons": reasons, "next_allowed_actions": ["refresh_sec_edgar_html_inline_xbrl_fact_authority_receipt"]},
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
    }
    if _contains_forbidden_output_ref(response):
        _blocked("sec_edgar_html_inline_xbrl_fact_material_bridge_blocked_response_raw_authority_exposed", "SEC EDGAR HTML/iXBRL fact material bridge blocked response would expose raw authority.", http_status=409)
    return response


def _expected_or_authority(request: Mapping[str, Any], request_key: str, authority: Mapping[str, Any], authority_key: str) -> str:
    value = str(request.get(request_key) or authority.get(authority_key) or "").strip()
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_bridge_{request_key}_invalid",
            "SEC EDGAR HTML/iXBRL fact material bridge requires SHA-256 authority hashes.",
            blocked_fields=[request_key],
        )
    if str(authority.get(authority_key) or "") != value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_bridge_{authority_key}_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge authority hash is stale or mismatched.",
            http_status=409,
            blocked_fields=[request_key],
        )
    return value


def _write_receipt(response: Mapping[str, Any]) -> bool:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "fact_material_bridge_receipt_id": response["fact_material_bridge_receipt_id"],
        "fact_material_bridge_receipt_hash": response["fact_material_bridge_receipt_hash"],
        "receipt_hash_basis": {
            "fact_material_bridge_receipt_hash": response["fact_material_bridge_receipt_hash"],
            "fact_authority_receipt_hash": response["fact_authority_receipt_hash"],
            "parser_receipt_hash": response["parser_receipt_hash"],
            "dataset_version_hash": response["dataset_version_hash"],
            "materialization_receipt_hash": response["materialization_receipt_hash"],
            "material_preview_hash": response["material_preview_hash"],
            "gate_b_decision_manifest_id": response["gate_b_decision_manifest_id"],
        },
        "response": dict(response),
        "recorded_at": _server_time(),
    }
    target = _receipt_path(str(response["fact_material_bridge_receipt_id"]))
    if target.exists():
        existing = _read_verified_receipt(str(response["fact_material_bridge_receipt_id"]))
        if existing.get("fact_material_bridge_receipt_hash") != response["fact_material_bridge_receipt_hash"]:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_conflict",
                "A SEC EDGAR HTML/iXBRL fact material bridge receipt already exists for different authority.",
                http_status=409,
            )
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return False


def _read_verified_receipt(fact_material_bridge_receipt_id: str) -> dict[str, Any]:
    receipt_id = str(fact_material_bridge_receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL fact material bridge status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["fact_material_bridge_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_missing",
            "SEC EDGAR HTML/iXBRL fact material bridge receipt was not found.",
            http_status=404,
            blocked_fields=["fact_material_bridge_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL fact material bridge receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("fact_material_bridge_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_invalid",
            "SEC EDGAR HTML/iXBRL fact material bridge receipt is invalid or mismatched.",
            http_status=409,
        )
    if not _is_hash(str(receipt.get("fact_material_bridge_receipt_hash") or "")):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact material bridge receipt hash is invalid.",
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
            "sec_edgar_html_inline_xbrl_fact_material_bridge_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL fact material bridge request binding could not be read.",
            http_status=409,
        )
    if not isinstance(value, dict):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_request_binding_invalid",
            "SEC EDGAR HTML/iXBRL fact material bridge request binding is invalid.",
            http_status=409,
        )
    return value


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_material_bridge_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "fact_material_bridge_basis_hash": basis_hash,
        "fact_material_bridge_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("fact_material_bridge_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_bridge_request_binding_conflict",
                "SEC EDGAR HTML/iXBRL fact material bridge request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            (f"{key}_redacted" if str(key) in _REDACT_KEYS else str(key)): (
                _redacted_ref(nested) if str(key) in _REDACT_KEYS else _redact_value(nested)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str) and (_RAW_URL_RE.search(value) or _LOCAL_PATH_RE.search(value)):
        return _redacted_ref(value)
    return value


def _redacted_ref(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    return {"present": bool(text), "redacted": True, "sha256": _sha256_text(text) if text else None}


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
        "fact_authority_receipt_required": True,
        "direct_unbridged_fact_authority_material_admitted": False,
        "live_sec_network_fetch_performed_by_bridge": False,
        "submissions_lookup_runtime_performed_by_bridge": False,
        "browser_supplied_html_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_local_path_admitted": False,
        "artifact_bytes_admitted": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_enabled": False,
        "fact_to_statement_classification_enabled": False,
        "material_text_table_bridge_mutated": False,
        "existing_downstream_proof_mutated": False,
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
        "raw_fact_values_exposed_in_operator_projection": False,
    }


def _dataset_ids(materialization_hash: str) -> dict[str, str]:
    return {
        "dataset_id": f"ds-sec-ixbrl-facts-{materialization_hash[:20]}",
        "dataset_version_id": f"dv-sec-ixbrl-facts-{materialization_hash[:20]}",
    }


def _datasets_dir() -> Path:
    return _root() / "datasets"


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_bridge_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL fact material bridge requires the existing Layer 3 storage root.",
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
            f"sec_edgar_html_inline_xbrl_fact_material_bridge_{key}_missing",
            f"SEC EDGAR HTML/iXBRL fact material bridge requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_bridge_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL fact material bridge requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_bridge_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL fact material bridge request does not match the admitted runtime contract.",
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
    raise Layer3WorkbenchError(code, message, status="blocked", http_status=http_status, blocked_fields=blocked_fields or [])
