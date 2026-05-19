from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "tools" / "l3-fixture-validate.py"
RECORD_PATH = (
    ROOT
    / "next_milestone_plans"
    / "Layer3_planning_docs"
    / "850_FIXTURE_VALIDATE_ONLY.md"
)
CHECKPOINT_RECORD_PATH = (
    ROOT
    / "next_milestone_plans"
    / "Layer3_planning_docs"
    / "851_FIXTURE_CHECKPOINT.md"
)


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "l3_fixture_validate",
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
        "## Structured Fixture Authority Record",
        "",
        "```yaml",
    ]
    for field in module.ALL_FIELDS:
        lines.append(f"{field}: {values[field]}")
    lines.extend(
        [
            "```",
            "",
            "## Next Section",
        ]
    )
    return "\n".join(lines)


def _pending_values(module) -> dict[str, str]:
    values = dict(module.FIXED_FIELDS)
    values.update({field: "pending" for field in module.TOOL_STATUS_FIELDS})
    values.update({field: "null" for field in module.SELECTION_FIELDS})
    values["selection_complete"] = "false"
    values["implementation_entry_freeze_written"] = "false"
    return values


def _checkpoint_values(module) -> dict[str, str]:
    values = _pending_values(module)
    values["tabpfn_fixture_authority_status"] = "deferred_absent_fixture_authority"
    values["nrc_rag_fixture_authority_status"] = "deferred_absent_fixture_authority"
    return values


def _selected_values(module) -> dict[str, str]:
    values = dict(module.FIXED_FIELDS)
    values.update(
        {
            "tabpfn_fixture_authority_status": "selected",
            "nrc_rag_fixture_authority_status": "selected",
        }
    )
    values.update(
        {
            "tabpfn_fixture_authority": "tests/fixtures/layer3/tabpfn_micro_fixture.json",
            "tabpfn_source_authority": "backend/tests/test_layer3_pass_entry.py",
            "tabpfn_fixture_kind": "dataset_version_supervised_tabular_micro_fixture",
            "tabpfn_target_column": "label",
            "tabpfn_feature_columns": "feature_a,feature_b",
            "tabpfn_task_type": "classification",
            "tabpfn_train_test_split": "deterministic_70_30",
            "tabpfn_leakage_checks": "no_target_in_features,no_future_rows",
            "tabpfn_row_count_band": "micro_10_100_rows",
            "tabpfn_metric_family": "accuracy_or_auc",
            "tabpfn_baseline_family": "majority_class",
            "tabpfn_no_adopt_threshold": "must_exceed_baseline_by_0.05_accuracy",
            "tabpfn_license_dependency_runtime_constraints": "no_runtime_no_dependency",
            "nrc_rag_fixture_authority": "tests/fixtures/layer3/nrc_rag_queries.json",
            "nrc_rag_query_set_authority": "manually_reviewed_query_set_v1",
            "nrc_rag_fixture_kind": "regulatory_context_grounding_query_set",
            "nrc_rag_query_ids": "q1,q2",
            "nrc_rag_query_texts": "fixed_text_q1,fixed_text_q2",
            "nrc_rag_answerability_labels": "q1_answerable,q2_unsupported_by_corpus",
            "nrc_rag_expected_source_identifiers": "source_a,source_b",
            "nrc_rag_expected_source_spans": "source_a:10-20",
            "nrc_rag_expected_refusal_behavior": "q2_refuse_unsupported",
            "nrc_rag_citation_rubric": "cite_expected_source_span_or_fail",
            "nrc_rag_baseline_surface_set": "lexical,hash_vector,hybrid_context",
            "nrc_rag_no_adopt_threshold": "must_improve_citation_recall_by_0.10",
            "nrc_rag_dependency_provider_network_runtime_constraints": "no_runtime_no_provider_no_network",
        }
    )
    values["selection_complete"] = "true"
    values["implementation_entry_freeze_written"] = "false"
    return values


def _defer_tabpfn(values: dict[str, str]) -> dict[str, str]:
    deferred = dict(values)
    deferred["tabpfn_fixture_authority_status"] = "deferred_absent_fixture_authority"
    for field in (
        "tabpfn_fixture_authority",
        "tabpfn_source_authority",
        "tabpfn_fixture_kind",
        "tabpfn_target_column",
        "tabpfn_feature_columns",
        "tabpfn_task_type",
        "tabpfn_train_test_split",
        "tabpfn_leakage_checks",
        "tabpfn_row_count_band",
        "tabpfn_metric_family",
        "tabpfn_baseline_family",
        "tabpfn_no_adopt_threshold",
        "tabpfn_license_dependency_runtime_constraints",
    ):
        deferred[field] = "null"
    return deferred


def _defer_nrc_rag(values: dict[str, str]) -> dict[str, str]:
    deferred = dict(values)
    deferred["nrc_rag_fixture_authority_status"] = "deferred_absent_fixture_authority"
    for field in (
        "nrc_rag_fixture_authority",
        "nrc_rag_query_set_authority",
        "nrc_rag_fixture_kind",
        "nrc_rag_query_ids",
        "nrc_rag_query_texts",
        "nrc_rag_answerability_labels",
        "nrc_rag_expected_source_identifiers",
        "nrc_rag_expected_source_spans",
        "nrc_rag_expected_refusal_behavior",
        "nrc_rag_citation_rubric",
        "nrc_rag_baseline_surface_set",
        "nrc_rag_no_adopt_threshold",
        "nrc_rag_dependency_provider_network_runtime_constraints",
    ):
        deferred[field] = "null"
    return deferred


def _issue_codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def test_current_fixture_authority_record_validates_as_pending() -> None:
    module = _load_validator()
    text = RECORD_PATH.read_text(encoding="utf-8")

    assert module.validate_text(text, "pending") == []
    assert "checkpoint_record_requires_nonpending_tool_status" in _issue_codes(
        module.validate_text(text, "checkpoint")
    )
    assert "selected_record_requires_selected_tool" in _issue_codes(
        module.validate_text(text, "selected")
    )
    assert "frozen_record_requires_selected_tool" in _issue_codes(
        module.validate_text(text, "frozen")
    )


def test_selected_and_frozen_fixture_records_have_distinct_freeze_expectations() -> None:
    module = _load_validator()
    selected_values = _selected_values(module)

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


def test_checkpoint_record_validates_as_no_runtime_nonselection() -> None:
    module = _load_validator()
    values = _checkpoint_values(module)

    assert values["selection_complete"] == "false"
    assert values["implementation_entry_freeze_written"] == "false"
    assert module.validate_text(_record_text(module, values), "checkpoint") == []
    assert "pending_tool_status_must_be_pending" in _issue_codes(
        module.validate_text(_record_text(module, values), "pending")
    )
    assert "selected_record_requires_selected_tool" in _issue_codes(
        module.validate_text(_record_text(module, values), "selected")
    )
    assert "frozen_record_requires_selected_tool" in _issue_codes(
        module.validate_text(_record_text(module, values), "frozen")
    )


def test_checkpoint_record_rejects_selected_tools_and_fixture_fields() -> None:
    module = _load_validator()
    values = _checkpoint_values(module)
    values["tabpfn_fixture_authority_status"] = "selected"
    values["tabpfn_target_column"] = "comb08"

    issue_codes = _issue_codes(module.validate_text(_record_text(module, values), "checkpoint"))
    assert "checkpoint_record_must_not_select_tool" in issue_codes
    assert "checkpoint_field_must_be_null" in issue_codes


def test_candidate_checkpoint_file_validates_only_as_checkpoint() -> None:
    module = _load_validator()
    text = CHECKPOINT_RECORD_PATH.read_text(encoding="utf-8")

    assert module.validate_text(text, "checkpoint") == []
    assert "pending_tool_status_must_be_pending" in _issue_codes(
        module.validate_text(text, "pending")
    )
    assert "selected_record_requires_selected_tool" in _issue_codes(
        module.validate_text(text, "selected")
    )
    assert "frozen_record_requires_selected_tool" in _issue_codes(
        module.validate_text(text, "frozen")
    )


def test_per_tool_selected_tabpfn_with_nrc_deferred_stays_pre_freeze() -> None:
    module = _load_validator()
    values = _defer_nrc_rag(_selected_values(module))

    assert values["selection_complete"] == "true"
    assert values["implementation_entry_freeze_written"] == "false"
    assert module.validate_text(_record_text(module, values), "selected") == []
    assert "frozen_freeze_written_must_be_true" in _issue_codes(
        module.validate_text(_record_text(module, values), "frozen")
    )


def test_per_tool_selected_nrc_with_tabpfn_deferred_stays_pre_freeze() -> None:
    module = _load_validator()
    values = _defer_tabpfn(_selected_values(module))

    assert values["selection_complete"] == "true"
    assert values["implementation_entry_freeze_written"] == "false"
    assert module.validate_text(_record_text(module, values), "selected") == []
    assert "frozen_freeze_written_must_be_true" in _issue_codes(
        module.validate_text(_record_text(module, values), "frozen")
    )


def test_fixture_record_rejects_runtime_or_network_admission() -> None:
    module = _load_validator()
    values = _selected_values(module)
    values["runtime_behavior_change"] = "true"
    values["network_or_provider_call_allowed"] = "true"

    assert "fixed_field_mismatch" in _issue_codes(
        module.validate_text(_record_text(module, values), "selected")
    )


def test_selected_tool_must_fill_all_required_fields() -> None:
    module = _load_validator()
    values = _defer_nrc_rag(_selected_values(module))
    values["tabpfn_target_column"] = "null"

    assert "selected_field_must_be_filled" in _issue_codes(
        module.validate_text(_record_text(module, values), "selected")
    )


def test_nonselected_tool_fields_must_remain_null() -> None:
    module = _load_validator()
    values = _defer_nrc_rag(_selected_values(module))
    values["nrc_rag_query_ids"] = "q1,q2"

    assert "nonselected_tool_field_must_be_null" in _issue_codes(
        module.validate_text(_record_text(module, values), "selected")
    )


def test_fixture_record_rejects_invalid_selected_tool_fixture_fields() -> None:
    module = _load_validator()
    values = _selected_values(module)
    values["tabpfn_fixture_kind"] = "generic_table"
    values["tabpfn_task_type"] = "forecast"
    values["nrc_rag_fixture_kind"] = "generic_queries"

    issue_codes = _issue_codes(module.validate_text(_record_text(module, values), "selected"))
    assert "invalid_tabpfn_fixture_kind" in issue_codes
    assert "invalid_tabpfn_task_type" in issue_codes
    assert "invalid_nrc_rag_fixture_kind" in issue_codes


def test_duplicate_structured_fixture_authority_key_fails_closed() -> None:
    module = _load_validator()
    values = _pending_values(module)
    text = _record_text(module, values).replace(
        "tabpfn_fixture_authority: null",
        "tabpfn_fixture_authority: null\ntabpfn_fixture_authority: null",
    )

    assert "duplicate_key" in _issue_codes(module.validate_text(text, "pending"))
