from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.services.layer3_sec_xbrl_canonical_concepts import project_issuer_canonical_facts_by_periods
from app.services.layer3_sec_xbrl_offline_evidence_loader import (
    SecXbrlOfflineEvidenceLoaderError,
    inspect_sec_xbrl_offline_evidence_storage,
    load_sec_xbrl_offline_evidence_bundle,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_xbrl_report_leak_guard import reject_report_leaks_with_error


REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_offline_companyfacts_oracle_packet.v1"


def inspect_sec_xbrl_offline_companyfacts_oracle_packet(
    storage_dir: str | Path,
    *,
    companyfacts_path: str | Path | None = None,
    expected_sidecar_receipt_hash: str | None = None,
    expected_statement_classification_receipt_hash: str | None = None,
    period_limit: int = 2,
) -> dict[str, Any]:
    """Validate an operator-acquired CompanyFacts oracle packet without acquiring sources."""

    base_report = inspect_sec_xbrl_offline_evidence_storage(
        storage_dir,
        expected_sidecar_receipt_hash=expected_sidecar_receipt_hash,
        expected_statement_classification_receipt_hash=expected_statement_classification_receipt_hash,
    )
    if base_report.get("status") == "offline_evidence_bundle_blocked":
        blocked_reason = _first_blocked_reason(base_report)
        return _blocked_report(
            base_report=base_report,
            reason=blocked_reason["reason"],
            message=blocked_reason["message"],
            details=blocked_reason.get("details"),
        )
    if not companyfacts_path:
        return _blocked_report(
            base_report=base_report,
            reason="companyfacts_oracle_packet_missing",
            message="Offline CompanyFacts oracle JSON was not supplied.",
        )

    try:
        payload = _read_json_object(Path(companyfacts_path))
        companyfacts = _companyfacts_map(payload)
        bundle = load_sec_xbrl_offline_evidence_bundle(
            storage_dir,
            companyfacts_path=companyfacts_path,
            expected_sidecar_receipt_hash=expected_sidecar_receipt_hash,
            expected_statement_classification_receipt_hash=expected_statement_classification_receipt_hash,
        )
    except (SecXbrlOfflineEvidenceLoaderError, CompanyFactsOraclePacketError) as exc:
        return _blocked_report(
            base_report=base_report,
            reason=getattr(exc, "code", "companyfacts_oracle_packet_invalid"),
            message=str(exc),
            details=getattr(exc, "details", None),
        )

    evidence = bundle["evidence"]
    sidecar = evidence["sidecar_receipt"]
    value_store = evidence["value_store"]
    projection = project_issuer_canonical_facts_by_periods(
        companyfacts=companyfacts,
        sidecar_records=list(sidecar.get("resolved_fact_records") or []),
        value_records=list(value_store.get("value_records") or []),
        sidecar_receipt_id=str(sidecar.get("sidecar_receipt_id") or ""),
        sidecar_receipt_hash=str(sidecar.get("sidecar_receipt_hash") or ""),
        value_store_hash=str(value_store.get("value_store_hash") or ""),
        dataset_version_id=str(evidence.get("dataset_version_id") or ""),
        period_limit=period_limit,
    )
    projection_summary = _projection_summary(projection)
    companyfacts_summary = _companyfacts_summary(companyfacts)
    if projection.get("status") != "canonical_multi_period_projection_ready" or projection_summary["projected_count"] <= 0:
        return _blocked_report(
            base_report=base_report,
            authority_refs={**dict(bundle.get("authority_refs") or {}), "companyfacts_payload_hash": stable_hash(companyfacts)},
            summary={**dict(bundle.get("summary") or {}), **companyfacts_summary, **projection_summary},
            reason="companyfacts_oracle_packet_projection_not_ready",
            message="Offline CompanyFacts oracle did not produce a ready canonical projection.",
        )
    if companyfacts_summary["companyfacts_observation_count"] <= 0 or projection_summary["oracle_confirmed_count"] <= 0:
        return _blocked_report(
            base_report=base_report,
            authority_refs={**dict(bundle.get("authority_refs") or {}), "companyfacts_payload_hash": stable_hash(companyfacts)},
            summary={**dict(bundle.get("summary") or {}), **companyfacts_summary, **projection_summary},
            reason="companyfacts_oracle_packet_oracle_confirmation_missing",
            message="Offline CompanyFacts oracle did not confirm any projected facts.",
        )

    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "schema_version": 1,
        "status": "offline_companyfacts_oracle_packet_ready",
        "blocked_reasons": [],
        "paths_redacted": True,
        "storage_marker": base_report.get("storage_marker", ""),
        "authority_refs": {
            **dict(bundle.get("authority_refs") or {}),
            "companyfacts_payload_hash": stable_hash(companyfacts),
        },
        "summary": {
            **dict(bundle.get("summary") or {}),
            **companyfacts_summary,
            **projection_summary,
        },
        "readiness": {
            "companyfacts_oracle_packet_supplied": True,
            "operator_review_creation_ready": True,
            "production_admission_ready": False,
            "production_admission_blocked_reason": "diagnostic_validate_only_not_production_admission",
        },
        "controls": _controls(),
    }
    _reject_report_leaks(report)
    return report


class CompanyFactsOraclePacketError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _reject_report_leaks(value: Any) -> None:
    reject_report_leaks_with_error(
        value,
        error_type=CompanyFactsOraclePacketError,
        error_code="companyfacts_oracle_packet_report_redaction_failed",
        message="SEC XBRL CompanyFacts oracle packet report leaked raw authority references.",
    )


def _first_blocked_reason(base_report: Mapping[str, Any]) -> dict[str, Any]:
    reasons = base_report.get("blocked_reasons") if isinstance(base_report.get("blocked_reasons"), list) else []
    for item in reasons:
        if not isinstance(item, Mapping):
            continue
        reason = str(item.get("reason") or "").strip()
        message = str(item.get("message") or "").strip()
        if reason:
            blocked_reason: dict[str, Any] = {
                "reason": reason,
                "message": message or "Offline evidence storage is blocked.",
            }
            details = item.get("details")
            if isinstance(details, Mapping) and details:
                blocked_reason["details"] = dict(details)
            return blocked_reason
    return {"reason": "offline_evidence_bundle_blocked", "message": "Offline evidence storage is blocked."}


def _blocked_report(
    *,
    base_report: Mapping[str, Any],
    reason: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    authority_refs: Mapping[str, Any] | None = None,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    blocked_reason: dict[str, Any] = {"reason": reason, "message": message}
    if details:
        blocked_reason["details"] = dict(details)
    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "schema_version": 1,
        "status": "offline_companyfacts_oracle_packet_blocked",
        "blocked_reasons": [blocked_reason],
        "paths_redacted": True,
        "storage_marker": base_report.get("storage_marker", ""),
        "base_evidence_status": base_report.get("status", ""),
        "authority_refs": dict(authority_refs or base_report.get("authority_refs") or {}),
        "summary": dict(summary or base_report.get("summary") or {}),
        "readiness": {
            "companyfacts_oracle_packet_supplied": False,
            "operator_review_creation_ready": False,
            "operator_review_creation_blocked_reason": reason,
            "production_admission_ready": False,
            "production_admission_blocked_reason": reason,
        },
        "controls": _controls(),
    }
    _reject_report_leaks(report)
    return report


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise CompanyFactsOraclePacketError(
            "companyfacts_oracle_packet_json_missing",
            "Offline CompanyFacts oracle JSON file is missing.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise CompanyFactsOraclePacketError(
            "companyfacts_oracle_packet_json_invalid",
            "Offline CompanyFacts oracle JSON file is invalid.",
        ) from exc
    if not isinstance(payload, dict):
        raise CompanyFactsOraclePacketError(
            "companyfacts_oracle_packet_json_not_object",
            "Offline CompanyFacts oracle JSON must contain an object.",
        )
    return payload


def _companyfacts_map(payload: Mapping[str, Any]) -> dict[str, Any]:
    facts = payload.get("facts") if isinstance(payload.get("facts"), Mapping) else payload
    if not isinstance(facts, Mapping):
        raise CompanyFactsOraclePacketError(
            "companyfacts_oracle_packet_facts_missing",
            "Offline CompanyFacts oracle packet must contain a facts object.",
        )
    return dict(facts)


def _companyfacts_summary(companyfacts: Mapping[str, Any]) -> dict[str, int]:
    taxonomy_count = concept_count = unit_group_count = fact_observation_count = 0
    for concepts in companyfacts.values():
        if not isinstance(concepts, Mapping):
            continue
        taxonomy_count += 1
        for concept in concepts.values():
            if not isinstance(concept, Mapping):
                continue
            units = concept.get("units") if isinstance(concept.get("units"), Mapping) else {}
            concept_count += 1
            unit_group_count += len(units)
            for observations in units.values():
                if isinstance(observations, list):
                    fact_observation_count += len(observations)
    return {
        "companyfacts_taxonomy_count": taxonomy_count,
        "companyfacts_concept_count": concept_count,
        "companyfacts_unit_group_count": unit_group_count,
        "companyfacts_observation_count": fact_observation_count,
    }


def _projection_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    ready_periods = [item for item in projection.get("periods") or [] if isinstance(item, Mapping)]
    oracle_confirmed_count = 0
    for item in ready_periods:
        period_projection = item.get("projection") if isinstance(item.get("projection"), Mapping) else {}
        oracle_confirmed_count += int(period_projection.get("oracle_confirmed_count") or 0)
    return {
        "projection_status": str(projection.get("status") or ""),
        "projection_period_count": int(projection.get("period_count") or 0),
        "projection_ready_period_count": int(projection.get("ready_period_count") or 0),
        "projected_count": int(projection.get("projected_count") or 0),
        "oracle_confirmed_count": oracle_confirmed_count,
        "provenance_complete_count": int(projection.get("provenance_complete_count") or 0),
        "period_result_count": len(ready_periods),
        "projection_blocking_reasons": _projection_blocking_reasons(projection),
    }


def _projection_blocking_reasons(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    for item in projection.get("blocking_reasons") or []:
        if not isinstance(item, Mapping):
            continue
        entry: dict[str, Any] = {"reason": str(item.get("reason") or "canonical_projection_blocked")}
        if item.get("period_ref"):
            entry["period_ref"] = str(item.get("period_ref"))
        nested = item.get("blocking_reasons")
        if isinstance(nested, list):
            nested_reasons = [
                str(reason.get("reason") or "canonical_projection_blocked")
                for reason in nested
                if isinstance(reason, Mapping)
            ]
            entry["nested_reason_count"] = len(nested_reasons)
            entry["nested_reasons"] = nested_reasons
        reasons.append(entry)
    return reasons


def _controls() -> dict[str, bool]:
    return {
        "offline_storage_read_only": True,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "network_performed": False,
        "db_persistence_performed": False,
        "value_reveal_performed": False,
        "api_route_enabled": False,
        "production_readiness_claimed": False,
    }
