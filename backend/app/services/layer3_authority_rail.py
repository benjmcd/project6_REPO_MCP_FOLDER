from __future__ import annotations

from typing import Any

from app.services.layer3_response_contract import LAYER3_SCHEMA_VERSION


DEFAULT_DOWNSTREAM_UNAVAILABLE = ("plan", "execution", "results", "package")


def authority_rail(
    *,
    session_id: str | None = None,
    preflight_id: str | None = None,
    source_set_id: str | None = None,
    current_gate: str = "intent",
    persistence_mode: str = "not_committed",
    source_classes: list[str] | None = None,
    counts: dict[str, int] | None = None,
    typing_status: str = "not_started",
    browser_only_state: list[str] | None = None,
    downstream_unavailable: list[str] | tuple[str, ...] | None = None,
    execution_enabled: bool = False,
    package_review_enabled: bool = False,
) -> dict[str, Any]:
    gate_counts = counts or {}
    return {
        "schema_id": "layer3.authority_rail.v1",
        "schema_version": LAYER3_SCHEMA_VERSION,
        "session_id": session_id or "none",
        "preflight_id": preflight_id or "none",
        "source_set_id": source_set_id or "none",
        "current_gate": current_gate,
        "persistence_mode": persistence_mode,
        "source_authority": {
            "source_classes": list(source_classes or []),
            "runtime_label": None,
            "database_label": None,
            "storage_label": None,
        },
        "approved_material_count": gate_counts.get("approved", 0),
        "denied_material_count": gate_counts.get("denied", 0),
        "isolated_material_count": gate_counts.get("isolated", 0),
        "flagged_material_count": gate_counts.get("flagged", 0),
        "typing_status": typing_status,
        "execution_enabled": execution_enabled,
        "package_review_enabled": package_review_enabled,
        "downstream_unavailable": list(downstream_unavailable or DEFAULT_DOWNSTREAM_UNAVAILABLE),
        "browser_only_state": list(browser_only_state or []),
    }
