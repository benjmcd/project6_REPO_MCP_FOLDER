from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import http.client
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.services import (
    layer3_sec_edgar_delivery_status_provenance,
    layer3_sec_edgar_durable_delivery_archive,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_operator_inspection,
    layer3_sec_edgar_operator_product_surface,
    layer3_sec_edgar_real_company_corpus_validation,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_xbrl_sidecar,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json")
DEFAULT_LIVE_STORAGE = Path("backend/app/storage_test_runtime/sec-real-product-runner")
MATRIX_PLAN_SCHEMA_ID = "diagnostics.sec_xbrl_stratified_real_filing_validation_matrix_plan.v1"
MATRIX_PLAN_MODE = "sec_edgar_stratified_real_filing_validation_matrix_v1"
REQUIRED_FORMS = ("10-K", "10-Q", "20-F", "40-F", "6-K", "8-K")
REQUIRED_REAL_FILING_COUNT = 30
REQUIRED_ISSUER_HASH_COUNT = 15
MIN_COMPANYFACTS_MATCH_RATE = 0.98
REQUIRED_STRATA = (
    "large_domestic_us_gaap",
    "small_mid_domestic_us_gaap",
    "foreign_private_ifrs_20f",
    "canadian_40f",
    "current_report_8k_sparse",
    "foreign_6k_sparse",
    "amendment_restatement",
    "no_inline_or_zero_fact_diagnostic",
)
MATRIX_CHUNKS = (
    ("core", ("MSFT", "STLD", "SONY", "CCJ")),
    ("breadth", ("JPM", "MET", "PLD", "FIZZ")),
    ("expansion", ("XOM", "PFE", "UAL", "T")),
    ("large-cap-extension", ("AAPL", "NVDA", "AMZN", "TSLA")),
)
REQUIRED_ARELLE_ENV = (
    "SEC_XBRL_ARELLE_PYTHON",
    "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES",
    "SEC_XBRL_ARELLE_CACHE_DIR",
)
ADMITTED_COMPANY_REFS = frozenset(layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_CIK_REFS)
RAW_ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
RAW_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
RAW_CONTACT_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
RAW_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s'\"(])/(?:[^/\s]+/)+[^/\s]+)")
LABEL_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.-]{0,9}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnostic SEC/iXBRL real-corpus product-path runner. It orchestrates the existing "
            "governed SEC connector, Arelle sidecar, bridge, product, delivery, operator surface, "
            "and archive services. It is not runtime authority."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--storage-dir", default="")
    parser.add_argument(
        "--matrix-plan",
        default=os.environ.get("SEC_XBRL_STRATIFIED_MATRIX_PLAN", ""),
        help=(
            "Optional off-repo stratified matrix plan JSON. The plan is read only to select "
            "bounded chunks; reports keep issuer identities redacted."
        ),
    )
    parser.add_argument("--user-agent", default=os.environ.get("LAYER3_SEC_EDGAR_USER_AGENT", ""))
    parser.add_argument("--request-namespace", default="sec-xbrl-real-corpus-product-runner-v1")
    parser.add_argument(
        "--taxonomy-internet-connectivity",
        default=os.environ.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", "offline"),
        choices=("online", "offline"),
    )
    parser.add_argument(
        "--apply-default-decision",
        action="store_true",
        help="Apply the gate verdict to the committed Arelle cutover config default.",
    )
    args = parser.parse_args()

    report = build_report(
        live=bool(args.live),
        storage_dir=Path(args.storage_dir) if args.storage_dir else None,
        matrix_plan_path=Path(args.matrix_plan) if args.matrix_plan else None,
        user_agent=str(args.user_agent or ""),
        request_namespace=str(args.request_namespace or ""),
        taxonomy_internet_connectivity=str(args.taxonomy_internet_connectivity or "offline"),
    )
    output = _repo_path(Path(args.output))
    if args.apply_default_decision:
        applied = _apply_runtime_default_decision(report)
        report["runtime_default_decision"]["applied_to_config"] = applied
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_display_output_path(output)}")
    print(f"headline={report['headline']}")
    return 0


def build_report(
    *,
    live: bool,
    storage_dir: Path | None = None,
    matrix_plan_path: Path | None = None,
    matrix_plan: Mapping[str, Any] | None = None,
    user_agent: str = "",
    request_namespace: str = "sec-xbrl-real-corpus-product-runner-v1",
    taxonomy_internet_connectivity: str = "offline",
    runner: Callable[[Path, str, str, str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    preflight = _live_preflight(live=live, user_agent=user_agent)
    matrix_plan_readiness = _matrix_plan_readiness(matrix_plan_path=matrix_plan_path, matrix_plan=matrix_plan)
    public_matrix_plan_readiness = _public_matrix_plan_readiness(matrix_plan_readiness)
    matrix_chunks = _matrix_chunks_from_readiness(matrix_plan_readiness)
    rows: list[dict[str, Any]] = []
    storage_marker = None
    if preflight["state"] == "passed" and matrix_plan_readiness["state"] == "passed":
        live_storage = _live_storage_dir(storage_dir)
        storage_marker = _storage_marker(live_storage)
        run = runner or _run_live_product_path
        if runner is None:
            rows = run(
                live_storage,
                user_agent.strip(),
                request_namespace.strip() or "sec-xbrl-real-corpus-product-runner-v1",
                taxonomy_internet_connectivity,
                matrix_chunks,
            )
        else:
            rows = run(
                live_storage,
                user_agent.strip(),
                request_namespace.strip() or "sec-xbrl-real-corpus-product-runner-v1",
                taxonomy_internet_connectivity,
            )

    summary = _summary(rows)
    criteria = _criteria(preflight, summary, public_matrix_plan_readiness)
    blockers = [
        {
            "criterion": item["criterion"],
            "reason": item["blocked_reason"],
            "evidence": item["evidence"],
        }
        for item in criteria
        if item["state"] != "passed"
    ]
    decision = "real_corpus_default_on_validated" if not blockers else "real_corpus_default_on_blocked"
    pass_gate = not blockers
    current_default = _config_cutover_default_enabled()
    return {
        "schema_id": "diagnostics.sec_xbrl_real_corpus_product_runner.v1",
        "target": "sec_edgar_real_corpus_product_path_runner_v1",
        "decision": decision,
        "gate_verdict": "PASS" if pass_gate else "FAIL_OR_INCONCLUSIVE",
        "headline": _headline(decision, blockers, summary),
        "live_sec_network_used": bool(
            live and preflight["state"] == "passed" and matrix_plan_readiness["state"] == "passed"
        ),
        "fake_sec_client_used": False,
        "storage_dir_marker": storage_marker,
        "storage_dir_paths_redacted": True,
        "diagnostic_request_namespace_hash": stable_hash({"request_namespace": request_namespace})[:24],
        "matrix_execution_plan": public_matrix_plan_readiness,
        "matrix_chunks": _matrix_chunk_projection(matrix_chunks),
        "preflight": preflight,
        "criteria": criteria,
        "blocking_reasons": blockers,
        "summary": summary,
        "per_matrix": rows,
        "per_filing": _per_filing_from_rows(rows),
        "runtime_default_decision": {
            "current_default_enabled": current_default,
            "resulting_default_enabled": bool(pass_gate),
            "action": _runtime_default_action(pass_gate=pass_gate, current_default=current_default),
            "applied_to_config": False,
            "gate_has_teeth": True,
        },
        "redaction": {
            "raw_tickers_committed": False,
            "raw_accessions_committed": False,
            "raw_sec_urls_committed": False,
            "local_storage_roots_committed": False,
            "raw_values_committed": False,
            "identity_hash_only": True,
        },
        "non_goals_preserved": {
            "runtime_network_default_changed": False,
            "operator_value_reveal_enabled": False,
            "gate_b_product_package_ui_redesign_performed": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
            "new_layer3_source_shape_created": False,
        },
        "next_slice": _next_slice(pass_gate=pass_gate, blockers=blockers),
    }


def _run_live_product_path(
    storage_dir: Path,
    user_agent: str,
    request_namespace: str,
    taxonomy_internet_connectivity: str,
    matrix_chunks: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] | None = None,
) -> list[dict[str, Any]]:
    selected_chunks = matrix_chunks or _default_matrix_chunks()
    previous = {
        "storage_dir": settings.storage_dir,
        "live_enabled": settings.layer3_sec_edgar_live_network_enabled,
        "user_agent": settings.layer3_sec_edgar_user_agent,
        "rate": settings.layer3_sec_edgar_rate_limit_per_second,
        "max_bytes": settings.layer3_sec_edgar_max_bytes,
        "cutover": getattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False),
        "rate_limit": layer3_sec_edgar_live_source_artifact._enforce_rate_limit,
        "taxonomy_internet": os.environ.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY"),
    }
    settings.storage_dir = str(storage_dir.resolve(strict=False))
    settings.layer3_sec_edgar_live_network_enabled = True
    settings.layer3_sec_edgar_user_agent = user_agent
    settings.layer3_sec_edgar_rate_limit_per_second = 1
    settings.layer3_sec_edgar_max_bytes = 120_000_000
    settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = True
    os.environ["SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY"] = taxonomy_internet_connectivity
    layer3_sec_edgar_live_source_artifact._enforce_rate_limit = _waiting_rate_limit(previous["rate_limit"])
    bootstrap_storage_tree(settings.storage_dir)
    db = _memory_db_session()
    try:
        rows = [
            _run_matrix_chunk(
                label,
                matrix,
                strata=strata,
                db=db,
                request_namespace=request_namespace,
                user_agent=user_agent,
            )
            for label, matrix, strata in selected_chunks
        ]
    finally:
        db.close()
        settings.storage_dir = previous["storage_dir"]
        settings.layer3_sec_edgar_live_network_enabled = previous["live_enabled"]
        settings.layer3_sec_edgar_user_agent = previous["user_agent"]
        settings.layer3_sec_edgar_rate_limit_per_second = previous["rate"]
        settings.layer3_sec_edgar_max_bytes = previous["max_bytes"]
        settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = previous["cutover"]
        layer3_sec_edgar_live_source_artifact._enforce_rate_limit = previous["rate_limit"]
        if previous["taxonomy_internet"] is None:
            os.environ.pop("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", None)
        else:
            os.environ["SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY"] = previous["taxonomy_internet"]
    return rows


def _run_matrix_chunk(
    label: str,
    matrix: tuple[str, ...],
    *,
    strata: tuple[str, ...] = (),
    db: Any,
    request_namespace: str,
    user_agent: str,
) -> dict[str, Any]:
    matrix_hash = stable_hash({"matrix": list(matrix)})[:24]
    row: dict[str, Any] = {
        "matrix_label": label,
        "matrix_ref_hash": matrix_hash,
        "raw_identity_redacted": True,
        "storage_path_redacted": True,
        "live_sec_network_used": True,
        "fake_sec_client_used": False,
        "strata": list(strata),
    }
    try:
        validation = layer3_sec_edgar_real_company_corpus_validation.validate_sec_edgar_real_company_corpus_product_path(
            {
                "client_request_id": f"{request_namespace}-{label}-validation",
                "validation_mode": layer3_sec_edgar_real_company_corpus_validation.VALIDATION_MODE,
                "operator_decision": layer3_sec_edgar_real_company_corpus_validation.OPERATOR_DECISION,
                "company_matrix": list(matrix),
                "operator_confirmation": True,
            },
            db,
        )
    except Exception as exc:  # diagnostic-only: report exact class, not paths/URLs/identity.
        return {
            **row,
            "pipeline_state": "blocked",
            "blocked_stage": "validation",
            "blocked_reasons": [_safe_reason(exc)],
        }
    row.update(_validation_projection(validation, user_agent=user_agent))
    if validation.get("validation_state") != layer3_sec_edgar_real_company_corpus_validation.READY_STATE:
        return {
            **row,
            "pipeline_state": "blocked",
            "blocked_stage": "validation",
            "blocked_reasons": _blocked_reasons(validation),
        }
    if not _delivery_archive_matrix_admitted(matrix):
        row["delivery_status"] = "not_required_for_broader_extraction_gate"
        row["operator_inspection_status"] = "not_required_for_broader_extraction_gate"
        row["operator_product_surface_status"] = "not_required_for_broader_extraction_gate"
        row["durable_delivery_archive_status"] = "not_required_for_broader_extraction_gate"
        row["pipeline_state"] = (
            "ready"
            if row.get("supported_unblocked_or_no_inline_count") == row.get("filing_count")
            else "blocked"
        )
        row["blocked_stage"] = None if row["pipeline_state"] == "ready" else "validation_records"
        row["blocked_reasons"] = [] if row["pipeline_state"] == "ready" else ["unexpected_blocked_or_degraded_records"]
        return row
    delivery = _delivery(validation, label=label, db=db, request_namespace=request_namespace)
    row["delivery_status"] = _state(delivery, "delivery_status_provenance_state")
    if delivery.get("delivery_status_provenance_state") != layer3_sec_edgar_delivery_status_provenance.READY_STATE:
        reasons = _blocked_reasons(delivery)
        if _delivery_block_allowed_for_no_inline_records(row, reasons):
            row["delivery_status"] = "not_required_for_allowed_no_inline_xbrl_records"
            row["operator_inspection_status"] = "not_required_for_broader_extraction_gate"
            row["operator_product_surface_status"] = "not_required_for_broader_extraction_gate"
            row["durable_delivery_archive_status"] = "not_required_for_broader_extraction_gate"
            row["pipeline_state"] = "ready"
            row["blocked_stage"] = None
            row["blocked_reasons"] = []
            return row
        return {**row, "pipeline_state": "blocked", "blocked_stage": "delivery", "blocked_reasons": reasons}
    operator = _operator(delivery, label=label, db=db, request_namespace=request_namespace)
    row["operator_inspection_status"] = _state(operator, "operator_inspection_state")
    if operator.get("operator_inspection_state") != layer3_sec_edgar_operator_inspection.READY_STATE:
        return {**row, "pipeline_state": "blocked", "blocked_stage": "operator_inspection", "blocked_reasons": _blocked_reasons(operator)}
    surface = _surface(operator, label=label, db=db, request_namespace=request_namespace)
    row["operator_product_surface_status"] = _state(surface, "operator_product_surface_state")
    row["operator_surface_values_exposed"] = bool(
        ((surface.get("value_reveal") or {}).get("value_reveal_state") == "ready")
    )
    if surface.get("operator_product_surface_state") != layer3_sec_edgar_operator_product_surface.READY_STATE:
        return {**row, "pipeline_state": "blocked", "blocked_stage": "operator_product_surface", "blocked_reasons": _blocked_reasons(surface)}
    archive = _archive(surface, label=label, db=db, request_namespace=request_namespace)
    row["durable_delivery_archive_status"] = _state(archive, "durable_delivery_archive_state")
    if archive.get("durable_delivery_archive_state") != layer3_sec_edgar_durable_delivery_archive.READY_STATE:
        return {**row, "pipeline_state": "blocked", "blocked_stage": "durable_delivery_archive", "blocked_reasons": _blocked_reasons(archive)}
    row["pipeline_state"] = "ready"
    row["blocked_stage"] = None
    row["blocked_reasons"] = []
    return row


def _delivery(validation: Mapping[str, Any], *, label: str, db: Any, request_namespace: str) -> dict[str, Any]:
    return layer3_sec_edgar_delivery_status_provenance.inspect_sec_edgar_real_company_delivery_status_provenance(
        {
            "client_request_id": f"{request_namespace}-{label}-delivery",
            "status_mode": layer3_sec_edgar_delivery_status_provenance.STATUS_MODE,
            "operator_decision": layer3_sec_edgar_delivery_status_provenance.OPERATOR_DECISION,
            "sec_edgar_real_company_corpus_validation_receipt_id": validation["validation_receipt_id"],
            "sec_edgar_real_company_corpus_validation_receipt_hash": validation["validation_receipt_hash"],
            "operator_confirmation": True,
        },
        db,
    )


def _delivery_block_allowed_for_no_inline_records(row: Mapping[str, Any], reasons: list[str]) -> bool:
    if set(reasons) != {"sec_edgar_delivery_status_provenance_missing_handoff_export_prepare_output"}:
        return False
    return (
        int(row.get("supported_unblocked_or_no_inline_count") or 0) == int(row.get("filing_count") or 0)
        and int(row.get("records_with_handoff_export_prepare") or 0) == int(row.get("supported_count") or 0)
        and int(row.get("blocked_or_degraded_count") or 0) > 0
        and set(dict(row.get("failure_reasons") or {}).keys())
        <= {"sec_edgar_html_inline_xbrl_fact_authority_no_inline_xbrl_markers"}
    )


def _operator(delivery: Mapping[str, Any], *, label: str, db: Any, request_namespace: str) -> dict[str, Any]:
    return layer3_sec_edgar_operator_inspection.inspect_sec_edgar_real_company_operator_surface(
        {
            "client_request_id": f"{request_namespace}-{label}-operator",
            "inspection_mode": layer3_sec_edgar_operator_inspection.INSPECTION_MODE,
            "operator_decision": layer3_sec_edgar_operator_inspection.OPERATOR_DECISION,
            "sec_edgar_delivery_status_provenance_receipt_id": delivery["delivery_status_provenance_receipt_id"],
            "sec_edgar_delivery_status_provenance_receipt_hash": delivery["delivery_status_provenance_receipt_hash"],
            "operator_confirmation": True,
        },
        db,
    )


def _surface(operator: Mapping[str, Any], *, label: str, db: Any, request_namespace: str) -> dict[str, Any]:
    return layer3_sec_edgar_operator_product_surface.render_sec_edgar_operator_product_surface(
        {
            "client_request_id": f"{request_namespace}-{label}-surface",
            "surface_mode": layer3_sec_edgar_operator_product_surface.SURFACE_MODE,
            "operator_decision": layer3_sec_edgar_operator_product_surface.OPERATOR_DECISION,
            "sec_edgar_operator_inspection_receipt_id": operator["operator_inspection_receipt_id"],
            "sec_edgar_operator_inspection_receipt_hash": operator["operator_inspection_receipt_hash"],
            "operator_confirmation": True,
        },
        db,
    )


def _archive(surface: Mapping[str, Any], *, label: str, db: Any, request_namespace: str) -> dict[str, Any]:
    return layer3_sec_edgar_durable_delivery_archive.archive_sec_edgar_durable_delivery(
        {
            "client_request_id": f"{request_namespace}-{label}-archive",
            "archive_mode": layer3_sec_edgar_durable_delivery_archive.ARCHIVE_MODE,
            "operator_decision": layer3_sec_edgar_durable_delivery_archive.OPERATOR_DECISION,
            "sec_edgar_operator_product_surface_receipt_id": surface["operator_product_surface_receipt_id"],
            "sec_edgar_operator_product_surface_receipt_hash": surface["operator_product_surface_receipt_hash"],
            "operator_confirmation": True,
        },
        db,
    )


def _validation_projection(validation: Mapping[str, Any], *, user_agent: str) -> dict[str, Any]:
    records = [record for record in validation.get("filing_validation_records") or [] if isinstance(record, Mapping)]
    forms = Counter(str(record.get("form_type") or "unknown") for record in records)
    quality = [record.get("quality_evidence") or {} for record in records]
    metrics = [item.get("quality_metrics") or {} for item in quality if isinstance(item, Mapping)]
    per_filing = _per_filing_projection(validation, user_agent=user_agent)
    return {
        "validation_state": _state(validation, "validation_state"),
        "validation_receipt_hash": validation.get("validation_receipt_hash"),
        "connector_receipt_hash": validation.get("connector_receipt_hash"),
        "filing_count": len(records),
        "forms": dict(sorted(forms.items())),
        "issuer_hash_count": len({str(record.get("cik_hash") or "") for record in records if record.get("cik_hash")}),
        "supported_count": sum(1 for record in records if record.get("supported_degraded_blocked") == "supported"),
        "blocked_or_degraded_count": sum(
            1 for record in records if record.get("supported_degraded_blocked") != "supported"
        ),
        "supported_unblocked_or_no_inline_count": sum(
            1
            for item in per_filing
            if item.get("record_state") == "supported"
            or item.get("zero_fact_status") == "allowed_no_inline_xbrl"
        ),
        "records_with_arelle_sidecar_output": sum(
            1 for record in records if "arelle_resolved_fact_authority_sidecar" in list(record.get("outputs_produced") or [])
        ),
        "records_with_selected_fact_authority_equal_to_sidecar": sum(
            1
            for record in records
            if (record.get("authority_hashes") or {}).get("arelle_sidecar_receipt_hash")
            and (record.get("authority_hashes") or {}).get("fact_authority_receipt_hash")
            == (record.get("authority_hashes") or {}).get("arelle_sidecar_receipt_hash")
        ),
        "records_with_handoff_export_prepare": sum(
            1 for record in records if "handoff_export_prepare" in list(record.get("outputs_produced") or [])
        ),
        "resolved_fact_count": sum(int(item.get("resolved_fact_count") or 0) for item in metrics),
        "independent_inline_fact_count": sum(int(item.get("independent_inline_fact_count") or 0) for item in per_filing),
        "completeness_guard_failed_count": sum(1 for item in per_filing if item.get("completeness_guard") != "passed" and item.get("record_state") == "supported"),
        "companyfacts_value_match_count": sum(int(item.get("companyfacts_effective_value_match_count") or 0) for item in per_filing),
        "companyfacts_value_compared_count": sum(int(item.get("companyfacts_effective_value_compared_count") or 0) for item in per_filing),
        "companyfacts_value_mismatch_count": sum(int(item.get("companyfacts_effective_value_mismatch_count") or 0) for item in per_filing),
        "companyfacts_oracle_unavailable_count": sum(
            1 for item in per_filing if item.get("companyfacts_oracle_used") is False and item.get("record_state") == "supported"
        ),
        "failure_reasons": dict(
            sorted(
                Counter(
                    reason
                    for item in per_filing
                    for reason in (item.get("gaps_found") or [])
                ).items()
            )
        ),
        "operator_surface_values_exposed": any(
            bool(item.get("operator_surface_values_exposed")) for item in metrics
        ),
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
        "per_filing": per_filing,
    }


def _per_filing_projection(validation: Mapping[str, Any], *, user_agent: str) -> list[dict[str, Any]]:
    records = [record for record in validation.get("filing_validation_records") or [] if isinstance(record, Mapping)]
    connector = _connector_receipt(validation)
    acquisitions_by_example_id = {
        str(item.get("example_id") or ""): item
        for item in (connector.get("acquisition_receipts") or [])
        if isinstance(item, Mapping)
    }
    source_identities_by_example_id = _source_identities_for_validation(
        validation,
        connector=connector,
        user_agent=user_agent,
    )
    companyfacts_cache: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for record in records:
        quality = record.get("quality_evidence") if isinstance(record.get("quality_evidence"), Mapping) else {}
        metrics = quality.get("quality_metrics") if isinstance(quality.get("quality_metrics"), Mapping) else {}
        sidecar_hash = str(metrics.get("arelle_sidecar_receipt_hash") or "")
        sidecar = _sidecar_receipt_by_hash(sidecar_hash) if sidecar_hash else None
        coverage = dict(sidecar.get("coverage") or {}) if isinstance(sidecar, Mapping) else {}
        sidecar_diagnostics = dict(sidecar.get("diagnostics") or {}) if isinstance(sidecar, Mapping) else {}
        record_state = str(record.get("supported_degraded_blocked") or "")
        example_id = str(record.get("example_id") or "")
        acquisition = acquisitions_by_example_id.get(example_id, {})
        source_identity = source_identities_by_example_id.get(example_id) or _source_identity_for_acquisition(acquisition)
        companyfacts = (
            _companyfacts_count(
                cik=str(source_identity.get("cik_or_filer_ref") or ""),
                accession=str(source_identity.get("accession_or_submission_id") or ""),
                user_agent=user_agent,
                cache=companyfacts_cache,
            )
            if record_state == "supported" and sidecar is not None
            else {"oracle_used": False, "confidence": "not_applicable", "fact_count": None}
        )
        value_match = (
            _companyfacts_value_match(sidecar=sidecar, companyfacts=companyfacts)
            if sidecar is not None
            else {"match_count": None, "compared_count": 0, "match_rate": None}
        )
        value_match_period_aware = (
            _companyfacts_value_match_period_aware(sidecar=sidecar, companyfacts=companyfacts)
            if sidecar is not None
            else {"match_count": None, "compared_count": 0, "match_rate": None}
        )
        arelle_count = int(metrics.get("resolved_fact_count") or sidecar.get("resolved_fact_count") or 0) if sidecar else 0
        independent_count = int(sidecar_diagnostics.get("independent_inline_fact_count") or 0)
        compared = int(value_match.get("compared_count") or 0)
        matched = int(value_match.get("match_count") or 0)
        compared_period_aware = int(value_match_period_aware.get("compared_count") or 0)
        matched_period_aware = int(value_match_period_aware.get("match_count") or 0)
        rows.append(
            {
                "fixture_hash": str(record.get("record_hash") or "")[:24],
                "form": str(record.get("form_type") or ""),
                "issuer_by_hash": str(record.get("cik_hash") or "")[:24],
                "record_state": "supported" if record_state == "supported" else "blocked_or_degraded",
                "failure_classification": str(record.get("failure_classification") or ""),
                "gaps_found": [str(item) for item in record.get("gaps_found") or []],
                "zero_fact_status": _zero_fact_status(record, arelle_count=arelle_count),
                "production_factauthority_fact_count": int(metrics.get("fact_count") or 0),
                "arelle_resolved_fact_count": arelle_count,
                "independent_inline_fact_count": independent_count,
                "completeness_guard": (
                    "passed"
                    if record_state == "supported"
                    and sidecar is not None
                    and independent_count <= arelle_count
                    and bool(sidecar_diagnostics.get("independent_inline_fact_count_reconciled"))
                    else "not_applicable"
                    if record_state != "supported"
                    else "failed"
                ),
                "multi_document_inline_document_count": int(
                    sidecar_diagnostics.get("independent_inline_fact_document_count") or 0
                ),
                "multi_document_scanned_document_count": int(
                    sidecar_diagnostics.get("independent_inline_fact_scanned_document_count") or 0
                ),
                "per_document_fact_tally": _document_tally_projection(
                    sidecar_diagnostics.get("independent_inline_fact_document_tally") or []
                ),
                "period_resolved_count": int(metrics.get("period_resolved_count") or 0),
                "unit_resolved_count": int(metrics.get("unit_resolved_count") or 0),
                "explicit_dimension_fact_count": int(metrics.get("explicit_dimension_fact_count") or 0),
                "typed_dimension_fact_count": int(metrics.get("typed_dimension_fact_count") or 0),
                "concept_resolved_from_dts_count": int(metrics.get("concept_resolved_from_dts_count") or 0),
                "standard_concept_count": int(metrics.get("standard_concept_count") or 0),
                "extension_concept_count": int(metrics.get("extension_concept_count") or 0),
                "taxonomy_package_count": int(sidecar_diagnostics.get("taxonomy_package_count") or 0),
                "taxonomy_package_invalid_count": int(sidecar_diagnostics.get("taxonomy_package_invalid_count") or 0),
                "taxonomy_package_invalid_hashes": [
                    str(item) for item in sidecar_diagnostics.get("taxonomy_package_invalid_hashes") or []
                ],
                "companyfacts_oracle_used": bool(companyfacts.get("oracle_used")),
                "companyfacts_confidence": companyfacts.get("confidence"),
                "companyfacts_standard_fact_count": companyfacts.get("fact_count"),
                "companyfacts_effective_value_match_count": matched,
                "companyfacts_effective_value_compared_count": compared,
                "companyfacts_effective_value_mismatch_count": max(compared - matched, 0),
                "companyfacts_effective_value_match_rate": value_match.get("match_rate"),
                "companyfacts_effective_value_match_count_period_aware": matched_period_aware,
                "companyfacts_effective_value_compared_count_period_aware": compared_period_aware,
                "companyfacts_effective_value_mismatch_count_period_aware": max(
                    compared_period_aware - matched_period_aware,
                    0,
                ),
                "companyfacts_effective_value_match_rate_period_aware": value_match_period_aware.get("match_rate"),
                "companyfacts_mismatch_diagnostics": (
                    "none" if compared and matched == compared else "mismatch_count_reported_values_redacted"
                    if compared
                    else "no_standard_numeric_intersection"
                ),
                "values_redacted_in_report": True,
                "raw_identity_redacted": True,
                "raw_urls_paths_storage_roots_redacted": True,
            }
        )
        if record_state == "supported":
            time.sleep(1.05)
    return rows


def _connector_receipt(validation: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
            str(validation.get("connector_receipt_id") or ""),
            expected_connector_receipt_hash=str(validation.get("connector_receipt_hash") or ""),
        )
    except Layer3WorkbenchError:
        return {}


def _source_identity_for_acquisition(acquisition: Mapping[str, Any]) -> dict[str, Any]:
    try:
        receipt = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_receipt(
            str(acquisition.get("live_source_artifact_receipt_id") or ""),
            expected_live_source_artifact_receipt_hash=str(acquisition.get("live_source_artifact_receipt_hash") or ""),
        )
    except Layer3WorkbenchError:
        return {}
    identity = receipt.get("source_identity") if isinstance(receipt.get("source_identity"), Mapping) else {}
    return dict(identity)


def _source_identities_for_validation(
    validation: Mapping[str, Any],
    *,
    connector: Mapping[str, Any],
    user_agent: str,
) -> dict[str, dict[str, str]]:
    example_set = connector.get("example_set") if isinstance(connector.get("example_set"), Mapping) else {}
    raw_matrix = example_set.get("company_matrix") or validation.get("company_matrix") or ()
    matrix = tuple(str(item or "").strip().upper() for item in raw_matrix if str(item or "").strip())
    if not matrix:
        return {}
    try:
        cik_refs = tuple(
            layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_CIK_REFS[item]
            for item in matrix
        )
    except KeyError:
        return {}
    selection_policy = str(
        example_set.get("filing_selection_policy")
        or validation.get("filing_selection_policy")
        or layer3_sec_edgar_real_filing_acquisition_connector.DEFAULT_FILING_SELECTION_POLICY
    )
    try:
        submissions = layer3_sec_edgar_real_filing_acquisition_connector._fetch_submissions_records(
            cik_refs,
            user_agent=user_agent,
        )
        examples = layer3_sec_edgar_real_filing_acquisition_connector._select_examples(
            submissions,
            {
                "company_matrix": matrix,
                "cik_refs": cik_refs,
                "form_types": (),
                "filing_selection_policy": selection_policy,
            },
        )
    except Exception:
        return {}
    identities: dict[str, dict[str, str]] = {}
    for example in examples:
        if not isinstance(example, Mapping):
            continue
        example_id = str(example.get("example_id") or "")
        cik = str(example.get("cik") or "")
        accession = str(example.get("accession_or_submission_id") or "")
        if example_id and cik and accession:
            identities[example_id] = {
                "cik_or_filer_ref": cik,
                "accession_or_submission_id": accession,
            }
    return identities


def _sidecar_receipt_by_hash(sidecar_hash: str) -> dict[str, Any] | None:
    if not sidecar_hash:
        return None
    root = Path(settings.storage_dir).resolve() / layer3_sec_xbrl_sidecar.RECEIPT_DIR / "receipts"
    for path in root.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("sidecar_receipt_hash") == sidecar_hash:
            return payload
    return None


def _document_tally_projection(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            {
                "document_index": item.get("document_index"),
                "document_type": item.get("document_type"),
                "primary_document": bool(item.get("primary_document")),
                "inline_fact_count": int(item.get("inline_fact_count") or 0),
                "document_filename_hash": str(item.get("document_filename_hash") or "")[:24],
                "document_text_hash": str(item.get("document_text_hash") or "")[:24],
            }
        )
    return rows


def _zero_fact_status(record: Mapping[str, Any], *, arelle_count: int) -> str:
    if arelle_count:
        return "not_zero"
    gaps = set(str(item) for item in record.get("gaps_found") or [])
    if "sec_edgar_html_inline_xbrl_fact_authority_no_inline_xbrl_markers" in gaps:
        return "allowed_no_inline_xbrl"
    roles = set(str(item) for item in record.get("source_family_roles") or [])
    if "html_inline_xbrl_classified_not_parsed" not in roles:
        return "allowed_no_inline_xbrl"
    return "unexpected_zero_inline_xbrl"


def _per_filing_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    per_filing: list[dict[str, Any]] = []
    for row in rows:
        for item in row.get("per_filing") or []:
            if isinstance(item, dict):
                per_filing.append(item)
    return per_filing


def _companyfacts_count(
    *,
    cik: str,
    accession: str,
    user_agent: str,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not cik or not accession:
        return {"oracle_used": False, "confidence": "unavailable_missing_identity", "fact_count": None}
    cache_key = str(cik).zfill(10)
    if cache_key not in cache:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cache_key}.json"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
        )
        try:
            layer3_sec_edgar_live_source_artifact._enforce_rate_limit()
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (
            OSError,
            TimeoutError,
            urllib.error.URLError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            http.client.HTTPException,
        ) as exc:
            cache[cache_key] = {
                "oracle_used": False,
                "confidence": "unavailable_fetch_failed",
                "error_hash": stable_hash({"error_type": type(exc).__name__})[:16],
                "_payload": None,
            }
        else:
            cache[cache_key] = {
                "oracle_used": True,
                "confidence": "primary_companyfacts_standard_taxonomy_accession_scope",
                "_payload": payload if isinstance(payload, dict) else None,
            }
    cached = dict(cache.get(cache_key) or {})
    payload = cached.get("_payload")
    if not isinstance(payload, dict):
        return {key: value for key, value in cached.items() if key != "_payload"} | {"fact_count": None}
    count = 0
    value_keys: list[tuple[str, str, str]] = []
    value_keys_period_aware: list[tuple[str, str, tuple[str, ...], str]] = []
    taxonomies = payload.get("facts") if isinstance(payload, dict) else {}
    if not isinstance(taxonomies, dict):
        return {"oracle_used": False, "confidence": "unavailable_invalid_payload", "fact_count": None}
    for taxonomy_name in ("us-gaap", "dei", "ifrs-full"):
        concepts = taxonomies.get(taxonomy_name) or {}
        if not isinstance(concepts, dict):
            continue
        for concept_name, concept in concepts.items():
            units = concept.get("units") if isinstance(concept, dict) else {}
            if not isinstance(units, dict):
                continue
            for unit_name, facts in units.items():
                if not isinstance(facts, list):
                    continue
                for fact in facts:
                    if not isinstance(fact, dict) or fact.get("accn") != accession:
                        continue
                    count += 1
                    value_key = _numeric_value_key(concept_name, unit_name, fact.get("val"))
                    if value_key is not None:
                        value_keys.append(value_key)
                    value_key_period_aware = _numeric_value_key_period_aware(
                        concept_name,
                        unit_name,
                        fact.get("val"),
                        _companyfacts_period_key(fact),
                    )
                    if value_key_period_aware is not None:
                        value_keys_period_aware.append(value_key_period_aware)
    return {
        "oracle_used": True,
        "confidence": "primary_companyfacts_standard_taxonomy_accession_scope",
        "fact_count": count,
        "_value_keys": value_keys,
        "_value_keys_period_aware": value_keys_period_aware,
    }


def _companyfacts_value_match(*, sidecar: Mapping[str, Any], companyfacts: Mapping[str, Any]) -> dict[str, Any]:
    value_keys = companyfacts.get("_value_keys")
    if not isinstance(value_keys, list) or not value_keys:
        return {"match_count": None, "compared_count": 0, "match_rate": None}
    try:
        store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(sidecar)
    except Layer3WorkbenchError:
        return {"match_count": None, "compared_count": 0, "match_rate": None}
    values_by_id = {
        str(item.get("resolved_fact_id") or ""): item
        for item in store.get("value_records") or []
        if isinstance(item, Mapping)
    }
    companyfacts_by_concept_unit: dict[tuple[str, str], list[Decimal]] = {}
    for item in value_keys:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            continue
        concept_name, unit_name, value_text = item
        try:
            value_decimal = Decimal(str(value_text))
        except (InvalidOperation, ValueError):
            continue
        companyfacts_by_concept_unit.setdefault((str(concept_name), str(unit_name)), []).append(value_decimal)
    compared = 0
    matched = 0
    for record in sidecar.get("resolved_fact_records") or []:
        if not isinstance(record, Mapping):
            continue
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        namespace = str(concept.get("namespace") or "")
        if not concept.get("standard") or not (
            "fasb.org/us-gaap" in namespace or "xbrl.sec.gov/dei" in namespace or "xbrl.ifrs.org" in namespace
        ):
            continue
        value_record = values_by_id.get(str(record.get("resolved_fact_id") or ""))
        if not isinstance(value_record, Mapping):
            continue
        unit = record.get("unit") if isinstance(record.get("unit"), Mapping) else {}
        dimensions = record.get("dimensions") if isinstance(record.get("dimensions"), Mapping) else {}
        if list(dimensions.get("explicit") or []) or list(dimensions.get("typed") or []):
            continue
        concept_unit = (str(concept.get("local_name") or ""), _companyfacts_unit_name(unit))
        candidates = companyfacts_by_concept_unit.get(concept_unit)
        if not candidates:
            continue
        try:
            effective_value = Decimal(str(value_record.get("effective_value")))
        except (InvalidOperation, ValueError):
            continue
        tolerance = _decimals_tolerance(record.get("decimals"))
        compared += 1
        match_index = _matching_decimal_index(candidates, effective_value, tolerance)
        if match_index is not None:
            matched += 1
            candidates.pop(match_index)
    return {
        "match_count": matched,
        "compared_count": compared,
        "match_rate": round(matched / compared, 4) if compared else None,
    }


def _companyfacts_value_match_period_aware(
    *,
    sidecar: Mapping[str, Any],
    companyfacts: Mapping[str, Any],
) -> dict[str, Any]:
    value_keys = companyfacts.get("_value_keys_period_aware")
    if not isinstance(value_keys, list) or not value_keys:
        return {"match_count": None, "compared_count": 0, "match_rate": None}
    try:
        store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(sidecar)
    except Layer3WorkbenchError:
        return {"match_count": None, "compared_count": 0, "match_rate": None}
    values_by_id = {
        str(item.get("resolved_fact_id") or ""): item
        for item in store.get("value_records") or []
        if isinstance(item, Mapping)
    }
    companyfacts_by_concept_unit_period: dict[tuple[str, str, tuple[str, ...]], list[Decimal]] = {}
    for item in value_keys:
        if not isinstance(item, (list, tuple)) or len(item) != 4:
            continue
        concept_name, unit_name, period_key, value_text = item
        if not isinstance(period_key, (list, tuple)):
            continue
        try:
            value_decimal = Decimal(str(value_text))
        except (InvalidOperation, ValueError):
            continue
        companyfacts_by_concept_unit_period.setdefault(
            (str(concept_name), str(unit_name), tuple(str(part) for part in period_key)),
            [],
        ).append(value_decimal)
    compared = 0
    matched = 0
    for record in sidecar.get("resolved_fact_records") or []:
        if not isinstance(record, Mapping):
            continue
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        namespace = str(concept.get("namespace") or "")
        if not concept.get("standard") or not (
            "fasb.org/us-gaap" in namespace or "xbrl.sec.gov/dei" in namespace or "xbrl.ifrs.org" in namespace
        ):
            continue
        value_record = values_by_id.get(str(record.get("resolved_fact_id") or ""))
        if not isinstance(value_record, Mapping):
            continue
        unit = record.get("unit") if isinstance(record.get("unit"), Mapping) else {}
        dimensions = record.get("dimensions") if isinstance(record.get("dimensions"), Mapping) else {}
        if list(dimensions.get("explicit") or []) or list(dimensions.get("typed") or []):
            continue
        concept_unit_period = (
            str(concept.get("local_name") or ""),
            _companyfacts_unit_name_period_aware(unit),
            _resolved_fact_period_key(record.get("period") if isinstance(record.get("period"), Mapping) else {}),
        )
        candidates = companyfacts_by_concept_unit_period.get(concept_unit_period)
        if not candidates:
            continue
        try:
            effective_value = Decimal(str(value_record.get("effective_value")))
        except (InvalidOperation, ValueError):
            continue
        tolerance = _decimals_tolerance(record.get("decimals"))
        compared += 1
        match_index = _matching_decimal_index(candidates, effective_value, tolerance)
        if match_index is not None:
            matched += 1
            candidates.pop(match_index)
    return {
        "match_count": matched,
        "compared_count": compared,
        "match_rate": round(matched / compared, 4) if compared else None,
    }


def _numeric_value_key(concept_name: Any, unit_name: Any, value: Any) -> tuple[str, str, str] | None:
    try:
        numeric = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return (str(concept_name or ""), str(unit_name or ""), format(numeric.normalize(), "f"))


def _numeric_value_key_period_aware(
    concept_name: Any,
    unit_name: Any,
    value: Any,
    period_key: tuple[str, ...],
) -> tuple[str, str, tuple[str, ...], str] | None:
    try:
        numeric = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return (str(concept_name or ""), str(unit_name or ""), period_key, format(numeric.normalize(), "f"))


def _decimals_tolerance(decimals: Any) -> Decimal:
    if decimals is None or decimals == "":
        return Decimal("0")
    text = str(decimals).strip()
    if text.upper() in {"INF", "INFINITY"}:
        return Decimal("0")
    try:
        return Decimal(1).scaleb(-int(text))
    except (ValueError, InvalidOperation):
        return Decimal("0")


def _matching_decimal_index(candidates: list[Decimal], effective_value: Decimal, tolerance: Decimal) -> int | None:
    for index, candidate in enumerate(candidates):
        if abs(candidate - effective_value) <= tolerance:
            return index
    return None


def _companyfacts_unit_name(unit: Mapping[str, Any]) -> str:
    currency = str(unit.get("currency") or "")
    if currency.startswith("iso4217:"):
        return currency.split(":", 1)[1]
    measures = list(unit.get("measures") or [])
    if measures:
        measure = str(measures[0])
        return measure.split(":", 1)[1] if ":" in measure else measure
    return ""


def _companyfacts_unit_name_period_aware(unit: Mapping[str, Any]) -> str:
    denominator = list(unit.get("denominator") or [])
    if denominator:
        numerator = list(unit.get("numerator") or [])
        if numerator:
            numerator_name = _unit_measure_name(numerator[0])
        else:
            currency = str(unit.get("currency") or "")
            numerator_name = currency.split(":", 1)[1] if currency.startswith("iso4217:") else ""
        return f"{numerator_name}/{_unit_measure_name(denominator[0])}"
    return _companyfacts_unit_name(unit)


def _unit_measure_name(value: Any) -> str:
    text = str(value or "")
    return text.split(":", 1)[1] if ":" in text else text


def _companyfacts_period_key(fact: Mapping[str, Any]) -> tuple[str, ...]:
    start = fact.get("start")
    end = fact.get("end")
    if start in (None, ""):
        return ("i", str(end or ""))
    return ("d", str(start or ""), str(end or ""))


def _resolved_fact_period_key(period: Mapping[str, Any]) -> tuple[str, ...]:
    period_type = str(period.get("type") or "")
    if period_type == "instant":
        return ("i", str(period.get("instant") or ""))
    if period_type == "duration":
        return ("d", str(period.get("start") or ""), str(period.get("end") or ""))
    return ("?",)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    forms: Counter[str] = Counter()
    per_filing = _per_filing_from_rows(rows)
    strata_readiness = _strata_readiness(rows)
    for row in rows:
        forms.update(row.get("forms") or {})
    compared = sum(int(item.get("companyfacts_effective_value_compared_count") or 0) for item in per_filing)
    matched = sum(int(item.get("companyfacts_effective_value_match_count") or 0) for item in per_filing)
    compared_period_aware = sum(
        int(item.get("companyfacts_effective_value_compared_count_period_aware") or 0) for item in per_filing
    )
    matched_period_aware = sum(
        int(item.get("companyfacts_effective_value_match_count_period_aware") or 0) for item in per_filing
    )
    issuer_hashes = {str(item.get("issuer_by_hash") or "") for item in per_filing if item.get("issuer_by_hash")}
    return {
        "matrix_chunk_count": len(rows),
        "ready_matrix_chunk_count": sum(1 for row in rows if row.get("pipeline_state") == "ready"),
        "blocked_matrix_chunk_count": sum(1 for row in rows if row.get("pipeline_state") != "ready"),
        "strata_readiness": strata_readiness,
        "real_filing_count": sum(int(row.get("filing_count") or 0) for row in rows),
        "supported_record_count": sum(int(row.get("supported_count") or 0) for row in rows),
        "blocked_or_degraded_record_count": sum(int(row.get("blocked_or_degraded_count") or 0) for row in rows),
        "forms": dict(sorted(forms.items())),
        "required_forms": list(REQUIRED_FORMS),
        "required_forms_present": all(form in forms for form in REQUIRED_FORMS),
        "issuer_hash_count": len(issuer_hashes),
        "required_issuer_hash_count": REQUIRED_ISSUER_HASH_COUNT,
        "resolved_fact_count": sum(int(row.get("resolved_fact_count") or 0) for row in rows),
        "independent_inline_fact_count": sum(int(row.get("independent_inline_fact_count") or 0) for row in rows),
        "completeness_guard_failed_count": sum(int(row.get("completeness_guard_failed_count") or 0) for row in rows),
        "unexpected_zero_inline_xbrl_count": sum(
            1 for item in per_filing if item.get("zero_fact_status") == "unexpected_zero_inline_xbrl"
        ),
        "unexpected_blocked_or_degraded_count": sum(
            1
            for item in per_filing
            if item.get("record_state") != "supported"
            and item.get("zero_fact_status") != "allowed_no_inline_xbrl"
        ),
        "companyfacts_value_match_count": matched,
        "companyfacts_value_compared_count": compared,
        "companyfacts_value_mismatch_count": max(compared - matched, 0),
        "companyfacts_value_match_rate": round(matched / compared, 4) if compared else None,
        "companyfacts_value_match_count_period_aware": matched_period_aware,
        "companyfacts_value_compared_count_period_aware": compared_period_aware,
        "companyfacts_value_mismatch_count_period_aware": max(compared_period_aware - matched_period_aware, 0),
        "companyfacts_value_match_rate_period_aware": (
            round(matched_period_aware / compared_period_aware, 4) if compared_period_aware else None
        ),
        "minimum_companyfacts_value_match_rate": MIN_COMPANYFACTS_MATCH_RATE,
        "companyfacts_oracle_unavailable_count": sum(int(row.get("companyfacts_oracle_unavailable_count") or 0) for row in rows),
        "taxonomy_package_invalid_count": sum(
            int(item.get("taxonomy_package_invalid_count") or 0) for item in per_filing
        ),
        "filings_with_invalid_taxonomy_package_entries": sum(
            1 for item in per_filing if int(item.get("taxonomy_package_invalid_count") or 0) > 0
        ),
        "failure_reasons": dict(
            sorted(
                Counter(
                    reason
                    for row in rows
                    for reason, count in dict(row.get("failure_reasons") or {}).items()
                    for _ in range(int(count or 0))
                ).items()
            )
        ),
        "records_with_arelle_sidecar_output": sum(int(row.get("records_with_arelle_sidecar_output") or 0) for row in rows),
        "records_with_selected_fact_authority_equal_to_sidecar": sum(
            int(row.get("records_with_selected_fact_authority_equal_to_sidecar") or 0) for row in rows
        ),
        "records_with_handoff_export_prepare": sum(int(row.get("records_with_handoff_export_prepare") or 0) for row in rows),
        "delivery_ready_matrix_chunk_count": sum(
            1 for row in rows if row.get("delivery_status") == layer3_sec_edgar_delivery_status_provenance.READY_STATE
        ),
        "operator_inspection_ready_matrix_chunk_count": sum(
            1 for row in rows if row.get("operator_inspection_status") == layer3_sec_edgar_operator_inspection.READY_STATE
        ),
        "operator_product_surface_ready_matrix_chunk_count": sum(
            1 for row in rows if row.get("operator_product_surface_status") == layer3_sec_edgar_operator_product_surface.READY_STATE
        ),
        "durable_delivery_archive_ready_matrix_chunk_count": sum(
            1 for row in rows if row.get("durable_delivery_archive_status") == layer3_sec_edgar_durable_delivery_archive.READY_STATE
        ),
        "operator_surface_values_exposed": any(bool(row.get("operator_surface_values_exposed")) for row in rows),
    }


def _strata_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_stratum = {
        stratum: {
            "matrix_chunk_count": 0,
            "ready_matrix_chunk_count": 0,
            "blocked_matrix_chunk_count": 0,
            "matrix_ref_hashes": [],
        }
        for stratum in REQUIRED_STRATA
    }
    unknown: set[str] = set()
    for row in rows:
        row_strata = [str(item) for item in row.get("strata") or [] if str(item)]
        if not row_strata:
            continue
        ready = row.get("pipeline_state") == "ready"
        matrix_ref_hash = str(row.get("matrix_ref_hash") or "")
        for stratum in row_strata:
            if stratum not in by_stratum:
                unknown.add(stratum)
                continue
            summary = by_stratum[stratum]
            summary["matrix_chunk_count"] += 1
            if ready:
                summary["ready_matrix_chunk_count"] += 1
            else:
                summary["blocked_matrix_chunk_count"] += 1
            if matrix_ref_hash:
                summary["matrix_ref_hashes"].append(matrix_ref_hash)

    for summary in by_stratum.values():
        summary["matrix_ref_hashes"] = sorted(set(summary["matrix_ref_hashes"]))

    missing = [
        stratum
        for stratum, summary in by_stratum.items()
        if int(summary["matrix_chunk_count"] or 0) == 0
    ]
    not_ready = [
        stratum
        for stratum, summary in by_stratum.items()
        if int(summary["ready_matrix_chunk_count"] or 0) == 0
    ]
    blocked = [
        stratum
        for stratum, summary in by_stratum.items()
        if int(summary["blocked_matrix_chunk_count"] or 0) > 0
    ]
    ready_strata = [
        stratum
        for stratum, summary in by_stratum.items()
        if int(summary["ready_matrix_chunk_count"] or 0) > 0
        and int(summary["blocked_matrix_chunk_count"] or 0) == 0
    ]
    return {
        "required_strata": list(REQUIRED_STRATA),
        "ready_strata": ready_strata,
        "missing_strata": missing,
        "not_ready_strata": not_ready,
        "blocked_strata": blocked,
        "unknown_strata": sorted(unknown),
        "all_required_strata_ready": not missing and not not_ready and not blocked and not unknown,
        "by_stratum": by_stratum,
    }


def _criteria(
    preflight: Mapping[str, Any],
    summary: Mapping[str, Any],
    matrix_plan_readiness: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _criterion(
            "live_preflight",
            preflight["state"] == "passed",
            preflight,
            "real_corpus_product_path_live_preflight_not_satisfied",
        ),
        _criterion(
            "matrix_execution_plan",
            matrix_plan_readiness["state"] == "passed",
            matrix_plan_readiness,
            "real_corpus_product_path_matrix_plan_not_satisfied",
        ),
        _criterion(
            "stratified_matrix_required_strata_readiness",
            matrix_plan_readiness.get("mode") != "external_stratified_matrix_plan"
            or matrix_plan_readiness.get("state") != "passed"
            or bool((summary.get("strata_readiness") or {}).get("all_required_strata_ready")),
            {
                "matrix_plan_mode": matrix_plan_readiness.get("mode"),
                "strata_readiness": summary.get("strata_readiness"),
            },
            "stratified_matrix_required_strata_not_ready",
        ),
        _criterion(
            "broader_real_product_path_corpus",
            summary["real_filing_count"] >= REQUIRED_REAL_FILING_COUNT
            and summary["issuer_hash_count"] >= REQUIRED_ISSUER_HASH_COUNT
            and summary["required_forms_present"],
            {
                "real_filing_count": summary["real_filing_count"],
                "required_real_filing_count": REQUIRED_REAL_FILING_COUNT,
                "issuer_hash_count": summary["issuer_hash_count"],
                "required_issuer_hash_count": REQUIRED_ISSUER_HASH_COUNT,
                "forms": summary["forms"],
                "required_forms": list(REQUIRED_FORMS),
            },
            "broader_real_product_path_required_corpus_not_proven",
        ),
        _criterion(
            "arelle_sidecar_selected_for_supported_records",
            summary["supported_record_count"] > 0
            and summary["records_with_arelle_sidecar_output"] == summary["supported_record_count"]
            and summary["records_with_selected_fact_authority_equal_to_sidecar"] == summary["supported_record_count"],
            {
                "supported_record_count": summary["supported_record_count"],
                "records_with_arelle_sidecar_output": summary["records_with_arelle_sidecar_output"],
                "records_with_selected_fact_authority_equal_to_sidecar": summary[
                    "records_with_selected_fact_authority_equal_to_sidecar"
                ],
            },
            "arelle_sidecar_not_proven_as_selected_authority_for_all_supported_records",
        ),
        _criterion(
            "product_path_validation_readiness",
            summary["matrix_chunk_count"] > 0
            and summary["ready_matrix_chunk_count"] == summary["matrix_chunk_count"]
            and summary["records_with_handoff_export_prepare"] == summary["supported_record_count"]
            and summary["unexpected_blocked_or_degraded_count"] == 0,
            {
                "matrix_chunk_count": summary["matrix_chunk_count"],
                "ready_matrix_chunk_count": summary["ready_matrix_chunk_count"],
                "supported_record_count": summary["supported_record_count"],
                "records_with_handoff_export_prepare": summary["records_with_handoff_export_prepare"],
                "unexpected_blocked_or_degraded_count": summary["unexpected_blocked_or_degraded_count"],
            },
            "real_corpus_product_path_validation_not_ready_across_matrix_chunks",
        ),
        _criterion(
            "completeness_guard",
            summary["supported_record_count"] > 0
            and summary["completeness_guard_failed_count"] == 0
            and summary["unexpected_zero_inline_xbrl_count"] == 0
            and summary["resolved_fact_count"] >= summary["independent_inline_fact_count"],
            {
                "resolved_fact_count": summary["resolved_fact_count"],
                "independent_inline_fact_count": summary["independent_inline_fact_count"],
                "completeness_guard_failed_count": summary["completeness_guard_failed_count"],
                "unexpected_zero_inline_xbrl_count": summary["unexpected_zero_inline_xbrl_count"],
            },
            "arelle_completeness_guard_failed_or_truncation_possible",
        ),
        _criterion(
            "companyfacts_effective_value_correctness",
            bool(summary["companyfacts_value_compared_count"])
            and float(summary["companyfacts_value_match_rate"] or 0.0) >= MIN_COMPANYFACTS_MATCH_RATE
            and summary["companyfacts_oracle_unavailable_count"] == 0,
            {
                "oracle": "primary_companyfacts_standard_taxonomy_accession_scope_non_dimensional_numeric_intersection",
                "match_count": summary["companyfacts_value_match_count"],
                "compared_count": summary["companyfacts_value_compared_count"],
                "mismatch_count": summary["companyfacts_value_mismatch_count"],
                "match_rate": summary["companyfacts_value_match_rate"],
                "minimum_match_rate": MIN_COMPANYFACTS_MATCH_RATE,
                "companyfacts_oracle_unavailable_count": summary["companyfacts_oracle_unavailable_count"],
            },
            "companyfacts_effective_value_correctness_not_proven_on_broader_corpus",
        ),
        _criterion(
            "redaction_and_non_admissions",
            not summary["operator_surface_values_exposed"],
            {
                "operator_surface_values_exposed": summary["operator_surface_values_exposed"],
                "final_financial_statement_semantics_claimed": False,
                "cross_company_comparability_claimed": False,
                "candidate_b_sec_routing_performed": False,
            },
            "operator_value_or_non_admitted_semantics_exposed",
        ),
    ]


def _criterion(name: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": name,
        "state": "passed" if passed else "blocked",
        "evidence": dict(evidence),
        "blocked_reason": None if passed else blocked_reason,
    }


def _live_preflight(*, live: bool, user_agent: str) -> dict[str, Any]:
    missing_env = [name for name in REQUIRED_ARELLE_ENV if not os.environ.get(name)]
    taxonomy = _taxonomy_package_preflight()
    cache = _cache_dir_preflight()
    arelle_python = _arelle_python_preflight()
    arelle_ready = (
        not missing_env
        and arelle_python["configured"]
        and taxonomy["configured"]
        and cache["configured"]
    )
    return {
        "state": "passed" if live and user_agent.strip() and arelle_ready else "blocked",
        "live_requested": live,
        "user_agent_configured": bool(user_agent.strip()),
        "required_arelle_env_configured": arelle_ready,
        "missing_env_names": missing_env,
        "arelle_python": arelle_python,
        "taxonomy_packages": taxonomy,
        "arelle_cache": cache,
        "sec_rate_limit_per_second": 1,
        "live_network_default_changed": False,
        "arelle_cutover_current_default_enabled": _config_cutover_default_enabled(),
        "blocked_reasons": [
            *([] if live else ["live_execution_not_requested"]),
            *([] if user_agent.strip() else ["sec_user_agent_not_configured"]),
            *([] if not missing_env else ["arelle_environment_not_configured"]),
            *([] if arelle_python["configured"] else ["arelle_python_unavailable"]),
            *([] if taxonomy["configured"] else ["taxonomy_package_files_unavailable"]),
            *([] if cache["configured"] else ["arelle_cache_dir_unavailable"]),
        ],
    }


def _matrix_plan_readiness(
    *,
    matrix_plan_path: Path | None,
    matrix_plan: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if matrix_plan_path is None and matrix_plan is None:
        return {
            "state": "passed",
            "mode": "built_in_broader_corpus_matrix",
            "external_plan_used": False,
            "plan_path_marker": None,
            "paths_redacted": True,
            "chunk_count": len(_default_matrix_chunks()),
            "chunks": _matrix_chunk_projection(_default_matrix_chunks()),
            "blocked_reasons": [],
        }
    path = matrix_plan_path.resolve(strict=False) if matrix_plan_path is not None else None
    plan: dict[str, Any] = {}
    blocked_reasons: list[str] = []
    plan_top_level_type = None
    if matrix_plan is not None:
        if isinstance(matrix_plan, Mapping):
            plan = dict(matrix_plan)
        else:
            blocked_reasons.append("matrix_plan_top_level_not_object")
            plan_top_level_type = type(matrix_plan).__name__
    if path is not None:
        if not path.exists() or not path.is_file():
            blocked_reasons.append("matrix_plan_file_unavailable")
        elif _path_inside_repo_or_onedrive(path):
            blocked_reasons.append("matrix_plan_file_inside_repo_or_onedrive")
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                blocked_reasons.append("matrix_plan_file_unreadable")
            else:
                if not isinstance(payload, Mapping):
                    blocked_reasons.append("matrix_plan_top_level_not_object")
                    plan_top_level_type = type(payload).__name__
                    plan = {}
                else:
                    plan = dict(payload)
    if plan.get("schema_id") != MATRIX_PLAN_SCHEMA_ID:
        blocked_reasons.append("matrix_plan_schema_not_admitted")
    if plan.get("matrix_mode") != MATRIX_PLAN_MODE:
        blocked_reasons.append("matrix_plan_mode_not_admitted")
    chunks, chunk_reasons = _matrix_chunks_from_external_plan(plan)
    blocked_reasons.extend(chunk_reasons)
    projection = _matrix_chunk_projection(chunks)
    covered = {
        stratum
        for item in projection
        for stratum in item.get("strata", [])
    }
    missing_strata = sorted(set(REQUIRED_STRATA) - covered)
    if missing_strata:
        blocked_reasons.append("matrix_plan_required_strata_missing")
    state = "passed" if not blocked_reasons else "blocked"
    return {
        "state": state,
        "mode": "external_stratified_matrix_plan",
        "external_plan_used": True,
        "plan_path_marker": stable_hash({"plan_path": str(path)})[:24] if path is not None else None,
        "paths_redacted": True,
        "chunk_count": len(chunks),
        "chunks": projection,
        "_chunks": chunks,
        "required_strata": list(REQUIRED_STRATA),
        "covered_strata": sorted(covered),
        "missing_required_strata": missing_strata,
        "plan_top_level_type": plan_top_level_type,
        "blocked_reasons": list(dict.fromkeys(blocked_reasons)),
    }


def _matrix_chunks_from_external_plan(
    plan: Mapping[str, Any],
) -> tuple[tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...], list[str]]:
    reasons: list[str] = []
    raw_chunks = plan.get("chunks")
    if not isinstance(raw_chunks, list) or not raw_chunks:
        return (), ["matrix_plan_chunks_missing"]
    chunks: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
    seen_labels: set[str] = set()
    seen_company_refs: set[str] = set()
    for index, raw in enumerate(raw_chunks):
        if not isinstance(raw, Mapping):
            reasons.append("matrix_plan_chunk_invalid")
            continue
        label = str(raw.get("matrix_label") or "").strip()
        if not label:
            reasons.append("matrix_plan_chunk_label_invalid")
            continue
        if _matrix_label_contains_raw_identity(label):
            reasons.append("matrix_plan_chunk_label_raw_identity_not_admitted")
            continue
        if label in seen_labels:
            reasons.append("matrix_plan_chunk_label_invalid")
            continue
        seen_labels.add(label)
        matrix = _external_company_matrix(raw.get("company_matrix"))
        strata = _external_strata(raw.get("strata"))
        if not matrix:
            reasons.append("matrix_plan_chunk_company_matrix_invalid")
        if not strata:
            reasons.append("matrix_plan_chunk_strata_invalid")
        if not matrix or not strata:
            continue
        if seen_company_refs.intersection(matrix):
            reasons.append("matrix_plan_duplicate_company_matrix_issuer")
            continue
        seen_company_refs.update(matrix)
        chunks.append((label, matrix, strata))
        if index >= 23:
            reasons.append("matrix_plan_chunk_count_exceeds_limit")
            break
    return tuple(chunks), reasons


def _external_company_matrix(value: Any) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(str(item or "").strip().upper() for item in _as_list(value)))
    if not values or len(values) > len(layer3_sec_edgar_real_filing_acquisition_connector.DEFAULT_REAL_COMPANY_MATRIX):
        return ()
    admitted = set(layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_CIK_REFS)
    if any(item not in admitted for item in values):
        return ()
    return values


def _external_strata(value: Any) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(str(item or "").strip() for item in _as_list(value) if str(item or "").strip()))
    if not values or any(item not in REQUIRED_STRATA for item in values):
        return ()
    return values


def _matrix_label_contains_raw_identity(label: str) -> bool:
    if RAW_ACCESSION_RE.search(label):
        return True
    if RAW_URL_RE.search(label):
        return True
    if RAW_CONTACT_RE.search(label):
        return True
    if RAW_PATH_RE.search(label):
        return True
    for token in LABEL_TOKEN_RE.findall(label):
        if token.upper() in ADMITTED_COMPANY_REFS:
            return True
    return False


def _matrix_chunks_from_readiness(
    readiness: Mapping[str, Any],
) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    if readiness.get("mode") != "external_stratified_matrix_plan" or readiness.get("state") != "passed":
        return _default_matrix_chunks()
    return tuple(readiness.get("_chunks") or ())


def _public_matrix_plan_readiness(readiness: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in readiness.items() if not str(key).startswith("_")}


def _delivery_archive_matrix_admitted(matrix: tuple[str, ...]) -> bool:
    return tuple(matrix) in {
        tuple(layer3_sec_edgar_delivery_status_provenance.EXPECTED_COMPANY_MATRIX),
        tuple(layer3_sec_edgar_delivery_status_provenance.DELIVERY_STATUS_PROVENANCE_BREADTH_SELECTED_MATRIX),
    }


def _default_matrix_chunks() -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    return tuple((label, matrix, ()) for label, matrix in MATRIX_CHUNKS)


def _arelle_python_preflight() -> dict[str, Any]:
    raw = str(os.environ.get("SEC_XBRL_ARELLE_PYTHON") or os.environ.get("ARELLE_PYTHON") or "").strip()
    path = Path(raw).resolve(strict=False) if raw else None
    return {
        "configured": bool(path and path.exists() and path.is_file()),
        "path_redacted": bool(raw),
    }


def _taxonomy_package_preflight() -> dict[str, Any]:
    raw = str(os.environ.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES") or "").strip()
    entries = [item.strip() for item in raw.split(os.pathsep) if item.strip()]
    valid_count = 0
    invalid_reasons: Counter[str] = Counter()
    for item in entries:
        path = Path(item).resolve(strict=False)
        if not path.exists():
            invalid_reasons["missing"] += 1
        elif not path.is_file():
            invalid_reasons["not_file"] += 1
        elif _path_inside_repo_or_onedrive(path):
            invalid_reasons["inside_repo_or_onedrive"] += 1
        else:
            valid_count += 1
    return {
        "configured": bool(valid_count and not invalid_reasons),
        "entry_count": len(entries),
        "valid_file_count": valid_count,
        "invalid_entry_count": sum(invalid_reasons.values()),
        "invalid_reasons": dict(sorted(invalid_reasons.items())),
        "paths_redacted": True,
    }


def _cache_dir_preflight() -> dict[str, Any]:
    raw = str(os.environ.get("SEC_XBRL_ARELLE_CACHE_DIR") or "").strip()
    path = Path(raw).resolve(strict=False) if raw else None
    inside_restricted = bool(path and _path_inside_repo_or_onedrive(path))
    return {
        "configured": bool(path and not inside_restricted),
        "path_redacted": bool(raw),
        "inside_repo_or_onedrive": inside_restricted,
    }


def _path_inside_repo_or_onedrive(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    repo = ROOT.resolve(strict=False)
    try:
        resolved.relative_to(repo)
        return True
    except ValueError:
        return any(part.lower() == "onedrive" for part in resolved.parts)


def _matrix_chunk_projection(
    matrix_chunks: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...],
) -> list[dict[str, Any]]:
    return [
        {
            "matrix_label": label,
            "matrix_ref_hash": stable_hash({"matrix": list(matrix)})[:24],
            "issuer_count": len(matrix),
            "strata": list(strata),
            "strata_hash": stable_hash({"strata": list(strata)})[:24] if strata else None,
            "raw_identity_redacted": True,
        }
        for label, matrix, strata in matrix_chunks
    ]


def _headline(decision: str, blockers: list[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    if decision == "real_corpus_default_on_validated":
        return (
            "PASS: broader real-corpus SEC default-on path is validated: "
            f"{summary['real_filing_count']} filings across {summary['issuer_hash_count']} issuers "
            f"met completeness and CompanyFacts value-correctness gates."
        )
    reasons = ", ".join(str(item["reason"]) for item in blockers[:3]) or "unknown"
    return f"FAIL/INCONCLUSIVE: broader real-corpus SEC default-on path is blocked: {reasons}."


def _next_slice(*, pass_gate: bool, blockers: list[Mapping[str, Any]]) -> str:
    if pass_gate:
        return "sec_edgar_operator_surface_gated_value_reveal_v1"
    reasons = {str(item.get("reason") or "") for item in blockers}
    if "real_corpus_product_path_live_preflight_not_satisfied" in reasons:
        return "sec_edgar_real_corpus_product_path_runner_live_execution_v1"
    return "sec_edgar_arelle_extraction_coverage_remediation_then_gate_rerun_v1"


def _runtime_default_action(*, pass_gate: bool, current_default: bool) -> str:
    if pass_gate:
        return "keep_default_true" if current_default else "set_default_true"
    return "keep_default_false" if not current_default else "roll_back_default_false"


def _memory_db_session() -> Any:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()


def _waiting_rate_limit(original: Any) -> Any:
    def wait_then_enforce() -> None:
        for attempt in range(4):
            try:
                original()
                return
            except Exception as exc:
                if "sec_edgar_text_table_live_source_artifact_rate_limit_deferred" not in str(exc):
                    raise
                if attempt >= 3:
                    raise
                time.sleep(1.1)

    return wait_then_enforce


def _live_storage_dir(storage_dir: Path | None) -> Path:
    if storage_dir is not None:
        return _repo_path(storage_dir)
    return _repo_path(DEFAULT_LIVE_STORAGE / time.strftime("%Y%m%d%H%M%S", time.gmtime()))


def _repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _display_output_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return f"<external>/{resolved.name}"


def _storage_marker(path: Path) -> str:
    return stable_hash({"storage_dir_name": path.name, "parent_name": path.parent.name})[:24]


def _as_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _config_cutover_default_enabled() -> bool:
    text = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
    return (
        "layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n"
        "        default=True,"
    ) in text


def _apply_runtime_default_decision(report: Mapping[str, Any]) -> bool:
    decision = report.get("runtime_default_decision") if isinstance(report.get("runtime_default_decision"), Mapping) else {}
    desired = bool(decision.get("resulting_default_enabled"))
    config_path = ROOT / "backend/app/core/config.py"
    text = config_path.read_text(encoding="utf-8")
    old = (
        "layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n"
        "        default=False,"
    )
    new = (
        "layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n"
        "        default=True,"
    )
    desired_text = new if desired else old
    current_text = old if desired else new
    if desired_text in text:
        return False
    if current_text not in text:
        raise RuntimeError("sec_xbrl_arelle_cutover_default_pattern_not_found")
    config_path.write_text(text.replace(current_text, desired_text, 1), encoding="utf-8")
    return True


def _state(response: Mapping[str, Any], key: str) -> str:
    return str(response.get(key) or response.get("status") or "unknown")


def _blocked_reasons(response: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for reason in response.get("blocked_reasons") or []:
        if isinstance(reason, Mapping):
            reasons.append(str(reason.get("reason") or "blocked"))
    return reasons or ["blocked"]


def _safe_reason(exc: Exception) -> str:
    name = exc.__class__.__name__
    text = str(exc).replace("\\", "/")
    for marker in ("https://", "http://", ":/"):
        if marker in text:
            return name
    return f"{name}:{text[:120]}" if text else name


if __name__ == "__main__":
    raise SystemExit(main())
