from __future__ import annotations

from collections import Counter
from decimal import Decimal
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    L3SecXbrlProjectionFact,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketRow,
    L3SecXbrlStatementPacketSet,
    L3SecXbrlStatementPacketStatement,
)
from app.services import layer3_sec_xbrl_projection_persistence as projection_persistence
from app.services import layer3_sec_xbrl_statement_assembly as assembly
from app.services import layer3_sec_xbrl_statement_packet_persistence as packet_persistence


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "backend" / "alembic" / "versions" / "0039_layer3_sec_xbrl_statement_packet_persistence.py"
REDACTION_CONSTRAINT_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0041_layer3_sec_xbrl_redaction_constraints.py"
)
PERIOD_UNIQUE_MIGRATION_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0043_layer3_sec_xbrl_statement_packet_row_period_unique.py"
)


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


def _projection_rows() -> list[dict[str, Any]]:
    return [
        _projection_row("Revenue", "income"),
        _projection_row("TotalAssets", "balance"),
        _projection_row("OperatingCashFlow", "cashflow"),
    ]


def _projection_row(canonical_id: str, statement: str, *, family: str = "universal") -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": family,
        "status": "projected_oracle_confirmed",
        "source_qname": f"us-gaap:{canonical_id}",
        "oracle_confirmed": True,
        "mapping_method": "fixture",
        "mapping_confidence": "fixture",
        "unit_class": "monetary",
        "provenance_complete": True,
        "value_redacted": True,
        "resolved_fact_provenance_present": True,
        "sidecar_receipt_hash": _hash("b"),
        "value_store_hash": _hash("c"),
        "dataset_version_id": "dv-redacted-1",
    }


def _persisted_projection(db_session, *, periods: int = 1) -> dict[str, Any]:
    period_payload = []
    for index in range(1, periods + 1):
        period_payload.append(
            {
                "period_ref": f"fy-period-{index}",
                "period_index": index,
                "projection": {
                    "status": "canonical_projection_ready",
                    "dataset_version_id": "dv-redacted-1",
                    "sidecar_receipt_hash": _hash("b"),
                    "value_store_hash": _hash("c"),
                    "concepts": _projection_rows(),
                },
            }
        )
    return projection_persistence.materialize_redacted_projection_set(
        db_session,
        client_request_id=f"projection-{periods}",
        projection={
            "status": "canonical_multi_period_projection_ready",
            "sector_family_presence": {"activation_rule": "concept_presence_not_sic_gated"},
            "periods": period_payload,
        },
        source_report_schema_id="diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
        source_report_hash=_hash("a"),
    )


def _packet(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    projection_items = [
        _assembly_row("Revenue", "income"),
        _assembly_row("TotalAssets", "balance"),
        _assembly_row("OperatingCashFlow", "cashflow"),
    ]
    packet = assembly.assemble_reviewable_statement_packet(
        projection_items=projection_items,
        organization_result={
            "contract_passed": True,
            "contract_b_authoritative_organization": True,
            "contract_every_fact_id_bound": True,
            "contract_derived_inputs_bound_and_corroborated": True,
            "normalized_fact_count": 3,
            "organized_count": 3,
            "unjoined_count": 0,
            "a_divergent_count": 0,
            "a_role_unknown_count": 0,
        },
    )
    if rows is not None:
        for statement in packet["statements"]:
            statement_rows = [row for row in rows if row.get("statement") == statement["statement"]]
            status_counts = Counter(str(row.get("status") or "") for row in statement_rows)
            family_counts = Counter(str(row.get("family") or "universal") for row in statement_rows)
            statement["rows"] = statement_rows
            statement["line_count"] = len(statement_rows)
            statement["projected_count"] = sum(
                1 for row in statement_rows if str(row.get("status") or "").startswith("projected")
            )
            statement["derived_count"] = sum(1 for row in statement_rows if row.get("status") == "derived")
            statement["provenance_complete_count"] = sum(
                1 for row in statement_rows if row.get("provenance_complete") is True
            )
            statement["review_exception_count"] = sum(
                1
                for row in statement_rows
                if row.get("provenance_complete") is not True
                or row.get("oracle_confirmed") is False
                or row.get("oracle_confirmed") == "oracle_absent"
            )
            statement["status_counts"] = dict(sorted(status_counts.items()))
            statement["family_counts"] = dict(sorted(family_counts.items()))
        packet["total_review_rows"] = len(rows)
        packet["provenance_complete_count"] = sum(1 for row in rows if row.get("provenance_complete") is True)
        packet["review_exception_count"] = sum(
            1
            for row in rows
            if row.get("provenance_complete") is not True
            or row.get("oracle_confirmed") is False
            or row.get("oracle_confirmed") == "oracle_absent"
        )
        packet["review_ready"] = bool(rows) and packet["provenance_complete_count"] == len(rows)
    return packet


def _assembly_row(canonical_id: str, statement: str) -> dict[str, Any]:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": "universal",
        "status": "projected_oracle_confirmed",
        "source_qname": f"us-gaap:{canonical_id}",
        "oracle_confirmed": True,
        "mapping_method": "fixture",
        "mapping_confidence": "fixture",
        "unit_class": "monetary",
        "provenance_complete": True,
        "_value": Decimal("1"),
    }


def _materialize(db_session, packet: dict[str, Any] | None = None, *, request_id: str = "packet-1") -> dict[str, Any]:
    projection = _persisted_projection(db_session)
    return packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id=request_id,
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        packet=packet or _packet(),
    )


def test_statement_packet_persistence_materializes_redacted_packet_rows(db_session) -> None:
    response = _materialize(db_session)

    assert response["status"] == "materialized"
    assert response["schema_id"] == assembly.STATEMENT_ASSEMBLY_SCHEMA_ID
    assert response["statement_count"] == 3
    assert response["row_count"] == 3
    assert response["value_policy"] == "redacted_no_values"
    assert response["runtime_default_enabled"] is False
    assert response["value_reveal_performed"] is False
    assert response["operator_workflow_enabled"] is False

    packet_set = db_session.query(L3SecXbrlStatementPacketSet).one()
    statements = db_session.query(L3SecXbrlStatementPacketStatement).all()
    rows = db_session.query(L3SecXbrlStatementPacketRow).all()
    assert packet_set.packet_schema_id == "layer3.sec_xbrl_reviewable_statement_packet.v1"
    assert packet_set.packet_summary_json["total_review_rows"] == 3
    assert len(statements) == 3
    assert {row.value_redacted for row in rows} == {True}
    assert {row.sec_xbrl_projection_fact_id for row in rows} == {
        fact.sec_xbrl_projection_fact_id for fact in db_session.query(L3SecXbrlProjectionFact).all()
    }


def test_statement_packet_persistence_replays_same_request_and_basis(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()

    first = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-replay",
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        packet=packet,
    )
    second = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-replay",
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        packet=packet,
    )
    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-same-basis",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert second["idempotent_replay"] is True
    assert second["sec_xbrl_statement_packet_set_id"] == first["sec_xbrl_statement_packet_set_id"]
    assert exc.value.code == "sec_xbrl_statement_packet_persistence_basis_replay_request_mismatch"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 1
    assert db_session.query(L3SecXbrlStatementPacketRow).count() == 3


def test_statement_packet_persistence_rejects_client_request_conflict(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-conflict",
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        packet=packet,
    )
    changed = _packet()
    changed["organization_contract"]["a_role_unknown_count"] = 1

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-conflict",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=changed,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_client_request_conflict"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 1


def test_statement_packet_persistence_rejects_header_count_mismatch(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["review_exception_count"] = 1

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-header-count-mismatch",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_packet_summary_invalid"
    assert exc.value.details["field"] == "review_exception_count"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_statement_count_mismatch(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["statements"][0]["line_count"] = 9

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-statement-count-mismatch",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_packet_summary_invalid"
    assert exc.value.details["field"] == "line_count"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_raw_value_fields(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["statements"][0]["rows"][0]["amount"] = "100"

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-raw-value",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_raw_authority_not_admitted"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_lexical_value_fields(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["statements"][0]["rows"][0]["lexical_value"] = "100"

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-lexical-value",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_raw_authority_not_admitted"
    assert exc.value.details == {"field": "lexical_value"}
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_local_ref_client_request_id(db_session) -> None:
    projection = _persisted_projection(db_session)

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="file:///workspace/project/runtime/sec/packet.json",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=_packet(),
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_raw_reference_not_admitted"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_residual_magnitudes(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["identity_rollup"]["identity_residuals"] = [
        {
            "identity_id": "assets_identity",
            "relative_magnitude": "1E+0",
            "residual_abs": "1",
        }
    ]

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-residuals",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_residual_magnitudes_not_admitted"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_non_boolean_identity_tolerance(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["identity_rollup"]["identity_residuals_within_tolerance"] = "false"

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-identity-tolerance-string",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_boolean_required"
    assert exc.value.details == {"field": "identity_residuals_within_tolerance"}
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_unadmitted_organization_contract_numeric_alias(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["organization_contract"]["mean"] = "12345.67"

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-organization-contract-mean",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_organization_contract_invalid"
    assert exc.value.details == {"fields": ["mean"]}
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_rejects_empty_packet(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet(rows=[])

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-empty",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_empty_packet"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_requires_period_binding_for_multi_period_projection(db_session) -> None:
    projection = _persisted_projection(db_session, periods=2)

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError) as exc:
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-multi-period",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=_packet(),
        )

    assert exc.value.code == "sec_xbrl_statement_packet_persistence_period_binding_required"
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0


def test_statement_packet_persistence_allows_same_statement_row_index_across_periods(db_session) -> None:
    projection = _persisted_projection(db_session, periods=2)
    base_rows = [
        dict(row)
        for statement in _packet()["statements"]
        for row in statement["rows"]
    ]
    rows = []
    for period_index in (1, 2):
        for row in base_rows:
            rows.append(
                {
                    **row,
                    "period_ref": f"fy-period-{period_index}",
                    "period_index": period_index,
                }
            )
    packet = _packet(rows=rows)

    response = packet_persistence.materialize_redacted_statement_packet(
        db_session,
        client_request_id="packet-multi-period-bound",
        sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
        packet=packet,
    )

    assert response["row_count"] == 6
    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 1
    assert db_session.query(L3SecXbrlStatementPacketRow).count() == 6
    rows_by_statement = db_session.query(L3SecXbrlStatementPacketRow).filter(
        L3SecXbrlStatementPacketRow.statement == "income"
    ).all()
    assert sorted((row.period_ref, row.period_index, row.statement_row_index) for row in rows_by_statement) == [
        ("fy-period-1", 1, 1),
        ("fy-period-2", 2, 1),
    ]


def test_statement_packet_persistence_leaves_no_partial_rows_on_late_invalid_row(db_session) -> None:
    projection = _persisted_projection(db_session)
    packet = _packet()
    packet["statements"][2]["rows"][0]["local_path"] = "C:/raw/filing.json"

    with pytest.raises(packet_persistence.SecXbrlStatementPacketPersistenceError):
        packet_persistence.materialize_redacted_statement_packet(
            db_session,
            client_request_id="packet-late-invalid",
            sec_xbrl_projection_set_id=projection["sec_xbrl_projection_set_id"],
            packet=packet,
        )

    assert db_session.query(L3SecXbrlStatementPacketSet).count() == 0
    assert db_session.query(L3SecXbrlStatementPacketStatement).count() == 0
    assert db_session.query(L3SecXbrlStatementPacketRow).count() == 0


def test_statement_packet_row_value_redacted_is_db_constrained(db_session) -> None:
    _materialize(db_session)
    row = db_session.query(L3SecXbrlStatementPacketRow).first()
    assert row is not None

    row.value_redacted = False
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_statement_packet_persistence_tables_are_registered_in_metadata() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    try:
        assert "l3_sec_xbrl_statement_packet_set" in inspector.get_table_names()
        assert "l3_sec_xbrl_statement_packet_statement" in inspector.get_table_names()
        assert "l3_sec_xbrl_statement_packet_row" in inspector.get_table_names()
        row_columns = {column["name"] for column in inspector.get_columns("l3_sec_xbrl_statement_packet_row")}
        assert "sec_xbrl_projection_fact_id" in row_columns
        assert "value_redacted" in row_columns
        assert "review_exception" in row_columns
        row_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("l3_sec_xbrl_statement_packet_row")
        }
        row_unique_constraints = {
            constraint["name"]: tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("l3_sec_xbrl_statement_packet_row")
        }
        assert "ck_l3_sec_xbrl_statement_packet_row_value_redacted" in row_constraints
        assert row_unique_constraints["uq_l3_sec_xbrl_statement_packet_row_statement_period_index"] == (
            "sec_xbrl_statement_packet_statement_id",
            "period_ref",
            "period_index",
            "statement_row_index",
        )
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_statement_packet_persistence_migration_declares_additive_tables() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location("migration_0039_sec_xbrl_statement_packet", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0039_layer3_sec_xbrl_statement_packet_persistence"
    assert module.down_revision == "0038_layer3_sec_xbrl_projection_persistence"
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_statement_packet_set" in source
    assert "l3_sec_xbrl_statement_packet_statement" in source
    assert "l3_sec_xbrl_statement_packet_row" in source
    assert "drop_table_idempotent(\"l3_sec_xbrl_statement_packet_row\")" in source


def test_statement_packet_redaction_constraint_migration_declares_check() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0041_sec_xbrl_redaction_constraints_statement_packet",
        REDACTION_CONSTRAINT_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0041_layer3_sec_xbrl_redaction_constraints"
    assert module.down_revision == "0040_layer3_sec_xbrl_operator_review_workflow"
    source = REDACTION_CONSTRAINT_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "ck_l3_sec_xbrl_projection_fact_value_redacted" in source
    assert "ck_l3_sec_xbrl_statement_packet_row_value_redacted" in source


def test_statement_packet_period_unique_migration_replaces_row_index_constraint() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location(
        "migration_0043_sec_xbrl_statement_packet_row_period_unique",
        PERIOD_UNIQUE_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0043_layer3_sec_xbrl_statement_packet_row_period_unique"
    assert module.down_revision == "0042_layer3_sec_xbrl_operator_review_decision"
    source = PERIOD_UNIQUE_MIGRATION_PATH.read_text(encoding="utf-8")
    assert "uq_l3_sec_xbrl_statement_packet_row_statement_period_index" in source
    assert "period_ref" in source
    assert "period_index" in source
    assert "drop_constraint" in source
