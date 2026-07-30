"""Pure custody-marker contract shared by NRC Phase B and origin continuity."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any
from uuid import UUID, uuid4


CUSTODY_STORAGE_KEY = "nrc_phase_b_custody_v1"
CUSTODY_SCHEMA_ID = "project6.nrc_phase_b_custody.v1"
PENDING_SNAPSHOT_EXIT = "pending_snapshot_exit"
VERIFIED = "verified"

_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_URI_SCHEME_PREFIX = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:[\\/]")
_WINDOWS_DRIVE_PREFIX = re.compile(r"[A-Za-z]:")
_CANONICAL_WINDOWS_ABSOLUTE_PATH = re.compile(
    r"[A-Za-z]:[\\/](?![\\/])"
)
_FIELDS = frozenset(
    {
        "schema_id",
        "status",
        "attempt_id",
        "connector_run_id",
        "connector_run_target_id",
        "aps_content_linkage_id",
        "content_id",
        "blob_ref",
        "blob_sha256",
        "blob_size_bytes",
    }
)
_STATUSES = frozenset({PENDING_SNAPSHOT_EXIT, VERIFIED})


class NrcPhaseBCustodyMarkerError(ValueError):
    """Raised when a custody marker is malformed or contradicts authority."""


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NrcPhaseBCustodyMarkerError(f"{field}_invalid")
    if value.startswith(("\\\\", "//")) or (
        _URI_SCHEME_PREFIX.match(value)
        and not _WINDOWS_ABSOLUTE_PATH.match(value)
    ):
        raise NrcPhaseBCustodyMarkerError(f"{field}_url_forbidden")
    return value


def _required_blob_ref(value: object) -> str:
    blob_ref = _required_text(value, field="blob_ref")
    if _WINDOWS_DRIVE_PREFIX.match(
        blob_ref
    ) and not _CANONICAL_WINDOWS_ABSOLUTE_PATH.match(blob_ref):
        raise NrcPhaseBCustodyMarkerError("blob_ref_url_forbidden")
    return blob_ref


def parse_custody_marker(value: object) -> dict[str, Any]:
    """Return one exact canonical marker or fail closed."""

    if not isinstance(value, Mapping) or frozenset(value) != _FIELDS:
        raise NrcPhaseBCustodyMarkerError("marker_shape_invalid")
    marker = dict(value)
    if marker.get("schema_id") != CUSTODY_SCHEMA_ID:
        raise NrcPhaseBCustodyMarkerError("marker_schema_invalid")
    if marker.get("status") not in _STATUSES:
        raise NrcPhaseBCustodyMarkerError("marker_status_invalid")

    attempt_id = _required_text(
        marker.get("attempt_id"),
        field="attempt_id",
    )
    try:
        parsed_attempt = UUID(attempt_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise NrcPhaseBCustodyMarkerError(
            "attempt_id_invalid"
        ) from exc
    if str(parsed_attempt) != attempt_id or parsed_attempt.version != 4:
        raise NrcPhaseBCustodyMarkerError("attempt_id_invalid")

    for field in (
        "connector_run_id",
        "connector_run_target_id",
        "aps_content_linkage_id",
    ):
        marker[field] = _required_text(marker.get(field), field=field)
    marker["blob_ref"] = _required_blob_ref(marker.get("blob_ref"))
    for field in ("content_id", "blob_sha256"):
        digest = _required_text(marker.get(field), field=field)
        if not _HEX_SHA256.fullmatch(digest):
            raise NrcPhaseBCustodyMarkerError(f"{field}_invalid")
        marker[field] = digest

    size = marker.get("blob_size_bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise NrcPhaseBCustodyMarkerError("blob_size_bytes_invalid")
    return marker


def build_pending_custody_marker(
    *,
    connector_run_id: str,
    connector_run_target_id: str,
    aps_content_linkage_id: str,
    content_id: str,
    blob_ref: str,
    blob_sha256: str,
    blob_size_bytes: int,
) -> dict[str, Any]:
    """Mint one server-owned pending marker for a first admitted bind."""

    return parse_custody_marker(
        {
            "schema_id": CUSTODY_SCHEMA_ID,
            "status": PENDING_SNAPSHOT_EXIT,
            "attempt_id": str(uuid4()),
            "connector_run_id": connector_run_id,
            "connector_run_target_id": connector_run_target_id,
            "aps_content_linkage_id": aps_content_linkage_id,
            "content_id": content_id,
            "blob_ref": blob_ref,
            "blob_sha256": blob_sha256,
            "blob_size_bytes": blob_size_bytes,
        }
    )


def verified_custody_marker(
    pending_marker: Mapping[str, Any],
) -> dict[str, Any]:
    """Acknowledge successful snapshot exit for one exact pending attempt.

    ``verified`` does not attest current or perpetual file immutability.
    """

    marker = parse_custody_marker(pending_marker)
    if marker["status"] != PENDING_SNAPSHOT_EXIT:
        raise NrcPhaseBCustodyMarkerError("marker_not_pending")
    marker["status"] = VERIFIED
    return marker


def require_exact_custody_marker(
    value: object,
    *,
    status: str,
    connector_run_id: str,
    connector_run_target_id: str,
    aps_content_linkage_id: str,
    content_id: str,
    blob_ref: str,
    blob_sha256: str,
    blob_size_bytes: int,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    """Return marker only when every authority binding is exact."""

    marker = parse_custody_marker(value)
    expected = {
        "schema_id": CUSTODY_SCHEMA_ID,
        "status": status,
        "attempt_id": marker["attempt_id"],
        "connector_run_id": connector_run_id,
        "connector_run_target_id": connector_run_target_id,
        "aps_content_linkage_id": aps_content_linkage_id,
        "content_id": content_id,
        "blob_ref": blob_ref,
        "blob_sha256": blob_sha256,
        "blob_size_bytes": blob_size_bytes,
    }
    if marker != expected or (
        attempt_id is not None and marker["attempt_id"] != attempt_id
    ):
        raise NrcPhaseBCustodyMarkerError("marker_binding_mismatch")
    return marker
