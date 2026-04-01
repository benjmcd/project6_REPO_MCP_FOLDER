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
