from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

import app.api.review_nrc_aps as review_api
import app.services.review_nrc_aps_candidate_b_trace as trace_service
import app.services.review_nrc_aps_runtime as runtime_service
import app.services.review_nrc_aps_workbench_compare as compare_service
from app.schemas.review_nrc_aps import NrcApsReviewRunSelectorItemOut, NrcApsReviewRunSelectorOut
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding
from tests.review_nrc_aps_runtime_fixture import latest_document_trace_ready_runtime, make_session, resolve_target_for_accession


RUNTIME = latest_document_trace_ready_runtime()


@dataclass(frozen=True)
class ReviewBrowserFixture:
    baseline_binding: ReviewRuntimeBinding
    candidate_a_binding: ReviewRuntimeBinding
    checkout_root: Path
    bundle_id: str
    fixture_id: str
    selector: NrcApsReviewRunSelectorOut


def capture_review_browser_patch_state() -> dict[str, object]:
    return {
        "runtime_discover_review_roots": runtime_service.discover_review_roots,
        "compare_discover_runtime_bindings": compare_service.discover_runtime_bindings,
        "compare_discover_candidate_runs": compare_service.discover_candidate_runs,
        "api_discover_candidate_runs": review_api.discover_candidate_runs,
        "api_discover_workbench_compare_sources": review_api.discover_workbench_compare_sources,
        "api_compose_workbench_compare_targets": review_api.compose_workbench_compare_targets,
        "api_compose_workbench_compare_manifest": review_api.compose_workbench_compare_manifest,
        "api_compose_workbench_compare_tab": review_api.compose_workbench_compare_tab,
        "api_compose_candidate_b_trace_manifest": review_api.compose_candidate_b_trace_manifest,
        "api_resolve_candidate_b_trace_annotated_pdf_info": review_api.resolve_candidate_b_trace_annotated_pdf_info,
        "api_load_candidate_b_trace_raw_json": review_api.load_candidate_b_trace_raw_json,
        "api_load_candidate_b_trace_raw_markdown": review_api.load_candidate_b_trace_raw_markdown,
    }


def restore_review_browser_patches(patch_state: dict[str, object]) -> None:
    runtime_service.discover_review_roots = patch_state["runtime_discover_review_roots"]
    compare_service.discover_runtime_bindings = patch_state["compare_discover_runtime_bindings"]
    compare_service.discover_candidate_runs = patch_state["compare_discover_candidate_runs"]
    review_api.discover_candidate_runs = patch_state["api_discover_candidate_runs"]
    review_api.discover_workbench_compare_sources = patch_state["api_discover_workbench_compare_sources"]
    review_api.compose_workbench_compare_targets = patch_state["api_compose_workbench_compare_targets"]
    review_api.compose_workbench_compare_manifest = patch_state["api_compose_workbench_compare_manifest"]
    review_api.compose_workbench_compare_tab = patch_state["api_compose_workbench_compare_tab"]
    review_api.compose_candidate_b_trace_manifest = patch_state["api_compose_candidate_b_trace_manifest"]
    review_api.resolve_candidate_b_trace_annotated_pdf_info = patch_state["api_resolve_candidate_b_trace_annotated_pdf_info"]
    review_api.load_candidate_b_trace_raw_json = patch_state["api_load_candidate_b_trace_raw_json"]
    review_api.load_candidate_b_trace_raw_markdown = patch_state["api_load_candidate_b_trace_raw_markdown"]
    runtime_service._load_binding_request_config_json.cache_clear()


def _load_unique_manifest_entry() -> dict[str, str]:
    manifest_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    basenames: dict[str, dict[str, str] | None] = {}
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        basename = Path(str(entry.get("path") or "")).name.strip().lower()
        if not basename:
            continue
        if basename in basenames:
            basenames[basename] = None
            continue
        basenames[basename] = {
            "fixture_id": str(entry.get("fixture_id") or "").strip(),
            "basename": Path(str(entry.get("path") or "")).name.strip(),
        }
    for item in basenames.values():
        if item:
            return item
    raise AssertionError("Expected at least one unique corpus-manifest entry")


def _source_target_id() -> str:
    session = make_session(RUNTIME)
    try:
        target_id, _ = resolve_target_for_accession(session, RUNTIME.run_id)
        return target_id
    except AssertionError:
        row = session.execute(
            text(
                "SELECT connector_run_target_id FROM connector_run_target "
                "WHERE connector_run_id = :run_id ORDER BY connector_run_target_id ASC LIMIT 1"
            ),
            {"run_id": RUNTIME.run_id},
        ).first()
        assert row is not None, f"Could not find any target in run {RUNTIME.run_id}"
        return str(row[0])
    finally:
        session.close()


def _copy_runtime_binding(
    tmp_path: Path,
    *,
    run_id: str,
    visual_lane_mode: str | None,
    target_id: str,
    sciencebase_basename: str,
) -> ReviewRuntimeBinding:
    copied_root = tmp_path / run_id
    shutil.copytree(RUNTIME.runtime_dir, copied_root)

    copied_storage_dir = copied_root / "storage"
    source_storage_dir = RUNTIME.storage_dir.resolve() if RUNTIME.storage_dir and RUNTIME.storage_dir.exists() else None
    if source_storage_dir is not None and not copied_storage_dir.exists():
        try:
            source_storage_dir.relative_to(RUNTIME.runtime_dir.resolve())
        except ValueError:
            shutil.copytree(source_storage_dir, copied_storage_dir)

    summary_path = copied_root / "local_corpus_e2e_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["run_id"] = run_id
    summary["database_path"] = "lc.db"
    summary["database_url"] = "sqlite:///lc.db"
    summary["storage_dir"] = "storage" if copied_storage_dir.exists() else ""
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    database_path = copied_root / RUNTIME.db_path.name
    request_config: dict[str, str] = {}
    if visual_lane_mode:
        request_config["visual_lane_mode"] = visual_lane_mode

    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute("UPDATE connector_run SET connector_run_id = ?, request_config_json = ?", (run_id, json.dumps(request_config)))
        connection.execute("UPDATE connector_run_target SET connector_run_id = ?", (run_id,))
        connection.execute("UPDATE aps_content_linkage SET run_id = ?", (run_id,))
        connection.execute(
            """
            UPDATE connector_run_target
            SET sciencebase_file_name = ?
            WHERE connector_run_id = ? AND connector_run_target_id = ?
            """,
            (sciencebase_basename, run_id, target_id),
        )
        connection.commit()
    finally:
        connection.close()

    return ReviewRuntimeBinding(
        run_id=run_id,
        review_root=copied_root,
        summary=summary,
        database_path=database_path,
        storage_dir=copied_storage_dir if copied_storage_dir.exists() else None,
    )


def _write_candidate_b_bundle(tmp_path: Path, *, fixture_id: str, sciencebase_basename: str) -> tuple[Path, str]:
    checkout_root = tmp_path / "checkout"
    manifest_source = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"
    manifest_dest = checkout_root / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_source, manifest_dest)

    bundle_rel = Path("tests") / "reports" / "cb-compare-browser-test"
    bundle_root = checkout_root / bundle_rel
    raw_root = bundle_root / "raw"
    annotated_path = raw_root / "annotated" / f"{fixture_id}.pdf"
    raw_json_path = raw_root / f"{fixture_id}.json"
    raw_markdown_path = raw_root / f"{fixture_id}.md"
    raw_root.mkdir(parents=True, exist_ok=True)

    annotated_path.parent.mkdir(parents=True, exist_ok=True)
    annotated_path.write_bytes(b"%PDF-1.4\n% candidate b browser fixture\n")
    raw_json_path.write_text(json.dumps({"fixture_id": fixture_id, "kind": "candidate_b"}, indent=2), encoding="utf-8")
    raw_markdown_path.write_text(f"# Candidate B\n\nFixture: {fixture_id}\n", encoding="utf-8")

    annotated_ref = (bundle_rel / "raw" / "annotated" / f"{fixture_id}.pdf").as_posix()
    raw_json_ref = (bundle_rel / "raw" / f"{fixture_id}.json").as_posix()
    raw_markdown_ref = (bundle_rel / "raw" / f"{fixture_id}.md").as_posix()
    raw_output_root = (bundle_rel / "raw").as_posix()

    (bundle_root / "baseline-summary.json").write_text(
        json.dumps({"documents": [{"fixture_id": fixture_id, "baseline": {"char_count": 1200}}]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (bundle_root / "compare.json").write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-04-13T23:00:00Z",
                "run_id": "cb-run-browser-001",
                "decision_recommendation": "workbench_useful_with_explicit_footer_limitation",
                "interference_check_passed": True,
                "derived_comparison_only": ["candidate_b_normalized_text"],
                "non_equivalent_repo_fields": ["element_counts_by_type"],
                "raw_output_root": raw_output_root,
                "documents": [
                    {
                        "fixture_id": fixture_id,
                        "document_ref": "doc-ref-browser-001",
                        "document_sha256": "sha256-browser-001",
                        "baseline": {"char_count": 1200},
                        "expected_gain_claims": ["heading_count"],
                        "expected_non_equivalences": ["element_counts_by_type"],
                        "regime_labels": ["browser_regression"],
                        "review_notes": "Browser regression fixture.",
                        "candidate_b": {
                            "file_name": sciencebase_basename,
                            "processing_status": "succeeded",
                            "candidate_b_normalized_char_count": 1188,
                            "candidate_b_normalized_text": "Candidate B normalized text body",
                            "odl_page_count": 4,
                            "heading_count": 2,
                            "list_count": 1,
                            "image_count": 0,
                            "table_count": 1,
                            "hidden_text_present": False,
                            "hidden_text_node_count": 0,
                            "struct_tree_state": "struct_tree_absent",
                            "element_counts_by_type": {"Text": 14, "Title": 2},
                            "page_summaries": [{"page_number": 1, "element_count": 5}],
                            "footer_page_numbers": [4],
                            "image_sources": [],
                            "limitation_flags": ["footer_page_numbers_detected"],
                            "warning_flags": ["footer_warning"],
                            "annotated_pdf_status": "present",
                            "annotated_pdf_ref": annotated_ref,
                            "raw_json_ref": raw_json_ref,
                            "raw_markdown_ref": raw_markdown_ref,
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle_root / "proof.json").write_text(
        json.dumps(
            {
                "warnings": {
                    "header_footer_emitted_despite_config": [fixture_id],
                    "image_source_collisions": [],
                    "labels_sidecar_manifest_hash_status": {"status": "matched"},
                },
                "interference_check_passed": True,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (bundle_root / "retain.json").write_text(
        json.dumps(
            {
                "raw_file_inventory": [
                    {"path": annotated_ref, "category": "candidate_b_annotated_pdf"},
                    {"path": raw_json_ref, "category": "candidate_b_raw_json"},
                    {"path": raw_markdown_ref, "category": "candidate_b_raw_markdown"},
                ],
                "outputs_outside_approved_roots": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return checkout_root, bundle_rel.as_posix()


def build_review_browser_fixture(tmp_path: Path) -> ReviewBrowserFixture:
    manifest_entry = _load_unique_manifest_entry()
    source_target_id = _source_target_id()
    baseline_binding = _copy_runtime_binding(
        tmp_path,
        run_id="baseline-run-001",
        visual_lane_mode="baseline",
        target_id=source_target_id,
        sciencebase_basename=manifest_entry["basename"],
    )
    candidate_a_binding = _copy_runtime_binding(
        tmp_path,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
        target_id=source_target_id,
        sciencebase_basename=manifest_entry["basename"],
    )
    checkout_root, bundle_id = _write_candidate_b_bundle(
        tmp_path,
        fixture_id=manifest_entry["fixture_id"],
        sciencebase_basename=manifest_entry["basename"],
    )
    selector = NrcApsReviewRunSelectorOut(
        default_run_id=baseline_binding.run_id,
        runs=[
            NrcApsReviewRunSelectorItemOut(
                run_id=baseline_binding.run_id,
                display_label="Baseline Run",
                status="completed",
                submitted_at="2026-04-13T22:50:00Z",
                completed_at="2026-04-13T23:00:00Z",
                reviewable=True,
            ),
            NrcApsReviewRunSelectorItemOut(
                run_id=candidate_a_binding.run_id,
                display_label="Candidate A Run",
                status="completed",
                submitted_at="2026-04-13T22:55:00Z",
                completed_at="2026-04-13T23:05:00Z",
                reviewable=True,
            ),
        ],
    )
    return ReviewBrowserFixture(
        baseline_binding=baseline_binding,
        candidate_a_binding=candidate_a_binding,
        checkout_root=checkout_root,
        bundle_id=bundle_id,
        fixture_id=manifest_entry["fixture_id"],
        selector=selector,
    )


def install_review_browser_patches(fixture: ReviewBrowserFixture) -> None:
    runtime_service._load_binding_request_config_json.cache_clear()
    runtime_service.discover_review_roots = lambda: [
        fixture.baseline_binding.review_root,
        fixture.candidate_a_binding.review_root,
    ]

    compare_service.discover_runtime_bindings = lambda: [
        fixture.baseline_binding,
        fixture.candidate_a_binding,
    ]
    compare_service.discover_candidate_runs = lambda: fixture.selector

    review_api.discover_candidate_runs = lambda: fixture.selector
    review_api.discover_workbench_compare_sources = lambda: compare_service.discover_workbench_compare_sources(
        checkout_root=fixture.checkout_root,
    )
    review_api.compose_workbench_compare_targets = (
        lambda *, baseline_run_id, candidate_a_run_id, candidate_b_bundle_id: compare_service.compose_workbench_compare_targets(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_bundle_id=candidate_b_bundle_id,
            checkout_root=fixture.checkout_root,
        )
    )
    review_api.compose_workbench_compare_manifest = (
        lambda *, baseline_run_id, candidate_a_run_id, candidate_b_bundle_id, fixture_id: compare_service.compose_workbench_compare_manifest(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=fixture.checkout_root,
        )
    )
    review_api.compose_workbench_compare_tab = (
        lambda *, baseline_run_id, candidate_a_run_id, candidate_b_bundle_id, fixture_id, tab_id: compare_service.compose_workbench_compare_tab(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            tab_id=tab_id,
            checkout_root=fixture.checkout_root,
        )
    )
    review_api.compose_candidate_b_trace_manifest = (
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.compose_candidate_b_trace_manifest(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=fixture.checkout_root,
        )
    )
    review_api.resolve_candidate_b_trace_annotated_pdf_info = (
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.resolve_candidate_b_trace_annotated_pdf_info(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=fixture.checkout_root,
        )
    )
    review_api.load_candidate_b_trace_raw_json = (
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.load_candidate_b_trace_raw_json(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=fixture.checkout_root,
        )
    )
    review_api.load_candidate_b_trace_raw_markdown = (
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.load_candidate_b_trace_raw_markdown(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=fixture.checkout_root,
        )
    )
