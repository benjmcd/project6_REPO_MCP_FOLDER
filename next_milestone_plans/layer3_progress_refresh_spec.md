# Layer3 Progress Refresh Spec

## Purpose

This file tells an external agent, including Claude Cowork, how to refresh the Layer3 progress artifact without guessing.
Use it together with:
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`

This spec is intentionally scoped to the bounded Layer3 Phase1A through APS multisource chain.

## Canonical Inputs

### GitHub authority for state

Treat GitHub PR state as authority for:
- whether a step is still open or already merged
- merge commit SHA
- PR URL
- whether a docs-closeout follow-up is still pending

Current tracked PR set:
- `#69`, `#70`, `#71`, `#72`, `#73`, `#74`, `#75`
- `#77`, `#79`, `#80`
- `#81`, `#82`, `#84`
- `#85`, `#86`, `#87`
- `#88`, `#89`, `#90`
- `#91`, `#92`, `#93`
- `#94`, `#95`, `#96`
- `#97`, `#98`, `#99`
- `#100`, `#101`, `#102`

Hard rule:
- never mark a step as landed on `main` from repo docs alone if the GitHub PR is still open

### Repo authority for implementation and scope

Treat current `project6-origin/main` repo truth as authority for:
- which implementation surfaces are actually landed
- which freeze docs exist on current `main`
- which families remain explicitly deferred

Read these files first:
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `next_milestone_plans/README_LAYER3_PHASE1A_PACK.md`
- `next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/06_GATEC_PASS_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/07_GATEC_COHORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/08_GATED_PACKAGE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`

### Local checkout rule

Use any clean local checkout of `benjmcd/project6_REPO_MCP_FOLDER` whose contents match current `main` as the filesystem authority for the artifact.

Discovery rule:
- prefer the checkout that actually contains this spec and the matching `layer3_progress_manifest.json`
- if multiple clean checkouts exist, prefer the one tracking `project6-origin/main` or otherwise matching current `main`

Seed path used when this artifact pack was authored:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3-progress-main`

Do not treat the dirty root checkout at:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER`

as the local authority for this artifact, because it may be on a different branch.

## Required Output Files

Maintain exactly these files:
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`

Optional render surfaces are allowed, but only if they do not replace or contradict those two files.

## Refresh Procedure

1. Read `next_milestone_plans/layer3_progress_manifest.json`.
2. Refresh GitHub state for the tracked PR set.
3. Refresh the current `main` commit SHA.
4. Re-read:
   - `docs/nrc_adams/nrc_aps_status_handoff.md`
   - `next_milestone_plans/README_LAYER3_PHASE1A_PACK.md`
   - `next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
   - `next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
   - `next_milestone_plans/Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md` through `14_GATED_APS_MULTISOURCE_FREEZE.md`
5. For each milestone:
   - update PR state from GitHub
   - update merge commit from GitHub
   - keep the milestone grouped under the same semantic milestone id unless repo truth proves the grouping wrong
6. Reconcile board wording against the manifest.
7. Update Mermaid diagrams so merged, open, and planned states remain visually distinct.
8. Preserve explicit deferred scope.
9. If the next-step decision has changed, update `next_required_decision` in the manifest and the matching section in the board.
10. Fail closed if GitHub state cannot be refreshed:
   - keep the last known manifest state
   - mark the refresh as stale instead of inventing merged/open status

## State Mapping Rules

Use these labels exactly:
- `merged`
- `open`
- `planned`
- `deferred`
- `branch_only`

Special case:
- use `merged_with_open_docs_closeout` when implementation is merged on `main` but the explicitly-tracked docs-only follow-up PR is still open

Hard rule:
- do not collapse `merged_with_open_docs_closeout` into plain `merged`

## What Not To Do

Do not:
- infer merged state from prose like `now landed on current main` unless GitHub confirms the relevant PR merged
- widen the artifact into unrelated repo work
- rewrite milestone ids or reorder the whole chain without repo-confirmed reason
- silently drop the docs-closeout PRs, because they are part of the actual operational progression
- present speculative later families as already admitted

## Current Program Boundary

The current bounded chain ends at:
- APS same-run multisource admission

The next required decision is:
- freeze the first downstream shared APS consumer of the landed multisource seam

The current leading candidates are:
- `evidence_report_export_package`
- `context_dossier`

These are still planned, not landed.

## Schedule Guidance

If a scheduled refresh is available, use one of these:
- every 6 hours during active development
- once daily if a lower-noise cadence is preferred

If an on-merge trigger is available, prefer:
- refresh on PR merge
- otherwise fall back to the fixed schedule

## Cowork-Specific Guidance

If Claude Cowork does not have a native GitHub MCP connector:
- use any available GitHub public page or GitHub API access that Cowork can reach
- if neither is available, keep the last known GitHub-derived state and report that live PR refresh is blocked

Do not compensate for missing GitHub access by upgrading repo-doc wording into proof of merge.
