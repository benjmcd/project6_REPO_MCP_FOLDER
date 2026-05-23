# 981 - Candidate B Operator Status Eligibility

## Purpose

Make the Candidate B full-corpus operator workflow status surface more directly usable by exposing explicit eligibility and rollback summaries from the governed receipt/status path.

This is a bounded runtime/status-surface improvement. It does not rerun the corpus, mutate selectors, broaden Candidate B beyond eligible/effective PDFs, activate Candidate B as the default visual lane, add source families, copy runtime roots, write provider objects, dispatch arbitrary connectors, add RAG/model runtime, or activate full mockups.

```yaml
milestone: candidate_b_operator_status_eligibility_v1
checkpoint_base_main: 273cb7aa67b500235e1dfbc3a44e631f8a95fb1d
workflow_runner: tools/run_candidate_b_full_corpus_operator_workflow.py
status_service: backend/app/services/layer3_candidate_b_full_corpus_operator_workflow_status.py
status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
workflow_schema_id: candidate_b.full_corpus_layer3_operator_workflow.v1
workflow_mode: candidate_b_full_corpus_operator_workflow_v1
status_schema_id: layer3.candidate_b_full_corpus_operator_workflow_status.v1
status_mode: candidate_b_full_corpus_operator_workflow_status_v1
eligibility_summary_projection_visible: true
baseline_rollback_projection_visible: true
eligible_pdf_count_source: candidate_b_target_status_counts.recommended
skipped_pdf_count_required: 0
failed_pdf_count_required: 0
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
```

## Runtime Change

The operator workflow receipt now records:

- `corpus.eligibility_summary.corpus_pdf_count`;
- `corpus.eligibility_summary.eligible_pdf_count`;
- `corpus.eligibility_summary.skipped_pdf_count`;
- `corpus.eligibility_summary.failed_pdf_count`;
- `corpus.eligibility_summary.source_directory_eligible_file_count`;
- `corpus.eligibility_summary.source_directory_extra_material_file_count`;
- `corpus.eligibility_summary.all_eligible_pdfs_processed`;
- `corpus.eligibility_summary.candidate_b_target_status_counts`;
- `baseline_rollback.selector`;
- `baseline_rollback.explicit_document_processing_engine`;
- `baseline_rollback.depends_on_candidate_b_artifacts`;
- `baseline_rollback.candidate_a_visual_lane_preserved`;
- `baseline_rollback.rollback_requires_selector_mutation`.

The status service derives the same eligibility summary from the receipt's validated target-status counts and fails closed when:

- the selected receipt has no target-status counts;
- `candidate_b.recommended` does not equal the corpus PDF count;
- skipped or failed Candidate B PDF counts are nonzero;
- source-directory eligible material count is lower than eligible PDF count;
- a supplied receipt eligibility summary contradicts the derived summary;
- supplied baseline rollback evidence contradicts the accepted baseline rollback model.

## Operator Value

Operators can now inspect one status response and see:

- which workflow receipt is selected;
- which bridge/downstream/lifecycle receipts are selected;
- how many corpus PDFs were eligible and processed;
- whether any eligible PDFs were skipped or failed;
- whether the selected status still permits explicit baseline rollback;
- whether rollback depends on Candidate B artifacts;
- whether Candidate A visual-lane preservation is still true;
- whether the status surface remains redacted and read-only.

## Guarded Evidence

The slice is guarded by:

- `tests/test_candidate_b_full_corpus_operator_workflow.py::test_operator_eligibility_summary_records_counts_and_rollback`;
- `backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_status.py::test_candidate_b_full_corpus_operator_workflow_status_is_read_only_and_redacted`;
- `backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_status.py::test_candidate_b_full_corpus_operator_workflow_status_rejects_incomplete_eligibility`;
- `backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_status.py::test_candidate_b_full_corpus_operator_workflow_status_rejects_stale_rollback`;
- `tools/l3-progress-check.py`.

## Next Exact Posture

```text
candidate_b_operator_repeatability_status_gap_audit_v1
```

After this slice lands, the next pass should audit whether any remaining operator repeatability gap is still real against the now-explicit workflow receipt, eligibility summary, rollback summary, runtime-root lifecycle, Layer 3 bridge receipt, downstream proof receipt, artifact-family status, and default operational acceptance checkpoint. Do not add another status surface unless the audit names a concrete operator-use gap.
