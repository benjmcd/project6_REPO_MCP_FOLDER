"""Migrated-schema smoke test for Layer 3 / Sublayer 3C golden path.

Drives the FULL 3C golden path (Lane 15 production smoke + Lane 31 migration
continuity) against a REAL Alembic-migrated SQLite schema — never
Base.metadata.create_all.

Coverage:
- test_migrated_schema_has_core_3c_tables      : migration chain produced the
                                                  required 3C tables
- test_migrated_schema_operates_full_golden_path: end-to-end service chain on
                                                  migrated schema
- test_migrated_schema_admission_preview        : package-bridge admission
                                                  preview on migrated schema
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Path / env bootstrap — must precede any app import so startup does not
# attempt a migrate-on-boot against the default sqlite path.
# ---------------------------------------------------------------------------
os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from alembic.config import Config  # noqa: E402
from alembic import command  # noqa: E402

import app.models.models  # noqa: E402, F401  — registers ORM classes

from app.models.models import (  # noqa: E402
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
)
from app.services.layer3_analysis_product_generation import (  # noqa: E402
    generate_analysis_product,
)
from app.services.layer3_analysis_product_lineage import (  # noqa: E402
    build_analysis_product_lineage,
)
from app.services.layer3_analysis_product_promotion import (  # noqa: E402
    AnalysisProductTransitionRequest,
    transition_analysis_product,
)
from app.services.layer3_analysis_product_replay import (  # noqa: E402
    verify_analysis_product_replay,
)
from app.services.layer3_working_set import (  # noqa: E402
    WorkingSetDraft,
    WorkingSetMemberDraft,
    create_working_set,
)
from app.services.layer3_workbench import (  # noqa: E402
    _build_analysis_product_admission_preview,
)

# ---------------------------------------------------------------------------
# Alembic helpers — replicate the exact pattern from test_layer3_migrations.py
# ---------------------------------------------------------------------------

ALEMBIC_INI = BACKEND / "alembic.ini"


def _make_alembic_config(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _run_upgrade(url: str) -> None:
    """Run alembic upgrade head against *url*.

    env.py's _database_url() checks os.environ["DATABASE_URL"] first, so we
    must set that env var — not just the alembic config option — to ensure the
    online migration path targets the correct file.  The previous value is
    restored after the upgrade completes.

    Alembic's env.py calls ``logging.config.fileConfig(...)``, which defaults to
    ``disable_existing_loggers=True`` and would disable every app logger not
    named in alembic.ini (e.g. ``layer3.lifecycle``) for the REST of the test
    process — silently breaking later caplog-based tests sharing the worker.  We
    snapshot every logger's ``disabled`` flag and restore it after the upgrade so
    this fixture leaves the logging configuration exactly as it found it.
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
        command.upgrade(cfg, "head")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev
        # Restore the disabled-state alembic's fileConfig may have changed.
        for name, lg in manager.loggerDict.items():
            if isinstance(lg, logging.Logger):
                lg.disabled = disabled_before.get(name, False)


# ---------------------------------------------------------------------------
# Fixture: fresh file-based SQLite migrated to head
# ---------------------------------------------------------------------------


@pytest.fixture()
def migrated_db_session(tmp_path):
    """Yield a SQLAlchemy Session bound to a freshly-migrated SQLite database.

    Schema comes exclusively from alembic upgrade head — Base.metadata.create_all
    is never called.  File-based so the migrated schema persists across the
    multiple connections that Alembic and SQLAlchemy open separately.
    """
    db_file = tmp_path / "smoke.db"
    url = f"sqlite:///{db_file}"

    # Run the real migration chain.
    _run_upgrade(url)

    # Prove the alembic_version table exists (confirms migrate path ran).
    check_engine = create_engine(url, future=True)
    with check_engine.connect() as conn:
        rows = list(conn.execute(text("SELECT version_num FROM alembic_version")))
    check_engine.dispose()
    assert len(rows) == 1, (
        f"Expected exactly one alembic_version row after upgrade head; got {rows}"
    )

    # Build session factory bound to the migrated engine.
    engine = create_engine(url, future=True)
    SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, future=True
    )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# Seed helper — mirrors seeded_db from test_layer3_analysis_product_generation
# ---------------------------------------------------------------------------

_SESSION_ID = "session-smoke-3c"
_SNAPSHOT_ID = "snapshot-smoke-3c"
_ANALYSIS_PLAN_ID = "plan-smoke-3c"
_ANALYSIS_SET_ID = "set-smoke-3c"


def _seed_session(db) -> None:
    """Insert the minimal rows needed by the 3C golden path."""
    session_row = L3Session(
        session_id=_SESSION_ID,
        selection_manifest_id="manifest-smoke-3c",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id=_SNAPSHOT_ID,
        session_id=_SESSION_ID,
        descriptor_id="descriptor-smoke-3c",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://smoke-3c",
        payload_hash="hash-smoke-3c",
        source_identity_json={"dataset_version_id": "dv-smoke-3c"},
        source_provenance_json={},
        load_summary_json={},
    )
    analysis_unit = L3AnalysisUnit(
        analysis_unit_id="unit-smoke-3c",
        session_id=_SESSION_ID,
        unit_kind="material_snapshot",
        analysis_modality="quantitative",
        member_snapshot_ids_json=[_SNAPSHOT_ID],
        member_ranges_json=[],
        must_remain_intact=True,
        typing_record_ids_json=[],
        unit_hash="unit-hash-smoke-3c",
        summary_json={},
    )
    analysis_group = L3AnalysisGroup(
        analysis_group_id="group-smoke-3c",
        session_id=_SESSION_ID,
        analysis_modality="quantitative",
        typing_basis_json={},
        analysis_unit_ids_json=["unit-smoke-3c"],
        status="formed",
    )
    analysis_set = L3AnalysisSet(
        analysis_set_id=_ANALYSIS_SET_ID,
        session_id=_SESSION_ID,
        analysis_group_ids_json=["group-smoke-3c"],
        analysis_unit_ids_json=["unit-smoke-3c"],
        set_type="associated_cohort",
        formation_basis_json={},
    )
    analysis_plan = L3AnalysisPlan(
        analysis_plan_id=_ANALYSIS_PLAN_ID,
        session_id=_SESSION_ID,
        analysis_set_ids_json=[_ANALYSIS_SET_ID],
        status="approved",
        approved_by_operator=True,
        approved_at=datetime(2026, 6, 17, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 17, 0, 0, tzinfo=timezone.utc),
        plan_json={},
    )
    pass_run = L3PassRun(
        pass_run_id="pass-run-smoke-3c",
        session_id=_SESSION_ID,
        analysis_plan_id=_ANALYSIS_PLAN_ID,
        analysis_set_id=_ANALYSIS_SET_ID,
        pass_type="associated_cohort",
        engine_family="wrapped_quantitative_analysis",
        status="completed",
        input_payload_ref="payload://input-smoke",
        output_payload_ref="payload://output-smoke",
        summary_json={},
    )
    db.add_all(
        [
            session_row,
            snapshot,
            analysis_unit,
            analysis_group,
            analysis_set,
            analysis_plan,
            pass_run,
        ]
    )
    db.commit()


# ---------------------------------------------------------------------------
# Test 1: core 3C tables must exist after migration
# ---------------------------------------------------------------------------


def test_migrated_schema_has_core_3c_tables(migrated_db_session):
    """After alembic upgrade head, all core Sublayer 3C tables must be present.

    This confirms the migration chain — not create_all — produced the schema.
    """
    engine = migrated_db_session.get_bind()
    live_tables = set(sa_inspect(engine).get_table_names())

    required = {
        "l3_session",
        "l3_working_set",
        "l3_analysis_product",
        "l3_analysis_product_evidence_link",
        "l3_analysis_product_review_decision",
        "l3_material_snapshot",
    }
    missing = required - live_tables
    assert not missing, (
        f"Core 3C tables missing from migrated schema: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# Test 2: full golden path on migrated schema
# ---------------------------------------------------------------------------


def test_migrated_schema_operates_full_golden_path(migrated_db_session):
    """Drive the complete Layer 3 / Sublayer 3C golden path on a migrated schema.

    Stages (asserted at each step):
      1. create_working_set          -> working_set created
      2. generate_analysis_product   -> lifecycle_status == "draft"
      3. promote draft -> proposed   -> lifecycle_status == "proposed"
      4. promote proposed -> validated -> lifecycle_status == "validated"
      5. accept validated -> accepted  -> lifecycle_status == "accepted"
      6. mark_package_eligible         -> lifecycle_status == "package_eligible"
      7. verify_analysis_product_replay -> reproduced True, classification "reproduced"
      8. build_analysis_product_lineage -> working_set_linked True,
                                          package.package_eligible_or_packaged True
    """
    db = migrated_db_session
    _seed_session(db)

    # --- Stage 1: create working set -------------------------------------------
    ws_result = create_working_set(
        db,
        session_id=_SESSION_ID,
        client_request_id="req-ws-smoke-3c-001",
        draft=WorkingSetDraft(
            name="Smoke 3C Working Set",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot", ref_id=_SNAPSHOT_ID
                ),
            ),
        ),
    )
    db.commit()
    ws = ws_result.working_set
    assert ws is not None

    # --- Stage 2: generate analysis product ------------------------------------
    gen_result = generate_analysis_product(
        db,
        session_id=_SESSION_ID,
        client_request_id="req-gen-smoke-3c-001",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    product = gen_result.product
    assert product.executor_type == "deterministic"
    assert product.lifecycle_status == "draft", (
        f"Expected 'draft' after generate; got '{product.lifecycle_status}'"
    )
    pid = product.analysis_product_id

    # --- Stage 3: draft -> proposed --------------------------------------------
    def _transition(crid: str, intent: str, reason: str):
        r = transition_analysis_product(
            db,
            session_id=_SESSION_ID,
            analysis_product_id=pid,
            client_request_id=crid,
            request=AnalysisProductTransitionRequest(
                decision_intent=intent,
                decision_reason_code=reason,
            ),
        )
        db.commit()
        return r

    proposed_result = _transition("d-smoke-1", "promote", "proposed_ready")
    assert proposed_result.product.lifecycle_status == "proposed", (
        f"Expected 'proposed'; got '{proposed_result.product.lifecycle_status}'"
    )

    # --- Stage 4: proposed -> validated ----------------------------------------
    validated_result = _transition("d-smoke-2", "promote", "validation_passed")
    assert validated_result.product.lifecycle_status == "validated", (
        f"Expected 'validated'; got '{validated_result.product.lifecycle_status}'"
    )

    # --- Stage 5: validated -> accepted ----------------------------------------
    accepted_result = _transition("d-smoke-3", "accept", "grounded_accept")
    assert accepted_result.product.lifecycle_status == "accepted", (
        f"Expected 'accepted'; got '{accepted_result.product.lifecycle_status}'"
    )
    assert accepted_result.decision.grounding_asserted is True

    # --- Stage 6: accepted -> package_eligible ---------------------------------
    pkg_result = _transition("d-smoke-4", "mark_package_eligible", "package_ready")
    assert pkg_result.product.lifecycle_status == "package_eligible", (
        f"Expected 'package_eligible'; got '{pkg_result.product.lifecycle_status}'"
    )

    # --- Stage 7: verify replay ------------------------------------------------
    replay_result = verify_analysis_product_replay(
        db,
        session_id=_SESSION_ID,
        analysis_product_id=pid,
    )
    assert replay_result.reproduced is True, (
        f"Expected reproduced=True; got classification='{replay_result.classification}'"
    )
    assert replay_result.classification == "reproduced", (
        f"Unexpected replay classification: '{replay_result.classification}'"
    )

    # --- Stage 8: lineage inspector --------------------------------------------
    lineage = build_analysis_product_lineage(
        db,
        session_id=_SESSION_ID,
        analysis_product_id=pid,
    )
    assert lineage["working_set_linked"] is True, (
        "Lineage: working_set_linked must be True after full promotion"
    )
    assert lineage["package"]["package_eligible_or_packaged"] is True, (
        f"Lineage: package_eligible_or_packaged must be True; "
        f"lifecycle_status='{lineage['package']['lifecycle_status']}'"
    )


# ---------------------------------------------------------------------------
# Test 3: admission preview on migrated schema
# ---------------------------------------------------------------------------


def test_migrated_schema_admission_preview(migrated_db_session):
    """Package-bridge admission preview works correctly on a migrated schema.

    After one product reaches package_eligible it appears in 'products'.
    A second product left in 'draft' appears in 'excluded_products' with an
    exclusion_reason.
    """
    db = migrated_db_session
    _seed_session(db)

    # --- Working set (shared) --------------------------------------------------
    ws_result = create_working_set(
        db,
        session_id=_SESSION_ID,
        client_request_id="req-ws-adm-001",
        draft=WorkingSetDraft(
            name="Admission Preview WS",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot", ref_id=_SNAPSHOT_ID
                ),
            ),
        ),
    )
    db.commit()
    ws = ws_result.working_set

    # --- Product A: promote all the way to package_eligible -------------------
    gen_a = generate_analysis_product(
        db,
        session_id=_SESSION_ID,
        client_request_id="req-gen-adm-a",
        working_set_id=ws.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    pid_a = gen_a.product.analysis_product_id

    def _transition(crid, intent, reason):
        r = transition_analysis_product(
            db,
            session_id=_SESSION_ID,
            analysis_product_id=pid_a,
            client_request_id=crid,
            request=AnalysisProductTransitionRequest(
                decision_intent=intent,
                decision_reason_code=reason,
            ),
        )
        db.commit()
        return r

    _transition("adm-d1", "promote", "proposed_ready")
    _transition("adm-d2", "promote", "validation_passed")
    _transition("adm-d3", "accept", "grounded_accept")
    _transition("adm-d4", "mark_package_eligible", "package_ready")

    # --- Product B: second working set for an isolated draft product -----------
    ws_result_b = create_working_set(
        db,
        session_id=_SESSION_ID,
        client_request_id="req-ws-adm-b",
        draft=WorkingSetDraft(
            name="Admission Preview WS B",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot", ref_id=_SNAPSHOT_ID
                ),
            ),
        ),
    )
    db.commit()
    ws_b = ws_result_b.working_set

    gen_b = generate_analysis_product(
        db,
        session_id=_SESSION_ID,
        client_request_id="req-gen-adm-b",
        working_set_id=ws_b.working_set_id,
        method_id="working_set_composition_summary",
    )
    db.commit()
    # Leave product B in draft — it must appear in excluded_products.
    assert gen_b.product.lifecycle_status == "draft"

    # --- Build admission preview -----------------------------------------------
    preview = _build_analysis_product_admission_preview(db, _SESSION_ID)

    assert preview["available"] is True, (
        f"Admission preview unavailable: {preview.get('note')}"
    )

    # Product A must appear in products (package_eligible).
    eligible_ids = [p.get("lifecycle_status") for p in preview["products"]]
    assert "package_eligible" in eligible_ids, (
        f"Expected product with lifecycle_status='package_eligible' in products; "
        f"got {eligible_ids}"
    )
    assert preview["package_eligible_product_count"] >= 1

    # Product B (draft) must appear in excluded_products with an exclusion_reason.
    excluded_statuses = [p.get("lifecycle_status") for p in preview["excluded_products"]]
    assert "draft" in excluded_statuses, (
        f"Expected draft product in excluded_products; got statuses={excluded_statuses}"
    )
    for exc in preview["excluded_products"]:
        assert exc.get("exclusion_reason") is not None, (
            f"excluded_product missing exclusion_reason: {exc}"
        )
        assert exc["exclusion_reason"] != "", (
            f"excluded_product has empty exclusion_reason: {exc}"
        )
