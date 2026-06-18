from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    SecXbrlInAppAuthPolicyError,
    route_level_operator_authorization_required,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response

# ---------------------------------------------------------------------------
# Shared auth helpers for the market-pipeline / analyst-insight compute routes.
# Same operator-identity seam used by router.py and review_nrc_aps.py, kept in
# the api layer (not services) because it builds Request/JSONResponse envelopes.
#
# The function name _route_level_operator_identity is load-bearing: both the
# pre-body enumeration guard (main._operator_authorization_access_from_endpoint)
# and the AST drift guard detect a route's write gate by that literal call name
# in the handler source. Callers must keep calling it by that name.
# ---------------------------------------------------------------------------


def _route_level_operator_identity(request: Request, *, access: str = "write") -> None:
    """Gate: raises SecXbrlInAppAuthPolicyError if operator identity is not admitted."""
    route_level_operator_authorization_required(
        {str(k): str(v) for k, v in request.headers.items()},
        access=access,
    )


def _analyst_insight_auth_policy_error_response(exc: SecXbrlInAppAuthPolicyError) -> JSONResponse:
    """Return a governed error envelope matching the layer3 workbench error shape."""
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(f)
                    for f in exc.details.get(
                        "blocked_fields",
                        exc.details.get("mismatched_fields", []),
                    )
                ],
                next_allowed_actions=["inspect_operator_identity_projection"],
            )
        ),
    )
