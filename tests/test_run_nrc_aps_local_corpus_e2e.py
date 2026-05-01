from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import run_nrc_aps_local_corpus_e2e as local_corpus_e2e


def _write_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n% minimal fixture\n")


def _local_doc(path: Path) -> local_corpus_e2e.LocalCorpusDocument:
    _write_pdf(path)
    return local_corpus_e2e.LocalCorpusDocument(
        ordinal=1,
        accession_number="ML26000A001",
        title="Fixture Document",
        document_type="Inspection Report",
        folder_name="inspection_reports_for_testing",
        folder_slug="inspection",
        allow_unknown_document_type=False,
        file_path=path,
        document_date="2026-01-01",
        date_added_timestamp="2026-01-01T00:00:00Z",
        url="https://example.test/fixture.pdf",
    )


def test_document_processing_engine_parser_defaults_to_baseline() -> None:
    args = local_corpus_e2e.build_parser().parse_args([])

    assert args.document_processing_engine == local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_BASELINE


def test_document_processing_engine_parser_accepts_candidate_b() -> None:
    args = local_corpus_e2e.build_parser().parse_args(
        ["--document-processing-engine", local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B]
    )

    assert args.document_processing_engine == local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B


def test_document_processing_engine_parser_rejects_invalid() -> None:
    with pytest.raises(SystemExit):
        local_corpus_e2e.build_parser().parse_args(["--document-processing-engine", "other"])


def test_build_submit_payload_preserves_baseline_default(tmp_path: Path) -> None:
    doc = _local_doc(tmp_path / "ML26000A001.pdf")

    payload = local_corpus_e2e._build_submit_payload(
        [doc],
        document_processing_engine=local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_BASELINE,
        idempotency_key="local-corpus-e2e-test",
    )

    assert payload["client_request_id"] == "local-corpus-e2e-test"
    assert payload["max_items"] == 1
    assert "document_processing_engine" not in payload


def test_build_submit_payload_propagates_candidate_b(tmp_path: Path) -> None:
    doc = _local_doc(tmp_path / "ML26000A001.pdf")

    payload = local_corpus_e2e._build_submit_payload(
        [doc],
        document_processing_engine=local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
        idempotency_key="local-corpus-e2e-test",
    )

    assert payload["document_processing_engine"] == local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B


def test_main_summary_records_document_processing_engine(tmp_path: Path, monkeypatch) -> None:
    runtime_parent = tmp_path / "lc_e2e"
    runtime_root = runtime_parent / "cb-p3"
    doc = _local_doc(tmp_path / "corpus" / "ML26000A001.pdf")
    observed: dict[str, str] = {}

    @contextmanager
    def fake_isolated_runtime(fake_client, actual_runtime_root):  # noqa: ANN001
        del fake_client
        yield SimpleNamespace(
            client=object(),
            env={"DATABASE_URL": "sqlite:///lc.db"},
            database_path=actual_runtime_root / "lc.db",
            storage_dir=actual_runtime_root / "storage",
        )

    def fake_execute_proof(runtime, docs, actual_runtime_root, fake_client, *, document_processing_engine):  # noqa: ANN001
        del runtime, docs, actual_runtime_root, fake_client
        observed["document_processing_engine"] = document_processing_engine
        return {
            "run_id": "run-candidate-b",
            "submission": {"document_processing_engine": document_processing_engine},
        }

    monkeypatch.setattr(local_corpus_e2e, "DEFAULT_RUNTIME_PARENT", runtime_parent)
    monkeypatch.setattr(local_corpus_e2e, "_run_preflight", lambda actual_runtime_root: ([doc], {"passed": True}, []))
    monkeypatch.setattr(local_corpus_e2e, "_isolated_runtime", fake_isolated_runtime)
    monkeypatch.setattr(local_corpus_e2e, "_execute_proof", fake_execute_proof)

    exit_code = local_corpus_e2e.main(
        [
            "--runtime-root",
            str(runtime_root),
            "--document-processing-engine",
            local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
        ]
    )

    summary = json.loads((runtime_root / "local_corpus_e2e_summary.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert observed["document_processing_engine"] == local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    assert summary["document_processing_engine"] == local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    assert summary["submission"]["document_processing_engine"] == local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B


def test_candidate_b_advanced_metrics_require_candidate_b_extractor_not_ocr() -> None:
    summary = local_corpus_e2e._summarize_advanced_metrics(
        [
            {
                "ocr_exercised": False,
                "table_unit_count": 0,
                "ordered_unit_count": 3,
                "visual_ref_count": 0,
                "extractor_family": "pdf_candidate_b_opendataloader",
                "extractor_id": "aps_odl_pdf_extractor",
            }
        ],
        document_processing_engine=local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
        unknown_doc_type_failures=[],
        unresolved_visual_refs=[],
    )

    assert summary["ocr_file_count"] == 0
    assert summary["table_file_count"] == 0
    assert summary["candidate_b_extractor_file_count"] == 1
    assert summary["candidate_b_ordered_unit_file_count"] == 1
    assert summary["candidate_b_ordered_unit_total"] == 3


def test_baseline_advanced_metrics_still_require_ocr_and_table() -> None:
    with pytest.raises(local_corpus_e2e.ProofError, match="OCR-assisted extraction"):
        local_corpus_e2e._summarize_advanced_metrics(
            [
                {
                    "ocr_exercised": False,
                    "table_unit_count": 0,
                    "ordered_unit_count": 3,
                    "visual_ref_count": 0,
                    "extractor_family": "pdf_candidate_b_opendataloader",
                    "extractor_id": "aps_odl_pdf_extractor",
                }
            ],
            document_processing_engine=local_corpus_e2e.DOCUMENT_PROCESSING_ENGINE_BASELINE,
            unknown_doc_type_failures=[],
            unresolved_visual_refs=[],
        )


def test_build_local_corpus_documents_discovers_dynamic_folder_shape(tmp_path: Path, monkeypatch) -> None:
    corpus_root = tmp_path / "nrc_adams_documents_for_testing"
    known_folder = corpus_root / "inspection_reports_for_testing"
    dynamic_folder = corpus_root / "new_files_for_testing_added"
    empty_folder = corpus_root / "empty_folder"

    _write_pdf(known_folder / "ML26000A001_known.pdf")
    _write_pdf(dynamic_folder / "nested" / "ML26000A002_dynamic.pdf")
    _write_pdf(dynamic_folder / "nested" / "supplement.pdf")
    empty_folder.mkdir(parents=True, exist_ok=True)

    document_types_path = tmp_path / "document_types.json"
    document_types_path.write_text(
        json.dumps(
            {
                "document_types": [
                    "Inspection Report",
                    "Technical Specification, Amendment",
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(local_corpus_e2e, "DEFAULT_CORPUS_ROOT", corpus_root)
    monkeypatch.setattr(local_corpus_e2e, "DOCUMENT_TYPES_JSON", document_types_path)

    docs, corpus_shape = local_corpus_e2e._build_local_corpus_documents(corpus_root)

    assert len(docs) == 3
    assert corpus_shape["total_pdfs"] == 3
    assert corpus_shape["folder_counts"]["inspection"] == 1
    assert corpus_shape["folder_counts"]["new-files-added"] == 2
    assert corpus_shape["dynamic_folder_names"] == ["new_files_for_testing_added"]
    assert corpus_shape["ignored_empty_top_level_dirs"] == ["empty_folder"]

    inspection_doc = next(doc for doc in docs if doc.folder_slug == "inspection")
    assert inspection_doc.document_type == "Inspection Report"
    assert inspection_doc.allow_unknown_document_type is False

    dynamic_docs = [doc for doc in docs if doc.folder_slug == "new-files-added"]
    assert len(dynamic_docs) == 2
    assert all(doc.document_type == local_corpus_e2e.UNKNOWN_LOCAL_CORPUS_DOCUMENT_TYPE for doc in dynamic_docs)
    assert all(doc.allow_unknown_document_type is True for doc in dynamic_docs)
