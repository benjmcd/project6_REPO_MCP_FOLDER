# 978 - Candidate B Full-Corpus Runtime Root Lifecycle

## Purpose

Record the governed runtime-root lifecycle binding for the Candidate B full-corpus operator workflow. The operator runner now validates the selected baseline, Candidate A, and Candidate B runtime roots, requires one admitted `storage_test_runtime/lc_e2e` or `storage/lc_e2e` parent, hashes the summary/database authority files, writes a redacted lifecycle receipt, and includes that receipt in the operator workflow/status projection.

```yaml
milestone: candidate_b_full_corpus_runtime_root_lifecycle_v1
current_main: 5122ae632d6adc18791365cf006918786b398119
runner: tools/run_candidate_b_full_corpus_operator_workflow.py
status_service: backend/app/services/layer3_candidate_b_full_corpus_operator_workflow_status.py
test: tests/test_candidate_b_full_corpus_operator_workflow.py
status_test: backend/tests/test_layer3_candidate_b_full_corpus_operator_workflow_status.py
runbook: docs/nrc_adams/local_corpus_e2e_runbook.md
schema_id: candidate_b.full_corpus_runtime_root_lifecycle.v1
lifecycle_mode: candidate_b_full_corpus_runtime_root_lifecycle_v1
receipt_id_prefix: cb-full-corpus-runtime-roots-
root_count: 3
validate_only_triplet: true
runtime_roots_moved_or_copied: false
runtime_artifacts_seeded_by_lifecycle: false
raw_local_path_exposed: false
raw_url_exposed: false
```

## Scope

This slice does not regenerate the corpus, copy runtime roots, import broad runtime storage, or add a new source family. It binds already validated full-corpus runtime evidence to a durable receipt so an operator can distinguish a live root authority binding from a session-local helper assumption.

The lifecycle receipt records:

- baseline run id, Candidate A run id, and Candidate B run id;
- compare target set hash;
- one admitted runtime parent reference;
- per-run `local_corpus_e2e_summary.json` hash;
- per-run `lc.db` hash;
- redacted or repo-relative refs only;
- negative invariants proving no root movement, no artifact seeding, no raw path/URL exposure, no selector broadening, and no frontend durable authority.

## Status Projection

The Candidate B full-corpus operator workflow status surface remains read-only. When a workflow receipt includes a runtime-root lifecycle projection, the status response reports:

```text
runtime_root_lifecycle.available: true
runtime_root_lifecycle.lifecycle_receipt_id: cb-full-corpus-runtime-roots-...
runtime_root_lifecycle.root_count: 3
runtime_root_lifecycle.validate_only_triplet: true
operator_projection.runtime_root_lifecycle_projection_visible: true
```

Older workflow receipts that do not include this projection remain readable, but they report `runtime_root_lifecycle.available: false`.

## Verification

Focused checks for this slice:

```powershell
py -3.12 -m py_compile .\tools\run_candidate_b_full_corpus_operator_workflow.py .\backend\app\services\layer3_candidate_b_full_corpus_operator_workflow_status.py
py -3.12 -m pytest .\tests\test_candidate_b_full_corpus_operator_workflow.py .\backend\tests\test_layer3_candidate_b_full_corpus_operator_workflow_status.py
python .\tools\l3-progress-check.py
```

## Remaining Work

The next exact posture remains an operator-repeatability proof from a clean current-main checkout with live full-corpus roots available. If a fresh 40-50 minute corpus regeneration is required, run it only when current evidence is stale, missing, or a concrete defect appears. Do not add proof variants, broader source ingestion, provider object writes, connector dispatch, RAG/vector/model runtime, auth/security changes, browser-storage authority, frontend-only durable authority, or full mockup activation as part of this lifecycle slice.
