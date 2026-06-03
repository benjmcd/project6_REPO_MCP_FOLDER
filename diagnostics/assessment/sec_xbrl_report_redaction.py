from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


RESIDUAL_MAGNITUDE_KEYS = frozenset({"relative_magnitude", "residual_abs", "residual", "magnitude"})


def strip_residual_magnitude_fields(value: Any) -> Any:
    """Return a JSON-compatible clone with residual magnitude fields removed."""
    if isinstance(value, Mapping):
        return {
            str(key): strip_residual_magnitude_fields(item)
            for key, item in value.items()
            if str(key) not in RESIDUAL_MAGNITUDE_KEYS
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [strip_residual_magnitude_fields(item) for item in value]
    return value
