"""Migration validation suite for Layer 3 alembic migrations.

Covers:
- SQLite: alembic upgrade head succeeds
- SQLite: exactly one head in the script directory
- SQLite: idempotent re-run (upgrade head twice without error)
- SQLite: ORM metadata match (all Base tables/columns present after upgrade)
- Postgres variants: guarded by pytest.mark.skipif when psycopg2 or
  LAYER3_MIGRATION_TEST_DATABASE_URL env var is absent
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.exc import IntegrityError

# ---------------------------------------------------------------------------
# Path bootstrap — replicate the pattern used by the other test_layer3_*.py
# files: set DB_INIT_MODE before importing app modules so the app startup
# does not attempt a migrate-on-boot against the default SQLite path.
# ---------------------------------------------------------------------------
os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from alembic.config import Config  # noqa: E402
from alembic import command  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402

# Import Base (and trigger model registration) after path/env setup.
from app.db.session import Base  # noqa: E402
import app.models.models  # noqa: E402,F401  — registers all ORM classes


# ---------------------------------------------------------------------------
# Known-allowlist for live-vs-metadata table differences.
# Add entries here (with comments) if a legitimate drift is ever introduced.
# ---------------------------------------------------------------------------
EXTRA_LIVE_TABLES_ALLOWLIST: frozenset[str] = frozenset(
    {
        "alembic_version",  # Alembic's internal tracking table — always present
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALEMBIC_INI = BACKEND / "alembic.ini"


def _make_alembic_config(url: str) -> Config:
    """Return an Alembic Config pointed at alembic.ini with the given DB URL."""
    cfg = Config(str(ALEMBIC_INI))
    # alembic.ini declares script_location relative to the backend/ directory;
    # pin it absolutely so the suite passes regardless of pytest's cwd.
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _run_alembic_command(url: str, operation, revision: str) -> None:
    """Run an Alembic operation against *url*.

    env.py's ``_database_url()`` checks ``os.environ["DATABASE_URL"]`` first,
    so we must set that env var — not just the alembic config option — to
    ensure the online migration path targets the correct database file.
    The previous value (if any) is restored after the upgrade completes.

    Alembic's env.py calls ``logging.config.fileConfig(...)``, which defaults to
    ``disable_existing_loggers=True`` and would disable every app logger not
    named in alembic.ini (e.g. ``layer3.lifecycle``) for the REST of the test
    process — silently breaking later caplog-based tests sharing the worker.  We
    snapshot every logger's ``disabled`` flag and restore it after the upgrade so
    this helper leaves the logging configuration exactly as it found it.
    """
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    manager = logging.Logger.manager
    disabled_before = {
        name: lg.disabled
        for name, lg in manager.loggerDict.items()
        if isinstance(lg, logging.Logger)
    }
    try:
        cfg = _make_alembic_config(url)
        operation(cfg, revision)
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev
        # Restore the disabled-state alembic's fileConfig may have changed.
        for name, lg in manager.loggerDict.items():
            if isinstance(lg, logging.Logger):
                lg.disabled = disabled_before.get(name, False)


def _run_upgrade(url: str) -> None:
    """Run alembic upgrade head against *url*."""
    _run_alembic_command(url, command.upgrade, "head")


def _run_upgrade_to(url: str, revision: str) -> None:
    """Run alembic upgrade to a specific revision against *url*."""
    _run_alembic_command(url, command.upgrade, revision)


def _run_downgrade_to(url: str, revision: str) -> None:
    """Run alembic downgrade to a specific revision against *url*."""
    _run_alembic_command(url, command.downgrade, revision)


def _check_schema_match(url: str) -> None:
    """Assert that all ORM metadata tables/columns are present in the live DB.

    Extra tables in the live DB that are present in EXTRA_LIVE_TABLES_ALLOWLIST
    are ignored.  Any unlisted extra tables are reported but do NOT cause a
    failure (they may be created by future migrations not yet reflected in the
    ORM metadata — that is acceptable drift in the forward direction).

    Missing tables (tables in metadata but absent from the live DB) always
    fail the assertion.
    """
    engine = create_engine(url, future=True)
    inspector = sa_inspect(engine)
    live_tables = set(inspector.get_table_names())
    meta_tables = set(Base.metadata.tables.keys())

    missing_tables = meta_tables - live_tables
    assert not missing_tables, (
        f"ORM metadata tables missing from live schema after alembic upgrade head: "
        f"{sorted(missing_tables)}"
    )

    # Check columns for every table that exists in both places.
    missing_columns: dict[str, list[str]] = {}
    for table_name in meta_tables:
        if table_name not in live_tables:
            continue  # already reported above
        live_cols = {c["name"] for c in inspector.get_columns(table_name)}
        meta_cols = {
            col.name for col in Base.metadata.tables[table_name].columns
        }
        absent = meta_cols - live_cols
        if absent:
            missing_columns[table_name] = sorted(absent)

    assert not missing_columns, (
        f"ORM metadata columns missing from live schema after alembic upgrade head: "
        f"{missing_columns}"
    )

    engine.dispose()


# ---------------------------------------------------------------------------
# Postgres skip guard
# ---------------------------------------------------------------------------

_POSTGRES_URL = os.environ.get("LAYER3_MIGRATION_TEST_DATABASE_URL", "")


def _psycopg_available() -> bool:
    try:
        import psycopg  # noqa: F401
        return True
    except ImportError:
        return False


_skip_postgres = pytest.mark.skipif(
    not (_psycopg_available() and bool(_POSTGRES_URL)),
    reason=(
        "Postgres migration tests require psycopg (v3) and "
        "LAYER3_MIGRATION_TEST_DATABASE_URL to be set"
    ),
)


# ---------------------------------------------------------------------------
# SQLite tests (always run)
# ---------------------------------------------------------------------------


def test_alembic_single_head(tmp_path):
    """The alembic script directory must expose exactly one current head."""
    cfg = _make_alembic_config(f"sqlite:///{tmp_path / 'single_head.db'}")
    scripts = ScriptDirectory.from_config(cfg)
    heads = scripts.get_heads()
    assert len(heads) == 1, (
        f"Expected exactly one alembic head; found {len(heads)}: {heads}. "
        "A merge migration may be missing."
    )


def test_alembic_upgrade_head_sqlite(tmp_path):
    """alembic upgrade head completes without error against a fresh SQLite db."""
    db_url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    _run_upgrade(db_url)
    # Verify the alembic_version table records the single head revision.
    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = [row[0] for row in result]
    engine.dispose()
    assert len(rows) == 1, f"Expected one version row, got {rows}"


def test_alembic_upgrade_head_idempotent_sqlite(tmp_path):
    """Running alembic upgrade head twice on the same SQLite db must not error."""
    db_url = f"sqlite:///{tmp_path / 'idempotent.db'}"
    _run_upgrade(db_url)
    # Second run — should be a no-op and should not raise.
    _run_upgrade(db_url)


def test_alembic_orm_metadata_match_sqlite(tmp_path):
    """After upgrade head, every ORM table and column must exist in the live schema."""
    db_url = f"sqlite:///{tmp_path / 'metadata_match.db'}"
    _run_upgrade(db_url)
    _check_schema_match(db_url)


def test_controlled_value_reveal_submit_request_hash_migration_up_down_sqlite(tmp_path):
    """0053 hashes legacy controlled-submit client_request_id values and redacts raw storage."""
    db_url = f"sqlite:///{tmp_path / 'controlled_submit_hash.db'}"
    legacy_revision = "0052_layer3_analysis_product_supersession"
    raw_request_id = "legacy-private-submit-request"
    expected_hash = hashlib.sha256(raw_request_id.encode("utf-8")).hexdigest()

    _run_upgrade_to(db_url, legacy_revision)
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(
            text(
                """
                INSERT INTO l3_sec_xbrl_controlled_value_reveal_submit_receipt (
                    sec_xbrl_controlled_value_reveal_submit_receipt_id,
                    client_request_id,
                    submit_basis_hash,
                    submit_schema_id,
                    sec_xbrl_value_reveal_authority_receipt_id,
                    authority_basis_hash,
                    sec_xbrl_operator_review_decision_id,
                    decision_basis_hash,
                    sec_xbrl_operator_review_workflow_id,
                    workflow_basis_hash,
                    sec_xbrl_statement_packet_set_id,
                    statement_packet_basis_hash,
                    sec_xbrl_projection_set_id,
                    projection_basis_hash,
                    dataset_version_id,
                    dataset_version_hash,
                    sidecar_receipt_id_hash,
                    sidecar_receipt_hash,
                    value_store_hash,
                    submit_state,
                    submit_policy_id,
                    redaction_policy,
                    revealed_fact_count,
                    value_redacted_fact_count,
                    fact_inventory_hash,
                    value_inventory_hash,
                    response_inventory_hash,
                    submit_summary_json,
                    negative_invariants_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    :receipt_id,
                    :client_request_id,
                    :submit_basis_hash,
                    :submit_schema_id,
                    :authority_receipt_id,
                    :authority_basis_hash,
                    :decision_id,
                    :decision_basis_hash,
                    :workflow_id,
                    :workflow_basis_hash,
                    :packet_set_id,
                    :statement_packet_basis_hash,
                    :projection_set_id,
                    :projection_basis_hash,
                    :dataset_version_id,
                    :dataset_version_hash,
                    :sidecar_receipt_id_hash,
                    :sidecar_receipt_hash,
                    :value_store_hash,
                    :submit_state,
                    :submit_policy_id,
                    :redaction_policy,
                    :revealed_fact_count,
                    :value_redacted_fact_count,
                    :fact_inventory_hash,
                    :value_inventory_hash,
                    :response_inventory_hash,
                    :submit_summary_json,
                    :negative_invariants_json,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "receipt_id": "legacy-submit-receipt",
                "client_request_id": raw_request_id,
                "submit_basis_hash": "a" * 64,
                "submit_schema_id": "layer3.sec_xbrl_controlled_value_reveal_submit.v1",
                "authority_receipt_id": "legacy-authority-receipt",
                "authority_basis_hash": "b" * 64,
                "decision_id": "legacy-decision",
                "decision_basis_hash": "c" * 64,
                "workflow_id": "legacy-workflow",
                "workflow_basis_hash": "d" * 64,
                "packet_set_id": "legacy-packet-set",
                "statement_packet_basis_hash": "e" * 64,
                "projection_set_id": "legacy-projection-set",
                "projection_basis_hash": "f" * 64,
                "dataset_version_id": "legacy-dataset-version",
                "dataset_version_hash": "1" * 64,
                "sidecar_receipt_id_hash": "2" * 64,
                "sidecar_receipt_hash": "3" * 64,
                "value_store_hash": "4" * 64,
                "submit_state": "controlled_values_revealed_transiently",
                "submit_policy_id": "sec_xbrl_authority_receipt_bound_controlled_value_reveal_submit_v1",
                "redaction_policy": "sec_xbrl_controlled_value_reveal_submit_hash_count_receipt_v1",
                "revealed_fact_count": 1,
                "value_redacted_fact_count": 0,
                "fact_inventory_hash": "5" * 64,
                "value_inventory_hash": "6" * 64,
                "response_inventory_hash": "7" * 64,
                "submit_summary_json": json.dumps({"legacy": True}),
                "negative_invariants_json": json.dumps({"raw_values_persisted": False}),
                "created_at": "2026-06-19T00:00:00Z",
                "updated_at": "2026-06-19T00:00:00Z",
            },
        )
    engine.dispose()

    _run_upgrade(db_url)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    columns = {
        column["name"]
        for column in inspector.get_columns("l3_sec_xbrl_controlled_value_reveal_submit_receipt")
    }
    assert "client_request_id_hash" in columns
    with engine.connect() as conn:
        migrated = conn.execute(
            text(
                """
                SELECT client_request_id, client_request_id_hash
                FROM l3_sec_xbrl_controlled_value_reveal_submit_receipt
                WHERE sec_xbrl_controlled_value_reveal_submit_receipt_id = :receipt_id
                """
            ),
            {"receipt_id": "legacy-submit-receipt"},
        ).mappings().one()
    engine.dispose()
    assert migrated["client_request_id_hash"] == expected_hash
    assert migrated["client_request_id"] == f"redacted-client-request-id:{expected_hash}"
    assert migrated["client_request_id"] != raw_request_id

    _run_downgrade_to(db_url, legacy_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    downgraded_columns = {
        column["name"]
        for column in inspector.get_columns("l3_sec_xbrl_controlled_value_reveal_submit_receipt")
    }
    assert "client_request_id_hash" not in downgraded_columns
    with engine.connect() as conn:
        downgraded_request_id = conn.execute(
            text(
                """
                SELECT client_request_id
                FROM l3_sec_xbrl_controlled_value_reveal_submit_receipt
                WHERE sec_xbrl_controlled_value_reveal_submit_receipt_id = :receipt_id
                """
            ),
            {"receipt_id": "legacy-submit-receipt"},
        ).scalar_one()
    engine.dispose()
    assert downgraded_request_id == f"redacted-client-request-id:{expected_hash}"
    assert downgraded_request_id != raw_request_id


def test_dataset_version_source_fidelity_migration_up_down_sqlite(tmp_path):
    """0055 adds nullable source-fidelity metadata to dataset_version and rolls it back."""
    db_url = f"sqlite:///{tmp_path / 'dataset_version_source_fidelity.db'}"
    previous_revision = "0054_layer3_sec_xbrl_controlled_submit_pagination"
    fidelity_revision = "0055_dataset_version_source_fidelity"
    fidelity_columns = {"content_hash", "source_row_count", "dropped_row_count"}

    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE dataset_version (
                    dataset_version_id VARCHAR(36) NOT NULL,
                    row_count INTEGER,
                    PRIMARY KEY (dataset_version_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO dataset_version (dataset_version_id, row_count)
                VALUES ('legacy-version', 2)
                """
            )
        )
    engine.dispose()

    _run_alembic_command(db_url, command.stamp, previous_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    prior_columns = {
        column["name"] for column in inspector.get_columns("dataset_version")
    }
    engine.dispose()
    assert fidelity_columns.isdisjoint(prior_columns)

    _run_upgrade_to(db_url, fidelity_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    upgraded_columns = {
        column["name"]: column for column in inspector.get_columns("dataset_version")
    }
    assert fidelity_columns.issubset(upgraded_columns)
    assert upgraded_columns["content_hash"]["nullable"] is True
    assert upgraded_columns["source_row_count"]["nullable"] is True
    assert upgraded_columns["dropped_row_count"]["nullable"] is True
    with engine.connect() as conn:
        upgraded_row = conn.execute(
            text(
                """
                SELECT row_count, content_hash, source_row_count, dropped_row_count
                FROM dataset_version
                WHERE dataset_version_id = 'legacy-version'
                """
            )
        ).one()
    engine.dispose()
    assert upgraded_row == (2, None, None, None)

    _run_downgrade_to(db_url, previous_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    downgraded_columns = {
        column["name"] for column in inspector.get_columns("dataset_version")
    }
    assert fidelity_columns.isdisjoint(downgraded_columns)
    with engine.connect() as conn:
        downgraded_row_count = conn.execute(
            text(
                """
                SELECT row_count
                FROM dataset_version
                WHERE dataset_version_id = 'legacy-version'
                """
            )
        ).scalar_one()
    engine.dispose()
    assert downgraded_row_count == 2


def test_connector_source_intake_record_migration_up_down_sqlite(tmp_path):
    """0056 creates the connector source-intake table and cleanly rolls it back."""
    db_url = f"sqlite:///{tmp_path / 'connector_source_intake_record.db'}"
    previous_revision = "0055_dataset_version_source_fidelity"
    connector_revision = "0056_layer3_connector_source_intake_record"

    _run_upgrade_to(db_url, previous_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    assert not inspector.has_table("l3_connector_source_intake_record")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO connector_run (
                    connector_run_id,
                    connector_key,
                    source_system,
                    source_mode,
                    status,
                    submitted_at,
                    created_at
                )
                VALUES (
                    'run-0056-proof',
                    'sciencebase-public',
                    'sciencebase',
                    'public_api',
                    'running',
                    '2026-07-09T00:00:00Z',
                    '2026-07-09T00:00:00Z'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO connector_run_target (
                    connector_run_target_id,
                    connector_run_id,
                    ordinal,
                    artifact_surface,
                    public_read_confirmed,
                    status,
                    retry_eligible,
                    attempt_count,
                    created_at
                )
                VALUES (
                    'target-0056-proof',
                    'run-0056-proof',
                    1,
                    'files',
                    1,
                    'downloaded',
                    0,
                    0,
                    '2026-07-09T00:00:00Z'
                )
                """
            )
        )
    engine.dispose()

    _run_upgrade_to(db_url, connector_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    assert inspector.has_table("l3_connector_source_intake_record")
    columns = {
        column["name"]: column
        for column in inspector.get_columns("l3_connector_source_intake_record")
    }
    assert {
        "connector_source_intake_record_id",
        "client_request_id",
        "operator_decision",
        "source_family",
        "source_label",
        "source_description",
        "original_filename",
        "media_type",
        "content_size_bytes",
        "content_sha256",
        "metadata_hash",
        "authority_basis_hash",
        "storage_ref",
        "freshness_timestamp",
        "provenance_json",
        "downstream_eligibility_json",
        "summary_json",
        "status",
        "created_at",
        "updated_at",
        "connector_key",
        "connector_run_id",
        "connector_run_target_id",
    }.issubset(columns)
    assert columns["connector_key"]["nullable"] is False
    assert columns["connector_run_id"]["nullable"] is False
    assert columns["connector_run_target_id"]["nullable"] is False
    checks = {
        constraint["name"]: constraint["sqltext"]
        for constraint in inspector.get_check_constraints("l3_connector_source_intake_record")
    }
    assert (
        checks["ck_l3_connector_source_intake_operator_decision"]
        == "operator_decision = 'record_connector_produced_source'"
    )
    assert (
        checks["ck_l3_connector_source_intake_status"]
        == "status IN ('recorded', 'already_recorded')"
    )
    uniques = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("l3_connector_source_intake_record")
    }
    assert {
        "uq_l3_connector_source_intake_client_request",
        "uq_l3_connector_source_intake_authority_basis",
    }.issubset(uniques)
    indexes = {
        index["name"]
        for index in inspector.get_indexes("l3_connector_source_intake_record")
    }
    assert {
        "ix_l3_connector_source_intake_content_sha256",
        "ix_l3_connector_source_intake_source_family",
        "ix_l3_connector_source_intake_status",
        "ix_l3_connector_source_intake_run_target",
    }.issubset(indexes)
    engine.dispose()

    _run_downgrade_to(db_url, previous_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    assert not inspector.has_table("l3_connector_source_intake_record")
    with engine.connect() as conn:
        target_status = conn.execute(
            text(
                """
                SELECT status
                FROM connector_run_target
                WHERE connector_run_target_id = 'target-0056-proof'
                """
            )
        ).scalar_one()
    engine.dispose()
    assert target_status == "downloaded"

    _run_upgrade_to(db_url, connector_revision)
    engine = create_engine(db_url, future=True)
    inspector = sa_inspect(engine)
    assert inspector.has_table("l3_connector_source_intake_record")
    engine.dispose()


# ---------------------------------------------------------------------------
# Postgres tests (skipped when driver or URL absent)
# ---------------------------------------------------------------------------


@_skip_postgres
def test_alembic_upgrade_head_postgres():
    """alembic upgrade head completes against the Postgres test database."""
    _run_upgrade(_POSTGRES_URL)


@_skip_postgres
def test_alembic_upgrade_head_idempotent_postgres():
    """Running alembic upgrade head twice on Postgres must not error."""
    _run_upgrade(_POSTGRES_URL)
    _run_upgrade(_POSTGRES_URL)


@_skip_postgres
def test_connector_source_intake_record_0056_constraints_postgres():
    """0056 constraints reject invalid values and duplicate idempotency keys on Postgres."""
    _run_upgrade(_POSTGRES_URL)
    engine = create_engine(_POSTGRES_URL, future=True)
    suffix = uuid.uuid4().hex[:12]

    def _row(record_id: str, request_id: str, authority_hash: str, **overrides):
        row = {
            "connector_source_intake_record_id": record_id,
            "client_request_id": request_id,
            "operator_decision": "record_connector_produced_source",
            "source_family": "connector_produced_single_source",
            "source_label": "Postgres 0056 proof CSV",
            "source_description": None,
            "original_filename": "postgres-0056-proof.csv",
            "media_type": "text/csv",
            "content_size_bytes": 17,
            "content_sha256": hashlib.sha256(record_id.encode("utf-8")).hexdigest(),
            "metadata_hash": hashlib.sha256(request_id.encode("utf-8")).hexdigest(),
            "authority_basis_hash": authority_hash,
            "storage_ref": f"connector://postgres-0056/{record_id}",
            "freshness_timestamp": None,
            "provenance_json": json.dumps({"schema_id": "postgres-0056-proof"}),
            "downstream_eligibility_json": json.dumps({"eligible": True}),
            "summary_json": json.dumps({"proof": "postgres-0056"}),
            "status": "recorded",
            "connector_key": "sciencebase-public",
            "connector_run_id": f"run-postgres-0056-{suffix}",
            "connector_run_target_id": f"target-postgres-0056-{suffix}",
        }
        row.update(overrides)
        return row

    def _insert(row):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO l3_connector_source_intake_record (
                        connector_source_intake_record_id,
                        client_request_id,
                        operator_decision,
                        source_family,
                        source_label,
                        source_description,
                        original_filename,
                        media_type,
                        content_size_bytes,
                        content_sha256,
                        metadata_hash,
                        authority_basis_hash,
                        storage_ref,
                        freshness_timestamp,
                        provenance_json,
                        downstream_eligibility_json,
                        summary_json,
                        status,
                        created_at,
                        updated_at,
                        connector_key,
                        connector_run_id,
                        connector_run_target_id
                    )
                    VALUES (
                        :connector_source_intake_record_id,
                        :client_request_id,
                        :operator_decision,
                        :source_family,
                        :source_label,
                        :source_description,
                        :original_filename,
                        :media_type,
                        :content_size_bytes,
                        :content_sha256,
                        :metadata_hash,
                        :authority_basis_hash,
                        :storage_ref,
                        :freshness_timestamp,
                        CAST(:provenance_json AS JSON),
                        CAST(:downstream_eligibility_json AS JSON),
                        CAST(:summary_json AS JSON),
                        :status,
                        now(),
                        now(),
                        :connector_key,
                        :connector_run_id,
                        :connector_run_target_id
                    )
                    """
                ),
                row,
            )

    base_authority_hash = hashlib.sha256(f"authority-{suffix}".encode("utf-8")).hexdigest()
    _insert(
        _row(
            f"pg0056-{suffix}-base",
            f"pg0056-client-{suffix}-base",
            base_authority_hash,
        )
    )

    with pytest.raises(IntegrityError):
        _insert(
            _row(
                f"pg0056-{suffix}-bad-decision",
                f"pg0056-client-{suffix}-bad-decision",
                hashlib.sha256(f"bad-decision-{suffix}".encode("utf-8")).hexdigest(),
                operator_decision="wrong_decision",
            )
        )
    with pytest.raises(IntegrityError):
        _insert(
            _row(
                f"pg0056-{suffix}-bad-status",
                f"pg0056-client-{suffix}-bad-status",
                hashlib.sha256(f"bad-status-{suffix}".encode("utf-8")).hexdigest(),
                status="wrong_status",
            )
        )
    with pytest.raises(IntegrityError):
        _insert(
            _row(
                f"pg0056-{suffix}-dup-client",
                f"pg0056-client-{suffix}-base",
                hashlib.sha256(f"dup-client-{suffix}".encode("utf-8")).hexdigest(),
            )
        )
    with pytest.raises(IntegrityError):
        _insert(
            _row(
                f"pg0056-{suffix}-dup-authority",
                f"pg0056-client-{suffix}-dup-authority",
                base_authority_hash,
            )
        )

    engine.dispose()


@_skip_postgres
def test_alembic_orm_metadata_match_postgres():
    """After upgrade head, every ORM table and column must exist in Postgres live schema."""
    _run_upgrade(_POSTGRES_URL)
    _check_schema_match(_POSTGRES_URL)
