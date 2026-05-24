# 994 - Candidate B Rendered Workflow Run Start Control

## Purpose

Implement the runtime slice admitted by `993-cb-rendered-run-start-freeze.md`: a rendered Candidate B full-corpus workflow run start/progress control that calls the server-owned workflow-run endpoint, then inspects progress/status through the returned status request and the existing read-only status endpoint.

```yaml
milestone: candidate_b_rendered_operator_workflow_run_start_control_v1
source_authority_freeze: next_milestone_plans/Layer3_planning_docs/993-cb-rendered-run-start-freeze.md
current_main_entry: 27d36a3c8c28cc5def58ac6a2b0cf63c532ee9ab
runtime_status: implemented
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_rendered_start_mode: rendered_candidate_b_full_corpus_operator_workflow_run_start_control
selected_rendered_progress_mode: rendered_candidate_b_full_corpus_operator_workflow_run_progress_control
run_schema_id: layer3.candidate_b_full_corpus_operator_workflow_run.v1
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
status_mode: candidate_b_full_corpus_operator_workflow_status_v1
status_operator_decision: inspect_candidate_b_full_corpus_operator_workflow_status
rendered_start_control_admitted: true
rendered_progress_control_admitted: true
rendered_status_control_remains_read_only: true
run_endpoint_status_request_used_for_progress: true
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
queue_scheduler_runtime_admitted: contract_only
cancel_runtime_admitted: contract_only
proof_headless_chrome: passed
proof_headed_chrome: passed
verification_node_check: passed
verification_backend_pytest: 25 passed
verification_headless_e2e: 1 passed
verification_headed_e2e: 1 passed
next_exact_posture: candidate_b_rendered_operator_workflow_run_live_http_operator_proof_v1
```

## Implemented Behavior

The rendered workbench now includes a `candidate-b-full-corpus-workflow-run-form` in the Candidate B full-corpus workflow panel. The form collects only server authority identifiers:

- runtime-root lifecycle receipt id;
- baseline, Candidate A, and Candidate B run ids;
- compare target-set hash;
- optional material relative name.

The browser posts those fields to the server-owned run endpoint. It does not submit runtime roots, source directories, bridge directories, local paths, raw URLs, selector mutations, provider refs, connector destinations, or frontend durable authority.

When the run endpoint returns, the UI stores the redacted run response in transient state, fills the existing workflow status inputs from the returned `status_request`, and posts that exact returned status request to the read-only workflow status endpoint. The existing manual status inspection form remains available.

## Verification

```text
node --check .\backend\app\review_ui\static\layer3.js
python -m pytest .\backend\tests\test_layer3_candidate_b_full_corpus_operator_workflow_run.py .\tests\test_candidate_b_full_corpus_operator_workflow.py -q
npm run test:e2e -- --grep "starts Candidate B full-corpus workflow through rendered server-owned run control"
npm run test:e2e:headed -- --grep "starts Candidate B full-corpus workflow through rendered server-owned run control"
```

Results:

```text
node --check: passed
pytest: 25 passed
headless chromium: 1 passed
headed chromium: 1 passed
```

## Next Posture

The next exact slice is `candidate_b_rendered_operator_workflow_run_live_http_operator_proof_v1`: prove the rendered start/progress control against a configured live Layer 3 server and isolated durable runtime state, not only Playwright-routed browser responses.
