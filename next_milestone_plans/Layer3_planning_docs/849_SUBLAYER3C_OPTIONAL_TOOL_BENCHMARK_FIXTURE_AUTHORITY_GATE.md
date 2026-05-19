# 849 - Sublayer 3C Optional Tool Benchmark Fixture Authority Gate

## Status

Status: no-runtime fixture-authority gate for `sublayer3c_optional_tool_benchmark_fixture_authority_gate`.

Doc: `849_SUBLAYER3C_OPTIONAL_TOOL_BENCHMARK_FIXTURE_AUTHORITY_GATE.md`.

Branch: `codex/l3-optional-tool-fixture-authority-gate`.

Current-main preflight checkpoint: `d79b832a884ada38a471a2d42991cf31d3cd09ee`.

Selected from posture: `select_optional_tool_benchmark_fixture_authority_or_stop_for_product_authority`.

Decision: `stop_optional_tool_benchmark_progression_until_fixture_authority_selected`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this gate: `false`.

Benchmark execution introduced by this gate: `false`.

Fixture materialization introduced by this gate: `false`.

## Purpose

Doc 848 selected a combined static benchmark plan for TabPFN and NRC RAG. That plan required the next lane to choose exact fixture authority for both optional-tool candidates or stop for product authority.

This gate records the stop condition. Current main does not yet contain the exact fixture authority required to execute, even in an isolated benchmark lane, either optional-tool candidate.

This gate does not no-adopt TabPFN or NRC RAG as products. It no-adopts runtime progression under current authority until a later current-main freeze selects exact benchmark fixture authority.

## Canonical Source Of Truth

Live source, tests, manifests, current-main review/check state, and repo-native validation remain authority.

The current-main evidence inspected for this gate is:

- `next_milestone_plans/Layer3_planning_docs/848_SUBLAYER3C_OPTIONAL_TOOL_STATIC_BENCHMARK_PLAN.md`;
- `backend/app/services/analysis.py`;
- `backend/app/services/layer3_pass_entry.py`;
- `backend/tests/test_layer3_pass_entry.py`;
- `backend/tests/test_layer3_source_directory_context_packet.py`;
- `backend/tests/test_layer3_source_directory_qualitative_analysis.py`;
- `backend/tests/test_layer3_source_directory_vector_retrieval.py`;
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`; and
- `tests/fixtures/nrc_aps_replay/v1/index.json`.

The relevant manifests are intentionally scoped Layer 3 progress/proof ledgers, not exhaustive indexes. This pass validates only the declared no-runtime gate and the directly relevant current-main evidence.

## Fixture Authority Decision

Fixture authority status: `absent_current_main_authority`.

Selected TabPFN benchmark fixture authority: `none`.

Selected NRC RAG benchmark fixture authority: `none`.

Selected runtime or benchmark execution lane: `none`.

Result: `optional_tool_benchmark_fixture_authority_not_selected`.

Reason: current main contains useful candidate surfaces and tests, but not the exact benchmark fixture authority Doc 848 requires.

## TabPFN Fixture Authority Finding

TabPFN remains limited to planning around:

- `quantitative_single_item_dataset_version`;
- `quantitative_associated_cohort_dataset_version`; and
- `wrapped_quantitative_analysis`.

Current main supports deterministic wrapped quantitative analysis methods:

- `cross_correlation`;
- `descriptive_summary`;
- `decomposition`; and
- `structural_break`.

Current-main quantitative fixtures and tests seed time-series or descriptive dataset versions with fields such as `observed_at`, `value`, category/dimension fields, profile rows, and associated-cohort source dataset-version ids. They prove current Layer 3 quantitative pass-entry and execution behavior.

They do not provide Doc 848's required supervised predictive fixture authority:

- no selected `target_column_declared`;
- no selected `feature_columns_declared`;
- no selected `train_test_split_declared`;
- no selected `leakage_checks_declared`;
- no selected `classification` or `regression` benchmark case; and
- no selected TabPFN no-adopt threshold tied to a concrete supervised micro-fixture.

Therefore TabPFN benchmark execution remains blocked with `no_adopt_tabpfn_for_absent_supervised_fixture_authority` under current main.

## NRC RAG Fixture Authority Finding

NRC RAG remains limited to planning around:

- `source_directory_material_preview`;
- `source_directory_vector_retrieval`;
- `source_directory_hybrid_context_packet`;
- `source_directory_qualitative_hybrid_analysis`; and
- `source_directory_hybrid_context_packet_qualitative_analysis`.

Current-main source-directory tests prove deterministic local source-directory scan, material admission, lexical retrieval, local hash-vector retrieval, hybrid context, qualitative extraction, package preparation, and export/download delivery behavior over controlled toy text such as `alpha beta` fixtures.

The repo also contains NRC APS fixture and replay assets. Those assets are not current-main source-directory benchmark query-set authority for nrc-licensing-rag, and this gate does not promote them into that role.

Current main does not provide Doc 848's required regulatory grounding query-set authority:

- no selected `query_set_authority`;
- no selected fixed query set with stable benchmark case ids;
- no selected `answerability` labels;
- no selected expected source identifiers;
- no selected expected source spans;
- no selected unsupported-query refusal behavior;
- no selected citation rubric; and
- no selected baseline surface set declared as a benchmark fixture.

Therefore NRC RAG benchmark execution remains blocked with `no_adopt_nrc_rag_for_absent_query_set_authority` under current main.

## Later Authority Required

A later fixture-selection freeze may reopen this lane only if it selects exact repo-owned or manually reviewed fixture authority.

For TabPFN, the later freeze must name:

- exact fixture file or current-main source authority;
- target column;
- feature columns;
- task type;
- train/test split;
- leakage checks;
- row-count band;
- metric family;
- simple baseline;
- no-adopt threshold; and
- license/dependency/runtime constraints.

For NRC RAG, the later freeze must name:

- exact query-set file or current-main source authority;
- query ids and fixed query text;
- answerability labels;
- expected source identifiers;
- expected source spans for answerable queries;
- expected refusal behavior for unsupported queries;
- citation rubric;
- baseline surface set;
- no-adopt threshold; and
- dependency/provider/network/runtime constraints.

## Non-Admission Boundary

This gate admits no runtime behavior, benchmark execution, fixture data creation, fixture materialization, fixture selection, backend route, API DTO, response model, database model, migration, dependency, package installation, provider adapter, provider credential, network egress, rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, embedding call, vector-store startup, corpus download, Chroma runtime, OpenAI/Claude/provider runtime, no TabPFN runtime, TabPFN dependency, TabPFN fit/predict execution, TabPFN checkpoint loading, nrc-licensing-rag dependency, no NRC RAG runtime, or auth/security behavior change.

## Validation Basis

Required validation for this gate:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime test is required for this gate because no runtime behavior, route, dependency, fixture data, or UI behavior is changed.

## Next Posture

The next exact posture is `await_product_authority_for_optional_tool_benchmark_fixture_selection`.

A future lane may either:

- select exact fixture authority for TabPFN and NRC RAG while remaining no-runtime; or
- pivot away from optional-tool benchmark progression to a different deferred Layer 3 lane if product authority for benchmark fixtures remains absent.
