from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
REPORTS_DIR = TESTS_DIR / "reports"
RAW_OUTPUT_PARENT = REPORTS_DIR / "nrc_aps_candidate_b_opendataloader_raw"
PROOF_REPORT_PATH = REPORTS_DIR / "nrc_aps_candidate_b_opendataloader_proof_report.json"
COMPARE_REPORT_PATH = REPORTS_DIR / "nrc_aps_candidate_b_opendataloader_compare_report.json"
RETENTION_MANIFEST_PATH = REPORTS_DIR / "nrc_aps_candidate_b_opendataloader_retention_manifest.json"
CORPUS_DIR = TESTS_DIR / "fixtures" / "nrc_aps_docs" / "v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
LABELS_PATH = CORPUS_DIR / "candidate_b_opendataloader_labels.json"
REQUIREMENTS_PATH = TESTS_DIR / "requirements_nrc_aps_candidate_b_opendataloader.txt"
BACKEND_DIR = ROOT / "backend"
FROZEN_FIXTURE_IDS = [
    "ml17123a319",
    "layout",
    "fontish",
    "scanned",
    "mixed",
]
NON_EQUIVALENT_REPO_FIELDS = [
    "document_processing_contract_id",
    "extractor_family",
    "extractor_id",
    "extractor_version",
    "normalization_contract_id",
    "quality_status",
    "degradation_codes",
    "document_class",
    "visual_page_refs[*].status",
    "visual_page_refs[*].visual_page_class",
    "visual_page_refs[*].artifact_ref",
]
DERIVED_COMPARISON_ONLY = [
    "document text segmentation quality",
    "page-level structural density",
    "hidden-text incidence",
    "tagged-PDF benefit",
    "multi-column evidence",
]
PROTECTED_DIFF_PATHS = [
    "backend/app/services/nrc_aps_document_processing.py",
    "backend/app/services/nrc_aps_page_evidence.py",
    "tools/run_nrc_aps_page_evidence_workbench.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    resolved = path.resolve()
    root_resolved = ROOT.resolve()
    try:
        return resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        return resolved.as_posix()


def stable_counter(mapping: Counter[str]) -> dict[str, int]:
    return {key: mapping[key] for key in sorted(mapping)}


def parse_expected_hash() -> str:
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith("opendataloader-pdf=="):
            continue
        for fragment in stripped.split():
            if fragment.startswith("--hash=sha256:"):
                return fragment.split("sha256:", 1)[1]
    raise RuntimeError("missing_odl_expected_hash")


def load_manifest() -> dict[str, Any]:
    payload = read_json(MANIFEST_PATH)
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_manifest_payload")
    return payload


def load_labels() -> dict[str, Any]:
    payload = read_json(LABELS_PATH)
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_labels_payload")
    return payload


def load_first_run_compare(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_first_run_compare_payload")
    return payload


def manifest_entry_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("invalid_manifest_entries")
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        fixture_id = str(entry.get("fixture_id") or "").strip()
        if fixture_id:
            out[fixture_id] = entry
    return out


def labels_entry_map(labels: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = labels.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("invalid_label_entries")
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        fixture_id = str(entry.get("fixture_id") or "").strip()
        if fixture_id:
            out[fixture_id] = entry
    return out


def first_run_baseline_map(first_run_compare: dict[str, Any]) -> dict[str, dict[str, Any]]:
    docs = first_run_compare.get("documents")
    if not isinstance(docs, list):
        raise RuntimeError("invalid_first_run_compare_documents")
    out: dict[str, dict[str, Any]] = {}
    for entry in docs:
        if not isinstance(entry, dict):
            continue
        fixture_id = str(entry.get("fixture_id") or "").strip()
        baseline = entry.get("baseline")
        if fixture_id and isinstance(baseline, dict):
            out[fixture_id] = baseline
    return out


def live_manifest_sha256() -> str:
    return sha256_path(MANIFEST_PATH)


def validate_labels_sidecar(labels: dict[str, Any], manifest_sha256: str) -> dict[str, str]:
    recorded = str(labels.get("manifest_sha256") or "").strip()
    if not recorded:
        raise RuntimeError("missing_labels_manifest_sha256")
    if recorded != manifest_sha256:
        raise RuntimeError("labels_manifest_sha256_mismatch")
    scope = labels.get("first_run_scope") or {}
    included = scope.get("included_fixture_ids") or []
    if list(included) != FROZEN_FIXTURE_IDS:
        raise RuntimeError("labels_fixture_scope_mismatch")
    if bool(scope.get("candidate_a_secondary_comparison", True)):
        raise RuntimeError("secondary_candidate_a_comparison_reopened")
    return {
        "current_manifest_sha256": manifest_sha256,
        "recorded_manifest_sha256": recorded,
        "status": "matched",
    }


def run_shell_command(command: list[str], *, cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        "args": command,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def git_head() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def git_protected_diff() -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", "--", *PROTECTED_DIFF_PATHS],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError("protected_diff_check_failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def build_java_preflight() -> dict[str, Any]:
    where_result = subprocess.run(
        ["where.exe", "java"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if where_result.returncode != 0:
        raise RuntimeError("java_not_on_path")
    java_paths = [line.strip() for line in where_result.stdout.splitlines() if line.strip()]
    version_result = subprocess.run(
        ["java", "-version"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if version_result.returncode != 0:
        raise RuntimeError("java_version_command_failed")
    lines = [line.strip() for line in (version_result.stderr + "\n" + version_result.stdout).splitlines() if line.strip()]
    java_version = lines[0] if lines else "unknown"
    java_vendor = "unknown"
    for line in lines:
        lower = line.lower()
        if "temurin" in lower:
            java_vendor = "Temurin"
            break
        if "adoptium" in lower:
            java_vendor = "Eclipse Adoptium"
            break
        if "openjdk" in lower and java_vendor == "unknown":
            java_vendor = "OpenJDK"
    return {
        "java_version": java_version,
        "java_vendor": java_vendor,
        "java_resolution_path": java_paths[0],
        "java_all_resolution_paths": java_paths,
    }


def build_python_metadata() -> dict[str, Any]:
    expected_hash = parse_expected_hash()
    distribution = importlib.metadata.distribution("opendataloader-pdf")
    return {
        "python_version": sys.version.replace("\n", " "),
        "python_executable": sys.executable,
        "odl_package_name": "opendataloader-pdf",
        "odl_package_version": distribution.version,
        "odl_package_location": str(distribution.locate_file("")),
        "odl_package_sha256_expected": expected_hash,
        "odl_package_sha256_verified": None,
        "odl_package_sha256_verification_reason": "installed_package_directory_not_reconstructable_to_pinned_wheel_hash",
    }


def run_baseline_proof(*, label: str, run_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    proof_dir = run_root / label
    proof_dir.mkdir(parents=True, exist_ok=True)
    report_path = proof_dir / "nrc_aps_document_processing_proof_report.json"
    artifact_report_path = proof_dir / "nrc_aps_artifact_ingestion_validation_report.json"
    content_index_report_path = proof_dir / "nrc_aps_content_index_validation_report.json"
    runtime_root = proof_dir / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["NRC_APS_CORPUS_OCR_MODE"] = "required"
    command = [
        "py",
        "-3.12",
        "tools/run_nrc_aps_document_processing_proof.py",
        "--report",
        str(report_path),
        "--artifact-report",
        str(artifact_report_path),
        "--content-index-report",
        str(content_index_report_path),
        "--runtime-root",
        str(runtime_root),
        "--require-ocr",
    ]
    result = run_shell_command(command, cwd=ROOT, env=env)
    if not result["passed"]:
        raise RuntimeError(f"{label}_proof_failed")
    report_payload = read_json(report_path)
    if not bool(report_payload.get("passed")):
        raise RuntimeError(f"{label}_proof_report_failed")
    result["label"] = label
    result["report_ref"] = repo_rel(report_path)
    result["artifact_report_ref"] = repo_rel(artifact_report_path)
    result["content_index_report_ref"] = repo_rel(content_index_report_path)
    return result, report_payload


def build_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed = hashlib.sha256(f"{stamp}|candidate-b-second-iteration".encode("utf-8")).hexdigest()[:8]
    return f"cbodl2_{stamp}_{seed}"


def typed_nodes(root: Any) -> Iterable[dict[str, Any]]:
    if isinstance(root, dict):
        if isinstance(root.get("type"), str):
            yield root
        kids = root.get("kids")
        if isinstance(kids, list):
            for child in kids:
                yield from typed_nodes(child)
    elif isinstance(root, list):
        for item in root:
            yield from typed_nodes(item)


def page_number_from_node(node: dict[str, Any]) -> int | None:
    raw = node.get("page number")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


def bbox_from_node(node: dict[str, Any]) -> list[float] | None:
    raw = node.get("bounding box")
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    out: list[float] = []
    for value in raw:
        if not isinstance(value, (int, float)):
            return None
        out.append(float(value))
    return out


def collect_footer_pages(root: Any) -> dict[str, Any]:
    pages: list[int] = []
    for node in typed_nodes(root):
        if str(node.get("type") or "").strip().lower() != "footer":
            continue
        page = page_number_from_node(node)
        if page is not None:
            pages.append(page)
    unique_pages = sorted(set(pages))
    return {
        "count": len(pages),
        "pages": unique_pages,
    }


def find_image_source_collisions(image_sources_by_fixture: dict[str, list[str]]) -> list[dict[str, Any]]:
    owners: dict[str, set[str]] = defaultdict(set)
    for fixture_id, sources in image_sources_by_fixture.items():
        for source in sources:
            owners[source].add(fixture_id)
    collisions: list[dict[str, Any]] = []
    for source in sorted(owners):
        fixture_ids = sorted(owners[source])
        if len(fixture_ids) > 1:
            collisions.append({
                "fixture_ids": fixture_ids,
                "source": source,
            })
    return collisions


def detect_layout_multi_column_signal(root: Any) -> bool:
    paragraphs: list[tuple[int, list[float]]] = []
    for node in typed_nodes(root):
        if str(node.get("type") or "").strip().lower() != "paragraph":
            continue
        page = page_number_from_node(node)
        bbox = bbox_from_node(node)
        if page is None or bbox is None:
            continue
        paragraphs.append((page, bbox))
    by_page: dict[int, list[list[float]]] = defaultdict(list)
    for page, bbox in paragraphs:
        by_page[page].append(bbox)
    for boxes in by_page.values():
        for index, left in enumerate(boxes):
            for right in boxes[index + 1:]:
                horizontal_gap = abs(right[0] - left[0])
                top = max(left[1], right[1])
                bottom = min(left[3], right[3])
                vertical_overlap = max(0.0, bottom - top)
                if horizontal_gap >= 180.0 and vertical_overlap >= 20.0:
                    return True
    return False


def normalize_candidate_text(root: Any) -> str:
    parts: list[str] = []
    for node in typed_nodes(root):
        content = node.get("content")
        if not isinstance(content, str):
            continue
        cleaned = " ".join(content.split())
        if cleaned:
            parts.append(cleaned)
    return "\n".join(parts)


def hidden_text_count(root: Any) -> int:
    count = 0
    for node in typed_nodes(root):
        node_type = str(node.get("type") or "").strip().lower().replace("_", "-")
        if node_type == "hidden-text":
            count += 1
    return count


def detect_struct_tree_state(log_text: str) -> tuple[str, str]:
    lowered = log_text.lower()
    if "struct" in lowered and ("ignored" in lowered or "no structure tree" in lowered or "not found" in lowered):
        return "struct_tree_absent", "execution_log_warning_use_struct_tree_ignored"
    return "struct_tree_unknown", "no_explicit_struct_tree_signal_in_execution_log"


def summarize_candidate_output(
    *,
    fixture_id: str,
    label_entry: dict[str, Any],
    raw_json_path: Path,
    raw_markdown_path: Path,
    log_text: str,
) -> dict[str, Any]:
    root = read_json(raw_json_path)
    normalized_text = normalize_candidate_text(root)
    footer_info = collect_footer_pages(root)
    element_counts: Counter[str] = Counter()
    page_element_counts: dict[int, Counter[str]] = defaultdict(Counter)
    heading_counts: Counter[int] = Counter()
    list_counts: Counter[int] = Counter()
    table_counts: Counter[int] = Counter()
    image_counts: Counter[int] = Counter()
    hidden_counts: Counter[int] = Counter()
    image_sources: list[str] = []
    for node in typed_nodes(root):
        node_type = str(node.get("type") or "").strip().lower()
        if not node_type:
            continue
        element_counts[node_type] += 1
        page = page_number_from_node(node)
        if page is not None:
            page_element_counts[page][node_type] += 1
        if node_type == "heading" and page is not None:
            heading_counts[page] += 1
        if node_type == "list" and page is not None:
            list_counts[page] += 1
        if node_type == "table" and page is not None:
            table_counts[page] += 1
        if node_type == "image":
            source = str(node.get("source") or "").strip()
            if source:
                image_sources.append(source)
            if page is not None:
                image_counts[page] += 1
        normalized_type = node_type.replace("_", "-")
        if normalized_type == "hidden-text" and page is not None:
            hidden_counts[page] += 1
    struct_tree_state, struct_tree_source = detect_struct_tree_state(log_text)
    page_count = int(root.get("number of pages") or 0)
    page_summaries: list[dict[str, Any]] = []
    for page_number in range(1, page_count + 1):
        limitation_tags: list[str] = []
        if page_number in footer_info["pages"]:
            limitation_tags.append("footer_emitted_despite_config")
        page_summaries.append({
            "element_type_counts": stable_counter(page_element_counts[page_number]),
            "heading_count": heading_counts[page_number],
            "hidden_text_count": hidden_counts[page_number],
            "hidden_text_present": hidden_counts[page_number] > 0,
            "image_count": image_counts[page_number],
            "limitation_tags": limitation_tags,
            "non_equivalence_tags": [],
            "page_number": page_number,
            "semantic_gain_hypotheses": [],
            "struct_tree_state": struct_tree_state,
            "table_count": table_counts[page_number],
        })
    warning_flags: list[str] = []
    if footer_info["count"] > 0:
        warning_flags.append("include_header_footer_false_but_header_footer_emitted")
    if struct_tree_state == "struct_tree_absent":
        warning_flags.append("use_struct_tree_ignored_no_structure_tree")
    limitation_flags = ["non_equivalent_owner_field"]
    if "scanned_ocr_control" in list(label_entry.get("regime_labels") or []):
        limitation_flags.append("ocr_owner_path_non_equivalence")
        limitation_flags.append("image_not_equivalent_to_visual_page_refs")
    return {
        "candidate_b_normalized_char_count": len(normalized_text),
        "candidate_b_normalized_text": normalized_text,
        "caption_count": int(element_counts.get("caption", 0)),
        "element_counts_by_type": stable_counter(element_counts),
        "file_name": str(root.get("file name") or raw_json_path.name),
        "footer_page_numbers": footer_info["pages"],
        "footer_node_count": footer_info["count"],
        "heading_count": int(element_counts.get("heading", 0)),
        "hidden_text_node_count": hidden_text_count(root),
        "hidden_text_present": hidden_text_count(root) > 0,
        "image_count": int(element_counts.get("image", 0)),
        "image_sources": sorted(set(image_sources)),
        "limitation_flags": limitation_flags,
        "list_count": int(element_counts.get("list", 0)),
        "odl_page_count": page_count,
        "page_summaries": page_summaries,
        "processing_status": "succeeded",
        "raw_json_ref": repo_rel(raw_json_path),
        "raw_json_sha256": sha256_path(raw_json_path),
        "raw_markdown_ref": repo_rel(raw_markdown_path),
        "raw_markdown_sha256": sha256_path(raw_markdown_path),
        "struct_tree_state": struct_tree_state,
        "struct_tree_state_source": struct_tree_source,
        "table_count": int(element_counts.get("table", 0)),
        "warning_flags": warning_flags,
    }


def ocr_control_pages(candidate_b_summary: dict[str, Any]) -> list[int]:
    return sorted(
        page_summary["page_number"]
        for page_summary in candidate_b_summary.get("page_summaries") or []
        if page_summary.get("image_count", 0) > 0
    )


def run_candidate_b_cli(
    *,
    fixture_entry: dict[str, Any],
    raw_root: Path,
) -> tuple[dict[str, Any], str]:
    fixture_path = CORPUS_DIR / str(fixture_entry.get("path") or "")
    if not fixture_path.exists():
        raise RuntimeError(f"missing_fixture:{fixture_entry.get('fixture_id')}")
    fixture_id = str(fixture_entry.get("fixture_id") or "").strip()
    image_dir = Path("images") / fixture_id
    command = [
        sys.executable,
        "-m",
        "opendataloader_pdf",
        str(fixture_path),
        "--output-dir",
        ".",
        "--format",
        "json,markdown",
        "--reading-order",
        "xycut",
        "--table-method",
        "default",
        "--image-output",
        "external",
        "--image-format",
        "png",
        "--image-dir",
        image_dir.as_posix(),
        "--replace-invalid-chars",
        " ",
        "--use-struct-tree",
        "--hybrid",
        "off",
    ]
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=str(raw_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    elapsed = time.perf_counter() - started
    combined_output = (result.stdout or "") + ("\n" if result.stdout and result.stderr else "") + (result.stderr or "")
    json_path = raw_root / f"{fixture_path.stem}.json"
    markdown_path = raw_root / f"{fixture_path.stem}.md"
    if result.returncode != 0:
        return ({
            "fixture_id": fixture_id,
            "elapsed_seconds": elapsed,
            "passed": False,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "raw_json_exists": json_path.exists(),
            "raw_markdown_exists": markdown_path.exists(),
        }, combined_output)
    if not json_path.exists() or not markdown_path.exists():
        raise RuntimeError(f"missing_candidate_b_output:{fixture_id}")
    return ({
        "fixture_id": fixture_id,
        "elapsed_seconds": elapsed,
        "passed": True,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "raw_json_ref": repo_rel(json_path),
        "raw_markdown_ref": repo_rel(markdown_path),
        "image_dir": (raw_root / image_dir).as_posix(),
    }, combined_output)


def durable_report_inventory(paths: list[Path]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for path in paths:
        inventory.append({
            "category": "durable_report",
            "path": repo_rel(path),
            "sha256": sha256_path(path),
            "size_bytes": path.stat().st_size,
        })
    return inventory


def raw_file_inventory(raw_root: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for path in sorted(raw_root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        category = "candidate_b_raw_file"
        relative = repo_rel(path)
        if "baseline_" in relative and suffix == ".json":
            category = "baseline_proof_artifact"
        elif suffix == ".json":
            category = "candidate_b_raw_json"
        elif suffix == ".md":
            category = "candidate_b_raw_markdown"
        elif suffix in {".png", ".jpeg", ".jpg"}:
            category = "candidate_b_extracted_image"
        inventory.append({
            "category": category,
            "path": relative,
            "sha256": sha256_path(path),
            "size_bytes": path.stat().st_size,
        })
    return inventory


def outputs_outside_approved_roots(paths: Iterable[str]) -> list[str]:
    approved_prefixes = [
        "tests/reports/nrc_aps_candidate_b_opendataloader_raw/",
        "tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json",
        "tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json",
        "tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json",
    ]
    out: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if not any(normalized.startswith(prefix) for prefix in approved_prefixes):
            out.append(normalized)
    return sorted(set(out))


def build_batch_plan(fixture_ids: list[str]) -> dict[str, Any]:
    return {
        "batch_count": len(fixture_ids),
        "batches": [
            {
                "batch_id": index + 1,
                "fixture_ids": [fixture_id],
            }
            for index, fixture_id in enumerate(fixture_ids)
        ],
        "split_reason": "per_document_external_image_provenance_isolation",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Candidate B second-iteration workbench proof.")
    parser.add_argument("--first-run-compare-report", required=True)
    parser.add_argument("--proof-report", default=str(PROOF_REPORT_PATH))
    parser.add_argument("--compare-report", default=str(COMPARE_REPORT_PATH))
    parser.add_argument("--retention-manifest", default=str(RETENTION_MANIFEST_PATH))
    args = parser.parse_args(argv)

    started = time.perf_counter()
    proof_report_path = Path(args.proof_report)
    compare_report_path = Path(args.compare_report)
    retention_manifest_path = Path(args.retention_manifest)
    first_run_compare_path = Path(args.first_run_compare_report)

    manifest = load_manifest()
    labels = load_labels()
    manifest_sha = live_manifest_sha256()
    label_hash_status = validate_labels_sidecar(labels, manifest_sha)
    label_entry_by_fixture = labels_entry_map(labels)
    manifest_entry_by_fixture = manifest_entry_map(manifest)
    first_run_compare = load_first_run_compare(first_run_compare_path)
    first_run_baseline_by_fixture = first_run_baseline_map(first_run_compare)

    fixture_entries: list[dict[str, Any]] = []
    for fixture_id in FROZEN_FIXTURE_IDS:
        manifest_entry = manifest_entry_by_fixture.get(fixture_id)
        if manifest_entry is None:
            raise RuntimeError(f"manifest_fixture_missing:{fixture_id}")
        fixture_entries.append(manifest_entry)

    java_preflight = build_java_preflight()
    python_metadata = build_python_metadata()
    run_id = build_run_id()
    raw_root = RAW_OUTPUT_PARENT / run_id
    raw_root.mkdir(parents=True, exist_ok=True)

    batch_plan = build_batch_plan(FROZEN_FIXTURE_IDS)
    execution_events: list[dict[str, Any]] = []
    baseline_before_command, baseline_before_report = run_baseline_proof(label="baseline_before_require_ocr", run_root=raw_root)
    execution_events.append({
        "event": "baseline_before_require_ocr_passed",
        "passed": True,
        "report_ref": baseline_before_command["report_ref"],
    })

    documents: list[dict[str, Any]] = []
    failed_documents: list[dict[str, Any]] = []
    element_counts_total: Counter[str] = Counter()
    regime_counts: Counter[str] = Counter()
    limitation_counts: Counter[str] = Counter()
    structural_gain_signals: list[dict[str, Any]] = []
    hidden_text_signals: list[dict[str, Any]] = []
    control_limitations: list[dict[str, Any]] = []
    text_presence_deltas: list[dict[str, Any]] = []
    scanned_control_pages: list[dict[str, Any]] = []
    image_sources_by_fixture: dict[str, list[str]] = {}
    page_count_mismatches: list[dict[str, Any]] = []
    page_count_matches = 0
    candidate_convert_elapsed = 0.0

    for fixture_entry in fixture_entries:
        fixture_id = str(fixture_entry.get("fixture_id") or "").strip()
        label_entry = label_entry_by_fixture.get(fixture_id)
        baseline_summary = first_run_baseline_by_fixture.get(fixture_id)
        if label_entry is None or baseline_summary is None:
            raise RuntimeError(f"missing_reference_data:{fixture_id}")
        for regime_label in list(label_entry.get("regime_labels") or []):
            regime_counts[str(regime_label)] += 1
        cli_result, log_text = run_candidate_b_cli(fixture_entry=fixture_entry, raw_root=raw_root)
        candidate_convert_elapsed += float(cli_result["elapsed_seconds"])
        if not cli_result["passed"]:
            failed = {
                "fixture_id": fixture_id,
                "reason": "candidate_b_convert_failed",
                "exit_code": cli_result["exit_code"],
            }
            failed_documents.append(failed)
            execution_events.append({
                "event": "candidate_b_convert_failed",
                "fixture_id": fixture_id,
                "exit_code": cli_result["exit_code"],
            })
            documents.append({
                "baseline": baseline_summary,
                "candidate_b": {
                    "processing_status": "failed",
                    "raw_json_ref": None,
                    "raw_markdown_ref": None,
                    "warning_flags": ["raw_output_generation_failure"],
                },
                "document_ref": str(label_entry.get("document_ref") or ""),
                "document_sha256": str(label_entry.get("document_sha256") or ""),
                "expected_gain_claims": list(label_entry.get("expected_gain_claims") or []),
                "expected_non_equivalences": list(label_entry.get("expected_non_equivalences") or []),
                "fixture_id": fixture_id,
                "page_scope": str(label_entry.get("page_scope") or "all"),
                "regime_labels": list(label_entry.get("regime_labels") or []),
                "review_notes": str(label_entry.get("review_notes") or ""),
            })
            continue

        json_path = raw_root / f"{Path(str(fixture_entry.get('path') or '')).stem}.json"
        markdown_path = raw_root / f"{Path(str(fixture_entry.get('path') or '')).stem}.md"
        candidate_summary = summarize_candidate_output(
            fixture_id=fixture_id,
            label_entry=label_entry,
            raw_json_path=json_path,
            raw_markdown_path=markdown_path,
            log_text=log_text,
        )
        image_sources_by_fixture[fixture_id] = list(candidate_summary["image_sources"])
        element_counts_total.update(candidate_summary["element_counts_by_type"])
        for limitation_flag in candidate_summary["limitation_flags"]:
            limitation_counts[limitation_flag] += 1
        structural_signals: list[str] = []
        if fixture_id == "layout" and detect_layout_multi_column_signal(read_json(json_path)):
            structural_signals.append("expected_multi_column_signal")
        structural_gain_signals.append({
            "fixture_id": fixture_id,
            "signals": structural_signals,
        })
        hidden_text_signals.append({
            "fixture_id": fixture_id,
            "hidden_text_present": bool(candidate_summary["hidden_text_present"]),
        })
        control_tags = []
        if "scanned_ocr_control" in list(label_entry.get("regime_labels") or []):
            control_tags.append("ocr_owner_path_non_equivalence")
            control_tags.append("image_not_equivalent_to_visual_page_refs")
            scanned_pages = ocr_control_pages(candidate_summary)
            scanned_control_pages.append({
                "fixture_id": fixture_id,
                "pages": scanned_pages,
            })
        control_limitations.append({
            "fixture_id": fixture_id,
            "limitations": control_tags,
        })
        baseline_page_count = int(baseline_summary.get("page_count") or 0)
        candidate_page_count = int(candidate_summary["odl_page_count"])
        if baseline_page_count == candidate_page_count:
            page_count_matches += 1
        else:
            page_count_mismatches.append({
                "fixture_id": fixture_id,
                "baseline_page_count": baseline_page_count,
                "candidate_b_page_count": candidate_page_count,
            })
        baseline_chars = int(baseline_summary.get("normalized_char_count") or 0)
        candidate_chars = int(candidate_summary["candidate_b_normalized_char_count"])
        text_presence_deltas.append({
            "baseline_char_count": baseline_chars,
            "baseline_has_text": baseline_chars > 0,
            "candidate_b_char_count": candidate_chars,
            "candidate_b_has_text": candidate_chars > 0,
            "char_delta": candidate_chars - baseline_chars,
            "fixture_id": fixture_id,
        })
        documents.append({
            "baseline": baseline_summary,
            "candidate_b": candidate_summary,
            "document_ref": str(label_entry.get("document_ref") or ""),
            "document_sha256": str(label_entry.get("document_sha256") or ""),
            "expected_gain_claims": list(label_entry.get("expected_gain_claims") or []),
            "expected_non_equivalences": list(label_entry.get("expected_non_equivalences") or []),
            "fixture_id": fixture_id,
            "page_scope": str(label_entry.get("page_scope") or "all"),
            "regime_labels": list(label_entry.get("regime_labels") or []),
            "review_notes": str(label_entry.get("review_notes") or ""),
        })
        execution_events.append({
            "event": "candidate_b_convert_passed",
            "fixture_id": fixture_id,
            "elapsed_seconds": cli_result["elapsed_seconds"],
            "raw_json_ref": candidate_summary["raw_json_ref"],
            "raw_markdown_ref": candidate_summary["raw_markdown_ref"],
        })

    baseline_after_command, baseline_after_report = run_baseline_proof(label="baseline_after_require_ocr", run_root=raw_root)
    execution_events.append({
        "event": "baseline_after_require_ocr_passed",
        "passed": True,
        "report_ref": baseline_after_command["report_ref"],
    })

    image_collisions = find_image_source_collisions(image_sources_by_fixture)
    footer_warning_fixtures = sorted(
        doc["fixture_id"]
        for doc in documents
        if isinstance(doc.get("candidate_b"), dict) and doc["candidate_b"].get("footer_node_count", 0) > 0
    )
    interference_check_passed = bool(baseline_before_report.get("passed")) and bool(baseline_after_report.get("passed"))
    interference_check_status = "passed" if interference_check_passed else "failed"
    execution_seconds = time.perf_counter() - started

    proof_report = {
        "schema_id": "aps.candidate_b_opendataloader.proof_report.v2",
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "repo_root": str(ROOT),
        "git_revision": git_head(),
        "python_version": python_metadata["python_version"],
        "python_executable": python_metadata["python_executable"],
        "java_version": java_preflight["java_version"],
        "java_vendor": java_preflight["java_vendor"],
        "java_resolution_path": java_preflight["java_resolution_path"],
        "odl_package_name": python_metadata["odl_package_name"],
        "odl_package_version": python_metadata["odl_package_version"],
        "odl_package_location": python_metadata["odl_package_location"],
        "odl_package_sha256_expected": python_metadata["odl_package_sha256_expected"],
        "odl_package_sha256_verified": python_metadata["odl_package_sha256_verified"],
        "odl_package_sha256_verification_reason": python_metadata["odl_package_sha256_verification_reason"],
        "odl_config_snapshot": {
            "batch_input_fixture_ids": list(FROZEN_FIXTURE_IDS),
            "format": "json,markdown",
            "hybrid": "off",
            "image_dir": "images/<fixture_id>",
            "image_format": "png",
            "image_output": "external",
            "include_header_footer": False,
            "keep_line_breaks": False,
            "quiet": False,
            "reading_order": "xycut",
            "replace_invalid_chars": " ",
            "table_method": "default",
            "use_struct_tree": True,
        },
        "batch_plan": batch_plan,
        "batch_count": batch_plan["batch_count"],
        "corpus_manifest_ref": repo_rel(MANIFEST_PATH),
        "corpus_manifest_sha256": manifest_sha,
        "labels_ref": repo_rel(LABELS_PATH),
        "labels_sha256": sha256_path(LABELS_PATH),
        "raw_output_root": repo_rel(raw_root),
        "baseline_before_initial_default_reference": None,
        "baseline_before_reference": baseline_before_command["report_ref"],
        "baseline_after_reference": baseline_after_command["report_ref"],
        "documents_attempted": len(FROZEN_FIXTURE_IDS),
        "documents_succeeded": len(FROZEN_FIXTURE_IDS) - len(failed_documents),
        "documents_failed": len(failed_documents),
        "failed_documents": failed_documents,
        "documents": documents,
        "struct_tree_present_count": sum(
            1 for doc in documents if doc.get("candidate_b", {}).get("struct_tree_state") == "struct_tree_present"
        ),
        "struct_tree_absent_count": sum(
            1 for doc in documents if doc.get("candidate_b", {}).get("struct_tree_state") == "struct_tree_absent"
        ),
        "struct_tree_unknown_count": sum(
            1 for doc in documents if doc.get("candidate_b", {}).get("struct_tree_state") == "struct_tree_unknown"
        ),
        "element_counts_by_type": stable_counter(element_counts_total),
        "hidden_text_document_count": sum(1 for item in hidden_text_signals if item["hidden_text_present"]),
        "regime_counts": stable_counter(regime_counts),
        "limitation_counts": stable_counter(limitation_counts),
        "safety_filter_state": "default_on",
        "execution_seconds": execution_seconds,
        "interference_check_passed": interference_check_passed,
        "interference_check_status": interference_check_status,
        "execution_events": execution_events,
        "warnings": {
            "header_footer_emitted_despite_config": footer_warning_fixtures,
            "image_source_collisions": image_collisions,
            "labels_sidecar_manifest_hash_status": label_hash_status,
        },
        "durable_report_hash_authority": repo_rel(RETENTION_MANIFEST_PATH),
        "baseline_before_command": baseline_before_command,
        "baseline_after_command": baseline_after_command,
        "candidate_b_convert_elapsed_seconds": candidate_convert_elapsed,
    }
    write_json(proof_report_path, proof_report)

    if image_collisions:
        decision_recommendation = "stop_candidate_b_or_target_provenance_again"
    elif footer_warning_fixtures:
        decision_recommendation = "workbench_useful_with_explicit_footer_limitation"
    else:
        decision_recommendation = "good_enough_for_continued_workbench_use"

    compare_report = {
        "schema_id": "aps.candidate_b_opendataloader.compare_report.v2",
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "repo_root": str(ROOT),
        "git_revision": git_head(),
        "python_version": python_metadata["python_version"],
        "python_executable": python_metadata["python_executable"],
        "java_version": java_preflight["java_version"],
        "java_vendor": java_preflight["java_vendor"],
        "odl_package_name": python_metadata["odl_package_name"],
        "odl_package_version": python_metadata["odl_package_version"],
        "odl_package_sha256_expected": python_metadata["odl_package_sha256_expected"],
        "odl_package_sha256_verified": python_metadata["odl_package_sha256_verified"],
        "odl_config_snapshot": proof_report["odl_config_snapshot"],
        "batch_plan": batch_plan,
        "corpus_manifest_ref": repo_rel(MANIFEST_PATH),
        "corpus_manifest_sha256": manifest_sha,
        "labels_ref": repo_rel(LABELS_PATH),
        "labels_sha256": sha256_path(LABELS_PATH),
        "raw_output_root": repo_rel(raw_root),
        "baseline_reference": baseline_before_command["report_ref"],
        "candidate_a_reference": None,
        "prior_iteration_compare_reference": repo_rel(first_run_compare_path),
        "documents": documents,
        "page_count_match": len(page_count_mismatches) == 0,
        "page_count_matches": page_count_matches,
        "page_count_mismatches": page_count_mismatches,
        "page_index_consistency": len(page_count_mismatches) == 0,
        "text_presence_delta": text_presence_deltas,
        "text_presence_deltas": text_presence_deltas,
        "structural_gain_signals": structural_gain_signals,
        "candidate_b_structural_gain_signals": structural_gain_signals,
        "candidate_b_hidden_text_signals": hidden_text_signals,
        "control_limitations": control_limitations,
        "vector_control_pages": [],
        "scanned_ocr_control_pages": scanned_control_pages,
        "ocr_control_findings": scanned_control_pages,
        "candidate_b_non_equivalent_fields": list(NON_EQUIVALENT_REPO_FIELDS),
        "non_equivalent_repo_fields": list(NON_EQUIVALENT_REPO_FIELDS),
        "derived_comparison_only": list(DERIVED_COMPARISON_ONLY),
        "decision_recommendation": decision_recommendation,
        "decision_rationale": [
            "Baseline proof passed before and after the Candidate B second iteration under OCR-required proof posture.",
            "Per-document execution isolates external image output paths so provenance can be judged document-by-document.",
            "Header/footer emission is treated as a package-behavior control-noise finding and not silently normalized away.",
            "Candidate B remains workbench-only and does not change runtime owner-path behavior.",
        ],
        "remediation_findings": {
            "image_source_collisions": {
                "status": "resolved" if not image_collisions else "unresolved",
                "collisions": image_collisions,
            },
            "footer_emission": {
                "status": "resolved" if not footer_warning_fixtures else "detected_not_suppressed",
                "fixtures": footer_warning_fixtures,
            },
            "labels_sidecar_manifest_hash": label_hash_status,
            "java_preflight": {
                "status": "passed",
                "java_resolution_path": java_preflight["java_resolution_path"],
                "java_version": java_preflight["java_version"],
                "java_vendor": java_preflight["java_vendor"],
            },
        },
        "interference_check_passed": interference_check_passed,
        "durable_report_hash_authority": repo_rel(RETENTION_MANIFEST_PATH),
    }
    write_json(compare_report_path, compare_report)

    durable_inventory = durable_report_inventory([proof_report_path, compare_report_path])
    raw_inventory = raw_file_inventory(raw_root)
    written_paths = [entry["path"] for entry in durable_inventory] + [entry["path"] for entry in raw_inventory]
    retention_manifest = {
        "schema_id": "aps.candidate_b_opendataloader.retention_manifest.v2",
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "repo_root": str(ROOT),
        "git_revision": git_head(),
        "raw_output_root": repo_rel(raw_root),
        "approved_output_roots": [
            "tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/",
            "tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json",
            "tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json",
            "tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json",
        ],
        "durable_report_hash_authority": repo_rel(retention_manifest_path),
        "durable_report_inventory": durable_inventory,
        "raw_file_inventory": raw_inventory,
        "execution_events": execution_events,
        "image_source_collisions": image_collisions,
        "label_sidecar_manifest_hash_status": label_hash_status,
        "outputs_outside_approved_roots": outputs_outside_approved_roots(written_paths),
        "raw_outputs_committed": False,
        "retention_posture": "raw_outputs_retained_locally_under_run_scoped_root_not_committed",
    }
    write_json(retention_manifest_path, retention_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
