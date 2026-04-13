# 06R - Candidate B OpenDataLoader Remaining Open Items and Decision Gates

## Purpose

List only the genuinely remaining open items after planning adoption reconciliation and the implementation-entry preflight/envelope freeze.

Many earlier ambiguities are now closed.
What remains open now is narrower, explicit, and separated from what this pass already froze.

---

## Resolved in this pass - docs destination

Resolved posture:
- keep the pack in `next_milestone_plans/candidate_b_workbench/`
- treat that path as committed, non-authoritative planning/workbench storage on `main`
- do not relocate the pack into `docs/nrc_adams/...` in v1

---

## Resolved in this pass - secondary Candidate A comparison decision

Resolved posture:
- first-pass secondary Candidate A comparison = `NO`
- baseline comparison remains mandatory
- any later Candidate A comparison requires a separate explicit freeze

---

## Resolved in this pass - exact first-run sidecar labels

Resolved posture:
- the exact first-run label sidecar is now frozen at `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- the frozen first-run fixture scope is `ml17123a319`, `layout`, `fontish`, `scanned`, and `mixed`
- do not backfill labels after seeing results

---

## Resolved in this pass - package/source/hash posture

Resolved posture:
- exact package source for this pass is the `opendataloader-pdf==2.0.0` PyPI release plus its published wheel
- exact published wheel SHA256 is `18093fa87a3089abdba14043c187f85c6a4af48c4597710de32d90e95666313e`
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt` is the frozen sidecar requirements surface for later install
- implementation-day revalidation of the release line remains required, but that is now a known future burden rather than a planning ambiguity

---

## Remaining open item 1 - invocation tightening vs committed implementation

### What remains open
The current committed workbench support on `main` launches `sys.executable -m opendataloader_pdf`.
It does not yet use a direct `opendataloader_pdf.convert(...)` call.

### Hard rule
Do not describe direct-wrapper invocation as a current committed `main` fact unless the support module changes.

---

## Remaining open item 2 - dedicated compare pytest surface

### What remains open
The compare-surface lane adds `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`,
and an explicit isolated proof run has now been recorded locally from a prepared environment on this lane.

### Hard rule
Do not overstate validate-only green status as if it proves the full artifact-generating compare path has already been exercised.

---

## Remaining open item 3 - non-interference proof serialization depth

### What remains open
The committed support module defines `git_protected_diff()`,
but the committed proof/compare/retention artifacts do not serialize a touched-file inventory.

### Hard rule
Do not overstate the current committed artifacts as if they already include protected-diff inventory.
Treat that as a future hardening opportunity only.

---

## Remaining open item 4 - historical report provenance normalization

### What remains open
The committed proof/compare artifacts carry sibling-worktree provenance fields such as worktree-specific `repo_root` values and prior-iteration report references.

### Hard rule
Treat those artifacts as historical workbench evidence,
not as clean-`main` rerun proof.

---

## Remaining open item 5 - commit posture for any derived sample outputs

### What remains open
Whether a very small redacted sample of raw ODL output should ever be committed for reviewer convenience.

### Hard rule
Default answer is no.
Any committed sample output requires a separate explicit decision after the first proof run.

---

## Remaining open item 6 - compare proof evidence disposition

### What remains open
The compare surface is implemented on this lane, and one explicit isolated proof run has now been completed locally, including:

- a repo-native `project6.ps1` compare action
- a dedicated compare runner
- a fresh baseline-summary source for normal reruns
- a dedicated validate-only compare pytest file

The artifact-disposition decision is now closed: the completed proof artifacts remain local-only operator evidence and are not preserved in tracked history.

### Hard rule
Do not describe the compare surface artifacts as preserved in tracked history or as canonical repo evidence. Treat them only as local archived operator evidence.

---

## Resolved in this pass - compare surface landed status

Resolved posture:
- the compare surface is no longer the next planned lane; it is already landed on `main`
- future Candidate B planning must start from that shipped compare posture rather than from the older compare-gap assumptions

---

## Resolved in this pass - first inspection-lane classification boundary

Resolved posture:
- the first Candidate B inspection lane must remain bundle-scoped
- it must not modify `visual_lane_mode`
- it must not add Candidate B to the normal review run selector

### Hard rule
Do not describe Candidate B Trace as if it requires runtime admission in the first pass.
If a later program wants true runtime admission, that must be reopened explicitly.

---

## Remaining open item 7 - annotated PDF retention contract

### What remains open
The pinned package appears to expose annotated PDF output capability, but current committed `main` does not yet request or retain annotated PDF artifacts in Candidate B bundles.

### Hard rule
Do not assume annotated PDFs are already part of the current retained Candidate B bundle contract.
Treat that as a separate additive artifact decision frozen in `04D`.

---

## Remaining open item 8 - Candidate B Trace implementation lane

### What remains open
Current compare manifests and compare columns do not yet expose a Candidate B deep link, and there is no Candidate B-specific inspection page or API family on `main`.

### Hard rule
Do not claim Candidate B currently has parity with baseline/Candidate A document-trace inspection.
Current parity ends at compare-column payload adaptation only.

---

## Remaining open item 9 - compare-pack bridge note

### What remains open
The shipped Workbench Compare docs and the Candidate B planning pack must stay aligned on one point:

- current compare deep links are baseline/Candidate A only
- Candidate B Trace is a separate future lane

### Hard rule
Do not leave the compare docs phrased as if Candidate B already deep-links into the existing single-run document-trace page.

---

## Resolved in this pass - compare-lane contract freeze

Resolved posture:
- exact action name = `compare-nrc-aps-candidate-b`
- exact compare-runner public flags = optional `--run-root` and optional `--plan-only` only
- exact baseline-tool public flags = required `--runtime-root`, `--proof-report`, and `--out`
- exact default output root = `tests/reports/cb-compare-<run_id>/`
- exact durable top-level outputs = `baseline-summary.json`, `proof.json`, `compare.json`, `retain.json`
- exact baseline proof posture = explicit `baseline-before/runtime` and `baseline-after/runtime` roots with `--require-ocr`
- protected-diff serialization is out of scope for the first pass
- no new Candidate B sidecar manifest is authorized in the first pass
