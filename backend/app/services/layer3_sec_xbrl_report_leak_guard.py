from __future__ import annotations

import json
import re
from collections.abc import Callable
from collections.abc import Iterable
from typing import Any

from app.services.layer3_sec_xbrl_public_authority_guard import report_text_reference_flags


RAW_VALUE_KEYS = ("_value", "value", "amount", "effective_value", "raw_value", "lexical_value")


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


def reject_report_leaks(
    value: Any,
    *,
    exception_factory: Callable[[], Exception],
    include_raw_value_keys: bool = False,
) -> None:
    flags = report_leak_flags(value, include_raw_value_keys=include_raw_value_keys)
    if any(flags.values()):
        raise exception_factory()
