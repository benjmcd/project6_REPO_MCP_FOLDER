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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

from app.api.deps import get_db
from app.core.config import Settings, bootstrap_storage_tree, settings
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
from app.services.layer3_analysis_product_promotion import (
    AnalysisProductTransitionRequest,
    transition_analysis_product,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from main import app

# Import the session builder from test_layer3_pass_entry (returns tuple[str, str, datetime])
from test_layer3_pass_entry import _build_quant_ready_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient wired to a fresh in-memory SQLite DB, matching the fixture
    pattern from test_layer3_api.py."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "external-local-export"))
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/layer3-internal-webhook")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "test-internal-webhook")
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    bootstrap_storage_tree(storage_dir)

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
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
