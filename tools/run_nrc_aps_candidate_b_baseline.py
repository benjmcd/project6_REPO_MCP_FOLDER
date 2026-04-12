from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TESTS_DIR = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from app.services import nrc_aps_document_processing  # noqa: E402
from support_nrc_aps_candidate_b_opendataloader import (  # noqa: E402
    BASELINE_SUMMARY_SCHEMA_ID,
    CORPUS_DIR,
    FROZEN_FIXTURE_IDS,
    LABELS_PATH,
    MANIFEST_PATH,
    labels_entry_map,
    load_labels,
    load_manifest,
    manifest_entry_map,
    live_manifest_sha256,
    read_json,
    repo_rel,
    sha256_path,
    utc_now,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a fresh Candidate B baseline summary from isolated proof state.")
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--proof-report", required=True)
    parser.add_argument("--out", required=True)
    return parser


def load_and_validate_proof_report(*, runtime_root: Path, proof_report_path: Path) -> dict[str, Any]:
    payload = read_json(proof_report_path)
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_proof_report_payload")
    if str(payload.get("schema_id") or "").strip() != "aps.document_processing_proof.v1":
        raise RuntimeError("invalid_proof_report_schema")
    if not bool(payload.get("passed")):
        raise RuntimeError("proof_report_failed")
    recorded_runtime_root = Path(str(payload.get("runtime_root") or "")).resolve()
    if recorded_runtime_root != runtime_root.resolve():
        raise RuntimeError("proof_runtime_root_mismatch")
    if str(payload.get("ocr_mode") or "").strip() != "required":
        raise RuntimeError("proof_ocr_mode_mismatch")
    return payload


def build_baseline_documents(*, runtime_root: Path) -> list[dict[str, Any]]:
    manifest = load_manifest()
    labels = load_labels()
    manifest_entry_by_fixture = manifest_entry_map(manifest)
    label_entry_by_fixture = labels_entry_map(labels)
    artifact_storage_dir = runtime_root / "storage"
    documents: list[dict[str, Any]] = []
    for fixture_id in FROZEN_FIXTURE_IDS:
        manifest_entry = manifest_entry_by_fixture.get(fixture_id)
        label_entry = label_entry_by_fixture.get(fixture_id)
        if manifest_entry is None or label_entry is None:
            raise RuntimeError(f"missing_fixture_metadata:{fixture_id}")
        fixture_path = CORPUS_DIR / str(manifest_entry.get("path") or "")
        declared_content_type = str(manifest_entry.get("declared_content_type") or "").strip()
        if not fixture_path.exists() or not declared_content_type:
            raise RuntimeError(f"invalid_fixture_entry:{fixture_id}")
        processed = nrc_aps_document_processing.process_document(
            content=fixture_path.read_bytes(),
            declared_content_type=declared_content_type,
            config={"artifact_storage_dir": str(artifact_storage_dir)},
        )
        documents.append(
            {
                "fixture_id": fixture_id,
                "document_ref": str(label_entry.get("document_ref") or repo_rel(fixture_path)),
                "document_sha256": str(label_entry.get("document_sha256") or sha256_path(fixture_path)),
                "baseline": {
                    "page_count": int(processed.get("page_count") or 0),
                    "normalized_char_count": int(processed.get("normalized_char_count") or 0),
                    "document_class": str(processed.get("document_class") or "").strip() or None,
                    "degradation_codes": list(processed.get("degradation_codes") or []),
                },
            }
        )
    return documents


def build_baseline_summary_payload(*, runtime_root: Path, proof_report_path: Path) -> dict[str, Any]:
    load_and_validate_proof_report(runtime_root=runtime_root, proof_report_path=proof_report_path)
    return {
        "schema_id": BASELINE_SUMMARY_SCHEMA_ID,
        "generated_at_utc": utc_now(),
        "proof_report_ref": repo_rel(proof_report_path),
        "runtime_root": str(runtime_root.resolve()),
        "corpus_manifest_ref": repo_rel(MANIFEST_PATH),
        "corpus_manifest_sha256": live_manifest_sha256(),
        "documents": build_baseline_documents(runtime_root=runtime_root),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        runtime_root = Path(args.runtime_root).resolve()
        proof_report_path = Path(args.proof_report).resolve()
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = build_baseline_summary_payload(runtime_root=runtime_root, proof_report_path=proof_report_path)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
