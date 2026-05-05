from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3Session
from app.services.layer3_plan_revision_state import (
    PLAN_REVISION_CONTROL_CONTEXT_KEY,
    PLAN_REVISION_CONTROL_SCHEMA_ID,
    PLAN_REVISION_DECISIONS,
    PLAN_REVISION_STATE_BY_DECISION,
    plan_revision_control_from_session,
    plan_revision_control_record,
)


def test_plan_revision_control_record_maps_supported_decisions() -> None:
    assert PLAN_REVISION_DECISIONS == {"reject_current_preview", "request_revision"}
    assert PLAN_REVISION_STATE_BY_DECISION == {
        "reject_current_preview": "plan_rejected",
        "request_revision": "plan_revision_requested",
    }

    rejected = plan_revision_control_record(
        source_preview_id="preview-1",
        source_preview_hash="hash-1",
        operator_decision="reject_current_preview",
        operator_note="Needs a different plan basis.",
        created_at="2026-05-05T00:00:00Z",
    )
    requested = plan_revision_control_record(
        source_preview_id="preview-2",
        source_preview_hash="hash-2",
        operator_decision="request_revision",
        operator_note="",
        created_at="2026-05-05T00:00:01Z",
    )

    assert rejected == {
        "schema_id": PLAN_REVISION_CONTROL_SCHEMA_ID,
        "state": "plan_rejected",
        "source_preview_id": "preview-1",
        "source_preview_hash": "hash-1",
        "operator_decision": "reject_current_preview",
        "operator_note_recorded": True,
        "approval_available": False,
        "execution_started": False,
        "created_at": "2026-05-05T00:00:00Z",
    }
    assert requested["state"] == "plan_revision_requested"
    assert requested["operator_note_recorded"] is False
    assert requested["approval_available"] is False
    assert requested["execution_started"] is False


def test_plan_revision_control_record_rejects_unsupported_decision() -> None:
    with pytest.raises(ValueError, match="Unsupported plan revision decision"):
        plan_revision_control_record(
            source_preview_id="preview-1",
            source_preview_hash="hash-1",
            operator_decision="approve_anyway",
            operator_note="",
            created_at="2026-05-05T00:00:00Z",
        )


def test_plan_revision_control_from_session_requires_current_schema() -> None:
    record = plan_revision_control_record(
        source_preview_id="preview-1",
        source_preview_hash="hash-1",
        operator_decision="request_revision",
        operator_note="",
        created_at="2026-05-05T00:00:00Z",
    )
    session = L3Session(
        session_id="session-1",
        selection_manifest_id="manifest-1",
        summary_json={PLAN_REVISION_CONTROL_CONTEXT_KEY: record},
    )
    missing = L3Session(session_id="missing", selection_manifest_id="manifest-missing", summary_json={})
    wrong_schema = L3Session(
        session_id="wrong-schema",
        selection_manifest_id="manifest-wrong",
        summary_json={
            PLAN_REVISION_CONTROL_CONTEXT_KEY: {
                **record,
                "schema_id": "layer3.plan_revision_control.v0",
            }
        },
    )

    assert plan_revision_control_from_session(session) == record
    assert plan_revision_control_from_session(missing) is None
    assert plan_revision_control_from_session(wrong_schema) is None
    assert plan_revision_control_from_session(None) is None
