# 971 - Candidate B Full-Corpus Operator Run Checkpoint

## Purpose

Record the first current-main Candidate B full-corpus operator proof and the exact remaining bridge gap before this proof can be treated as a repeatable full-corpus Candidate B -> Layer 3 operator workflow.

This is a checkpoint/audit artifact only. It introduces no runtime, route, DTO, model, migration, rendered UI, parser, provider, connector, auth/security, source-expansion, RAG/vector/model, browser-storage, frontend-only durable-authority, or full-mockup behavior change.

```yaml
milestone: candidate_b_full_corpus_operator_run_v1
current_main: 7f2d93c392f6e42ef0812c10680c209b7b1e17eb
run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
summary_receipt: backend/app/storage_test_runtime/lc_e2e/cb-full-corpus-v1/local_corpus_e2e_summary.json
run_result: passed
corpus_pdf_count: 69
document_processing_engine: candidate_b_opendataloader_pdf
visual_lane_mode: candidate_b_opendataloader_page_evidence_v1
target_outcomes_recommended: 69
candidate_b_extractor_file_count: 69
candidate_b_ordered_unit_file_count: 68
candidate_b_ordered_unit_total: 52368
candidate_b_visual_ref_total: 1270
candidate_b_retained_source_pdf_ref_count: 1270
unresolved_visual_refs: 0
validate_wb_prep_blocker: baseline_run_missing
layer3_bridge_status_for_this_exact_run: not_executed_blocked_by_missing_same_checkout_baseline_candidate_a_compare_authority
```

## Authority Inputs

- Current main at `7f2d93c392f6e42ef0812c10680c209b7b1e17eb`.
- `docs/nrc_adams/local_corpus_e2e_runbook.md`.
- `tools/run_nrc_aps_local_corpus_e2e.py`.
- `tools/validate_wb_prep.py`.
- `backend/app/services/review_nrc_aps_workbench_compare.py`.
- `backend/app/services/layer3_candidate_b_runtime_bridge.py`.
- `backend/app/services/layer3_candidate_b_downstream_proof.py`.
- The isolated local runtime summary under `backend/app/storage_test_runtime/lc_e2e/cb-full-corpus-v1/`.

## Executed Proof

```powershell
..\..\.venvs\phase7a-py311\Scripts\python.exe .\tools\run_nrc_aps_local_corpus_e2e.py --document-processing-engine candidate_b_opendataloader_pdf --visual-lane-mode candidate_b_opendataloader_page_evidence_v1 --runtime-root .\backend\app\storage_test_runtime\lc_e2e\cb-full-corpus-v1
```

The proof used the current-main local 69-PDF corpus at `data_demo/nrc_adams_documents_for_testing` and ran inside an isolated runtime under `backend/app/storage_test_runtime/lc_e2e/cb-full-corpus-v1`.

## Result

| Check | Result |
|---|---|
| Candidate B package preflight | `opendataloader-pdf==2.0.0` importable from the Phase 7A interpreter |
| Corpus discovery | 69 PDFs discovered, including the dynamic `new_files_for_testing_added` folder |
| Candidate B engine | `candidate_b_opendataloader_pdf` |
| Candidate B visual lane | `candidate_b_opendataloader_page_evidence_v1` |
| Run status | passed |
| Connector run id | `f644b3f6-a7a9-4889-84d9-d842f5d12e79` |
| Target outcomes | 69 `recommended`, 0 failed |
| Candidate B extraction | 69 files used the Candidate B OpenDataLoader extractor |
| Ordered-unit evidence | 68 files with ordered units, 52368 ordered units total |
| Visual/page evidence | 1270 Candidate B visual refs and 1270 retained source-PDF refs |
| Unresolved visual refs | 0 |
| Search smoke | 1 hit |
| NRC client trace | 7 search calls, 69 document fetches, 69 downloads |

The proof produced and validated the NRC APS downstream artifact chain:

| Artifact family | Count |
|---|---:|
| Evidence bundles | 2 |
| Citation packs | 2 |
| Evidence reports | 2 |
| Evidence report exports | 2 |
| Evidence report export packages | 1 |
| Context packets | 3 |
| Context dossiers | 1 |
| Deterministic insight artifacts | 1 |
| Deterministic challenge artifacts | 1 |
| Deterministic challenge review packets | 1 |

All validate-only gate reports passed for the isolated run:

- `artifact_ingestion`
- `content_index`
- `context_dossier`
- `context_packet`
- `deterministic_challenge_artifact`
- `deterministic_challenge_review_packet`
- `deterministic_insight_artifact`
- `evidence_bundle`
- `evidence_citation_pack`
- `evidence_report`
- `evidence_report_export`
- `evidence_report_export_package`

## Nonblocking Findings

The run completed with these nonblocking findings, all already represented in the summary receipt:

- `technical_spec_document_type_vocabulary_mismatch`
- `idempotency_key_run_id_dependency_unavailable`
- `monolithic_router_dependency_surface`
- `proof_runtime_connector_lease_ttl_override`
- `dynamic_local_corpus_folder_set`

These are not Candidate B processing failures. They are operator-readiness observations for later cleanup if this workflow becomes a repeated production-adjacent run.

## Bridge Re-Audit

Grill-me coherence check:

Question: Can this checkpoint claim a full-corpus Candidate B -> Layer 3 material/package/delivery proof for this exact run?

Recommended answer: No. It can claim a successful full-corpus Candidate B processing run plus NRC APS downstream artifact/gate proof. It cannot claim the exact run reached the Layer 3 runtime bridge or Layer 3 package/delivery path in this pass.

Reason:

- `tools/validate_wb_prep.py --checkout-root .` failed closed with `baseline_run_missing` in this fresh current-main worktree.
- `backend/app/services/layer3_candidate_b_runtime_bridge.py` requires `candidate_b_run_id`, `baseline_run_id`, and `candidate_a_run_id`.
- `backend/app/services/review_nrc_aps_workbench_compare.py` builds Candidate B runtime bridge material from a shared fixture-id intersection across baseline, Candidate A, and Candidate B targets.
- This clean full-corpus lane has the Candidate B 69-PDF runtime proof, but it does not have same-checkout baseline and Candidate A compare authority for the same corpus.

Therefore the current exact posture is:

```yaml
candidate_b_full_corpus_processing: proven
nrc_aps_downstream_artifact_chain: proven
validate_only_gates: proven
same_checkout_baseline_candidate_a_compare_set: missing
layer3_material_bridge_for_this_exact_run: blocked
layer3_package_handoff_delivery_for_this_exact_run: not_executed
```

## Next Exact Posture

The next admitted slice should be one of these, in order of product clarity:

1. `candidate_b_full_corpus_compare_triplet_v1`

   Generate or validate same-checkout full-corpus baseline and Candidate A local-corpus runs, then prove a shared compare target set with the Candidate B run. This preserves the existing bridge requirement that Candidate B material authority is tied to baseline and Candidate A comparison evidence.

2. `candidate_b_full_corpus_runtime_to_layer3_material_authority_v1`

   If product authority decides full-corpus Candidate B Layer 3 material authority should not depend on the fixture-manifest workbench compare intersection, admit a separate full-corpus runtime bridge. That bridge must still preserve baseline rollback and Candidate A regression evidence through an explicit audit/receipt model.

3. `candidate_b_full_corpus_operator_runbook_v1`

   Once either bridge authority exists, write the operator runbook/checkpoint for repeating the workflow without exposing raw local paths, raw URLs, provider tokens, credentials, browser-storage authority, or frontend-only durable authority.

## High-ROI Improvements Identified

- Keep the 69-PDF full-corpus proof out of ordinary PR CI. It is an operator/checkpoint proof, not a fast regression check.
- Add a redacted operator checkpoint projection before exposing this proof in rendered UI. The raw summary is an internal proof receipt and contains local runtime references by design.
- Reduce the full-corpus bridge blocker by either creating the same-corpus baseline/Candidate A/Candidate B compare triplet or admitting a bridge that is explicitly full-corpus rather than workbench-fixture-scoped.
- Keep the existing sharded PR checks as the fast guardrail; use this proof only when corpus-scale confidence is required.

## Negative Invariants

- Do not change Candidate A semantics.
- Do not remove baseline rollback or fail-closed behavior.
- Do not broaden Candidate B default beyond eligible/effective PDFs through this checkpoint.
- Do not ingest arbitrary PDFs/images into Layer 3 text-material analysis without a separately admitted bridge.
- Do not add provider object writes, arbitrary connector dispatch, broad source expansion, RAG/vector/model runtime, auth/security changes, browser-storage authority, frontend-only durable authority, or full mockup activation.
- Do not expose raw local paths, raw URLs, provider keys, local roots, or unredacted artifact refs in rendered/operator surfaces.
