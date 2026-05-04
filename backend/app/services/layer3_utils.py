from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def stable_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def json_clone(value: Any) -> Any:
    return json.loads(stable_json_bytes(value).decode("utf-8"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(stable_json_bytes(value)).hexdigest()


def stable_id(prefix: str, value: Any, *, digest_chars: int = 16) -> str:
    return f"{prefix}-{stable_hash(value)[:digest_chars]}"


def utcnow_iso_z() -> str:
    return utcnow().isoformat().replace("+00:00", "Z")


def epoch_seconds_iso_z(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def stable_json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def stable_json_text_bytes(value: Any) -> bytes:
    return stable_json_text(value).encode("utf-8")


def json_text_clone(value: Any) -> Any:
    return json.loads(stable_json_text(value))


def stable_json_text_hash(value: Any) -> str:
    return hashlib.sha256(stable_json_text_bytes(value)).hexdigest()
