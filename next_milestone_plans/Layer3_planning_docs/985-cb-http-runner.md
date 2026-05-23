# 985 - Candidate B Live HTTP Operator Runner

## Purpose

Admit the smaller live-server execution path for the Candidate B full-corpus operator workflow.

The selected path is a governed `live-http` operator runner mode, not a new server-side orchestration API. This keeps the workflow on the already-admitted Layer 3 API chain while removing the requirement that the runner execute through `TestClient`, dependency overrides, or an in-memory database when an operator has a configured live server.

```yaml
milestone: candidate_b_live_http_operator_runner_v1
selected_path: live_http_operator_runner
deferred_path: server_side_operator_workflow_run_api
runner: tools/run_candidate_b_full_corpus_operator_workflow.py
execution_mode: live-http
api_base_url_required: true
readiness_endpoint: /api/v1/layer3/readiness
readiness_gate_required: true
candidate_b_runtime_material_bridge_admitted_required: true
candidate_b_runtime_bridge_source_scan_admitted_required: true
candidate_b_runtime_downstream_proof_admitted_required: true
candidate_b_full_corpus_operator_workflow_status_admitted_required: true
internal_webhook_mode_required: configured
local_ack_webhook_transport_allowed_in_live_http: false
testclient_dependency_used_in_live_http: false
in_memory_db_used_in_live_http: false
status_endpoint_verification_required: true
operator_workflow_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
local_testclient_regression_receipt_id: cb-full-corpus-operator-40cd13edeb4d8c10bd65e727
local_testclient_regression_receipt_hash: 40cd13edeb4d8c10bd65e727a1a8bd7c810c9809274d9f1db73a250fcc736c51
local_testclient_regression_status_hash: f126d919e9e9ce2a2766ac1a862a0e97a384edf0f685cdde8aadb4ad3dbea904
live_http_runtime_proof_status: proven
live_http_runtime_proof_checkpoint: next_milestone_plans/Layer3_planning_docs/986-cb-live-http-runtime-proof.md
live_http_runtime_proof_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
live_http_runtime_proof_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
```

## Change

The operator runner now has two explicit execution modes:

- `local-testclient`: the existing isolated proof harness used by focused tests and local regression proof.
- `live-http`: a live-server operator mode that calls a configured server through HTTP.

`live-http` fails closed unless:

- `--api-base-url` is provided;
- `--internal-webhook-mode configured` is selected;
- the live `/api/v1/layer3/readiness` response admits the Candidate B runtime bridge, bridge source scan, downstream proof, and full-corpus operator workflow status endpoints.

The live mode calls the same current-main Layer 3 API path as the proof harness:

```text
readiness -> Candidate B runtime bridge -> Candidate B bridge source scan -> material preview/Gate B -> hybrid authority -> qualitative analysis -> package/review -> handoff/export -> same-origin delivery -> provider-private prepare/status/use/revoke -> internal webhook -> downstream proof -> workflow status
```

## Boundaries

This slice does not activate a server-side operator workflow run API. That remains a separately admitted path if the live HTTP runner proves insufficient.

This slice does not broaden Candidate B beyond eligible PDFs, change baseline rollback, weaken Candidate A, seed or invent corpus artifacts, add provider object writes, add arbitrary connector dispatch, add RAG/vector/model runtime, add auth/security scope, or activate the full mockup.

## Proof

Focused tests cover the live mode contract without requiring a long-running local server:

```text
tests/test_candidate_b_full_corpus_operator_workflow.py::test_live_http_mode_requires_api_base_url_and_configured_webhook
tests/test_candidate_b_full_corpus_operator_workflow.py::test_live_http_client_accepts_server_root_or_layer3_api_root
tests/test_candidate_b_full_corpus_operator_workflow.py::test_live_http_readiness_requires_candidate_b_operator_endpoints
tests/test_candidate_b_full_corpus_operator_workflow.py::test_workflow_status_payload_binds_live_http_receipt_ids
```

The previous local proof mode remains available for regression coverage, but live operator completion now has a concrete execution surface that can be run against a real configured server.

The local regression runner still completes with the new execution metadata:

```yaml
local_testclient_regression_receipt_id: cb-full-corpus-operator-40cd13edeb4d8c10bd65e727
local_testclient_regression_receipt_hash: 40cd13edeb4d8c10bd65e727a1a8bd7c810c9809274d9f1db73a250fcc736c51
local_testclient_regression_downstream_proof_id: cb-runtime-downstream-proof-ffe65ba0f3d5008c5ae459f0
local_testclient_regression_downstream_proof_hash: ffe65ba0f3d5008c5ae459f02f3915aa4ff08ee64e3f8bebbd2ce57e6923f570
local_testclient_regression_status_hash: f126d919e9e9ce2a2766ac1a862a0e97a384edf0f685cdde8aadb4ad3dbea904
local_testclient_regression_workflow_status: proven
local_testclient_regression_raw_local_path_exposed: false
local_testclient_regression_raw_url_exposed: false
```

## Runtime Proof

A live run has now been proven against an operator-configured server with:

- `STORAGE_DIR` pointing at a runtime-discovery parent that contains the baseline, Candidate A, and Candidate B full-corpus runtime roots;
- `LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR` pointing at a server-owned bridge directory outside app-owned storage;
- `LAYER3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR` pointing at the shared durable operator workflow receipt directory;
- a durable `DATABASE_URL`;
- `LAYER3_INTERNAL_WEBHOOK_URL` configured for the internal webhook dispatch proof.

The proven live receipt is recorded in `986-cb-live-http-runtime-proof.md`. Without those live server settings, the runner must still fail closed with the exact missing server readiness, runtime-discovery, receipt-dir, or webhook blocker.

## Next Exact Posture

```text
candidate_b_operator_repeatability_acceptance_and_ui_status_decision_v1
```
