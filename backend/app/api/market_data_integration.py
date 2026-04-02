from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.market_data_integration import build_integrated_dataset

router = APIRouter(prefix="/market-pipeline/integration", tags=["market-pipeline"])


class CrossReferenceRequest(BaseModel):
    sources: dict[str, list[dict[str, Any]]] = Field(
        ...,
        description="Named lists of record dicts (e.g. manifests, bond activity, regulatory rows).",
    )
    link_keys: list[str] = Field(
        ...,
        min_length=1,
        description="Field names to join on (e.g. date, entity_id, region).",
    )


class CrossReferenceGroupResponse(BaseModel):
    key: dict[str, Any]
    records_by_source: dict[str, list[dict[str, Any]]]


class IntegratedDatasetResponse(BaseModel):
    link_keys: list[str]
    source_record_counts: dict[str, int]
    cross_references: list[CrossReferenceGroupResponse]


@router.post("/cross-reference", response_model=IntegratedDatasetResponse)
def cross_reference(body: CrossReferenceRequest) -> IntegratedDatasetResponse:
    raw = build_integrated_dataset(body.sources, body.link_keys)
    return IntegratedDatasetResponse(
        link_keys=raw["link_keys"],
        source_record_counts=raw["source_record_counts"],
        cross_references=[
            CrossReferenceGroupResponse(
                key=g["key"],
                records_by_source=g["records_by_source"],
            )
            for g in raw["cross_references"]
        ],
    )
