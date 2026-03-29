from __future__ import annotations

import math
import statistics
from typing import Any, Literal

OutlierMethod = Literal["zscore", "iqr", "none"]


def _is_bool(v: Any) -> bool:
    return isinstance(v, bool)


def _parse_numeric(v: Any) -> float | None:
    if v is None:
        return None
    if _is_bool(v):
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _collect_column_values(rows: list[dict[str, Any]], column: str) -> tuple[list[int], list[float]]:
    indices: list[int] = []
    values: list[float] = []
    for i, row in enumerate(rows):
        if column not in row:
            continue
        parsed = _parse_numeric(row[column])
        if parsed is None:
            continue
        indices.append(i)
        values.append(parsed)
    return indices, values


def _quartiles(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        x = values[0]
        return x, x
    qs = statistics.quantiles(values, n=4, method="exclusive")
    return float(qs[0]), float(qs[2])


def _zscore_outliers(
    rows: list[dict[str, Any]],
    column: str,
    threshold: float,
) -> list[dict[str, Any]]:
    _, values = _collect_column_values(rows, column)
    if len(values) < 2:
        return []
    mean = statistics.fmean(values)
    try:
        pstdev = statistics.pstdev(values)
    except statistics.StatisticsError:
        return []
    if pstdev == 0.0:
        return []

    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if column not in row:
            continue
        parsed = _parse_numeric(row[column])
        if parsed is None:
            continue
        z = abs((parsed - mean) / pstdev)
        if z > threshold:
            out.append(
                {
                    "row_index": i,
                    "column": column,
                    "value": parsed,
                    "method": "zscore",
                    "z_score": z,
                    "threshold": threshold,
                }
            )
    return out


def _iqr_outliers(
    rows: list[dict[str, Any]],
    column: str,
    multiplier: float,
) -> list[dict[str, Any]]:
    _, values = _collect_column_values(rows, column)
    if len(values) < 2:
        return []
    q1, q3 = _quartiles(values)
    iqr = q3 - q1
    low = q1 - multiplier * iqr
    high = q3 + multiplier * iqr

    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if column not in row:
            continue
        parsed = _parse_numeric(row[column])
        if parsed is None:
            continue
        if parsed < low or parsed > high:
            out.append(
                {
                    "row_index": i,
                    "column": column,
                    "value": parsed,
                    "method": "iqr",
                    "lower_bound": low,
                    "upper_bound": high,
                    "q1": q1,
                    "q3": q3,
                    "iqr": iqr,
                    "multiplier": multiplier,
                }
            )
    return out


def _column_stats(rows: list[dict[str, Any]], column: str) -> dict[str, Any] | None:
    _, values = _collect_column_values(rows, column)
    if not values:
        return None
    q1, q3 = _quartiles(values)
    vmin = min(values)
    vmax = max(values)
    mean = statistics.fmean(values)
    pstdev = statistics.pstdev(values) if len(values) >= 1 else 0.0
    return {
        "count": len(values),
        "min": vmin,
        "max": vmax,
        "mean": mean,
        "population_std": pstdev,
        "q1": q1,
        "q3": q3,
    }


def _min_max_normalize_rows(
    rows: list[dict[str, Any]],
    columns: list[str],
) -> list[dict[str, Any]]:
    stats_by_col: dict[str, dict[str, float]] = {}
    for col in columns:
        _, values = _collect_column_values(rows, col)
        if not values:
            stats_by_col[col] = {"min": 0.0, "max": 0.0, "span": 0.0}
            continue
        vmin = min(values)
        vmax = max(values)
        span = vmax - vmin
        stats_by_col[col] = {"min": float(vmin), "max": float(vmax), "span": float(span)}

    normalized: list[dict[str, Any]] = []
    for row in rows:
        new_row = dict(row)
        for col in columns:
            if col not in new_row:
                continue
            parsed = _parse_numeric(new_row[col])
            meta = stats_by_col[col]
            if parsed is None:
                continue
            span = meta["span"]
            if span == 0.0:
                new_row[col] = 0.5
            else:
                new_row[col] = (parsed - meta["min"]) / span
        normalized.append(new_row)
    return normalized


def _missing_fields_for_rows(rows: list[dict[str, Any]], required: list[str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        missing = [f for f in required if f not in row or row[f] is None or row[f] == ""]
        if missing:
            issues.append({"row_index": i, "missing_fields": missing})
    return issues


def _key_consistency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"consistent": True, "key_sets": []}
    sets = [frozenset(r.keys()) for r in rows]
    union: set[str] = set()
    for s in sets:
        union |= set(s)
    inconsistent_rows: list[int] = []
    for i, s in enumerate(sets):
        if set(s) != union:
            inconsistent_rows.append(i)
    return {
        "consistent": len(inconsistent_rows) == 0,
        "union_keys": sorted(union),
        "inconsistent_row_indices": inconsistent_rows,
    }


def validate_market_rows(
    rows: list[dict[str, Any]],
    *,
    required_fields: list[str] | None = None,
    numeric_columns: list[str] | None = None,
    outlier_method: OutlierMethod = "zscore",
    zscore_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
    normalize_columns: list[str] | None = None,
    check_key_consistency: bool = True,
) -> dict[str, Any]:
    """
    Validate tabular market rows: missing required fields, key consistency,
    numeric outliers (z-score or IQR), optional min-max normalization.
    """
    required = list(required_fields or [])
    numeric_cols = list(numeric_columns or [])
    norm_cols = list(normalize_columns or [])

    missing_report = _missing_fields_for_rows(rows, required)
    key_info = _key_consistency(rows) if check_key_consistency else {"consistent": True, "skipped": True}

    numeric_stats: dict[str, Any] = {}
    for col in numeric_cols:
        st = _column_stats(rows, col)
        if st:
            numeric_stats[col] = st

    outliers: list[dict[str, Any]] = []
    if outlier_method == "zscore":
        for col in numeric_cols:
            outliers.extend(_zscore_outliers(rows, col, zscore_threshold))
    elif outlier_method == "iqr":
        for col in numeric_cols:
            outliers.extend(_iqr_outliers(rows, col, iqr_multiplier))

    normalized_rows: list[dict[str, Any]] | None = None
    if norm_cols:
        normalized_rows = _min_max_normalize_rows(rows, norm_cols)

    return {
        "row_count": len(rows),
        "missing_field_issues": missing_report,
        "key_consistency": key_info,
        "numeric_stats": numeric_stats,
        "outliers": outliers,
        "outlier_method": outlier_method,
        "normalized_rows": normalized_rows,
    }
