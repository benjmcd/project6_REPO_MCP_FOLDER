from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "tools" / "l3-authority-index-validate.py"
INDEX_PATH = ROOT / "next_milestone_plans" / "authority-index.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "l3_authority_index_validate",
        VALIDATOR_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload() -> dict[str, object]:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _issue_codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def test_current_authority_index_validates() -> None:
    module = _load_validator()

    assert module.validate_index(INDEX_PATH) == []


def test_missing_declared_evidence_term_fails_closed() -> None:
    module = _load_validator()
    payload = _payload()
    first_source = payload["lanes"][0]["source_of_truth"][0]
    first_source["required_terms"] = ["not a real authority term"]

    assert "missing_required_term" in _issue_codes(module.validate_payload(payload, root=ROOT))


def test_onlook_paths_are_rejected() -> None:
    module = _load_validator()
    payload = _payload()
    first_source = payload["lanes"][0]["source_of_truth"][0]
    first_source["path"] = "next_milestone_plans/onlook-plan/README.md"

    assert "onlook_path" in _issue_codes(module.validate_payload(payload, root=ROOT))


def test_duplicate_lane_ids_fail_closed() -> None:
    module = _load_validator()
    payload = _payload()
    payload["lanes"][1]["lane_id"] = payload["lanes"][0]["lane_id"]

    assert "duplicate_lane_id" in _issue_codes(module.validate_payload(payload, root=ROOT))
