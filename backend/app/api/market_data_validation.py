from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.market_data_validation import validate_market_rows

router = APIRouter(prefix="/market-pipeline/validation", tags=["market_data_validation"])


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


@router.post("/run")
def run_market_data_validation(payload: MarketDataValidationRunRequest) -> dict[str, Any]:
    opts = payload.options
    return validate_market_rows(
        payload.rows,
        required_fields=opts.required_fields,
        numeric_columns=opts.numeric_columns,
        outlier_method=opts.outlier_method,
        zscore_threshold=opts.zscore_threshold,
        iqr_multiplier=opts.iqr_multiplier,
        normalize_columns=opts.normalize_columns,
        check_key_consistency=opts.check_key_consistency,
    )
