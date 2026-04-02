from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MarketInsight(BaseModel):
    """Actionable insight derived from validated signals (deterministic rules only)."""

    severity: Literal["low", "medium", "high"]
    category: Literal["trend", "correlation", "emerging_risk"]
    message: str
    supporting_metrics: dict[str, Any] = Field(default_factory=dict)
    derivation_label: Literal["heuristic"] = Field(
        default="heuristic",
        description="Insights are rule-based, not from a live LLM.",
    )


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sorted_severity_key(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _insight_sort_key(insight: MarketInsight) -> tuple[str, int, str]:
    return (insight.category, _sorted_severity_key(insight.severity), insight.message)


def _emit_validation_risks(validation_summary: dict[str, Any]) -> list[MarketInsight]:
    out: list[MarketInsight] = []
    invalid = _as_int(validation_summary.get("invalid_count"))
    failed = _as_int(validation_summary.get("failed_count"))
    pass_rate = _as_float(validation_summary.get("pass_rate"))

    if invalid > 0 or failed > 0:
        out.append(
            MarketInsight(
                severity="high",
                category="emerging_risk",
                message="Validation summary reports failed or invalid signals; review upstream checks before acting.",
                supporting_metrics={
                    "invalid_count": invalid,
                    "failed_count": failed,
                    "valid_count": _as_int(validation_summary.get("valid_count")),
                },
            )
        )
    elif pass_rate is not None and pass_rate < 0.85:
        out.append(
            MarketInsight(
                severity="medium",
                category="emerging_risk",
                message="Pass rate is below the 85% heuristic threshold; treat downstream conclusions as provisional.",
                supporting_metrics={"pass_rate": pass_rate, "threshold": 0.85},
            )
        )
    return out


def _emit_correlation(integrated: dict[str, Any]) -> list[MarketInsight]:
    raw = integrated.get("signals_by_category")
    if not isinstance(raw, dict):
        return []
    counts: list[tuple[str, int]] = []
    for key, value in raw.items():
        n = _as_int(value)
        if n > 0:
            counts.append((str(key), n))
    if len(counts) < 2:
        return []
    counts.sort(key=lambda item: item[1], reverse=True)
    top, second = counts[0][1], counts[1][1]
    if top <= 0:
        return []
    ratio = second / top
    if ratio < 0.75:
        return []
    return [
        MarketInsight(
            severity="medium",
            category="correlation",
            message="Multiple signal categories show comparable volume; investigate shared drivers or coupling.",
            supporting_metrics={
                "top_categories": [counts[0][0], counts[1][0]],
                "counts": {counts[0][0]: counts[0][1], counts[1][0]: counts[1][1]},
                "balance_ratio": round(ratio, 4),
                "rule": "second_highest_count / highest_count >= 0.75",
            },
        )
    ]


def _emit_trend(integrated: dict[str, Any]) -> list[MarketInsight]:
    traj = integrated.get("signal_trajectory")
    if not isinstance(traj, list) or len(traj) < 3:
        return []
    series: list[float] = []
    for item in traj:
        f = _as_float(item)
        if f is None:
            return []
        series.append(f)
    first_half = series[: len(series) // 2]
    if not first_half:
        return []
    baseline = sum(first_half) / len(first_half)
    last = series[-1]
    if last <= baseline:
        return []
    delta = last - series[0]
    if delta <= 0:
        return []
    return [
        MarketInsight(
            severity="medium",
            category="trend",
            message="Signal trajectory is rising versus its early window; monitor for sustained movement.",
            supporting_metrics={
                "series_head": series[:3],
                "series_tail": series[-3:],
                "early_window_mean": round(baseline, 6),
                "last_value": last,
                "rule": "last > mean(first_half) and last > first",
            },
        )
    ]


def process_market_insights(payload: dict[str, Any]) -> list[MarketInsight]:
    """
    Turn cross-referenced, validated signals into actionable insights using deterministic heuristics.

    Accepts either a nested shape with ``integrated`` / ``validation_summary`` or any generic dict
    (values are read defensively).
    """
    if not isinstance(payload, dict):
        return []

    insights: list[MarketInsight] = []

    validation_summary = payload.get("validation_summary")
    if isinstance(validation_summary, dict):
        insights.extend(_emit_validation_risks(validation_summary))

    integrated = payload.get("integrated")
    if isinstance(integrated, dict):
        insights.extend(_emit_correlation(integrated))
        insights.extend(_emit_trend(integrated))

    # De-duplicate identical messages while preserving deterministic order
    seen: set[tuple[str, str, str]] = set()
    unique: list[MarketInsight] = []
    for ins in insights:
        key = (ins.category, ins.severity, ins.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ins)

    return sorted(unique, key=_insight_sort_key)
