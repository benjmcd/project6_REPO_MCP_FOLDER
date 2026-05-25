# Candidate B Broader Eligible Corpus Default Scope Selector-Use Remediation Current-Main Sync

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_current_main_sync_v1
source_broader_eligible_corpus_default_scope_selector_use_rendered_stale_input_review_remediation: next_milestone_plans/Layer3_planning_docs/1077-cb-broader-eligible-corpus-default-scope-selector-use-rendered-stale-input-review-remediation.md
base_authority: project6-origin/main@d400a3ac7965e3e7d3221751bc4ab09665633818
merged_pr: "#1780"
source_branch: codex/cb-selector-use-sync
source_commit: 15109675064df2d156bd1b67936edda941c39c46
merge_commit: d400a3ac7965e3e7d3221751bc4ab09665633818
sync_status: current_main_synced_candidate_b_broader_scope_selector_use_stale_input_remediation
synced_rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_selector_use_status_control
synced_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
synced_runtime_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use
synced_operator_surface: /review/layer3 Candidate B default-promotion status panel
synced_runtime_default_helper: candidateBBroaderScopeSelectorUseRuntimeDefaults
synced_operator_edit_tracking: candidateBBroaderScopeSelectorUseInputEdited
synced_latest_runtime_receipt_default: true
synced_stale_selector_use_status_cleared_on_runtime_success: true
synced_second_runtime_receipt_proof: cb-broader-scope-runtime-rendered-proof-2
ci_backend_layer3_api: pass
ci_test: pass
review_threads_total_count: 0
unresolved_review_threads_total_count: 0
source_pr_1779_review_threads_total_count: 1
source_pr_1779_unresolved_review_threads_after_remediation: 0
current_main_progress_check: python ./tools/l3-progress-check.py PASS
runtime_behavior_introduced_by_this_sync: false
rendered_behavior_introduced_by_this_sync: false
backend_behavior_introduced_by_this_sync: false
route_api_dto_model_migration_service_behavior_introduced_by_this_sync: false
executable_test_behavior_introduced_by_this_sync: false
production_ui_behavior_introduced_by_this_sync: false
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_operator_status_inspection_v1
```

PR `#1780` makes the selector-use stale runtime input remediation current-main behavior. The rendered selector-use form now defaults to the latest selected broader-scope runtime receipt after runtime re-recording, clears stale selector-use status, and preserves explicit operator edits only after the operator edits the selector-use fields. The prior PR `#1779` review thread is resolved.

This sync records current-main posture only. It introduces no new runtime, backend, route, selector, source-ingestion, provider, connector, model, browser-storage, full-mockup, or frontend durable authority behavior beyond what PR `#1780` already merged.

## Current-Main Evidence

- PR `#1780` merged at `d400a3ac7965e3e7d3221751bc4ab09665633818`.
- PR `#1780` CI passed: `backend-layer3-api` and `test`.
- PR `#1780` review surface was clean: comments `0`, reviews `0`.
- Source PR `#1779` review thread `PRRT_kwDORzuv8M6EbkL8` is resolved.
- Post-merge current-main validation: `python ./tools/l3-progress-check.py` passed on `project6-origin/main@d400a3ac7965e3e7d3221751bc4ab09665633818`.

## Coherence Check

- Is the stale selector-use input remediation current-main authority now? Recommended answer: yes. PR `#1780` merged and current-main progress validation passes.
- Does this sync make broader corpus classes the default? Recommended answer: no. It records current-main sync only; selector use remains receipt-bound and class-bound.
- What is the next useful slice? Recommended answer: add or prove operator status inspection for selected selector-use receipts before broader default-promotion closeout.
