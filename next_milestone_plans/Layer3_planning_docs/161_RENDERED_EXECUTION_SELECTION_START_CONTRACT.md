# Rendered Execution Selection/Start Contract

Status: planning/control UI and API contract for `160_RENDERED_EXECUTION_SELECTION_START_FREEZE.md`.

This contract specifies the only future rendered control pass currently selected for moving the raw mixed `/review/layer3` UI past plan approval. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_execution_selection_start_controls`.

The future implementation may only add rendered operator controls for:

- `POST /api/v1/layer3/execution/select`
- `POST /api/v1/layer3/execution/start`

It must reuse the existing backend contracts:

- request DTO `Layer3ExecutionSelectionRequest`
- response schema `Layer3ExecutionSelectionResponse`
- request DTO `Layer3AnalysisExecutionStartRequest`
- response schema `Layer3AnalysisExecutionStartResponse`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package lifecycle, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, or auth/security behavior.

## Execution Selection Request

The rendered execution selection request must be assembled from server-backed state:

- `client_request_id`: new browser-generated request id for this operator action;
- `session_id`: current server-created Layer 3 session id;
- `analysis_plan_id`: id returned by plan approval for the current session;
- `preview_id`: current approved plan preview id;
- `preview_hash`: current approved plan preview hash;
- `operator_reason`: optional operator note if a rendered note field is added.

The browser must not include or infer deferred fields: `execute`, `execution`, `run`, `run_analysis`, `start_execution`, `analysis_run_id`, `analysis_run_ids`, `result_review`, `results`, `package`, `package_review`, `handoff`, `artifact_manifest`, `local_upload`, `local_directory`, `rag_plan`, `vector_plan`, `qualitative_plan`, or `hybrid_plan`.

Expected response fields that the UI may consume:

- `schema_id`
- `session_id`
- `analysis_plan_id`
- `preview_identity`
- `pass_run_ids`
- `pass_run_count`
- `execution_started`
- `analysis_run_ids`
- `pass_run_statuses`
- `downstream_unavailable`
- `next_state`
- `authority_rail`

The response is authoritative for selected pass runs. Browser state may display the response, but there must be no frontend-only durable authority.

## Execution Start Request

The rendered execution start request must be assembled only after selection response authority exists:

- `client_request_id`: new browser-generated request id for this operator action;
- `session_id`: same current server session id;
- `analysis_plan_id`: same approved plan id;
- `pass_run_id`: one id returned in `pass_run_ids` by execution selection;
- `preview_id`: same approved plan preview id;
- `preview_hash`: same approved plan preview hash;
- `execution_mode`: optional, and if present must be `synchronous_single_pass`;
- `operator_reason`: optional operator note if a rendered note field is added.

The browser must not include or infer deferred fields: `run_all`, `batch`, `package`, `package_review`, `handoff`, `result_review`, `local_upload`, `local_directory`, `rag_plan`, `vector_plan`, `qualitative_plan`, `hybrid_plan`, `approved_plan_supersession`, `schema_migration`, `artifact_manifest`, `results`, `source_expansion`, or `schema_widening`.

Expected response fields that the UI may consume:

- `schema_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_identity`
- `execution_started`
- `analysis_run_id`
- `pass_run_status`
- `output_payload_ref`
- `output_payload_hash`
- `downstream_unavailable`
- `next_state`
- `authority_rail`
- `selected_pass_scope`
- `selected_pass_type`
- `selected_method_name`
- `dataset_version_id`

The start response may unlock existing result-status inspection only when server state says execution has started. It must not unlock result review, package review, handoff/export, APS dispatch, or external export/download without each existing downstream server precondition.

## Rendered State Model

The future UI state must use these phases:

- `not_ready`: no approved plan for the current session;
- `ready_to_select`: approved plan and matching preview identity are present;
- `selecting`: request to `/execution/select` is pending;
- `selected`: response supplies `pass_run_ids` and `pass_run_count`;
- `starting`: request to `/execution/start` is pending for one selected pass run;
- `started`: response confirms `execution_started`;
- `blocked`: server error, stale preview, missing plan, revision/cancel state, forbidden field, unsupported mode, or pass-run mismatch.

The UI must preserve existing disabled states for result/package/handoff controls until the correct server-backed phase is reached. An error in selection or start must not unlock downstream controls.

## Selector and Layout Contract

Future selectors must be stable and explicit:

- `#execution-select`
- `#execution-start`
- `#execution-selection-start-panel`

The controls must be keyboard focusable, have visible labels, and have aria-live status for request progress/errors. They must fit the existing workbench composition and must not place a card inside another card. They must not overlap step chips, result review controls, package controls, handoff controls, or external export/download controls across desktop and mobile viewports.

## Theme Contract

The controls must inherit the existing Layer 3 theme system:

- shared `light`;
- shared `dark`;
- Layer 3 `workbench`;
- existing `system` resolution;
- no change to `claude` prototype routing.

The implementation must not create a new theme family or alter existing theme preference storage semantics. It must prove visible focus, disabled contrast, loading state, success state, blocked/error state, and text fit in `light`, `dark`, and `workbench`.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through rendered controls or approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization/seed setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval;
- click rendered execution selection;
- use only returned `pass_run_ids` to click rendered execution start;
- assert `/execution/select` and `/execution/start` requests contain only admitted fields;
- assert no package, handoff, APS dispatch, external export/download, provider URL, connector dispatch, RAG/vector, upload, directory, hidden LLM, mockup, or auth/security behavior appears;
- run headed and headless Chromium sequentially on the fixed-port `8031` harness unless a later freeze changes the harness.

## Negative Invariants

The implementation must keep these blocked:

- backend route, DTO, service, model, or migration change;
- source family expansion beyond current admitted classes;
- source adapter registry;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- broad package mutation or reconstruction;
- package payload rewrite outside admitted package commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Required Validation for Future Implementation

At minimum, the future implementation must run:

- `python .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_page.py -q`
- a focused Playwright test proving rendered raw mixed execution selection/start;
- the same focused Playwright test in headed Chromium;
- `npx playwright test e2e/layer3-workbench.spec.js` if feasible;
- `git diff --check`

The future pass should stop at execution start/result-status eligibility unless it separately proves the existing rendered downstream controls can continue without new controls or hidden API calls.

## Acceptance Criteria

This contract is accepted only when:

- this file exists and names `Layer3ExecutionSelectionRequest`, `Layer3ExecutionSelectionResponse`, `Layer3AnalysisExecutionStartRequest`, and `Layer3AnalysisExecutionStartResponse`;
- it names `POST /api/v1/layer3/execution/select` and `POST /api/v1/layer3/execution/start`;
- it records exact admitted request fields and deferred forbidden fields;
- it records the `light`, `dark`, and `workbench` theme proof obligation;
- progress/proof manifests, progress board, and `tools/l3-progress-check.py` reference it;
- `python .\tools\l3-progress-check.py` passes.
