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
from app.services.layer3_utils import stable_hash


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "backend" / "alembic" / "versions" / "0046_layer3_sec_xbrl_auth_binding_receipt.py"


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
    return {
        "decision": "allow",
        "route_family": route_family,
        "role": role,
        "actor_ref_hash": _hash(actor),
        "workspace_ref_hash": _hash(workspace),
        "policy_hash": _hash(policy),
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
        assert "uq_l3_sec_xbrl_auth_binding_source_receipt" in unique_constraints
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_auth_binding_migration_declares_additive_table() -> None:
    backend_root = str(ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    spec = importlib.util.spec_from_file_location("migration_0046_sec_xbrl_auth_binding", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0046_layer3_sec_xbrl_auth_binding_receipt"
    assert module.down_revision == "0045_layer3_sec_xbrl_controlled_value_reveal_submit"
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "l3_sec_xbrl_auth_binding_receipt" in source
    assert "drop_table_idempotent(TABLE_NAME)" in source
    assert "source_receipt_kind" in source
    assert "actor_ref_hash" in source
    assert "workspace_ref_hash" in source


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
    assert cross_owner.value.code == "sec_xbrl_auth_binding_context_mismatch"
    assert "actor_ref_hash" in cross_owner.value.details["mismatched_fields"]

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
    auth_binding.record_sec_xbrl_auth_binding(
        db_session,
        client_request_id="auth-binding-route-family",
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        source_receipt_basis_hash=workflow.workflow_basis_hash,
        route_family="sec_xbrl_operator_review_workflow_status_read",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_workflow_status_read"),
    )

    owner_write = auth_binding.require_sec_xbrl_owner_binding(
        db_session,
        source_receipt_kind="operator_review_workflow",
        source_receipt_id=workflow.sec_xbrl_operator_review_workflow_id,
        route_family="sec_xbrl_operator_review_decision_submit_write",
        policy_decision=_policy(route_family="sec_xbrl_operator_review_decision_submit_write"),
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

    assert owner_write["route_family"] == "sec_xbrl_operator_review_workflow_status_read"
    assert auditor_read["role"] == "owner"
    assert db_session.query(L3SecXbrlAuthBindingReceipt).count() == 1
