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

## Candidate B Async Progress Checkpoint Authority Selection

```yaml
milestone: candidate_b_async_progress_checkpoint_authority_selection_v1
source_worker_attempt_runtime: next_milestone_plans/Layer3_planning_docs/1005-cb-async-worker-attempt-runtime.md
current_main_entry: 7ff4bbea39d6b989f0e6d50a7d1a844107125798
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_progress_checkpoint_receipt_v1
selected_progress_checkpoint_scope: server_owned_candidate_b_full_corpus_operator_workflow_worker_attempt_receipts
selected_progress_checkpoint_mode: append_only_progress_checkpoint_receipt_without_completion_or_cancel_retry_resume
selected_progress_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint
existing_worker_attempt_endpoint_reused_for_source_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_progress_checkpoint_receipt_model: append_only_progress_checkpoint_receipt_without_mutating_worker_attempt_scheduler_lease_queue_state_or_source_run_receipt
selected_progress_checkpoint_receipt_binding: worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,scheduler_lease_receipt_id,queue_state_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,progress_checkpoint_sequence,progress_checkpoint_hash
selected_progress_checkpoint_sequence_model: monotonically_increasing_append_only_sequence_per_worker_attempt
selected_progress_checkpoint_idempotency_basis: client_request_id_plus_progress_checkpoint_authority_hash
stale_worker_attempt_receipt_must_reject: true
stale_scheduler_lease_receipt_must_reject: true
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_worker_attempt_receipt_must_reject: true
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
progress_checkpoint_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_progress_checkpoint_receipt_v1
```

The selected next runtime should create server-owned append-only progress-checkpoint receipts over an existing worker-attempt receipt. It must preserve worker-attempt, scheduler-lease, queue-state, and source-run receipt immutability and must not execute the job, complete the workflow, cancel, retry, resume, enforce expiry, broaden Candidate B scope, or expose raw paths/URLs.

## Candidate B Async Progress Checkpoint Runtime

```yaml
milestone: candidate_b_async_progress_checkpoint_receipt_v1
source_progress_checkpoint_selection: next_milestone_plans/Layer3_planning_docs/1006-cb-async-progress-checkpoint-selection.md
runtime_status: implemented
selected_progress_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint
selected_progress_checkpoint_mode: append_only_progress_checkpoint_receipt_without_completion_or_cancel_retry_resume
selected_progress_checkpoint_action: record_candidate_b_async_progress_checkpoint
selected_progress_checkpoint_scope: server_owned_candidate_b_full_corpus_operator_workflow_worker_attempt_receipts
selected_progress_checkpoint_receipt_model: append_only_progress_checkpoint_receipt_without_mutating_worker_attempt_scheduler_lease_queue_state_or_source_run_receipt
selected_progress_checkpoint_sequence_model: monotonically_increasing_append_only_sequence_per_worker_attempt
selected_progress_checkpoint_idempotency_basis: client_request_id_plus_progress_checkpoint_authority_hash
stale_worker_attempt_receipt_rejected: true
stale_scheduler_lease_receipt_rejected: true
stale_queue_state_receipt_rejected: true
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_worker_attempt_receipt_rejected: true
non_next_progress_checkpoint_sequence_rejected: true
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
progress_checkpoint_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_completion_failure_authority_selection_v1
```

Operators can record append-only progress checkpoints for an existing worker-attempt receipt. A replayed request returns the same receipt, a non-next sequence fails closed, and workflow-run history remains a run-list projection even after child queue/lease/attempt/checkpoint receipts exist.

## Candidate B Async Completion/Failure Authority Selection

```yaml
milestone: candidate_b_async_completion_failure_authority_selection_v1
source_progress_checkpoint_runtime: next_milestone_plans/Layer3_planning_docs/1007-cb-async-progress-checkpoint-runtime.md
current_main_entry: 2d439e6b98786d38ba7d846c3ab1415d7abe0439
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_completion_failure_receipt_v1
selected_completion_failure_scope: server_owned_candidate_b_full_corpus_operator_workflow_worker_attempts_with_progress_checkpoint_receipts
selected_completion_failure_mode: append_only_completion_failure_receipt_without_cancel_retry_resume_or_source_receipt_mutation
selected_completion_failure_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
existing_progress_checkpoint_endpoint_reused_for_checkpoint_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint
existing_worker_attempt_endpoint_reused_for_attempt_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_completion_failure_receipt_model: append_only_terminal_receipt_without_mutating_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipt
selected_completion_failure_receipt_binding: worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,latest_progress_checkpoint_authority_hash,progress_checkpoint_sequence,scheduler_lease_receipt_id,queue_state_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,terminal_outcome,terminal_outcome_hash
selected_completion_failure_idempotency_basis: client_request_id_plus_completion_failure_authority_hash
selected_terminal_outcomes: completed,failed
minimum_progress_checkpoint_required: true
pre_checkpoint_failure_runtime_selected_now: false
terminal_failure_payload_must_be_operator_safe: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
stale_progress_checkpoint_receipt_must_reject: true
stale_worker_attempt_receipt_must_reject: true
stale_scheduler_lease_receipt_must_reject: true
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_progress_checkpoint_receipt_must_reject: true
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
completion_failure_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_completion_failure_receipt_v1
```

The next runtime-bearing Candidate B async workflow slice should record terminal completion/failure receipts over existing worker-attempt and latest progress-checkpoint authority. It must not execute the job, mutate any prior receipt, admit cancel/retry/resume, expose raw traces/logs/paths/URLs, broaden Candidate B scope, or activate provider/connector/model/full-mockup behavior.

## Candidate B Async Completion/Failure Runtime

```yaml
milestone: candidate_b_async_completion_failure_receipt_v1
source_completion_failure_selection: next_milestone_plans/Layer3_planning_docs/1008-cb-async-completion-failure-selection.md
runtime_status: implemented
selected_completion_failure_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
selected_completion_failure_mode: append_only_completion_failure_receipt_without_cancel_retry_resume_or_source_receipt_mutation
selected_completion_failure_action: record_candidate_b_async_completion_failure
selected_completion_failure_scope: server_owned_candidate_b_full_corpus_operator_workflow_worker_attempts_with_progress_checkpoint_receipts
selected_completion_failure_receipt_model: append_only_terminal_receipt_without_mutating_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipt
selected_completion_failure_receipt_binding: worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,latest_progress_checkpoint_authority_hash,progress_checkpoint_sequence,scheduler_lease_receipt_id,queue_state_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,terminal_outcome,terminal_outcome_hash
selected_completion_failure_idempotency_basis: client_request_id_plus_completion_failure_authority_hash
selected_terminal_outcomes: completed,failed
minimum_progress_checkpoint_required: true
pre_checkpoint_failure_runtime_selected_now: false
stale_progress_checkpoint_receipt_rejected: true
missing_progress_checkpoint_receipt_rejected: true
non_latest_progress_checkpoint_receipt_rejected: true
terminal_conflict_rejected: true
terminal_failure_payload_operator_safe: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
completion_failure_runtime_selected: true
background_process_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_cancel_retry_resume_policy_selection_v1
```

Operators can record exactly one terminal completion/failure receipt for a worker attempt with latest progress-checkpoint authority. The endpoint accepts `completed` or `failed`; failed receipts require short operator-safe failure code and phase tokens and reject raw traces/logs/paths/URLs.

## Candidate B Async Cancel/Retry/Resume Policy Selection

```yaml
milestone: candidate_b_async_cancel_retry_resume_policy_selection_v1
source_completion_failure_runtime: next_milestone_plans/Layer3_planning_docs/1009-cb-async-completion-failure-runtime.md
current_main_entry: e14ec1f9a78cb3ca85db2a3a83754de5413bf209
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_policy_receipt_v1
selected_retry_policy_scope: server_owned_candidate_b_full_corpus_operator_workflow_failed_terminal_receipts
selected_retry_policy_mode: append_only_retry_policy_receipt_without_creating_retry_attempt_or_mutating_terminal_receipts
selected_retry_policy_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
existing_completion_failure_endpoint_reused_for_terminal_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
selected_retry_policy_receipt_model: append_only_retry_policy_receipt_without_mutating_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_policy_receipt_binding: completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,terminal_outcome,terminal_outcome_hash,worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,queue_state_receipt_id,scheduler_lease_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_policy_hash
selected_retry_policy_idempotency_basis: client_request_id_plus_retry_policy_authority_hash
terminal_outcome_required_for_retry: failed
completed_terminal_receipt_retry_rejected: true
missing_terminal_receipt_retry_rejected: true
stale_terminal_receipt_retry_rejected: true
terminal_conflict_retry_rejected: true
retry_attempt_creation_admitted_now: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
cancel_runtime_selected_now: false
retry_policy_runtime_selected_after_sync: true
retry_attempt_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_policy_receipt_v1
```

The selected next runtime should record append-only retry-policy authority over an existing failed terminal completion/failure receipt. It must reject completed terminal receipts, avoid creating a retry attempt in the same slice, preserve all prior queue/lease/attempt/progress/terminal/source receipts, and keep cancel, resume, expiry enforcement, job execution, provider/connector/model behavior, and full mockup activation outside this admission.

## Candidate B Async Retry-Policy Runtime

```yaml
milestone: candidate_b_async_retry_policy_receipt_v1
source_cancel_retry_resume_selection: next_milestone_plans/Layer3_planning_docs/1010-cb-async-cancel-retry-resume-selection.md
runtime_status: implemented
selected_retry_policy_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
selected_retry_policy_mode: append_only_retry_policy_receipt_without_creating_retry_attempt_or_mutating_terminal_receipts
selected_retry_policy_action: record_candidate_b_async_retry_policy
selected_retry_policy_scope: server_owned_candidate_b_full_corpus_operator_workflow_failed_terminal_receipts
selected_retry_policy_receipt_model: append_only_retry_policy_receipt_without_mutating_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_policy_receipt_binding: completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,terminal_outcome,terminal_outcome_hash,worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,queue_state_receipt_id,scheduler_lease_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_policy_hash
selected_retry_policy_idempotency_basis: client_request_id_plus_retry_policy_authority_hash
terminal_outcome_required_for_retry: failed
completed_terminal_receipt_retry_rejected: true
stale_terminal_receipt_retry_rejected: true
terminal_conflict_retry_rejected: true
retry_policy_runtime_selected: true
retry_attempt_creation_admitted_now: false
retry_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
next_exact_posture: candidate_b_async_retry_attempt_authority_selection_v1
```

Operators can record retry-policy authority for an existing failed terminal receipt. The runtime proves retry eligibility or ineligibility without creating a retry attempt, mutating any existing queue/lease/attempt/progress/terminal/source receipt, executing a job, cancelling work, resuming from a checkpoint, broadening Candidate B scope, or exposing raw authority.

## Candidate B Async Retry-Attempt Authority Selection

```yaml
milestone: candidate_b_async_retry_attempt_authority_selection_v1
source_retry_policy_runtime: next_milestone_plans/Layer3_planning_docs/1011-cb-async-retry-policy-runtime.md
current_main_entry: 264e397c49512bbf280e9511b24e39b78dbd0dd0
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_queue_state_receipt_v1
selected_first_retry_runtime_reason: retry_attempt_requires_new_queue_state_scheduler_lease_and_worker_attempt_lineage
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_queue_state_scope: server_owned_candidate_b_full_corpus_operator_workflow_eligible_retry_policy_receipts
selected_retry_queue_state_mode: append_only_retry_queue_state_receipt_without_creating_scheduler_lease_worker_attempt_or_mutating_original_lineage
selected_retry_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
selected_retry_queue_state_receipt_model: append_only_retry_queue_state_receipt_without_mutating_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_queue_state_receipt_binding: retry_policy_receipt_id,retry_policy_receipt_hash,retry_policy_authority_hash,retry_policy_result,completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,failed_worker_attempt_receipt_id,failed_worker_attempt_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_queue_state_hash
selected_retry_queue_state_idempotency_basis: client_request_id_plus_retry_queue_state_authority_hash
retry_policy_result_required: eligible
ineligible_retry_policy_rejected: true
missing_retry_policy_receipt_rejected: true
stale_retry_policy_receipt_rejected: true
retry_policy_conflict_rejected: true
retry_attempt_number_selected: 2
retry_scheduler_lease_creation_admitted_now: false
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
retry_queue_state_runtime_selected_after_sync: true
retry_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_queue_state_receipt_v1
```

The selected next runtime should create retry queue-state authority over an eligible retry-policy receipt. It starts a new retry lineage without reusing or mutating the original failed queue/lease/attempt/progress/terminal receipts and without creating the retry scheduler lease, retry worker attempt, retry progress checkpoint, retry terminal receipt, or any job execution in the same slice.

## Candidate B Async Retry Queue-State Runtime

```yaml
milestone: candidate_b_async_retry_queue_state_receipt_v1
source_retry_attempt_selection: next_milestone_plans/Layer3_planning_docs/1012-cb-async-retry-attempt-selection.md
runtime_status: implemented
selected_retry_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
selected_retry_queue_state_mode: append_only_retry_queue_state_receipt_without_creating_scheduler_lease_worker_attempt_or_mutating_original_lineage
selected_retry_queue_state_action: record_candidate_b_async_retry_queue_state
selected_retry_queue_state_scope: server_owned_candidate_b_full_corpus_operator_workflow_eligible_retry_policy_receipts
selected_retry_queue_state_receipt_model: append_only_retry_queue_state_receipt_without_mutating_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_queue_state_receipt_binding: retry_policy_receipt_id,retry_policy_receipt_hash,retry_policy_authority_hash,retry_policy_result,completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,failed_worker_attempt_receipt_id,failed_worker_attempt_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_queue_state_hash
selected_retry_queue_state_idempotency_basis: client_request_id_plus_retry_queue_state_authority_hash
retry_policy_result_required: eligible
ineligible_retry_policy_rejected: true
missing_retry_policy_receipt_rejected: true
stale_retry_policy_receipt_rejected: true
retry_policy_conflict_rejected: true
retry_attempt_number_selected: 2
retry_queue_state_runtime_selected: true
retry_scheduler_lease_creation_admitted_now: false
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
retry_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
next_exact_posture: candidate_b_async_retry_scheduler_lease_authority_selection_v1
```

Operators can record retry queue-state authority over one eligible retry-policy receipt. The runtime starts the retry lineage at attempt number 2, rejects ineligible or stale retry-policy authority, preserves the original failed lineage, and still defers retry scheduler lease creation, retry worker attempt creation, retry progress/failure receipts, cancel/resume, and job execution to separately admitted slices.

## Candidate B Async Retry Scheduler-Lease Authority Selection

```yaml
milestone: candidate_b_async_retry_scheduler_lease_authority_selection_v1
source_retry_queue_state_runtime: next_milestone_plans/Layer3_planning_docs/1013-cb-async-retry-queue-state-runtime.md
current_main_entry: 23d11e18f2c97450108ffb8c194cee9de789303d
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_scheduler_lease_receipt_v1
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_scheduler_lease_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_queue_state_receipts
selected_retry_scheduler_lease_mode: append_only_retry_scheduler_lease_receipt_without_creating_worker_attempt_or_mutating_retry_queue_state_original_lineage
selected_retry_scheduler_lease_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease
existing_retry_queue_state_endpoint_reused_for_retry_lineage_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
selected_retry_scheduler_lease_receipt_model: append_only_retry_scheduler_lease_receipt_without_mutating_retry_queue_state_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_scheduler_lease_receipt_binding: retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_queue_state_authority_hash,retry_attempt_number,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_scheduler_lease_hash
selected_retry_scheduler_lease_idempotency_basis: client_request_id_plus_retry_scheduler_lease_authority_hash
retry_queue_state_receipt_required: true
retry_queue_state_runtime_required: true
retry_attempt_number_required: 2
missing_retry_queue_state_receipt_rejected: true
stale_retry_queue_state_receipt_rejected: true
retry_queue_state_conflict_rejected: true
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
retry_scheduler_lease_runtime_selected_after_sync: true
retry_worker_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_scheduler_lease_receipt_v1
```

The next selected runtime should record a retry scheduler-lease receipt over a current retry queue-state receipt. It must preserve the original failed lineage and the retry queue-state receipt, reject stale or conflicting retry queue-state authority, and still defer retry worker attempts, retry progress/failure receipts, cancel/resume, background process, and job execution.

## Candidate B Async Retry Scheduler-Lease Runtime

```yaml
milestone: candidate_b_async_retry_scheduler_lease_receipt_v1
source_retry_scheduler_lease_selection: next_milestone_plans/Layer3_planning_docs/1014-cb-async-retry-scheduler-lease-selection.md
runtime_status: implemented
selected_retry_scheduler_lease_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease
selected_retry_scheduler_lease_mode: append_only_retry_scheduler_lease_receipt_without_creating_worker_attempt_or_mutating_retry_queue_state_original_lineage
selected_retry_scheduler_lease_action: record_candidate_b_async_retry_scheduler_lease
selected_retry_scheduler_lease_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_queue_state_receipts
selected_retry_scheduler_lease_receipt_model: append_only_retry_scheduler_lease_receipt_without_mutating_retry_queue_state_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_scheduler_lease_receipt_binding: retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_queue_state_authority_hash,retry_attempt_number,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_scheduler_lease_hash
selected_retry_scheduler_lease_idempotency_basis: client_request_id_plus_retry_scheduler_lease_authority_hash
retry_queue_state_receipt_required: true
retry_queue_state_runtime_required: true
retry_attempt_number_required: 2
missing_retry_queue_state_receipt_rejected: true
stale_retry_queue_state_receipt_rejected: true
retry_queue_state_conflict_rejected: true
append_only_retry_scheduler_lease_receipt: true
exclusive_retry_queue_state_lease: true
retry_scheduler_lease_runtime_selected: true
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
retry_worker_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_worker_attempt_authority_selection_v1
```

Operators can now record retry scheduler-lease authority over a current retry queue-state receipt. The receipt creates exclusive retry lease authority without creating worker attempts, progress checkpoints, terminal retry failures, cancel/resume behavior, background processes, or job execution in this slice.

## Candidate B Async Retry Worker-Attempt Authority Selection

```yaml
milestone: candidate_b_async_retry_worker_attempt_authority_selection_v1
source_retry_scheduler_lease_runtime: next_milestone_plans/Layer3_planning_docs/1015-cb-async-retry-scheduler-lease-runtime.md
current_main_entry: ec83458e125f27a312fbf18a6e9ffc5027057504
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_worker_attempt_receipt_v1
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_worker_attempt_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_receipts
selected_retry_worker_attempt_mode: append_only_retry_worker_attempt_receipt_without_job_execution
selected_retry_worker_attempt_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt
existing_retry_scheduler_lease_endpoint_reused_for_retry_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease
existing_retry_queue_state_endpoint_reused_for_retry_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
selected_retry_worker_attempt_receipt_model: append_only_retry_worker_attempt_receipt_without_mutating_retry_scheduler_lease_retry_queue_state_retry_policy_completion_failure_failed_worker_attempt_progress_checkpoint_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_worker_attempt_receipt_binding: retry_scheduler_lease_receipt_id,retry_scheduler_lease_receipt_hash,retry_scheduler_lease_authority_hash,retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_queue_state_authority_hash,retry_attempt_number,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_worker_attempt_hash
selected_retry_worker_attempt_idempotency_basis: client_request_id_plus_retry_worker_attempt_authority_hash
selected_retry_worker_attempt_number: 2
exclusive_retry_worker_attempt_per_retry_scheduler_lease: true
stale_retry_scheduler_lease_receipt_must_reject: true
stale_retry_queue_state_receipt_must_reject: true
stale_retry_policy_receipt_must_reject: true
stale_completion_failure_receipt_must_reject: true
stale_failed_worker_attempt_receipt_must_reject: true
missing_retry_scheduler_lease_receipt_must_reject: true
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
retry_worker_attempt_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_progress_checkpoint_runtime_selected_now: false
retry_completion_failure_runtime_selected_now: false
cancel_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_retry_worker_attempt_receipt_v1
```

The next selected runtime should record retry worker-attempt authority over a current retry scheduler-lease receipt. It must create new attempt-number-2 authority without reusing the failed worker attempt as the retry attempt, and without starting job execution, progress, retry completion, cancel/resume, provider writes, connector dispatch, model runtime, or full mockup behavior.

## Candidate B Async Retry Worker-Attempt Runtime

```yaml
milestone: candidate_b_async_retry_worker_attempt_receipt_v1
source_retry_worker_attempt_selection: next_milestone_plans/Layer3_planning_docs/1016-cb-async-retry-worker-attempt-selection.md
runtime_status: implemented
selected_retry_worker_attempt_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt
selected_retry_worker_attempt_mode: append_only_retry_worker_attempt_receipt_without_job_execution
selected_retry_worker_attempt_action: record_candidate_b_async_retry_worker_attempt
selected_retry_worker_attempt_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_receipts
selected_retry_worker_attempt_receipt_model: append_only_retry_worker_attempt_receipt_without_mutating_retry_scheduler_lease_retry_queue_state_retry_policy_completion_failure_failed_worker_attempt_progress_checkpoint_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_worker_attempt_receipt_binding: retry_scheduler_lease_receipt_id,retry_scheduler_lease_receipt_hash,retry_scheduler_lease_authority_hash,retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_queue_state_authority_hash,retry_attempt_number,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_worker_attempt_hash
selected_retry_worker_attempt_idempotency_basis: client_request_id_plus_retry_worker_attempt_authority_hash
selected_retry_worker_attempt_number: 2
retry_scheduler_lease_receipt_required: true
retry_scheduler_lease_runtime_required: true
missing_retry_scheduler_lease_receipt_rejected: true
stale_retry_scheduler_lease_receipt_rejected: true
retry_scheduler_lease_conflict_rejected: true
append_only_retry_worker_attempt_receipt: true
exclusive_retry_worker_attempt_per_retry_scheduler_lease: true
retry_worker_attempt_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_progress_checkpoint_runtime_selected_now: false
retry_completion_failure_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
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
next_exact_posture: candidate_b_async_retry_progress_checkpoint_authority_selection_v1
```

Operators can now record retry worker-attempt identity over a retry scheduler-lease receipt. The runtime preserves retry lineage authority and still defers retry progress, retry completion/failure, cancellation/resume, background execution, and job execution to separately selected slices.

## Candidate B Async Retry Progress Checkpoint Authority Selection

```yaml
milestone: candidate_b_async_retry_progress_checkpoint_authority_selection_v1
source_retry_worker_attempt_runtime: next_milestone_plans/Layer3_planning_docs/1017-cb-async-retry-worker-attempt-runtime.md
current_main_entry: bf4943296d62bbaf8500075eee981325b7b9a8dc
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_progress_checkpoint_receipt_v1
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_progress_checkpoint_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_receipts
selected_retry_progress_checkpoint_mode: append_only_retry_progress_checkpoint_receipt_without_retry_completion_cancel_resume_or_job_execution
selected_retry_progress_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint
existing_retry_worker_attempt_endpoint_reused_for_retry_attempt_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt
existing_retry_scheduler_lease_endpoint_reused_for_retry_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease
existing_retry_queue_state_endpoint_reused_for_retry_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
selected_retry_progress_checkpoint_receipt_model: append_only_retry_progress_checkpoint_receipt_without_mutating_retry_worker_attempt_retry_scheduler_lease_retry_queue_state_retry_policy_completion_failure_failed_worker_attempt_progress_checkpoint_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_progress_checkpoint_receipt_binding: retry_worker_attempt_receipt_id,retry_worker_attempt_receipt_hash,retry_worker_attempt_authority_hash,retry_scheduler_lease_receipt_id,retry_scheduler_lease_receipt_hash,retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_progress_checkpoint_sequence,retry_progress_checkpoint_hash
selected_retry_progress_checkpoint_sequence_model: monotonically_increasing_append_only_sequence_per_retry_worker_attempt
selected_retry_progress_checkpoint_idempotency_basis: client_request_id_plus_retry_progress_checkpoint_authority_hash
retry_attempt_number_required: 2
stale_retry_worker_attempt_receipt_must_reject: true
stale_retry_scheduler_lease_receipt_must_reject: true
stale_retry_queue_state_receipt_must_reject: true
stale_retry_policy_receipt_must_reject: true
stale_completion_failure_receipt_must_reject: true
stale_failed_worker_attempt_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_retry_worker_attempt_receipt_must_reject: true
retry_worker_attempt_receipt_mutation_admitted: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
retry_progress_checkpoint_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_completion_failure_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_progress_checkpoint_receipt_v1
```

The next selected runtime should record retry progress-checkpoint authority over a current retry worker-attempt receipt. It must preserve retry worker-attempt, retry scheduler-lease, retry queue-state, retry-policy, original failed lineage, and source-run receipt immutability while still deferring retry completion/failure, cancel/resume, background process, and job execution.

## Candidate B Async Retry Progress Checkpoint Runtime

```yaml
milestone: candidate_b_async_retry_progress_checkpoint_receipt_v1
source_retry_progress_checkpoint_selection: next_milestone_plans/Layer3_planning_docs/1018-cb-async-retry-progress-checkpoint-selection.md
runtime_status: implemented
selected_retry_progress_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint
selected_retry_progress_checkpoint_mode: append_only_retry_progress_checkpoint_receipt_without_retry_completion_cancel_resume_or_job_execution
selected_retry_progress_checkpoint_action: record_candidate_b_async_retry_progress_checkpoint
selected_retry_progress_checkpoint_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_receipts
selected_retry_progress_checkpoint_receipt_model: append_only_retry_progress_checkpoint_receipt_without_mutating_retry_worker_attempt_retry_scheduler_lease_retry_queue_state_retry_policy_completion_failure_failed_worker_attempt_progress_checkpoint_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_progress_checkpoint_receipt_binding: retry_worker_attempt_receipt_id,retry_worker_attempt_receipt_hash,retry_worker_attempt_authority_hash,retry_scheduler_lease_receipt_id,retry_scheduler_lease_receipt_hash,retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_progress_checkpoint_sequence,retry_progress_checkpoint_hash
selected_retry_progress_checkpoint_sequence_model: monotonically_increasing_append_only_sequence_per_retry_worker_attempt
selected_retry_progress_checkpoint_idempotency_basis: client_request_id_plus_retry_progress_checkpoint_authority_hash
retry_attempt_number_required: 2
retry_worker_attempt_receipt_required: true
missing_retry_worker_attempt_receipt_rejected: true
stale_retry_worker_attempt_receipt_rejected: true
non_next_retry_progress_checkpoint_sequence_rejected: true
append_only_retry_progress_checkpoint_receipt: true
monotonic_retry_progress_checkpoint_sequence: true
retry_progress_checkpoint_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_completion_failure_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
retry_worker_attempt_receipt_mutation_admitted: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_completion_failure_authority_selection_v1
```

Operators can now record retry progress-checkpoint authority after retry worker-attempt authority exists for attempt number 2. This does not complete the retry, start background processing, execute a job, expose raw refs, or mutate the original failed lineage; retry completion/failure remains a separate selected slice.

## Candidate B Async Retry Completion/Failure Authority Selection

```yaml
milestone: candidate_b_async_retry_completion_failure_authority_selection_v1
source_retry_progress_checkpoint_runtime: next_milestone_plans/Layer3_planning_docs/1019-cb-async-retry-progress-checkpoint-runtime.md
current_main_entry: 10a49385ee1578993df7bf738b7c2e2e9a5fe764
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_completion_failure_receipt_v1
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_completion_failure_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_worker_attempts_with_retry_progress_checkpoint_receipts
selected_retry_completion_failure_mode: append_only_retry_completion_failure_receipt_without_cancel_resume_job_execution_or_source_receipt_mutation
selected_retry_completion_failure_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure
existing_retry_progress_checkpoint_endpoint_reused_for_retry_checkpoint_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint
existing_retry_worker_attempt_endpoint_reused_for_retry_attempt_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt
existing_retry_scheduler_lease_endpoint_reused_for_retry_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease
existing_retry_queue_state_endpoint_reused_for_retry_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_policy_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
existing_original_completion_failure_endpoint_reused_for_failed_lineage: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_retry_completion_failure_receipt_model: append_only_retry_terminal_receipt_without_mutating_retry_progress_checkpoint_retry_worker_attempt_retry_scheduler_lease_retry_queue_state_retry_policy_original_completion_failure_failed_worker_attempt_progress_checkpoint_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_completion_failure_receipt_binding: retry_worker_attempt_receipt_id,retry_worker_attempt_receipt_hash,retry_worker_attempt_authority_hash,latest_retry_progress_checkpoint_receipt_id,latest_retry_progress_checkpoint_receipt_hash,latest_retry_progress_checkpoint_authority_hash,retry_progress_checkpoint_sequence,retry_scheduler_lease_receipt_id,retry_queue_state_receipt_id,retry_policy_receipt_id,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_terminal_outcome,retry_terminal_outcome_hash
selected_retry_completion_failure_idempotency_basis: client_request_id_plus_retry_completion_failure_authority_hash
selected_retry_terminal_outcomes: completed,failed
minimum_retry_progress_checkpoint_required: true
pre_retry_checkpoint_failure_runtime_selected_now: false
retry_terminal_failure_payload_must_be_operator_safe: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
stale_retry_progress_checkpoint_receipt_must_reject: true
stale_retry_worker_attempt_receipt_must_reject: true
stale_retry_scheduler_lease_receipt_must_reject: true
stale_retry_queue_state_receipt_must_reject: true
stale_retry_policy_receipt_must_reject: true
stale_original_completion_failure_receipt_must_reject: true
stale_failed_worker_attempt_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_retry_progress_checkpoint_receipt_must_reject: true
retry_progress_checkpoint_receipt_mutation_admitted: false
retry_worker_attempt_receipt_mutation_admitted: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
retry_completion_failure_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_retry_completion_failure_receipt_v1
```

The selected next slice is retry terminal authority over an existing retry progress checkpoint. It must record a retry completion/failure receipt without executing work, mutating retry or original failed-lineage receipts, exposing raw traces or refs, or admitting cancel/resume/job execution.

## Candidate B Async Retry Completion/Failure Runtime

```yaml
milestone: candidate_b_async_retry_completion_failure_receipt_v1
source_retry_completion_failure_selection: next_milestone_plans/Layer3_planning_docs/1020-cb-async-retry-completion-failure-selection.md
runtime_status: implemented
selected_retry_completion_failure_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure
selected_retry_completion_failure_mode: append_only_retry_completion_failure_receipt_without_cancel_resume_job_execution_or_source_receipt_mutation
selected_retry_completion_failure_action: record_candidate_b_async_retry_completion_failure
selected_retry_completion_failure_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_worker_attempts_with_retry_progress_checkpoint_receipts
selected_retry_completion_failure_receipt_model: append_only_retry_terminal_receipt_without_mutating_retry_progress_checkpoint_retry_worker_attempt_retry_scheduler_lease_retry_queue_state_retry_policy_original_completion_failure_failed_worker_attempt_progress_checkpoint_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_completion_failure_receipt_binding: retry_worker_attempt_receipt_id,retry_worker_attempt_receipt_hash,retry_worker_attempt_authority_hash,latest_retry_progress_checkpoint_receipt_id,latest_retry_progress_checkpoint_receipt_hash,latest_retry_progress_checkpoint_authority_hash,retry_progress_checkpoint_sequence,retry_scheduler_lease_receipt_id,retry_queue_state_receipt_id,retry_policy_receipt_id,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_terminal_outcome,retry_terminal_outcome_hash
selected_retry_completion_failure_idempotency_basis: client_request_id_plus_retry_completion_failure_authority_hash
selected_retry_terminal_outcomes: completed,failed
retry_attempt_number_required: 2
minimum_retry_progress_checkpoint_required: true
missing_retry_progress_checkpoint_receipt_rejected: true
stale_retry_progress_checkpoint_receipt_rejected: true
non_latest_retry_progress_checkpoint_receipt_rejected: true
retry_terminal_conflict_rejected: true
retry_terminal_failure_payload_operator_safe: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
retry_progress_checkpoint_receipt_mutation_admitted: false
retry_worker_attempt_receipt_mutation_admitted: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
retry_completion_failure_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_retry_terminal_status_projection_selection_v1
```

Operators can now record retry terminal authority after retry progress-checkpoint authority exists for retry attempt number 2. This does not start background processing, execute a job, mutate retry or original failed-lineage receipts, expose raw refs, or admit cancel/resume; the next useful slice should make retry terminal receipts visible through status/history projection.

## Candidate B Async Retry Terminal Status Projection Selection

```yaml
milestone: candidate_b_async_retry_terminal_status_projection_selection_v1
source_retry_completion_failure_runtime: next_milestone_plans/Layer3_planning_docs/1021-cb-async-retry-completion-failure-runtime.md
current_main_entry: 33abf1eada164eafd95e48273f60440b3ba26f05
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_terminal_status_projection_v1
selected_retry_terminal_status_projection_scope: server_owned_candidate_b_full_corpus_operator_workflow_status_history_projection_of_retry_completion_failure_receipts
selected_retry_terminal_status_projection_mode: read_only_retry_terminal_receipt_projection_without_receipt_creation_or_lineage_mutation
selected_retry_terminal_status_projection_surfaces: status,history
existing_status_endpoint_reused_for_retry_terminal_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_history_endpoint_reused_for_retry_terminal_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_retry_completion_failure_endpoint_reused_for_retry_terminal_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure
selected_retry_terminal_status_projection_model: redacted_read_only_projection_of_latest_retry_completion_failure_receipt_per_retry_worker_attempt
selected_retry_terminal_status_projection_binding: retry_completion_failure_receipt_id,retry_completion_failure_receipt_hash,retry_completion_failure_authority_hash,retry_worker_attempt_receipt_id,retry_worker_attempt_authority_hash,latest_retry_progress_checkpoint_receipt_id,latest_retry_progress_checkpoint_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_terminal_outcome,retry_terminal_outcome_hash
selected_retry_terminal_status_projection_idempotency_basis: read_only_projection_from_server_owned_retry_terminal_receipts
retry_terminal_projection_state_values: not_recorded,completed,failed,blocked
missing_retry_terminal_receipt_projects_not_recorded: true
stale_retry_terminal_receipt_must_reject: true
ambiguous_retry_terminal_receipt_must_reject: true
retry_terminal_failure_payload_operator_safe: true
operator_safe_retry_terminal_failure_code_visible: true
operator_safe_retry_terminal_failure_phase_visible: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
retry_terminal_receipt_creation_admitted_now: false
retry_completion_failure_receipt_mutation_admitted: false
retry_progress_checkpoint_receipt_mutation_admitted: false
retry_worker_attempt_receipt_mutation_admitted: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
failed_worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
retry_terminal_status_projection_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_retry_terminal_status_projection_v1
```

The selected next slice should project retry terminal completion/failure authority through existing status and history surfaces. Missing retry terminal authority should show `not_recorded`; stale or ambiguous retry terminal authority must fail closed. This slice does not admit receipt creation, retry-lineage mutation, job execution, cancel/resume, source expansion, connector/provider writes, RAG/model runtime, or raw refs.

## Candidate B Async Retry Terminal Status Projection Runtime

```yaml
milestone: candidate_b_async_retry_terminal_status_projection_v1
source_retry_terminal_status_projection_selection: next_milestone_plans/Layer3_planning_docs/1022-cb-async-retry-terminal-status-projection-selection.md
current_main_entry: f775019701ba0312e1638164e22d2de33c6564e3
runtime_status: implemented
selected_retry_terminal_status_projection_mode: read_only_retry_terminal_receipt_projection_without_receipt_creation_or_lineage_mutation
selected_retry_terminal_status_projection_surfaces: status,history
existing_status_endpoint_reused_for_retry_terminal_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_history_endpoint_reused_for_retry_terminal_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_retry_completion_failure_endpoint_reused_for_retry_terminal_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure
missing_retry_terminal_receipt_projects_not_recorded: true
stale_retry_terminal_receipt_rejected: true
ambiguous_retry_terminal_receipt_rejected: true
history_row_hash_excludes_retry_terminal_status_projection: true
history_hash_excludes_retry_terminal_status_projection: true
retry_terminal_receipt_creation_admitted_now: false
retry_completion_failure_receipt_mutation_admitted: false
retry_progress_checkpoint_receipt_mutation_admitted: false
retry_worker_attempt_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
retry_terminal_status_projection_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_terminal_rendered_status_projection_selection_v1
```

Operators can now inspect retry terminal completion/failure authority through existing workflow status and history responses. No terminal receipt projects as `not_recorded`; completed and failed terminal receipts project only redacted receipt/outcome/progress/worker-attempt authority; stale or ambiguous terminal receipts fail closed. The projection does not change row/history authority hashes, does not create receipts, does not mutate retry lineage, and does not admit job execution, cancel, resume, raw refs, provider writes, connector dispatch, RAG/model runtime, or full mockup activation.

### Candidate B Async Retry Terminal Rendered Status Projection Selection

```yaml
milestone: candidate_b_async_retry_terminal_rendered_status_projection_selection_v1
source_retry_terminal_status_projection_runtime: next_milestone_plans/Layer3_planning_docs/1023-cb-async-retry-terminal-status-projection-runtime.md
current_main_entry: 0297917e4b45dcca9d9e4153cc14b61e61e440ee
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_terminal_rendered_status_projection_v1
selected_rendered_retry_terminal_projection_mode: rendered_read_only_projection_without_receipt_creation_lineage_mutation_or_frontend_authority
selected_rendered_retry_terminal_projection_surfaces: status,history
existing_status_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_history_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_rendered_status_control_reused: candidate-b-full-corpus-workflow-status-form
existing_rendered_history_control_reused: candidate-b-full-corpus-workflow-history-form
missing_retry_terminal_receipt_renders_not_recorded: true
completed_retry_terminal_receipt_renders_completed: true
failed_retry_terminal_receipt_renders_failed: true
stale_retry_terminal_receipt_must_fail_closed_server_side: true
ambiguous_retry_terminal_receipt_must_fail_closed_server_side: true
retry_terminal_receipt_creation_admitted_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_terminal_rendered_status_projection_v1
```

The next rendered slice should make the already-server-projected retry terminal status visible in the existing read-only Candidate B workflow status and history controls. The browser may display only server-provided redacted retry terminal projection fields. It must not create or repair terminal receipts, mutate retry lineage, start jobs, admit cancel/resume, expose raw refs, or add frontend durable authority.

### Candidate B Async Retry Terminal Rendered Status Projection Runtime

```yaml
milestone: candidate_b_async_retry_terminal_rendered_status_projection_v1
source_rendered_retry_terminal_projection_selection: next_milestone_plans/Layer3_planning_docs/1024-cb-async-retry-terminal-rendered-status-projection-selection.md
current_main_entry: e9f6b3c5d8dd0d32daf7dcced74904cc9d1ce143
runtime_status: implemented
selected_rendered_retry_terminal_projection_mode: rendered_read_only_projection_without_receipt_creation_lineage_mutation_or_frontend_authority
selected_rendered_retry_terminal_projection_surfaces: status,history
existing_rendered_status_control_reused: candidate-b-full-corpus-workflow-status-form
existing_rendered_history_control_reused: candidate-b-full-corpus-workflow-history-form
rendered_retry_terminal_projection_helper: candidateBRetryTerminalProjectionItems
rendered_status_projection_card: Retry Terminal Projection
rendered_status_e2e_target: e2e/layer3-workbench.spec.js::Layer 3 workbench inspects Candidate B full-corpus workflow status through rendered read-only control
rendered_history_e2e_target: e2e/layer3-workbench.spec.js::Layer 3 workbench refreshes Candidate B workflow history and inspects a selected run
missing_retry_terminal_receipt_renders_not_recorded: true
completed_retry_terminal_receipt_renders_completed: true
failed_retry_terminal_receipt_renders_failed: true
stale_retry_terminal_receipt_must_fail_closed_server_side: true
ambiguous_retry_terminal_receipt_must_fail_closed_server_side: true
retry_terminal_receipt_creation_admitted_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_background_job_execution_boundary_selection_v1
```

Operators can now inspect retry terminal status through the rendered full-corpus workflow status and history controls. The rendered projection shows server-provided retry terminal state, outcome, receipt authority, worker-attempt/progress-checkpoint binding, operator-safe failure code/phase, and guardrail fields without exposing raw paths, URLs, traces, logs, or artifact bytes.

### Candidate B Async Background Job Execution Boundary Selection

```yaml
milestone: candidate_b_async_background_job_execution_boundary_selection_v1
source_rendered_retry_terminal_projection_runtime: next_milestone_plans/Layer3_planning_docs/1025-cb-async-retry-terminal-rendered-status-projection-runtime.md
current_main_entry: 9c88315b06839c921ac5fbecc616b8dc4591be18
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_background_job_execution_boundary_v1
selected_background_execution_boundary_mode: execution_boundary_receipt_without_process_start_or_job_execution
selected_background_execution_boundary_source_lineage: operator_workflow_receipt,queue_state_receipt,scheduler_lease_receipt,worker_attempt_receipt,progress_checkpoint_receipt,completion_failure_receipt,retry_policy_receipt,retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_background_execution_boundary_outputs: execution_boundary_receipt,execution_boundary_receipt_hash,execution_boundary_authority_hash,operator_safe_execution_state,status_history_projection_fields
status_history_projection_required_after_boundary: true
rendered_operator_projection_required_after_boundary: true
stale_history_row_must_reject: true
stale_scheduler_lease_must_reject: true
stale_worker_attempt_must_reject: true
stale_progress_checkpoint_must_reject: true
terminal_receipt_conflict_must_reject: true
background_process_runtime_selected_after_sync: true
job_execution_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_background_job_execution_boundary_v1
```

The next runtime should record a server-owned background execution-boundary receipt over the existing Candidate B async lineage. It should prove the workflow row, queue/lease/attempt/progress/terminal authority, retry lineage, and rendered status/history projection are coherent enough to become a future execution target without starting a worker or executing corpus processing in the same slice.

### Candidate B Async Background Job Execution Boundary Runtime

```yaml
milestone: candidate_b_async_background_job_execution_boundary_v1
source_background_job_execution_boundary_selection: next_milestone_plans/Layer3_planning_docs/1026-cb-async-background-job-execution-boundary-selection.md
current_main_entry: 351d22068cb26cb7e2b48f3ba9a42243c8561c39
runtime_status: implemented
selected_execution_boundary_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary
selected_execution_boundary_mode: append_only_execution_boundary_receipt_without_process_start_or_job_execution
selected_execution_boundary_action: record_candidate_b_async_background_job_execution_boundary
selected_execution_boundary_scope: server_owned_candidate_b_full_corpus_workflow_execution_boundary_over_existing_queue_lease_attempt_progress_terminal_receipts
selected_execution_boundary_source_lineage: operator_workflow_receipt,queue_state_receipt,scheduler_lease_receipt,worker_attempt_receipt,progress_checkpoint_receipt,completion_failure_receipt,retry_completion_failure_receipt
selected_execution_boundary_outputs: execution_boundary_receipt,execution_boundary_receipt_hash,execution_boundary_authority_hash,execution_boundary_projection
status_history_projection_after_boundary: true
rendered_operator_projection_after_boundary: true
stale_history_row_must_reject: true
stale_scheduler_lease_must_reject: true
stale_worker_attempt_must_reject: true
stale_progress_checkpoint_must_reject: true
terminal_receipt_conflict_must_reject: true
missing_retry_terminal_receipt_must_reject: true
source_run_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
retry_completion_failure_receipt_mutation_admitted: false
execution_boundary_runtime_selected: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_scope: backend_service_api_readiness_status_history_rendered_operator_control_focused_tests
next_exact_posture: candidate_b_async_background_process_execution_selection_v1
```

Operators can now record an append-only execution-boundary receipt for a selected workflow row after terminal retry projection is visible. The server revalidates configured receipt authority and projects the boundary through workflow status/history plus the rendered operator surface. This still does not start a background process, execute a job, accept commands/paths/URLs from the browser, mutate source lineage, broaden Candidate B scope, or enable provider writes, connector dispatch, RAG/model runtime, full mockup activation, browser storage authority, or frontend durable authority.

### Candidate B Async Background Process Execution Selection

```yaml
milestone: candidate_b_async_background_process_execution_selection_v1
source_execution_boundary_runtime: next_milestone_plans/Layer3_planning_docs/1027-cb-async-background-job-execution-boundary-runtime.md
current_main_entry: fc59ebc05a889fc9471b07866d16400f85aaee36
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_background_process_execution_v1
selected_process_execution_scope: server_owned_candidate_b_full_corpus_operator_workflow_process_over_existing_execution_boundary_receipt
selected_process_execution_mode: server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority
selected_process_execution_command_authority: repo_allowlisted_python_module_or_script_from_server_config
selected_process_execution_allowlisted_command_family: tools/run_candidate_b_full_corpus_operator_workflow.py
selected_process_execution_arguments_authority: server_resolved_receipt_ids_and_configured_runtime_roots_only
selected_process_execution_outputs: process_execution_receipt,process_execution_receipt_hash,process_execution_authority_hash,redacted_process_status_projection
process_state_values: queued,started,completed,failed,blocked,expired
raw_stdout_admitted_after_sync: false
raw_stderr_admitted_after_sync: false
raw_exception_trace_admitted_after_sync: false
raw_log_excerpt_admitted_after_sync: false
status_history_projection_required_after_process_start: true
rendered_operator_projection_required_after_process_start: true
stale_execution_boundary_must_reject: true
missing_runtime_dependency_must_reject: true
non_allowlisted_command_must_reject: true
process_timeout_must_emit_failed_or_blocked_receipt: true
background_process_runtime_selected_after_sync: true
job_execution_runtime_selected_after_sync: false
actual_subprocess_spawn_admitted_after_sync: true
actual_corpus_processing_execution_admitted_after_sync: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_background_process_execution_v1
```

The selected next slice is a server-owned process-start receipt over the already-proven execution boundary. It must use a server-side allowlist and configured runtime authority, not browser-supplied commands, paths, URLs, runtime roots, selector fields, provider refs, connector destinations, model/RAG controls, or artifact bytes. It may admit a real subprocess start only after the implementation freeze sync, and it must record redacted process status plus timeout/failure receipts without raw stdout, stderr, traces, logs, local roots, or URLs.

### Candidate B Async Background Process Execution Runtime

```yaml
milestone: candidate_b_async_background_process_execution_v1
source_process_execution_selection: next_milestone_plans/Layer3_planning_docs/1028-cb-async-background-process-execution-selection.md
runtime_status: implemented
selected_process_execution_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution
selected_process_execution_mode: server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority
selected_process_execution_action: record_candidate_b_async_background_process_execution
selected_process_execution_allowlisted_command_family: tools/run_candidate_b_full_corpus_operator_workflow.py
selected_process_execution_arguments_authority: server_resolved_receipt_ids_and_configured_runtime_roots_only
selected_process_execution_outputs: process_execution_receipt,process_execution_receipt_hash,process_execution_authority_hash,redacted_process_status_projection
status_history_projection_after_process_start: true
rendered_operator_projection_after_process_start: true
stale_history_row_must_reject: true
stale_execution_boundary_must_reject: true
missing_execution_boundary_must_reject: true
background_process_runtime_selected_now: true
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: true
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
next_exact_posture: candidate_b_async_process_completion_result_adoption_selection_v1
```

Operators can now start only the server-owned allowlisted Candidate B full-corpus operator workflow process after an execution-boundary receipt is visible. The receipt and UI expose a redacted process reference, receipt hashes, and status/history projection; they do not expose raw command lines, local paths, URLs, stdout, stderr, traces, logs, job-completion authority, or result-adoption authority.

### Candidate B Async Process Completion/Result Adoption Selection

```yaml
milestone: candidate_b_async_process_completion_result_adoption_selection_v1
source_process_execution_runtime: next_milestone_plans/Layer3_planning_docs/1029-cb-async-background-process-execution-runtime.md
current_main_entry: 41be8a608ea31a17b5b1cb43ebffcb517a06eeaf
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_process_completion_result_adoption_v1
selected_completion_result_scope: server_owned_candidate_b_full_corpus_operator_workflow_process_result_over_existing_process_execution_receipt
selected_completion_result_mode: append_only_process_completion_result_adoption_receipt_without_source_run_mutation_or_raw_output_exposure
selected_completion_result_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result
selected_completion_result_receipt_model: append_only_receipt_binding_process_execution_receipt_to_validated_operator_workflow_result_receipt
selected_completion_result_receipt_binding: process_execution_receipt_id,process_execution_receipt_hash,process_execution_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,row_hash,authority_basis_hash,history_hash,result_workflow_receipt_id,result_workflow_receipt_hash,result_authority_hash,result_status_request_hash,result_downstream_proof_hash
selected_process_terminal_states: completed,failed,blocked,expired
completed_result_adoption_requires: current_process_execution_receipt,current_history_row,current_execution_boundary_authority,validated_result_workflow_receipt_from_allowlisted_workflow,matching_operator_workflow_lineage,operator_safe_status_request
failed_result_adoption_requires: current_process_execution_receipt,operator_safe_failure_code,operator_safe_failure_phase,redacted_failure_summary_hash
timeout_or_expiry_must_emit_operator_safe_terminal_receipt: true
missing_process_execution_receipt_must_reject: true
stale_process_execution_receipt_must_reject: true
missing_result_receipt_must_reject_for_completed_adoption: true
stale_or_unrelated_result_receipt_must_reject: true
competing_completion_result_receipt_must_reject: true
status_history_projection_required_after_result_adoption: true
rendered_operator_projection_required_after_result_adoption: true
raw_stdout_admitted_after_sync: false
raw_stderr_admitted_after_sync: false
raw_exception_trace_admitted_after_sync: false
raw_log_excerpt_admitted_after_sync: false
raw_local_path_exposed_after_sync: false
raw_url_exposed_after_sync: false
artifact_bytes_exposed_after_sync: false
process_completion_result_runtime_selected_after_sync: true
result_adoption_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
source_run_receipt_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_process_completion_result_adoption_v1
```

The selected next runtime may adopt a terminal process result only from server-validated Candidate B workflow lineage. It must bind the current process-execution receipt, workflow row, execution-boundary authority, and validated result workflow receipt, then project an operator-safe completion/result status. It does not admit browser-supplied completion claims, arbitrary files, raw paths, raw URLs, stdout, stderr, traces, logs, artifact bytes, source-run mutation, provider writes, connector dispatch, model runtime, or broader default scope.

### Candidate B Async Process Completion/Result Adoption Runtime

```yaml
milestone: candidate_b_async_process_completion_result_adoption_v1
source_process_completion_result_selection: next_milestone_plans/Layer3_planning_docs/1030-cb-async-process-completion-result-adoption-selection.md
runtime_status: implemented
selected_completion_result_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result
selected_completion_result_mode: append_only_process_completion_result_adoption_receipt_without_source_run_mutation_or_raw_output_exposure
selected_completion_result_action: record_candidate_b_async_process_completion_result_adoption
completed_result_adoption_requires: current_process_execution_receipt,current_history_row,current_execution_boundary_authority,validated_result_workflow_receipt_from_allowlisted_workflow,matching_operator_workflow_lineage,operator_safe_status_request
status_history_projection_after_result_adoption: true
rendered_operator_projection_after_result_adoption: true
process_completion_result_runtime_selected: true
result_adoption_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
source_run_receipt_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_async_adopted_process_result_downstream_operator_proof_selection_v1
```

Operators can now adopt a terminal process result only after the selected workflow row exposes a started process-execution receipt. Completed adoption must point at a validated Candidate B workflow result receipt from the same lineage; failed, blocked, or expired adoption must use only operator-safe failure code, phase, and summary hash. The browser control cannot provide commands, runtime roots, local paths, raw URLs, stdout, stderr, traces, logs, artifact bytes, provider refs, connector destinations, model/RAG controls, selector mutations, or durable authority.

### Candidate B Async Adopted Process Result Downstream Operator Proof Selection

```yaml
milestone: candidate_b_async_adopted_process_result_downstream_operator_proof_selection_v1
source_process_completion_result_runtime: next_milestone_plans/Layer3_planning_docs/1031-cb-async-process-completion-result-adoption-runtime.md
current_main_entry: e47446b193e94f50de2822a2393d011376278414
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_adopted_process_result_downstream_operator_proof_v1
selected_downstream_proof_mode: read_only_adopted_process_result_downstream_operator_proof_without_result_mutation_or_reexecution
selected_downstream_proof_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof
selected_downstream_proof_action: record_candidate_b_async_adopted_process_result_downstream_operator_proof
selected_downstream_proof_receipt_model: append_only_receipt_binding_process_completion_result_receipt_to_validated_adopted_result_status_and_downstream_proof
completed_process_result_required: true
failed_blocked_or_expired_process_result_must_reject: true
adopted_result_status_request_revalidation_required: true
adopted_result_downstream_proof_status_required: proven
missing_process_completion_result_receipt_must_reject: true
stale_process_completion_result_receipt_must_reject: true
stale_or_unrelated_adopted_result_status_must_reject: true
unproven_downstream_result_must_reject: true
competing_adopted_result_downstream_proof_receipt_must_reject: true
status_history_projection_required_after_downstream_proof: true
rendered_operator_projection_required_after_downstream_proof: true
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
raw_stdout_admitted_after_sync: false
raw_stderr_admitted_after_sync: false
raw_local_path_exposed_after_sync: false
raw_url_exposed_after_sync: false
artifact_bytes_exposed_after_sync: false
process_completion_result_receipt_mutation_admitted: false
adopted_result_workflow_receipt_mutation_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_async_adopted_process_result_downstream_operator_proof_v1
```

The next selected runtime should prove that an adopted completed process result is downstream-usable by revalidating its stored result status request and existing downstream proof. It should not re-run Candidate B, replay Layer 3, mutate any source/result receipt, expose raw process output, or broaden source/provider/connector/RAG/model/full-mockup/default scope.

### Candidate B Async Adopted Process Result Downstream Operator Proof Runtime

```yaml
milestone: candidate_b_async_adopted_process_result_downstream_operator_proof_v1
source_adopted_process_result_downstream_proof_selection: next_milestone_plans/Layer3_planning_docs/1032-cb-async-adopted-process-result-downstream-proof-selection.md
current_main_entry: 516807d78a2f4a87e2931e86bdf967cd0773f1fd
runtime_status: implemented
selected_downstream_proof_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof
selected_downstream_proof_mode: read_only_adopted_process_result_downstream_operator_proof_without_result_mutation_or_reexecution
selected_downstream_proof_action: record_candidate_b_async_adopted_process_result_downstream_operator_proof
completed_process_result_required: true
adopted_result_status_request_revalidation_required: true
adopted_result_downstream_proof_status_required: proven
status_history_projection_after_downstream_proof: true
rendered_operator_projection_after_downstream_proof: true
adopted_result_downstream_proof_runtime_selected: true
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
process_completion_result_receipt_mutation_admitted: false
adopted_result_workflow_receipt_mutation_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_async_operator_workflow_completion_monitor_selection_v1
```

Operators can now prove that an adopted completed process result is still downstream-usable without rerunning Candidate B or Layer 3. The server writes an append-only proof receipt only after reloading the process-completion/result receipt, revalidating its stored adopted-result status request, and confirming the adopted result's downstream proof remains proven. The browser control cannot provide commands, runtime roots, local paths, raw URLs, stdout, stderr, traces, logs, artifact bytes, provider refs, connector destinations, model/RAG controls, selector mutations, or durable authority.

### Candidate B Async Operator Workflow Completion Monitor Selection

```yaml
milestone: candidate_b_async_operator_workflow_completion_monitor_selection_v1
source_adopted_process_result_downstream_runtime: next_milestone_plans/Layer3_planning_docs/1033-cb-async-adopted-process-result-downstream-proof-runtime.md
current_main_entry: 6c626e70a3a3690bd9b9343d136780e85a9534f4
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_operator_workflow_completion_monitor_v1
selected_completion_monitor_scope: server_owned_read_only_completion_monitor_over_candidate_b_async_operator_workflow_receipts
selected_completion_monitor_mode: read_only_operator_workflow_completion_monitor_without_process_control_result_mutation_or_reexecution
selected_completion_monitor_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor
selected_completion_monitor_action: inspect_candidate_b_async_operator_workflow_completion_monitor
selected_completion_monitor_projection_model: read_only_projection_binding_process_execution_receipt_to_terminal_result_adoption_and_downstream_proof_status
selected_completion_monitor_states: not_started,started_status_unknown,started_running_or_unresolved,completed_result_adopted,completed_downstream_proven,failed,blocked,expired,stale_authority,monitor_unavailable
process_execution_projection_required: true
process_completion_result_projection_if_present_required: true
adopted_result_downstream_proof_projection_if_present_required: true
retry_terminal_status_projection_if_present_required: true
missing_process_execution_receipt_must_reject_for_started_monitor: true
stale_process_execution_receipt_must_reject: true
stale_or_unrelated_completion_result_must_reject: true
stale_or_unrelated_downstream_proof_must_reject: true
contradictory_terminal_state_must_reject: true
competing_terminal_receipts_must_reject: true
status_history_projection_required_after_completion_monitor: true
rendered_operator_projection_required_after_completion_monitor: true
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
process_completion_result_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_pid_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_async_operator_workflow_completion_monitor_v1
```

The next selected runtime should provide a read-only operator completion monitor over existing Candidate B workflow receipts and projections. It should answer whether the workflow has started, whether terminal process-result adoption exists, and whether an adopted completed result is downstream-proven, without controlling processes, rerunning Candidate B, mutating receipts, or exposing raw process output or local authority.

### Candidate B Async Operator Workflow Completion Monitor Runtime

```yaml
milestone: candidate_b_async_operator_workflow_completion_monitor_v1
source_completion_monitor_selection: next_milestone_plans/Layer3_planning_docs/1034-cb-async-operator-workflow-completion-monitor-selection.md
current_main_entry: 105ce59c299a7c01fd53cd249450a7a4ee99e1b1
runtime_status: implemented
selected_completion_monitor_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor
selected_completion_monitor_mode: read_only_operator_workflow_completion_monitor_without_process_control_result_mutation_or_reexecution
selected_completion_monitor_action: inspect_candidate_b_async_operator_workflow_completion_monitor
selected_completion_monitor_states: not_started,started_status_unknown,started_running_or_unresolved,completed_result_adopted,completed_downstream_proven,failed,blocked,expired,stale_authority,monitor_unavailable
process_execution_projection_required: true
process_completion_result_projection_if_present_required: true
adopted_result_downstream_proof_projection_if_present_required: true
stale_projection_binding_rejects: true
contradictory_terminal_state_rejects: true
completion_without_started_process_rejects: true
status_history_projection_after_completion_monitor: true
rendered_operator_projection_after_completion_monitor: true
completion_monitor_runtime_selected: true
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
process_completion_result_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_pid_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_selection_v1
```

Operators can now inspect the server-owned completion state of a Candidate B full-corpus workflow row without controlling processes or mutating result authority. The monitor projects not-started, running/unresolved, adopted-result, downstream-proven, and terminal failure/blocked/expired states from existing governed receipts only.

### Candidate B Full-Corpus Operator Repeatability Checkpoint Selection

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_selection_v1
source_completion_monitor_runtime: next_milestone_plans/Layer3_planning_docs/1035-cb-async-operator-workflow-completion-monitor-runtime.md
prior_repeatability_completion_audit: next_milestone_plans/Layer3_planning_docs/989-cb-repeatability-completion-audit.md
current_main_entry: 89682c0dd533977bdd13e5e18f6fa34f757a8002
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_operator_repeatability_checkpoint_v1
selected_repeatability_checkpoint_scope: append_only_operator_repeatability_checkpoint_over_server_owned_candidate_b_workflow_receipts
selected_repeatability_checkpoint_mode: append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
selected_repeatability_checkpoint_model: bind_workflow_history_status_completion_monitor_and_downstream_receipts_to_repeatability_checkpoint
historical_repeatability_completion_audit_remains_valid: true
post_monitor_repeatability_checkpoint_required: true
completion_monitor_state_required: completed_downstream_proven
workflow_history_row_required: true
workflow_status_projection_required: true
completion_monitor_projection_required: true
stale_history_hash_must_reject: true
stale_row_hash_must_reject: true
stale_workflow_status_must_reject: true
stale_completion_monitor_must_reject: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_pid_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_v1
```

This freeze selects the post-monitor repeatability checkpoint without implementing it. The next runtime should write a single append-only checkpoint receipt over the current server-owned workflow row, status projection, completion monitor projection, runtime-root lifecycle receipt, bridge receipt, downstream proof, compare target set, and operator runbook repeatability steps. It must not rerun Candidate B or Layer 3, control processes, mutate existing receipts, accept raw local paths or URLs, expose raw process output, or broaden provider/connector/RAG/model/full-mockup/default scope.

### Candidate B Full-Corpus Operator Repeatability Checkpoint Runtime

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_v1
source_repeatability_checkpoint_selection: next_milestone_plans/Layer3_planning_docs/1036-cb-repeatability-checkpoint-selection.md
current_main_entry: 194fd3c3bd225736869c4152b9e1e0d6d9859763
runtime_status: implemented
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_mode: append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
selected_repeatability_checkpoint_model: bind_workflow_history_status_completion_monitor_and_downstream_receipts_to_repeatability_checkpoint
repeatability_checkpoint_runtime_selected: true
append_only_repeatability_checkpoint_receipt: true
exclusive_repeatability_checkpoint_per_authority: true
workflow_history_row_required: true
workflow_status_projection_required: true
workflow_status_required: proven
completion_monitor_projection_required: true
completion_monitor_state_required: completed_downstream_proven
runtime_root_lifecycle_receipt_required: true
bridge_receipt_required: true
downstream_proof_required: true
baseline_run_id_required: true
candidate_a_run_id_required: true
candidate_b_run_id_required: true
compare_target_set_hash_required: true
material_relative_name_required: true
operator_runbook_repeatability_steps_required: true
stale_history_hash_rejects: true
stale_row_hash_rejects: true
stale_workflow_status_rejects: true
stale_completion_monitor_rejects: true
non_downstream_proven_monitor_rejects: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
raw_pid_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_selection_v1
```

Operators can now record a repeatability checkpoint receipt for a downstream-proven Candidate B async operator workflow without rerunning corpus processing, controlling a process, or mutating prior receipts. The request supplies hashes and receipt ids; the server reloads workflow history, status, and completion-monitor authority and rejects stale, missing, mismatched, non-downstream-proven, or raw-leaking inputs.

### Candidate B Full-Corpus Operator Repeatability Checkpoint Rendered Control Selection

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_selection_v1
source_repeatability_checkpoint_runtime: next_milestone_plans/Layer3_planning_docs/1037-cb-repeatability-checkpoint-runtime.md
current_main_entry: 349fb54afc70a86b3339718d1d18f35801211eef
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_v1
selected_rendered_control_scope: server_projection_consumer_for_candidate_b_repeatability_checkpoint_receipts
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
selected_rendered_control_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint_from_current_history_status_and_completion_monitor_projection
selected_rendered_control_model: per_workflow_history_row_button_enabled_only_when_status_and_completion_monitor_projection_are_current_and_downstream_proven
existing_history_panel_reused: true
existing_status_projection_reused: true
existing_completion_monitor_projection_reused: true
rendered_control_button_label: Record Repeatability Checkpoint
headless_rendered_proof_required: true
headed_rendered_proof_required: true
stale_status_or_completion_monitor_must_disable_or_fail_closed: true
non_downstream_proven_completion_monitor_must_disable_or_fail_closed: true
browser_supplied_local_authority_admitted: false
browser_supplied_raw_url_admitted: false
browser_supplied_command_admitted: false
browser_supplied_process_control_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_v1
```

The next rendered pass should add the operator control that records the already admitted repeatability checkpoint. It should reuse current workflow history, workflow status, and completion-monitor projections; submit only receipt ids/hashes and bounded runbook step constants; and prove headed/headless rendered behavior without giving the browser durable authority.

### Candidate B Full-Corpus Operator Repeatability Checkpoint Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_v1
source_repeatability_checkpoint_rendered_selection: next_milestone_plans/Layer3_planning_docs/1038-cb-repeatability-checkpoint-rendered-selection.md
current_main_entry: e216becebf2745a976e6b92a1b57b1907bc0b939
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_operator_repeatability_checkpoint_control
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
rendered_control_runtime_selected: true
rendered_control_button_label: Record Repeatability Checkpoint
history_status_completion_monitor_projection_required: true
workflow_status_required: proven
completion_monitor_state_required: completed_downstream_proven
runtime_root_lifecycle_receipt_required: true
bridge_receipt_required: true
downstream_proof_required: true
operator_runbook_repeatability_steps_required: true
stale_status_or_completion_monitor_disables_or_fails_closed: true
non_downstream_proven_monitor_disables_or_fails_closed: true
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability checkpoint" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability checkpoint" --project=chromium --headed PASS
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_selection_v1
```

Operators can now refresh Candidate B workflow history, inspect a selected run status, inspect the completion monitor, and record the repeatability checkpoint through rendered controls. The checkpoint control is a projection consumer only: it posts receipt ids, hashes, run ids, material identity, and fixed runbook step constants to the server-owned repeatability checkpoint endpoint. It stays disabled or fails closed when workflow status is not proven, completion monitor is not downstream-proven, or the selected history/status/monitor projections do not bind to the same row.

### Candidate B Full-Corpus Repeatability Rerun Trial Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_selection_v1
source_repeatability_checkpoint_rendered_runtime: next_milestone_plans/Layer3_planning_docs/1039-cb-repeatability-checkpoint-rendered-runtime.md
current_main_entry: 963774f0545917dd9ae0e5cc7bdba35cb84012db
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_rerun_trial_v1
selected_repeatability_trial_scope: compare_two_server_owned_candidate_b_full_corpus_operator_workflows_for_same_eligible_pdf_corpus
selected_repeatability_trial_model: append_only_trial_receipt_over_original_checkpoint_and_second_downstream_proven_workflow
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
original_repeatability_checkpoint_required: true
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
same_compare_target_set_hash_required: true
artifact_family_hash_comparison_required: true
layer3_downstream_projection_comparison_required: true
regression_or_delta_disposition_required: true
append_only_repeatability_trial_receipt_required: true
stale_original_checkpoint_must_reject: true
stale_rerun_status_or_monitor_must_reject: true
mismatched_corpus_identity_must_reject: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
actual_corpus_processing_execution_admitted_by_trial_endpoint: false
actual_subprocess_spawn_admitted_by_trial_endpoint: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_v1
```

The next runtime should compare an original checkpointed workflow with a second downstream-proven Candidate B workflow for the same eligible PDF corpus. It should write only an append-only repeatability trial receipt. The trial endpoint must not spawn or control the rerun process; the second workflow must be produced through existing server-owned workflow-run authority before the trial comparator records repeatability evidence.

### Candidate B Full-Corpus Repeatability Rerun Trial Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_v1
source_repeatability_rerun_trial_selection: next_milestone_plans/Layer3_planning_docs/1040-cb-repeatability-rerun-trial-selection.md
runtime_status: implemented_branch_local
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
selected_repeatability_trial_mode: append_only_repeatability_rerun_trial_receipt_without_process_execution_or_authority_mutation
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
repeatability_rerun_trial_runtime_selected: true
original_repeatability_checkpoint_required: true
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
same_compare_target_set_hash_required: true
artifact_family_hash_comparison_required: true
layer3_downstream_projection_comparison_required: true
retained_artifact_role_counts_comparison_required: true
regression_or_delta_disposition_required: true
append_only_repeatability_rerun_trial_receipt: true
stale_original_checkpoint_rejects: true
stale_rerun_status_or_monitor_rejects: true
mismatched_corpus_identity_rejects: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_selection_v1
```

Operators can now record repeatability evidence for two independently produced, downstream-proven Candidate B full-corpus workflows. The endpoint compares server-owned original-checkpoint, original-status, original-monitor, rerun-status, and rerun-monitor authority; it writes an append-only rerun-trial receipt and does not execute Candidate B, spawn subprocesses, control processes, expose raw stdout/stderr, or accept raw local paths or URLs from the browser.

### Candidate B Full-Corpus Repeatability Rerun Trial Rendered Control Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_selection_v1
source_repeatability_rerun_trial_runtime: next_milestone_plans/Layer3_planning_docs/1041-cb-repeatability-rerun-trial-runtime.md
current_main_entry: 2a10ca531a36a89b23da740056df5fa5608c8150
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_v1
selected_rendered_control_scope: server_projection_consumer_for_candidate_b_repeatability_rerun_trial_receipts
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
selected_rendered_control_action: record_candidate_b_full_corpus_repeatability_rerun_trial_from_current_original_checkpoint_and_rerun_workflow_projection
rendered_control_button_label: Record Rerun Trial
headless_rendered_proof_required: true
headed_rendered_proof_required: true
original_repeatability_checkpoint_required: true
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
stale_original_checkpoint_must_disable_or_fail_closed: true
stale_rerun_status_or_monitor_must_disable_or_fail_closed: true
mismatched_corpus_identity_must_disable_or_fail_closed: true
regression_or_delta_disposition_required: true
browser_supplied_local_authority_admitted: false
browser_supplied_raw_url_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_v1
```

The next rendered pass should add the operator control for recording a rerun-trial receipt. The UI may pair an original repeatability checkpoint with a second downstream-proven workflow and choose an admitted regression/delta disposition, but it remains a server-projection consumer only. It must post bounded ids/hashes and runbook constants to the server endpoint, then render the server comparison and receipt without local paths, raw URLs, commands, stdout/stderr, process controls, browser storage authority, or frontend durable authority.

### Candidate B Full-Corpus Repeatability Rerun Trial Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_v1
source_repeatability_rerun_trial_rendered_selection: next_milestone_plans/Layer3_planning_docs/1042-cb-repeatability-rerun-trial-rendered-selection.md
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_rerun_trial_control
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
rendered_control_runtime_selected: true
rendered_control_button_label: Record Rerun Trial
original_repeatability_checkpoint_required: true
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
artifact_family_hash_comparison_required: true
layer3_downstream_projection_comparison_required: true
retained_artifact_role_counts_comparison_required: true
regression_or_delta_disposition_required: true
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial" --project=chromium --headed PASS
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_checkpoint_selection_v1
```

Operators can now record the repeatability rerun-trial receipt through the rendered Candidate B workflow history/status/monitor surface. The sequence is: refresh workflow history, inspect the original workflow status and completion monitor, record the original repeatability checkpoint, inspect the rerun workflow status and completion monitor, then click `Record Rerun Trial` on the rerun row. The rendered control submits only server-projected ids, hashes, material identity, the admitted disposition, and bounded runbook constants; the server writes the receipt and returns the comparison summary and negative invariants.

### Candidate B Full-Corpus Repeatability Acceptance Checkpoint Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_checkpoint_selection_v1
source_repeatability_rerun_trial_rendered_runtime: next_milestone_plans/Layer3_planning_docs/1043-cb-repeatability-rerun-trial-rendered-runtime.md
current_main_entry: 49875df0079e79984877f27fabbc38e9b38ec57a
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_checkpoint_v1
selected_acceptance_checkpoint_scope: append_only_operator_acceptance_checkpoint_over_original_repeatability_checkpoint_and_rerun_trial_receipts
selected_acceptance_checkpoint_mode: append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
rerun_trial_state_required: repeatability_rerun_trial_recorded
same_eligible_corpus_identity_required: true
same_compare_target_set_hash_required: true
same_material_relative_name_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
acceptance_checkpoint_receipt_required: true
stale_original_checkpoint_must_reject: true
stale_rerun_trial_must_reject: true
mismatched_corpus_identity_must_reject: true
regression_detected_must_block_acceptance: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_checkpoint_v1
```

This freeze selects the post-rerun acceptance checkpoint without implementing it. The next runtime should write a single append-only acceptance receipt over the original repeatability checkpoint, the rerun-trial receipt, the comparison summary, the operator acceptance decision, and bounded runbook steps. It must accept only `no_regression_observed` or `delta_reviewed_no_regression`, block `regression_detected_blocked`, and preserve baseline rollback, Candidate A semantics, Candidate B eligible-PDF scope, redaction, no process control, no provider/connector/model expansion, and no frontend durable authority.

### Candidate B Full-Corpus Repeatability Acceptance Checkpoint Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_checkpoint_v1
source_repeatability_acceptance_checkpoint_selection: next_milestone_plans/Layer3_planning_docs/1044-cb-repeatability-acceptance-checkpoint-selection.md
current_main_entry: a928e288ee3a5aa32ad0a43a3ebe7eab11588caa
runtime_status: implemented
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_mode: append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
repeatability_acceptance_checkpoint_runtime_selected: true
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_block_acceptance: true
append_only_repeatability_acceptance_checkpoint_receipt: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
focused_pytest: py -3.12 -m pytest .\backend\tests\test_layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint.py -q PASS
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_rendered_control_selection_v1
```

Operators can now record a server-owned acceptance checkpoint after an original repeatability checkpoint and rerun-trial receipt exist. The endpoint revalidates the original checkpoint, rerun-trial receipt, workflow statuses, completion monitors, and comparison disposition before writing the append-only acceptance receipt. It accepts only `no_regression_observed` or `delta_reviewed_no_regression`; `regression_detected_blocked` fails closed and blocks acceptance.

### Candidate B Full-Corpus Repeatability Acceptance Rendered Control Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_rendered_control_selection_v1
source_repeatability_acceptance_checkpoint_runtime: next_milestone_plans/Layer3_planning_docs/1045-cb-repeatability-acceptance-checkpoint-runtime.md
current_main_entry: 4d8bf45430f87c59926588e6525af90fadac3a4f
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_rendered_control_v1
selected_rendered_control_scope: server_projection_consumer_for_candidate_b_repeatability_acceptance_checkpoint_receipts
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
selected_rendered_control_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint_from_current_checkpoint_and_rerun_trial_projection
rendered_control_button_label: Record Acceptance Checkpoint
headless_rendered_proof_required: true
headed_rendered_proof_required: true
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
rerun_trial_state_required: repeatability_rerun_trial_recorded
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_disable_or_fail_closed: true
stale_original_checkpoint_must_disable_or_fail_closed: true
stale_rerun_trial_must_disable_or_fail_closed: true
mismatched_corpus_identity_must_disable_or_fail_closed: true
browser_supplied_local_authority_admitted: false
browser_supplied_raw_url_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_rendered_control_v1
```

The next rendered pass should add the operator control for recording the final acceptance-checkpoint receipt. The UI may consume existing workflow history, status, completion-monitor, repeatability-checkpoint, and rerun-trial projections, but it remains a server-projection consumer only. It must post bounded ids/hashes, material identity, admitted disposition, operator decision, and runbook constants to the server endpoint, then render the server acceptance receipt without local paths, raw URLs, commands, stdout/stderr, process controls, browser storage authority, or frontend durable authority.

### Candidate B Full-Corpus Repeatability Acceptance Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_rendered_control_v1
source_repeatability_acceptance_rendered_selection: next_milestone_plans/Layer3_planning_docs/1046-cb-repeatability-acceptance-rendered-selection.md
current_main_entry: 35113ed4ba52f9193c21f45737ba0b1e79165ab5
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_acceptance_checkpoint_control
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
rendered_control_runtime_selected: true
rendered_control_button_label: Record Acceptance Checkpoint
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
rerun_trial_state_required: repeatability_rerun_trial_recorded
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
same_eligible_corpus_identity_required: true
same_compare_target_set_hash_required: true
same_material_relative_name_required: true
same_runtime_root_lifecycle_policy_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_disable_or_fail_closed: true
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial" --project=chromium --headed PASS
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_operator_closeout_selection_v1
```

Operators can now record the final repeatability acceptance-checkpoint receipt through rendered controls after a current original checkpoint and non-regression rerun-trial receipt exist. The control remains a server-projection consumer: it submits bounded receipt ids/hashes, status/monitor hashes, accepted disposition, operator decision, and runbook constants to the server acceptance endpoint, then renders the server receipt and negative invariants without path, URL, process, provider, connector, model, full-mockup, default-scope, or frontend durable-authority expansion.

### Candidate B Full-Corpus Repeatability Acceptance Operator Closeout Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_operator_closeout_selection_v1
source_repeatability_acceptance_rendered_runtime: next_milestone_plans/Layer3_planning_docs/1047-cb-repeatability-acceptance-rendered-runtime.md
current_main_entry: b36cb9a8b168e09c460590d8faac5a68398b054a
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_operator_closeout_v1
selected_closeout_scope: server_owned_operator_closeout_receipt_over_accepted_candidate_b_full_corpus_repeatability_evidence
selected_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
selected_closeout_action: record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
repeatability_acceptance_checkpoint_receipt_required: true
acceptance_checkpoint_state_required: repeatability_acceptance_checkpoint_recorded
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_block_closeout: true
rendered_acceptance_control_proof_required: true
headed_and_headless_rendered_proof_required: true
operator_runbook_closeout_steps_required: true
full_corpus_workflow_history_status_monitor_chain_required: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_operator_closeout_v1
```

The next runtime should close out the accepted repeatability chain by writing one append-only operator closeout receipt over server-owned workflow history/status/monitor projections, original checkpoint, rerun-trial receipt, acceptance-checkpoint receipt, headed/headless rendered proof labels, and bounded runbook closeout steps. It should not rerun Candidate B or Layer 3, mutate prior receipts, broaden Candidate B default scope, expose raw paths/URLs/output, or add process/provider/connector/model/full-mockup/frontend durable authority.

### Candidate B Full-Corpus Repeatability Acceptance Operator Closeout Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_operator_closeout_v1
source_repeatability_acceptance_closeout_selection: next_milestone_plans/Layer3_planning_docs/1048-cb-repeatability-acceptance-closeout-selection.md
current_main_entry: 894c82f70ddcd79cf3ef5976f1696eb279777078
runtime_status: implemented
selected_closeout_scope: server_owned_operator_closeout_receipt_over_accepted_candidate_b_full_corpus_repeatability_evidence
implemented_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
implemented_service: backend/app/services/layer3_candidate_b_full_corpus_repeatability_acceptance_closeout.py
implemented_api_route: backend/app/api/layer3.py
repeatability_acceptance_checkpoint_receipt_required: true
acceptance_checkpoint_state_required: repeatability_acceptance_checkpoint_recorded
original_repeatability_checkpoint_revalidated: true
repeatability_rerun_trial_receipt_revalidated: true
full_corpus_workflow_history_status_monitor_chain_revalidated: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_block_closeout: true
rendered_acceptance_control_proof_state_required: headed_and_headless_passed
operator_runbook_closeout_steps_required: true
negative_invariants_bound: true
append_only_closeout_receipt: true
exclusive_closeout_receipt_per_authority: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_control_selection_v1
```

Operators can now record a server-owned closeout receipt after the final acceptance checkpoint is available. The closeout reloads and revalidates the accepted checkpoint chain, requires headed and headless rendered acceptance proof labels, records bounded closeout runbook steps, binds the negative invariant set, and writes its own append-only receipt without mutating the checkpoint, rerun-trial, workflow, process, completion, or downstream-proof receipts.

### Candidate B Full-Corpus Repeatability Acceptance Closeout Rendered Control Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_control_selection_v1
source_repeatability_acceptance_closeout_runtime: next_milestone_plans/Layer3_planning_docs/1049-cb-repeatability-acceptance-closeout-runtime.md
current_main_entry: e49f954bbb3c8e28c9b8a62487f3d0a993390787
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_control_v1
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control
selected_rendered_control_scope: operator_visible_record_and_inspect_acceptance_closeout_receipt
selected_rendered_control_button_label: Record Acceptance Closeout
source_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
selected_closeout_action: record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout
repeatability_acceptance_checkpoint_receipt_required: true
acceptance_checkpoint_state_required: repeatability_acceptance_checkpoint_recorded
acceptance_closeout_state_required_after_submit: repeatability_acceptance_operator_closeout_recorded
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_disable_or_fail_closed: true
rendered_acceptance_control_proof_state_submitted: headed_and_headless_passed
operator_runbook_closeout_steps_submitted: true
negative_invariant_attestations_submitted: true
server_owned_closeout_receipt_required: true
append_only_closeout_receipt_required: true
closeout_receipt_ref_rendered_redacted: true
raw_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
raw_stdout_rendered: false
raw_stderr_rendered: false
artifact_bytes_rendered: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_control_v1
```

The next runtime should add a rendered `Record Acceptance Closeout` control that posts only bounded server receipt/hash evidence, admitted proof labels, runbook constants, and negative invariant attestations to the closeout endpoint. It should render the server closeout state and redacted receipt reference without raw filesystem paths, raw URLs, stdout/stderr, artifact bytes, process control, provider/connector/model expansion, default-scope expansion, full mockup activation, browser-storage authority, or frontend durable authority.

### Candidate B Full-Corpus Repeatability Acceptance Closeout Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_control_v1
source_repeatability_acceptance_closeout_rendered_selection: next_milestone_plans/Layer3_planning_docs/1050-cb-repeatability-acceptance-closeout-rendered-selection.md
current_main_entry: e098ee10223f6f6edac6c6026ae4d26bad88cfeb
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control
rendered_control_button_label: Record Acceptance Closeout
source_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
selected_closeout_action: record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout
repeatability_acceptance_checkpoint_receipt_required: true
acceptance_checkpoint_state_required: repeatability_acceptance_checkpoint_recorded
acceptance_closeout_state_required_after_submit: repeatability_acceptance_operator_closeout_recorded
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_disable_or_fail_closed: true
rendered_acceptance_control_proof_state_submitted: headed_and_headless_passed
operator_runbook_closeout_steps_submitted: true
negative_invariant_attestations_submitted: true
server_owned_closeout_receipt_required: true
append_only_closeout_receipt_required: true
closeout_receipt_ref_rendered_redacted: true
raw_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
raw_stdout_rendered: false
raw_stderr_rendered: false
artifact_bytes_rendered: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium --headed PASS
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_status_selection_v1
```

Operators can now click `Record Acceptance Closeout` after the acceptance checkpoint is recorded. The browser posts only bounded server receipt/hash evidence, proof labels, runbook constants, and negative invariant attestations. The server remains durable authority for the closeout receipt, and the rendered response stays redacted.

### Candidate B Full-Corpus Repeatability Acceptance Closeout Status Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_status_selection_v1
source_repeatability_acceptance_closeout_rendered_runtime: next_milestone_plans/Layer3_planning_docs/1051-cb-repeatability-acceptance-closeout-rendered-runtime.md
current_main_entry: 470cac93ddace9c212ad2cd3557b7b0174e015bb
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_closeout_status_v1
selected_closeout_status_scope: server_owned_read_only_status_review_projection_of_persisted_acceptance_closeout_receipts
selected_closeout_status_mode: read_only_acceptance_closeout_status_without_receipt_creation_lineage_mutation_or_frontend_authority
selected_closeout_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status
source_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
selected_closeout_status_binding: repeatability_acceptance_operator_closeout_receipt_id,repeatability_acceptance_operator_closeout_receipt_hash,repeatability_acceptance_operator_closeout_hash,repeatability_acceptance_operator_closeout_authority_hash,repeatability_acceptance_checkpoint_receipt_id,repeatability_acceptance_checkpoint_receipt_hash,repeatability_acceptance_checkpoint_authority_hash,original_repeatability_checkpoint_receipt_id,repeatability_rerun_trial_receipt_id,original_operator_workflow_receipt_id,rerun_operator_workflow_receipt_id,baseline_run_id,candidate_a_run_id,original_candidate_b_run_id,rerun_candidate_b_run_id,compare_target_set_hash,material_relative_name,acceptance_disposition,comparison_hash,negative_invariants_hash,rendered_acceptance_control_proof_state
closeout_status_values: not_recorded,available,blocked
missing_closeout_receipt_projects_not_recorded: true
stale_closeout_receipt_must_reject: true
ambiguous_closeout_receipt_must_reject: true
closeout_status_projection_must_be_redacted: true
acceptance_closeout_receipt_creation_admitted_now: false
acceptance_closeout_receipt_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_status_v1
```

The next runtime should add a read-only closeout status/review projection over persisted acceptance-closeout receipts. It should report `not_recorded` when no closeout exists, `available` when current closeout authority is present, and fail closed for stale, contradictory, or ambiguous closeout receipts. It must not create or mutate receipts, re-run Candidate B or Layer 3, expose raw paths/URLs/output/artifact bytes, or admit provider, connector, RAG/model, full mockup, default-scope, browser-storage, or frontend durable authority.

### Candidate B Full-Corpus Repeatability Acceptance Closeout Status Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_status_v1
source_repeatability_acceptance_closeout_status_selection: next_milestone_plans/Layer3_planning_docs/1052-cb-repeatability-acceptance-closeout-status-selection.md
current_main_entry: 030a4934fb0b37cbcf9890121b7fe18fb003f3a7
runtime_status: implemented
implemented_closeout_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status
implemented_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
implemented_bootstrap_readiness: true
selected_closeout_status_mode: read_only_acceptance_closeout_status_without_receipt_creation_lineage_mutation_or_frontend_authority
closeout_status_values: not_recorded,available,blocked
missing_closeout_receipt_projects_not_recorded: true
available_closeout_receipt_projects_available: true
stale_closeout_receipt_rejected: true
ambiguous_closeout_receipt_rejected: true
closeout_status_projection_must_be_redacted: true
closeout_receipt_ref_rendered_redacted: true
closeout_status_negative_invariants_visible: true
closeout_status_comparison_summary_visible: true
closeout_status_rendered_proof_summary_visible: true
acceptance_closeout_api_rendered_mode_literal_fixed: rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control
acceptance_closeout_receipt_creation_admitted_now: false
acceptance_closeout_receipt_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
focused_service_proof: python -m pytest .\backend\tests\test_layer3_candidate_b_full_corpus_repeatability_acceptance_closeout.py PASS
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_status_selection_v1
```

The status endpoint is read-only. It can inspect an explicit closeout receipt or scan for a closeout receipt bound to a selected acceptance-checkpoint receipt. It returns `not_recorded` when no closeout receipt exists, `available` when current closeout authority exists, and rejects stale or ambiguous authority without mutating any repeatability, workflow, process, provider, connector, model, or default-selector state.

### Candidate B Full-Corpus Repeatability Acceptance Closeout Rendered Status Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_status_selection_v1
source_repeatability_acceptance_closeout_status_runtime: next_milestone_plans/Layer3_planning_docs/1053-cb-repeatability-acceptance-closeout-status-runtime.md
current_main_entry: eadad722ab4c2256ef3621b040c673e6d85f1bce
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_status_v1
selected_rendered_closeout_status_scope: operator_visible_read_only_status_review_projection_of_acceptance_closeout_status
selected_rendered_closeout_status_mode: rendered_read_only_acceptance_closeout_status_without_receipt_creation_lineage_mutation_or_frontend_authority
selected_rendered_status_control_target: rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_status_control
selected_rendered_status_surfaces: status,history,review
existing_status_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status
existing_closeout_endpoint_reused_for_recording: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
existing_rendered_closeout_control_reused: candidate-b-repeatability-acceptance-closeout-submit
existing_rendered_closeout_card_reused: candidate-b-full-corpus-repeatability-acceptance-closeout-card
selected_rendered_status_fields: repeatability_acceptance_operator_closeout_receipt_id,repeatability_acceptance_operator_closeout_receipt_hash,repeatability_acceptance_operator_closeout_hash,repeatability_acceptance_operator_closeout_authority_hash,repeatability_acceptance_checkpoint_receipt_id,repeatability_acceptance_checkpoint_receipt_hash,repeatability_acceptance_checkpoint_authority_hash,original_repeatability_checkpoint_receipt_id,repeatability_rerun_trial_receipt_id,original_operator_workflow_receipt_id,rerun_operator_workflow_receipt_id,baseline_run_id,candidate_a_run_id,original_candidate_b_run_id,rerun_candidate_b_run_id,compare_target_set_hash,material_relative_name,acceptance_disposition,comparison_hash,negative_invariants_hash,rendered_acceptance_control_proof_state,closeout_status_state
closeout_status_values_rendered: not_recorded,available,blocked
missing_closeout_receipt_renders_not_recorded: true
available_closeout_receipt_renders_available: true
stale_closeout_receipt_must_fail_closed: true
ambiguous_closeout_receipt_must_fail_closed: true
redacted_closeout_receipt_ref_required: true
raw_local_path_rendered: false
raw_url_rendered: false
artifact_bytes_rendered: false
acceptance_closeout_receipt_creation_admitted_now: false
acceptance_closeout_receipt_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
headless_rendered_status_proof_required: true
headed_rendered_status_proof_required: true
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_status_v1
```

The next rendered runtime should add a read-only status/review projection over the existing closeout status endpoint. It should display `not_recorded`, `available`, or server-blocked status without creating closeout receipts, mutating lineage, re-running Candidate B or Layer 3, exposing raw paths/URLs/output/artifact bytes, or admitting provider, connector, RAG/model, full mockup, default-scope, browser-storage, or frontend durable authority.

### Candidate B Full-Corpus Repeatability Acceptance Closeout Rendered Status Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_status_v1
source_repeatability_acceptance_closeout_rendered_status_selection: next_milestone_plans/Layer3_planning_docs/1054-cb-repeatability-acceptance-closeout-rendered-status-selection.md
current_main_entry: a1eb838a7fc9338ee94f7612dc7dbb33057cb53a
runtime_status: implemented
implemented_rendered_status_control: rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_status_control
implemented_status_button: candidate-b-repeatability-acceptance-closeout-status-submit
implemented_rendered_status_surface: candidate-b-full-corpus-repeatability-acceptance-closeout-card
implemented_static_runtime: backend/app/review_ui/static/layer3.js
implemented_rendered_proof: e2e/layer3-workbench.spec.js
existing_status_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status
status_api_mode: read_only_acceptance_closeout_status_without_receipt_creation_lineage_mutation_or_frontend_authority
status_operator_decision: inspect_candidate_b_full_corpus_repeatability_acceptance_closeout_status
closeout_status_values_rendered: not_recorded,available,blocked
missing_closeout_receipt_renders_not_recorded: true
available_closeout_receipt_renders_available: true
status_can_use_acceptance_checkpoint_receipt: true
status_can_use_closeout_receipt: true
status_payload_excludes_raw_paths_urls_and_artifact_bytes: true
redacted_closeout_receipt_ref_required: true
raw_local_path_rendered: false
raw_url_rendered: false
artifact_bytes_rendered: false
acceptance_closeout_receipt_creation_admitted_now: false
acceptance_closeout_receipt_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
headless_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium PASS
headed_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium --headed PASS
next_exact_posture: candidate_b_full_corpus_repeatability_operator_workflow_completion_audit_selection_v1
```

Operators can now inspect closeout status from the rendered closeout card. The control uses acceptance-checkpoint authority to render `not_recorded` before closeout and closeout receipt authority to render `available` after closeout. The rendered path remains read-only and does not create receipts, mutate lineage, run Candidate B or Layer 3, expose raw authority, or broaden provider, connector, RAG/model, full mockup, default-scope, browser-storage, or frontend durable authority.

### Candidate B Full-Corpus Repeatability Operator Workflow Completion Audit Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_operator_workflow_completion_audit_selection_v1
source_repeatability_acceptance_closeout_rendered_status_runtime: next_milestone_plans/Layer3_planning_docs/1055-cb-repeatability-acceptance-closeout-rendered-status-runtime.md
current_main_entry: a4a39bdacf000cdd93f6b747b9de992e722a7c6a
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_operator_workflow_completion_audit_v1
selected_audit_scope: requirement_by_requirement_completion_audit_for_candidate_b_full_corpus_repeatability_operator_workflow
selected_audit_mode: no_runtime_completion_audit_over_server_owned_receipts_rendered_operator_controls_and_downstream_proof
selected_authority_chain: workflow_run,workflow_history,workflow_status,completion_monitor,repeatability_checkpoint,repeatability_checkpoint_rendered_status,rerun_trial,rerun_trial_rendered_status,acceptance_checkpoint,acceptance_rendered_control,acceptance_closeout,acceptance_closeout_rendered_control,acceptance_closeout_status,acceptance_closeout_rendered_status
selected_completion_requirements: server_owned_workflow_run_receipts,read_only_history_status_progress_completion_monitoring,rendered_operator_start_progress_status_review_controls,original_and_rerun_downstream_proven_rows_bound_to_same_corpus_material_compare_target_runtime_root_policy,repeatability_checkpoint_receipt,repeatability_rerun_trial_receipt,acceptance_checkpoint_receipt,acceptance_closeout_receipt,acceptance_closeout_status_projection,headed_and_headless_rendered_proof,runbook_and_progress_checker_guards
selected_negative_invariants: no_raw_paths_urls_stdout_stderr_logs_traces_pids_artifact_bytes,no_frontend_durable_authority,no_browser_storage_authority,no_process_control_or_browser_triggered_execution,no_operator_supplied_command_path_or_url,no_provider_object_write,no_connector_dispatch,no_rag_vector_model_runtime,no_full_mockup_activation,no_default_scope_expansion
audit_must_report: requirement_status,source_authority,proof_artifact,operator_surface,negative_invariant_result,remaining_blocker,next_exact_posture
audit_must_not_implement_runtime: true
audit_must_not_create_or_mutate_receipts: true
audit_must_not_run_actual_corpus_processing: true
audit_must_not_spawn_processes: true
audit_must_not_change_routes_services_models_or_ui: true
audit_must_not_expand_candidate_b_default_scope: true
audit_must_not_activate_full_mockup: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_full_corpus_repeatability_operator_workflow_completion_audit_v1
```

The next pass is a no-runtime, requirement-by-requirement completion audit over the Candidate B full-corpus repeatability operator workflow. It should inspect current-main receipts, rendered/operator controls, runbook entries, and existing proof artifacts rather than creating new runtime evidence. Any remaining gap must be named as a concrete blocker before the program moves into broader production hardening, eligible-corpus/default-scope decisions, full mockup activation readiness, or future semantic/RAG/model runtime selection.

### Candidate B Full-Corpus Repeatability Operator Workflow Completion Audit

```yaml
milestone: candidate_b_full_corpus_repeatability_operator_workflow_completion_audit_v1
source_repeatability_operator_workflow_completion_audit_selection: next_milestone_plans/Layer3_planning_docs/1056-cb-repeatability-operator-workflow-completion-audit-selection.md
current_main: 1c536a20d7cc19f9b826b2023799ed64bafd348f
audit_mode: no_runtime_requirement_by_requirement_completion_audit
runtime_status: audit_only_no_runtime_change
completion_status: complete_for_current_server_owned_repeatability_operator_workflow_scope
accepted_scope: server_owned_candidate_b_full_corpus_repeatability_operator_workflow_for_eligible_effective_pdfs
operator_surface: rendered_start_progress_status_review_repeatability_rerun_acceptance_closeout_and_closeout_status_controls
authority_chain_verified: workflow_run,workflow_history,workflow_status,completion_monitor,repeatability_checkpoint,repeatability_checkpoint_rendered_status,rerun_trial,rerun_trial_rendered_status,acceptance_checkpoint,acceptance_rendered_control,acceptance_closeout,acceptance_closeout_rendered_control,acceptance_closeout_status,acceptance_closeout_rendered_status
server_owned_workflow_run_receipts: proven
read_only_history_status_progress_completion_monitoring: proven
rendered_operator_start_progress_status_review_controls: proven
repeatability_checkpoint_receipt: proven
repeatability_rerun_trial_receipt: proven
acceptance_checkpoint_receipt: proven
acceptance_closeout_receipt: proven
acceptance_closeout_status_projection: proven
headed_and_headless_rendered_proof: proven
runbook_and_progress_checker_guards: proven
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
raw_paths_urls_stdout_stderr_logs_traces_pids_artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
runtime_behavior_change_introduced_by_this_audit: false
remaining_blockers_for_current_repeatability_operator_workflow_scope: []
remaining_program_work_after_this_audit: production_auth_security_multi_user_storage_hardening,broader_eligible_corpus_default_scope_decision,full_mockup_activation_readiness,semantic_rag_model_runtime_selection_if_separately_admitted
next_exact_posture: candidate_b_post_repeatability_production_hardening_selection_v1
```

The Candidate B full-corpus repeatability operator workflow is complete for the current admitted server-owned eligible/effective PDF scope. This audit does not complete the whole production platform objective; it moves the program out of repeatability-proof work and into a separately selected production-hardening or broader-scope lane.

### Candidate B Post-Repeatability Production Hardening Selection

```yaml
milestone: candidate_b_post_repeatability_production_hardening_selection_v1
source_repeatability_operator_workflow_completion_audit: next_milestone_plans/Layer3_planning_docs/1057-cb-repeatability-operator-workflow-completion-audit.md
current_main_entry: 75874f900629fa710122abc83231c5f0a8588058
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_target: candidate_b_operator_workflow_ownership_access_policy_freeze_v1
selected_hardening_lane: production_auth_security_multi_user_storage_hardening
selected_first_hardening_slice: candidate_b_operator_workflow_owner_scoped_access_policy
selected_named_security_behavior: candidate_b_operator_workflow_owner_scoped_access_decision_v1
selected_protected_surface: candidate_b_full_corpus_operator_workflow_receipts_and_rendered_operator_controls
selected_policy_mode: ownership_access_policy_contract_only
selected_identity_authority_status: unresolved_not_runtime_admitted
selected_tenant_authority_status: unresolved_not_runtime_admitted
selected_operator_role_status: unresolved_not_runtime_admitted
selected_storage_authority_status: existing_server_owned_receipt_and_storage_refs_only
selected_audit_event_contract_status: required_next_not_runtime_admitted
implementation_admitted_after_current_main_sync: true
protected_route_families: workflow_run,workflow_history,workflow_status,queue_scheduler_worker_progress_completion_retry,lifecycle_expiry,process_execution,completion_result_adoption,downstream_proof,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,closeout_status
protected_rendered_surfaces: run_start,history,status,progress,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,closeout_status
threat_model_required: cross_operator_receipt_replay,stale_receipt_use,tenant_workspace_mixup,untrusted_proxy_header_spoofing,browser_state_identity_forgery,storage_root_cross_run_access,raw_path_url_token_leakage,provider_connector_secret_leakage
runtime_behavior_change_introduced_by_selection: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_ownership_access_policy_freeze_v1
```

The next production-hardening pass should freeze owner-scoped access policy for the existing Candidate B operator workflow receipt family and rendered controls. It must name identity, tenant/workspace, role, receipt-owner, storage-root, audit-event, negative-test, and rollback/fail-closed authority before runtime auth/security or multi-user behavior is admitted.

### Candidate B Operator Workflow Ownership Access Policy Freeze

```yaml
milestone: candidate_b_operator_workflow_ownership_access_policy_freeze_v1
source_post_repeatability_production_hardening_selection: next_milestone_plans/Layer3_planning_docs/1058-cb-post-repeatability-production-hardening-selection.md
current_main_entry: 6c8e58f31f7850b6b81a87b639ee7705ee672012
entry_decision: freeze_only
runtime_status: not_implemented
selected_auth_mode: session_tenant_owner_authorization
selected_policy_scope: candidate_b_full_corpus_operator_workflow_receipts_and_rendered_operator_controls
selected_named_security_behavior: candidate_b_operator_workflow_owner_scoped_access_decision_v1
selected_next_target: candidate_b_operator_workflow_ownership_access_policy_contract_v1
implementation_admitted_after_current_main_sync: true
identity_authority: server_derived_operator_identity_ref_required_before_runtime
tenant_or_workspace_authority: server_derived_tenant_or_workspace_ref_required_before_runtime
operator_role_matrix: owner,auditor
workflow_receipt_owner_binding: actor_ref_hash,tenant_or_workspace_ref_hash,workflow_receipt_id,workflow_receipt_hash,authority_basis_hash,policy_hash
storage_root_access_policy: server_owned_receipt_refs_only_no_client_supplied_paths
audit_event_contract: append_only_policy_decision_event_required_before_runtime
forbidden_request_fields: auth_policy_override,auth_security_directive,security_context,browser_identity,local_storage_identity,proxy_identity_header,raw_tenant_id,raw_workspace_id,operator_role_override,permission_override,raw_storage_root,raw_receipt_path,raw_url
owner_role_policy: may_create_and_mutate_own_workflow_receipts_when_runtime_admitted
auditor_role_policy: may_read_status_history_review_and_audit_projection_when_runtime_admitted
cross_owner_receipt_access_policy: reject_fail_closed
missing_identity_policy: reject_fail_closed_for_nonlocal_runtime
missing_tenant_or_workspace_policy: reject_fail_closed_for_nonlocal_runtime
stale_policy_hash_policy: reject_fail_closed
local_proof_harness_compatibility: AUTH_OWNER_none_single_operator_dev_profile_unchanged
nonlocal_identity_prerequisite: AUTH_OWNER_proxy_and_TRUSTED_PROXY_MODE_true_with_explicit_future_header_contract
storage_exposure_prerequisite: nonlocal_direct_storage_exposure_remains_disabled_or_auto
backwards_compatibility_policy: current_local_default_routes_remain_unchanged_until_runtime_contract
negative_tests_required: rejects_missing_identity_authority,rejects_untrusted_proxy_identity,rejects_cross_owner_receipt,rejects_stale_policy_hash,rejects_browser_storage_identity,rejects_raw_path_url_token_response,rejects_storage_root_escape,rejects_provider_connector_secret_exposure
runtime_behavior_change_introduced_by_freeze: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
route_level_auth_dependency_admitted_now: false
model_migration_admitted_now: false
rendered_identity_control_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_ownership_access_policy_contract_v1
```

This freeze names `session_tenant_owner_authorization` as the future policy mode for Candidate B operator workflow receipts and rendered controls. It does not enforce auth, add route dependencies, add models or migrations, or add rendered identity controls. The next pass must turn this into an exact contract before any runtime enforcement is admitted.

### Candidate B Operator Workflow Ownership Access Policy Contract

```yaml
milestone: candidate_b_operator_workflow_ownership_access_policy_contract_v1
source_operator_workflow_ownership_access_policy_freeze: next_milestone_plans/Layer3_planning_docs/1059-cb-operator-workflow-ownership-access-policy-freeze.md
current_main_entry: ea8f4b56cacb559bbf43157d63ccb98bc8c7a18e
contract_status: frozen_no_runtime
runtime_status: not_implemented
selected_runtime_target: candidate_b_operator_workflow_ownership_access_policy_runtime_v1
implementation_admitted_after_current_main_sync: true
selected_auth_mode: session_tenant_owner_authorization
selected_policy_scope: candidate_b_full_corpus_operator_workflow_receipts_and_rendered_operator_controls
selected_named_security_behavior: candidate_b_operator_workflow_owner_scoped_access_decision_v1
policy_decision_schema_id: layer3.candidate_b.operator_workflow.owner_access_policy_decision.v1
identity_authority_contract: server_derived_operator_identity_ref_only
tenant_or_workspace_authority_contract: server_derived_tenant_or_workspace_ref_only
operator_role_contract: owner_can_mutate_own_workflow,auditor_can_read_projection_only
workflow_receipt_owner_binding_contract: actor_ref_hash,tenant_or_workspace_ref_hash,workflow_receipt_id,workflow_receipt_hash,authority_basis_hash,policy_hash
storage_root_access_contract: receipt_bound_storage_refs_only_no_client_supplied_paths_no_storage_root_escape
audit_event_contract: append_only_policy_decision_event
request_admitted_fields: workflow_receipt_id,workflow_receipt_hash,actor_ref_hash,tenant_or_workspace_ref_hash,operator_role,route_family,rendered_surface,client_request_id,policy_hash
request_forbidden_fields: auth_policy_override,auth_security_directive,security_context,browser_identity,local_storage_identity,proxy_identity_header,raw_operator_identity,raw_tenant_id,raw_workspace_id,operator_role_override,permission_override,raw_storage_root,raw_receipt_path,raw_url,provider_secret,connector_secret
response_admitted_fields: policy_schema_id,policy_hash,decision,reason_code,workflow_receipt_id,workflow_receipt_hash,actor_ref_hash,tenant_or_workspace_ref_hash,route_family,rendered_surface,audit_event_id,next_actions
response_forbidden_fields: raw_operator_identity,raw_proxy_header,raw_tenant_id,raw_workspace_id,raw_local_path,raw_url,raw_token,provider_secret,connector_secret,artifact_bytes,permission_internals
owner_allowed_decisions: workflow_run,queue_scheduler_worker_progress_completion_retry,lifecycle_expiry,process_execution,completion_result_adoption,downstream_proof,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout
auditor_allowed_decisions: workflow_history,workflow_status,completion_monitor,closeout_status,rendered_history,rendered_status,rendered_progress,rendered_review
cross_owner_receipt_access_policy: reject_fail_closed
missing_identity_policy: reject_fail_closed_for_nonlocal_runtime
missing_tenant_or_workspace_policy: reject_fail_closed_for_nonlocal_runtime
stale_policy_hash_policy: reject_fail_closed
browser_identity_policy: never_authority
local_storage_identity_policy: never_authority
untrusted_proxy_header_policy: reject_fail_closed
local_proof_harness_compatibility: AUTH_OWNER_none_single_operator_dev_profile_unchanged
nonlocal_runtime_prerequisite: AUTH_OWNER_proxy,TRUSTED_PROXY_MODE_true,explicit_trusted_header_contract,storage_exposure_auto_or_disabled
rollback_fail_closed_behavior: disabling_policy_runtime_reverts_to_current_receipt_validated_workflow_without_owner_enforcement
negative_tests_required: rejects_missing_identity_authority,rejects_untrusted_proxy_identity,rejects_cross_owner_receipt,rejects_stale_policy_hash,rejects_browser_storage_identity,rejects_raw_path_url_token_response,rejects_storage_root_escape,rejects_provider_connector_secret_exposure,rejects_operator_role_override,rejects_permission_override
runtime_behavior_change_introduced_by_contract: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
route_level_auth_dependency_admitted_now: false
model_migration_admitted_now: false
rendered_identity_control_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_ownership_access_policy_runtime_v1
```

This contract defines the future owner-scoped policy decision layer for Candidate B workflow receipts and rendered controls. It still introduces no runtime behavior; the next slice may implement only this contract if current main still admits it after sync.

### Candidate B Operator Workflow Ownership Access Policy Runtime

```yaml
milestone: candidate_b_operator_workflow_ownership_access_policy_runtime_v1
source_operator_workflow_ownership_access_policy_contract: next_milestone_plans/Layer3_planning_docs/1060-cb-operator-workflow-ownership-access-policy-contract.md
current_main_entry: d62b03bbe0d881d20236359d3300b093e0f96054
runtime_status: core_run_status_history_implemented
implemented_policy_module: backend/app/services/layer3_candidate_b_operator_workflow_access_policy.py
implemented_route_context_surface: backend/app/api/layer3.py
implemented_service_surfaces: backend/app/services/layer3_candidate_b_full_corpus_operator_workflow_run.py,backend/app/services/layer3_candidate_b_full_corpus_operator_workflow_status.py,backend/app/services/layer3_candidate_b_full_corpus_operator_workflow_history.py
implemented_test_surfaces: backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_run.py,backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_status.py
selected_auth_mode: session_tenant_owner_authorization
selected_named_security_behavior: candidate_b_operator_workflow_owner_scoped_access_decision_v1
policy_decision_schema_id: layer3.candidate_b.operator_workflow.owner_access_policy_decision.v1
audit_event_schema_id: layer3.candidate_b.operator_workflow.ownership_access_audit_event.v1
policy_receipt_prefix: cb-full-corpus-operator-policy
protected_route_families_implemented: workflow_run,workflow_status,workflow_history
protected_rendered_surfaces_implemented: run_start,status,history
remaining_protected_route_families: lifecycle_expiry,queue_scheduler_worker_progress_completion_retry,process_execution,completion_result_adoption,downstream_proof,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,closeout_status,review_status_projection,audit_projection
identity_authority_runtime: AUTH_OWNER_none_local_single_operator_or_AUTH_OWNER_proxy_trusted_header_hash
tenant_or_workspace_authority_runtime: AUTH_OWNER_none_local_single_workspace_or_AUTH_OWNER_proxy_trusted_groups_header_hash
operator_role_runtime: owner_can_run,auditor_can_read_status_history
workflow_receipt_owner_binding_runtime: server_owned_workflow_run.workflow_receipt_owner_binding
storage_root_access_runtime: configured_workflow_receipt_root_only_no_client_supplied_paths
audit_event_runtime: append_only_redacted_policy_receipt_under_configured_workflow_root
missing_identity_policy: reject_fail_closed_for_AUTH_OWNER_proxy
missing_tenant_or_workspace_policy: reject_fail_closed_for_AUTH_OWNER_proxy
untrusted_proxy_header_policy: reject_fail_closed
cross_owner_receipt_access_policy: reject_fail_closed
stale_policy_hash_policy: reject_fail_closed
browser_identity_policy: never_authority
local_storage_identity_policy: never_authority
local_proof_harness_compatibility: AUTH_OWNER_none_single_operator_dev_profile_unchanged
runtime_behavior_change_introduced_by_runtime: true
auth_security_runtime_admitted_now: true
multi_user_runtime_admitted_now: partially_core_surfaces_only
storage_policy_runtime_admitted_now: configured_workflow_receipt_root_only
audit_event_runtime_admitted_now: true
model_migration_admitted_now: false
rendered_identity_control_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
proof_status: local_passed
next_exact_posture: candidate_b_operator_workflow_ownership_access_policy_protected_route_expansion_v1
```

The first runtime pass now protects Candidate B workflow run, status, and history with server-owned policy decisions and redacted append-only audit receipts. It preserves the local `AUTH_OWNER=none` operator harness while making proxy-owned operation fail closed unless trusted server identity and tenant/workspace headers are present and match any stored workflow owner binding. The remaining workflow route families still need policy-context expansion before this can be described as complete ownership enforcement.

### Candidate B Operator Workflow Ownership Access Policy Protected Route Expansion

```yaml
milestone: candidate_b_operator_workflow_ownership_access_policy_protected_route_expansion_v1
source_operator_workflow_ownership_access_policy_runtime: next_milestone_plans/Layer3_planning_docs/1061-cb-operator-workflow-ownership-access-policy-runtime.md
current_main_entry: 632d44ec1516235258ce33f0a63a4180cb28ca87
runtime_status: protected_route_family_policy_context_expanded
implemented_policy_module: backend/app/services/layer3_candidate_b_operator_workflow_access_policy.py
implemented_route_context_surface: backend/app/api/layer3.py
protected_route_families_implemented: workflow_run,workflow_status,workflow_history,lifecycle_expiry,queue_scheduler_worker_progress_completion_retry,process_execution,completion_result_adoption,downstream_proof,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout
remaining_protected_route_families: closeout_status,review_status_projection,audit_projection
shared_row_authority_policy_helper: authorize_history_row_access
route_context_wrapped_api_surfaces: lifecycle_expire,queue_state,scheduler_lease,worker_attempt,progress_checkpoint,completion_failure,retry_policy,retry_queue_state,retry_scheduler_lease,retry_worker_attempt,retry_progress_checkpoint,retry_completion_failure,execution_boundary,process_execution,process_completion_result,adopted_result_downstream_proof,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,acceptance_closeout_status
cross_owner_receipt_access_policy: reject_fail_closed
missing_identity_policy: reject_fail_closed_for_AUTH_OWNER_proxy
untrusted_proxy_header_policy: reject_fail_closed
audit_event_runtime: append_only_redacted_policy_receipt_under_configured_workflow_root
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
proof_status: local_passed
next_exact_posture: candidate_b_operator_workflow_ownership_access_policy_closeout_status_review_audit_projection_v1
```

The protected-route expansion carries trusted policy request context into the remaining Candidate B operator workflow API route families and enforces owner/auditor policy at the shared workflow-row authority boundary. The focused regression covers proxy-owned queue-state continuation, redacted policy audit emission, and fail-closed cross-owner rejection. Closeout-status, review-status projection, and audit projection remain next because they are read-only projection surfaces that need explicit projection-policy treatment.

### Candidate B Operator Workflow Ownership Access Policy Closeout Status Review Audit Projection

```yaml
milestone: candidate_b_operator_workflow_ownership_access_policy_closeout_status_review_audit_projection_v1
source_operator_workflow_ownership_access_policy_route_expansion: next_milestone_plans/Layer3_planning_docs/1062-cb-operator-workflow-ownership-access-policy-route-expansion.md
current_main_entry: 16a2b3b09f4e379a38b4ea7b3058d52e93a33db0
runtime_status: closeout_status_review_audit_projection_policy_enforced
implemented_policy_module: backend/app/services/layer3_candidate_b_operator_workflow_access_policy.py
implemented_closeout_status_service: backend/app/services/layer3_candidate_b_full_corpus_repeatability_acceptance_closeout.py
implemented_route_context_surface: backend/app/api/layer3.py
protected_route_families_implemented: workflow_run,workflow_status,workflow_history,lifecycle_expiry,queue_scheduler_worker_progress_completion_retry,process_execution,completion_result_adoption,downstream_proof,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,closeout_status,review_status_projection,audit_projection
remaining_protected_route_families: none_for_current_candidate_b_operator_workflow_scope
protected_projection_surfaces_implemented: acceptance_closeout_status,acceptance_closeout_status_review,acceptance_closeout_status_audit
shared_projection_authority_policy_helper: authorize_projection_receipt_access
closeout_status_projection_authority: repeatability_acceptance_operator_closeout_receipt_or_repeatability_acceptance_checkpoint_selector
closeout_status_policy_enforced: true
review_status_projection_policy_enforced: true
audit_projection_policy_enforced: true
ownership_access_policy_response_projection: closeout_status,review_status_projection,audit_projection
missing_identity_policy: reject_fail_closed_for_AUTH_OWNER_proxy
audit_event_runtime: append_only_redacted_policy_receipt_under_configured_workflow_root
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
proof_status: local_passed
next_exact_posture: candidate_b_operator_workflow_rendered_identity_status_controls_selection_v1
```

The acceptance-closeout status endpoint is now also the governed read-only status/review/audit projection surface for the current Candidate B operator workflow scope. Operators see redacted policy refs and audit event refs for the closeout status, review projection, and audit projection decisions; no new execution, provider, connector, source expansion, RAG/model, default-scope, browser-storage, or frontend authority is admitted by this slice.

### Candidate B Operator Workflow Rendered Identity Status Controls Selection

```yaml
milestone: candidate_b_operator_workflow_rendered_identity_status_controls_selection_v1
source_operator_workflow_ownership_access_policy_projections: next_milestone_plans/Layer3_planning_docs/1063-cb-operator-workflow-ownership-access-policy-projections.md
current_main_entry: cd23835141aee3e984e7bb93900ded6024973a1c
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_rendered_identity_status_controls_runtime_v1
selected_rendered_control_scope: candidate_b_operator_workflow_policy_status_identity_projection_controls
selected_rendered_surfaces: workflow_run,workflow_history,workflow_status,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,acceptance_closeout_status
selected_policy_response_projection: ownership_access_policy,policy_status,policy_hash,route_family,rendered_surface,audit_event_ref,actor_ref_hash,tenant_or_workspace_ref_hash
selected_request_role_projection: owner_for_mutating_workflow_receipt_actions,auditor_for_read_only_status_history_review_audit_projection
selected_closeout_status_request_change: add_operator_role_auditor_to_rendered_payload
selected_error_projection: missing_identity_authority,missing_tenant_or_workspace_authority,untrusted_proxy_identity,cross_owner_receipt,stale_policy_hash,forbidden_request_fields
selected_status_copy: server_derived_identity_only_browser_storage_never_authority
selected_headed_rendered_proof: required_before_runtime_closeout
selected_headless_rendered_proof: required_before_runtime_closeout
implementation_admitted_after_current_main_sync: true
runtime_behavior_change_introduced_by_selection: false
rendered_behavior_change_introduced_by_selection: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_proxy_header_exposed: false
raw_operator_identity_exposed: false
raw_tenant_or_workspace_exposed: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_rendered_identity_status_controls_runtime_v1
```

The next rendered runtime may expose only redacted server policy status and identity refs already produced by the Candidate B ownership/access policy layer. It must not turn browser storage, local storage, copied proxy headers, raw identity strings, or frontend-only state into authority.

### Candidate B Operator Workflow Rendered Identity Status Controls Runtime

```yaml
milestone: candidate_b_operator_workflow_rendered_identity_status_controls_runtime_v1
source_operator_workflow_rendered_identity_status_controls_selection: next_milestone_plans/Layer3_planning_docs/1064-cb-operator-workflow-rendered-identity-status-controls-selection.md
current_main_entry: 092cb5253719bb940b0fc9ff849daa61d03fef8d
runtime_status: rendered_policy_identity_status_controls_implemented
implemented_rendered_control_scope: candidate_b_operator_workflow_policy_status_identity_projection_controls
implemented_rendered_surfaces: workflow_run,workflow_history,workflow_status,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,acceptance_closeout_status,acceptance_closeout_status_review,acceptance_closeout_status_audit
implemented_policy_response_projection: ownership_access_policy,policy_status,policy_hash,route_family,rendered_surface,audit_event_ref,actor_ref_hash,tenant_or_workspace_ref_hash
implemented_request_role_projection: workflow_status_payload_operator_role_auditor,workflow_history_status_request_operator_role_auditor,acceptance_closeout_status_payload_operator_role_auditor
rendered_workflow_status_policy_control: Workflow Status Ownership Policy
rendered_workflow_history_policy_control: workflow_history_row_policy_items
rendered_acceptance_closeout_status_policy_control: Closeout Status Policy
rendered_acceptance_closeout_review_policy_control: Review Status Projection Policy
rendered_acceptance_closeout_audit_policy_control: Audit Projection Policy
raw_proxy_header_exposed: false
raw_operator_identity_exposed: false
raw_tenant_or_workspace_exposed: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_or_connector_secret_exposed: false
browser_storage_authority_enabled: false
frontend_durable_authority_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
proof_status: local_passed
next_exact_posture: candidate_b_operator_workflow_production_auth_storage_hardening_selection_v1
```

Rendered operator status controls now show server-owned ownership/access policy decisions wherever the response already carries an `ownership_access_policy` projection. Operators can inspect redacted policy hashes, route families, rendered surfaces, audit event refs, actor/tenant hash refs, and negative authority flags without raw identity, proxy headers, local paths, URLs, provider secrets, browser storage authority, or frontend durable authority.

### Candidate B Operator Workflow Production Auth Storage Hardening Selection

```yaml
milestone: candidate_b_operator_workflow_production_auth_storage_hardening_selection_v1
source_operator_workflow_rendered_identity_status_controls_runtime: next_milestone_plans/Layer3_planning_docs/1065-cb-operator-workflow-rendered-identity-status-controls-runtime.md
current_main_entry: 9214366ac68d9f7331f15b019d4dd379f72c4239
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1
selected_auth_owner_mode: AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true
selected_storage_access_policy: configured_workflow_receipt_root_only_receipt_bound_refs_only_no_client_supplied_paths
selected_audit_event_policy: append_only_redacted_policy_receipt_under_configured_workflow_root
selected_local_compatibility: AUTH_OWNER_none_single_operator_dev_profile_unchanged
implementation_admitted_after_current_main_sync: true
auth_security_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1
```

The next production-hardening pass is selected but not implemented here. It should bind existing Candidate B workflow receipts, status/history/review/audit projections, and rendered controls to proxy-derived owner and tenant/workspace authority under `AUTH_OWNER=proxy` with `TRUSTED_PROXY_MODE=true`, while preserving the local `AUTH_OWNER=none` single-operator proof harness. Storage remains limited to configured workflow receipt roots and receipt-bound refs; raw paths, URLs, provider secrets, connector secrets, browser/local-storage identity, frontend durable authority, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, and broader Candidate B default scope remain outside this selection.

### Candidate B Operator Workflow Proxy Owner Storage Policy Runtime

```yaml
milestone: candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1
source_operator_workflow_production_auth_storage_hardening_selection: next_milestone_plans/Layer3_planning_docs/1066-cb-operator-workflow-production-auth-storage-hardening-selection.md
current_main_entry: 46a414c57e0e9ba78eaecd635f85297c97a61bbf
runtime_status: proxy_owner_storage_policy_runtime_implemented
implemented_policy_runtime: candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1
implemented_auth_owner_mode: AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true
implemented_storage_access_policy: configured_workflow_receipt_root_only_receipt_bound_refs_only_no_client_supplied_paths
implemented_audit_event_policy: append_only_redacted_policy_receipt_under_configured_workflow_root
missing_tenant_fail_closed_proven: true
untrusted_proxy_fail_closed_proven: true
storage_root_escape_fail_closed_proven: true
AUTH_OWNER_none_compatibility_proven: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
verification_backend_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_status.py ./backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_run.py -q PASS 112 passed
verification_node_check: node --check ./backend/app/review_ui/static/layer3.js PASS
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B full-corpus workflow status|Candidate B workflow history|records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium PASS 3 passed
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B full-corpus workflow status|Candidate B workflow history|records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium --headed PASS 3 passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selection_v1
```

Candidate B workflow policy decisions and audit receipts now name the proxy-owner storage policy runtime, auth-owner mode, configured server identity/tenant authority, configured workflow-receipt-root storage policy, and redacted audit-event policy. `AUTH_OWNER=proxy` fails closed without trusted proxy mode, server identity, and tenant/workspace authority; existing owner bindings reject cross-owner access; stale policy hashes reject contradictory authority; caller storage roots remain forbidden; and local `AUTH_OWNER=none` single-operator proof remains compatible.

### Candidate B Broader Eligible Corpus Default Scope Selection

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selection_v1
source_operator_workflow_proxy_owner_storage_policy_runtime: next_milestone_plans/Layer3_planning_docs/1067-cb-operator-workflow-proxy-owner-storage-policy-runtime.md
current_main_entry: 39c23a61c306695b801158fef6e871182a825f46
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_audit_target: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
selected_decision_scope: candidate_b_default_scope_after_eligible_effective_pdf_acceptance
selected_evaluation_mode: read_only_no_runtime_scope_readiness_audit
default_scope_expansion_admitted_now: false
current_default_scope: eligible_effective_pdfs_only
non_pdf_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
bundle_and_runtime_authority_remain_distinct: true
candidate_scope_classes_to_audit: office_documents,images_or_ocr,zip_members,structured_json_or_csv_or_xlsx,sec_edgar,web_or_database_sources,mixed_corpus_batches
required_scope_evidence: exact_corpus_class_list,explicit_exclusion_list,current_parser_or_engine_authority,baseline_rollback_behavior,candidate_a_interaction,candidate_b_runtime_compatibility,layer3_material_authority_bridge_compatibility,artifact_family_preservation,redaction_and_status_projection,corpus_scale_proof,fail_closed_stale_or_missing_authority,regression_disposition
selector_mutation_admitted: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
```

Broader Candidate B default scope is now selected only as a read-only readiness-audit question. Candidate B remains the default for eligible/effective PDFs only; baseline remains the non-PDF default and rollback path; Candidate A remains its explicit PageEvidence visual-lane variant; and no selector, ingestion, provider, connector, RAG/model, frontend authority, or full-mockup expansion is admitted by this checkpoint.

### Candidate B Broader Eligible Corpus Scope Readiness Audit

```yaml
milestone: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
source_broader_eligible_corpus_default_scope_selection: next_milestone_plans/Layer3_planning_docs/1068-cb-broader-eligible-corpus-default-scope-selection.md
current_main_entry: 4d1ab21446428d4f38ddb439e3e6f63c06b05730
runtime_status: broader_scope_readiness_audit_implemented
implemented_audit_mode: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
implemented_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit
implemented_scope_classes: office_documents,images_or_ocr,zip_members,structured_json_or_csv_or_xlsx,sec_edgar,web_or_database_sources,mixed_corpus_batches
implemented_required_scope_evidence: current_parser_or_engine_authority,baseline_rollback_behavior,candidate_a_interaction,candidate_b_runtime_compatibility,layer3_material_authority_bridge_compatibility,artifact_family_preservation,redaction_and_status_projection,corpus_scale_proof,fail_closed_stale_or_missing_authority,regression_disposition
implemented_contract_exposure: readiness_contract,bootstrap_contract,openapi
ready_state_meaning: ready_for_later_separately_frozen_default_scope_selection_only
default_scope_expansion_admitted: false
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_current_default_scope_preserved: eligible_effective_pdfs_only
verification_focused_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_broader_scope_readiness.py ./backend/tests/test_layer3_readiness_contract.py ./backend/tests/test_layer3_bootstrap_contract.py -q PASS 6 passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_selection_v1
```

The broader-scope readiness audit is now an operator-callable, read-only API surface. It checks exact scope-class evidence and can only prepare a later separately frozen default-scope selection; it does not broaden Candidate B default behavior, mutate selectors, ingest new source families, expose paths/URLs, or enable provider/connector/RAG/model/full-mockup/browser/frontend authority.

### Candidate B Broader Eligible Corpus Default Scope Runtime Selection

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_runtime_selection_v1
source_broader_eligible_corpus_scope_readiness_audit: next_milestone_plans/Layer3_planning_docs/1069-cb-broader-eligible-corpus-scope-readiness-audit.md
current_main_entry: 3d2dc7a9178fc0f6ed0923333b1c9e8dc36c7fed
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
selected_runtime_scope: candidate_b_default_scope_selection_for_ready_broader_corpus_classes_only
selected_scope_binding_authority: candidate_b_broader_eligible_corpus_scope_readiness_audit_ready_state
selected_scope_binding_state_required: candidate_b_broader_eligible_corpus_scope_ready_for_separate_selection
selected_scope_classes_source: proposed_default_scope_classes_from_matching_ready_audit
current_ready_audit_receipt_available: false
current_runtime_scope_classes_selected: none_until_ready_audit_receipt_bound
current_default_scope_preserved: eligible_effective_pdfs_only
non_pdf_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
runtime_must_fail_closed_without_ready_audit: true
runtime_must_fail_closed_on_stale_or_mismatched_audit_hash: true
runtime_must_fail_closed_on_unready_or_unproposed_scope_class: true
runtime_must_project_operator_visible_scope_status: true
runtime_must_record_redacted_selection_receipt: true
default_scope_expansion_admitted_now: false
selector_mutation_admitted_now: false
source_expansion_admitted_now: false
runtime_db_or_storage_expansion_admitted_now: false
pdf_or_image_text_material_ingestion_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
```

The default-scope runtime selection is frozen but not implemented here. The future runtime must bind to a ready broader-scope audit result and exact proposed classes before recording any redacted selection receipt. No broader classes are selected in this checkpoint because current main has the audit API but no bound ready audit receipt.

### Candidate B Broader Eligible Corpus Default Scope Runtime

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
source_broader_eligible_corpus_default_scope_runtime_selection: next_milestone_plans/Layer3_planning_docs/1070-cb-broader-eligible-corpus-default-scope-runtime-selection.md
current_main_entry: 798c3e279a97af14444da7e6210cd6cd1cd4c723
runtime_status: broader_scope_default_scope_runtime_implemented
implemented_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
implemented_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime
implemented_scope_binding_authority: candidate_b_broader_eligible_corpus_scope_readiness_audit_ready_state
implemented_scope_binding_state_required: candidate_b_broader_eligible_corpus_scope_ready_for_separate_selection
implemented_scope_classes_source: proposed_default_scope_classes_from_matching_ready_audit
implemented_audit_hash_binding_required: true
implemented_audit_id_binding_required: true
implemented_redacted_selection_receipt: true
implemented_contract_exposure: readiness_contract,bootstrap_contract,openapi
missing_audit_fail_closed_proven: true
stale_audit_hash_fail_closed_proven: true
unready_or_unproposed_scope_class_fail_closed_proven: true
current_default_scope_preserved: eligible_effective_pdfs_only
non_pdf_default_preserved_until_selection: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
verification_focused_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_broader_scope_runtime.py ./backend/tests/test_layer3_candidate_b_broader_scope_readiness.py ./backend/tests/test_layer3_readiness_contract.py ./backend/tests/test_layer3_bootstrap_contract.py -q PASS 11 passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_rendered_status_v1
```

Operators can now call the broader eligible-corpus runtime only with a ready scope-readiness audit result, matching audit id/hash, exact proposed selected classes, rollback confirmation, and operator confirmation. A selected response writes a redacted `candidate-b-broader-scope-runtime://...` receipt under the configured Candidate B runtime bridge receipt root. Blocked responses record no receipt and keep Candidate B's current eligible/effective PDF default plus baseline non-PDF fallback intact.

### Candidate B Broader Eligible Corpus Default Scope Runtime Rendered Status

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_runtime_rendered_status_v1
source_broader_eligible_corpus_default_scope_runtime: next_milestone_plans/Layer3_planning_docs/1071-cb-broader-eligible-corpus-default-scope-runtime.md
current_main_entry: e3007dd8824770585d442916067c9a40f3343927
rendered_status: broader_scope_default_scope_runtime_rendered_status_implemented
rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_runtime_status_control
runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
runtime_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime
selected_state_visible: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
blocked_state_visible: candidate_b_broader_eligible_corpus_default_scope_runtime_blocked
ready_audit_json_required: true
selected_scope_classes_required: true
readiness_audit_id_hash_bound: true
redacted_selection_receipt_visible: true
operator_visible_scope_status_visible: true
current_default_scope_preserved: eligible_effective_pdfs_only
non_pdf_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
rendered_contract_proof: e2e/layer3-workbench.spec.js::Layer 3 workbench renders Candidate B default-promotion status contract without route calls
rendered_runtime_status_proof: e2e/layer3-workbench.spec.js::Layer 3 workbench records Candidate B broader eligible-corpus runtime status through rendered control
verification_node_check: node --check ./backend/app/review_ui/static/layer3.js PASS
headless_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium PASS 2 passed
headed_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium --headed PASS 2 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_current_main_sync_v1
```

The rendered status control lets an operator paste a server-produced broader-scope readiness audit result, select exact proposed scope classes, and call the admitted runtime endpoint from the Candidate B status panel. The UI displays selected and blocked states, readiness binding, redacted receipt status, selected class count, current PDF default preservation, baseline non-PDF fallback, and negative authority flags without raw path, raw URL, provider, connector, browser-storage, or frontend-durable authority.

### Candidate B Broader Eligible Corpus Default Scope Runtime Current-Main Sync

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

Current main now includes the rendered broader-scope runtime status control from PR `#1775`. This checkpoint does not use that runtime receipt to mutate Candidate B's default selector; a later selector-use slice must separately freeze how exact selected classes can consume the redacted runtime receipt while preserving baseline rollback, Candidate A semantics, and fail-closed stale authority.

### Candidate B Broader Eligible Corpus Default Scope Selector-Use Selection

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_selection_v1
source_broader_eligible_corpus_default_scope_runtime_current_main_sync: next_milestone_plans/Layer3_planning_docs/1073-cb-broader-eligible-corpus-default-scope-runtime-current-main-sync.md
current_main_entry: 86aec5e059b66d98a1b6a48cd83096a8915684a0
entry_decision: freeze_only
selector_use_runtime_status: not_implemented
selected_next_runtime_target: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
selected_selector_use_scope: receipt_bound_default_selector_use_for_exact_selected_broader_scope_classes_only
selected_selector_authority_source: redacted_candidate_b_broader_scope_runtime_receipt
selected_selector_authority_state_required: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
selected_scope_classes_source: selected_scope_classes_from_matching_runtime_receipt
selected_runtime_receipt_id_hash_binding_required: true
selected_readiness_audit_id_hash_binding_required: true
selected_operator_confirmation_required: true
selected_baseline_rollback_confirmation_required: true
selected_candidate_a_preservation_required: true
selected_stale_authority_rejection_required: true
selected_unknown_or_unselected_class_rejection_required: true
selected_missing_receipt_rejection_required: true
selected_blocked_receipt_rejection_required: true
current_runtime_receipt_operator_surface: /review/layer3 Candidate B default-promotion status panel
current_default_scope_preserved_at_selection: eligible_effective_pdfs_only
future_default_scope_may_change_only_for_receipt_bound_selected_classes: true
non_selected_class_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
bundle_and_runtime_authority_remain_distinct: true
selector_use_behavior_change_introduced_by_selection: false
runtime_behavior_introduced_by_selection: false
rendered_behavior_introduced_by_selection: false
backend_behavior_introduced_by_selection: false
api_service_behavior_introduced_by_selection: false
default_scope_expansion_performed_now: false
selector_mutation_performed_now: false
source_expansion_admitted_now: false
runtime_db_or_storage_expansion_admitted_now: false
pdf_or_image_text_material_ingestion_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_or_connector_secret_exposed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
```

The selected next runtime may use only a server-owned selected broader-scope runtime receipt as selector authority for exact receipt-bound classes. This selection does not mutate the default selector, broaden source ingestion, treat browser input as durable authority, or change baseline/Candidate A behavior. Missing, blocked, stale, unknown, unselected, or separately unauthorized classes remain baseline/fail-closed.

### Candidate B Broader Eligible Corpus Default Scope Selector-Use Runtime

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
source_broader_eligible_corpus_default_scope_selector_use_selection: next_milestone_plans/Layer3_planning_docs/1074-cb-broader-eligible-corpus-default-scope-selector-use-selection.md
current_main_entry: 82ee2274710edad3decbbffaac2028b983098634
runtime_status: selector_use_runtime_implemented
implemented_schema_id: layer3.candidate_b_broader_eligible_corpus_default_scope_selector_use.v1
implemented_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
implemented_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use
implemented_selected_state: candidate_b_broader_eligible_corpus_default_scope_selector_use_selected
implemented_blocked_state: candidate_b_broader_eligible_corpus_default_scope_selector_use_blocked
implemented_selector_authority_source: redacted_candidate_b_broader_scope_runtime_receipt
implemented_source_runtime_required_state: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
implemented_source_runtime_schema_id: layer3.candidate_b_broader_eligible_corpus_default_scope_runtime.v1
implemented_source_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
implemented_selected_scope_classes_source: selected_scope_classes_from_matching_runtime_receipt
implemented_receipt_binding_required: runtime_selection_receipt_id_and_hash
implemented_readiness_binding_required: readiness_audit_id_and_hash_from_source_runtime_receipt
implemented_receipt_root: configured_layer3_candidate_b_runtime_bridge_dir
implemented_receipt_family: broader-scope-selector-use
implemented_receipt_ref_scheme: candidate-b-broader-scope-selector-use
implemented_status_surface: api_response_redacted_selector_status
current_default_scope_before_use: eligible_effective_pdfs_only
default_scope_enabled_for_selected_classes: receipt_bound_only
non_selected_class_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
missing_runtime_receipt_blocks_selector_use: true
blocked_runtime_receipt_blocks_selector_use: true
stale_runtime_receipt_hash_blocks_selector_use: true
stale_readiness_audit_hash_blocks_selector_use: true
unknown_scope_class_blocks_selector_use: true
unselected_scope_class_blocks_selector_use: true
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
verification_backend_py_compile: python -m py_compile ./backend/app/services/layer3_candidate_b_broader_scope_selector_use.py ./backend/app/api/layer3.py ./backend/app/services/layer3_readiness_contract.py ./backend/app/services/layer3_bootstrap_contract.py PASS
verification_focused_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_broader_scope_selector_use.py ./backend/tests/test_layer3_candidate_b_broader_scope_runtime.py ./backend/tests/test_layer3_candidate_b_broader_scope_readiness.py ./backend/tests/test_layer3_readiness_contract.py ./backend/tests/test_layer3_bootstrap_contract.py -q PASS 16 passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_rendered_status_v1
```

The selector-use runtime reloads the selected broader-scope runtime receipt from configured server authority, validates receipt id/hash and exact selected classes, then records a redacted selector-use receipt. It does not accept browser-supplied runtime roots, raw paths, raw URLs, receipt JSON, provider refs, connector destinations, model controls, or selector mutation fields.

### Candidate B Broader Eligible Corpus Default Scope Selector-Use Rendered Status

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_rendered_status_v1
source_broader_eligible_corpus_default_scope_selector_use_runtime: next_milestone_plans/Layer3_planning_docs/1075-cb-broader-eligible-corpus-default-scope-selector-use-runtime.md
current_main_entry: d4f71a839c6d0525a9caba57441ca0f69c9aafb9
rendered_status: selector_use_rendered_status_implemented
rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_selector_use_status_control
runtime_mode: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
runtime_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use
selected_state_visible: candidate_b_broader_eligible_corpus_default_scope_selector_use_selected
blocked_state_visible: candidate_b_broader_eligible_corpus_default_scope_selector_use_blocked
runtime_selection_receipt_id_hash_required: true
selected_scope_classes_required: true
selector_authority_source_visible: redacted_candidate_b_broader_scope_runtime_receipt
runtime_receipt_binding_visible: true
redacted_selector_use_receipt_visible: true
operator_visible_selector_status_visible: true
default_scope_enabled_for_selected_classes_visible: true
non_selected_class_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
rendered_contract_proof: e2e/layer3-workbench.spec.js::Layer 3 workbench renders Candidate B default-promotion status contract without route calls
rendered_selector_use_status_proof: e2e/layer3-workbench.spec.js::Layer 3 workbench records Candidate B broader eligible-corpus runtime status through rendered control
verification_node_check: node --check ./backend/app/review_ui/static/layer3.js PASS
headless_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium PASS 2 passed
headed_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium --headed PASS 2 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_rendered_stale_input_review_remediation_v1
```

The rendered selector-use control records status from server receipt authority only. It submits receipt id/hash and exact selected classes, then displays selected or blocked server status, redacted selector-use receipt metadata, runtime receipt binding, and negative authority flags without raw paths, URLs, runtime roots, provider refs, connector destinations, model controls, selector mutation fields, browser storage authority, or frontend durable authority.

### Candidate B Broader Eligible Corpus Default Scope Selector-Use Rendered Stale Input Review Remediation

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_rendered_stale_input_review_remediation_v1
source_broader_eligible_corpus_default_scope_selector_use_rendered_status: next_milestone_plans/Layer3_planning_docs/1076-cb-broader-eligible-corpus-default-scope-selector-use-rendered-status.md
current_main_entry: 8147bed5c661a4ac6fd10821879f92c0edf34c7a
source_review_pr: "#1779"
source_review_thread_total_count: 1
source_review_unresolved_before_remediation: 1
source_review_path: backend/app/review_ui/static/layer3.js
source_review_line: 8334
review_disposition: remediated_in_followup_slice
remediation_status: implemented
remediated_failure_mode: selector_use_payload_reuses_stale_runtime_receipt_or_classes_after_runtime_re_record
runtime_defaults_source: latest_selected_candidate_b_broader_scope_runtime_receipt
operator_edit_tracking: candidateBBroaderScopeSelectorUseInputEdited
runtime_default_helper: candidateBBroaderScopeSelectorUseRuntimeDefaults
runtime_success_resets_selector_use_input: true
runtime_success_clears_stale_selector_use_status: true
operator_edited_fields_preserved_after_explicit_edit: true
selector_use_payload_prefers_latest_runtime_unless_operator_edited: true
second_runtime_receipt_proof: cb-broader-scope-runtime-rendered-proof-2
second_runtime_receipt_hash_proof: "7777777777777777777777777777777777777777777777777777777777777777"
rendered_selector_use_latest_runtime_payload_proof: true
selected_state_preserved: candidate_b_broader_eligible_corpus_default_scope_selector_use_selected
blocked_state_preserved: candidate_b_broader_eligible_corpus_default_scope_selector_use_blocked
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
headless_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status" --project=chromium PASS 1 passed
headed_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status" --project=chromium --headed PASS 1 passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_current_main_sync_v1
```

The selector-use rendered panel now defaults to the latest selected broader-scope runtime receipt after runtime re-recording, unless the operator explicitly edits the selector-use fields. This closes the stale receipt/class reuse path identified after PR `#1779` without changing backend selector behavior, mutating defaults, or introducing frontend durable authority.

### Candidate B Broader Eligible Corpus Default Scope Selector-Use Remediation Current-Main Sync

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
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_operator_status_inspection_v1
```

The selector-use stale runtime input remediation is now current-main behavior. The next useful slice is operator status inspection for selected selector-use receipts, so an operator can inspect which receipt/class selection is active before any broader default-promotion closeout.
