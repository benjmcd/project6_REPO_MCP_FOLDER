from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_xbrl_sidecar,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-report.json")
DEFAULT_CORPUS_OUTPUT = Path("diagnostics/assessment/sec-xbrl-corpus.json")
DEFAULT_LIVE_STORAGE = Path("backend/app/storage_test_runtime/sec-xbrl-measure")
SCAN_ROOTS = (Path("backend/tests"), Path("tests"))

SEC_DOCUMENT_RE = re.compile(r"<SEC-DOCUMENT\b.*?</SEC-DOCUMENT>", re.IGNORECASE | re.DOTALL)
HTML_IX_RE = re.compile(r"<html\b[^>]*(?:inlineXBRL|xmlns:ix)[\s\S]*?</html>", re.IGNORECASE)
CURRENT_FACT_RE = re.compile(
    r"<\s*(?P<tag>ix:(?:nonFraction|nonNumeric|fraction))\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)</\s*(?P=tag)\s*>",
    re.IGNORECASE | re.DOTALL,
)
SHADOW_FACT_RE = re.compile(
    r"<\s*(?P<tag>(?:[A-Za-z_][\w.-]*:)?(?:nonFraction|nonNumeric|fraction))\b(?P<attrs>[^>]*)"
    r"(?:>(?P<body>.*?)</\s*(?P=tag)\s*>|/?>)",
    re.IGNORECASE | re.DOTALL,
)
ATTR_RE = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+))")
FORM_RE = re.compile(
    r"<(?:CONFORMED-SUBMISSION-TYPE|TYPE)>\s*([A-Z0-9/-]+)",
    re.IGNORECASE,
)
HIDDEN_RE = re.compile(r"<\s*ix:hidden\b.*?</\s*ix:hidden\s*>", re.IGNORECASE | re.DOTALL)
CONTINUATION_RE = re.compile(r"<\s*ix:continuation\b", re.IGNORECASE)
CONTEXT_RE = re.compile(r"<\s*(?:[A-Za-z_][\w.-]*:)?context\b", re.IGNORECASE)
UNIT_RE = re.compile(r"<\s*(?:[A-Za-z_][\w.-]*:)?unit\b", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Quarantined SEC/iXBRL coverage measurement. This is not runtime authority "
            "and must not be imported by Layer 3 services."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--corpus", default="")
    parser.add_argument("--run-live-corpus", action="store_true")
    parser.add_argument("--corpus-output", default=str(DEFAULT_CORPUS_OUTPUT))
    parser.add_argument("--storage-dir", default="")
    parser.add_argument("--user-agent", default=os.environ.get("LAYER3_SEC_EDGAR_USER_AGENT", ""))
    parser.add_argument("--company-matrix", default="")
    parser.add_argument("--arelle-python", default=os.environ.get("ARELLE_PYTHON", ""))
    parser.add_argument("--taxonomy-packages", default=os.environ.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", ""))
    parser.add_argument("--taxonomy-cache-dir", default=os.environ.get("SEC_XBRL_ARELLE_CACHE_DIR", ""))
    parser.add_argument(
        "--taxonomy-internet-connectivity",
        default=os.environ.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", "offline"),
        choices=("online", "offline"),
    )
    args = parser.parse_args()

    if args.storage_dir:
        _override_storage_dir(Path(args.storage_dir))
    elif args.run_live_corpus:
        _override_storage_dir(DEFAULT_LIVE_STORAGE / time.strftime("%Y%m%d%H%M%S", time.gmtime()))

    previous_cutover = getattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False)
    if args.run_live_corpus:
        settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = True
    try:
        report = build_report(
            arelle_python=args.arelle_python,
            corpus_path=Path(args.corpus) if args.corpus else None,
            run_live_corpus=args.run_live_corpus,
            corpus_output=Path(args.corpus_output),
            user_agent=args.user_agent,
            company_matrix=tuple(
                item.strip().upper()
                for item in args.company_matrix.split(",")
                if item.strip()
            ),
            taxonomy_packages=args.taxonomy_packages,
            taxonomy_cache_dir=args.taxonomy_cache_dir,
            taxonomy_internet_connectivity=args.taxonomy_internet_connectivity,
        )
    finally:
        settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled = previous_cutover
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"headline={report['headline']}")
    return 0


def build_report(
    *,
    arelle_python: str = "",
    corpus_path: Path | None = None,
    run_live_corpus: bool = False,
    corpus_output: Path = DEFAULT_CORPUS_OUTPUT,
    user_agent: str = "",
    company_matrix: tuple[str, ...] = (),
    taxonomy_packages: str = "",
    taxonomy_cache_dir: str = "",
    taxonomy_internet_connectivity: str = "offline",
) -> dict[str, Any]:
    candidates = list(_inventoried_ixbrl_candidates(include_storage=not run_live_corpus))
    if corpus_path is not None:
        candidates.extend(_inventoried_corpus_candidates(corpus_path))
    live_manifest: dict[str, Any] | None = None
    if run_live_corpus:
        live_manifest = _run_live_corpus(
            user_agent=user_agent,
            company_matrix=company_matrix,
            arelle_python=arelle_python,
            corpus_output=corpus_output,
            taxonomy_packages=taxonomy_packages,
            taxonomy_cache_dir=taxonomy_cache_dir,
            taxonomy_internet_connectivity=taxonomy_internet_connectivity,
        )
    real_candidates = [item for item in candidates if item["fixture_class"] == "real_filing"]
    if live_manifest:
        real_candidates.extend(list(live_manifest.get("filings") or []))
    arelle = _arelle_status(arelle_python=arelle_python, has_real_input=bool(real_candidates))
    rows = [_row_for_candidate(candidate, real_input_available=bool(real_candidates)) for candidate in candidates]
    if live_manifest:
        rows.extend(list(live_manifest.get("per_fixture") or []))
    headline = _headline(rows=rows, real_input_available=bool(real_candidates))
    storage = _storage_inventory()
    committed_candidates = [item for item in candidates if item.get("source_kind") == "committed_test_source"]
    synthetic_candidates = [item for item in candidates if item.get("fixture_class") == "synthetic_stub"]
    primary_companyfacts = _primary_oracle_status(live_manifest=live_manifest)
    gold_arelle = _gold_oracle_status(live_manifest=live_manifest, fallback=arelle)
    return {
        "schema_id": "diagnostics.sec_xbrl_measure.v1",
        "purpose": "Measure whether Strategy A coverage/fact counts are trustworthy without mutating runtime authority.",
        "runtime_authority_created": False,
        "parser_expansion_performed": False,
        "value_unredaction_performed": False,
        "candidate_b_sec_routing_performed": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
        "identity_redaction": {
            "raw_tickers_urls_paths_storage_roots_committed": False,
            "fixture_identity_hash_only": True,
        },
        "inventory_summary": {
            "committed_ixbrl_candidate_count": len(committed_candidates),
            "real_filing_candidate_count": len(real_candidates),
            "synthetic_stub_candidate_count": len(synthetic_candidates),
            **storage,
            "retained_artifacts_observed": storage["storage_dir_file_count"] > 0,
            "retained_artifact_byte_status": storage["retained_artifact_byte_status"],
            "live_corpus_run_performed": run_live_corpus,
        },
        "live_corpus_manifest": live_manifest["manifest"] if live_manifest else None,
        "oracle_status": {
            "primary_companyfacts": primary_companyfacts,
            "gold_arelle": gold_arelle,
            "sanity_shadow_parse": {
                "oracle_used": bool(candidates),
                "confidence": "low_lower_bound",
                "reason": (
                    "Counts fact-bearing inline XBRL elements by tag shape only and shares blind spots "
                    "with the regex parser under test."
                ),
            },
        },
        "sidecar_summary": _sidecar_summary(rows),
        "companyfacts_effective_value_correctness": _companyfacts_effective_value_summary(rows),
        "per_fixture": rows,
        "headline": headline,
    }


def _sidecar_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [row for row in rows if row.get("sidecar_state") == layer3_sec_xbrl_sidecar.READY_STATE]
    counted = [row for row in ready if isinstance(row.get("sidecar_resolved_fact_count"), int)]
    return {
        "schema_id": "diagnostics.sec_xbrl_sidecar_summary.v1",
        "sidecar_target": layer3_sec_xbrl_sidecar.SIDECAR_MODE,
        "ready_filing_count": len(ready),
        "measured_filing_count": len(rows),
        "arelle_dependency": f"{layer3_sec_xbrl_sidecar.ARELLE_PACKAGE}=={layer3_sec_xbrl_sidecar.ARELLE_VERSION}",
        "resolved_fact_count": sum(int(row.get("sidecar_resolved_fact_count") or 0) for row in counted),
        "recovered_vs_regex": sum(int(row.get("sidecar_recovered_vs_regex") or 0) for row in counted if isinstance(row.get("sidecar_recovered_vs_regex"), int)),
        "period_resolved_count": sum(int(row.get("sidecar_period_resolved_count") or 0) for row in counted),
        "unit_resolved_count": sum(int(row.get("sidecar_unit_resolved_count") or 0) for row in counted),
        "explicit_dimension_fact_count": sum(int(row.get("sidecar_explicit_dimension_fact_count") or 0) for row in counted),
        "typed_dimension_fact_count": sum(int(row.get("sidecar_typed_dimension_fact_count") or 0) for row in counted),
        "concept_resolved_from_dts_count": sum(int(row.get("sidecar_concept_resolved_from_dts_count") or 0) for row in counted),
        "concept_unresolved_from_dts_count": sum(int(row.get("sidecar_concept_unresolved_from_dts_count") or 0) for row in counted),
        "independent_inline_fact_count": sum(int(row.get("sidecar_independent_inline_fact_count") or 0) for row in counted),
        "independent_inline_fact_count_all_reconciled": all(row.get("sidecar_independent_inline_fact_count_reconciled") is True for row in counted),
        "taxonomy_package_loaded_all_ready_rows": all(row.get("sidecar_taxonomy_package_loaded") is True for row in counted),
        "max_loaded_document_count": max([int(row.get("sidecar_loaded_document_count") or 0) for row in counted] or [0]),
        "values_redacted_in_report": True,
        "runtime_default_changed": False,
        "bridge_gate_b_product_package_ui_mutated": False,
    }


def _companyfacts_effective_value_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counted = [
        row
        for row in rows
        if isinstance(row.get("companyfacts_effective_value_match_count"), int)
        and isinstance(row.get("companyfacts_effective_value_compared_count"), int)
    ]
    compared = sum(int(row.get("companyfacts_effective_value_compared_count") or 0) for row in counted)
    matched = sum(int(row.get("companyfacts_effective_value_match_count") or 0) for row in counted)
    return {
        "schema_id": "diagnostics.sec_xbrl_companyfacts_effective_value_correctness.v1",
        "oracle": "primary_companyfacts_us_gaap_dei_accession_scope_non_dimensional_numeric_intersection",
        "match_count": matched,
        "compared_count": compared,
        "match_rate": round(matched / compared, 4) if compared else None,
        "values_redacted_in_report": True,
        "identity_redacted": True,
    }


def _inventoried_ixbrl_candidates(*, include_storage: bool = True) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    roots = (*SCAN_ROOTS, _resolved_storage_dir()) if include_storage else SCAN_ROOTS
    for root in roots:
        base = ROOT / root
        if root.is_absolute():
            base = root
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            if path.suffix.lower() not in {".py", ".txt", ".htm", ".html", ".xml", ".json"}:
                continue
            text = _read_text(path)
            if "inlineXBRL" not in text and "ix:" not in text:
                continue
            for index, snippet in enumerate(_snippets(text), start=1):
                if not SHADOW_FACT_RE.search(snippet):
                    continue
                candidates.append(_candidate(path=path, snippet=snippet, index=index))
    return candidates


def _inventoried_corpus_candidates(corpus_path: Path) -> list[dict[str, Any]]:
    base = corpus_path if corpus_path.is_absolute() else ROOT / corpus_path
    if not base.exists():
        return []
    paths = [base] if base.is_file() else sorted(path for path in base.rglob("*") if path.is_file())
    candidates: list[dict[str, Any]] = []
    for path in paths:
        text = _read_text(path)
        for index, snippet in enumerate(_snippets(text), start=1):
            if SHADOW_FACT_RE.search(snippet):
                candidates.append(_candidate(path=path, snippet=snippet, index=index))
    return candidates


def _snippets(text: str) -> list[str]:
    sec_documents = SEC_DOCUMENT_RE.findall(text)
    if sec_documents:
        return sec_documents
    return HTML_IX_RE.findall(text)


def _candidate(*, path: Path, snippet: str, index: int) -> dict[str, Any]:
    rel = _safe_rel(path)
    fixture_hash = _sha256(snippet.encode("utf-8"))[:24]
    return {
        "fixture_hash": fixture_hash,
        "source_path_hash": _sha256(rel.encode("utf-8"))[:24],
        "source_path_redacted": True,
        "source_kind": _source_kind(path),
        "fixture_class": _fixture_class(path=path, snippet=snippet),
        "snippet_index": index,
        "byte_length": len(snippet.encode("utf-8")),
        "form": _form(snippet),
        "issuer_by_hash": _issuer_hash(snippet),
        "content_sha256": _sha256(snippet.encode("utf-8")),
    }


def _row_for_candidate(candidate: dict[str, Any], *, real_input_available: bool) -> dict[str, Any]:
    snippet = _snippet_by_hash(candidate["content_sha256"])
    current = list(CURRENT_FACT_RE.finditer(snippet))
    shadow = list(SHADOW_FACT_RE.finditer(snippet))
    missed_categories = _missed_categories(snippet=snippet, current_count=len(current), shadow_count=len(shadow))
    oracle_used = "sanity_shadow_parse_only"
    confidence = "low_lower_bound"
    if candidate["fixture_class"] != "real_filing" or not real_input_available:
        oracle_used = "none_real_oracle_unavailable_synthetic_fixture"
        confidence = "inconclusive"
    return {
        "fixture_hash": candidate["fixture_hash"],
        "form": candidate["form"],
        "fixture_class": candidate["fixture_class"],
        "source_kind": candidate["source_kind"],
        "issuer_by_hash": candidate["issuer_by_hash"],
        "current_parser_fact_count": len(current),
        "oracle_fact_count": len(shadow) if confidence != "inconclusive" else None,
        "oracle_used": oracle_used,
        "missed_count": max(len(shadow) - len(current), 0) if confidence != "inconclusive" else None,
        "missed_categories": missed_categories,
        "confidence": confidence,
        "shadow_lower_bound_fact_count": len(shadow),
        "context_element_count": len(CONTEXT_RE.findall(snippet)),
        "unit_element_count": len(UNIT_RE.findall(snippet)),
        "hidden_fact_bearing_count": _hidden_fact_count(snippet),
        "continuation_element_count": len(CONTINUATION_RE.findall(snippet)),
        "continued_at_reference_count": len(re.findall(r"\bcontinuedAt\s*=", snippet, flags=re.IGNORECASE)),
        "text_segment_cap_impact_assessed": "not_applicable_to_fact_count_measurement",
    }


def _snippet_by_hash(content_sha256: str) -> str:
    for root in (*SCAN_ROOTS, _resolved_storage_dir()):
        base = ROOT / root
        if root.is_absolute():
            base = root
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            text = _read_text(path)
            for snippet in _snippets(text):
                if _sha256(snippet.encode("utf-8")) == content_sha256:
                    return snippet
    raise RuntimeError(f"snippet not found for hash {content_sha256[:12]}")


def _missed_categories(*, snippet: str, current_count: int, shadow_count: int) -> list[str]:
    categories: list[str] = []
    if shadow_count > current_count:
        categories.append("prefix_or_shape_not_matched_by_current_regex")
    if _hidden_fact_count(snippet):
        categories.append("ix_hidden_present")
    if CONTINUATION_RE.search(snippet) or re.search(r"\bcontinuedAt\s*=", snippet, flags=re.IGNORECASE):
        categories.append("continuation_present")
    if CONTEXT_RE.search(snippet):
        categories.append("contexts_present_but_unresolved")
    if UNIT_RE.search(snippet):
        categories.append("units_present_but_unresolved")
    if not categories:
        categories.append("none_observed_in_fixture")
    return categories


def _run_live_corpus(
    *,
    user_agent: str,
    company_matrix: tuple[str, ...],
    arelle_python: str,
    corpus_output: Path,
    taxonomy_packages: str,
    taxonomy_cache_dir: str,
    taxonomy_internet_connectivity: str,
) -> dict[str, Any]:
    if not user_agent.strip():
        raise RuntimeError("live corpus acquisition requires --user-agent or LAYER3_SEC_EDGAR_USER_AGENT")
    previous = {
        "enabled": settings.layer3_sec_edgar_live_network_enabled,
        "user_agent": settings.layer3_sec_edgar_user_agent,
        "rate": settings.layer3_sec_edgar_rate_limit_per_second,
        "max_bytes": settings.layer3_sec_edgar_max_bytes,
        "enforce_rate_limit": layer3_sec_edgar_live_source_artifact._enforce_rate_limit,
    }
    settings.layer3_sec_edgar_live_network_enabled = True
    settings.layer3_sec_edgar_user_agent = user_agent.strip()
    settings.layer3_sec_edgar_rate_limit_per_second = 1
    settings.layer3_sec_edgar_max_bytes = 120_000_000
    previous_arelle_python = os.environ.get("SEC_XBRL_ARELLE_PYTHON")
    previous_taxonomy_packages = os.environ.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES")
    previous_taxonomy_cache_dir = os.environ.get("SEC_XBRL_ARELLE_CACHE_DIR")
    previous_taxonomy_internet = os.environ.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY")
    if arelle_python:
        os.environ["SEC_XBRL_ARELLE_PYTHON"] = arelle_python
    if taxonomy_packages:
        os.environ["SEC_XBRL_ARELLE_TAXONOMY_PACKAGES"] = taxonomy_packages
    if taxonomy_cache_dir:
        os.environ["SEC_XBRL_ARELLE_CACHE_DIR"] = taxonomy_cache_dir
    os.environ["SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY"] = taxonomy_internet_connectivity
    layer3_sec_edgar_live_source_artifact._enforce_rate_limit = _waiting_rate_limit(
        previous["enforce_rate_limit"]
    )
    bootstrap_storage_tree(settings.storage_dir)
    try:
        return _run_live_corpus_inner(
            company_matrix=company_matrix,
            arelle_python=arelle_python,
            corpus_output=corpus_output,
            user_agent=user_agent.strip(),
        )
    finally:
        settings.layer3_sec_edgar_live_network_enabled = previous["enabled"]
        settings.layer3_sec_edgar_user_agent = previous["user_agent"]
        settings.layer3_sec_edgar_rate_limit_per_second = previous["rate"]
        settings.layer3_sec_edgar_max_bytes = previous["max_bytes"]
        if previous_arelle_python is None:
            os.environ.pop("SEC_XBRL_ARELLE_PYTHON", None)
        else:
            os.environ["SEC_XBRL_ARELLE_PYTHON"] = previous_arelle_python
        if previous_taxonomy_packages is None:
            os.environ.pop("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", None)
        else:
            os.environ["SEC_XBRL_ARELLE_TAXONOMY_PACKAGES"] = previous_taxonomy_packages
        if previous_taxonomy_cache_dir is None:
            os.environ.pop("SEC_XBRL_ARELLE_CACHE_DIR", None)
        else:
            os.environ["SEC_XBRL_ARELLE_CACHE_DIR"] = previous_taxonomy_cache_dir
        if previous_taxonomy_internet is None:
            os.environ.pop("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", None)
        else:
            os.environ["SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY"] = previous_taxonomy_internet
        layer3_sec_edgar_live_source_artifact._enforce_rate_limit = previous["enforce_rate_limit"]


def _waiting_rate_limit(original: Any) -> Any:
    def wait_then_enforce() -> None:
        for attempt in range(4):
            try:
                original()
                return
            except Layer3WorkbenchError as exc:
                if "sec_edgar_text_table_live_source_artifact_rate_limit_deferred" not in str(exc):
                    raise
                if attempt >= 3:
                    raise
                time.sleep(1.1)

    return wait_then_enforce


def _run_live_corpus_inner(
    *,
    company_matrix: tuple[str, ...],
    arelle_python: str,
    corpus_output: Path,
    user_agent: str,
) -> dict[str, Any]:
    if not company_matrix:
        raise RuntimeError("live corpus acquisition requires --company-matrix")
    label = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    connector = layer3_sec_edgar_real_filing_acquisition_connector.acquire_sec_edgar_real_filing_validation_corpus(
        {
            "client_request_id": f"sec-xbrl-measure-live-{label}",
            "connector_mode": layer3_sec_edgar_real_filing_acquisition_connector.CONNECTOR_MODE,
            "operator_decision": layer3_sec_edgar_real_filing_acquisition_connector.OPERATOR_DECISION,
            "example_set_mode": layer3_sec_edgar_real_filing_acquisition_connector.EXAMPLE_SET_MODE,
            "company_matrix": list(company_matrix),
            "filing_selection_policy": layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_DISCOVERY_POLICY,
            "operator_confirmation": True,
        }
    )
    connector_receipt = layer3_sec_edgar_real_filing_acquisition_connector.read_sec_edgar_real_filing_acquisition_connector_receipt(
        connector["connector_receipt_id"],
        expected_connector_receipt_hash=connector["connector_receipt_hash"],
    )
    db = _memory_db_session()
    rows: list[dict[str, Any]] = []
    filings: list[dict[str, Any]] = []
    try:
        for index, acquisition in enumerate(connector["acquisition_receipts"], start=1):
            example_record = _example_record_for_acquisition(connector, str(acquisition["example_id"]))
            row = _process_live_filing(
                index=index,
                label=label,
                connector=connector,
                connector_receipt=connector_receipt,
                acquisition=acquisition,
                example_record=example_record,
                db=db,
                arelle_python=arelle_python,
                user_agent=user_agent,
            )
            rows.append(row)
            filings.append(
                {
                    "fixture_hash": row["fixture_hash"],
                    "fixture_class": "real_filing",
                    "form": row["form"],
                    "issuer_by_hash": row["issuer_by_hash"],
                }
            )
    finally:
        db.close()
    manifest = {
        "schema_id": "diagnostics.sec_xbrl_real_corpus_manifest.v1",
        "connector_receipt_hash": connector["connector_receipt_hash"],
        "connector_example_count": connector["corpus_manifest"]["example_count"],
        "processed_filing_count": len(rows),
        "forms": sorted({str(row["form"]) for row in rows}),
        "issuer_hashes": sorted({str(row["issuer_by_hash"]) for row in rows}),
        "source_identity_redacted": True,
        "raw_tickers_urls_paths_storage_roots_committed": False,
    }
    output = corpus_output if corpus_output.is_absolute() else ROOT / corpus_output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"manifest": manifest, "per_fixture": rows}, indent=2, sort_keys=True) + "\n")
    return {"manifest": manifest, "per_fixture": rows, "filings": filings}


def _process_live_filing(
    *,
    index: int,
    label: str,
    connector: Mapping[str, Any],
    connector_receipt: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    example_record: Mapping[str, Any],
    db: Any,
    arelle_python: str,
    user_agent: str,
) -> dict[str, Any]:
    live_receipt, content = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_bytes(
        str(acquisition["live_source_artifact_receipt_id"]),
        expected_live_source_artifact_receipt_hash=str(acquisition["live_source_artifact_receipt_hash"]),
    )
    text = content.decode("utf-8", errors="ignore")
    raw_identity = _raw_sec_identity(text)
    if not raw_identity["cik"]:
        raw_identity["cik"] = _cik_from_hash(str(example_record.get("cik_hash") or ""))
    parser = layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
        {
            "client_request_id": f"sec-xbrl-measure-parser-{label}-{index}",
            "parser_mode": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
            "operator_decision": layer3_sec_edgar_html_inline_xbrl_parser.OPERATOR_DECISION,
            "connector_receipt_id": connector["connector_receipt_id"],
            "connector_receipt_hash": connector["connector_receipt_hash"],
            "connector_example_id": acquisition["example_id"],
            "live_source_artifact_receipt_id": acquisition["live_source_artifact_receipt_id"],
            "live_source_artifact_receipt_hash": acquisition["live_source_artifact_receipt_hash"],
            "expected_source_artifact_receipt_hash": acquisition["source_artifact_receipt"]["source_artifact_receipt_hash"],
            "operator_confirmation": True,
        }
    )
    reparse = layer3_sec_edgar_html_inline_xbrl_parser.reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge(
        connector_receipt,
        connector_example_id=str(acquisition["example_id"]),
        retained_complete_submission_text=content,
    )
    primary = str(reparse.get("primary_document_text") or "")
    try:
        fact = layer3_sec_edgar_html_inline_xbrl_fact_authority.derive_sec_edgar_html_inline_xbrl_fact_authority(
            _fact_authority_payload(index=index, label=label, parser=parser)
        )
    except Layer3WorkbenchError as exc:
        return _blocked_fact_row(
            index=index,
            label=label,
            live_receipt=live_receipt,
            parser=parser,
            primary=primary,
            raw_identity=raw_identity,
            arelle_python=arelle_python,
            user_agent=user_agent,
            block=str(exc.args[0] if exc.args else exc).strip(),
        )
    companyfacts = _companyfacts_count(
        cik=raw_identity["cik"],
        accession=raw_identity["accession"],
        user_agent=user_agent,
    )
    sidecar = _sidecar_response(index=index, label=label, parser=parser, fact=fact, companyfacts=companyfacts)
    value_match = _companyfacts_value_match(sidecar=sidecar, companyfacts=companyfacts)
    bridge: dict[str, Any] | None = None
    classification: dict[str, Any] | None = None
    pipeline_block: str | None = None
    try:
        bridge = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
            _fact_material_payload(index=index, label=label, parser=parser, fact=fact, sidecar=sidecar),
            db,
        )
        if bridge.get("bridge_state") != layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.READY_STATE:
            pipeline_block = str(((bridge.get("status_projection") or {}).get("blocked_reasons") or [{}])[0].get("reason") or "bridge_blocked")
        elif bridge.get("fact_authority_input_mode") != layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.ARELLE_FACT_AUTHORITY_INPUT_MODE:
            classification = layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates(
                _classification_payload(index=index, label=label, parser=parser, fact=fact, bridge=bridge)
            )
    except Layer3WorkbenchError as exc:
        pipeline_block = str(exc.args[0] if exc.args else exc).strip()
    arelle = _arelle_fact_count(primary_document=primary, arelle_python=arelle_python)
    oracle_count = arelle.get("fact_count")
    if not isinstance(oracle_count, int):
        oracle_count = companyfacts.get("fact_count")
    production_count = int(fact.get("fact_count") or 0)
    missed_count = max(int(oracle_count) - production_count, 0) if isinstance(oracle_count, int) else None
    return {
        "fixture_hash": str(live_receipt["source_artifact_receipt"]["content_sha256"])[:24],
        "form": raw_identity["form"] or "unknown",
        "fixture_class": "real_filing",
        "issuer_by_hash": _sha256(raw_identity["cik"].encode("utf-8"))[:24] if raw_identity["cik"] else None,
        "production_factauthority_fact_count": production_count,
        **_sidecar_fields(sidecar),
        "companyfacts_fact_count": companyfacts.get("fact_count"),
        "companyfacts_oracle_used": companyfacts.get("oracle_used"),
        "companyfacts_confidence": companyfacts.get("confidence"),
        "companyfacts_effective_value_match_count": value_match["match_count"],
        "companyfacts_effective_value_compared_count": value_match["compared_count"],
        "companyfacts_effective_value_match_rate": value_match["match_rate"],
        "arelle_fact_count": arelle.get("fact_count"),
        "arelle_oracle_used": arelle.get("oracle_used"),
        "arelle_confidence": arelle.get("confidence"),
        "missed_count": missed_count,
        "missed_categories": _live_missed_categories(primary=primary, parser=parser, fact=fact),
        "confidence": _live_confidence(companyfacts=companyfacts, arelle=arelle),
        "fact_material_bridge_ready": bool(bridge and bridge.get("bridge_state") == layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.READY_STATE),
        "classification_receipt_hash": classification.get("classification_receipt_hash") if classification else None,
        "classification_ready": bool(
            classification
            and classification.get("classification_state")
            == layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.READY_STATE
        ),
        "downstream_pipeline_block": pipeline_block,
        "raw_identity_redacted": True,
        "fact_values_redacted": True,
    }


def _fact_authority_payload(*, index: int, label: str, parser: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "client_request_id": f"sec-xbrl-measure-fact-authority-{label}-{index}",
        "fact_authority_mode": layer3_sec_edgar_html_inline_xbrl_fact_authority.FACT_AUTHORITY_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_authority.OPERATOR_DECISION,
        "parser_receipt_id": parser["parser_receipt_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "expected_connector_receipt_hash": parser["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "expected_document_inventory_hash": parser["document_inventory_hash"],
        "expected_content_order_hash": parser["content_order_hash"],
        "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
        "operator_confirmation": True,
    }


def _sidecar_response(
    *,
    index: int,
    label: str,
    parser: Mapping[str, Any],
    fact: Mapping[str, Any] | None,
    companyfacts: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
            _sidecar_payload(index=index, label=label, parser=parser, fact=fact, companyfacts=companyfacts)
        )
    except Layer3WorkbenchError as exc:
        return {
            "status": "blocked",
            "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_blocked",
            "status_projection": {
                "blocked_reasons": [
                    {
                        "reason": str(exc.error_code),
                        "blocked_fields": list(exc.blocked_fields),
                    }
                ]
            },
        }


def _sidecar_payload(
    *,
    index: int,
    label: str,
    parser: Mapping[str, Any],
    fact: Mapping[str, Any] | None,
    companyfacts: Mapping[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_request_id": f"sec-xbrl-sidecar-{label}-{index}",
        "sidecar_mode": layer3_sec_xbrl_sidecar.SIDECAR_MODE,
        "operator_decision": layer3_sec_xbrl_sidecar.OPERATOR_DECISION,
        "parser_receipt_id": parser["parser_receipt_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "expected_connector_receipt_hash": parser["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "expected_document_inventory_hash": parser["document_inventory_hash"],
        "expected_content_order_hash": parser["content_order_hash"],
        "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
        "max_facts": layer3_sec_xbrl_sidecar.DEFAULT_MAX_FACTS,
        "operator_confirmation": True,
    }
    if fact and fact.get("fact_authority_receipt_id") and fact.get("fact_authority_receipt_hash"):
        payload["regex_fact_authority_receipt_id"] = fact["fact_authority_receipt_id"]
        payload["regex_fact_authority_receipt_hash"] = fact["fact_authority_receipt_hash"]
    if isinstance(companyfacts.get("fact_count"), int):
        payload["companyfacts_standard_fact_count"] = companyfacts["fact_count"]
        payload["companyfacts_oracle_confidence"] = companyfacts.get("confidence")
    return payload


def _sidecar_fields(sidecar: Mapping[str, Any]) -> dict[str, Any]:
    coverage = sidecar.get("coverage") if isinstance(sidecar.get("coverage"), Mapping) else {}
    parity = sidecar.get("parity") if isinstance(sidecar.get("parity"), Mapping) else {}
    diagnostics = sidecar.get("diagnostics") if isinstance(sidecar.get("diagnostics"), Mapping) else {}
    reasons = ((sidecar.get("status_projection") or {}).get("blocked_reasons") or []) if isinstance(sidecar.get("status_projection"), Mapping) else []
    return {
        "sidecar_state": sidecar.get("sidecar_state"),
        "sidecar_receipt_hash": sidecar.get("sidecar_receipt_hash"),
        "sidecar_resolved_fact_count": sidecar.get("resolved_fact_count"),
        "sidecar_recovered_vs_regex": parity.get("recovered_vs_regex"),
        "sidecar_period_resolved_count": coverage.get("period_resolved_count"),
        "sidecar_unit_resolved_count": coverage.get("unit_resolved_count"),
        "sidecar_explicit_dimension_fact_count": coverage.get("explicit_dimension_fact_count"),
        "sidecar_typed_dimension_fact_count": coverage.get("typed_dimension_fact_count"),
        "sidecar_concept_resolved_from_dts_count": coverage.get("concept_resolved_from_dts_count"),
        "sidecar_concept_unresolved_from_dts_count": coverage.get("concept_unresolved_from_dts_count"),
        "sidecar_hidden_fact_count": coverage.get("hidden_fact_count"),
        "sidecar_continued_fact_count": coverage.get("continued_fact_count"),
        "sidecar_standard_concept_count": coverage.get("standard_concept_count"),
        "sidecar_extension_concept_count": coverage.get("extension_concept_count"),
        "sidecar_taxonomy_package_loaded": diagnostics.get("taxonomy_package_loaded"),
        "sidecar_loaded_document_count": (diagnostics.get("document_set") or {}).get("loaded_document_count"),
        "sidecar_independent_inline_fact_count": diagnostics.get("independent_inline_fact_count"),
        "sidecar_independent_inline_fact_scanned_document_count": diagnostics.get("independent_inline_fact_scanned_document_count"),
        "sidecar_independent_inline_fact_document_count": diagnostics.get("independent_inline_fact_document_count"),
        "sidecar_independent_inline_fact_tally_hash": diagnostics.get("independent_inline_fact_tally_hash"),
        "sidecar_independent_inline_fact_document_tally": diagnostics.get("independent_inline_fact_document_tally"),
        "sidecar_independent_inline_fact_count_reconciled": diagnostics.get("independent_inline_fact_count_reconciled"),
        "sidecar_blocked_reasons": [str(item.get("reason")) for item in reasons if isinstance(item, Mapping)],
        "sidecar_values_redacted_in_report": True,
        "sidecar_local_receipt_retains_values": False,
        "sidecar_internal_value_store_state": (sidecar.get("internal_value_store") or {}).get("store_state") if isinstance(sidecar.get("internal_value_store"), Mapping) else None,
        "sidecar_internal_value_store_hash": (sidecar.get("internal_value_store") or {}).get("value_store_hash") if isinstance(sidecar.get("internal_value_store"), Mapping) else None,
    }


def _blocked_fact_row(
    *,
    index: int,
    label: str,
    live_receipt: Mapping[str, Any],
    parser: Mapping[str, Any],
    primary: str,
    raw_identity: Mapping[str, str],
    arelle_python: str,
    user_agent: str,
    block: str,
) -> dict[str, Any]:
    companyfacts = _companyfacts_count(
        cik=raw_identity["cik"],
        accession=raw_identity["accession"],
        user_agent=user_agent,
    )
    sidecar = _sidecar_response(index=index, label=f"{label}-blocked", parser=parser, fact=None, companyfacts=companyfacts)
    arelle = _arelle_fact_count(primary_document=primary, arelle_python=arelle_python)
    oracle_count = arelle.get("fact_count") if isinstance(arelle.get("fact_count"), int) else companyfacts.get("fact_count")
    return {
        "fixture_hash": str(live_receipt["source_artifact_receipt"]["content_sha256"])[:24],
        "form": raw_identity["form"] or "unknown",
        "fixture_class": "real_filing",
        "issuer_by_hash": _sha256(raw_identity["cik"].encode("utf-8"))[:24] if raw_identity["cik"] else None,
        "production_factauthority_fact_count": 0,
        **_sidecar_fields(sidecar),
        "companyfacts_fact_count": companyfacts.get("fact_count"),
        "companyfacts_oracle_used": companyfacts.get("oracle_used"),
        "companyfacts_confidence": companyfacts.get("confidence"),
        "arelle_fact_count": arelle.get("fact_count"),
        "arelle_oracle_used": arelle.get("oracle_used"),
        "arelle_confidence": arelle.get("confidence"),
        "missed_count": int(oracle_count) if isinstance(oracle_count, int) else None,
        "missed_categories": [
            "fact_authority_blocked",
            *(
                ["contexts_present_but_unresolved"] if CONTEXT_RE.search(primary) else []
            ),
            *(
                ["units_present_but_unresolved"] if UNIT_RE.search(primary) else []
            ),
        ],
        "confidence": _live_confidence(companyfacts=companyfacts, arelle=arelle),
        "fact_material_bridge_ready": False,
        "classification_receipt_hash": None,
        "classification_ready": False,
        "downstream_pipeline_block": block,
        "parser_marker_count": int((parser.get("diagnostics") or {}).get("inline_xbrl_marker_count") or 0),
        "raw_identity_redacted": True,
        "fact_values_redacted": True,
    }


def _fact_material_payload(
    *,
    index: int,
    label: str,
    parser: Mapping[str, Any],
    fact: Mapping[str, Any],
    sidecar: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "client_request_id": f"sec-xbrl-measure-fact-material-{label}-{index}",
        "bridge_mode": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.OPERATOR_DECISION,
        "fact_authority_receipt_id": fact["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": fact["fact_authority_receipt_hash"],
        "parser_receipt_id": parser["parser_receipt_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "expected_connector_receipt_hash": parser["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "expected_document_inventory_hash": parser["document_inventory_hash"],
        "expected_content_order_hash": parser["content_order_hash"],
        "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
        "expected_fact_inventory_hash": fact["fact_inventory_hash"],
        "expected_diagnostics_hash": fact["diagnostics_hash"],
        "rollback_confirmed": True,
        "operator_confirmed": True,
    }
    if sidecar.get("sidecar_state") == layer3_sec_xbrl_sidecar.READY_STATE:
        payload["arelle_sidecar_receipt_id"] = sidecar["sidecar_receipt_id"]
        payload["arelle_sidecar_receipt_hash"] = sidecar["sidecar_receipt_hash"]
        payload["expected_fact_inventory_hash"] = sidecar["resolved_fact_inventory_hash"]
        payload["expected_diagnostics_hash"] = sidecar["diagnostics_hash"]
    return payload


def _classification_payload(
    *,
    index: int,
    label: str,
    parser: Mapping[str, Any],
    fact: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "client_request_id": f"sec-xbrl-measure-classification-{label}-{index}",
        "classification_mode": layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.CLASSIFICATION_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.OPERATOR_DECISION,
        "fact_authority_receipt_id": fact["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": fact["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_id": bridge["fact_material_bridge_receipt_id"],
        "fact_material_bridge_receipt_hash": bridge["fact_material_bridge_receipt_hash"],
        "expected_parser_receipt_hash": parser["parser_receipt_hash"],
        "expected_connector_receipt_hash": parser["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "expected_document_inventory_hash": parser["document_inventory_hash"],
        "expected_content_order_hash": parser["content_order_hash"],
        "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
        "expected_fact_inventory_hash": fact["fact_inventory_hash"],
        "expected_diagnostics_hash": fact["diagnostics_hash"],
        "expected_materialization_receipt_hash": bridge["materialization_receipt_hash"],
        "expected_dataset_version_hash": bridge["dataset_version_hash"],
        "expected_gate_b_decision_manifest_id": bridge["gate_b_decision_manifest_id"],
        "operator_confirmation": True,
    }


def _memory_db_session() -> Any:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)()


def _example_record_for_acquisition(connector: Mapping[str, Any], example_id: str) -> Mapping[str, Any]:
    for record in (connector.get("corpus_manifest") or {}).get("example_records") or []:
        if str(record.get("example_id") or "") == example_id:
            return record
    return {}


def _cik_from_hash(cik_hash: str) -> str:
    for cik in layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_CIK_REFS.values():
        normalized = str(cik).strip().lstrip("0") or "0"
        if _sha256(normalized.encode("utf-8")) == cik_hash:
            return normalized
    return ""


def _raw_sec_identity(text: str) -> dict[str, str]:
    return {
        "accession": _first_header(text, "ACCESSION-NUMBER"),
        "cik": (_first_header(text, "CENTRAL INDEX KEY").lstrip("0") or ""),
        "form": _first_header(text, "CONFORMED-SUBMISSION-TYPE") or _first_header(text, "TYPE"),
    }


def _first_header(text: str, name: str) -> str:
    match = re.search(rf"<{re.escape(name)}>\s*([^\r\n<]+)", text, flags=re.IGNORECASE)
    if match:
        return str(match.group(1)).strip()
    label = re.escape(name.replace("-", " "))
    match = re.search(rf"{label}\s*:\s*([^\r\n<]+)", text, flags=re.IGNORECASE)
    return str(match.group(1)).strip() if match else ""


def _live_missed_categories(*, primary: str, parser: Mapping[str, Any], fact: Mapping[str, Any]) -> list[str]:
    categories: list[str] = []
    if len(SHADOW_FACT_RE.findall(primary)) > int(fact.get("fact_count") or 0):
        categories.append("shadow_parse_found_more_fact_bearing_elements")
    if _hidden_fact_count(primary):
        categories.append("ix_hidden_present")
    if CONTINUATION_RE.search(primary) or re.search(r"\bcontinuedAt\s*=", primary, flags=re.IGNORECASE):
        categories.append("continuation_present")
    if CONTEXT_RE.search(primary):
        categories.append("contexts_present_but_unresolved")
    if UNIT_RE.search(primary):
        categories.append("units_present_but_unresolved")
    if int((parser.get("diagnostics") or {}).get("ordered_text_segment_count") or 0) >= 100:
        categories.append("text_segment_inventory_cap_possible")
    diagnostics = fact.get("diagnostics") or {}
    if int(diagnostics.get("unsupported_marker_shape") or 0):
        categories.append("unsupported_marker_shape")
    if not categories:
        categories.append("none_observed")
    return categories


def _live_confidence(*, companyfacts: Mapping[str, Any], arelle: Mapping[str, Any]) -> str:
    if arelle.get("oracle_used") is True and isinstance(arelle.get("fact_count"), int):
        return "gold_arelle_count_available"
    if companyfacts.get("oracle_used") is True and isinstance(companyfacts.get("fact_count"), int):
        return "primary_companyfacts_count_available_partial_scope"
    return "unverified_oracle_unavailable"


def _primary_oracle_status(*, live_manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if not live_manifest:
        return {
            "oracle_used": False,
            "confidence": "unverified",
            "reason": "No retained real filing bytes or real filing fixture identity existed in this environment.",
        }
    rows = list(live_manifest.get("per_fixture") or [])
    used = [row for row in rows if row.get("companyfacts_oracle_used") is True]
    return {
        "oracle_used": bool(used),
        "confidence": "primary_companyfacts_us_gaap_dei_accession_scope" if used else "unverified",
        "filing_count_with_companyfacts": len(used),
        "reason": (
            "CompanyFacts was fetched for retained real filings and counted us-gaap/dei facts by accession."
            if used
            else "CompanyFacts could not be used for retained real filings."
        ),
    }


def _gold_oracle_status(*, live_manifest: Mapping[str, Any] | None, fallback: Mapping[str, Any]) -> dict[str, Any]:
    if not live_manifest:
        return dict(fallback)
    rows = list(live_manifest.get("per_fixture") or [])
    used = [row for row in rows if row.get("arelle_oracle_used") is True]
    return {
        "oracle_used": bool(used),
        "confidence": "gold_arelle_inline_xbrl_model_fact_count" if used else str(fallback.get("confidence") or "unverified"),
        "filing_count_with_arelle": len(used),
        "reason": (
            "Arelle extracted model fact counts for retained real filing documents; sidecar resolved counts are used when available."
            if used
            else str(fallback.get("reason") or "Arelle did not produce retained filing counts.")
        ),
    }


def _arelle_status(*, arelle_python: str, has_real_input: bool) -> dict[str, Any]:
    if not arelle_python:
        return {
            "oracle_used": False,
            "confidence": "not_attempted_no_isolated_arelle_python_configured",
            "reason": "Set ARELLE_PYTHON or pass --arelle-python to record contained Arelle availability.",
        }
    try:
        completed = subprocess.run(
            [arelle_python, "-m", "arelle.CntlrCmdLine", "--version"],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - environment finding path
        return {
            "oracle_used": False,
            "confidence": "unavailable",
            "reason": f"Arelle dry-run failed before invocation: {type(exc).__name__}",
        }
    return {
        "oracle_used": False,
        "confidence": "available_no_real_input" if completed.returncode == 0 and not has_real_input else "available",
        "return_code": completed.returncode,
        "version_output_hash": _sha256((completed.stdout + completed.stderr).encode("utf-8"))[:24],
        "reason": (
            "Contained Arelle invocation succeeded, but no real retained iXBRL filing input existed for gold counts."
            if completed.returncode == 0 and not has_real_input
            else "Arelle invocation did not produce fixture counts in this measurement pass."
        ),
    }


def _companyfacts_count(*, cik: str, accession: str, user_agent: str) -> dict[str, Any]:
    if not cik or not accession:
        return {"oracle_used": False, "confidence": "unavailable_missing_identity", "fact_count": None}
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError, http.client.HTTPException) as exc:
        return {
            "oracle_used": False,
            "confidence": "unavailable_fetch_failed",
            "fact_count": None,
            "error_hash": _sha256(type(exc).__name__.encode("utf-8"))[:16],
        }
    count = 0
    value_keys: list[tuple[str, str, str]] = []
    taxonomies = payload.get("facts") if isinstance(payload, dict) else {}
    if not isinstance(taxonomies, dict):
        return {"oracle_used": False, "confidence": "unavailable_invalid_payload", "fact_count": None}
    for taxonomy_name in ("us-gaap", "dei"):
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
    return {
        "oracle_used": True,
        "confidence": "primary_companyfacts_us_gaap_dei_accession_scope",
        "fact_count": count,
        "_value_keys": value_keys,
    }


def _companyfacts_value_match(*, sidecar: Mapping[str, Any], companyfacts: Mapping[str, Any]) -> dict[str, Any]:
    if sidecar.get("sidecar_state") != layer3_sec_xbrl_sidecar.READY_STATE:
        return {"match_count": None, "compared_count": 0, "match_rate": None}
    value_keys = companyfacts.get("_value_keys")
    if not isinstance(value_keys, list) or not value_keys:
        return {"match_count": None, "compared_count": 0, "match_rate": None}
    try:
        receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
            str(sidecar["sidecar_receipt_id"]),
            expected_sidecar_receipt_hash=str(sidecar["sidecar_receipt_hash"]),
        )
        store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)
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
    for record in receipt.get("resolved_fact_records") or []:
        if not isinstance(record, Mapping):
            continue
        concept = record.get("concept") if isinstance(record.get("concept"), Mapping) else {}
        namespace = str(concept.get("namespace") or "")
        if not concept.get("standard") or not ("fasb.org/us-gaap" in namespace or "xbrl.sec.gov/dei" in namespace):
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


def _numeric_value_key(concept_name: Any, unit_name: Any, value: Any) -> tuple[str, str, str] | None:
    try:
        numeric = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return (
        str(concept_name or ""),
        str(unit_name or ""),
        format(numeric.normalize(), "f"),
    )


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


def _arelle_fact_count(*, primary_document: str, arelle_python: str) -> dict[str, Any]:
    if not arelle_python:
        return {"oracle_used": False, "confidence": "not_configured", "fact_count": None}
    with tempfile.TemporaryDirectory(prefix="sec-xbrl-arelle-") as temp_dir:
        temp = Path(temp_dir)
        entry = temp / "filing.htm"
        entry.write_text(primary_document, encoding="utf-8")
        code = (
            "import json, sys;"
            "from arelle import Cntlr;"
            "cntlr=Cntlr.Cntlr(logFileName='logToBuffer');"
            "model=cntlr.modelManager.load(sys.argv[1]);"
            "facts=list(getattr(model,'facts',[]) or []) if model is not None else [];"
            "errors=list(getattr(model,'errors',[]) or []) if model is not None else [];"
            "print(json.dumps({'fact_count':len(facts),'error_count':len(errors)}));"
            "model.close() if model is not None else None;"
            "cntlr.close()"
        )
        env = dict(os.environ)
        env["XDG_CONFIG_HOME"] = str(temp / "xdg")
        try:
            completed = subprocess.run(
                [arelle_python, "-c", code, str(entry)],
                cwd=str(temp),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=90,
                env=env,
                check=False,
            )
        except Exception as exc:
            return {
                "oracle_used": False,
                "confidence": "unavailable_invocation_failed",
                "fact_count": None,
                "error_hash": _sha256(type(exc).__name__.encode("utf-8"))[:16],
            }
    if completed.returncode != 0:
        return {
            "oracle_used": False,
            "confidence": "unavailable_nonzero_exit",
            "fact_count": None,
            "return_code": completed.returncode,
            "stderr_hash": _sha256(completed.stderr.encode("utf-8"))[:24],
        }
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {
            "oracle_used": False,
            "confidence": "unavailable_invalid_stdout",
            "fact_count": None,
            "stdout_hash": _sha256(completed.stdout.encode("utf-8"))[:24],
        }
    return {
        "oracle_used": True,
        "confidence": "gold_arelle_inline_xbrl_model_fact_count",
        "fact_count": int(payload.get("fact_count") or 0),
        "validation_error_count": int(payload.get("error_count") or 0),
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _source_kind(path: Path) -> str:
    rel = _safe_rel(path)
    storage = _resolved_storage_dir().resolve(strict=False)
    try:
        path.resolve(strict=False).relative_to(storage)
        return "settings_storage_dir"
    except ValueError:
        pass
    if rel.startswith("backend/app/storage"):
        return "settings_storage_dir"
    if rel.startswith("backend/tests/") or rel.startswith("tests/"):
        return "committed_test_source"
    return "committed_source"


def _fixture_class(*, path: Path, snippet: str) -> str:
    rel = _safe_rel(path)
    synthetic_markers = ("{concept}", "Company narrative", "Business overview", "Metric", "123")
    if rel.startswith("backend/tests/") or rel.startswith("tests/"):
        return "synthetic_stub"
    if any(marker in snippet for marker in synthetic_markers):
        return "synthetic_stub"
    return "real_filing"


def _form(snippet: str) -> str:
    match = FORM_RE.search(snippet)
    return match.group(1).upper() if match else "unknown"


def _issuer_hash(snippet: str) -> str:
    seed = "|".join(
        item
        for item in (
            _form(snippet),
            _first_attr(snippet, "name"),
            _sha256(snippet[:256].encode("utf-8"))[:16],
        )
        if item
    )
    return _sha256(seed.encode("utf-8"))[:24]


def _first_attr(snippet: str, attr_name: str) -> str:
    for match in ATTR_RE.finditer(snippet):
        if match.group(1).lower() == attr_name.lower():
            return match.group(2) or match.group(3) or match.group(4) or ""
    return ""


def _hidden_fact_count(snippet: str) -> int:
    return sum(len(SHADOW_FACT_RE.findall(match.group(0))) for match in HIDDEN_RE.finditer(snippet))


def _storage_inventory() -> dict[str, Any]:
    storage = _resolved_storage_dir()
    file_count = _storage_file_count()
    receipt_dirs = []
    byte_files = 0
    if storage.exists():
        for path in storage.iterdir():
            if path.is_dir() and path.name.startswith("layer3-sec-edgar"):
                receipt_dirs.append(_sha256(path.name.encode("utf-8"))[:16])
        for path in storage.rglob("*"):
            if path.is_file() and path.suffix.lower() not in {".json", ".lock"}:
                byte_files += 1
    return {
        "storage_dir_observed": storage.exists(),
        "storage_dir_marker": _sha256(str(storage.resolve(strict=False)).encode("utf-8"))[:24],
        "storage_dir_path_redacted": True,
        "storage_dir_gitignored": _is_gitignored(storage),
        "storage_dir_file_count": file_count,
        "sec_receipt_dir_count": len(receipt_dirs),
        "sec_receipt_dir_hashes": receipt_dirs[:12],
        "retained_sec_source_byte_file_count": byte_files,
        "retained_artifact_byte_status": (
            "retained_source_bytes_present" if byte_files else "absent_or_hashes_only"
        ),
    }


def _storage_file_count() -> int:
    storage = _resolved_storage_dir()
    if not storage.exists():
        return 0
    return sum(1 for path in storage.rglob("*") if path.is_file())


def _resolved_storage_dir() -> Path:
    return Path(settings.storage_dir).resolve(strict=False)


def _override_storage_dir(path: Path) -> None:
    resolved = path if path.is_absolute() else ROOT / path
    settings.storage_dir = str(resolved.resolve(strict=False))
    bootstrap_storage_tree(settings.storage_dir)


def _safe_rel(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{_sha256(str(path.resolve(strict=False)).encode('utf-8'))[:24]}"


def _is_gitignored(path: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except Exception:
        return False
    return completed.returncode == 0


def _headline(*, rows: list[dict[str, Any]], real_input_available: bool) -> str:
    if not real_input_available:
        return (
            "UNVERIFIED: current parser fact coverage cannot be graded from this environment because only "
            "synthetic/minimal iXBRL fixtures and no retained real filing bytes were found."
        )
    real_rows = [row for row in rows if row.get("fixture_class") == "real_filing"]
    counted = [
        row
        for row in real_rows
        if isinstance(row.get("production_factauthority_fact_count"), int)
        and isinstance(_gold_count_for_headline(row), int)
        and int(_gold_count_for_headline(row) or 0) > 0
    ]
    if counted:
        production = sum(int(row["production_factauthority_fact_count"]) for row in counted)
        arelle = sum(int(_gold_count_for_headline(row) or 0) for row in counted)
        ratio = production / arelle if arelle else 0.0
        if ratio >= 0.98:
            return f"TRUSTWORTHY: production fact-authority coverage matched {production}/{arelle} Arelle facts across real filings."
        if ratio >= 0.80:
            return f"PARTIALLY TRUSTWORTHY: production fact-authority coverage captured {production}/{arelle} Arelle facts across real filings."
        return f"POOR: production fact-authority coverage captured only {production}/{arelle} Arelle facts across real filings."
    if not rows:
        return "UNVERIFIED: no iXBRL fixture rows were measured."
    return "UNVERIFIED: real rows exist, but no gold Arelle fact counts were available."


def _gold_count_for_headline(row: Mapping[str, Any]) -> int | None:
    if row.get("sidecar_state") == layer3_sec_xbrl_sidecar.READY_STATE and isinstance(row.get("sidecar_resolved_fact_count"), int):
        return int(row["sidecar_resolved_fact_count"])
    if isinstance(row.get("arelle_fact_count"), int):
        return int(row["arelle_fact_count"])
    return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
