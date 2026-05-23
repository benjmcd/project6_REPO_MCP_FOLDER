# 972 - Candidate B Full-Corpus Compare Triplet Validation

## Purpose

Record the first same-checkout full-corpus baseline / Candidate A / Candidate B comparison triplet for the 69-PDF NRC APS local corpus and close the blocker identified in `971-cb-full-corpus-run.md`.

This is a validate-only checkpoint. It introduces no runtime, route, DTO, model, migration, rendered UI, parser, provider, connector, auth/security, source-expansion, RAG/vector/model, browser-storage, frontend-only durable-authority, or full-mockup behavior change.

```yaml
milestone: candidate_b_full_corpus_compare_triplet_v1
current_main: aac0817cdb7247d647cb434fbb43e1303d3f0933
validation_schema_id: aps.full_corpus_compare_triplet_validation.v1
validator: tools/validate_full_corpus_triplet.py
validator_result: passed
validate_only: true
artifacts_seeded_or_generated: false
corpus_pdf_count: 69
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
candidate_b_full_corpus_runtime_to_layer3_material_authority_v1: requires_separate_current_main_admission
existing_layer3_candidate_b_runtime_bridge_scope: workbench_fixture_target_set
```

## Authority Inputs

- Current main at `aac0817cdb7247d647cb434fbb43e1303d3f0933`.
- `docs/nrc_adams/local_corpus_e2e_runbook.md`.
- `tools/run_nrc_aps_local_corpus_e2e.py`.
- `tools/validate_full_corpus_triplet.py`.
- `backend/app/services/review_nrc_aps_workbench_compare.py`.
- `backend/app/services/layer3_candidate_b_runtime_bridge.py`.
- Baseline receipt: `backend/app/storage_test_runtime/lc_e2e/baseline-full-corpus-v2/local_corpus_e2e_summary.json`.
- Candidate A receipt: `backend/app/storage_test_runtime/lc_e2e/candidate-a-full-corpus-v1/local_corpus_e2e_summary.json`.
- Candidate B receipt: `backend/app/storage_test_runtime/lc_e2e/cb-full-corpus-v1/local_corpus_e2e_summary.json`.

## Executed Proof

Baseline rollback proof:

```powershell
..\..\.venvs\phase7a-py311\Scripts\python.exe .\tools\run_nrc_aps_local_corpus_e2e.py --runtime-root .\backend\app\storage_test_runtime\lc_e2e\baseline-full-corpus-v2
```

Candidate A PageEvidence comparison proof:

```powershell
..\..\.venvs\phase7a-py311\Scripts\python.exe .\tools\run_nrc_aps_local_corpus_e2e.py --document-processing-engine baseline --visual-lane-mode candidate_a_page_evidence_v1 --runtime-root .\backend\app\storage_test_runtime\lc_e2e\candidate-a-full-corpus-v1
```

Triplet validator:

```powershell
..\..\.venvs\phase7a-py311\Scripts\python.exe .\tools\validate_full_corpus_triplet.py --checkout-root .
```

## Result

| Leg | Run ID | Engine | Visual lane | Targets | Status |
|---|---|---|---|---:|---|
| Baseline | `7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20` | `baseline` | `baseline` | 69 | 69 `recommended` |
| Candidate A | `9b09f014-95f9-41cb-820c-8f5296a993bc` | `baseline` | `candidate_a_page_evidence_v1` | 69 | 69 `recommended` |
| Candidate B | `f644b3f6-a7a9-4889-84d9-d842f5d12e79` | `candidate_b_opendataloader_pdf` | `candidate_b_opendataloader_page_evidence_v1` | 69 | 69 `recommended` |

All three legs share the same ordered 69-target accession set:

```yaml
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
accession_head:
  - LOCALAPS00001
  - LOCALAPS00002
  - LOCALAPS00003
accession_tail:
  - LOCALAPS00067
  - LOCALAPS00068
  - LOCALAPS00069
```

Request-config validation proved the baseline and Candidate A legs requested explicit baseline rollback after Candidate B default promotion:

| Leg | `document_processing_engine` | `document_processing_engine_explicit` | `visual_lane_mode` |
|---|---|---|---|
| Baseline | `baseline` | `true` | `baseline` |
| Candidate A | `baseline` | `true` | `candidate_a_page_evidence_v1` |
| Candidate B | `candidate_b_opendataloader_pdf` | `true` | `candidate_b_opendataloader_page_evidence_v1` |

All validate-only gates passed for all three legs:

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

## Metrics

| Leg | OCR files | Table files | Candidate B extractor files | Ordered-unit files | Ordered units | Candidate B visual refs | Retained source-PDF refs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 47 | 48 | 0 | 69 | 216022 | 0 | 0 |
| Candidate A | 47 | 48 | 0 | 69 | 216022 | 0 | 0 |
| Candidate B | 0 | 0 | 69 | 68 | 52368 | 1270 | 1270 |

## Bridge Re-Audit

Grill-me coherence check:

Question: Does this pass now prove the full-corpus Candidate B -> Layer 3 material/package/delivery bridge?

Recommended answer: No. It proves the same-checkout full-corpus compare triplet that was missing in checkpoint 971. The existing runtime bridge is still explicitly tied to `compose_workbench_compare_targets`, which emits a workbench fixture target set. A new current-main admission is still required before the 69-PDF full-corpus target set can become Layer 3 material authority.

Current exact posture:

```yaml
candidate_b_full_corpus_processing: proven
nrc_aps_downstream_artifact_chain: proven
baseline_full_corpus_rollback: proven
candidate_a_full_corpus_page_evidence_selection: proven
same_checkout_baseline_candidate_a_candidate_b_compare_triplet: proven
layer3_full_corpus_material_bridge_for_this_triplet: blocked_pending_admission
layer3_package_handoff_delivery_for_this_triplet: not_executed
```

## Next Exact Posture

The next admitted slice should be:

```text
candidate_b_full_corpus_runtime_to_layer3_material_authority_v1
```

That bridge should accept the validated full-corpus triplet receipt, preserve the baseline/Candidate A regression linkage, avoid the fixture-manifest workbench target-set assumption, and expose only a bounded redacted material-authority receipt into Layer 3. It must not ingest arbitrary PDFs/images into text-material analysis, broaden Candidate B beyond eligible/effective PDFs, weaken rollback, add provider writes, add connector dispatch, add RAG/vector/model runtime, activate full mockups, or expose raw local paths/URLs in operator surfaces.

## Negative Invariants

- Baseline remains rollback and can still be explicitly selected.
- Candidate A remains the admitted `candidate_a_page_evidence_v1` visual-lane variant over the baseline processing engine.
- Candidate B remains the default only for eligible/effective PDF processing.
- The validator is validate-only and did not seed or generate artifacts.
- The raw local-corpus summaries remain internal proof receipts and contain local runtime references by design.
- No provider object writes, arbitrary connector dispatch, broad source expansion, RAG/vector/model runtime, auth/security changes, browser-storage authority, frontend-only durable authority, or full mockup activation were introduced.
