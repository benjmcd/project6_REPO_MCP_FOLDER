# 06I Local Performance Baseline and Regression Check Specification

## Purpose

Define the local performance acceptance gate for the first integrated selector/bootstrap pass.

This spec exists because no repo-advertised benchmark surface was found in the scanned authority areas.
So performance acceptance must be controlled explicitly and locally.

## Scope

This spec applies to:

- baseline-only selector bootstrap
- any later candidate selector implementation that claims to preserve baseline-equivalent behavior in the integrated path

It does **not** apply to:
- uncontrolled experiment-only worktrees
- arbitrary bakeoff explorations with intentionally different behavior

## Fixture sources

### Tier 1 — Lightweight deterministic core-processing corpus
Source evidence:
- `tests/test_nrc_aps_document_processing.py`
- fixture root: `tests/fixtures/nrc_aps_docs/v1`

Primary fixture set:
- `born_digital.pdf`
- `mixed.pdf`
- `scanned.pdf`

Reason:
- these are active, deterministic, already used by the owner-path tests
- they exercise born-digital, mixed, and OCR-heavy/scanned behavior

### Tier 2 — Heavier artifact-aware corpus
Source evidence:
- `backend/tests/test_visual_artifact_pipeline.py`

Primary source roots:
- `handoff/tests/fixtures/nrc_aps_docs/v1`
- `data_demo/nrc_adams_documents_for_testing`

Preferred heavier sample:
- up to 3 files from the real ADAMS subset listed in the test when present
- otherwise fallback to at least 3 PDF fixtures available from the declared roots

Reason:
- this path exercises real artifact generation and downstream persistence expectations

## Measurement policy

### General rules
1. Compare baseline vs candidate on the **same machine/environment**.
2. Use the **same Python interpreter** and dependency state.
3. Use the **same storage sandbox policy** for compared runs.
4. Run each fixture at least **3 times** after one warm-up pass.
5. Compare using **median wall-clock time** per fixture and per tier aggregate.
6. Record whether artifact generation is enabled for the tier.

### Tier 1 measurement
Measure:
- `process_document(...)` wall-clock time for each of the 3 primary fixtures
- aggregate median across the 3 fixtures

### Tier 2 measurement
Measure:
- end-to-end artifact-aware processing wall-clock on the selected heavier corpus
- aggregate median across the chosen files
- artifact generation enabled

## Output-stability precondition

A candidate cannot “pass performance” if it fails output stability first.

At minimum, the compared runs must preserve the expected current-scope invariants for the tested path, including:
- no public contract drift
- no artifact-equivalence drift where baseline-equivalent behavior is required
- no diagnostics/runtime/review/report/export baseline-lock drift

## Initial regression thresholds

These thresholds are policy choices for the local gate.
They are not claimed as existing repo truth.

### Tier 1 threshold
Fail if:
- aggregate median slows by more than **20%**, or
- any primary fixture slows by more than **25%**

### Tier 2 threshold
Fail if:
- aggregate median slows by more than **30%**

Reason for looser Tier 2 threshold:
- artifact-heavy paths are more variable and may involve heavier IO and rendering work

## Baseline capture record

The first accepted baseline capture should record:

1. fixture list
2. command/invocation form used
3. machine/OS note
4. Python version
5. whether artifact generation was enabled
6. median times per fixture
7. aggregate median times per tier
8. date/time captured

## Candidate comparison record

Each candidate comparison should record the same fields plus:
- relative slowdown/speedup percentages
- pass/fail per tier
- whether any output-stability prerequisite failed first

## Current acceptance rule

For the first integrated selector/bootstrap pass:
- Tier 1 is mandatory
- Tier 2 is strongly recommended when artifact-aware paths are affected
- if the bootstrap is truly baseline-equivalent, no meaningful slowdown should be expected on Tier 1

## What remains tied to another open item

This spec defines the **performance gate**, but still depends on the separate open item:
- exact pytest-family invocation string and backend-path bootstrap method
