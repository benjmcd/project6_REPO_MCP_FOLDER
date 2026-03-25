from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_ocr  # noqa: E402
from tests.support_nrc_aps_doc_corpus import manifest_entries  # noqa: E402


PROOF_SCHEMA_ID = "aps.document_processing_proof.v1"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _run_command(*, args: list[str], env: dict[str, str], cwd: Path, label: str) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=str(cwd), env=env, capture_output=True, text=True)
    return {
        "label": label,
        "args": args,
        "cwd": str(cwd),
        "exit_code": int(completed.returncode),
        "stdout": str(completed.stdout or ""),
        "stderr": str(completed.stderr or ""),
        "passed": completed.returncode == 0,
    }


def _default_runtime_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="apsdocproof_"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fresh isolated NRC APS lower-layer document-processing proof.")
    parser.add_argument("--report", default=str(ROOT / "tests" / "reports" / "nrc_aps_document_processing_proof_report.json"))
    parser.add_argument("--artifact-report", default=str(ROOT / "tests" / "reports" / "nrc_aps_artifact_ingestion_validation_report.json"))
    parser.add_argument("--content-index-report", default=str(ROOT / "tests" / "reports" / "nrc_aps_content_index_validation_report.json"))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--require-ocr", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime_root = Path(args.runtime_root).resolve() if str(args.runtime_root).strip() else _default_runtime_root()
    storage_dir = runtime_root / "storage"
    database_path = runtime_root / "proof.db"
    report_path = Path(args.report).resolve()
    artifact_report_path = Path(args.artifact_report).resolve()
    content_index_report_path = Path(args.content_index_report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_report_path.parent.mkdir(parents=True, exist_ok=True)
    content_index_report_path.parent.mkdir(parents=True, exist_ok=True)

    tesseract_available = bool(nrc_aps_ocr.tesseract_available())
    if args.require_ocr and not tesseract_available:
        proof_payload = {
            "schema_id": PROOF_SCHEMA_ID,
            "schema_version": 1,
            "generated_at_utc": _utc_iso(),
            "passed": False,
            "ocr_mode": "required",
            "ocr_success_proven": False,
            "tesseract_available": False,
            "runtime_root": str(runtime_root),
            "database_url": None,
            "storage_dir": str(storage_dir),
            "corpus_fixture_ids": sorted(str(entry.get("fixture_id") or "") for entry in manifest_entries()),
            "commands": [],
            "artifact_ingestion_report_ref": None,
            "content_index_report_ref": None,
            "failure_reason": "tesseract_required",
        }
        report_path.write_text(_stable_json(proof_payload), encoding="utf-8")
        return 2

    database_url = f"sqlite:///{database_path.as_posix()}"
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["STORAGE_DIR"] = str(storage_dir)
    env["DB_INIT_MODE"] = "none"
    env["NRC_ADAMS_APS_SUBSCRIPTION_KEY"] = env.get("NRC_ADAMS_APS_SUBSCRIPTION_KEY") or "test-nrc-key"
    env["NRC_ADAMS_APS_API_BASE_URL"] = env.get("NRC_ADAMS_APS_API_BASE_URL") or "https://adams-api.nrc.gov"
    env["NRC_APS_CORPUS_OCR_MODE"] = "required" if args.require_ocr else "disabled"

    commands: list[dict[str, Any]] = []
    proof_tests = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_nrc_aps_media_detection.py",
        "tests/test_nrc_aps_document_processing.py",
        "tests/test_nrc_aps_document_corpus.py",
        "tests/test_nrc_aps_artifact_ingestion.py",
        "tests/test_nrc_aps_content_index.py",
        "tests/test_nrc_aps_content_index_gate.py",
        "-q",
    ]
    commands.append(_run_command(args=proof_tests, env=env, cwd=ROOT, label="lower_layer_pytest"))

    api_selector = [
        "test_nrc_content_index_artifacts_and_search_route",
        "test_nrc_real_born_digital_content_search_and_evidence_bundle",
    ]
    if args.require_ocr:
        api_selector.append("test_nrc_scanned_content_search_and_evidence_bundle_with_ocr")
    api_tests = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_api.py",
        "-k",
        " or ".join(api_selector),
        "-q",
    ]
    commands.append(_run_command(args=api_tests, env=env, cwd=ROOT, label="api_proof_pytest"))

    if all(bool(item["passed"]) for item in commands):
        commands.append(
            _run_command(
                args=[sys.executable, "tools/nrc_aps_artifact_ingestion_gate.py", "--report", str(artifact_report_path)],
                env=env,
                cwd=ROOT,
                label="artifact_ingestion_gate",
            )
        )
        commands.append(
            _run_command(
                args=[sys.executable, "tools/nrc_aps_content_index_gate.py", "--report", str(content_index_report_path)],
                env=env,
                cwd=ROOT,
                label="content_index_gate",
            )
        )

    passed = all(bool(item["passed"]) for item in commands)
    proof_payload = {
        "schema_id": PROOF_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": _utc_iso(),
        "passed": passed,
        "ocr_mode": "required" if args.require_ocr else "disabled",
        "ocr_success_proven": bool(args.require_ocr and tesseract_available and passed),
        "tesseract_available": tesseract_available,
        "runtime_root": str(runtime_root),
        "database_url": database_url,
        "storage_dir": str(storage_dir),
        "corpus_fixture_ids": sorted(str(entry.get("fixture_id") or "") for entry in manifest_entries()),
        "commands": commands,
        "artifact_ingestion_report_ref": str(artifact_report_path) if artifact_report_path.exists() else None,
        "content_index_report_ref": str(content_index_report_path) if content_index_report_path.exists() else None,
        "failure_reason": None if passed else "proof_command_failed",
    }
    report_path.write_text(_stable_json(proof_payload), encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
