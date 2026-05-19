# 850 - Fixture Authority Validate Only

## Status

Status: validate-only fixture-authority record contract for `sublayer3c_optional_tool_benchmark_fixture_authority_selection`.

Doc: `850_FIXTURE_VALIDATE_ONLY.md`.

Branch: `codex/l3-fixture-authority-validator`.

Current-main preflight checkpoint: `ccad39c85ec3257027a3706558a04f49f51ae13d`.

Prior gate: `849_SUBLAYER3C_OPTIONAL_TOOL_BENCHMARK_FIXTURE_AUTHORITY_GATE.md`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this validator: `false`.

Benchmark execution introduced by this validator: `false`.

Fixture materialization introduced by this validator: `false`.

Fixture authority selection introduced by this validator: `false`.

## Purpose

Doc 849 correctly stops optional-tool benchmark progression because current main does not yet select supervised TabPFN fixture authority or NRC RAG regulatory grounding query-set authority.

This validate-only pass makes the future fixture-authority selection record executable and fail-closed before any later freeze can claim that product authority exists. It does not fill fixture authority, choose benchmark cases, generate fixture data, run benchmarks, install optional dependencies, or admit runtime behavior.

The validator is `tools/l3-fixture-validate.py`. The focused tests are `backend/tests/test_layer3_fixture_validate.py`.

## Canonical Source Of Truth

Live current-main source, tests, progress/proof manifests, review/check state, and repo-native validation remain authority.

This record is intentionally scoped to the pending fixture-authority selection gate. It is not an exhaustive index of all future Sublayer 3C behavior.

The governing current-main context is:

- `848_SUBLAYER3C_OPTIONAL_TOOL_STATIC_BENCHMARK_PLAN.md`;
- `849_SUBLAYER3C_OPTIONAL_TOOL_BENCHMARK_FIXTURE_AUTHORITY_GATE.md`;
- `tools/l3-fixture-validate.py`; and
- `backend/tests/test_layer3_fixture_validate.py`.

## Structured Fixture Authority Record

The current record is pending. Selection fields remain `null`; control fields remain fail-closed.

```yaml
benchmark_fixture_authority_schema_id: layer3.sublayer3c_optional_tool_benchmark_fixture_authority.v1
candidate_tools: tabpfn,nrc_licensing_rag
runtime_isolation_required: true
default_dependency_allowed: false
network_or_provider_call_allowed: false
package_handoff_export_download_allowed: false
runtime_behavior_change: false
benchmark_execution_change: false
fixture_materialization_change: false
tabpfn_fixture_authority: null
tabpfn_source_authority: null
tabpfn_fixture_kind: null
tabpfn_target_column: null
tabpfn_feature_columns: null
tabpfn_task_type: null
tabpfn_train_test_split: null
tabpfn_leakage_checks: null
tabpfn_row_count_band: null
tabpfn_metric_family: null
tabpfn_baseline_family: null
tabpfn_no_adopt_threshold: null
tabpfn_license_dependency_runtime_constraints: null
nrc_rag_fixture_authority: null
nrc_rag_query_set_authority: null
nrc_rag_fixture_kind: null
nrc_rag_query_ids: null
nrc_rag_query_texts: null
nrc_rag_answerability_labels: null
nrc_rag_expected_source_identifiers: null
nrc_rag_expected_source_spans: null
nrc_rag_expected_refusal_behavior: null
nrc_rag_citation_rubric: null
nrc_rag_baseline_surface_set: null
nrc_rag_no_adopt_threshold: null
nrc_rag_dependency_provider_network_runtime_constraints: null
selection_complete: false
implementation_entry_freeze_written: false
```

## Validator States

`tools/l3-fixture-validate.py --expect pending` accepts only this pending posture:

- fixed schema and tool set are present;
- runtime isolation remains required;
- default dependency, provider/network, package/handoff/export/download, runtime behavior, benchmark execution, and fixture materialization remain false;
- all TabPFN and NRC RAG selection fields remain `null`;
- `selection_complete` is false; and
- `implementation_entry_freeze_written` is false.

`--expect selected` is reserved for a later product-authority record. It requires every TabPFN and NRC RAG selection field to be filled, keeps runtime/execution/materialization flags false, requires `selection_complete: true`, and requires `implementation_entry_freeze_written: false`.

`--expect frozen` is reserved for a later current-main implementation-entry freeze. It requires the same selected fixture authority fields, keeps runtime/execution/materialization flags false, requires `selection_complete: true`, and requires `implementation_entry_freeze_written: true`.

## Required Future Selection Fields

The later product-authority fill must include every TabPFN field:

- `tabpfn_fixture_authority`;
- `tabpfn_source_authority`;
- `tabpfn_fixture_kind`;
- `tabpfn_target_column`;
- `tabpfn_feature_columns`;
- `tabpfn_task_type`;
- `tabpfn_train_test_split`;
- `tabpfn_leakage_checks`;
- `tabpfn_row_count_band`;
- `tabpfn_metric_family`;
- `tabpfn_baseline_family`;
- `tabpfn_no_adopt_threshold`; and
- `tabpfn_license_dependency_runtime_constraints`.

The later product-authority fill must include every NRC RAG field:

- `nrc_rag_fixture_authority`;
- `nrc_rag_query_set_authority`;
- `nrc_rag_fixture_kind`;
- `nrc_rag_query_ids`;
- `nrc_rag_query_texts`;
- `nrc_rag_answerability_labels`;
- `nrc_rag_expected_source_identifiers`;
- `nrc_rag_expected_source_spans`;
- `nrc_rag_expected_refusal_behavior`;
- `nrc_rag_citation_rubric`;
- `nrc_rag_baseline_surface_set`;
- `nrc_rag_no_adopt_threshold`; and
- `nrc_rag_dependency_provider_network_runtime_constraints`.

The validator additionally fail-closes selected and frozen records unless:

- `tabpfn_fixture_kind` is exactly `dataset_version_supervised_tabular_micro_fixture`;
- `tabpfn_task_type` is exactly `classification` or `regression`;
- classification fixtures use `tabpfn_metric_family: accuracy_or_auc`;
- regression fixtures use `tabpfn_metric_family: mae_or_rmse`; and
- `nrc_rag_fixture_kind` is exactly `regulatory_context_grounding_query_set`.

## Non-Admission Boundary

This validate-only pass admits no runtime behavior, benchmark execution, fixture data creation, fixture materialization, fixture selection, backend route, API DTO, response model, database model, migration, dependency, package installation, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, embedding call, vector-store startup, corpus download, Chroma runtime, OpenAI/Claude/provider runtime, TabPFN runtime, TabPFN dependency, TabPFN fit/predict execution, TabPFN checkpoint loading, nrc-licensing-rag dependency, NRC RAG runtime, or auth/security behavior change.

## Validation Basis

Required validation for this pass:

- `python .\tools\l3-fixture-validate.py --expect pending`;
- `python -m pytest .\backend\tests\test_layer3_fixture_validate.py -q`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py .\tools\l3-fixture-validate.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

## Next Posture

The next exact posture remains `await_product_authority_for_optional_tool_benchmark_fixture_selection`.

A later lane may fill this record only when product authority selects exact fixture authority for both TabPFN and NRC RAG. Without that authority, optional-tool benchmark progression remains blocked.
