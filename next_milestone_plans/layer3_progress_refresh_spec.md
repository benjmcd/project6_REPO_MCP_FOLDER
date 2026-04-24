# Layer3 Progress Refresh Spec

## Purpose

This file tells an external agent, including Claude Cowork, how to refresh the Layer3 progress artifact without guessing.
Use it together with:
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/progress-ui-spec.md`

This spec is intentionally scoped to the bounded Layer3 Phase1A through APS dedicated validate-only runtime/report-ref chain already landed on current `main`, plus the landed `23_GATED_APS_PROMOTION_FREEZE.md` continuation freeze from PR `#145`, the post-PR145 docs/progress sync from PR `#146`, the later APS family settlement closeout from PR `#147`, the post-PR147 progress-packet closeout from PR `#148`, the merged planning-only `24_L3_WB_FREEZE.md` / `25_L3_QUAL1_FREEZE.md` deferred-prep docs from PR `#165`, the post-PR165 docs/progress/front-door sync from PR `#166`, the merged broader-workbench implementation-entry prep packet from PR `#168`, the post-PR168 current-main closeout from PR `#169`, the post-PR169 duplicate-default cleanup from PR `#170`, the merged qualitative single-item input packet from PR `#172`, the post-PR172 deferred-prep front-door tightening from PR `#174`, and the merged planning-only `28_L3_WB_FIRST_SLICE_FREEZE.md` first-slice setup target from PR `#178` beyond that landed boundary.
If a future checkout carries additional planning-only workbench prep beyond current `main`, preserve it as branch-local until GitHub and current `main` both confirm it. The current `main` version of `26_L3_WB_INPUTS.md` is already merged planning-only prep rather than an open review state; the current `main` version of `28_L3_WB_FIRST_SLICE_FREEZE.md` from PR `#178` is also merged planning-only setup rather than an active route/API claim.
If a future checkout carries additional planning-only qualitative single-item companion prep beyond current `main`, preserve it as branch-local until GitHub and current `main` both confirm it. The current `main` version of `27_L3_QUAL1_INPUTS.md` is already merged planning-only prep rather than an open review state.

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
- `#110`, `#111`, `#112`, `#113`, `#115`, `#116`, `#117`, `#118`, `#119`, `#120`, `#121`, `#122`, `#123`, `#124`, `#125`, `#126`, `#127`, `#128`, `#129`, `#130`, `#131`, `#132`, `#133`, `#134`, `#135`, `#136`, `#137`, `#138`, `#139`, `#140`, `#141`, `#142`, `#143`, `#144`, `#145`, `#146`, `#147`, `#148`, `#165`, `#166`, `#167`, `#168`, `#169`, `#170`, `#172`, `#174`, `#178`

Hard rule:
- never mark a step as landed on `main` from repo docs alone if the GitHub PR is still open

### Repo authority for implementation and scope

Treat current `project6-origin/main` repo truth as authority for:
- which implementation surfaces are actually landed
- which freeze docs exist on current `main`
- which later families remain explicitly deferred
- what each deferred item would need before it could graduate into `Candidate Next Consumers` or `Current Focus`

Read these files first:
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `next_milestone_plans/README_LAYER3_PHASE1A_PACK.md`
- `next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/04_GATEC_ENTRY_FREEZE.md` through `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/nrc_aps_validate_only_gates_contract.py`
- `backend/app/services/nrc_aps_validate_only_gates.py`
- `backend/app/services/nrc_aps_validate_only_gates_gate.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `backend/app/services/connectors_sciencebase.py`
- `project6.ps1`
- `next_milestone_plans/progress-prompt.md`

When present in the current checkout, also read:
- `next_milestone_plans/Layer3_planning_docs/23_GATED_APS_PROMOTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/24_L3_WB_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/26_L3_WB_INPUTS.md`
- `next_milestone_plans/Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md`
- `next_milestone_plans/layer3-mockups/mockup-spec.txt`
- `next_milestone_plans/layer3-mockups/assets.md`
- `next_milestone_plans/Layer3_planning_docs/25_L3_QUAL1_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/27_L3_QUAL1_INPUTS.md`
- `backend/app/services/nrc_aps_promotion_gate.py`
- `tests/test_nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `tests/test_nrc_aps_promotion_tuning.py`
- `backend/app/services/nrc_adams_resources/aps_promotion_policy_v1.json`
- `backend/app/services/aps_retrieval_plane_cutover_validation.py`
- `backend/tests/test_aps_retrieval_plane_cutover_validation.py`
- `backend/tests/test_aps_retrieval_plane_cutover_gate.py`
- `tools/nrc_aps_retrieval_cutover_gate.py`

### Local checkout rule

Use a clean local checkout of `benjmcd/project6_REPO_MCP_FOLDER` whose contents match the artifact state being refreshed as the filesystem authority for the artifact.

Discovery rule:
- prefer the checkout that actually contains this spec and the matching `layer3_progress_manifest.json`
- if multiple clean checkouts exist, prefer the one matching current `main` for merged repo truth, or the one carrying the declared open or branch-only milestone when the manifest says a non-merged step is in scope

Seed path used when this artifact pack was authored:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3activate`

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
6. Re-read the active planning/status/progress packet and all repo authority surfaces named in `refresh_inputs.repo_paths`.
7. For each milestone:
   - update PR state from GitHub
   - update merge commit from GitHub
   - keep the milestone grouped under the same semantic milestone id unless repo truth proves the grouping wrong
8. Reconcile board wording against the manifest.
9. Reconcile any external render surface against `next_milestone_plans/progress-ui-spec.md`.
10. Ensure the primary render path is HTML/CSS readable without JavaScript or Mermaid.
11. Preserve explicit deferred scope.
12. Preserve and re-audit the deferred activation contract so every deferred item still has explicit candidate-next and current-focus promotion rules.
13. If the next-step decision has changed, or the bounded packet is now settled with no further active next lane, update `next_required_decision` in the manifest and the matching sections in the board and prompt.
14. If the live artifact cannot read refreshed files at view time, regenerate the artifact itself from the refreshed manifest and board instead of leaving a stale embedded snapshot in place.
15. Fail closed if GitHub state cannot be refreshed:
   - keep the last known manifest state
   - mark the refresh as stale instead of inventing merged/open status
16. If the current checkout carries a milestone that is not yet merged on `main`:
   - keep that milestone as `branch_only` only when no open or merged GitHub PR exists
   - upgrade it to `open` once GitHub confirms a PR exists
   - do not upgrade it to `merged` until GitHub confirms the merge
   - do not hide it from active artifact surfaces if the manifest declares it
17. If the current checkout carries branch-local planning-only prep or docs/progress sync beyond current `main`:
   - keep a GitHub-backed open planning or docs/progress follow-up visible while GitHub still shows the PR open, even if equivalent content is already present locally
   - keep any additional branch-local planning-only companion updates, including future revisions to `26_L3_WB_INPUTS.md`, `28_L3_WB_FIRST_SLICE_FREEZE.md`, or a branch-local `27_L3_QUAL1_INPUTS.md`, as branch-local prep rather than merged milestone history until GitHub and current `main` both confirm them
   - do not let either change settled packet counts unless both GitHub state and current `main` repo truth warrant it

## State Mapping Rules

Use these labels exactly:
- `merged`
- `open`
- `planned`
- `settled`
- `deferred`
- `branch_only`

Special case:
- use `merged_with_open_docs_closeout` when implementation is merged on `main` but the explicitly-tracked docs-only follow-up PR is still open

Hard rule:
- do not collapse `merged_with_open_docs_closeout` into plain `merged`
- when `next_required_decision.state=settled`, do not invent a planned or open next lane in the artifact
- do not promote a deferred item into candidate-next or current-focus unless its manifest-declared activation conditions are actually satisfied by refreshed repo truth
- do not silently omit the deferred activation section when the deferred list is non-empty
- do not treat merged planning-only deferred-prep docs on current `main` as new milestones or as packet-reopen evidence unless the manifest explicitly promotes them

## What Not To Do

Do not:
- infer merged state from prose like `now landed on current \`main\`` unless GitHub confirms the relevant PR merged
- widen the artifact into unrelated repo work
- rewrite milestone ids or reorder the whole chain without repo-confirmed reason
- silently drop the docs-closeout PRs, because they are part of the actual operational progression
- present speculative later families as already admitted
- invent activation criteria ad hoc in the artifact without first updating the repo-side manifest and board
- call the artifact live if it only embeds a stale snapshot and never updates from refreshed inputs
- rely on Mermaid or JavaScript as the only way primary progress meaning becomes visible

## Current Program Boundary

The current bounded chain on `main` ends at:
- the landed dedicated validate-only runtime/report-ref continuation freeze from PR `#140`
- the post-PR140 docs/progress sync from PR `#141`
- the post-PR141 docs/progress sync from PR `#142`
- the landed dedicated validate-only runtime/report-ref implementation lane from PR `#143`
- the post-PR143 docs/progress sync from PR `#144`

The preserved source-branch rule on current `main` is:
- dossier input must remain paired export-derived context packets rather than package-derived context

The current landed continuation at the end of current `main` is:
- the bounded dedicated validate-only runtime/report-ref implementation lane from PR `#143`, rooted in the dedicated validate-only contract/runtime/gate trio plus the bounded review graph/tree/runtime/report-ref integrations selected by `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`

The current settled state in this checkout is:
- current `main` now also includes the landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`, the post-PR145 docs/progress sync from PR `#146`, the later APS family settlement closeout from PR `#147`, and the post-PR147 progress-packet closeout from PR `#148`
- live repo truth now also shows the existing promotion governance family already sufficient on current `main`
- retrieval cutover already exists on current `main` as a separate validate-only parity-proof family
- current `main` also includes the merged planning-only `24_L3_WB_FREEZE.md` and `25_L3_QUAL1_FREEZE.md` docs from PR `#165`, but they remain deferred-scope prep artifacts and do not change the settled packet counts or `next_required_decision`
- current `main` also includes the post-PR165 docs/progress/front-door sync from PR `#166`, which aligns the progress artifact, pack front door, and canonical status/index surfaces with those merged planning-only deferred-prep docs without changing the settled packet state
- current `main` also includes the merged broader-workbench implementation-entry prep packet from PR `#168`, the post-PR168 current-main closeout from PR `#169`, and the post-PR169 duplicate-default cleanup from PR `#170`; together they land and finalize `26_L3_WB_INPUTS.md` plus companion updates to `24_L3_WB_FREEZE.md`, `25_L3_QUAL1_FREEZE.md`, `README_LAYER3_PHASE1A_PACK.md`, and the progress/control packet without changing the settled packet state
- keep the PR `#169` closeout visible as landed current-main history rather than treating the broader workbench packet as merely frozen at PR `#168`
- keep the PR `#170` duplicate-default cleanup visible as landed current-main history rather than leaving the current-main packet one correction behind
- if `next_milestone_plans/Layer3_planning_docs/26_L3_WB_INPUTS.md` is present in the current checkout, preserve it as a planning-only companion input doc for the deferred future workbench route family rather than as a merged milestone, packet-reopen signal, or active lane, even if it now freezes planning-only trigger/route-family/typing/owner/proof/no-go implementation-entry prep
- current `main` also includes the merged planning-only `28_L3_WB_FIRST_SLICE_FREEZE.md` first-slice setup target from PR `#178`; preserve it as deferred-scope setup rather than as a merged milestone, packet-reopen signal, live `/review/layer3` route claim, or live `/api/v1/layer3/...` API claim
- current `main` also includes the merged qualitative single-item input packet from PR `#172`; together `27_L3_QUAL1_INPUTS.md` plus companion updates to `25_L3_QUAL1_FREEZE.md`, `README_LAYER3_PHASE1A_PACK.md`, and the progress/control packet remain planning-only deferred-scope prep rather than an active lane
- if `next_milestone_plans/Layer3_planning_docs/27_L3_QUAL1_INPUTS.md` is present in the current checkout and the checkout matches current `main` after PR `#172`, preserve it as a merged planning-only companion input doc for the deferred qualitative single-item breadth axis rather than as a merged milestone, packet-reopen signal, or an active lane
- current `main` also includes the post-PR172 deferred-prep front-door tightening from PR `#174`, which carries the merged workbench and qualitative companion prep into the remaining current-main status/front-door surfaces without changing the settled packet state
- keep the PR `#174` front-door tightening visible as landed current-main history rather than leaving the current-main packet one front-door sync behind
- keep the PR `#178` first-slice setup target visible as landed current-main history rather than branch-local prep, while preserving the settled packet counts and active-lane guardrails
- if a future checkout carries additional branch-local revisions to `27_L3_QUAL1_INPUTS.md` plus associated companion-doc edits beyond current `main`, keep those future revisions branch-local and planning-only rather than folded into current merged-state facts
- do not invent another later APS family lane unless live repo truth proves a concrete new gap

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
- rebuild the deferred activation section from `deferred_scope_activation_contract`, not from a hardcoded stale prose block
- treat JavaScript and Mermaid as optional enhancement only
