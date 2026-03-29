from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.market_data_validation import router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.market_data_validation import validate_market_rows  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix=settings.api_prefix)
    return TestClient(app)


def test_validate_missing_required_fields() -> None:
    rows = [{"a": 1}, {"a": 2, "b": "x"}]
    out = validate_market_rows(rows, required_fields=["b"])
    assert out["missing_field_issues"][0]["row_index"] == 0
    assert "b" in out["missing_field_issues"][0]["missing_fields"]


def test_key_consistency_flags_mismatched_keys() -> None:
    rows = [{"a": 1, "b": 2}, {"a": 3}]
    out = validate_market_rows(rows, numeric_columns=["a"], check_key_consistency=True)
    assert out["key_consistency"]["consistent"] is False
    assert 1 in out["key_consistency"]["inconsistent_row_indices"]


def test_zscore_outlier_detects_extreme_value() -> None:
    base = [10.0] * 20
    rows = [{"v": x} for x in base] + [{"v": 1e6}]
    out = validate_market_rows(
        rows,
        numeric_columns=["v"],
        outlier_method="zscore",
        zscore_threshold=3.0,
    )
    assert any(o["row_index"] == 20 and o["method"] == "zscore" for o in out["outliers"])


def test_iqr_outlier_detects_extreme_value() -> None:
    rows = [{"x": float(i)} for i in range(1, 11)] + [{"x": 1000.0}]
    out = validate_market_rows(
        rows,
        numeric_columns=["x"],
        outlier_method="iqr",
        iqr_multiplier=1.5,
    )
    assert any(o["row_index"] == 10 for o in out["outliers"])


def test_no_outliers_when_method_none() -> None:
    rows = [{"x": 1.0}, {"x": 100.0}]
    out = validate_market_rows(
        rows,
        numeric_columns=["x"],
        outlier_method="none",
    )
    assert out["outliers"] == []


def test_min_max_normalization() -> None:
    rows = [{"x": 0.0}, {"x": 10.0}, {"x": 5.0}]
    out = validate_market_rows(rows, numeric_columns=["x"], normalize_columns=["x"])
    assert out["normalized_rows"] is not None
    nr = out["normalized_rows"]
    assert nr[0]["x"] == 0.0
    assert nr[1]["x"] == 1.0
    assert nr[2]["x"] == pytest.approx(0.5)


def test_min_max_normalization_constant_column() -> None:
    rows = [{"x": 7.0}, {"x": 7.0}]
    out = validate_market_rows(rows, normalize_columns=["x"])
    assert out["normalized_rows"] is not None
    assert out["normalized_rows"][0]["x"] == 0.5
    assert out["normalized_rows"][1]["x"] == 0.5


def test_api_run_endpoint() -> None:
    client = _client()
    payload = {
        "rows": [{"a": 1, "b": 2.0}],
        "options": {
            "required_fields": ["a"],
            "numeric_columns": ["b"],
            "outlier_method": "none",
        },
    }
    r = client.post(f"{settings.api_prefix}/market-pipeline/validation/run", json=payload)
    assert r.status_code == 200
    assert r.json()["row_count"] == 1
    assert r.json()["missing_field_issues"] == []


def test_api_run_endpoint_validation_error_on_empty_body() -> None:
    client = _client()
    r = client.post(f"{settings.api_prefix}/market-pipeline/validation/run", json={})
    assert r.status_code == 422
