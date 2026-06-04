from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_INIT_MODE", "none")
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models import L3SecXbrlAuthBindingReceipt, L3SecXbrlOperatorReviewWorkflow
from app.models.models import (
    L3_SEC_XBRL_AUTH_BINDING_POLICY_ID,
    L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY,
    L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND,
)
from app.services import layer3_sec_xbrl_auth_binding as auth_binding
from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy
from app.services.layer3_utils import stable_hash


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_0046_PATH = ROOT / "backend" / "alembic" / "versions" / "0046_layer3_sec_xbrl_auth_binding_receipt.py"
MIGRATION_0047_PATH = (
    ROOT / "backend" / "alembic" / "versions" / "0047_layer3_sec_xbrl_auth_binding_route_actor_scope.py"
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


def _hash(label: str) -> str:
    return stable_hash({"sec_xbrl_auth_binding_test": label})


def _policy(
    *,
    role: str = "owner",
    actor: str = "actor",
    workspace: str = "workspace",
    policy: str = "policy",
    route_family: str = "sec_xbrl_operator_review_workflow_status_read",
):
    actor_ref_hash = _hash(actor)
    workspace_ref_hash = _hash(workspace)
    return {
        "decision": "allow",
        "route_family": route_family,
        "role": role,
        "actor_ref_hash": actor_ref_hash,
        "workspace_ref_hash": workspace_ref_hash,
        "policy_hash": stable_hash(
            {
                "policy": policy,
                "actor_ref_hash": actor_ref_hash,
                "workspace_ref_hash": workspace_ref_hash,
                "route_family": route_family,
                "role": role,
            }
        ),
    }


def _workflow(db_session, *, workflow_id: str = "workflow-1", basis_hash: str | None = None):
    row = L3SecXbrlOperatorReviewWorkflow(
        sec_xbrl_operator_review_workflow_id=workflow_id,
        sec_xbrl_statement_packet_set_id="packet-1",
        client_request_id=f"{workflow_id}-client-request",
        workflow_basis_hash=basis_hash or _hash(f"{workflow_id}-basis"),
        workflow_schema_id="layer3.sec_xbrl_operator_review_workflow.v1",
        statement_packet_basis_hash=_hash(f"{workflow_id}-packet"),
        source_projection_basis_hash=_hash(f"{workflow_id}-projection"),
        statement_count=1,
        row_count=1,
        review_exception_count=0,
        review_ready=True,
        permitted_controls_json=[],
        blocked_controls_json=[],
        authority_refs_json={},
        review_summary_json={},
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_auth_binding_model_creates_additive_table() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    try:
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("l3_sec_xbrl_auth_binding_receipt")}
        indexes = {index["name"] for index in inspector.get_indexes("l3_sec_xbrl_auth_binding_receipt")}
        unique_constraints = {
            constraint["name"] for constraint in inspector.get_unique_constraints("l3_sec_xbrl_auth_binding_receipt")
        }

        assert "sec_xbrl_auth_binding_receipt_id" in columns
        assert "source_receipt_kind" in columns
        assert "source_receipt_id" in columns
        assert "source_receipt_basis_hash" in columns
        assert "actor_ref_hash" in columns
        assert "workspace_ref_hash" in columns
        assert "negative_invariants_json" in columns
        assert "ix_l3_sec_xbrl_auth_binding_source_basis" in indexes
        assert "ix_l3_sec_xbrl_auth_binding_actor_workspace" in indexes
        assert "uq_l3_sec_xbrl_auth_binding_source_route_actor_role" in unique_constraints
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_auth_binding_migration_declares_additive_table() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location("migration_0046_sec_xbrl_auth_binding", MIGRATION_0046_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0046_layer3_sec_xbrl_auth_binding_receipt"
    assert module.down_revision == "0045_layer3_sec_xbrl_controlled_value_reveal_submit"
    source = MIGRATION_0046_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_auth_binding_receipt" in source
    assert "drop_table_idempotent(TABLE_NAME)" in source
    assert "source_receipt_kind" in source
    assert "actor_ref_hash" in source
    assert "workspace_ref_hash" in source


def test_auth_binding_route_actor_scope_migration_rescopes_source_unique_constraint() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location("migration_0047_sec_xbrl_auth_binding", MIGRATION_0047_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0047_layer3_sec_xbrl_auth_binding_route_actor_scope"
    assert module.down_revision == "0046_layer3_sec_xbrl_auth_binding_receipt"
    source = MIGRATION_0047_PATH.read_text(encoding="utf-8")
    assert "uq_l3_sec_xbrl_auth_binding_source_receipt" in source
    assert "uq_l3_sec_xbrl_auth_binding_source_route_actor_role" in source
    assert "route_family" in source
    assert "actor_ref_hash" in source
    assert "workspace_ref_hash" in source
    assert "role" in source
    assert "Cannot safely downgrade SEC XBRL auth binding route/actor uniqueness" in source


def test_auth_binding_records_hash_only_receipt_and_replays_by_basis(db_session) -> None:
    workflow = _workflow(db_session)
    response = auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-1",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(),
    )

    assert response["schema_id"] == auth_binding.AUTH_BINDING_SCHEMA_ID
    assert response["binding_policy_id"] == L3_SEC_XBRL_AUTH_BINDING_POLICY_ID
    assert response["binding_state"] == L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND
    assert response["redaction_policy"] == L3_SEC_XBRL_AUTH_BINDING_REDACTION_POLICY
    assert response["source_receipt_kind"] == "operator_review_workflow"
    assert response["source_receipt_basis_hash"] == workflow.workflow_basis_hash
    assert response["actor_ref_hash"] == _hash("actor")
    assert response["workspace_ref_hash"] == _hash("workspace")
    assert response["runtime_auth_dependency_installed"] is False
    assert response["api_route_behavior_changed"] is False
    assert response["value_reveal_performed"] is False
    assert "source_receipt_id" not in response

    row = db_session.query(L3SecXbrlAuthBindingReceipt).one()
    assert row.binding_basis_hash == response["binding_basis_hash"]
    assert row.binding_summary_json["hash_only_actor_workspace_refs"] is True
    assert row.negative_invariants_json["raw_operator_identity_persisted"] is False

    replay = auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-2",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(),
    )
    assert replay["idempotent_replay"] is True
    assert replay["sec_xbrl_auth_binding_receipt_id"] == response["sec_xbrl_auth_binding_receipt_id"]
    assert db_session.query(L3SecXbrlAuthBindingReceipt).count() == 1

    text = json.dumps(response, sort_keys=True)
    assert "operator@example.com" not in text
    assert "C:/" not in text
    assert "\\Users\\" not in text
    assert "0000123456-26-000001" not in text
    assert "123.45" not in text


def test_auth_binding_fails_closed_on_source_and_policy_gaps(db_session) -> None:
    workflow = _workflow(db_session, workflow_id="workflow-gaps")

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as missing_source:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-missing-source",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id="missing",
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=_policy(),
        )
    assert missing_source.value.code == "sec_xbrl_auth_binding_source_receipt_missing"

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as bad_route:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-bad-route",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_controlled_value_reveal_submit_status_read",
            policy_decision=_policy(),
        )
    assert bad_route.value.code == "sec_xbrl_auth_binding_route_family_not_admitted"

    raw_policy = {**_policy(), "operator_email": "operator@example.com"}
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as raw_fields:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-raw-policy",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=raw_policy,
        )
    assert raw_fields.value.code == "sec_xbrl_auth_binding_policy_raw_fields_not_admitted"

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as raw_client_request:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="operator@example.com",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=_policy(),
        )
    assert raw_client_request.value.code == "sec_xbrl_auth_binding_raw_reference_not_admitted"

    for index, raw_reference in enumerate(("0000123456", "issuer 0000123456 packet", "CIK0000123456")):
        with pytest.raises(auth_binding.SecXbrlAuthBindingError) as raw_cik_client_request:
            auth_binding.record_sec_xbrl_auth_binding(
                db_session,
                client_request_id=raw_reference,
                source_receipt_kind="operator_review_workflow",
                source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
                source_receipt_basis_hash=workflow.workflow_basis_hash,
                route_family="sec_xbrl_operator_review_workflow_status_read",
                policy_decision=_policy(),
            )
        assert raw_cik_client_request.value.code == "sec_xbrl_auth_binding_raw_reference_not_admitted"

        with pytest.raises(auth_binding.SecXbrlAuthBindingError) as raw_cik_source_id:
            auth_binding.record_sec_xbrl_auth_binding(
                db_session,
                client_request_id=f"auth-binding-raw-source-{index}",
                source_receipt_kind="operator_review_workflow",
                source_receipt_id=raw_reference,
                source_receipt_basis_hash=workflow.workflow_basis_hash,
                route_family="sec_xbrl_operator_review_workflow_status_read",
                policy_decision=_policy(),
            )
        assert raw_cik_source_id.value.code == "sec_xbrl_auth_binding_raw_reference_not_admitted"

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as bad_role:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-bad-role",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=_policy(role="admin"),
        )
    assert bad_role.value.code == "sec_xbrl_auth_binding_role_not_admitted"

    missing_policy_route = {k: v for k, v in _policy().items() if k != "route_family"}
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as missing_route:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-missing-policy-route",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=missing_policy_route,
        )
    assert missing_route.value.code == "sec_xbrl_auth_binding_policy_route_family_missing"

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as auditor_write:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-auditor-write",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_decision_submit_write",
            policy_decision=_policy(
                role="auditor",
                route_family="sec_xbrl_operator_review_decision_submit_write",
            ),
        )
    assert auditor_write.value.code == "sec_xbrl_auth_binding_role_route_forbidden"

    missing_decision = {k: v for k, v in _policy().items() if k != "decision"}
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as missing_policy_decision:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-missing-policy-decision",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=missing_decision,
        )
    assert missing_policy_decision.value.code == "sec_xbrl_auth_binding_policy_decision_missing"
    assert db_session.query(L3SecXbrlAuthBindingReceipt).count() == 0


def test_auth_binding_requires_matching_owner_context(db_session) -> None:
    workflow = _workflow(db_session, workflow_id="workflow-owner-context")
    auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-owner-context",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(),
    )

    allowed = auth_binding.require_sec_xbrl_owner_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(),
    )
    assert allowed["binding_state"] == L3_SEC_XBRL_AUTH_BINDING_STATE_OWNER_BOUND

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as cross_owner:
        auth_binding.require_sec_xbrl_owner_binding(
            db_session,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=_policy(actor="other-actor"),
        )
    assert cross_owner.value.code == "sec_xbrl_auth_binding_missing"

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as stale_policy:
        auth_binding.require_sec_xbrl_owner_binding(
            db_session,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=_policy(policy="stale-policy"),
        )
    assert stale_policy.value.code == "sec_xbrl_auth_binding_context_mismatch"
    assert "policy_hash" in stale_policy.value.details["mismatched_fields"]


def test_auth_binding_allows_same_source_owner_across_admitted_route_family(db_session) -> None:
    workflow = _workflow(db_session, workflow_id="workflow-route-family")
    read_binding = auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-route-family",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_workflow_status_read"),
    )

    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as write_before_route_binding:
        auth_binding.require_sec_xbrl_owner_binding(
            db_session,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            route_family="sec_xbrl_operator_review_decision_submit_write",
            policy_decision=_policy(route_family="sec_xbrl_operator_review_decision_submit_write"),
        )
    assert write_before_route_binding.value.code == "sec_xbrl_auth_binding_missing"

    write_binding = auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-route-family-write",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_decision_submit_write",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_decision_submit_write"),
    )
    owner_write = auth_binding.require_sec_xbrl_owner_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        route_family="sec_xbrl_operator_review_decision_submit_write",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_decision_submit_write"),
    )

    auditor_binding = auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-route-family-auditor",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(
            role="auditor",
            route_family="sec_xbrl_operator_review_workflow_status_read",
        ),
    )
    auditor_read = auth_binding.require_sec_xbrl_owner_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(
            role="auditor",
            route_family="sec_xbrl_operator_review_workflow_status_read",
        ),
    )

    assert read_binding["route_family"] == "sec_xbrl_operator_review_workflow_status_read"
    assert write_binding["route_family"] == "sec_xbrl_operator_review_decision_submit_write"
    assert owner_write["route_family"] == "sec_xbrl_operator_review_decision_submit_write"
    assert auditor_binding["role"] == "auditor"
    assert auditor_read["role"] == "auditor"
    assert db_session.query(L3SecXbrlAuthBindingReceipt).count() == 3

    changed_policy = _policy(
        policy="changed",
        route_family="sec_xbrl_operator_review_decision_submit_write",
    )
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as duplicate_route_actor:
        auth_binding.record_sec_xbrl_auth_binding(
            db_session,
            client_request_id="auth-binding-route-family-write-new-policy",
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            source_receipt_basis_hash=workflow.workflow_basis_hash,
            route_family="sec_xbrl_operator_review_decision_submit_write",
            policy_decision=changed_policy,
        )
    assert duplicate_route_actor.value.code == "sec_xbrl_auth_binding_source_route_actor_conflict"


def test_auth_binding_inspection_returns_redacted_list_for_multiple_route_bindings(db_session) -> None:
    workflow = _workflow(db_session, workflow_id="workflow-inspection-multiple")
    auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-inspection-read",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_workflow_status_read"),
    )
    auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-inspection-write",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_decision_submit_write",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_decision_submit_write"),
    )
    auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-inspection-auditor",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(
            role="auditor",
            route_family="sec_xbrl_operator_review_workflow_status_read",
        ),
    )

    inspection = auth_binding.inspect_sec_xbrl_auth_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
    )
    auditor_read = auth_binding.inspect_sec_xbrl_auth_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        role="auditor",
    )

    assert inspection["inspection_state"] == "multiple_bindings"
    assert inspection["binding_count"] == 3
    assert {
        (item["route_family"], item["role"])
        for item in inspection["bindings"]
    } == {
        ("sec_xbrl_operator_review_workflow_status_read", "owner"),
        ("sec_xbrl_operator_review_workflow_status_read", "auditor"),
        ("sec_xbrl_operator_review_decision_submit_write", "owner"),
    }
    assert auditor_read["route_family"] == "sec_xbrl_operator_review_workflow_status_read"
    assert auditor_read["role"] == "auditor"
    assert workflow.sec_xbrl_operator_review_workflow_id not in json.dumps(inspection, sort_keys=True)


def test_auth_binding_accepts_legacy_policy_hash_candidate_for_existing_binding(db_session) -> None:
    workflow = _workflow(db_session, workflow_id="workflow-legacy-policy-hash")
    legacy_policy = _policy(policy="legacy-policy")
    current_policy = _policy(policy="current-policy")
    current_policy_with_legacy_candidate = {
        **current_policy,
        "compatible_policy_hashes": [
            current_policy["policy_hash"],
            legacy_policy["policy_hash"],
        ],
    }
    auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-legacy-policy",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=legacy_policy,
    )

    accepted = auth_binding.require_sec_xbrl_owner_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=current_policy_with_legacy_candidate,
    )
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as stale_without_candidate:
        auth_binding.require_sec_xbrl_owner_binding(
            db_session,
            source_receipt_kind="operator_review_workflow",
            source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
            route_family="sec_xbrl_operator_review_workflow_status_read",
            policy_decision=current_policy,
        )

    assert accepted["policy_hash"] == legacy_policy["policy_hash"]
    assert stale_without_candidate.value.code == "sec_xbrl_auth_binding_context_mismatch"
    assert "policy_hash" in stale_without_candidate.value.details["mismatched_fields"]


def test_in_app_auth_policy_emits_legacy_policy_hash_candidate() -> None:
    decision = auth_policy.authorize_sec_xbrl_route(
        headers={},
        route_family="sec_xbrl_operator_review_workflow_status_read",
        requested_role="owner",
    )

    legacy_hash = auth_policy._legacy_policy_hash(
        actor_ref_hash=decision["actor_ref_hash"],
        workspace_ref_hash=decision["workspace_ref_hash"],
    )
    assert decision["policy_hash"] in decision["compatible_policy_hashes"]
    assert legacy_hash in decision["compatible_policy_hashes"]
    assert legacy_hash != decision["policy_hash"]
