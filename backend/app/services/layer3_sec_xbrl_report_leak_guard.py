from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any


ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:[\\/]|\\\\|file://|/(?:Users|home|tmp|workspace|var|mnt|private)(?:/|$)")
RAW_VALUE_KEY_RE = re.compile(r'"(?:effective_value|raw_value|lexical_value)"')


def report_leak_flags(value: Any, *, include_raw_value_keys: bool = False) -> dict[str, bool]:
    text = json.dumps(value, sort_keys=True)
    flags = {
        "raw_accession_found": bool(ACCESSION_RE.search(text)),
        "sec_url_found": bool(SEC_URL_RE.search(text)),
        "local_path_found": bool(LOCAL_PATH_RE.search(text)),
    }
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
