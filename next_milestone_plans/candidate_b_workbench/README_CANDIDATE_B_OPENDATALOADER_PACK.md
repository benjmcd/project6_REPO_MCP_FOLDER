# README - Candidate B OpenDataLoader Workbench Objective Pack

## Purpose

This folder is the frozen planning and control pack for a new Candidate B objective that is:
- workbench-only
- comparison-oriented
- non-admitted
- non-default
- not runtime-visible
- not integrated into the owner path

This pack is subordinate to the merged-main authority stack rooted in:
- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md`
- `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
- `05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`
- the adopted PageEvidence hold-state pack under `next_milestone_plans/pageevidence/`

It does not reopen the closed PageEvidence Lane Class A work.

## Current merged baseline

Candidate B now starts from these live repo truths on merged `main`:
- `baseline` remains the default posture.
- `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` value.
- the previous PageEvidence Lane Class A objective is closed.
- Pass 1 is complete.
- Pass 2 was considered and found unnecessary for the merged baseline.
- the correct current PageEvidence posture is stop and hold.
- any future PageEvidence or later-candidate work requires a new explicit freeze.
- `backend/app/services/nrc_aps_document_processing.py` remains the protected integrated owner path.
- `backend/app/services/nrc_aps_page_evidence.py` and `tools/run_nrc_aps_page_evidence_workbench.py` are part of the current admitted Candidate A baseline and are read-only in this objective.

## Frozen objective definition

### Objective name
`candidate_b_opendataloader_workbench_v1`

### Objective class
Workbench-only candidate objective.

### Objective purpose
Determine whether OpenDataLoader can provide program-relevant structural or layout comparison evidence against the current merged baseline without altering integrated runtime behavior.

### Why this objective is justified now
Candidate B is justified only because the merged baseline is now stable enough to compare against honestly:
- the lower-layer proof harness already exists
- the admitted Candidate A path is already bounded
- the pinned Candidate A artifact already exists as a secondary comparison anchor
- the PageEvidence lane is closed and no longer competing for the same implementation scope

### Why Candidate B is workbench-only
Candidate B remains workbench-only because all of the following are still true:
- Candidate B is not admitted by `05P` or `05Q`
- there is no approved runtime selector value for Candidate B
- there is no approval to touch `backend/app/services/nrc_aps_document_processing.py`
- there is no approval to widen API, review, report, export, schema, or persistence surfaces
- Candidate B introduces a different dependency posture that is acceptable only inside an isolated workbench envelope until separately proven and separately approved

## Allowed scope

Allowed now:
- planning and control docs in this folder
- future tests-side Candidate B support and compare surfaces only if a later implementation pass is explicitly opened from this pack
- future workbench-only dependency sidecar under `tests/`
- future labels sidecar under `tests/fixtures/nrc_aps_docs/v1/`
- future Candidate B proof, compare, and retention artifacts under `tests/reports/`

Not allowed now:
- runtime integration
- selector activation or admission
- owner-path rewiring
- `project6.ps1` expansion
- `backend/requirements.txt` changes
- generic candidate registry or framework work
- outward review/API/report/export/schema widening

## Protected scope

These surfaces remain protected unless a later separate objective explicitly reopens them:
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- current selector semantics and normalization behavior
- retrieval, evidence bundle, review/document-trace, report/export/package, and other hidden-consumer surfaces
- current admitted Candidate A behavior and the pinned Candidate A workbench artifact

## Dependency and substrate posture

Candidate B currently implies a workbench-only OpenDataLoader posture:
- Python wrapper usage only
- Windows PowerShell
- `py -3.12`
- external Java 11+ availability
- isolated dependency sidecar rather than backend runtime dependency changes

This pack records that posture as a proposed workbench envelope only.
It is not promoted here to repo-runtime truth.
A later implementation pass must revalidate package version, package hash, license posture, Java availability, and wrapper API/signature before code begins.

## Validation burden for any future implementation pass

A future Candidate B implementation pass must at minimum:
1. re-establish merged-main truth again before code
2. prove the existing lower-layer baseline still passes before Candidate B work
3. preserve the protected owner path and admitted Candidate A behavior
4. run Candidate B only through approved workbench-only tests/report surfaces
5. generate proof, compare, and retention-manifest artifacts with provenance
6. prove no writes escaped the approved Candidate B roots
7. rerun the baseline proof after Candidate B work to prove non-interference
8. treat secondary Candidate A comparison as optional and bounded by the exact frozen artifact refs in `04B`

## Stop conditions and escalation triggers

Stop immediately if any of the following becomes necessary:
- touching `backend/app/services/nrc_aps_document_processing.py`
- adding a runtime selector or admitting Candidate B
- widening API, review, report, export, or schema surfaces
- changing the meaning of `candidate_a_page_evidence_v1`
- modifying `backend/requirements.txt`
- adding a generic candidate framework to make Candidate B work
- relying on unverified OpenDataLoader package or API assumptions at implementation time

Any of those requires a new explicit freeze.

## Reading order

1. `README_CANDIDATE_B_OPENDATALOADER_PACK.md`
2. `00M_CANDIDATE_B_OPENDATALOADER_REPO_TRUTH_ANCHORS_AND_REFERENCES.md`
3. `00A_CANDIDATE_B_OPENDATALOADER_HANDOFF_AND_DECISION_MAP.md`
4. `00B_CANDIDATE_B_OPENDATALOADER_REPO_SURFACE_MAP_AND_TOUCH_POLICY.md`
5. `00C_CANDIDATE_B_OPENDATALOADER_DEPENDENCY_RUNTIME_AND_LICENSE_MATRIX.md`
6. `03AD_EXACT_CANDIDATE_B_OPENDATALOADER_WORKBENCH_COMPARISON_BOUNDARY.md`
7. `04B_CANDIDATE_B_OPENDATALOADER_BASELINE_AND_CANDIDATE_A_CROSSWALK.md`
8. `05R_CANDIDATE_B_OPENDATALOADER_WORKBENCH_COMPARISON_EXECUTION_PACKET.md`
9. `08A_CANDIDATE_B_OPENDATALOADER_COMMANDS_VALIDATION_AND_DECISION_RUNBOOK.md`
10. `06R_CANDIDATE_B_OPENDATALOADER_REMAINING_OPEN_ITEMS_AND_DECISION_GATES.md`

## One-line use rule

Use this pack only to open or review a bounded Candidate B OpenDataLoader workbench-comparison lane; do not treat it as permission to integrate Candidate B or to reopen the closed PageEvidence lane.
