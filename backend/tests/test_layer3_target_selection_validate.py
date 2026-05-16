from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "tools" / "l3-target-selection-validate.py"
INTAKE_PATH = (
    ROOT
    / "next_milestone_plans"
    / "Layer3_planning_docs"
    / "612_TARGET_SELECTION_INTAKE.md"
)


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "l3_target_selection_validate",
        VALIDATOR_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _record_text(module, values: dict[str, str]) -> str:
    lines = [
        "## Structured Selection Record",
        "",
        "```yaml",
    ]
    for field in module.REQUIRED_FIELDS + module.CONTROL_FIELDS:
        lines.append(f"{field}: {values[field]}")
    lines.extend(
        [
            "```",
            "",
            "## Next Section",
        ]
    )
    return "\n".join(lines)


def _filled_values(module) -> dict[str, str]:
    values = {field: f"filled_{field}" for field in module.REQUIRED_FIELDS}
    values["selection_complete"] = "true"
    values["implementation_entry_freeze_written"] = "false"
    return values


def _issue_codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def test_current_target_selection_intake_validates_as_pending() -> None:
    module = _load_validator()
    text = INTAKE_PATH.read_text(encoding="utf-8")

    assert module.validate_text(text, "pending") == []
    assert "selected_field_must_be_filled" in _issue_codes(
        module.validate_text(text, "selected")
    )


def test_selected_and_frozen_records_have_distinct_freeze_expectations() -> None:
    module = _load_validator()
    selected_values = _filled_values(module)

    assert module.validate_text(_record_text(module, selected_values), "selected") == []
    assert "pending_field_must_be_null" in _issue_codes(
        module.validate_text(_record_text(module, selected_values), "pending")
    )
    assert "frozen_freeze_written_must_be_true" in _issue_codes(
        module.validate_text(_record_text(module, selected_values), "frozen")
    )

    frozen_values = dict(selected_values)
    frozen_values["implementation_entry_freeze_written"] = "true"
    assert module.validate_text(_record_text(module, frozen_values), "frozen") == []


def test_duplicate_structured_record_key_fails_closed() -> None:
    module = _load_validator()
    text = "\n".join(
        [
            "## Structured Selection Record",
            "",
            "```yaml",
            "target_identity: null",
            "target_identity: null",
            "selection_complete: false",
            "implementation_entry_freeze_written: false",
            "```",
            "",
            "## Next Section",
        ]
    )

    assert "duplicate_key" in _issue_codes(module.validate_text(text, "pending"))
