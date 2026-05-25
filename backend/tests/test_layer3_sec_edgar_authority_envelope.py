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
from app.services import layer3_sec_edgar_authority_envelope
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
