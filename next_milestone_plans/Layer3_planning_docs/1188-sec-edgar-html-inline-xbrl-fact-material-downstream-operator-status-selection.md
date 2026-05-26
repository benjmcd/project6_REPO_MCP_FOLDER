# SEC EDGAR HTML Inline XBRL Fact Material Downstream Operator Status Selection

```yaml
milestone: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_selection_v1
source_fact_material_downstream_proof_runtime: next_milestone_plans/Layer3_planning_docs/1187-sec-edgar-html-inline-xbrl-fact-material-downstream-proof-runtime.md
source_existing_html_inline_xbrl_status_runtime: next_milestone_plans/Layer3_planning_docs/1177-sec-edgar-html-inline-xbrl-downstream-operator-status-runtime.md
current_main_entry: b88622c9d849e9bec9913fec42cf082ae1fa5180
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_runtime_v1
selected_status_mode: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_v1
selected_operator_decision: inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status
selected_status_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status
selected_existing_proof_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof
selected_future_service: backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status.py
selected_request_model_future: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusRequest
selected_response_model_future: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusResponse
selected_status_states: not_recorded,available,blocked
selected_authority_model: fact_material_downstream_proof_request_plus_expected_proof_hash_revalidated_server_side
selected_required_proof_bindings: parser_receipt_hash,connector_receipt_hash,live_source_artifact_receipt_hash,source_artifact_receipt_hash,content_sha256,primary_document_hash,content_order_hash,fact_authority_receipt_hash,fact_inventory_hash,diagnostics_hash,dataset_version_id,dataset_version_hash,materialization_receipt_hash,fact_material_bridge_receipt_hash,material_preview_hash,gate_b_decision_manifest_id,session_id,selection_manifest_id,material_snapshot_payload_hash,coverage_evidence_hash,negative_invariants_hash,proof_hash
selected_status_projection_fields: operator_status_state,expected_proof_hash,proof_hash,proof_state,dataset_version_id,dataset_version_hash,source_family,parser_family,typed_content_contract_id,parser_receipt_hash,connector_receipt_hash,live_source_artifact_receipt_hash,source_artifact_receipt_hash,content_sha256,primary_document_hash,content_order_hash,fact_authority_receipt_hash,fact_inventory_hash,diagnostics_hash,materialization_receipt_hash,fact_material_bridge_receipt_hash,material_preview_hash,gate_b_decision_manifest_id,session_id,selection_manifest_id,material_snapshot_payload_hash,coverage_evidence_hash,negative_invariants_hash,operator_status_hash,operator_status_projection_ref,proof_summary,blocked_reasons,next_allowed_actions
not_recorded_status_must_render: true
available_status_must_render: true
blocked_status_must_render: true
available_requires_server_revalidated_fact_material_proof_request: true
available_requires_expected_proof_hash_match: true
browser_held_hash_alone_is_not_authority: true
stale_or_mismatched_proof_hash_must_fail_closed: true
raw_or_forbidden_proof_authority_must_fail_closed: true
raw_fact_values_must_not_render: true
fact_value_reconstruction_by_status_admitted: false
direct_rendered_status_implementation_before_status_endpoint_admitted: false
selected_deferred_rendered_selection_target: sec_edgar_html_inline_xbrl_fact_material_downstream_rendered_status_selection_v1
status_can_create_downstream_proof: false
status_can_mutate_gate_b_session: false
status_can_mutate_material_snapshot: false
status_can_mutate_package_or_delivery: false
status_can_fetch_sec_content: false
status_can_run_submissions_lookup: false
status_can_reparse_or_materialize_html_inline_xbrl: false
status_can_create_xml_xbrl_fact_authority: false
status_can_call_sec_companyfacts_api: false
status_can_resolve_taxonomy_networks: false
status_can_add_financial_statement_semantics: false
status_can_classify_facts_to_statements: false
status_can_create_runtime_storage_root: false
status_can_start_process: false
status_can_dispatch_connector: false
status_can_write_provider_object: false
status_can_add_rag_or_model_runtime: false
status_can_activate_full_mockup: false
raw_proof_request_rendered: false
raw_proof_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
artifact_bytes_rendered: false
raw_fact_values_rendered: false
provider_token_rendered: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
sec_edgar_network_fetch_admitted: false
sec_edgar_parser_expansion_admitted: false
xml_xbrl_fact_authority_admitted: false
sec_companyfacts_api_runtime_enabled: false
taxonomy_network_resolution_enabled: false
financial_statement_semantics_admitted: false
fact_to_statement_classification_enabled: false
raw_sec_filing_url_authority_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
runtime_implementation_in_this_freeze: false
rendered_runtime_in_this_freeze: false
verification_progress_check: python ./tools/l3-progress-check.py PASS
verification_target_selection: python ./tools/l3-target-selection-validate.py --expect frozen PASS
next_exact_posture: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_runtime_v1
```

This freeze selects the next server-owned status runtime for SEC EDGAR HTML/iXBRL fact-material downstream proof. Current main can record the bounded fact-material downstream proof, and current main already has the non-fact HTML/iXBRL downstream status pattern. It does not yet have a fact-material downstream operator-status endpoint, so rendered/operator status must not be implemented first.

The selected status endpoint is read-only and deterministic. It may report `not_recorded` when no proof authority is supplied, `available` only after the server revalidates the supplied fact-material downstream proof request and recomputes the expected proof hash, and `blocked` for stale, contradictory, missing, ambiguous, self-declared, raw-value-bearing, or forbidden authority.

## Required Runtime Shape

The future runtime may accept only:

- `client_request_id`;
- `status_mode`;
- `operator_decision`;
- `fact_material_downstream_proof_request`;
- `expected_proof_hash`;
- `actor`.

It must call the existing fact-material downstream proof validator server-side, compare the recomputed `proof_hash` to `expected_proof_hash`, and return only redacted status/provenance fields. The browser-held request or hash alone is not durable authority.

## Stop Conditions

Implementation must stop if status inspection would require SEC network fetch, submissions lookup, HTML/iXBRL reparse/materialization, fact-value reconstruction, standalone XML XBRL authority, SEC Company Facts, taxonomy resolution, financial-statement semantics, fact-to-statement classification, Gate B/session/material mutation, package/delivery mutation, runtime DB/storage expansion, process execution, provider object writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, full mockup activation, browser storage, frontend durable authority, raw local paths, raw SEC URLs, provider tokens, raw fact values, or artifact bytes.

## Coherence Check

- Can this reuse the existing HTML/iXBRL downstream operator-status endpoint unchanged? Recommended answer: no. That status endpoint revalidates the narrative/table proof request and `sec_edgar_html_inline_xbrl_material_units_v1`; fact-material status must revalidate fact-authority and fact-material bridge bindings.
- Should status inspection create, repair, or persist downstream proof? Recommended answer: no. It can only revalidate supplied authority and project status.
- Does status inspection expose fact values or compute statement semantics? Recommended answer: no. Fact values remain internal material authority; taxonomy and statement semantics remain separate future slices.
