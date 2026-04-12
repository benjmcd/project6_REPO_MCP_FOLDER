# 05T - Candidate B OpenDataLoader Compare Surface Implementation Plan

## Purpose

Define the smallest justified implementation lane for a polished, repo-native Candidate B compare surface.

This plan is intentionally narrower than product integration work.
It is only for a first-class workbench compare flow.

---

## Canonical source of truth

Use these files as authority before editing:

- `project6.ps1`
- `tools/run_nrc_aps_document_processing_proof.py`
- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- committed Candidate B reports under `tests/reports/`

Current repo-confirmed gap:

- the lower-layer proof lane already has a repo-native entrypoint
- Candidate B already has an executable workbench harness
- Candidate B does not yet have a repo-native compare action
- Candidate B still depends on a prior compare artifact input instead of generating a fresh compare-ready baseline summary
- Candidate B does not yet have a dedicated compare pytest surface

---

## Goal

Add a repo-native Candidate B compare workflow that:

- starts from current `main`
- runs against isolated runtime state
- avoids overwriting the committed historical Candidate B reports by default
- compares against a fresh baseline summary generated during the same run
- remains workbench-only and non-integrated

---

## Explicit non-goals

Do not use this lane to:

- change `backend/app/services/...`
- change `backend/app/api/...`
- change review UI files
- change runtime selector/defaulting behavior
- change persistence schemas
- add admission or promotion logic
- add endpoint or export surfaces

---

## Frozen implementation decisions

These decisions are now fixed for the first implementation pass.
Do not reopen them during coding unless a repo-confirmed blocker appears.

### 1. Exact top-level action name

The new repo-native action name is fixed:

- `compare-nrc-aps-candidate-b`

Do not introduce alternate action names in the first pass.

### 2. Exact public compare-runner CLI

The compare runner public CLI is fixed to:

- `py -3.12 tools/run_nrc_aps_candidate_b_compare.py`
- optional `--run-root <path>`
- optional `--plan-only`

No `--dry-run` alias in the first pass.
No additional public flags in the first pass unless a repo-confirmed blocker requires them.

### 3. Exact baseline-tool CLI

The baseline-summary tool public CLI is fixed to:

- `py -3.12 tools/run_nrc_aps_candidate_b_baseline.py`
- required `--runtime-root <path>`
- required `--proof-report <path>`
- required `--out <path>`

It must not require a historical compare artifact path.

### 4. Exact support-harness input contract

The support harness must accept exactly one baseline source:

- new normal path: `--baseline-summary <path>`
- retained legacy manual path: `--first-run-compare-report <path>`

If both are supplied, fail closed.
If neither is supplied, fail closed.
The compare runner must use `--baseline-summary`.
The legacy `--first-run-compare-report` path remains only for historical/manual workbench use in the first pass.

### 5. Exact runtime-isolation posture

The compare lane must use explicit run-local proof runtimes, not shared repo tiers or historical roots.

For a run root `<run-root>`:

- baseline-before proof runtime root = `<run-root>/baseline-before/runtime`
- baseline-after proof runtime root = `<run-root>/baseline-after/runtime`

The compare runner must call `tools/run_nrc_aps_document_processing_proof.py` with explicit:

- `--runtime-root <run-root>/baseline-before/runtime`
- `--report <run-root>/baseline-before/nrc_aps_document_processing_proof_report.json`
- `--artifact-report <run-root>/baseline-before/nrc_aps_artifact_ingestion_validation_report.json`
- `--content-index-report <run-root>/baseline-before/nrc_aps_content_index_validation_report.json`

and the same shape under `<run-root>/baseline-after/...`.

Use `--require-ocr` in both baseline proof calls.
Do not rely on shared `app/storage_test_runtime`, `app/storage_eval`, `attached_eval.db`, or committed historical Candidate B report paths as the active compare runtime.

### 6. Exact default output posture

If `--run-root` is not supplied, the compare runner must create:

- `tests/reports/cb-compare-<run_id>/`

Within that run root, the top-level durable outputs are fixed to:

- `baseline-summary.json`
- `proof.json`
- `compare.json`
- `retain.json`
- `raw/`

Fresh runs must not overwrite:

- `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json`

No mirroring or copy-back into those historical top-level files in the first pass.

### 7. Exact baseline-summary schema

The baseline-summary artifact schema is fixed to:

- `schema_id = "aps.candidate_b_baseline_summary.v1"`

Required top-level fields:

- `schema_id`
- `generated_at_utc`
- `proof_report_ref`
- `runtime_root`
- `corpus_manifest_ref`
- `corpus_manifest_sha256`
- `documents`

Required per-document fields:

- `fixture_id`
- `document_ref`
- `document_sha256`
- `baseline`

Required `baseline` subfields:

- `page_count`
- `normalized_char_count`
- `document_class`
- `degradation_codes`

In the first pass, the support harness may consume only `page_count` and `normalized_char_count`,
but all required fields above must still be emitted for reviewer context and report continuity.

### 8. Exact non-interference proof scope

Protected-diff serialization is out of scope for the first compare-surface pass.

The first pass non-interference proof is limited to:

- before/after lower-layer proof staying green
- output-root allowlist enforcement
- no forbidden-surface edits

Do not add serialized protected-diff inventory in this lane.
That remains a later hardening lane if still wanted afterward.

### 9. Exact corpus posture

Do not add a new Candidate B sidecar manifest in the first pass.
Use the existing base manifest plus the already-frozen labels sidecar only.

---

## Required implementation surfaces

### 1. Top-level command entrypoint

Add one new `project6.ps1` action:

- exact action name: `compare-nrc-aps-candidate-b`

Responsibilities:

- run Python/Java/package preflight
- call the dedicated Candidate B compare runner
- keep runtime isolation consistent with the explicit run-local proof posture frozen above
- expose no additional action-specific PowerShell parameters in the first pass

### 2. Dedicated compare runner

Add one new orchestration tool:

- exact file: `tools/run_nrc_aps_candidate_b_compare.py`

Responsibilities:

- create or validate an isolated run root
- trigger fresh lower-layer baseline proof before Candidate B
- generate a fresh Candidate B-compatible baseline summary
- launch Candidate B through the existing support harness
- trigger lower-layer baseline proof after Candidate B
- write proof, compare, retention, and baseline-summary artifacts under the run root
- fail closed on missing preflight, missing baseline summary, or outputs outside approved roots

### 3. Fresh baseline-summary generator

Add one fresh baseline-summary surface instead of widening the stable proof report schema:

- exact file: `tools/run_nrc_aps_candidate_b_baseline.py`

Responsibilities:

- read the isolated lower-layer proof runtime/output state
- emit per-fixture baseline summaries in the shape Candidate B compare needs
- remove reliance on a manually supplied historical compare artifact path

This is the main architectural requirement for a polished compare surface.

### 4. Candidate B support harness tightening

Update `tests/support_nrc_aps_candidate_b_opendataloader.py` only as needed to:

- accept fresh baseline-summary input rather than requiring a historical compare artifact
- accept explicit run-scoped output paths
- keep raw outputs and durable reports under the caller-specified run root
- preserve the legacy historical compare-artifact input for manual use only
- fail closed if both baseline input modes are supplied at once

### 5. Dedicated validate-only compare tests

Add one compare-surface test file:

- exact file: `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`

Responsibilities:

- validate CLI parsing and required arguments
- validate fail-closed behavior on missing baseline-summary input
- validate run-root/output-root planning
- validate report-schema shape using fixtures or canned payloads
- validate mutual exclusion of `--baseline-summary` and `--first-run-compare-report`
- avoid generating ODL outputs during normal pytest runs

---

## Output posture

Do not use the committed historical Candidate B report paths as default write targets for fresh reruns.

Fixed output posture:

- one run-scoped root under `tests/reports/`
- exact default pattern: `tests/reports/cb-compare-<run_id>/`

Within that run root:

- `baseline-summary.json`
- `proof.json`
- `compare.json`
- `retain.json`
- `raw/`

The committed historical top-level Candidate B report files should remain reviewable evidence, not the default destination for reruns.

---

## Blast radius

Expected touched files for the implementation lane:

- `project6.ps1`
- `tools/run_nrc_aps_candidate_b_compare.py` (new)
- `tools/run_nrc_aps_candidate_b_baseline.py` (new)
- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py` (new)
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt` (read-only package/hash authority only)
- Candidate B planning docs that need command/output updates after implementation lands

Expected untouched files:

- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_page_evidence.py`
- all API route files
- all review UI files
- corpus manifest files beyond the already-frozen labels sidecar

---

## Implementation order

1. add the fresh baseline-summary tool
2. add the compare runner
3. wire the new `project6.ps1` action
4. tighten support-harness path injection and baseline-summary consumption
5. add validate-only compare tests
6. run validate-only verification
7. run one explicit isolated artifact-generating acceptance pass only after validate-only verification is green

---

## Stop rules

Stop and re-audit if any of the following becomes necessary:

- changing backend service code
- changing API or review UI surfaces
- changing runtime admission/default behavior
- modifying baseline lower-layer semantics instead of just consuming their outputs
- requiring committed raw Candidate B outputs as part of normal operation
- needing a new sidecar corpus manifest
- needing protected-diff serialization to make the first pass viable

---

## Sizing

This is a moderate implementation lane.

Expected effort:

- about 2 to 4 focused days

Expected result:

- a first-class developer/operator compare surface
- not a productized runtime feature
