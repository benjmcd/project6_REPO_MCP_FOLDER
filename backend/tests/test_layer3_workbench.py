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

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    L3AnalysisGroup,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
)
from app.services import layer3_workbench
from app.services.layer3_workbench import Layer3WorkbenchError


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _preflight_source_material() -> tuple[dict, dict, dict]:
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight",
            "natural_language_intent": "Review deterministic dataset and APS document material.",
            "manual_constraints": {"source_classes": ["dataset_version", "aps_content_document"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version", "aps_content_document"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [item["source_candidate_id"] for item in source["source_candidates"]],
            "query_basis": {"terms": ["deterministic", "document"]},
        }
    )
    return preflight, source, material


def _gate_b_payload(preflight: dict, source: dict, material: dict) -> dict:
    candidates = material["material_candidates"]
    first, second = candidates
    return {
        "client_request_id": "req-gate-b",
        "preflight_id": preflight["preflight_id"],
        "source_set_id": source["source_set_id"],
        "material_preview_id": material["material_preview_id"],
        "candidate_decisions": [
            {
                "candidate_id": first["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": {
                    "source_ref": first["source_ref"],
                    "query_basis": first["query_basis"],
                    "provenance_ref": first["provenance_ref"],
                },
            },
            {
                "candidate_id": second["candidate_id"],
                "decision": "flagged",
                "operator_reason": "Held for second-slice review.",
                "decision_basis": {
                    "source_ref": second["source_ref"],
                    "query_basis": second["query_basis"],
                    "provenance_ref": second["provenance_ref"],
                },
            },
        ],
        "commit_reason": "pytest_gate_b",
        "actor": "pytest",
    }


def test_bootstrap_is_explicit_about_first_slice_limits() -> None:
    result = layer3_workbench.bootstrap()

    assert result["route"] == "/review/layer3"
    assert result["api_root"] == "/api/v1/layer3"
    assert result["features"]["analysis_execution"] is False
    assert result["features"]["rag_vector_retrieval"] is False
    assert result["features"]["typing_override_enabled"] is False
    assert result["unavailable_gate_labels"] == ["plan", "execution", "results", "package"]
    assert result["authority_rail"]["browser_only_state"] == [
        "expanded_rows",
        "hidden_uncommitted_candidates",
        "selected_tab",
    ]


def test_preflight_fails_closed_on_missing_intent_and_unsupported_sources() -> None:
    with pytest.raises(Layer3WorkbenchError) as empty:
        layer3_workbench.preflight({"natural_language_intent": " "})
    assert empty.value.error_code == "empty_intent"
    assert empty.value.status == "blocked"

    with pytest.raises(Layer3WorkbenchError) as unsupported:
        layer3_workbench.preflight(
            {
                "natural_language_intent": "Review material.",
                "manual_constraints": {"source_classes": ["rag_vector_index"]},
            }
        )
    assert unsupported.value.error_code == "unsupported_source_class"
    assert unsupported.value.next_allowed_actions == ["choose_supported_sources"]


def test_preview_shapes_keep_owner_service_and_planning_shape_separate() -> None:
    preflight, source, material = _preflight_source_material()

    assert preflight["eligible_for_source_selection"] is True
    assert {item["source_class"] for item in source["source_candidates"]} == {
        "dataset_version",
        "aps_content_document",
    }
    shapes = {
        item["owner_service_source_shape"]: item["planning_shape_family"]
        for item in material["material_candidates"]
    }
    assert shapes == {"dataset_version": "tabular_numeric", "aps_content_document": "document_chunks"}
    assert material["authority_rail"]["persistence_mode"] == "preview_only"


def test_gate_b_persists_only_approved_material_through_layer3_owner_services(db_session) -> None:
    preflight, source, material = _preflight_source_material()

    result = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    assert result["next_state"] == "gate_c_preview_ready"
    assert len(result["approved_candidate_ids"]) == 1
    assert len(result["flagged_candidate_ids"]) == 1
    assert result["authority_rail"]["persistence_mode"] == "durable_layer3_control"
    assert result["authority_rail"]["approved_material_count"] == 1
    assert result["authority_rail"]["flagged_material_count"] == 1

    session = db_session.get(L3Session, result["session_id"])
    manifest = db_session.get(L3SelectionManifest, result["selection_manifest_id"])
    snapshots = db_session.query(L3MaterialSnapshot).all()

    assert session is not None
    assert session.status == "completed"
    assert session.operator_context_json["layer3_gate_b_decision_manifest_v1"]["schema_id"] == (
        "layer3.gate_b_decision_manifest.v1"
    )
    assert session.summary_json["gate_b_summary_v1"]["approved"] == 1
    assert session.summary_json["gate_b_summary_v1"]["flagged"] == 1
    assert manifest is not None
    assert len(manifest.manifest_json["items"]) == 1
    assert len(snapshots) == 1
    assert snapshots[0].source_shape == "dataset_version"
    assert Path(snapshots[0].payload_ref).is_file()


def test_gate_c_preview_is_non_authoritative_and_override_is_unavailable(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    preview = layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c", "session_id": gate_b["session_id"], "commit_typing": False},
    )
    override = layer3_workbench.gate_c_override_unavailable({"client_request_id": "req-override"})

    assert preview["next_state"] == "first_slice_complete"
    assert preview["override_allowed"] is False
    assert preview["typing_records"][0]["authoritative"] is False
    assert preview["analysis_units"][0]["authoritative"] is False
    assert db_session.query(L3TypingRecord).count() == 0
    assert db_session.query(L3AnalysisUnit).count() == 0
    assert override["status"] == "unavailable"
    assert override["error_code"] == "override_unavailable"


def test_gate_c_commit_typing_materializes_owner_service_records(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    committed = layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c-commit", "session_id": gate_b["session_id"], "commit_typing": True},
    )

    assert committed["next_state"] == "first_slice_complete"
    assert committed["override_allowed"] is False
    assert committed["typing_records"][0]["authoritative"] is True
    assert committed["analysis_units"][0]["authoritative"] is True
    assert db_session.query(L3TypingRecord).count() == 1
    assert db_session.query(L3AnalysisUnit).count() == 1
    assert db_session.query(L3AnalysisGroup).count() == 1
    assert db_session.query(L3AnalysisSet).count() == 1

    summary = layer3_workbench.session_summary(db_session, gate_b["session_id"])
    assert summary["current_gate"] == "complete"
    assert summary["gate_c_summary"]["typing_committed"] is True
    assert summary["authority_rail"]["typing_status"] == "committed"


def test_session_summary_reflects_gate_b_counts_without_overclaiming_typing_commit(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    summary = layer3_workbench.session_summary(db_session, gate_b["session_id"])

    assert summary["current_gate"] == "gate_c"
    assert summary["gate_b_summary"] == {"approved": 1, "denied": 0, "isolated": 0, "flagged": 1}
    assert summary["gate_c_summary"]["typing_committed"] is False
    assert summary["downstream_unavailable"] == ["plan", "execution", "results", "package"]
