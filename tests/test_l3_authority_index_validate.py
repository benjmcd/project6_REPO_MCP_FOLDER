from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "l3-authority-index-validate.py"


def _validator_module():
    spec = importlib.util.spec_from_file_location("l3_authority_index_validate", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _valid_payload(tmp_path: Path) -> dict:
    authority_doc = tmp_path / "docs" / "authority.md"
    authority_doc.parent.mkdir()
    authority_doc.write_text("canonical authority marker\n", encoding="utf-8")
    return {
        "artifact_version": 1,
        "artifact_name": "Project6 authority index",
        "index_scope": "intentionally_scoped",
        "non_exhaustive_reason": "Focused current-main authority index.",
        "onlook_policy": "excluded",
        "last_verified": {
            "remote": "project6-origin/main",
            "commit": "a" * 40,
            "verified_at_utc": "2026-06-04T00:00:00Z",
            "verification_summary": "Fixture verification.",
            "commands": ["python ./tools/l3-authority-index-validate.py"],
        },
        "authority_order": ["live git authority"],
        "lanes": [
            {
                "lane_id": "fixture-lane",
                "lane_name": "Fixture lane",
                "lane_scope": "Fixture scope",
                "current_state": "Fixture current state",
                "source_of_truth": [
                    {
                        "path": "docs/authority.md",
                        "kind": "tracked_doc",
                        "authority": "fixture authority",
                        "freshness": "current_status_doc",
                        "required_terms": ["canonical authority marker"],
                    }
                ],
                "current_truth_order": ["source doc"],
                "known_limits": ["fixture-only"],
                "next_decision": "No decision.",
            }
        ],
    }


def _issue_codes(payload: dict, tmp_path: Path) -> set[str]:
    validator = _validator_module()
    return {issue.code for issue in validator.validate_payload(payload, root=tmp_path)}


def test_authority_index_validator_rejects_empty_required_lists(tmp_path: Path) -> None:
    payload = _valid_payload(tmp_path)
    payload["authority_order"] = []
    payload["last_verified"]["commands"] = []
    payload["lanes"][0]["current_truth_order"] = []
    payload["lanes"][0]["source_of_truth"][0]["required_terms"] = []

    codes = _issue_codes(payload, tmp_path)

    assert "invalid_authority_order" in codes
    assert "invalid_verification_commands" in codes
    assert "invalid_lane_list" in codes
    assert "invalid_required_terms" in codes


def test_authority_index_validator_rejects_unsupported_fields(tmp_path: Path) -> None:
    payload = _valid_payload(tmp_path)
    payload["unsupported_roadmap_claim"] = "not part of the schema"
    payload["last_verified"]["extra"] = "not part of the schema"
    payload["lanes"][0]["extra"] = "not part of the schema"
    payload["lanes"][0]["source_of_truth"][0]["extra"] = "not part of the schema"

    codes = _issue_codes(payload, tmp_path)

    assert codes == {"unsupported_field"}


def test_authority_index_validator_rejects_onlook_lane_metadata(tmp_path: Path) -> None:
    payload = copy.deepcopy(_valid_payload(tmp_path))
    payload["lanes"][0]["lane_name"] = "Onlook roadmap lane"
    payload["lanes"][0]["current_truth_order"] = ["current main", "Onlook export"]

    codes = _issue_codes(payload, tmp_path)

    assert codes == {"onlook_lane_metadata"}
