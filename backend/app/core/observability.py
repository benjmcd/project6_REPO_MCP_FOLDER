"""
Observability helpers: request-id middleware, structured JSON logging (opt-in),
and a global unhandled-exception handler.

Reads LAYER3_LOG_FORMAT from os.environ directly — intentionally does NOT import
config.py so that this module can be used without triggering the Settings validator.
"""
from __future__ import annotations

import json
import logging
import os
import re
import traceback
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = "X-Request-ID"

# Allowlist: alphanumeric plus safe punctuation only; max 128 chars.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


# ---------------------------------------------------------------------------
# JSON log formatter (opt-in via LAYER3_LOG_FORMAT=json)
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
        payload: dict = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include request_id if injected onto the record
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """
    Configure root logger.  When LAYER3_LOG_FORMAT=json (case-insensitive),
    replace root handlers with a JSON formatter; otherwise leave logging
    configuration untouched (stdlib default / uvicorn defaults apply).
    """
    fmt = os.environ.get("LAYER3_LOG_FORMAT", "").strip().lower()
    if fmt != "json":
        return

    root = logging.getLogger()
    json_formatter = _JsonFormatter()
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(json_formatter)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(json_formatter)
        root.addHandler(handler)
        if root.level == logging.NOTSET:
            root.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Accept an inbound X-Request-ID header if it passes validation; otherwise
    generate a UUID4.  Validation: at most 128 chars, matching ^[A-Za-z0-9._-]+$.
    Invalid or absent inbound ids are silently replaced — prevents log/header
    injection via reflected user-controlled input.

    Exposes the id on ``request.state.request_id`` and returns it in the
    response header.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        inbound = request.headers.get(_REQUEST_ID_HEADER)
        if inbound and _REQUEST_ID_RE.match(inbound):
            request_id = inbound
        else:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response


# ---------------------------------------------------------------------------
# Global unhandled-exception handler
# ---------------------------------------------------------------------------

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch any unhandled exception.  Returns a bounded 500 JSON body with no
    stack trace or internal detail.  Full traceback is logged server-side with
    the request_id for correlation.
    """
    request_id = getattr(getattr(request, "state", None), "request_id", None) or "unknown"
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception [request_id=%s]: %s",
        request_id,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "request_id": request_id,
        },
    )
