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

The current proven downstream receipt is:

```yaml
downstream_proof_id: cb-runtime-downstream-proof-1a8c44a841830707c2168578
coverage_count: 17
provider_private_state: provider_private_signed_url_prepared
provider_private_revoke_state: provider_private_signed_url_revoked
internal_webhook_state: source_directory_internal_webhook_dispatched
candidate_b_default_promotion_enabled: false
```

For a quick repeatability smoke against current main, run the focused test that exercises the same bridge and downstream surfaces without broadening runtime state:

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
- No API/schema/DB contract changes.
- No rendered run-submission UI is added here.
- No mutation of `tests/reports/*.json`, `backend/method_aware.db`, `backend/app/storage`, or the historical `run_20260314_010136` evidence package.

## Notes
- The proof intentionally maps `technical_specification_amendment_documents_for_testing` to `Technical Specification Amendment` so the live advanced-table routing path is exercised. The current `document_types.json` vocabulary still uses `Technical Specification, Amendment`; the summary records that mismatch as observed tech debt instead of changing repo contracts here.
- The live submit route assigns `connector_run_id` server-side, so the tool uses a runtime-stamp-derived `Idempotency-Key`. It does not modify the API just to force a caller-chosen run ID.
- The lease TTL override is proof-local only. It is applied through the isolated runtime environment, not by changing shared repo defaults or the `project6.ps1` operator surface.
