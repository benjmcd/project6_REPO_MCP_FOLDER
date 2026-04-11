from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from app.services import nrc_aps_page_evidence


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "nrc_aps_docs" / "v1"


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def test_analyze_pdf_bytes_born_digital_projects_text_heavy() -> None:
    result = nrc_aps_page_evidence.analyze_pdf_bytes(
        content=_fixture_bytes("born_digital.pdf"),
        source_name="born_digital.pdf",
    )

    assert result["schema_id"] == "aps.page_evidence.v1"
    assert result["candidate_id"] == "candidate_a_page_evidence"
    assert result["page_count"] == 1
    page = result["pages"][0]
    assert page["word_count"] > 0
    assert page["image_count"] == 0
    assert page["drawing_count"] == 0
    assert page["projected_visual_page_class"] == "text_heavy_or_empty"
    assert result["summary"]["contains_visual_projection"] is False


def test_analyze_pdf_bytes_scanned_projects_visual() -> None:
    result = nrc_aps_page_evidence.analyze_pdf_bytes(
        content=_fixture_bytes("scanned.pdf"),
        source_name="scanned.pdf",
    )

    assert result["page_count"] == 1
    page = result["pages"][0]
    assert page["word_count"] == 0
    assert page["image_count"] >= 1
    assert page["projected_visual_page_class"] == "diagram_or_visual"
    assert result["summary"]["contains_visual_projection"] is True


def test_invalid_pdf_fails_closed() -> None:
    with pytest.raises(ValueError, match="pdf_open_failed"):
        nrc_aps_page_evidence.analyze_pdf_bytes(
            content=b"not a pdf",
            source_name="invalid.pdf",
        )


def test_default_page_evidence_config_normalizes_thresholds() -> None:
    config = nrc_aps_page_evidence.default_page_evidence_config(
        {
            "text_word_threshold": -5,
            "visual_coverage_threshold": 2.0,
        }
    )

    assert config["text_word_threshold"] == 0
    assert config["visual_coverage_threshold"] == 1.0


def test_extract_page_evidence_record_keeps_projection_separate() -> None:
    with fitz.open(stream=_fixture_bytes("scanned.pdf"), filetype="pdf") as document:
        record = nrc_aps_page_evidence.extract_page_evidence_record(
            page=document[0],
            page_number=1,
        )

    assert record["page_number"] == 1
    assert record["image_count"] >= 1
    assert "projected_visual_page_class" not in record


def test_project_candidate_a_page_evidence_does_not_mutate_shared_record() -> None:
    with fitz.open(stream=_fixture_bytes("scanned.pdf"), filetype="pdf") as document:
        record = nrc_aps_page_evidence.extract_page_evidence_record(
            page=document[0],
            page_number=1,
        )

    projected = nrc_aps_page_evidence.project_candidate_a_page_evidence(record)

    assert "projected_visual_page_class" not in record
    assert projected["projected_visual_page_class"] == "diagram_or_visual"
    assert projected["image_count"] == record["image_count"]


def test_extract_pdf_document_evidence_bytes_keeps_document_candidate_neutral() -> None:
    result = nrc_aps_page_evidence.extract_pdf_document_evidence_bytes(
        content=_fixture_bytes("scanned.pdf"),
        source_name="scanned.pdf",
    )

    assert result["schema_id"] == "aps.page_evidence.v1"
    assert "candidate_id" not in result
    assert "summary" not in result
    assert result["page_count"] == 1
    assert "projected_visual_page_class" not in result["pages"][0]


def test_project_candidate_a_document_evidence_does_not_mutate_shared_document() -> None:
    shared = nrc_aps_page_evidence.extract_pdf_document_evidence_bytes(
        content=_fixture_bytes("scanned.pdf"),
        source_name="scanned.pdf",
    )

    projected = nrc_aps_page_evidence.project_candidate_a_document_evidence(shared)

    assert "candidate_id" not in shared
    assert "summary" not in shared
    assert "projected_visual_page_class" not in shared["pages"][0]
    assert projected["candidate_id"] == "candidate_a_page_evidence"
    assert projected["summary"]["contains_visual_projection"] is True
    assert projected["pages"][0]["projected_visual_page_class"] == "diagram_or_visual"


class _FakePage:
    rect = SimpleNamespace(width=612.0, height=792.0)

    def get_text(self, mode: str):
        if mode in {"words", "blocks"}:
            return []
        raise AssertionError(f"unexpected_text_mode:{mode}")

    def get_image_info(self):
        return []

    def get_drawings(self):
        return []


class _FakeDocument:
    def __init__(self) -> None:
        self.page_count = 1
        self.closed = False
        self._page = _FakePage()

    def __getitem__(self, index: int):
        assert index == 0
        return self._page

    def close(self) -> None:
        self.closed = True


def test_analyze_pdf_bytes_closes_document_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    document = _FakeDocument()
    monkeypatch.setattr(nrc_aps_page_evidence.fitz, "open", lambda *args, **kwargs: document)

    result = nrc_aps_page_evidence.analyze_pdf_bytes(
        content=b"%PDF-1.4",
        source_name="fake.pdf",
    )

    assert result["page_count"] == 1
    assert result["summary"]["contains_visual_projection"] is False
    assert document.closed is True


def test_analyze_pdf_bytes_closes_document_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    document = _FakeDocument()
    monkeypatch.setattr(nrc_aps_page_evidence.fitz, "open", lambda *args, **kwargs: document)
    monkeypatch.setattr(
        nrc_aps_page_evidence,
        "extract_page_evidence_record",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("simulated_page_evidence_failure")),
    )

    with pytest.raises(RuntimeError, match="simulated_page_evidence_failure"):
        nrc_aps_page_evidence.analyze_pdf_bytes(
            content=b"%PDF-1.4",
            source_name="fake.pdf",
        )

    assert document.closed is True
