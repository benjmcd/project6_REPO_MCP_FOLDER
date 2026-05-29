from __future__ import annotations

import re


_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def is_storage_id(value: str, *, prefix: str) -> bool:
    text = str(value or "").strip()
    if not text or not text.startswith(f"{prefix}-"):
        return False
    suffix = text[len(prefix) + 1 :]
    if not suffix or suffix in {".", ".."} or text in {".", ".."}:
        return False
    if "/" in text or "\\" in text or ".." in text or ":" in text:
        return False
    if text.startswith(("/", "\\")) or _WINDOWS_DRIVE_RE.match(text) or _WINDOWS_DRIVE_RE.match(suffix):
        return False
    return True
