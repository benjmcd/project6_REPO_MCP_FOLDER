from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import seed_wb_compare


def test_build_fixture_documents_uses_frozen_pdf_fixture_set() -> None:
    docs, corpus_shape = seed_wb_compare.build_fixture_documents()

    assert [doc.file_path.stem.lower() for doc in docs] == [
        "ml17123a319",
        "layout",
        "fontish",
        "scanned",
        "mixed",
    ]
    assert [doc.title for doc in docs] == [doc.file_path.name for doc in docs]
    assert corpus_shape["included_fixture_ids"] == list(seed_wb_compare.FROZEN_FIXTURE_IDS)
    assert corpus_shape["fixture_count"] == len(seed_wb_compare.FROZEN_FIXTURE_IDS)
    assert corpus_shape["document_type"] == seed_wb_compare.FIXTURE_DOCUMENT_TYPE
    assert corpus_shape["ocr_required_fixture_ids"] == ["scanned", "mixed"]


def test_inject_visual_lane_mode_only_marks_candidate_a() -> None:
    baseline_payload = seed_wb_compare._inject_visual_lane_mode({"mode": "strict_builder"}, "baseline")
    candidate_payload = seed_wb_compare._inject_visual_lane_mode({"mode": "strict_builder"}, "candidate_a_page_evidence_v1")

    assert "visual_lane_mode" not in baseline_payload
    assert candidate_payload["visual_lane_mode"] == "candidate_a_page_evidence_v1"


def test_main_writes_summary_for_candidate_a_seed(tmp_path: Path, monkeypatch) -> None:
    runtime_root = tmp_path / "seed-runtime"
    docs = ["fixture-doc"]
    preflight = {"runtime_root": str(runtime_root)}
    findings = [{"code": "seed"}]

    monkeypatch.setattr(seed_wb_compare, "run_preflight", lambda candidate: (docs, preflight, findings))

    @contextmanager
    def fake_runtime_context(fake_client, candidate_runtime_root):
        del fake_client
        assert candidate_runtime_root == runtime_root
        runtime = type(
            "FakeRuntime",
            (),
            {
                "database_path": runtime_root / "lc.db",
                "storage_dir": runtime_root / "storage",
                "env": {"DATABASE_URL": "sqlite:///fake.db"},
            },
        )()
        yield runtime

    monkeypatch.setattr(seed_wb_compare, "_isolated_runtime", fake_runtime_context)
    monkeypatch.setattr(seed_wb_compare, "LocalCorpusNrcClient", lambda seed_docs: object())
    monkeypatch.setattr(
        seed_wb_compare,
        "execute_seed",
        lambda runtime, seed_docs, candidate_runtime_root, fake_client, *, visual_lane_mode: {
            "run_id": "seed-run-001",
            "submission": {"visual_lane_mode": visual_lane_mode},
            "run_detail": {"status": "completed", "selected_count": len(seed_docs)},
            "search_smoke": {},
            "selected_branch_rows": [],
            "downstream_artifacts": {},
            "gate_results": {},
            "advanced_metrics": {},
            "client_trace": {},
        },
    )
    monkeypatch.setattr(seed_wb_compare, "_resolve_runtime_root", lambda raw: runtime_root)
    monkeypatch.setattr(seed_wb_compare, "EXPECTED_INTERPRETER", Path(sys.executable))

    exit_code = seed_wb_compare.main(["--runtime-root", str(runtime_root), "--visual-lane-mode", "candidate_a_page_evidence_v1"])

    assert exit_code == 0
    summary = json.loads((runtime_root / "local_corpus_e2e_summary.json").read_text(encoding="utf-8"))
    assert summary["passed"] is True
    assert summary["run_id"] == "seed-run-001"
    assert summary["visual_lane_mode"] == "candidate_a_page_evidence_v1"
    assert summary["corpus_fixture_ids"] == list(seed_wb_compare.FROZEN_FIXTURE_IDS)


def test_main_skips_summary_write_when_preflight_rejects_runtime_root(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    runtime_root = tmp_path / "occupied-runtime"
    runtime_root.mkdir()
    sentinel = runtime_root / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(seed_wb_compare, "_resolve_runtime_root", lambda raw: runtime_root)
    monkeypatch.setattr(
        seed_wb_compare,
        "run_preflight",
        lambda candidate: (_ for _ in ()).throw(RuntimeError("runtime_root must be empty")),
    )

    exit_code = seed_wb_compare.main(["--runtime-root", str(runtime_root), "--visual-lane-mode", "baseline"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert not (runtime_root / "local_corpus_e2e_summary.json").exists()
