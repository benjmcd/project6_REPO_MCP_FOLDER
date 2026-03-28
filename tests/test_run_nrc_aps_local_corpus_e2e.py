from __future__ import annotations

import json
from pathlib import Path

from tools import run_nrc_aps_local_corpus_e2e as local_corpus_e2e


def _write_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n% minimal fixture\n")


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
