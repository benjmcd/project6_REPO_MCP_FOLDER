# NRC Local Corpus E2E Runbook

## Purpose
This proof runner exercises the live NRC ADAMS APS route chain against the local 69-PDF corpus under `data_demo/nrc_adams_documents_for_testing` inside a fresh isolated runtime. It is a verification surface, not a new operator lane.

## Invocation
Run it directly with the repo-local Phase 7A interpreter:

```powershell
C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\phase7a-py311\Scripts\python.exe `
  C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\run_nrc_aps_local_corpus_e2e.py
```

Optional:

```powershell
C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\phase7a-py311\Scripts\python.exe `
  C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\run_nrc_aps_local_corpus_e2e.py `
  --runtime-root C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\<empty_dir>
```

Candidate B / OpenDataLoader PDF runtime admission can be selected through the same proof tool and the existing `/api/v1/connectors/nrc-adams-aps/runs` path:

```powershell
C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\phase7a-py311\Scripts\python.exe `
  C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\run_nrc_aps_local_corpus_e2e.py `
  --document-processing-engine candidate_b_opendataloader_pdf `
  --runtime-root C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\<empty_dir>
```

Allowed `--document-processing-engine` values are `baseline` and `candidate_b_opendataloader_pdf`. The runner default remains `baseline` and is sent explicitly so the proof exercises baseline rollback even though omitted eligible-PDF submissions select Candidate B in the live API.

Candidate A PageEvidence comparison evidence uses the baseline processing engine with the admitted Candidate A visual lane:

```powershell
..\..\.venvs\phase7a-py311\Scripts\python.exe `
  .\tools\run_nrc_aps_local_corpus_e2e.py `
  --document-processing-engine baseline `
  --visual-lane-mode candidate_a_page_evidence_v1 `
  --runtime-root .\backend\app\storage_test_runtime\lc_e2e\<empty_dir>
```

After baseline, Candidate A, and Candidate B full-corpus receipts exist in the same checkout, validate the compare triplet without seeding or generating artifacts:

```powershell
..\..\.venvs\phase7a-py311\Scripts\python.exe .\tools\validate_full_corpus_triplet.py --checkout-root .
```

The triplet validator is intentionally validate-only. It proves `candidate_b_full_corpus_compare_triplet_v1` from existing receipts and SQLite request config. It must not seed missing evidence or generate bridge artifacts.

## Candidate B Full-Corpus Layer 3 Workflow

After the triplet validates, the current admitted Layer 3 bridge mode is:

```text
candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
```

The bridge request must use the validated baseline, Candidate A, and Candidate B run ids from the same checkout. The current proven triplet is:

```yaml
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
```

Prepare the bridge only after `LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR` points at a server-owned bridge directory outside app storage, raw storage, artifact storage, and export staging. The API payload is:

```json
{
  "client_request_id": "candidate-b-full-corpus-runtime-bridge",
  "bridge_mode": "candidate_b_full_corpus_runtime_to_layer3_material_authority_v1",
  "candidate_b_run_id": "f644b3f6-a7a9-4889-84d9-d842f5d12e79",
  "baseline_run_id": "7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20",
  "candidate_a_run_id": "9b09f014-95f9-41cb-820c-8f5296a993bc",
  "operator_confirmation": true
}
```

Expected bridge receipt from the current proven run:

```yaml
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
curated_file_count: 71
material_text_files: 69
top_level_files:
  - compare-targets.json
  - runtime-summary.json
material_file_for_smoke: text/target-00001.md
```

Then set `LAYER3_SOURCE_INGESTION_DIR` to the server-owned curated material root for that receipt and run the normal Layer 3 source-directory path:

1. Source-directory scan over the curated root; expect 71 eligible files.
2. Material preview for `text/target-00001.md`.
3. Gate B approval for that material candidate.
4. Hybrid qualitative analysis over the approved material snapshot.
5. Package commit.
6. Package review submit.
7. Handoff/export prepare.
8. External export download prepare.
9. Same-origin delivery status and same-origin delivery.
10. Provider-private redacted prepare, status, use, and revoke.
11. Internal webhook dispatch and status.
12. Qualitative-analysis status projection and session projection.
13. Candidate B visual-lane status.
14. Candidate B runtime downstream proof with all required coverage steps.

The historical downstream receipt guarded by the progress checker is:

```yaml
downstream_proof_id: cb-runtime-downstream-proof-1a8c44a841830707c2168578
coverage_count: 17
```

The latest merged-current-main downstream receipt is:

```yaml
downstream_proof_id: cb-runtime-downstream-proof-1d437ddfaaae417cf0b0f386
coverage_count: 17
provider_private_state: provider_private_signed_url_prepared
provider_private_revoke_state: provider_private_signed_url_revoked
internal_webhook_state: source_directory_internal_webhook_dispatched
candidate_b_default_promotion_enabled: false
```

For operator repeatability against current main, run the governed workflow runner from a checkout where the live baseline, Candidate A, and Candidate B full-corpus runtime roots are present:

```powershell
python .\tools\run_candidate_b_full_corpus_operator_workflow.py
```

If the three full-corpus runtime roots are not inside the proof checkout but are available under one admitted `storage_test_runtime\lc_e2e` parent, pass the three roots explicitly:

```powershell
python .\tools\run_candidate_b_full_corpus_operator_workflow.py `
  --baseline-run-root "<baseline full-corpus runtime root>" `
  --candidate-a-run-root "<Candidate A full-corpus runtime root>" `
  --candidate-b-run-root "<Candidate B full-corpus runtime root>"
```

The explicit roots must all share one `storage_test_runtime\lc_e2e` or `storage\lc_e2e` parent. During the bridge call, the runner temporarily uses that parent as server-side runtime discovery authority, then restores isolated Layer 3 storage for downstream proof. The request to the Layer 3 bridge still carries only run ids, never local path fields.

Each runner execution now records the selected runtime roots in a redacted lifecycle receipt before the Layer 3 bridge runs:

```text
schema_id: candidate_b.full_corpus_runtime_root_lifecycle.v1
lifecycle_mode: candidate_b_full_corpus_runtime_root_lifecycle_v1
receipt_id_prefix: cb-full-corpus-runtime-roots-
default_receipt_dir: repo://backend/app/storage_test_runtime/lc_e2e/cb-full-corpus-runtime-root-lifecycle
root_count: 3
validate_only_triplet: true
runtime_roots_moved_or_copied: false
runtime_artifacts_seeded_by_lifecycle: false
raw_local_path_exposed: false
raw_url_exposed: false
```

The lifecycle receipt hashes each selected run's `local_corpus_e2e_summary.json` and `lc.db`, binds the baseline/Candidate A/Candidate B run ids and compare target set, and stores only repo-relative or redacted references. It is an authority binding for the existing runtime roots, not a copier, seeder, importer, or source-expansion mechanism.

The merged-current-main proof checkpoint is:

```yaml
main_commit: 11d63b329fe7af253c5ec06c7817a4c65ba29580
receipt_id: cb-full-corpus-operator-8228167a5375e8a76a00918a
receipt_hash: 8228167a5375e8a76a00918a5f00e56dba4215993e34ad17ff66e3f57d549768
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-1d437ddfaaae417cf0b0f386
downstream_proof_hash: 1d437ddfaaae417cf0b0f386ce1a3cdd0f51ca637687a417a5fcb2143851fa80
workflow_status: proven
status_endpoint_status: available
raw_local_path_exposed: false
raw_url_exposed: false
```

The runner emits `candidate_b.full_corpus_layer3_operator_workflow.v1` with `workflow_mode: candidate_b_full_corpus_operator_workflow_v1`. It writes one durable receipt per execution:

```yaml
receipt_id_prefix: cb-full-corpus-operator-
downstream_proof_id_prefix: cb-runtime-downstream-proof-
status: proven
coverage_count: 17
source_directory_eligible_file_count: 71
raw_local_path_exposed: false
raw_url_exposed: false
```

To inspect the receipt through the operator status surface, configure `LAYER3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR` or `settings.layer3_candidate_b_full_corpus_operator_workflow_dir` to the server-owned workflow receipt directory, then call:

```text
POST /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
```

with:

```json
{
  "client_request_id": "candidate-b-full-corpus-operator-status-check",
  "status_mode": "candidate_b_full_corpus_operator_workflow_status_v1",
  "operator_decision": "inspect_candidate_b_full_corpus_operator_workflow_status",
  "operator_workflow_receipt_id": "cb-full-corpus-operator-8228167a5375e8a76a00918a",
  "baseline_run_id": "7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20",
  "candidate_a_run_id": "9b09f014-95f9-41cb-820c-8f5296a993bc",
  "candidate_b_run_id": "f644b3f6-a7a9-4889-84d9-d842f5d12e79",
  "bridge_receipt_id": "cb-runtime-l3-0110fe894c68d6a0291f9979",
  "downstream_proof_id": "cb-runtime-downstream-proof-1d437ddfaaae417cf0b0f386"
}
```

Expected status output:

```yaml
status: available
workflow_status: proven
workflow_receipt_id: cb-full-corpus-operator-8228167a5375e8a76a00918a
workflow_receipt_hash: 8228167a5375e8a76a00918a5f00e56dba4215993e34ad17ff66e3f57d549768
artifact_bytes_exposed: false
selector_mutation_performed: false
negative_invariants:
  raw_local_path_exposed: false
  raw_url_exposed: false
  provider_public_url_enabled: false
  provider_object_writes_enabled: false
  connector_dispatch_enabled: false
  rag_vector_model_runtime_enabled: false
  frontend_durable_authority_enabled: false
  full_mockup_activation_enabled: false
```

After the runtime-root lifecycle receipt landed, the merged-current-main lifecycle proof checkpoint is:

```yaml
main_commit: 5f8c3964597bada9af993b3d835cbd06cec63256
workflow_receipt_id: cb-full-corpus-operator-5be9b2dcecb9810127379140
workflow_receipt_hash: 5be9b2dcecb9810127379140f392b367976ab07800a0723d3008b626490db25e
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-f0ea5bd2af66a9da70cc73bd
downstream_proof_hash: f0ea5bd2af66a9da70cc73bddaa933a01e177e662e7192d63784f551a66139ab
status_endpoint_status: available
runtime_root_lifecycle_projection_visible: true
root_count: 3
raw_local_path_exposed: false
raw_url_exposed: false
selector_mutation_performed: false
```

The lifecycle-bearing status projection reports `runtime_root_lifecycle.available: true`, `runtime_root_lifecycle.root_count: 3`, and `operator_projection.runtime_root_lifecycle_projection_visible: true`. Older workflow receipts remain readable but report `runtime_root_lifecycle.available: false`.

The Candidate B default operational acceptance checkpoint is:

```yaml
milestone: candidate_b_default_operational_acceptance_v1
checkpoint_base_main: 561b6e40c7559c1c88c9fb6a5932c605537e0a29
document_processing_engine_default_for_eligible_pdf: candidate_b_opendataloader_pdf
non_pdf_document_processing_engine_default: baseline
baseline_rollback_selector: baseline
candidate_a_visual_lane_mode: candidate_a_page_evidence_v1
candidate_b_visual_lane_mode: candidate_b_opendataloader_page_evidence_v1
candidate_b_visual_lane_default_enabled: false
selector_mutation_performed: false
runtime_root_lifecycle_projection_visible: true
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
```

This acceptance does not create new corpus artifacts or promote any broader source family. It accepts the current eligible-PDF default selector only when the full-corpus operator workflow, runtime-root lifecycle receipt, Layer 3 bridge receipt, downstream proof, redacted operator status, explicit baseline rollback, and Candidate A visual-lane preservation remain intact.

The operator workflow receipt/status path also projects an explicit eligibility and rollback summary:

```yaml
milestone: candidate_b_operator_status_eligibility_v1
eligibility_summary_projection_visible: true
baseline_rollback_projection_visible: true
eligible_pdf_count_source: candidate_b_target_status_counts.recommended
skipped_pdf_count_required: 0
failed_pdf_count_required: 0
baseline_rollback_selector: baseline
rollback_depends_on_candidate_b_artifacts: false
candidate_a_visual_lane_preserved: true
selector_mutation_performed: false
```

The status endpoint fails closed if the selected workflow receipt reports incomplete Candidate B eligibility counts, skipped/failed eligible PDFs, a stale eligibility summary, or rollback evidence that depends on Candidate B artifacts.

After the eligibility/status surface landed, the current-main operator execution checkpoint is:

```yaml
milestone: candidate_b_full_corpus_current_main_operator_execution_v1
current_main: 4659f3362f5d441f8501cb4cb5cd180eb8835ef5
workflow_receipt_id: cb-full-corpus-operator-9dbd003b8177fe6c8025cec5
workflow_receipt_hash: 9dbd003b8177fe6c8025cec5035e68ac41e7f962447e2088eb102a64e737f5f2
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-31c7b242d398dbf536aefc88
downstream_proof_hash: 31c7b242d398dbf536aefc88ecb4d38cca073361166d6e5a981a9b70bd808906
status_endpoint_http_status: 200
status_endpoint_status: available
workflow_status: proven
coverage_count: 17
corpus_pdf_count: 69
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
source_directory_extra_material_file_count: 2
eligibility_summary_projection_visible: true
baseline_rollback_projection_visible: true
runtime_root_lifecycle_projection_visible: true
baseline_rollback_selector: baseline
rollback_depends_on_candidate_b_artifacts: false
candidate_a_visual_lane_preserved: true
selector_mutation_performed: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
next_exact_posture: candidate_b_operator_invocation_surface_gap_audit_v1
```

Each execution may produce a new downstream proof receipt and workflow receipt. Newer executions should preserve the same schema, workflow mode, validated triplet, bridge receipt binding, coverage count, and negative invariants even when per-run receipt ids change.

No corpus artifacts are seeded or generated by this operator runner. It validates the existing triplet, prepares the admitted Layer 3 bridge, drives the downstream path, writes a redacted durable receipt, and fails closed if a required runtime root, run id, bridge receipt, curated root, dependency, or API surface is missing.

The operator runner no longer reads the material snapshot through a test-session helper before package preparation. After Gate B, it calls the governed hybrid authority API:

```text
POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare
```

Current invocation-surface checkpoint:

```yaml
milestone: candidate_b_operator_hybrid_authority_api_invocation_v1
checkpoint_base_main: 0b599adc9c4784ff32b6840704e28b0013f028d6
governed_authority_api: /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare
direct_material_snapshot_query_removed: true
direct_text_index_service_call_removed: true
direct_vector_index_service_call_removed: true
client_layer3_session_factory_removed_from_runner_orchestration: true
workflow_receipt_id: cb-full-corpus-operator-95256b11fd16e84a43bb4b8b
workflow_receipt_hash: 95256b11fd16e84a43bb4b8b69dfb99b178d43e201251ae56dfb72e996592c2c
downstream_proof_id: cb-runtime-downstream-proof-4e4dfc87454f0acc66bc8111
downstream_proof_hash: 4e4dfc87454f0acc66bc81119780223701a5035377b17d30ae27aabf826a2677
status_endpoint_http_status: 200
status_endpoint_status: available
workflow_status: proven
coverage_count: 17
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
workflow_receipt_schema_unchanged: candidate_b.full_corpus_layer3_operator_workflow.v1
workflow_mode_unchanged: candidate_b_full_corpus_operator_workflow_v1
baseline_rollback_preserved: true
candidate_a_visual_lane_preserved: true
next_exact_posture: candidate_b_live_server_invocation_surface_gap_audit_v1
```

For a lower-level repeatability smoke against current main, run the focused test that exercises the same bridge and downstream surfaces without broadening runtime state:

```powershell
py -3.12 -m pytest .\backend\tests\test_layer3_candidate_b_runtime_bridge.py::test_candidate_b_full_corpus_runtime_bridge_uses_triplet_and_reaches_gate_b -q
```

Stop and report the exact missing runtime root, run id, bridge receipt, curated root, dependency, or API failure if any required evidence is absent. Do not proceed from historical reports alone when the live artifact roots are missing.

## What The Tool Does
- Fails closed unless the corpus root, folder counts, PDF total, Phase 7A interpreter, `fitz`/`camelot`/`paddleocr`, Paddle model dirs, and Ghostscript all check out.
- In Candidate B mode, fails closed during preflight unless the active Phase 7A interpreter has importable `opendataloader-pdf==2.0.0`. This is checked before the proof submits a run so package drift does not appear later as a missing extraction artifact.
- Assumes that `.venvs\phase7a-py311` is aligned with [backend/requirements.txt](C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\requirements.txt). If that interpreter drifts, real app import surfaces like FastAPI form handling or analysis-module imports will fail before the NRC proof can start.
- Creates a fresh isolated runtime under `backend/app/storage_test_runtime/lc_e2e/...` with its own SQLite DB and `STORAGE_DIR`.
- Raises `CONNECTOR_LEASE_TTL_SECONDS` to `1800` inside that isolated runtime so the largest local-corpus OCR/table targets do not self-expire the connector lease mid-proof.
- Boots the live FastAPI app in-process with `TestClient`.
- Monkeypatches the NRC ADAMS client only inside the proof process so the live `/runs` path pages across the local corpus instead of the external API.
- Submits one strict NRC APS run using the selected document-processing engine, waits for completion, runs search smoke, persists the downstream chain through deterministic challenge review packet, then executes the validate-only gates against the isolated runtime.
- Writes `local_corpus_e2e_summary.json` into the runtime root, records `document_processing_engine`, and leaves the runtime intact on both pass and fail.

## Success Criteria
- 69 PDFs discovered, selected, and downloaded.
- Zero failed targets.
- Persisted downstream chain reaches deterministic challenge review packet.
- Baseline mode observes at least one persisted OCR-derived file and at least one persisted table-bearing file from the generated artifacts.
- Candidate B mode observes Candidate B / OpenDataLoader PDF extraction for every persisted target and non-empty ordered-unit evidence across the run. Candidate B is not treated as an OCR-owner-path equivalent.
- All validate-only gates pass against the isolated runtime.
- Candidate B full-corpus Layer 3 bridge emits a 71-file curated material root for the validated 69-target triplet without widening source-directory policy.
- Candidate B full-corpus downstream proof reaches analysis, package/review, handoff/export, same-origin delivery, provider-private redacted lifecycle, internal webhook status, visual-lane status, and runtime downstream proof with all required coverage steps.

## Focused Test Runner Note
The Candidate B runtime tests exercise the same package pin as the proof runner. If `python -m pytest ...` is executed with a global interpreter that has another `opendataloader-pdf` version, those tests should fail; that is environment drift, not proof that the repo widened the Candidate B contract.

When the Phase 7A interpreter has the pinned package but not `pytest`, run focused Candidate B runtime tests with the normal test runner and prepend the Phase 7A package path explicitly for that command only:

```powershell
$env:PYTHONPATH = "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\phase7a-py311\Lib\site-packages"
python -m pytest .\tests\test_api.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_document_processing.py .\backend\tests\test_review_nrc_aps_page.py .\backend\tests\test_review_nrc_aps_document_trace_page.py -q
```

For git worktrees under `worktrees\...`, use the checkout-relative Phase 7A package path that resolves back to the focused workspace root, for example `..\..\.venvs\phase7a-py311\Lib\site-packages`.

## Non-Goals
- No `project6.ps1` wrapper is added here. That script is still bound to `py -3.12`, while this proof must run in `.venvs/phase7a-py311`.
- No local-corpus submit API/schema/DB contract changes are required by this proof tool; the Candidate B live-server checkpoint below adds a bounded Layer 3 bridge source-scan API.
- No rendered run-submission UI is added here.
- No mutation of `tests/reports/*.json`, `backend/method_aware.db`, `backend/app/storage`, or the historical `run_20260314_010136` evidence package.

## Notes
- The proof intentionally maps `technical_specification_amendment_documents_for_testing` to `Technical Specification Amendment` so the live advanced-table routing path is exercised. The current `document_types.json` vocabulary still uses `Technical Specification, Amendment`; the summary records that mismatch as observed tech debt instead of changing repo contracts here.
- The live submit route assigns `connector_run_id` server-side, so the tool uses a runtime-stamp-derived `Idempotency-Key`. It does not modify the API just to force a caller-chosen run ID.
- The lease TTL override is proof-local only. It is applied through the isolated runtime environment, not by changing shared repo defaults or the `project6.ps1` operator surface.

## Candidate B Live-Server Bridge Source Scan Checkpoint

Current milestone:

```yaml
milestone: candidate_b_live_server_bridge_source_scan_v1
governed_source_scan_api: /api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge/source-scan
source_scan_mode: candidate_b_runtime_bridge_curated_source_scan_v1
operator_decision: scan_candidate_b_runtime_bridge_curated_material_root
bridge_receipt_authority_required: true
settings_layer3_source_ingestion_dir_mutation_removed: true
material_preview_resolves_persisted_batch_root_ref: true
text_index_resolves_persisted_batch_root_ref: true
workflow_receipt_id: cb-full-corpus-operator-2408b420e3634bb6af6dffdd
workflow_receipt_hash: 2408b420e3634bb6af6dffddde6ef5346b40a3f73500797037cff193125d660e
workflow_status_hash: a82d24c258958bb711d2c5a068cdff2f9ea72957ad7160711ddc8266f424011e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
downstream_proof_id: cb-runtime-downstream-proof-ba446008ff89a03057a122c3
downstream_proof_hash: ba446008ff89a03057a122c38a5cf51eb6bb941f2d1522bc270e848a0274a352
status_endpoint_status: available
workflow_status: proven
coverage_count: 17
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
source_root_ref: candidate-b-runtime-bridge://cb-runtime-l3-0110fe894c68d6a0291f9979/curated
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
next_exact_posture: candidate_b_live_server_operator_workflow_run_api_or_http_client_decision_v1
```

The operator runner now continues from the Candidate B runtime material bridge by calling the Candidate B bridge source-scan API. It no longer sets `LAYER3_SOURCE_INGESTION_DIR` or mutates `settings.layer3_source_ingestion_dir` to the bridge-curated root. The server records the persisted batch root as a redacted bridge ref and material preview/text indexing resolve that batch-bound root ref for downstream Layer 3 proof.

## Candidate B Live HTTP Operator Runner

```yaml
milestone: candidate_b_live_http_operator_runner_v1
selected_path: live_http_operator_runner
deferred_path: server_side_operator_workflow_run_api
execution_mode: live-http
api_base_url_required: true
readiness_gate_required: true
candidate_b_runtime_material_bridge_admitted_required: true
candidate_b_runtime_bridge_source_scan_admitted_required: true
candidate_b_runtime_downstream_proof_admitted_required: true
candidate_b_full_corpus_operator_workflow_status_admitted_required: true
internal_webhook_mode_required: configured
local_ack_webhook_transport_allowed_in_live_http: false
testclient_dependency_used_in_live_http: false
in_memory_db_used_in_live_http: false
status_endpoint_verification_required: true
operator_workflow_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
local_testclient_regression_receipt_id: cb-full-corpus-operator-40cd13edeb4d8c10bd65e727
local_testclient_regression_receipt_hash: 40cd13edeb4d8c10bd65e727a1a8bd7c810c9809274d9f1db73a250fcc736c51
local_testclient_regression_status_hash: f126d919e9e9ce2a2766ac1a862a0e97a384edf0f685cdde8aadb4ad3dbea904
live_http_runtime_proof_status: proven
live_http_runtime_proof_checkpoint: next_milestone_plans/Layer3_planning_docs/986-cb-live-http-runtime-proof.md
live_http_runtime_proof_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
live_http_runtime_proof_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
next_exact_posture: candidate_b_operator_repeatability_acceptance_and_ui_status_decision_v1
```

The operator runner now supports a live HTTP execution mode:

```powershell
python .\tools\run_candidate_b_full_corpus_operator_workflow.py `
  --execution-mode live-http `
  --api-base-url http://127.0.0.1:8000/api/v1/layer3 `
  --internal-webhook-mode configured `
  --baseline-run-root <baseline-run-root> `
  --candidate-a-run-root <candidate-a-run-root> `
  --candidate-b-run-root <candidate-b-run-root> `
  --receipt-dir <server-shared-operator-workflow-receipt-dir>
```

The live server must already be configured with a durable database, a runtime-discovery `STORAGE_DIR` containing the selected full-corpus baseline/Candidate A/Candidate B runtime roots, a server-owned `LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR`, the same `LAYER3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR` used by `--receipt-dir`, and `LAYER3_INTERNAL_WEBHOOK_URL`. The runner fails closed if the live readiness endpoint does not admit the required Candidate B bridge/source-scan/downstream-proof/status endpoints or if the workflow status endpoint cannot inspect the final durable receipt.

## Candidate B Live HTTP Runtime Proof

```yaml
milestone: candidate_b_live_http_operator_workflow_runtime_proof_v1
current_main: ebc8f46cd4ec48f2e97b6de10bfd5ff6cbe07d71
execution_mode: live-http
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
configured_internal_webhook_used: true
status_endpoint_verified: true
status_endpoint_status: available
workflow_status: proven
workflow_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
workflow_receipt_hash: 3d717f0edcbeaba69179af1582a90abf2ce087c5d35400afdb62fe7534b3266c
workflow_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-ee7d48afbe62ffc011fac4d3
downstream_proof_hash: ee7d48afbe62ffc011fac4d3ae8796f9b5bdaa42c5db91d3ac0f5d527d8b8481
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
artifact_family_hash: bc32ee4f789f078b9f1d1e46dd9402df5b92aeb4afbde369fbd00553e6a61380
coverage_count: 17
corpus_pdf_count: 69
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
curated_file_count: 71
text_file_count: 69
visual_page_evidence_count: 1805
product_inspection_artifact_count: 1873
delivery_artifact_count: 1873
provenance_audit_artifact_count: 2542
material_analysis_payload_count: 71
baseline_rollback_available: true
candidate_a_visual_lane_preserved: true
selector_mutation_performed: false
source_directory_scan_status: available
qualitative_analysis_status: available
external_export_download_status: prepared
same_origin_delivery_available: true
provider_private_state: provider_private_signed_url_prepared
provider_private_revoke_state: provider_private_signed_url_revoked
internal_webhook_state: source_directory_internal_webhook_dispatched
visual_lane_status: available
downstream_proof_status: proven
api_base_url_ref: redacted://url/0eed07a75735dce278294964
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
baseline_default_changed: false
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
artifacts_seeded_or_generated_by_triplet_validator: false
validate_only_triplet: true
next_exact_posture: candidate_b_operator_repeatability_acceptance_and_ui_status_decision_v1
```

This live proof used the governed `live-http` runner against a configured FastAPI server, not `TestClient`, dependency overrides, or an in-memory database. The status endpoint re-read the durable workflow receipt and projected workflow, bridge, downstream proof, artifact-family, eligibility, rollback, and runtime-root lifecycle status without raw path, raw URL, or artifact-byte exposure.

## Candidate B Operator Repeatability Acceptance

```yaml
milestone: candidate_b_operator_repeatability_acceptance_and_ui_status_decision_v1
current_main: 8b70d2f83bfc9540b9491e34c93c7fc73f650d1d
acceptance_basis_checkpoint: next_milestone_plans/Layer3_planning_docs/986-cb-live-http-runtime-proof.md
accepted_operator_execution_surface: live_http_operator_runner_plus_status_endpoint
accepted_for_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
server_side_operator_workflow_run_api_admitted_now: false
rendered_run_start_control_admitted_now: false
rendered_read_only_status_projection_admitted_now: false
next_rendered_status_step: candidate_b_read_only_operator_status_rendered_projection_gap_audit_v1
workflow_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
workflow_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
downstream_proof_id: cb-runtime-downstream-proof-ee7d48afbe62ffc011fac4d3
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
configured_internal_webhook_used: true
status_endpoint_verified: true
status_endpoint_status: available
workflow_status: proven
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
coverage_count: 17
baseline_rollback_available: true
baseline_default_changed: false
candidate_a_visual_lane_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_performed: false
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
validate_only_triplet: true
artifacts_seeded_or_generated_by_triplet_validator: false
next_exact_posture: candidate_b_read_only_operator_status_rendered_projection_gap_audit_v1
```

This acceptance treats the live HTTP runner plus full-corpus operator workflow status endpoint as the current repeatable operator surface for prepared eligible-PDF corpus runs on a configured live server. It does not admit a server-side workflow-run API, rendered run-start control, browser-storage authority, broader Candidate B default scope, or new provider/connector/model behavior. Any next UI step should be a read-only rendered status projection gap audit before implementation.

## Candidate B Rendered Operator Workflow Status Proof

```yaml
milestone: candidate_b_read_only_operator_status_rendered_projection_gap_audit_v1
current_main: 9906745bdc5ff4b94146860588159481f1b8642c
selected_gap: rendered_full_corpus_operator_workflow_status_read_only_projection
selected_path: prove_existing_rendered_status_control
new_runtime_api_admitted: false
server_side_operator_workflow_run_api_admitted_now: false
rendered_run_start_control_admitted_now: false
rendered_status_control_id: candidate-b-full-corpus-workflow-status-form
rendered_status_mode: rendered_candidate_b_full_corpus_operator_workflow_status_control
status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
status_mode: candidate_b_full_corpus_operator_workflow_status_v1
operator_decision: inspect_candidate_b_full_corpus_operator_workflow_status
frontend_durable_authority_enabled: false
submitted_authority_fields_only: true
payload_raw_url_field_submitted: false
payload_local_path_field_submitted: false
payload_selector_mutation_field_submitted: false
rendered_workflow_status_visible: true
rendered_bridge_receipt_visible: true
rendered_downstream_proof_visible: true
rendered_artifact_family_projection_visible: true
rendered_visual_page_evidence_count_visible: true
rendered_raw_local_path_guardrail_visible: true
focused_e2e_test: e2e/layer3-workbench.spec.js::Layer 3 workbench inspects Candidate B full-corpus workflow status through rendered read-only control
next_exact_posture: candidate_b_operator_repeatability_completion_audit_v1
```

The rendered proof covers the existing read-only workbench status control. It does not add run-start authority or any new runtime route; it only proves the browser can inspect the server-revalidated workflow status projection from durable receipt authority.

## Candidate B Operator Repeatability Completion Audit

```yaml
milestone: candidate_b_operator_repeatability_completion_audit_v1
current_main: bf1a991740a76ef84fe64af5d5be6fea0833e80f
completion_status: complete_for_current_admitted_scope
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
operator_surface: live_http_operator_runner_plus_status_endpoint_plus_rendered_read_only_status_control
accepted_execution_surface_checkpoint: next_milestone_plans/Layer3_planning_docs/987-cb-repeatability-acceptance.md
live_http_runtime_proof_checkpoint: next_milestone_plans/Layer3_planning_docs/986-cb-live-http-runtime-proof.md
rendered_status_proof_checkpoint: next_milestone_plans/Layer3_planning_docs/988-cb-rendered-status-proof.md
workflow_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
workflow_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
downstream_proof_id: cb-runtime-downstream-proof-ee7d48afbe62ffc011fac4d3
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
configured_internal_webhook_used: true
status_endpoint_verified: true
rendered_read_only_status_control_proven: true
headed_chrome_rendered_status_proof_passed: true
headless_chromium_rendered_status_proof_passed: true
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
coverage_count: 17
artifact_family_inspection_available: true
visual_page_evidence_count: 1805
baseline_rollback_available: true
baseline_default_changed: false
candidate_a_visual_lane_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_performed: false
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
server_side_operator_workflow_run_api_admitted_now: false
rendered_run_start_control_admitted_now: false
validate_only_triplet: true
artifacts_seeded_or_generated_by_triplet_validator: false
next_exact_posture: candidate_b_post_repeatability_operator_workflow_expansion_selection_v1
```

This completion audit closes the current Candidate B operator-repeatability goal for the accepted scope: prepared full-corpus eligible-PDF runs on a configured live server. The next useful action is a new post-repeatability product selection, not another proof variant, unless a concrete defect appears.

## Candidate B Server-Owned Workflow Run API Freeze

```yaml
milestone: candidate_b_server_owned_workflow_run_api_authority_freeze_v1
current_main: c6c0c481794098b984792bbc49ae84a63a9b2a4e
source_posture_checkpoint: next_milestone_plans/Layer3_planning_docs/989-cb-repeatability-completion-audit.md
selected_next_slice: candidate_b_server_owned_workflow_run_api_authority_v1
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_runtime_target: candidate_b_server_owned_workflow_run_api_runtime_v1
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
source_authority_model: server_owned_runtime_root_lifecycle_receipt_plus_compare_target_set
client_supplied_raw_runtime_roots_admitted: false
browser_supplied_runtime_roots_admitted: false
server_resolves_runtime_roots_from_receipt_authority: true
workflow_receipt_binding_required: true
runtime_root_lifecycle_receipt_required: true
idempotency_key_required: true
state_machine_required: true
required_states: accepted,running,proven,blocked,cancelled,expired
rendered_run_start_control_admitted_now: false
rendered_progress_control_admitted_now: false
rendered_status_control_remains_read_only: true
baseline_rollback_required: true
baseline_default_changed: false
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_allowed: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
next_exact_posture: candidate_b_server_owned_workflow_run_api_runtime_v1
```

This freeze selects server-owned workflow-run authority as the next exact post-repeatability slice. It does not implement the runtime endpoint yet and does not admit rendered start/progress controls until server authority lands.

## Candidate B Server-Owned Workflow Run API Runtime

```yaml
milestone: candidate_b_server_owned_workflow_run_api_runtime_v1
source_authority_freeze: next_milestone_plans/Layer3_planning_docs/990-cb-server-run-api-freeze.md
runtime_status: implemented
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
run_schema_id: layer3.candidate_b_full_corpus_operator_workflow_run.v1
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
source_authority_model: server_owned_runtime_root_lifecycle_receipt_plus_compare_target_set
server_resolves_source_workflow_receipt_from_configured_receipt_dir: true
workflow_receipt_binding_required: true
runtime_root_lifecycle_receipt_required: true
baseline_run_id_required: true
candidate_a_run_id_required: true
candidate_b_run_id_required: true
compare_target_set_hash_required: true
idempotency_key_required: true
idempotency_basis: client_request_id_plus_authority_basis_hash
state_machine: accepted,running,proven,blocked,cancelled,expired
durable_run_receipt_written: true
status_endpoint_compatibility: proven
status_endpoint_request_returned: true
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_allowed: false
client_supplied_raw_runtime_roots_admitted: false
browser_supplied_runtime_roots_admitted: false
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
rendered_run_start_control_admitted: false
rendered_progress_control_admitted: false
verification: python -m pytest .\backend\tests\test_layer3_candidate_b_full_corpus_operator_workflow_run.py .\backend\tests\test_layer3_candidate_b_full_corpus_operator_workflow_status.py .\backend\tests\test_layer3_readiness_contract.py .\backend\tests\test_layer3_bootstrap_contract.py -q
verification_result: 14 passed
next_exact_posture: candidate_b_server_owned_workflow_run_api_live_http_proof_v1
```

The run endpoint starts from existing configured server receipt authority. Operators provide only server authority identifiers and intent; the browser does not submit local runtime roots, raw URLs, selector changes, provider refs, connector destinations, or model/runtime controls. The server resolves the matching proven workflow receipt, revalidates runtime-root lifecycle and compare-target authority, writes an idempotent durable run receipt, and returns a status request that the existing read-only status endpoint can inspect.

## Candidate B Server-Owned Workflow Run API Live HTTP Proof

```yaml
milestone: candidate_b_server_owned_workflow_run_api_live_http_proof_v1
source_runtime_checkpoint: next_milestone_plans/Layer3_planning_docs/991-cb-server-run-api-runtime.md
current_main_entry: 35b5613e3cfa7c5155ce2e25f097f298eae7b9df
execution_mode: live-http
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
server_run_endpoint_verification_required: true
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
run_schema_id: layer3.candidate_b_full_corpus_operator_workflow_run.v1
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
server_run_endpoint_verified: true
status_endpoint_verified_after_server_run: true
server_run_state: proven
workflow_status_after_server_run: proven
operator_workflow_receipt_id: cb-full-corpus-operator-run-a281171ae1718620ff0dfdb8
operator_workflow_receipt_hash: 2c365c456eea0300c60a4d99c8ff28b8c3b79413087d6df03ffe962d292a9d87
source_operator_workflow_receipt_id: cb-full-corpus-operator-2c365c456eea0300c60a4d99
source_operator_workflow_receipt_hash: 2c365c456eea0300c60a4d99c8ff28b8c3b79413087d6df03ffe962d292a9d87
authority_basis_hash: b10068440d99e496dbace35fd004eb3d7b0e6b46bc703b3f2bdd435e3cac98b9
idempotency_key_hash: a281171ae1718620ff0dfdb8625d1561aa034fe750b9e164037999114353de5b
workflow_status_hash_after_server_run: 0e6005881f8b10f454fb40a0b06c298a8f4922c9da5343c5e9b21e051a5c002f
source_workflow_status_hash: 96ff73f0aed18ff8f4e4b68809314b378b2ac0ed317a8a9b16bce9d50098f9fd
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-b63d0968304450c4031312ba
downstream_proof_hash: b63d0968304450c4031312baf7ed81fdf29502d12dbc1e6e3735d16a9f491e77
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
corpus_pdf_count: 69
eligible_pdf_count: 69
failed_pdf_count: 0
skipped_pdf_count: 0
curated_file_count: 71
governed_retained_artifact_family_hash: bc32ee4f789f078b9f1d1e46dd9402df5b92aeb4afbde369fbd00553e6a61380
live_http_runtime_dirs_isolated: true
bridge_dir_outside_storage_root_required: true
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
rendered_run_start_control_admitted: false
rendered_progress_control_admitted: false
verification_result: proven
next_exact_posture: candidate_b_rendered_operator_workflow_run_start_control_freeze_v1
```

The live proof used an isolated durable database and proof-local receipt directories so it did not depend on older seeded live state. The server-owned runtime bridge directory must remain outside the configured `STORAGE_DIR`; the live bridge guard fails closed when bridge output overlaps app-owned storage/export staging. The runner now verifies the server-owned run endpoint after the source workflow receipt is written, then uses the returned status request to inspect the durable run receipt through the existing read-only status endpoint.

## Candidate B Rendered Workflow Run Start Control Freeze

```yaml
milestone: candidate_b_rendered_operator_workflow_run_start_control_freeze_v1
source_live_http_proof: next_milestone_plans/Layer3_planning_docs/992-cb-server-run-live-http-proof.md
current_main_entry: 45c93d83bb9b99aad6c993bca36ba3241a618902
selected_next_slice: candidate_b_rendered_operator_workflow_run_start_control_authority_v1
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_runtime_target: candidate_b_rendered_operator_workflow_run_start_control_v1
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_rendered_start_mode: rendered_candidate_b_full_corpus_operator_workflow_run_start_control
selected_rendered_progress_mode: rendered_candidate_b_full_corpus_operator_workflow_run_progress_control
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
status_mode: candidate_b_full_corpus_operator_workflow_status_v1
status_operator_decision: inspect_candidate_b_full_corpus_operator_workflow_status
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
source_authority_model: server_owned_runtime_root_lifecycle_receipt_plus_compare_target_set
server_resolves_source_workflow_receipt_from_configured_receipt_dir: true
rendered_start_control_admitted_after_sync: true
rendered_progress_control_admitted_after_sync: true
rendered_status_control_already_admitted: true
status_endpoint_reused_after_run: true
run_endpoint_status_request_must_be_used: true
allowed_browser_supplied_run_fields: client_request_id,run_mode,operator_decision,runtime_root_lifecycle_receipt_id,baseline_run_id,candidate_a_run_id,candidate_b_run_id,compare_target_set_hash,material_relative_name
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_allowed: false
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
queue_scheduler_runtime_admitted: false
cancel_runtime_admitted: false
arbitrary_corpus_processing_start_admitted: false
proof_required_headless_chrome: true
proof_required_headed_chrome: true
next_exact_posture: candidate_b_rendered_operator_workflow_run_start_control_v1
```

The next implementation may add a rendered start/progress control for the already-proven server-owned run endpoint. The browser may submit only bounded server authority identifiers and intent, then must use the returned `status_request` to inspect progress through the existing read-only status endpoint. It must not submit runtime roots, source directories, bridge directories, raw paths, raw URLs, provider refs, connector destinations, selector mutations, or frontend durable authority.

## Candidate B Rendered Workflow Run Start Control

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
selector_mutation_performed: false
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

The rendered control starts only a server-owned workflow run from already prepared Candidate B full-corpus server authority. It then follows the run endpoint's returned `status_request` into the existing read-only status endpoint. This does not add broad corpus processing start, browser-owned runtime roots, source-directory selection, queue scheduling beyond the existing contract-only response, cancel runtime, selector mutation, provider writes, connector dispatch, model runtime, or full mockup activation.

## Candidate B Rendered Workflow Run Live HTTP Proof

```yaml
milestone: candidate_b_rendered_operator_workflow_run_live_http_operator_proof_v1
source_rendered_control_checkpoint: next_milestone_plans/Layer3_planning_docs/994-cb-rendered-run-start-control.md
source_live_http_api_checkpoint: next_milestone_plans/Layer3_planning_docs/992-cb-server-run-live-http-proof.md
current_main_entry: 1a124dfcfd548181acb633a9cacadcc1446f3228
execution_mode: live-http-rendered-browser
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_required: true
playwright_browser_surface_used: true
selected_rendered_start_mode: rendered_candidate_b_full_corpus_operator_workflow_run_start_control
selected_rendered_progress_mode: rendered_candidate_b_full_corpus_operator_workflow_run_progress_control
run_endpoint_verified: true
status_endpoint_verified_after_rendered_run: true
run_endpoint_status_request_used_for_progress: true
rendered_payload_allowed_fields_only: true
forbidden_rendered_payload_fields_present: []
headless_chromium_proof_receipt_id: cb-rendered-run-live-http-3e92b0d89030d0d329b52c4c
headless_chromium_proof_hash: 3e92b0d89030d0d329b52c4cb6c77c3bc08adce41fd304676b76e0d02758791e
headed_chromium_proof_receipt_id: cb-rendered-run-live-http-62a856b709e3504edf1307a3
headed_chromium_proof_hash: 62a856b709e3504edf1307a33fc0275d5e8915dca7f0160563c5ec62d869869f
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
runtime_roots_submitted_by_browser: false
source_directory_submitted_by_browser: false
bridge_dir_submitted_by_browser: false
selector_mutation_performed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
verification_script_syntax: node --check .\tools\prove_candidate_b_rendered_workflow_run_live_http.js
verification_headless_rendered_live_http: passed
verification_headed_rendered_live_http: passed
next_exact_posture: candidate_b_operator_workflow_run_history_and_lifecycle_selection_v1
```

The live rendered proof runs the actual `/review/layer3` page against a configured FastAPI server. The proof helper fills only server authority identifiers from a prepared Candidate B full-corpus workflow receipt, submits the rendered start control, verifies the live run endpoint, and verifies the browser posts the run endpoint's returned `status_request` to the live status endpoint. It proves rendered operator start/progress behavior without TestClient, route stubs, in-memory database state, browser-owned runtime roots, raw path/URL submission, selector mutation, provider writes, connector dispatch, model runtime, or full mockup activation.

## Candidate B Workflow Run History and Lifecycle Selection

```yaml
milestone: candidate_b_operator_workflow_run_history_and_lifecycle_selection_v1
source_rendered_live_http_proof: next_milestone_plans/Layer3_planning_docs/995-cb-rendered-run-live-http-proof.md
current_main_entry: e35d04ce35e1db16c5a159cf42bf29359b9cce50
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_run_history_read_only_projection_v1
selected_history_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_history_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
selected_rendered_history_mode: rendered_candidate_b_full_corpus_operator_workflow_run_history_control
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
read_only_history_projection_admitted_after_sync: true
single_run_status_endpoint_reused_for_detail: true
history_rows_must_bind_authority_basis_hash: true
history_rows_must_bind_status_request: true
invalid_or_stale_receipts_fail_closed: true
missing_configured_receipt_root_fails_closed: true
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
cancel_runtime_admitted: false
retry_runtime_admitted: false
resume_runtime_admitted: false
queue_scheduler_runtime_admitted: false
expiry_mutation_runtime_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_operator_workflow_run_history_read_only_projection_v1
```

The selected next implementation is a read-only server-owned workflow-run history projection. It should list Candidate B full-corpus workflow-run receipts from configured server receipt authority, expose only redacted operator-safe run metadata, and let the operator inspect a selected run through the existing status endpoint's server-provided request. It does not admit lifecycle mutation, queue scheduling, cancel/retry/resume/expiry runtime, broader Candidate B default scope, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, browser storage authority, or frontend durable authority.

## Candidate B Workflow Run History Read-Only Projection

```yaml
milestone: candidate_b_operator_workflow_run_history_read_only_projection_v1
source_selection: next_milestone_plans/Layer3_planning_docs/996-cb-workflow-run-history-selection.md
current_main_entry: dbadb7a35f61fffbb3ddf85118c0e00e06599b8f
runtime_status: implemented
selected_history_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_history_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
selected_rendered_history_mode: rendered_candidate_b_full_corpus_operator_workflow_run_history_control
history_schema_id: layer3.candidate_b_full_corpus_operator_workflow_history.v1
history_mode: candidate_b_full_corpus_operator_workflow_history_v1
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
configured_receipt_authority_used: true
read_only_history_projection: true
single_run_status_endpoint_reused_for_detail: true
history_rows_bind_authority_basis_hash: true
history_rows_bind_status_request: true
invalid_or_stale_receipts_fail_closed: true
missing_configured_receipt_root_fails_closed: true
non_run_receipts_fail_closed: true
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
cancel_runtime_admitted: false
retry_runtime_admitted: false
resume_runtime_admitted: false
queue_scheduler_runtime_admitted: false
expiry_mutation_runtime_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
verification_node_check: passed
verification_backend_py_compile: passed
verification_backend_pytest: 10 passed
verification_headless_rendered_e2e: passed
verification_headed_rendered_e2e: passed
next_exact_posture: candidate_b_operator_workflow_lifecycle_mutation_selection_v1
```

Operators can refresh the rendered history surface to list server-owned Candidate B workflow-run receipts from configured receipt authority. Selecting a row sends only the row's returned `status_request` to the existing full-corpus workflow status endpoint, so detail inspection remains server-authoritative and read-only.

The projection is not a lifecycle-mutation surface. Cancel, retry, resume, expiry enforcement, queue scheduling, broader default scope, provider writes, connector dispatch, RAG/vector/model runtime, and full mockup activation remain separate selections.

## Candidate B Workflow Run Lifecycle Mutation Selection

```yaml
milestone: candidate_b_operator_workflow_lifecycle_mutation_selection_v1
source_history_projection: next_milestone_plans/Layer3_planning_docs/997-cb-workflow-run-history-projection.md
current_main_entry: 0b48b12da7d48f8faefdb46d93d955130041ab13
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_run_expiry_closeout_receipt_v1
selected_lifecycle_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_lifecycle_action: expire_or_close_server_owned_workflow_run_receipt
selected_lifecycle_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
existing_history_endpoint_reused_for_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_lifecycle_receipt_model: append_only_lifecycle_receipt_without_mutating_source_run_receipt
selected_lifecycle_receipt_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,row_hash,authority_basis_hash,history_hash
selected_idempotency_basis: client_request_id_plus_lifecycle_authority_hash
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_run_receipt_rejected: true
source_run_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
queue_scheduler_runtime_selected_now: false
expiry_closeout_runtime_selected_after_sync: true
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_operator_workflow_run_expiry_closeout_receipt_v1
```

The next selected lifecycle runtime is an append-only expiry/closeout receipt over an existing server-owned Candidate B full-corpus workflow-run receipt. It must revalidate run receipt authority, history row binding, source receipt authority, and idempotency before writing a lifecycle receipt, and it must not mutate the original run receipt.

Cancel, retry, resume, and queue scheduling remain intentionally unselected until async scheduler/runtime authority is separately frozen.

## Candidate B Workflow Run Expiry/Closeout Receipt

```yaml
milestone: candidate_b_operator_workflow_run_expiry_closeout_receipt_v1
source_lifecycle_selection: next_milestone_plans/Layer3_planning_docs/998-cb-workflow-lifecycle-selection.md
runtime_status: implemented
selected_lifecycle_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_lifecycle_mode: candidate_b_operator_workflow_run_expiry_closeout_receipt_v1
selected_lifecycle_action: expire_or_close_server_owned_workflow_run_receipt
selected_lifecycle_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
existing_history_endpoint_reused_for_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_rendered_lifecycle_mode: rendered_candidate_b_full_corpus_operator_workflow_lifecycle_expire_control
selected_lifecycle_receipt_model: append_only_lifecycle_receipt_without_mutating_source_run_receipt
selected_lifecycle_receipt_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,row_hash,authority_basis_hash,history_hash
selected_idempotency_basis: client_request_id_plus_lifecycle_authority_hash
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_run_receipt_rejected: true
source_run_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
queue_scheduler_runtime_selected_now: false
expiry_closeout_runtime_selected: true
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
next_exact_posture: candidate_b_async_cancel_retry_queue_authority_selection_v1
```

Operators close out a Candidate B workflow run by refreshing server-owned history, choosing a run row, and submitting only the current row/hash authority to the lifecycle endpoint. The endpoint writes a separate lifecycle receipt and leaves the original workflow-run receipt unchanged so detail inspection still uses the returned status request.

This lifecycle pass does not add cancel, retry, resume, async queue scheduling, broader Candidate B default scope, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, browser storage authority, or frontend durable authority.

## Candidate B Async Cancel/Retry/Queue Authority Selection

```yaml
milestone: candidate_b_async_cancel_retry_queue_authority_selection_v1
source_expiry_closeout_runtime: next_milestone_plans/Layer3_planning_docs/999-cb-workflow-expiry-closeout-runtime.md
current_main_entry: 8320d8e480ea368fed1504ed985061910936dc11
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_workflow_queue_state_authority_v1
selected_next_runtime_scope: server_owned_candidate_b_full_corpus_operator_workflow_queue_state_receipts
selected_first_runtime_reason: cancel_retry_resume_require_server_owned_queue_attempt_and_checkpoint_authority
selected_queue_state_mode: append_only_queue_state_receipt_without_background_scheduler
selected_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_run_start_endpoint_reused_for_current_sync_start: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_history_endpoint_reused_for_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_expiry_closeout_endpoint_remains_only_lifecycle_mutation: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_queue_state_receipt_model: append_only_queue_state_receipt_without_mutating_source_run_receipt
selected_queue_state_receipt_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,authority_basis_hash,history_hash,queue_state_hash
selected_queue_state_idempotency_basis: client_request_id_plus_queue_state_authority_hash
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_run_receipt_must_reject: true
source_run_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
queue_state_authority_runtime_selected_after_sync: true
queue_scheduler_runtime_selected_now: false
background_worker_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_workflow_queue_state_authority_v1
```

The next runtime-bearing Candidate B workflow slice should be server-owned queue-state receipt authority, not cancel, retry, resume, or a background scheduler. Cancellation needs an in-flight job/lease target, retry needs attempt/failure authority, and resume needs checkpoint authority; current main does not provide those yet.

The queue-state runtime must remain append-only and server-authoritative. It should bind to the existing run receipt, history row, authority basis, and queue-state hash, reject stale or missing authority, expose no raw paths or URLs, and preserve the existing run, status, history, and expiry-closeout surfaces.

## Candidate B Async Queue-State Runtime

```yaml
milestone: candidate_b_async_workflow_queue_state_authority_v1
source_async_selection: next_milestone_plans/Layer3_planning_docs/1000-cb-async-cancel-retry-queue-selection.md
runtime_status: implemented
selected_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
selected_queue_state_mode: append_only_queue_state_receipt_without_background_scheduler
selected_queue_state_action: record_candidate_b_async_workflow_queue_state
selected_queue_state_scope: server_owned_candidate_b_full_corpus_operator_workflow_queue_state_receipts
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
existing_run_start_endpoint_reused_for_current_sync_start: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_history_endpoint_reused_for_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_expiry_closeout_endpoint_remains_only_lifecycle_mutation: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_rendered_queue_state_mode: rendered_candidate_b_full_corpus_operator_workflow_queue_state_control
selected_queue_state_receipt_model: append_only_queue_state_receipt_without_mutating_source_run_receipt
selected_queue_state_receipt_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,row_hash,authority_basis_hash,history_hash,queue_state_hash
selected_queue_state_idempotency_basis: client_request_id_plus_queue_state_authority_hash
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_run_receipt_rejected: true
source_run_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
queue_state_authority_runtime_selected: true
queue_scheduler_runtime_selected_now: false
background_worker_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_scope: backend_service_api_readiness_rendered_operator_control_focused_tests
next_exact_posture: candidate_b_async_queue_scheduler_authority_selection_v1
```

Operators can refresh workflow-run history and record queue-state authority for a selected row. The server writes a separate append-only queue-state receipt and leaves the original workflow-run receipt unchanged. Queue scheduling, background workers, cancel, retry, resume, and expiry enforcement remain unselected.

## Candidate B Async Queue Scheduler Authority Selection

```yaml
milestone: candidate_b_async_queue_scheduler_authority_selection_v1
source_queue_state_runtime: next_milestone_plans/Layer3_planning_docs/1001-cb-async-queue-state-runtime.md
current_main_entry: ead28c301404b7a3128b4a8234177efd29d44164
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_scheduler_lease_receipt_v1
selected_scheduler_scope: server_owned_candidate_b_full_corpus_operator_workflow_queue_state_receipts
selected_scheduler_mode: append_only_scheduler_lease_receipt_without_background_worker
selected_scheduler_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_source_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_expiry_closeout_endpoint_remains_only_lifecycle_mutation: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_scheduler_receipt_model: append_only_scheduler_lease_receipt_without_mutating_queue_state_or_source_run_receipt
selected_scheduler_receipt_binding: queue_state_receipt_id,queue_state_receipt_hash,queue_state_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,scheduler_lease_hash
selected_scheduler_idempotency_basis: client_request_id_plus_scheduler_lease_authority_hash
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_queue_state_receipt_must_reject: true
source_run_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
scheduler_lease_runtime_selected_after_sync: true
background_worker_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_scheduler_lease_receipt_v1
```

The selected next scheduler runtime should create a server-owned append-only lease receipt over an existing queue-state receipt. It must not start a worker, run the job, cancel, retry, resume, enforce expiry, mutate the queue-state receipt, mutate the source run receipt, broaden Candidate B default scope, or expose raw paths/URLs.

## Candidate B Async Scheduler Lease Runtime

```yaml
milestone: candidate_b_async_scheduler_lease_receipt_v1
source_scheduler_selection: next_milestone_plans/Layer3_planning_docs/1002-cb-async-scheduler-selection.md
runtime_status: implemented
selected_scheduler_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
selected_scheduler_mode: append_only_scheduler_lease_receipt_without_background_worker
selected_scheduler_action: record_candidate_b_async_scheduler_lease
selected_scheduler_scope: server_owned_candidate_b_full_corpus_operator_workflow_queue_state_receipts
selected_scheduler_receipt_model: append_only_scheduler_lease_receipt_without_mutating_queue_state_or_source_run_receipt
selected_scheduler_receipt_binding: queue_state_receipt_id,queue_state_receipt_hash,queue_state_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,scheduler_lease_hash
selected_scheduler_idempotency_basis: client_request_id_plus_scheduler_lease_authority_hash
exclusive_queue_state_lease: true
stale_queue_state_receipt_rejected: true
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_queue_state_receipt_rejected: true
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
scheduler_lease_runtime_selected: true
background_worker_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
next_exact_posture: candidate_b_async_worker_attempt_authority_selection_v1
```

Operators can record exactly one server-owned scheduler lease for an existing queue-state receipt. Replaying the same client request returns the same receipt; a competing request for the same queue-state authority fails closed. The runtime still does not start a worker, execute the job, cancel, retry, resume, enforce lease expiry, mutate queue-state/source-run receipts, broaden Candidate B scope, or expose raw paths/URLs.

## Candidate B Async Worker Attempt Authority Selection

```yaml
milestone: candidate_b_async_worker_attempt_authority_selection_v1
source_scheduler_lease_runtime: next_milestone_plans/Layer3_planning_docs/1003-cb-async-scheduler-lease-runtime.md
current_main_entry: 1330270116a637eed6aa45a740146d53b838add0
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_worker_attempt_receipt_v1
selected_worker_attempt_scope: server_owned_candidate_b_full_corpus_operator_workflow_scheduler_lease_receipts
selected_worker_attempt_mode: append_only_worker_attempt_receipt_without_job_execution
selected_worker_attempt_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_source_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_worker_attempt_receipt_model: append_only_worker_attempt_receipt_without_mutating_scheduler_lease_queue_state_or_source_run_receipt
selected_worker_attempt_receipt_binding: scheduler_lease_receipt_id,scheduler_lease_receipt_hash,scheduler_lease_authority_hash,queue_state_receipt_id,queue_state_receipt_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,worker_attempt_hash
selected_worker_attempt_idempotency_basis: client_request_id_plus_worker_attempt_authority_hash
selected_initial_attempt_number: 1
exclusive_initial_attempt_per_scheduler_lease: true
stale_scheduler_lease_receipt_must_reject: true
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_scheduler_lease_receipt_must_reject: true
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
worker_attempt_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
progress_checkpoint_runtime_selected_now: false
completion_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_worker_attempt_receipt_v1
```

The selected next runtime should create a server-owned append-only initial worker-attempt receipt over an existing scheduler lease receipt. It must not start a process, execute the job, emit progress, complete, cancel, retry, resume, enforce expiry, mutate scheduler-lease/queue-state/source-run receipts, broaden Candidate B scope, or expose raw paths/URLs.

## Candidate B Async Worker Attempt Runtime

```yaml
milestone: candidate_b_async_worker_attempt_receipt_v1
source_worker_attempt_selection: next_milestone_plans/Layer3_planning_docs/1004-cb-async-worker-attempt-selection.md
runtime_status: implemented
selected_worker_attempt_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
selected_worker_attempt_mode: append_only_worker_attempt_receipt_without_job_execution
selected_worker_attempt_action: record_candidate_b_async_worker_attempt
selected_worker_attempt_scope: server_owned_candidate_b_full_corpus_operator_workflow_scheduler_lease_receipts
selected_worker_attempt_receipt_model: append_only_worker_attempt_receipt_without_mutating_scheduler_lease_queue_state_or_source_run_receipt
selected_worker_attempt_receipt_binding: scheduler_lease_receipt_id,scheduler_lease_receipt_hash,scheduler_lease_authority_hash,queue_state_receipt_id,queue_state_receipt_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,worker_attempt_hash
selected_worker_attempt_idempotency_basis: client_request_id_plus_worker_attempt_authority_hash
selected_initial_attempt_number: 1
exclusive_initial_attempt_per_scheduler_lease: true
stale_scheduler_lease_receipt_rejected: true
stale_queue_state_receipt_rejected: true
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_scheduler_lease_receipt_rejected: true
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
worker_attempt_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
progress_checkpoint_runtime_selected_now: false
completion_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
next_exact_posture: candidate_b_async_progress_checkpoint_authority_selection_v1
```

Operators can record exactly one server-owned initial worker-attempt receipt for an existing scheduler lease receipt. Replaying the same request returns the same receipt; a competing request for the same scheduler lease fails closed. The runtime still does not start a process, execute the job, emit progress, complete, cancel, retry, resume, enforce expiry, mutate scheduler-lease/queue-state/source-run receipts, broaden Candidate B scope, or expose raw paths/URLs.
