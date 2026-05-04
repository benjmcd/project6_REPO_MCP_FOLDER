from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
import re
import zipfile
import xml.etree.ElementTree as ET


APS_XLSX_TABLE_CONTRACT_ID = "aps_xlsx_table_units_v1"
APS_XLSX_PARSER_ID = "aps_xlsx_workbook_parser"
APS_XLSX_PARSER_VERSION = "1.0.0"

_NULL_MARKERS = {"", "na", "n/a", "null", "none", "nan"}
_CELL_REF_RE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


@dataclass(frozen=True)
class _SheetRef:
    name: str
    sheet_id: str
    relationship_id: str
    path: str
    index: int


def _local_name(value: str) -> str:
    return str(value or "").rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _first_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _descendant_text(element: ET.Element, name: str) -> str:
    values: list[str] = []
    for child in element.iter():
        if _local_name(child.tag) == name and child.text:
            values.append(child.text)
    return "".join(values)


def _read_xml(archive: zipfile.ZipFile, path: str) -> ET.Element:
    try:
        payload = archive.read(path)
    except KeyError as exc:
        raise ValueError(f"xlsx_part_missing:{path}") from exc
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"xlsx_xml_parse_failed:{path}") from exc


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


def _dedupe_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    used: set[str] = set()
    result: list[str] = []
    for index, header in enumerate(headers, start=1):
        base = str(header or "").strip() or f"column_{index}"
        seen[base] = int(seen.get(base, 0)) + 1
        key = base if seen[base] == 1 else f"{base}_{seen[base]}"
        while key in used:
            seen[base] += 1
            key = f"{base}_{seen[base]}"
        used.add(key)
        result.append(key)
    return result


def _looks_like_header(row: list[str], next_row: list[str]) -> bool:
    if not row or any(_is_null(value) for value in row):
        return False
    has_duplicate_labels = len(set(str(value).strip() for value in row)) != len(row)
    headerish = sum(1 for value in row if not _is_number(value) and not _is_datetime(value))
    dataish = sum(1 for value in next_row if _is_number(value) or _is_datetime(value) or _is_bool(value))
    return (headerish == len(row) and (not has_duplicate_labels or dataish >= 1)) or (
        headerish >= max(1, len(row) // 2) and dataish >= 1
    )


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


def _column_index(cell_ref: str) -> int:
    match = _CELL_REF_RE.match(str(cell_ref or "").upper())
    if not match:
        raise ValueError("xlsx_cell_reference_invalid")
    letters = match.group(1)
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def _safe_sheet_path(target: str) -> str:
    raw = str(target or "").replace("\\", "/").lstrip("/")
    path = PurePosixPath(raw if raw.startswith("xl/") else str(PurePosixPath("xl") / raw))
    normalized = str(path)
    if ".." in path.parts or not normalized.startswith("xl/"):
        raise ValueError("xlsx_sheet_path_unsafe")
    return normalized


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _read_xml(archive, "xl/sharedStrings.xml")
    values: list[str] = []
    for item in root.iter():
        if _local_name(item.tag) == "si":
            values.append(_descendant_text(item, "t"))
    return values


def _relationship_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    root = _read_xml(archive, "xl/_rels/workbook.xml.rels")
    targets: dict[str, str] = {}
    for relationship in root.iter():
        if _local_name(relationship.tag) != "Relationship":
            continue
        rel_id = str(relationship.attrib.get("Id") or "").strip()
        target = str(relationship.attrib.get("Target") or "").strip()
        if rel_id and target:
            targets[rel_id] = _safe_sheet_path(target)
    return targets


def _sheet_refs(archive: zipfile.ZipFile) -> list[_SheetRef]:
    root = _read_xml(archive, "xl/workbook.xml")
    rels = _relationship_targets(archive)
    refs: list[_SheetRef] = []
    for index, sheet in enumerate(root.iter(), start=1):
        if _local_name(sheet.tag) != "sheet":
            continue
        name = str(sheet.attrib.get("name") or "").strip() or f"Sheet{index}"
        sheet_id = str(sheet.attrib.get("sheetId") or "").strip() or str(index)
        rel_id = str(sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") or "").strip()
        if not rel_id:
            raise ValueError("xlsx_sheet_relationship_missing")
        path = rels.get(rel_id)
        if not path:
            raise ValueError("xlsx_sheet_relationship_target_missing")
        refs.append(_SheetRef(name=name, sheet_id=sheet_id, relationship_id=rel_id, path=path, index=len(refs) + 1))
    if not refs:
        raise ValueError("xlsx_workbook_sheets_missing")
    return refs


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if _first_child(cell, "f") is not None:
        raise ValueError("xlsx_formula_not_admitted")
    cell_type = str(cell.attrib.get("t") or "").strip()
    if cell_type == "e":
        raise ValueError("xlsx_error_cell_not_admitted")
    value_node = _first_child(cell, "v")
    if cell_type == "inlineStr":
        return _descendant_text(cell, "t")
    raw = "" if value_node is None or value_node.text is None else str(value_node.text)
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError) as exc:
            raise ValueError("xlsx_shared_string_invalid") from exc
    if cell_type == "b":
        return "true" if raw == "1" else "false"
    return raw


def _sheet_rows(root: ET.Element, shared_strings: list[str], *, max_columns: int) -> list[list[str]]:
    sheet_data = _first_child(root, "sheetData")
    if sheet_data is None:
        return []
    rows: list[list[str]] = []
    for row in _children(sheet_data, "row"):
        values_by_index: dict[int, str] = {}
        for cell in _children(row, "c"):
            cell_ref = str(cell.attrib.get("r") or "").strip()
            if not cell_ref:
                raise ValueError("xlsx_cell_reference_missing")
            column_index = _column_index(cell_ref)
            if column_index > int(max_columns):
                raise ValueError("xlsx_column_limit_exceeded")
            values_by_index[column_index] = _cell_value(cell, shared_strings)
        if not values_by_index:
            continue
        width = max(values_by_index)
        values = [values_by_index.get(index, "") for index in range(1, width + 1)]
        if any(str(value or "").strip() for value in values):
            rows.append(values)
    return rows


def _rectangular_rows(rows: list[list[str]], *, max_rows: int, max_columns: int) -> list[list[str]]:
    if not rows:
        raise ValueError("xlsx_empty_table")
    if len(rows) < 2:
        raise ValueError("xlsx_header_only")
    if len(rows) > int(max_rows) + 1:
        raise ValueError("xlsx_row_limit_exceeded")
    width = max(len(row) for row in rows)
    if width < 2:
        raise ValueError("xlsx_column_count_unsupported")
    if width > int(max_columns):
        raise ValueError("xlsx_column_limit_exceeded")
    return [row + [""] * (width - len(row)) for row in rows]


def _table_payload(rows: list[list[str]], sheet: _SheetRef) -> dict[str, Any]:
    header_present = len(rows) > 1 and _looks_like_header(rows[0], rows[1])
    headers = _dedupe_headers(rows[0] if header_present else [f"column_{index}" for index in range(1, len(rows[0]) + 1)])
    data_rows = rows[1:] if header_present else rows
    if not data_rows:
        raise ValueError("xlsx_header_only")

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
            "source_sheet_name": sheet.name,
            "values": {headers[col_index]: row[col_index] for col_index in range(len(headers))},
            "raw_values": list(row),
        }
        for index, row in enumerate(data_rows, start=1)
    ]
    table_unit = {
        "unit_kind": "table",
        "table_index": 1,
        "workbook_sheet_index": sheet.index,
        "workbook_sheet_name": sheet.name,
        "workbook_sheet_id": sheet.sheet_id,
        "workbook_sheet_path": sheet.path,
        "row_count": len(data_rows),
        "column_count": len(headers),
        "header_present": header_present,
        "columns": columns,
        "rows": row_units,
    }
    return {
        "header_present": header_present,
        "row_count": len(data_rows),
        "column_count": len(headers),
        "columns": columns,
        "numeric_columns": numeric_columns,
        "time_column_candidates": time_column_candidates,
        "table_units": [table_unit],
        "time_series_units": [
            {
                "unit_kind": "time_series_candidate",
                "table_index": 1,
                "workbook_sheet_name": sheet.name,
                "time_column": column_name,
                "numeric_columns": numeric_columns,
                "row_count": len(data_rows),
            }
            for column_name in time_column_candidates
            if numeric_columns
        ],
    }


def parse_xlsx_workbook(
    *,
    content: bytes,
    max_bytes: int = 5_000_000,
    max_rows: int = 10_000,
    max_columns: int = 200,
    selected_sheet_name: str | None = None,
) -> dict[str, Any]:
    data = bytes(content or b"")
    if not data:
        raise ValueError("xlsx_empty")
    if len(data) > int(max_bytes):
        raise ValueError("xlsx_size_limit_exceeded")

    selected_name = str(selected_sheet_name or "").strip()
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("xlsx_open_failed") from exc
    with archive:
        names = {str(name or "").replace("\\", "/").lower() for name in archive.namelist()}
        if "xl/vbaproject.bin" in names:
            raise ValueError("xlsx_macro_workbook_not_admitted")
        if "encryptioninfo" in names or "encryptedpackage" in names:
            raise ValueError("xlsx_encrypted_not_admitted")
        if "[content_types].xml" not in names or "xl/workbook.xml" not in names:
            raise ValueError("xlsx_workbook_missing")

        shared_strings = _shared_strings(archive)
        sheets = _sheet_refs(archive)
        candidates: list[tuple[_SheetRef, list[list[str]]]] = []
        for sheet in sheets:
            if selected_name and sheet.name != selected_name:
                continue
            root = _read_xml(archive, sheet.path)
            rows = _sheet_rows(root, shared_strings, max_columns=max_columns)
            if rows:
                candidates.append((sheet, rows))

    if selected_name and not candidates:
        raise ValueError("xlsx_selected_sheet_missing_or_empty")
    if not candidates:
        raise ValueError("xlsx_empty_workbook")
    if len(candidates) > 1:
        raise ValueError("xlsx_ambiguous_sheets")

    sheet, rows = candidates[0]
    rectangular = _rectangular_rows(rows, max_rows=max_rows, max_columns=max_columns)
    table = _table_payload(rectangular, sheet)
    return {
        "xlsx_table_contract_id": APS_XLSX_TABLE_CONTRACT_ID,
        "xlsx_parser_id": APS_XLSX_PARSER_ID,
        "xlsx_parser_version": APS_XLSX_PARSER_VERSION,
        "workbook_metadata": {
            "sheet_count": len(sheets),
            "selected_sheet_name": sheet.name,
            "selected_sheet_index": sheet.index,
            "selected_sheet_id": sheet.sheet_id,
            "selected_sheet_path": sheet.path,
            "formula_policy": "fail_closed_formula_cells_not_admitted",
        },
        **table,
    }
