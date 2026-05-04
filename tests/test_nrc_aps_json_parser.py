import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_json_parser  # noqa: E402


def _json_bytes(value: object) -> bytes:
    return json.dumps(value).encode("utf-8")


def test_parse_json_recordset_accepts_root_array_of_flat_objects():
    result = nrc_aps_json_parser.parse_json_recordset(
        content=_json_bytes(
            [
                {"date": "2026-01-01", "value": 42, "label": "alpha"},
                {"date": "2026-01-02", "value": 43, "label": "beta"},
            ]
        )
    )

    assert result["json_recordset_contract_id"] == "aps_json_recordset_units_v1"
    assert result["record_path"] == "$"
    assert result["row_count"] == 2
    assert result["column_count"] == 3
    assert result["numeric_columns"] == ["value"]
    assert result["time_column_candidates"] == ["date"]
    assert result["columns"][0]["field_path"] == "$[*].date"
    assert result["table_units"][0]["rows"][0]["record_path"] == "$[0]"
    assert result["time_series_units"][0]["time_column"] == "date"


def test_parse_json_recordset_accepts_configured_records_path():
    result = nrc_aps_json_parser.parse_json_recordset(
        content=_json_bytes(
            {
                "meta": {"source": "fixture"},
                "data": {
                    "records": [
                        {"date": "2026-01-01", "value": 42},
                        {"date": "2026-01-02", "value": None},
                    ]
                },
            }
        ),
        record_path="data.records",
    )

    assert result["record_path"] == "$.data.records"
    assert result["columns"][1]["null_count"] == 1
    assert result["table_units"][0]["rows"][1]["values"]["value"] is None


def test_parse_json_recordset_preserves_first_record_column_order_when_key_order_varies():
    result = nrc_aps_json_parser.parse_json_recordset(
        content=_json_bytes(
            [
                {"date": "2026-01-01", "value": 42, "label": "alpha"},
                {"label": "beta", "value": 43, "date": "2026-01-02"},
            ]
        )
    )

    assert [column["name"] for column in result["columns"]] == ["date", "value", "label"]
    assert list(result["table_units"][0]["rows"][1]["values"].keys()) == ["date", "value", "label"]
    assert result["table_units"][0]["rows"][1]["values"]["date"] == "2026-01-02"


def test_parse_json_recordset_requires_path_for_object_root():
    try:
        nrc_aps_json_parser.parse_json_recordset(content=_json_bytes({"records": [{"a": 1}]}))
    except ValueError as exc:
        assert str(exc) == "json_record_path_required_for_object_root"
    else:
        raise AssertionError("expected object root without record_path to fail closed")


def test_parse_json_recordset_rejects_nested_values_without_flattening_policy():
    try:
        nrc_aps_json_parser.parse_json_recordset(content=_json_bytes([{"a": {"nested": 1}}]))
    except ValueError as exc:
        assert str(exc) == "json_nested_value_not_admitted"
    else:
        raise AssertionError("expected nested record value to fail closed")


def test_parse_json_recordset_rejects_heterogeneous_keys():
    try:
        nrc_aps_json_parser.parse_json_recordset(content=_json_bytes([{"a": 1}, {"b": 2}]))
    except ValueError as exc:
        assert str(exc) == "json_recordset_heterogeneous_keys"
    else:
        raise AssertionError("expected heterogeneous record keys to fail closed")


def test_parse_json_recordset_rejects_empty_array_invalid_json_and_size_limit():
    for payload, expected in [
        (_json_bytes([]), "json_recordset_empty"),
        (b"{not valid", "json_parse_failed"),
        (_json_bytes([{"a": 1}]), "json_size_limit_exceeded"),
    ]:
        try:
            nrc_aps_json_parser.parse_json_recordset(
                content=payload,
                max_bytes=1 if expected == "json_size_limit_exceeded" else 5_000_000,
            )
        except ValueError as exc:
            assert str(exc) == expected
        else:
            raise AssertionError(f"expected {expected} to fail closed")
