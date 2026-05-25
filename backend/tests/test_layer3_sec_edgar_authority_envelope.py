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
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.services import layer3_sec_edgar_authority_envelope, layer3_sec_edgar_material_bridge, layer3_workbench
from test_layer3_workbench import _seed_aps_derived_dataset_version


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


def _seed_sec_edgar_dataset(db_session, tmp_path) -> str:
    return _seed_aps_derived_dataset_version(
        db_session,
        tmp_path,
        dataset_version_id="dv-aps-sec-edgar-envelope-001",
        parser_family="sec_edgar_filing",
        typed_content_contract_id="aps_sec_edgar_filing_units_v1",
        source_mode="artifact_sec_edgar_filing_parser",
        parser_contract_id="aps_sec_edgar_filing_parser_v1",
    )


def test_sec_edgar_text_table_authority_envelope_ready(db_session, tmp_path) -> None:
    dataset_version_id = _seed_sec_edgar_dataset(db_session, tmp_path)

    result = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    assert result["schema_id"] == "layer3.sec_edgar_text_table_authority_envelope_validation.v1"
    assert result["authority_envelope_mode"] == "sec_edgar_text_table_authority_envelope_validation_runtime_v1"
    assert result["authority_envelope_state"] == "sec_edgar_text_table_authority_envelope_ready"
    assert result["source_family"] == "sec_edgar_text_table"
    assert result["parser_family"] == "sec_edgar_filing"
    assert result["typed_content_contract_id"] == "aps_sec_edgar_filing_units_v1"
    assert result["authority_envelope_hash"]
    assert result["authority_envelope_ref"].startswith("sec-edgar-text-table-authority-envelope://")
    assert result["material_analysis_payload"]["payload_shape"] == "mixed_narrative_table"
    assert result["material_analysis_payload"]["layer3_material_bridge_admitted_now"] is False
    assert result["negative_invariants"]["sec_edgar_network_fetch_admitted"] is False
    assert result["negative_invariants"]["connector_dispatch_enabled"] is False
    assert result["provenance_summary"]["redaction"]["raw_storage_ref_exposed"] is False
    assert "aps-target-artifacts/run-001" not in str(result)


def test_sec_edgar_text_table_authority_envelope_blocks_wrong_parser(db_session, tmp_path) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(
        db_session,
        tmp_path,
        dataset_version_id="dv-aps-csv-not-sec-edgar",
    )

    result = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    reasons = {item["reason"] for item in result["status_projection"]["blocked_reasons"]}
    assert result["authority_envelope_state"] == "sec_edgar_text_table_authority_envelope_blocked"
    assert "sec_edgar_text_table_authority_parser_family_mismatch" in reasons
    assert "sec_edgar_text_table_authority_source_family_mismatch" in reasons
    assert "sec_edgar_text_table_authority_typed_content_contract_mismatch" in reasons


def test_sec_edgar_text_table_authority_envelope_blocks_stale_hash(db_session, tmp_path) -> None:
    dataset_version_id = _seed_sec_edgar_dataset(db_session, tmp_path)
    first = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    result = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "expected_authority_envelope_hash": "f" * 64,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    reasons = {item["reason"] for item in result["status_projection"]["blocked_reasons"]}
    assert first["authority_envelope_hash"] != "f" * 64
    assert result["authority_envelope_state"] == "sec_edgar_text_table_authority_envelope_blocked"
    assert "sec_edgar_text_table_authority_stale_envelope_hash" in reasons


def test_sec_edgar_text_table_material_bridge_returns_redacted_gate_b_payload(db_session, tmp_path) -> None:
    dataset_version_id = _seed_sec_edgar_dataset(db_session, tmp_path)
    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    result = layer3_sec_edgar_material_bridge.prepare_sec_edgar_text_table_material_authority_bridge(
        {
            "client_request_id": "sec-edgar-material-bridge-ready",
            "bridge_mode": "sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1",
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": envelope["authority_envelope_hash"],
            "authority_envelope_ref": envelope["authority_envelope_ref"],
            "expected_materialization_receipt_hash": envelope["materialization_receipt_hash"],
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    assert result["schema_id"] == "layer3.sec_edgar_text_table_material_authority_bridge.v1"
    assert result["mode"] == "sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1"
    assert result["bridge_state"] == "sec_edgar_text_table_layer3_material_authority_bridge_ready"
    assert result["material_candidate"]["source_class"] == "dataset_version"
    assert result["material_candidate"]["planning_shape_family"] == "mixed_narrative_table"
    assert result["material_preview_request_basis"]["dataset_version_ids"] == [dataset_version_id]
    assert result["gate_b_decision_payload"]["material_preview_hash"] == result["material_preview_hash"]
    assert result["gate_b_decision_manifest_id"]
    assert result["negative_invariants"]["direct_unbridged_sec_edgar_dataset_version_material_authority_admitted"] is False
    assert "aps-target-artifacts/run-001" not in str(result)
    assert str(tmp_path) not in str(result)

    gate_b = layer3_workbench.gate_b_decision(db_session, result["gate_b_decision_payload"])
    assert gate_b["next_state"] == "gate_c_preview_ready"
    assert gate_b["material_preview_hash"] == result["material_preview_hash"]
    assert gate_b["gate_b_decision_manifest_id"] == result["gate_b_decision_manifest_id"]


def test_sec_edgar_text_table_material_bridge_blocks_stale_envelope_hash(db_session, tmp_path) -> None:
    dataset_version_id = _seed_sec_edgar_dataset(db_session, tmp_path)

    result = layer3_sec_edgar_material_bridge.prepare_sec_edgar_text_table_material_authority_bridge(
        {
            "client_request_id": "sec-edgar-material-bridge-stale-envelope",
            "bridge_mode": "sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1",
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": "e" * 64,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    reasons = {item["reason"] for item in result["status_projection"]["blocked_reasons"]}
    assert result["bridge_state"] == "sec_edgar_text_table_layer3_material_authority_bridge_blocked"
    assert "missing_ready_envelope" in reasons
    assert "sec_edgar_text_table_authority_stale_envelope_hash" in reasons
    assert result["material_preview_hash"] is None


def test_sec_edgar_text_table_material_bridge_blocks_preview_hash_mismatch(db_session, tmp_path) -> None:
    dataset_version_id = _seed_sec_edgar_dataset(db_session, tmp_path)
    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    result = layer3_sec_edgar_material_bridge.prepare_sec_edgar_text_table_material_authority_bridge(
        {
            "client_request_id": "sec-edgar-material-bridge-preview-mismatch",
            "bridge_mode": "sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1",
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": envelope["authority_envelope_hash"],
            "expected_material_preview_hash": "d" * 64,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db_session,
    )

    reasons = {item["reason"] for item in result["status_projection"]["blocked_reasons"]}
    assert result["bridge_state"] == "sec_edgar_text_table_layer3_material_authority_bridge_blocked"
    assert "material_preview_hash_mismatch" in reasons
