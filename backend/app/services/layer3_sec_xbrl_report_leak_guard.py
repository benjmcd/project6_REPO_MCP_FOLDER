from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from app.services.layer3_sec_xbrl_public_authority_guard import report_text_reference_flags


RAW_VALUE_KEY_RE = re.compile(r'"(?:_value|value|amount|effective_value|raw_value|lexical_value)"\s*:')


def report_leak_flags(value: Any, *, include_raw_value_keys: bool = False) -> dict[str, bool]:
    text = json.dumps(value, sort_keys=True)
    flags = report_text_reference_flags(text)
    if include_raw_value_keys:
        flags["raw_value_key_found"] = bool(RAW_VALUE_KEY_RE.search(text))
    return flags


def reject_report_leaks(
    value: Any,
    *,
    exception_factory: Callable[[], Exception],
    include_raw_value_keys: bool = False,
) -> None:
    flags = report_leak_flags(value, include_raw_value_keys=include_raw_value_keys)
    if any(flags.values()):
        raise exception_factory()
