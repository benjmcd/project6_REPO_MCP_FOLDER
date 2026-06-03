from __future__ import annotations

import json
import re
from collections.abc import Callable
from collections.abc import Iterable
from typing import Any

from app.services.layer3_sec_xbrl_canonical_concepts import report_redaction_scan_payload
from app.services.layer3_sec_xbrl_public_authority_guard import report_text_reference_flags


RAW_VALUE_KEYS = ("_value", "value", "amount", "effective_value", "raw_value", "lexical_value")
DIAGNOSTIC_AUTHORITY_RAW_VALUE_KEYS = ("_value", "value", "effective_value", "amount")
DIAGNOSTIC_AUTHORITY_KEY_RE = re.compile(r'"(?:resolved_fact_id|fact_id_or_order_key)"\s*:', re.IGNORECASE)
DIAGNOSTIC_ISSUER_IDENTITY_TOKENS = ("issuer_ref", "issuer_hash", "issuer_name", "entity_name", "company_name")


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


def raw_value_key_found(
    text: str,
    *,
    raw_value_keys: Iterable[str] = RAW_VALUE_KEYS,
    ignore_case: bool = False,
) -> bool:
    key_pattern = "|".join(re.escape(key) for key in raw_value_keys)
    flags = re.IGNORECASE if ignore_case else 0
    return bool(re.search(rf'"(?:{key_pattern})"\s*:', text, flags))



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


def reject_report_leaks(
    value: Any,
    *,
    exception_factory: Callable[[], Exception],
    include_raw_value_keys: bool = False,
) -> None:
    flags = report_leak_flags(value, include_raw_value_keys=include_raw_value_keys)
    if any(flags.values()):
        raise exception_factory()
