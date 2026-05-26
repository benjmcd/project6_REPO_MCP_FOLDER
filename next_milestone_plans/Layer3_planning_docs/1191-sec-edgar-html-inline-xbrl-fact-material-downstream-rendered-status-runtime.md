# SEC EDGAR HTML Inline XBRL Fact Material Downstream Rendered Status Runtime

```yaml
milestone: sec_edgar_html_inline_xbrl_fact_material_downstream_rendered_status_runtime_v1
source_rendered_status_selection: next_milestone_plans/Layer3_planning_docs/1190-sec-edgar-html-inline-xbrl-fact-material-downstream-rendered-status-selection.md
source_fact_material_operator_status_runtime: next_milestone_plans/Layer3_planning_docs/1189-sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-runtime.md
source_existing_html_inline_xbrl_rendered_status_runtime: next_milestone_plans/Layer3_planning_docs/1179-sec-edgar-html-inline-xbrl-downstream-rendered-status-runtime.md
current_main_entry: b6b78ca786e076b225d1beddaf0af5b04d3d92c1
entry_decision: runtime_implementation
runtime_status: implemented
rendered_status: implemented
implemented_rendered_mode: rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_control
implemented_status_mode: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_v1
implemented_operator_decision: inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status
implemented_status_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status
implemented_existing_proof_endpoint: /api/v1/layer3/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof
implemented_bootstrap_capability: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status
implemented_bootstrap_endpoint_field: sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_endpoint
implemented_rendered_panel: sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-panel
implemented_rendered_form: sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-form
implemented_rendered_submit: sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-submit
implemented_payload_fields: client_request_id,status_mode,operator_decision,fact_material_downstream_proof_request,expected_proof_hash
implemented_status_states: not_recorded,available,blocked
implemented_fixture_route: /__test/layer3/sec-edgar-html-inline-xbrl-fact-material-downstream-status
implemented_fixture_authority_chain: real_filing_connector_acquisition,html_inline_xbrl_source_family_parser,html_inline_xbrl_fact_authority,html_inline_xbrl_fact_material_authority_bridge,gate_b_commit,html_inline_xbrl_fact_material_downstream_proof,html_inline_xbrl_fact_material_downstream_operator_status
implemented_files: backend/app/review_ui/static/layer3.html,backend/app/review_ui/static/layer3.js,backend/tests/review_browser_server.py,backend/tests/test_review_browser_server.py,backend/tests/test_layer3_page.py,e2e/layer3-workbench.spec.js
server_revalidates_submitted_fact_material_proof_request: true
browser_held_hash_alone_is_not_authority: true
not_recorded_status_renders: true
available_status_renders: true
blocked_status_renders: true
stale_or_mismatched_proof_hash_fails_closed: true
raw_or_forbidden_proof_authority_fails_closed: true
raw_fact_values_must_not_render: true
fact_value_reconstruction_by_rendered_status_admitted: false
rendered_status_can_create_downstream_proof: false
rendered_status_can_mutate_gate_b_session: false
rendered_status_can_mutate_material_snapshot: false
rendered_status_can_mutate_package_or_delivery: false
rendered_status_can_fetch_sec_content: false
rendered_status_can_run_submissions_lookup: false
rendered_status_can_reparse_or_materialize_html_inline_xbrl: false
rendered_status_can_create_xml_xbrl_fact_authority: false
rendered_status_can_call_sec_companyfacts_api: false
rendered_status_can_resolve_taxonomy_networks: false
rendered_status_can_add_financial_statement_semantics: false
rendered_status_can_classify_facts_to_statements: false
rendered_status_can_dispatch_connector: false
rendered_status_can_write_provider_object: false
rendered_status_can_add_rag_or_model_runtime: false
rendered_status_can_activate_full_mockup: false
raw_proof_request_rendered: false
raw_proof_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
artifact_bytes_rendered: false
raw_fact_values_rendered: false
fact_value_reconstruction_enabled: false
provider_token_rendered: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
sec_edgar_network_fetch_by_rendered_status: false
sec_edgar_parser_expansion_admitted: false
html_inline_xbrl_reparse_or_materialization_admitted_in_rendered_status: false
xml_xbrl_fact_authority_admitted: false
sec_companyfacts_api_runtime_enabled: false
taxonomy_network_resolution_enabled: false
financial_statement_semantics_admitted: false
fact_to_statement_classification_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
focused_py_compile: python -m py_compile ./backend/tests/review_browser_server.py ./backend/tests/test_review_browser_server.py ./backend/tests/test_layer3_page.py PASS
focused_js_check: node --check ./backend/app/review_ui/static/layer3.js PASS
focused_review_browser_pytest: python -m pytest ./backend/tests/test_review_browser_server.py -q -k "fact_material_downstream_status or html_inline_xbrl_downstream_status or review_browser_harness_info" PASS
focused_page_pytest: python -m pytest ./backend/tests/test_layer3_page.py -q -k "render or javascript" PASS
headless_rendered_status_proof: npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "fact-material" PASS
headed_rendered_status_proof: npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "fact-material" PASS
verification_progress_check: python ./tools/l3-progress-check.py PASS
verification_target_selection: python ./tools/l3-target-selection-validate.py --expect frozen PASS
next_exact_posture: sec_edgar_html_inline_xbrl_fact_material_downstream_rendered_status_current_main_sync_v1
```

The rendered runtime adds the operator-visible inspection control for the existing SEC EDGAR HTML/iXBRL fact-material downstream status endpoint. The panel can submit the exact fact-material downstream proof request plus expected proof hash to the server and render only the server-returned redacted projection.

The fixture prepares the current-main authority chain through the test-only fake SEC client boundary, then proves status revalidation through connector receipt, HTML/iXBRL parser receipt, fact authority receipt, fact material bridge receipt, Gate B session, downstream proof, and operator status. The rendered action itself does not create proof, mutate Gate B or material snapshots, fetch SEC content, run submissions lookup, reparse/rematerialize HTML/iXBRL, reconstruct fact values, resolve taxonomy, add statement semantics, dispatch connectors, write provider objects, activate full mockup behavior, or create frontend durable authority.

## Coherence Check

- Does this runtime make the browser-held proof request or expected hash durable authority? Recommended answer: no. `available` requires server revalidation and expected proof hash agreement.
- Does the rendered panel expose fact values, `value_text`, raw SEC URLs, local paths, retained HTML bytes, or artifact storage refs? Recommended answer: no. It renders the status projection and hashes only.
- Does this admit CompanyFacts, taxonomy network resolution, statement semantics, or fact-to-statement classification? Recommended answer: no. Those remain separate future slices.
- What is next? Recommended answer: current-main sync/closeout for this rendered runtime, then select the next exact SEC/EDGAR slice only if it advances fact authority downstream usability without widening source/runtime/provider scope.
