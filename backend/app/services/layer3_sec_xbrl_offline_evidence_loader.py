from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Any

from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    STATEMENT_CLASSIFICATION_HASH_VERSION,
    STATEMENT_CLASSIFICATION_MODE,
    classification_authority_view,
    classification_receipt_hash_basis,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_xbrl_public_authority_guard import report_text_reference_flags
from app.services.layer3_sec_xbrl_report_leak_guard import reject_report_leaks


SCHEMA_ID = "layer3.sec_xbrl_offline_evidence_loader.v1"
REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_offline_evidence_loader_report.v1"
SIDECAR_RECEIPT_DIR = "layer3-sec-edgar-arelle-resolved-fact-authority"
VALUE_STORE_SUBDIR = "internal-value-stores"
STATEMENT_CLASSIFICATION_DIR = "layer3-sec-edgar-html-inline-xbrl-fact-statement-classification"

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
SIDECAR_RECEIPT_ID_RE = re.compile(r"^sec-edgar-arelle-resolved-fact-authority-[0-9a-f]{24}$")


class SecXbrlOfflineEvidenceLoaderError(ValueError):
    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_report(self) -> dict[str, Any]:
        return {
            "status": "offline_evidence_bundle_blocked",
            "blocked_reasons": [
                {
                    "reason": self.code,
                    "message": self.message,
                    "details": dict(self.details),
                }
            ],
        }


_reject_report_leaks = partial(
    reject_report_leaks,
    exception_factory=lambda: SecXbrlOfflineEvidenceLoaderError(
        "sec_xbrl_offline_evidence_loader_report_redaction_failed",
        "SEC XBRL offline evidence loader report leaked raw authority references.",
    ),
)


def load_sec_xbrl_offline_evidence_bundle(
    storage_dir: str | Path,
    *,
    companyfacts_path: str | Path | None = None,
    expected_sidecar_receipt_hash: str | None = None,
    expected_statement_classification_receipt_hash: str | None = None,
) -> dict[str, Any]:
    """Read already-acquired SEC XBRL storage into the orchestrator's in-memory evidence contract."""

    storage = _required_storage_dir(storage_dir)
    sidecar = _select_receipt(
        storage / SIDECAR_RECEIPT_DIR / "receipts",
        hash_field="sidecar_receipt_hash",
        expected_hash=expected_sidecar_receipt_hash,
        ambiguous_code="sec_xbrl_offline_evidence_loader_sidecar_ambiguous",
        missing_code="sec_xbrl_offline_evidence_loader_sidecar_missing",
    )
    _validate_sidecar(sidecar)
    sidecar_receipt_id = _required_sidecar_receipt_id(sidecar.get("sidecar_receipt_id"), "sidecar_receipt_id")
    sidecar_receipt_hash = _required_hash(sidecar.get("sidecar_receipt_hash"), "sidecar_receipt_hash")
    value_store = _read_value_store(storage, sidecar_receipt_id=sidecar_receipt_id)
    value_records = _required_sequence(value_store.get("value_records"), "value_records")
    value_store_hash = _validate_value_store(sidecar=sidecar, value_store=value_store, value_records=value_records)

    classification = _select_receipt(
        storage / STATEMENT_CLASSIFICATION_DIR / "receipts",
        hash_field="statement_classification_receipt_hash",
        expected_hash=expected_statement_classification_receipt_hash,
        ambiguous_code="sec_xbrl_offline_evidence_loader_statement_classification_ambiguous",
        missing_code="sec_xbrl_offline_evidence_loader_statement_classification_missing",
    )
    _validate_statement_classification_receipt_hash(classification)
    statement_roles = _statement_roles_from_classification(classification, sidecar=sidecar)
    companyfacts, companyfacts_state = _read_companyfacts(companyfacts_path)
    dataset_version_id = _dataset_version_id(
        storage,
        sidecar_receipt_hash=sidecar_receipt_hash,
        fact_material_bridge_receipt_hash=_classification_bridge_hash(classification),
    )
    if not dataset_version_id:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_dataset_version_missing",
            "SEC XBRL offline evidence storage must include bridge dataset-version provenance.",
        )

    evidence = {
        "companyfacts": companyfacts,
        "sidecar_receipt": sidecar,
        "value_store": {
            "value_store_hash": value_store_hash,
            "value_records": value_records,
        },
        "statement_role_view_records": statement_roles,
        "dataset_version_id": dataset_version_id,
    }
    authority_refs = {
        "sidecar_receipt_hash": sidecar_receipt_hash,
        "value_store_hash": value_store_hash,
        "statement_classification_receipt_hash": _required_hash(
            classification.get("statement_classification_receipt_hash"),
            "statement_classification_receipt_hash",
        ),
        "statement_role_view_hash": stable_hash(statement_roles),
    }
    if dataset_version_id:
        authority_refs["dataset_version_id_hash"] = stable_hash({"dataset_version_id": dataset_version_id})[:24]

    return {
        "schema_id": SCHEMA_ID,
        "status": (
            "offline_evidence_bundle_ready"
            if companyfacts_state == "supplied"
            else "offline_evidence_bundle_ready_without_companyfacts_oracle"
        ),
        "evidence": evidence,
        "authority_refs": authority_refs,
        "summary": {
            "resolved_fact_count": len(_required_sequence(sidecar.get("resolved_fact_records"), "resolved_fact_records")),
            "resolved_fact_projection_count": len(
                _required_sequence(sidecar.get("resolved_fact_projection"), "resolved_fact_projection")
            ),
            "value_record_count": len(value_records),
            "statement_role_record_count": len(statement_roles),
            "companyfacts_authority_state": companyfacts_state,
            "companyfacts_oracle_supplied": companyfacts_state == "supplied",
        },
        "controls": _controls(db_persistence_performed=False),
    }


def inspect_sec_xbrl_offline_evidence_storage(
    storage_dir: str | Path,
    *,
    companyfacts_path: str | Path | None = None,
    expected_sidecar_receipt_hash: str | None = None,
    expected_statement_classification_receipt_hash: str | None = None,
) -> dict[str, Any]:
    """Return a redacted validate-only readiness report for already-acquired offline storage."""

    try:
        bundle = load_sec_xbrl_offline_evidence_bundle(
            storage_dir,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=expected_sidecar_receipt_hash,
            expected_statement_classification_receipt_hash=expected_statement_classification_receipt_hash,
        )
    except SecXbrlOfflineEvidenceLoaderError as exc:
        report = {
            "schema_id": REPORT_SCHEMA_ID,
            "schema_version": 1,
            **exc.to_report(),
            "storage_marker": _blocked_storage_marker(Path(storage_dir)),
            "paths_redacted": True,
            "controls": _controls(db_persistence_performed=False),
        }
        _reject_report_leaks(report)
        return report

    summary = dict(bundle["summary"])
    companyfacts_supplied = summary["companyfacts_oracle_supplied"] is True
    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "schema_version": 1,
        "status": bundle["status"],
        "storage_marker": _storage_marker(Path(storage_dir)),
        "paths_redacted": True,
        "authority_refs": dict(bundle["authority_refs"]),
        "summary": summary,
        "readiness": {
            "operator_review_creation_ready": companyfacts_supplied,
            "operator_review_creation_blocked_reason": (
                ""
                if companyfacts_supplied
                else "companyfacts_oracle_not_supplied"
            ),
            "companyfacts_oracle_supplied": companyfacts_supplied,
            "production_admission_ready": False,
            "production_admission_blocked_reason": (
                "diagnostic_validate_only_not_production_admission"
                if companyfacts_supplied
                else "companyfacts_oracle_not_supplied"
            ),
        },
        "controls": _controls(db_persistence_performed=False),
    }
    _reject_report_leaks(report)
    return report


def _required_storage_dir(value: str | Path) -> Path:
    path = Path(value)
    if not path.exists() or not path.is_dir():
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_storage_missing",
            "SEC XBRL offline evidence storage directory is missing.",
        )
    return path


def _select_receipt(
    receipt_dir: Path,
    *,
    hash_field: str,
    expected_hash: str | None,
    ambiguous_code: str,
    missing_code: str,
) -> dict[str, Any]:
    if expected_hash is not None:
        expected_hash = _required_hash(expected_hash, hash_field)
    receipts = []
    for path in sorted(receipt_dir.glob("*.json")):
        payload = _read_json_object(path)
        if expected_hash is None or str(payload.get(hash_field) or "") == expected_hash:
            receipts.append(payload)
    if not receipts:
        raise SecXbrlOfflineEvidenceLoaderError(
            missing_code,
            "Required SEC XBRL offline evidence receipt is missing.",
            details={"hash_field": hash_field, "expected_hash_supplied": expected_hash is not None},
        )
    if len(receipts) > 1:
        raise SecXbrlOfflineEvidenceLoaderError(
            ambiguous_code,
            "SEC XBRL offline evidence storage has multiple candidate receipts; supply an expected hash.",
            details={"hash_field": hash_field, "candidate_count": len(receipts)},
        )
    return receipts[0]


def _validate_sidecar(sidecar: Mapping[str, Any]) -> None:
    sidecar_hash = _required_hash(sidecar.get("sidecar_receipt_hash"), "sidecar_receipt_hash")
    records = _required_sequence(sidecar.get("resolved_fact_records"), "resolved_fact_records")
    projection = _required_sequence(sidecar.get("resolved_fact_projection"), "resolved_fact_projection")
    inventory_hash = _required_hash(sidecar.get("resolved_fact_inventory_hash"), "resolved_fact_inventory_hash")
    if stable_hash(projection) != inventory_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_sidecar_projection_hash_mismatch",
            "SEC XBRL offline sidecar projection is stale or hash-mismatched.",
        )
    record_ids = {str(record.get("resolved_fact_id") or "") for record in records}
    projection_ids = {str(item.get("resolved_fact_id") or "") for item in projection}
    if not record_ids or not record_ids.issubset(projection_ids):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_sidecar_projection_unbound",
            "SEC XBRL offline sidecar projection does not bind every resolved fact.",
            details={"resolved_fact_count": len(record_ids), "projection_count": len(projection_ids)},
        )
    for item in projection:
        if item.get("value_redacted") is not True or any(item.get(key) is not None for key in ("value", "effective_value", "lexical_value")):
            raise SecXbrlOfflineEvidenceLoaderError(
                "sec_xbrl_offline_evidence_loader_sidecar_projection_not_redacted",
                "SEC XBRL offline sidecar projection is not redacted.",
            )
    authority = sidecar.get("authority_hashes") if isinstance(sidecar.get("authority_hashes"), Mapping) else {}
    if authority and str(authority.get("sidecar_receipt_hash") or "") != sidecar_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_sidecar_authority_hash_mismatch",
            "SEC XBRL offline sidecar authority hash does not match the receipt hash.",
        )


def _read_value_store(storage: Path, *, sidecar_receipt_id: str) -> dict[str, Any]:
    parent = (storage / SIDECAR_RECEIPT_DIR / VALUE_STORE_SUBDIR).resolve()
    path = (parent / f"{sidecar_receipt_id}.json").resolve()
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_value_store_path_escape",
            "SEC XBRL offline value-store path must remain inside the supplied storage directory.",
        ) from exc
    return _read_json_object(path)


def _validate_value_store(
    *,
    sidecar: Mapping[str, Any],
    value_store: Mapping[str, Any],
    value_records: Sequence[Mapping[str, Any]],
) -> str:
    sidecar_hash = _required_hash(sidecar.get("sidecar_receipt_hash"), "sidecar_receipt_hash")
    if str(value_store.get("sidecar_receipt_hash") or "") != sidecar_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_value_store_lineage_mismatch",
            "SEC XBRL offline value store does not match the sidecar receipt.",
        )
    metadata = sidecar.get("internal_value_store") if isinstance(sidecar.get("internal_value_store"), Mapping) else {}
    declared = _required_hash(metadata.get("value_store_hash"), "value_store_hash")
    if stable_hash(list(value_records)) != declared:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_value_store_hash_mismatch",
            "SEC XBRL offline value store hash is stale or mismatched.",
        )
    declared_count = _required_int(metadata.get("value_record_count"), "internal_value_store.value_record_count")
    if declared_count != len(value_records):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_value_store_count_mismatch",
            "SEC XBRL offline value store count does not match sidecar metadata.",
        )
    return declared


def _statement_roles_from_classification(
    classification: Mapping[str, Any],
    *,
    sidecar: Mapping[str, Any],
) -> list[dict[str, Any]]:
    sidecar_hash = _required_hash(sidecar.get("sidecar_receipt_hash"), "sidecar_receipt_hash")
    inventory_hash = _required_hash(sidecar.get("resolved_fact_inventory_hash"), "resolved_fact_inventory_hash")
    if _classification_fact_authority_hash(classification) != sidecar_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_authority_mismatch",
            "SEC XBRL statement classification does not bind to the selected sidecar receipt.",
        )
    if _classification_fact_inventory_hash(classification) != inventory_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_inventory_mismatch",
            "SEC XBRL statement classification does not bind to the selected resolved-fact inventory.",
        )
    _classification_bridge_hash(classification)
    records = _required_sequence(classification.get("classification_inventory"), "classification_inventory")
    classification_inventory_hash = _required_hash(
        classification.get("classification_inventory_hash"),
        "classification_inventory_hash",
    )
    if stable_hash(records) != classification_inventory_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_inventory_hash_mismatch",
            "SEC XBRL statement classification inventory is stale or hash-mismatched.",
        )
    roles: list[dict[str, Any]] = []
    for record in records:
        fact_id = _required_text(record.get("fact_id_or_order_key"), "fact_id_or_order_key")
        role = _required_text(record.get("statement_candidate_role"), "statement_candidate_role")
        roles.append(
            {
                "fact_id_or_order_key": fact_id,
                "statement_candidate_role": role,
                "classification_confidence": str(record.get("classification_confidence") or ""),
                "classification_basis": record.get("classification_basis") if isinstance(record.get("classification_basis"), Mapping) else {},
            }
        )
    if not roles:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_roles_missing",
            "SEC XBRL statement classification has no statement-role records.",
        )
    return roles


def _read_companyfacts(companyfacts_path: str | Path | None) -> tuple[dict[str, Any], str]:
    if companyfacts_path is None:
        return {}, "not_supplied"
    payload = _read_json_object(Path(companyfacts_path))
    facts = payload.get("facts") if isinstance(payload.get("facts"), Mapping) else payload
    if not isinstance(facts, Mapping):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_companyfacts_invalid",
            "SEC XBRL offline CompanyFacts payload must be an object.",
        )
    return dict(facts), "supplied"


def _validate_statement_classification_receipt_hash(classification: Mapping[str, Any]) -> None:
    declared = _required_hash(
        classification.get("statement_classification_receipt_hash"),
        "statement_classification_receipt_hash",
    )
    classification_mode = _required_text(classification.get("classification_mode"), "classification_mode")
    basis = classification_receipt_hash_basis(
        classification_mode=classification_mode,
        fact_authority_receipt_hash=_classification_fact_authority_hash(classification),
        fact_material_bridge_receipt_hash=_classification_bridge_hash(classification),
        fact_inventory_hash=_classification_fact_inventory_hash(classification),
        classification_inventory_hash=_required_hash(
            classification.get("classification_inventory_hash"),
            "classification_inventory_hash",
        ),
        semantic_profile_inventory_hash=_required_hash(
            classification.get("semantic_profile_inventory_hash"),
            "semantic_profile_inventory_hash",
        ),
        classification_order_hash=_required_hash(
            classification.get("classification_order_hash"),
            "classification_order_hash",
        ),
        statement_group_inventory_hash=_required_hash(
            classification.get("statement_group_inventory_hash"),
            "statement_group_inventory_hash",
        ),
        unclassified_fact_inventory_hash=_required_hash(
            classification.get("unclassified_fact_inventory_hash"),
            "unclassified_fact_inventory_hash",
        ),
        classification_diagnostics_hash=_required_hash(
            classification.get("classification_diagnostics_hash"),
            "classification_diagnostics_hash",
        ),
    )
    if classification_mode != STATEMENT_CLASSIFICATION_MODE:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_mode_mismatch",
            "SEC XBRL statement classification mode is not admitted by the offline loader.",
        )
    if stable_hash(basis) != declared:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_receipt_hash_mismatch",
            "SEC XBRL statement classification receipt hash is stale or mismatched.",
        )


def _classification_fact_authority_hash(classification: Mapping[str, Any]) -> str:
    view = classification_authority_view(classification)
    top_level_hash = _required_hash(
        view["top_level"].get("fact_authority_receipt_hash"),
        "fact_authority_receipt_hash",
    )
    authority_hash = _required_hash(
        view["authority_hashes"].get("fact_authority_receipt_hash"),
        "authority_hashes.fact_authority_receipt_hash",
    )
    if authority_hash != top_level_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_fact_authority_hash_mismatch",
            "SEC XBRL statement classification fact authority hash copies do not match.",
        )
    return top_level_hash


def _classification_fact_inventory_hash(classification: Mapping[str, Any]) -> str:
    view = classification_authority_view(classification)
    top_level_hash = _required_hash(
        view["top_level"].get("fact_inventory_hash"),
        "fact_inventory_hash",
    )
    authority_hash = _required_hash(
        view["authority_hashes"].get("fact_inventory_hash"),
        "authority_hashes.fact_inventory_hash",
    )
    if authority_hash != top_level_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_fact_inventory_hash_mismatch",
            "SEC XBRL statement classification fact inventory hash copies do not match.",
        )
    return top_level_hash


def _classification_bridge_hash(classification: Mapping[str, Any]) -> str:
    view = classification_authority_view(classification)
    bridge_hash = _required_hash(
        view["top_level"].get("fact_material_bridge_receipt_hash"),
        "fact_material_bridge_receipt_hash",
    )
    authority_bridge_hash = str(view["authority_hashes"].get("fact_material_bridge_receipt_hash") or "")
    if authority_bridge_hash and authority_bridge_hash != bridge_hash:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_statement_classification_bridge_hash_mismatch",
            "SEC XBRL statement classification bridge authority hash does not match the receipt.",
        )
    return bridge_hash


def _dataset_version_id(
    storage: Path,
    *,
    sidecar_receipt_hash: str,
    fact_material_bridge_receipt_hash: str,
) -> str | None:
    bridge_dir = storage / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge" / "receipts"
    matches: list[str] = []
    for path in sorted(bridge_dir.glob("*.json")):
        payload = _read_json_object(path)
        bridge_hash = _required_hash(payload.get("fact_material_bridge_receipt_hash"), "fact_material_bridge_receipt_hash")
        if bridge_hash != fact_material_bridge_receipt_hash:
            continue
        response = payload.get("response") if isinstance(payload.get("response"), Mapping) else {}
        if str(response.get("arelle_sidecar_receipt_hash") or "") != sidecar_receipt_hash:
            raise SecXbrlOfflineEvidenceLoaderError(
                "sec_xbrl_offline_evidence_loader_bridge_sidecar_hash_mismatch",
                "SEC XBRL material bridge receipt does not bind to the selected sidecar receipt.",
            )
        matches.append(_required_text(response.get("dataset_version_id"), "dataset_version_id"))
    if len(matches) > 1:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_bridge_ambiguous",
            "SEC XBRL offline evidence storage has multiple bridge receipts for the selected classification.",
        )
    return matches[0] if matches else None


def _storage_marker(storage_dir: Path) -> str:
    storage = _required_storage_dir(storage_dir)
    markers = []
    for path in sorted(storage.rglob("*.json")):
        try:
            payload = _read_json_object(path)
        except SecXbrlOfflineEvidenceLoaderError:
            continue
        for key in (
            "sidecar_receipt_hash",
            "statement_classification_receipt_hash",
            "fact_material_bridge_receipt_hash",
            "connector_receipt_hash",
        ):
            value = payload.get(key)
            if isinstance(value, str) and HASH_RE.fullmatch(value):
                markers.append({key: value})
    return stable_hash(markers)[:24]


def _blocked_storage_marker(storage_dir: Path) -> str:
    try:
        return _storage_marker(storage_dir)
    except SecXbrlOfflineEvidenceLoaderError:
        return ""


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_json_missing",
            "SEC XBRL offline evidence JSON file is missing.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_json_invalid",
            "SEC XBRL offline evidence JSON file is invalid.",
        ) from exc
    if not isinstance(payload, dict):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_json_not_object",
            "SEC XBRL offline evidence JSON file must contain an object.",
        )
    return payload


def _required_sequence(value: Any, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_sequence_missing",
            "SEC XBRL offline evidence requires a sequence field.",
            details={"field": field},
        )
    items = list(value)
    if any(not isinstance(item, Mapping) for item in items):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_sequence_invalid",
            "SEC XBRL offline evidence sequence entries must be objects.",
            details={"field": field},
        )
    return items


def _required_hash(value: Any, field: str) -> str:
    text = _required_text(value, field).lower()
    if not HASH_RE.fullmatch(text):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_hash_invalid",
            "SEC XBRL offline evidence requires 64-character lowercase hex hashes.",
            details={"field": field},
        )
    return text


def _required_sidecar_receipt_id(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not SIDECAR_RECEIPT_ID_RE.fullmatch(text):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_receipt_id_invalid",
            "SEC XBRL offline sidecar receipt id is not a governed receipt id.",
            details={"field": field},
        )
    return text


def _required_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_count_invalid",
            "SEC XBRL offline evidence count fields must be integers.",
            details={"field": field},
        ) from exc


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_field_missing",
            "SEC XBRL offline evidence requires a non-empty field.",
            details={"field": field},
        )
    if any(report_text_reference_flags(text).values()):
        raise SecXbrlOfflineEvidenceLoaderError(
            "sec_xbrl_offline_evidence_loader_raw_reference_not_admitted",
            "SEC XBRL offline evidence public references cannot carry raw accession, SEC URL, or local path text.",
            details={"field": field},
        )
    return text


def _controls(*, db_persistence_performed: bool) -> dict[str, bool]:
    return {
        "offline_storage_read_only": True,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "network_performed": False,
        "db_persistence_performed": db_persistence_performed,
        "value_reveal_performed": False,
        "api_route_enabled": False,
        "production_readiness_claimed": False,
    }
