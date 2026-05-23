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
