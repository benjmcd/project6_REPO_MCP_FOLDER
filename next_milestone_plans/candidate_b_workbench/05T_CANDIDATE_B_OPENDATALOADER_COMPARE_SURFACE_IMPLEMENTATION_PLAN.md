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

## Required implementation surfaces

### 1. Top-level command entrypoint

Add one new `project6.ps1` action:

- recommended action name: `compare-nrc-aps-candidate-b`

Responsibilities:

- run Python/Java/package preflight
- call the dedicated Candidate B compare runner
- keep runtime isolation consistent with other repo-native proof/gate actions

### 2. Dedicated compare runner

Add one new orchestration tool:

- recommended file: `tools/run_nrc_aps_candidate_b_compare.py`

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

- recommended file: `tools/run_nrc_aps_candidate_b_baseline.py`

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
- serialize protected-diff inventory if the lane chooses to harden non-interference evidence in the same pass

### 5. Dedicated validate-only compare tests

Add one compare-surface test file:

- recommended file: `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`

Responsibilities:

- validate CLI parsing and required arguments
- validate fail-closed behavior on missing baseline-summary input
- validate run-root/output-root planning
- validate report-schema shape using fixtures or canned payloads
- avoid generating ODL outputs during normal pytest runs

---

## Output posture

Do not use the committed historical Candidate B report paths as default write targets for fresh reruns.

Preferred output posture:

- one run-scoped root under `tests/reports/`
- recommended pattern: `tests/reports/cb-compare-<run_id>/`

Within that run root:

- `baseline.json`
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
- Candidate B planning docs that need command/output updates after implementation lands

Expected untouched files:

- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_page_evidence.py`
- all API route files
- all review UI files

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

---

## Sizing

This is a moderate implementation lane.

Expected effort:

- about 2 to 4 focused days

Expected result:

- a first-class developer/operator compare surface
- not a productized runtime feature
