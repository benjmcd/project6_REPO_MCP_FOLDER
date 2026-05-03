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

from app.services import nrc_aps_csv_parser  # noqa: E402


def test_parse_csv_table_reports_table_and_time_series_diagnostics():
    result = nrc_aps_csv_parser.parse_csv_table(
        content=b"date,value,label\n2026-01-01,42,alpha\n2026-01-02,43,beta\n",
    )

    assert result["csv_table_contract_id"] == "aps_csv_table_units_v1"
    assert result["delimiter"] == ","
    assert result["encoding"] == "utf-8-sig"
    assert result["header_present"] is True
    assert result["row_count"] == 2
    assert result["column_count"] == 3
    assert result["numeric_columns"] == ["value"]
    assert result["time_column_candidates"] == ["date"]
    assert result["table_units"][0]["rows"][0]["source_row_number"] == 2
    assert result["time_series_units"][0]["time_column"] == "date"


def test_parse_csv_table_handles_quoted_delimiters_and_null_markers():
    result = nrc_aps_csv_parser.parse_csv_table(
        content=b'name,amount,note\n"A, Inc.",,n/a\n"B LLC",5,"quoted, note"\n',
    )

    assert result["row_count"] == 2
    assert result["null_markers"] == ["n/a"]
    assert result["table_units"][0]["rows"][0]["values"]["name"] == "A, Inc."
    assert result["table_units"][0]["rows"][1]["values"]["note"] == "quoted, note"


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (b"", "csv_empty"),
        (b"just prose without a delimiter\nanother line\n", "csv_delimiter_not_detected"),
        (b"a,b\n", "csv_header_only"),
        (b"a,b\n1,2,3\n", "csv_ragged_rows"),
        (b"name,value\nx,=SUM(A1:A2)\n", "csv_formula_injection_risk"),
        (b"\xff\xfe\x00\x00bad", "csv_decode_failed"),
    ],
)
def test_parse_csv_table_fails_closed_on_unsupported_inputs(content: bytes, error: str):
    with pytest.raises(ValueError, match=error):
        nrc_aps_csv_parser.parse_csv_table(content=content)


def test_parse_csv_table_enforces_bounds():
    with pytest.raises(ValueError, match="csv_size_limit_exceeded"):
        nrc_aps_csv_parser.parse_csv_table(content=b"a,b\n1,2\n", max_bytes=3)
