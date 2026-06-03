from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


RAW_VALUE_KEYS = frozenset({"_value", "value", "effective_value", "amount", "lexical_value"})
RAW_AUTHORITY_KEYS = frozenset(
    {
        "resolved_fact_id",
        "resolved_fact_ids",
        "derived_from_resolved_fact_ids",
        "raw_resolved_fact_authority",
        "raw_resolved_fact_authorities",
        "cik",
        "cik_or_filer_ref",
        "filer_or_cik",
        "accession",
        "accession_number",
        "company_name",
        "issuer_name",
        "registrant",
        "registrant_name",
        "ticker",
        "contact",
        "user_agent",
        "local_path",
        "raw_path",
        "storage_dir",
        "storage_root",
        "sec_url",
    }
)

ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
ANY_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*:" + "/" + "/")
BARE_SEC_DOMAIN_RE = re.compile(r"(?:https?://)?(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
WINDOWS_ABS_PATH_START_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_ABS_PATH_ANYWHERE_RE = re.compile(r"[A-Za-z]:[\\/]")
LOCAL_REF_RE = re.compile(
    r"(?i)(?:"
    r"file://"
    r"|\\\\[^\\/]+[\\/]"
    r"|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$)"
    r")"
)
REPORT_LOCAL_PATH_RE = re.compile(r"[A-Za-z]:[\\/]|\\\\|file://|/(?:Users|home|tmp|workspace|var|mnt|private)(?:/|$)")
LOCAL_REF_SEGMENT_RE = re.compile(r"(^|[\\/])(?:workspace|tmp|temp|users|home)[\\/]", re.IGNORECASE)
RAW_PERIOD_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
CIK_RE = re.compile(r"\b\d{10}\b")
OPERATOR_CONTACT_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


@dataclass(frozen=True)
class PublicAuthorityGuardViolation:
    kind: str
    field: str | None = None


def raw_or_local_authority_violation(
    value: Any,
    *,
    raw_value_keys: set[str] | frozenset[str] = RAW_VALUE_KEYS,
    raw_authority_keys: set[str] | frozenset[str] = RAW_AUTHORITY_KEYS,
    residual_magnitude_keys: set[str] | frozenset[str] = frozenset(),
    scan_raw_period_dates: bool = True,
    scan_cik: bool = False,
    scan_cik_fullmatch: bool = False,
    scan_operator_contact: bool = False,
    scan_bare_sec_domain: bool = False,
    scan_standard_local_refs: bool = True,
    scan_windows_abs_path_anywhere: bool = False,
    scan_local_ref_segment: bool = False,
) -> PublicAuthorityGuardViolation | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_match = key_text.strip().lower()
            if key_match in raw_value_keys or key_match in raw_authority_keys:
                if item is not None:
                    return PublicAuthorityGuardViolation("raw_authority", key_text)
            if key_match in residual_magnitude_keys and item is not None:
                return PublicAuthorityGuardViolation("residual_magnitude", key_text)
            nested = raw_or_local_authority_violation(
                item,
                raw_value_keys=raw_value_keys,
                raw_authority_keys=raw_authority_keys,
                residual_magnitude_keys=residual_magnitude_keys,
                scan_raw_period_dates=scan_raw_period_dates,
                scan_cik=scan_cik,
                scan_cik_fullmatch=scan_cik_fullmatch,
                scan_operator_contact=scan_operator_contact,
                scan_bare_sec_domain=scan_bare_sec_domain,
                scan_standard_local_refs=scan_standard_local_refs,
                scan_windows_abs_path_anywhere=scan_windows_abs_path_anywhere,
                scan_local_ref_segment=scan_local_ref_segment,
            )
            if nested is not None:
                return nested
        return None
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
    ) or isinstance(value, set):
        for item in value:
            nested = raw_or_local_authority_violation(
                item,
                raw_value_keys=raw_value_keys,
                raw_authority_keys=raw_authority_keys,
                residual_magnitude_keys=residual_magnitude_keys,
                scan_raw_period_dates=scan_raw_period_dates,
                scan_cik=scan_cik,
                scan_cik_fullmatch=scan_cik_fullmatch,
                scan_operator_contact=scan_operator_contact,
                scan_bare_sec_domain=scan_bare_sec_domain,
                scan_standard_local_refs=scan_standard_local_refs,
                scan_windows_abs_path_anywhere=scan_windows_abs_path_anywhere,
                scan_local_ref_segment=scan_local_ref_segment,
            )
            if nested is not None:
                return nested
        return None
    if not isinstance(value, str):
        return None
    if public_text_reference_detected(
        value,
        scan_raw_period_dates=scan_raw_period_dates,
        scan_cik=scan_cik,
        scan_cik_fullmatch=scan_cik_fullmatch,
        scan_operator_contact=scan_operator_contact,
        scan_bare_sec_domain=scan_bare_sec_domain,
        scan_standard_local_refs=scan_standard_local_refs,
        scan_windows_abs_path_anywhere=scan_windows_abs_path_anywhere,
        scan_local_ref_segment=scan_local_ref_segment,
    ):
        return PublicAuthorityGuardViolation("raw_reference")
    return None


def public_text_reference_detected(
    value: str,
    *,
    scan_raw_period_dates: bool = True,
    scan_cik: bool = False,
    scan_cik_fullmatch: bool = False,
    scan_operator_contact: bool = False,
    scan_bare_sec_domain: bool = False,
    scan_standard_local_refs: bool = True,
    scan_windows_abs_path_anywhere: bool = False,
    scan_local_ref_segment: bool = False,
) -> bool:
    text = str(value or "").strip()
    return bool(
        ACCESSION_RE.search(text)
        or SEC_URL_RE.search(text)
        or (scan_bare_sec_domain and BARE_SEC_DOMAIN_RE.search(text))
        or WINDOWS_ABS_PATH_RE.search(text)
        or (scan_windows_abs_path_anywhere and WINDOWS_ABS_PATH_ANYWHERE_RE.search(text))
        or (scan_standard_local_refs and LOCAL_REF_RE.search(text))
        or (scan_local_ref_segment and LOCAL_REF_SEGMENT_RE.search(text))
        or (scan_raw_period_dates and RAW_PERIOD_DATE_RE.search(text))
        or (scan_cik and CIK_RE.search(text))
        or (scan_cik_fullmatch and CIK_RE.fullmatch(text))
        or (scan_operator_contact and OPERATOR_CONTACT_RE.search(text))
    )


def raw_accession_reference_found(value: str) -> bool:
    return bool(ACCESSION_RE.search(str(value or "")))


def sec_url_reference_found(value: str) -> bool:
    return bool(SEC_URL_RE.search(str(value or "")))


def any_url_reference_found(value: str) -> bool:
    return bool(ANY_URL_RE.search(str(value or "")))


def report_local_path_reference_found(value: str) -> bool:
    return bool(REPORT_LOCAL_PATH_RE.search(str(value or "")))


def windows_local_path_reference_found(value: str) -> bool:
    return bool(WINDOWS_ABS_PATH_ANYWHERE_RE.search(str(value or "")))


def windows_local_path_start_reference_found(value: str) -> bool:
    return bool(WINDOWS_ABS_PATH_START_RE.search(str(value or "")))


def report_text_reference_flags(value: str) -> dict[str, bool]:
    return {
        "raw_accession_found": raw_accession_reference_found(value),
        "sec_url_found": sec_url_reference_found(value),
        "local_path_found": report_local_path_reference_found(value),
    }


def blocked_authority_keys(
    value: Mapping[str, Any],
    *,
    raw_value_keys: set[str] | frozenset[str] = RAW_VALUE_KEYS,
    raw_authority_keys: set[str] | frozenset[str] = RAW_AUTHORITY_KEYS,
) -> list[str]:
    lower_keys = {str(key).lower() for key in value}
    return sorted((lower_keys & set(raw_value_keys)) | (lower_keys & set(raw_authority_keys)))


def blocked_authority_keys_violation(
    value: Any,
    *,
    raw_value_keys: set[str] | frozenset[str] = RAW_VALUE_KEYS,
    raw_authority_keys: set[str] | frozenset[str] = RAW_AUTHORITY_KEYS,
) -> list[str] | None:
    if isinstance(value, Mapping):
        blocked_keys = blocked_authority_keys(
            value,
            raw_value_keys=raw_value_keys,
            raw_authority_keys=raw_authority_keys,
        )
        if blocked_keys:
            return blocked_keys
        children = value.values()
    elif (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
    ) or isinstance(value, set):
        children = value
    else:
        return None

    for item in children:
        blocked_keys = blocked_authority_keys_violation(
            item,
            raw_value_keys=raw_value_keys,
            raw_authority_keys=raw_authority_keys,
        )
        if blocked_keys:
            return blocked_keys
    return None


def reject_raw_or_local_authority_with_blocked_keys(
    value: Any,
    *,
    error_type: type[Exception],
    raw_authority_code: str,
    raw_authority_message: str,
    raw_reference_code: str,
    raw_reference_message: str,
    blocked_raw_value_keys: set[str] | frozenset[str] = RAW_VALUE_KEYS,
    blocked_raw_authority_keys: set[str] | frozenset[str] = RAW_AUTHORITY_KEYS,
    reference_raw_value_keys: set[str] | frozenset[str] = frozenset(),
    reference_raw_authority_keys: set[str] | frozenset[str] = frozenset(),
    scan_raw_period_dates: bool = True,
    scan_cik: bool = False,
    scan_cik_fullmatch: bool = False,
    scan_operator_contact: bool = False,
    raw_authority_http_status: int = 400,
    raw_reference_http_status: int = 400,
) -> None:
    blocked_keys = blocked_authority_keys_violation(
        value,
        raw_value_keys=blocked_raw_value_keys,
        raw_authority_keys=blocked_raw_authority_keys,
    )
    if blocked_keys:
        raise error_type(
            raw_authority_code,
            raw_authority_message,
            details={"blocked_keys": blocked_keys},
            http_status=raw_authority_http_status,
        )
    if raw_or_local_authority_violation(
        value,
        raw_value_keys=reference_raw_value_keys,
        raw_authority_keys=reference_raw_authority_keys,
        scan_raw_period_dates=scan_raw_period_dates,
        scan_cik=scan_cik,
        scan_cik_fullmatch=scan_cik_fullmatch,
        scan_operator_contact=scan_operator_contact,
    ):
        raise error_type(
            raw_reference_code,
            raw_reference_message,
            http_status=raw_reference_http_status,
        )


def reject_public_text_references(
    value: Any,
    *,
    error_type: type[Exception],
    raw_reference_code: str,
    raw_reference_message: str,
    field: str,
    scan_raw_period_dates: bool = True,
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            reject_public_text_references(
                item,
                error_type=error_type,
                raw_reference_code=raw_reference_code,
                raw_reference_message=raw_reference_message,
                field=str(key),
                scan_raw_period_dates=scan_raw_period_dates,
            )
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            reject_public_text_references(
                item,
                error_type=error_type,
                raw_reference_code=raw_reference_code,
                raw_reference_message=raw_reference_message,
                field=field,
                scan_raw_period_dates=scan_raw_period_dates,
            )
        return
    if not isinstance(value, str):
        return
    if public_text_reference_detected(value, scan_raw_period_dates=scan_raw_period_dates):
        raise error_type(
            raw_reference_code,
            raw_reference_message,
            details={"field": field},
        )


def reject_public_output_policy(
    value: Any,
    *,
    error_type: type[Exception],
    raw_output_code: str,
    raw_output_message: str,
    raw_reference_code: str,
    raw_reference_message: str,
    raw_output_keys: set[str] | frozenset[str],
    residual_magnitude_keys: set[str] | frozenset[str] = frozenset(),
    residual_magnitude_code: str | None = None,
    residual_magnitude_message: str | None = None,
    scan_raw_period_dates: bool = True,
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_match = key_text.strip().lower()
            if key_match in residual_magnitude_keys:
                raise error_type(
                    residual_magnitude_code or raw_output_code,
                    residual_magnitude_message or raw_output_message,
                    details={"field": key_text},
                )
            if key_match in raw_output_keys and item is not None:
                raise error_type(
                    raw_output_code,
                    raw_output_message,
                    details={"field": key_text},
                )
            reject_public_output_policy(
                item,
                error_type=error_type,
                raw_output_code=raw_output_code,
                raw_output_message=raw_output_message,
                raw_reference_code=raw_reference_code,
                raw_reference_message=raw_reference_message,
                raw_output_keys=raw_output_keys,
                residual_magnitude_keys=residual_magnitude_keys,
                residual_magnitude_code=residual_magnitude_code,
                residual_magnitude_message=residual_magnitude_message,
                scan_raw_period_dates=scan_raw_period_dates,
            )
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            reject_public_output_policy(
                item,
                error_type=error_type,
                raw_output_code=raw_output_code,
                raw_output_message=raw_output_message,
                raw_reference_code=raw_reference_code,
                raw_reference_message=raw_reference_message,
                raw_output_keys=raw_output_keys,
                residual_magnitude_keys=residual_magnitude_keys,
                residual_magnitude_code=residual_magnitude_code,
                residual_magnitude_message=residual_magnitude_message,
                scan_raw_period_dates=scan_raw_period_dates,
            )
        return
    reject_public_text_references(
        value,
        error_type=error_type,
        raw_reference_code=raw_reference_code,
        raw_reference_message=raw_reference_message,
        field="value",
        scan_raw_period_dates=scan_raw_period_dates,
    )


def reject_raw_or_local_authority(
    value: Any,
    *,
    error_type: type[Exception],
    raw_authority_code: str,
    raw_authority_message: str,
    raw_reference_code: str,
    raw_reference_message: str,
    residual_magnitude_code: str | None = None,
    residual_magnitude_message: str | None = None,
    raw_value_keys: set[str] | frozenset[str] = RAW_VALUE_KEYS,
    raw_authority_keys: set[str] | frozenset[str] = RAW_AUTHORITY_KEYS,
    residual_magnitude_keys: set[str] | frozenset[str] = frozenset(),
    scan_raw_period_dates: bool = True,
    scan_cik: bool = False,
    scan_cik_fullmatch: bool = False,
    scan_operator_contact: bool = False,
    scan_bare_sec_domain: bool = False,
    scan_standard_local_refs: bool = True,
    scan_windows_abs_path_anywhere: bool = False,
    scan_local_ref_segment: bool = False,
) -> None:
    violation = raw_or_local_authority_violation(
        value,
        raw_value_keys=raw_value_keys,
        raw_authority_keys=raw_authority_keys,
        residual_magnitude_keys=residual_magnitude_keys,
        scan_raw_period_dates=scan_raw_period_dates,
        scan_cik=scan_cik,
        scan_cik_fullmatch=scan_cik_fullmatch,
        scan_operator_contact=scan_operator_contact,
        scan_bare_sec_domain=scan_bare_sec_domain,
        scan_standard_local_refs=scan_standard_local_refs,
        scan_windows_abs_path_anywhere=scan_windows_abs_path_anywhere,
        scan_local_ref_segment=scan_local_ref_segment,
    )
    if violation is None:
        return
    if violation.kind == "raw_authority":
        raise error_type(
            raw_authority_code,
            raw_authority_message,
            details={"field": str(violation.field or "")},
        )
    if violation.kind == "residual_magnitude":
        raise error_type(
            residual_magnitude_code or raw_authority_code,
            residual_magnitude_message or raw_authority_message,
            details={"field": str(violation.field or "")},
        )
    raise error_type(raw_reference_code, raw_reference_message)


def unadmitted_keys(value: Mapping[str, Any], *, admitted: set[str]) -> list[str]:
    return sorted(str(key) for key in value if str(key) not in admitted)
