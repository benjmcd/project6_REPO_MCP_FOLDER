from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import nrc_aps_contract


APS_COMPARISON_CONTRACT_VERSION = "aps_comparison_basis_v1"
APS_PROJECTION_HASH_CONTRACT = "aps_projection_hash_v1"

APS_SYNC_DELTA_SCHEMA_ID = "aps.sync_delta.v1"
APS_SYNC_DRIFT_SCHEMA_ID = "aps.sync_drift.v1"
APS_SYNC_DRIFT_FAILURE_SCHEMA_ID = "aps.sync_drift_failure.v1"
APS_SYNC_ARTIFACT_SCHEMA_VERSION = 1

APS_SEVERITY_INFO = "info"
APS_SEVERITY_WARNING = "warning"
APS_SEVERITY_CRITICAL = "critical"
APS_SEVERITIES = {APS_SEVERITY_INFO, APS_SEVERITY_WARNING, APS_SEVERITY_CRITICAL}

APS_BASELINE_INCREMENTAL_STRICT = "incremental_prev_incremental"
APS_BASELINE_INCREMENTAL_FALLBACK = "incremental_fallback_prev_completed"
APS_BASELINE_RECON_STRICT = "reconciliation_prev_reconciliation"
APS_BASELINE_RECON_FALLBACK = "reconciliation_fallback_prev_completed"
APS_BASELINE_NO_BASELINE = "no_baseline"

APS_COMPARISON_STATUS_COMPARED = "compared"
APS_COMPARISON_STATUS_CURRENT_EMPTY = "current_empty"
APS_COMPARISON_STATUS_BASELINE_EMPTY = "baseline_empty"
APS_COMPARISON_STATUS_BOTH_EMPTY = "both_empty"
APS_COMPARISON_STATUS_WATERMARK_INCOMPARABLE = "watermark_incomparable"
APS_COMPARISON_STATUS_NO_BASELINE = "no_baseline"

APS_FINDING_ADDED = "added_identity_observed"
APS_FINDING_UPDATED = "updated_projection_observed"
APS_FINDING_INCREMENTAL_ABSENCE = "incremental_window_absence"
APS_FINDING_SCHEMA_SHIFT = "schema_variant_shift"
APS_FINDING_DIALECT_SHIFT = "dialect_shift"
APS_FINDING_RECON_REMOVED = "reconciliation_candidate_removed"
APS_FINDING_WATERMARK_NO_PROGRESS = "watermark_no_progress_with_hits"
APS_FINDING_WATERMARK_REGRESSION = "watermark_regression_confirmed"
APS_FINDING_MISSING_EVIDENCE = "missing_required_evidence"
APS_FINDING_ARTIFACT_PARTIAL = "artifact_generation_partial_corruption"
APS_FINDING_CURRENT_EMPTY_NON_EVIDENCE = "current_empty_non_evidence"
APS_FINDING_CURRENT_EMPTY_RECON = "current_empty_reconciliation_window"
APS_FINDING_BASELINE_EMPTY_INIT = "baseline_empty_initialization"
APS_FINDING_BOTH_EMPTY = "both_empty_no_change_evidence"
APS_FINDING_WATERMARK_MISSING = "watermark_missing_or_unparseable"

APS_PROJECTION_HASH_FIELDS = (
    "document_title",
    "document_type",
    "document_date",
    "date_added_timestamp",
    "url",
    "docket_number",
)


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _stable_hash(payload: dict[str, Any]) -> str:
    return nrc_aps_contract.stable_json_hash(payload)


def canonical_source_system(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"nrc_adams_aps", "nrc-adams-aps", "nrc_adams", "nrc"}:
        return "nrc_adams_aps"
    return raw


def is_metadata_compatible_run_mode(run_mode: Any) -> bool:
    normalized = str(run_mode or "").strip().lower()
    if not normalized:
        return False
    if normalized == "dry_run":
        return False
    return normalized.startswith("metadata")


def build_comparison_basis(
    *,
    connector_key: Any,
    source_system: Any,
    source_query_fingerprint: Any,
    run_mode: Any,
    comparison_contract_version: Any = None,
    projection_hash_contract: Any = None,
) -> dict[str, Any]:
    basis = {
        "connector_key": str(connector_key or "").strip(),
        "source_system": canonical_source_system(source_system),
        "source_query_fingerprint": str(source_query_fingerprint or "").strip(),
        "comparison_contract_version": str(comparison_contract_version or APS_COMPARISON_CONTRACT_VERSION).strip(),
        "projection_hash_contract": str(projection_hash_contract or APS_PROJECTION_HASH_CONTRACT).strip(),
        "run_mode": str(run_mode or "").strip().lower(),
    }
    basis["run_mode_metadata_compatible"] = is_metadata_compatible_run_mode(basis["run_mode"])
    return basis


def are_runs_comparable(current_basis: dict[str, Any], baseline_basis: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if str(current_basis.get("connector_key") or "") != "nrc_adams_aps":
        failures.append("current_connector_key_invalid")
    if str(baseline_basis.get("connector_key") or "") != "nrc_adams_aps":
        failures.append("baseline_connector_key_invalid")
    if str(current_basis.get("source_system") or "") != "nrc_adams_aps":
        failures.append("current_source_system_invalid")
    if str(baseline_basis.get("source_system") or "") != "nrc_adams_aps":
        failures.append("baseline_source_system_invalid")
    current_fp = str(current_basis.get("source_query_fingerprint") or "").strip()
    baseline_fp = str(baseline_basis.get("source_query_fingerprint") or "").strip()
    if not current_fp:
        failures.append("current_source_query_fingerprint_missing")
    if not baseline_fp:
        failures.append("baseline_source_query_fingerprint_missing")
    if current_fp and baseline_fp and current_fp != baseline_fp:
        failures.append("source_query_fingerprint_mismatch")
    if str(current_basis.get("comparison_contract_version") or "") != APS_COMPARISON_CONTRACT_VERSION:
        failures.append("current_comparison_contract_mismatch")
    if str(baseline_basis.get("comparison_contract_version") or "") != APS_COMPARISON_CONTRACT_VERSION:
        failures.append("baseline_comparison_contract_mismatch")
    if str(current_basis.get("projection_hash_contract") or "") != APS_PROJECTION_HASH_CONTRACT:
        failures.append("current_projection_hash_contract_mismatch")
    if str(baseline_basis.get("projection_hash_contract") or "") != APS_PROJECTION_HASH_CONTRACT:
        failures.append("baseline_projection_hash_contract_mismatch")
    if not bool(current_basis.get("run_mode_metadata_compatible")):
        failures.append("current_run_mode_not_metadata_compatible")
    if not bool(baseline_basis.get("run_mode_metadata_compatible")):
        failures.append("baseline_run_mode_not_metadata_compatible")
    return (len(failures) == 0, failures)


def _normalize_projection_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            normalized_item = _normalize_projection_value(item)
            if normalized_item is None:
                continue
            if isinstance(normalized_item, dict):
                values.append(_stable_json(normalized_item))
            elif isinstance(normalized_item, list):
                values.append(_stable_json({"v": normalized_item}))
            else:
                normalized_text = str(normalized_item).strip()
                if normalized_text:
                    values.append(normalized_text)
        deduped = sorted(list(dict.fromkeys(values)))
        return deduped or None
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key in sorted(value.keys()):
            normalized_item = _normalize_projection_value(value.get(key))
            if normalized_item is None:
                continue
            output[str(key)] = normalized_item
        return output or None
    return value


def projection_hash_input(projection: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in APS_PROJECTION_HASH_FIELDS:
        payload[field] = _normalize_projection_value(projection.get(field))
    return payload


def compute_projection_hash(projection: dict[str, Any]) -> str:
    return _stable_hash(projection_hash_input(projection))


def _safe_accession(target: dict[str, Any]) -> str:
    item_id = str(target.get("item_id") or "").strip()
    if item_id:
        return item_id
    artifact_key = str(target.get("source_artifact_key") or "").strip()
    if "::" in artifact_key:
        return artifact_key.rsplit("::", 1)[-1].strip()
    return ""


def build_projection_index(
    *,
    metadata_payloads: list[dict[str, Any]],
    metadata_refs: list[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, Any]]]:
    projection_hashes: dict[str, str] = {}
    projection_ref_by_accession: dict[str, str] = {}
    projection_input_by_accession: dict[str, dict[str, Any]] = {}
    for payload, ref in zip(metadata_payloads, metadata_refs):
        accession = str(payload.get("accession_number") or "").strip()
        if not accession:
            continue
        projection = {
            "document_title": payload.get("document_title"),
            "document_type": payload.get("document_type"),
            "document_date": payload.get("document_date"),
            "date_added_timestamp": payload.get("date_added_timestamp"),
            "url": payload.get("url"),
            "docket_number": payload.get("docket_number"),
        }
        projection_input = projection_hash_input(projection)
        projection_hashes[accession] = _stable_hash(projection_input)
        projection_ref_by_accession[accession] = str(ref)
        projection_input_by_accession[accession] = projection_input
    return projection_hashes, projection_ref_by_accession, projection_input_by_accession


def build_snapshot(
    *,
    run_id: str,
    connector_key: str,
    source_system: str,
    source_query_fingerprint: str,
    run_mode: str,
    sync_mode: str,
    comparison_contract_version: str,
    projection_hash_contract: str,
    discovery_ref: str | None,
    selection_ref: str | None,
    discovery_payload: dict[str, Any],
    selection_payload: dict[str, Any],
    projection_hashes: dict[str, str],
    projection_refs: dict[str, str],
    projection_inputs: dict[str, dict[str, Any]],
    max_observed_watermark: str | None,
    observed_schema_variants: dict[str, int],
    dialect_order: list[str],
) -> dict[str, Any]:
    targets = [dict(item or {}) for item in (selection_payload.get("targets") or []) if isinstance(item, dict)]
    accessions = [_safe_accession(target) for target in targets]
    accessions = sorted([item for item in accessions if item])
    search_refs = [str(item) for item in (discovery_payload.get("search_exchange_refs") or []) if str(item).strip()]
    accession_refs: dict[str, dict[str, str | None]] = {}
    for target in targets:
        accession = _safe_accession(target)
        if not accession:
            continue
        accession_refs[accession] = {
            "target_id": str(target.get("target_id") or "") or None,
            "target_ref": str(target.get("target_ref") or "") or None,
            "metadata_ref": projection_refs.get(accession),
        }
    basis = build_comparison_basis(
        connector_key=connector_key,
        source_system=source_system,
        source_query_fingerprint=source_query_fingerprint,
        run_mode=run_mode,
        comparison_contract_version=comparison_contract_version,
        projection_hash_contract=projection_hash_contract,
    )
    return {
        "run_id": run_id,
        "connector_key": connector_key,
        "source_system": canonical_source_system(source_system),
        "source_query_fingerprint": source_query_fingerprint,
        "run_mode": run_mode,
        "sync_mode": sync_mode,
        "comparison_contract_version": comparison_contract_version,
        "projection_hash_contract": projection_hash_contract,
        "comparison_basis": basis,
        "discovery_ref": discovery_ref,
        "selection_ref": selection_ref,
        "search_exchange_refs": search_refs,
        "accessions": accessions,
        "projection_hashes": {key: value for key, value in projection_hashes.items() if key in accessions},
        "projection_inputs": {key: value for key, value in projection_inputs.items() if key in accessions},
        "accession_refs": accession_refs,
        "max_observed_watermark": max_observed_watermark,
        "observed_schema_variants": {str(key): int(value) for key, value in dict(observed_schema_variants or {}).items()},
        "dialect_order": [str(item) for item in dialect_order if str(item).strip()],
    }


def _finding_id(payload: dict[str, Any]) -> str:
    seed = {
        "finding_class": payload.get("finding_class"),
        "run_id": payload.get("run_id"),
        "baseline_run_id": payload.get("baseline_run_id"),
        "accessions": payload.get("accessions", []),
        "sync_mode": payload.get("sync_mode"),
        "message": payload.get("message"),
    }
    return _stable_hash(seed)


def _parse_iso(value: Any) -> datetime | None:
    return nrc_aps_contract.parse_iso_datetime(value)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _accession_evidence(
    *,
    accessions: list[str],
    current_snapshot: dict[str, Any],
    baseline_snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_refs = dict(current_snapshot.get("accession_refs") or {})
    baseline_refs = dict(baseline_snapshot.get("accession_refs") or {}) if baseline_snapshot else {}
    for accession in accessions:
        rows.append(
            {
                "accession_number": accession,
                "current": current_refs.get(accession),
                "baseline": baseline_refs.get(accession),
            }
        )
    return rows


def _new_finding(
    *,
    finding_class: str,
    severity: str,
    message: str,
    current_snapshot: dict[str, Any],
    baseline_snapshot: dict[str, Any] | None,
    baseline_comparison: bool,
    accessions: list[str] | None = None,
    include_search_refs: bool = False,
) -> dict[str, Any]:
    accessions_list = sorted([str(item) for item in (accessions or []) if str(item).strip()])
    evidence: dict[str, Any] = {
        "current": {
            "discovery_ref": current_snapshot.get("discovery_ref"),
            "selection_ref": current_snapshot.get("selection_ref"),
        }
    }
    if include_search_refs:
        evidence["current"]["search_exchange_refs"] = list(current_snapshot.get("search_exchange_refs") or [])
    if baseline_comparison and baseline_snapshot is not None:
        evidence["baseline"] = {
            "run_id": baseline_snapshot.get("run_id"),
            "discovery_ref": baseline_snapshot.get("discovery_ref"),
            "selection_ref": baseline_snapshot.get("selection_ref"),
        }
        if include_search_refs:
            evidence["baseline"]["search_exchange_refs"] = list(baseline_snapshot.get("search_exchange_refs") or [])
    else:
        evidence["baseline"] = None
    if accessions_list:
        evidence["accession_refs"] = _accession_evidence(
            accessions=accessions_list,
            current_snapshot=current_snapshot,
            baseline_snapshot=baseline_snapshot,
        )
    payload = {
        "finding_id": "",
        "finding_class": finding_class,
        "severity": severity,
        "run_id": current_snapshot.get("run_id"),
        "baseline_run_id": (baseline_snapshot.get("run_id") if baseline_snapshot and baseline_comparison else None),
        "source_query_fingerprint": current_snapshot.get("source_query_fingerprint"),
        "sync_mode": current_snapshot.get("sync_mode"),
        "message": message,
        "accessions": accessions_list,
        "evidence": evidence,
    }
    payload["finding_id"] = _finding_id(payload)
    return payload


def _missing_required_evidence_finding(
    *,
    finding: dict[str, Any],
    reasons: list[str],
    current_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return _new_finding(
        finding_class=APS_FINDING_MISSING_EVIDENCE,
        severity=APS_SEVERITY_CRITICAL,
        message=f"finding_id={finding.get('finding_id')} missing evidence: {', '.join(reasons)}",
        current_snapshot=current_snapshot,
        baseline_snapshot=None,
        baseline_comparison=False,
        accessions=[str(finding.get("finding_id") or "")],
        include_search_refs=False,
    )


def _validate_finding_evidence(
    *,
    finding: dict[str, Any],
    current_snapshot: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    evidence = dict(finding.get("evidence") or {})
    current = dict(evidence.get("current") or {})
    if not str(current.get("discovery_ref") or "").strip():
        reasons.append("missing_current_discovery_ref")
    if not str(current.get("selection_ref") or "").strip():
        reasons.append("missing_current_selection_ref")

    baseline_classes = {
        APS_FINDING_UPDATED,
        APS_FINDING_INCREMENTAL_ABSENCE,
        APS_FINDING_RECON_REMOVED,
        APS_FINDING_SCHEMA_SHIFT,
        APS_FINDING_DIALECT_SHIFT,
        APS_FINDING_WATERMARK_NO_PROGRESS,
        APS_FINDING_WATERMARK_REGRESSION,
    }
    finding_class = str(finding.get("finding_class") or "")
    if finding_class in baseline_classes:
        if not str(finding.get("baseline_run_id") or "").strip():
            reasons.append("missing_baseline_run_id")
        baseline = dict(evidence.get("baseline") or {})
        if not str(baseline.get("discovery_ref") or "").strip():
            reasons.append("missing_baseline_discovery_ref")
        if not str(baseline.get("selection_ref") or "").strip():
            reasons.append("missing_baseline_selection_ref")

    accession_classes = {
        APS_FINDING_ADDED,
        APS_FINDING_UPDATED,
        APS_FINDING_INCREMENTAL_ABSENCE,
        APS_FINDING_RECON_REMOVED,
    }
    if finding_class in accession_classes:
        accessions = [str(item) for item in (finding.get("accessions") or []) if str(item).strip()]
        if not accessions:
            reasons.append("missing_accessions")
        accession_refs = [dict(item or {}) for item in (evidence.get("accession_refs") or []) if isinstance(item, dict)]
        refs_by_accession = {str(item.get("accession_number") or "").strip(): item for item in accession_refs}
        for accession in accessions:
            row = refs_by_accession.get(accession, {})
            current_ref = dict(row.get("current") or {})
            baseline_ref = dict(row.get("baseline") or {})
            has_ref = bool(
                str(current_ref.get("metadata_ref") or current_ref.get("target_ref") or "").strip()
                or str(baseline_ref.get("metadata_ref") or baseline_ref.get("target_ref") or "").strip()
            )
            if not has_ref:
                reasons.append(f"missing_accession_ref:{accession}")

    search_ref_classes = {
        APS_FINDING_SCHEMA_SHIFT,
        APS_FINDING_DIALECT_SHIFT,
        APS_FINDING_WATERMARK_MISSING,
        APS_FINDING_WATERMARK_NO_PROGRESS,
        APS_FINDING_WATERMARK_REGRESSION,
    }
    if finding_class in search_ref_classes:
        current_refs = [str(item) for item in (current.get("search_exchange_refs") or []) if str(item).strip()]
        if not current_refs:
            reasons.append("missing_current_search_exchange_ref")
        if finding_class in baseline_classes:
            baseline = dict(evidence.get("baseline") or {})
            baseline_refs = [str(item) for item in (baseline.get("search_exchange_refs") or []) if str(item).strip()]
            if not baseline_refs:
                reasons.append("missing_baseline_search_exchange_ref")
    return reasons


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {APS_SEVERITY_INFO: 0, APS_SEVERITY_WARNING: 0, APS_SEVERITY_CRITICAL: 0}
    for finding in findings:
        severity = str(finding.get("severity") or "")
        if severity in counts:
            counts[severity] = int(counts.get(severity, 0)) + 1
    return counts


def build_delta_and_drift_artifacts(
    *,
    current_snapshot: dict[str, Any],
    baseline_snapshot: dict[str, Any] | None,
    baseline_resolution: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current_accessions = sorted([str(item) for item in (current_snapshot.get("accessions") or []) if str(item).strip()])
    baseline_accessions = sorted([str(item) for item in (baseline_snapshot.get("accessions") or []) if str(item).strip()]) if baseline_snapshot else []
    current_set = set(current_accessions)
    baseline_set = set(baseline_accessions)

    overlap = sorted(list(current_set & baseline_set))
    added = sorted(list(current_set - baseline_set))
    baseline_only = sorted(list(baseline_set - current_set))

    current_hashes = dict(current_snapshot.get("projection_hashes") or {})
    baseline_hashes = dict(baseline_snapshot.get("projection_hashes") or {}) if baseline_snapshot else {}

    updated: list[str] = []
    unchanged: list[str] = []
    hash_unavailable: list[str] = []
    for accession in overlap:
        current_hash = str(current_hashes.get(accession) or "").strip()
        baseline_hash = str(baseline_hashes.get(accession) or "").strip()
        if current_hash and baseline_hash:
            if current_hash == baseline_hash:
                unchanged.append(accession)
            else:
                updated.append(accession)
        else:
            hash_unavailable.append(accession)

    sync_mode = str(current_snapshot.get("sync_mode") or "").strip().lower()
    if baseline_snapshot is None:
        comparison_status = APS_COMPARISON_STATUS_NO_BASELINE
    elif len(current_accessions) == 0 and len(baseline_accessions) > 0:
        comparison_status = APS_COMPARISON_STATUS_CURRENT_EMPTY
    elif len(current_accessions) > 0 and len(baseline_accessions) == 0:
        comparison_status = APS_COMPARISON_STATUS_BASELINE_EMPTY
    elif len(current_accessions) == 0 and len(baseline_accessions) == 0:
        comparison_status = APS_COMPARISON_STATUS_BOTH_EMPTY
    else:
        comparison_status = APS_COMPARISON_STATUS_COMPARED

    current_watermark_raw = current_snapshot.get("max_observed_watermark")
    baseline_watermark_raw = baseline_snapshot.get("max_observed_watermark") if baseline_snapshot else None
    current_watermark = _parse_iso(current_watermark_raw)
    baseline_watermark = _parse_iso(baseline_watermark_raw)
    watermark_comparable = bool(current_watermark and baseline_watermark)
    watermark_regression = bool(
        baseline_snapshot
        and watermark_comparable
        and len(current_accessions) > 0
        and current_watermark is not None
        and baseline_watermark is not None
        and current_watermark < baseline_watermark
    )
    if (
        baseline_snapshot is not None
        and comparison_status == APS_COMPARISON_STATUS_COMPARED
        and not watermark_comparable
    ):
        comparison_status = APS_COMPARISON_STATUS_WATERMARK_INCOMPARABLE

    findings: list[dict[str, Any]] = []
    if baseline_snapshot is None:
        # Explicit no-baseline status is carried by artifact fields.
        pass
    elif comparison_status == APS_COMPARISON_STATUS_CURRENT_EMPTY:
        if sync_mode == "reconciliation":
            findings.append(
                _new_finding(
                    finding_class=APS_FINDING_CURRENT_EMPTY_RECON,
                    severity=APS_SEVERITY_WARNING,
                    message="Current reconciliation run returned no hits against non-empty baseline window.",
                    current_snapshot=current_snapshot,
                    baseline_snapshot=baseline_snapshot,
                    baseline_comparison=True,
                    include_search_refs=True,
                )
            )
        else:
            findings.append(
                _new_finding(
                    finding_class=APS_FINDING_CURRENT_EMPTY_NON_EVIDENCE,
                    severity=APS_SEVERITY_INFO,
                    message="Current incremental window returned no hits; treated as non-evidence for removals.",
                    current_snapshot=current_snapshot,
                    baseline_snapshot=baseline_snapshot,
                    baseline_comparison=True,
                    include_search_refs=True,
                )
            )
    elif comparison_status == APS_COMPARISON_STATUS_BASELINE_EMPTY:
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_BASELINE_EMPTY_INIT,
                severity=APS_SEVERITY_INFO,
                message="Baseline run had zero hits; current identities treated as initialization/additions.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=True,
                include_search_refs=True,
            )
        )
    elif comparison_status == APS_COMPARISON_STATUS_BOTH_EMPTY:
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_BOTH_EMPTY,
                severity=APS_SEVERITY_INFO,
                message="Current and baseline runs both had zero hits.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=True,
                include_search_refs=True,
            )
        )

    if added:
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_ADDED,
                severity=APS_SEVERITY_INFO,
                message=f"Observed {len(added)} added accession identities.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=False,
                accessions=added,
                include_search_refs=False,
            )
        )
    if updated:
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_UPDATED,
                severity=APS_SEVERITY_INFO,
                message=f"Observed {len(updated)} projection updates for overlapping identities.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=baseline_snapshot is not None,
                accessions=updated,
                include_search_refs=False,
            )
        )
    if baseline_only:
        if sync_mode == "reconciliation":
            findings.append(
                _new_finding(
                    finding_class=APS_FINDING_RECON_REMOVED,
                    severity=APS_SEVERITY_WARNING,
                    message=f"Observed {len(baseline_only)} baseline identities absent from reconciliation window.",
                    current_snapshot=current_snapshot,
                    baseline_snapshot=baseline_snapshot,
                    baseline_comparison=True,
                    accessions=baseline_only,
                    include_search_refs=False,
                )
            )
        else:
            findings.append(
                _new_finding(
                    finding_class=APS_FINDING_INCREMENTAL_ABSENCE,
                    severity=APS_SEVERITY_INFO,
                    message=f"Observed {len(baseline_only)} baseline identities absent from incremental window.",
                    current_snapshot=current_snapshot,
                    baseline_snapshot=baseline_snapshot,
                    baseline_comparison=True,
                    accessions=baseline_only,
                    include_search_refs=False,
                )
            )

    if baseline_snapshot is not None:
        current_schema = sorted(list((current_snapshot.get("observed_schema_variants") or {}).keys()))
        baseline_schema = sorted(list((baseline_snapshot.get("observed_schema_variants") or {}).keys()))
        if current_schema != baseline_schema:
            findings.append(
                _new_finding(
                    finding_class=APS_FINDING_SCHEMA_SHIFT,
                    severity=APS_SEVERITY_WARNING,
                    message="Observed schema variant set changed versus baseline.",
                    current_snapshot=current_snapshot,
                    baseline_snapshot=baseline_snapshot,
                    baseline_comparison=True,
                    include_search_refs=True,
                )
            )
        current_dialect = [str(item) for item in (current_snapshot.get("dialect_order") or []) if str(item).strip()]
        baseline_dialect = [str(item) for item in (baseline_snapshot.get("dialect_order") or []) if str(item).strip()]
        if current_dialect != baseline_dialect:
            findings.append(
                _new_finding(
                    finding_class=APS_FINDING_DIALECT_SHIFT,
                    severity=APS_SEVERITY_WARNING,
                    message="Observed dialect preference order changed versus baseline.",
                    current_snapshot=current_snapshot,
                    baseline_snapshot=baseline_snapshot,
                    baseline_comparison=True,
                    include_search_refs=True,
                )
            )

    if baseline_snapshot is not None and not watermark_comparable:
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_WATERMARK_MISSING,
                severity=APS_SEVERITY_WARNING,
                message="Watermark missing or unparseable; regression check suppressed.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=True,
                include_search_refs=True,
            )
        )
    elif watermark_regression:
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_WATERMARK_REGRESSION,
                severity=APS_SEVERITY_CRITICAL,
                message="Current watermark regressed below comparable baseline watermark.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=True,
                include_search_refs=True,
            )
        )
    elif (
        baseline_snapshot is not None
        and watermark_comparable
        and current_watermark is not None
        and baseline_watermark is not None
        and len(current_accessions) > 0
        and current_watermark == baseline_watermark
    ):
        findings.append(
            _new_finding(
                finding_class=APS_FINDING_WATERMARK_NO_PROGRESS,
                severity=APS_SEVERITY_WARNING,
                message="Current run had hits but watermark did not advance relative to baseline.",
                current_snapshot=current_snapshot,
                baseline_snapshot=baseline_snapshot,
                baseline_comparison=True,
                include_search_refs=True,
            )
        )

    evidence_errors: list[dict[str, Any]] = []
    for finding in findings:
        missing = _validate_finding_evidence(finding=finding, current_snapshot=current_snapshot)
        if missing:
            evidence_errors.append(
                _missing_required_evidence_finding(
                    finding=finding,
                    reasons=missing,
                    current_snapshot=current_snapshot,
                )
            )
    if evidence_errors:
        findings.extend(evidence_errors)

    delta_artifact = {
        "schema_id": APS_SYNC_DELTA_SCHEMA_ID,
        "schema_version": APS_SYNC_ARTIFACT_SCHEMA_VERSION,
        "comparison_contract_version": APS_COMPARISON_CONTRACT_VERSION,
        "projection_hash_contract": APS_PROJECTION_HASH_CONTRACT,
        "run_id": current_snapshot.get("run_id"),
        "baseline_run_id": (baseline_snapshot.get("run_id") if baseline_snapshot else None),
        "baseline_resolution": baseline_resolution,
        "comparison_status": comparison_status,
        "source_query_fingerprint": current_snapshot.get("source_query_fingerprint"),
        "sync_mode": sync_mode,
        "counts": {
            "current": len(current_accessions),
            "baseline": len(baseline_accessions),
            "overlap": len(overlap),
            "added": len(added),
            "updated": len(updated),
            "unchanged": len(unchanged),
            "baseline_only": len(baseline_only),
            "hash_unavailable": len(hash_unavailable),
        },
        "watermark": {
            "current_max_observed": _iso_utc(current_watermark) if current_watermark else current_watermark_raw,
            "baseline_max_observed": _iso_utc(baseline_watermark) if baseline_watermark else baseline_watermark_raw,
            "comparable": watermark_comparable,
            "regression": watermark_regression,
        },
        "identity_sets": {
            "added": added,
            "updated": updated,
            "unchanged": unchanged,
            "baseline_only": baseline_only,
            "overlap": overlap,
            "hash_unavailable": hash_unavailable,
        },
        "hashes": {
            "current_identity_hash": _stable_hash({"ids": current_accessions}),
            "baseline_identity_hash": _stable_hash({"ids": baseline_accessions}),
            "delta_identity_hash": _stable_hash({"added": added, "updated": updated, "baseline_only": baseline_only}),
        },
        "evidence_refs": {
            "current": {
                "discovery_ref": current_snapshot.get("discovery_ref"),
                "selection_ref": current_snapshot.get("selection_ref"),
            },
            "baseline": (
                {
                    "run_id": baseline_snapshot.get("run_id"),
                    "discovery_ref": baseline_snapshot.get("discovery_ref"),
                    "selection_ref": baseline_snapshot.get("selection_ref"),
                }
                if baseline_snapshot
                else None
            ),
        },
    }

    drift_artifact = {
        "schema_id": APS_SYNC_DRIFT_SCHEMA_ID,
        "schema_version": APS_SYNC_ARTIFACT_SCHEMA_VERSION,
        "comparison_contract_version": APS_COMPARISON_CONTRACT_VERSION,
        "projection_hash_contract": APS_PROJECTION_HASH_CONTRACT,
        "run_id": current_snapshot.get("run_id"),
        "baseline_run_id": (baseline_snapshot.get("run_id") if baseline_snapshot else None),
        "baseline_resolution": baseline_resolution,
        "comparison_status": comparison_status,
        "source_query_fingerprint": current_snapshot.get("source_query_fingerprint"),
        "sync_mode": sync_mode,
        "finding_counts": _severity_counts(findings),
        "findings": findings,
    }
    return delta_artifact, drift_artifact


def build_failure_artifact(
    *,
    run_id: str,
    source_query_fingerprint: str,
    sync_mode: str,
    error_class: str,
    error_message: str,
) -> dict[str, Any]:
    return {
        "schema_id": APS_SYNC_DRIFT_FAILURE_SCHEMA_ID,
        "schema_version": APS_SYNC_ARTIFACT_SCHEMA_VERSION,
        "comparison_contract_version": APS_COMPARISON_CONTRACT_VERSION,
        "projection_hash_contract": APS_PROJECTION_HASH_CONTRACT,
        "run_id": run_id,
        "source_query_fingerprint": source_query_fingerprint,
        "sync_mode": sync_mode,
        "error_class": str(error_class or APS_FINDING_ARTIFACT_PARTIAL),
        "error_message": str(error_message or ""),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def artifact_paths(*, run_id: str, reports_dir: str | Path) -> dict[str, str]:
    base = Path(reports_dir)
    return {
        "aps_sync_delta": str(base / f"{run_id}_aps_sync_delta_v1.json"),
        "aps_sync_drift": str(base / f"{run_id}_aps_sync_drift_v1.json"),
        "aps_sync_drift_failure": str(base / f"{run_id}_aps_sync_drift_failure_v1.json"),
    }


def write_json_deterministic(path: str | Path, payload: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return str(target)


def read_json_object(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def collect_metadata_payloads(*, run_id: str, manifests_dir: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    base = Path(manifests_dir)
    payloads: list[dict[str, Any]] = []
    refs: list[str] = []
    for path in sorted(base.glob(f"{run_id}_*_aps_metadata.json"), key=lambda item: item.name):
        payload = read_json_object(path)
        if not payload:
            continue
        payloads.append(payload)
        refs.append(str(path))
    return payloads, refs


def validate_sync_drift_artifact_presence(
    *,
    run_rows: list[dict[str, Any]],
    reports_dir: str | Path,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        paths = artifact_paths(run_id=run_id, reports_dir=reports_dir)
        delta_exists = Path(paths["aps_sync_delta"]).exists()
        drift_exists = Path(paths["aps_sync_drift"]).exists()
        failure_exists = Path(paths["aps_sync_drift_failure"]).exists()
        success_exists = bool(delta_exists and drift_exists)
        passed = success_exists
        reasons: list[str] = []
        if not success_exists and failure_exists:
            reasons.append("failure_artifact_without_success")
        if not success_exists and not failure_exists:
            reasons.append("no_success_or_failure_artifact")
        if not delta_exists:
            reasons.append("missing_delta_artifact")
        if not drift_exists:
            reasons.append("missing_drift_artifact")
        checks.append(
            {
                "run_id": run_id,
                "passed": passed,
                "reasons": reasons,
                "paths": paths,
                "success_exists": success_exists,
                "delta_exists": delta_exists,
                "drift_exists": drift_exists,
                "failure_exists": failure_exists,
            }
        )
    overall_passed = all(bool(item.get("passed")) for item in checks)
    return {
        "schema_id": "aps.sync_drift_validation.v1",
        "schema_version": 1,
        "passed": overall_passed,
        "checked_runs": len(checks),
        "failed_runs": len([item for item in checks if not bool(item.get("passed"))]),
        "checks": checks,
    }
