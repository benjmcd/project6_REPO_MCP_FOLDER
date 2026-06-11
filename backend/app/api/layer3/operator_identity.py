from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.layer3 import router
from app.api.layer3._shared import (  # noqa: F401
    SecXbrlInAppAuthPolicyError,
    _route_level_operator_identity,
    _sec_xbrl_auth_policy_error_response,
)

# ---------------------------------------------------------------------------
# GET /review/layer3/operator/identity
#
# Read-only projection of the server-derived operator principal.  Never echoes
# raw header values beyond what the policy already derives.  Fail-closed
# semantics are identical to all other read routes: the _route_level_operator_identity
# helper raises SecXbrlInAppAuthPolicyError which is turned into the canonical
# error JSON by _sec_xbrl_auth_policy_error_response.
# ---------------------------------------------------------------------------

_OPERATOR_IDENTITY_PROJECTION_SCHEMA_ID = (
    "layer3.operator_identity_projection.v1"
)


@router.get("/operator/identity", response_model=None)
def get_operator_identity(request: Request) -> dict[str, Any] | JSONResponse:
    """Return the server-derived operator principal as a read-only projection.

    Error responses follow the same contract as all other layer3 read routes:
    - AUTH_OWNER=proxy, TRUSTED_PROXY_MODE=false  -> 409
    - proxy+trusted, missing identity header        -> 401
    - proxy+trusted, missing workspace header       -> 401
    - role_enforcing, missing roles header          -> 401
    - role_enforcing, insufficient role             -> 403
    """
    try:
        auth_result = _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)

    return {
        "schema_id": _OPERATOR_IDENTITY_PROJECTION_SCHEMA_ID,
        "operator_ref_hash": auth_result.get("operator_ref_hash"),
        "workspace_ref_hash": auth_result.get("workspace_ref_hash"),
        "auth_owner_mode": auth_result.get("auth_owner_mode"),
        "derived_role": auth_result.get("role"),
        "authorization_mode": auth_result.get("authorization_mode"),
        "auth_owner": settings.auth_owner,
        "trusted_proxy_mode": settings.trusted_proxy_mode,
        "deployment_mode": settings.deployment_mode,
    }
