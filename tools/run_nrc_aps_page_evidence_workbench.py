from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.nrc_aps_page_evidence import analyze_pdf_path, default_page_evidence_config  # noqa: E402


WORKBENCH_REPORT_SCHEMA_ID = "aps.page_evidence_workbench_report.v1"
CORPUS_DIR = ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_generated_at_utc(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return _utc_iso()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid_generated_at_utc:{raw}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _load_manifest_entries() -> list[dict[str, Any]]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries") or []
    return [dict(item or {}) for item in entries if isinstance(item, dict)]


def _resolve_fixture_targets(fixture_ids: list[str], *, allow_default: bool) -> list[dict[str, Any]]:
    entries = _load_manifest_entries()
    requested = [str(item).strip() for item in fixture_ids if str(item).strip()]
    targets: list[dict[str, Any]] = []

    if not requested and allow_default:
        for entry in entries:
            if str(entry.get("fixture_role") or "").strip() != "representative_lower_bound":
                continue
            relative = str(entry.get("path") or "").strip()
            if not relative.lower().endswith(".pdf"):
                continue
            targets.append(
                {
                    "source_kind": "fixture",
                    "fixture_id": str(entry.get("fixture_id") or "").strip(),
                    "path": str((CORPUS_DIR / relative).resolve()),
                }
            )
        return targets
    if not requested:
        return targets

    for fixture_id in requested:
        matched = next(
            (entry for entry in entries if str(entry.get("fixture_id") or "").strip() == fixture_id),
            None,
        )
        if matched is None:
            raise ValueError(f"unknown_fixture_id:{fixture_id}")
        relative = str(matched.get("path") or "").strip()
        if not relative.lower().endswith(".pdf"):
            raise ValueError(f"fixture_is_not_pdf:{fixture_id}")
        targets.append(
            {
                "source_kind": "fixture",
                "fixture_id": fixture_id,
                "path": str((CORPUS_DIR / relative).resolve()),
            }
        )
    return targets


def _resolve_explicit_targets(paths: list[str]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(str(raw_path).strip()).resolve()
        if not path.exists():
            raise ValueError(f"pdf_path_missing:{path}")
        targets.append(
            {
                "source_kind": "path",
                "fixture_id": None,
                "path": str(path),
            }
        )
    return targets


def _normalize_output_path(target_path: Path, *, path_mode: str) -> str:
    resolved = target_path.resolve()
    if path_mode == "absolute":
        return str(resolved)
    if path_mode != "repo_relative":
        raise ValueError(f"unsupported_path_mode:{path_mode}")
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"repo_relative_path_unavailable:{resolved}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated PageEvidence workbench analysis for Candidate A.")
    parser.add_argument("--report", required=True, help="Path to the output JSON report.")
    parser.add_argument("--fixture-id", action="append", default=[], help="Corpus fixture ID to analyze.")
    parser.add_argument("--input-pdf", action="append", default=[], help="Explicit PDF path to analyze.")
    parser.add_argument("--text-word-threshold", type=int, default=20)
    parser.add_argument("--visual-coverage-threshold", type=float, default=0.15)
    parser.add_argument(
        "--path-mode",
        choices=("absolute", "repo_relative"),
        default="absolute",
        help="How document paths should be written into the JSON report.",
    )
    parser.add_argument(
        "--generated-at-utc",
        default="",
        help="Optional ISO8601 UTC timestamp override for durable report generation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at_utc = _normalize_generated_at_utc(args.generated_at_utc)

    config = default_page_evidence_config(
        {
            "text_word_threshold": args.text_word_threshold,
            "visual_coverage_threshold": args.visual_coverage_threshold,
        }
    )

    try:
        explicit_targets = _resolve_explicit_targets(list(args.input_pdf))
        targets = _resolve_fixture_targets(
            list(args.fixture_id),
            allow_default=len(explicit_targets) == 0,
        )
        targets.extend(explicit_targets)
    except ValueError as exc:
        payload = {
            "schema_id": WORKBENCH_REPORT_SCHEMA_ID,
            "generated_at_utc": generated_at_utc,
            "candidate_stage": "pre_admission",
            "passed": False,
            "config": dict(config),
            "documents": [],
            "failure_reason": str(exc),
        }
        report_path.write_text(_stable_json(payload), encoding="utf-8")
        return 2

    documents: list[dict[str, Any]] = []
    passed = True
    failure_reason: str | None = None

    for target in targets:
        target_path = Path(str(target["path"]))
        try:
            analysis = analyze_pdf_path(target_path, config=config)
            documents.append(
                {
                    "source_kind": target["source_kind"],
                    "fixture_id": target["fixture_id"],
                    "path": _normalize_output_path(target_path, path_mode=args.path_mode),
                    "analysis": analysis,
                }
            )
        except Exception as exc:  # noqa: BLE001
            passed = False
            failure_reason = str(exc)
            documents.append(
                {
                    "source_kind": target["source_kind"],
                    "fixture_id": target["fixture_id"],
                    "path": _normalize_output_path(target_path, path_mode=args.path_mode)
                    if target_path.exists()
                    else str(target_path),
                    "failure_reason": str(exc),
                }
            )

    payload = {
        "schema_id": WORKBENCH_REPORT_SCHEMA_ID,
        "generated_at_utc": generated_at_utc,
        "candidate_stage": "pre_admission",
        "passed": passed,
        "config": dict(config),
        "document_count": len(documents),
        "documents": documents,
        "failure_reason": failure_reason,
    }
    report_path.write_text(_stable_json(payload), encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
