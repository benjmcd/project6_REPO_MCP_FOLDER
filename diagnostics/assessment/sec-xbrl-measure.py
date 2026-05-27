from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-report.json")
SCAN_ROOTS = (Path("backend/tests"), Path("tests"), Path("backend/app/storage"))

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
    parser.add_argument("--arelle-python", default=os.environ.get("ARELLE_PYTHON", ""))
    args = parser.parse_args()

    report = build_report(arelle_python=args.arelle_python)
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"headline={report['headline']}")
    return 0


def build_report(*, arelle_python: str = "") -> dict[str, Any]:
    candidates = list(_inventoried_ixbrl_candidates())
    real_candidates = [item for item in candidates if item["fixture_class"] == "real_filing"]
    arelle = _arelle_status(arelle_python=arelle_python, has_real_input=bool(real_candidates))
    rows = [_row_for_candidate(candidate, real_input_available=bool(real_candidates)) for candidate in candidates]
    headline = _headline(rows=rows, real_input_available=bool(real_candidates))
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
            "committed_ixbrl_candidate_count": len(candidates),
            "real_filing_candidate_count": len(real_candidates),
            "synthetic_stub_candidate_count": len(candidates) - len(real_candidates),
            "storage_dir_observed": True,
            "storage_dir_gitignored": True,
            "storage_dir_file_count": _storage_file_count(),
            "retained_artifacts_observed": _storage_file_count() > 0,
            "retained_artifact_byte_status": "absent_empty_storage_dir",
        },
        "oracle_status": {
            "primary_companyfacts": {
                "oracle_used": False,
                "confidence": "unverified",
                "reason": "No retained real filing bytes or real filing fixture identity existed in this environment.",
            },
            "gold_arelle": arelle,
            "sanity_shadow_parse": {
                "oracle_used": bool(candidates),
                "confidence": "low_lower_bound",
                "reason": (
                    "Counts fact-bearing inline XBRL elements by tag shape only and shares blind spots "
                    "with the regex parser under test."
                ),
            },
        },
        "per_fixture": rows,
        "headline": headline,
    }


def _inventoried_ixbrl_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for root in SCAN_ROOTS:
        base = ROOT / root
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


def _snippets(text: str) -> list[str]:
    sec_documents = SEC_DOCUMENT_RE.findall(text)
    if sec_documents:
        return sec_documents
    return HTML_IX_RE.findall(text)


def _candidate(*, path: Path, snippet: str, index: int) -> dict[str, Any]:
    rel = path.relative_to(ROOT).as_posix()
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
    for root in SCAN_ROOTS:
        base = ROOT / root
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


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _source_kind(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("backend/app/storage/"):
        return "settings_storage_dir"
    if rel.startswith("backend/tests/") or rel.startswith("tests/"):
        return "committed_test_source"
    return "committed_source"


def _fixture_class(*, path: Path, snippet: str) -> str:
    rel = path.relative_to(ROOT).as_posix()
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


def _storage_file_count() -> int:
    storage = ROOT / "backend/app/storage"
    if not storage.exists():
        return 0
    return sum(1 for path in storage.rglob("*") if path.is_file())


def _headline(*, rows: list[dict[str, Any]], real_input_available: bool) -> str:
    if not real_input_available:
        return (
            "UNVERIFIED: current parser fact coverage cannot be graded from this environment because only "
            "synthetic/minimal iXBRL fixtures and no retained real filing bytes were found."
        )
    if not rows:
        return "UNVERIFIED: no iXBRL fixture rows were measured."
    return "PARTIALLY TRUSTWORTHY: real fixture rows exist, but only lower-bound sanity counts were measured."


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
