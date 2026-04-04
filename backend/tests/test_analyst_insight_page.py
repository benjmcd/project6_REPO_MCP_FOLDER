from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def test_analyst_insight_page_route_serves() -> None:
    response = client.get("/review/analyst-insight")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text

    assert "<title>Analyst Insight Layer</title>" in html
    assert "Analyst insight layer" in html
    assert 'href="/review/nrc-aps/static/analyst_insight.css"' in html
    assert 'src="/review/nrc-aps/static/analyst_insight.js"' in html
    assert 'id="integration-json"' in html
    assert 'id="validation-json"' in html
    assert 'id="insight-json"' in html
    assert 'id="btn-full-flow"' in html


def test_root_exposes_analyst_insight_link() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "href='/review/analyst-insight'" in response.text
    assert "Analyst insight layer" in response.text


def test_market_pipeline_page_remains_absent() -> None:
    response = client.get("/review/market-pipeline")
    assert response.status_code == 404


def test_analyst_insight_js_uses_alias_routes() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "analyst_insight.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "/analyst-insight/integration/cross-reference" in js_content
    assert "/analyst-insight/validation/run" in js_content
    assert "/analyst-insight/insights/process" in js_content


def test_analyst_insight_html_references_alias_routes() -> None:
    html_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "analyst_insight.html"
    html_content = html_path.read_text(encoding="utf-8")

    assert "/api/v1/analyst-insight/..." in html_content
    assert "market-pipeline" not in html_content
