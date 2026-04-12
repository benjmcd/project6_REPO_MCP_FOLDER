# 06R - Candidate B OpenDataLoader Remaining Open Items and Decision Gates

## Purpose

List only the genuinely remaining open items after planning adoption reconciliation and the implementation-entry preflight/envelope freeze.

Many earlier ambiguities are now closed.
What remains open now is narrower, explicit, and separated from what this pass already froze.

---

## Resolved in this pass - docs destination

Resolved posture:
- keep the pack in `next_milestone_plans/candidate_b_workbench/`
- treat that path as branch-local, non-authoritative planning/workbench storage
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

## Remaining open item 1 - local Java readiness

### What remains open
The current machine still does not prove Java 11+ readiness on `PATH`.

### Hard rule
Do not run Candidate B until Java resolution is proven.

---

## Remaining open item 2 - post-proof helper-script decision

### What remains open
Whether a later repo-native helper script or `project6.ps1` action should ever be added after the first proof pass.

### Hard rule
No helper-script addition in v1.
That is a post-proof governance question only.

---

## Remaining open item 3 - commit posture for any derived sample outputs

### What remains open
Whether a very small redacted sample of raw ODL output should ever be committed for reviewer convenience.

### Hard rule
Default answer is no.
Any committed sample output requires a separate explicit decision after the first proof run.
