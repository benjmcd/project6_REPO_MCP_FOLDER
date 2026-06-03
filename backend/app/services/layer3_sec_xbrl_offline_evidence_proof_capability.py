from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlProjectionFact,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketRow,
    L3SecXbrlStatementPacketSet,
)
from app.services.layer3_sec_xbrl_e2e_offline_orchestrator import (
    SecXbrlE2EOfflineOrchestratorError,
    open_redacted_operator_review_from_offline_evidence,
)
from app.services.layer3_sec_xbrl_offline_companyfacts_oracle_packet import (
    inspect_sec_xbrl_offline_companyfacts_oracle_packet,
)
from app.services.layer3_sec_xbrl_offline_evidence_loader import (
    SecXbrlOfflineEvidenceLoaderError,
    inspect_sec_xbrl_offline_evidence_storage,
    load_sec_xbrl_offline_evidence_bundle,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_xbrl_report_leak_guard import reject_report_leaks


REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_offline_evidence_proof_capability.v1"

ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:[\\/]|\\\\|file://|/(?:Users|home|tmp|workspace|var|mnt|private)(?:/|$)")
RAW_VALUE_KEY_RE = re.compile(r'"(?:effective_value|raw_value|lexical_value)"')
_reject_report_leaks = partial(
    reject_report_leaks,
    exception_factory=lambda: ValueError(
        "SEC XBRL offline evidence proof report leaked raw authority or value references."
    ),
    include_raw_value_keys=True,
)


def inspect_sec_xbrl_offline_evidence_proof_capability(
    storage_dir: str | Path | None = None,
    *,
    companyfacts_path: str | Path | None = None,
    expected_sidecar_receipt_hash: str | None = None,
    expected_statement_classification_receipt_hash: str | None = None,
    period_limit: int = 2,
) -> dict[str, Any]:
    """Prove offline SEC XBRL evidence can open a redacted review workflow.

    This diagnostic is intentionally operator-supplied-input driven. The
    committed no-argument path fails closed instead of implying that repo-bundled
    evidence is present.
    """

    if not storage_dir:
        return _blocked_report(
            reason="offline_evidence_proof_operator_storage_missing",
            message="Operator-supplied governed offline storage was not supplied.",
            loader_status="not_run",
            oracle_status="not_run",
        )

    loader_report = inspect_sec_xbrl_offline_evidence_storage(
        Path(storage_dir),
        companyfacts_path=Path(companyfacts_path) if companyfacts_path else None,
        expected_sidecar_receipt_hash=expected_sidecar_receipt_hash,
        expected_statement_classification_receipt_hash=expected_statement_classification_receipt_hash,
    )
    if loader_report.get("status") == "offline_evidence_bundle_blocked":
        return _blocked_report(
            reason=_first_reason(loader_report, "offline_evidence_bundle_blocked"),
            message=_first_message(loader_report, "Offline evidence storage is blocked."),
            details=_first_details(loader_report),
            loader_status=str(loader_report.get("status") or ""),
            oracle_status="not_run",
            storage_marker=str(loader_report.get("storage_marker") or ""),
            authority_refs=_mapping_or_empty(loader_report.get("authority_refs")),
            operator_evidence_files_read=True,
        )

    oracle_report = inspect_sec_xbrl_offline_companyfacts_oracle_packet(
        Path(storage_dir),
        companyfacts_path=Path(companyfacts_path) if companyfacts_path else None,
        expected_sidecar_receipt_hash=expected_sidecar_receipt_hash,
        expected_statement_classification_receipt_hash=expected_statement_classification_receipt_hash,
        period_limit=period_limit,
    )
    proof_source_hash = _proof_source_report_hash(
        loader_report=loader_report,
        oracle_report=oracle_report,
        period_limit=period_limit,
    )
    if oracle_report.get("status") != "offline_companyfacts_oracle_packet_ready":
        return _blocked_report(
            reason=_first_reason(oracle_report, "offline_companyfacts_oracle_packet_blocked"),
            message=_first_message(oracle_report, "Offline CompanyFacts oracle packet is blocked."),
            details=_first_details(oracle_report),
            loader_status=str(loader_report.get("status") or ""),
            oracle_status=str(oracle_report.get("status") or ""),
            storage_marker=str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            authority_refs=_proof_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
                proof_source_hash=proof_source_hash,
            ),
            loader_summary=_mapping_or_empty(loader_report.get("summary")),
            oracle_summary=_mapping_or_empty(oracle_report.get("summary")),
            operator_evidence_files_read=True,
        )

    try:
        bundle = load_sec_xbrl_offline_evidence_bundle(
            Path(storage_dir),
            companyfacts_path=Path(companyfacts_path) if companyfacts_path else None,
            expected_sidecar_receipt_hash=expected_sidecar_receipt_hash,
            expected_statement_classification_receipt_hash=expected_statement_classification_receipt_hash,
        )
        isolated = _run_isolated_orchestrator(
            evidence=_mapping_or_empty(bundle.get("evidence")),
            source_report_hash=proof_source_hash,
            period_limit=period_limit,
        )
    except (SecXbrlOfflineEvidenceLoaderError, SecXbrlE2EOfflineOrchestratorError) as exc:
        return _blocked_report(
            reason=getattr(exc, "code", "offline_evidence_proof_orchestrator_blocked"),
            message=str(exc),
            details=getattr(exc, "details", None),
            loader_status=str(loader_report.get("status") or ""),
            oracle_status=str(oracle_report.get("status") or ""),
            storage_marker=str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            authority_refs=_proof_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
                proof_source_hash=proof_source_hash,
            ),
            loader_summary=_mapping_or_empty(loader_report.get("summary")),
            oracle_summary=_mapping_or_empty(oracle_report.get("summary")),
            operator_evidence_files_read=True,
        )

    isolated_response = _mapping_or_empty(isolated.get("response"))
    redaction_scan = dict(isolated["redaction_scan"])
    source_hash_issue = _source_hash_binding_block_reason(isolated_response, proof_source_hash)
    if source_hash_issue:
        return _blocked_report(
            reason=source_hash_issue["reason"],
            message=source_hash_issue["message"],
            details=source_hash_issue["details"],
            loader_status=str(loader_report.get("status") or ""),
            oracle_status=str(oracle_report.get("status") or ""),
            storage_marker=str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            authority_refs=_proof_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
                proof_source_hash=proof_source_hash,
            ),
            loader_summary=_mapping_or_empty(loader_report.get("summary")),
            oracle_summary=_mapping_or_empty(oracle_report.get("summary")),
            redaction_scan=redaction_scan,
            isolated_persistence_counts=_mapping_or_empty(isolated.get("persisted_counts")),
            operator_evidence_files_read=True,
        )
    redaction_issue = _redaction_block_reason(redaction_scan)
    if redaction_issue:
        return _blocked_report(
            reason=redaction_issue["reason"],
            message=redaction_issue["message"],
            details=redaction_issue["details"],
            loader_status=str(loader_report.get("status") or ""),
            oracle_status=str(oracle_report.get("status") or ""),
            storage_marker=str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            authority_refs=_proof_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
                proof_source_hash=proof_source_hash,
            ),
            loader_summary=_mapping_or_empty(loader_report.get("summary")),
            oracle_summary=_mapping_or_empty(oracle_report.get("summary")),
            redaction_scan=redaction_scan,
            isolated_persistence_counts=_mapping_or_empty(isolated.get("persisted_counts")),
            operator_evidence_files_read=True,
        )
    persistence_issue = _isolated_persistence_block_reason(_mapping_or_empty(isolated.get("persisted_counts")))
    if persistence_issue:
        return _blocked_report(
            reason=persistence_issue["reason"],
            message=persistence_issue["message"],
            details=persistence_issue["details"],
            loader_status=str(loader_report.get("status") or ""),
            oracle_status=str(oracle_report.get("status") or ""),
            storage_marker=str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            authority_refs=_proof_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
                proof_source_hash=proof_source_hash,
            ),
            loader_summary=_mapping_or_empty(loader_report.get("summary")),
            oracle_summary=_mapping_or_empty(oracle_report.get("summary")),
            redaction_scan=redaction_scan,
            isolated_persistence_counts=_mapping_or_empty(isolated.get("persisted_counts")),
            operator_evidence_files_read=True,
        )
    transaction_issue = _single_transaction_block_reason(isolated_response)
    if transaction_issue:
        return _blocked_report(
            reason=transaction_issue["reason"],
            message=transaction_issue["message"],
            details=transaction_issue["details"],
            loader_status=str(loader_report.get("status") or ""),
            oracle_status=str(oracle_report.get("status") or ""),
            storage_marker=str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            authority_refs=_proof_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
                proof_source_hash=proof_source_hash,
            ),
            loader_summary=_mapping_or_empty(loader_report.get("summary")),
            oracle_summary=_mapping_or_empty(oracle_report.get("summary")),
            redaction_scan=redaction_scan,
            isolated_persistence_counts=_mapping_or_empty(isolated.get("persisted_counts")),
            operator_evidence_files_read=True,
        )
    proof_result_hash = _proof_result_hash(
        proof_source_hash=proof_source_hash,
        isolated_response=isolated_response,
        isolated_persistence_counts=_mapping_or_empty(isolated.get("persisted_counts")),
        redaction_scan=redaction_scan,
    )
    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "schema_version": 1,
        "status": "offline_evidence_proof_capability_ready",
        "blocked_reasons": [],
        "paths_redacted": True,
        "storage_marker": str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
        "authority_refs": _proof_authority_refs(
            loader_report=loader_report,
            oracle_report=oracle_report,
            proof_source_hash=proof_source_hash,
            proof_result_hash=proof_result_hash,
        ),
        "summary": {
            "loader_status": str(loader_report.get("status") or ""),
            "oracle_status": str(oracle_report.get("status") or ""),
            "orchestrator_status": str(isolated_response.get("status") or ""),
            "proof_source_report_hash_bound": True,
            **_prefixed_counts("loader", _mapping_or_empty(loader_report.get("summary"))),
            **_prefixed_counts("oracle", _mapping_or_empty(oracle_report.get("summary"))),
            **_prefixed_counts("orchestrator", _mapping_or_empty(isolated_response.get("summary"))),
            **_prefixed_counts("isolated_persistence", _mapping_or_empty(isolated.get("persisted_counts"))),
        },
        "readiness": {
            "operator_review_creation_ready": isolated_response.get("status") == "review_ready",
            "production_admission_ready": False,
            "production_admission_blocked_reason": "diagnostic_validate_only_not_production_admission",
        },
        "containment": {
            **_mapping_or_empty(isolated_response.get("containment")),
            "isolated_in_memory_db_used": True,
            "production_database_touched": False,
        },
        "controls": _controls(
            operator_evidence_files_read=True,
            isolated_db_persistence_performed=True,
        ),
        "proof_artifact_policy": _proof_artifact_policy(),
        "redaction_scan": redaction_scan,
    }
    _reject_report_leaks(report)
    return report


def blocked_sec_xbrl_offline_evidence_proof_capability_report(
    *,
    reason: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    operator_evidence_files_read: bool = False,
) -> dict[str, Any]:
    return _blocked_report(
        reason=reason,
        message=message,
        details=details,
        loader_status="not_run",
        oracle_status="not_run",
        operator_evidence_files_read=operator_evidence_files_read,
    )


def _run_isolated_orchestrator(
    *,
    evidence: Mapping[str, Any],
    source_report_hash: str,
    period_limit: int,
) -> dict[str, Any]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = Session()
    try:
        response = open_redacted_operator_review_from_offline_evidence(
            db,
            client_request_id="offline-evidence-proof-capability",
            evidence=evidence,
            source_report_hash=source_report_hash or None,
            period_limit=period_limit,
            single_transaction=True,
        )
        projection_facts = db.query(L3SecXbrlProjectionFact).all()
        packet_rows = db.query(L3SecXbrlStatementPacketRow).all()
        response_text = json.dumps(response, sort_keys=True)
        return {
            "response": response,
            "persisted_counts": {
                "projection_set_count": db.query(L3SecXbrlProjectionSet).count(),
                "projection_fact_count": len(projection_facts),
                "statement_packet_set_count": db.query(L3SecXbrlStatementPacketSet).count(),
                "statement_packet_row_count": len(packet_rows),
                "operator_review_workflow_count": db.query(L3SecXbrlOperatorReviewWorkflow).count(),
            },
            "redaction_scan": {
                "public_response_raw_accession_found": bool(ACCESSION_RE.search(response_text)),
                "public_response_sec_url_found": bool(SEC_URL_RE.search(response_text)),
                "public_response_local_path_found": bool(LOCAL_PATH_RE.search(response_text)),
                "public_response_raw_value_key_found": bool(RAW_VALUE_KEY_RE.search(response_text)),
                "projection_facts_all_value_redacted": all(row.value_redacted is True for row in projection_facts),
                "statement_rows_all_value_redacted": all(row.value_redacted is True for row in packet_rows),
            },
        }
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _blocked_report(
    *,
    reason: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    loader_status: str,
    oracle_status: str,
    storage_marker: str = "",
    authority_refs: Mapping[str, Any] | None = None,
    loader_summary: Mapping[str, Any] | None = None,
    oracle_summary: Mapping[str, Any] | None = None,
    redaction_scan: Mapping[str, Any] | None = None,
    isolated_persistence_counts: Mapping[str, Any] | None = None,
    operator_evidence_files_read: bool = False,
) -> dict[str, Any]:
    blocked_reason: dict[str, Any] = {"reason": reason, "message": message}
    if details:
        blocked_reason["details"] = dict(details)
    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "schema_version": 1,
        "status": "offline_evidence_proof_capability_blocked",
        "blocked_reasons": [blocked_reason],
        "paths_redacted": True,
        "storage_marker": storage_marker,
        "authority_refs": dict(authority_refs or {}),
        "summary": {
            "loader_status": loader_status,
            "oracle_status": oracle_status,
            **_prefixed_counts("loader", _mapping_or_empty(loader_summary)),
            **_prefixed_counts("oracle", _mapping_or_empty(oracle_summary)),
            **_prefixed_counts("isolated_persistence", _mapping_or_empty(isolated_persistence_counts)),
        },
        "readiness": {
            "operator_review_creation_ready": False,
            "operator_review_creation_blocked_reason": reason,
            "production_admission_ready": False,
            "production_admission_blocked_reason": reason,
        },
        "containment": {
            "isolated_in_memory_db_used": False,
            "production_database_touched": False,
            "single_transaction_claimed": False,
        },
        "controls": _controls(
            operator_evidence_files_read=operator_evidence_files_read,
            isolated_db_persistence_performed=False,
        ),
        "proof_artifact_policy": _proof_artifact_policy(),
        "redaction_scan": dict(redaction_scan or {
            "public_response_raw_accession_found": False,
            "public_response_sec_url_found": False,
            "public_response_local_path_found": False,
            "public_response_raw_value_key_found": False,
            "projection_facts_all_value_redacted": False,
            "statement_rows_all_value_redacted": False,
        }),
    }
    _reject_report_leaks(report)
    return report


def _controls(
    *,
    operator_evidence_files_read: bool,
    isolated_db_persistence_performed: bool,
) -> dict[str, bool]:
    return {
        "operator_evidence_files_read": operator_evidence_files_read,
        "offline_storage_read_only": True,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "network_performed": False,
        "isolated_db_persistence_performed": isolated_db_persistence_performed,
        "production_db_persistence_performed": False,
        "value_reveal_performed": False,
        "api_route_enabled": False,
        "production_readiness_claimed": False,
    }


def _proof_artifact_policy() -> dict[str, bool]:
    return {
        "hash_count_state_only": True,
        "proof_lineage_hashes_are_redacted_authority_handles": True,
        "proof_lineage_hashes_are_raw_evidence_refs": False,
        "operator_supplied_evidence_required": True,
        "raw_storage_committed": False,
        "raw_companyfacts_committed": False,
        "default_reports_remain_blocked_without_operator_evidence": True,
        "production_admission_claimed": False,
    }


def _proof_source_report_hash(
    *,
    loader_report: Mapping[str, Any],
    oracle_report: Mapping[str, Any],
    period_limit: int,
) -> str:
    return stable_hash(
        {
            "schema_id": REPORT_SCHEMA_ID,
            "loader_status": str(loader_report.get("status") or ""),
            "oracle_status": str(oracle_report.get("status") or ""),
            "storage_marker": str(oracle_report.get("storage_marker") or loader_report.get("storage_marker") or ""),
            "authority_refs": _combined_authority_refs(
                loader_report=loader_report,
                oracle_report=oracle_report,
            ),
            "loader_summary_counts": _prefixed_counts(
                "loader",
                _mapping_or_empty(loader_report.get("summary")),
            ),
            "oracle_summary_counts": _prefixed_counts(
                "oracle",
                _mapping_or_empty(oracle_report.get("summary")),
            ),
            "period_limit": period_limit,
            "proof_artifact_policy": _proof_artifact_policy(),
        }
    )


def _proof_authority_refs(
    *,
    loader_report: Mapping[str, Any],
    oracle_report: Mapping[str, Any],
    proof_source_hash: str,
    proof_result_hash: str | None = None,
) -> dict[str, Any]:
    refs = {
        **_combined_authority_refs(
            loader_report=loader_report,
            oracle_report=oracle_report,
        ),
        "proof_source_report_hash": proof_source_hash,
    }
    if proof_result_hash:
        refs["proof_result_hash"] = proof_result_hash
    return refs


def _proof_result_hash(
    *,
    proof_source_hash: str,
    isolated_response: Mapping[str, Any],
    isolated_persistence_counts: Mapping[str, Any],
    redaction_scan: Mapping[str, Any],
) -> str:
    return stable_hash(
        {
            "schema_id": REPORT_SCHEMA_ID,
            "proof_source_report_hash": proof_source_hash,
            "orchestrator_status": str(isolated_response.get("status") or ""),
            "orchestrator_summary_counts": _prefixed_counts(
                "orchestrator",
                _mapping_or_empty(isolated_response.get("summary")),
            ),
            "isolated_persistence_counts": _prefixed_counts(
                "isolated_persistence",
                isolated_persistence_counts,
            ),
            "redaction_scan": dict(redaction_scan),
            "production_admission_ready": False,
        }
    )


def _combined_authority_refs(
    *,
    loader_report: Mapping[str, Any],
    oracle_report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **_mapping_or_empty(loader_report.get("authority_refs")),
        **_mapping_or_empty(oracle_report.get("authority_refs")),
    }


def _redaction_block_reason(redaction_scan: Mapping[str, Any]) -> dict[str, Any] | None:
    leak_fields = [
        key
        for key in (
            "public_response_raw_accession_found",
            "public_response_sec_url_found",
            "public_response_local_path_found",
            "public_response_raw_value_key_found",
        )
        if redaction_scan.get(key) is True
    ]
    redaction_fields = [
        key
        for key in (
            "projection_facts_all_value_redacted",
            "statement_rows_all_value_redacted",
        )
        if redaction_scan.get(key) is not True
    ]
    if leak_fields or redaction_fields:
        return {
            "reason": "offline_evidence_proof_redaction_scan_failed",
            "message": "SEC XBRL offline evidence proof failed redaction containment checks.",
            "details": {
                "leak_fields": leak_fields,
                "redaction_fields": redaction_fields,
            },
        }
    return None


def _source_hash_binding_block_reason(response: Mapping[str, Any], expected_hash: str) -> dict[str, Any] | None:
    if str(response.get("source_report_hash") or "") == expected_hash:
        return None
    return {
        "reason": "offline_evidence_proof_source_hash_unbound",
        "message": "SEC XBRL offline evidence proof did not bind the isolated workflow to the proof source hash.",
        "details": {"source_report_hash_bound": False},
    }


def _isolated_persistence_block_reason(counts: Mapping[str, Any]) -> dict[str, Any] | None:
    required_exactly_one = (
        "projection_set_count",
        "statement_packet_set_count",
        "operator_review_workflow_count",
    )
    required_positive = (
        "projection_fact_count",
        "statement_packet_row_count",
    )
    exact_failures = [
        key
        for key in required_exactly_one
        if _int_value(counts.get(key)) != 1
    ]
    positive_failures = [
        key
        for key in required_positive
        if _int_value(counts.get(key)) <= 0
    ]
    if exact_failures or positive_failures:
        return {
            "reason": "offline_evidence_proof_isolated_persistence_incomplete",
            "message": "SEC XBRL offline evidence proof did not persist a complete isolated review workflow.",
            "details": {
                "exact_count_fields": exact_failures,
                "positive_count_fields": positive_failures,
            },
        }
    return None


def _single_transaction_block_reason(response: Mapping[str, Any]) -> dict[str, Any] | None:
    containment = _mapping_or_empty(response.get("containment"))
    if (
        containment.get("single_transaction_claimed") is True
        and containment.get("existing_materializers_commit_per_stage") is False
    ):
        return None
    return {
        "reason": "offline_evidence_proof_single_transaction_unproven",
        "message": "SEC XBRL offline evidence proof did not prove a single transaction persistence boundary.",
        "details": {
            "single_transaction_claimed": containment.get("single_transaction_claimed") is True,
            "existing_materializers_commit_per_stage": containment.get("existing_materializers_commit_per_stage") is True,
        },
    }


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _first_reason(report: Mapping[str, Any], fallback: str) -> str:
    for item in report.get("blocked_reasons") or []:
        if isinstance(item, Mapping) and str(item.get("reason") or "").strip():
            return str(item["reason"])
    return fallback


def _first_message(report: Mapping[str, Any], fallback: str) -> str:
    for item in report.get("blocked_reasons") or []:
        if isinstance(item, Mapping) and str(item.get("message") or "").strip():
            return str(item["message"])
    return fallback


def _first_details(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for item in report.get("blocked_reasons") or []:
        if isinstance(item, Mapping) and isinstance(item.get("details"), Mapping):
            return item["details"]
    return None


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _prefixed_counts(prefix: str, value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        f"{prefix}_{key}": item
        for key, item in value.items()
        if key.endswith("_count")
        or key.endswith("_counts")
        or key in {"status", "period_count", "ready_period_count", "row_count", "statement_count"}
    }
