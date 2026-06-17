"""Layer 3 / Sublayer 3C agent adapter contract — Lane 18 (handoff to Lane 19).

CONTRACT-ONLY module: frozen declaration + fail-closed validator.

NO runtime, NO model/network calls, NO migration, NO wiring into
authoring/generation (that is Lane 19).

A valid v0 contract:
  - is draft-only (``draft_only`` MUST be True),
  - binds a default-deny EgressPolicy (``allow_model_egress`` MUST be False),
  - carries only the SHA-256 hash of the prompt/spec (raw text NEVER stored),
  - admits only ``trust_policy="draft_only_review_required"``.

Lane 19 will consume this contract to gate a runtime.  Lane 18 adds NO runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.layer3_egress_policy import (
    EgressPolicy,
    evaluate_executor_egress,
)
from app.services.layer3_utils import stable_hash


# ---------------------------------------------------------------------------
# Schema identity
# ---------------------------------------------------------------------------

AGENT_ADAPTER_SCHEMA_ID = "layer3.agent_adapter_contract.v1"


# ---------------------------------------------------------------------------
# Allowed sets (v0)
# ---------------------------------------------------------------------------

# The contract applies to model executor types only.
ALLOWED_ADAPTER_EXECUTOR_TYPES: frozenset[str] = frozenset({"agent", "external_api"})

# v0 admits only this trust posture.
ALLOWED_TRUST_POLICIES: frozenset[str] = frozenset({"draft_only_review_required"})

# Regex for a valid 64-char lowercase hex string (SHA-256 digest).
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class AgentAdapterContractError(ValueError):
    """Raised when the adapter contract fails validation (fail-closed).

    Mirrors the shape of ``Layer3AnalysisProductError`` / ``EgressPolicyError``
    so callers can handle all Layer-3 error types uniformly.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status

    def response_body(self) -> dict:
        return {
            "schema_id": AGENT_ADAPTER_SCHEMA_ID,
            "error_code": self.error_code,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Contract dataclass (frozen declaration)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentAdapterContract:
    """Frozen declaration of a future model/agent method binding.

    Fields
    ------
    adapter_id:
        Unique identifier for this adapter declaration.
    adapter_version:
        Monotonically increasing integer version, >= 1.
    executor_type:
        Must be in ``ALLOWED_ADAPTER_EXECUTOR_TYPES`` (agent, external_api).
    provider:
        Identity string for the model provider, e.g. ``"example_provider"``.
        NEVER used to make a network call in this module.
    model_identity:
        Model identity string, e.g. ``"example-model-v1"``.
        Identity only — NEVER used to make a call.
    prompt_spec_hash:
        64-character lowercase hex SHA-256 hash of the prompt/spec dict.
        The raw prompt/spec text is NEVER stored in the contract or its
        provenance — only this hash travels with the declaration.
    input_schema_id:
        Schema ID describing the adapter's input envelope.
    output_schema_id:
        Schema ID describing the adapter's output envelope.
    egress_policy:
        Bound Lane-17 EgressPolicy.  MUST have ``allow_model_egress=False``
        in v0 — no opt-in path exists yet.
    trust_policy:
        Must be ``"draft_only_review_required"`` in v0.
    draft_only:
        MUST be True in v0.  A non-draft adapter is rejected by the validator.
    """

    adapter_id: str
    adapter_version: int
    executor_type: str
    provider: str
    model_identity: str
    prompt_spec_hash: str
    input_schema_id: str
    output_schema_id: str
    egress_policy: EgressPolicy
    trust_policy: str
    draft_only: bool = True


# ---------------------------------------------------------------------------
# Prompt-spec hashing helper
# ---------------------------------------------------------------------------


def compute_prompt_spec_hash(prompt_spec: dict) -> str:
    """Return the SHA-256 hex digest of *prompt_spec*.

    The raw prompt/spec is never persisted in the contract or its provenance.
    Only the returned hash should be stored in ``AgentAdapterContract.prompt_spec_hash``.
    """
    return stable_hash(prompt_spec)


# ---------------------------------------------------------------------------
# Validator (fail-closed)
# ---------------------------------------------------------------------------


def validate_agent_adapter_contract(contract: AgentAdapterContract) -> None:
    """Validate *contract* against the v0 rules; raise ``AgentAdapterContractError`` on any failure.

    All checks are fail-closed: the first violation raises immediately.
    Error messages name only the field/reason — no raw prompt text or data
    is ever included in an error message.

    Checks (in order)
    -----------------
    1. adapter_id — non-empty str.
    2. adapter_version — int >= 1.
    3. executor_type — must be in ALLOWED_ADAPTER_EXECUTOR_TYPES.
    4. provider, model_identity, input_schema_id, output_schema_id — non-empty str.
    5. prompt_spec_hash — 64-char lowercase hex string.
    6. trust_policy — must be in ALLOWED_TRUST_POLICIES.
    7. draft_only — must be True.
    8. egress_policy — must be an EgressPolicy instance with allow_model_egress is False.
    """
    # 1. adapter_id
    if not isinstance(contract.adapter_id, str) or not contract.adapter_id:
        raise AgentAdapterContractError(
            "adapter_id must be a non-empty string.",
            error_code="invalid_adapter_id",
        )

    # 2. adapter_version — reject bool explicitly (bool is a subclass of int,
    #    so True would otherwise satisfy `>= 1`).
    if (
        isinstance(contract.adapter_version, bool)
        or not isinstance(contract.adapter_version, int)
        or contract.adapter_version < 1
    ):
        raise AgentAdapterContractError(
            "adapter_version must be an integer >= 1.",
            error_code="invalid_adapter_version",
        )

    # 3. executor_type — type-guard before membership so a non-string (e.g. an
    #    unhashable list/dict from malformed input) fails closed as a contract
    #    error rather than a raw TypeError.
    if (
        not isinstance(contract.executor_type, str)
        or contract.executor_type not in ALLOWED_ADAPTER_EXECUTOR_TYPES
    ):
        raise AgentAdapterContractError(
            f"executor_type '{contract.executor_type}' is not allowed; "
            f"must be one of {sorted(ALLOWED_ADAPTER_EXECUTOR_TYPES)}.",
            error_code="invalid_executor_type",
        )

    # 4. Required non-empty string fields
    for field_name in ("provider", "model_identity", "input_schema_id", "output_schema_id"):
        value = getattr(contract, field_name)
        if not isinstance(value, str) or not value:
            raise AgentAdapterContractError(
                f"{field_name} must be a non-empty string.",
                error_code="missing_required_field",
            )

    # 5. prompt_spec_hash — must be a 64-char lowercase hex string
    if not isinstance(contract.prompt_spec_hash, str) or not _HEX64_RE.match(contract.prompt_spec_hash):
        raise AgentAdapterContractError(
            "prompt_spec_hash must be a 64-character lowercase hex string (SHA-256 digest).",
            error_code="invalid_prompt_spec_hash",
        )

    # 6. trust_policy — type-guard before membership (fail closed on non-string).
    if (
        not isinstance(contract.trust_policy, str)
        or contract.trust_policy not in ALLOWED_TRUST_POLICIES
    ):
        raise AgentAdapterContractError(
            f"trust_policy '{contract.trust_policy}' is not supported in v0; "
            f"must be one of {sorted(ALLOWED_TRUST_POLICIES)}.",
            error_code="unsupported_trust_policy",
        )

    # 7. draft_only must be True
    if contract.draft_only is not True:
        raise AgentAdapterContractError(
            "draft_only must be True in v0; non-draft adapters are not permitted.",
            error_code="draft_only_required",
        )

    # 8. egress_policy — must be an EgressPolicy with allow_model_egress is False
    if not isinstance(contract.egress_policy, EgressPolicy):
        raise AgentAdapterContractError(
            "egress_policy must be an EgressPolicy instance.",
            error_code="egress_not_permitted_by_default",
        )
    if contract.egress_policy.allow_model_egress is not False:
        raise AgentAdapterContractError(
            "egress_policy.allow_model_egress must be False in v0; "
            "no opt-in egress path exists yet.",
            error_code="egress_not_permitted_by_default",
        )


# ---------------------------------------------------------------------------
# Cross-check: egress denied by default (binds Lane 17)
# ---------------------------------------------------------------------------


def assert_adapter_egress_denied_by_default(
    contract: AgentAdapterContract,
    *,
    model_egress_enabled: bool = True,
) -> None:
    """Cross-check with Lane 17: assert that this contract's BOUND POLICY denies egress.

    Calls ``evaluate_executor_egress`` (Lane 17) with the contract's
    ``executor_type`` and ``egress_policy``.  The default is
    ``model_egress_enabled=True`` ON PURPOSE: with the master flag off, Lane 17
    denies every model executor before the bound policy is even consulted, so the
    proof would be vacuous (it would "pass" even for a contract carrying an
    allowing policy).  Forcing the flag on isolates the bound policy as the sole
    remaining gate, so a pass genuinely proves ``egress_policy.allow_model_egress``
    is False.

    For a valid v0 contract the decision MUST be denied (``allowed is False``).
    If it is unexpectedly allowed — impossible for a contract that passed
    ``validate_agent_adapter_contract`` (which rejects any allowing policy) —
    raises ``AgentAdapterContractError`` with
    ``error_code="egress_unexpectedly_permitted"`` and ``http_status=500``.

    Callers SHOULD ``validate_agent_adapter_contract`` first; this is the
    independent runtime cross-check Lane 19 uses.
    """
    decision = evaluate_executor_egress(
        contract.executor_type,
        policy=contract.egress_policy,
        model_egress_enabled=model_egress_enabled,
    )
    if decision.allowed is True:
        raise AgentAdapterContractError(
            f"Egress unexpectedly permitted for executor_type '{contract.executor_type}'; "
            "this is an internal invariant violation for a v0 adapter contract.",
            error_code="egress_unexpectedly_permitted",
            http_status=500,
        )
