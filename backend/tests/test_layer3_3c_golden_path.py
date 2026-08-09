"""3C Packaged-Deliverable Golden Path v0.

Proves the full 3C product→package path end-to-end:
  - Build a working/typed session + completed pass
  - Author a GROUNDED analysis product
  - Promote it to lifecycle_status 'package_eligible'
  - Construct & COMMIT a workbench package with the default-off bridge flag
    ENABLED (test A: flag OFF; test B: flag ON)
  - Read the COMMITTED package payload from disk
  - Assert the bounded analysis_product_inventory roster (and no-body /
    user_facing-minimization invariants)

Construction path chosen: TestClient/API path mirroring _construct_quant_package_set
in test_layer3_api.py. Rationale:
  (1) Routes through package_construction_commit in layer3_workbench.py which
      calls _merge_analysis_product_inventory_extras (the real flag gate).
  (2) Allows authoring+promoting the 3C product on the same session via direct
      DB calls between API steps (using client.layer3_session_factory()).
  (3) Committed L3OutputPackage rows are queryable from the same DB engine.
  (4) payload_ref is the on-disk path; json.loads(Path(row.payload_ref).read_text())
      gives the committed payload.
  (5) service-level materialize_package_entry (layer3_package_entry.py) does NOT
      call _merge_analysis_product_inventory_extras, so it cannot exercise the gate.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    L3AnalysisProduct,
    L3MaterialSnapshot,
    L3OutputPackage,
)
from app.services import layer3_workbench
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    create_analysis_product_draft,
)
from app.services.layer3_analysis_product_generation import generate_analysis_product
from app.services.layer3_deterministic_methods import DETERMINISTIC_METHODS
from app.services.layer3_working_set import (
    WorkingSetDraft,
    WorkingSetMemberDraft,
    create_working_set,
)
from app.services.layer3_analysis_product_promotion import (
    AnalysisProductTransitionRequest,
    transition_analysis_product,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from main import app

# Import the session builder from test_layer3_pass_entry (returns tuple[str, str, datetime])
from test_layer3_pass_entry import _build_quant_ready_session

# ---------------------------------------------------------------------------
# PostgreSQL skip guard (mirrors test_layer3_migrations.py)
# ---------------------------------------------------------------------------

_GOLDEN_PATH_PG_URL = os.environ.get("LAYER3_GOLDEN_PATH_TEST_DATABASE_URL", "")


def _psycopg_available() -> bool:
    try:
        import psycopg  # noqa: F401
        return True
    except ImportError:
        return False


_PG_AVAILABLE = _psycopg_available() and bool(_GOLDEN_PATH_PG_URL)

ALEMBIC_INI = BACKEND / "alembic.ini"


def _make_alembic_config_gp(url: str) -> AlembicConfig:
    """Return an Alembic Config for the golden-path PG database."""
    cfg = AlembicConfig(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _run_alembic_upgrade_gp(url: str) -> None:
    """Run alembic upgrade head, setting DATABASE_URL so env.py picks it up."""
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        cfg = _make_alembic_config_gp(url)
        alembic_command.upgrade(cfg, "head")
    finally:
        if prev is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _pg_schema_built():
    """Build the PG schema once per test session via alembic upgrade head.

    Skipped (returns None) when PG is not configured.  The per-test `client`
    fixture depends on this to ensure schema exists before running tests.
    """
    if not _PG_AVAILABLE:
        return None
    _run_alembic_upgrade_gp(_GOLDEN_PATH_PG_URL)
    return _GOLDEN_PATH_PG_URL


def _truncate_all_pg_tables(engine) -> None:
    """TRUNCATE every non-alembic table between tests for isolation.

    Derives the table list from the LIVE inspector (not metadata) so that
    any forward-drift migration table is also covered.  Asserts non-empty
    and that the set covers every inspector-reported table minus alembic_version.
    """
    inspector = sa_inspect(engine)
    live_tables = set(inspector.get_table_names())
    truncate_tables = live_tables - {"alembic_version"}
    assert truncate_tables, (
        "No tables found to truncate — schema may not have been built correctly"
    )
    # Assert full coverage: every live non-alembic table must be in the truncate set.
    missed = (live_tables - {"alembic_version"}) - truncate_tables
    assert not missed, (
        f"Truncate set missed live tables: {sorted(missed)}"
    )
    # Build a quoted, comma-separated table list for a single TRUNCATE statement.
    table_list = ", ".join(f'"{t}"' for t in sorted(truncate_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def client(tmp_path, monkeypatch, _pg_schema_built):
    """TestClient wired to either PostgreSQL (when LAYER3_GOLDEN_PATH_TEST_DATABASE_URL
    is set and psycopg v3 is importable) or an in-memory SQLite database.

    PostgreSQL branch:
      - Engine built on the env URL with postgresql+psycopg:// dialect.
      - Schema built ONCE per session via alembic upgrade head (_pg_schema_built).
      - Per-test isolation: TRUNCATE all non-alembic tables RESTART IDENTITY CASCADE.

    SQLite branch (default):
      - Unchanged: StaticPool, check_same_thread=False, Base.metadata.create_all.
    """
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "external-local-export"))
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/layer3-internal-webhook")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "test-internal-webhook")
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", False)
    bootstrap_storage_tree(storage_dir)

    if _pg_schema_built is not None:
        # --- PostgreSQL branch ---
        pg_url = _pg_schema_built
        engine = create_engine(pg_url, future=True, pool_pre_ping=True)
        # Truncate all tables before each test for clean isolation.
        _truncate_all_pg_tables(engine)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    else:
        # --- SQLite branch (default, unchanged behaviour) ---
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
    test_client = TestClient(app)
    test_client.layer3_session_factory = SessionLocal
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_managed_quant_ready_session(db, tmp_path: Path):
    return _build_quant_ready_session(
        db,
        tmp_path,
        snapshot_storage_root=Path(settings.artifact_storage_dir) / "layer3",
    )


def _make_grounded_product_for_session(db, *, session_id: str, client_request_id: str):
    """Author a grounded 'finding' product whose evidence ref points to the
    first real L3MaterialSnapshot in the given session."""
    snapshot = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .first()
    )
    assert snapshot is not None, f"No material snapshot found for session {session_id}"

    draft = AnalysisProductDraft(
        product_kind="finding",
        title=f"Golden-path finding [{client_request_id}]",
        body="Body text — should never appear in package payload.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id=snapshot.material_snapshot_id,
                evidence_role="observation",
            ),
        ),
    )
    result = create_analysis_product_draft(
        db,
        session_id=session_id,
        client_request_id=client_request_id,
        draft=draft,
    )
    db.commit()
    return result.product


def _promote_to_package_eligible(db, *, session_id: str, product_id: str, prefix: str) -> None:
    """Walk a product draft -> proposed_ready -> validation_passed ->
    grounded_accept -> package_ready (package_eligible)."""
    steps = [
        ("promote", "proposed_ready"),
        ("promote", "validation_passed"),
        ("accept", "grounded_accept"),
        ("mark_package_eligible", "package_ready"),
    ]
    for i, (intent, code) in enumerate(steps):
        transition_analysis_product(
            db,
            session_id=session_id,
            analysis_product_id=product_id,
            client_request_id=f"{prefix}-step-{i}",
            request=AnalysisProductTransitionRequest(
                decision_intent=intent,
                decision_reason_code=code,
            ),
        )
        db.commit()

    # Verify the product genuinely reached package_eligible (so the roster's
    # presence in TEST B is contingent on a real package_eligible product, and a
    # promotion regression surfaces here rather than as a confusing count==0).
    refreshed = (
        db.query(L3AnalysisProduct)
        .filter(L3AnalysisProduct.analysis_product_id == product_id)
        .first()
    )
    assert refreshed is not None, f"Product {product_id} missing after promotion"
    assert refreshed.lifecycle_status == "package_eligible", (
        f"Product {product_id} did not reach package_eligible; "
        f"got {refreshed.lifecycle_status}"
    )


def _build_session_with_package_eligible_product(
    client: TestClient,
    tmp_path: Path,
    *,
    request_prefix: str,
) -> tuple[str, dict, dict, dict, dict, dict, dict]:
    """Build a quant session, author+promote a 3C product to package_eligible,
    run plan/approve + execution/select + execution/start + result/review.

    Returns:
        (session_id, preview_body, approval_body, selection_body, start_body,
         status_body, review_body)
    """
    # 1. Build the quant-ready session (typed, pass-ready) via direct DB call.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    # 2. Author + promote a 3C analysis product to package_eligible.
    db = client.layer3_session_factory()
    try:
        product = _make_grounded_product_for_session(
            db, session_id=session_id, client_request_id=f"{request_prefix}-product"
        )
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=product.analysis_product_id,
            prefix=f"{request_prefix}-promote",
        )
    finally:
        db.close()

    # 3. Plan preview + approve (API).
    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"{request_prefix}-plan-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"{request_prefix}-plan-approve",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200, approval.text
    approval_body = approval.json()

    # 4. Execution select.
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_prefix}-exec-select",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200, selection.text
    selection_body = selection.json()
    pass_run_id = selection_body["pass_run_ids"][0]

    # 5. Execution start.
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_prefix}-exec-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200, start.text
    start_body = start.json()

    # 6. Result status check.
    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"] == "available"

    # 7. Result review (approve).
    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_prefix}-result-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "3C golden path — output traceable for package preview.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"

    return (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    )


def _commit_package(
    client: TestClient,
    *,
    request_prefix: str,
    session_id: str,
    approval_body: dict,
    selection_body: dict,
    preview_body: dict,
    start_body: dict,
    review_body: dict,
) -> dict:
    """Run package/review/preview then package/review/commit.
    Returns the commit response JSON body."""
    pass_run_id = selection_body["pass_run_ids"][0]

    pkg_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview.status_code == 200, pkg_preview.text
    pkg_preview_body = pkg_preview.json()

    pkg_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": pkg_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert pkg_commit.status_code == 200, pkg_commit.text
    return pkg_commit.json()


def _load_payload(payload_ref: str) -> dict:
    return json.loads(Path(payload_ref).read_text(encoding="utf-8"))


def _packages_by_kind(db, session_id: str) -> dict[str, L3OutputPackage]:
    rows = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .all()
    )
    return {row.package_kind: row for row in rows}


# ---------------------------------------------------------------------------
# TEST A — flag OFF (default) → committed payload has NO roster
# ---------------------------------------------------------------------------


def test_3c_golden_path_flag_off_no_inventory(client, tmp_path, monkeypatch):
    """When the flag is OFF (default), the committed packages must NOT contain
    an analysis_product_inventory section — proves default-off cleanliness at
    the FULL construction level (not just the helper level)."""
    request_prefix = "3c-flag-off"

    # Ensure the flag is explicitly OFF for this test (it defaults to False, but
    # we set it explicitly to document the intent and guard against test-order effects).
    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        False,
    )

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_package_eligible_product(
        client, tmp_path, request_prefix=request_prefix
    )

    _commit_package(
        client,
        request_prefix=request_prefix,
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        preview_body=preview_body,
        start_body=start_body,
        review_body=review_body,
    )

    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) == {
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    }, f"Unexpected package kinds: {set(rows)}"

    for kind, row in rows.items():
        assert Path(row.payload_ref).exists(), f"Payload file missing for kind {kind}"
        payload = _load_payload(row.payload_ref)
        assert "analysis_product_inventory" not in payload, (
            f"analysis_product_inventory must be absent when flag is OFF; found in {kind}"
        )


# ---------------------------------------------------------------------------
# TEST B — flag ON → committed payload carries the bounded roster
# ---------------------------------------------------------------------------


def test_3c_golden_path_flag_on_inventory_present(client, tmp_path, monkeypatch):
    """When the flag is ON, every committed package must carry an
    analysis_product_inventory section, with the correct schema and invariants:
      - canonical_internal & review_facing: full product entries (title,
        evidence_refs, basis_hash); no 'body' key.
      - user_facing: minimal entries (product_kind + by_evidence_role only);
        no title/evidence_refs/basis_hash.
      - No-body invariant: 'body' absent from ALL payload JSON strings.
      - Title leak check: title present in canonical/review but absent from user_facing.
    """
    request_prefix = "3c-flag-on"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_package_eligible_product(
        client, tmp_path, request_prefix=request_prefix
    )

    _commit_package(
        client,
        request_prefix=request_prefix,
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        preview_body=preview_body,
        start_body=start_body,
        review_body=review_body,
    )

    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) == {
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    }, f"Unexpected package kinds: {set(rows)}"

    # All payload files must exist.
    for kind, row in rows.items():
        assert Path(row.payload_ref).exists(), f"Payload file missing for kind {kind}"

    canonical_payload = _load_payload(rows[PACKAGE_KIND_CANONICAL_INTERNAL].payload_ref)
    user_payload = _load_payload(rows[PACKAGE_KIND_USER_FACING].payload_ref)
    review_payload = _load_payload(rows[PACKAGE_KIND_REVIEW_FACING].payload_ref)

    # ------------------------------------------------------------------
    # NO-BODY INVARIANT: 'body' key must not appear in any payload JSON.
    # ------------------------------------------------------------------
    for kind, payload in [
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_USER_FACING, user_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_payload),
    ]:
        payload_text = json.dumps(payload)
        assert '"body"' not in payload_text, (
            f"'body' key found in {kind} payload — body must never appear in package payloads"
        )
        assert "Body text — should never appear in package payload." not in payload_text, (
            f"Raw body text leaked into {kind} payload"
        )

    # ------------------------------------------------------------------
    # analysis_product_inventory present in all three kinds.
    # ------------------------------------------------------------------
    for kind, payload in [
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_USER_FACING, user_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_payload),
    ]:
        assert "analysis_product_inventory" in payload, (
            f"analysis_product_inventory missing from {kind} payload when flag is ON"
        )

    # ------------------------------------------------------------------
    # canonical_internal: full product entries.
    # ------------------------------------------------------------------
    canonical_inv = canonical_payload["analysis_product_inventory"]
    assert canonical_inv["schema_id"] == "layer3.analysis_product_package_inventory.v1"
    assert canonical_inv["package_eligible_product_count"] == 1

    canonical_products = canonical_inv["products"]
    assert len(canonical_products) == 1

    canonical_product = canonical_products[0]
    assert canonical_product["product_kind"] == "finding"
    assert canonical_product["lifecycle_status"] == "package_eligible"
    assert canonical_product.get("title"), "canonical_internal product must have a non-empty title"
    # evidence_refs present and contains the material_snapshot ref
    assert "evidence_refs" in canonical_product, "canonical_internal product must have evidence_refs"
    assert len(canonical_product["evidence_refs"]) >= 1
    evidence_ref = canonical_product["evidence_refs"][0]
    assert evidence_ref.get("ref_kind") == "material_snapshot"
    assert evidence_ref.get("ref_id"), "evidence ref_id must be non-empty"
    # basis_hash present
    assert "basis_hash" in canonical_product, "canonical_internal product must have basis_hash"
    # NO body key
    assert "body" not in canonical_product, "canonical_internal product must NOT have a body key"

    # ------------------------------------------------------------------
    # review_facing: same full structure as canonical_internal.
    # ------------------------------------------------------------------
    review_inv = review_payload["analysis_product_inventory"]
    assert review_inv["schema_id"] == "layer3.analysis_product_package_inventory.v1"
    assert review_inv["package_eligible_product_count"] == 1

    review_products = review_inv["products"]
    assert len(review_products) == 1

    review_product = review_products[0]
    assert review_product["product_kind"] == "finding"
    assert review_product["lifecycle_status"] == "package_eligible"
    assert review_product.get("title"), "review_facing product must have a non-empty title"
    assert "evidence_refs" in review_product, "review_facing product must have evidence_refs"
    assert "basis_hash" in review_product, "review_facing product must have basis_hash"
    assert "body" not in review_product, "review_facing product must NOT have a body key"

    # ------------------------------------------------------------------
    # user_facing: minimized — product_kind + by_evidence_role ONLY.
    # ------------------------------------------------------------------
    user_inv = user_payload["analysis_product_inventory"]
    assert user_inv["schema_id"] == "layer3.analysis_product_package_inventory.v1"

    user_products = user_inv["products"]
    assert len(user_products) == 1

    user_product = user_products[0]
    assert user_product["product_kind"] == "finding"
    # Minimization invariants: no title, evidence_refs, basis_hash, or body.
    assert "title" not in user_product, (
        "user_facing product must NOT expose title"
    )
    assert "evidence_refs" not in user_product, (
        "user_facing product must NOT expose evidence_refs"
    )
    assert "basis_hash" not in user_product, (
        "user_facing product must NOT expose basis_hash"
    )
    assert "body" not in user_product, (
        "user_facing product must NOT expose body"
    )
    assert "executor_type" not in user_product, (
        "user_facing product must NOT expose executor_type"
    )
    assert "generation_method" not in user_product, (
        "user_facing product must NOT expose generation_method"
    )
    # by_evidence_role must be present (the only allowed summary field)
    assert "by_evidence_role" in user_product, (
        "user_facing product must carry by_evidence_role summary"
    )
    # The bounded analysis_product_id IS permitted in user_facing (it is an
    # identifier, not a value); the minimization excludes title/evidence_refs/
    # basis_hash/body, NOT the id. Document that boundary explicitly.
    assert "analysis_product_id" in user_product, (
        "user_facing product should carry the bounded analysis_product_id"
    )

    # ------------------------------------------------------------------
    # PROVENANCE: executor_type + generation_method (human-authored product).
    # ------------------------------------------------------------------
    # The golden-path product is human-authored: executor_type must be "human"
    # and generation_method must be None (deterministic-only field).
    assert canonical_product.get("executor_type") == "human", (
        f"canonical_internal product executor_type must be 'human', got {canonical_product.get('executor_type')!r}"
    )
    assert canonical_product.get("generation_method") is None, (
        f"canonical_internal product generation_method must be None for human product, "
        f"got {canonical_product.get('generation_method')!r}"
    )
    assert review_product.get("executor_type") == "human", (
        f"review_facing product executor_type must be 'human', got {review_product.get('executor_type')!r}"
    )
    assert review_product.get("generation_method") is None, (
        f"review_facing product generation_method must be None for human product, "
        f"got {review_product.get('generation_method')!r}"
    )

    # ------------------------------------------------------------------
    # TITLE LEAK CHECK:
    # product title appears in canonical/review payloads but NOT in user_facing.
    # ------------------------------------------------------------------
    product_title = canonical_product["title"]
    assert product_title in json.dumps(canonical_payload), (
        "Product title must appear in canonical_internal payload"
    )
    assert product_title in json.dumps(review_payload), (
        "Product title must appear in review_facing payload"
    )
    assert product_title not in json.dumps(user_payload), (
        "Product title must NOT appear in user_facing payload (title leak)"
    )


# ---------------------------------------------------------------------------
# TEST C - package preview hash binds the package-eligible roster
# ---------------------------------------------------------------------------

def test_3c_package_commit_rejects_stale_analysis_product_roster(
    client,
    tmp_path,
    monkeypatch,
):
    request_prefix = "3c-roster-stale"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_package_eligible_product(
        client, tmp_path, request_prefix=request_prefix
    )

    pass_run_id = selection_body["pass_run_ids"][0]
    pkg_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview.status_code == 200, pkg_preview.text
    pkg_preview_body = pkg_preview.json()

    db = client.layer3_session_factory()
    try:
        late_product = _make_grounded_product_for_session(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-late-product",
        )
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=late_product.analysis_product_id,
            prefix=f"{request_prefix}-late-promote",
        )
    finally:
        db.close()

    stale_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": pkg_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )

    assert stale_commit.status_code == 409, stale_commit.text
    assert stale_commit.json()["error_code"] == "package_review_preview_mismatch"


# ---------------------------------------------------------------------------
# TEST D - working_set evidence ref survives into committed package payload
# ---------------------------------------------------------------------------


def _build_session_with_working_set_eligible_product(
    client: TestClient,
    tmp_path: Path,
    *,
    request_prefix: str,
) -> tuple[str, str, dict, dict, dict, dict, dict, dict]:
    """Build a quant session, create a working set, author a product whose
    evidence ref is the working_set, promote to package_eligible, and run the
    full plan/approve + exec/select + exec/start + result/review chain.

    Returns:
        (session_id, working_set_id, preview_body, approval_body,
         selection_body, start_body, status_body, review_body)
    """
    # 1. Build the quant-ready session via direct DB call.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    # 2. Create a working set + author a product with working_set evidence.
    db = client.layer3_session_factory()
    try:
        # Query the real material_snapshot id so we can add it as a working set member.
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .first()
        )
        assert snapshot is not None, f"No material snapshot for session {session_id}"

        ws_draft = WorkingSetDraft(
            name="WS-lineage test set",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot",
                    ref_id=snapshot.material_snapshot_id,
                ),
            ),
        )
        ws_result = create_working_set(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-ws-create",
            draft=ws_draft,
        )
        db.commit()
        working_set_id = ws_result.working_set.working_set_id

        # Author a grounded product with a working_set evidence ref.
        product_draft = AnalysisProductDraft(
            product_kind="finding",
            title="WS-lineage finding",
            body="Body text — should never appear in package payload.",
            evidence=(
                AnalysisProductEvidenceDraft(
                    ref_kind="working_set",
                    ref_id=working_set_id,
                    evidence_role="context",
                ),
            ),
        )
        product_result = create_analysis_product_draft(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-product",
            draft=product_draft,
        )
        db.commit()
        product_id = product_result.product.analysis_product_id

        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=product_id,
            prefix=f"{request_prefix}-promote",
        )
    finally:
        db.close()

    # 3. Plan preview + approve (API).
    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"{request_prefix}-plan-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"{request_prefix}-plan-approve",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200, approval.text
    approval_body = approval.json()

    # 4. Execution select.
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_prefix}-exec-select",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200, selection.text
    selection_body = selection.json()
    pass_run_id = selection_body["pass_run_ids"][0]

    # 5. Execution start.
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_prefix}-exec-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200, start.text
    start_body = start.json()

    # 6. Result status check.
    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"] == "available"

    # 7. Result review (approve).
    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_prefix}-result-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "WS-lineage golden path — working_set evidence ref traceable.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"

    return (
        session_id,
        working_set_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    )


def test_3c_working_set_lineage_survives_package_commit(client, tmp_path, monkeypatch):
    """CORE PROOF: a product whose evidence ref is a working_set ref survives
    END-TO-END into the committed canonical_internal and review_facing package
    payloads with the exact ref_kind=='working_set' and ref_id preserved.

    Invariants asserted for canonical_internal and review_facing:
      - analysis_product_inventory.products contains the finding.
      - that product's evidence_refs has an entry with ref_kind=='working_set'
        AND ref_id==<working_set_id>.
      - No-body invariant: raw body text does not appear in the payload JSON.
    """
    request_prefix = "3c-ws-lineage"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        working_set_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_working_set_eligible_product(
        client, tmp_path, request_prefix=request_prefix
    )

    _commit_package(
        client,
        request_prefix=request_prefix,
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        preview_body=preview_body,
        start_body=start_body,
        review_body=review_body,
    )

    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) >= {PACKAGE_KIND_CANONICAL_INTERNAL, PACKAGE_KIND_REVIEW_FACING}, (
        f"Expected at least canonical_internal and review_facing; got {set(rows)}"
    )

    for kind in (PACKAGE_KIND_CANONICAL_INTERNAL, PACKAGE_KIND_REVIEW_FACING):
        row = rows[kind]
        assert row.payload_ref and Path(row.payload_ref).exists(), (
            f"Payload file missing for kind {kind}"
        )
        payload = _load_payload(row.payload_ref)

        # analysis_product_inventory must be present (flag is ON).
        assert "analysis_product_inventory" in payload, (
            f"analysis_product_inventory missing from {kind} payload"
        )

        products = payload["analysis_product_inventory"]["products"]
        findings = [p for p in products if p.get("product_kind") == "finding"]
        assert len(findings) >= 1, (
            f"No finding product found in {kind} analysis_product_inventory"
        )

        # CORE PROOF: the finding carries a working_set evidence ref with the
        # exact working_set_id created in this test.
        finding = findings[0]
        assert "evidence_refs" in finding, (
            f"{kind} finding must carry evidence_refs"
        )
        ws_refs = [
            ref for ref in finding["evidence_refs"]
            if ref.get("ref_kind") == "working_set"
        ]
        assert len(ws_refs) >= 1, (
            f"{kind} finding has no evidence_ref with ref_kind=='working_set'; "
            f"got evidence_refs={finding['evidence_refs']}"
        )
        assert ws_refs[0]["ref_id"] == working_set_id, (
            f"{kind} working_set ref_id mismatch: expected {working_set_id!r}, "
            f"got {ws_refs[0]['ref_id']!r}"
        )

        # No-body invariant: body text must not leak into the committed payload.
        payload_text = json.dumps(payload)
        assert "Body text — should never appear in package payload." not in payload_text, (
            f"Raw body text leaked into {kind} payload"
        )


# ---------------------------------------------------------------------------
# TEST D — deterministic generation → package → provenance
# ---------------------------------------------------------------------------

_DETERMINISTIC_METHOD_ID = "working_set_composition_summary"
_DETERMINISTIC_METHOD_VERSION = DETERMINISTIC_METHODS[_DETERMINISTIC_METHOD_ID].version


def _build_session_with_deterministic_eligible_product(
    client: TestClient,
    tmp_path: Path,
    *,
    request_prefix: str,
) -> tuple[str, str, dict, dict, dict, dict, dict, dict]:
    """Build a quant session, create a working set, GENERATE a product
    deterministically over that working set, promote to package_eligible,
    and run the full plan/approve + exec/select + exec/start + result/review
    chain.

    Returns:
        (session_id, generated_product_id, preview_body, approval_body,
         selection_body, start_body, status_body, review_body)
    """
    # 1. Build the quant-ready session via direct DB call.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    # 2. Create a working set, then generate a product deterministically.
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .first()
        )
        assert snapshot is not None, f"No material snapshot for session {session_id}"

        ws_draft = WorkingSetDraft(
            name="Deterministic provenance test set",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot",
                    ref_id=snapshot.material_snapshot_id,
                ),
            ),
        )
        ws_result = create_working_set(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-ws-create",
            draft=ws_draft,
        )
        db.commit()
        working_set_id = ws_result.working_set.working_set_id

        # Generate the product deterministically (flushes but does not commit).
        gen_result = generate_analysis_product(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-gen",
            working_set_id=working_set_id,
            method_id=_DETERMINISTIC_METHOD_ID,
        )
        db.commit()
        generated_product_id = gen_result.product.analysis_product_id

        # Promote the generated (draft) product to package_eligible via the
        # standard 4-step path.
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=generated_product_id,
            prefix=f"{request_prefix}-promote",
        )
    finally:
        db.close()

    # 3. Plan preview + approve (API).
    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"{request_prefix}-plan-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"{request_prefix}-plan-approve",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200, approval.text
    approval_body = approval.json()

    # 4. Execution select.
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_prefix}-exec-select",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200, selection.text
    selection_body = selection.json()
    pass_run_id = selection_body["pass_run_ids"][0]

    # 5. Execution start.
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_prefix}-exec-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200, start.text
    start_body = start.json()

    # 6. Result status check.
    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"] == "available"

    # 7. Result review (approve).
    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_prefix}-result-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Deterministic provenance golden path — executor_type traceable.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "generated_narrative",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"

    return (
        session_id,
        generated_product_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    )


def test_3c_deterministic_provenance_survives_package_commit(client, tmp_path, monkeypatch):
    """CORE PROOF: a product generated via the deterministic path carries
    executor_type=='deterministic' and the exact generation_method dict into the
    COMMITTED canonical_internal and review_facing package payloads.

    Invariants asserted for canonical_internal and review_facing:
      - analysis_product_inventory.products contains the generated product
        (matched by analysis_product_id).
      - executor_type == "deterministic".
      - generation_method == {"method_id": "working_set_composition_summary",
                               "method_version": <version from registry>}.
      - No-body invariant holds (body never leaks).
    """
    request_prefix = "3c-det-prov"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        generated_product_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_deterministic_eligible_product(
        client, tmp_path, request_prefix=request_prefix
    )

    _commit_package(
        client,
        request_prefix=request_prefix,
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        preview_body=preview_body,
        start_body=start_body,
        review_body=review_body,
    )

    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) >= {PACKAGE_KIND_CANONICAL_INTERNAL, PACKAGE_KIND_REVIEW_FACING}, (
        f"Expected at least canonical_internal and review_facing; got {set(rows)}"
    )

    expected_generation_method = {
        "method_id": _DETERMINISTIC_METHOD_ID,
        "method_version": _DETERMINISTIC_METHOD_VERSION,
    }

    for kind in (PACKAGE_KIND_CANONICAL_INTERNAL, PACKAGE_KIND_REVIEW_FACING):
        row = rows[kind]
        assert row.payload_ref and Path(row.payload_ref).exists(), (
            f"Payload file missing for kind {kind}"
        )
        payload = _load_payload(row.payload_ref)

        # analysis_product_inventory must be present (flag is ON).
        assert "analysis_product_inventory" in payload, (
            f"analysis_product_inventory missing from {kind} payload"
        )

        products = payload["analysis_product_inventory"]["products"]

        # Locate the generated product by analysis_product_id.
        matching = [
            p for p in products
            if p.get("analysis_product_id") == generated_product_id
        ]
        assert len(matching) == 1, (
            f"{kind}: expected exactly 1 product with analysis_product_id="
            f"{generated_product_id!r}; found {len(matching)} in "
            f"{[p.get('analysis_product_id') for p in products]}"
        )
        det_product = matching[0]

        # Lifecycle must have reached package_eligible.
        assert det_product.get("lifecycle_status") == "package_eligible", (
            f"{kind}: deterministic product lifecycle_status must be 'package_eligible', "
            f"got {det_product.get('lifecycle_status')!r}"
        )

        # CORE PROOF — executor_type.
        assert det_product.get("executor_type") == "deterministic", (
            f"{kind}: executor_type must be 'deterministic', "
            f"got {det_product.get('executor_type')!r}"
        )

        # CORE PROOF — generation_method exact dict.
        assert det_product.get("generation_method") == expected_generation_method, (
            f"{kind}: generation_method mismatch.\n"
            f"  expected: {expected_generation_method!r}\n"
            f"  got:      {det_product.get('generation_method')!r}"
        )

        # No-body invariant.
        payload_text = json.dumps(payload)
        assert '"body"' not in payload_text, (
            f"'body' key found in {kind} payload — body must never appear in package payloads"
        )


# ---------------------------------------------------------------------------
# TEST E — mixed-state roster: only package_eligible subset embeds
# ---------------------------------------------------------------------------

# Expected key sets (verified against source layer3_workbench.py).
_PREVIEW_PRODUCT_KEYS = frozenset(
    {"product_kind", "lifecycle_status", "evidence_count", "basis_hash", "executor_type"}
)
_FULL_INVENTORY_PRODUCT_KEYS = frozenset(
    {
        "analysis_product_id",
        "product_kind",
        "title",
        "lifecycle_status",
        "basis_hash",
        "evidence_refs",
        "evidence_refs_truncated",
        "by_evidence_role",
        "latest_review_decision",
        "executor_type",
        "generation_method",
    }
)
_USER_FACING_PRODUCT_KEYS = frozenset(
    {"analysis_product_id", "product_kind", "by_evidence_role"}
)


def _build_session_with_mixed_products(
    client: TestClient,
    tmp_path: Path,
    *,
    request_prefix: str,
) -> tuple[str, str, str, dict, dict, dict, dict, dict, dict]:
    """Build a quant session with 5 products in different lifecycle states,
    run the full plan/approve + exec/select + exec/start + result/review chain.

    Products created:
      1. draft_id         — created, never transitioned
      2. accepted_id      — promoted to 'accepted' (not package_eligible)
      3. rejected_id      — promoted draft->proposed, then rejected
      4. eligible_human   — human-authored w/ material_snapshot ref, package_eligible
      5. eligible_det     — deterministic product via working_set, package_eligible

    Returns:
        (session_id, eligible_human_id, eligible_det_id,
         preview_body, approval_body, selection_body,
         start_body, status_body, review_body)
    """
    # 1. Build the quant-ready session via direct DB call.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    # 2. Create all 5 products.
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .first()
        )
        assert snapshot is not None, f"No material snapshot for session {session_id}"

        # --- product 1: draft (never transitioned) ---
        draft_result = create_analysis_product_draft(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-p1-draft",
            draft=AnalysisProductDraft(
                product_kind="finding",
                title="Mixed-state: draft product",
                body="Body — draft.",
                evidence=(
                    AnalysisProductEvidenceDraft(
                        ref_kind="material_snapshot",
                        ref_id=snapshot.material_snapshot_id,
                        evidence_role="observation",
                    ),
                ),
            ),
        )
        db.commit()
        _draft_id = draft_result.product.analysis_product_id  # noqa: F841

        # --- product 2: accepted (draft->proposed->validated->accepted) ---
        accepted_result = create_analysis_product_draft(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-p2-accepted",
            draft=AnalysisProductDraft(
                product_kind="finding",
                title="Mixed-state: accepted product",
                body="Body — accepted.",
                evidence=(
                    AnalysisProductEvidenceDraft(
                        ref_kind="material_snapshot",
                        ref_id=snapshot.material_snapshot_id,
                        evidence_role="observation",
                    ),
                ),
            ),
        )
        db.commit()
        accepted_id = accepted_result.product.analysis_product_id
        for i, (intent, code) in enumerate(
            [("promote", "proposed_ready"), ("promote", "validation_passed"), ("accept", "grounded_accept")]
        ):
            transition_analysis_product(
                db,
                session_id=session_id,
                analysis_product_id=accepted_id,
                client_request_id=f"{request_prefix}-p2-step-{i}",
                request=AnalysisProductTransitionRequest(
                    decision_intent=intent,
                    decision_reason_code=code,
                ),
            )
            db.commit()

        # --- product 3: rejected (draft->proposed->rejected) ---
        rejected_result = create_analysis_product_draft(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-p3-rejected",
            draft=AnalysisProductDraft(
                product_kind="finding",
                title="Mixed-state: rejected product",
                body="Body — rejected.",
                evidence=(
                    AnalysisProductEvidenceDraft(
                        ref_kind="material_snapshot",
                        ref_id=snapshot.material_snapshot_id,
                        evidence_role="observation",
                    ),
                ),
            ),
        )
        db.commit()
        rejected_id = rejected_result.product.analysis_product_id
        transition_analysis_product(
            db,
            session_id=session_id,
            analysis_product_id=rejected_id,
            client_request_id=f"{request_prefix}-p3-step-0",
            request=AnalysisProductTransitionRequest(
                decision_intent="promote",
                decision_reason_code="proposed_ready",
            ),
        )
        db.commit()
        transition_analysis_product(
            db,
            session_id=session_id,
            analysis_product_id=rejected_id,
            client_request_id=f"{request_prefix}-p3-step-1",
            request=AnalysisProductTransitionRequest(
                decision_intent="reject",
                decision_reason_code="evidence_gap",
                decision_notes="Insufficient evidence for inclusion.",
            ),
        )
        db.commit()

        # --- product 4: eligible_human (material_snapshot evidence, package_eligible) ---
        human_result = create_analysis_product_draft(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-p4-human",
            draft=AnalysisProductDraft(
                product_kind="finding",
                title="Mixed-state: human-authored eligible product",
                body="Body — human eligible.",
                evidence=(
                    AnalysisProductEvidenceDraft(
                        ref_kind="material_snapshot",
                        ref_id=snapshot.material_snapshot_id,
                        evidence_role="observation",
                    ),
                ),
            ),
        )
        db.commit()
        eligible_human_id = human_result.product.analysis_product_id
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=eligible_human_id,
            prefix=f"{request_prefix}-p4-promote",
        )

        # --- product 5: eligible_det (deterministic generation over working_set) ---
        ws_draft = WorkingSetDraft(
            name="Mixed-state deterministic working set",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot",
                    ref_id=snapshot.material_snapshot_id,
                ),
            ),
        )
        ws_result = create_working_set(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-p5-ws",
            draft=ws_draft,
        )
        db.commit()
        working_set_id = ws_result.working_set.working_set_id

        gen_result = generate_analysis_product(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-p5-gen",
            working_set_id=working_set_id,
            method_id=_DETERMINISTIC_METHOD_ID,
        )
        db.commit()
        eligible_det_id = gen_result.product.analysis_product_id
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=eligible_det_id,
            prefix=f"{request_prefix}-p5-promote",
        )
    finally:
        db.close()

    # 3. Plan preview + approve (API).
    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"{request_prefix}-plan-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"{request_prefix}-plan-approve",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200, approval.text
    approval_body = approval.json()

    # 4. Execution select.
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_prefix}-exec-select",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200, selection.text
    selection_body = selection.json()
    pass_run_id = selection_body["pass_run_ids"][0]

    # 5. Execution start.
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_prefix}-exec-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200, start.text
    start_body = start.json()

    # 6. Result status check.
    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"] == "available"

    # 7. Result review (approve).
    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_prefix}-result-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Mixed-state golden path — only eligible subset embeds.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"

    return (
        session_id,
        eligible_human_id,
        eligible_det_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    )


def test_3c_multi_product_mixed_states_only_eligible_subset_embeds(
    client, tmp_path, monkeypatch
):
    """Five products in mixed states — only the two package_eligible ones embed.

    Products: draft, accepted (not eligible), rejected, eligible_human,
    eligible_det.

    Asserts:
      (a) package/review/preview admission section: available=True,
          embedding_enabled=True, count=2, correct basis_hash set,
          preview entries carry exactly the preview key set.
      (b) package/review/commit payloads: each kind's inventory contains
          exactly {eligible_human, eligible_det}; draft/accepted/rejected ids
          absent; key-set invariants per kind; no '"body"' substring; executor
          provenance correct for each eligible product.
    """
    request_prefix = "3c-mixed-states"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        eligible_human_id,
        eligible_det_id,
        plan_preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_mixed_products(
        client, tmp_path, request_prefix=request_prefix
    )

    pass_run_id = selection_body["pass_run_ids"][0]

    # ------------------------------------------------------------------
    # (a) package/review/preview — assert admission section.
    # ------------------------------------------------------------------
    pkg_preview_resp = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan_preview_body["preview_id"],
            "preview_hash": plan_preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview_resp.status_code == 200, pkg_preview_resp.text
    pkg_preview_body = pkg_preview_resp.json()

    admission = pkg_preview_body["analysis_product_admission"]
    assert admission["available"] is True, (
        f"admission.available must be True; got {admission['available']!r}"
    )
    assert admission["embedding_enabled"] is True, (
        f"admission.embedding_enabled must be True; got {admission['embedding_enabled']!r}"
    )
    assert admission["package_eligible_product_count"] == 2, (
        f"admission.package_eligible_product_count must be 2; "
        f"got {admission['package_eligible_product_count']!r}"
    )
    assert admission["total_package_eligible"] == 2, (
        f"admission.total_package_eligible must be 2; "
        f"got {admission['total_package_eligible']!r}"
    )
    assert admission["truncated"] is False, (
        f"admission.truncated must be False; got {admission['truncated']!r}"
    )
    assert len(admission["products"]) == 2, (
        f"admission must carry exactly 2 preview products; "
        f"got {len(admission['products'])}"
    )

    # Fetch the two eligible products' basis_hashes from DB to compare.
    db = client.layer3_session_factory()
    try:
        human_row = (
            db.query(L3AnalysisProduct)
            .filter(L3AnalysisProduct.analysis_product_id == eligible_human_id)
            .first()
        )
        det_row = (
            db.query(L3AnalysisProduct)
            .filter(L3AnalysisProduct.analysis_product_id == eligible_det_id)
            .first()
        )
        assert human_row is not None and det_row is not None
        expected_basis_hashes = {human_row.basis_hash, det_row.basis_hash}
    finally:
        db.close()

    preview_basis_hashes = {p["basis_hash"] for p in admission["products"]}
    assert preview_basis_hashes == expected_basis_hashes, (
        f"admission preview basis_hash set mismatch.\n"
        f"  expected: {expected_basis_hashes!r}\n"
        f"  got:      {preview_basis_hashes!r}"
    )

    # Each preview entry must carry ONLY the preview key set (no extra keys).
    for entry in admission["products"]:
        assert set(entry.keys()) == _PREVIEW_PRODUCT_KEYS, (
            f"Preview product entry has unexpected keys.\n"
            f"  expected: {sorted(_PREVIEW_PRODUCT_KEYS)}\n"
            f"  got:      {sorted(entry.keys())}"
        )

    # ------------------------------------------------------------------
    # (b) package/review/commit — assert committed payloads.
    # ------------------------------------------------------------------
    pkg_commit_resp = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan_preview_body["preview_id"],
            "preview_hash": plan_preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": pkg_preview_body["package_review_preview_hash"],
            "expected_package_kinds": [
                "canonical_internal",
                "user_facing",
                "review_facing",
            ],
        },
    )
    assert pkg_commit_resp.status_code == 200, pkg_commit_resp.text

    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) == {
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    }, f"Unexpected package kinds: {set(rows)}"

    canonical_payload = _load_payload(rows[PACKAGE_KIND_CANONICAL_INTERNAL].payload_ref)
    user_payload = _load_payload(rows[PACKAGE_KIND_USER_FACING].payload_ref)
    review_payload = _load_payload(rows[PACKAGE_KIND_REVIEW_FACING].payload_ref)

    expected_eligible_ids = {eligible_human_id, eligible_det_id}

    # Collect all product ids in this session to derive the non-eligible ones.
    db = client.layer3_session_factory()
    try:
        all_products = (
            db.query(L3AnalysisProduct)
            .filter(L3AnalysisProduct.session_id == session_id)
            .all()
        )
        non_eligible_ids = {
            p.analysis_product_id
            for p in all_products
            if p.analysis_product_id not in expected_eligible_ids
        }
    finally:
        db.close()

    # Pin the excluded population: draft + accepted + rejected must all exist,
    # otherwise the exclusion loop below weakens silently.
    assert len(non_eligible_ids) == 3, non_eligible_ids

    for kind, payload in [
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_USER_FACING, user_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_payload),
    ]:
        inv = payload["analysis_product_inventory"]

        # Correct counts.
        assert inv["package_eligible_product_count"] == 2, (
            f"{kind}: package_eligible_product_count must be 2; got {inv['package_eligible_product_count']!r}"
        )
        assert inv["total_package_eligible"] == 2, (
            f"{kind}: total_package_eligible must be 2; got {inv['total_package_eligible']!r}"
        )
        assert inv["truncated"] is False, (
            f"{kind}: truncated must be False; got {inv['truncated']!r}"
        )

        products = inv["products"]
        assert len(products) == 2, (
            f"{kind}: inventory must contain exactly 2 products; got {len(products)}"
        )

        # Exact id set matches the two eligible products.
        actual_ids = {p["analysis_product_id"] for p in products}
        assert actual_ids == expected_eligible_ids, (
            f"{kind}: product id set mismatch.\n"
            f"  expected: {expected_eligible_ids!r}\n"
            f"  got:      {actual_ids!r}"
        )

        # Non-eligible ids must be absent from the serialized inventory section.
        inv_text = json.dumps(inv)
        for bad_id in non_eligible_ids:
            assert bad_id not in inv_text, (
                f"{kind}: non-eligible product id {bad_id!r} found in serialized "
                f"analysis_product_inventory"
            )

        # No '"body"' key anywhere in the committed payload (full-payload scope,
        # matching Test D and the bounded-e2e boundedness test).
        payload_text = json.dumps(payload)
        assert '"body"' not in payload_text, (
            f"{kind}: '\"body\"' found in serialized committed payload"
        )

    # Per-kind key-set invariants.
    for kind, payload in [
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_payload),
    ]:
        for entry in payload["analysis_product_inventory"]["products"]:
            assert set(entry.keys()) == _FULL_INVENTORY_PRODUCT_KEYS, (
                f"{kind}: full product entry has unexpected keys.\n"
                f"  expected: {sorted(_FULL_INVENTORY_PRODUCT_KEYS)}\n"
                f"  got:      {sorted(entry.keys())}"
            )

    for entry in user_payload["analysis_product_inventory"]["products"]:
        assert set(entry.keys()) == _USER_FACING_PRODUCT_KEYS, (
            f"user_facing: product entry has unexpected keys.\n"
            f"  expected: {sorted(_USER_FACING_PRODUCT_KEYS)}\n"
            f"  got:      {sorted(entry.keys())}"
        )

    # Executor provenance: one human, one deterministic.
    canonical_products = canonical_payload["analysis_product_inventory"]["products"]

    human_entries = [
        p for p in canonical_products
        if p["analysis_product_id"] == eligible_human_id
    ]
    assert len(human_entries) == 1
    human_entry = human_entries[0]
    assert human_entry.get("executor_type") == "human", (
        f"eligible_human executor_type must be 'human'; "
        f"got {human_entry.get('executor_type')!r}"
    )
    assert human_entry.get("generation_method") is None, (
        f"eligible_human generation_method must be None; "
        f"got {human_entry.get('generation_method')!r}"
    )

    det_entries = [
        p for p in canonical_products
        if p["analysis_product_id"] == eligible_det_id
    ]
    assert len(det_entries) == 1
    det_entry = det_entries[0]
    assert det_entry.get("executor_type") == "deterministic", (
        f"eligible_det executor_type must be 'deterministic'; "
        f"got {det_entry.get('executor_type')!r}"
    )
    expected_gen_method = {
        "method_id": _DETERMINISTIC_METHOD_ID,
        "method_version": _DETERMINISTIC_METHOD_VERSION,
    }
    assert det_entry.get("generation_method") == expected_gen_method, (
        f"eligible_det generation_method mismatch.\n"
        f"  expected: {expected_gen_method!r}\n"
        f"  got:      {det_entry.get('generation_method')!r}"
    )


# ---------------------------------------------------------------------------
# TEST F — two-product roster stale after third promotion (2-product baseline)
# ---------------------------------------------------------------------------


def _build_session_with_two_package_eligible_products(
    client: TestClient,
    tmp_path: Path,
    *,
    request_prefix: str,
) -> tuple[str, dict, dict, dict, dict, dict, dict]:
    """Build a quant session with TWO package_eligible products and run
    the full plan/approve + exec/select + exec/start + result/review chain.

    Returns:
        (session_id, preview_body, approval_body, selection_body,
         start_body, status_body, review_body)
    """
    # 1. Build the quant-ready session via direct DB call.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    # 2. Author two grounded products and promote both to package_eligible.
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .first()
        )
        assert snapshot is not None, f"No material snapshot for session {session_id}"

        for idx in range(2):
            prod_result = create_analysis_product_draft(
                db,
                session_id=session_id,
                client_request_id=f"{request_prefix}-p{idx}",
                draft=AnalysisProductDraft(
                    product_kind="finding",
                    title=f"Two-eligible product {idx}",
                    body="Body — never in payload.",
                    evidence=(
                        AnalysisProductEvidenceDraft(
                            ref_kind="material_snapshot",
                            ref_id=snapshot.material_snapshot_id,
                            evidence_role="observation",
                        ),
                    ),
                ),
            )
            db.commit()
            _promote_to_package_eligible(
                db,
                session_id=session_id,
                product_id=prod_result.product.analysis_product_id,
                prefix=f"{request_prefix}-p{idx}-promote",
            )
    finally:
        db.close()

    # 3. Plan preview + approve (API).
    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"{request_prefix}-plan-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"{request_prefix}-plan-approve",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200, approval.text
    approval_body = approval.json()

    # 4. Execution select.
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_prefix}-exec-select",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200, selection.text
    selection_body = selection.json()
    pass_run_id = selection_body["pass_run_ids"][0]

    # 5. Execution start.
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_prefix}-exec-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200, start.text
    start_body = start.json()

    # 6. Result status check.
    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"] == "available"

    # 7. Result review (approve).
    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_prefix}-result-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Two-eligible baseline — stale-roster test.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"

    return (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    )


def test_3c_two_product_roster_stale_after_third_promotion_rejected(
    client, tmp_path, monkeypatch
):
    """Roster hash computed over a 2-product eligible set becomes stale when a
    third product is promoted to package_eligible before commit.

    The package/review/commit MUST reject with 409 / package_review_preview_mismatch.
    """
    request_prefix = "3c-2p-stale"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_two_package_eligible_products(
        client, tmp_path, request_prefix=request_prefix
    )

    pass_run_id = selection_body["pass_run_ids"][0]

    # Capture the admission hash over the 2-product roster.
    pkg_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview.status_code == 200, pkg_preview.text
    pkg_preview_body = pkg_preview.json()

    # Promote a THIRD product to package_eligible after the preview hash was captured.
    db = client.layer3_session_factory()
    try:
        late_product = _make_grounded_product_for_session(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-late-product",
        )
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=late_product.analysis_product_id,
            prefix=f"{request_prefix}-late-promote",
        )
    finally:
        db.close()

    # Commit with the now-stale preview hash — must be rejected.
    stale_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": pkg_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )

    assert stale_commit.status_code == 409, stale_commit.text
    assert stale_commit.json()["error_code"] == "package_review_preview_mismatch"


# ---------------------------------------------------------------------------
# TEST G — supersession v0: superseding a package_eligible product drops it
# from the future roster; stale hash is rejected; fresh preview/commit succeeds
# ---------------------------------------------------------------------------


def test_3c_supersede_drops_product_from_future_roster(
    client, tmp_path, monkeypatch
):
    """Superseding a package_eligible product removes it from the roster.

    Flow:
      1. Build a session with two package_eligible products (product #1, product #2).
      2. POST package/review/preview → admission count == 2 (capture preview hash).
      3. Supersede product #2 via the API transition route.
      4. Assert transition response lifecycle_status == "superseded".
      5. Assert the stored supersede decision carries
         successor_analysis_product_id == product #1's id (via DB).
      6. POST package/review/commit with the STALE preview hash → 409 mismatch.
      7. Re-run package/review/preview → admission count == 1, only product #1 remains.
      8. Commit with fresh hash → success; load all three committed payloads;
         assert inventory contains exactly product #1 (count 1), product #2 absent.
    """
    request_prefix = "3c-supersede-roster"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_two_package_eligible_products(
        client, tmp_path, request_prefix=request_prefix
    )

    pass_run_id = selection_body["pass_run_ids"][0]

    # Query the two package_eligible product ids from DB (ordered by id asc,
    # matching _load_package_eligible_analysis_products ordering).
    db = client.layer3_session_factory()
    try:
        eligible_rows = (
            db.query(L3AnalysisProduct)
            .filter(
                L3AnalysisProduct.session_id == session_id,
                L3AnalysisProduct.lifecycle_status == "package_eligible",
            )
            .order_by(L3AnalysisProduct.analysis_product_id)
            .all()
        )
        assert len(eligible_rows) == 2, (
            f"Expected 2 package_eligible products before supersession; "
            f"got {len(eligible_rows)}"
        )
        product_1_id = eligible_rows[0].analysis_product_id
        product_2_id = eligible_rows[1].analysis_product_id
    finally:
        db.close()

    # Step 2: package/review/preview — capture hash over the 2-product roster.
    pkg_preview_1 = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview-1",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview_1.status_code == 200, pkg_preview_1.text
    pkg_preview_1_body = pkg_preview_1.json()

    admission_1 = pkg_preview_1_body["analysis_product_admission"]
    assert admission_1["package_eligible_product_count"] == 2, (
        f"Expected 2 eligible products before supersession; "
        f"got {admission_1['package_eligible_product_count']!r}"
    )
    stale_pkg_hash = pkg_preview_1_body["package_review_preview_hash"]

    # Step 3: supersede product #2 via the API.
    supersede_resp = client.post(
        f"/api/v1/layer3/analysis-product/{product_2_id}/transition",
        json={
            "session_id": session_id,
            "client_request_id": f"{request_prefix}-supersede-p2",
            "decision_intent": "supersede",
            "decision_reason_code": "superseded_by_successor",
            "decision_notes": "Product #2 superseded by product #1 in this test.",
            "decision_provenance": {"successor_analysis_product_id": product_1_id},
        },
    )
    assert supersede_resp.status_code == 201, supersede_resp.text
    supersede_body = supersede_resp.json()

    # Step 4: transition response must show lifecycle_status == "superseded".
    assert supersede_body["lifecycle_status"] == "superseded", (
        f"Expected lifecycle_status 'superseded'; got {supersede_body['lifecycle_status']!r}"
    )

    # Step 5: verify successor_analysis_product_id stored on the decision (via DB).
    from app.models.models import L3AnalysisProductReviewDecision
    db = client.layer3_session_factory()
    try:
        p2_row = (
            db.query(L3AnalysisProduct)
            .filter(L3AnalysisProduct.analysis_product_id == product_2_id)
            .first()
        )
        assert p2_row is not None
        assert p2_row.lifecycle_status == "superseded", (
            f"product_2 lifecycle_status in DB must be 'superseded'; "
            f"got {p2_row.lifecycle_status!r}"
        )
        latest_decision = (
            db.query(L3AnalysisProductReviewDecision)
            .filter(
                L3AnalysisProductReviewDecision.analysis_product_id == product_2_id,
                L3AnalysisProductReviewDecision.review_decision == "supersede",
            )
            .order_by(L3AnalysisProductReviewDecision.analysis_product_review_decision_id.desc())
            .first()
        )
        assert latest_decision is not None, "No supersede decision recorded for product_2"
        stored_provenance = (
            latest_decision.decision_provenance_json
            if isinstance(latest_decision.decision_provenance_json, dict)
            else {}
        )
        assert stored_provenance.get("successor_analysis_product_id") == product_1_id, (
            f"Stored successor_analysis_product_id mismatch: "
            f"expected {product_1_id!r}, "
            f"got {stored_provenance.get('successor_analysis_product_id')!r}"
        )
    finally:
        db.close()

    # Step 6: commit with the STALE preview hash (captured before supersession) → 409.
    stale_commit_2 = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit-stale",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": stale_pkg_hash,
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert stale_commit_2.status_code == 409, stale_commit_2.text
    assert stale_commit_2.json()["error_code"] == "package_review_preview_mismatch"

    # Step 7: fresh package/review/preview → admission count == 1, only product #1.
    pkg_preview_2 = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview-2",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview_2.status_code == 200, pkg_preview_2.text
    pkg_preview_2_body = pkg_preview_2.json()

    admission_2 = pkg_preview_2_body["analysis_product_admission"]
    assert admission_2["available"] is True, (
        f"admission.available must be True after supersession; "
        f"got {admission_2['available']!r}"
    )
    assert admission_2["package_eligible_product_count"] == 1, (
        f"Expected 1 eligible product after supersession; "
        f"got {admission_2['package_eligible_product_count']!r}"
    )

    # Step 8: commit with the FRESH hash → success.
    fresh_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit-fresh",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": pkg_preview_2_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert fresh_commit.status_code == 200, fresh_commit.text

    # Load all three committed payloads and assert inventory invariants.
    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) == {
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    }, f"Unexpected package kinds: {set(rows)}"

    canonical_payload = _load_payload(rows[PACKAGE_KIND_CANONICAL_INTERNAL].payload_ref)
    user_payload = _load_payload(rows[PACKAGE_KIND_USER_FACING].payload_ref)
    review_payload = _load_payload(rows[PACKAGE_KIND_REVIEW_FACING].payload_ref)

    for kind, payload in [
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_USER_FACING, user_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_payload),
    ]:
        inv = payload["analysis_product_inventory"]

        # Exactly one product in the inventory.
        assert inv["package_eligible_product_count"] == 1, (
            f"{kind}: package_eligible_product_count must be 1; "
            f"got {inv['package_eligible_product_count']!r}"
        )

        products = inv["products"]
        assert len(products) == 1, (
            f"{kind}: inventory must contain exactly 1 product; got {len(products)}"
        )

        # Only product #1 present; product #2 absent from the serialized inventory.
        assert products[0]["analysis_product_id"] == product_1_id, (
            f"{kind}: inventory product must be product_1 ({product_1_id!r}); "
            f"got {products[0]['analysis_product_id']!r}"
        )
        inv_text = json.dumps(inv)
        assert product_2_id not in inv_text, (
            f"{kind}: superseded product_2 id {product_2_id!r} found in serialized inventory"
        )

        # The surviving product's latest_review_decision must NOT be a supersede
        # decision (it is product #1, not the superseded one).
        if kind != PACKAGE_KIND_USER_FACING:
            p1_entry = products[0]
            lrd = p1_entry.get("latest_review_decision")
            assert lrd is not None, (
                f"{kind}: product_1 latest_review_decision must be present"
            )
            assert lrd.get("review_decision") != "supersede", (
                f"{kind}: product_1 latest_review_decision must NOT be a supersede "
                f"decision; got {lrd.get('review_decision')!r}"
            )


# ---------------------------------------------------------------------------
# TEST H — supersession v0: superseding the only eligible product yields an
# empty roster; commit with count==0 succeeds
# ---------------------------------------------------------------------------


def test_3c_supersede_only_eligible_product_empty_roster_commit_succeeds(
    client, tmp_path, monkeypatch
):
    """Superseding the only package_eligible product gives an empty roster.

    Flow:
      1. Build a session with ONE package_eligible product.
      2. Supersede it via the API (reason: stale_basis; no successor required).
      3. POST package/review/preview → admission: available=True,
         embedding_enabled=True, count=0, products=[].
      4. POST package/review/commit with that hash → SUCCESS (count→0 boundary).
      5. Load all three committed payloads: inventory present with count=0,
         products==[], superseded product id absent from every serialized section.
    """
    request_prefix = "3c-supersede-empty"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        status_body,
        review_body,
    ) = _build_session_with_package_eligible_product(
        client, tmp_path, request_prefix=request_prefix
    )

    pass_run_id = selection_body["pass_run_ids"][0]

    # Capture the single product's id from DB.
    db = client.layer3_session_factory()
    try:
        eligible_rows = (
            db.query(L3AnalysisProduct)
            .filter(
                L3AnalysisProduct.session_id == session_id,
                L3AnalysisProduct.lifecycle_status == "package_eligible",
            )
            .all()
        )
        assert len(eligible_rows) == 1, (
            f"Expected 1 package_eligible product; got {len(eligible_rows)}"
        )
        sole_product_id = eligible_rows[0].analysis_product_id
    finally:
        db.close()

    # Step 2: supersede the only eligible product (stale_basis; no successor).
    supersede_resp = client.post(
        f"/api/v1/layer3/analysis-product/{sole_product_id}/transition",
        json={
            "session_id": session_id,
            "client_request_id": f"{request_prefix}-supersede-sole",
            "decision_intent": "supersede",
            "decision_reason_code": "stale_basis",
            "decision_notes": "Sole product superseded due to stale basis — empty roster test.",
        },
    )
    assert supersede_resp.status_code == 201, supersede_resp.text
    assert supersede_resp.json()["lifecycle_status"] == "superseded", (
        f"Expected lifecycle_status 'superseded'; "
        f"got {supersede_resp.json()['lifecycle_status']!r}"
    )

    # Step 3: package/review/preview → empty roster admission.
    pkg_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_prefix}-pkg-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert pkg_preview.status_code == 200, pkg_preview.text
    pkg_preview_body = pkg_preview.json()

    admission = pkg_preview_body["analysis_product_admission"]
    assert admission["available"] is True, (
        f"admission.available must be True (roster can be empty); "
        f"got {admission['available']!r}"
    )
    assert admission["embedding_enabled"] is True, (
        f"admission.embedding_enabled must be True (flag is ON); "
        f"got {admission['embedding_enabled']!r}"
    )
    assert admission["package_eligible_product_count"] == 0, (
        f"admission.package_eligible_product_count must be 0; "
        f"got {admission['package_eligible_product_count']!r}"
    )
    assert admission["total_package_eligible"] == 0, (
        f"admission.total_package_eligible must be 0; "
        f"got {admission['total_package_eligible']!r}"
    )
    assert admission["products"] == [], (
        f"admission.products must be [] (empty roster); "
        f"got {admission['products']!r}"
    )

    # Step 4: commit with the empty-roster hash → SUCCESS.
    pkg_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_prefix}-pkg-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": pkg_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert pkg_commit.status_code == 200, pkg_commit.text

    # Step 5: load all three committed payloads and assert empty-inventory invariants.
    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) == {
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    }, f"Unexpected package kinds: {set(rows)}"

    canonical_payload = _load_payload(rows[PACKAGE_KIND_CANONICAL_INTERNAL].payload_ref)
    user_payload = _load_payload(rows[PACKAGE_KIND_USER_FACING].payload_ref)
    review_payload = _load_payload(rows[PACKAGE_KIND_REVIEW_FACING].payload_ref)

    for kind, payload in [
        (PACKAGE_KIND_CANONICAL_INTERNAL, canonical_payload),
        (PACKAGE_KIND_USER_FACING, user_payload),
        (PACKAGE_KIND_REVIEW_FACING, review_payload),
    ]:
        assert "analysis_product_inventory" in payload, (
            f"{kind}: analysis_product_inventory must be present when flag is ON"
        )
        inv = payload["analysis_product_inventory"]

        assert inv["package_eligible_product_count"] == 0, (
            f"{kind}: package_eligible_product_count must be 0; "
            f"got {inv['package_eligible_product_count']!r}"
        )
        assert inv.get("total_package_eligible") == 0, (
            f"{kind}: total_package_eligible must be 0; "
            f"got {inv.get('total_package_eligible')!r}"
        )
        assert inv.get("truncated") is False, (
            f"{kind}: truncated must be False; got {inv.get('truncated')!r}"
        )
        assert inv["products"] == [], (
            f"{kind}: inventory products must be [] (empty); "
            f"got {inv['products']!r}"
        )

        # Superseded product id must be absent from the entire serialized inventory.
        inv_text = json.dumps(inv)
        assert sole_product_id not in inv_text, (
            f"{kind}: superseded product id {sole_product_id!r} found in "
            f"serialized analysis_product_inventory"
        )


# ---------------------------------------------------------------------------
# TEST I — staleness-diagnostic product survives package commit with correct
#           provenance and no-body / no-input_state_hash leak invariants
# ---------------------------------------------------------------------------

_STALENESS_DIAGNOSTIC_METHOD_ID = "working_set_staleness_diagnostic"
_STALENESS_DIAGNOSTIC_METHOD_VERSION = DETERMINISTIC_METHODS[_STALENESS_DIAGNOSTIC_METHOD_ID].version


def test_3c_staleness_diagnostic_provenance_survives_package_commit(
    client, tmp_path, monkeypatch
):
    """Rails proof: a working_set_staleness_diagnostic product (product_kind='diagnostic',
    executor_type='deterministic') carries exact generation_method into the committed
    canonical_internal and review_facing payloads.

    Invariants asserted for canonical_internal and review_facing:
      - product present (matched by analysis_product_id).
      - product_kind == "diagnostic".
      - executor_type == "deterministic".
      - generation_method == {"method_id": "working_set_staleness_diagnostic",
                               "method_version": 1}.
      - No "body" key anywhere in the payload (no-body invariant).
      - "input_state_hash" absent from the serialized payload bytes.
    """
    request_prefix = "3c-stale-diag-prov"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    # Build quant-ready session.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    # Create working set and generate the staleness-diagnostic product.
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .first()
        )
        assert snapshot is not None, f"No material snapshot for session {session_id}"

        ws_draft = WorkingSetDraft(
            name="Staleness diagnostic rails test set",
            members=(
                WorkingSetMemberDraft(
                    ref_kind="material_snapshot",
                    ref_id=snapshot.material_snapshot_id,
                ),
            ),
        )
        ws_result = create_working_set(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-ws-create",
            draft=ws_draft,
        )
        db.commit()
        working_set_id = ws_result.working_set.working_set_id

        gen_result = generate_analysis_product(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-gen",
            working_set_id=working_set_id,
            method_id=_STALENESS_DIAGNOSTIC_METHOD_ID,
        )
        db.commit()
        generated_product_id = gen_result.product.analysis_product_id

        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=generated_product_id,
            prefix=f"{request_prefix}-promote",
        )
    finally:
        db.close()

    # Run plan/approve + exec/select + exec/start + result/review via API,
    # then commit the package (reusing _build_session_with_deterministic_eligible_product
    # pattern but inline since we already have session_id + product ready).
    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"{request_prefix}-plan-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"{request_prefix}-plan-approve",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200, approval.text
    approval_body = approval.json()

    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_prefix}-exec-select",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200, selection.text
    selection_body = selection.json()
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_prefix}-exec-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200, start.text
    start_body = start.json()

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"] == "available"

    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_prefix}-result-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Staleness-diagnostic rails proof — provenance traceable.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "generated_narrative",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200, review.text
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"

    _commit_package(
        client,
        request_prefix=request_prefix,
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        preview_body=preview_body,
        start_body=start_body,
        review_body=review_body,
    )

    db = client.layer3_session_factory()
    try:
        rows = _packages_by_kind(db, session_id)
    finally:
        db.close()

    assert set(rows) >= {PACKAGE_KIND_CANONICAL_INTERNAL, PACKAGE_KIND_REVIEW_FACING}, (
        f"Expected at least canonical_internal and review_facing; got {set(rows)}"
    )

    expected_generation_method = {
        "method_id": _STALENESS_DIAGNOSTIC_METHOD_ID,
        "method_version": _STALENESS_DIAGNOSTIC_METHOD_VERSION,
    }

    for kind in (PACKAGE_KIND_CANONICAL_INTERNAL, PACKAGE_KIND_REVIEW_FACING):
        row = rows[kind]
        assert row.payload_ref and Path(row.payload_ref).exists(), (
            f"Payload file missing for kind {kind}"
        )
        payload = _load_payload(row.payload_ref)

        assert "analysis_product_inventory" in payload, (
            f"analysis_product_inventory missing from {kind} payload"
        )

        products = payload["analysis_product_inventory"]["products"]

        matching = [
            p for p in products
            if p.get("analysis_product_id") == generated_product_id
        ]
        assert len(matching) == 1, (
            f"{kind}: expected exactly 1 product with analysis_product_id="
            f"{generated_product_id!r}; found {len(matching)}"
        )
        diag_product = matching[0]

        # product_kind must be "diagnostic" (spec-level proof).
        assert diag_product.get("product_kind") == "diagnostic", (
            f"{kind}: product_kind must be 'diagnostic'; "
            f"got {diag_product.get('product_kind')!r}"
        )

        # CORE PROOF — executor_type.
        assert diag_product.get("executor_type") == "deterministic", (
            f"{kind}: executor_type must be 'deterministic'; "
            f"got {diag_product.get('executor_type')!r}"
        )

        # CORE PROOF — generation_method exact dict.
        assert diag_product.get("generation_method") == expected_generation_method, (
            f"{kind}: generation_method mismatch.\n"
            f"  expected: {expected_generation_method!r}\n"
            f"  got:      {diag_product.get('generation_method')!r}"
        )

        # No-body invariant: "body" key must never appear in package payloads.
        payload_text = json.dumps(payload)
        assert '"body"' not in payload_text, (
            f"'body' key found in {kind} payload — body must never appear in package payloads"
        )

        # No-leak: "input_state_hash" must never appear in serialized payload bytes.
        payload_bytes = Path(row.payload_ref).read_bytes()
        assert b"input_state_hash" not in payload_bytes, (
            f"'input_state_hash' found in {kind} serialized payload bytes — "
            f"provenance internals must not leak into package payloads"
        )


# ---------------------------------------------------------------------------
# TEST J — R6: supersession of a GENERATED (deterministic) product; closes
#           the only rails evidence gap (no prior test superseded a deterministic
#           product before this tranche)
# ---------------------------------------------------------------------------


def test_3c_generated_product_supersession_stale_basis(client, tmp_path, monkeypatch):
    """R6 minimal proof: a deterministic product promoted to package_eligible can be
    superseded (reason: stale_basis); lifecycle_status becomes 'superseded' and the
    product drops out of the package_eligible roster query.
    """
    request_prefix = "3c-gen-supersede"

    monkeypatch.setattr(
        layer3_workbench.settings,
        "layer3_analysis_product_package_inventory_enabled",
        True,
    )

    # Build session and generate a deterministic product, promote to package_eligible.
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_managed_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .first()
        )
        assert snapshot is not None
        ws_result = create_working_set(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-ws",
            draft=WorkingSetDraft(
                name="R6 supersession test set",
                members=(
                    WorkingSetMemberDraft(
                        ref_kind="material_snapshot",
                        ref_id=snapshot.material_snapshot_id,
                    ),
                ),
            ),
        )
        db.commit()
        gen_result = generate_analysis_product(
            db,
            session_id=session_id,
            client_request_id=f"{request_prefix}-gen",
            working_set_id=ws_result.working_set.working_set_id,
            method_id=_DETERMINISTIC_METHOD_ID,
        )
        db.commit()
        generated_id = gen_result.product.analysis_product_id
        _promote_to_package_eligible(
            db,
            session_id=session_id,
            product_id=generated_id,
            prefix=f"{request_prefix}-promote",
        )
    finally:
        db.close()

    # Confirm the product is in the package_eligible roster before supersession.
    db = client.layer3_session_factory()
    try:
        before = (
            db.query(L3AnalysisProduct)
            .filter(
                L3AnalysisProduct.session_id == session_id,
                L3AnalysisProduct.lifecycle_status == "package_eligible",
            )
            .all()
        )
        assert any(r.analysis_product_id == generated_id for r in before), (
            f"Generated product {generated_id!r} not in package_eligible roster before supersession"
        )
    finally:
        db.close()

    # Supersede the generated product (stale_basis; no successor required).
    supersede_resp = client.post(
        f"/api/v1/layer3/analysis-product/{generated_id}/transition",
        json={
            "session_id": session_id,
            "client_request_id": f"{request_prefix}-supersede",
            "decision_intent": "supersede",
            "decision_reason_code": "stale_basis",
            "decision_notes": "Generated product superseded due to stale basis — R6 proof.",
        },
    )
    assert supersede_resp.status_code == 201, supersede_resp.text
    assert supersede_resp.json()["lifecycle_status"] == "superseded", (
        f"Expected lifecycle_status 'superseded'; "
        f"got {supersede_resp.json()['lifecycle_status']!r}"
    )

    # Product must be absent from the package_eligible roster after supersession.
    db = client.layer3_session_factory()
    try:
        after = (
            db.query(L3AnalysisProduct)
            .filter(
                L3AnalysisProduct.session_id == session_id,
                L3AnalysisProduct.lifecycle_status == "package_eligible",
            )
            .all()
        )
        assert not any(r.analysis_product_id == generated_id for r in after), (
            f"Superseded generated product {generated_id!r} still appears in "
            f"package_eligible roster after supersession"
        )
    finally:
        db.close()
