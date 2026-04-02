from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app

client = TestClient(app)

def test_page_loads():
    response = client.get("/review/nrc-aps")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "NRC APS Pipeline Review" in response.text
    assert "Pipeline Overview" in response.text
    assert "Run-specific Overview (Light)" in response.text
    assert "Run-specific Overview (Heavy)" in response.text
    assert "Theme:" in response.text
    assert ">System<" in response.text
    assert ">Light<" in response.text
    assert ">Dark<" in response.text
    assert 'aria-label="Close details"' in response.text


def test_page_has_run_identity_container():
    response = client.get("/review/nrc-aps")
    assert response.status_code == 200
    assert 'id="current-run-info"' in response.text
    assert 'run-identity-bar' in response.text


def test_review_js_has_identity_aware_overlay_messages():
    """Verify review.js sets identity-aware overlay messages with state-appropriate titles."""
    from pathlib import Path
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "review.js"
    js_content = js_path.read_text(encoding="utf-8")

    # disabledTitle element reference exists
    assert "disabledTitle" in js_content

    # Non-reviewable state includes run identity and correct title
    assert "Run Not Reviewable" in js_content
    assert "is not reviewable" in js_content

    # Fetch-failure state has distinct title from non-reviewable
    assert "Error Loading Run" in js_content
    assert "Failed to load overview for run" in js_content

    # No-runs state has its own title
    assert "No Runs Available" in js_content

    # Catalog error
    assert "Failed to load the run catalog" in js_content
