from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.services import layer3_sec_edgar_html_inline_xbrl_fact_material_bridge
from app.services.layer3_workbench_error import Layer3WorkbenchError


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-bridge-cutover-report.json")
csv.field_size_limit(10_000_000)
REQUIRED_TYPED_FIELDS = (
    "concept_qname",
    "concept_namespace",
    "concept_local_name",
    "concept_standard",
    "concept_extension",
    "concept_resolved_from_dts",
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
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Quarantined SEC/iXBRL bridge cutover proof. Reads persisted Arelle sidecar "
            "receipts and runs the fact-material bridge with the cutover flag enabled. "
            "This script is diagnostic-only and is not Layer 3 runtime authority."
        )
    )
    parser.add_argument("--storage-dir", action="append", default=[])
    parser.add_argument("--source-report", action="append", default=[])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--request-namespace", default="sec-xbrl-bridge-cutover-v1")
    args = parser.parse_args()
    if not args.storage_dir:
        raise RuntimeError("at least one --storage-dir is required")

    report = build_report(
        storage_dirs=[Path(item) for item in args.storage_dir],
        source_reports=[Path(item) for item in args.source_report],
        request_namespace=args.request_namespace,
    )
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"headline={report['headline']}")
    return 0


def build_report(*, storage_dirs: list[Path], source_reports: list[Path], request_namespace: str) -> dict[str, Any]:
    metadata = _metadata_from_reports(source_reports)
    rows: list[dict[str, Any]] = []
    storage_markers: list[str] = []
    previous_storage_dir = settings.storage_dir
    previous_cutover = getattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False)
    try:
        for raw_dir in storage_dirs:
            storage_dir = _resolve_repo_path(raw_dir)
            storage_markers.append(_sha256_text(storage_dir.name)[:24])
            rows.extend(_run_storage_dir(storage_dir, metadata=metadata, request_namespace=request_namespace))
    finally:
        settings.storage_dir = previous_storage_dir
        settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = previous_cutover

    ready_rows = [row for row in rows if row["bridge_state"] == layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.READY_STATE]
    not_applicable_rows = [row for row in rows if row["bridge_state"] == "not_applicable_no_inline_xbrl"]
    blocked_rows = [row for row in rows if row["bridge_state"] not in {layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.READY_STATE, "not_applicable_no_inline_xbrl"}]
    sidecar_total = sum(int(row.get("sidecar_resolved_fact_count") or 0) for row in rows)
    bridge_total = sum(int(row.get("bridge_fact_count") or 0) for row in ready_rows)
    all_ready_match = all(row.get("bridge_fact_count_matches_sidecar") is True for row in ready_rows)
    twenty_f = next((row for row in rows if row.get("form") == "20-F"), None)
    forty_f = next((row for row in rows if row.get("form") == "40-F"), None)
    verdict = "trustworthy_for_gated_cutover" if not blocked_rows and all_ready_match else "blocked_or_incomplete_cutover_proof"
    return {
        "schema_id": "diagnostics.sec_xbrl_bridge_cutover_report.v1",
        "target": "sec_edgar_arelle_fact_authority_input_cutover_v1",
        "headline": (
            f"{verdict}: flag-on bridge materialized {bridge_total}/{sidecar_total} sidecar facts "
            f"across {len(ready_rows)} inline filings; {len(not_applicable_rows)} zero-inline filings were not applicable."
        ),
        "verdict": verdict,
        "source_reports": [_repo_display_path(path) for path in source_reports],
        "storage_dir_markers": sorted(storage_markers),
        "storage_dir_paths_redacted": True,
        "diagnostic_request_namespace_hash": _sha256_text(request_namespace)[:24],
        "runtime_default_changed": False,
        "flag_enabled_only_inside_diagnostic": True,
        "synchronous_arelle_invocation_performed_by_bridge": False,
        "regex_fallback_performed_under_flag": False,
        "new_layer3_source_shape_created": False,
        "candidate_b_sec_routing_performed": False,
        "value_unredaction_performed": False,
        "internal_analysis_layer_value_materialization_performed": True,
        "operator_surface_value_exposure_performed": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
        "summary": {
            "real_filing_count": len(rows),
            "inline_bridge_ready_count": len(ready_rows),
            "zero_inline_not_applicable_count": len(not_applicable_rows),
            "blocked_count": len(blocked_rows),
            "regex_fact_authority_fact_count": sum(int(row.get("production_factauthority_fact_count") or 0) for row in rows),
            "sidecar_resolved_fact_count": sidecar_total,
            "bridge_fact_count": bridge_total,
            "bridge_matches_sidecar_all_ready_rows": all_ready_match,
            "required_typed_fields_present_all_ready_rows": all(
                row.get("required_typed_fields_present") is True for row in ready_rows
            ),
            "raw_values_detected_in_dataset_rows": any(
                row.get("raw_values_detected_in_dataset_rows") is True for row in ready_rows
            ),
            "effective_value_nonempty_count": sum(int(row.get("effective_value_nonempty_count") or 0) for row in ready_rows),
            "lexical_value_nonempty_count": sum(int(row.get("lexical_value_nonempty_count") or 0) for row in ready_rows),
            "effective_value_empty_count": sum(int(row.get("effective_value_empty_count") or 0) for row in ready_rows),
            "value_hash_present_count": sum(int(row.get("value_hash_present_count") or 0) for row in ready_rows),
            "twenty_f_bridge_fact_count": twenty_f.get("bridge_fact_count") if twenty_f else None,
            "twenty_f_sidecar_resolved_fact_count": twenty_f.get("sidecar_resolved_fact_count") if twenty_f else None,
            "forty_f_bridge_fact_count": forty_f.get("bridge_fact_count") if forty_f else None,
            "forty_f_sidecar_resolved_fact_count": forty_f.get("sidecar_resolved_fact_count") if forty_f else None,
        },
        "per_fixture": rows,
    }


def _run_storage_dir(storage_dir: Path, *, metadata: dict[str, dict[str, Any]], request_namespace: str) -> list[dict[str, Any]]:
    settings.storage_dir = str(storage_dir)
    settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = True
    bootstrap_storage_tree(settings.storage_dir)
    facts = _read_receipts(storage_dir, "layer3-sec-edgar-html-inline-xbrl-fact-authority", "receipts")
    sidecars = _read_receipts(storage_dir, "layer3-sec-edgar-arelle-resolved-fact-authority", "receipts")
    facts_by_hash = {str(item.get("fact_authority_receipt_hash") or ""): item for item in facts}
    db = _memory_db_session()
    try:
        return [
            _run_sidecar_bridge(
                sidecar,
                facts_by_hash=facts_by_hash,
                metadata=metadata,
                db=db,
                request_namespace=request_namespace,
            )
            for sidecar in sorted(sidecars, key=lambda item: str(item.get("sidecar_receipt_hash") or ""))
        ]
    finally:
        db.close()


def _run_sidecar_bridge(
    sidecar: Mapping[str, Any],
    *,
    facts_by_hash: Mapping[str, Mapping[str, Any]],
    metadata: Mapping[str, Mapping[str, Any]],
    db: Any,
    request_namespace: str,
) -> dict[str, Any]:
    sidecar_hash = str(sidecar.get("sidecar_receipt_hash") or "")
    row_meta = dict(metadata.get(sidecar_hash) or {})
    row = {
        "fixture_hash": row_meta.get("fixture_hash"),
        "form": row_meta.get("form", "unknown"),
        "issuer_by_hash": row_meta.get("issuer_by_hash"),
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_resolved_fact_count": int(sidecar.get("resolved_fact_count") or 0),
        "sidecar_independent_inline_fact_count": row_meta.get("sidecar_independent_inline_fact_count"),
        "production_factauthority_fact_count": row_meta.get("production_factauthority_fact_count"),
        "values_redacted_in_report": True,
        "raw_identity_redacted": True,
        "storage_path_redacted": True,
    }
    regex_hash = str(sidecar.get("regex_fact_authority_receipt_hash") or "")
    if int(sidecar.get("resolved_fact_count") or 0) == 0 and not regex_hash:
        return {
            **row,
            "bridge_state": "not_applicable_no_inline_xbrl",
            "bridge_fact_count": 0,
            "bridge_fact_count_matches_sidecar": True,
            "not_applicable_reason": "zero_inline_xbrl_sidecar_has_no_regex_fact_authority",
        }
    fact = facts_by_hash.get(regex_hash)
    if fact is None:
        return {
            **row,
            "bridge_state": "blocked_missing_regex_fact_authority",
            "bridge_fact_count": None,
            "bridge_fact_count_matches_sidecar": False,
            "blocked_reasons": ["regex_fact_authority_receipt_not_found_for_sidecar"],
        }
    row["production_factauthority_fact_count"] = int(fact.get("fact_count") or 0)
    payload = _bridge_payload(sidecar=sidecar, fact=fact, request_namespace=request_namespace)
    try:
        bridge = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
            payload,
            db,
        )
    except Layer3WorkbenchError as exc:
        return {
            **row,
            "bridge_state": "blocked",
            "bridge_fact_count": None,
            "bridge_fact_count_matches_sidecar": False,
            "blocked_reasons": [str(exc.error_code)],
            "blocked_fields": list(exc.blocked_fields),
        }
    dataset_checks = _dataset_checks(bridge, sidecar)
    bridge_count = int((bridge.get("materialization_summary") or {}).get("fact_count") or 0)
    return {
        **row,
        "bridge_state": bridge.get("bridge_state"),
        "bridge_fact_count": bridge_count,
        "bridge_fact_count_matches_sidecar": bridge_count == int(sidecar.get("resolved_fact_count") or 0),
        "bridge_fact_authority_input_mode": bridge.get("fact_authority_input_mode"),
        "bridge_arelle_sidecar_receipt_hash_matches": bridge.get("arelle_sidecar_receipt_hash") == sidecar_hash,
        "bridge_resolved_fact_inventory_hash_matches": (
            (bridge.get("authority_hashes") or {}).get("resolved_fact_inventory_hash")
            == sidecar.get("resolved_fact_inventory_hash")
        ),
        "dataset_version_hash": bridge.get("dataset_version_hash"),
        "materialization_receipt_hash": bridge.get("materialization_receipt_hash"),
        "material_preview_hash": bridge.get("material_preview_hash"),
        "required_typed_fields_present": dataset_checks["required_typed_fields_present"],
        "missing_typed_fields": dataset_checks["missing_typed_fields"],
        "dataset_row_count": dataset_checks["dataset_row_count"],
        "period_field_nonempty_count": dataset_checks["period_field_nonempty_count"],
        "unit_field_nonempty_count": dataset_checks["unit_field_nonempty_count"],
        "explicit_dimension_row_count": dataset_checks["explicit_dimension_row_count"],
        "typed_dimension_row_count": dataset_checks["typed_dimension_row_count"],
        "concept_namespace_nonempty_count": dataset_checks["concept_namespace_nonempty_count"],
        "raw_values_detected_in_dataset_rows": dataset_checks["raw_values_detected_in_dataset_rows"],
        "analysis_layer_values_materialized": dataset_checks["analysis_layer_values_materialized"],
        "effective_value_nonempty_count": dataset_checks["effective_value_nonempty_count"],
        "effective_value_empty_count": dataset_checks["effective_value_empty_count"],
        "lexical_value_nonempty_count": dataset_checks["lexical_value_nonempty_count"],
        "value_text_nonempty_count": dataset_checks["value_text_nonempty_count"],
        "value_hash_present_count": dataset_checks["value_hash_present_count"],
        "value_redacted_false_count": dataset_checks["value_redacted_false_count"],
    }


def _bridge_payload(*, sidecar: Mapping[str, Any], fact: Mapping[str, Any], request_namespace: str) -> dict[str, Any]:
    sidecar_hash = str(sidecar["sidecar_receipt_hash"])
    return {
        "client_request_id": f"sec-xbrl-bridge-cutover-{_sha256_text(request_namespace)[:8]}-{sidecar_hash[:16]}",
        "bridge_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.OPERATOR_DECISION,
        "fact_authority_receipt_id": fact["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": fact["fact_authority_receipt_hash"],
        "arelle_sidecar_receipt_id": sidecar["sidecar_receipt_id"],
        "arelle_sidecar_receipt_hash": sidecar_hash,
        "parser_receipt_id": sidecar["parser_receipt_id"],
        "parser_receipt_hash": sidecar["parser_receipt_hash"],
        "expected_connector_receipt_hash": sidecar["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": sidecar["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": sidecar["source_artifact_receipt_hash"],
        "expected_content_sha256": sidecar["content_sha256"],
        "expected_primary_document_hash": sidecar["primary_document_hash"],
        "expected_document_inventory_hash": sidecar["document_inventory_hash"],
        "expected_content_order_hash": sidecar["content_order_hash"],
        "expected_table_candidate_inventory_hash": sidecar["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": sidecar["inline_xbrl_marker_inventory_hash"],
        "expected_fact_inventory_hash": sidecar["resolved_fact_inventory_hash"],
        "expected_diagnostics_hash": sidecar["diagnostics_hash"],
        "rollback_confirmed": True,
        "operator_confirmed": True,
    }


def _dataset_checks(bridge: Mapping[str, Any], sidecar: Mapping[str, Any]) -> dict[str, Any]:
    dataset_version_id = str(bridge["dataset_version_id"])
    csv_path = (
        Path(settings.storage_dir)
        / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
        / "datasets"
        / f"{dataset_version_id}.csv"
    )
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    missing = [field for field in REQUIRED_TYPED_FIELDS if field not in fieldnames]
    value_text_nonempty_count = sum(1 for row in rows if str(row.get("value_text") or "").strip())
    effective_value_nonempty_count = sum(1 for row in rows if str(row.get("effective_value_text") or "").strip())
    lexical_value_nonempty_count = sum(1 for row in rows if str(row.get("lexical_value_text") or "").strip())
    value_hash_present_count = sum(1 for row in rows if str(row.get("value_hash") or "").strip())
    value_redacted_false_count = sum(
        1 for row in rows if str(row.get("value_redacted") or "").strip().lower() not in {"true", "1"}
    )
    return {
        "required_typed_fields_present": not missing,
        "missing_typed_fields": missing,
        "dataset_row_count": len(rows),
        "period_field_nonempty_count": sum(
            1
            for row in rows
            if row.get("period_start") or row.get("period_end") or row.get("period_instant")
        ),
        "unit_field_nonempty_count": sum(1 for row in rows if row.get("unit_currency") or row.get("unit_measures_json")),
        "explicit_dimension_row_count": sum(1 for row in rows if row.get("explicit_dimension_count") not in {"", "0", None}),
        "typed_dimension_row_count": sum(1 for row in rows if row.get("typed_dimension_count") not in {"", "0", None}),
        "concept_namespace_nonempty_count": sum(1 for row in rows if row.get("concept_namespace")),
        "raw_values_detected_in_dataset_rows": effective_value_nonempty_count > 0 or lexical_value_nonempty_count > 0,
        "analysis_layer_values_materialized": value_hash_present_count == len(rows),
        "effective_value_nonempty_count": effective_value_nonempty_count,
        "effective_value_empty_count": len(rows) - effective_value_nonempty_count,
        "lexical_value_nonempty_count": lexical_value_nonempty_count,
        "value_text_nonempty_count": value_text_nonempty_count,
        "value_hash_present_count": value_hash_present_count,
        "value_redacted_false_count": value_redacted_false_count,
    }


def _read_receipts(storage_dir: Path, *parts: str) -> list[dict[str, Any]]:
    receipt_dir = storage_dir.joinpath(*parts)
    if not receipt_dir.exists():
        return []
    receipts: list[dict[str, Any]] = []
    for path in sorted(receipt_dir.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            receipts.append(value)
    return receipts


def _metadata_from_reports(paths: list[Path]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for raw_path in paths:
        path = _resolve_repo_path(raw_path)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("per_fixture") or []:
            if not isinstance(row, Mapping):
                continue
            sidecar_hash = str(row.get("sidecar_receipt_hash") or "")
            if not sidecar_hash:
                continue
            output[sidecar_hash] = {
                "fixture_hash": row.get("fixture_hash"),
                "form": row.get("form"),
                "issuer_by_hash": row.get("issuer_by_hash"),
                "production_factauthority_fact_count": row.get("production_factauthority_fact_count"),
                "sidecar_independent_inline_fact_count": row.get("sidecar_independent_inline_fact_count"),
            }
    return output


def _memory_db_session() -> Any:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()


def _resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else (ROOT / path).resolve()


def _repo_display_path(path: Path) -> str:
    resolved = _resolve_repo_path(path)
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{_sha256_text(str(resolved))[:24]}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
