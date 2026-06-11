"""
Tests for backend/app/core/observability.py and the wired /ready endpoint.

Pattern mirrors existing test_layer3_api.py: DB_INIT_MODE=none, in-memory
SQLite, StaticPool, dependency override for get_db.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before any app import so _initialize_database() is a no-op
os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.core.observability import (
    RequestIdMiddleware,
    _JsonFormatter,
    setup_logging,
)
from app.db.session import Base
from main import app


# ---------------------------------------------------------------------------
# Shared fixture: in-memory DB + TestClient
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    tc = TestClient(app, raise_server_exceptions=False)
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# 1. Request-ID roundtrip: valid inbound header honored
# ---------------------------------------------------------------------------

def test_request_id_inbound_honored(client):
    # Valid id: alphanumeric + safe punctuation, <= 128 chars
    inbound_id = "test-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": inbound_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == inbound_id


# ---------------------------------------------------------------------------
# 1b. Request-ID: overlong id rejected → generated uuid4 returned instead
# ---------------------------------------------------------------------------

def test_request_id_overlong_rejected(client):
    overlong_id = "a" * 129  # exceeds 128-char limit
    response = client.get("/health", headers={"X-Request-ID": overlong_id})
    assert response.status_code == 200
    returned_id = response.headers.get("X-Request-ID")
    assert returned_id is not None
    # Must NOT echo back the overlong id
    assert returned_id != overlong_id
    # Must be a UUID4 (8-4-4-4-12)
    parts = returned_id.split("-")
    assert len(parts) == 5, f"Expected UUID4 format for rejected id, got: {returned_id}"


# ---------------------------------------------------------------------------
# 1c. Request-ID: id with newline/invalid chars rejected → generated uuid4
# ---------------------------------------------------------------------------

def test_request_id_invalid_chars_rejected(client):
    # Newline in header value is a classic header injection vector
    invalid_id = "valid-prefix\r\nX-Injected: malicious"
    response = client.get("/health", headers={"X-Request-ID": invalid_id})
    assert response.status_code == 200
    returned_id = response.headers.get("X-Request-ID")
    assert returned_id is not None
    assert returned_id != invalid_id
    # Must be a UUID4 (8-4-4-4-12)
    parts = returned_id.split("-")
    assert len(parts) == 5, f"Expected UUID4 format for rejected id, got: {returned_id}"


# ---------------------------------------------------------------------------
# 2. Request-ID roundtrip: absent → generated UUID4
# ---------------------------------------------------------------------------

def test_request_id_generated_when_absent(client):
    response = client.get("/health")
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    assert len(rid) > 0
    # UUID4 format: 8-4-4-4-12
    parts = rid.split("-")
    assert len(parts) == 5, f"Expected UUID4 format, got: {rid}"


# ---------------------------------------------------------------------------
# 3. Global exception handler: returns bounded 500 JSON without traceback
# ---------------------------------------------------------------------------

def test_unhandled_exception_returns_bounded_500(client):
    """
    The exception handler must return 500 with error_code + request_id,
    and must NOT leak any traceback text into the response body.
    """
    # Inject a route that always raises
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as _TC
    from app.core.observability import RequestIdMiddleware, unhandled_exception_handler

    mini = FastAPI()
    mini.add_middleware(RequestIdMiddleware)
    mini.add_exception_handler(Exception, unhandled_exception_handler)

    @mini.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail XYZ")

    tc = _TC(mini, raise_server_exceptions=False)
    resp = tc.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body.get("error_code") == "internal_error"
    assert "request_id" in body
    # No traceback or internal message in the body
    body_text = resp.text
    assert "secret internal detail XYZ" not in body_text
    assert "Traceback" not in body_text
    assert "RuntimeError" not in body_text


# ---------------------------------------------------------------------------
# 4. /ready returns 200 with working in-memory DB
# ---------------------------------------------------------------------------

def test_ready_returns_200_with_working_db(client):
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ready"


# ---------------------------------------------------------------------------
# 5. JSON formatter emits valid JSON lines when enabled
# ---------------------------------------------------------------------------

def test_json_formatter_emits_valid_json():
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    line = formatter.format(record)
    parsed = json.loads(line)  # must not raise
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello world"
    assert parsed["logger"] == "test.logger"


def test_json_formatter_includes_request_id():
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="request failed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-abc-123"
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["request_id"] == "req-abc-123"


def test_setup_logging_json_sets_json_formatter(monkeypatch):
    monkeypatch.setenv("LAYER3_LOG_FORMAT", "json")
    root = logging.getLogger()
    # Ensure at least one handler so setup_logging can patch it
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    setup_logging()
    # At least one handler should now have a _JsonFormatter
    has_json = any(isinstance(h.formatter, _JsonFormatter) for h in root.handlers)
    assert has_json, "Expected at least one handler with _JsonFormatter after setup_logging()"


def test_setup_logging_plain_leaves_formatters_unchanged(monkeypatch):
    """setup_logging must not install _JsonFormatter when format is not 'json'."""
    monkeypatch.setenv("LAYER3_LOG_FORMAT", "plain")
    root = logging.getLogger()
    # Snapshot and reset handlers so prior tests don't bleed state
    original_handlers = root.handlers[:]
    root.handlers = [logging.StreamHandler()]
    try:
        setup_logging()
        # Formatters must not have changed to _JsonFormatter
        for h in root.handlers:
            assert not isinstance(h.formatter, _JsonFormatter), (
                "Plain log format should not install _JsonFormatter"
            )
    finally:
        root.handlers = original_handlers
