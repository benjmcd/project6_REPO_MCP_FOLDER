from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.market_insight_ai import router
from app.services.market_insight_ai import MarketInsight, process_market_insights


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_empty_payload_returns_empty_list() -> None:
    assert process_market_insights({}) == []


def test_non_dict_payload_returns_empty() -> None:
    assert process_market_insights([]) == []  # type: ignore[arg-type]


def test_emerging_risk_on_invalid_signals() -> None:
    payload = {
        "validation_summary": {"valid_count": 10, "invalid_count": 3, "failed_count": 0},
    }
    out = process_market_insights(payload)
    assert len(out) == 1
    assert out[0].category == "emerging_risk"
    assert out[0].severity == "high"
    assert out[0].derivation_label == "heuristic"
    assert out[0].supporting_metrics["invalid_count"] == 3


def test_emerging_risk_on_low_pass_rate() -> None:
    payload = {"validation_summary": {"pass_rate": 0.72, "invalid_count": 0, "failed_count": 0}}
    out = process_market_insights(payload)
    assert len(out) == 1
    assert out[0].severity == "medium"
    assert out[0].category == "emerging_risk"
    assert out[0].supporting_metrics["pass_rate"] == 0.72


def test_correlation_balanced_categories() -> None:
    payload = {
        "integrated": {
            "signals_by_category": {"a": 100, "b": 80, "c": 5},
        },
    }
    out = process_market_insights(payload)
    assert len(out) == 1
    assert out[0].category == "correlation"
    assert out[0].derivation_label == "heuristic"
    assert out[0].supporting_metrics["balance_ratio"] == 0.8


def test_trend_rising_trajectory() -> None:
    payload = {"integrated": {"signal_trajectory": [1.0, 1.1, 1.2, 2.0, 3.5]}}
    out = process_market_insights(payload)
    assert len(out) == 1
    assert out[0].category == "trend"
    assert out[0].derivation_label == "heuristic"


def test_combined_payload_sorted_deterministically() -> None:
    payload = {
        "validation_summary": {"invalid_count": 1, "failed_count": 0, "valid_count": 5},
        "integrated": {
            "signals_by_category": {"x": 10, "y": 9},
            "signal_trajectory": [0.5, 0.6, 0.7, 1.2, 2.0],
        },
    }
    out = process_market_insights(payload)
    categories = [i.category for i in out]
    assert categories == sorted(categories)
    assert all(i.derivation_label == "heuristic" for i in out)
    assert len(out) == 3


def test_api_post_returns_json_insights() -> None:
    client = _client()
    body = {
        "integrated": {"signals_by_category": {"p": 20, "q": 16}},
        "validation_summary": {"invalid_count": 0, "failed_count": 0, "pass_rate": 0.95},
    }
    res = client.post("/api/v1/market-pipeline/insights/process", json=body)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert data[0]["derivation_label"] == "heuristic"
    assert MarketInsight.model_validate(data[0])
