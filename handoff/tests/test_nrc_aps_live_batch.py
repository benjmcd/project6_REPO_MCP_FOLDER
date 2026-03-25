import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_live_batch  # noqa: E402


def _write_live_report(path: Path, generated_at: datetime) -> None:
    payload = {
        "schema_id": "aps.live_validation_report.v1",
        "schema_version": 1,
        "evaluator_version": "test_live_validator",
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "tests": {
            "APS-V1_qps_ramp_test": {"status": "observed", "recommended_max_rps": 6, "first_failure_rps": 8},
            "APS-V2_request_shape_acceptance": {
                "shape_a_q_filters": {"status_code": 200},
                "guide_native": {"status_code": 500},
                "shape_b_queryString_docket": {"status_code": 500},
            },
            "APS-V3_response_envelope_variant": {"envelope_variant": "results"},
            "APS-V5_date_added_timestamp_filter_syntax": {"date_added_timestamp_ge": {"ok": True}},
            "APS-V8_take_page_size_behavior": {"take_1000": {"count_returned": 100}},
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_batch(tmp_path: Path) -> Path:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)

    def _runner(
        *,
        cycle_index: int,
        output_path: Path,
        timeout_seconds: int,
        pagination_max_pages: int,
        pagination_take: int,
        url_probe_bytes: int,
    ) -> dict[str, Any]:
        _write_live_report(output_path, now)
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    summary = nrc_aps_live_batch.collect_live_validation_batch(
        cycle_count=2,
        spacing_seconds=0.0,
        timeout_seconds=45,
        pagination_max_pages=2,
        pagination_take=10,
        url_probe_bytes=4096,
        batch_root=tmp_path / "batches",
        cycle_runner=_runner,
        invocation_argv=["--test"],
    )
    return Path(summary["manifest_ref"])


def test_load_and_validate_finalized_manifest_passes(tmp_path: Path):
    manifest_path = _build_batch(tmp_path)
    payload = nrc_aps_live_batch.load_and_validate_finalized_manifest(manifest_path)
    assert payload["schema_id"] == "aps.live_validation_batch.v1"
    assert payload["finalized"] is True
    assert payload["manifest_sha256"]
    assert payload["manifest_checksum"]["algorithm"] == "sha256"


def test_load_and_validate_finalized_manifest_fails_on_mutation(tmp_path: Path):
    manifest_path = _build_batch(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["completed_cycle_count"] = int(payload.get("completed_cycle_count") or 0) + 1
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(nrc_aps_live_batch.BatchManifestValidationError):
        nrc_aps_live_batch.load_and_validate_finalized_manifest(manifest_path)


def test_load_and_validate_finalized_manifest_fails_on_sidecar_mismatch(tmp_path: Path):
    manifest_path = _build_batch(tmp_path)
    sidecar_path = manifest_path.with_suffix(manifest_path.suffix + ".sha256")
    sidecar_path.write_text("deadbeef\n", encoding="utf-8")

    with pytest.raises(nrc_aps_live_batch.BatchManifestValidationError):
        nrc_aps_live_batch.load_and_validate_finalized_manifest(manifest_path)

