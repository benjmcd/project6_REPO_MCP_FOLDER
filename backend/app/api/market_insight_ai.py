from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from app.services.market_insight_ai import MarketInsight, process_market_insights

router = APIRouter(prefix="/market-pipeline/insights", tags=["market-pipeline"])
alias_router = APIRouter(prefix="/analyst-insight/insights", tags=["analyst-insight"])


@router.post(
    "/process",
    response_model=list[MarketInsight],
    summary="Run heuristic market insight processor (Stage 3)",
)
def post_process_market_insights(
    payload: dict[str, Any] = Body(...),
) -> list[MarketInsight]:
    """Derive trends, correlations, and emerging risks from structured pipeline output (deterministic, no LLM)."""
    return process_market_insights(payload)


alias_router.add_api_route(
    "/process",
    post_process_market_insights,
    methods=["POST"],
    response_model=list[MarketInsight],
    summary="Run heuristic analyst insight processor (Stage 3)",
    name="analyst_insight_process",
)
