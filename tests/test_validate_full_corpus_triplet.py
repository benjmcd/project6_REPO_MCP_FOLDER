from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tools import validate_full_corpus_triplet as triplet


def _write_db(
    path: Path,
    *,
    run_id: str,
    document_processing_engine: str,
    visual_lane_mode: str,
    explicit_engine: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table if not exists connector_run "
            "(connector_run_id text primary key, status text, request_config_json text)"
        )
        connection.execute("delete from connector_run")
        connection.execute(
            "insert into connector_run values (?, ?, ?)",
            (
                run_id,
                "completed",
                json.dumps(
                    {
                        "document_processing_engine": document_processing_engine,
                        "document_processing_engine_explicit": explicit_engine,
                        "visual_lane_mode": visual_lane_mode,
                    }
                ),
            ),
        )


def _target_outcomes() -> list[dict[str, object]]:
    return [
        {
            "target_id": f"target-{ordinal}",
            "ordinal": ordinal,
            "status": "recommended",
            "accession_number": f"LOCALAPS{ordinal:05d}",
            "artifact_ref": f"artifact-{ordinal}",
        }
        for ordinal in range(1, triplet.EXPECTED_CORPUS_PDF_COUNT + 1)
    ]


def _seed_admitted_corpus(checkout_root: Path) -> None:
    corpus_root = checkout_root / triplet.ADMITTED_CORPUS_ROOT_RELATIVE
    corpus_root.mkdir(parents=True, exist_ok=True)
    for ordinal in range(1, triplet.EXPECTED_CORPUS_PDF_COUNT + 1):
        (corpus_root / f"target-{ordinal:05d}.pdf").write_bytes(b"%PDF-1.4\n")


def _gate_results() -> dict[str, dict[str, object]]:
    return {gate_name: {"passed": True} for gate_name in triplet.REQUIRED_GATE_NAMES}


def _metrics(*, document_processing_engine: str) -> dict[str, object]:
    if document_processing_engine == triplet.CANDIDATE_B_ENGINE:
        return {
            "ocr_file_count": 0,
            "table_file_count": 0,
            "candidate_b_extractor_file_count": triplet.EXPECTED_CORPUS_PDF_COUNT,
            "candidate_b_ordered_unit_file_count": 68,
            "candidate_b_ordered_unit_total": 52368,
            "candidate_b_visual_ref_total": 1270,
            "candidate_b_retained_source_pdf_ref_count": 1270,
        }
    return {
        "ocr_file_count": 47,
        "table_file_count": 48,
        "candidate_b_extractor_file_count": 0,
        "candidate_b_ordered_unit_file_count": triplet.EXPECTED_CORPUS_PDF_COUNT,
        "candidate_b_ordered_unit_total": 216022,
        "candidate_b_visual_ref_total": 0,
        "candidate_b_retained_source_pdf_ref_count": 0,
    }


def _write_summary(
    runtime_root: Path,
    *,
    run_id: str,
    document_processing_engine: str,
    visual_lane_mode: str,
    explicit_engine: bool = True,
    target_outcomes: list[dict[str, object]] | None = None,
    generated_at_utc: str = "2026-05-23T01:00:00Z",
) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    database_path = runtime_root / "lc.db"
    _write_db(
        database_path,
        run_id=run_id,
        document_processing_engine=document_processing_engine,
        visual_lane_mode=visual_lane_mode,
        explicit_engine=explicit_engine,
    )
    summary = {
        "schema_id": triplet.LOCAL_CORPUS_SUMMARY_SCHEMA_ID,
        "schema_version": 1,
        "generated_at_utc": generated_at_utc,
        "passed": True,
        "runtime_root": str(runtime_root),
        "database_path": str(database_path),
        "storage_dir": str(runtime_root / "storage"),
        "document_processing_engine": document_processing_engine,
        "visual_lane_mode": visual_lane_mode,
        "run_id": run_id,
        "corpus_pdf_count": triplet.EXPECTED_CORPUS_PDF_COUNT,
        "gate_results": _gate_results(),
        "advanced_metrics": _metrics(document_processing_engine=document_processing_engine),
        "target_outcomes": target_outcomes or _target_outcomes(),
    }
    (runtime_root / "local_corpus_e2e_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )


def _seed_triplet(checkout_root: Path) -> dict[str, Path]:
    _seed_admitted_corpus(checkout_root)
    parent = checkout_root / "backend" / "app" / "storage_test_runtime" / "lc_e2e"
    roots = {
        "baseline": parent / "baseline-full-corpus-v2",
        "candidate_a": parent / "candidate-a-full-corpus-v1",
        "candidate_b": parent / "cb-full-corpus-v1",
    }
    _write_summary(
        roots["baseline"],
        run_id="baseline-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.BASELINE_ENGINE,
    )
    _write_summary(
        roots["candidate_a"],
        run_id="candidate-a-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.CANDIDATE_A_VISUAL_LANE,
    )
    _write_summary(
        roots["candidate_b"],
        run_id="candidate-b-run",
        document_processing_engine=triplet.CANDIDATE_B_ENGINE,
        visual_lane_mode=triplet.CANDIDATE_B_VISUAL_LANE,
    )
    return roots


def _rewrite_summary(runtime_root: Path, **updates: object) -> None:
    summary_path = runtime_root / "local_corpus_e2e_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(updates)
    summary_path.write_text(json.dumps(summary), encoding="utf-8")


def test_validate_triplet_accepts_same_checkout_full_corpus_receipts(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)

    payload = triplet.validate_triplet(
        checkout_root=checkout_root,
        baseline_run_root=roots["baseline"],
        candidate_a_run_root=roots["candidate_a"],
        candidate_b_run_root=roots["candidate_b"],
    )

    assert payload["passed"] is True
    assert payload["validation_mode"] == "candidate_b_full_corpus_compare_triplet_v1"
    assert payload["artifacts_seeded_or_generated"] is False
    assert payload["selected_runs"]["baseline"]["run_id"] == "baseline-run"
    assert payload["selected_runs"]["candidate_a"]["visual_lane_mode"] == triplet.CANDIDATE_A_VISUAL_LANE
    assert payload["selected_runs"]["candidate_b"]["document_processing_engine"] == triplet.CANDIDATE_B_ENGINE
    assert payload["compare_target_set"]["target_count"] == triplet.EXPECTED_CORPUS_PDF_COUNT
    assert (
        payload["compare_target_set"]["target_set_hash"]
        == payload["compare_target_set"]["admitted_target_set_hash"]
    )
    assert (
        payload["compare_target_set"]["admitted_target_set_authority"]
        == triplet.ADMITTED_TARGET_SET_AUTHORITY
    )
    assert payload["target_status_counts"]["candidate_b"] == {"recommended": triplet.EXPECTED_CORPUS_PDF_COUNT}
    assert payload["request_configs"]["baseline"]["document_processing_engine_explicit"] is True
    assert (
        payload["bridge_readiness"]["candidate_b_full_corpus_runtime_to_layer3_material_authority_v1"]
        == "requires_separate_current_main_admission"
    )


def test_validate_triplet_rejects_absolute_database_path_outside_runtime_root(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)
    outside_db = tmp_path / "outside" / "lc.db"
    _write_db(
        outside_db,
        run_id="baseline-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.BASELINE_ENGINE,
    )
    _rewrite_summary(roots["baseline"], database_path=str(outside_db))

    with pytest.raises(triplet.ValidationError) as exc_info:
        triplet.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=roots["baseline"],
            candidate_a_run_root=roots["candidate_a"],
            candidate_b_run_root=roots["candidate_b"],
        )

    assert exc_info.value.code == "baseline_database_outside_runtime_root"


def test_validate_triplet_rejects_relative_database_path_escape(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)
    escaped_db = roots["baseline"].parent / "escaped.db"
    _write_db(
        escaped_db,
        run_id="baseline-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.BASELINE_ENGINE,
    )
    _rewrite_summary(roots["baseline"], database_path="../escaped.db")

    with pytest.raises(triplet.ValidationError) as exc_info:
        triplet.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=roots["baseline"],
            candidate_a_run_root=roots["candidate_a"],
            candidate_b_run_root=roots["candidate_b"],
        )

    assert exc_info.value.code == "baseline_database_outside_runtime_root"


def test_run_root_rejects_explicit_runtime_root_outside_admitted_parent(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()
    external_root = tmp_path / "other-checkout" / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "baseline"
    _write_summary(
        external_root,
        run_id="baseline-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.BASELINE_ENGINE,
    )

    with pytest.raises(triplet.ValidationError) as exc_info:
        triplet._run_root(
            str(external_root),
            checkout_root=checkout_root,
            label="baseline",
            engine=triplet.BASELINE_ENGINE,
            visual_lane=triplet.BASELINE_ENGINE,
        )

    assert exc_info.value.code == "baseline_runtime_root_outside_admitted_parent"


def test_main_discovers_latest_triplet_without_generating_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    _seed_triplet(checkout_root)
    monkeypatch.setattr(triplet, "ROOT", checkout_root)

    exit_code = triplet.main([])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["validate_only"] is True
    assert payload["artifacts_seeded_or_generated"] is False


def test_main_discovery_ignores_newer_variant_receipt_without_full_corpus_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout_root = tmp_path / "checkout"
    _seed_triplet(checkout_root)
    parent = checkout_root / "backend" / "app" / "storage_test_runtime" / "lc_e2e"
    _write_summary(
        parent / "baseline-newer-incomplete",
        run_id="baseline-newer-incomplete-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.BASELINE_ENGINE,
        target_outcomes=_target_outcomes()[:-1],
        generated_at_utc="2026-05-24T01:00:00Z",
    )
    monkeypatch.setattr(triplet, "ROOT", checkout_root)

    exit_code = triplet.main([])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_runs"]["baseline"]["run_id"] == "baseline-run"
    assert payload["compare_target_set"]["target_count"] == triplet.EXPECTED_CORPUS_PDF_COUNT


def test_validate_triplet_fails_closed_on_implicit_baseline_engine(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)
    _write_summary(
        roots["baseline"],
        run_id="baseline-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.BASELINE_ENGINE,
        explicit_engine=False,
    )

    with pytest.raises(triplet.ValidationError, match="baseline must prove explicit document_processing_engine"):
        triplet.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=roots["baseline"],
            candidate_a_run_root=roots["candidate_a"],
            candidate_b_run_root=roots["candidate_b"],
        )


def test_validate_triplet_fails_closed_on_target_set_mismatch(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)
    altered_targets = _target_outcomes()
    altered_targets[-1] = {**altered_targets[-1], "accession_number": "LOCALAPS99999"}
    _write_summary(
        roots["candidate_b"],
        run_id="candidate-b-run",
        document_processing_engine=triplet.CANDIDATE_B_ENGINE,
        visual_lane_mode=triplet.CANDIDATE_B_VISUAL_LANE,
        target_outcomes=altered_targets,
    )

    with pytest.raises(triplet.ValidationError, match="do not share the same full-corpus target set"):
        triplet.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=roots["baseline"],
            candidate_a_run_root=roots["candidate_a"],
            candidate_b_run_root=roots["candidate_b"],
        )


def test_validate_triplet_rejects_shared_target_set_outside_admitted_corpus(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)
    altered_targets = _target_outcomes()
    altered_targets[-1] = {**altered_targets[-1], "accession_number": "LOCALAPS99999"}
    for label, engine, visual_lane in (
        ("baseline", triplet.BASELINE_ENGINE, triplet.BASELINE_ENGINE),
        ("candidate_a", triplet.BASELINE_ENGINE, triplet.CANDIDATE_A_VISUAL_LANE),
        ("candidate_b", triplet.CANDIDATE_B_ENGINE, triplet.CANDIDATE_B_VISUAL_LANE),
    ):
        _write_summary(
            roots[label],
            run_id=f"{label}-run",
            document_processing_engine=engine,
            visual_lane_mode=visual_lane,
            target_outcomes=altered_targets,
        )

    with pytest.raises(triplet.ValidationError) as exc_info:
        triplet.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=roots["baseline"],
            candidate_a_run_root=roots["candidate_a"],
            candidate_b_run_root=roots["candidate_b"],
        )

    assert exc_info.value.code == "triplet_target_set_not_admitted"
    assert exc_info.value.context["admitted_target_set_authority"] == triplet.ADMITTED_TARGET_SET_AUTHORITY


def test_validate_triplet_rejects_duplicate_run_ids(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    roots = _seed_triplet(checkout_root)
    _write_summary(
        roots["candidate_a"],
        run_id="baseline-run",
        document_processing_engine=triplet.BASELINE_ENGINE,
        visual_lane_mode=triplet.CANDIDATE_A_VISUAL_LANE,
    )

    with pytest.raises(triplet.ValidationError) as exc_info:
        triplet.validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=roots["baseline"],
            candidate_a_run_root=roots["candidate_a"],
            candidate_b_run_root=roots["candidate_b"],
        )

    assert exc_info.value.code == "triplet_run_ids_not_distinct"
    assert exc_info.value.context["duplicates"] == {"baseline-run": ["baseline", "candidate_a"]}
