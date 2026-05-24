# Candidate B Broader Eligible Corpus Default Scope Runtime Current-Main Sync

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_runtime_current_main_sync_v1
source_broader_eligible_corpus_default_scope_runtime_rendered_status: next_milestone_plans/Layer3_planning_docs/1072-cb-broader-eligible-corpus-default-scope-runtime-rendered-status.md
base_authority: project6-origin/main@b7c7bd75e853250338ea3c7335c02ed2f9ade777
merged_pr: "#1775"
source_branch: codex/cb-scope-runtime-rendered
source_commit: 4d9dfdac830d10b0e8b807d8c0c82eb39723bf80
merge_commit: b7c7bd75e853250338ea3c7335c02ed2f9ade777
sync_status: current_main_synced_candidate_b_broader_scope_runtime_rendered_status
synced_rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_runtime_status_control
synced_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
synced_runtime_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime
synced_selected_state: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
synced_blocked_state: candidate_b_broader_eligible_corpus_default_scope_runtime_blocked
synced_operator_surface: /review/layer3 Candidate B default-promotion status panel
synced_input_authority: ready_broader_scope_readiness_audit_json_plus_exact_selected_scope_classes
synced_server_authority: readiness_audit_id_hash_binding_and_redacted_runtime_receipt
ci_backend_layer3_api: pass
ci_test: pass
review_threads_total_count: 0
unresolved_review_threads_total_count: 0
merge_state_before_merge: CLEAN
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
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_selection_v1
```

PR `#1775` makes the broader eligible-corpus default-scope runtime rendered status control current-main behavior. Operators can now inspect and invoke the admitted runtime from the Candidate B status panel by supplying a server-produced ready broader-scope readiness audit and exact selected scope classes. The server remains the authority for audit id/hash binding, selected versus blocked status, redacted receipt projection, and fail-closed rejection.

This sync introduces no new runtime behavior beyond what PR `#1775` already merged, and it does not use the broader-scope runtime receipt to mutate the default selector. Candidate B remains the current default for eligible/effective PDFs only; baseline remains the non-PDF default and rollback path; Candidate A semantics remain unchanged; and broader default-scope selector use remains a separately selected future slice.

## Current-Main Evidence

- PR `#1775` merged at `b7c7bd75e853250338ea3c7335c02ed2f9ade777`.
- PR `#1775` CI passed: `backend-layer3-api` and `test`.
- PR `#1775` merge state was `CLEAN`.
- PR `#1775` review surface was clean: comments `0`, reviews `0`, review threads `0`, unresolved review threads `0`.
- Post-merge current-main validation: `python ./tools/l3-progress-check.py` passed on `project6-origin/main@b7c7bd75e853250338ea3c7335c02ed2f9ade777`.

## Non-Admission Boundary

This sync does not admit broader default selector use, source expansion, runtime DB/storage expansion, PDF/image text material ingestion, provider object writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, full mockup activation, browser storage authority, frontend durable authority, raw local path exposure, or raw URL exposure.

## Coherence Check

- Is the rendered runtime status current-main authority now? Recommended answer: yes. PR `#1775` merged and current-main progress validation passes.
- Does this sync make broader corpus classes the default? Recommended answer: no. It records current-main sync only; selector use remains a separate decision.
- What is the next useful slice? Recommended answer: freeze whether and how a redacted broader-scope runtime receipt can be used as selector authority for exact selected classes.
