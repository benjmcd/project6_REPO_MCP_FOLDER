# Layer3 Progress Refresh Spec

## Purpose

This file tells an external agent, including Claude Cowork, how to refresh the Layer3 progress artifact without guessing.
Use it together with:
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/progress-ui-spec.md`

This spec is intentionally scoped to the bounded Layer3 Phase1A through APS dedicated validate-only runtime/report-ref chain already landed on current `main`, plus the landed `23_GATED_APS_PROMOTION_FREEZE.md` continuation freeze from PR `#145`, the post-PR145 docs/progress sync from PR `#146`, the later APS family settlement closeout from PR `#147`, the post-PR147 progress-packet closeout from PR `#148`, the merged planning-only `24_L3_WB_FREEZE.md` / `25_L3_QUAL1_FREEZE.md` deferred-prep docs from PR `#165`, the post-PR165 docs/progress/front-door sync from PR `#166`, the merged broader-workbench implementation-entry prep packet from PR `#168`, the post-PR168 current-main closeout from PR `#169`, the post-PR169 duplicate-default cleanup from PR `#170`, the merged qualitative single-item input packet from PR `#172`, the post-PR172 deferred-prep front-door tightening from PR `#174`, the merged planning-only `28_L3_WB_FIRST_SLICE_FREEZE.md` first-slice setup target from PR `#178`, the merged planning-only `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` endpoint/state companion from PR `#182`, the bounded first-slice workbench implementation from PR `#184`, the post-PR184 status/cohesion/explicit-Gate-C-typing/review-feedback closeouts from PRs `#185` through `#190`, the merged planning-only `30_L3_WB_PLAN_PREVIEW_FREEZE.md` / `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` second-slice plan-preview packet from PR `#191`, the post-PR191 progress/tracked-metadata syncs from PRs `#192` and `#193`, the bounded read-only plan-preview implementation from PR `#194`, the post-PR194 proof/board-metadata closeouts from PRs `#195` and `#196`, the PR `#198` plan-approval freeze packet, and the merged PR `#199` bounded plan-approval implementation.
It also tracks the later workbench chain through PR `#227` bounded selected-pass result-review implementation, PR `#228`/`#229` result-review post-merge/state-vocabulary syncs, docs `46`/`47` as planning-only result-review UI governance, PR `#232` as the bounded result-review UI implementation, PR `#234` docs `48`/`49` as planning-only package-review preview governance, PR `#235` as the bounded read-only package-preview implementation, PR `#236` as package-preview postmerge status sync, PR `#237` docs `50`/`51` as planning-only package-construction governance, PR `#238` as the bounded package-construction implementation, PR `#241` docs `52`/`53` as planning-only package-review submit/decision governance, PR `#243` as the bounded backend package-review submit implementation, PR `#245` as the current-main bounded rendered package-review UI implementation, PR `#246` as the post-PR245 docs/proof sync, PR `#247` as post-review fallback hardening inside the same rendered package-review UI boundary, PRs `#248`/`#249` as post-PR247 docs/proof/metadata syncs, docs `54`/`55` as planning-only handoff/export preparation governance, PR `#251` as the bounded backend/API handoff-export prepare-only implementation, PR `#252` as blocker-vocabulary/session-summary hardening, PR `#255` docs `56`/`57` as planning-only rendered handoff/export preparation UI governance, and future branch-local rendered package-review or handoff/export candidates only when the active branch explicitly declares one. Docs `46`/`47` must not be rendered as live UI behavior by themselves; PR `#232` is the separate live bounded UI state on current `main`. Docs `48`/`49` must not be rendered as live package review, package construction, package rows, handoff/export, or `materialize_package_entry(...)` admission by themselves; PR `#235` is live only for read-only preview inspection. Docs `50`/`51` must not be rendered as live package construction by themselves; PR `#238` is live only for bounded backend package construction. Docs `52`/`53` must not be rendered as live package-review submit behavior by themselves; PR `#243` is the separate current-main backend implementation, PR `#245` separately renders the bounded current-main UI controls, and PR `#247` only hardens stale session-summary fallback after package commit. Docs `54`/`55` must not be rendered as live handoff/export preparation by themselves; PR `#251` is live only for backend/API prepare-only reference-envelope state, and PR `#252` only hardens blocker vocabulary and active-substate summary selection. Docs `56`/`57` must not be rendered as live handoff/export UI behavior by themselves. None of these must be treated as APS dispatch, external export, physical export artifact creation, `AnalysisArtifact` creation, package payload mutation, package reconstruction, schema/runtime widening, rendered handoff/export controls, or full mockup activation. Future branch-local rendered package-review or handoff/export controls must stay branch-local until merged. Handoff/export execution beyond prepare-only, package payload mutation, package reconstruction, schema/runtime widening, and full mockup activation remain out.
If a future checkout carries additional planning-only workbench prep beyond current `main`, preserve it as branch-local until GitHub and current `main` both confirm it. The current `main` version of `26_L3_WB_INPUTS.md` is already merged planning-only prep rather than an open review state; the current `main` version of `28_L3_WB_FIRST_SLICE_FREEZE.md` from PR `#178` is merged planning-only setup that now governs the bounded PR `#184` first-slice implementation; the current `main` version of `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` from PR `#182` is merged planning-only endpoint/state contract detail that now governs the bounded PR `#184` first-slice route/API.
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
- `#110`, `#111`, `#112`, `#113`, `#115`, `#116`, `#117`, `#118`, `#119`, `#120`, `#121`, `#122`, `#123`, `#124`, `#125`, `#126`, `#127`, `#128`, `#129`, `#130`, `#131`, `#132`, `#133`, `#134`, `#135`, `#136`, `#137`, `#138`, `#139`, `#140`, `#141`, `#142`, `#143`, `#144`, `#145`, `#146`, `#147`, `#148`, `#165`, `#166`, `#167`, `#168`, `#169`, `#170`, `#172`, `#174`, `#178`, `#181`, `#182`, `#183`, `#184`, `#185`, `#186`, `#187`, `#188`, `#189`, `#190`, `#191`, `#192`, `#193`, `#194`, `#195`, `#196`, `#198`, `#199`, `#200`, `#201`, `#202`, `#203`, `#204`, `#205`, `#206`, `#207`, `#208`, `#209`, `#210`, `#211`, `#212`, `#213`, `#215`, `#216`, `#217`, `#218`, `#219`, `#220`, `#221`, `#222`, `#223`, `#224`, `#225`, `#226`, `#227`, `#228`, `#229`, `#230`, `#232`, `#233`, `#234`, `#235`, `#236`, `#237`, `#238`, `#241`, `#242`, `#243`, `#244`, `#245`, `#246`, `#247`, `#248`, `#249`, `#250`, `#251`, `#252`, `#253`, `#254`, `#255`

Tracked metadata-refresh PR rule:
- include merged PRs that are known completed inputs to the refresh, including prior docs/progress sync PRs
- the PR performing the current refresh is not required to list itself before merge; the next refresh should add it if it becomes a known completed input

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
- `next_milestone_plans/Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/34_L3_WB_PLAN_REVISION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/42_L3_WB_RESULT_STATUS_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/Layer3_planning_docs/56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`
- `next_milestone_plans/layer3-mockups/mockup-spec.txt`
- `next_milestone_plans/layer3-mockups/assets.md`
- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`
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
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3-handoff-export-freeze`

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
9. Reconcile `layer3_workbench_current_decision` and `layer3_workbench_slices` against the board and prompt so workbench slice state is not inferred only from prose.
10. Confirm every `main_state` used by `milestones` or `layer3_workbench_slices` is declared in `state_model` and has a matching `artifact_render_contract.state_visuals` entry.
11. Reconcile any external render surface against `next_milestone_plans/progress-ui-spec.md`.
12. Ensure the primary render path is HTML/CSS readable without JavaScript or Mermaid.
13. Preserve explicit deferred scope.
14. Preserve and re-audit the deferred activation contract so every deferred item still has explicit candidate-next and current-focus promotion rules.
15. If the APS next-step decision has changed, or the bounded APS packet is now settled with no further active next lane, update `next_required_decision` in the manifest and the matching sections in the board and prompt.
16. If the Layer 3 workbench next-step decision has changed, update `layer3_workbench_current_decision` without repurposing the APS `next_required_decision`.
17. If the live artifact cannot read refreshed files at view time, regenerate the artifact itself from the refreshed manifest and board instead of leaving a stale embedded snapshot in place.
18. Fail closed if GitHub state cannot be refreshed:
   - keep the last known manifest state
   - mark the refresh as stale instead of inventing merged/open status
19. If the current checkout carries a milestone that is not yet merged on `main`:
   - keep that milestone as `branch_only` only when no open or merged GitHub PR exists
   - upgrade it to `open` once GitHub confirms a PR exists
   - do not upgrade it to `merged` until GitHub confirms the merge
   - do not hide it from active artifact surfaces if the manifest declares it
20. If the current checkout carries branch-local planning-only prep or docs/progress sync beyond current `main`:
   - keep a GitHub-backed open planning or docs/progress follow-up visible while GitHub still shows the PR open, even if equivalent content is already present locally
   - keep any additional branch-local planning-only companion updates, including future revisions to `26_L3_WB_INPUTS.md`, `28_L3_WB_FIRST_SLICE_FREEZE.md`, or a branch-local `27_L3_QUAL1_INPUTS.md`, as branch-local prep rather than merged milestone history until GitHub and current `main` both confirm them
   - do not let either change settled packet counts unless both GitHub state and current `main` repo truth warrant it

## State Mapping Rules

Use these labels exactly:
- `merged`
- `merged_with_open_docs_closeout`
- `open`
- `planned`
- `settled`
- `deferred`
- `branch_only`
- `branch_local_planning_only`
- `branch_local_live_bounded_read_only`
- `merged_planning_only`
- `merged_live_bounded`
- `merged_live_bounded_approval_only`
- `merged_live_bounded_revision_control`
- `merged_live_bounded_read_only`
- `merged_live_bounded_execution_selection`
- `merged_live_bounded_analysis_execution_start`
- `planning_only_result_status_freeze`
- `merged_live_bounded_result_status`
- `planning_only_result_review_freeze`
- `merged_live_bounded_result_review`
- `planning_only_result_review_ui_freeze`
- `merged_live_bounded_result_review_ui`
- `planning_only_package_review_preview_freeze`
- `merged_live_bounded_read_only_package_review_preview`
- `planning_only_package_construction_freeze`
- `merged_live_bounded_package_construction_commit`
- `planning_only_package_review_submit_freeze`
- `merged_live_bounded_package_review_submit`
- `merged_live_bounded_package_review_submit_ui`
- `planning_only_handoff_export_freeze`

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
- current `main` also includes the merged planning-only `28_L3_WB_FIRST_SLICE_FREEZE.md` first-slice setup target from PR `#178`; when it landed, preserve it as deferred-scope setup rather than as a merged milestone, packet-reopen signal, or live route/API claim by itself
- current `main` also includes the merged planning-only `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` endpoint/state companion from PR `#182`; when it landed, preserve it as endpoint/state contract detail for the deferred first-slice workbench target rather than as a merged milestone, active lane, live route/API claim by itself, schema/runtime widening signal, or downstream execution/package/handoff signal
- current `main` also includes the bounded first-slice workbench implementation from PR `#184`; preserve `/review/layer3` and `/api/v1/layer3/...` as live only for intent/preflight, deterministic source preview, material preview, Gate B decision recording, Gate C UI non-authoritative typing preview, explicit API owner-service typing materialization when `commit_typing` is true, explicit Gate C override unavailability, and session summary, not as proof of the full mockup/broader workbench
- current `main` also includes the merged qualitative single-item input packet from PR `#172`; together `27_L3_QUAL1_INPUTS.md` plus companion updates to `25_L3_QUAL1_FREEZE.md`, `README_LAYER3_PHASE1A_PACK.md`, and the progress/control packet remain planning-only deferred-scope prep rather than an active lane
- if `next_milestone_plans/Layer3_planning_docs/27_L3_QUAL1_INPUTS.md` is present in the current checkout and the checkout matches current `main` after PR `#172`, preserve it as a merged planning-only companion input doc for the deferred qualitative single-item breadth axis rather than as a merged milestone, packet-reopen signal, or an active lane
- current `main` also includes the post-PR172 deferred-prep front-door tightening from PR `#174`, which carries the merged workbench and qualitative companion prep into the remaining current-main status/front-door surfaces without changing the settled packet state
- keep the PR `#174` front-door tightening visible as landed current-main history rather than leaving the current-main packet one front-door sync behind
- keep the PR `#178` first-slice setup target and PR `#182` endpoint/state companion visible as landed current-main planning-only history, and keep PR `#184` visible as the bounded first-slice implementation, while preserving the settled packet counts and broader-workbench active-lane guardrails
- current `main` also includes the merged `30_L3_WB_PLAN_PREVIEW_FREEZE.md` and `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` second-slice plan-preview packet from PR `#191` and the bounded read-only implementation from PR `#194`; present plan preview as live only after explicit Gate C typing commit, not as a merged milestone-count change, schema/runtime widening, execution/results/package/handoff activation, qualitative/hybrid/RAG/vector activation, or an LLM-planning admission signal
- current `main` also includes the PRs `#195` and `#196` proof/board-metadata closeouts after PR `#194`; preserve them as metadata/proof closeouts only, not as implementation milestones, packet-reopen evidence, or downstream activation
- preserve PR `#198` as the planning-only plan-approval freeze packet; preserve PR `#199` as the bounded approval-only implementation that persists `L3AnalysisPlan` after server-backed preview and still does not admit `L3PassRun`, analysis execution, execution/results/package/handoff activation, runtime DB/schema widening, or qualitative/hybrid/RAG/vector/LLM planning
- current `main` also includes PRs `#200`, `#201`, and `#202`; preserve them as post-approval docs/control syncs only, and do not treat them as runtime behavior expansion
- if `34_L3_WB_PLAN_REVISION_FREEZE.md` and `35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md` are present, preserve them as the PR `#203` planning-only fourth-slice revision-control freeze/API-state packet, with PR `#204` limited to deferred-scope count correction; after PR `#205`, mark only pre-approval plan rejection/revision-control live; preserve PR `#206` as post-implementation docs/control sync; after PR `#207`, treat backend row-locking and shared UI in-flight locking as hardening of that same bounded slice rather than a new functional slice; preserve PRs `#208`/`#209` as docs/progress cohesion syncs only; do not let any of these imply approved-plan reopening/supersession, execution, manifests, results/package/handoff, runtime DB/schema widening, or qualitative/hybrid/RAG/vector/LLM planning
- if `36_L3_WB_EXECUTION_READINESS_FREEZE.md`, `37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`, and `layer3_workbench_proof_manifest.json` are present on current `main` after PR `#212`, preserve them as merged planning-only execution-readiness proof/state gates; do not treat them as execution selection, approved-plan supersession, results/package/handoff activation, runtime DB/schema widening, source-ingestion expansion, or qualitative/hybrid/RAG/vector/LLM planning admission
- if `/api/v1/layer3/readiness`, explicit preview identity/hash metadata, and approval/revision serialization checks are present on current `main` after PR `#213`, preserve them as merged live bounded read-only implementation-readiness proof; do not treat them as execution selection or downstream activation
- if `38_L3_WB_EXECUTION_SELECTION_FREEZE.md` and `39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md` are present, preserve them as planning-only execution-selection governance; do not treat them as analysis execution, results/package/handoff activation, approved-plan supersession, runtime DB/schema widening, source-breadth expansion, or full mockup activation
- if `/api/v1/layer3/execution/select` and selected/not-started `L3PassRun` shell tests are present after PR `#216`, preserve that state as merged live bounded execution-selection only; do not treat it as `materialize_pass_entry(...)` admission, `AnalysisRun` creation, analysis execution, artifact-manifest writing, result/package/handoff activation, approved-plan supersession, runtime DB/schema widening, source-breadth expansion, UI change, or full mockup activation
- if `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md` and `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md` are present after PR `#217`, preserve them as planning-only analysis-execution-start governance for one future selected-pass-run wrapped quantitative execution boundary; do not treat them as live execution, `AnalysisRun` creation, batch execution, result/package/handoff activation, source-breadth expansion, approved-plan supersession, runtime DB/schema widening, UI change, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if `/api/v1/layer3/execution/result/status` and selected-pass result/status tests are present after PR `#222`, preserve that state as merged live bounded result/status inspection only; do not treat it as result review, result approval/rejection, package review, handoff/export, rerun/recovery, source/schema/runtime widening, UI change, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation
- if `44_L3_WB_RESULT_REVIEW_FREEZE.md` and `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md` are present by themselves, preserve them as planning-only result-review governance for one future bounded operator decision on one terminal selected pass after PR `#222` result/status authority; do not treat those docs alone as a live result-review endpoint, package review, handoff/export, rerun/recovery, source/schema/runtime widening, UI change by itself, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation
- if current `main` includes merged PR `#227`, classify `/api/v1/layer3/execution/result/review` as current-main live bounded selected-pass result-review behavior only; preserve the exact no-go boundary for package review, handoff/export, rerun/recovery, new execution, new plan/pass/run/artifact/package/reconciliation rows, source/schema/runtime widening, UI changes, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, and full mockup activation
- if `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md` and `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md` are present, preserve them as planning-only UI governance for the `/review/layer3` result-review presentation/control boundary after PR `#227`; do not treat those docs alone as live UI behavior, execution selection/start UI, package review, handoff/export, rerun/recovery, new backend endpoints by default, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if current `main` includes merged PR `#232`, classify `/review/layer3` result-review UI behavior as current-main live bounded UI only for session refresh, selected-pass result/status inspection, and one result-review submission through existing backend endpoints; do not treat it as execution selection/start UI, package review, handoff/export, rerun/recovery, new backend endpoint admission, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if `48_L3_WB_PACKAGE_REVIEW_FREEZE.md` and `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md` are present, preserve them as planning-only package-review preview governance after PR `#232`; do not treat those docs alone as live package review, package construction, `L3OutputPackage` or `L3ReconciliationRecord` creation, `materialize_package_entry(...)` admission, handoff/export, rerun/recovery, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if `/api/v1/layer3/package/review/preview`, `layer3.package_review_preview.v1`, and package-preview UI tests are present only on an unmerged branch, classify that behavior as a branch-only read-only package-preview implementation candidate until GitHub and current `main` both confirm it; preserve the exact no-go boundary for package construction, package-review submit/commit, package/reconciliation/artifact/handoff/runtime/source-ingestion rows, package payload writes, `materialize_package_entry(...)` calls, handoff/export, rerun/recovery, source/schema/runtime widening, execution selection/start UI, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, and full mockup activation
- if `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md` and `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md` are present, preserve them as planning-only package-construction governance after PR `#235`; do not treat those docs alone as live package construction, package-review submit/decision state, handoff/export, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if current `main` includes merged PR `#238`, classify `/api/v1/layer3/package/review/commit` and `layer3.package_construction_commit.v1` as current-main live bounded package-construction behavior only; preserve the exact write boundary of one `L3ReconciliationRecord`, three `L3OutputPackage` rows, and three package payload files, and do not treat it as package-review submission, package-review approval/rejection, handoff/export, source/schema/runtime widening, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, rendered UI activation, or full mockup activation
- if `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md` are present, preserve PR `#241` docs `52`/`53` as planning-only package-review submit/decision governance after PR `#238`; do not treat those docs alone as live package-review submit behavior, handoff/export, package payload mutation, package reconstruction, additional package/reconciliation/artifact rows, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if current `main` includes merged PR `#243`, classify `/api/v1/layer3/package/review/submit` and `layer3.package_review_submit.v1` as current-main live bounded backend package-review submit behavior only; preserve the exact write boundary of one operator decision object in existing reconciliation/session JSON, and do not treat it by itself as rendered UI activation, package payload mutation, package reconstruction, additional package/reconciliation/artifact rows, handoff/export, source/schema/runtime widening, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation
- if current `main` includes merged PR `#245`, classify rendered `/review/layer3` package construction commit and package-review submit controls as current-main live bounded UI behavior only; require the headed/headless proof record and keep handoff/export, package payload mutation, package reconstruction, source/schema/runtime widening, and full mockup activation out. If current `main` also includes merged PR `#247`, classify it only as stale session-summary fallback hardening inside that same rendered UI boundary after package commit; do not treat it as a new endpoint, new package row family, handoff/export, package mutation, package reconstruction, source/schema/runtime widening, or full mockup activation. If a future branch explicitly declares additional rendered package-review controls beyond PR `#245`/`#247`, classify that surface as branch-local until GitHub merge authority confirms it on `main`
- if `54_L3_WB_HANDOFF_EXPORT_FREEZE.md` and `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md` are present, preserve them as planning-only handoff/export preparation governance after package-review approval; do not treat those docs alone as a live handoff/export endpoint, APS dispatch, external export, physical export artifact, `AnalysisArtifact`, package payload mutation, package reconstruction, source/schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if current `main` includes merged PR `#251`, classify `/api/v1/layer3/handoff/export/prepare` and `layer3.handoff_export_prepare.v1` as current-main live bounded backend/API prepare-only behavior only; preserve the planned internal reference-envelope boundary over existing JSON-bearing workbench state and do not treat it as rendered UI activation, APS dispatch, external export, physical artifact creation, `AnalysisArtifact` creation, package payload mutation, package reconstruction, source/schema/runtime widening, or full mockup activation. If current `main` also includes merged PR `#252`, classify it only as downstream-blocker vocabulary and session-summary active-substate hardening inside that same backend/API boundary
- if `56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md` and `57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md` are present, preserve them as planning-only rendered handoff/export preparation UI governance after PR `#251`/`#252`; do not treat those docs alone as live UI behavior, backend behavior changes, APS handoff, external export/download, downstream dispatch, physical export artifacts, `AnalysisArtifact`, package payload mutation/reconstruction, source/schema/runtime widening, execution selection/start UI expansion, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation
- if a future branch implements additional `/api/v1/layer3/handoff/export/prepare` behavior or equivalent handoff/export behavior beyond PR `#251`/`#252`, classify it as branch-local until GitHub and current `main` both confirm it; preserve the planned `prepare_only` internal export-envelope boundary over existing JSON-bearing workbench state and do not treat it as APS dispatch, external export, physical artifact creation, `AnalysisArtifact` creation, package payload mutation, package reconstruction, source/schema/runtime widening, rendered UI activation, or full mockup activation
- if `/api/v1/layer3/package/review/submit` and `layer3.package_review_submit.v1` are present only on an unmerged branch, classify that behavior as a branch-only package-review submit implementation candidate until GitHub and current `main` both confirm it; preserve the exact write boundary of one operator decision object in existing reconciliation/session JSON, and do not treat it as package payload mutation, package reconstruction, additional package/reconciliation/artifact rows, handoff/export, rendered UI activation, source/schema/runtime widening, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation
- if a future branch implements `/api/v1/layer3/package/review/commit` or equivalent package-construction commit behavior, classify it as branch-local until GitHub and current `main` both confirm it; preserve the exact write boundary of one `L3ReconciliationRecord`, three `L3OutputPackage` rows, and three payload files, and do not treat it as package-review submission or handoff/export
- if `/api/v1/layer3/execution/result/review` and selected-pass result-review tests are present only on an unmerged branch, classify that behavior as a branch-only implementation candidate until GitHub and current `main` both confirm it; preserve the exact no-go boundary for package review, handoff/export, rerun/recovery, new execution, new plan/pass/run/artifact/package/reconciliation rows, source/schema/runtime widening, UI changes, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, and full mockup activation
- if a future branch checkout adds further readiness, execution, source, results, package, handoff, or correction behavior beyond PR `#227` bounded result-review, preserve those additions as branch-local until GitHub and current `main` both confirm them
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
