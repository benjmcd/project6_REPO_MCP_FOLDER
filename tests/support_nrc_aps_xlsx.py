from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape
import zipfile


def _cell_ref(column_index: int, row_index: int) -> str:
    letters = ""
    value = column_index
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"{letters}{row_index}"


def _cell_xml(value: object, *, column_index: int, row_index: int, formula: bool = False) -> str:
    ref = _cell_ref(column_index, row_index)
    if formula:
        return f'<c r="{ref}"><f>{escape(str(value))}</f><v>0</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _sheet_xml(rows: list[list[object]], *, formula_cell: tuple[int, int] | None = None) -> str:
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cells.append(
                _cell_xml(
                    value,
                    column_index=column_index,
                    row_index=row_index,
                    formula=formula_cell == (row_index, column_index),
                )
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def build_xlsx_bytes(
    sheets: dict[str, list[list[object]]],
    *,
    formula_sheet: str | None = None,
    formula_cell: tuple[int, int] = (2, 2),
    macro: bool = False,
) -> bytes:
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        sheet_entries = []
        rel_entries = []
        for index, (sheet_name, rows) in enumerate(sheets.items(), start=1):
            rel_id = f"rId{index}"
            sheet_entries.append(
                f'<sheet name="{escape(sheet_name)}" sheetId="{index}" r:id="{rel_id}"/>'
            )
            rel_entries.append(
                f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            )
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _sheet_xml(
                    rows,
                    formula_cell=formula_cell if formula_sheet == sheet_name else None,
                ),
            )
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(sheet_entries)}</sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{"".join(rel_entries)}'
            "</Relationships>",
        )
        if macro:
            archive.writestr("xl/vbaProject.bin", b"macro")
    return payload.getvalue()
