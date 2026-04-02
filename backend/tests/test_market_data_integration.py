from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.market_data_integration import router as integration_router
from app.core.config import settings
from app.services.market_data_integration import build_integrated_dataset, ingest_sources


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(integration_router, prefix=settings.api_prefix)
    return TestClient(app)


def test_ingest_sources_copies_rows():
    src = {"a": [{"x": 1}]}
    out = ingest_sources(src)
    assert out["a"][0]["x"] == 1
    out["a"][0]["x"] = 2
    assert src["a"][0]["x"] == 1


def test_build_integrated_dataset_links_two_sources():
    sources = {
        "manifests": [{"date": "2026-01-01", "entity_id": "E1", "cargo": "x"}],
        "bonds": [{"date": "2026-01-01", "entity_id": "E1", "volume": 100}],
    }
    result = build_integrated_dataset(sources, ["date", "entity_id"])
    assert result["link_keys"] == ["date", "entity_id"]
    assert result["source_record_counts"] == {"manifests": 1, "bonds": 1}
    assert len(result["cross_references"]) == 1
    g = result["cross_references"][0]
    assert g["key"] == {"date": "2026-01-01", "entity_id": "E1"}
    assert set(g["records_by_source"]) == {"manifests", "bonds"}


def test_build_integrated_dataset_skips_incomplete_keys():
    sources = {
        "a": [{"date": "2026-01-01"}],
        "b": [{"date": "2026-01-01", "region": "US"}],
    }
    result = build_integrated_dataset(sources, ["date", "region"])
    assert result["cross_references"] == []


def test_build_integrated_dataset_single_source_no_cross_ref():
    sources = {"only": [{"date": "2026-01-01", "region": "US", "v": 1}]}
    result = build_integrated_dataset(sources, ["date", "region"])
    assert result["cross_references"] == []


def test_api_cross_reference():
    client = _client()
    payload = {
        "sources": {
            "regulatory": [{"date": "2026-03-01", "region": "EU", "rule": "R1"}],
            "manifests": [{"date": "2026-03-01", "region": "EU", "ship": "S1"}],
        },
        "link_keys": ["date", "region"],
    }
    r = client.post(f"{settings.api_prefix}/market-pipeline/integration/cross-reference", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["link_keys"] == ["date", "region"]
    assert len(data["cross_references"]) == 1
    assert data["cross_references"][0]["key"] == {"date": "2026-03-01", "region": "EU"}
