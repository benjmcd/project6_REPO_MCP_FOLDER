from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.services import nrc_aps_csv_parser


APS_SEC_EDGAR_FILING_CONTRACT_ID = "aps_sec_edgar_filing_units_v1"
APS_SEC_EDGAR_PARSER_ID = "aps_sec_edgar_filing_parser"
APS_SEC_EDGAR_PARSER_VERSION = "1.0.0"
APS_SEC_EDGAR_CONTENT_TYPE = "application/x-sec-edgar-submission"

_DEFAULT_ADMITTED_FORMS = ("10-K", "10-Q", "8-K")
_SEC_TAG_RE = re.compile(r"<([A-Z0-9-]+)>\s*([^\r\n<]*)", re.IGNORECASE)
_DOCUMENT_RE = re.compile(r"<DOCUMENT>(?P<body>.*?)</DOCUMENT>", re.IGNORECASE | re.DOTALL)
_TEXT_RE = re.compile(r"<TEXT>(?P<text>.*?)</TEXT>", re.IGNORECASE | re.DOTALL)
_TABLE_RE = re.compile(r"<TABLE>(?P<table>.*?)</TABLE>", re.IGNORECASE | re.DOTALL)
_ITEM_RE = re.compile(r"(?im)^\s*(ITEM\s+\d+[A-Z]?(?:\.\d+)?\.?)\s+")


def _decode_filing_content(content: bytes) -> tuple[str, str]:
    data = bytes(content or b"")
    if not data:
        raise ValueError("sec_edgar_empty")
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        try:
            return data.decode("cp1252"), "cp1252"
        except UnicodeDecodeError as exc:
            raise ValueError("sec_edgar_decode_failed") from exc


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _tag_map(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in _SEC_TAG_RE.finditer(text):
        key = match.group(1).strip().upper()
        value = match.group(2).strip()
        if key and value and key not in result:
            result[key] = value
    return result


def _header_text(text: str) -> str:
    match = re.search(r"<SEC-HEADER>(?P<header>.*?)</SEC-HEADER>", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group("header")
    first_document = re.search(r"<DOCUMENT>", text, re.IGNORECASE)
    return text[: first_document.start()] if first_document else ""


def _document_metadata(document_body: str) -> tuple[dict[str, Any], str]:
    text_match = _TEXT_RE.search(document_body)
    tag_region = document_body[: text_match.start()] if text_match else document_body
    tags = _tag_map(tag_region)
    doc_text = text_match.group("text") if text_match else ""
    return (
        {
            "type": tags.get("TYPE", ""),
            "sequence": tags.get("SEQUENCE", ""),
            "filename": tags.get("FILENAME", ""),
            "description": tags.get("DESCRIPTION", ""),
        },
        doc_text,
    )


def _assert_plain_admitted_document_text(text: str) -> None:
    stripped = str(text or "").lstrip()
    lower = stripped[:512].lower()
    if lower.startswith("<!doctype html") or lower.startswith("<html"):
        raise ValueError("sec_edgar_html_document_not_admitted")
    if lower.startswith("<?xml") or lower.startswith("<xbrl") or lower.startswith("<ix:"):
        raise ValueError("sec_edgar_xml_or_inline_xbrl_not_admitted")


def _split_sections(text: str, *, document_index: int, form_type: str) -> list[dict[str, Any]]:
    normalized = _normalize_text(_TABLE_RE.sub("", text))
    if not normalized:
        return []
    matches = list(_ITEM_RE.finditer(normalized))
    if not matches:
        return [
            {
                "unit_kind": "filing_section",
                "document_index": document_index,
                "section_index": 1,
                "section_label": "full_text",
                "form_type": form_type,
                "text": normalized,
                "start_char": 0,
                "end_char": len(normalized),
            }
        ]

    sections: list[dict[str, Any]] = []
    preamble = normalized[: matches[0].start()].strip()
    if preamble:
        sections.append(
            {
                "unit_kind": "filing_section",
                "document_index": document_index,
                "section_index": len(sections) + 1,
                "section_label": "preamble",
                "form_type": form_type,
                "text": preamble,
                "start_char": 0,
                "end_char": len(preamble),
            }
        )
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        section_text = normalized[start:end].strip()
        if not section_text:
            continue
        sections.append(
            {
                "unit_kind": "filing_section",
                "document_index": document_index,
                "section_index": len(sections) + 1,
                "section_label": match.group(1).strip().rstrip("."),
                "form_type": form_type,
                "text": section_text,
                "start_char": start,
                "end_char": end,
            }
        )
    return sections


def _parse_table_block(
    table_text: str,
    *,
    table_index: int,
    document_index: int,
    max_rows: int,
    max_columns: int,
) -> dict[str, Any]:
    normalized = "\n".join(line.strip() for line in str(table_text or "").splitlines() if line.strip())
    if not normalized:
        raise ValueError("sec_edgar_table_empty")
    try:
        parsed = nrc_aps_csv_parser.parse_csv_table(
            content=normalized.encode("utf-8"),
            max_rows=max_rows,
            max_columns=max_columns,
        )
    except ValueError as exc:
        raise ValueError(f"sec_edgar_table_parse_failed:{exc}") from exc
    table_unit = dict(parsed["table_units"][0])
    table_unit.update(
        {
            "table_index": table_index,
            "document_index": document_index,
            "table_source": "sec_edgar_table_block",
        }
    )
    return {
        "table_unit": table_unit,
        "time_series_units": [
            {
                **dict(unit),
                "table_index": table_index,
                "document_index": document_index,
                "table_source": "sec_edgar_table_block",
            }
            for unit in parsed["time_series_units"]
        ],
        "columns": parsed["columns"],
        "row_count": parsed["row_count"],
        "column_count": parsed["column_count"],
    }


def parse_sec_edgar_filing(
    *,
    content: bytes,
    max_bytes: int = 10_000_000,
    max_rows: int = 10_000,
    max_columns: int = 200,
    admitted_form_types: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    data = bytes(content or b"")
    if len(data) > int(max_bytes):
        raise ValueError("sec_edgar_size_limit_exceeded")
    text, encoding = _decode_filing_content(data)
    if not re.search(r"<SEC-DOCUMENT>|<SEC-HEADER>", text, re.IGNORECASE):
        raise ValueError("sec_edgar_signature_missing")

    header_tags = _tag_map(_header_text(text))
    form_type = (header_tags.get("CONFORMED-SUBMISSION-TYPE") or header_tags.get("TYPE") or "").strip().upper()
    admitted = tuple(str(item or "").strip().upper() for item in (admitted_form_types or _DEFAULT_ADMITTED_FORMS) if str(item or "").strip())
    if not form_type:
        raise ValueError("sec_edgar_form_type_missing")
    if admitted and form_type not in set(admitted):
        raise ValueError("sec_edgar_form_type_not_admitted")

    documents: list[dict[str, Any]] = []
    ordered_units: list[dict[str, Any]] = []
    table_units: list[dict[str, Any]] = []
    time_series_units: list[dict[str, Any]] = []
    table_diagnostics: list[dict[str, Any]] = []
    normalized_text_parts: list[str] = []

    document_matches = list(_DOCUMENT_RE.finditer(text))
    if not document_matches:
        raise ValueError("sec_edgar_document_blocks_missing")

    for document_index, match in enumerate(document_matches, start=1):
        metadata, document_text = _document_metadata(match.group("body"))
        if not document_text.strip():
            raise ValueError("sec_edgar_document_text_missing")
        _assert_plain_admitted_document_text(document_text)
        normalized_document_text = _normalize_text(_TABLE_RE.sub("", document_text))
        documents.append(
            {
                "document_index": document_index,
                **metadata,
                "text_char_count": len(normalized_document_text),
            }
        )
        if normalized_document_text:
            normalized_text_parts.append(normalized_document_text)
        for section in _split_sections(document_text, document_index=document_index, form_type=form_type):
            ordered_units.append(section)
        for table_match in _TABLE_RE.finditer(document_text):
            parsed_table = _parse_table_block(
                table_match.group("table"),
                table_index=len(table_units) + 1,
                document_index=document_index,
                max_rows=max_rows,
                max_columns=max_columns,
            )
            table_units.append(parsed_table["table_unit"])
            time_series_units.extend(parsed_table["time_series_units"])
            table_diagnostics.append(
                {
                    "table_index": parsed_table["table_unit"]["table_index"],
                    "document_index": document_index,
                    "row_count": parsed_table["row_count"],
                    "column_count": parsed_table["column_count"],
                    "columns": parsed_table["columns"],
                }
            )

    normalized_text = "\n\n".join(part for part in normalized_text_parts if part)
    if not normalized_text and not table_units:
        raise ValueError("sec_edgar_no_admitted_content")

    metadata = {
        "accession_number": header_tags.get("ACCESSION-NUMBER", ""),
        "form_type": form_type,
        "filed_as_of_date": header_tags.get("FILED-AS-OF-DATE", ""),
        "company_conformed_name": header_tags.get("COMPANY-CONFORMED-NAME", ""),
        "central_index_key": header_tags.get("CENTRAL-INDEX-KEY", ""),
        "public_document_count": header_tags.get("PUBLIC-DOCUMENT-COUNT", ""),
    }
    return {
        "sec_edgar_filing_contract_id": APS_SEC_EDGAR_FILING_CONTRACT_ID,
        "sec_edgar_parser_id": APS_SEC_EDGAR_PARSER_ID,
        "sec_edgar_parser_version": APS_SEC_EDGAR_PARSER_VERSION,
        "encoding": encoding,
        "filing_metadata": metadata,
        "document_count": len(documents),
        "documents": documents,
        "section_count": len(ordered_units),
        "table_count": len(table_units),
        "ordered_units": ordered_units,
        "table_units": table_units,
        "time_series_units": time_series_units,
        "table_diagnostics": table_diagnostics,
        "normalized_text": normalized_text,
    }
