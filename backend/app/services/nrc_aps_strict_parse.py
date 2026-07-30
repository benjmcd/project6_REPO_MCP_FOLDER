"""Frozen NRC parser profile for the dual-live proof.

Spawn denial is a Python process-level guard, not an OS sandbox. RSS, CPU, and
wall-clock checks fail at the next checkpoint; they cannot preempt one blocking
native call in flight.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable


STRICT_PARSE_PROFILE_ID = "dual_live_proof_v1"
STRICT_PARSE_MAX_PAGES = 500
STRICT_PARSE_MAX_RENDERED_PIXELS = 0
STRICT_PARSE_MAX_TEXT_BYTES = 20_000_000
STRICT_PARSE_MAX_TABLE_ROWS = 10_000
STRICT_PARSE_MAX_TABLE_COLUMNS = 200
STRICT_PARSE_MAX_TEMP_BYTES = 0
STRICT_PARSE_MAX_PEAK_RSS_BYTES = 2_147_483_648
STRICT_PARSE_MAX_WALL_SECONDS = 300
STRICT_PARSE_MAX_CPU_SECONDS = 300
STRICT_PARSE_MAX_OUTPUT_BYTES = 30_000_000
STRICT_PARSE_MAX_SUBPROCESS_SPAWNS = 0

STRICT_PARSE_FORBIDDEN_DEGRADATION_CODES = frozenset(
    {
        "ocr_fallback_used",
        "ocr_required_but_unavailable",
        "ocr_execution_failed",
        "ocr_hybrid_failed",
        "advanced_ocr_weights_missing",
        "advanced_ocr_execution_failed",
        "visual_artifact_failed",
        "visual_capture_failed",
    }
)

_SUBPROCESS_GUARD_MARKER = "__nrc_aps_strict_subprocess_denial_guard__"


class StrictParseViolation(RuntimeError):
    """A frozen strict-parse invariant was breached."""


def _denied_spawn_primitive(name: str) -> Callable[..., Any]:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise StrictParseViolation(f"strict_subprocess_spawn_refused:{name}")

    denied.__name__ = f"strictly_denied_{name.replace('.', '_')}"
    setattr(denied, _SUBPROCESS_GUARD_MARKER, True)
    return denied


def _guard_primitive(owner: Any, name: str, *, label: str) -> None:
    primitive = getattr(owner, name, None)
    if not callable(primitive):
        return
    if bool(getattr(primitive, _SUBPROCESS_GUARD_MARKER, False)):
        return
    setattr(owner, name, _denied_spawn_primitive(label))


def install_subprocess_denial_guard() -> None:
    """Deny Python-level subprocess and process-replacement primitives."""

    _guard_primitive(subprocess, "Popen", label="subprocess.Popen")
    for name in sorted(dir(os)):
        if (
            name == "system"
            or name == "startfile"
            or name.startswith("spawn")
            or name.startswith("exec")
            or name.startswith("posix_spawn")
        ):
            _guard_primitive(os, name, label=f"os.{name}")


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    try:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise StrictParseViolation("strict_output_not_canonical_json") from exc
    return serialized.encode("utf-8")


def parse_admitted_blob_strict(
    *,
    blob_path: str | os.PathLike[str],
    expected_sha256: str,
) -> dict[str, Any]:
    """Parse one admitted PDF under the frozen dual-live proof profile."""

    install_subprocess_denial_guard()

    admitted_path = Path(blob_path)
    content = admitted_path.read_bytes()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if str(expected_sha256) != actual_sha256:
        raise StrictParseViolation("strict_blob_sha256_mismatch")

    # Application import stays lazy so the denial guard is installed first.
    from app.services import nrc_aps_document_processing

    pinned_config = {
        "strict_parse_profile": STRICT_PARSE_PROFILE_ID,
        "content_parse_max_pages": STRICT_PARSE_MAX_PAGES,
        "content_parse_timeout_seconds": STRICT_PARSE_MAX_WALL_SECONDS,
        "document_processing_engine": "baseline",
        "document_processing_engine_explicit": True,
        "ocr_enabled": False,
        "visual_lane_mode": "baseline",
    }

    previous_tempdir = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix="nrc-strict-parse-") as scratch_name:
        scratch_path = Path(scratch_name)
        tempfile.tempdir = scratch_name
        try:
            result = nrc_aps_document_processing.process_document(
                content=content,
                declared_content_type="application/pdf",
                config=pinned_config,
            )
            if any(scratch_path.iterdir()):
                raise StrictParseViolation("strict_temp_disk_limit_exceeded")
        finally:
            tempfile.tempdir = previous_tempdir

    if len(_canonical_json_bytes(result)) > STRICT_PARSE_MAX_OUTPUT_BYTES:
        raise StrictParseViolation("strict_output_limit_exceeded")
    if result.get("extractor_id") != "aps_pdf_text_extractor":
        raise StrictParseViolation("strict_extractor_refused")
    if result.get("ocr_page_count") != 0:
        raise StrictParseViolation("strict_ocr_page_count_refused")

    if "degradation_codes" not in result:
        raise StrictParseViolation("strict_degradation_refused")
    raw_degradation_codes = result["degradation_codes"]
    if not isinstance(raw_degradation_codes, (list, tuple)) or any(
        not isinstance(code, str)
        for code in raw_degradation_codes
    ):
        raise StrictParseViolation("strict_degradation_refused")
    degradation_codes = {code for code in raw_degradation_codes if code}
    if degradation_codes & STRICT_PARSE_FORBIDDEN_DEGRADATION_CODES:
        raise StrictParseViolation("strict_degradation_refused")
    return result
