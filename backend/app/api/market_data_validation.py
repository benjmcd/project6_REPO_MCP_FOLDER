from __future__ import annotations

from typing import Any, Literal, Union

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.market_data_validation import validate_market_rows

router = APIRouter(prefix="/market-pipeline/validation", tags=["market_data_validation"])
alias_router = APIRouter(prefix="/analyst-insight/validation", tags=["analyst-insight"])


class MarketDataValidationOptions(BaseModel):
    required_fields: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)
    outlier_method: Literal["zscore", "iqr", "none"] = "zscore"
    zscore_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    normalize_columns: list[str] = Field(default_factory=list)
    check_key_consistency: bool = True


class MarketDataValidationRunRequest(BaseModel):
    rows: list[dict[str, Any]]
    options: MarketDataValidationOptions = Field(default_factory=MarketDataValidationOptions)


class MissingFieldIssue(BaseModel):
    row_index: int
    missing_fields: list[str]


class KeyConsistencyCheckedResponse(BaseModel):
    consistent: bool
    union_keys: list[str]
    inconsistent_row_indices: list[int]


class KeyConsistencyEmptyResponse(BaseModel):
    consistent: bool
    key_sets: list[Any]


class KeyConsistencySkippedResponse(BaseModel):
    consistent: bool
    skipped: bool


class NumericColumnStats(BaseModel):
    count: int
    min: float
    max: float
    mean: float
    population_std: float
    q1: float
    q3: float


class ZScoreValidationOutlier(BaseModel):
    row_index: int
    column: str
    value: float
    method: Literal["zscore"]
    z_score: float
    threshold: float


class IqrValidationOutlier(BaseModel):
    row_index: int
    column: str
    value: float
    method: Literal["iqr"]
    lower_bound: float
    upper_bound: float
    q1: float
    q3: float
    iqr: float
    multiplier: float


class MarketDataValidationRunResponse(BaseModel):
    row_count: int
    missing_field_issues: list[MissingFieldIssue]
    key_consistency: Union[
        KeyConsistencyCheckedResponse,
        KeyConsistencyEmptyResponse,
        KeyConsistencySkippedResponse,
    ]
    numeric_stats: dict[str, NumericColumnStats]
    outliers: list[Union[ZScoreValidationOutlier, IqrValidationOutlier]]
    outlier_method: Literal["zscore", "iqr", "none"]
    normalized_rows: list[dict[str, Any]] | None


@router.post("/run", response_model=MarketDataValidationRunResponse)
def run_market_data_validation(payload: MarketDataValidationRunRequest) -> MarketDataValidationRunResponse:
    opts = payload.options
    return MarketDataValidationRunResponse(
        **validate_market_rows(
            payload.rows,
            required_fields=opts.required_fields,
            numeric_columns=opts.numeric_columns,
            outlier_method=opts.outlier_method,
            zscore_threshold=opts.zscore_threshold,
            iqr_multiplier=opts.iqr_multiplier,
            normalize_columns=opts.normalize_columns,
            check_key_consistency=opts.check_key_consistency,
        )
    )


alias_router.add_api_route(
    "/run",
    run_market_data_validation,
    methods=["POST"],
    response_model=MarketDataValidationRunResponse,
    name="analyst_insight_run_validation",
)
