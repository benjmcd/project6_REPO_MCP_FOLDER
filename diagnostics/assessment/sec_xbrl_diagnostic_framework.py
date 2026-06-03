from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


PASSED_STATE = "passed"
BLOCKED_STATE = "blocked"


def criterion(
    name: str,
    passed: bool,
    evidence: Mapping[str, Any],
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "criterion": name,
        "state": PASSED_STATE if passed else BLOCKED_STATE,
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def blocking_reasons(criteria: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "criterion": str(item.get("criterion") or ""),
            "reason": str(item.get("blocked_reason") or ""),
            "evidence": item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {},
        }
        for item in criteria
        if item.get("state") != PASSED_STATE
    ]


def decision(criteria: Sequence[Mapping[str, Any]], *, ready: str, blocked: str) -> str:
    return ready if not blocking_reasons(criteria) else blocked


def report_envelope(
    *,
    schema_id: str,
    target: str,
    next_slice: str,
    decision: str,
    source_mode: str,
    validate_only: bool = True,
    **payload: Any,
) -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "target": target,
        "next_slice": next_slice,
        "decision": decision,
        "source_mode": source_mode,
        "validate_only": validate_only,
        **payload,
    }


def controls(
    *,
    validate_only: bool,
    source_acquisition_performed: bool,
    arelle_invoked: bool,
    network_performed: bool,
    value_reveal_performed: bool,
    production_database_touched: bool,
    production_readiness_claimed: bool,
) -> dict[str, bool]:
    return {
        "validate_only": validate_only,
        "source_acquisition_performed": source_acquisition_performed,
        "arelle_invoked": arelle_invoked,
        "network_performed": network_performed,
        "value_reveal_performed": value_reveal_performed,
        "production_database_touched": production_database_touched,
        "production_readiness_claimed": production_readiness_claimed,
    }
