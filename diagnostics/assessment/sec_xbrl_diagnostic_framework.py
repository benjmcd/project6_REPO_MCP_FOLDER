from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
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


def redaction_hit_classes(
    packet_text: str,
    packet: Any,
    *,
    regexes: Mapping[str, Any],
    raw_keys: Sequence[str] | set[str] | frozenset[str],
    authority_ref_invalid: Callable[[Any], bool],
) -> list[str]:
    hits: list[str] = []
    for name, regex in regexes.items():
        if regex.search(packet_text):
            hits.append(str(name))
    if authority_ref_invalid(packet):
        hits.append("raw_or_unreduced_authority_ref")
    raw_key_set = {str(key).lower() for key in raw_keys}
    for key in _iter_keys(packet):
        if key.lower() in raw_key_set:
            hits.append("raw_or_local_authority_key")
    return hits


def text_redaction_scan(
    texts: Iterable[str],
    *,
    regexes: Mapping[str, Any],
) -> dict[str, Any]:
    hits = {str(name): False for name in regexes}
    for text in texts:
        for name, regex in regexes.items():
            hits[str(name)] = hits[str(name)] or bool(regex.search(text))
    return {"passed": not any(hits.values()), **hits}


def _iter_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, nested in value.items():
            keys.append(str(key))
            keys.extend(_iter_keys(nested))
        return keys
    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_iter_keys(item))
        return keys
    return []
