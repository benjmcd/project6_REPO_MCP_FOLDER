# 986 - Candidate B Live HTTP Runtime Proof

## Purpose

Record the live-server proof for the Candidate B full-corpus operator workflow after the `live-http` runner was admitted.

This checkpoint proves the operator runner can drive the current-main Layer 3 API chain through a live FastAPI server with durable runtime directories, a durable SQLite database, configured internal webhook dispatch, and status-endpoint inspection. It is not a new server-side orchestration API and does not broaden Candidate B beyond eligible PDFs.

```yaml
milestone: candidate_b_live_http_operator_workflow_runtime_proof_v1
current_main: ebc8f46cd4ec48f2e97b6de10bfd5ff6cbe07d71
execution_mode: live-http
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
configured_internal_webhook_required: true
configured_internal_webhook_used: true
status_endpoint_verified: true
status_endpoint_status: available
workflow_status: proven
workflow_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
workflow_receipt_hash: 3d717f0edcbeaba69179af1582a90abf2ce087c5d35400afdb62fe7534b3266c
workflow_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-ee7d48afbe62ffc011fac4d3
downstream_proof_hash: ee7d48afbe62ffc011fac4d3ae8796f9b5bdaa42c5db91d3ac0f5d527d8b8481
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
artifact_family_hash: bc32ee4f789f078b9f1d1e46dd9402df5b92aeb4afbde369fbd00553e6a61380
coverage_count: 17
corpus_pdf_count: 69
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
curated_file_count: 71
text_file_count: 69
visual_page_evidence_count: 1805
product_inspection_artifact_count: 1873
delivery_artifact_count: 1873
provenance_audit_artifact_count: 2542
material_analysis_payload_count: 71
baseline_rollback_available: true
baseline_selector: baseline
candidate_a_visual_lane_preserved: true
selector_mutation_performed: false
source_directory_scan_status: available
qualitative_analysis_status: available
external_export_download_status: prepared
same_origin_delivery_available: true
provider_private_state: provider_private_signed_url_prepared
provider_private_revoke_state: provider_private_signed_url_revoked
internal_webhook_state: source_directory_internal_webhook_dispatched
visual_lane_status: available
downstream_proof_status: proven
api_base_url_ref: redacted://url/0eed07a75735dce278294964
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
baseline_default_changed: false
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
artifacts_seeded_or_generated_by_triplet_validator: false
validate_only_triplet: true
next_exact_posture: candidate_b_operator_repeatability_acceptance_and_ui_status_decision_v1
```

## Proof Path

The live proof executed the current-main API chain:

```text
readiness -> Candidate B runtime bridge -> Candidate B bridge source scan -> material preview/Gate B -> hybrid authority -> qualitative analysis -> package/review -> handoff/export -> same-origin delivery -> provider-private prepare/status/use/revoke -> internal webhook dispatch -> qualitative/status and session projection -> Candidate B visual-lane status -> Candidate B runtime downstream proof -> full-corpus operator workflow status
```

The status endpoint then re-read the durable workflow receipt and returned `status: available`, `workflow_status: proven`, `workflow_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e`, and no raw local path, raw URL, or artifact bytes exposure.

## Boundaries

This proof does not seed or generate corpus artifacts, mutate baseline default behavior, weaken Candidate A, broaden Candidate B beyond eligible PDFs, add provider object writes, expose public provider URLs, enable arbitrary connector dispatch, add RAG/vector/model runtime, activate full mockup behavior, or create frontend-only durable authority.
