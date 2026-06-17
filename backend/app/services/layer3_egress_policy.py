"""Layer 3 / Sublayer 3C egress policy authority — Lane 17.

Default-DENY posture: all 3C working-set data is classified local_only, and any
model/agent executor type requires an EXPLICIT policy object AND the
LAYER3_MODEL_EGRESS_ENABLED settings flag to be True.  Neither condition can be
satisfied today — no factory constructs an allowing EgressPolicy, and the flag
defaults False.  This module is the documented seam where Lane 18/19 will
introduce per-session policy construction and opt-in model egress.

IMPORTANT: holding package/delivery authority NEVER implies egress authority.
See ``package_authority_grants_egress()`` for the explicit tested invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Schema identity
# ---------------------------------------------------------------------------

EGRESS_POLICY_SCHEMA_ID = "layer3.egress_policy.v1"


# ---------------------------------------------------------------------------
# Data-sensitivity model
# ---------------------------------------------------------------------------

DATA_SENSITIVITY_VALUES = ("local_only", "externally_shareable")

# Conservative default: 3C working-set data is treated as local_only.
# No current mechanism exists to downgrade this classification.
DEFAULT_DATA_SENSITIVITY = "local_only"


def default_data_sensitivity() -> str:
    """Return the default data sensitivity classification for 3C working-set data.

    The default is ``local_only``.  No current mechanism downgrades it —
    conservative posture is intentional.  Lane 18/19 may introduce an explicit
    downgrade path when external sharing is warranted, but that is out of scope
    for Lane 17.
    """
    return DEFAULT_DATA_SENSITIVITY


# ---------------------------------------------------------------------------
# Executor classification
# ---------------------------------------------------------------------------

# Local executor types: execution stays on-process, no model/provider involvement.
LOCAL_EXECUTOR_TYPES: frozenset[str] = frozenset({"human", "deterministic"})

# Model executor types: imply model/provider involvement and potential egress.
# These are BLOCKED by default; an explicit EgressPolicy + settings flag are
# required (neither is constructible until Lane 18/19).
MODEL_EXECUTOR_TYPES: frozenset[str] = frozenset({"agent", "external_api"})


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class EgressPolicyError(ValueError):
    """Raised when an egress assertion fails (fail-closed).

    Mirrors the shape of ``Layer3AnalysisProductError`` so callers can handle
    both error types uniformly.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        http_status: int = 403,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status

    def response_body(self) -> dict:
        return {
            "schema_id": EGRESS_POLICY_SCHEMA_ID,
            "error_code": self.error_code,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Opt-in policy seam (documented, default-off, UNCONSTRUCTED until Lane 18/19)
# ---------------------------------------------------------------------------
# Lane 18/19 will introduce an explicit, per-session construction path for
# EgressPolicy.  Until then, no factory or route builds an allowing policy;
# every caller passes ``policy=None`` (the default), and all model executor
# types are denied.  Both ``allow_model_egress=True`` on the policy object AND
# ``model_egress_enabled=True`` on the settings flag must hold simultaneously
# before egress is permitted.  Today neither condition is reachable.


@dataclass(frozen=True)
class EgressPolicy:
    """Explicit opt-in egress policy object.

    Default-off.  Must be constructed by an authorized Lane 18/19 factory (which
    does not exist yet).  Even a non-None policy with ``allow_model_egress=True``
    is denied unless the ``LAYER3_MODEL_EGRESS_ENABLED`` settings flag is also
    True.
    """

    allow_model_egress: bool = False
    egress_targets: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Decision type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EgressDecision:
    """Immutable result of an egress evaluation."""

    allowed: bool
    reason: str
    executor_type: str
    data_sensitivity: str
    schema_id: str = EGRESS_POLICY_SCHEMA_ID


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------


def evaluate_executor_egress(
    executor_type: str,
    *,
    policy: EgressPolicy | None = None,
    model_egress_enabled: bool = False,
) -> EgressDecision:
    """Evaluate whether ``executor_type`` is permitted to proceed.

    Decision matrix
    ---------------
    - LOCAL_EXECUTOR_TYPES (human, deterministic):
        Always allowed — execution is local, no egress implied.
        reason: "local_execution_no_egress"

    - MODEL_EXECUTOR_TYPES (agent, external_api):
        Allowed ONLY when ALL of the following hold simultaneously:
          1. ``model_egress_enabled is True``   (settings flag, default False)
          2. ``policy is not None``              (explicit policy object provided)
          3. ``policy.allow_model_egress is True``
        This combination is unreachable today: no caller provides an allowing
        policy and the settings flag defaults off.
        reason on deny: "model_egress_requires_explicit_policy"

    - Unknown executor types:
        Always denied — fail-closed.
        reason: "unknown_executor_type"

    Data sensitivity is always ``default_data_sensitivity()`` (conservative).
    """
    if executor_type in LOCAL_EXECUTOR_TYPES:
        return EgressDecision(
            allowed=True,
            reason="local_execution_no_egress",
            executor_type=executor_type,
            data_sensitivity=default_data_sensitivity(),
        )

    if executor_type in MODEL_EXECUTOR_TYPES:
        egress_permitted = (
            model_egress_enabled is True
            and policy is not None
            and policy.allow_model_egress is True
        )
        return EgressDecision(
            allowed=egress_permitted,
            reason=(
                "model_egress_explicitly_permitted"
                if egress_permitted
                else "model_egress_requires_explicit_policy"
            ),
            executor_type=executor_type,
            data_sensitivity=default_data_sensitivity(),
        )

    # Unknown executor type — fail closed.
    return EgressDecision(
        allowed=False,
        reason="unknown_executor_type",
        executor_type=executor_type,
        data_sensitivity=default_data_sensitivity(),
    )


def assert_executor_egress_allowed(
    executor_type: str,
    *,
    policy: EgressPolicy | None = None,
    model_egress_enabled: bool = False,
) -> EgressDecision:
    """Assert that egress is permitted for ``executor_type``; raise on denial.

    Raises ``EgressPolicyError`` with ``error_code="model_egress_not_permitted"``
    and ``http_status=403`` if the decision is denied.  The error message names
    only the executor_type and denial reason — no data or session references are
    included.

    Returns the ``EgressDecision`` on success (allowed=True).
    """
    decision = evaluate_executor_egress(
        executor_type,
        policy=policy,
        model_egress_enabled=model_egress_enabled,
    )
    if not decision.allowed:
        # Bound the echoed executor_type defensively: it is server-set today, but
        # the public response_body must never carry an unbounded/untrusted value.
        safe_executor_type = str(executor_type)[:64]
        raise EgressPolicyError(
            f"Egress denied for executor_type '{safe_executor_type}': {decision.reason}.",
            error_code="model_egress_not_permitted",
            http_status=403,
        )
    return decision


# ---------------------------------------------------------------------------
# Package authority invariant
# ---------------------------------------------------------------------------


def package_authority_grants_egress() -> bool:
    """Return False — holding package/delivery authority NEVER implies egress authority.

    Lane 17 establishes an explicit separation between the right to package and
    deliver analysis products (which may remain local) and the right to transmit
    data to an external model or provider (which requires an independent, explicit
    egress policy).  This function is an executable, tested invariant documenting
    that separation.  Lane 18/19 may introduce a separate egress-grant path, but
    that path will be independent of package authority.
    """
    return False
