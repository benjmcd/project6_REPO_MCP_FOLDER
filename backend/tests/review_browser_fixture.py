from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.api.review_nrc_aps as review_api
from app.db.session import Base
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget
import app.services.review_nrc_aps_candidate_b_trace as trace_service
import app.services.review_nrc_aps_runtime as runtime_service
import app.services.review_nrc_aps_workbench_compare as compare_service
from app.schemas.review_nrc_aps import NrcApsReviewRunSelectorItemOut, NrcApsReviewRunSelectorOut
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding


FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrc_aps_docs" / "v1"
SUMMARY_SCHEMA_ID = "aps.local_corpus_e2e_summary.v1"
SUMMARY_SCHEMA_VERSION = 1
SOURCE_FIXTURE_ID = "fontish"
APS_CONTENT_CONTRACT_ID = "aps_content_units_v2"
APS_CHUNKING_CONTRACT_ID = "aps_chunking_v2"
APS_NORMALIZATION_CONTRACT_ID = "aps_text_normalization_v2"
APS_CONTENT_STATUS_INDEXED = "indexed"


@dataclass(frozen=True)
class _BrowserCorpusFixture:
    fixture_id: str
    basename: str
    source_path: Path


@dataclass(frozen=True)
class ReviewBrowserFixture:
    baseline_binding: ReviewRuntimeBinding
    candidate_a_binding: ReviewRuntimeBinding
    checkout_root: Path
    bundle_id: str
    fixture_id: str
    selector: NrcApsReviewRunSelectorOut


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(payload: str) -> str:
    return _sha256_bytes(payload.encode("utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_browser_corpus_fixture() -> _BrowserCorpusFixture:
    manifest_path = FIXTURES_ROOT / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") or []
    if not isinstance(entries, list):
        raise AssertionError("Expected corpus manifest entries list")

    selected: dict[str, str] | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("fixture_id") or "").strip() != SOURCE_FIXTURE_ID:
            continue
        basename = Path(str(entry.get("path") or "")).name.strip()
        if not basename:
            continue
        selected = {
            "fixture_id": SOURCE_FIXTURE_ID,
            "basename": basename,
        }
        break

    if selected is None:
        raise AssertionError(f"Expected corpus manifest fixture {SOURCE_FIXTURE_ID}")

    source_path = FIXTURES_ROOT / selected["basename"]
    if not source_path.is_file():
        raise AssertionError(f"Expected corpus source fixture on disk: {source_path}")

    return _BrowserCorpusFixture(
        fixture_id=selected["fixture_id"],
        basename=selected["basename"],
        source_path=source_path,
    )


def _runtime_summary(
    *,
    run_id: str,
    submitted_at: str,
    completed_at: str,
) -> dict[str, object]:
    return {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "run_id": run_id,
        "passed": True,
        "generated_at_utc": completed_at,
        "database_path": "lc.db",
        "database_url": "sqlite:///lc.db",
        "storage_dir": "storage",
        "submission": {
            "submitted_at": submitted_at,
        },
        "run_detail": {
            "status": "completed",
            "completed_at": completed_at,
            "selected_count": 1,
            "downloaded_count": 1,
            "failed_count": 0,
            "report_refs": {
                "aps_artifact_ingestion": "reports/aps_artifact_ingestion.json",
                "aps_content_index": "reports/aps_content_index.json",
            },
        },
    }


def _seed_runtime_binding(
    tmp_path: Path,
    *,
    run_id: str,
    visual_lane_mode: str,
    accession_number: str,
    submitted_at: str,
    completed_at: str,
    corpus_fixture: _BrowserCorpusFixture,
) -> ReviewRuntimeBinding:
    runtime_root = tmp_path / run_id
    runtime_root.mkdir(parents=True, exist_ok=True)

    storage_dir = runtime_root / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    source_pdf_path = runtime_root / corpus_fixture.basename
    shutil.copy2(corpus_fixture.source_path, source_pdf_path)
    normalized_text = f"Normalized text for {corpus_fixture.fixture_id} in {run_id}.\n"

    (runtime_root / "normalized.txt").write_text(normalized_text, encoding="utf-8")
    _write_json(
        runtime_root / "diagnostics-linkage.json",
        {
            "extractor_metadata": {
                "fixture_id": corpus_fixture.fixture_id,
                "run_id": run_id,
            },
            "warnings": [],
            "degradation_codes": [],
            "ordered_units": [
                {
                    "page_number": 1,
                    "unit_kind": "pdf_paragraph",
                    "text": normalized_text.strip(),
                    "start_char": 0,
                    "end_char": len(normalized_text.strip()),
                    "bbox": [72.0, 72.0, 240.0, 96.0],
                }
            ],
        },
    )
    _write_json(
        runtime_root / "diagnostics-document.json",
        {
            "page_count": 1,
            "quality_status": "strong",
        },
    )
    _write_json(runtime_root / "download.json", {"run_id": run_id})
    _write_json(runtime_root / "discovery.json", {"fixture_id": corpus_fixture.fixture_id})
    _write_json(runtime_root / "selection.json", {"fixture_id": corpus_fixture.fixture_id})
    _write_json(runtime_root / "reports" / "aps_artifact_ingestion.json", {"status": "completed"})
    _write_json(runtime_root / "reports" / "aps_content_index.json", {"status": "completed"})

    summary = _runtime_summary(
        run_id=run_id,
        submitted_at=submitted_at,
        completed_at=completed_at,
    )
    _write_json(runtime_root / "local_corpus_e2e_summary.json", summary)

    database_path = runtime_root / "lc.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    source_pdf_bytes = source_pdf_path.read_bytes()
    normalized_sha256 = _sha256_text(normalized_text)
    blob_sha256 = _sha256_bytes(source_pdf_bytes)
    content_id = f"{run_id}-content-001"
    target_id = f"{run_id}-target-001"
    request_config = {"visual_lane_mode": visual_lane_mode}
    timestamp = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).astimezone(timezone.utc)

    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        session.add(
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system="nrc_adams",
                source_mode="aps",
                status="completed",
                request_config_json=request_config,
                submitted_at=datetime.fromisoformat(submitted_at.replace("Z", "+00:00")).astimezone(timezone.utc),
                completed_at=timestamp,
            )
        )
        session.flush()

        session.add(
            ConnectorRunTarget(
                connector_run_target_id=target_id,
                connector_run_id=run_id,
                artifact_surface="documents",
                ordinal=0,
                sciencebase_file_name=corpus_fixture.basename,
                status="completed",
                public_read_confirmed=True,
                source_reference_json={
                    "aps_normalized": {
                        "document_title": f"Browser Fixture {corpus_fixture.fixture_id}",
                        "document_type": "layout_complex_pdf",
                    }
                },
            )
        )
        session.add(
            ApsContentDocument(
                content_id=content_id,
                content_contract_id=APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
                normalization_contract_id=APS_NORMALIZATION_CONTRACT_ID,
                normalized_text_sha256=normalized_sha256,
                normalized_char_count=len(normalized_text),
                chunk_count=1,
                content_status=APS_CONTENT_STATUS_INDEXED,
                media_type="application/pdf",
                document_class="layout_complex_pdf",
                quality_status="strong",
                page_count=1,
                diagnostics_ref="diagnostics-document.json",
                visual_page_refs_json="[]",
                updated_at=timestamp,
            )
        )
        session.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=f"{run_id}-chunk-001",
                content_contract_id=APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=len(normalized_text.strip()),
                chunk_text=normalized_text.strip(),
                chunk_text_sha256=_sha256_text(normalized_text.strip()),
                page_start=1,
                page_end=1,
                unit_kind="pdf_paragraph",
                quality_status="strong",
                updated_at=timestamp,
            )
        )
        session.add(
            ApsContentLinkage(
                content_id=content_id,
                run_id=run_id,
                target_id=target_id,
                accession_number=accession_number,
                content_contract_id=APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
                normalized_text_ref="normalized.txt",
                normalized_text_sha256=normalized_sha256,
                blob_ref=corpus_fixture.basename,
                blob_sha256=blob_sha256,
                download_exchange_ref="download.json",
                discovery_ref="discovery.json",
                selection_ref="selection.json",
                diagnostics_ref="diagnostics-linkage.json",
            )
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    return ReviewRuntimeBinding(
        run_id=run_id,
        review_root=runtime_root,
        summary=summary,
        database_path=database_path,
        storage_dir=storage_dir,
    )


def _write_candidate_b_bundle(
    tmp_path: Path,
    *,
    corpus_fixture: _BrowserCorpusFixture,
) -> tuple[Path, str]:
    checkout_root = tmp_path / "checkout"
    manifest_source = FIXTURES_ROOT / "manifest.json"
    manifest_dest = checkout_root / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_source, manifest_dest)

    bundle_rel = Path("tests") / "reports" / "cb-compare-browser-test"
    bundle_root = checkout_root / bundle_rel
    raw_root = bundle_root / "raw"
    annotated_path = raw_root / "annotated" / f"{corpus_fixture.fixture_id}.pdf"
    raw_json_path = raw_root / f"{corpus_fixture.fixture_id}.json"
    raw_markdown_path = raw_root / f"{corpus_fixture.fixture_id}.md"
    raw_root.mkdir(parents=True, exist_ok=True)

    annotated_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(corpus_fixture.source_path, annotated_path)
    raw_json_path.write_text(
        json.dumps({"fixture_id": corpus_fixture.fixture_id, "kind": "candidate_b"}, indent=2),
        encoding="utf-8",
    )
    raw_markdown_path.write_text(f"# Candidate B\n\nFixture: {corpus_fixture.fixture_id}\n", encoding="utf-8")

    annotated_ref = (bundle_rel / "raw" / "annotated" / f"{corpus_fixture.fixture_id}.pdf").as_posix()
    raw_json_ref = (bundle_rel / "raw" / f"{corpus_fixture.fixture_id}.json").as_posix()
    raw_markdown_ref = (bundle_rel / "raw" / f"{corpus_fixture.fixture_id}.md").as_posix()
    raw_output_root = (bundle_rel / "raw").as_posix()

    _write_json(
        bundle_root / "baseline-summary.json",
        {"documents": [{"fixture_id": corpus_fixture.fixture_id, "baseline": {"char_count": 1200}}]},
    )
    _write_json(
        bundle_root / "compare.json",
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
                    "fixture_id": corpus_fixture.fixture_id,
                    "document_ref": "doc-ref-browser-001",
                    "document_sha256": "sha256-browser-001",
                    "baseline": {"char_count": 1200},
                    "expected_gain_claims": ["heading_count"],
                    "expected_non_equivalences": ["element_counts_by_type"],
                    "regime_labels": ["browser_regression"],
                    "review_notes": "Browser regression fixture.",
                    "candidate_b": {
                        "file_name": corpus_fixture.basename,
                        "processing_status": "succeeded",
                        "candidate_b_normalized_char_count": 1188,
                        "candidate_b_normalized_text": "Candidate B normalized text body",
                        "odl_page_count": 1,
                        "heading_count": 2,
                        "list_count": 1,
                        "image_count": 0,
                        "table_count": 1,
                        "hidden_text_present": False,
                        "hidden_text_node_count": 0,
                        "struct_tree_state": "struct_tree_absent",
                        "element_counts_by_type": {"Text": 14, "Title": 2},
                        "page_summaries": [{"page_number": 1, "element_count": 5}],
                        "footer_page_numbers": [1],
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
    )
    _write_json(
        bundle_root / "proof.json",
        {
            "warnings": {
                "header_footer_emitted_despite_config": [corpus_fixture.fixture_id],
                "image_source_collisions": [],
                "labels_sidecar_manifest_hash_status": {"status": "matched"},
            },
            "interference_check_passed": True,
        },
    )
    _write_json(
        bundle_root / "retain.json",
        {
            "raw_file_inventory": [
                {"path": annotated_ref, "category": "candidate_b_annotated_pdf"},
                {"path": raw_json_ref, "category": "candidate_b_raw_json"},
                {"path": raw_markdown_ref, "category": "candidate_b_raw_markdown"},
            ],
            "outputs_outside_approved_roots": [],
        },
    )

    return checkout_root, bundle_rel.as_posix()


def build_review_browser_fixture(tmp_path: Path) -> ReviewBrowserFixture:
    corpus_fixture = _load_browser_corpus_fixture()
    baseline_binding = _seed_runtime_binding(
        tmp_path,
        run_id="baseline-run-001",
        visual_lane_mode="baseline",
        accession_number="ML-BROWSER-001",
        submitted_at="2026-04-13T22:50:00Z",
        completed_at="2026-04-13T23:00:00Z",
        corpus_fixture=corpus_fixture,
    )
    candidate_a_binding = _seed_runtime_binding(
        tmp_path,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
        accession_number="ML-BROWSER-002",
        submitted_at="2026-04-13T22:55:00Z",
        completed_at="2026-04-13T23:05:00Z",
        corpus_fixture=corpus_fixture,
    )
    checkout_root, bundle_id = _write_candidate_b_bundle(
        tmp_path,
        corpus_fixture=corpus_fixture,
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
        fixture_id=corpus_fixture.fixture_id,
        selector=selector,
    )


def capture_review_browser_patch_state() -> dict[str, object]:
    return {
        "runtime_discover_runtime_bindings": runtime_service.discover_runtime_bindings,
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
    runtime_service.discover_runtime_bindings = patch_state["runtime_discover_runtime_bindings"]
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


def install_review_browser_patches(fixture: ReviewBrowserFixture) -> None:
    runtime_service._load_binding_request_config_json.cache_clear()
    bindings = [fixture.baseline_binding, fixture.candidate_a_binding]
    runtime_service.discover_runtime_bindings = lambda: list(bindings)
    compare_service.discover_runtime_bindings = lambda: list(bindings)
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
