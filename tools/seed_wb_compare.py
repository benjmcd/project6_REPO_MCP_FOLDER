from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TESTS_DIR = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from tools.run_nrc_aps_local_corpus_e2e import (  # noqa: E402
    ALEMBIC_STUB_FINDING,
    DOCUMENT_PROCESSING_ENGINE_BASELINE,
    DOCUMENT_PROCESSING_ENGINE_CHOICES,
    EXPECTED_INTERPRETER,
    LEASE_TTL_OVERRIDE_FINDING,
    LOCAL_PROOF_CONNECTOR_LEASE_TTL_SECONDS,
    LocalCorpusDocument,
    LocalCorpusNrcClient,
    SUMMARY_SCHEMA_ID,
    SUMMARY_SCHEMA_VERSION,
    _assert,
    _execute_proof,
    _ghostscript_path,
    _isolated_runtime,
    _resolve_runtime_root,
)
import tools.run_nrc_aps_local_corpus_e2e as local_corpus_e2e  # noqa: E402
from support_nrc_aps_candidate_b_opendataloader import FROZEN_FIXTURE_IDS  # noqa: E402
from support_nrc_aps_doc_corpus import corpus_ocr_available, fixture_path, manifest_entry  # noqa: E402


FIXTURE_DOCUMENT_TYPE = "Inspection Report"
FIXTURE_FOLDER_NAME = "fixture_compare_documents_for_testing"
FIXTURE_FOLDER_SLUG = "fixture-compare"
_SUPPORTED_VISUAL_LANE_MODES = {"baseline", "candidate_a_page_evidence_v1"}
_SUPPORTED_DOCUMENT_PROCESSING_ENGINES = set(DOCUMENT_PROCESSING_ENGINE_CHOICES)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_fixture_documents() -> tuple[list[LocalCorpusDocument], dict[str, Any]]:
    docs: list[LocalCorpusDocument] = []
    fixture_rows: list[dict[str, Any]] = []
    ocr_fixture_ids: list[str] = []

    for ordinal, fixture_id in enumerate(FROZEN_FIXTURE_IDS, start=1):
        entry = manifest_entry(fixture_id)
        declared_content_type = str(entry.get("declared_content_type") or "").strip().lower()
        path = fixture_path(entry)
        _assert(path.exists() and path.is_file(), f"fixture_path_missing:{fixture_id}")
        _assert(declared_content_type == "application/pdf", f"fixture_not_pdf:{fixture_id}")
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        accession = f"FIXTUREAPS{ordinal:05d}"
        requires_ocr = bool(entry.get("requires_ocr", False))
        if requires_ocr:
            ocr_fixture_ids.append(fixture_id)
        docs.append(
            LocalCorpusDocument(
                ordinal=ordinal,
                accession_number=accession,
                title=path.name,
                document_type=FIXTURE_DOCUMENT_TYPE,
                folder_name=FIXTURE_FOLDER_NAME,
                folder_slug=FIXTURE_FOLDER_SLUG,
                allow_unknown_document_type=False,
                file_path=path,
                document_date=mtime.date().isoformat(),
                date_added_timestamp=mtime.isoformat().replace("+00:00", "Z"),
                url=f"https://adams.nrc.gov/fixture-corpus/{accession}.pdf",
            )
        )
        fixture_rows.append(
            {
                "fixture_id": fixture_id,
                "path": str(path),
                "declared_content_type": declared_content_type,
                "requires_ocr": requires_ocr,
                "accession_number": accession,
            }
        )

    return docs, {
        "corpus_root": str((ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1").resolve()),
        "included_fixture_ids": list(FROZEN_FIXTURE_IDS),
        "fixture_count": len(docs),
        "folder_name": FIXTURE_FOLDER_NAME,
        "folder_slug": FIXTURE_FOLDER_SLUG,
        "document_type": FIXTURE_DOCUMENT_TYPE,
        "fixtures": fixture_rows,
        "ocr_required_fixture_ids": ocr_fixture_ids,
    }


def run_preflight(runtime_root: Path) -> tuple[list[LocalCorpusDocument], dict[str, Any], list[dict[str, Any]]]:
    docs, corpus_shape = build_fixture_documents()

    _assert(EXPECTED_INTERPRETER.exists(), f"expected Phase 7A interpreter missing: {EXPECTED_INTERPRETER}")
    _assert(
        Path(sys.executable).resolve() == EXPECTED_INTERPRETER.resolve(),
        f"tool must run with {EXPECTED_INTERPRETER}, got {Path(sys.executable).resolve()}",
    )

    imported_modules: list[dict[str, Any]] = []
    for module_name in ("fitz", "camelot", "paddleocr", "matplotlib", "ruptures", "statsmodels", "sklearn", "multipart"):
        module = importlib.import_module(module_name)
        imported_modules.append(
            {
                "module": module_name,
                "loaded_from": str(Path(getattr(module, "__file__", "built-in")).resolve())
                if getattr(module, "__file__", None)
                else "built-in",
            }
        )

    aps_settings = importlib.import_module("app.services.nrc_aps_settings")
    paddle_dirs = {
        "PADDLE_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_MODEL_DIR"))),
        "PADDLE_DET_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_DET_MODEL_DIR"))),
        "PADDLE_REC_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_REC_MODEL_DIR"))),
        "PADDLE_CLS_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_CLS_MODEL_DIR"))),
    }
    for name, path in paddle_dirs.items():
        _assert(path.exists(), f"{name} missing: {path}")

    ghostscript = _ghostscript_path()
    _assert(ghostscript is not None, "Ghostscript executable not found")

    if runtime_root.exists():
        _assert(
            runtime_root.resolve().is_relative_to(local_corpus_e2e.DEFAULT_RUNTIME_PARENT.resolve()),
            f"runtime_root must stay under {local_corpus_e2e.DEFAULT_RUNTIME_PARENT}",
        )
        _assert(not any(runtime_root.iterdir()), f"runtime_root must be empty when provided: {runtime_root}")

    findings: list[dict[str, Any]] = [
        {
            "code": "fixture_compare_seed_fixed_fixture_set",
            "message": (
                "This seed path intentionally uses the same fixed five-fixture PDF set as the Candidate B workbench "
                "bundle so the compare workspace has a real three-way fixture intersection."
            ),
        },
        {
            "code": "idempotency_key_run_id_dependency_unavailable",
            "message": (
                "The submit route assigns connector_run_id server-side, so the seed uses a runtime-stamp-derived "
                "Idempotency-Key instead of a value derived from the fresh run ID."
            ),
        },
        {
            "code": "monolithic_router_dependency_surface",
            "message": (
                "The fixture-corpus seed must boot the full API router, which currently imports unrelated analysis/"
                "profiling/transform services and therefore depends on their runtime packages even though this seed "
                "exercises only NRC APS review surfaces."
            ),
        },
        dict(LEASE_TTL_OVERRIDE_FINDING),
    ]

    ocr_available = corpus_ocr_available()
    if corpus_shape["ocr_required_fixture_ids"] and not ocr_available:
        findings.append(
            {
                "code": "fixture_compare_seed_ocr_unavailable",
                "message": (
                    "OCR is unavailable for this seed run, so OCR-dependent fixtures can still be included in the "
                    "review root but may produce degraded baseline/Candidate A outputs relative to the Candidate B "
                    "bundle."
                ),
            }
        )

    return docs, {
        "interpreter_path": str(Path(sys.executable).resolve()),
        "expected_interpreter_path": str(EXPECTED_INTERPRETER.resolve()),
        "corpus_shape": {**corpus_shape, "ocr_available": ocr_available},
        "imports": imported_modules,
        "ghostscript_path": ghostscript,
        "paddle_model_dirs": {name: str(path) for name, path in paddle_dirs.items()},
        "isolated_runtime_overrides": {
            "CONNECTOR_LEASE_TTL_SECONDS": LOCAL_PROOF_CONNECTOR_LEASE_TTL_SECONDS,
        },
        "runtime_root": str(runtime_root),
    }, findings


def _normalize_visual_lane_mode(value: str) -> str:
    normalized = str(value or "").strip().lower()
    _assert(normalized in _SUPPORTED_VISUAL_LANE_MODES, "invalid_visual_lane_mode")
    return normalized


def _normalize_document_processing_engine(value: str) -> str:
    normalized = str(value or "").strip().lower() or DOCUMENT_PROCESSING_ENGINE_BASELINE
    _assert(normalized in _SUPPORTED_DOCUMENT_PROCESSING_ENGINES, "invalid_document_processing_engine")
    return normalized


def _validate_seed_modes(*, visual_lane_mode: str, document_processing_engine: str) -> tuple[str, str]:
    normalized_lane = _normalize_visual_lane_mode(visual_lane_mode)
    normalized_engine = _normalize_document_processing_engine(document_processing_engine)
    _assert(
        normalized_engine == DOCUMENT_PROCESSING_ENGINE_BASELINE or normalized_lane == "baseline",
        "candidate_b_document_processing_engine_requires_baseline_visual_lane",
    )
    return normalized_lane, normalized_engine


def _inject_visual_lane_mode(payload: dict[str, Any], visual_lane_mode: str) -> dict[str, Any]:
    normalized = _normalize_visual_lane_mode(visual_lane_mode)
    outbound = dict(payload)
    if normalized == "candidate_a_page_evidence_v1":
        outbound["visual_lane_mode"] = normalized
    else:
        outbound.pop("visual_lane_mode", None)
    return outbound


@contextmanager
def _patched_submit_visual_lane_mode(visual_lane_mode: str) -> Iterator[None]:
    normalized = _normalize_visual_lane_mode(visual_lane_mode)
    original_post_json = local_corpus_e2e._post_json

    def wrapped_post_json(client: Any, path: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        outbound = payload
        if path == "/api/v1/connectors/nrc-adams-aps/runs":
            outbound = _inject_visual_lane_mode(payload, normalized)
        return original_post_json(client, path, outbound, headers=headers)

    local_corpus_e2e._post_json = wrapped_post_json
    try:
        yield
    finally:
        local_corpus_e2e._post_json = original_post_json


def execute_seed(
    runtime: Any,
    docs: list[LocalCorpusDocument],
    runtime_root: Path,
    fake_client: LocalCorpusNrcClient,
    *,
    visual_lane_mode: str,
    document_processing_engine: str,
) -> dict[str, Any]:
    document_processing_engine = _normalize_document_processing_engine(document_processing_engine)
    with _patched_submit_visual_lane_mode(visual_lane_mode):
        return _execute_proof(
            runtime,
            docs,
            runtime_root,
            fake_client,
            document_processing_engine=document_processing_engine,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a reviewable NRC APS fixture-corpus runtime root for the workbench compare workspace."
    )
    parser.add_argument(
        "--runtime-root",
        default="",
        help=(
            f"Optional empty runtime directory under {local_corpus_e2e.DEFAULT_RUNTIME_PARENT}. "
            "If omitted, the tool creates a fresh timestamped runtime."
        ),
    )
    parser.add_argument(
        "--visual-lane-mode",
        choices=sorted(_SUPPORTED_VISUAL_LANE_MODES),
        default="baseline",
        help="Seed either a baseline or Candidate A review runtime for the fixed workbench-compare fixture set.",
    )
    parser.add_argument(
        "--document-processing-engine",
        choices=sorted(_SUPPORTED_DOCUMENT_PROCESSING_ENGINES),
        default=DOCUMENT_PROCESSING_ENGINE_BASELINE,
        help=(
            "Document processing engine for the fixed workbench-compare fixture seed. "
            "Use candidate_b_opendataloader_pdf with baseline visual lane to create a Candidate B runtime source."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    visual_lane_mode, document_processing_engine = _validate_seed_modes(
        visual_lane_mode=args.visual_lane_mode,
        document_processing_engine=args.document_processing_engine,
    )
    runtime_root = _resolve_runtime_root(args.runtime_root)
    summary_path = runtime_root / "local_corpus_e2e_summary.json"
    summary: dict[str, Any] = {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "passed": False,
        "runtime_root": str(runtime_root),
        "database_path": None,
        "database_url": None,
        "storage_dir": None,
        "interpreter_path": str(Path(sys.executable).resolve()),
        "run_id": None,
        "corpus_root": str((ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1").resolve()),
        "corpus_pdf_count": 0,
        "corpus_fixture_ids": list(FROZEN_FIXTURE_IDS),
        "seed_kind": "workbench_compare_fixture_seed",
        "visual_lane_mode": visual_lane_mode,
        "document_processing_engine": document_processing_engine,
        "preflight": {},
        "submission": {},
        "run_detail": {},
        "search_smoke": {},
        "selected_branch_rows": [],
        "downstream_artifacts": {},
        "gate_results": {},
        "advanced_metrics": {},
        "client_trace": {},
        "observed_non_blocking_findings": [],
        "failure": None,
    }

    exit_code = 1
    preflight_passed = False
    try:
        docs, preflight, findings = run_preflight(runtime_root)
        summary["preflight"] = preflight
        summary["corpus_pdf_count"] = len(docs)
        summary["observed_non_blocking_findings"] = findings
        preflight_passed = True
        runtime_root.mkdir(parents=True, exist_ok=True)

        fake_client = LocalCorpusNrcClient(docs)
        with _isolated_runtime(fake_client, runtime_root) as runtime:
            summary["database_path"] = str(runtime.database_path)
            summary["database_url"] = runtime.env["DATABASE_URL"]
            summary["storage_dir"] = str(runtime.storage_dir)
            proof_payload = execute_seed(
                runtime,
                docs,
                runtime_root,
                fake_client,
                visual_lane_mode=visual_lane_mode,
                document_processing_engine=document_processing_engine,
            )
            summary.update(proof_payload)
            summary["run_id"] = proof_payload["run_id"]
            summary["passed"] = True
            exit_code = 0
    except Exception as exc:  # noqa: BLE001
        summary["failure"] = {
            "error_class": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if preflight_passed:
            if local_corpus_e2e._ALEMBIC_STUB_INSTALLED and not any(
                str(item.get("code") or "") == ALEMBIC_STUB_FINDING["code"]
                for item in summary["observed_non_blocking_findings"]
                if isinstance(item, dict)
            ):
                summary["observed_non_blocking_findings"].append(dict(ALEMBIC_STUB_FINDING))
            summary["generated_at_utc"] = utc_now()
            write_json(summary_path, summary)
            print(str(summary_path))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
