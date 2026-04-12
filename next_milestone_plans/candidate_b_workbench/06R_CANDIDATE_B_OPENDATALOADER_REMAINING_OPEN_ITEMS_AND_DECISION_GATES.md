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

## Remaining open item 1 - invocation tightening vs committed implementation

### What remains open
The current committed workbench support on `main` launches `sys.executable -m opendataloader_pdf`.
It does not yet use a direct `opendataloader_pdf.convert(...)` call.

### Hard rule
Do not describe direct-wrapper invocation as a current committed `main` fact unless the support module changes.

---

## Remaining open item 2 - dedicated compare pytest surface

### What remains open
`main` contains `tests/test_nrc_aps_candidate_b_opendataloader.py`,
but it does not contain a separate `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`.

### Hard rule
Do not tell operators to run a compare pytest that does not exist.
Any new compare pytest surface requires a separate bounded change.

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

## Remaining open item 6 - polished compare-surface ergonomics

### What remains open
Candidate B still lacks:

- a repo-native `project6.ps1` compare action
- a dedicated compare runner
- a fresh baseline-summary source for normal reruns
- a dedicated validate-only compare pytest file

### Hard rule
Do not describe the current committed surface as a first-class compare workflow yet.
Use `05T` and `08E` as the implementation-preparation docs for that lane.
