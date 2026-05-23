# 980 - Candidate B Default Operational Acceptance

## Purpose

Record the current-main acceptance posture for Candidate B as the default eligible-PDF document-processing path that can be operated through the governed full-corpus Layer 3 workflow.

This is an acceptance checkpoint. It does not mutate selectors, broaden Candidate B beyond eligible/effective PDFs, make Candidate B the default visual lane, regenerate corpus artifacts, copy runtime roots, activate full mockups, add source families, or add provider/connector/RAG/model behavior.

```yaml
milestone: candidate_b_default_operational_acceptance_v1
checkpoint_base_main: 561b6e40c7559c1c88c9fb6a5932c605537e0a29
default_selector_scope: candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only
document_processing_engine_default_for_eligible_pdf: candidate_b_opendataloader_pdf
non_pdf_document_processing_engine_default: baseline
baseline_rollback_selector: baseline
candidate_a_visual_lane_mode: candidate_a_page_evidence_v1
candidate_b_visual_lane_mode: candidate_b_opendataloader_page_evidence_v1
candidate_b_visual_lane_default_enabled: false
selector_mutation_performed: false
workflow_schema_id: candidate_b.full_corpus_layer3_operator_workflow.v1
workflow_mode: candidate_b_full_corpus_operator_workflow_v1
lifecycle_schema_id: candidate_b.full_corpus_runtime_root_lifecycle.v1
lifecycle_mode: candidate_b_full_corpus_runtime_root_lifecycle_v1
readiness_mode: candidate_b_default_promotion_readiness_audit_v1
final_proof_mode: candidate_b_default_promotion_final_proof_v1
full_corpus_workflow_receipt_id: cb-full-corpus-operator-5be9b2dcecb9810127379140
full_corpus_workflow_receipt_hash: 5be9b2dcecb9810127379140f392b367976ab07800a0723d3008b626490db25e
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
runtime_bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
runtime_bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
runtime_downstream_proof_id: cb-runtime-downstream-proof-f0ea5bd2af66a9da70cc73bd
runtime_downstream_proof_hash: f0ea5bd2af66a9da70cc73bddaa933a01e177e662e7192d63784f551a66139ab
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
corpus_pdf_count: 69
source_directory_eligible_file_count: 71
coverage_count: 17
runtime_root_lifecycle_projection_visible: true
raw_local_path_exposed: false
raw_url_exposed: false
provider_public_url_enabled: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
browser_storage_authority_enabled: false
frontend_durable_authority_enabled: false
full_mockup_activation_enabled: false
```

## Accepted Posture

Current main proves the following bounded posture:

- omitted `document_processing_engine` selects `candidate_b_opendataloader_pdf` only after the effective content type is `application/pdf`;
- non-PDF document-processing defaults remain `baseline`;
- explicit `document_processing_engine="baseline"` remains the rollback selector and does not depend on Candidate B artifacts;
- Candidate A remains the explicit `candidate_a_page_evidence_v1` visual-lane variant and is not routed through Candidate B by omitted-engine defaulting;
- Candidate B visual evidence remains explicit through `candidate_b_opendataloader_page_evidence_v1`, not the default visual lane;
- Candidate B full-corpus runtime outputs can become governed Layer 3 material authority through `candidate_b_full_corpus_runtime_to_layer3_material_authority_v1`;
- the full-corpus workflow reaches material preview, Gate B, analysis, package/review, handoff/export, same-origin delivery, provider-private redacted prepare/status/use/revoke, internal webhook status, visual-lane status, and operator status;
- the latest lifecycle-bearing workflow receipt binds the existing baseline, Candidate A, and Candidate B runtime roots without moving, copying, seeding, or exposing raw local paths;
- default-readiness and final-proof APIs remain server-authoritative, fail closed on stale/missing evidence, and record no selector mutation in the proof response.

## Coherence Checks

The next-slice decision was checked against these questions:

- Is a new selector implementation required for this checkpoint? No. The eligible-PDF default selector already exists in current main; this checkpoint records operational acceptance over that existing selector and the full-corpus workflow evidence.
- Does this checkpoint make Candidate B the default visual lane? No. Candidate B visual evidence is admitted through `candidate_b_opendataloader_page_evidence_v1`, but the visual-lane default remains `baseline`.
- Does this checkpoint collapse runtime evidence and bundle evidence into one authority? No. Full-corpus operational evidence is runtime-root based; the default-promotion readiness audit still validates selected bundle and runtime receipts separately when that gate is exercised.
- Does this checkpoint prove broader corpus expansion? No. It is bounded to eligible/effective PDFs and preserves baseline behavior for text, CSV, XLSX, JSON, SEC EDGAR, ZIP, images, and unsupported selectors.
- Is historical reporting sufficient by itself? No. Acceptance depends on current-main guarded tests, validated triplet evidence, durable receipts, and the lifecycle-bearing merged-main workflow proof.

## Guarded Evidence

The checkpoint is guarded by:

- `backend/tests/test_nrc_aps_document_processing_default_selector.py`, covering omitted PDF defaulting, Candidate A preservation, explicit baseline rollback, non-PDF baseline defaulting, ZIP-member baseline behavior, invalid selector fallback, and retained Candidate B page evidence refs;
- `backend/tests/test_layer3_candidate_b_default_readiness.py`, covering readiness/final-proof read-only behavior, stale receipt rejection, operator status and closure binding, visual-lane status binding, delivery artifact authority binding, forbidden field rejection, redacted inspection previews, and final proof/status fail-closed behavior;
- `tools/l3-progress-check.py`, which now requires this checkpoint and the selector/readiness terms above.

## What Comes Next

Immediate next pass:

1. Keep monitoring `candidate_b_default_operational_acceptance_v1` against current-main CI and operator workflow proof receipts.
2. Re-run the focused default selector and readiness tests after any selector, visual-lane, bridge, operator workflow, or status-surface change.
3. If a full-corpus root, dependency, bridge receipt, lifecycle receipt, or API surface is missing, stop and report the exact blocker instead of generating substitute evidence.

The first post-acceptance runtime/status slice is `candidate_b_operator_status_eligibility_v1`, recorded in `981-cb-operator-status-eligibility.md`.

Mid-term passes:

1. Turn the operator workflow into the primary repeatable acceptance route for future Candidate B corpus runs, including clear run IDs, receipt IDs, status endpoint inspection, and rollback instructions.
2. Improve operator-visible status surfaces only where they reduce ambiguity for real corpus operations: selected corpus, eligible/skipped/failed counts, bridge receipt, lifecycle receipt, downstream proof, artifact-family status, and rollback state.
3. Add acceptance smoke coverage for any future workflow-runner changes that could break lifecycle binding, receipt redaction, downstream proof coverage, or baseline rollback.
4. Keep default-readiness/final-proof gates separate from runtime workflow execution so readiness can fail closed on stale selected evidence without blocking the lower-level runtime workflow status surface.

Long-term passes:

1. Treat Candidate B as the accepted default for eligible/effective PDF corpus processing while preserving explicit baseline rollback and Candidate A visual-lane semantics.
2. Decide any broader corpus scope only through a separate freeze and proof path; do not infer Office, image/OCR, ZIP-member, mixed corpus, or arbitrary source expansion from this acceptance.
3. Decide any production operator UI expansion separately, after the current receipt/status model is stable enough to show provenance, blocked reasons, rollback state, and artifact inspection without raw path or URL leakage.
4. Decide any RAG/vector/model runtime, provider object write, connector dispatch, auth/security expansion, or full mockup activation as separate product-authority slices with their own fail-closed proof.

## Stop Conditions

Stop or block the posture if any of the following appear:

- omitted eligible-PDF processing no longer selects Candidate B;
- non-PDF defaults no longer remain baseline;
- explicit baseline rollback stops bypassing Candidate B artifacts;
- Candidate A visual-lane selection is weakened or rerouted through Candidate B;
- Candidate B visual lane becomes default without a separate admission;
- runtime bridge receipts, lifecycle receipts, downstream proof receipts, or final proof receipts become stale, missing, hash-mismatched, or unredacted;
- operator surfaces expose raw local paths, raw URLs, provider-private tokens, provider object writes, connector dispatch, browser storage authority, frontend-only durable authority, RAG/model runtime, or full mockup behavior.
