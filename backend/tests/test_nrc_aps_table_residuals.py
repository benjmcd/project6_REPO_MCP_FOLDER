from __future__ import annotations

import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import (  # noqa: E402
    connectors_nrc_adams,
    nrc_aps_csv_parser,
    nrc_aps_dataset_bridge,
    nrc_aps_document_processing,
    nrc_aps_spreadsheet_parser,
)


def _xlsx_content(sheet_xml: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types" />')
        archive.writestr(
            "xl/workbook.xml",
            (
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" /></sheets></workbook>'
            ),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml" /></Relationships>'
            ),
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def _sec_edgar_content() -> bytes:
    return b"""
<SEC-DOCUMENT>
<SEC-HEADER>
<CONFORMED-SUBMISSION-TYPE>10-K
<ACCESSION-NUMBER>0000000000-26-000001
<FILED-AS-OF-DATE>20260101
<COMPANY-CONFORMED-NAME>EXAMPLE INC
</SEC-HEADER>
<DOCUMENT>
<TYPE>10-K
<TEXT>
ITEM 1. Business overview.
<TABLE>
period,value
2025-01-01,10
2025-02-01,20
</TABLE>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""


def test_csv_header_dedupe_avoids_pre_suffixed_collisions() -> None:
    parsed = nrc_aps_csv_parser.parse_csv_table(content=b"a,a_2,a\n1,2,3\n4,5,6\n")

    assert [column["name"] for column in parsed["columns"]] == ["a", "a_2", "a_3"]
    assert parsed["table_units"][0]["rows"][0]["values"] == {"a": "1", "a_2": "2", "a_3": "3"}


def test_csv_duplicate_text_row_without_data_evidence_is_not_forced_to_header() -> None:
    parsed = nrc_aps_csv_parser.parse_csv_table(content=b"a,a\nx,y\np,q\n")

    assert [column["name"] for column in parsed["columns"]] == ["column_1", "column_2"]
    assert parsed["table_units"][0]["rows"][0]["values"] == {"column_1": "a", "column_2": "a"}


def test_xlsx_header_dedupe_avoids_pre_suffixed_collisions() -> None:
    sheet_xml = """
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>a</t></is></c>
      <c r="B1" t="inlineStr"><is><t>a_2</t></is></c>
      <c r="C1" t="inlineStr"><is><t>a</t></is></c>
    </row>
    <row r="2">
      <c r="A2"><v>1</v></c><c r="B2"><v>2</v></c><c r="C2"><v>3</v></c>
    </row>
  </sheetData>
</worksheet>
"""
    parsed = nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=_xlsx_content(sheet_xml), max_columns=3)

    assert [column["name"] for column in parsed["columns"]] == ["a", "a_2", "a_3"]
    assert parsed["table_units"][0]["rows"][0]["values"] == {"a": "1", "a_2": "2", "a_3": "3"}


def test_xlsx_duplicate_text_row_without_data_evidence_is_not_forced_to_header() -> None:
    sheet_xml = """
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>a</t></is></c><c r="B1" t="inlineStr"><is><t>a</t></is></c></row>
    <row r="2"><c r="A2" t="inlineStr"><is><t>x</t></is></c><c r="B2" t="inlineStr"><is><t>y</t></is></c></row>
    <row r="3"><c r="A3" t="inlineStr"><is><t>p</t></is></c><c r="B3" t="inlineStr"><is><t>q</t></is></c></row>
  </sheetData>
</worksheet>
"""
    parsed = nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=_xlsx_content(sheet_xml), max_columns=2)

    assert [column["name"] for column in parsed["columns"]] == ["column_1", "column_2"]
    assert parsed["table_units"][0]["rows"][0]["values"] == {"column_1": "a", "column_2": "a"}


def test_xlsx_sparse_far_right_cells_fail_before_row_expansion() -> None:
    sheet_xml = """
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="XFD1" t="inlineStr"><is><t>too_far</t></is></c></row>
    <row r="2"><c r="XFD2"><v>1</v></c></row>
  </sheetData>
</worksheet>
"""
    with pytest.raises(ValueError, match="xlsx_column_limit_exceeded"):
        nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=_xlsx_content(sheet_xml), max_columns=2)


def test_dataset_bridge_boolean_coercion_preserves_null_markers() -> None:
    frame = pd.DataFrame({"flag": ["true", "", "no", None, "null"]})
    coerced = nrc_aps_dataset_bridge._coerce_frame(
        frame,
        [{"name": "flag", "kind": "boolean"}],
        time_column=None,
    )

    assert coerced["flag"].tolist()[0] is True
    assert pd.isna(coerced["flag"].tolist()[1])
    assert coerced["flag"].tolist()[2] is False
    assert pd.isna(coerced["flag"].tolist()[3])
    assert pd.isna(coerced["flag"].tolist()[4])


def test_sec_edgar_document_processing_accepts_comma_delimited_form_config_and_surfaces_time_candidates() -> None:
    result = nrc_aps_document_processing.process_document(
        content=_sec_edgar_content(),
        declared_content_type="application/x-sec-edgar-submission",
        config={"sec_edgar_admitted_form_types": "10-K, 10-Q"},
    )

    assert result["extractor_family"] == "sec_edgar_filing"
    assert result["table_diagnostics"]["time_column_candidates"] == ["period"]
    assert result["table_diagnostics"]["tables"][0]["time_column_candidates"] == ["period"]


def test_csv_dataset_bridge_runs_when_table_bridge_is_also_enabled() -> None:
    run = SimpleNamespace(status="completed")

    assert connectors_nrc_adams._should_generate_csv_dataset_bridge_artifacts(
        run=run,
        config={"csv_dataset_bridge_enabled": True, "table_dataset_bridge_enabled": True},
    )
