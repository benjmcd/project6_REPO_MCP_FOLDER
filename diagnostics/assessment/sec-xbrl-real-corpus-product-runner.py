from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping


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
)
from app.services.layer3_utils import stable_hash


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json")
DEFAULT_LIVE_STORAGE = Path("backend/app/storage_test_runtime/sec-real-product-runner")
REQUIRED_FORMS = ("10-K", "10-Q", "20-F", "40-F", "6-K", "8-K")
REQUIRED_REAL_FILING_COUNT = 12
MATRIX_CHUNKS = (
    ("core", ("MSFT", "STLD", "SONY", "CCJ")),
    ("breadth", ("JPM", "MET", "PLD", "FIZZ")),
    ("expansion", ("XOM", "PFE", "UAL", "T")),
)
REQUIRED_ARELLE_ENV = (
    "SEC_XBRL_ARELLE_PYTHON",
    "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES",
    "SEC_XBRL_ARELLE_CACHE_DIR",
)


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
    parser.add_argument("--user-agent", default=os.environ.get("LAYER3_SEC_EDGAR_USER_AGENT", ""))
    parser.add_argument("--request-namespace", default="sec-xbrl-real-corpus-product-runner-v1")
    parser.add_argument(
        "--taxonomy-internet-connectivity",
        default=os.environ.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", "offline"),
        choices=("online", "offline"),
    )
    args = parser.parse_args()

    report = build_report(
        live=bool(args.live),
        storage_dir=Path(args.storage_dir) if args.storage_dir else None,
        user_agent=str(args.user_agent or ""),
        request_namespace=str(args.request_namespace or ""),
        taxonomy_internet_connectivity=str(args.taxonomy_internet_connectivity or "offline"),
    )
    output = _repo_path(Path(args.output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"headline={report['headline']}")
    return 0


def build_report(
    *,
    live: bool,
    storage_dir: Path | None = None,
    user_agent: str = "",
    request_namespace: str = "sec-xbrl-real-corpus-product-runner-v1",
    taxonomy_internet_connectivity: str = "offline",
    runner: Callable[[Path, str, str, str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    preflight = _live_preflight(live=live, user_agent=user_agent)
    rows: list[dict[str, Any]] = []
    storage_marker = None
    if preflight["state"] == "passed":
        live_storage = _live_storage_dir(storage_dir)
        storage_marker = _storage_marker(live_storage)
        run = runner or _run_live_product_path
        rows = run(
            live_storage,
            user_agent.strip(),
            request_namespace.strip() or "sec-xbrl-real-corpus-product-runner-v1",
            taxonomy_internet_connectivity,
        )

    summary = _summary(rows)
    criteria = _criteria(preflight, summary)
    blockers = [
        {
            "criterion": item["criterion"],
            "reason": item["blocked_reason"],
            "evidence": item["evidence"],
        }
        for item in criteria
        if item["state"] != "passed"
    ]
    decision = "real_corpus_product_path_ready" if not blockers else "real_corpus_product_path_blocked"
    return {
        "schema_id": "diagnostics.sec_xbrl_real_corpus_product_runner.v1",
        "target": "sec_edgar_real_corpus_product_path_runner_v1",
        "decision": decision,
        "headline": _headline(decision, blockers, summary),
        "live_sec_network_used": bool(live and preflight["state"] == "passed"),
        "fake_sec_client_used": False,
        "storage_dir_marker": storage_marker,
        "storage_dir_paths_redacted": True,
        "diagnostic_request_namespace_hash": stable_hash({"request_namespace": request_namespace})[:24],
        "matrix_chunks": _matrix_chunk_projection(),
        "preflight": preflight,
        "criteria": criteria,
        "blocking_reasons": blockers,
        "summary": summary,
        "per_matrix": rows,
        "redaction": {
            "raw_tickers_committed": False,
            "raw_accessions_committed": False,
            "raw_sec_urls_committed": False,
            "local_storage_roots_committed": False,
            "raw_values_committed": False,
            "identity_hash_only": True,
        },
        "non_goals_preserved": {
            "runtime_default_changed": False,
            "operator_value_reveal_enabled": False,
            "gate_b_product_package_ui_redesign_performed": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
            "new_layer3_source_shape_created": False,
        },
        "next_slice": (
            "sec_edgar_operator_surface_gated_value_reveal_v1"
            if decision == "real_corpus_product_path_ready"
            else "sec_edgar_real_corpus_product_path_runner_live_execution_v1"
        ),
    }


def _run_live_product_path(
    storage_dir: Path,
    user_agent: str,
    request_namespace: str,
    taxonomy_internet_connectivity: str,
) -> list[dict[str, Any]]:
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
            _run_matrix_chunk(label, matrix, db=db, request_namespace=request_namespace)
            for label, matrix in MATRIX_CHUNKS
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
    db: Any,
    request_namespace: str,
) -> dict[str, Any]:
    matrix_hash = stable_hash({"matrix": list(matrix)})[:24]
    row: dict[str, Any] = {
        "matrix_label": label,
        "matrix_ref_hash": matrix_hash,
        "raw_identity_redacted": True,
        "storage_path_redacted": True,
        "live_sec_network_used": True,
        "fake_sec_client_used": False,
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
    row.update(_validation_projection(validation))
    if validation.get("validation_state") != layer3_sec_edgar_real_company_corpus_validation.READY_STATE:
        return {
            **row,
            "pipeline_state": "blocked",
            "blocked_stage": "validation",
            "blocked_reasons": _blocked_reasons(validation),
        }
    delivery = _delivery(validation, label=label, db=db, request_namespace=request_namespace)
    row["delivery_status"] = _state(delivery, "delivery_status_provenance_state")
    if delivery.get("delivery_status_provenance_state") != layer3_sec_edgar_delivery_status_provenance.READY_STATE:
        return {**row, "pipeline_state": "blocked", "blocked_stage": "delivery", "blocked_reasons": _blocked_reasons(delivery)}
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


def _validation_projection(validation: Mapping[str, Any]) -> dict[str, Any]:
    records = [record for record in validation.get("filing_validation_records") or [] if isinstance(record, Mapping)]
    forms = Counter(str(record.get("form_type") or "unknown") for record in records)
    quality = [record.get("quality_evidence") or {} for record in records]
    metrics = [item.get("quality_metrics") or {} for item in quality if isinstance(item, Mapping)]
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
        "records_with_arelle_sidecar_output": sum(
            1 for record in records if "arelle_resolved_fact_authority_sidecar" in list(record.get("outputs_produced") or [])
        ),
        "records_with_selected_fact_authority_equal_to_sidecar": sum(
            1
            for record in records
            if (record.get("authority_hashes") or {}).get("fact_authority_receipt_hash")
            == (record.get("authority_hashes") or {}).get("arelle_sidecar_receipt_hash")
        ),
        "records_with_handoff_export_prepare": sum(
            1 for record in records if "handoff_export_prepare" in list(record.get("outputs_produced") or [])
        ),
        "resolved_fact_count": sum(int(item.get("resolved_fact_count") or 0) for item in metrics),
        "operator_surface_values_exposed": any(
            bool(item.get("operator_surface_values_exposed")) for item in metrics
        ),
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    forms: Counter[str] = Counter()
    for row in rows:
        forms.update(row.get("forms") or {})
    return {
        "matrix_chunk_count": len(rows),
        "ready_matrix_chunk_count": sum(1 for row in rows if row.get("pipeline_state") == "ready"),
        "blocked_matrix_chunk_count": sum(1 for row in rows if row.get("pipeline_state") != "ready"),
        "real_filing_count": sum(int(row.get("filing_count") or 0) for row in rows),
        "supported_record_count": sum(int(row.get("supported_count") or 0) for row in rows),
        "blocked_or_degraded_record_count": sum(int(row.get("blocked_or_degraded_count") or 0) for row in rows),
        "forms": dict(sorted(forms.items())),
        "required_forms": list(REQUIRED_FORMS),
        "required_forms_present": all(form in forms for form in REQUIRED_FORMS),
        "issuer_hash_count_sum": sum(int(row.get("issuer_hash_count") or 0) for row in rows),
        "resolved_fact_count": sum(int(row.get("resolved_fact_count") or 0) for row in rows),
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


def _criteria(preflight: Mapping[str, Any], summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _criterion(
            "live_preflight",
            preflight["state"] == "passed",
            preflight,
            "real_corpus_product_path_live_preflight_not_satisfied",
        ),
        _criterion(
            "broader_real_product_path_corpus",
            summary["real_filing_count"] >= REQUIRED_REAL_FILING_COUNT and summary["required_forms_present"],
            {
                "real_filing_count": summary["real_filing_count"],
                "required_real_filing_count": REQUIRED_REAL_FILING_COUNT,
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
            "product_path_readiness",
            summary["matrix_chunk_count"] > 0
            and summary["ready_matrix_chunk_count"] == summary["matrix_chunk_count"]
            and summary["delivery_ready_matrix_chunk_count"] == summary["matrix_chunk_count"]
            and summary["operator_inspection_ready_matrix_chunk_count"] == summary["matrix_chunk_count"]
            and summary["operator_product_surface_ready_matrix_chunk_count"] == summary["matrix_chunk_count"]
            and summary["durable_delivery_archive_ready_matrix_chunk_count"] == summary["matrix_chunk_count"],
            {
                "matrix_chunk_count": summary["matrix_chunk_count"],
                "ready_matrix_chunk_count": summary["ready_matrix_chunk_count"],
                "delivery_ready_matrix_chunk_count": summary["delivery_ready_matrix_chunk_count"],
                "operator_inspection_ready_matrix_chunk_count": summary["operator_inspection_ready_matrix_chunk_count"],
                "operator_product_surface_ready_matrix_chunk_count": summary[
                    "operator_product_surface_ready_matrix_chunk_count"
                ],
                "durable_delivery_archive_ready_matrix_chunk_count": summary[
                    "durable_delivery_archive_ready_matrix_chunk_count"
                ],
            },
            "real_corpus_product_path_not_ready_across_all_matrix_chunks",
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
        "arelle_cutover_default_changed": False,
        "blocked_reasons": [
            *([] if live else ["live_execution_not_requested"]),
            *([] if user_agent.strip() else ["sec_user_agent_not_configured"]),
            *([] if not missing_env else ["arelle_environment_not_configured"]),
            *([] if arelle_python["configured"] else ["arelle_python_unavailable"]),
            *([] if taxonomy["configured"] else ["taxonomy_package_files_unavailable"]),
            *([] if cache["configured"] else ["arelle_cache_dir_unavailable"]),
        ],
    }


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


def _matrix_chunk_projection() -> list[dict[str, Any]]:
    return [
        {
            "matrix_label": label,
            "matrix_ref_hash": stable_hash({"matrix": list(matrix)})[:24],
            "issuer_count": len(matrix),
            "raw_identity_redacted": True,
        }
        for label, matrix in MATRIX_CHUNKS
    ]


def _headline(decision: str, blockers: list[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    if decision == "real_corpus_product_path_ready":
        return (
            "Broader real-corpus SEC product path is ready: "
            f"{summary['real_filing_count']} filings across required forms reached archive readiness."
        )
    reasons = ", ".join(str(item["reason"]) for item in blockers[:3]) or "unknown"
    return f"Broader real-corpus SEC product path remains blocked: {reasons}."


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


def _storage_marker(path: Path) -> str:
    return stable_hash({"storage_dir_name": path.name, "parent_name": path.parent.name})[:24]


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
