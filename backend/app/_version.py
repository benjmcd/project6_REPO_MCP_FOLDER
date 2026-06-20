from __future__ import annotations

import os
import re


VERSION = "0.1.0-rc1"
UNKNOWN_SOURCE_SHA = "unknown"
_SOURCE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.IGNORECASE)


def _source_sha_from_env() -> str:
    for name in ("PROJECT6_SOURCE_SHA", "GITHUB_SHA"):
        value = os.environ.get(name, "").strip()
        if _SOURCE_SHA_PATTERN.fullmatch(value):
            return value.lower()
    return UNKNOWN_SOURCE_SHA


BUILD_INFO = {
    "version": VERSION,
    "source_sha": _source_sha_from_env(),
}
