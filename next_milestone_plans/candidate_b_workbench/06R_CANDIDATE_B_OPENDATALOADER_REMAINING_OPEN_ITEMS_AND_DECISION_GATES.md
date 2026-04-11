# 06R - Candidate B OpenDataLoader Remaining Open Items and Decision Gates

## Purpose

List only the genuinely remaining open items after reconciling the Candidate B pack against the current merged baseline.

## Resolved by this reconciliation pass

The following earlier ambiguities are now closed:
- Candidate B is now explicitly defined relative to merged `main`, not older lower-layer-only repo state.
- the docs destination is now fixed to `next_milestone_plans/candidate_b_workbench/` for this frozen planning objective.
- exact secondary Candidate A comparison anchors are now frozen in `04B`.
- Candidate B is now explicitly subordinate to the MVVLC control spine and the adopted PageEvidence hold-state pack.
- Candidate B is now explicitly prevented from reopening the closed PageEvidence lane by implication.

## Remaining open item 1 - implementation-day package and API revalidation

What remains open:
- whether the planned OpenDataLoader version, hash, license posture, and wrapper API/signature still match this pack when implementation day arrives

Hard rule:
- if any of those differ, amend the pack before implementation proceeds

## Remaining open item 2 - Java availability in the actual workbench environment

What remains open:
- whether the implementation machine actually has Java 11+ available for the planned OpenDataLoader posture

Hard rule:
- if Java is unavailable and no equally bounded alternative exists, stop rather than improvising a broader substrate path

## Remaining open item 3 - exact sidecar label contents

What remains open:
- the exact page or document labels for the first Candidate B run

Hard rule:
- do not backfill labels after seeing results

## Remaining open item 4 - whether the first run needs the optional Candidate A comparison

What remains open:
- whether the first Candidate B run should compare only against the mandatory baseline or also against the optional frozen Candidate A anchors

Hard rule:
- baseline comparison is mandatory
- Candidate A comparison remains optional and must use the exact anchors from `04B`

## Remaining open item 5 - whether a helper or runner is justified after first proof

What remains open:
- whether a later tests-side helper or runner is justified after the first proof run

Hard rule:
- no helper, `tools/` runner, or `project6.ps1` action is justified by default in the initial implementation lane

## Remaining open item 6 - commit posture for derived sample outputs

What remains open:
- whether any tiny derived sample of raw Candidate B output should ever be committed for review convenience

Hard rule:
- default answer is no
- any committed sample output requires a separate explicit decision after the first proof run

## Remaining open item 7 - future adoption into merged-main control docs

What remains open:
- whether any later Candidate B materials should ever be adopted into the merged-main control spine

Hard rule:
- no adoption is part of this objective
- any later adoption requires a separate explicit doc-only objective after proof exists
