# 08E - Candidate B OpenDataLoader Compare Surface Validation Plan

## Purpose

Separate validate-only verification from explicit artifact-generating Candidate B workbench proof.

This doc exists because the compare surface is supposed to become easier to run, but it must still respect the repo rule that validate actions fail closed and do not seed artifacts.

---

## Validation phases

### Phase A - validate-only

This phase must not generate fresh Candidate B proof artifacts.

Required coverage:

- compare runner CLI argument validation
- baseline-summary schema validation
- fail-closed behavior on missing Java, missing package, or missing baseline summary
- run-root/output-root planning
- support-harness unit coverage that remains artifact-free
- mutual-exclusion validation for `--baseline-summary` vs `--first-run-compare-report`

Recommended tests:

- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`

Exact validate-only command-wiring support:

- add `--plan-only` to the compare runner so command wiring and output planning can be tested without generating reports
- do not add a `--dry-run` alias in the first pass

### Phase B - explicit isolated proof run

This phase is not standard pytest validation.
It is an intentional workbench execution.

Required posture:

- isolated worktree
- isolated runtime root
- isolated run-scoped output root
- no overwrite of committed historical Candidate B report files
- explicit run-local proof runtimes under `<run-root>/baseline-before/runtime` and `<run-root>/baseline-after/runtime`

Required proof sequence:

1. lower-layer baseline proof before Candidate B
2. fresh baseline-summary generation
3. Candidate B run
4. lower-layer baseline proof after Candidate B
5. proof/compare/retention review

---

## Acceptance criteria

The compare surface is implementation-complete only if all of the following are true:

- the new `project6.ps1` action launches successfully
- the compare runner no longer depends on a manually supplied historical compare artifact as its normal baseline source
- the compare runner writes into a run-scoped output root by default
- the compare runner uses `--plan-only` for validate-only command wiring
- the baseline proof passes before Candidate B
- the baseline proof passes after Candidate B
- proof, compare, retention, and baseline-summary artifacts are all present
- no outputs appear outside the approved Candidate B run root
- compare conclusions remain workbench-only and do not imply runtime admission
- the first pass does not introduce protected-diff serialization or raw-output commit behavior

---

## Required evidence

Validate-only evidence:

- green compare-surface pytest file
- green existing helper-focused pytest file
- green command-wiring `--plan-only` validation

Artifact-generating evidence:

- one fresh baseline summary artifact
- one fresh proof report
- one fresh compare report
- one fresh retention manifest
- one recorded run root

---

## Hard failure conditions

Fail the lane if any of the following occurs:

- the compare runner regresses to requiring a historical compare artifact path for normal use
- the default execution path overwrites the committed historical Candidate B artifacts
- Candidate B writes outside the approved run root
- the before/after lower-layer proof does not remain green
- the implementation touches forbidden service/API/UI surfaces
- the compare flow quietly degrades to historical-artifact review without producing a fresh baseline summary
- the runner accepts both baseline-input modes at once
- the runner introduces a `--dry-run` alias instead of the frozen `--plan-only` contract

---

## Documentation follow-up after implementation

After the compare surface lands, update:

- `README_CANDIDATE_B_OPENDATALOADER_PACK.md`
- `05R_CANDIDATE_B_OPENDATALOADER_WORKBENCH_COMPARISON_EXECUTION_PACKET.md`
- `06R_CANDIDATE_B_OPENDATALOADER_REMAINING_OPEN_ITEMS_AND_DECISION_GATES.md`
- `08A_CANDIDATE_B_OPENDATALOADER_COMMANDS_VALIDATION_AND_DECISION_RUNBOOK.md`

Those docs should then point to the real command instead of the current manual-first posture.
