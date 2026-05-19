# 870 - Optional Tool Authority Revalidation Selection

## Status

Status: no-runtime current-main selection control for `sublayer3c_optional_tool_fixture_authority_revalidation_after_analysis_environment_sync`.

Selection doc: `870_OPTIONAL_TOOL_AUTHORITY_REVALIDATION_SELECTION.md`.

Predecessor current-main sync doc: `869_DOWNSTREAM_ANALYSIS_ENVIRONMENT_RENDERED_PROJECTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this selection: `cbf084839573b70880a478eea43705770170ef8a`.

Selected gap: `sublayer3c_optional_tool_fixture_authority_revalidation_after_analysis_environment_sync`.

Decision: `keep_optional_tool_benchmark_runtime_blocked_until_product_fixture_authority`.

Runtime behavior introduced by this selection: `false`.

Benchmark execution introduced by this selection: `false`.

Fixture materialization introduced by this selection: `false`.

Fixture authority selection introduced by this selection: `false`.

Implementation-entry allowed next: `false`.

## Current-Main Evidence

Current main now contains the bounded downstream Analysis Environment rendered projection runtime from doc `869`, but that runtime is read-only UI projection over `State.sessionSummary.analysis_environment_projection`. It does not select optional-tool benchmark fixtures, does not run TabPFN, does not run NRC RAG, and does not admit optional-tool Gate C or pass-entry behavior.

The canonical optional-tool authority remains:

- `850_FIXTURE_VALIDATE_ONLY.md` as the pending validate-only fixture-authority record;
- `851_FIXTURE_CHECKPOINT.md` as the no-runtime deferred-authority checkpoint;
- `tools/l3-fixture-validate.py` as the fail-closed validator for `pending`, `checkpoint`, `selected`, and `frozen` states; and
- `backend/tests/test_layer3_fixture_validate.py` as focused validator coverage.

The current `850` record still validates only as `pending`. The current `851` checkpoint still validates as `checkpoint`. Neither record selects a TabPFN supervised micro-fixture or an NRC RAG regulatory query set.

## Selection Result

Optional-tool benchmark progression remains blocked.

TabPFN remains candidate-supported but not selected because current main does not contain product-approved supervised micro-fixture authority with a fixed row basis, target column, feature columns, train/test split, leakage checks, metric family, baseline family, and no-adopt threshold.

NRC RAG remains deferred for absent query-set authority because current main does not contain product-approved fixed query ids, query texts, answerability labels, expected source identifiers, expected spans, unsupported-query refusal behavior, citation rubric, baseline surface set, and no-adopt threshold.

This selection does not no-adopt either tool as a product. It no-adopts runtime progression under current authority until a later current-main record reaches `selected` or `frozen` validator state with exact product authority.

## Non-Admission Boundary

This selection admits no runtime behavior, benchmark execution, fixture data creation, fixture materialization, fixture selection, backend route, API DTO, response model, database model, migration, dependency, package installation, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, hidden model call, cloud/API inference, embedding call, vector-store startup, corpus download, Chroma runtime, OpenAI/Claude/provider runtime, TabPFN runtime, TabPFN dependency, TabPFN fit/predict execution, TabPFN checkpoint loading, nrc-licensing-rag dependency, NRC RAG runtime, or auth/security behavior change.

## Required Future Authority

A future optional-tool lane may proceed only if it first updates or introduces a fixture-authority record that passes `tools/l3-fixture-validate.py` with either:

- `--expect selected`, for a product-authority selection that names at least one selected tool while keeping `implementation_entry_freeze_written: false`; or
- `--expect frozen`, for a separate implementation-entry freeze with no pending tools, `selection_complete: true`, and `implementation_entry_freeze_written: true`.

Until then, optional-tool benchmark execution, dependency installation, rendered controls, package/handoff/export/download integration, and Gate C/pass-entry admission remain blocked.

## Validation Basis

Required validation for this selection:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-fixture-validate.py --expect pending`;
- `python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py .\tools\l3-fixture-validate.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime or browser test is required for this selection because it changes no runtime behavior, route, dependency, fixture data, or rendered UI behavior.

## Next Posture

The next exact posture is `select_next_non_optional_tool_layer3_end_to_end_gap_after_optional_tool_authority_revalidation`.

Do not implement optional-tool runtime, benchmarks, dependencies, rendered controls, or Gate C/pass-entry integration until product authority supplies an exact selected or frozen fixture-authority record and that record is current-main selected, review-cleared, and checker-backed.
