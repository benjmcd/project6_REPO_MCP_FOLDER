from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import ApsContentChunk, ApsContentDocument, L3PassRun
from app.services import layer3_pdf_location


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_document(db, *, page_start: int | None = 2) -> None:
    text = "Cooling pump inspection evidence appears in the selected PDF paragraph."
    db.add(
        ApsContentDocument(
            content_id="content-pdf-location",
            content_contract_id="aps_pdf_content_units_v1",
            chunking_contract_id="aps_pdf_chunking_v1",
            normalization_contract_id="aps_pdf_normalization_v1",
            normalized_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            normalized_char_count=len(text),
            chunk_count=1,
            content_status="indexed",
            media_type="application/pdf",
            document_class="inspection_report",
            quality_status="strong",
            page_count=4,
            diagnostics_ref="secret-diagnostics.json",
            visual_page_refs_json=json.dumps(
                [{"page_number": 2, "status": "preserved", "blob_ref": "secret.pdf"}]
            ),
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-pdf-location",
            chunk_id="chunk-pdf-location-1",
            content_contract_id="aps_pdf_content_units_v1",
            chunking_contract_id="aps_pdf_chunking_v1",
            chunk_ordinal=0,
            start_char=0,
            end_char=len(text),
            chunk_text=text,
            chunk_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            page_start=page_start,
            page_end=page_start,
            unit_kind="pdf_paragraph",
            quality_status="strong",
        )
    )
    db.flush()


def _pass_run(output_payload_ref: str | None) -> L3PassRun:
    return L3PassRun(
        pass_run_id="pass-run-pdf-location",
        session_id="session-pdf-location",
        analysis_plan_id="plan-pdf-location",
        analysis_set_id="set-pdf-location",
        pass_type="single_item",
        engine_family="qualitative_aps_document",
        status="completed",
        input_payload_ref="payload://input",
        output_payload_ref=output_payload_ref,
    )


def _write_output(tmp_path: Path, *, content_id: str = "content-pdf-location") -> Path:
    output = tmp_path / "output.json"
    output.write_text(
        json.dumps(
            {
                "source_shape": "aps_content_document",
                "session_id": "session-pdf-location",
                "analysis_plan_id": "plan-pdf-location",
                "pass_run_id": "pass-run-pdf-location",
                "material_snapshot_id": "snapshot-pdf-location",
                "analysis_unit_id": "unit-pdf-location",
                "document_identity": {
                    "content_id": content_id,
                    "content_contract_id": "aps_pdf_content_units_v1",
                    "chunking_contract_id": "aps_pdf_chunking_v1",
                    "normalization_contract_id": "aps_pdf_normalization_v1",
                },
                "chunk_summary": {
                    "chunk_ids": ["chunk-pdf-location-1"],
                    "chunk_hashes": ["hash-pdf-location"],
                },
                "output_items_json": [
                    {
                        "item_ref": "item-pdf-location",
                        "chunk_id": "chunk-pdf-location-1",
                        "bounded_text_preview": "Cooling pump inspection evidence appears.",
                        "highlight_spans": [{"start": 0, "end": 16}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return output


def test_pdf_location_projection_uses_existing_document_chunk_page_authority(db_session, tmp_path) -> None:
    _seed_document(db_session)
    pass_run = _pass_run(str(_write_output(tmp_path)))
    db_session.add(pass_run)
    db_session.flush()

    projection = layer3_pdf_location.pdf_location_projection_for_pass_run(db_session, pass_run=pass_run)

    assert projection["schema_id"] == "layer3.pdf_location_projection.v1"
    assert projection["available"] is True
    assert projection["named_runtime_use_case"] == "pdf_location_from_aps_content_document_citation"
    assert projection["server_authority_contract"] == "aps_content_document_chunk_page_refs_and_citation_highlight_spans"
    assert projection["document_identity"]["content_id"] == "content-pdf-location"
    assert projection["document_identity"]["media_type"] == "application/pdf"
    assert projection["visual_page_refs"] == [{"page_number": 2, "status": "preserved"}]
    assert projection["location_items"][0]["chunk_id"] == "chunk-pdf-location-1"
    assert projection["location_items"][0]["page_start"] == 2
    assert projection["location_items"][0]["page_end"] == 2
    assert projection["location_items"][0]["page_label"] == "p. 2"
    assert projection["location_items"][0]["highlight_spans"] == [
        {"start": 0, "end": 16, "source": "sections[].citations[].highlight_spans"}
    ]
    serialized = json.dumps(projection)
    assert "secret.pdf" not in serialized
    assert "secret-diagnostics.json" not in serialized
    assert "raw_pdf_blob_streaming" in projection["forbidden_runtime"]
    assert projection["no_side_effects"] is True


def test_pdf_location_projection_fails_closed_without_document_authority(db_session, tmp_path) -> None:
    pass_run = _pass_run(str(_write_output(tmp_path, content_id="missing-content")))
    db_session.add(pass_run)
    db_session.flush()

    projection = layer3_pdf_location.pdf_location_projection_for_pass_run(db_session, pass_run=pass_run)

    assert projection["available"] is False
    assert projection["blocked_reason"] == "pdf_location_document_authority_missing"
    assert projection["location_items"] == []


def test_pdf_location_projection_fails_closed_without_page_authority(db_session, tmp_path) -> None:
    _seed_document(db_session, page_start=None)
    pass_run = _pass_run(str(_write_output(tmp_path)))
    db_session.add(pass_run)
    db_session.flush()

    projection = layer3_pdf_location.pdf_location_projection_for_pass_run(db_session, pass_run=pass_run)

    assert projection["available"] is False
    assert projection["blocked_reason"] == "pdf_location_page_authority_missing"
