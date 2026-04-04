"""Parity tests proving analyst-insight alias routes return identical responses to market-pipeline routes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.market_data_integration import alias_router as integration_alias, router as integration_router
from app.api.market_data_validation import alias_router as validation_alias, router as validation_router
from app.api.market_insight_ai import alias_router as insight_alias, router as insight_router
from app.core.config import settings


def _client() -> TestClient:
    app = FastAPI()
    prefix = settings.api_prefix
    app.include_router(integration_router, prefix=prefix)
    app.include_router(validation_router, prefix=prefix)
    app.include_router(insight_router, prefix=prefix)
    app.include_router(integration_alias, prefix=prefix)
    app.include_router(validation_alias, prefix=prefix)
    app.include_router(insight_alias, prefix=prefix)
    return TestClient(app)


# --- Integration stage parity ---

INTEGRATION_PAYLOAD = {
    "sources": {
        "regulatory": [{"date": "2026-03-01", "region": "EU", "rule": "R1"}],
        "manifests": [{"date": "2026-03-01", "region": "EU", "ship": "S1"}],
    },
    "link_keys": ["date", "region"],
}


def test_integration_success_parity() -> None:
    c = _client()
    old = c.post(f"{settings.api_prefix}/market-pipeline/integration/cross-reference", json=INTEGRATION_PAYLOAD)
    new = c.post(f"{settings.api_prefix}/analyst-insight/integration/cross-reference", json=INTEGRATION_PAYLOAD)
    assert old.status_code == new.status_code == 200
    assert old.json() == new.json()


def test_integration_invalid_payload_parity() -> None:
    c = _client()
    bad = {"sources": {}, "link_keys": []}  # link_keys min_length=1 violation
    old = c.post(f"{settings.api_prefix}/market-pipeline/integration/cross-reference", json=bad)
    new = c.post(f"{settings.api_prefix}/analyst-insight/integration/cross-reference", json=bad)
    assert old.status_code == new.status_code == 422


# --- Validation stage parity ---

VALIDATION_PAYLOAD = {
    "rows": [{"a": 1, "b": 2.0}],
    "options": {
        "required_fields": ["a"],
        "numeric_columns": ["b"],
        "outlier_method": "none",
    },
}


def test_validation_success_parity() -> None:
    c = _client()
    old = c.post(f"{settings.api_prefix}/market-pipeline/validation/run", json=VALIDATION_PAYLOAD)
    new = c.post(f"{settings.api_prefix}/analyst-insight/validation/run", json=VALIDATION_PAYLOAD)
    assert old.status_code == new.status_code == 200
    assert old.json() == new.json()


def test_validation_empty_body_parity() -> None:
    c = _client()
    old = c.post(f"{settings.api_prefix}/market-pipeline/validation/run", json={})
    new = c.post(f"{settings.api_prefix}/analyst-insight/validation/run", json={})
    assert old.status_code == new.status_code == 422


# --- Insight stage parity ---

INSIGHT_PAYLOAD = {
    "integrated": {"signals_by_category": {"p": 20, "q": 16}},
    "validation_summary": {"invalid_count": 0, "failed_count": 0, "pass_rate": 0.95},
}


def test_insight_success_parity() -> None:
    c = _client()
    old = c.post(f"{settings.api_prefix}/market-pipeline/insights/process", json=INSIGHT_PAYLOAD)
    new = c.post(f"{settings.api_prefix}/analyst-insight/insights/process", json=INSIGHT_PAYLOAD)
    assert old.status_code == new.status_code == 200
    assert old.json() == new.json()


def test_insight_empty_body_parity() -> None:
    c = _client()
    old = c.post(f"{settings.api_prefix}/market-pipeline/insights/process", json={})
    new = c.post(f"{settings.api_prefix}/analyst-insight/insights/process", json={})
    assert old.status_code == new.status_code == 200
    assert old.json() == new.json() == []
