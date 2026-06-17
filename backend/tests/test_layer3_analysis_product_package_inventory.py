"""Tests for the analysis_product_package_inventory extras builder (PR1, Sublayer 3C).

Uses an in-memory SQLite database matching the StaticPool pattern from the
existing layer3 service test suite.  No schema migrations; DB_INIT_MODE=none.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    L3AnalysisPlan,
    L3AnalysisProduct,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3AnalysisGroup,
    L3MaterialSnapshot,
    L3PassRun,
    L3Session,
)
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    create_analysis_product_draft,
)
from app.services.layer3_analysis_product_promotion import (
    AnalysisProductTransitionRequest,
    transition_analysis_product,
)
from app.services import layer3_workbench
from app.services.layer3_workbench import (
    _analysis_product_admission_hash,
    _analysis_product_package_payload_extras,
    _build_analysis_product_admission_preview,
    _load_excluded_analysis_products,
    _load_package_eligible_analysis_products,
    _merge_analysis_product_inventory_extras,
    _ANALYSIS_PRODUCT_EXCLUSION_REASON_BY_STATUS,
    _ANALYSIS_PRODUCT_EXCLUSION_REASON_FALLBACK,
    _ANALYSIS_PRODUCT_INVENTORY_MAX,
    _EVIDENCE_REFS_PER_PRODUCT_MAX,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SESSION_ID = "session-inv-test"
SESSION_ID_OTHER = "session-inv-other"


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
        engine.dispose()


@pytest.fixture()
def seeded_db(db_session):
    """Seed two sessions each with a material_snapshot + pass_run."""
    from datetime import datetime, timezone

    def _seed_session(sid: str, suffix: str):
        session_row = L3Session(
            session_id=sid,
            selection_manifest_id=f"manifest-{suffix}",
            status="active_execution",
            operator_context_json={},
            summary_json={},
        )
        snapshot = L3MaterialSnapshot(
            material_snapshot_id=f"snapshot-{suffix}",
            session_id=sid,
            descriptor_id=f"descriptor-{suffix}",
            source_plane="runtime",
            source_shape="dataset_version",
            payload_ref=f"payload://{suffix}",
            payload_hash=f"hash-{suffix}",
            source_identity_json={"dataset_version_id": f"dv-{suffix}"},
            source_provenance_json={},
            load_summary_json={},
        )
        analysis_unit = L3AnalysisUnit(
            analysis_unit_id=f"unit-{suffix}",
            session_id=sid,
            unit_kind="material_snapshot",
            analysis_modality="quantitative",
            member_snapshot_ids_json=[f"snapshot-{suffix}"],
            member_ranges_json=[],
            must_remain_intact=True,
            typing_record_ids_json=[],
            unit_hash=f"unit-hash-{suffix}",
            summary_json={},
        )
        analysis_group = L3AnalysisGroup(
            analysis_group_id=f"group-{suffix}",
            session_id=sid,
            analysis_modality="quantitative",
            typing_basis_json={},
            analysis_unit_ids_json=[f"unit-{suffix}"],
            status="formed",
        )
        analysis_set = L3AnalysisSet(
            analysis_set_id=f"set-{suffix}",
            session_id=sid,
            analysis_group_ids_json=[f"group-{suffix}"],
            analysis_unit_ids_json=[f"unit-{suffix}"],
            set_type="associated_cohort",
            formation_basis_json={},
        )
        analysis_plan = L3AnalysisPlan(
            analysis_plan_id=f"plan-{suffix}",
            session_id=sid,
            analysis_set_ids_json=[f"set-{suffix}"],
            status="approved",
            approved_by_operator=True,
            approved_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc),
            plan_json={},
        )
        pass_run = L3PassRun(
            pass_run_id=f"pass-{suffix}",
            session_id=sid,
            analysis_plan_id=f"plan-{suffix}",
            analysis_set_id=f"set-{suffix}",
            pass_type="associated_cohort",
            engine_family="wrapped_quantitative_analysis",
            status="completed",
            input_payload_ref=f"payload://input-{suffix}",
            output_payload_ref=f"payload://output-{suffix}",
            summary_json={},
        )
        db_session.add_all(
            [session_row, snapshot, analysis_unit, analysis_group, analysis_set, analysis_plan, pass_run]
        )

    _seed_session(SESSION_ID, "inv")
    _seed_session(SESSION_ID_OTHER, "inv-other")
    db_session.commit()
    return db_session


def _make_grounded_product(db, *, session_id: str = SESSION_ID, client_request_id: str) -> L3AnalysisProduct:
    """Author a grounded finding product in the given session."""
    snapshot_id = "snapshot-inv" if session_id == SESSION_ID else "snapshot-inv-other"
    draft = AnalysisProductDraft(
        product_kind="finding",
        title=f"Grounded finding [{client_request_id}]",
        body="Body text — should never appear in package payload.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id=snapshot_id,
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
    """Walk a product draft -> proposed -> validated -> accepted -> package_eligible."""
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


# ---------------------------------------------------------------------------
# (a) Flag OFF => gate returns input byte-identical; Flag ON => section added
# ---------------------------------------------------------------------------


def test_flag_off_gate_returns_input_unchanged(seeded_db) -> None:
    """When the flag is OFF, _merge_analysis_product_inventory_extras must return
    the input dict byte-identical — no analysis_product_inventory key added,
    pre-existing keys preserved."""
    from app.services.layer3_package_entry import (
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    )

    db = seeded_db
    product = _make_grounded_product(db, client_request_id="inv-flag-off")
    _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="fo")

    baseline = {PACKAGE_KIND_USER_FACING: {"existing_key": 1}}

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        # Confirm the patch is live inside the helper
        assert layer3_workbench.settings.layer3_analysis_product_package_inventory_enabled is False
        result = _merge_analysis_product_inventory_extras(db, SESSION_ID, baseline)

    # Returned dict is the same object (byte-identical pass-through)
    assert result is baseline
    # No analysis_product_inventory key in any kind
    for kind_dict in result.values():
        assert "analysis_product_inventory" not in kind_dict
    # Pre-existing key survived untouched
    assert result[PACKAGE_KIND_USER_FACING]["existing_key"] == 1


def test_flag_on_gate_merges_section_additively(seeded_db) -> None:
    """When the flag is ON, _merge_analysis_product_inventory_extras must add
    analysis_product_inventory to all three kinds while preserving pre-existing keys."""
    from app.services.layer3_package_entry import (
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    )

    db = seeded_db
    product = _make_grounded_product(db, client_request_id="inv-flag-on")
    _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="fon")

    baseline = {PACKAGE_KIND_USER_FACING: {"existing_key": 99}}

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", True):
        assert layer3_workbench.settings.layer3_analysis_product_package_inventory_enabled is True
        result = _merge_analysis_product_inventory_extras(db, SESSION_ID, baseline)

    # All three kinds present (canonical and review_facing added from None)
    assert PACKAGE_KIND_CANONICAL_INTERNAL in result
    assert PACKAGE_KIND_USER_FACING in result
    assert PACKAGE_KIND_REVIEW_FACING in result

    # analysis_product_inventory section present in all three kinds
    assert "analysis_product_inventory" in result[PACKAGE_KIND_CANONICAL_INTERNAL]
    assert "analysis_product_inventory" in result[PACKAGE_KIND_USER_FACING]
    assert "analysis_product_inventory" in result[PACKAGE_KIND_REVIEW_FACING]

    # Pre-existing key on user_facing survived (additive, non-clobbering)
    assert result[PACKAGE_KIND_USER_FACING]["existing_key"] == 99


# ---------------------------------------------------------------------------
# (b) Flag ON + one package_eligible product => correct per-kind sections
# ---------------------------------------------------------------------------


def test_flag_on_one_product_full_and_summary(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="inv-b-001")
    _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="b1")

    extras = _analysis_product_package_payload_extras(db, SESSION_ID)

    from app.services.layer3_package_entry import (
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    )

    # All three kinds present.
    assert PACKAGE_KIND_CANONICAL_INTERNAL in extras
    assert PACKAGE_KIND_USER_FACING in extras
    assert PACKAGE_KIND_REVIEW_FACING in extras

    canonical = extras[PACKAGE_KIND_CANONICAL_INTERNAL]["analysis_product_inventory"]
    user_facing = extras[PACKAGE_KIND_USER_FACING]["analysis_product_inventory"]
    review = extras[PACKAGE_KIND_REVIEW_FACING]["analysis_product_inventory"]

    # Schema id correct.
    assert canonical["schema_id"] == "layer3.analysis_product_package_inventory.v1"
    assert canonical["analysis_product_inventory_enabled"] is True
    assert canonical["package_eligible_product_count"] == 1
    assert canonical["total_package_eligible"] == 1
    assert canonical["truncated"] is False
    assert canonical["max_products"] == _ANALYSIS_PRODUCT_INVENTORY_MAX

    # Canonical / review: full inventory with title + evidence_refs + provenance.
    assert len(canonical["products"]) == 1
    c_prod = canonical["products"][0]
    assert c_prod["analysis_product_id"] == product.analysis_product_id
    assert c_prod["product_kind"] == "finding"
    assert "title" in c_prod
    assert c_prod["lifecycle_status"] == "package_eligible"
    assert "basis_hash" in c_prod
    assert "evidence_refs" in c_prod
    assert len(c_prod["evidence_refs"]) == 1
    assert c_prod["evidence_refs"][0]["ref_kind"] == "material_snapshot"
    assert "ref_id" in c_prod["evidence_refs"][0]
    assert "evidence_role" in c_prod["evidence_refs"][0]
    assert "evidence_refs_truncated" in c_prod
    assert c_prod["evidence_refs_truncated"] is False
    assert "by_evidence_role" in c_prod
    assert "latest_review_decision" in c_prod

    # Review_facing identical to canonical for full inventory.
    assert review["products"][0]["analysis_product_id"] == product.analysis_product_id
    assert "title" in review["products"][0]

    # User_facing: summary only — product_kind + by_evidence_role, NO title, NO ref ids.
    assert len(user_facing["products"]) == 1
    u_prod = user_facing["products"][0]
    assert u_prod["analysis_product_id"] == product.analysis_product_id
    assert u_prod["product_kind"] == "finding"
    assert "by_evidence_role" in u_prod
    assert "title" not in u_prod
    assert "evidence_refs" not in u_prod
    assert "latest_review_decision" not in u_prod


# ---------------------------------------------------------------------------
# (b2) evidence_refs truncation: products with >MAX refs are capped + flagged
# ---------------------------------------------------------------------------


def test_evidence_refs_truncation(seeded_db) -> None:
    """A product whose evidence_refs list exceeds _EVIDENCE_REFS_PER_PRODUCT_MAX
    must have evidence_refs capped at the bound and evidence_refs_truncated=True
    in canonical_internal.  Uses a monkeypatched bound of 3 to avoid seeding
    hundreds of DB rows."""
    from app.services.layer3_package_entry import PACKAGE_KIND_CANONICAL_INTERNAL

    db = seeded_db
    product = _make_grounded_product(db, client_request_id="inv-evref-trunc")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="evt"
    )

    # Build a fake serialized roster that has more refs than the patched bound.
    small_bound = 3
    many_refs = [
        {"ref_kind": "material_snapshot", "ref_id": f"snap-{i}", "evidence_role": "observation"}
        for i in range(small_bound + 2)  # 5 refs > bound of 3
    ]
    fake_products = [
        {
            "analysis_product_id": product.analysis_product_id,
            "product_kind": "finding",
            "title": "Truncation test product",
            "lifecycle_status": "package_eligible",
            "basis_hash": "hash-abc",
            "evidence_refs": many_refs,
            "by_evidence_role": {"observation": len(many_refs)},
            "latest_review_decision": None,
        }
    ]

    with patch("app.services.layer3_workbench._session_analyst_products", return_value=fake_products):
        with patch.object(layer3_workbench, "_EVIDENCE_REFS_PER_PRODUCT_MAX", small_bound):
            extras = _analysis_product_package_payload_extras(db, SESSION_ID)

    canonical = extras[PACKAGE_KIND_CANONICAL_INTERNAL]["analysis_product_inventory"]
    c_prod = canonical["products"][0]
    assert len(c_prod["evidence_refs"]) == small_bound
    assert c_prod["evidence_refs_truncated"] is True


# ---------------------------------------------------------------------------
# No-body invariant: 'body' must never appear in any kind's section
# ---------------------------------------------------------------------------


def test_no_body_key_in_any_kind(seeded_db) -> None:
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="inv-body-001")
    _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="nb1")

    extras = _analysis_product_package_payload_extras(db, SESSION_ID)
    serialized = json.dumps(extras)
    assert '"body"' not in serialized, "The 'body' key must never appear in any package inventory section"
    # Also assert the body value text is not present.
    assert "Body text" not in serialized


# ---------------------------------------------------------------------------
# (c) Only package_eligible products included; draft/accepted/rejected excluded
# ---------------------------------------------------------------------------


def test_only_package_eligible_included(seeded_db) -> None:
    db = seeded_db
    # draft product — stays in draft
    _make_grounded_product(db, client_request_id="inv-c-draft")

    # proposed product
    proposed_product = _make_grounded_product(db, client_request_id="inv-c-proposed")
    transition_analysis_product(
        db,
        session_id=SESSION_ID,
        analysis_product_id=proposed_product.analysis_product_id,
        client_request_id="inv-c-proposed-s1",
        request=AnalysisProductTransitionRequest(decision_intent="promote", decision_reason_code="proposed_ready"),
    )
    db.commit()

    # accepted product
    accepted_product = _make_grounded_product(db, client_request_id="inv-c-accepted")
    for idx, (step_intent, step_code) in enumerate([("promote", "proposed_ready"), ("promote", "validation_passed"), ("accept", "grounded_accept")]):
        transition_analysis_product(
            db,
            session_id=SESSION_ID,
            analysis_product_id=accepted_product.analysis_product_id,
            client_request_id=f"inv-c-acc-{idx}",
            request=AnalysisProductTransitionRequest(decision_intent=step_intent, decision_reason_code=step_code),
        )
        db.commit()

    # package_eligible product
    eligible_product = _make_grounded_product(db, client_request_id="inv-c-eligible")
    _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=eligible_product.analysis_product_id, prefix="ce")

    roster, meta = _load_package_eligible_analysis_products(db, SESSION_ID)
    eligible_ids = {p["analysis_product_id"] for p in roster}
    assert eligible_product.analysis_product_id in eligible_ids
    assert proposed_product.analysis_product_id not in eligible_ids
    assert accepted_product.analysis_product_id not in eligible_ids
    assert meta["total"] == 1
    assert meta["included"] == 1


# ---------------------------------------------------------------------------
# (d) Cross-session products excluded
# ---------------------------------------------------------------------------


def test_cross_session_products_excluded(seeded_db) -> None:
    db = seeded_db
    # product in main session
    product_main = _make_grounded_product(db, session_id=SESSION_ID, client_request_id="inv-d-main")
    _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=product_main.analysis_product_id, prefix="dm")

    # product in other session
    product_other = _make_grounded_product(db, session_id=SESSION_ID_OTHER, client_request_id="inv-d-other")
    _promote_to_package_eligible(db, session_id=SESSION_ID_OTHER, product_id=product_other.analysis_product_id, prefix="do")

    roster_main, _ = _load_package_eligible_analysis_products(db, SESSION_ID)
    ids_main = {p["analysis_product_id"] for p in roster_main}
    assert product_main.analysis_product_id in ids_main
    assert product_other.analysis_product_id not in ids_main

    roster_other, _ = _load_package_eligible_analysis_products(db, SESSION_ID_OTHER)
    ids_other = {p["analysis_product_id"] for p in roster_other}
    assert product_other.analysis_product_id in ids_other
    assert product_main.analysis_product_id not in ids_other


# ---------------------------------------------------------------------------
# (e) >100 products => truncated flag True, roster length == 100
# ---------------------------------------------------------------------------


def test_truncation_at_max(seeded_db) -> None:
    db = seeded_db
    # Create MAX+5 products and promote them all to package_eligible.
    count = _ANALYSIS_PRODUCT_INVENTORY_MAX + 5
    for i in range(count):
        p = _make_grounded_product(db, client_request_id=f"inv-e-{i:04d}")
        _promote_to_package_eligible(db, session_id=SESSION_ID, product_id=p.analysis_product_id, prefix=f"e{i}")

    roster, meta = _load_package_eligible_analysis_products(db, SESSION_ID)
    assert meta["total"] == count
    assert meta["truncated"] is True
    assert meta["included"] == _ANALYSIS_PRODUCT_INVENTORY_MAX
    assert len(roster) == _ANALYSIS_PRODUCT_INVENTORY_MAX


def test_roster_load_queries_only_eligible_capped_rows(seeded_db) -> None:
    db = seeded_db
    with patch(
        "app.services.layer3_workbench._count_session_analyst_products",
        return_value=_ANALYSIS_PRODUCT_INVENTORY_MAX + 5,
    ) as count_products:
        with patch(
            "app.services.layer3_workbench._session_analyst_products",
            return_value=[],
        ) as load_products:
            roster, meta = _load_package_eligible_analysis_products(db, SESSION_ID)

    count_products.assert_called_once_with(
        db,
        session_id=SESSION_ID,
        lifecycle_status="package_eligible",
    )
    load_products.assert_called_once_with(
        db,
        session_id=SESSION_ID,
        lifecycle_status="package_eligible",
        limit=_ANALYSIS_PRODUCT_INVENTORY_MAX,
    )
    assert roster == []
    assert meta == {
        "truncated": True,
        "total": _ANALYSIS_PRODUCT_INVENTORY_MAX + 5,
        "included": 0,
    }


# ---------------------------------------------------------------------------
# (f) Evidence ref with unknown ref_kind => fail-closed (raises ValueError)
# ---------------------------------------------------------------------------


def test_unknown_ref_kind_fails_closed(seeded_db) -> None:
    db = seeded_db

    # Mock session_analyst_products to return a product with an invalid ref_kind.
    fake_products = [
        {
            "analysis_product_id": "ap-bad-ref",
            "product_kind": "finding",
            "title": "Bad ref product",
            "lifecycle_status": "package_eligible",
            "basis_hash": "abc123",
            "evidence_refs": [
                {
                    "ref_kind": "INVALID_REF_KIND_NOT_IN_ENUM",
                    "ref_id": "some-id",
                    "evidence_role": "observation",
                }
            ],
            "by_evidence_role": {"observation": 1},
            "latest_review_decision": None,
        }
    ]

    with patch("app.services.layer3_workbench._session_analyst_products", return_value=fake_products):
        with pytest.raises(ValueError, match="unknown ref_kind"):
            _load_package_eligible_analysis_products(db, SESSION_ID)


# ---------------------------------------------------------------------------
# TEXT ANCHOR: admission_preview_tests
# _build_analysis_product_admission_preview — flag OFF / flag ON / error path
# ---------------------------------------------------------------------------


def test_admission_preview_flag_off_one_product(seeded_db) -> None:
    """Flag OFF: embedding_enabled is False, roster is still visible, product
    is bounded (no title/evidence_refs/body in admission products)."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="adm-off-001")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="adm-off"
    )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["schema_id"] == "layer3.analysis_product_admission_preview.v1"
    assert result["embedding_enabled"] is False
    assert result["available"] is True
    assert result["package_eligible_product_count"] == 1
    assert result["total_package_eligible"] == 1
    assert result["truncated"] is False
    assert len(result["products"]) == 1

    p = result["products"][0]
    assert p["product_kind"] == "finding"
    assert p["lifecycle_status"] == "package_eligible"
    assert isinstance(p["evidence_count"], int)
    assert p["evidence_count"] == 1
    # Bounded: no title, no evidence_refs, no body
    assert "title" not in p
    assert "evidence_refs" not in p
    assert "body" not in p


def test_admission_preview_flag_on_one_product(seeded_db) -> None:
    """Flag ON: embedding_enabled is True, same roster shape."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="adm-on-001")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="adm-on"
    )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", True):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["schema_id"] == "layer3.analysis_product_admission_preview.v1"
    assert result["embedding_enabled"] is True
    assert result["available"] is True
    assert result["package_eligible_product_count"] == 1
    assert result["total_package_eligible"] == 1
    assert result["truncated"] is False
    assert len(result["products"]) == 1

    p = result["products"][0]
    assert p["product_kind"] == "finding"
    assert p["lifecycle_status"] == "package_eligible"
    assert "basis_hash" in p
    # executor_type is a bounded enum — present in admission preview.
    assert "executor_type" in p
    assert p["executor_type"] == "human"
    # Bounded: no title, no evidence_refs, no body
    assert "title" not in p
    assert "evidence_refs" not in p
    assert "body" not in p


def test_admission_preview_no_products(seeded_db) -> None:
    """Session with no package_eligible products: count 0, products == []."""
    db = seeded_db

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["available"] is True
    assert result["package_eligible_product_count"] == 0
    assert result["products"] == []
    assert result["truncated"] is False


def test_admission_preview_error_path(seeded_db) -> None:
    """When _load_package_eligible_analysis_products raises, available=False and no
    exception propagates (informational-only safety contract)."""
    db = seeded_db

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated roster load failure")

    with patch("app.services.layer3_workbench._load_package_eligible_analysis_products", side_effect=_raise):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["schema_id"] == "layer3.analysis_product_admission_preview.v1"
    assert result["available"] is False
    assert result["package_eligible_product_count"] is None
    assert result["products"] == []
    assert result["note"] == "admission_preview_unavailable"


def test_admission_preview_bounded_keys_only(seeded_db) -> None:
    """Assert that the per-product dict in admission preview contains exactly
    the four bounded keys and nothing else."""
    db = seeded_db
    product = _make_grounded_product(db, client_request_id="adm-keys-001")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="adm-keys"
    )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert len(result["products"]) == 1
    p = result["products"][0]
    allowed_keys = {"product_kind", "lifecycle_status", "evidence_count", "basis_hash", "executor_type"}
    assert set(p.keys()) == allowed_keys, (
        f"Admission product must have exactly {allowed_keys}, got {set(p.keys())}"
    )


def test_admission_hash_is_flag_gated_and_roster_sensitive(seeded_db) -> None:
    db = seeded_db
    first_product = _make_grounded_product(db, client_request_id="adm-hash-001")
    _promote_to_package_eligible(
        db,
        session_id=SESSION_ID,
        product_id=first_product.analysis_product_id,
        prefix="adm-hash-one",
    )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        admission_one_flag_off = _build_analysis_product_admission_preview(db, SESSION_ID)
        assert _analysis_product_admission_hash(admission_one_flag_off) is None

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", True):
        admission_one = _build_analysis_product_admission_preview(db, SESSION_ID)
        hash_one = _analysis_product_admission_hash(admission_one)

    second_product = _make_grounded_product(db, client_request_id="adm-hash-002")
    _promote_to_package_eligible(
        db,
        session_id=SESSION_ID,
        product_id=second_product.analysis_product_id,
        prefix="adm-hash-two",
    )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", True):
        admission_two = _build_analysis_product_admission_preview(db, SESSION_ID)
        hash_two = _analysis_product_admission_hash(admission_two)

    assert admission_one["package_eligible_product_count"] == 1
    assert admission_two["package_eligible_product_count"] == 2
    assert hash_one is not None
    assert hash_two is not None
    assert hash_two != hash_one


# ---------------------------------------------------------------------------
# TEXT ANCHOR: admission_preview_exclusion_tests
# _build_analysis_product_admission_preview — excluded_products section
# ---------------------------------------------------------------------------


def _insert_product_direct(db, *, session_id: str, lifecycle_status: str, client_request_id: str) -> L3AnalysisProduct:
    """Insert an L3AnalysisProduct row directly with the given lifecycle_status,
    bypassing the authoring workflow so we can place products in any lifecycle state."""
    import hashlib

    row = L3AnalysisProduct(
        session_id=session_id,
        product_kind="finding",
        executor_type="human",
        lifecycle_status=lifecycle_status,
        title=f"Direct insert [{client_request_id}]",
        body="body text",
        is_non_evidentiary=False,
        basis_hash=hashlib.sha256(client_request_id.encode()).hexdigest()[:16],
        spec_hash=hashlib.sha256(f"spec-{client_request_id}".encode()).hexdigest()[:16],
        client_request_id=client_request_id,
        authoring_provenance_json={},
        summary_json={},
    )
    db.add(row)
    db.commit()
    return row


def test_admission_preview_excluded_products_present_with_reasons(seeded_db) -> None:
    """Mix of eligible and non-eligible products: excluded_products lists the
    non-eligible ones with correct exclusion_reason; the package_eligible product
    appears only in products, not in excluded_products."""
    db = seeded_db

    # One package_eligible product (via normal promotion path)
    eligible = _make_grounded_product(db, client_request_id="excl-mix-eligible")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=eligible.analysis_product_id, prefix="excl-mix-e"
    )

    # Three non-eligible products inserted directly
    _insert_product_direct(db, session_id=SESSION_ID, lifecycle_status="draft", client_request_id="excl-mix-draft")
    _insert_product_direct(db, session_id=SESSION_ID, lifecycle_status="rejected", client_request_id="excl-mix-rejected")
    _insert_product_direct(db, session_id=SESSION_ID, lifecycle_status="accepted", client_request_id="excl-mix-accepted")

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["available"] is True
    assert result["package_eligible_product_count"] == 1
    assert len(result["products"]) == 1
    assert result["products"][0]["lifecycle_status"] == "package_eligible"

    excluded = result["excluded_products"]
    assert isinstance(excluded, list)
    assert len(excluded) == 3

    by_status = {e["lifecycle_status"]: e for e in excluded}
    assert set(by_status.keys()) == {"draft", "rejected", "accepted"}
    assert by_status["draft"]["exclusion_reason"] == "not_yet_promoted"
    assert by_status["rejected"]["exclusion_reason"] == "rejected"
    assert by_status["accepted"]["exclusion_reason"] == "not_marked_package_eligible"

    # The eligible product must NOT appear in excluded_products
    eligible_ids_in_excluded = [e for e in excluded if e.get("lifecycle_status") == "package_eligible"]
    assert eligible_ids_in_excluded == []

    assert result["total_excluded"] == 3
    assert result["excluded_product_count"] == 3
    assert result["excluded_truncated"] is False


def test_admission_preview_excluded_bounded_keys_only(seeded_db) -> None:
    """Every excluded_products entry has exactly the 6 bounded keys."""
    db = seeded_db

    _insert_product_direct(db, session_id=SESSION_ID, lifecycle_status="draft", client_request_id="excl-keys-draft")
    _insert_product_direct(db, session_id=SESSION_ID, lifecycle_status="superseded", client_request_id="excl-keys-sup")

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["available"] is True
    excluded = result["excluded_products"]
    assert len(excluded) == 2

    expected_keys = {"product_kind", "lifecycle_status", "evidence_count", "basis_hash", "executor_type", "exclusion_reason"}
    for entry in excluded:
        assert set(entry.keys()) == expected_keys, (
            f"Excluded entry must have exactly {expected_keys}, got {set(entry.keys())}"
        )


def test_admission_preview_no_excluded_when_all_eligible(seeded_db) -> None:
    """A session whose only product is package_eligible: excluded_products is empty."""
    db = seeded_db

    product = _make_grounded_product(db, client_request_id="excl-none-001")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="excl-none"
    )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["available"] is True
    assert result["excluded_products"] == []
    assert result["total_excluded"] == 0
    assert result["excluded_product_count"] == 0
    assert result["excluded_truncated"] is False


def test_admission_preview_excluded_error_path_defaults(seeded_db) -> None:
    """If _load_excluded_analysis_products raises, the preview still returns
    available=True with the eligible roster intact and excluded fields defaulted."""
    db = seeded_db

    product = _make_grounded_product(db, client_request_id="excl-err-001")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=product.analysis_product_id, prefix="excl-err"
    )
    _insert_product_direct(db, session_id=SESSION_ID, lifecycle_status="draft", client_request_id="excl-err-draft")

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated excluded loader failure")

    with patch("app.services.layer3_workbench._load_excluded_analysis_products", side_effect=_raise):
        with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
            result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["available"] is True
    # Eligible roster unaffected
    assert result["package_eligible_product_count"] == 1
    assert len(result["products"]) == 1
    assert result["products"][0]["lifecycle_status"] == "package_eligible"
    # Excluded fields defaulted to safe values
    assert result["excluded_products"] == []
    assert result["excluded_product_count"] is None
    assert result["total_excluded"] is None
    assert result["excluded_truncated"] is None


def test_admission_preview_excluded_reason_for_every_non_eligible_status(seeded_db) -> None:
    """Each non-package_eligible lifecycle status maps to its declared exclusion_reason."""
    db = seeded_db

    expected = {
        "draft": "not_yet_promoted",
        "proposed": "pending_validation",
        "validated": "pending_acceptance",
        "accepted": "not_marked_package_eligible",
        "rejected": "rejected",
        "superseded": "superseded",
        "packaged": "already_packaged",
    }
    for status in expected:
        _insert_product_direct(
            db, session_id=SESSION_ID, lifecycle_status=status, client_request_id=f"excl-reason-{status}"
        )

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    by_status = {e["lifecycle_status"]: e["exclusion_reason"] for e in result["excluded_products"]}
    assert by_status == expected
    assert result["total_excluded"] == len(expected)
    assert result["excluded_truncated"] is False


def test_admission_preview_excluded_truncates_beyond_cap(seeded_db) -> None:
    """More than _ANALYSIS_PRODUCT_INVENTORY_MAX excluded products: the sample is
    capped at MAX, total_excluded reflects the true count, and excluded_truncated
    is True.  Eligible products never starve the excluded sample (DB-side filter)."""
    db = seeded_db

    cap = layer3_workbench._ANALYSIS_PRODUCT_INVENTORY_MAX
    over = cap + 5

    # One eligible product to prove it does not consume excluded-sample slots.
    eligible = _make_grounded_product(db, client_request_id="excl-cap-eligible")
    _promote_to_package_eligible(
        db, session_id=SESSION_ID, product_id=eligible.analysis_product_id, prefix="excl-cap-e"
    )

    rows = [
        L3AnalysisProduct(
            session_id=SESSION_ID,
            product_kind="finding",
            executor_type="human",
            lifecycle_status="draft",
            title=f"Bulk excluded {i}",
            body="body text",
            is_non_evidentiary=False,
            basis_hash=f"basis-cap-{i:04d}",
            spec_hash=f"spec-cap-{i:04d}",
            client_request_id=f"excl-cap-{i:04d}",
            authoring_provenance_json={},
            summary_json={},
        )
        for i in range(over)
    ]
    db.add_all(rows)
    db.commit()

    with patch.object(layer3_workbench.settings, "layer3_analysis_product_package_inventory_enabled", False):
        result = _build_analysis_product_admission_preview(db, SESSION_ID)

    assert result["total_excluded"] == over
    assert result["excluded_product_count"] == cap
    assert len(result["excluded_products"]) == cap
    assert result["excluded_truncated"] is True
    # Eligible product still surfaces in the included roster, unaffected by excluded volume.
    assert result["package_eligible_product_count"] == 1
    # Excluded entries are all the draft inserts, never the eligible product.
    assert all(e["lifecycle_status"] == "draft" for e in result["excluded_products"])


# ---------------------------------------------------------------------------
# TEXT ANCHOR: serializer_generation_method_tests
# Unit tests for serialize_analysis_product generation_method field
# (bounded provenance completeness — deterministic-only).
# ---------------------------------------------------------------------------


def test_serialize_analysis_product_deterministic_generation_method() -> None:
    """A deterministic product with authoring_provenance_json containing
    method_id + method_version must surface generation_method with only
    those two keys.  Other provenance fields (param_hash, input_basis_hash,
    result_summary, validation) must NOT appear."""
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    product = SimpleNamespace(
        analysis_product_id="ap-det-001",
        product_kind="metric",
        executor_type="deterministic",
        lifecycle_status="package_eligible",
        title="Deterministic metric",
        is_non_evidentiary=False,
        basis_hash="bh-det",
        spec_hash="sh-det",
        created_at=None,
        authoring_provenance_json={
            "method_id": "working_set_composition_summary",
            "method_version": 2,
            "input_basis_hash": "ibh-secret",
            "param_hash": "ph-secret",
            "result_summary": {"member_count": 3},
            "validation": "deterministic_recomputed_match",
        },
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    assert result["executor_type"] == "deterministic"
    gm = result["generation_method"]
    assert gm is not None
    assert gm == {"method_id": "working_set_composition_summary", "method_version": 2}
    # Only the two bounded keys — no leakage of param_hash, input_basis_hash, etc.
    assert set(gm.keys()) == {"method_id", "method_version"}
    assert "param_hash" not in gm
    assert "input_basis_hash" not in gm
    assert "result_summary" not in gm
    assert "validation" not in gm


def test_serialize_analysis_product_human_generation_method_is_none() -> None:
    """A human-authored product must have generation_method == None regardless
    of what authoring_provenance_json contains."""
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    product = SimpleNamespace(
        analysis_product_id="ap-human-001",
        product_kind="finding",
        executor_type="human",
        lifecycle_status="package_eligible",
        title="Human finding",
        is_non_evidentiary=False,
        basis_hash="bh-human",
        spec_hash="sh-human",
        created_at=None,
        authoring_provenance_json={"operator_note": "manually authored"},
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    assert result["executor_type"] == "human"
    assert result["generation_method"] is None


def test_serialize_analysis_product_deterministic_missing_provenance_fields() -> None:
    """A deterministic product whose authoring_provenance_json lacks method_id
    or method_version must still return generation_method with None values for
    the missing keys — no KeyError."""
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    product = SimpleNamespace(
        analysis_product_id="ap-det-partial",
        product_kind="summary",
        executor_type="deterministic",
        lifecycle_status="draft",
        title="Partial provenance product",
        is_non_evidentiary=False,
        basis_hash="bh-partial",
        spec_hash="sh-partial",
        created_at=None,
        authoring_provenance_json={"method_id": "some_method"},  # method_version absent
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    gm = result["generation_method"]
    assert gm is not None
    assert gm["method_id"] == "some_method"
    assert gm["method_version"] is None


def test_serialize_analysis_product_deterministic_non_dict_provenance() -> None:
    """A deterministic product whose authoring_provenance_json is not a dict
    (e.g. empty default {}) still satisfies isinstance check — empty dict is
    falsy for .get() but generation_method dict is still returned with None values."""
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    product = SimpleNamespace(
        analysis_product_id="ap-det-empty",
        product_kind="summary",
        executor_type="deterministic",
        lifecycle_status="draft",
        title="Empty provenance product",
        is_non_evidentiary=False,
        basis_hash="bh-empty",
        spec_hash="sh-empty",
        created_at=None,
        authoring_provenance_json={},
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    # {} is a dict so generation_method dict is returned, both values are None.
    gm = result["generation_method"]
    assert gm is not None
    assert gm == {"method_id": None, "method_version": None}


# ---------------------------------------------------------------------------
# TEXT ANCHOR: new_provenance_keys_no_leak_tests
# R10: state-consuming method provenance keys (input_state_hash,
# validation="function_purity_recomputed_match", result_summary with capped
# ref lists) must NEVER appear in serialize_analysis_product output.
# ---------------------------------------------------------------------------


def test_serialize_no_leak_state_consuming_provenance_keys() -> None:
    """A deterministic product whose authoring_provenance_json contains the NEW
    state-consuming provenance keys (input_state_hash, validation sentinel
    'function_purity_recomputed_match', result_summary with capped ref lists)
    must expose ONLY {method_id, method_version} in generation_method and NONE
    of those new keys anywhere in the serialized output."""
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    product = SimpleNamespace(
        analysis_product_id="ap-state-consuming-001",
        product_kind="summary",
        executor_type="deterministic",
        lifecycle_status="package_eligible",
        title="Member state profile product",
        is_non_evidentiary=False,
        basis_hash="bh-msp",
        spec_hash="sh-msp",
        created_at=None,
        authoring_provenance_json={
            "method_id": "working_set_member_state_profile",
            "method_version": 1,
            # new state-consuming keys that must not leak
            "input_basis_hash": "ibh-msp-secret",
            "input_state_hash": "ish-msp-secret",
            "param_hash": "ph-msp-secret",
            "validation": "function_purity_recomputed_match",
            "result_summary": {
                "member_count": 5,
                "resolved_count": 4,
                "unresolved_count": 1,
                "unresolved_refs": ["ref-a", "ref-b"],
                "by_ref_kind": {"prior_product": 2, "pass_run": 3},
            },
        },
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    # generation_method must be bounded: only the two identity keys
    gm = result["generation_method"]
    assert gm is not None
    assert set(gm.keys()) == {"method_id", "method_version"}
    assert gm["method_id"] == "working_set_member_state_profile"
    assert gm["method_version"] == 1

    # New provenance keys must not appear in generation_method
    assert "input_state_hash" not in gm
    assert "validation" not in gm
    assert "result_summary" not in gm
    assert "input_basis_hash" not in gm
    assert "param_hash" not in gm

    # New provenance keys must not appear at the top-level result dict either
    assert "input_state_hash" not in result
    assert "input_basis_hash" not in result
    assert "param_hash" not in result
    assert "result_summary" not in result
    assert "validation" not in result
    # authoring_provenance_json itself must not be exposed
    assert "authoring_provenance_json" not in result


def test_serialize_no_leak_staleness_diagnostic_provenance_keys() -> None:
    """Same no-leak contract for the staleness diagnostic method, which also
    uses function_purity_recomputed_match and stores a result_summary with
    capped per-category ref-id lists."""
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    product = SimpleNamespace(
        analysis_product_id="ap-stale-diag-001",
        product_kind="diagnostic",
        executor_type="deterministic",
        lifecycle_status="package_eligible",
        title="Staleness diagnostic product",
        is_non_evidentiary=False,
        basis_hash="bh-sd",
        spec_hash="sh-sd",
        created_at=None,
        authoring_provenance_json={
            "method_id": "working_set_staleness_diagnostic",
            "method_version": 1,
            # new state-consuming keys
            "input_basis_hash": "ibh-sd-secret",
            "input_state_hash": "ish-sd-secret",
            "param_hash": "ph-sd-secret",
            "validation": "function_purity_recomputed_match",
            "result_summary": {
                "clean": False,
                "superseded_prior_product_count": 2,
                "failed_pass_run_count": 1,
                "unresolved_member_count": 0,
                # capped ref-id lists — must never leak
                "superseded_prior_product_refs": ["pp-1", "pp-2"],
                "failed_pass_run_refs": ["pr-7"],
                "unresolved_member_refs": [],
            },
        },
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    gm = result["generation_method"]
    assert gm is not None
    assert set(gm.keys()) == {"method_id", "method_version"}
    assert gm["method_id"] == "working_set_staleness_diagnostic"
    assert gm["method_version"] == 1

    # None of the new provenance keys may appear in generation_method
    assert "input_state_hash" not in gm
    assert "validation" not in gm
    assert "result_summary" not in gm

    # None of the new provenance keys may appear at the top level
    assert "input_state_hash" not in result
    assert "input_basis_hash" not in result
    assert "param_hash" not in result
    assert "result_summary" not in result
    assert "validation" not in result
    assert "authoring_provenance_json" not in result


def test_serialize_no_leak_full_serialized_dict_contains_no_provenance_internals() -> None:
    """Exhaustive check: iterate the entire flattened key set of the serialized
    output and assert none of the forbidden provenance internal keys appear at
    any level of the top-level dict (not recursive, but covers all direct keys
    and keys inside generation_method)."""
    import json as _json
    from types import SimpleNamespace
    from app.services.layer3_sublayer_state import serialize_analysis_product

    _FORBIDDEN_KEYS = {
        "input_state_hash",
        "input_basis_hash",
        "param_hash",
        "result_summary",
        "validation",
        "authoring_provenance_json",
        "executor_identity",
        "payload_ref",
    }

    product = SimpleNamespace(
        analysis_product_id="ap-exhaustive-001",
        product_kind="diagnostic",
        executor_type="deterministic",
        lifecycle_status="accepted",
        title="Exhaustive no-leak product",
        is_non_evidentiary=False,
        basis_hash="bh-ex",
        spec_hash="sh-ex",
        created_at=None,
        authoring_provenance_json={
            "method_id": "working_set_staleness_diagnostic",
            "method_version": 1,
            "input_basis_hash": "ibh-ex",
            "input_state_hash": "ish-ex",
            "param_hash": "ph-ex",
            "validation": "function_purity_recomputed_match",
            "executor_identity": {"operator_id": "op-1"},
            "result_summary": {
                "clean": True,
                "superseded_prior_product_count": 0,
                "failed_pass_run_count": 0,
                "unresolved_member_count": 0,
                "superseded_prior_product_refs": [],
                "failed_pass_run_refs": [],
                "unresolved_member_refs": [],
            },
        },
    )

    result = serialize_analysis_product(product, evidence_links=[], latest_decision=None)

    # Collect all top-level keys of the result dict and all keys inside
    # generation_method (the only nested dict from provenance)
    all_exposed_keys: set[str] = set(result.keys())
    gm = result.get("generation_method")
    if isinstance(gm, dict):
        all_exposed_keys |= set(gm.keys())

    for forbidden in _FORBIDDEN_KEYS:
        assert forbidden not in all_exposed_keys, (
            f"Forbidden provenance key '{forbidden}' leaked into serialized output. "
            f"Exposed keys: {sorted(all_exposed_keys)}"
        )

    # Confirm no forbidden key appears anywhere in the JSON-serialized output string
    serialized_str = _json.dumps(result)
    for forbidden in _FORBIDDEN_KEYS:
        assert f'"{forbidden}"' not in serialized_str, (
            f"Forbidden key '{forbidden}' appeared in JSON-serialized output"
        )
