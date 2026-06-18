"""
Tests for bounded, structured lifecycle log events — Layer 3 / Sublayer 3C
(handoff Lane 14).

Covers:
  - Unit tests for emit_lifecycle_event, bounded_operator_ref, _JsonFormatter extension.
  - Route-level tests: product_generated and product_replay_verified events are emitted
    with the correct bounded fields; no product body/title leaks into captured records.

All tests are self-contained and use the standard in-memory SQLite pattern so
they can be run in isolation:

  cd backend && py -3.12 -m pytest tests/test_layer3_lifecycle_events.py \\
      -p no:cacheprovider --basetemp=C:/pt -q
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

# Must be set before any app import so _initialize_database() is a no-op.
os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.core.observability import _JsonFormatter
from app.db.session import Base
from app.services.layer3_lifecycle_events import (
    bounded_operator_ref,
    emit_lifecycle_event,
)
from main import app


# ---------------------------------------------------------------------------
# Shared TestClient fixture — mirrors pattern from test_layer3_api.py
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(
        settings, "layer3_internal_webhook_url", "http://127.0.0.1/layer3-internal-webhook"
    )
    monkeypatch.setattr(
        settings, "layer3_internal_webhook_display_name", "test-internal-webhook"
    )
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
    tc = TestClient(app)
    # Required by _construct_quant_package_set / _approve_quant_plan helpers
    # imported from test_layer3_api to share the same session factory.
    tc.layer3_session_factory = SessionLocal  # type: ignore[attr-defined]
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper: seed a working-set + generate an analysis product via the API.
# Mirrors the relevant subset of _construct_quant_package_set in test_layer3_api.py
# without the expensive package-commit path.
# ---------------------------------------------------------------------------


def _seed_and_generate(client: TestClient, tmp_path, *, request_id: str):
    """Drive the minimal path through the API to produce a generated analysis product.

    Returns (session_id, product_id, ws_id, method_id).
    """
    # ---- 1. Bootstrap a session through analysis-run start ---
    # Top-level import (not `tests.test_layer3_api`): pytest's prepend import mode
    # puts backend/tests on sys.path and imports sibling test modules top-level.
    # The `tests.` form only resolves when backend/ is also on sys.path as a
    # namespace package, which held in CI but not locally — hence the prior
    # local-only ModuleNotFoundError. This form is consistent in both.
    from test_layer3_api import _construct_quant_package_set  # noqa: PLC0415

    # We only need a session with a committed pass-run/snapshot; _construct_quant_package_set
    # gives us that plus a committed package.  Use it so we get the same level of seeding
    # as the replay-verify test which depends on having a materialized snapshot.
    session_id = _construct_quant_package_set(client, tmp_path, request_id=request_id)[0]

    # ---- 2. Get a snapshot id from the session summary ----
    summary = client.get(f"/api/v1/layer3/session/{session_id}").json()
    snap_id = summary["sublayer_visualization"]["material_objects"][0]["material_snapshot_id"]

    # ---- 3. Create a working set ----
    ws_resp = client.post(
        "/api/v1/layer3/working-set",
        json={
            "session_id": session_id,
            "client_request_id": f"{request_id}-ws",
            "name": "Lifecycle events test scope",
            "members": [{"ref_kind": "material_snapshot", "ref_id": snap_id}],
        },
    )
    assert ws_resp.status_code == 201, ws_resp.text
    ws_id = ws_resp.json()["working_set_id"]

    method_id = "working_set_composition_summary"

    # ---- 4. Generate the deterministic product ----
    gen_resp = client.post(
        "/api/v1/layer3/analysis-product/generate",
        json={
            "session_id": session_id,
            "client_request_id": f"{request_id}-gen",
            "working_set_id": ws_id,
            "method_id": method_id,
        },
    )
    assert gen_resp.status_code == 201, gen_resp.text
    product_id = gen_resp.json()["analysis_product_id"]

    return session_id, product_id, ws_id, method_id


# ===========================================================================
# UNIT TESTS — emit_lifecycle_event helper
# ===========================================================================


class TestEmitLifecycleEvent:
    def test_produces_layer3_event_extra_on_record(self, caplog):
        """emit_lifecycle_event injects layer3_event dict onto the log record."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            emit_lifecycle_event(
                "test_event",
                request_id="req-unit-001",
                operator_ref="op-hash-abc",
                product_id="prod-123",
                lifecycle_status="draft",
            )
        records = [r for r in caplog.records if r.name == "layer3.lifecycle"]
        assert len(records) == 1, f"Expected 1 record, got {len(records)}"
        evt = records[0].layer3_event  # type: ignore[attr-defined]
        assert evt["event"] == "test_event"
        assert evt["request_id"] == "req-unit-001"
        assert evt["operator_ref"] == "op-hash-abc"
        assert evt["product_id"] == "prod-123"
        assert evt["lifecycle_status"] == "draft"

    def test_none_fields_are_dropped(self, caplog):
        """Fields with None values are NOT included in the bounded dict."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            emit_lifecycle_event(
                "test_event_none",
                request_id=None,
                operator_ref=None,
                product_id="prod-456",
                classification=None,
            )
        records = [r for r in caplog.records if r.name == "layer3.lifecycle"]
        assert len(records) == 1
        evt = records[0].layer3_event  # type: ignore[attr-defined]
        assert "request_id" not in evt
        assert "operator_ref" not in evt
        assert "classification" not in evt
        assert evt["product_id"] == "prod-456"

    def test_request_id_in_extra(self, caplog):
        """request_id is present in the record's extra (not just in layer3_event)."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            emit_lifecycle_event(
                "test_event_rid",
                request_id="req-999",
                operator_ref="op-x",
            )
        records = [r for r in caplog.records if r.name == "layer3.lifecycle"]
        assert len(records) == 1
        # request_id is injected as an extra field directly on the record too
        assert getattr(records[0], "request_id", None) == "req-999"

    def test_swallows_exceptions(self, monkeypatch):
        """emit_lifecycle_event must not raise even if the logger raises."""
        import app.services.layer3_lifecycle_events as mod

        def _raise(*args, **kwargs):
            raise RuntimeError("logger exploded")

        monkeypatch.setattr(mod._lifecycle_logger, "info", _raise)
        # Must not raise.
        emit_lifecycle_event("safe_event", request_id="req-x", operator_ref=None)


# ===========================================================================
# UNIT TESTS — bounded_operator_ref
# ===========================================================================


class TestBoundedOperatorRef:
    def test_none_principal_returns_none(self):
        assert bounded_operator_ref(None) is None

    def test_uses_operator_ref_hash_when_present(self):
        principal = {
            "operator_ref_hash": "abc123hash",
            "workspace_ref_hash": "wsx",
            "auth_owner_mode": "none",
        }
        result = bounded_operator_ref(principal)
        assert result == "abc123hash"

    def test_fallback_blake2b_for_principal_without_ref_hash(self):
        principal = {"auth_owner_mode": "none", "role": None, "access": "write"}
        result = bounded_operator_ref(principal)
        assert result is not None
        # Should be a hex string (16 chars for digest_size=8).
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_stable_across_calls(self):
        principal = {"auth_owner_mode": "none", "role": "owner", "access": "read"}
        r1 = bounded_operator_ref(principal)
        r2 = bounded_operator_ref(principal)
        assert r1 == r2

    def test_never_contains_raw_header_value(self):
        """Even if a principal dict carries a suspicious 'x-forwarded-user'-like field,
        its raw value must NOT appear verbatim in the output."""
        raw_header_value = "attacker-raw-identity-DO-NOT-LEAK"
        principal = {
            "operator_ref_hash": None,  # force fallback path
            "x-forwarded-user": raw_header_value,
            "auth_owner_mode": "proxy",
        }
        # Remove the None key so it doesn't short-circuit to operator_ref_hash=None string.
        principal_clean = {k: v for k, v in principal.items() if v is not None}
        result = bounded_operator_ref(principal_clean)
        # The raw value must never appear in the output.
        assert result is not None
        assert raw_header_value not in (result or "")


# ===========================================================================
# UNIT TESTS — _JsonFormatter extension for layer3_event
# ===========================================================================


class TestJsonFormatterLayer3Event:
    def test_renders_layer3_event_under_event_key(self):
        """_JsonFormatter includes record.layer3_event under 'event' in the JSON line."""
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="layer3.lifecycle",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="layer3.lifecycle",
            args=(),
            exc_info=None,
        )
        bounded = {
            "event": "product_generated",
            "product_id": "prod-789",
            "request_id": "req-fmt-001",
        }
        record.layer3_event = bounded  # type: ignore[attr-defined]
        line = formatter.format(record)
        parsed = json.loads(line)  # must not raise
        assert "event" in parsed
        assert parsed["event"]["event"] == "product_generated"
        assert parsed["event"]["product_id"] == "prod-789"

    def test_json_roundtrip_contains_event(self):
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="layer3.lifecycle",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="layer3.lifecycle",
            args=(),
            exc_info=None,
        )
        record.layer3_event = {"event": "replay_verified", "classification": "reproduced"}  # type: ignore[attr-defined]
        parsed = json.loads(formatter.format(record))
        assert parsed["event"]["classification"] == "reproduced"

    def test_no_layer3_event_leaves_format_intact(self):
        """Records without layer3_event are not changed by the extension."""
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="app.core.observability",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="plain warning",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert "event" not in parsed
        assert parsed["message"] == "plain warning"


# ===========================================================================
# ROUTE-LEVEL TESTS — product_generated event emitted with correct fields
# ===========================================================================


class TestRouteProductGeneratedEvent:
    def test_product_generated_event_emitted_with_bounded_fields(
        self, client: TestClient, tmp_path, caplog
    ):
        """POST /analysis-product/generate emits product_generated event with
        product_id, method_id, method_version, lifecycle_status; no title/body leaked."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            _session_id, product_id, _ws_id, method_id = _seed_and_generate(
                client, tmp_path, request_id="lc-ev-gen-001"
            )

        lifecycle_records = [
            r for r in caplog.records
            if r.name == "layer3.lifecycle"
            and getattr(r, "layer3_event", {}).get("event") == "product_generated"
        ]
        assert lifecycle_records, "Expected at least one product_generated lifecycle record"
        evt = lifecycle_records[-1].layer3_event  # type: ignore[attr-defined]

        # Required bounded fields.
        assert evt["product_id"] == product_id
        assert evt["method_id"] == method_id
        assert isinstance(evt.get("method_version"), int)
        assert evt.get("lifecycle_status") is not None

        # Leak guard: every lifecycle record's keys must stay within the bounded
        # allow-set for its event — asserts the contract precisely rather than
        # substring-matching (which would false-fail on a future key like
        # "decision_basis_body").
        allowed_by_event = {
            "product_generated": {
                "event", "request_id", "operator_ref",
                "product_id", "method_id", "method_version", "lifecycle_status",
            },
            "product_transitioned": {
                "event", "request_id", "operator_ref", "product_id",
                "from_status", "to_status", "review_decision", "decision_reason_code",
            },
            "product_replay_verified": {
                "event", "request_id", "operator_ref",
                "product_id", "reproduced", "classification",
            },
        }
        for r in caplog.records:
            if r.name != "layer3.lifecycle":
                continue
            evt_dict = getattr(r, "layer3_event", {})
            allowed = allowed_by_event.get(evt_dict.get("event"), set())
            extra_keys = set(evt_dict) - allowed
            assert not extra_keys, f"unexpected lifecycle event keys leaked: {extra_keys}"

    def test_product_generated_event_no_raw_payload_or_path(
        self, client: TestClient, tmp_path, caplog
    ):
        """No payload_ref, path, URI, or credential appears in lifecycle records."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            _seed_and_generate(client, tmp_path, request_id="lc-ev-gen-002")

        for record in caplog.records:
            if record.name != "layer3.lifecycle":
                continue
            evt_str = json.dumps(getattr(record, "layer3_event", {}))
            assert "payload_ref" not in evt_str
            assert "payload://" not in evt_str


# ===========================================================================
# ROUTE-LEVEL TESTS — product_replay_verified event emitted
# ===========================================================================


class TestRouteReplayVerifiedEvent:
    def test_replay_verified_event_emitted_with_classification(
        self, client: TestClient, tmp_path, caplog
    ):
        """POST /analysis-product/replay-verify emits product_replay_verified event
        with product_id, reproduced, classification; no body/title leaked."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            session_id, product_id, _ws_id, _method_id = _seed_and_generate(
                client, tmp_path, request_id="lc-ev-replay-001"
            )
            # Trigger replay-verify.
            verify_resp = client.post(
                "/api/v1/layer3/analysis-product/replay-verify",
                json={"session_id": session_id, "analysis_product_id": product_id},
            )
        assert verify_resp.status_code == 200, verify_resp.text

        lifecycle_records = [
            r for r in caplog.records
            if r.name == "layer3.lifecycle"
            and getattr(r, "layer3_event", {}).get("event") == "product_replay_verified"
        ]
        assert lifecycle_records, "Expected at least one product_replay_verified lifecycle record"
        evt = lifecycle_records[-1].layer3_event  # type: ignore[attr-defined]

        assert evt["product_id"] == product_id
        assert evt.get("reproduced") is True
        assert evt.get("classification") == "reproduced"

        # Leak guard: no body/title in any lifecycle record.
        all_lifecycle_text = " ".join(
            json.dumps(getattr(r, "layer3_event", {}))
            for r in caplog.records
            if r.name == "layer3.lifecycle"
        )
        assert "title" not in all_lifecycle_text
        assert "body" not in all_lifecycle_text

    def test_no_product_body_in_any_captured_lifecycle_record(
        self, client: TestClient, tmp_path, caplog
    ):
        """Across a full generate + replay cycle, no product body string is present
        in any captured lifecycle log record."""
        with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
            session_id, product_id, _ws_id, _method_id = _seed_and_generate(
                client, tmp_path, request_id="lc-ev-body-guard-001"
            )
            client.post(
                "/api/v1/layer3/analysis-product/replay-verify",
                json={"session_id": session_id, "analysis_product_id": product_id},
            )

        for record in caplog.records:
            if record.name != "layer3.lifecycle":
                continue
            evt_str = json.dumps(getattr(record, "layer3_event", {}))
            # These strings must never appear in any event payload.
            for forbidden in ("title", "body", "payload_ref", "payload://"):
                assert forbidden not in evt_str, (
                    f"Forbidden field '{forbidden}' found in lifecycle record: {evt_str}"
                )


# ===========================================================================
# REPLAY + LOGGER-LEVEL — codex review hardening
# ===========================================================================


def test_lifecycle_logger_level_is_info():
    """The lifecycle logger pins its own INFO level so events are not silently
    filtered by an inherited WARNING root level (uvicorn/Docker default)."""
    assert logging.getLogger("layer3.lifecycle").level == logging.INFO


def test_generate_replay_emits_no_lifecycle_event(client: TestClient, tmp_path, caplog):
    """An idempotent generate replay (same client_request_id) records replayed=True
    but must NOT emit a new product_generated event — the audit stream records
    real lifecycle changes only."""
    session_id, _product_id, ws_id, method_id = _seed_and_generate(
        client, tmp_path, request_id="lc-ev-replay-001"
    )
    # Drop the first generate's event so only the replay call's records remain.
    caplog.clear()
    # Re-POST the identical generate request -> replayed=True, no new product.
    with caplog.at_level(logging.INFO, logger="layer3.lifecycle"):
        resp = client.post(
            "/api/v1/layer3/analysis-product/generate",
            json={
                "session_id": session_id,
                "client_request_id": "lc-ev-replay-001-gen",  # same id _seed_and_generate used
                "working_set_id": ws_id,
                "method_id": method_id,
            },
        )
    assert resp.status_code == 201, resp.text
    assert resp.json()["replayed"] is True
    gen_events = [
        r for r in caplog.records
        if r.name == "layer3.lifecycle"
        and getattr(r, "layer3_event", {}).get("event") == "product_generated"
    ]
    assert gen_events == [], "an idempotent replay must not emit a product_generated event"
