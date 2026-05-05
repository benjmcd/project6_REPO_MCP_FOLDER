from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.layer3_response_contract import base_response


@dataclass(frozen=True)
class Layer3WorkbenchError(ValueError):
    error_code: str
    message: str
    status: str = "invalid"
    http_status: int = 400
    recoverable: bool = True
    blocked_fields: list[str] = field(default_factory=list)
    next_allowed_actions: list[str] = field(default_factory=list)


def workbench_error_response(exc: Layer3WorkbenchError, *, request_id: str | None = None) -> dict[str, Any]:
    return {
        **base_response("layer3.workbench_error.v1", request_id=request_id, status=exc.status),
        "error_code": exc.error_code,
        "message": exc.message,
        "recoverable": exc.recoverable,
        "blocked_fields": list(exc.blocked_fields),
        "next_allowed_actions": list(exc.next_allowed_actions),
    }
