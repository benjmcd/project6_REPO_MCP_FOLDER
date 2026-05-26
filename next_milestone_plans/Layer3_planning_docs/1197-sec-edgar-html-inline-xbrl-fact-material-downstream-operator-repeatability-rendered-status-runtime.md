# SEC EDGAR HTML Inline XBRL Fact Material Downstream Operator Repeatability Rendered Status Runtime

```yaml
milestone: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_rendered_status_runtime_v1
source_rendered_status_selection: next_milestone_plans/Layer3_planning_docs/1196-sec-edgar-html-inline-xbrl-fact-material-downstream-operator-repeatability-rendered-status-selection.md
source_repeatability_trial_runtime: next_milestone_plans/Layer3_planning_docs/1195-sec-edgar-html-inline-xbrl-fact-material-downstream-operator-repeatability-trial-runtime.md
source_existing_live_repeatability_rendered_status_runtime: next_milestone_plans/Layer3_planning_docs/1163-sec-edgar-text-table-live-source-artifact-downstream-operator-repeatability-rendered-status-runtime.md
current_main_entry: 76cf2a85eb429835888aa46495bce0b69f8861cf
runtime_status: implemented
rendered_status: implemented
implemented_bootstrap_capability: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial
implemented_bootstrap_endpoint_field: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_endpoint
implemented_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/operator-repeatability/trial
implemented_existing_fact_material_status_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status
implemented_rendered_mode: rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_control
implemented_trial_mode: append_only_trial_receipt_over_original_and_repeat_fact_material_downstream_status_authority_without_sec_fetch_or_processing_execution
implemented_operator_decision: record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial
implemented_panel: sec-edgar-html-inline-xbrl-fact-material-downstream-repeatability-trial-panel
implemented_form: sec-edgar-html-inline-xbrl-fact-material-downstream-repeatability-trial-form
implemented_submit: sec-edgar-html-inline-xbrl-fact-material-downstream-repeatability-trial-submit
implemented_static_runtime: backend/app/review_ui/static/layer3.js
implemented_static_shell: backend/app/review_ui/static/layer3.html
implemented_trial_states_rendered: accepted,blocked
implemented_payload_fields: client_request_id,trial_mode,operator_decision,original_operator_status_request,original_operator_status_hash,repeat_operator_status_request,repeat_operator_status_hash,operator_repeatability_disposition,operator_confirmation
implemented_response_projection_fields: operator_repeatability_trial_state,operator_repeatability_disposition,trial_receipt_id,trial_receipt_hash,trial_receipt_ref,authority_pair_hash,idempotent_replay,original_operator_status,repeat_operator_status,authority_bindings,operator_status_hash_comparison,proof_hash_comparison,coverage_step_set_comparison,fact_inventory_hash_comparison,fact_material_authority_hash_comparison,trial_authority,operator_visible_repeatability_trial_status,fail_closed_behavior,negative_invariants,next_allowed_actions
accepted_status_rendered: true
blocked_status_rendered: true
idempotent_replay_rendered: true
available_statuses_must_be_server_revalidated: true
browser_held_status_hash_alone_is_not_authority: true
append_only_repeatability_trial_receipt_required: true
exclusive_trial_per_original_repeat_authority_pair_required: true
stale_original_operator_status_must_fail_closed: true
stale_repeat_operator_status_must_fail_closed: true
mismatched_source_or_parser_family_must_fail_closed: true
mismatched_fact_authority_must_fail_closed: true
mismatched_fact_inventory_must_fail_closed: true
mismatched_fact_material_bridge_must_fail_closed: true
mismatched_material_authority_must_fail_closed: true
mismatched_inline_xbrl_marker_inventory_must_fail_closed: true
mismatched_gate_b_or_selection_must_fail_closed: true
mismatched_downstream_proof_hash_must_fail_closed: true
mismatched_coverage_evidence_must_fail_closed: true
test_only_fixture_route: /__test/layer3/sec-edgar-html-inline-xbrl-fact-material-repeatability-trial
test_only_fixture_route_scope: prepares_existing_sec_edgar_html_inline_xbrl_fact_material_parser_fact_authority_material_bridge_gate_b_downstream_proof_and_status_requests_for_browser_to_submit_to_production_trial_endpoint
test_only_fixture_route_user_facing_authority: false
sec_edgar_browser_fixture_state_isolation: true
rendered_trial_creates_fact_material_downstream_proof: false
rendered_trial_mutates_gate_b_session: false
rendered_trial_mutates_material_snapshot: false
rendered_trial_mutates_package_or_delivery: false
rendered_trial_fetches_sec_content: false
rendered_trial_reparses_html_inline_xbrl: false
rendered_trial_reconstructs_raw_fact_values: false
rendered_trial_creates_xml_xbrl_or_companyfacts_authority: false
rendered_trial_creates_runtime_storage_root: false
rendered_trial_starts_process: false
rendered_trial_dispatches_connector: false
rendered_trial_writes_provider_object: false
rendered_trial_adds_rag_or_model_runtime: false
rendered_trial_activates_full_mockup: false
raw_original_status_request_rendered: false
raw_repeat_status_request_rendered: false
raw_trial_receipt_path_rendered: false
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
html_inline_xbrl_reparse_or_rematerialization_admitted: false
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
focused_py_compile: python -m py_compile ./backend/tests/review_browser_server.py ./backend/tests/test_review_browser_server.py ./backend/tests/test_layer3_page.py ./backend/app/services/layer3_bootstrap_contract.py PASS
focused_node_check: node --check ./backend/app/review_ui/static/layer3.js PASS
focused_backend_page_pytest: python -m pytest ./backend/tests/test_layer3_bootstrap_contract.py ./backend/tests/test_layer3_page.py ./backend/tests/test_review_browser_server.py -q -k "bootstrap_contract or layer3_page or fact_material_repeatability" PASS
headless_rendered_trial_proof: npx playwright test ./e2e/layer3-workbench.spec.js --grep "fact-material downstream repeatability trial" --project=chromium PASS
headed_rendered_trial_proof: npx playwright test ./e2e/layer3-workbench.spec.js --grep "fact-material downstream repeatability trial" --project=chromium --headed PASS
next_exact_posture: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_rendered_status_current_main_sync_v1
```

The rendered workbench now exposes a SEC EDGAR HTML/iXBRL fact-material downstream repeatability-trial surface backed by the existing production repeatability endpoint. The browser may submit only the original and repeat fact-material downstream operator-status requests plus expected status hashes, disposition, and confirmation. The server revalidates both status projections, compares fact/material/proof/coverage authority, records or blocks the append-only receipt, and returns only redacted operator-visible projection fields.

The browser proof uses a test-only fixture route only to prepare existing SEC HTML/iXBRL parser, fact authority, fact-material bridge, Gate B, downstream proof, and status-request inputs. The rendered operator action still calls the production `/api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/operator-repeatability/trial` endpoint. The panel keeps SEC fetch, parser expansion, raw fact-value reconstruction, proof mutation, Gate B mutation, provider writes, connector dispatch, RAG/model runtime, full mockup activation, browser storage authority, frontend durable authority, raw paths, raw URLs, receipt paths, and artifact bytes out of scope.

## Coherence Check

- Does the rendered surface create fact-material downstream proof or re-run SEC acquisition/parser work? Recommended answer: no. It records a trial over two server-revalidated fact-material downstream status projections only.
- Does the browser-held status JSON or hash become durable authority? Recommended answer: no. The server revalidates both submitted status requests and rejects stale or mismatched hashes.
- Are raw SEC URLs, local paths, artifact bytes, receipt paths, raw fact values, process output, or provider credentials rendered? Recommended answer: no. The headed/headless proof checks redacted projection and forbidden raw-authority absence.
- What comes next? Recommended answer: sync this runtime to current main, then use current-main evidence to choose whether the next exact SEC slice is closeout/current-main sync or the broader real-filing acquisition/corpus-validation path.
