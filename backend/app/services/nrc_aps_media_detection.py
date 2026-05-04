from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
import zipfile


APS_MEDIA_DETECTION_CONTRACT_ID = "aps_media_detection_v1"
APS_MEDIA_DETECTION_VERSION = "1.1.0"
APS_SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/csv",
    "application/csv",
    "text/plain",
    "application/zip",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/json",
}
APS_REFUSAL_CONTENT_TYPES = {
    "application/xml",
    "text/html",
}
APS_TYPED_UNADMITTED_CONTENT_TYPES = {
    "application/vnd.ms-excel",
    "application/vnd.ms-excel.sheet.macroenabled.12",
}
APS_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
}
APS_EXTENSION_CONTENT_TYPES = {
    ".csv": "text/csv",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroenabled.12",
    ".json": "application/json",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
}
APS_CONTENT_FAMILIES = {
    "application/pdf": "document",
    "text/plain": "qualitative_text",
    "application/zip": "archive",
    "image/jpeg": "image_ocr",
    "image/png": "image_ocr",
    "image/tiff": "image_ocr",
    "text/csv": "table",
    "application/csv": "table",
    "application/vnd.ms-excel": "spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "spreadsheet",
    "application/vnd.ms-excel.sheet.macroenabled.12": "spreadsheet",
    "application/json": "recordset",
    "application/xml": "structured_document",
    "text/html": "structured_document",
}
APS_GENERIC_CONTENT_TYPES = {
    "",
    "application/binary",
    "application/octet-stream",
    "binary/octet-stream",
}
APS_MEDIA_DETECTION_STATUS_MATCH = "declared_and_sniffed_match"
APS_MEDIA_DETECTION_STATUS_DECLARED_ONLY = "declared_only_supported_type"
APS_MEDIA_DETECTION_STATUS_SNIFFED = "sniffed_supported_type"
APS_MEDIA_DETECTION_STATUS_MISMATCH = "content_type_mismatch"
APS_MEDIA_DETECTION_STATUS_EXTENSION = "extension_supported_type"
APS_MEDIA_DETECTION_STATUS_REFUSED = "refused_content_type"
APS_MEDIA_DETECTION_STATUS_TYPED_UNADMITTED = "typed_content_type_not_admitted"
APS_MEDIA_DETECTION_STATUS_UNKNOWN = "unknown_content_type"


def normalize_content_type(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if ";" in raw:
        raw = raw.split(";", 1)[0].strip()
    return raw


def normalize_source_filename(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return Path(raw.replace("\\", "/")).name.strip()


def _extension_from_filename(value: Any) -> str:
    filename = normalize_source_filename(value)
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def _content_family(content_type: Any) -> str:
    return APS_CONTENT_FAMILIES.get(normalize_content_type(content_type), "unsupported")


def _zip_container_content_type(content: bytes) -> str:
    if not bytes(content or b"").startswith(b"PK\x03\x04"):
        return ""
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = {str(name or "").replace("\\", "/").lower() for name in archive.namelist()}
    except (OSError, zipfile.BadZipFile):
        return ""
    if "[content_types].xml" in names and "xl/vbaproject.bin" in names:
        return "application/vnd.ms-excel.sheet.macroenabled.12"
    if "[content_types].xml" in names and "xl/workbook.xml" in names:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return ""


def _decode_utf16_text(content: bytes) -> str | None:
    if content.startswith(b"\xff\xfe") or content.startswith(b"\xfe\xff"):
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
    return None


def _decode_utf8_text(content: bytes) -> str | None:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(1 for char in text if char.isprintable() or char in "\r\n\t")
    return printable / max(len(text), 1)


def is_probably_text_bytes(content: bytes) -> bool:
    sample = bytes(content or b"")[:4096]
    if not sample:
        return False
    if b"\x00" in sample and not (sample.startswith(b"\xff\xfe") or sample.startswith(b"\xfe\xff")):
        return False
    decoded = _decode_utf16_text(sample) or _decode_utf8_text(sample)
    if decoded is None:
        try:
            decoded = sample.decode("cp1252")
        except UnicodeDecodeError:
            return False
    return _printable_ratio(decoded) >= 0.85


def sniff_content_type(content: bytes, *, sniff_bytes: int = 4096) -> dict[str, Any]:
    sample = bytes(content or b"")[: max(int(sniff_bytes or 0), 0)]
    if not sample:
        return {
            "sniffed_content_type": "",
            "signature_basis": "empty_body",
            "confidence": "none",
        }

    stripped = sample.lstrip()
    lower = stripped.lower()

    if sample.startswith(b"%PDF-"):
        return {"sniffed_content_type": "application/pdf", "signature_basis": "pdf_header", "confidence": "high"}
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"sniffed_content_type": "image/png", "signature_basis": "png_signature", "confidence": "high"}
    if sample.startswith(b"\xff\xd8\xff"):
        return {"sniffed_content_type": "image/jpeg", "signature_basis": "jpeg_signature", "confidence": "high"}
    if sample.startswith((b"II*\x00", b"MM\x00*")):
        return {"sniffed_content_type": "image/tiff", "signature_basis": "tiff_signature", "confidence": "high"}
    if sample.startswith(b"PK\x03\x04"):
        container_type = _zip_container_content_type(content)
        if container_type:
            return {
                "sniffed_content_type": container_type,
                "signature_basis": "office_open_xml_package",
                "confidence": "high",
            }
        return {"sniffed_content_type": "application/zip", "signature_basis": "zip_signature", "confidence": "high"}
    if lower.startswith(b"<!doctype html") or lower.startswith(b"<html"):
        return {"sniffed_content_type": "text/html", "signature_basis": "html_signature", "confidence": "high"}
    if lower.startswith(b"<?xml") or (stripped.startswith(b"<") and lower.startswith((b"<feed", b"<rss", b"<xml"))):
        return {"sniffed_content_type": "application/xml", "signature_basis": "xml_signature", "confidence": "medium"}
    if stripped.startswith((b"{", b"[")):
        return {"sniffed_content_type": "application/json", "signature_basis": "json_signature", "confidence": "medium"}
    if is_probably_text_bytes(sample):
        return {"sniffed_content_type": "text/plain", "signature_basis": "text_heuristic", "confidence": "medium"}
    return {
        "sniffed_content_type": "",
        "signature_basis": "unknown_binary",
        "confidence": "none",
    }


def _compatible_types(declared_type: str, sniffed_type: str) -> bool:
    declared = normalize_content_type(declared_type)
    sniffed = normalize_content_type(sniffed_type)
    if declared == sniffed:
        return True
    if declared in APS_GENERIC_CONTENT_TYPES:
        return False
    if declared == "text/plain" and sniffed == "text/plain":
        return True
    return False


def _diagnostic_fields(*, source_filename: Any, declared: str, sniffed: str, effective: str) -> dict[str, Any]:
    filename = normalize_source_filename(source_filename)
    extension = _extension_from_filename(filename)
    extension_content_type = APS_EXTENSION_CONTENT_TYPES.get(extension, "")
    return {
        "source_filename": filename,
        "file_extension": extension,
        "extension_content_type": extension_content_type,
        "content_family": _content_family(effective or sniffed or declared or extension_content_type),
    }


def _typed_unadmitted_result(
    *,
    declared: str,
    sniffed: str,
    effective: str,
    reason: str,
    source_filename: Any,
) -> dict[str, Any]:
    return {
        "declared_content_type": declared,
        "sniffed_content_type": sniffed,
        "effective_content_type": effective,
        "media_detection_status": APS_MEDIA_DETECTION_STATUS_TYPED_UNADMITTED,
        "media_detection_reason": reason,
        "supported_for_processing": False,
        **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=effective),
    }


def _refused_result(*, declared: str, sniffed: str, effective: str, reason: str, source_filename: Any) -> dict[str, Any]:
    return {
        "declared_content_type": declared,
        "sniffed_content_type": sniffed,
        "effective_content_type": effective,
        "media_detection_status": APS_MEDIA_DETECTION_STATUS_REFUSED,
        "media_detection_reason": reason,
        "supported_for_processing": False,
        **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=effective),
    }


def resolve_effective_content_type(
    *,
    declared_content_type: Any,
    sniffed_content_type: Any,
    source_filename: Any = "",
) -> dict[str, Any]:
    declared = normalize_content_type(declared_content_type)
    sniffed = normalize_content_type(sniffed_content_type)
    extension = _extension_from_filename(source_filename)
    extension_content_type = APS_EXTENSION_CONTENT_TYPES.get(extension, "")

    if sniffed in APS_REFUSAL_CONTENT_TYPES:
        return _refused_result(
            declared=declared,
            sniffed=sniffed,
            effective=sniffed,
            reason="sniffed_refusal_type",
            source_filename=source_filename,
        )

    if extension_content_type in APS_REFUSAL_CONTENT_TYPES:
        return _refused_result(
            declared=declared,
            sniffed=sniffed,
            effective=extension_content_type,
            reason="extension_refusal_type",
            source_filename=source_filename,
        )

    if declared in APS_REFUSAL_CONTENT_TYPES:
        return _refused_result(
            declared=declared,
            sniffed=sniffed,
            effective=declared,
            reason="declared_refusal_type",
            source_filename=source_filename,
        )

    if sniffed in APS_TYPED_UNADMITTED_CONTENT_TYPES:
        return _typed_unadmitted_result(
            declared=declared,
            sniffed=sniffed,
            effective=sniffed,
            reason="sniffed_typed_parser_not_admitted",
            source_filename=source_filename,
        )

    if extension_content_type in APS_TYPED_UNADMITTED_CONTENT_TYPES:
        return _typed_unadmitted_result(
            declared=declared,
            sniffed=sniffed,
            effective=extension_content_type,
            reason="extension_typed_parser_not_admitted",
            source_filename=source_filename,
        )

    if declared in APS_TYPED_UNADMITTED_CONTENT_TYPES:
        return _typed_unadmitted_result(
            declared=declared,
            sniffed=sniffed,
            effective=declared,
            reason="declared_typed_parser_not_admitted",
            source_filename=source_filename,
        )

    if extension_content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" and sniffed in {"", "application/zip"}:
        if declared in APS_GENERIC_CONTENT_TYPES or declared in {"application/zip", extension_content_type}:
            return {
                "declared_content_type": declared,
                "sniffed_content_type": sniffed,
                "effective_content_type": extension_content_type,
                "media_detection_status": APS_MEDIA_DETECTION_STATUS_EXTENSION,
                "media_detection_reason": "xlsx_extension_admitted_before_generic_zip",
                "supported_for_processing": True,
                **_diagnostic_fields(
                    source_filename=source_filename,
                    declared=declared,
                    sniffed=sniffed,
                    effective=extension_content_type,
                ),
            }

    if extension_content_type in APS_CSV_CONTENT_TYPES and sniffed in {"", "text/plain"}:
        if declared in APS_GENERIC_CONTENT_TYPES or declared in APS_CSV_CONTENT_TYPES or declared == "text/plain":
            return {
                "declared_content_type": declared,
                "sniffed_content_type": sniffed,
                "effective_content_type": "text/csv",
                "media_detection_status": APS_MEDIA_DETECTION_STATUS_EXTENSION,
                "media_detection_reason": "csv_extension_admitted_with_text_signature",
                "supported_for_processing": True,
                **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective="text/csv"),
            }

    if declared in APS_CSV_CONTENT_TYPES and sniffed in {"", "text/plain"}:
        return {
            "declared_content_type": declared,
            "sniffed_content_type": sniffed,
            "effective_content_type": "text/csv",
            "media_detection_status": APS_MEDIA_DETECTION_STATUS_DECLARED_ONLY,
            "media_detection_reason": "csv_declared_type_admitted_with_text_signature",
            "supported_for_processing": True,
            **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective="text/csv"),
        }

    if sniffed in APS_SUPPORTED_CONTENT_TYPES:
        if _compatible_types(declared, sniffed):
            return {
                "declared_content_type": declared,
                "sniffed_content_type": sniffed,
                "effective_content_type": sniffed,
                "media_detection_status": APS_MEDIA_DETECTION_STATUS_MATCH,
                "media_detection_reason": "declared_matches_sniffed",
                "supported_for_processing": True,
                **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=sniffed),
            }
        if declared in APS_GENERIC_CONTENT_TYPES:
            return {
                "declared_content_type": declared,
                "sniffed_content_type": sniffed,
                "effective_content_type": sniffed,
                "media_detection_status": APS_MEDIA_DETECTION_STATUS_SNIFFED,
                "media_detection_reason": "supported_type_sniffed_from_generic_or_missing_header",
                "supported_for_processing": True,
                **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=sniffed),
            }
        return {
            "declared_content_type": declared,
            "sniffed_content_type": sniffed,
            "effective_content_type": sniffed,
            "media_detection_status": APS_MEDIA_DETECTION_STATUS_MISMATCH,
            "media_detection_reason": "supported_type_mismatch",
            "supported_for_processing": True,
            **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=sniffed),
        }

    if declared in APS_SUPPORTED_CONTENT_TYPES:
        return {
            "declared_content_type": declared,
            "sniffed_content_type": sniffed,
            "effective_content_type": declared,
            "media_detection_status": APS_MEDIA_DETECTION_STATUS_DECLARED_ONLY,
            "media_detection_reason": "supported_declared_type_without_signature_match",
            "supported_for_processing": True,
            **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=declared),
        }

    return {
        "declared_content_type": declared,
        "sniffed_content_type": sniffed,
        "effective_content_type": sniffed or declared,
        "media_detection_status": APS_MEDIA_DETECTION_STATUS_UNKNOWN,
        "media_detection_reason": "unsupported_or_unknown_media_type",
        "supported_for_processing": False,
        **_diagnostic_fields(source_filename=source_filename, declared=declared, sniffed=sniffed, effective=sniffed or declared),
    }


def detect_media_type(
    content: bytes,
    *,
    declared_content_type: Any,
    sniff_bytes: int = 4096,
    source_filename: Any = "",
) -> dict[str, Any]:
    sniffed = sniff_content_type(content, sniff_bytes=sniff_bytes)
    resolved = resolve_effective_content_type(
        declared_content_type=declared_content_type,
        sniffed_content_type=sniffed.get("sniffed_content_type"),
        source_filename=source_filename,
    )
    return {
        "media_detection_contract_id": APS_MEDIA_DETECTION_CONTRACT_ID,
        "media_detection_version": APS_MEDIA_DETECTION_VERSION,
        **sniffed,
        **resolved,
    }
