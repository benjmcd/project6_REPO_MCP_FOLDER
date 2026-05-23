# 982 - Candidate B Full-Corpus Current-Main Operator Execution

## Purpose

Record the current-main operator execution of the Candidate B full-corpus workflow after the eligibility/status surface landed.

This checkpoint proves that the available baseline, Candidate A, and Candidate B full-corpus runtime roots can still be validated from current main, bridged into Layer 3, driven through downstream proof, and inspected through the governed operator status endpoint. It is evidence recording only. It does not copy runtime roots, seed artifacts, mutate selectors, broaden Candidate B beyond eligible PDFs, add source families, write provider objects, dispatch arbitrary connectors, add RAG/model runtime, or activate full mockups.

```yaml
milestone: candidate_b_full_corpus_current_main_operator_execution_v1
current_main: 4659f3362f5d441f8501cb4cb5cd180eb8835ef5
runner: tools/run_candidate_b_full_corpus_operator_workflow.py
status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
workflow_receipt_id: cb-full-corpus-operator-9dbd003b8177fe6c8025cec5
workflow_receipt_hash: 9dbd003b8177fe6c8025cec5035e68ac41e7f962447e2088eb102a64e737f5f2
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-31c7b242d398dbf536aefc88
downstream_proof_hash: 31c7b242d398dbf536aefc88ecb4d38cca073361166d6e5a981a9b70bd808906
status_endpoint_http_status: 200
workflow_status: proven
status_endpoint_status: available
coverage_count: 17
corpus_pdf_count: 69
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
source_directory_extra_material_file_count: 2
eligibility_summary_projection_visible: true
baseline_rollback_projection_visible: true
runtime_root_lifecycle_projection_visible: true
baseline_rollback_selector: baseline
rollback_depends_on_candidate_b_artifacts: false
candidate_a_visual_lane_preserved: true
selector_mutation_performed: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
```

## Execution

The current-main run used existing validated runtime roots from the same admitted `lc_e2e` parent:

```powershell
python .\tools\run_candidate_b_full_corpus_operator_workflow.py `
  --baseline-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\baseline-full-corpus-v2 `
  --candidate-a-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\candidate-a-full-corpus-v1 `
  --candidate-b-run-root ..\cb-full-corpus\backend\app\storage_test_runtime\lc_e2e\cb-full-corpus-v1
```

The compare triplet validated without seeding or generating artifacts:

```yaml
validate_only_triplet: true
artifacts_seeded_or_generated_by_triplet_validator: false
target_status_counts:
  baseline:
    recommended: 69
  candidate_a:
    recommended: 69
  candidate_b:
    recommended: 69
```

The resulting operator receipt reached the complete downstream path:

```yaml
source_directory_scan_status: available
bridge_status: prepared
qualitative_analysis_status: available
same_origin_delivery_available: true
provider_private_state: provider_private_signed_url_prepared
provider_private_revoke_state: provider_private_signed_url_revoked
internal_webhook_state: source_directory_internal_webhook_dispatched
visual_lane_status: available
downstream_proof_status: proven
```

## Status Inspection

The fresh receipt was inspected through the operator status endpoint with the current-main status service. The status response returned:

```yaml
http_status: 200
status: available
workflow_status: proven
workflow_receipt_id: cb-full-corpus-operator-9dbd003b8177fe6c8025cec5
workflow_receipt_hash: 9dbd003b8177fe6c8025cec5035e68ac41e7f962447e2088eb102a64e737f5f2
runtime_root_lifecycle.available: true
runtime_root_lifecycle.root_count: 3
operator_projection.workflow_status_visible: true
operator_projection.workflow_receipt_projection_visible: true
operator_projection.bridge_receipt_projection_visible: true
operator_projection.downstream_proof_projection_visible: true
operator_projection.artifact_family_projection_visible: true
operator_projection.eligibility_summary_projection_visible: true
operator_projection.baseline_rollback_projection_visible: true
operator_projection.runtime_root_lifecycle_projection_visible: true
operator_projection.artifact_bytes_exposed: false
operator_projection.raw_local_path_exposed: false
operator_projection.raw_url_exposed: false
```

## Result

Candidate B has a current-main full-corpus operator execution checkpoint after the status eligibility slice:

- baseline remains the explicit rollback selector;
- Candidate A visual-lane semantics remain preserved;
- Candidate B remains scoped to eligible PDF/corpus processing;
- the full-corpus triplet is validated before bridge execution;
- the runtime-root lifecycle receipt binds existing roots without moving or copying them;
- the Layer 3 bridge and downstream proof remain receipt-bound;
- status inspection is read-only and redacted;
- provider-private, internal webhook, same-origin delivery, artifact-family, and final status evidence remain visible through the governed path.

## Next Exact Posture

```text
candidate_b_operator_invocation_surface_gap_audit_v1
```

The next pass should determine whether the current script-based operator runner is sufficient as the governed operator invocation surface, or whether current main should admit a smaller API/CLI wrapper that avoids any remaining TestClient/session-helper dependency. Implement only if the audit names a concrete repeatability or operator-usability gap.
