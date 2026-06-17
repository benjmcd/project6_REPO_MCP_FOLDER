"""Tests for layer3_agent_adapter_contract — Lane 18 Agent Adapter Contract v0.

Covers:
- Valid contract passes validate_agent_adapter_contract (no raise).
- assert_adapter_egress_denied_by_default passes for a valid contract.
- Each rejection path: empty adapter_id, adapter_version < 1, invalid executor_type,
  empty required string fields, bad prompt_spec_hash variants, unsupported
  trust_policy, draft_only=False, allowing egress_policy.
- compute_prompt_spec_hash is deterministic and produces a 64-char hex digest
  that does not contain the raw prompt text.
- AgentAdapterContract is a frozen dataclass (FrozenInstanceError on assignment).
- AgentAdapterContractError.response_body() shape.
- assert_adapter_egress_denied_by_default with model_egress_enabled=True but a
  default-deny egress_policy still denies (policy gate wins).
"""

from __future__ import annotations

import os
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.layer3_agent_adapter_contract import (
    AGENT_ADAPTER_SCHEMA_ID,
    ALLOWED_ADAPTER_EXECUTOR_TYPES,
    ALLOWED_TRUST_POLICIES,
    AgentAdapterContract,
    AgentAdapterContractError,
    assert_adapter_egress_denied_by_default,
    compute_prompt_spec_hash,
    validate_agent_adapter_contract,
)
from app.services.layer3_egress_policy import EgressPolicy


# ---------------------------------------------------------------------------
# Helper: build a valid contract
# ---------------------------------------------------------------------------

_VALID_PROMPT_SPEC = {"prompt": "Summarise the working-set findings."}
_VALID_HASH = compute_prompt_spec_hash(_VALID_PROMPT_SPEC)


def _valid_contract(**overrides) -> AgentAdapterContract:
    """Return a fully valid v0 AgentAdapterContract.

    Any keyword argument overrides a field value to exercise rejection paths.
    """
    defaults = dict(
        adapter_id="adapter-test-001",
        adapter_version=1,
        executor_type="agent",
        provider="example_provider",
        model_identity="example-model-v1",
        prompt_spec_hash=_VALID_HASH,
        input_schema_id="layer3.adapter.input.v1",
        output_schema_id="layer3.adapter.output.v1",
        egress_policy=EgressPolicy(),
        trust_policy="draft_only_review_required",
        draft_only=True,
    )
    defaults.update(overrides)
    return AgentAdapterContract(**defaults)


# ---------------------------------------------------------------------------
# Valid contract — happy path
# ---------------------------------------------------------------------------


def test_valid_contract_passes_validate() -> None:
    contract = _valid_contract()
    validate_agent_adapter_contract(contract)  # must not raise


def test_valid_contract_egress_denied_by_default() -> None:
    contract = _valid_contract()
    # Must not raise — egress is denied for a valid v0 contract.
    assert_adapter_egress_denied_by_default(contract)


def test_valid_contract_egress_denied_with_flag_true() -> None:
    """model_egress_enabled=True but policy.allow_model_egress=False => still denied."""
    contract = _valid_contract()
    assert_adapter_egress_denied_by_default(contract, model_egress_enabled=True)


# ---------------------------------------------------------------------------
# adapter_id rejections
# ---------------------------------------------------------------------------


def test_empty_adapter_id_raises() -> None:
    contract = _valid_contract(adapter_id="")
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "invalid_adapter_id"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# adapter_version rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_version", [0, -1, -99])
def test_adapter_version_below_one_raises(bad_version: int) -> None:
    contract = _valid_contract(adapter_version=bad_version)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "invalid_adapter_version"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# executor_type rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_type", ["deterministic", "human", "bogus", "", "llm"])
def test_invalid_executor_type_raises(bad_type: str) -> None:
    contract = _valid_contract(executor_type=bad_type)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "invalid_executor_type"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# Required non-empty string fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    ["provider", "model_identity", "input_schema_id", "output_schema_id"],
)
def test_empty_required_field_raises(field_name: str) -> None:
    contract = _valid_contract(**{field_name: ""})
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "missing_required_field"
    assert field_name in exc_info.value.message
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# prompt_spec_hash rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_hash",
    [
        "abc123",                              # too short
        "Z" * 64,                              # non-hex character (uppercase invalid)
        "A" * 64,                              # uppercase hex — rejected (must be lowercase)
        "g" * 64,                              # non-hex character
        "",                                    # empty
        "a" * 63,                              # one char too short
        "a" * 65,                              # one char too long
        "ABCDEF1234567890" * 4,                # uppercase 64-char — still invalid
    ],
)
def test_invalid_prompt_spec_hash_raises(bad_hash: str) -> None:
    contract = _valid_contract(prompt_spec_hash=bad_hash)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "invalid_prompt_spec_hash"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# trust_policy rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_policy", ["anything_goes", "open", "draft", "", "review_not_required"])
def test_unsupported_trust_policy_raises(bad_policy: str) -> None:
    contract = _valid_contract(trust_policy=bad_policy)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "unsupported_trust_policy"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# draft_only=False rejection
# ---------------------------------------------------------------------------


def test_draft_only_false_raises() -> None:
    contract = _valid_contract(draft_only=False)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "draft_only_required"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# egress_policy with allow_model_egress=True rejection
# ---------------------------------------------------------------------------


def test_allowing_egress_policy_raises() -> None:
    contract = _valid_contract(egress_policy=EgressPolicy(allow_model_egress=True))
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "egress_not_permitted_by_default"
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# compute_prompt_spec_hash — determinism and hash properties
# ---------------------------------------------------------------------------


def test_compute_prompt_spec_hash_is_deterministic() -> None:
    spec = {"prompt": "Test prompt.", "version": 1}
    h1 = compute_prompt_spec_hash(spec)
    h2 = compute_prompt_spec_hash(spec)
    assert h1 == h2


def test_compute_prompt_spec_hash_different_specs_differ() -> None:
    h1 = compute_prompt_spec_hash({"prompt": "Prompt A"})
    h2 = compute_prompt_spec_hash({"prompt": "Prompt B"})
    assert h1 != h2


def test_compute_prompt_spec_hash_is_64_char_lowercase_hex() -> None:
    h = compute_prompt_spec_hash({"prompt": "Any prompt text."})
    assert len(h) == 64
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_prompt_spec_hash_does_not_contain_raw_prompt() -> None:
    raw = "Summarise the working-set findings."
    h = compute_prompt_spec_hash({"prompt": raw})
    assert raw not in h


# ---------------------------------------------------------------------------
# Frozen dataclass invariant
# ---------------------------------------------------------------------------


def test_contract_is_frozen() -> None:
    contract = _valid_contract()
    with pytest.raises(FrozenInstanceError):
        contract.adapter_id = "mutated"  # type: ignore[misc]


def test_contract_frozen_on_egress_policy() -> None:
    contract = _valid_contract()
    with pytest.raises(FrozenInstanceError):
        contract.egress_policy = EgressPolicy(allow_model_egress=True)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AgentAdapterContractError.response_body() shape
# ---------------------------------------------------------------------------


def test_error_response_body_shape() -> None:
    err = AgentAdapterContractError(
        "test message",
        error_code="invalid_adapter_id",
        http_status=400,
    )
    body = err.response_body()
    assert body["schema_id"] == AGENT_ADAPTER_SCHEMA_ID
    assert body["error_code"] == "invalid_adapter_id"
    assert body["message"] == "test message"


def test_error_response_body_default_http_status() -> None:
    err = AgentAdapterContractError("msg", error_code="draft_only_required")
    assert err.http_status == 400


def test_error_response_body_custom_http_status() -> None:
    err = AgentAdapterContractError(
        "invariant breach",
        error_code="egress_unexpectedly_permitted",
        http_status=500,
    )
    assert err.http_status == 500
    body = err.response_body()
    assert body["error_code"] == "egress_unexpectedly_permitted"


# ---------------------------------------------------------------------------
# assert_adapter_egress_denied_by_default — explicit egress check
# ---------------------------------------------------------------------------


def test_assert_egress_denied_with_default_policy() -> None:
    """Default EgressPolicy (allow_model_egress=False) always denies model executors."""
    for executor_type in ALLOWED_ADAPTER_EXECUTOR_TYPES:
        contract = _valid_contract(executor_type=executor_type)
        # Must not raise.
        assert_adapter_egress_denied_by_default(contract)


def test_assert_egress_denied_model_egress_enabled_flag_true_policy_deny() -> None:
    """Flag=True but policy.allow_model_egress=False => denied (policy gate wins)."""
    contract = _valid_contract(egress_policy=EgressPolicy(allow_model_egress=False))
    # Must not raise — the deny policy overrides the flag.
    assert_adapter_egress_denied_by_default(contract, model_egress_enabled=True)


def test_assert_egress_cross_check_catches_allowing_policy() -> None:
    """The cross-check is MEANINGFUL: it defaults the flag on, so a contract whose
    bound policy allows egress is caught (egress_unexpectedly_permitted) rather
    than silently passing because the master flag was off."""
    bad = _valid_contract(egress_policy=EgressPolicy(allow_model_egress=True))
    with pytest.raises(AgentAdapterContractError) as exc_info:
        assert_adapter_egress_denied_by_default(bad)  # default flag is now True
    assert exc_info.value.error_code == "egress_unexpectedly_permitted"
    assert exc_info.value.http_status == 500


# ---------------------------------------------------------------------------
# Type-guard rejections (fail-closed on malformed / non-canonical inputs)
# ---------------------------------------------------------------------------


def test_adapter_version_bool_rejected() -> None:
    """adapter_version=True must be rejected (bool is a subclass of int)."""
    contract = _valid_contract(adapter_version=True)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "invalid_adapter_version"


@pytest.mark.parametrize("bad_executor", [["agent"], {"t": "agent"}, 123, None])
def test_non_string_executor_type_fails_closed(bad_executor) -> None:
    """A non-string executor_type fails closed as a contract error, not a TypeError."""
    contract = _valid_contract(executor_type=bad_executor)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "invalid_executor_type"


@pytest.mark.parametrize("bad_policy", [["draft_only_review_required"], {"x": 1}, 7, None])
def test_non_string_trust_policy_fails_closed(bad_policy) -> None:
    """A non-string trust_policy fails closed as a contract error, not a TypeError."""
    contract = _valid_contract(trust_policy=bad_policy)
    with pytest.raises(AgentAdapterContractError) as exc_info:
        validate_agent_adapter_contract(contract)
    assert exc_info.value.error_code == "unsupported_trust_policy"


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


def test_allowed_adapter_executor_types_are_model_types() -> None:
    assert ALLOWED_ADAPTER_EXECUTOR_TYPES == frozenset({"agent", "external_api"})


def test_allowed_trust_policies_v0() -> None:
    assert ALLOWED_TRUST_POLICIES == frozenset({"draft_only_review_required"})


def test_agent_adapter_schema_id() -> None:
    assert AGENT_ADAPTER_SCHEMA_ID == "layer3.agent_adapter_contract.v1"


# ---------------------------------------------------------------------------
# external_api executor type also works
# ---------------------------------------------------------------------------


def test_valid_contract_external_api_executor() -> None:
    contract = _valid_contract(executor_type="external_api")
    validate_agent_adapter_contract(contract)
    assert_adapter_egress_denied_by_default(contract)
