"""Deterministic joining of named record lists by shared key fields."""

from __future__ import annotations

from typing import Any, TypedDict


class CrossReferenceGroupOut(TypedDict):
    """Records from multiple sources that share the same composite key."""

    key: dict[str, Any]
    records_by_source: dict[str, list[dict[str, Any]]]


class IntegratedDatasetOut(TypedDict):
    """Structured result of cross-referencing named sources on ``link_keys``."""

    link_keys: list[str]
    source_record_counts: dict[str, int]
    cross_references: list[CrossReferenceGroupOut]


def ingest_sources(sources: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """Return a shallow copy of sources with only list[dict] values (defensive normalize)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for name, rows in sources.items():
        out[name] = [dict(r) for r in rows]
    return out


def _composite_key(record: dict[str, Any], link_keys: list[str]) -> tuple[Any, ...] | None:
    vals: list[Any] = []
    for k in link_keys:
        if k not in record:
            return None
        vals.append(record[k])
    return tuple(vals)


def build_integrated_dataset(
    sources: dict[str, list[dict[str, Any]]],
    link_keys: list[str],
) -> IntegratedDatasetOut:
    """
    Group records across sources that share the same values for all ``link_keys``.

    Only emits cross-reference groups where at least two distinct source names
    contribute at least one record (true multi-source links).
    """
    if not link_keys:
        normalized = ingest_sources(sources)
        return IntegratedDatasetOut(
            link_keys=[],
            source_record_counts={n: len(rows) for n, rows in normalized.items()},
            cross_references=[],
        )

    # bucket: composite tuple -> source name -> list of records
    buckets: dict[tuple[Any, ...], dict[str, list[dict[str, Any]]]] = {}

    for source_name, rows in sources.items():
        for raw in rows:
            record: dict[str, Any] = dict(raw)
            ck = _composite_key(record, link_keys)
            if ck is None:
                continue
            if ck not in buckets:
                buckets[ck] = {}
            if source_name not in buckets[ck]:
                buckets[ck][source_name] = []
            buckets[ck][source_name].append(record)

    cross: list[CrossReferenceGroupOut] = []
    for ck, by_src in buckets.items():
        if len(by_src) < 2:
            continue
        key_dict = {link_keys[i]: ck[i] for i in range(len(link_keys))}
        cross.append(CrossReferenceGroupOut(key=key_dict, records_by_source=dict(by_src)))

    cross.sort(key=lambda g: tuple(str(g["key"].get(k, "")) for k in link_keys))

    normalized = ingest_sources(sources)
    return IntegratedDatasetOut(
        link_keys=list(link_keys),
        source_record_counts={n: len(rows) for n, rows in normalized.items()},
        cross_references=cross,
    )
