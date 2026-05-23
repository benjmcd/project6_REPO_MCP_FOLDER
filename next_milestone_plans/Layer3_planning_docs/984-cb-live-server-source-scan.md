# 984 - Candidate B Live-Server Bridge Source Scan

## Purpose

Remove the Candidate B full-corpus operator workflow runner's remaining process-local source-directory mutation after the runtime material bridge.

The runner now uses a governed bridge-receipt source scan API:

```text
POST /api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge/source-scan
```

instead of setting `settings.layer3_source_ingestion_dir` to the bridge-curated root and then calling the generic server-configured directory scan. This makes the next operator invocation surface server-owned: the client supplies a durable `bridge_receipt_id`, and the server resolves the curated material root from `LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR` without accepting caller paths, raw roots, URLs, connector dispatch, browser authority, provider object writes, RAG/model runtime, or full mockup activation.

```yaml
milestone: candidate_b_live_server_bridge_source_scan_v1
checkpoint_base_main: f283c6d2e7dc1d3b3b9fc6c526b12b06a0941021
governed_source_scan_api: /api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge/source-scan
source_scan_mode: candidate_b_runtime_bridge_curated_source_scan_v1
operator_decision: scan_candidate_b_runtime_bridge_curated_material_root
bridge_receipt_authority_required: true
caller_supplied_path_admitted: false
settings_layer3_source_ingestion_dir_mutation_removed: true
material_preview_resolves_persisted_batch_root_ref: true
text_index_resolves_persisted_batch_root_ref: true
workflow_receipt_id: cb-full-corpus-operator-2408b420e3634bb6af6dffdd
workflow_receipt_hash: 2408b420e3634bb6af6dffddde6ef5346b40a3f73500797037cff193125d660e
workflow_status_hash: a82d24c258958bb711d2c5a068cdff2f9ea72957ad7160711ddc8266f424011e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-ba446008ff89a03057a122c3
downstream_proof_hash: ba446008ff89a03057a122c38a5cf51eb6bb941f2d1522bc270e848a0274a352
status_endpoint_status: available
workflow_status: proven
coverage_count: 17
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
source_root_ref: candidate-b-runtime-bridge://cb-runtime-l3-0110fe894c68d6a0291f9979/curated
baseline_rollback_preserved: true
candidate_a_visual_lane_preserved: true
candidate_b_default_scope_broadened: false
selector_mutation_performed: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
```

## Change

Before this slice, the operator workflow was mostly API-driven but still depended on in-process mutation:

- prepare Candidate B runtime material bridge;
- compute `bridge_dir / bridge_receipt_id / "curated"` in the runner;
- set `settings.layer3_source_ingestion_dir` to that local root;
- call the generic source-directory scan API.

Current main now adds the exact missing server-owned bridge continuation:

- the Candidate B runtime bridge service validates the durable bridge receipt and curated material manifest;
- the source scan request requires `bridge_receipt_id`, baseline run id, Candidate A run id, Candidate B run id, `source_scan_mode`, admitted operator decision, and `operator_confirmation=true`;
- the source-directory ingestion batch records `source_root_ref` as `candidate-b-runtime-bridge://{bridge_receipt_id}/curated`;
- material preview and deterministic text indexing resolve the persisted batch root ref server-side instead of reading `LAYER3_SOURCE_INGESTION_DIR`;
- the runner calls the bridge source-scan API and no longer mutates `settings.layer3_source_ingestion_dir` after the bridge.

## Runtime Proof

The updated runner completed the full-corpus operator workflow and the status surface accepted the fresh receipt:

```yaml
workflow_receipt_id: cb-full-corpus-operator-2408b420e3634bb6af6dffdd
workflow_receipt_hash: 2408b420e3634bb6af6dffddde6ef5346b40a3f73500797037cff193125d660e
workflow_status_hash: a82d24c258958bb711d2c5a068cdff2f9ea72957ad7160711ddc8266f424011e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-ba446008ff89a03057a122c3
downstream_proof_hash: ba446008ff89a03057a122c38a5cf51eb6bb941f2d1522bc270e848a0274a352
status_endpoint_status: available
workflow_status: proven
coverage_count: 17
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
raw_local_path_exposed: false
raw_url_exposed: false
```

## Guarded Evidence

This slice is guarded by:

- `backend/tests/test_layer3_candidate_b_runtime_bridge.py`;
- `tests/test_candidate_b_full_corpus_operator_workflow.py::test_source_scan_uses_bridge_receipt_api_without_source_dir_mutation`;
- `tools/l3-progress-check.py`;
- `python -m pytest .\tests\test_candidate_b_full_corpus_operator_workflow.py .\backend\tests\test_layer3_candidate_b_runtime_bridge.py -q`;
- `python .\tools\run_candidate_b_full_corpus_operator_workflow.py --baseline-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\baseline-full-corpus-v2 --candidate-a-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\candidate-a-full-corpus-v1 --candidate-b-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\cb-full-corpus-v1`.

## Remaining Invocation Gap

The runner still uses an in-process `TestClient` and an isolated in-memory database for proof execution. That is acceptable for this bounded slice because the removed blocker was the post-bridge source-root mutation. The next separate slice should decide whether to expose a live-server HTTP operator client or a server-side `operator-workflow/run` API for durable execution orchestration.

## Next Exact Posture

```text
candidate_b_live_server_operator_workflow_run_api_or_http_client_decision_v1
```
