# SEC EDGAR HTML Inline XBRL Fact Material Downstream Rendered Status Current Main Sync

```yaml
milestone: sec_edgar_html_inline_xbrl_fact_material_downstream_rendered_status_current_main_sync_v1
source_rendered_status_runtime: next_milestone_plans/Layer3_planning_docs/1191-sec-edgar-html-inline-xbrl-fact-material-downstream-rendered-status-runtime.md
current_main_entry: e33116c78c4567075f5aee0ec1c66ce99113414d
source_pr: "#1894"
source_branch: codex/sec-ixbrl-fact-rendered-status-runtime
source_commit: 015c37da46d0e683068a1208985f3670b8486930
source_merge_commit: e33116c78c4567075f5aee0ec1c66ce99113414d
merge_state_before_merge: CLEAN
review_comments_count: 0
reviews_count: 0
ci_status: no_checks_reported
ci_successful_checks: 0
local_proof_status: passed
current_main_progress_check: python ./tools/l3-progress-check.py PASS
current_main_target_selection_check: python ./tools/l3-target-selection-validate.py --expect frozen PASS
synced_bootstrap_capability: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status
synced_status_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status
synced_existing_proof_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof
synced_rendered_mode: rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_control
synced_status_mode: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_v1
synced_operator_decision: inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status
synced_panel: sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-panel
synced_form: sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-form
synced_submit: sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-submit
synced_payload_fields: client_request_id,status_mode,operator_decision,fact_material_downstream_proof_request,expected_proof_hash
synced_status_states_rendered: not_recorded,available,blocked
synced_available_requires_server_revalidated_fact_material_proof_request: true
synced_available_requires_expected_proof_hash_match: true
synced_browser_held_hash_alone_is_not_authority: true
synced_stale_or_mismatched_proof_hash_fails_closed: true
synced_server_revalidated_status_projection_displayed: true
synced_parser_authority_bound: true
synced_fact_authority_bound: true
synced_fact_material_bridge_authority_bound: true
synced_gate_b_material_authority_bound: true
synced_test_only_fixture_route: /__test/layer3/sec-edgar-html-inline-xbrl-fact-material-downstream-status
synced_test_only_fixture_user_facing_authority: false
synced_headless_rendered_status_proof: true
synced_headed_rendered_status_proof: true
runtime_behavior_introduced_by_this_sync: false
rendered_behavior_introduced_by_this_sync: false
backend_behavior_introduced_by_this_sync: false
proof_mutation_performed: false
gate_b_mutation_performed: false
material_snapshot_mutation_performed: false
package_or_delivery_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
sec_edgar_network_fetch_admitted_by_sync: false
sec_edgar_parser_expansion_admitted: false
html_inline_xbrl_reparse_or_materialization_admitted: false
xml_xbrl_fact_authority_admitted: false
sec_companyfacts_api_runtime_enabled: false
taxonomy_network_resolution_enabled: false
financial_statement_semantics_admitted: false
fact_to_statement_classification_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_proof_request_rendered_in_status_projection: false
raw_proof_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
artifact_bytes_rendered: false
raw_fact_values_rendered: false
fact_value_reconstruction_enabled: false
provider_token_rendered: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
next_exact_posture: sec_edgar_html_inline_xbrl_fact_material_downstream_closeout_readiness_v1
```

PR `#1894` merged the SEC EDGAR HTML/iXBRL fact-material downstream rendered operator-status inspection surface into current main. The landed tree is now `e33116c78c4567075f5aee0ec1c66ce99113414d`. GitHub did not attach status checks to this PR after the wait window, so this sync records `ci_status: no_checks_reported` and relies on the local proof suite captured in the runtime checkpoint.

This sync records no new runtime, backend, rendered, parser, connector, or storage behavior beyond the merged slice. The current-main surface is a redacted operator-status inspection path over existing fact-material downstream proof authority. It does not create proof, mutate Gate B/session/material/package/delivery state, fetch from SEC, run submissions lookup, reparse or rematerialize retained HTML/iXBRL bytes, reconstruct fact values, create XML/XBRL or CompanyFacts authority, add taxonomy or financial-statement semantics, expose raw URLs/paths/artifact bytes/provider tokens, or add provider, connector, RAG/model, browser-storage, frontend durable, auth/security, or full mockup authority.

## Coherence Check

- Does this sync add runtime behavior? Recommended answer: no. It records the merged current-main state only.
- Did GitHub report CI checks for PR `#1894`? Recommended answer: no. The PR merged cleanly with no reviews and no status check rollup; local proof is the evidence source for this sync.
- Is the test-only fixture route user-facing authority? Recommended answer: no. It prepares browser proof inputs only.
- What comes next? Recommended answer: run a closeout-readiness checkpoint for the bounded SEC HTML/iXBRL fact-material downstream rendered status chain, then choose the next exact SEC/EDGAR slice that advances fact/table authority, real corpus execution, or downstream operator usability without widening parser/source/provider/runtime scope.
