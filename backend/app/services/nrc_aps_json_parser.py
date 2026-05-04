from __future__ import annotations

import json
from datetime import datetime
from typing import Any


APS_JSON_RECORDSET_CONTRACT_ID = "aps_json_recordset_units_v1"
APS_JSON_PARSER_ID = "aps_json_recordset_parser"
APS_JSON_PARSER_VERSION = "1.0.0"

_NULL_MARKERS = {"", "na", "n/a", "null", "none", "nan"}


def _decode_json_content(content: bytes) -> str:
    data = bytes(content or b"")
    if not data:
        raise ValueError("json_empty")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("json_decode_failed") from exc


def _path_parts(record_path: str | None) -> list[str]:
    raw = str(record_path or "").strip()
    if not raw or raw == "$":
        return []
    if raw.startswith("$."):
        raw = raw[2:]
    if raw.startswith(".") or raw.endswith(".") or "[" in raw or "]" in raw:
        raise ValueError("json_record_path_unsupported")
    parts = [part.strip() for part in raw.split(".") if part.strip()]
    if not parts:
        raise ValueError("json_record_path_unsupported")
    return parts


def _get_path(root: Any, record_path: str | None) -> tuple[Any, str]:
    parts = _path_parts(record_path)
    current = root
    for part in parts:
        if not isinstance(current, dict):
            raise ValueError("json_record_path_not_object")
        if part not in current:
            raise ValueError("json_record_path_missing")
        current = current[part]
    return current, "$" if not parts else "$." + ".".join(parts)


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and value.strip().lower() in _NULL_MARKERS


def _is_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    raw = value.strip()
    if not raw:
        return False
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _scalar_kind(value: Any) -> str:
    if _is_null(value):
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if _is_datetime(value):
        return "datetime"
    if isinstance(value, str):
        return "text"
    raise ValueError("json_nested_value_not_admitted")


def _column_kind(values: list[Any]) -> str:
    present = [value for value in values if not _is_null(value)]
    if not present:
        return "empty"
    kinds = {_scalar_kind(value) for value in present}
    if kinds == {"integer"}:
        return "integer"
    if kinds <= {"integer", "number"}:
        return "number"
    if kinds == {"datetime"}:
        return "datetime"
    if kinds == {"boolean"}:
        return "boolean"
    if kinds == {"text"}:
        return "text"
    return "text"


def _validate_records(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError("json_recordset_not_array")
    if not records:
        raise ValueError("json_recordset_empty")
    normalized: list[dict[str, Any]] = []
    expected_keys: tuple[str, ...] | None = None
    expected_key_set: set[str] | None = None
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("json_recordset_item_not_object")
        if not item:
            raise ValueError("json_recordset_empty_object")
        keys = tuple(str(key) for key in item.keys())
        if expected_keys is None:
            expected_keys = keys
            expected_key_set = set(keys)
        elif set(keys) != expected_key_set:
            raise ValueError("json_recordset_heterogeneous_keys")
        row: dict[str, Any] = {}
        for key in expected_keys:
            value = item[key]
            _scalar_kind(value)
            row[str(key)] = value
        normalized.append(row)
    return normalized


def parse_json_recordset(
    *,
    content: bytes,
    max_bytes: int = 5_000_000,
    max_rows: int = 10_000,
    max_columns: int = 200,
    record_path: str | None = None,
) -> dict[str, Any]:
    data = bytes(content or b"")
    if len(data) > int(max_bytes):
        raise ValueError("json_size_limit_exceeded")
    text = _decode_json_content(data)
    try:
        root = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("json_parse_failed") from exc

    records_node, resolved_path = _get_path(root, record_path)
    if isinstance(root, dict) and not record_path:
        raise ValueError("json_record_path_required_for_object_root")
    records = _validate_records(records_node)
    if len(records) > int(max_rows):
        raise ValueError("json_row_limit_exceeded")

    columns = list(records[0].keys())
    if len(columns) < 1:
        raise ValueError("json_column_count_unsupported")
    if len(columns) > int(max_columns):
        raise ValueError("json_column_limit_exceeded")

    column_units: list[dict[str, Any]] = []
    numeric_columns: list[str] = []
    time_column_candidates: list[str] = []
    for index, name in enumerate(columns, start=1):
        values = [row.get(name) for row in records]
        kind = _column_kind(values)
        non_null_count = sum(1 for value in values if not _is_null(value))
        column = {
            "name": name,
            "field_path": f"{resolved_path}[*].{name}",
            "ordinal": index,
            "kind": kind,
            "non_null_count": non_null_count,
            "null_count": len(values) - non_null_count,
            "missing_count": 0,
        }
        column_units.append(column)
        if kind in {"integer", "number"}:
            numeric_columns.append(name)
        if kind == "datetime":
            time_column_candidates.append(name)

    row_units = [
        {
            "row_number": index,
            "source_row_number": index,
            "record_path": f"{resolved_path}[{index - 1}]",
            "values": dict(row),
            "raw_values": [row.get(name) for name in columns],
        }
        for index, row in enumerate(records, start=1)
    ]
    table_unit = {
        "unit_kind": "table",
        "table_index": 1,
        "record_path": resolved_path,
        "row_count": len(records),
        "column_count": len(columns),
        "header_present": True,
        "columns": column_units,
        "rows": row_units,
    }
    time_series_units = [
        {
            "unit_kind": "time_series_candidate",
            "table_index": 1,
            "time_column": column_name,
            "numeric_columns": numeric_columns,
            "row_count": len(records),
        }
        for column_name in time_column_candidates
        if numeric_columns
    ]
    return {
        "json_recordset_contract_id": APS_JSON_RECORDSET_CONTRACT_ID,
        "json_parser_id": APS_JSON_PARSER_ID,
        "json_parser_version": APS_JSON_PARSER_VERSION,
        "record_path": resolved_path,
        "row_count": len(records),
        "column_count": len(columns),
        "columns": column_units,
        "numeric_columns": numeric_columns,
        "time_column_candidates": time_column_candidates,
        "table_units": [table_unit],
        "time_series_units": time_series_units,
    }
