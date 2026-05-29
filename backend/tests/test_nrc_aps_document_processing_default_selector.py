from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import types
import zipfile
from typing import Any

import pytest

from app.services import nrc_aps_document_processing as processing


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _fake_pdf_result(*, detection: dict[str, Any], config: dict[str, Any], extractor_family: str) -> dict[str, Any]:
    return {
        **detection,
        "document_processing_contract_id": processing.APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **processing._parser_registry_fields(config),
        "extractor_family": extractor_family,
        "quality_status": "ok",
        "ordered_units": [
            {
                "page_number": 1,
                "unit_kind": "text_block",
                "text": "candidate b selector proof",
                "start_char": 0,
                "end_char": 26,
            }
        ],
        "candidate_b_default_fallback_reason": config.get("candidate_b_default_fallback_reason"),
    }


def test_omitted_document_processing_engine_defaults_to_candidate_b_for_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        calls.append(dict(config))
        return _fake_pdf_result(
            detection=detection,
            config=config,
            extractor_family="pdf_candidate_b_opendataloader",
        )

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", fake_candidate_b)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={},
    )

    assert result["parser_family"] == "pdf_candidate_b_opendataloader"
    assert result["parser_contract_id"] == "aps_candidate_b_opendataloader_pdf_parser_v1"
    assert calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    assert calls[0]["document_processing_engine_explicit"] is False
    assert calls[0]["visual_lane_mode"] == processing.APS_VISUAL_LANE_MODE_BASELINE


def test_omitted_document_processing_engine_preserves_candidate_a_visual_lane_on_baseline_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_calls: list[dict[str, Any]] = []

    def forbidden_candidate_b(
        *,
        content: bytes,
        detection: dict[str, Any],
        config: dict[str, Any],
        deadline: float | None,
    ):
        raise AssertionError("Candidate A visual lane must not be rerouted through Candidate B by omitted engine default")

    def fake_baseline(
        *,
        content: bytes,
        detection: dict[str, Any],
        config: dict[str, Any],
        deadline: float | None,
    ):
        baseline_calls.append(dict(config))
        return _fake_pdf_result(detection=detection, config=config, extractor_family="pdf_baseline")

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", forbidden_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", fake_baseline)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={"visual_lane_mode": processing.APS_VISUAL_LANE_MODE_CANDIDATE_A},
    )

    assert result["parser_family"] == "pdf_document"
    assert baseline_calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
    assert baseline_calls[0]["document_processing_engine_explicit"] is False
    assert baseline_calls[0]["visual_lane_mode"] == processing.APS_VISUAL_LANE_MODE_CANDIDATE_A


def test_omitted_document_processing_engine_with_candidate_b_visual_lane_keeps_candidate_b_pdf_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_candidate_b(
        *,
        content: bytes,
        detection: dict[str, Any],
        config: dict[str, Any],
        deadline: float | None,
    ):
        calls.append(dict(config))
        return _fake_pdf_result(
            detection=detection,
            config=config,
            extractor_family="pdf_candidate_b_opendataloader",
        )

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", fake_candidate_b)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={"visual_lane_mode": processing.APS_VISUAL_LANE_MODE_CANDIDATE_B},
    )

    assert result["parser_family"] == "pdf_candidate_b_opendataloader"
    assert calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    assert calls[0]["document_processing_engine_explicit"] is False
    assert calls[0]["visual_lane_mode"] == processing.APS_VISUAL_LANE_MODE_CANDIDATE_B


def test_omitted_pdf_selector_falls_closed_to_baseline_when_candidate_b_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_calls: list[dict[str, Any]] = []

    def fake_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise ValueError("candidate_b_package_unavailable")

    def fake_baseline(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        baseline_calls.append(dict(config))
        return _fake_pdf_result(detection=detection, config=config, extractor_family="pdf_baseline")

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", fake_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", fake_baseline)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={},
    )

    assert result["parser_family"] == "pdf_document"
    assert result["candidate_b_default_fallback_reason"] == "candidate_b_package_unavailable"
    assert baseline_calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE


def test_omitted_pdf_selector_falls_closed_to_baseline_when_candidate_b_parser_unadmitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_resolve_parser = processing.nrc_aps_parser_registry.resolve_parser

    def fake_resolve_parser(
        *,
        effective_content_type: Any,
        document_processing_engine: Any,
        supported_for_processing: Any = True,
    ) -> dict[str, Any]:
        if document_processing_engine == processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B:
            return {
                "parser_admission_status": processing.nrc_aps_parser_registry.APS_PARSER_ADMISSION_STATUS_UNSUPPORTED,
                "parser_failure_code": "candidate_b_parser_unadmitted",
            }
        return original_resolve_parser(
            effective_content_type=effective_content_type,
            document_processing_engine=document_processing_engine,
            supported_for_processing=supported_for_processing,
        )

    def forbidden_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise AssertionError("unadmitted Candidate B parser must fail closed before Candidate B processing")

    def fake_baseline(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        return _fake_pdf_result(detection=detection, config=config, extractor_family="pdf_baseline")

    monkeypatch.setattr(processing.nrc_aps_parser_registry, "resolve_parser", fake_resolve_parser)
    monkeypatch.setattr(processing, "_process_pdf_candidate_b", forbidden_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", fake_baseline)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={},
    )

    assert result["parser_family"] == "pdf_document"
    assert result["candidate_b_default_fallback_reason"] == "parser_admission:candidate_b_parser_unadmitted"


def test_explicit_baseline_for_pdf_forces_baseline_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    baseline_calls: list[dict[str, Any]] = []

    def forbidden_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise AssertionError("explicit baseline must not call Candidate B")

    def fake_baseline(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        baseline_calls.append(dict(config))
        return _fake_pdf_result(detection=detection, config=config, extractor_family="pdf_baseline")

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", forbidden_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", fake_baseline)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={"document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE},
    )

    assert result["parser_family"] == "pdf_document"
    assert baseline_calls[0]["document_processing_engine_explicit"] is True


def test_explicit_candidate_b_for_pdf_still_raises_candidate_b_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise ValueError("candidate_b_package_unavailable")

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", fake_candidate_b)

    with pytest.raises(ValueError, match="candidate_b_package_unavailable"):
        processing.process_document(
            content=PDF_BYTES,
            declared_content_type="application/pdf",
            config={"document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B},
        )


def test_explicit_candidate_b_for_non_pdf_fails_closed_to_baseline() -> None:
    result = processing.process_document(
        content=b"hello from a plain text corpus artifact",
        declared_content_type="text/plain",
        config={"document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B},
    )

    assert result["parser_family"] == "plain_text"
    assert result["parser_contract_id"] == "aps_plain_text_parser_v1"


def test_invalid_document_processing_engine_for_pdf_fails_closed_to_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_calls: list[dict[str, Any]] = []

    def forbidden_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise AssertionError("invalid selector must fail closed before Candidate B")

    def fake_baseline(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        baseline_calls.append(dict(config))
        return _fake_pdf_result(detection=detection, config=config, extractor_family="pdf_baseline")

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", forbidden_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", fake_baseline)

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={"document_processing_engine": "candidate_c_other_pdf"},
    )

    assert result["parser_family"] == "pdf_document"
    assert baseline_calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
    assert baseline_calls[0]["document_processing_engine_explicit"] is True


def test_default_selector_policy_keeps_non_pdf_families_on_baseline() -> None:
    for content_type in (
        "text/plain",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/json",
        "application/x-sec-edgar-submission",
        "application/zip",
        "image/png",
    ):
        assert (
            processing._resolve_document_processing_engine(
                {"document_processing_engine_explicit": False},
                effective_content_type=content_type,
            )
            == processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
        )


def test_zip_pdf_member_remains_baseline_without_explicit_candidate_b(monkeypatch: pytest.MonkeyPatch) -> None:
    baseline_calls: list[dict[str, Any]] = []

    def forbidden_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise AssertionError("ZIP member processing is outside the Candidate B default selector slice")

    def fake_baseline(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        baseline_calls.append(dict(config))
        return _fake_pdf_result(detection=detection, config=config, extractor_family="pdf_baseline")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w") as zf:
        zf.writestr("inner.pdf", PDF_BYTES)

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", forbidden_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", fake_baseline)

    result = processing.process_document(
        content=archive.getvalue(),
        declared_content_type="application/zip",
        config={},
    )

    assert result["parser_family"] == "archive_bundle"
    assert result["member_summaries"][0]["status"] == "success"
    assert baseline_calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
    assert baseline_calls[0]["document_processing_engine_explicit"] is True


def test_zip_pdf_member_preserves_explicit_candidate_b_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate_b_calls: list[dict[str, Any]] = []

    def fake_candidate_b(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        candidate_b_calls.append(dict(config))
        return _fake_pdf_result(
            detection=detection,
            config=config,
            extractor_family="pdf_candidate_b_opendataloader",
        )

    def forbidden_baseline(*, content: bytes, detection: dict[str, Any], config: dict[str, Any], deadline: float | None):
        raise AssertionError("explicit Candidate B ZIP PDF members must not be forced through baseline")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w") as zf:
        zf.writestr("inner.pdf", PDF_BYTES)

    monkeypatch.setattr(processing, "_process_pdf_candidate_b", fake_candidate_b)
    monkeypatch.setattr(processing, "_process_pdf", forbidden_baseline)

    result = processing.process_document(
        content=archive.getvalue(),
        declared_content_type="application/zip",
        config={"document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B},
    )

    assert result["parser_family"] == "archive_bundle"
    assert result["member_summaries"][0]["status"] == "success"
    assert candidate_b_calls[0]["document_processing_engine"] == processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    assert candidate_b_calls[0]["document_processing_engine_explicit"] is True


def test_candidate_b_pdf_page_count_respects_configured_parse_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_convert(*, output_dir: str, **_: Any) -> None:
        Path(output_dir, "input.json").write_text(
            json.dumps({"number of pages": 3, "kids": []}),
            encoding="utf-8",
        )

    module = types.ModuleType("opendataloader_pdf")
    module.convert = fake_convert
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", module)
    monkeypatch.setattr(
        processing.importlib.metadata,
        "version",
        lambda package_name: processing.APS_ODL_PDF_EXPECTED_VERSION,
    )

    with pytest.raises(ValueError, match="candidate_b_pdf_page_limit_exceeded"):
        processing.process_document(
            content=PDF_BYTES,
            declared_content_type="application/pdf",
            config={
                "artifact_storage_dir": str(tmp_path),
                "content_parse_max_pages": 2,
                "document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
            },
        )


def test_candidate_b_pdf_timeout_is_checked_after_convert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_convert(*, output_dir: str, **_: Any) -> None:
        Path(output_dir, "input.json").write_text(
            json.dumps({"number of pages": 1, "kids": []}),
            encoding="utf-8",
        )

    module = types.ModuleType("opendataloader_pdf")
    module.convert = fake_convert
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", module)
    monkeypatch.setattr(
        processing.importlib.metadata,
        "version",
        lambda package_name: processing.APS_ODL_PDF_EXPECTED_VERSION,
    )
    deadline_checks = 0

    def fake_deadline_check(deadline: float | None) -> None:
        nonlocal deadline_checks
        deadline_checks += 1
        if deadline_checks == 2:
            raise ValueError("content_parse_timeout_exceeded")

    monkeypatch.setattr(processing, "_raise_if_deadline_exceeded", fake_deadline_check)

    with pytest.raises(ValueError, match="content_parse_timeout_exceeded"):
        processing._process_pdf_candidate_b(
            content=PDF_BYTES,
            detection={"effective_content_type": "application/pdf"},
            config=processing.default_processing_config({"artifact_storage_dir": str(tmp_path)}),
            deadline=1.0,
        )


def test_candidate_b_visual_lane_emits_retained_page_evidence_refs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_convert(*, input_path: str, output_dir: str, **_: Any) -> None:
        assert Path(input_path).name == "input.pdf"
        payload = {
            "number of pages": 1,
            "kids": [
                {
                    "type": "image",
                    "page number": 1,
                    "bounding box": [0, 0, 100, 100],
                },
                {
                    "type": "paragraph",
                    "page number": 1,
                    "content": "Candidate B page evidence text",
                    "bounding box": [1, 2, 3, 4],
                },
            ],
        }
        Path(output_dir, "input.json").write_text(json.dumps(payload), encoding="utf-8")

    module = types.ModuleType("opendataloader_pdf")
    module.convert = fake_convert
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", module)
    monkeypatch.setattr(
        processing.importlib.metadata,
        "version",
        lambda package_name: processing.APS_ODL_PDF_EXPECTED_VERSION,
    )

    result = processing.process_document(
        content=PDF_BYTES,
        declared_content_type="application/pdf",
        config={
            "artifact_storage_dir": str(tmp_path),
            "visual_lane_mode": processing.APS_VISUAL_LANE_MODE_CANDIDATE_B,
        },
    )

    assert result["parser_family"] == "pdf_candidate_b_opendataloader"
    assert result["visual_lane_mode"] == processing.APS_VISUAL_LANE_MODE_CANDIDATE_B
    assert result["candidate_b_retained_artifact_refs"] == [
        {"relative_name": "input.pdf", "artifact_role": "source_pdf", "material_text_payload": False},
        {"relative_name": "input.json", "artifact_role": "raw_json", "material_text_payload": True},
    ]
    assert result["visual_page_refs"] == [
        {
            "page_number": 1,
            "visual_lane_mode": processing.APS_VISUAL_LANE_MODE_CANDIDATE_B,
            "document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
            "visual_page_class": processing.APS_VISUAL_CLASS_DIAGRAM,
            "status": "candidate_b_page_evidence_retained",
            "evidence_source": "opendataloader_pdf_json",
            "image_count": 1,
            "retained_artifact_refs": result["candidate_b_retained_artifact_refs"],
        }
    ]
    assert list(tmp_path.rglob("input.pdf"))
    assert list(tmp_path.rglob("input.json"))
