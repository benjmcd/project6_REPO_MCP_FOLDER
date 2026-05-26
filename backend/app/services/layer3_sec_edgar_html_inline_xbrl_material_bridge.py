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
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
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


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_material_bridge.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_material_bridge_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_material_bridge_status.v1"
SCHEMA_VERSION = 1
BRIDGE_MODE = "sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority_v1"
OPERATOR_DECISION = "bridge_sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority"
READY_STATE = "sec_edgar_html_inline_xbrl_material_bridge_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_material_bridge_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
PARSER_FAMILY = "sec_edgar_html_inline_xbrl_source_family_parser_v1"
PARSER_CONTRACT_ID = PARSER_FAMILY
TYPED_CONTENT_CONTRACT_ID = "sec_edgar_html_inline_xbrl_material_units_v1"
MATERIAL_PREVIEW_SCHEMA_ID = "layer3.material_preview_request.v1"
GATE_B_DECISION_SCHEMA_ID = "layer3.gate_b_decision_request.v1"
SOURCE_CLASS = "dataset_version"
SOURCE_CANDIDATE_PREFIX = "src-dataset_version-"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-l3-material-bridge"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-material-bridge"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_material_bridge_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_material_bridge_hash_v1"
MAX_TEXT_UNITS = 100
MAX_TABLE_UNITS = 50

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "bridge_mode",
    "operator_decision",
    "parser_receipt_id",
    "parser_receipt_hash",
    "expected_connector_receipt_hash",
    "expected_live_source_artifact_receipt_hash",
    "expected_source_artifact_receipt_hash",
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
    "local_path",
    "path",
    "paths",
    "process",
    "provider_credentials",
    "provider_url",
    "rag_vector_index",
    "raw_path",
    "raw_url",
    "runtime_db_write",
    "source_expansion",
    "source_upload",
    "source_url",
    "stderr",
    "stdout",
    "storage_dir",
    "url",
    "urls",
}
_REDACT_KEYS = {
    "blob_ref",
    "content_units_ref",
    "diagnostics_ref",
    "download_exchange_ref",
    "raw_storage_ref",
    "source_artifact_key",
    "storage_ref",
}
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_TEXT_TOKEN_RE = re.compile(r"<[^>]+>|[^<]+", re.DOTALL)
_TABLE_RE = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)


def prepare_sec_edgar_html_inline_xbrl_material_bridge(fields: Mapping[str, Any], db: Session) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "bridge_mode", BRIDGE_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    parser_receipt_id = _required(request, "parser_receipt_id")
    parser_receipt_hash = _required_hash(request, "parser_receipt_hash")
    if request.get("rollback_confirmed") is not True or request.get("operator_confirmed") is not True:
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                *([] if request.get("rollback_confirmed") is True else [_reason("missing_rollback_confirmation")]),
                *([] if request.get("operator_confirmed") is True else [_reason("missing_operator_confirmation")]),
            ],
        )

    parser_receipt = layer3_sec_edgar_html_inline_xbrl_parser.read_sec_edgar_html_inline_xbrl_source_family_parser_receipt(
        parser_receipt_id,
        expected_parser_receipt_hash=parser_receipt_hash,
    )
    connector_hash = _expected_or_authority(request, "expected_connector_receipt_hash", parser_receipt, "connector_receipt_hash")
    live_hash = _expected_or_authority(
        request,
        "expected_live_source_artifact_receipt_hash",
        parser_receipt,
        "live_source_artifact_receipt_hash",
    )
    source_hash = _expected_or_authority(
        request,
        "expected_source_artifact_receipt_hash",
        parser_receipt,
        "source_artifact_receipt_hash",
    )
    connector_receipt = layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
        str(parser_receipt["connector_receipt_id"]),
        expected_connector_receipt_hash=connector_hash,
    )
    live_receipt, content = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_bytes(
        str(parser_receipt["live_source_artifact_receipt_id"]),
        expected_live_source_artifact_receipt_hash=live_hash,
    )
    live_artifact = _source_artifact(live_receipt)
    _validate_source_binding(parser_receipt, live_artifact, source_hash=source_hash, content=content)
    reparsed = layer3_sec_edgar_html_inline_xbrl_parser.reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge(
        connector_receipt,
        connector_example_id=str(parser_receipt["connector_example_id"]),
        retained_complete_submission_text=content,
    )
    _validate_reparse_binding(parser_receipt, reparsed)
    units = _material_units(str(reparsed["primary_document_text"]), parser_receipt=parser_receipt)
    materialization = _materialization_basis(parser_receipt, units)
    materialization_hash = stable_hash(materialization)
    expected_materialization_hash = str(request.get("expected_materialization_receipt_hash") or "").strip()
    if expected_materialization_hash and expected_materialization_hash != materialization_hash:
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                _reason(
                    "materialization_receipt_hash_mismatch",
                    expected_materialization_receipt_hash=expected_materialization_hash,
                    received_materialization_receipt_hash=materialization_hash,
                )
            ],
        )

    ids = _dataset_ids(materialization_hash)
    dataset_version_hash = stable_hash(
        {
            "dataset_version_id": ids["dataset_version_id"],
            "materialization_receipt_hash": materialization_hash,
            "admitted_subset_hash": materialization["admitted_subset_hash"],
            "unit_count": len(units),
        }
    )
    _materialize_dataset_version(
        db,
        ids=ids,
        units=units,
        parser_receipt=parser_receipt,
        materialization_hash=materialization_hash,
        dataset_version_hash=dataset_version_hash,
    )
    db.flush()
    material_preview_request_basis = _material_preview_request_basis(
        request_id=request_id,
        dataset_version_id=ids["dataset_version_id"],
        actor=str(request.get("actor") or "operator").strip() or "operator",
    )
    raw_preview = layer3_workbench.material_preview(material_preview_request_basis, db)
    raw_candidates = raw_preview.get("material_candidates") if isinstance(raw_preview.get("material_candidates"), list) else []
    if len(raw_candidates) != 1:
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("material_preview_candidate_count_mismatch", candidate_count=len(raw_candidates))],
        )
    material_candidate = _redacted_material_candidate(
        raw_candidates[0],
        parser_receipt=parser_receipt,
        materialization_hash=materialization_hash,
    )
    candidate_basis = material_candidate_basis_from_preview(material_candidate)
    bridged_preview_hash = material_preview_hash([candidate_basis])
    expected_preview_hash = str(request.get("expected_material_preview_hash") or "").strip()
    if expected_preview_hash and expected_preview_hash != bridged_preview_hash:
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[
                _reason(
                    "material_preview_hash_mismatch",
                    expected_material_preview_hash=expected_preview_hash,
                    received_material_preview_hash=bridged_preview_hash,
                )
            ],
        )
    gate_b_payload, gate_b_manifest_id = _gate_b_payload(
        request_id=request_id,
        raw_preview=raw_preview,
        material_candidate=material_candidate,
        candidate_basis=candidate_basis,
        material_preview_hash_value=bridged_preview_hash,
        actor=str(request.get("actor") or "operator").strip() or "operator",
    )
    expected_gate_b = str(request.get("expected_gate_b_decision_manifest_id") or "").strip()
    if expected_gate_b and expected_gate_b != gate_b_manifest_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_gate_b_decision_basis_mismatch",
            "SEC EDGAR HTML/iXBRL material bridge Gate B decision basis is stale or mismatched.",
            http_status=409,
            blocked_fields=["expected_gate_b_decision_manifest_id"],
        )
    bridge_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "bridge_mode": BRIDGE_MODE,
            "parser_receipt_hash": parser_receipt_hash,
            "connector_receipt_hash": connector_hash,
            "live_source_artifact_receipt_hash": live_hash,
            "source_artifact_receipt_hash": source_hash,
            "content_sha256": parser_receipt["content_sha256"],
            "dataset_version_hash": dataset_version_hash,
            "materialization_receipt_hash": materialization_hash,
            "material_preview_hash": bridged_preview_hash,
            "gate_b_decision_manifest_id": gate_b_manifest_id,
        }
    )
    bridge_receipt_id = f"{RECEIPT_PREFIX}-{bridge_hash[:24]}"
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=SCHEMA_ID),
        "mode": BRIDGE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "bridge_state": READY_STATE,
        "bridge_receipt_id": bridge_receipt_id,
        "bridge_receipt_ref": f"{RECEIPT_PREFIX}:{bridge_hash[:24]}",
        "bridge_receipt_hash": bridge_hash,
        "idempotent_replay": _receipt_path(bridge_receipt_id).exists(),
        "dataset_id": ids["dataset_id"],
        "dataset_version_id": ids["dataset_version_id"],
        "dataset_version_hash": dataset_version_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_contract_id": PARSER_CONTRACT_ID,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "parser_receipt_id": parser_receipt_id,
        "parser_receipt_hash": parser_receipt_hash,
        "connector_receipt_hash": connector_hash,
        "live_source_artifact_receipt_hash": live_hash,
        "source_artifact_receipt_hash": source_hash,
        "materialization_receipt_hash": materialization_hash,
        "material_preview_request_basis": material_preview_request_basis,
        "material_preview_id": raw_preview["material_preview_id"],
        "material_preview_hash": bridged_preview_hash,
        "material_candidate": material_candidate,
        "gate_b_decision_manifest_id": gate_b_manifest_id,
        "gate_b_decision_payload": gate_b_payload,
        "authority_hashes": {
            "parser_receipt_hash": parser_receipt_hash,
            "connector_receipt_hash": connector_hash,
            "live_source_artifact_receipt_hash": live_hash,
            "source_artifact_receipt_hash": source_hash,
            "content_sha256": str(parser_receipt["content_sha256"]),
            "dataset_version_hash": dataset_version_hash,
            "materialization_receipt_hash": materialization_hash,
            "material_preview_hash": bridged_preview_hash,
            "gate_b_decision_manifest_id": gate_b_manifest_id,
            "bridge_receipt_hash": bridge_hash,
        },
        "materialization_summary": {
            "unit_count": len(units),
            "text_unit_count": sum(1 for unit in units if unit["unit_type"] == "narrative_text"),
            "table_unit_count": sum(1 for unit in units if unit["unit_type"] == "html_table_candidate"),
            "admitted_subset_hash": materialization["admitted_subset_hash"],
            "source_order_preserved": True,
            "bounded_text_units": MAX_TEXT_UNITS,
            "bounded_table_units": MAX_TABLE_UNITS,
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
                "submit_sec_edgar_html_inline_xbrl_material_bridge_gate_b_decision_payload",
                "select_sec_edgar_html_inline_xbrl_downstream_layer3_proof",
            ],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
    }
    if _contains_forbidden_output_ref(response):
        return _blocked_response(
            request_id=request_id,
            parser_receipt_hash=parser_receipt_hash,
            reasons=[_reason("raw_path_or_url_authority")],
        )
    db.commit()
    idempotent_replay = _write_receipt(response)
    response["idempotent_replay"] = idempotent_replay
    return response


def inspect_sec_edgar_html_inline_xbrl_material_bridge_status(bridge_receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(bridge_receipt_id)
    response = dict(receipt["response"])
    response.update(
        {
            "schema_id": STATUS_SCHEMA_ID,
            "request_id": f"sec-edgar-html-inline-xbrl-material-bridge-status-{receipt['bridge_receipt_hash'][:12]}",
            "server_time": _server_time(),
            "idempotent_replay": False,
        }
    )
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_status_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL material bridge status would expose raw authority.",
            http_status=409,
        )
    return response


def _materialize_dataset_version(
    db: Session,
    *,
    ids: Mapping[str, str],
    units: list[dict[str, Any]],
    parser_receipt: Mapping[str, Any],
    materialization_hash: str,
    dataset_version_hash: str,
) -> None:
    csv_path = _datasets_dir() / f"{ids['dataset_version_id']}.csv"
    if not csv_path.exists():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(units[0]))
            writer.writeheader()
            writer.writerows(units)
    if db.get(Dataset, ids["dataset_id"]) is None:
        db.add(
            Dataset(
                dataset_id=ids["dataset_id"],
                name="SEC EDGAR HTML iXBRL material units",
                description="Receipt-bound SEC EDGAR HTML/iXBRL narrative and table candidate units.",
                frequency_hint=None,
                time_column=None,
            )
        )
    if db.get(DatasetVersion, ids["dataset_version_id"]) is None:
        db.add(
            DatasetVersion(
                dataset_version_id=ids["dataset_version_id"],
                dataset_id=ids["dataset_id"],
                version_label="sec-html-ixbrl-material-v1",
                version_type="sec_edgar_html_inline_xbrl_material_units",
                status="ready",
                storage_ref=str(csv_path),
                row_count=len(units),
                notes=f"materialization_receipt_hash={materialization_hash}",
            )
        )
        for index, (name, dtype, role, numeric) in enumerate(
            (
                ("unit_order", "int64", "ordinal", True),
                ("unit_type", "string", "dimension", False),
                ("source_start", "int64", "source_offset", True),
                ("source_end", "int64", "source_offset", True),
                ("content_hash", "string", "authority_hash", False),
                ("content_length", "int64", "measure", True),
                ("content_text", "string", "material_payload", False),
                ("parser_receipt_hash", "string", "authority_hash", False),
            )
        ):
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
                source_mode="sec_edgar_html_inline_xbrl_material_bridge",
                source_artifact_key=f"sec-edgar-html-inline-xbrl-material:{materialization_hash[:24]}",
                downloaded_sha256=str(parser_receipt["content_sha256"]),
                raw_storage_ref=None,
                artifact_locator_type="server_owned_ref",
                fetch_policy_mode="server_owned_receipt",
                source_reference_json={
                    "target_id": str(parser_receipt["connector_example_id"]),
                    "accession_number": str((parser_receipt.get("identity_binding") or {}).get("accession_or_submission_id_hash") or ""),
                    "table_index": 0,
                    "table_hash": stable_hash([unit["content_hash"] for unit in units if unit["unit_type"] == "html_table_candidate"]),
                    "parser_family": PARSER_FAMILY,
                    "parser_contract_id": PARSER_CONTRACT_ID,
                    "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
                    "diagnostics_ref": f"sec-edgar-html-inline-xbrl-diagnostics:{str(parser_receipt['diagnostics_hash'])[:24]}",
                    "materialization_receipt_hash": materialization_hash,
                    "dataset_version_hash": dataset_version_hash,
                },
            )
        )


def _material_units(primary_text: str, *, parser_receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    text_count = 0
    table_count = 0
    for match in _TEXT_TOKEN_RE.finditer(primary_text):
        token = match.group(0)
        if token.startswith("<"):
            continue
        normalized = re.sub(r"\s+", " ", html_lib.unescape(token)).strip()
        if not normalized:
            continue
        text_count += 1
        if text_count <= MAX_TEXT_UNITS:
            units.append(_unit("narrative_text", match.start(), match.end(), normalized, parser_receipt))
    for match in _TABLE_RE.finditer(primary_text):
        table_count += 1
        if table_count <= MAX_TABLE_UNITS:
            units.append(_unit("html_table_candidate", match.start(), match.end(), match.group(0), parser_receipt))
    units.sort(key=lambda item: (int(item["source_start"]), item["unit_type"]))
    for index, unit in enumerate(units, start=1):
        unit["unit_order"] = index
    if not units:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_no_material_units",
            "SEC EDGAR HTML/iXBRL material bridge found no bounded narrative or table units.",
            http_status=409,
        )
    return units


def _unit(unit_type: str, start: int, end: int, content: str, parser_receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "unit_order": 0,
        "unit_type": unit_type,
        "source_start": start,
        "source_end": end,
        "content_hash": _sha256_text(content),
        "content_length": len(content),
        "content_text": content,
        "parser_receipt_hash": str(parser_receipt["parser_receipt_hash"]),
    }


def _materialization_basis(parser_receipt: Mapping[str, Any], units: list[dict[str, Any]]) -> dict[str, Any]:
    admitted_subset = [
        {
            "unit_order": unit["unit_order"],
            "unit_type": unit["unit_type"],
            "source_start": unit["source_start"],
            "source_end": unit["source_end"],
            "content_hash": unit["content_hash"],
            "content_length": unit["content_length"],
        }
        for unit in units
    ]
    return {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_materialization_receipt.v1",
        "schema_version": SCHEMA_VERSION,
        "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
        "document_inventory_hash": parser_receipt["document_inventory_hash"],
        "content_order_hash": parser_receipt["content_order_hash"],
        "table_candidate_inventory_hash": parser_receipt["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": parser_receipt["inline_xbrl_marker_inventory_hash"],
        "admitted_subset_hash": stable_hash(admitted_subset),
        "unit_count": len(units),
    }


def _material_preview_request_basis(*, request_id: str, dataset_version_id: str, actor: str) -> dict[str, Any]:
    return {
        "schema_id": MATERIAL_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "client_request_id": f"{request_id}:material-preview",
        "source_candidate_ids": [f"{SOURCE_CANDIDATE_PREFIX}sec-html-{_sha256_text(dataset_version_id)[:16]}"],
        "dataset_version_ids": [dataset_version_id],
        "query_basis": {
            "terms": ["sec_edgar_html_inline_xbrl_material_bridge"],
            "filters": {"dataset_version_ids": [dataset_version_id]},
        },
        "actor": actor,
    }


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
            "sec_edgar_html_inline_xbrl_material_bridge_gate_b_decision_basis_mismatch",
            "SEC EDGAR HTML/iXBRL material bridge Gate B decision basis no longer matches material preview.",
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
            "preflight_id": f"sec-edgar-html-inline-xbrl-{_sha256_text(request_id)[:16]}",
            "source_set_id": f"sec-edgar-html-inline-xbrl-material-{_sha256_text(str(material_candidate['source_ref']))[:16]}",
            "material_preview_id": raw_preview["material_preview_id"],
            "material_preview_hash": material_preview_hash_value,
            "candidate_decisions": [
                {
                    "candidate_id": material_candidate["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": decision_basis,
                }
            ],
            "commit_reason": "sec_edgar_html_inline_xbrl_material_bridge",
            "actor": actor,
        },
        manifest_id,
    )


def _redacted_material_candidate(
    candidate: Mapping[str, Any],
    *,
    parser_receipt: Mapping[str, Any],
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
            "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
            "materialization_receipt_hash": materialization_hash,
            "redaction": {"raw_storage_ref_exposed": False, "raw_url_exposed": False, "artifact_bytes_exposed": False},
        }
    )
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_label": "SEC EDGAR HTML/iXBRL Dataset Version",
        "source_class": SOURCE_CLASS,
        "source_ref": str(candidate.get("source_ref") or ""),
        "owner_service_source_shape": SOURCE_CLASS,
        "planning_shape_family": "mixed_narrative_table",
        "source_family": SOURCE_FAMILY,
        "source_family_label": "SEC/EDGAR HTML inline XBRL",
        "source_admission_state": str(candidate.get("source_admission_state") or "admitted_materialized_dataset_version"),
        "source_family_scope": str(candidate.get("source_family_scope") or ""),
        "source_trace": source_trace,
        "query_basis": BRIDGE_MODE,
        "validation_status": str(candidate.get("validation_status") or "valid"),
        "duplicate_status": str(candidate.get("duplicate_status") or "unique"),
        "size_or_unit_count": int(candidate.get("size_or_unit_count") or 0),
        "preview_payload_ref": None,
        "provenance_ref": f"{RECEIPT_PREFIX}:{str(parser_receipt['parser_receipt_hash'])[:24]}",
        "source_identity": source_identity,
        "source_provenance": source_provenance,
        "payload": {
            "dataset_version_id": (candidate.get("payload") or {}).get("dataset_version_id")
            if isinstance(candidate.get("payload"), Mapping)
            else None,
            "source_family": SOURCE_FAMILY,
            "parser_family": PARSER_FAMILY,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
            "materialization_receipt_hash": materialization_hash,
        },
        "load_summary": {
            "loaded_records": int((candidate.get("load_summary") or {}).get("loaded_records") or 0)
            if isinstance(candidate.get("load_summary"), Mapping)
            else 0,
            "failed_records": 0,
            "preview_material": True,
            "storage_available": bool((candidate.get("load_summary") or {}).get("storage_available"))
            if isinstance(candidate.get("load_summary"), Mapping)
            else False,
            "raw_refs_redacted": True,
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


def _validate_reparse_binding(parser_receipt: Mapping[str, Any], reparsed: Mapping[str, Any]) -> None:
    parsed = reparsed.get("parsed") if isinstance(reparsed.get("parsed"), Mapping) else {}
    expected = {
        "primary_document_hash": parsed.get("primary_document_hash"),
        "document_inventory_hash": stable_hash(parsed.get("document_inventory") or []),
        "content_order_hash": stable_hash(parsed.get("content_order") or []),
        "table_candidate_inventory_hash": stable_hash(parsed.get("table_candidate_inventory") or []),
        "inline_xbrl_marker_inventory_hash": stable_hash(parsed.get("inline_xbrl_marker_inventory") or []),
    }
    mismatches = [key for key, value in expected.items() if str(parser_receipt.get(key) or "") != str(value or "")]
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_parser_reparse_mismatch",
            "SEC EDGAR HTML/iXBRL material bridge requires retained artifact content to reparse to the parser receipt.",
            http_status=409,
            blocked_fields=mismatches,
        )


def _validate_source_binding(
    parser_receipt: Mapping[str, Any],
    live_artifact: Mapping[str, Any],
    *,
    source_hash: str,
    content: bytes,
) -> None:
    checks = {
        "source_artifact_receipt_hash": source_hash,
        "content_sha256": hashlib.sha256(content).hexdigest(),
    }
    for key, expected in checks.items():
        if str(parser_receipt.get(key) or "") != str(expected or "") or str(live_artifact.get(key) or "") != str(expected or ""):
            _blocked(
                "sec_edgar_html_inline_xbrl_material_bridge_source_artifact_mismatch",
                "SEC EDGAR HTML/iXBRL material bridge requires parser and live source-artifact authority to match.",
                http_status=409,
                blocked_fields=[key],
            )


def _source_artifact(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    artifact = receipt.get("source_artifact_receipt")
    if not isinstance(artifact, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_source_artifact_missing",
            "SEC EDGAR HTML/iXBRL material bridge requires live source-artifact authority.",
            http_status=409,
        )
    return artifact


def _expected_or_authority(request: Mapping[str, Any], request_key: str, authority: Mapping[str, Any], authority_key: str) -> str:
    value = str(request.get(request_key) or authority.get(authority_key) or "").strip()
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_material_bridge_{request_key}_invalid",
            "SEC EDGAR HTML/iXBRL material bridge requires SHA-256 authority hashes.",
            blocked_fields=[request_key],
        )
    if str(authority.get(authority_key) or "") != value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_material_bridge_{authority_key}_mismatch",
            "SEC EDGAR HTML/iXBRL material bridge authority hash is stale or mismatched.",
            http_status=409,
            blocked_fields=[request_key],
        )
    return value


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL material bridge rejects caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_unknown_field",
            "SEC EDGAR HTML/iXBRL material bridge fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL material bridge requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _blocked_response(*, request_id: str, parser_receipt_hash: str, reasons: list[dict[str, Any]]) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": BRIDGE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "bridge_state": BLOCKED_STATE,
        "parser_receipt_hash": parser_receipt_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "material_preview_request_basis": None,
        "material_preview_hash": None,
        "gate_b_decision_manifest_id": None,
        "status_projection": {
            "ready": False,
            "blocked_reasons": reasons,
            "next_allowed_actions": ["refresh_sec_edgar_html_inline_xbrl_parser_receipt"],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_blocked_response_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL material bridge blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _write_receipt(response: Mapping[str, Any]) -> bool:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "bridge_receipt_id": response["bridge_receipt_id"],
        "bridge_receipt_hash": response["bridge_receipt_hash"],
        "receipt_hash_basis": {
            "bridge_receipt_hash": response["bridge_receipt_hash"],
            "parser_receipt_hash": response["parser_receipt_hash"],
            "dataset_version_hash": response["dataset_version_hash"],
            "materialization_receipt_hash": response["materialization_receipt_hash"],
            "material_preview_hash": response["material_preview_hash"],
            "gate_b_decision_manifest_id": response["gate_b_decision_manifest_id"],
        },
        "response": dict(response),
        "recorded_at": _server_time(),
    }
    target = _receipt_path(str(response["bridge_receipt_id"]))
    if target.exists():
        existing = _read_verified_receipt(str(response["bridge_receipt_id"]))
        if existing.get("bridge_receipt_hash") != response["bridge_receipt_hash"]:
            _blocked(
                "sec_edgar_html_inline_xbrl_material_bridge_receipt_conflict",
                "A SEC EDGAR HTML/iXBRL material bridge receipt already exists for different authority.",
                http_status=409,
            )
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return False


def _read_verified_receipt(bridge_receipt_id: str) -> dict[str, Any]:
    bridge_receipt_id = str(bridge_receipt_id or "").strip()
    suffix = bridge_receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not bridge_receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL material bridge status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["bridge_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(bridge_receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_receipt_missing",
            "SEC EDGAR HTML/iXBRL material bridge receipt was not found.",
            http_status=404,
            blocked_fields=["bridge_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL material bridge receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("bridge_receipt_id") != bridge_receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_receipt_invalid",
            "SEC EDGAR HTML/iXBRL material bridge receipt is invalid or mismatched.",
            http_status=409,
        )
    if not _is_hash(str(receipt.get("bridge_receipt_hash") or "")):
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_receipt_hash_invalid",
            "SEC EDGAR HTML/iXBRL material bridge receipt hash is invalid.",
            http_status=409,
        )
    return receipt


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
        "direct_unbridged_html_inline_xbrl_parser_receipt_material_authority_admitted": False,
        "live_sec_network_fetch_performed_by_bridge": False,
        "submissions_lookup_runtime_performed_by_bridge": False,
        "arbitrary_url_or_upload_parse_admitted": False,
        "xml_xbrl_fact_authority_created": False,
        "financial_statement_semantics_enabled": False,
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
    }


def _dataset_ids(materialization_hash: str) -> dict[str, str]:
    return {
        "dataset_id": f"ds-sec-html-{materialization_hash[:20]}",
        "dataset_version_id": f"dv-sec-html-{materialization_hash[:20]}",
    }


def _datasets_dir() -> Path:
    return _root() / "datasets"


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_material_bridge_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL material bridge requires the existing Layer 3 storage root.",
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
            f"sec_edgar_html_inline_xbrl_material_bridge_{key}_missing",
            f"SEC EDGAR HTML/iXBRL material bridge requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_material_bridge_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL material bridge requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_material_bridge_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL material bridge request does not match the admitted runtime contract.",
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
