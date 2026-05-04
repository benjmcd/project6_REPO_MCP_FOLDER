from __future__ import annotations

from dataclasses import dataclass
from typing import Any


APS_PARSER_REGISTRY_CONTRACT_ID = "aps_parser_registry_v1"
APS_PARSER_REGISTRY_VERSION = "1.0.0"

APS_PARSER_ADMISSION_STATUS_ADMITTED = "admitted"
APS_PARSER_ADMISSION_STATUS_MEDIA_UNSUPPORTED = "media_not_supported_for_processing"
APS_PARSER_ADMISSION_STATUS_UNSUPPORTED = "unsupported_parser_lookup"

APS_DOCUMENT_PROCESSING_ENGINE_BASELINE = "baseline"
APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B = "candidate_b_opendataloader_pdf"


@dataclass(frozen=True)
class ApsParserSpec:
    content_type: str
    document_processing_engine: str
    parser_family: str
    parser_output_family: str
    parser_contract_id: str


_PARSER_SPECS: tuple[ApsParserSpec, ...] = (
    ApsParserSpec(
        content_type="text/plain",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="plain_text",
        parser_output_family="document_text_units",
        parser_contract_id="aps_plain_text_parser_v1",
    ),
    ApsParserSpec(
        content_type="text/csv",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="csv_table",
        parser_output_family="table_units",
        parser_contract_id="aps_csv_table_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/csv",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="csv_table",
        parser_output_family="table_units",
        parser_contract_id="aps_csv_table_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="xlsx_workbook",
        parser_output_family="table_units",
        parser_contract_id="aps_xlsx_workbook_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/json",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="json_recordset",
        parser_output_family="table_units",
        parser_contract_id="aps_json_recordset_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/x-sec-edgar-submission",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="sec_edgar_filing",
        parser_output_family="mixed_document_table_units",
        parser_contract_id="aps_sec_edgar_filing_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/pdf",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="pdf_document",
        parser_output_family="document_units",
        parser_contract_id="aps_pdf_document_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/pdf",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
        parser_family="pdf_candidate_b_opendataloader",
        parser_output_family="document_units",
        parser_contract_id="aps_candidate_b_opendataloader_pdf_parser_v1",
    ),
    ApsParserSpec(
        content_type="image/jpeg",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="ocr_image",
        parser_output_family="document_units",
        parser_contract_id="aps_image_ocr_parser_v1",
    ),
    ApsParserSpec(
        content_type="image/png",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="ocr_image",
        parser_output_family="document_units",
        parser_contract_id="aps_image_ocr_parser_v1",
    ),
    ApsParserSpec(
        content_type="image/tiff",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="ocr_image",
        parser_output_family="document_units",
        parser_contract_id="aps_image_ocr_parser_v1",
    ),
    ApsParserSpec(
        content_type="application/zip",
        document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        parser_family="archive_bundle",
        parser_output_family="archive_units",
        parser_contract_id="aps_archive_bundle_parser_v1",
    ),
)

_PARSER_SPEC_BY_KEY: dict[tuple[str, str], ApsParserSpec] = {
    (spec.content_type, spec.document_processing_engine): spec for spec in _PARSER_SPECS
}


def _base_registry_payload(
    *,
    effective_content_type: str,
    document_processing_engine: str,
) -> dict[str, Any]:
    return {
        "parser_registry_contract_id": APS_PARSER_REGISTRY_CONTRACT_ID,
        "parser_registry_version": APS_PARSER_REGISTRY_VERSION,
        "effective_content_type": effective_content_type,
        "document_processing_engine": document_processing_engine,
        "parser_admission_status": None,
        "parser_family": None,
        "parser_output_family": None,
        "parser_contract_id": None,
        "parser_failure_code": None,
        "parser_failure_reason": None,
    }


def resolve_parser(
    *,
    effective_content_type: Any,
    document_processing_engine: Any,
    supported_for_processing: Any = True,
) -> dict[str, Any]:
    """Resolve the current APS media result to an admitted parser contract.

    This registry is intentionally metadata-only. It makes parser admission
    explicit without changing the existing processor dispatch behavior.
    """
    content_type = str(effective_content_type or "").strip().lower()
    engine = str(document_processing_engine or APS_DOCUMENT_PROCESSING_ENGINE_BASELINE).strip().lower()
    payload = _base_registry_payload(
        effective_content_type=content_type,
        document_processing_engine=engine,
    )
    if not bool(supported_for_processing):
        return {
            **payload,
            "parser_admission_status": APS_PARSER_ADMISSION_STATUS_MEDIA_UNSUPPORTED,
            "parser_failure_code": "media_not_supported_for_processing",
            "parser_failure_reason": "media detection did not admit the content for processing",
        }

    spec = _PARSER_SPEC_BY_KEY.get((content_type, engine))
    if spec is None:
        return {
            **payload,
            "parser_admission_status": APS_PARSER_ADMISSION_STATUS_UNSUPPORTED,
            "parser_failure_code": f"unsupported_parser_lookup:{engine}:{content_type or 'unknown'}",
            "parser_failure_reason": "no parser contract is admitted for the content type and processing engine",
        }

    return {
        **payload,
        "parser_admission_status": APS_PARSER_ADMISSION_STATUS_ADMITTED,
        "parser_family": spec.parser_family,
        "parser_output_family": spec.parser_output_family,
        "parser_contract_id": spec.parser_contract_id,
    }


def admitted_parser_specs() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "content_type": spec.content_type,
            "document_processing_engine": spec.document_processing_engine,
            "parser_family": spec.parser_family,
            "parser_output_family": spec.parser_output_family,
            "parser_contract_id": spec.parser_contract_id,
        }
        for spec in _PARSER_SPECS
    )
