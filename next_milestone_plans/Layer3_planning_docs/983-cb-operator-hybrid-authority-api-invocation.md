# 983 - Candidate B Operator Hybrid Authority API Invocation

## Purpose

Remove the Candidate B full-corpus operator workflow runner's direct session-helper dependency for material snapshot and hybrid authority preparation.

The runner now uses the governed Layer 3 API surface:

```text
POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare
```

instead of reading `L3MaterialSnapshot` through a `client.layer3_session_factory` test helper or calling text/vector index services directly. This is a bounded invocation-surface improvement. It does not change Candidate B selector defaults, Candidate A semantics, baseline rollback, bridge authority, source-directory policy, provider behavior, connector behavior, RAG/model runtime, or full mockup activation.

```yaml
milestone: candidate_b_operator_hybrid_authority_api_invocation_v1
checkpoint_base_main: 0b599adc9c4784ff32b6840704e28b0013f028d6
runner: tools/run_candidate_b_full_corpus_operator_workflow.py
governed_authority_api: /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare
direct_material_snapshot_query_removed: true
direct_text_index_service_call_removed: true
direct_vector_index_service_call_removed: true
client_layer3_session_factory_removed_from_runner_orchestration: true
workflow_receipt_id: cb-full-corpus-operator-95256b11fd16e84a43bb4b8b
workflow_receipt_hash: 95256b11fd16e84a43bb4b8b69dfb99b178d43e201251ae56dfb72e996592c2c
downstream_proof_id: cb-runtime-downstream-proof-4e4dfc87454f0acc66bc8111
downstream_proof_hash: 4e4dfc87454f0acc66bc81119780223701a5035377b17d30ae27aabf826a2677
status_endpoint_http_status: 200
status_endpoint_status: available
workflow_status: proven
coverage_count: 17
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
workflow_receipt_schema_unchanged: candidate_b.full_corpus_layer3_operator_workflow.v1
workflow_mode_unchanged: candidate_b_full_corpus_operator_workflow_v1
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

Before this slice, the runner used API calls for most downstream steps but reached behind the API boundary for the material authority handoff:

- it queried `L3MaterialSnapshot` through a `client.layer3_session_factory` helper after Gate B;
- it called `source_directory_material_text_index` directly;
- it called `source_directory_material_embedding_vector_index` directly.

Current main already has a server-owned hybrid authority API that performs the same material snapshot loading, text index, vector index, authority hash construction, and redaction checks. The runner now calls that API after Gate B and uses its `authority_payload` as the downstream analysis payload basis.

## Runtime Proof

The updated runner completed the full-corpus operator workflow and the status endpoint accepted the fresh receipt:

```yaml
workflow_receipt_id: cb-full-corpus-operator-95256b11fd16e84a43bb4b8b
workflow_receipt_hash: 95256b11fd16e84a43bb4b8b69dfb99b178d43e201251ae56dfb72e996592c2c
downstream_proof_id: cb-runtime-downstream-proof-4e4dfc87454f0acc66bc8111
downstream_proof_hash: 4e4dfc87454f0acc66bc81119780223701a5035377b17d30ae27aabf826a2677
status_endpoint_http_status: 200
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

- `tests/test_candidate_b_full_corpus_operator_workflow.py::test_prepare_package_uses_hybrid_authority_api_without_session_helper`;
- `tools/l3-progress-check.py`;
- `python -m pytest .\tests\test_candidate_b_full_corpus_operator_workflow.py -q`;
- `python .\tools\run_candidate_b_full_corpus_operator_workflow.py --baseline-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\baseline-full-corpus-v2 --candidate-a-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\candidate-a-full-corpus-v1 --candidate-b-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\cb-full-corpus-v1`.

## Remaining Invocation Gap

The runner still uses an in-process local API client to create an isolated database and storage runtime for proof execution. That is acceptable for this bounded slice, but it is not the final production-grade invocation surface.

The next separate audit should decide whether current main needs:

- a live-server HTTP operator client;
- a server-side `operator-workflow/run` API;
- or a narrower bridge-curated source-directory scan API that lets a live server continue after bridge preparation without mutating process-local settings.

## Next Exact Posture

```text
candidate_b_live_server_invocation_surface_gap_audit_v1
```

Do not implement a broader live-server runner until the audit identifies the exact current-main blocker and the narrowest API or CLI surface needed.
