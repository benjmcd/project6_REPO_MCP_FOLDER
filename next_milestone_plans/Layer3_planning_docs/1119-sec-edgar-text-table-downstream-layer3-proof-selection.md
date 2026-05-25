# SEC EDGAR Text Table Downstream Layer 3 Proof Selection

```yaml
milestone: sec_edgar_text_table_downstream_layer3_proof_selection_v1
source_material_authority_bridge_runtime: next_milestone_plans/Layer3_planning_docs/1118-sec-edgar-text-table-layer3-material-authority-bridge-runtime.md
current_main_entry: 939272a054ee049d6af8f49f132aa8353f6ca6b5
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
selected_next_runtime_target: sec_edgar_text_table_downstream_layer3_proof_runtime_v1
selected_proof_mode: sec_edgar_text_table_downstream_layer3_e2e_proof_v1
selected_operator_decision: record_sec_edgar_text_table_downstream_layer3_e2e_proof
selected_source_family: sec_edgar_text_table
selected_parser_family: sec_edgar_filing
selected_typed_content_contract_id: aps_sec_edgar_filing_units_v1
required_authority_envelope_schema_id: layer3.sec_edgar_text_table_authority_envelope_validation.v1
required_material_bridge_schema_id: layer3.sec_edgar_text_table_material_authority_bridge.v1
required_material_bridge_mode: sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1
required_material_bridge_state: sec_edgar_text_table_layer3_material_authority_bridge_ready
required_material_source_class: dataset_version
required_gate_b_decision_schema_id: layer3.gate_b_decision_request.v1
required_gate_b_commit_surface: existing_gate_b_decision_api
required_gate_b_commit_in_bridge: false
required_downstream_session_authority: L3Session,L3SelectionManifest,L3MaterialSnapshot
required_material_snapshot_source_shape: dataset_version
required_hash_bindings: authority_envelope_hash,materialization_receipt_hash,bridge_receipt_hash,material_preview_hash,gate_b_decision_manifest_id,session_id,selection_manifest_id,material_snapshot_payload_hash,coverage_evidence_hash,proof_hash
required_coverage_steps: authority_envelope_validation,material_authority_bridge,gate_b_commit,gate_c_typing,retrieval_context,analysis_execution_or_status,package_commit,package_review_submit,handoff_export_prepare,external_export_download_prepare,same_origin_delivery_status,same_origin_delivery,provider_private_prepare,provider_private_status,provider_private_use,provider_private_revoke,internal_webhook_dispatch,internal_webhook_status,session_status_projection,operator_artifact_inspection
required_evidence_model: server_owned_receipts_and_response_hashes_not_self_declared_coverage_only
required_fail_closed_conditions: missing_ready_envelope,missing_ready_bridge,bridge_hash_mismatch,gate_b_payload_mismatch,gate_b_hash_mismatch,missing_gate_b_session,material_snapshot_mismatch,missing_coverage_step,coverage_not_bound_to_server_receipt,raw_path_or_url_authority,missing_operator_confirmation,forbidden_input_authority
runtime_implementation_in_this_freeze: false
rendered_runtime_in_this_freeze: false
sec_edgar_network_fetch_admitted: false
sec_edgar_parser_expansion_admitted: false
xml_html_inline_xbrl_admitted: false
raw_sec_filing_url_authority_admitted: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
verification_progress_check: python ./tools/l3-progress-check.py PASS
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
next_exact_posture: sec_edgar_text_table_downstream_layer3_proof_runtime_v1
```

This freeze admits the next implementation slice only: a bounded downstream proof runtime for SEC EDGAR text-table material that has already passed authority-envelope validation and the Layer 3 material-authority bridge. It introduces no runtime code, route, DTO, model, migration, rendered UI, SEC fetch, parser, provider, connector, auth/security, RAG/vector/model, browser-storage, frontend-only durable authority, or full mockup behavior change.

The proof must start from server-owned authority already produced by current main:

- a ready `layer3.sec_edgar_text_table_authority_envelope_validation.v1` envelope;
- a ready `layer3.sec_edgar_text_table_material_authority_bridge.v1` bridge receipt/projection;
- the bridge-returned Gate B decision payload;
- an actual committed Gate B session through the existing Gate B API, not a bridge-local pseudo-commit.

## Required Runtime Shape

The future proof runtime may accept:

- `client_request_id`;
- `proof_mode`;
- `operator_decision`;
- `dataset_version_id`;
- `authority_envelope_hash`;
- `bridge_receipt_hash`;
- `material_preview_hash`;
- `gate_b_decision_manifest_id`;
- `session_id`;
- `selection_manifest_id`;
- `coverage_evidence`;
- `operator_confirmation`.

It must recompute or verify the relevant server-owned hashes and refuse proof if the committed Gate B session, selection manifest, material snapshot, bridge projection, or coverage evidence no longer match.

## Coverage

The future proof must cover every required step:

- authority envelope validation;
- material authority bridge;
- Gate B commit;
- Gate C typing;
- retrieval/context;
- analysis execution or explicit analysis-status proof;
- package commit;
- package review submit;
- handoff/export prepare;
- external export download prepare;
- same-origin delivery status;
- same-origin delivery;
- provider-private prepare;
- provider-private status;
- provider-private use;
- provider-private revoke;
- internal webhook dispatch;
- internal webhook status;
- session/status projection;
- operator artifact inspection.

Coverage evidence must bind to server-owned ids, hashes, or response receipts from current runtime surfaces. The runtime must not accept historical reports alone, raw local paths, raw URLs, provider tokens, raw artifact refs, browser storage, or frontend state as proof.

## Stop Conditions

Implementation must stop if:

- the SEC EDGAR authority envelope is blocked, stale, or missing;
- the material bridge is blocked, stale, or missing;
- Gate B has not been committed through the existing Gate B API;
- the committed session or material snapshot does not prove `source_shape=dataset_version` and `source_family=sec_edgar_text_table`;
- required downstream coverage cannot be linked to server-owned response hashes or receipts;
- any proof path would require SEC network fetch, parser expansion, XML/HTML/inline XBRL reinterpretation, source expansion, runtime DB/storage expansion, provider object writes, arbitrary connector dispatch, RAG/vector/model runtime, auth/security changes, full mockup activation, browser storage, or frontend durable authority.

## Coherence Check

- Does this implement downstream proof? Recommended answer: no. It freezes the exact proof contract for the next runtime slice.
- Why require a real Gate B commit? Recommended answer: the material bridge intentionally returns a Gate B payload but does not commit Gate B; downstream proof must verify the existing Gate B API/session/material-snapshot authority.
- Can coverage be self-declared? Recommended answer: no. Coverage must be bound to server-owned ids, hashes, receipts, or response projections.
- What comes next? Recommended answer: implement `sec_edgar_text_table_downstream_layer3_proof_runtime_v1` using proof mode `sec_edgar_text_table_downstream_layer3_e2e_proof_v1`.
