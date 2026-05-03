from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import Any


APS_CSV_TABLE_CONTRACT_ID = "aps_csv_table_units_v1"
APS_CSV_PARSER_ID = "aps_csv_table_parser"
APS_CSV_PARSER_VERSION = "1.0.0"

_NULL_MARKERS = {"", "na", "n/a", "null", "none", "nan"}
_DELIMITERS = [",", ";", "\t", "|"]
_FORMULA_PREFIXES = ("=", "+", "@")


def _decode_csv_content(content: bytes) -> tuple[str, str]:
    data = bytes(content or b"")
    if not data:
        raise ValueError("csv_empty")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16"), "utf-16"
        except UnicodeDecodeError as exc:
            raise ValueError("csv_decode_failed") from exc
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError as exc:
        raise ValueError("csv_decode_failed") from exc


def _sniff_dialect(text: str) -> csv.Dialect:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(_DELIMITERS))
    except csv.Error as exc:
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        delimiter = max(_DELIMITERS, key=lambda item: first_line.count(item))
        if first_line.count(delimiter) <= 0:
            raise ValueError("csv_delimiter_not_detected") from exc

        class FallbackDialect(csv.excel):
            pass

        FallbackDialect.delimiter = delimiter
        return FallbackDialect
    if dialect.delimiter not in _DELIMITERS:
        raise ValueError("csv_delimiter_not_detected")
    return dialect


def _is_null(value: Any) -> bool:
    return str(value or "").strip().lower() in _NULL_MARKERS


def _is_number(value: str) -> bool:
    raw = str(value or "").strip().replace(",", "")
    if not raw:
        return False
    try:
        float(raw)
    except ValueError:
        return False
    return True


def _is_integer(value: str) -> bool:
    raw = str(value or "").strip().replace(",", "")
    if not raw:
        return False
    try:
        int(raw)
    except ValueError:
        return False
    return True


def _is_datetime(value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _is_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {"true", "false", "yes", "no"}


def _unsafe_formula_cell(value: str) -> bool:
    raw = str(value or "").lstrip()
    if not raw:
        return False
    if raw.startswith(_FORMULA_PREFIXES):
        return True
    if raw.startswith("-"):
        return len(raw) == 1 or not (raw[1].isdigit() or raw[1] == ".")
    return False


def _dedupe_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for index, header in enumerate(headers, start=1):
        base = str(header or "").strip() or f"column_{index}"
        key = base
        seen[key] = int(seen.get(key, 0)) + 1
        if seen[key] > 1:
            key = f"{base}_{seen[base]}"
        result.append(key)
    return result


def _looks_like_header(row: list[str], next_row: list[str]) -> bool:
    if not row or any(_is_null(value) for value in row):
        return False
    if len(set(str(value).strip() for value in row)) != len(row):
        return False
    headerish = sum(1 for value in row if not _is_number(value) and not _is_datetime(value))
    dataish = sum(1 for value in next_row if _is_number(value) or _is_datetime(value) or _is_bool(value))
    return headerish == len(row) or (headerish >= max(1, len(row) // 2) and dataish >= 1)


def _column_kind(values: list[str]) -> str:
    present = [value for value in values if not _is_null(value)]
    if not present:
        return "empty"
    if all(_is_integer(value) for value in present):
        return "integer"
    if all(_is_number(value) for value in present):
        return "number"
    if all(_is_datetime(value) for value in present):
        return "datetime"
    if all(_is_bool(value) for value in present):
        return "boolean"
    return "text"


def parse_csv_table(
    *,
    content: bytes,
    max_bytes: int = 5_000_000,
    max_rows: int = 10_000,
    max_columns: int = 200,
) -> dict[str, Any]:
    data = bytes(content or b"")
    if len(data) > int(max_bytes):
        raise ValueError("csv_size_limit_exceeded")
    text, encoding = _decode_csv_content(data)
    dialect = _sniff_dialect(text)
    try:
        rows = list(csv.reader(StringIO(text), dialect))
    except csv.Error as exc:
        raise ValueError("csv_parse_failed") from exc

    rows = [row for row in rows if any(str(cell or "").strip() for cell in row)]
    if not rows:
        raise ValueError("csv_empty")
    if len(rows) < 2:
        raise ValueError("csv_header_only")
    if len(rows) > int(max_rows) + 1:
        raise ValueError("csv_row_limit_exceeded")

    column_count = len(rows[0])
    if column_count < 2:
        raise ValueError("csv_column_count_unsupported")
    if column_count > int(max_columns):
        raise ValueError("csv_column_limit_exceeded")
    if any(len(row) != column_count for row in rows):
        raise ValueError("csv_ragged_rows")

    header_present = len(rows) > 1 and _looks_like_header(rows[0], rows[1])
    headers = _dedupe_headers(rows[0] if header_present else [f"column_{index}" for index in range(1, column_count + 1)])
    data_rows = rows[1:] if header_present else rows
    if not data_rows:
        raise ValueError("csv_header_only")

    for row in data_rows:
        for cell in row:
            if _unsafe_formula_cell(cell):
                raise ValueError("csv_formula_injection_risk")

    null_markers = sorted(
        {
            str(cell or "").strip()
            for row in data_rows
            for cell in row
            if _is_null(cell) and str(cell or "").strip()
        }
    )
    columns: list[dict[str, Any]] = []
    numeric_columns: list[str] = []
    time_column_candidates: list[str] = []
    for index, name in enumerate(headers):
        values = [row[index] for row in data_rows]
        kind = _column_kind(values)
        non_null_count = sum(1 for value in values if not _is_null(value))
        column = {
            "name": name,
            "ordinal": index + 1,
            "kind": kind,
            "non_null_count": non_null_count,
            "null_count": len(values) - non_null_count,
        }
        columns.append(column)
        if kind in {"integer", "number"}:
            numeric_columns.append(name)
        if kind == "datetime":
            time_column_candidates.append(name)

    row_units = [
        {
            "row_number": index,
            "source_row_number": index + (1 if header_present else 0),
            "values": {headers[col_index]: row[col_index] for col_index in range(column_count)},
            "raw_values": list(row),
        }
        for index, row in enumerate(data_rows, start=1)
    ]
    table_unit = {
        "unit_kind": "table",
        "table_index": 1,
        "row_count": len(data_rows),
        "column_count": column_count,
        "header_present": header_present,
        "columns": columns,
        "rows": row_units,
    }
    time_series_units = [
        {
            "unit_kind": "time_series_candidate",
            "table_index": 1,
            "time_column": column_name,
            "numeric_columns": numeric_columns,
            "row_count": len(data_rows),
        }
        for column_name in time_column_candidates
        if numeric_columns
    ]
    return {
        "csv_table_contract_id": APS_CSV_TABLE_CONTRACT_ID,
        "csv_parser_id": APS_CSV_PARSER_ID,
        "csv_parser_version": APS_CSV_PARSER_VERSION,
        "encoding": encoding,
        "delimiter": dialect.delimiter,
        "header_present": header_present,
        "row_count": len(data_rows),
        "column_count": column_count,
        "null_markers": null_markers,
        "columns": columns,
        "numeric_columns": numeric_columns,
        "time_column_candidates": time_column_candidates,
        "table_units": [table_unit],
        "time_series_units": time_series_units,
    }
