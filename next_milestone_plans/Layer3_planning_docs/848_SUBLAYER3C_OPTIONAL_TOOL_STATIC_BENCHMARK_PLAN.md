# 848 - Sublayer 3C Optional Tool Static Benchmark Plan

## Status

Status: no-runtime static benchmark-planning freeze for `sublayer3c_optional_tool_static_benchmark_plan`.

Doc: `848_SUBLAYER3C_OPTIONAL_TOOL_STATIC_BENCHMARK_PLAN.md`.

Branch: `codex/l3-optional-tool-static-benchmark-plan`.

Current-main preflight checkpoint: `c01bed789b4ba4f83fa1bc7899dd85ba3348085f`.

Selected from posture: `select_sublayer3c_optional_tool_static_benchmark_plan_or_stop_for_product_authority`.

Decision: `plan_combined_tabpfn_and_nrc_rag_static_benchmarks_no_runtime`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this plan: `false`.

## Purpose

This plan defines the no-runtime benchmark-planning envelope for both accepted Sublayer 3C optional-tool candidates:

- TabPFN as an optional supervised tabular predictive-method candidate; and
- nrc-licensing-rag as an optional regulatory-context retrieval/grounding candidate.

This plan does not run benchmarks. It does not create benchmark fixtures, fixture data, provider credentials, model calls, vector stores, routes, rendered controls, package/handoff/export/download integrations, or readiness states.

The only admitted work in this lane is static planning: use-site selection rules, fixture schema, baseline families, metrics, no-adopt thresholds, runtime-isolation requirements, and the next authority gate.

## Canonical Source Of Truth

Live source, tests, manifests, current-main review/check state, and repo-native validation remain authority.

The governing planning/control chain is:

- `844_PUBLIC_URL_DELIVERY_SUBLAYER3C_PREREQUISITE_CLOSEOUT.md`;
- `845_SUBLAYER3C_OPTIONAL_TOOL_PLANNING_INDEX_ADR_GATE.md`;
- `846_TABPFN_SUBLAYER3C_OPTIONAL_PREDICTIVE_METHOD_ADR.md`;
- `847_NRC_RAG_SUBLAYER3C_OPTIONAL_TOOL_ADR.md`;
- `backend/app/services/layer3_pass_entry.py`;
- `backend/app/services/analysis.py`;
- `backend/app/services/layer3_source_directory_text_retrieval.py`;
- `backend/app/services/layer3_source_directory_vector_retrieval.py`;
- `backend/app/services/layer3_source_directory_hybrid_context.py`;
- `backend/app/services/layer3_source_directory_hybrid_analysis.py`;
- `backend/tests/test_layer3_pass_entry.py`; and
- the source-directory retrieval, context, and qualitative-analysis tests.

The accepted planning packs remain planning context only:

- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_tabpfn_sublayer3c_tool_planning_pack`;
- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_nrc_rag_sublayer3c_tool_planning_pack`.

## Shared Benchmark Planning Contract

Any future benchmark-execution lane must first materialize a benchmark plan with these fields, without running the candidate tools:

- `benchmark_plan_schema_id`: `layer3.sublayer3c_optional_tool_static_benchmark_plan.v1`;
- `benchmark_case_id`: stable deterministic identifier;
- `candidate_tool`: `tabpfn` or `nrc_licensing_rag`;
- `current_main_use_site`: one of the exact admitted use-sites in this document;
- `source_authority`: current-main file, service, test, or manually reviewed fixture authority;
- `fixture_kind`: one of the exact fixture kinds in this document;
- `baseline_family`: one of the exact current-main or simple deterministic baselines in this document;
- `metric_family`: predeclared metric family;
- `no_adopt_threshold`: measurable threshold below which the candidate is no-adopted;
- `runtime_isolation_required`: `true`;
- `default_dependency_allowed`: `false`;
- `network_or_provider_call_allowed`: `false`;
- `package_handoff_export_download_allowed`: `false`; and
- `readiness_or_runtime_gate_required_before_execution`: `true`.

The benchmark plan must fail closed if any of these fields are missing, ambiguous, request-supplied by an operator, or inconsistent with current-main authority.

## TabPFN Static Benchmark Plan

### Admitted Candidate Use-Sites

TabPFN benchmark planning may consider only these current-main quantitative use-sites:

- `quantitative_single_item_dataset_version`;
- `quantitative_associated_cohort_dataset_version`;
- engine family `wrapped_quantitative_analysis`.

The current-main supported method baseline set is:

- `cross_correlation`;
- `descriptive_summary`;
- `decomposition`;
- `structural_break`.

TabPFN is not admitted for qualitative APS, source-directory qualitative analysis, NRC RAG, connector, provider URL, package/handoff/export/download, signed-reference, rendered UI, or agent tool-call use.

### Fixture Schema

TabPFN benchmark planning may define only static fixture metadata. It may not create, download, or execute fixture data in this lane.

Required fixture metadata:

- `fixture_kind`: `dataset_version_supervised_tabular_micro_fixture`;
- `dataset_version_authority`: current-main dataset-version-backed source or later manually reviewed fixture authority;
- `target_column_declared`: `true`;
- `feature_columns_declared`: `true`;
- `train_test_split_declared`: `true`;
- `leakage_checks_declared`: `true`;
- `row_count_band`: bounded small fixture class, not full-corpus execution;
- `task_type`: `classification` or `regression`;
- `metric_family`: `accuracy_or_auc` for classification, `mae_or_rmse` for regression; and
- `fixture_materialization_status`: `not_materialized_by_this_plan`.

If no current-main or later-authorized fixture can declare a target column, feature columns, and leakage checks, the benchmark path must stop with `no_adopt_tabpfn_for_absent_supervised_fixture_authority`.

### Baselines And Thresholds

TabPFN must be compared against simpler project6-native or simple deterministic baselines before any runtime can be considered:

- existing wrapped quantitative method output where applicable;
- trivial majority-class, mean, median, persistence, or descriptive baseline where applicable;
- project6 dataset-version provenance and split metadata; and
- a predeclared minimum marginal improvement threshold.

Minimum no-adopt rule:

- If TabPFN cannot beat the selected simple baseline by a predeclared margin on the selected metric, result is `no_adopt_tabpfn_for_sublayer3c_optional_predictive_method`.
- If TabPFN requires default dependency installation, hidden checkpoint download, token handling, browser login, cache writes outside an admitted runtime root, or commercial/production license authority not present in current main, result is `no_adopt_or_readiness_unavailable_tabpfn`.

## NRC RAG Static Benchmark Plan

### Admitted Candidate Use-Sites

NRC RAG benchmark planning may consider only these current-main regulatory-context comparison surfaces:

- `source_directory_material_preview`;
- `source_directory_vector_retrieval`;
- `source_directory_hybrid_context_packet`;
- `source_directory_qualitative_hybrid_analysis`;
- `source_directory_hybrid_context_packet_qualitative_analysis`.

NRC RAG is not admitted for provider URL delivery, provider-private signed URL, connector dispatch, external vector-store runtime, OpenAI/Claude provider runtime, package mutation, handoff/export/download rewrite, signed-reference integration, rendered retrieval controls, quantitative method selection, or agent tool-call use.

### Fixture Schema

NRC RAG benchmark planning may define only static query-set metadata. It may not load Chroma, OpenAI embeddings, external datasets, or vector stores in this lane.

Required fixture metadata:

- `fixture_kind`: `regulatory_context_grounding_query_set`;
- `query_set_authority`: current-main source-directory corpus or later manually reviewed query-set authority;
- `query_id`: stable deterministic identifier;
- `query_text`: fixed query text;
- `answerability`: `answerable` or `unsupported_by_corpus`;
- `expected_source_identifiers_declared`: `true`;
- `expected_source_spans_declared`: `true` when answerable;
- `expected_refusal_behavior_declared`: `true` when unsupported;
- `citation_rubric_declared`: `true`;
- `baseline_surface_set_declared`: `true`; and
- `fixture_materialization_status`: `not_materialized_by_this_plan`.

If no current-main or later-authorized query set can declare expected source identifiers, source spans, and unsupported-query behavior, the benchmark path must stop with `no_adopt_nrc_rag_for_absent_query_set_authority`.

### Baselines And Thresholds

NRC RAG must be compared against current project6-native retrieval and analysis surfaces before any runtime can be considered:

- current source-directory lexical retrieval;
- current deterministic local hash vector retrieval;
- current hybrid context packet;
- current qualitative hybrid analysis output;
- citation/source-span recall at fixed `k`;
- citation precision and source-grounding quality;
- unsupported-query refusal behavior; and
- a predeclared minimum marginal improvement threshold.

Minimum no-adopt rule:

- If nrc-licensing-rag cannot provide measurable marginal value over project6-native source-directory/vector/hybrid surfaces on the selected source-grounding metrics, result is `no_adopt_nrc_rag_for_sublayer3c_optional_tool_use`.
- If nrc-licensing-rag requires default Chroma/OpenAI/Claude dependency installation, hidden embedding calls, vector-store startup, corpus download, provider credentials, network egress, or source-authority promotion not present in current main, result is `no_adopt_or_readiness_unavailable_nrc_rag`.

## Execution Gate Required Before Any Benchmark Run

A later benchmark-execution freeze is required before any candidate tool can run.

That later freeze must decide, at minimum:

- exact benchmark fixture authority;
- exact runtime root and cache boundaries;
- whether external dependencies are permitted in an isolated optional environment;
- whether any provider credential, model token, embedding call, checkpoint download, or network egress is permitted;
- how outputs are stored, redacted, or discarded;
- how no-adopt results are recorded;
- how base project6 works without optional dependencies installed; and
- how CI proves fail-closed behavior.

Without that later freeze, benchmark execution remains forbidden.

## Non-Admission Boundary

This plan admits no runtime behavior, benchmark execution, fixture data creation, fixture materialization, backend route, API DTO, response model, database model, migration, dependency, package installation, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, embedding call, vector-store startup, corpus download, Chroma runtime, OpenAI/Claude/provider runtime, no TabPFN runtime, no TabPFN dependency, no TabPFN fit/predict execution, no TabPFN checkpoint loading, no nrc-licensing-rag dependency, no NRC RAG runtime, or auth/security behavior change.

## Validation Basis

Required validation for this plan:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime test is required for this plan because no runtime behavior, route, dependency, fixture data, or UI behavior is changed.

## Next Posture

The next exact posture is `select_optional_tool_benchmark_fixture_authority_or_stop_for_product_authority`.

The next PR should either:

- choose exact static benchmark fixture authority for both tools while remaining no-runtime; or
- record that product/fixture authority is insufficient and stop optional-tool benchmark progression.
