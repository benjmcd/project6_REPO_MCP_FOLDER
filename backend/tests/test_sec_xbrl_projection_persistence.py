from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import L3SecXbrlProjectionFact, L3SecXbrlProjectionSet
from app.services import layer3_sec_xbrl_projection_persistence as persistence


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "backend" / "alembic" / "versions" / "0038_layer3_sec_xbrl_projection_persistence.py"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _hash(char: str) -> str:
    return char * 64


def _projection(*, rows: list[dict[str, Any]] | None = None, period_ref: str = "fy-period-1") -> dict[str, Any]:
    return {
        "status": "canonical_multi_period_projection_ready",
        "sector_family_presence": {
            "activation_rule": "concept_presence_not_sic_gated",
            "active_families": ["banking"],
        },
        "periods": [
            {
                "period_ref": period_ref,
                "period_index": 1,
                "projection": {
                    "status": "canonical_projection_ready",
                    "dataset_version_id": "dv-redacted-1",
                    "sidecar_receipt_hash": _hash("b"),
                    "value_store_hash": _hash("c"),
                    "concepts": rows
                    if rows is not None
                    else [
                        _row("CashAndDueFromBanks", "balance"),
                        _row("InterestIncome", "income", family="banking"),
                    ],
                },
            }
        ],
    }


def _row(canonical_id: str, statement: str, *, family: str = "universal") -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": family,
        "status": "projected_oracle_confirmed",
        "source_qname": f"us-gaap:{canonical_id}",
        "oracle_confirmed": True,
        "mapping_method": "primary_taxonomy_sidecar_value_store_projection",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "unit_class": "monetary",
        "provenance_complete": True,
        "value_redacted": True,
        "resolved_fact_provenance_present": True,
        "sidecar_receipt_hash": _hash("b"),
        "value_store_hash": _hash("c"),
        "dataset_version_id": "dv-redacted-1",
    }


def _materialize(db_session, projection: dict[str, Any] | None = None, *, request_id: str = "request-1") -> dict[str, Any]:
    return persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id=request_id,
        projection=projection or _projection(),
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )


def test_sec_xbrl_projection_persistence_materializes_redacted_rows(db_session) -> None:
    response = _materialize(db_session)

    assert response["status"] == "materialized"
    assert response["schema_id"] == persistence.PROJECTION_SET_SCHEMA_ID
    assert response["fact_count"] == 2
    assert response["redaction_policy"] == "redacted_no_values"
    assert response["idempotent_replay"] is False
    assert response["runtime_default_enabled"] is False
    assert response["value_reveal_performed"] is False
    assert response["source_acquisition_performed"] is False
    assert response["arelle_invoked"] is False

    set_row = db_session.query(L3SecXbrlProjectionSet).one()
    facts = db_session.query(L3SecXbrlProjectionFact).order_by(
        L3SecXbrlProjectionFact.statement,
        L3SecXbrlProjectionFact.statement_row_index,
    ).all()
    assert set_row.projection_schema_id == "layer3.sec_xbrl_projection_set.v1"
    assert set_row.projection_summary_json["fact_count"] == 2
    assert set_row.period_refs_json == [{"period_ref": "fy-period-1", "period_index": 1}]
    assert [fact.value_redacted for fact in facts] == [True, True]
    assert {fact.statement for fact in facts} == {"balance", "income"}
    assert all(fact.resolved_fact_provenance_present is True for fact in facts)


def test_sec_xbrl_projection_persistence_replays_same_request_and_basis(db_session) -> None:
    first = _materialize(db_session, request_id="request-replay")
    second = _materialize(db_session, request_id="request-replay")
    third = _materialize(db_session, request_id="request-same-basis")

    assert second["idempotent_replay"] is True
    assert third["idempotent_replay"] is True
    assert second["sec_xbrl_projection_set_id"] == first["sec_xbrl_projection_set_id"]
    assert third["sec_xbrl_projection_set_id"] == first["sec_xbrl_projection_set_id"]
    assert db_session.query(L3SecXbrlProjectionSet).count() == 1
    assert db_session.query(L3SecXbrlProjectionFact).count() == 2


def test_sec_xbrl_projection_persistence_rejects_client_request_conflict(db_session) -> None:
    _materialize(db_session, request_id="request-conflict")
    changed = _projection(rows=[_row("DifferentCanonicalFact", "income")])

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, changed, request_id="request-conflict")

    assert exc.value.code == "sec_xbrl_projection_persistence_client_request_conflict"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 1
    assert db_session.query(L3SecXbrlProjectionFact).count() == 2


def test_sec_xbrl_projection_persistence_rejects_raw_value_fields(db_session) -> None:
    row = _row("CashAndDueFromBanks", "balance")
    row["_value"] = "1000000"

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, _projection(rows=[row]))

    assert exc.value.code == "sec_xbrl_projection_persistence_raw_authority_not_admitted"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0
    assert db_session.query(L3SecXbrlProjectionFact).count() == 0


def test_sec_xbrl_projection_persistence_rejects_unredacted_row(db_session) -> None:
    row = _row("CashAndDueFromBanks", "balance")
    row["value_redacted"] = False

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, _projection(rows=[row]))

    assert exc.value.code == "sec_xbrl_projection_persistence_redaction_required"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0


def test_sec_xbrl_projection_persistence_rejects_raw_identity_and_paths(db_session) -> None:
    row = _row("CashAndDueFromBanks", "balance")
    row["source_qname"] = "https://www.sec.gov/Archives/edgar/data/0000000000"

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, _projection(rows=[row], period_ref="2024-12-31"))

    assert exc.value.code == "sec_xbrl_projection_persistence_raw_reference_not_admitted"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0


def test_sec_xbrl_projection_persistence_rejects_raw_issuer_identity_keys(db_session) -> None:
    row = _row("CashAndDueFromBanks", "balance")
    row["Company_Name"] = "Example Bank Corp"

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, _projection(rows=[row]))

    assert exc.value.code == "sec_xbrl_projection_persistence_raw_authority_not_admitted"
    assert exc.value.details == {"field": "Company_Name"}
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0


def test_sec_xbrl_projection_persistence_rejects_empty_projection(db_session) -> None:
    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, _projection(rows=[]))

    assert exc.value.code == "sec_xbrl_projection_persistence_empty_projection"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0


def test_sec_xbrl_projection_persistence_rejects_raw_resolved_fact_authority(db_session) -> None:
    row = _row("CashAndDueFromBanks", "balance")
    row["resolved_fact_id"] = "fact-raw-id"

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError) as exc:
        _materialize(db_session, _projection(rows=[row]))

    assert exc.value.code == "sec_xbrl_projection_persistence_raw_authority_not_admitted"
    assert db_session.query(L3SecXbrlProjectionSet).count() == 0


def test_sec_xbrl_projection_persistence_leaves_no_partial_rows_on_late_invalid_row(db_session) -> None:
    valid = _row("CashAndDueFromBanks", "balance")
    invalid = _row("InterestIncome", "income")
    invalid["amount"] = "100"

    with pytest.raises(persistence.SecXbrlProjectionPersistenceError):
        _materialize(db_session, _projection(rows=[valid, invalid]))

    assert db_session.query(L3SecXbrlProjectionSet).count() == 0
    assert db_session.query(L3SecXbrlProjectionFact).count() == 0


def test_sec_xbrl_projection_persistence_tables_are_registered_in_metadata() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    try:
        assert "l3_sec_xbrl_projection_set" in inspector.get_table_names()
        assert "l3_sec_xbrl_projection_fact" in inspector.get_table_names()
        fact_columns = {column["name"] for column in inspector.get_columns("l3_sec_xbrl_projection_fact")}
        assert "value_redacted" in fact_columns
        assert "resolved_fact_provenance_present" in fact_columns
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_sec_xbrl_projection_persistence_migration_declares_additive_tables() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location("migration_0038_sec_xbrl_projection", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0038_layer3_sec_xbrl_projection_persistence"
    assert module.down_revision == "0037_layer3_source_directory_bigint"
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_projection_set" in source
    assert "l3_sec_xbrl_projection_fact" in source
    assert "drop_table_idempotent(\"l3_sec_xbrl_projection_fact\")" in source
