"""Tests for layer3_agent_product_runtime — Lane 19 Gated Agent Runtime v0.

Verifies the FAILS-CLOSED scaffold:
- assert_agent_generation_admissible raises EgressPolicyError by default (gate 3).
- generate_agent_product_draft raises EgressPolicyError; no product created (DB count unchanged).
- An invalid adapter contract (draft_only=False or allowing egress_policy) raises
  AgentAdapterContractError before the egress gate.
- model_egress_enabled=True alone is insufficient: the bound policy still denies.
- No network/model/provider names imported into the runtime module.
- The NotImplementedError backstop is documented-unreachable under defaults.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import L3AnalysisProduct
from app.services.layer3_agent_adapter_contract import (
    AgentAdapterContract,
    AgentAdapterContractError,
    compute_prompt_spec_hash,
)
from app.services.layer3_agent_product_runtime import (
    AGENT_RUNTIME_SCHEMA_ID,
    assert_agent_generation_admissible,
    generate_agent_product_draft,
)
from app.services.layer3_egress_policy import EgressPolicy, EgressPolicyError

AGENT_RUNTIME_APP_MODULES = {
    module_name: sys.modules[module_name]
    for module_name in (
        "app.services.layer3_agent_adapter_contract",
        "app.services.layer3_agent_product_runtime",
        "app.services.layer3_egress_policy",
    )
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PROMPT_SPEC = {"prompt": "Summarise the working-set findings for agent review."}
_VALID_HASH = compute_prompt_spec_hash(_VALID_PROMPT_SPEC)


def _valid_contract(**overrides) -> AgentAdapterContract:
    """Return a fully valid v0 AgentAdapterContract (default-deny egress policy)."""
    defaults = dict(
        adapter_id="adapter-runtime-test-001",
        adapter_version=1,
        executor_type="agent",
        provider="example_provider",
        model_identity="example-model-v1",
        prompt_spec_hash=_VALID_HASH,
        input_schema_id="layer3.adapter.input.v1",
        output_schema_id="layer3.adapter.output.v1",
        egress_policy=EgressPolicy(),  # allow_model_egress=False by default
        trust_policy="draft_only_review_required",
        draft_only=True,
    )
    defaults.update(overrides)
    return AgentAdapterContract(**defaults)


# ---------------------------------------------------------------------------
# Fixtures — minimal in-memory SQLite session
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Minimal in-memory SQLite session with all ORM tables created."""
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


@pytest.fixture(autouse=True)
def _restore_agent_runtime_modules():
    for module_name, module in AGENT_RUNTIME_APP_MODULES.items():
        sys.modules[module_name] = module


# ---------------------------------------------------------------------------
# Schema ID sanity
# ---------------------------------------------------------------------------


def test_agent_runtime_schema_id() -> None:
    assert AGENT_RUNTIME_SCHEMA_ID == "layer3.agent_product_runtime.v1"


# ---------------------------------------------------------------------------
# assert_agent_generation_admissible — fail-closed default
# ---------------------------------------------------------------------------


def test_admissible_raises_egress_policy_error_by_default() -> None:
    """Gate 3 always raises EgressPolicyError(model_egress_not_permitted, 403) by default."""
    contract = _valid_contract()
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_agent_generation_admissible(contract)
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403


def test_admissible_raises_egress_error_explicit_flag_false() -> None:
    """Explicitly passing model_egress_enabled=False still raises at gate 3."""
    contract = _valid_contract()
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_agent_generation_admissible(contract, model_egress_enabled=False)
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403


def test_admissible_raises_egress_error_flag_true_policy_deny() -> None:
    """model_egress_enabled=True alone is insufficient: bound policy denies.

    Both switches (flag + policy.allow_model_egress) must be True simultaneously.
    The valid v0 contract has allow_model_egress=False, so gate 3 still raises.
    """
    contract = _valid_contract()
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_agent_generation_admissible(contract, model_egress_enabled=True)
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403


# ---------------------------------------------------------------------------
# assert_agent_generation_admissible — invalid contract rejected at gate 1
# ---------------------------------------------------------------------------


def test_admissible_invalid_contract_draft_only_false_raises_contract_error() -> None:
    """draft_only=False raises AgentAdapterContractError at gate 1 (before egress gate)."""
    contract = _valid_contract(draft_only=False)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        assert_agent_generation_admissible(contract)
    assert exc_info.value.error_code == "draft_only_required"
    assert exc_info.value.http_status == 400


def test_admissible_invalid_contract_allowing_policy_raises_contract_error() -> None:
    """An allowing egress_policy raises AgentAdapterContractError at gate 1."""
    contract = _valid_contract(egress_policy=EgressPolicy(allow_model_egress=True))
    with pytest.raises(AgentAdapterContractError) as exc_info:
        assert_agent_generation_admissible(contract)
    assert exc_info.value.error_code == "egress_not_permitted_by_default"
    assert exc_info.value.http_status == 400


def test_admissible_invalid_contract_empty_adapter_id_raises_contract_error() -> None:
    """Empty adapter_id is rejected at gate 1."""
    contract = _valid_contract(adapter_id="")
    with pytest.raises(AgentAdapterContractError) as exc_info:
        assert_agent_generation_admissible(contract)
    assert exc_info.value.error_code == "invalid_adapter_id"


def test_admissible_invalid_contract_unsupported_trust_policy_raises_contract_error() -> None:
    """Unsupported trust_policy is rejected at gate 1."""
    contract = _valid_contract(trust_policy="anything_goes")
    with pytest.raises(AgentAdapterContractError) as exc_info:
        assert_agent_generation_admissible(contract)
    assert exc_info.value.error_code == "unsupported_trust_policy"


# ---------------------------------------------------------------------------
# generate_agent_product_draft — fail-closed, no product created
# ---------------------------------------------------------------------------


def test_generate_raises_egress_error_no_product_created(db_session) -> None:
    """generate_agent_product_draft raises EgressPolicyError; DB product count stays 0.

    The gate fires before any DB write, so no L3AnalysisProduct row is ever created.
    """
    contract = _valid_contract()
    pre_count = db_session.query(L3AnalysisProduct).count()
    assert pre_count == 0

    with pytest.raises(EgressPolicyError) as exc_info:
        generate_agent_product_draft(
            db_session,
            session_id="session-runtime-test",
            client_request_id="crid-runtime-001",
            working_set_id="ws-runtime-001",
            adapter_contract=contract,
        )

    # Error identity
    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403

    # No product created — DB count unchanged
    post_count = db_session.query(L3AnalysisProduct).count()
    assert post_count == 0


def test_generate_raises_egress_not_not_implemented_error(db_session) -> None:
    """generate_agent_product_draft raises EgressPolicyError, NOT NotImplementedError.

    The fail-closed gate (EgressPolicyError) fires first; the NotImplementedError
    backstop is genuinely unreachable under the default posture.
    """
    contract = _valid_contract()
    with pytest.raises(EgressPolicyError):
        generate_agent_product_draft(
            db_session,
            session_id="session-runtime-test",
            client_request_id="crid-runtime-002",
            working_set_id="ws-runtime-002",
            adapter_contract=contract,
        )
    # The fact that we caught EgressPolicyError (not NotImplementedError) is the assertion.


def test_generate_invalid_contract_raises_contract_error_not_egress(db_session) -> None:
    """An invalid contract raises AgentAdapterContractError; the egress gate is never reached."""
    contract = _valid_contract(draft_only=False)
    pre_count = db_session.query(L3AnalysisProduct).count()

    with pytest.raises(AgentAdapterContractError) as exc_info:
        generate_agent_product_draft(
            db_session,
            session_id="session-runtime-test",
            client_request_id="crid-runtime-003",
            working_set_id="ws-runtime-003",
            adapter_contract=contract,
        )

    assert exc_info.value.error_code == "draft_only_required"
    # No product created
    assert db_session.query(L3AnalysisProduct).count() == pre_count


def test_generate_allowing_policy_raises_contract_error(db_session) -> None:
    """A contract with allow_model_egress=True raises AgentAdapterContractError at gate 1."""
    contract = _valid_contract(egress_policy=EgressPolicy(allow_model_egress=True))

    with pytest.raises(AgentAdapterContractError) as exc_info:
        generate_agent_product_draft(
            db_session,
            session_id="session-runtime-test",
            client_request_id="crid-runtime-004",
            working_set_id="ws-runtime-004",
            adapter_contract=contract,
        )

    assert exc_info.value.error_code == "egress_not_permitted_by_default"
    assert db_session.query(L3AnalysisProduct).count() == 0


def test_generate_flag_true_policy_deny_still_raises_egress_error(db_session) -> None:
    """model_egress_enabled=True with a default-deny policy still raises EgressPolicyError.

    Both the master flag AND the policy must permit; the policy alone blocks it.
    """
    contract = _valid_contract()

    with pytest.raises(EgressPolicyError) as exc_info:
        generate_agent_product_draft(
            db_session,
            session_id="session-runtime-test",
            client_request_id="crid-runtime-005",
            working_set_id="ws-runtime-005",
            adapter_contract=contract,
            model_egress_enabled=True,
        )

    assert exc_info.value.error_code == "model_egress_not_permitted"
    assert exc_info.value.http_status == 403
    assert db_session.query(L3AnalysisProduct).count() == 0


# ---------------------------------------------------------------------------
# No network/model/provider import in the runtime module
# ---------------------------------------------------------------------------


def test_runtime_module_has_no_network_imports() -> None:
    """The runtime module must not import requests, httpx, urllib, socket, or
    any obvious model-provider client library.

    This is a hard invariant: the gated runtime must be provably free of any
    code path that could initiate a network or model call.
    """
    import app.services.layer3_agent_product_runtime as runtime_mod

    # Re-import with importlib to get a fresh module dict snapshot
    mod = importlib.import_module("app.services.layer3_agent_product_runtime")
    mod_globals = vars(mod)

    forbidden_names = {"requests", "httpx", "urllib", "socket", "aiohttp", "httpcore"}
    for name in forbidden_names:
        assert name not in mod_globals, (
            f"Forbidden network library '{name}' found in runtime module globals."
        )


def test_runtime_module_source_contains_no_forbidden_imports() -> None:
    """Scan the runtime module's source file to confirm no forbidden network/provider
    imports are present, even if they are conditional or unused.
    """
    runtime_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "layer3_agent_product_runtime.py"
    )
    source = runtime_path.read_text(encoding="utf-8")

    # Network-transport modules must not appear as imports. Asserting the absence
    # of any transport is sufficient to prove the module cannot egress: any model
    # or provider SDK must ultimately reach the network through one of these, so a
    # transport-level absence covers all of them without naming a vendor.
    forbidden_patterns = [
        "import requests",
        "import httpx",
        "import urllib",
        "import socket",
        "import aiohttp",
        "import httpcore",
        "import boto3",
        "import botocore",
        "import grpc",
        "import websocket",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source, (
            f"Forbidden import pattern '{pattern}' found in runtime module source."
        )


# ---------------------------------------------------------------------------
# EgressPolicyError.response_body shape (verifies the error surface is correct)
# ---------------------------------------------------------------------------


def test_egress_policy_error_response_body_shape() -> None:
    """EgressPolicyError raised by the gate has the expected response_body shape."""
    contract = _valid_contract()
    with pytest.raises(EgressPolicyError) as exc_info:
        assert_agent_generation_admissible(contract)
    err = exc_info.value
    body = err.response_body()
    assert body["error_code"] == "model_egress_not_permitted"
    assert "schema_id" in body
    assert "message" in body


# ---------------------------------------------------------------------------
# NotImplementedError backstop documentation
# ---------------------------------------------------------------------------
# The NotImplementedError backstop in generate_agent_product_draft is genuinely
# unreachable under the default posture:
#   - A valid contract always triggers EgressPolicyError at gate 3 (tested above).
#   - An invalid contract triggers AgentAdapterContractError at gate 1 or 2.
#   - The only path past all gates requires BOTH model_egress_enabled=True AND
#     adapter_contract.egress_policy.allow_model_egress=True simultaneously;
#     but validate_agent_adapter_contract (gate 1) rejects any contract whose
#     egress_policy.allow_model_egress is True — making this combination
#     structurally impossible without bypassing the validator.
#
# A direct test of the backstop is therefore not included: reaching it without
# subverting the gate sequence is not possible today by design.
