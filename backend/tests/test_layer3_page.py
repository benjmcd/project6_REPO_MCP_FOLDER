from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def test_layer3_page_route_serves_workbench_shell() -> None:
    response = client.get("/review/layer3")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Layer 3 Workbench</title>" in response.text
    assert 'id="authority-rail"' in response.text
    assert 'id="intent-form"' in response.text
    assert 'id="material-ledger-body"' in response.text
    assert 'id="gate-c-panel"' in response.text
    assert 'id="plan-panel"' in response.text
    assert 'id="plan-preview"' in response.text
    assert 'id="plan-reject"' in response.text
    assert 'id="plan-request-revision"' in response.text
    assert 'id="plan-approve"' in response.text
    assert 'id="execution-step-chip"' in response.text
    assert 'id="results-step-chip"' in response.text
    assert 'id="package-step-chip"' in response.text
    assert 'id="result-review-panel"' in response.text
    assert 'id="result-review-refresh"' in response.text
    assert 'id="result-status-inspect"' in response.text
    assert 'id="result-review-decision"' in response.text
    assert 'id="result-review-notes"' in response.text
    assert 'id="result-review-submit"' in response.text
    assert 'id="package-review-preview-panel"' in response.text
    assert 'id="package-review-preview-inspect"' in response.text
    assert 'href="/review/layer3/static/layer3.css"' in response.text
    assert 'src="/review/layer3/static/layer3.js"' in response.text
    assert "Plan</button>" in response.text
    assert "Execution</button>" in response.text
    assert "Results</button>" in response.text
    assert "Package</button>" in response.text


def test_layer3_static_assets_are_mounted() -> None:
    css = client.get("/review/layer3/static/layer3.css")
    js = client.get("/review/layer3/static/layer3.js")

    assert css.status_code == 200
    assert js.status_code == 200
    assert ".authority-rail" in css.text
    assert "const API_ROOT = '/api/v1/layer3';" in js.text
    assert "postJson('/gate-b/decision'" in js.text
    assert "postJson('/gate-c/preview'" in js.text
    assert "postJson('/plan/preview'" in js.text
    assert "postJson('/plan/revise'" in js.text
    assert "postJson('/plan/approve'" in js.text
    assert "postJson('/package/review/preview'" in js.text
    assert "getJson(`/session/${encodeURIComponent(sessionId)}`)" in js.text
    assert "postJson('/execution/result/status'" in js.text
    assert "postJson('/execution/result/review'" in js.text
    assert "operator_view_mode: 'status_only'" in js.text
    assert "operator_decision: elements.resultReviewDecision.value" in js.text
    assert "planRevisionPending" in js.text
    assert "State.planRevisionPending = true" in js.text


def test_layer3_shell_does_not_remove_adjacent_review_pages() -> None:
    assert client.get("/review/nrc-aps").status_code == 200
    assert client.get("/review/nrc-aps/workbench-compare").status_code == 200
    assert client.get("/review/nrc-aps/candidate-b-trace").status_code == 200
    assert client.get("/review/analyst-insight").status_code == 200
