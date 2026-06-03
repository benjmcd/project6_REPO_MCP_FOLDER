from __future__ import annotations

import json
import re
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Mapping
from typing import Any

from app.services.layer3_sec_xbrl_canonical_concepts import report_redaction_scan_payload
from app.services.layer3_sec_xbrl_public_authority_guard import public_text_reference_detected
from app.services.layer3_sec_xbrl_public_authority_guard import report_text_reference_flags


RAW_VALUE_KEYS = ("_value", "value", "amount", "effective_value", "raw_value", "lexical_value")
DIAGNOSTIC_AUTHORITY_RAW_VALUE_KEYS = ("_value", "value", "effective_value", "amount")
DIAGNOSTIC_AUTHORITY_KEY_RE = re.compile(r'"(?:resolved_fact_id|fact_id_or_order_key)"\s*:', re.IGNORECASE)
DIAGNOSTIC_ISSUER_IDENTITY_TOKENS = ("issuer_ref", "issuer_hash", "issuer_name", "entity_name", "company_name")
DIAGNOSTIC_CANONICAL_ISSUER_IDENTITY_TOKENS = ("issuer_ref", "issuer_hash", "issuer_name")


def report_leak_flags(
    value: Any,
    *,
    include_raw_value_keys: bool = False,
    raw_value_keys: Iterable[str] = RAW_VALUE_KEYS,
    raw_value_key_ignore_case: bool = False,
) -> dict[str, bool]:
    text = json.dumps(value, sort_keys=True)
    flags = report_text_reference_flags(text)
    if include_raw_value_keys:
        flags["raw_value_key_found"] = raw_value_key_found(
            text,
            raw_value_keys=raw_value_keys,
            ignore_case=raw_value_key_ignore_case,
        )
    return flags


def report_text_leak_flags(
    text: str,
    *,
    include_raw_value_keys: bool = False,
    raw_value_keys: Iterable[str] = RAW_VALUE_KEYS,
    raw_value_key_ignore_case: bool = False,
) -> dict[str, bool]:
    flags = report_text_reference_flags(text)
    if include_raw_value_keys:
        flags["raw_value_key_found"] = raw_value_key_found(
            text,
            raw_value_keys=raw_value_keys,
            ignore_case=raw_value_key_ignore_case,
        )
    return flags


def report_public_text_reference_found(
    text: str,
    *,
    scan_raw_period_dates: bool = True,
) -> bool:
    return public_text_reference_detected(text, scan_raw_period_dates=scan_raw_period_dates)


def raw_value_key_found(
    text: str,
    *,
    raw_value_keys: Iterable[str] = RAW_VALUE_KEYS,
    ignore_case: bool = False,
) -> bool:
    key_pattern = "|".join(re.escape(key) for key in raw_value_keys)
    flags = re.IGNORECASE if ignore_case else 0
    return bool(re.search(rf'"(?:{key_pattern})"\s*:', text, flags))


def reject_report_public_text_references(
    text: str,
    *,
    exception_factory: Callable[[], Exception],
    scan_raw_period_dates: bool = True,
) -> None:
    if report_public_text_reference_found(text, scan_raw_period_dates=scan_raw_period_dates):
        raise exception_factory()



def diagnostic_authority_redaction_scan_payload(
    value: Any,
    *,
    raw_value_keys: Iterable[str] = DIAGNOSTIC_AUTHORITY_RAW_VALUE_KEYS,
    raw_authority_key_pattern: re.Pattern[str] = DIAGNOSTIC_AUTHORITY_KEY_RE,
    issuer_identity_tokens: Iterable[str] = DIAGNOSTIC_ISSUER_IDENTITY_TOKENS,
) -> dict[str, bool]:
    base = report_redaction_scan_payload(value)
    text = json.dumps(value, sort_keys=True)
    raw_value_key_found = report_leak_flags(
        value,
        include_raw_value_keys=True,
        raw_value_keys=raw_value_keys,
        raw_value_key_ignore_case=True,
    )["raw_value_key_found"]
    raw_authority_key_found = bool(raw_authority_key_pattern.search(text))
    issuer_identity_found = any(token in text for token in issuer_identity_tokens)
    return {
        **base,
        "raw_value_key_found": raw_value_key_found,
        "raw_resolved_fact_authority_key_found": raw_authority_key_found,
        "raw_issuer_identity_found": issuer_identity_found,
        "passed": base["passed"]
        and not raw_value_key_found
        and not raw_authority_key_found
        and not issuer_identity_found,
    }


def diagnostic_resolved_fact_redaction_scan_payload(
    value: Any,
    *,
    raw_resolved_fact_id_pattern: re.Pattern[str],
    issuer_identity_tokens: Iterable[str] = DIAGNOSTIC_CANONICAL_ISSUER_IDENTITY_TOKENS,
    extra_patterns: Mapping[str, re.Pattern[str]] | None = None,
) -> dict[str, bool]:
    text = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    base = report_redaction_scan_payload(value)
    extra_flags = {
        key: bool(pattern.search(text))
        for key, pattern in dict(extra_patterns or {}).items()
    }
    raw_resolved_fact_ids_found = bool(raw_resolved_fact_id_pattern.search(text))
    raw_issuer_identity_found = any(token in text for token in issuer_identity_tokens)
    return {
        **base,
        "raw_resolved_fact_ids_found": raw_resolved_fact_ids_found,
        "raw_issuer_identity_found": raw_issuer_identity_found,
        **extra_flags,
        "passed": (
            base.get("passed") is True
            and not raw_resolved_fact_ids_found
            and not raw_issuer_identity_found
            and not any(extra_flags.values())
        ),
    }


def reject_report_leaks(
    value: Any,
    *,
    exception_factory: Callable[[], Exception],
    include_raw_value_keys: bool = False,
) -> None:
    flags = report_leak_flags(value, include_raw_value_keys=include_raw_value_keys)
    if any(flags.values()):
        raise exception_factory()
