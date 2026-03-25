from __future__ import annotations

from typing import Any


APS_MEDIA_DETECTION_CONTRACT_ID = "aps_media_detection_v1"
APS_MEDIA_DETECTION_VERSION = "1.0.0"
APS_SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/zip",
    "image/jpeg",
    "image/png",
    "image/tiff",
}
APS_REFUSAL_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "text/html",
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
APS_MEDIA_DETECTION_STATUS_REFUSED = "refused_content_type"
APS_MEDIA_DETECTION_STATUS_UNKNOWN = "unknown_content_type"


def normalize_content_type(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if ";" in raw:
        raw = raw.split(";", 1)[0].strip()
    return raw


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


def resolve_effective_content_type(*, declared_content_type: Any, sniffed_content_type: Any) -> dict[str, Any]:
    declared = normalize_content_type(declared_content_type)
    sniffed = normalize_content_type(sniffed_content_type)

    if sniffed in APS_REFUSAL_CONTENT_TYPES:
        return {
            "declared_content_type": declared,
            "sniffed_content_type": sniffed,
            "effective_content_type": sniffed,
            "media_detection_status": APS_MEDIA_DETECTION_STATUS_REFUSED,
            "media_detection_reason": "sniffed_refusal_type",
            "supported_for_processing": False,
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
            }
        if declared in APS_GENERIC_CONTENT_TYPES:
            return {
                "declared_content_type": declared,
                "sniffed_content_type": sniffed,
                "effective_content_type": sniffed,
                "media_detection_status": APS_MEDIA_DETECTION_STATUS_SNIFFED,
                "media_detection_reason": "supported_type_sniffed_from_generic_or_missing_header",
                "supported_for_processing": True,
            }
        return {
            "declared_content_type": declared,
            "sniffed_content_type": sniffed,
            "effective_content_type": sniffed,
            "media_detection_status": APS_MEDIA_DETECTION_STATUS_MISMATCH,
            "media_detection_reason": "supported_type_mismatch",
            "supported_for_processing": True,
        }

    if declared in APS_SUPPORTED_CONTENT_TYPES:
        return {
            "declared_content_type": declared,
            "sniffed_content_type": sniffed,
            "effective_content_type": declared,
            "media_detection_status": APS_MEDIA_DETECTION_STATUS_DECLARED_ONLY,
            "media_detection_reason": "supported_declared_type_without_signature_match",
            "supported_for_processing": True,
        }

    return {
        "declared_content_type": declared,
        "sniffed_content_type": sniffed,
        "effective_content_type": sniffed or declared,
        "media_detection_status": APS_MEDIA_DETECTION_STATUS_UNKNOWN,
        "media_detection_reason": "unsupported_or_unknown_media_type",
        "supported_for_processing": False,
    }


def detect_media_type(content: bytes, *, declared_content_type: Any, sniff_bytes: int = 4096) -> dict[str, Any]:
    sniffed = sniff_content_type(content, sniff_bytes=sniff_bytes)
    resolved = resolve_effective_content_type(
        declared_content_type=declared_content_type,
        sniffed_content_type=sniffed.get("sniffed_content_type"),
    )
    return {
        "media_detection_contract_id": APS_MEDIA_DETECTION_CONTRACT_ID,
        "media_detection_version": APS_MEDIA_DETECTION_VERSION,
        **sniffed,
        **resolved,
    }
