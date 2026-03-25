import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.nrc_aps_replay_gate import (  # noqa: E402
    ReplayGateError,
    build_replay_corpus,
    check_replay_corpus,
    validate_replay_corpus,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_validate_and_check_replay_corpus(tmp_path: Path):
    source_root = ROOT / "backend" / "app" / "storage_test" / "connectors"
    out_dir = tmp_path / "v1"
    diff_report = tmp_path / "diff.json"
    validation_report = tmp_path / "validation.json"

    build_summary = build_replay_corpus(
        source_roots=[source_root],
        out_dir=out_dir,
        diff_report_path=diff_report,
    )
    assert build_summary["case_count"] > 0
    assert (out_dir / "index.json").exists()
    assert diff_report.exists()

    report = validate_replay_corpus(
        corpus_dir=out_dir,
        report_path=validation_report,
        override_path=None,
    )
    assert report.passed
    assert report.failed_cases == 0
    assert validation_report.exists()

    check_summary = check_replay_corpus(
        source_roots=[source_root],
        corpus_dir=out_dir,
        diff_report_path=tmp_path / "check_diff.json",
    )
    assert check_summary["passed"] is True


def test_builder_rejects_malformed_exchange_snapshot(tmp_path: Path):
    source_root = tmp_path / "connectors"
    manifests_dir = source_root / "manifests"
    snapshots_dir = source_root / "snapshots"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    run_id = "11111111-1111-1111-1111-111111111111"
    snapshot_path = snapshots_dir / f"{run_id}_aaaa_search_exchange.json"
    manifest_path = manifests_dir / f"{run_id}_discovery.json"

    # Intentionally malformed (missing response_log)
    snapshot_payload = {
        "request_log": {
            "endpoint": "POST /aps/api/search",
            "request_body": {"q": "x"},
        }
    }
    snapshot_path.write_text(json.dumps(snapshot_payload), encoding="utf-8")
    manifest_payload = {
        "provider": "nrc_adams_aps",
        "query_payload_normalized": {"searchCriteria": {"q": "x", "mainLibFilter": True, "legacyLibFilter": False, "properties": []}},
        "search_exchange_refs": [str(snapshot_path)],
        "pages": [],
    }
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")

    with pytest.raises(ReplayGateError):
        build_replay_corpus(
            source_roots=[source_root],
            out_dir=tmp_path / "out",
        )


def test_validator_detects_fixture_mutation(tmp_path: Path):
    source_root = ROOT / "backend" / "app" / "storage_test" / "connectors"
    out_dir = tmp_path / "v1"
    build_replay_corpus(source_roots=[source_root], out_dir=out_dir)

    index = _load_json(out_dir / "index.json")
    first_case_path = out_dir / index["case_files"][0]
    payload = _load_json(first_case_path)
    payload["expected"]["parse_status"] = "__wrong__"
    first_case_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = validate_replay_corpus(
        corpus_dir=out_dir,
        report_path=tmp_path / "validation.json",
        override_path=None,
    )
    assert report.passed is False
    assert report.failed_cases >= 1


def test_validator_override_allows_temporary_drift(tmp_path: Path):
    source_root = ROOT / "backend" / "app" / "storage_test" / "connectors"
    out_dir = tmp_path / "v1"
    build_replay_corpus(source_roots=[source_root], out_dir=out_dir)

    index = _load_json(out_dir / "index.json")
    first_search_case = None
    for rel_path in index["case_files"]:
        candidate = _load_json(out_dir / rel_path)
        if candidate.get("case_type") == "search":
            first_search_case = candidate
            first_search_path = out_dir / rel_path
            break
    assert first_search_case is not None

    first_search_case["expected"]["parse_status"] = "__wrong__"
    first_search_path.write_text(
        json.dumps(first_search_case, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    override_path = tmp_path / "overrides.json"
    expires = (date.today() + timedelta(days=14)).isoformat()
    override_payload = {
        "overrides": [
            {
                "case_id": first_search_case["case_id"],
                "reason": "temporary parser drift during contract update",
                "expires_on": expires,
                "ignore_paths": ["expected.parse_status"],
            }
        ]
    }
    override_path.write_text(json.dumps(override_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = validate_replay_corpus(
        corpus_dir=out_dir,
        report_path=tmp_path / "validation_with_override.json",
        override_path=override_path,
    )
    assert report.passed
    assert report.overrides_applied >= 1
    assert report.warning_count >= 1

