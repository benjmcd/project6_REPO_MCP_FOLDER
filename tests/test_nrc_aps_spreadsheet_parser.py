import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_spreadsheet_parser  # noqa: E402
from support_nrc_aps_xlsx import build_xlsx_bytes  # noqa: E402


def _simple_workbook() -> bytes:
    return build_xlsx_bytes(
        {
            "Observations": [
                ["date", "value", "label"],
                ["2026-01-01", 42, "alpha"],
                ["2026-01-02", 43, "beta"],
            ],
        }
    )


def test_parse_xlsx_workbook_emits_table_units_with_sheet_provenance():
    result = nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=_simple_workbook())

    assert result["xlsx_table_contract_id"] == "aps_xlsx_table_units_v1"
    assert result["workbook_metadata"]["sheet_count"] == 1
    assert result["workbook_metadata"]["selected_sheet_name"] == "Observations"
    assert result["workbook_metadata"]["formula_policy"] == "fail_closed_formula_cells_not_admitted"
    assert result["row_count"] == 2
    assert result["numeric_columns"] == ["value"]
    assert result["time_column_candidates"] == ["date"]

    table = result["table_units"][0]
    assert table["workbook_sheet_name"] == "Observations"
    assert table["rows"][0]["source_sheet_name"] == "Observations"
    assert table["rows"][0]["values"] == {
        "date": "2026-01-01",
        "value": "42",
        "label": "alpha",
    }
    assert result["time_series_units"][0]["workbook_sheet_name"] == "Observations"


def test_parse_xlsx_workbook_fails_closed_on_ambiguous_non_empty_sheets():
    content = build_xlsx_bytes(
        {
            "First": [["date", "value"], ["2026-01-01", 42]],
            "Second": [["date", "value"], ["2026-01-02", 43]],
        }
    )

    with pytest.raises(ValueError, match="xlsx_ambiguous_sheets"):
        nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=content)


def test_parse_xlsx_workbook_can_select_one_named_sheet():
    content = build_xlsx_bytes(
        {
            "First": [["date", "value"], ["2026-01-01", 42]],
            "Second": [["date", "value"], ["2026-01-02", 43]],
        }
    )

    result = nrc_aps_spreadsheet_parser.parse_xlsx_workbook(
        content=content,
        selected_sheet_name="Second",
    )

    assert result["workbook_metadata"]["selected_sheet_name"] == "Second"
    assert result["table_units"][0]["rows"][0]["values"]["value"] == "43"


def test_parse_xlsx_workbook_fails_closed_on_formula_cells():
    content = build_xlsx_bytes(
        {"Observations": [["date", "value"], ["2026-01-01", "SUM(B2:B2)"]]},
        formula_sheet="Observations",
        formula_cell=(2, 2),
    )

    with pytest.raises(ValueError, match="xlsx_formula_not_admitted"):
        nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=content)


def test_parse_xlsx_workbook_fails_closed_on_macro_workbook():
    content = build_xlsx_bytes(
        {"Observations": [["date", "value"], ["2026-01-01", 42]]},
        macro=True,
    )

    with pytest.raises(ValueError, match="xlsx_macro_workbook_not_admitted"):
        nrc_aps_spreadsheet_parser.parse_xlsx_workbook(content=content)
