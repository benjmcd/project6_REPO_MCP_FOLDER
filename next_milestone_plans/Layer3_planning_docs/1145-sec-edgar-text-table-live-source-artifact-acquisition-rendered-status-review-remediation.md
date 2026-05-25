# SEC EDGAR Text Table Live Source Artifact Acquisition Rendered Status Review Remediation

```yaml
milestone: sec_edgar_text_table_live_source_artifact_acquisition_rendered_status_review_remediation_v1
source_runtime: next_milestone_plans/Layer3_planning_docs/1144-sec-edgar-text-table-live-source-artifact-acquisition-rendered-status-runtime.md
current_main_entry: 5c5df31369f485848f392c247bb7a6e82c16b8bb
source_pr: 1848
source_branch: codex/sec-edgar-live-acquisition-rendered-status
source_commits: b456a4ec00f06880bd971622204e8a0a0d4e4994
source_merge_commit: 5c5df31369f485848f392c247bb7a6e82c16b8bb
entry_decision: review_remediation
runtime_status: unchanged
rendered_status: unchanged
review_threads_found_after_merge: 3
review_thread_source: gh_api_graphql_pr_1848_reviewThreads
review_thread_path: backend/tests/review_browser_server.py
review_thread_lines: 836,838,845
review_remediation_status: implemented
review_remediation_scope: review_browser_fixture_and_test_harness_state_isolation_only
implemented_seeded_sec_client: _ReviewBrowserSeededSecEdgarClient
implemented_seed_registration: register_complete_submission_text
implemented_seed_identity_function: _sec_edgar_live_source_artifact_identity
implemented_fixture_identity_policy: cik_and_accession_are_deterministic_seed_bound_values
implemented_fixture_cache_policy: each_setup_seed_registers_distinct_identity_and_content_hash
implemented_fake_client_call_redaction: url_hash_and_user_agent_hash_only
implemented_fake_client_installation: app_owned_client_installed_once_at_review_browser_app_creation
implemented_setup_route_mutates_sec_client: false
implemented_setup_route_mutates_sec_sleep: false
implemented_setup_route_mutates_sec_settings: false
implemented_patch_state_restore: sec_client_sec_sleep_sec_user_agent_sec_rate_limit_restored
implemented_test_restore_assertion: layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT_is_original_sec_edgar_client
implemented_test_seed_identity_assertion: setup_live_acquisition_request_cik_and_accession_differ_between_setup_calls
implemented_progress_guard: tools/l3-progress-check.py
production_sec_acquisition_behavior_changed: false
production_api_behavior_changed: false
production_rendered_behavior_changed: false
live_sec_manual_smoke_in_this_slice: false
parser_expansion_enabled: false
dataset_version_or_gate_b_mutation_enabled: false
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
server_user_agent_exposed: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_plus_receipt_bound_selected_classes_only
next_exact_posture: sec_edgar_text_table_live_source_artifact_acquisition_rendered_status_review_remediation_current_main_sync_v1
```

The merged rendered SEC EDGAR live source-artifact acquisition/status control had three post-merge review threads against the browser fixture route. The threads were concrete enough to address before recording a current-main closeout: the setup route reused one filing identity across generated content hashes, replaced the process-wide SEC client/sleep globals, and rewrote SEC settings without a dedicated restore path.

This remediation keeps the production runtime and rendered control unchanged. The browser harness now installs one app-owned seeded SEC EDGAR client at app creation, registers seed-specific content for each fixture setup, derives deterministic seed-bound CIK/accession values, stores only URL/User-Agent hashes in fake-client call records, and restores SEC client/sleep/settings through the existing review browser patch-state cleanup.

## Coherence Check

- Does this slice change production SEC acquisition behavior? Recommended answer: no. It changes the review-browser fixture harness and tests only.
- Does the setup route still replace process-wide SEC client/sleep/settings on each call? Recommended answer: no. The app-owned seeded client is installed once for the test app; setup calls only register seed-specific content.
- Does this solve the cache-staleness risk from reused filing identity? Recommended answer: yes. CIK and accession are deterministic functions of the setup seed, so a new setup seed has distinct source identity and content hash authority.
- Does this close the GitHub review-thread state by itself? Recommended answer: no. It addresses the code defects; a follow-up GitHub/PR state check is still required before claiming resolved review posture.
- What comes next? Recommended answer: merge this remediation if checks pass, then record `sec_edgar_text_table_live_source_artifact_acquisition_rendered_status_review_remediation_current_main_sync_v1` before selecting the SEC EDGAR retained source-artifact to Layer 3 material-authority bridge.
