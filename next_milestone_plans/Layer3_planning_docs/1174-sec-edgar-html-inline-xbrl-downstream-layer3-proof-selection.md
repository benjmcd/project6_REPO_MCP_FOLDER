# SEC EDGAR HTML Inline XBRL Downstream Layer 3 Proof Selection

```yaml
milestone: sec_edgar_html_inline_xbrl_downstream_layer3_proof_selection_v1
source_material_bridge_runtime: next_milestone_plans/Layer3_planning_docs/1173-sec-edgar-html-inline-xbrl-material-bridge-runtime.md
current_main_entry: e608ccd5f2729a83ec23cf43015f60fba77684bd
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: sec_edgar_html_inline_xbrl_downstream_layer3_proof_runtime_v1
selected_proof_mode: sec_edgar_html_inline_xbrl_downstream_layer3_e2e_proof_v1
selected_operator_decision: record_sec_edgar_html_inline_xbrl_downstream_layer3_e2e_proof
selected_future_service: backend/app/services/layer3_sec_edgar_html_inline_xbrl_downstream_proof.py
selected_future_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/downstream-proof
selected_source_family: sec_edgar_html_inline_xbrl
selected_parser_family: sec_edgar_html_inline_xbrl_source_family_parser_v1
selected_typed_content_contract_id: sec_edgar_html_inline_xbrl_material_units_v1
selected_material_bridge_mode: sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority_v1
selected_material_bridge_ready_state: sec_edgar_html_inline_xbrl_material_bridge_ready
selected_material_source_class: dataset_version
required_material_bridge_schema_id: layer3.sec_edgar_html_inline_xbrl_material_bridge.v1
required_material_bridge_request_schema_id: layer3.sec_edgar_html_inline_xbrl_material_bridge_request.v1
required_gate_b_decision_schema_id: layer3.gate_b_decision_request.v1
required_gate_b_commit_surface: existing_gate_b_decision_api
required_gate_b_commit_in_bridge: false
required_parser_receipt_authority: parser_receipt_id,parser_receipt_hash,connector_receipt_hash,live_source_artifact_receipt_hash,source_artifact_receipt_hash,content_sha256,primary_document_hash,document_inventory_hash,content_order_hash,table_candidate_inventory_hash,inline_xbrl_marker_inventory_hash
required_material_bridge_authority: bridge_receipt_id,bridge_receipt_hash,dataset_version_id,dataset_version_hash,materialization_receipt_hash,material_preview_hash,gate_b_decision_manifest_id,admitted_subset_hash
required_downstream_session_authority: L3Session,L3SelectionManifest,L3MaterialSnapshot
required_material_snapshot_source_shape: dataset_version
required_hash_bindings: parser_receipt_hash,connector_receipt_hash,live_source_artifact_receipt_hash,source_artifact_receipt_hash,content_sha256,materialization_receipt_hash,dataset_version_hash,bridge_receipt_hash,material_preview_hash,gate_b_decision_manifest_id,session_id,selection_manifest_id,material_snapshot_payload_hash,coverage_evidence_hash,proof_hash
required_coverage_steps: real_filing_connector_acquisition,live_source_artifact_acquisition,html_inline_xbrl_source_family_parser,html_inline_xbrl_material_authority_bridge,gate_b_commit,gate_c_typing,retrieval_context,analysis_execution_or_status,package_commit,package_review_submit,handoff_export_prepare,external_export_download_prepare,same_origin_delivery_status,same_origin_delivery,provider_private_prepare,provider_private_status,provider_private_use,provider_private_revoke,internal_webhook_dispatch,internal_webhook_status,session_status_projection,operator_artifact_inspection
required_evidence_model: server_owned_receipts_and_response_hashes_not_self_declared_coverage_only
required_fail_closed_conditions: missing_parser_receipt,stale_parser_receipt_hash,missing_material_bridge_receipt,stale_material_bridge_receipt_hash,material_bridge_not_ready,gate_b_payload_mismatch,gate_b_hash_mismatch,missing_gate_b_session,material_snapshot_mismatch,source_family_mismatch,parser_family_mismatch,typed_content_contract_mismatch,missing_coverage_step,coverage_not_bound_to_server_receipt,raw_path_or_url_authority,missing_operator_confirmation,forbidden_input_authority
runtime_implementation_in_this_freeze: false
rendered_runtime_in_this_freeze: false
gate_b_mutation_admitted_in_proof: false
live_sec_network_fetch_admitted_for_proof: false
submissions_lookup_runtime_admitted_for_proof: false
html_inline_xbrl_reparse_or_materialization_admitted_in_proof: false
xml_xbrl_fact_authority_admitted: false
financial_statement_semantics_admitted: false
raw_sec_filing_url_authority_admitted: false
broad_source_expansion_admitted: false
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
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
verification_progress_check: python ./tools/l3-progress-check.py PASS
verification_target_selection: python ./tools/l3-target-selection-validate.py --expect frozen PASS
next_exact_posture: sec_edgar_html_inline_xbrl_downstream_layer3_proof_runtime_v1
```

This freeze selects the next runtime only: a bounded downstream Layer 3 proof for SEC EDGAR HTML/iXBRL material that has already passed the parser-receipt material bridge. It introduces no runtime code, route, DTO, model, migration, rendered UI, SEC fetch, parser/materialization expansion, provider write, connector dispatch, auth/security, RAG/vector/model, browser-storage, frontend-only durable authority, or full mockup behavior change.

The proof must start from server-owned authority already produced by current main:

- a ready `layer3.sec_edgar_html_inline_xbrl_material_bridge.v1` bridge receipt/projection;
- the bridge-returned Gate B decision payload;
- an actual committed Gate B session through the existing Gate B API, not a bridge-local pseudo-commit;
- the committed material snapshot for the materialized `dataset_version`;
- structured downstream coverage evidence bound to server-owned ids, hashes, receipts, or response projections.

## Required Runtime Shape

The future runtime may accept only:

- `client_request_id`;
- `proof_mode`;
- `operator_decision`;
- `parser_receipt_id`;
- `parser_receipt_hash`;
- `material_bridge_receipt_id`;
- `material_bridge_receipt_hash`;
- `dataset_version_id`;
- `material_preview_hash`;
- `gate_b_decision_manifest_id`;
- `session_id`;
- `selection_manifest_id`;
- `material_snapshot_payload_hash`;
- `coverage_evidence`;
- `operator_confirmation`;
- `actor`.

It must re-read and verify the material bridge server-side, then verify the committed Gate B session, selection manifest, material snapshot, source-family contract, parser-family contract, typed-content contract, and coverage evidence. A raw parser receipt, raw material bridge id, raw DatasetVersion id, historical report, or rendered/browser state is not sufficient proof.

## Coverage

The future proof must cover every required step:

- real filing connector acquisition;
- live source-artifact acquisition;
- HTML/iXBRL source-family parser;
- HTML/iXBRL material-authority bridge;
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

Coverage evidence must bind to server-owned ids, hashes, receipts, or response projections from current runtime surfaces. It must not accept raw local paths, raw SEC URLs, provider tokens, raw artifact refs, artifact bytes, browser storage, frontend state, or historical reports without current server-owned authority.

## Stop Conditions

Implementation must stop if:

- the HTML/iXBRL material bridge receipt is blocked, stale, missing, or not ready;
- Gate B has not been committed through the existing Gate B API;
- the committed session or material snapshot does not prove `source_shape=dataset_version`, `source_family=sec_edgar_html_inline_xbrl`, `parser_family=sec_edgar_html_inline_xbrl_source_family_parser_v1`, and `typed_content_contract_id=sec_edgar_html_inline_xbrl_material_units_v1`;
- required downstream coverage cannot be linked to server-owned response hashes or receipts;
- any proof path would require SEC network fetch, submissions lookup, HTML/iXBRL reparse/materialization, XBRL fact extraction, financial-statement semantics, source expansion, runtime DB/storage expansion, provider object writes, arbitrary connector dispatch, RAG/vector/model runtime, auth/security changes, full mockup activation, browser storage, frontend durable authority, raw local paths, raw URLs, or artifact bytes.

## Coherence Check

- Does this implement downstream proof? Recommended answer: no. It freezes the exact proof contract for the next runtime slice.
- Can the bridge receipt alone prove Layer 3 E2E? Recommended answer: no. It proves material preview and Gate B payload compatibility, but the downstream proof must verify a real Gate B commit, material snapshot, and downstream coverage.
- Are inline XBRL markers converted into XBRL facts? Recommended answer: no. Inline XBRL markers remain provenance/evidence for a later separately frozen fact-authority slice.
- What comes next? Recommended answer: implement `sec_edgar_html_inline_xbrl_downstream_layer3_proof_runtime_v1` with proof mode `sec_edgar_html_inline_xbrl_downstream_layer3_e2e_proof_v1`.
