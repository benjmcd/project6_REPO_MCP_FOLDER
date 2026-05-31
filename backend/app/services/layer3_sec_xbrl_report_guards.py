from __future__ import annotations

from typing import Any, Mapping, Sequence


def rows_have_unique_required_key(
    rows: Sequence[Mapping[str, Any]],
    *,
    key_field: str,
    expected_count: int | None = None,
    expected_values: set[str] | None = None,
) -> bool:
    values: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return False
        value = str(row.get(key_field) or "")
        if not value:
            return False
        values.append(value)

    if expected_count is not None and len(values) != expected_count:
        return False
    unique_values = set(values)
    if len(unique_values) != len(values):
        return False
    if expected_values is not None and unique_values != expected_values:
        return False
    return True
