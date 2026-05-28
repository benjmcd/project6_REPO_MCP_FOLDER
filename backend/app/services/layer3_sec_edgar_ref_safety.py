from __future__ import annotations

import re
from typing import Any, Collection, Mapping

_URI_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://")
_SERVER_RECEIPT_REF_RE = re.compile(r"(?i)^sec-edgar-[a-z0-9-]+://[a-z0-9._:/-]+$")
_WINDOWS_DRIVE_RE = re.compile(r"(?i)(?:^|[\s\"'`=({\[])[a-z]:[\\/]")
_UNC_RE = re.compile(r"(?:^|[\s\"'`=({\[])(?:\\\\|//)[^\s]+")
_UNIX_ABSOLUTE_RE = re.compile(r"(?:^|[\s\"'`=({\[])/(?!/)[^\s]+")


def contains_forbidden_ref(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if _SERVER_RECEIPT_REF_RE.fullmatch(text):
        return False
    return bool(
        _URI_RE.search(text)
        or _WINDOWS_DRIVE_RE.search(text)
        or _UNC_RE.search(text)
        or _UNIX_ABSOLUTE_RE.search(text)
    )


def contains_forbidden_ref_tree(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(contains_forbidden_ref_tree(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_forbidden_ref_tree(item) for item in value)
    if isinstance(value, str):
        return contains_forbidden_ref(value)
    return False


def find_forbidden_ref_paths(
    value: Any,
    *,
    forbidden_keys: Collection[str],
    prefix: str = "",
) -> list[str]:
    found: list[str] = []
    forbidden_key_set = {str(key).lower() for key in forbidden_keys}
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in forbidden_key_set:
                found.append(child_path)
            found.extend(find_forbidden_ref_paths(nested, forbidden_keys=forbidden_key_set, prefix=child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(find_forbidden_ref_paths(nested, forbidden_keys=forbidden_key_set, prefix=f"{prefix}[{index}]"))
    elif isinstance(value, str) and contains_forbidden_ref(value):
        found.append(prefix or "request_body")
    return sorted(set(found))
