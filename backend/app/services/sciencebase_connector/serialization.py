from __future__ import annotations

from typing import Any

from app.models import ConnectorRunEvent


def serialize_run_event(event: ConnectorRunEvent) -> dict[str, Any]:
    return {
        "connector_run_event_id": event.connector_run_event_id,
        "connector_run_id": event.connector_run_id,
        "connector_run_target_id": event.connector_run_target_id,
        "phase": event.phase,
        "stage": event.stage,
        "event_type": event.event_type,
        "status_before": event.status_before,
        "status_after": event.status_after,
        "reason_code": event.reason_code,
        "error_class": event.error_class,
        "message": event.message,
        "metrics_json": event.metrics_json or {},
        "created_at": event.created_at,
    }
