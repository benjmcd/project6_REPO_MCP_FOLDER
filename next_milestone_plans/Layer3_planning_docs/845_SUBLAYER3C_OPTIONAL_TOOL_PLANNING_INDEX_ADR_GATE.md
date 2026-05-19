# 845 - Sublayer 3C Optional Tool Planning Index ADR Gate

## Status

Status: planning/control index and ADR gate for `sublayer3c_optional_tool_planning_index_adr_gate`.

Doc: `845_SUBLAYER3C_OPTIONAL_TOOL_PLANNING_INDEX_ADR_GATE.md`.

Branch: `codex/l3-sublayer3c-optional-tool-adr-gate`.

Current-main preflight checkpoint: `0e192941f5a7a5b9f13cccf9eca99638ac5a3c70`.

Selected from posture: `select_sublayer3c_optional_tool_planning_index_or_adr_gate_after_public_url_delivery_prerequisite_closeout`.

Entry decision: `planning_index_and_adr_gate_only`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this index: `false`.

## Canonical Source Of Truth

Live source, tests, manifests, current-main review/check state, and repo-native validation remain authority.

The current public URL prerequisite authority is:

- `844_PUBLIC_URL_DELIVERY_SUBLAYER3C_PREREQUISITE_CLOSEOUT.md`;
- `795_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_CURRENT_MAIN_SYNC.md`;
- `backend/app/services/layer3_provider_public_url_delivery_use.py`;
- `backend/tests/test_layer3_provider_public_url_delivery_use.py`; and
- `backend/tests/test_layer3_provider_public_url_state.py`.

The current bounded source-directory and same-origin delivery authority is:

- `839_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CURRENT_MAIN_SYNC.md`;
- `841_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_DELIVERY_CONTROL_CURRENT_MAIN_SYNC.md`;
- `843_SERVER_CONFIGURED_SOURCE_DIRECTORY_INGESTION_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`;
- `backend/app/services/layer3_source_directory_ingestion.py`;
- `backend/app/services/layer3_source_directory_hybrid_analysis.py`;
- `backend/app/review_ui/static/layer3.html`; and
- `backend/app/review_ui/static/layer3.js`.

The accepted Sublayer 3C planning packs are planning context only:

- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_tabpfn_sublayer3c_tool_planning_pack`;
- `C:\Users\benny\Downloads\Planning_packs\accepted\l3_nrc_rag_sublayer3c_tool_planning_pack`.

Their pack manifests observed project6 through PR `#1449`. Current main has since landed PR `#1450`, which is the public URL delivery prerequisite closeout and introduces no runtime behavior. This index revalidates that drift and keeps the planning packs subordinate to live current-main source and proof.

## Planning Index Decision

The next admitted Sublayer 3C work is an evaluation-only ADR sequence for optional-tool candidates.

This index admits no optional-tool runtime. It only selects the decision path for whether the repo should evaluate or no-adopt each candidate before any readiness or implementation lane can exist.

Candidate ADR gates:

- `ADR: evaluate or no-adopt TabPFN for Layer 3 Sublayer 3C optional predictive-method use`;
- `ADR: evaluate or no-adopt nrc-licensing-rag for Layer 3 Sublayer 3C optional-tool use`.

Default posture before each ADR is `no_runtime_no_dependency_no_default_provider`.

Each ADR must decide whether the candidate deserves benchmark/evaluation planning or should be no-adopted. A later readiness-unavailable or runtime lane is blocked unless the relevant ADR first records exact current-main use-site authority, evaluation baselines, proof obligations, dependency isolation, and stop rules.

## Required ADR Content

The TabPFN ADR must include:

- exact already-authorized Sublayer 3C quantitative use-site candidates, if any;
- static inspection plan;
- candidate fixture definition;
- baseline comparison plan against simpler supervised project6-native baselines;
- license/output-use decision statement;
- proof that no runtime behavior changes;
- proof that no default dependency is added;
- explicit no causal/econometric claim boundary; and
- stop rules for no-adopt, readiness-unavailable, or later runtime-entry freeze.

The nrc-licensing-rag ADR must include:

- exact already-authorized Sublayer 3C regulatory-context use-site candidates, if any;
- static inspection plan;
- fixed benchmark query-set plan;
- comparison baseline against project6-native source-directory, vector, hybrid, and qualitative-analysis surfaces;
- source-authority non-promotion statement;
- proof that no runtime behavior changes;
- proof that no default dependency is added;
- explicit no quantitative method-selection influence boundary; and
- stop rules for no-adopt, readiness-unavailable, or later runtime-entry freeze.

## Non-Admission Boundary

This index admits no runtime behavior, backend route, API DTO, response model, database model, migration, dependency, provider adapter, provider credential, network egress, no rendered optional-tool controls, frontend durable authority, connector dispatch, agent tool-call runtime, package mutation, handoff/export/download integration, signed-reference integration, Gate C/pass-entry admission, source-authority promotion, quantitative method-selection behavior, hidden model call, cloud/API inference, checkpoint loading, hidden download, or auth/security behavior change.

This index specifically admits no TabPFN runtime, no TabPFN dependency, no TabPFN fit/predict execution, no TabPFN model/checkpoint loading, no TabPFN cloud/API inference, no request-owned TabPFN runtime settings, and no causal/econometric claims.

This index specifically admits no NRC RAG runtime, no nrc-licensing-rag dependency, no Chroma/vector provider runtime, no OpenAI/Claude/provider runtime, no new Layer 3 retrieval endpoint, no rendered retrieval controls, no source-authority promotion, no quantitative method-selection influence, and no package/handoff/export/download use.

## Validation Basis

Required validation for this index:

- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- JSON validation for `layer3_progress_manifest.json` and `layer3_workbench_proof_manifest.json`; and
- `git diff --check`.

No runtime test is required for this index because no runtime behavior, route, dependency, or UI behavior is changed.

## Next Posture

The next exact posture is `select_first_sublayer3c_optional_tool_adr_from_planning_index`.

The next PR should be one evaluation-only ADR for TabPFN or nrc-licensing-rag unless current-main authority changes before that PR starts.
