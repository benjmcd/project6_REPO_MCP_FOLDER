from __future__ import annotations

from pathlib import Path

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
