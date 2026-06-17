"""Gated Agent Runtime v0, strict local-only, FAILS CLOSED.

No model/network calls; no agent runtime exists.  The model-invocation step is
intentionally absent — reaching it requires a future enabled egress posture AND
an implementation that does not exist.

Lane 19 / Sublayer 3C, Handoff Lane 19.

Gate sequence (fail-closed order):
  1. validate_agent_adapter_contract     — rejects invalid/non-draft/allowing contracts
  2. assert_adapter_egress_denied_by_default — proves bound policy denies (with flag=True)
  3. assert_executor_egress_allowed      — THE FAIL-CLOSED GATE: raises EgressPolicyError
                                          (model_egress_not_permitted, 403) by default

Under the strict local-only posture:
  - settings.layer3_model_egress_enabled defaults to False
  - No EgressPolicy factory constructs an allowing policy
  - Gate 3 always raises; no model is ever invoked; no product is ever created
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Schema identity
# ---------------------------------------------------------------------------

AGENT_RUNTIME_SCHEMA_ID = "layer3.agent_product_runtime.v1"


# ---------------------------------------------------------------------------
# Gate function
# ---------------------------------------------------------------------------


def assert_agent_generation_admissible(
    adapter_contract,
    *,
    model_egress_enabled: bool | None = None,
) -> None:
    """Assert the full gate sequence; raises on any failure (fail-closed).

    Gate sequence
    -------------
    1. ``validate_agent_adapter_contract(adapter_contract)``
       Raises ``AgentAdapterContractError`` if the contract is invalid, non-draft,
       or carries an allowing egress policy.

    2. ``assert_adapter_egress_denied_by_default(adapter_contract)``
       Proves the bound policy denies egress even with the master flag on.
       Raises ``AgentAdapterContractError(egress_unexpectedly_permitted, 500)``
       if the bound policy would allow egress (invariant breach).

    3. ``assert_executor_egress_allowed(...)`` — THE FAIL-CLOSED GATE.
       Raises ``EgressPolicyError(model_egress_not_permitted, 403)`` under the
       default posture.  This is ALWAYS the terminal gate today.

    Returns None only if all gates pass.  Under the strict local-only posture
    this return path is unreachable: gate 3 always raises.

    Parameters
    ----------
    adapter_contract:
        A validated ``AgentAdapterContract`` instance (Lane 18).
    model_egress_enabled:
        Override for the settings flag.  If None, reads
        ``settings.layer3_model_egress_enabled`` (default False).
    """
    # Lazy imports — keeps the module importable without loading the full app
    # stack at import time.  No network/model/provider import anywhere.
    from app.services.layer3_agent_adapter_contract import (
        assert_adapter_egress_denied_by_default,
        validate_agent_adapter_contract,
    )
    from app.services.layer3_egress_policy import assert_executor_egress_allowed

    # Gate 1: contract structural + policy validity
    validate_agent_adapter_contract(adapter_contract)

    # Gate 2: cross-check — bound policy must deny (even with master flag on)
    assert_adapter_egress_denied_by_default(adapter_contract)

    # Gate 3: resolve the master flag, then assert egress allowed — FAILS CLOSED
    if model_egress_enabled is None:
        from app.core.config import settings  # lazy: avoids import-time side-effects
        model_egress_enabled = getattr(settings, "layer3_model_egress_enabled", False)

    # This RAISES EgressPolicyError(model_egress_not_permitted, 403) by default.
    # It is the documented, intentional fail-closed gate for Lane 19 v0.
    assert_executor_egress_allowed(
        adapter_contract.executor_type,
        policy=adapter_contract.egress_policy,
        model_egress_enabled=model_egress_enabled,
    )

    # Unreachable under the strict local-only posture (gate 3 always raises).


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def generate_agent_product_draft(
    db,
    *,
    session_id: str,
    client_request_id: str,
    working_set_id: str,
    adapter_contract,
    model_egress_enabled: bool | None = None,
):
    """Gated entry point for agent-assisted DRAFT product generation — v0.

    Fails closed under the strict local-only posture: the egress gate raises
    EgressPolicyError before any DB work, product creation, or model invocation.

    Parameters
    ----------
    db:
        SQLAlchemy Session.  Consumed by the (currently unreachable) creation
        step — not touched before the gate raises.
    session_id:
        Session identifier.  Stable forward signature; consumed by the
        (currently unreachable) working-set session-scope verification step.
    client_request_id:
        Idempotency key.  Stable forward signature; consumed by the
        (currently unreachable) product creation step.
    working_set_id:
        Working set identifier.  Stable forward signature; consumed by the
        (currently unreachable) working-set load + session-scope check.
    adapter_contract:
        A Lane-18 ``AgentAdapterContract`` describing the intended adapter
        binding.  Validated by the gate before any other work.
    model_egress_enabled:
        Optional override for ``settings.layer3_model_egress_enabled``.
        If None, the live settings value (default False) is used.

    Raises
    ------
    AgentAdapterContractError
        If the adapter contract is structurally invalid, non-draft, or carries
        an unexpectedly allowing egress policy (gates 1–2).
    EgressPolicyError(model_egress_not_permitted, 403)
        Default outcome under the strict local-only posture (gate 3).
        No DB work, no product, no model call has occurred.

    Returns
    -------
    Never returns today; gate 3 always raises under defaults.
    """
    # Gate first — before ANY db work or product creation.
    # Under the strict local-only posture this raises EgressPolicyError before
    # touching db, session_id, client_request_id, or working_set_id.
    assert_agent_generation_admissible(
        adapter_contract,
        model_egress_enabled=model_egress_enabled,
    )

    # -----------------------------------------------------------------------
    # UNREACHABLE TODAY — strict local-only posture always raises above.
    #
    # A future, posture-changed lane would implement:
    #   (a) Load and verify the working set session-scoped:
    #         working_set = db.query(L3WorkingSet).filter(
    #             L3WorkingSet.working_set_id == working_set_id,
    #             L3WorkingSet.session_id == session_id,
    #         ).one_or_none()
    #         if working_set is None:
    #             raise Layer3AnalysisProductError(
    #                 ..., error_code="working_set_not_found", http_status=404
    #             )
    #
    #   (b) Invoke the model adapter UNDER POLICY using adapter_contract
    #       (adapter_id, provider, model_identity, prompt_spec_hash,
    #        egress_policy binding, trust_policy) — only after egress is
    #       explicitly permitted by a changed posture AND an implementation exists.
    #
    #   (c) Build a DRAFT-ONLY product (executor_type from the contract,
    #       e.g. "agent") with full adapter provenance and draft_only=True,
    #       client_request_id for idempotency, requiring review for package
    #       eligibility and never auto-accepted.
    #
    # The db/session_id/client_request_id/working_set_id params are the stable
    # forward signature; they are consumed only by this unreachable step.
    #
    # There is NO network/model/provider import or call anywhere in this module.
    # -----------------------------------------------------------------------

    raise NotImplementedError(
        "agent model invocation is not implemented; "
        "the gated runtime fails closed under the strict local-only egress posture"
    )
