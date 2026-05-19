# 851 - Fixture Authority Checkpoint

## Status

Status: no-runtime fixture-authority checkpoint for `sublayer3c_optional_tool_benchmark_fixture_authority_selection`.

Doc: `851_FIXTURE_CHECKPOINT.md`.

Prior record: `850_FIXTURE_VALIDATE_ONLY.md`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this checkpoint: `false`.

Benchmark execution introduced by this checkpoint: `false`.

Fixture materialization introduced by this checkpoint: `false`.

Fixture authority selection introduced by this checkpoint: `false`.

## Purpose

This checkpoint records the current per-tool authority posture after inspecting the candidate package `layer3_ingress_to_insight_example_final_audited`. It preserves the default pending record in doc 850 and adds a separate fail-closed checkpoint record for the current known absence of exact fixture authority.

This checkpoint does not select TabPFN fixture authority, does not select NRC RAG query-set authority, does not create fixture rows, does not run benchmarks, does not install dependencies, does not admit runtime behavior, and does not write an implementation-entry freeze.

## Structured Fixture Authority Record

The checkpoint record is non-selected and non-frozen. Per-tool statuses record absent exact fixture/query-set authority, while all selection fields stay `null`.

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
tabpfn_fixture_authority_status: deferred_absent_fixture_authority
nrc_rag_fixture_authority_status: deferred_absent_fixture_authority
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

## TabPFN Candidate Proposal

TabPFN is candidate-supported but not selected.

Candidate source: `layer3_ingress_to_insight_example_final_audited/01_initial_received_ingress_objects/ING-0022__epa_fueleconomy_vehicles.csv`.

Candidate target: `comb08`.

Candidate task: `regression`.

Candidate feature columns: `year`, `cylinders`, `displ`, `drive`, `trany`, `VClass`, `fuelType1`, and `phevBlended`.

Candidate metric family: `mae_or_rmse`.

Candidate baseline family: `mean_or_median_baseline_plus_project6_wrapped_quantitative_if_applicable`.

Candidate no-adopt threshold: `no_adopt_unless_regression_reduces_mae_or_rmse_by_at_least_0_10_relative_to_baseline_without_runtime_policy_violation`.

Proposed micro row and split rule, not selected authority:

- start from source rows in `ING-0022__epa_fueleconomy_vehicles.csv` with non-null `comb08` and non-null candidate feature values;
- use the CSV data-row ordinal after the header as the stable source row ordinal;
- sort complete rows by `year` ascending, then stable source row ordinal ascending;
- choose a `micro_100_to_1000_rows` static fixture basis by taking the most recent 1000 complete rows after that ordering, unless later product authority selects a smaller reviewed under-250-row basis;
- split before normalization or encoding by deterministic temporal holdout: older 80 percent by `year` plus source row ordinal for train, newest 20 percent for test;
- exclude city and highway MPG fields, CO2 fields, fuel costs, scores, ids, row numbers, and target-derived proxy columns from features; and
- define duplicate-cross-split review by the tuple `year,cylinders,displ,drive,trany,VClass,fuelType1,phevBlended,comb08`, with any duplicate group kept entirely on one side of the split before later benchmark execution can be admitted.

The proposal above is a product-review target only. It does not authorize fixture materialization and does not make `tabpfn_fixture_authority_status: selected`.

## NRC RAG Authority Posture

NRC RAG remains deferred for absent query-set authority, not no-adopted. The package does not provide stable NRC RAG query ids, fixed query texts, answerability labels, expected source identifiers, expected source spans, unsupported-query refusal behavior tied to query ids, or a citation rubric tied to the package corpus.

Regulatory-looking package material is not NRC Licensing RAG authority and must not be converted into a query set without later product authority.

## Validator State

`tools/l3-fixture-validate.py --expect checkpoint` is a no-runtime checkpoint state. It requires at least one non-pending tool status, rejects selected tools, keeps every fixture/query-set field `null`, keeps `selection_complete: false`, and keeps `implementation_entry_freeze_written: false`.

The default doc 850 pending record remains the active current-main fixture-authority gate and should still pass `python .\tools\l3-fixture-validate.py --expect pending`.

This checkpoint should pass:

- `python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint`.

This checkpoint should not pass `pending`, `selected`, or `frozen` validation.

## Non-Admission Boundary

This checkpoint admits no runtime behavior, benchmark execution, fixture data creation, fixture materialization, fixture selection, backend route, API DTO, response model, database model, migration, dependency, package installation, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, embedding call, vector-store startup, corpus download, Chroma runtime, OpenAI/Claude/provider runtime, TabPFN runtime, TabPFN dependency, TabPFN fit/predict execution, TabPFN checkpoint loading, nrc-licensing-rag dependency, NRC RAG runtime, or auth/security behavior change.

## Next Posture

The next exact posture is `await_product_authority_for_tabpfn_micro_fixture_or_nrc_query_set_selection`.

A later lane may move TabPFN from candidate-supported to selected only after product authority explicitly accepts a static micro-fixture row basis, train/test split basis, and duplicate-cross-split/leakage rule. A later lane may move NRC RAG from deferred to selected only after product authority supplies fixed query ids, query texts, answerability labels, expected source identifiers, expected source spans, unsupported-query refusal behavior, and citation rubric.
