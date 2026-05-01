from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.schemas.review_nrc_aps import NrcApsReviewRunSelectorItemOut, NrcApsReviewRunSelectorOut
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding
import app.services.review_nrc_aps_workbench_compare as compare_service
from review_nrc_aps_runtime_fixture import latest_document_trace_ready_runtime, make_session, resolve_target_for_accession


RUNTIME = latest_document_trace_ready_runtime()


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
            text("SELECT connector_run_target_id FROM connector_run_target WHERE connector_run_id = :run_id ORDER BY connector_run_target_id ASC LIMIT 1"),
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
    document_processing_engine: str | None = None,
    target_id: str,
    sciencebase_basename: str,
) -> ReviewRuntimeBinding:
    copied_root = tmp_path / run_id
    shutil.copytree(RUNTIME.runtime_dir, copied_root)

    summary_path = copied_root / "local_corpus_e2e_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["run_id"] = run_id
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    database_path = copied_root / RUNTIME.db_path.name
    request_config = {}
    if visual_lane_mode:
        request_config["visual_lane_mode"] = visual_lane_mode
    if document_processing_engine:
        request_config["document_processing_engine"] = document_processing_engine

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
        storage_dir=None,
    )


def _write_candidate_b_bundle(tmp_path: Path, *, fixture_id: str) -> tuple[Path, str]:
    checkout_root = tmp_path / "checkout"
    manifest_source = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"
    manifest_dest = checkout_root / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "manifest.json"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_source, manifest_dest)

    bundle_root = checkout_root / "archive" / "20260412-cb-proof" / "cb-proof-test"
    bundle_root.mkdir(parents=True, exist_ok=True)

    (bundle_root / "baseline-summary.json").write_text(
        json.dumps({"documents": [{"fixture_id": fixture_id, "baseline": {"char_count": 1200}}]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (bundle_root / "compare.json").write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-04-12T08:00:00Z",
                "run_id": "cb-run-001",
                "decision_recommendation": "workbench_useful_with_explicit_footer_limitation",
                "interference_check_passed": True,
                "derived_comparison_only": ["candidate_b_normalized_text"],
                "non_equivalent_repo_fields": ["element_counts_by_type"],
                "documents": [
                    {
                        "fixture_id": fixture_id,
                        "document_ref": "doc-ref-001",
                        "document_sha256": "sha256-fixture-001",
                        "baseline": {"char_count": 1200},
                        "candidate_b": {
                            "candidate_b_normalized_char_count": 1188,
                            "candidate_b_normalized_text": "Candidate B text body",
                            "odl_page_count": 4,
                            "heading_count": 2,
                            "list_count": 1,
                            "image_count": 0,
                            "table_count": 0,
                            "hidden_text_present": False,
                            "hidden_text_node_count": 0,
                            "struct_tree_state": "struct_tree_absent",
                            "element_counts_by_type": {"Text": 14, "Title": 2},
                            "page_summaries": [{"page_number": 1, "element_count": 5}],
                            "footer_page_numbers": [4],
                            "image_sources": [],
                            "limitation_flags": ["footer_page_numbers_detected"],
                            "warning_flags": ["footer_warning"],
                        },
                        "expected_gain_claims": ["heading_count"],
                        "expected_non_equivalences": ["element_counts_by_type"],
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
                    "header_footer_emitted_despite_config": [],
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
        json.dumps({"outputs_outside_approved_roots": []}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    bundle_id = Path("archive") / "20260412-cb-proof" / "cb-proof-test"
    return checkout_root, bundle_id.as_posix()


@pytest.fixture()
def compare_runtime_fixture(tmp_path: Path) -> dict[str, object]:
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
    checkout_root, bundle_id = _write_candidate_b_bundle(tmp_path, fixture_id=manifest_entry["fixture_id"])
    selector = NrcApsReviewRunSelectorOut(
        default_run_id=baseline_binding.run_id,
        runs=[
            NrcApsReviewRunSelectorItemOut(
                run_id=baseline_binding.run_id,
                display_label="Baseline Run",
                status="completed",
                submitted_at="2026-04-12T07:50:00Z",
                completed_at="2026-04-12T08:00:00Z",
                reviewable=True,
            ),
            NrcApsReviewRunSelectorItemOut(
                run_id=candidate_a_binding.run_id,
                display_label="Candidate A Run",
                status="completed",
                submitted_at="2026-04-12T07:55:00Z",
                completed_at="2026-04-12T08:05:00Z",
                reviewable=True,
            ),
        ],
    )
    return {
        "baseline_binding": baseline_binding,
        "candidate_a_binding": candidate_a_binding,
        "checkout_root": checkout_root,
        "bundle_id": bundle_id,
        "fixture_id": manifest_entry["fixture_id"],
        "selector": selector,
    }


def test_discover_workbench_compare_sources_returns_visible_runs_and_local_bundle(compare_runtime_fixture: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> None:
    baseline_binding = compare_runtime_fixture["baseline_binding"]
    candidate_a_binding = compare_runtime_fixture["candidate_a_binding"]
    checkout_root = compare_runtime_fixture["checkout_root"]
    selector = compare_runtime_fixture["selector"]

    monkeypatch.setattr(compare_service, "discover_runtime_bindings", lambda: [baseline_binding, candidate_a_binding])
    monkeypatch.setattr(compare_service, "discover_candidate_runs", lambda: selector)

    payload = compare_service.discover_workbench_compare_sources(checkout_root=checkout_root)

    assert [item.run_id for item in payload.baseline_runs] == [baseline_binding.run_id]
    assert [item.run_id for item in payload.candidate_a_runs] == [candidate_a_binding.run_id]
    assert payload.candidate_b_bundles[0].bundle_id == compare_runtime_fixture["bundle_id"]
    assert "\\" not in payload.candidate_b_bundles[0].bundle_id
    assert payload.baseline_runs[0].runtime_binding is not None
    assert payload.baseline_runs[0].runtime_binding.runtime_label == baseline_binding.review_root.name
    assert payload.baseline_runs[0].runtime_binding.database_label == baseline_binding.database_path.name
    expected_storage_label = baseline_binding.storage_dir.name if baseline_binding.storage_dir is not None else None
    assert payload.baseline_runs[0].runtime_binding.storage_label == expected_storage_label


def test_discover_workbench_compare_sources_omits_admitted_candidate_b_runtime(compare_runtime_fixture: dict[str, object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_entry = _load_unique_manifest_entry()
    baseline_binding = compare_runtime_fixture["baseline_binding"]
    candidate_a_binding = compare_runtime_fixture["candidate_a_binding"]
    checkout_root = compare_runtime_fixture["checkout_root"]
    candidate_b_runtime = _copy_runtime_binding(
        tmp_path,
        run_id="candidate-b-runtime-001",
        visual_lane_mode="baseline",
        document_processing_engine="candidate_b_opendataloader_pdf",
        target_id=_source_target_id(),
        sciencebase_basename=manifest_entry["basename"],
    )
    selector = NrcApsReviewRunSelectorOut(
        default_run_id=baseline_binding.run_id,
        runs=[
            *compare_runtime_fixture["selector"].runs,
            NrcApsReviewRunSelectorItemOut(
                run_id=candidate_b_runtime.run_id,
                display_label="Candidate B Runtime",
                status="completed",
                submitted_at="2026-04-12T08:10:00Z",
                completed_at="2026-04-12T08:15:00Z",
                reviewable=True,
            ),
        ],
    )

    monkeypatch.setattr(
        compare_service,
        "discover_runtime_bindings",
        lambda: [baseline_binding, candidate_a_binding, candidate_b_runtime],
    )
    monkeypatch.setattr(compare_service, "discover_candidate_runs", lambda: selector)

    payload = compare_service.discover_workbench_compare_sources(checkout_root=checkout_root)

    assert [item.run_id for item in payload.baseline_runs] == [baseline_binding.run_id]
    assert [item.run_id for item in payload.candidate_a_runs] == [candidate_a_binding.run_id]
    assert candidate_b_runtime.run_id not in {item.run_id for item in payload.baseline_runs}
    assert candidate_b_runtime.run_id not in {item.run_id for item in payload.candidate_a_runs}


def test_compose_workbench_compare_payloads_align_selected_fixture(compare_runtime_fixture: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> None:
    baseline_binding = compare_runtime_fixture["baseline_binding"]
    candidate_a_binding = compare_runtime_fixture["candidate_a_binding"]
    checkout_root = compare_runtime_fixture["checkout_root"]
    bundle_id = compare_runtime_fixture["bundle_id"]
    fixture_id = compare_runtime_fixture["fixture_id"]
    selector = compare_runtime_fixture["selector"]

    monkeypatch.setattr(compare_service, "discover_runtime_bindings", lambda: [baseline_binding, candidate_a_binding])
    monkeypatch.setattr(compare_service, "discover_candidate_runs", lambda: selector)

    targets = compare_service.compose_workbench_compare_targets(
        baseline_run_id=baseline_binding.run_id,
        candidate_a_run_id=candidate_a_binding.run_id,
        candidate_b_bundle_id=bundle_id,
        checkout_root=checkout_root,
    )
    assert targets.default_fixture_id == fixture_id
    assert targets.targets[0].fixture_id == fixture_id

    manifest = compare_service.compose_workbench_compare_manifest(
        baseline_run_id=baseline_binding.run_id,
        candidate_a_run_id=candidate_a_binding.run_id,
        candidate_b_bundle_id=bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )
    assert manifest.source_identity.fixture_id == fixture_id
    assert manifest.variant_bindings.candidate_b.bundle_id == bundle_id
    assert f"run_id={baseline_binding.run_id}" in (manifest.deep_links.baseline_trace or "")
    assert (manifest.deep_links.candidate_b_trace or "").startswith("/review/nrc-aps/candidate-b-trace?")
    assert f"fixture_id={fixture_id}" in (manifest.deep_links.candidate_b_trace or "")

    summary_tab = compare_service.compose_workbench_compare_tab(
        baseline_run_id=baseline_binding.run_id,
        candidate_a_run_id=candidate_a_binding.run_id,
        candidate_b_bundle_id=bundle_id,
        fixture_id=fixture_id,
        tab_id="summary",
        checkout_root=checkout_root,
    )
    assert summary_tab.columns["baseline"].available is True
    assert summary_tab.columns["candidate_a"].available is True
    assert summary_tab.columns["candidate_b"].comparability_class == "direct"
    assert (summary_tab.columns["candidate_b"].deep_link or "").startswith("/review/nrc-aps/candidate-b-trace?")

    text_tab = compare_service.compose_workbench_compare_tab(
        baseline_run_id=baseline_binding.run_id,
        candidate_a_run_id=candidate_a_binding.run_id,
        candidate_b_bundle_id=bundle_id,
        fixture_id=fixture_id,
        tab_id="normalized_text",
        checkout_root=checkout_root,
    )
    assert text_tab.columns["candidate_b"].comparability_class == "derived_only"
    assert text_tab.columns["candidate_b"].data["text"] == "Candidate B text body"


def test_compose_workbench_compare_manifest_accepts_dict_shaped_proof_warnings(
    compare_runtime_fixture: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline_binding = compare_runtime_fixture["baseline_binding"]
    candidate_a_binding = compare_runtime_fixture["candidate_a_binding"]
    checkout_root = compare_runtime_fixture["checkout_root"]
    bundle_id = compare_runtime_fixture["bundle_id"]
    fixture_id = compare_runtime_fixture["fixture_id"]
    selector = compare_runtime_fixture["selector"]

    proof_path = checkout_root / "archive" / "20260412-cb-proof" / "cb-proof-test" / "proof.json"
    proof_payload = json.loads(proof_path.read_text(encoding="utf-8"))
    proof_payload["warnings"] = {
        "header_footer_emitted_despite_config": [fixture_id],
        "image_source_collisions": [],
        "labels_sidecar_manifest_hash_status": {"status": "matched"},
    }
    proof_path.write_text(json.dumps(proof_payload, indent=2, sort_keys=True), encoding="utf-8")

    monkeypatch.setattr(compare_service, "discover_runtime_bindings", lambda: [baseline_binding, candidate_a_binding])
    monkeypatch.setattr(compare_service, "discover_candidate_runs", lambda: selector)

    manifest = compare_service.compose_workbench_compare_manifest(
        baseline_run_id=baseline_binding.run_id,
        candidate_a_run_id=candidate_a_binding.run_id,
        candidate_b_bundle_id=bundle_id,
        fixture_id=fixture_id,
        checkout_root=checkout_root,
    )

    assert "footer_warning" in manifest.warnings
    assert "header_footer_emitted_despite_config" in manifest.warnings
    assert "labels_sidecar_manifest_hash_status" not in manifest.warnings


def test_candidate_b_bundle_id_validation_fails_closed(compare_runtime_fixture: dict[str, object]) -> None:
    checkout_root = compare_runtime_fixture["checkout_root"]
    bundle_id = compare_runtime_fixture["bundle_id"]

    resolved = compare_service.resolve_candidate_b_bundle_root(bundle_id, checkout_root=checkout_root)
    assert resolved.name == "cb-proof-test"

    with pytest.raises(ValueError, match="candidate_b_bundle_id_invalid"):
        compare_service.resolve_candidate_b_bundle_root("../archive/20260412-cb-proof/cb-proof-test", checkout_root=checkout_root)

    with pytest.raises(ValueError, match="candidate_b_bundle_unavailable"):
        compare_service.resolve_candidate_b_bundle_root("archive/20260412-cb-proof/not-real", checkout_root=checkout_root)


def test_compose_workbench_compare_targets_rejects_non_reviewable_run(compare_runtime_fixture: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> None:
    baseline_binding = compare_runtime_fixture["baseline_binding"]
    candidate_a_binding = compare_runtime_fixture["candidate_a_binding"]
    checkout_root = compare_runtime_fixture["checkout_root"]
    bundle_id = compare_runtime_fixture["bundle_id"]

    selector = compare_runtime_fixture["selector"].model_copy(deep=True)
    selector.runs[0].reviewable = False

    monkeypatch.setattr(compare_service, "discover_runtime_bindings", lambda: [baseline_binding, candidate_a_binding])
    monkeypatch.setattr(compare_service, "discover_candidate_runs", lambda: selector)

    with pytest.raises(ValueError, match="invalid_baseline_run"):
        compare_service.compose_workbench_compare_targets(
            baseline_run_id=baseline_binding.run_id,
            candidate_a_run_id=candidate_a_binding.run_id,
            candidate_b_bundle_id=bundle_id,
            checkout_root=checkout_root,
        )
