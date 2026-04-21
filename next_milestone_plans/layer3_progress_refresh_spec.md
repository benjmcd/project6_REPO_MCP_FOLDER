# Layer3 Progress Refresh Spec

## Purpose

This file tells an external agent, including Claude Cowork, how to refresh the Layer3 progress artifact without guessing.
Use it together with:
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/progress-ui-spec.md`

This spec is intentionally scoped to the bounded Layer3 Phase1A through APS multisource chain, plus the landed first shared-consumer freeze beyond multisource, plus the now-landed bounded export-package handoff implementation slice governed by that freeze, plus the now-landed package-derived-context freeze that follows that landed boundary, plus the now-landed bounded package-derived context handoff implementation slice, plus the merged malformed-scoped candidate-discovery closeout from PR `#119`, plus the now-landed context-dossier freeze beyond that landed package-context boundary, plus the now-landed bounded context-dossier handoff implementation slice from PR `#121`, plus the post-PR122 artifact-state fix from PR `#123`, plus the now-landed deterministic-insight continuation freeze from PR `#124`, plus the current branch-only deterministic insight handoff implementation slice and narrow deterministic gate hardening beyond that landed freeze.

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
- `#106`, `#107`, `#108`, `#109`
- `#110`, `#111`, `#112`, `#113`, `#115`, `#116`, `#117`, `#118`, `#119`, `#120`, `#121`, `#122`, `#123`, `#124`

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

Also read:
- `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
- `backend/app/services/nrc_aps_evidence_report_export_gate.py`
- `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`
- `next_milestone_plans/progress-prompt.md`

When present in the current checkout, also read:
- `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
- `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/app/services/nrc_aps_context_dossier_contract.py`
- `backend/app/services/nrc_aps_context_dossier.py`
- `backend/app/services/nrc_aps_context_dossier_gate.py`
- `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_package_handoff.py`

### Local checkout rule

Use a clean local checkout of `benjmcd/project6_REPO_MCP_FOLDER` whose contents match the artifact state being refreshed as the filesystem authority for the artifact.

Discovery rule:
- prefer the checkout that actually contains this spec and the matching `layer3_progress_manifest.json`
- if multiple clean checkouts exist, prefer the one matching current `main` for merged repo truth, or the one carrying the declared branch-only milestone when the manifest says a branch-only step is in scope

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
Any external live artifact or dashboard must also obey:
- `next_milestone_plans/progress-ui-spec.md`

## Refresh Procedure

1. Read `next_milestone_plans/layer3_progress_manifest.json`.
2. Refresh GitHub state for the tracked PR set.
3. Refresh the current `main` commit SHA.
4. Record that SHA as `snapshot_base_main_commit`, meaning the base `main` commit used for the artifact refresh.
5. Do not write that SHA back as a self-updating `current_main_commit` claim, because this artifact can merge in a later commit than the snapshot it describes.
6. Re-read:
   - `docs/nrc_adams/nrc_aps_status_handoff.md`
   - `next_milestone_plans/README_LAYER3_PHASE1A_PACK.md`
   - `next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
   - `next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
   - `next_milestone_plans/Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md` through `14_GATED_APS_MULTISOURCE_FREEZE.md`
   - and the now-landed first shared-consumer freeze that sits immediately beyond that landed chain, currently `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
   - and the merged exact-run gate-hardening owner surfaces rooted in `backend/app/services/nrc_aps_evidence_report_export_gate.py` and `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`
   - and, when present in the current checkout, the bounded export-package handoff owner surfaces rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`
   - and the now-landed package-derived-context freeze rooted in `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
   - and the landed package-derived context owner/proof surfaces rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py`, `backend/app/services/nrc_aps_context_packet_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
   - and, when present in the current checkout, the landed `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze plus the live dossier family surfaces rooted in `backend/app/services/nrc_aps_context_dossier_contract.py`, `backend/app/services/nrc_aps_context_dossier.py`, `backend/app/services/nrc_aps_context_dossier_gate.py`, and `backend/app/services/review_nrc_aps_graph.py`
   - and, when present in the current checkout, the landed bounded dossier handoff owner/proof surfaces rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`
   - and, when present in the current checkout, the landed `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze plus the live deterministic insight family surfaces rooted in `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`, and `backend/app/services/review_nrc_aps_graph.py`
   - and, when present in the current checkout, the branch-local deterministic insight handoff owner/proof surfaces rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
7. For each milestone:
   - update PR state from GitHub
   - update merge commit from GitHub
   - keep the milestone grouped under the same semantic milestone id unless repo truth proves the grouping wrong
8. Reconcile board wording against the manifest.
9. Reconcile any external render surface against `next_milestone_plans/progress-ui-spec.md`.
10. Ensure the primary render path is HTML/CSS readable without JavaScript or Mermaid.
11. Preserve explicit deferred scope.
12. If the next-step decision has changed, update `next_required_decision` in the manifest and the matching section in the board.
13. If the live artifact cannot read refreshed files at view time, regenerate the artifact itself from the refreshed manifest and board instead of leaving a stale embedded snapshot in place.
14. Fail closed if GitHub state cannot be refreshed:
   - keep the last known manifest state
   - mark the refresh as stale instead of inventing merged/open status
15. If the current checkout carries a branch-local milestone that is not yet backed by an open or merged GitHub PR:
   - keep that milestone as `branch_only`
   - do not upgrade it to `open` until GitHub confirms a PR exists
   - do not hide it from branch-local artifact surfaces if the manifest declares it

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
- infer merged state from prose like `now landed on current \`main\`` unless GitHub confirms the relevant PR merged
- widen the artifact into unrelated repo work
- rewrite milestone ids or reorder the whole chain without repo-confirmed reason
- silently drop the docs-closeout PRs, because they are part of the actual operational progression
- present speculative later families as already admitted
- call the artifact live if it only embeds a stale snapshot and never updates from refreshed inputs
- rely on Mermaid or JavaScript as the only way primary progress meaning becomes visible

## Current Program Boundary

The current bounded chain on `main` ends at:
- the landed APS package-derived context handoff slice beyond the landed export-package handoff boundary
- the landed read-only `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze from PR `#118`
- the merged malformed-scoped candidate-discovery closeout from PR `#119` for the export, export-package, and context-packet gates
- the post-PR118 docs/progress closeout from PR `#120`
- the landed bounded `aps_context_dossier_handoff` implementation slice from PR `#121`
- the post-PR121 docs/progress closeout from PR `#122`
- the post-PR122 artifact-state fix from PR `#123`
- the landed read-only deterministic-insight continuation freeze from PR `#124`
- and, in branch-local artifact surfaces when present, the bounded deterministic insight handoff implementation slice plus narrow deterministic gate hardening beyond that landed freeze

The preserved source-branch rule on current `main` is:
- dossier input must remain paired export-derived context packets rather than package-derived context

The next required move beyond current `main` is:
- land the current branch-only bounded deterministic insight handoff lane for the first deterministic continuation beyond the landed `context_dossier` handoff, rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`

The first selected shared consumer on current `main` is:
- `evidence_report_export_package`

The landed bounded implementation target on current `main` is:
- `aps_evidence_report_export_package_handoff`

The later but not first consumer remains:
- `context_dossier`

These are not both still open candidates in the same way:
- `evidence_report_export_package` is selected on current `main`
- `aps_evidence_report_export_package_handoff` is now landed on current `main`
- package-derived context packet is now landed on current `main` as the next write-enabled shared-family target after that landed handoff boundary, and current `main` now also includes the merged malformed-scoped candidate-discovery closeout from PR `#119`
- `context_dossier` is now the settled next later shared-family target beyond the landed package-context boundary
- paired export-derived context packets remain the dossier input branch and must not be refreshed into package-derived dossier input claims

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

If Cowork can update the artifact but cannot read files live at render time:
- rewrite the artifact itself during each successful refresh
- rebuild all primary milestone rows and summary sections from the refreshed manifest
- treat JavaScript and Mermaid as optional enhancement only
