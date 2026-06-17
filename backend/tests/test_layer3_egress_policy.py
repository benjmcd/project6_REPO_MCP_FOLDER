"""Tests for layer3_egress_policy — Lane 17 default-DENY egress contract.

Covers:
- evaluate_executor_egress: local, model, and unknown executor types.
- assert_executor_egress_allowed: raises EgressPolicyError on denial.
- Default-deny with partial config (flag True but no policy; policy set but flag
  False — both switches required).
- package_authority_grants_egress() is False (tested invariant).
- default_data_sensitivity() is "local_only".
- Settings flag layer3_model_egress_enabled defaults to False.
- Authoring still works for human/deterministic (egress assertion is a no-op).
- Existing unsupported_executor_type behaviour for agent/external_api is unchanged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.layer3_egress_policy import (
    EGRESS_POLICY_SCHEMA_ID,
    EgressDecision,
    EgressPolicy,
    EgressPolicyError,
    assert_executor_egress_allowed,
    default_data_sensitivity,
    evaluate_executor_egress,
    package_authority_grants_egress,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deny_policy() -> EgressPolicy:
    """An EgressPolicy with allow_model_egress=False (the default)."""
    return EgressPolicy(allow_model_egress=False)


def _allow_policy() -> EgressPolicy:
    """An EgressPolicy with allow_model_egress=True.

    NOTE: Constructing this object is possible in tests; no factory provides
    it in production code today.  Having the flag AND this object is required
    for egress — neither alone suffices.
    """
    return EgressPolicy(allow_model_egress=True)


# ---------------------------------------------------------------------------
# Data-sensitivity defaults
# ---------------------------------------------------------------------------


def test_default_data_sensitivity_is_local_only() -> None:
    assert default_data_sensitivity() == "local_only"


# ---------------------------------------------------------------------------
# evaluate_executor_egress — local executor types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("executor_type", ["human", "deterministic"])
def test_evaluate_local_executor_allowed(executor_type: str) -> None:
    decision = evaluate_executor_egress(executor_type)
    assert decision.allowed is True
    assert decision.reason == "local_execution_no_egress"
    assert decision.executor_type == executor_type
    assert decision.data_sensitivity == "local_only"
    assert decision.schema_id == EGRESS_POLICY_SCHEMA_ID


@pytest.mark.parametrize("executor_type", ["human", "deterministic"])
def test_evaluate_local_executor_ignores_policy_and_flag(executor_type: str) -> None:
    """Local executor types are always allowed regardless of policy/flag state."""
    decision = evaluate_executor_egress(
        executor_type,
        policy=_allow_policy(),
        model_egress_enabled=True,
    )
    assert decision.allowed is True
    assert decision.reason == "local_execution_no_egress"


# ---------------------------------------------------------------------------
# evaluate_executor_egress — model executor types (default deny)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_evaluate_model_executor_denied_by_default(executor_type: str) -> None:
    decision = evaluate_executor_egress(executor_type)
    assert decision.allowed is False
    assert decision.reason == "model_egress_requires_explicit_policy"
    assert decision.executor_type == executor_type
    assert decision.data_sensitivity == "local_only"


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_evaluate_model_executor_denied_flag_true_no_policy(executor_type: str) -> None:
    """Flag=True but policy=None must still deny."""
    decision = evaluate_executor_egress(
        executor_type,
        policy=None,
        model_egress_enabled=True,
    )
    assert decision.allowed is False
    assert decision.reason == "model_egress_requires_explicit_policy"


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_evaluate_model_executor_denied_policy_set_flag_false(executor_type: str) -> None:
    """Allowing policy present but flag=False must still deny."""
    decision = evaluate_executor_egress(
        executor_type,
        policy=_allow_policy(),
        model_egress_enabled=False,
    )
    assert decision.allowed is False
    assert decision.reason == "model_egress_requires_explicit_policy"


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_evaluate_model_executor_denied_deny_policy_flag_true(executor_type: str) -> None:
    """Flag=True but policy.allow_model_egress=False must still deny."""
    decision = evaluate_executor_egress(
        executor_type,
        policy=_deny_policy(),
        model_egress_enabled=True,
    )
    assert decision.allowed is False
    assert decision.reason == "model_egress_requires_explicit_policy"


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_evaluate_model_executor_allowed_when_both_switches_on(executor_type: str) -> None:
    """Both flag=True AND policy.allow_model_egress=True => allowed.

    This path is unreachable in production today (no factory creates an allowing
    policy; flag defaults False).  Tested here to document the future contract.
    """
    decision = evaluate_executor_egress(
        executor_type,
        policy=_allow_policy(),
        model_egress_enabled=True,
    )
    assert decision.allowed is True
    # Allowed model egress must report a distinct, honest reason — not the
    # local-execution reason (guards against the reason being mislabeled).
    assert decision.reason == "model_egress_explicitly_permitted"


# ---------------------------------------------------------------------------
# evaluate_executor_egress — unknown executor type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("executor_type", ["unknown_type", "", "llm", "rpa"])
def test_evaluate_unknown_executor_denied(executor_type: str) -> None:
    decision = evaluate_executor_egress(executor_type)
    assert decision.allowed is False
    assert decision.reason == "unknown_executor_type"
    assert decision.executor_type == executor_type


# ---------------------------------------------------------------------------
# assert_executor_egress_allowed — local types pass (no exception)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("executor_type", ["human", "deterministic"])
def test_assert_local_executor_returns_decision(executor_type: str) -> None:
    decision = assert_executor_egress_allowed(executor_type)
    assert isinstance(decision, EgressDecision)
    assert decision.allowed is True


# ---------------------------------------------------------------------------
# assert_executor_egress_allowed — model types raise EgressPolicyError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_assert_model_executor_raises(executor_type: str) -> None:
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_executor_egress_allowed(executor_type)
    err = exc_info.value
    assert err.error_code == "model_egress_not_permitted"
    assert err.http_status == 403
    assert executor_type in err.message


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_assert_model_executor_raises_flag_true_no_policy(executor_type: str) -> None:
    """Flag=True but no policy — still raises."""
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_executor_egress_allowed(executor_type, model_egress_enabled=True)
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403


@pytest.mark.parametrize("executor_type", ["agent", "external_api"])
def test_assert_model_executor_raises_policy_set_flag_false(executor_type: str) -> None:
    """Allowing policy but flag=False — still raises."""
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_executor_egress_allowed(
            executor_type,
            policy=_allow_policy(),
            model_egress_enabled=False,
        )
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403


# ---------------------------------------------------------------------------
# assert_executor_egress_allowed — unknown type raises
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unknown_type", ["some_future_type", "", "llm", "rpa"])
def test_assert_unknown_executor_raises(unknown_type: str) -> None:
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_executor_egress_allowed(unknown_type)
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403


# ---------------------------------------------------------------------------
# EgressPolicyError.response_body shape
# ---------------------------------------------------------------------------


def test_egress_policy_error_response_body() -> None:
    err = EgressPolicyError(
        "test message",
        error_code="model_egress_not_permitted",
        http_status=403,
    )
    body = err.response_body()
    assert body["schema_id"] == EGRESS_POLICY_SCHEMA_ID
    assert body["error_code"] == "model_egress_not_permitted"
    assert body["message"] == "test message"


# ---------------------------------------------------------------------------
# package_authority_grants_egress — explicit tested invariant
# ---------------------------------------------------------------------------


def test_package_authority_grants_egress_is_false() -> None:
    assert package_authority_grants_egress() is False


# ---------------------------------------------------------------------------
# Settings flag default
# ---------------------------------------------------------------------------


def test_settings_flag_layer3_model_egress_enabled_defaults_false() -> None:
    from app.core.config import settings
    assert settings.layer3_model_egress_enabled is False


# ---------------------------------------------------------------------------
# Authoring integration — human/deterministic still work (egress no-op)
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.models import (
    L3AnalysisProduct,
    L3MaterialSnapshot,
    L3Session,
)
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    Layer3AnalysisProductError,
    create_analysis_product_draft,
)


@pytest.fixture()
def egress_db():
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
def egress_seeded_db(egress_db):
    session_row = L3Session(
        session_id="session-egress-test",
        selection_manifest_id="manifest-egress-test",
        status="active_execution",
        operator_context_json={},
        summary_json={},
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id="snapshot-egress-test",
        session_id="session-egress-test",
        descriptor_id="descriptor-egress-test",
        source_plane="runtime",
        source_shape="dataset_version",
        payload_ref="payload://egress-test",
        payload_hash="hash-egress-test",
        source_identity_json={"dataset_version_id": "dv-egress-test"},
        source_provenance_json={},
        load_summary_json={},
    )
    egress_db.add_all([session_row, snapshot])
    egress_db.commit()
    return egress_db


def test_authoring_human_executor_egress_noop(egress_seeded_db) -> None:
    """human executor_type passes egress assertion (local, no egress)."""
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Egress policy no-op check",
        body="This product is authored with executor_type=human; egress assertion is a no-op.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-egress-test",
                evidence_role="observation",
            ),
        ),
        executor_type="human",
    )
    result = create_analysis_product_draft(
        egress_seeded_db,
        session_id="session-egress-test",
        client_request_id="req-egress-human-001",
        draft=draft,
    )
    egress_seeded_db.commit()
    assert result.product.executor_type == "human"
    assert result.replayed is False


def test_authoring_deterministic_executor_egress_noop(egress_seeded_db) -> None:
    """deterministic executor_type passes egress assertion (local, no egress)."""
    draft = AnalysisProductDraft(
        product_kind="summary",
        title="Deterministic egress policy no-op",
        body="This product is authored with executor_type=deterministic; egress assertion is a no-op.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-egress-test",
                evidence_role="observation",
            ),
        ),
        executor_type="deterministic",
    )
    result = create_analysis_product_draft(
        egress_seeded_db,
        session_id="session-egress-test",
        client_request_id="req-egress-det-001",
        draft=draft,
    )
    egress_seeded_db.commit()
    assert result.product.executor_type == "deterministic"
    assert result.replayed is False


def test_authoring_agent_executor_raises_unsupported_executor_type(egress_seeded_db) -> None:
    """agent executor_type is rejected by the ALLOWED_EXECUTOR_TYPES gate first.

    The existing error_code='unsupported_executor_type' is unchanged — the
    ALLOWED_EXECUTOR_TYPES check fires before the egress assertion.
    """
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="Agent attempt",
        body="This should be rejected before the egress assertion.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-egress-test",
                evidence_role="observation",
            ),
        ),
        executor_type="agent",
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            egress_seeded_db,
            session_id="session-egress-test",
            client_request_id="req-egress-agent-001",
            draft=draft,
        )
    assert exc_info.value.error_code == "unsupported_executor_type"
    assert exc_info.value.http_status == 400


def test_authoring_external_api_executor_raises_unsupported_executor_type(egress_seeded_db) -> None:
    """external_api executor_type is rejected by the ALLOWED_EXECUTOR_TYPES gate first."""
    draft = AnalysisProductDraft(
        product_kind="finding",
        title="External API attempt",
        body="This should be rejected before the egress assertion.",
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="material_snapshot",
                ref_id="snapshot-egress-test",
                evidence_role="observation",
            ),
        ),
        executor_type="external_api",
    )
    with pytest.raises(Layer3AnalysisProductError) as exc_info:
        create_analysis_product_draft(
            egress_seeded_db,
            session_id="session-egress-test",
            client_request_id="req-egress-extapi-001",
            draft=draft,
        )
    assert exc_info.value.error_code == "unsupported_executor_type"
    assert exc_info.value.http_status == 400
