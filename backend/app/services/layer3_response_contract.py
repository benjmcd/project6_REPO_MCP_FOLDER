from __future__ import annotations

from typing import Any

from app.models.models import uuid_str
from app.services.layer3_utils import utcnow_iso_z


LAYER3_SCHEMA_VERSION = 1


def base_response(
    schema_id: str,
    *,
    request_id: str | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "schema_version": LAYER3_SCHEMA_VERSION,
        "request_id": request_id or uuid_str(),
        "server_time": utcnow_iso_z(),
        "status": status,
    }
