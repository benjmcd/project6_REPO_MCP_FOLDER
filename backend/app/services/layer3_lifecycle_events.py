"""
Bounded, structured lifecycle log events for Layer 3 / Sublayer 3C (handoff Lane 14).

Emits structured INFO records on the ``layer3.lifecycle`` logger.  Events are
intentionally bounded: only ids / hashes / statuses / method ids / classification
and operator_ref derived from the server-side principal dict.  Raw product body,
title, payload_ref, URIs, paths, credentials, and raw header values are never
included.

This module has no DB writes and no schema changes — it is purely observability.
Import cycles are avoided: the only app imports are hashlib (stdlib) and json
(stdlib); the caller passes in the principal dict, not a DB model.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

_lifecycle_logger = logging.getLogger("layer3.lifecycle")
# Pin the level to INFO explicitly: otherwise this logger inherits the root
# effective level, and under uvicorn/Docker the root can stay at WARNING, which
# would silently filter every lifecycle event before any handler/formatter sees
# it. Setting it here guarantees the records are produced and propagate to
# whatever root handlers are configured.
_lifecycle_logger.setLevel(logging.INFO)


def bounded_operator_ref(principal: dict[str, Any] | None) -> str | None:
    """Derive a bounded, stable, non-PII ref from the server-side principal dict.

    Preference order:
    1. ``operator_ref_hash`` when it is already a scalar server-derived hash.
    2. blake2b digest of the stable JSON serialisation of the whole principal.
    3. None when principal is None (or serialisation fails).

    The returned value is ALWAYS either a server-owned scalar hash or a blake2b
    digest, so no raw field value (e.g. a forwarded identity header) is ever
    emitted, whatever shape the principal has.
    """
    if principal is None:
        return None
    # Prefer the server-owned hash the policy layer already computed, but only
    # when it is a scalar — never str() a nested dict/list (that could stringify
    # structured data verbatim).
    ref_hash = principal.get("operator_ref_hash")
    if isinstance(ref_hash, (str, int)):
        return str(ref_hash)
    # Fall back to a digest of the whole principal. The OUTPUT is a hash, so the
    # raw values never appear in it; default=str keeps non-serialisable values
    # from raising.
    try:
        stable_bytes = json.dumps(
            principal, sort_keys=True, ensure_ascii=True, default=str
        ).encode()
        return hashlib.blake2b(stable_bytes, digest_size=8).hexdigest()
    except Exception:
        return None


def emit_lifecycle_event(
    event: str,
    *,
    request_id: str | None,
    operator_ref: str | None,
    **fields: Any,
) -> None:
    """Emit a bounded lifecycle event as a structured INFO log record.

    The helper is defensive: it NEVER raises into the request path.  Any
    exception during logging is silently swallowed so the caller's operation
    is unaffected.

    The log record carries an ``extra`` dict with key ``layer3_event`` whose
    value is the bounded event dict (None-valued fields dropped).

    Args:
        event: Event name, e.g. ``"product_generated"``.
        request_id: Request-ID from ``request.state.request_id`` (may be None).
        operator_ref: Bounded operator ref from ``bounded_operator_ref()``.
        **fields: Additional bounded fields (ids, hashes, statuses only).
    """
    try:
        bounded: dict[str, Any] = {"event": event}
        if request_id is not None:
            bounded["request_id"] = request_id
        if operator_ref is not None:
            bounded["operator_ref"] = operator_ref
        for key, value in fields.items():
            if value is not None:
                bounded[key] = value
        _lifecycle_logger.info(
            "layer3.lifecycle",
            extra={"layer3_event": bounded, "request_id": request_id},
        )
    except Exception:
        # Observability must not break the operation.
        pass
