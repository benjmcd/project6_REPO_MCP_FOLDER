# SEC EDGAR Text Table Downstream Layer 3 Rendered Operator Status Selection

```yaml
milestone: sec_edgar_text_table_downstream_layer3_rendered_operator_status_selection_v1
source_operator_status_runtime: next_milestone_plans/Layer3_planning_docs/1122-sec-edgar-text-table-downstream-operator-status-runtime.md
current_main_entry: d1e75c72dd9426a02d7c9f815fc8aa3d948684b3
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: sec_edgar_text_table_downstream_layer3_rendered_operator_status_runtime_v1
selected_rendered_mode: rendered_sec_edgar_text_table_downstream_layer3_operator_status_control
selected_status_mode: sec_edgar_text_table_downstream_layer3_operator_status_v1
selected_operator_decision: inspect_sec_edgar_text_table_downstream_layer3_operator_status
selected_status_endpoint: /api/v1/layer3/source/sec-edgar/text-table/downstream-proof/status
selected_existing_proof_endpoint: /api/v1/layer3/source/sec-edgar/text-table/downstream-proof
selected_rendered_scope: operator_visible_status_inspection_over_server_revalidated_sec_edgar_downstream_proof_authority
selected_status_states: not_recorded,available,blocked
selected_rendered_form: sec-edgar-downstream-operator-status-form
selected_rendered_submit: sec-edgar-downstream-operator-status-submit
selected_rendered_panel: sec-edgar-downstream-operator-status-panel
selected_rendered_payload_fields: client_request_id,status_mode,operator_decision,downstream_proof_request,expected_proof_hash
selected_rendered_status_fields: operator_status_state,expected_proof_hash,proof_hash,proof_state,dataset_version_id,authority_envelope_hash,bridge_receipt_hash,material_preview_hash,gate_b_decision_manifest_id,session_id,selection_manifest_id,material_snapshot_payload_hash,coverage_evidence_hash,negative_invariants_hash,operator_status_hash,operator_status_projection_ref,proof_summary,blocked_reasons,next_allowed_actions
not_recorded_status_must_render: true
available_status_must_render: true
blocked_status_must_render: true
stale_or_mismatched_proof_hash_must_fail_closed: true
raw_or_forbidden_proof_authority_must_fail_closed: true
available_requires_server_revalidated_proof_request: true
available_requires_expected_proof_hash_match: true
browser_held_hash_alone_is_not_authority: true
rendered_status_can_create_downstream_proof: false
rendered_status_can_mutate_gate_b_session: false
rendered_status_can_mutate_material_snapshot: false
rendered_status_can_mutate_package_or_delivery: false
rendered_status_can_fetch_sec_content: false
rendered_status_can_parse_xml_html_inline_xbrl: false
rendered_status_can_create_runtime_storage_root: false
rendered_status_can_start_process: false
rendered_status_can_dispatch_connector: false
rendered_status_can_write_provider_object: false
rendered_status_can_add_rag_or_model_runtime: false
rendered_status_can_activate_full_mockup: false
raw_proof_request_rendered: false
raw_proof_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
artifact_bytes_rendered: false
provider_token_rendered: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
sec_edgar_network_fetch_admitted: false
sec_edgar_parser_expansion_admitted: false
xml_html_inline_xbrl_admitted: false
raw_sec_filing_url_authority_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
headless_rendered_status_proof_required: true
headed_rendered_status_proof_required: true
rendered_status_runtime_in_this_freeze: false
next_exact_posture: sec_edgar_text_table_downstream_layer3_rendered_operator_status_runtime_v1
```

This freeze selects the rendered/operator inspection surface for the existing SEC EDGAR downstream operator-status endpoint. The rendered control may collect the exact downstream proof request and expected proof hash needed by the server endpoint, then render only the server-returned status projection. It must not treat browser-held proof JSON or hashes as durable authority, and it must not expose raw proof requests, raw local paths, URLs, artifact bytes, provider tokens, or storage refs.

The next implementation should place the control near the Layer 3 source-family and result-review status surfaces, use the existing status endpoint through the bootstrap contract, render `not_recorded`, `available`, and `blocked` states, and prove the path in both headless and headed Chrome. It must preserve the existing SEC EDGAR authority envelope, material bridge, downstream proof, Candidate B default scope, Candidate A semantics, and baseline rollback behavior.

## Coherence Check

- Does this freeze admit another proof-writing endpoint? Recommended answer: no. It selects rendered inspection over the existing status endpoint only.
- Can the rendered surface decide `available` from a hash alone? Recommended answer: no. The server must revalidate the supplied downstream proof request and compare the expected proof hash.
- Are raw proof requests or raw paths allowed in the rendered status panel? Recommended answer: no. The payload may be submitted to the server, but the UI must render only redacted status projection fields.
- What proof is required next? Recommended answer: implement the rendered control/status projection and prove it in both headless and headed Chrome.
