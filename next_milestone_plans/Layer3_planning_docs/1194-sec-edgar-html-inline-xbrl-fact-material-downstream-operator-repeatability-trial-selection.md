# SEC EDGAR HTML Inline XBRL Fact Material Downstream Operator Repeatability Trial Selection

```yaml
milestone: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_selection_v1
source_fact_material_downstream_closeout_readiness: next_milestone_plans/Layer3_planning_docs/1193-sec-edgar-html-inline-xbrl-fact-material-downstream-closeout-readiness.md
source_existing_text_table_repeatability_trial_selection: next_milestone_plans/Layer3_planning_docs/1127-sec-edgar-text-table-downstream-operator-repeatability-trial-selection.md
source_existing_live_source_repeatability_trial_selection: next_milestone_plans/Layer3_planning_docs/1160-sec-edgar-text-table-live-source-artifact-downstream-operator-repeatability-trial-selection.md
current_main_entry: e66053717326b47f8fd57cef3c6dd0783408ab20
source_closeout_readiness_pr: "#1896"
source_closeout_readiness_merge_commit: e66053717326b47f8fd57cef3c6dd0783408ab20
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_runtime_v1
selected_trial_scope: compare_two_server_owned_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_projections_for_same_fact_material_authority_and_proof_chain
selected_trial_model: append_only_trial_receipt_over_original_and_repeat_fact_material_downstream_status_authority_without_sec_fetch_or_processing_execution
selected_trial_action: record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial
selected_trial_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/operator-repeatability/trial
selected_existing_status_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status
selected_existing_proof_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof
selected_request_model_future: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialRequest
selected_response_model_future: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialResponse
selected_service_future: backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_repeatability_trial.py
selected_schema_id_future: layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial.v1
selected_request_schema_id_future: layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_request.v1
original_operator_status_required: available
repeat_operator_status_required: available
original_expected_operator_status_hash_required: true
repeat_expected_operator_status_hash_required: true
original_expected_proof_hash_required: true
repeat_expected_proof_hash_required: true
same_source_family_required: sec_edgar_html_inline_xbrl
same_parser_family_required: sec_edgar_html_inline_xbrl_source_family_parser_v1
same_typed_content_contract_id_required: sec_edgar_html_inline_xbrl_fact_material_units_v1
same_connector_receipt_hash_required: true
same_live_source_artifact_receipt_hash_required: true
same_source_artifact_receipt_hash_required: true
same_content_sha256_required: true
same_primary_document_hash_required: true
same_content_order_hash_required: true
same_inline_xbrl_marker_inventory_hash_required: true
same_fact_authority_receipt_hash_required: true
same_fact_inventory_hash_required: true
same_fact_material_bridge_receipt_hash_required: true
same_materialization_receipt_hash_required: true
same_material_preview_hash_required: true
same_gate_b_decision_manifest_id_required: true
same_gate_b_session_id_required: true
same_dataset_version_id_required: true
same_dataset_version_hash_required: true
same_session_id_required: true
same_selection_manifest_id_required: true
same_material_snapshot_payload_hash_required: true
same_coverage_evidence_hash_required: true
same_negative_invariants_hash_required: true
same_downstream_proof_hash_required: true
operator_status_hash_comparison_required: true
proof_hash_comparison_required: true
fact_inventory_hash_comparison_required: true
coverage_step_set_comparison_required: true
fact_material_authority_hash_comparison_required: true
operator_repeatability_disposition_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
append_only_repeatability_trial_receipt_required: true
exclusive_trial_per_original_repeat_authority_pair_required: true
stale_original_operator_status_must_reject: true
stale_repeat_operator_status_must_reject: true
missing_fact_material_downstream_proof_must_reject: true
mismatched_source_or_parser_family_must_reject: true
mismatched_fact_authority_must_reject: true
mismatched_fact_inventory_must_reject: true
mismatched_fact_material_bridge_must_reject: true
mismatched_material_authority_must_reject: true
mismatched_gate_b_or_selection_must_reject: true
mismatched_coverage_evidence_must_reject: true
non_available_original_or_repeat_status_must_reject: true
raw_fact_value_authority_must_reject: true
raw_url_or_path_authority_must_reject: true
browser_supplied_local_authority_admitted: false
browser_supplied_raw_url_admitted: false
browser_supplied_sec_url_admitted: false
browser_supplied_raw_fact_values_admitted: false
browser_supplied_command_admitted: false
browser_supplied_process_control_admitted: false
browser_supplied_stdout_stderr_admitted: false
browser_supplied_artifact_bytes_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
sec_edgar_network_fetch_admitted: false
sec_edgar_parser_expansion_admitted: false
html_inline_xbrl_reparse_or_rematerialization_admitted: false
xml_xbrl_fact_authority_admitted: false
sec_companyfacts_api_runtime_enabled: false
taxonomy_network_resolution_enabled: false
financial_statement_semantics_admitted: false
fact_to_statement_classification_enabled: false
raw_sec_filing_url_authority_admitted: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
actual_sec_processing_execution_admitted_by_trial_endpoint: false
actual_subprocess_spawn_admitted_by_trial_endpoint: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
raw_pid_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
raw_fact_values_exposed: false
fact_value_reconstruction_enabled: false
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
next_exact_posture: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_runtime_v1
```

This selection admits the smallest SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial after the fact-material downstream chain closeout. The trial is not a SEC fetcher, parser, retained-artifact reparser, fact rematerializer, process runner, model runtime, connector dispatcher, or frontend authority surface. It should compare two server-owned fact-material downstream operator-status projections for the same SEC HTML/iXBRL parser, fact authority, fact-material bridge, Gate B, material snapshot, downstream proof, and coverage chain, then write an append-only trial receipt only if both projections are current, `available`, redacted, and bound to the same authority.

The browser may supply only opaque status/proof request identifiers, expected hashes, fixed mode/decision fields, and disposition fields needed to identify the original and repeat projections. The server must reload and revalidate all fact-material proof/status authority before deciding the trial. SEC network acquisition, parser expansion, retained HTML/iXBRL reparsing, raw fact-value reconstruction, XML/XBRL or CompanyFacts authority, taxonomy or financial-statement semantics, provider writes, connector dispatch, RAG/model runtime, full mockup activation, browser storage, and frontend durable authority remain blocked.

## Next Runtime Requirements

The next runtime implementation must:

1. Add a server endpoint for `record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial`.
2. Load and revalidate the original SEC HTML/iXBRL fact-material downstream operator-status projection.
3. Load and revalidate the repeat SEC HTML/iXBRL fact-material downstream operator-status projection.
4. Require both projections to be `available`.
5. Require matching source family, parser family, typed content contract, connector/source artifact hashes, primary document hash, content order hash, inline XBRL marker inventory hash, fact authority receipt, fact inventory hash, fact-material bridge receipt, materialization receipt, material preview hash, Gate B decision/session, DatasetVersion id/hash, selection manifest, material snapshot hash, downstream proof hash, coverage evidence hash, and negative-invariant hash.
6. Compare operator-status hashes, proof hashes, fact inventory hashes, fact-material authority hashes, coverage step sets, and downstream receipt/hash bindings.
7. Record an accepted or blocked operator disposition in an append-only trial receipt without mutating proof, material, Gate B, package, delivery, source, parser, fact authority, fact-material bridge, or default-selector authority.
8. Reject stale, missing, mismatched, raw-leaking, non-available, browser-owned, path-owned, URL-owned, raw-fact-value-owned, command-owned, process-owned, stdout/stderr-owned, or artifact-byte-owned authority.
9. Preserve baseline rollback, Candidate A semantics, and Candidate B admitted default scope.
10. Avoid SEC acquisition, parser expansion, retained artifact reparsing/rematerialization, process execution, provider writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, and full mockup activation.

## Coherence Check

- Is this endpoint a SEC/EDGAR filing processor or fact parser? Recommended answer: no. It is a repeatability comparator and receipt writer over two already server-owned fact-material downstream status projections.
- Does it admit SEC network fetches, retained HTML/iXBRL reparsing, XML/XBRL fact authority, CompanyFacts, taxonomy resolution, financial-statement semantics, or raw fact-value reconstruction? Recommended answer: no.
- Can the browser provide paths, SEC URLs, raw fact values, commands, process state, stdout/stderr, or artifact bytes to prove repeatability? Recommended answer: no. It can identify server status/proof authority only; the server reloads authority.
- Why select this before rendered repeatability UI? Recommended answer: rendered controls would otherwise risk frontend authority. The server-owned append-only trial contract must exist first.
