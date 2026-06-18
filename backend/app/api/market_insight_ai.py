from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request

from app.api.market_route_auth import (
    _analyst_insight_auth_policy_error_response,
    _route_level_operator_identity,
)
from app.services.layer3_sec_xbrl_in_app_auth_policy import SecXbrlInAppAuthPolicyError
from app.services.market_insight_ai import MarketInsight, process_market_insights

router = APIRouter(prefix="/market-pipeline/insights", tags=["market-pipeline"])
alias_router = APIRouter(prefix="/analyst-insight/insights", tags=["analyst-insight"])


@router.post(
    "/process",
    response_model=list[MarketInsight],
    summary="Run heuristic market insight processor (Stage 3)",
)
def post_process_market_insights(
    request: Request,
    payload: dict[str, Any] = Body(...),
) -> list[MarketInsight]:
    """Derive trends, correlations, and emerging risks from structured pipeline output (deterministic, no LLM)."""
    try:
        _route_level_operator_identity(request, access="write")
        return process_market_insights(payload)
    except SecXbrlInAppAuthPolicyError as exc:
        return _analyst_insight_auth_policy_error_response(exc)


alias_router.add_api_route(
    "/process",
    post_process_market_insights,
    methods=["POST"],
    response_model=list[MarketInsight],
    summary="Run heuristic analyst insight processor (Stage 3)",
    name="analyst_insight_process",
)
