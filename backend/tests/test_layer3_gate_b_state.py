from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import L3Session
from app.services.layer3_gate_b_state import (
    GATE_B_IDEMPOTENCY_CONTEXT_KEY,
    GATE_B_IDEMPOTENCY_SCHEMA_ID,
    find_gate_b_idempotency_session,
    gate_b_idempotency_from_session,
    gate_b_idempotency_record,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _record(client_request_id: str = "req-gate-b") -> dict:
    return gate_b_idempotency_record(
        client_request_id=client_request_id,
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="hash-1",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )


def test_gate_b_idempotency_record_round_trips_from_session() -> None:
    record = _record()
    session = L3Session(
        session_id="session-1",
        selection_manifest_id="manifest-1",
        operator_context_json={GATE_B_IDEMPOTENCY_CONTEXT_KEY: record},
    )

    assert record["schema_id"] == GATE_B_IDEMPOTENCY_SCHEMA_ID
    assert gate_b_idempotency_from_session(session) == record


def test_gate_b_idempotency_from_session_rejects_missing_or_wrong_schema() -> None:
    missing = L3Session(session_id="missing", selection_manifest_id="manifest-missing", operator_context_json={})
    wrong_schema = L3Session(
        session_id="wrong-schema",
        selection_manifest_id="manifest-wrong",
        operator_context_json={
            GATE_B_IDEMPOTENCY_CONTEXT_KEY: {
                **_record(),
                "schema_id": "layer3.gate_b_idempotency.v0",
            }
        },
    )

    assert gate_b_idempotency_from_session(missing) is None
    assert gate_b_idempotency_from_session(wrong_schema) is None


def test_find_gate_b_idempotency_session_returns_matching_record(db_session) -> None:
    matching_record = _record("req-match")
    db_session.add_all(
        [
            L3Session(
                session_id="session-other",
                selection_manifest_id="manifest-other",
                operator_context_json={GATE_B_IDEMPOTENCY_CONTEXT_KEY: _record("req-other")},
            ),
            L3Session(
                session_id="session-match",
                selection_manifest_id="manifest-match",
                operator_context_json={GATE_B_IDEMPOTENCY_CONTEXT_KEY: matching_record},
            ),
        ]
    )
    db_session.commit()

    result = find_gate_b_idempotency_session(db_session, client_request_id="req-match")

    assert result is not None
    session, record = result
    assert session.session_id == "session-match"
    assert record == matching_record
    assert find_gate_b_idempotency_session(db_session, client_request_id="req-missing") is None
    assert find_gate_b_idempotency_session(db_session, client_request_id="") is None
