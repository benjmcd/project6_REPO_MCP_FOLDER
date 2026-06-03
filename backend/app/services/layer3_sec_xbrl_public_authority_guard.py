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
BARE_SEC_DOMAIN_RE = re.compile(r"(?:https?://)?(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
WINDOWS_ABS_PATH_ANYWHERE_RE = re.compile(r"[A-Za-z]:[\\/]")
LOCAL_REF_RE = re.compile(
    r"(?i)(?:"
    r"file://"
    r"|\\\\[^\\/]+[\\/]"
    r"|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$)"
    r")"
)
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
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
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


def blocked_authority_keys(
    value: Mapping[str, Any],
    *,
    raw_value_keys: set[str] | frozenset[str] = RAW_VALUE_KEYS,
    raw_authority_keys: set[str] | frozenset[str] = RAW_AUTHORITY_KEYS,
) -> list[str]:
    lower_keys = {str(key).lower() for key in value}
    return sorted((lower_keys & set(raw_value_keys)) | (lower_keys & set(raw_authority_keys)))


def unadmitted_keys(value: Mapping[str, Any], *, admitted: set[str]) -> list[str]:
    return sorted(str(key) for key in value if str(key) not in admitted)
