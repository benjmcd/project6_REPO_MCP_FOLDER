from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


os.environ["DB_INIT_MODE"] = "none"
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.review_nrc_aps import (  # noqa: E402
    NrcApsCandidateBTraceArtifactEndpointsOut,
    NrcApsCandidateBTraceIdentityOut,
    NrcApsCandidateBTraceManifestOut,
    NrcApsCandidateBTraceSummaryOut,
    NrcApsCandidateBTraceTabDefOut,
)
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding  # noqa: E402
from tools import validate_wb_prep  # noqa: E402


def _seed_summary(*, visual_lane_mode: str, document_processing_engine: str = "baseline") -> dict[str, object]:
    return {
        "seed_kind": "workbench_compare_fixture_seed",
        "visual_lane_mode": visual_lane_mode,
        "document_processing_engine": document_processing_engine,
        "corpus_fixture_ids": list(validate_wb_prep.FROZEN_FIXTURE_IDS),
        "corpus_pdf_count": len(validate_wb_prep.FROZEN_FIXTURE_IDS),
    }


def _make_binding(
    checkout_root: Path,
    *,
    run_id: str,
    visual_lane_mode: str,
    document_processing_engine: str = "baseline",
    donor: bool = False,
) -> ReviewRuntimeBinding:
    base_root = checkout_root.parent / "donor-runtime" if donor else checkout_root / "backend" / "app" / "storage_test_runtime" / "lc_e2e"
    review_root = base_root / run_id
    review_root.mkdir(parents=True, exist_ok=True)
    database_path = review_root / "lc.db"
    storage_dir = review_root / "storage"
    database_path.write_text("db", encoding="utf-8")
    storage_dir.mkdir(parents=True, exist_ok=True)
    return ReviewRuntimeBinding(
        run_id=run_id,
        review_root=review_root,
        summary=_seed_summary(
            visual_lane_mode=visual_lane_mode,
            document_processing_engine=document_processing_engine,
        ),
        database_path=database_path,
        storage_dir=storage_dir,
    )


def _trace_manifest(*, bundle_id: str, fixture_id: str, annotated: bool = True) -> NrcApsCandidateBTraceManifestOut:
    return NrcApsCandidateBTraceManifestOut(
        candidate_b_bundle_id=bundle_id,
        fixture_id=fixture_id,
        identity=NrcApsCandidateBTraceIdentityOut(
            fixture_id=fixture_id,
            bundle_id=bundle_id,
            candidate_b_run_id="cb-run-001",
            document_title=f"Fixture {fixture_id}",
            source_file_name=f"{fixture_id}.pdf",
            document_ref=f"doc-ref-{fixture_id}",
            document_sha256=f"sha256-{fixture_id}",
        ),
        summary=NrcApsCandidateBTraceSummaryOut(
            processing_status="succeeded",
            decision_recommendation="useful",
            page_count=1,
            normalized_char_count=1200,
            struct_tree_state="struct_tree_absent",
            annotated_pdf_status="present" if annotated else "missing",
        ),
        tabs=[
            NrcApsCandidateBTraceTabDefOut(tab_id="annotated_pdf", label="Annotated PDF", available=annotated),
            NrcApsCandidateBTraceTabDefOut(tab_id="summary", label="Summary", available=True),
            NrcApsCandidateBTraceTabDefOut(tab_id="raw_json", label="Raw JSON", available=True),
            NrcApsCandidateBTraceTabDefOut(tab_id="raw_markdown", label="Raw Markdown", available=True),
        ],
        default_tab="annotated_pdf" if annotated else "summary",
        warnings=[],
        limitations=[],
        artifacts=NrcApsCandidateBTraceArtifactEndpointsOut(
            annotated_pdf=f"/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?candidate_b_bundle_id={bundle_id}&fixture_id={fixture_id}"
            if annotated
            else None,
            raw_json=f"/api/v1/review/nrc-aps/candidate-b-trace/raw-json?candidate_b_bundle_id={bundle_id}&fixture_id={fixture_id}",
            raw_markdown=f"/api/v1/review/nrc-aps/candidate-b-trace/raw-markdown?candidate_b_bundle_id={bundle_id}&fixture_id={fixture_id}",
        ),
    )


def _runtime_targets_map(*fixture_ids: str) -> dict[str, SimpleNamespace]:
    return {
        fixture_id: SimpleNamespace(target_id=f"target-{fixture_id}")
        for fixture_id in fixture_ids
    }


def test_discover_runtime_bindings_for_checkout_reads_target_checkout_roots(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    review_root = checkout_root / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "baseline-run-001"
    review_root.mkdir(parents=True, exist_ok=True)
    (review_root / "lc.db").write_text("not-a-real-db", encoding="utf-8")
    (review_root / "storage").mkdir(parents=True, exist_ok=True)
    (review_root / "local_corpus_e2e_summary.json").write_text(
        json.dumps(
            {
                "schema_id": "aps.local_corpus_e2e_summary.v1",
                "schema_version": 1,
                "run_id": "baseline-run-001",
                "database_path": str((review_root / "lc.db").resolve()),
                "storage_dir": str((review_root / "storage").resolve()),
                "generated_at_utc": "2026-04-13T23:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    bindings = validate_wb_prep._discover_runtime_bindings_for_checkout(checkout_root)

    assert len(bindings) == 1
    assert bindings[0].run_id == "baseline-run-001"
    assert bindings[0].review_root == review_root.resolve()


def test_validate_wb_prep_returns_canonical_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_candidate_b_bundle_sources",
        lambda checkout_root: [
            {
                "bundle_id": "tests/reports/cb-compare-test",
                "display_label": "cb-compare-test | useful",
                "generated_at_utc": "2026-04-13T23:10:00Z",
                "decision_recommendation": "useful",
            }
        ],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_manifest_entries_by_basename",
        lambda checkout_root: {},
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_runtime_targets",
        lambda binding, manifest_by_basename: _runtime_targets_map("fontish", "ml17123a319", "layout"),
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_bundle_artifacts",
        lambda bundle_id, checkout_root: SimpleNamespace(compare={"generated_at_utc": "2026-04-13T23:10:00Z"}),
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_bundle_documents_by_fixture",
        lambda compare_payload: {
            "fontish": {"fixture_id": "fontish"},
            "ml17123a319": {"fixture_id": "ml17123a319"},
            "layout": {"fixture_id": "layout"},
        },
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "compose_candidate_b_trace_manifest",
        lambda **kwargs: _trace_manifest(
            bundle_id=kwargs["candidate_b_bundle_id"],
            fixture_id=kwargs["fixture_id"],
            annotated=True,
        ),
    )

    exit_code = validate_wb_prep.main(["--checkout-root", str(checkout_root)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["checkout_root"] == str(checkout_root.resolve())
    assert payload["selection"]["baseline_run_id"] == "baseline-run-001"
    assert payload["selection"]["candidate_a_run_id"] == "candidate-a-run-001"
    assert payload["selection"]["candidate_b_source_kind"] == "bundle"
    assert payload["selection"]["candidate_b_bundle_id"] == "tests/reports/cb-compare-test"
    assert payload["selection"]["follow_through_fixture_id"] == "fontish"
    assert payload["required_follow_through_fixture_ids_present"] == ["fontish", "ml17123a319"]
    assert payload["candidate_b_trace"]["default_tab"] == "annotated_pdf"
    assert payload["recommended_urls"]["workbench_compare"].startswith("/review/nrc-aps/workbench-compare?")


def test_validate_wb_prep_accepts_candidate_b_runtime_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )
    candidate_b_binding = _make_binding(
        checkout_root,
        run_id="candidate-b-runtime-001",
        visual_lane_mode="baseline",
        document_processing_engine="candidate_b_opendataloader_pdf",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding, candidate_b_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: str(binding.summary.get("document_processing_engine") or "") if binding.run_id.startswith("candidate-b") else (
            "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline"
        ),
    )
    monkeypatch.setattr(validate_wb_prep, "_manifest_entries_by_basename", lambda checkout_root: {})
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_runtime_targets",
        lambda binding, manifest_by_basename: _runtime_targets_map("fontish", "ml17123a319", "layout"),
    )

    exit_code = validate_wb_prep.main(
        [
            "--checkout-root",
            str(checkout_root),
            "--candidate-b-source-kind",
            "runtime",
            "--candidate-b-run-id",
            "candidate-b-runtime-001",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["checkout_root"] == str(checkout_root.resolve())
    assert payload["selection"] == {
        "candidate_b_source_kind": "runtime",
        "baseline_run_id": "baseline-run-001",
        "candidate_a_run_id": "candidate-a-run-001",
        "candidate_b_run_id": "candidate-b-runtime-001",
        "follow_through_fixture_id": "fontish",
    }
    assert payload["review_roots"]["candidate_b_review_root"].startswith("backend/app/storage_test_runtime/")
    assert payload["shared_fixture_ids"] == ["fontish", "layout", "ml17123a319"]
    assert "candidate_b_source_kind=runtime" in payload["recommended_urls"]["workbench_compare"]
    assert "candidate_b_run_id=candidate-b-runtime-001" in payload["recommended_urls"]["workbench_compare"]
    assert payload["recommended_urls"]["candidate_b_runtime_trace"].startswith("/review/nrc-aps/document-trace?")
    assert "candidate_b_trace" not in payload["recommended_urls"]
    assert payload["sources_snapshot"]["candidate_b_runtime_runs"][0]["review_root"].startswith(
        "backend/app/storage_test_runtime/"
    )


def test_validate_wb_prep_runtime_source_requires_explicit_candidate_b_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )
    candidate_b_binding = _make_binding(
        checkout_root,
        run_id="candidate-b-runtime-001",
        visual_lane_mode="baseline",
        document_processing_engine="candidate_b_opendataloader_pdf",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding, candidate_b_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: str(binding.summary.get("document_processing_engine") or "") if binding.run_id.startswith("candidate-b") else (
            "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline"
        ),
    )
    monkeypatch.setattr(validate_wb_prep, "_manifest_entries_by_basename", lambda checkout_root: {})
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_runtime_targets",
        lambda binding, manifest_by_basename: _runtime_targets_map("fontish", "ml17123a319", "layout"),
    )

    exit_code = validate_wb_prep.main(
        [
            "--checkout-root",
            str(checkout_root),
            "--candidate-b-source-kind",
            "runtime",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["error"]["code"] == "candidate_b_run_id_missing"
    assert payload["error"]["context"]["eligible_runs"][0]["run_id"] == "candidate-b-runtime-001"
    assert payload["error"]["context"]["eligible_runs"][0]["review_root"].startswith(
        "backend/app/storage_test_runtime/"
    )


def test_validate_wb_prep_runtime_source_rejects_invalid_candidate_b_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )
    candidate_b_binding = _make_binding(
        checkout_root,
        run_id="candidate-b-runtime-001",
        visual_lane_mode="baseline",
        document_processing_engine="candidate_b_opendataloader_pdf",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding, candidate_b_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: str(binding.summary.get("document_processing_engine") or "") if binding.run_id.startswith("candidate-b") else (
            "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline"
        ),
    )
    monkeypatch.setattr(validate_wb_prep, "_manifest_entries_by_basename", lambda checkout_root: {})
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_runtime_targets",
        lambda binding, manifest_by_basename: _runtime_targets_map("fontish", "ml17123a319", "layout"),
    )

    exit_code = validate_wb_prep.main(
        [
            "--checkout-root",
            str(checkout_root),
            "--candidate-b-source-kind",
            "runtime",
            "--candidate-b-run-id",
            "not-a-runtime-run",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["checkout_root"] == str(checkout_root.resolve())
    assert payload["error"]["code"] == "candidate_b_run_unavailable"
    assert payload["error"]["context"]["requested_run_id"] == "not-a-runtime-run"
    assert payload["error"]["context"]["eligible_runs"][0]["run_id"] == "candidate-b-runtime-001"
    assert payload["error"]["context"]["eligible_runs"][0]["review_root"].startswith(
        "backend/app/storage_test_runtime/"
    )


def test_validate_wb_prep_fails_closed_on_donor_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline", donor=True)
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_candidate_b_bundle_sources",
        lambda checkout_root: [],
    )

    exit_code = validate_wb_prep.main(["--checkout-root", str(checkout_root)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["error"]["code"] == "baseline_run_missing"


def test_validate_wb_prep_fails_closed_on_ambiguous_baseline_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding_a = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    baseline_binding_b = _make_binding(checkout_root, run_id="baseline-run-002", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding_a, baseline_binding_b, candidate_a_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_candidate_b_bundle_sources",
        lambda checkout_root: [],
    )

    exit_code = validate_wb_prep.main(["--checkout-root", str(checkout_root)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["error"]["code"] == "baseline_run_ambiguous"
    assert len(payload["error"]["context"]["eligible_runs"]) == 2


def test_validate_wb_prep_fails_when_required_fixture_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_candidate_b_bundle_sources",
        lambda checkout_root: [
            {
                "bundle_id": "tests/reports/cb-compare-test",
                "display_label": "cb-compare-test | useful",
                "generated_at_utc": "2026-04-13T23:10:00Z",
                "decision_recommendation": "useful",
            }
        ],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_manifest_entries_by_basename",
        lambda checkout_root: {},
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_runtime_targets",
        lambda binding, manifest_by_basename: _runtime_targets_map("fontish", "layout", "mixed"),
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_bundle_artifacts",
        lambda bundle_id, checkout_root: SimpleNamespace(compare={"generated_at_utc": "2026-04-13T23:10:00Z"}),
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_bundle_documents_by_fixture",
        lambda compare_payload: {
            "fontish": {"fixture_id": "fontish"},
            "layout": {"fixture_id": "layout"},
            "mixed": {"fixture_id": "mixed"},
        },
    )

    exit_code = validate_wb_prep.main(["--checkout-root", str(checkout_root)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["error"]["code"] == "shared_fixture_required_missing"


def test_validate_wb_prep_fails_closed_on_invalid_corpus_pdf_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )
    baseline_binding.summary["corpus_pdf_count"] = "not-a-number"

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_candidate_b_bundle_sources",
        lambda checkout_root: [],
    )

    exit_code = validate_wb_prep.main(["--checkout-root", str(checkout_root)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["error"]["code"] == "baseline_run_missing"


def test_validate_wb_prep_fails_closed_on_malformed_candidate_b_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    baseline_binding = _make_binding(checkout_root, run_id="baseline-run-001", visual_lane_mode="baseline")
    candidate_a_binding = _make_binding(
        checkout_root,
        run_id="candidate-a-run-001",
        visual_lane_mode="candidate_a_page_evidence_v1",
    )
    malformed_bundle_root = checkout_root / "tests" / "reports" / "cb-compare-bad"
    malformed_bundle_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        validate_wb_prep,
        "_discover_runtime_bindings_for_checkout",
        lambda checkout_root: [baseline_binding, candidate_a_binding],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "classify_runtime_binding_variant",
        lambda binding: "candidate_a_page_evidence_v1" if binding.run_id.startswith("candidate-a") else "baseline",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "discover_candidate_b_bundle_roots",
        lambda checkout_root: [malformed_bundle_root],
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_canonical_bundle_id",
        lambda bundle_root, checkout_root: "tests/reports/cb-compare-bad",
    )
    monkeypatch.setattr(
        validate_wb_prep,
        "_load_bundle_artifacts",
        lambda bundle_id, checkout_root: (_ for _ in ()).throw(ValueError("bad compare payload")),
    )

    exit_code = validate_wb_prep.main(["--checkout-root", str(checkout_root)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["passed"] is False
    assert payload["error"]["code"] == "candidate_b_bundle_missing"
