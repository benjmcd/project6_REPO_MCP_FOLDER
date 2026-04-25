# Layer3 Progress Artifact Rebuild Prompt

Use this prompt when rebuilding the Claude Cowork artifact or its scheduled refresh.

```text
Rebuild the Layer3 APS progress artifact so it reflects current repo truth and renders reliably.

Use the clean repo checkout that contains the current artifact files and matches the artifact state you want to refresh.
Do not assume `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3-progress-main` is still the correct checkout just because it was used earlier in this packet's history.
Prefer a clean checkout that actually contains the current packet files and matches current `project6-origin/main` when refreshing merged-main truth.
If you need the older authored seed as historical context only, it was:
`C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\worktrees\l3-progress-main`

Read these files in this order:
1. `next_milestone_plans/layer3_progress_refresh_spec.md`
2. `next_milestone_plans/layer3_progress_manifest.json`
3. `next_milestone_plans/layer3_progress_board.md`
4. `next_milestone_plans/progress-ui-spec.md`

Goal:
- rebuild the `layer3-aps-progress` Cowork artifact so it clearly shows:
  - what is done on `main`
  - what the current focus is
  - what the candidate next consumers are
  - what is explicitly deferred
  - what each deferred item would need before it could become a candidate next consumer or the current focus

Hard rules:
- GitHub PR state is authority for merged versus open.
- Do not infer merge state from planning-doc wording alone.
- The artifact must remain readable with HTML and CSS alone.
- JavaScript may enhance interaction, but it must not be required for milestone rows, current focus, candidate next consumers, deferred scope, or deferred activation criteria.
- Mermaid is optional enhancement only. If it does not render, there must be no loss of meaning.
- Do not call the artifact live if it only embeds a stale snapshot and never updates from refreshed inputs.
- Do not promote a deferred item into candidate-next or current-focus without using the manifest-declared activation criteria.

Required sections in order:
1. Program State Summary
2. Current Focus
3. Completed Chain
4. Milestone Table
5. Candidate Next Consumers
6. Deferred Scope
7. Deferred Scope Activation Criteria

Visual rules:
- `merged`: green
- `merged_with_open_docs_closeout`: distinct green-plus-followup state
- `open`: orange
- `planned`: amber
- `deferred`: gray
- `branch_only`: blue
- keep labels visible in text, not color alone

Critical architectural rule:
- If the artifact can read refreshed files at render time, use that.
- If it cannot, then the scheduled refresh must rewrite the artifact itself from the refreshed manifest and board during every successful refresh.

Current repo-side facts to preserve:
- current `main` includes the bounded APS multisource implementation from PR `#101`
- current `main` includes the docs-only multisource closeout from PR `#102`
- current `main` also includes the export-package first shared-consumer freeze and its docs-only closeout from PR `#106` and PR `#107`
- the immediate required move is no longer to choose the first shared consumer; that choice is already settled on current `main` in favor of `evidence_report_export_package`
- current `main` also includes the bounded export-package handoff implementation slice from PR `#109` and its docs-only closeout from PR `#110`, rooted in `backend/app/services/layer3_aps_report_export_package_handoff.py` and `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- current `main` also includes the exact-run export/export-package gate-hardening follow-up from PR `#111` and `#112`
- current `main` now includes the landed `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` freeze from PR `#113`, selecting package-derived context packet as the next later shared APS family beyond the landed export-package boundary
- current `main` now includes the bounded package-derived context handoff implementation slice from PR `#115`, rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- current `main` now also includes the merged PR `#119` malformed-scoped candidate-discovery closeout across the export, export-package, and context-packet gates
- current `main` also includes the post-PR116 docs/progress sync from PR `#117`
- current `main` now also includes the landed read-only `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze from PR `#118`, selecting `context_dossier` as the next later shared APS family after the landed package-context milestone
- current `main` also includes the post-PR118 docs/progress closeout from PR `#120`
- current `main` now includes the bounded `aps_context_dossier_handoff` implementation slice from PR `#121`, rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`, plus narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`
- current `main` also includes the post-PR121 docs/progress closeout from PR `#122`
- current `main` also includes the post-PR122 artifact-state fix from PR `#123`
- paired export-derived context packets remain the live dossier input branch; the landed package-derived context handoff must not be presented as dossier input proof
- current `main` now also includes the landed read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze from PR `#124`, selecting `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary
- current `main` now also includes the bounded deterministic insight handoff implementation slice from PR `#126`, rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, plus narrow deterministic gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- current `main` now also includes the post-PR126 docs/progress sync from PR `#127`
- current `main` now also includes the landed read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze from PR `#128`, selecting `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary
- current `main` now also includes the post-PR128 docs/progress sync from PR `#129`
- current `main` now also includes the bounded deterministic challenge handoff implementation slice from PR `#130`, rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`, and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`
- current `main` now also includes the post-PR130 docs/progress sync from PR `#131`
- current `main` now also includes the landed read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze from PR `#132`, selecting `deterministic_challenge_review_packet` as the next deterministic continuation beyond the now-landed deterministic challenge handoff
- current `main` now also includes the post-PR132 docs/progress sync from PR `#133`
- current `main` now also includes the bounded deterministic challenge review-packet handoff slice from PR `#134`, rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, plus the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`
- current `main` now also includes the post-PR134 docs/progress sync from PR `#135`
- current `main` now also includes the landed read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze from PR `#136`, selecting `validate_only_gates` as the exact next verification continuation beyond the landed review-packet handoff
- current `main` now also includes the post-PR136 docs/progress sync from PR `#137`
- current `main` now also includes the bounded validate-only gate-report refresh lane from PR `#138`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`
- current `main` now also includes the post-PR138 docs/progress sync from PR `#139`
- current `main` now also includes the post-PR140 docs/progress sync from PR `#141`
- current `main` now also includes the post-PR141 docs/progress sync from PR `#142`
- current `main` now also includes the bounded dedicated validate-only runtime/report-ref implementation lane from PR `#143`
- current `main` now also includes the post-PR143 docs/progress sync from PR `#144`
- if the current checkout matches current `main` after PR `#144`, render the dedicated validate-only runtime/report-ref implementation lane as `merged`
- if no later post-validate-only freeze exists on current `main`, render the current focus as the next freeze decision rather than as another current-main implementation lane
- if the current checkout matches current `main` after PR `#145`, render `23_GATED_APS_PROMOTION_FREEZE.md` as `merged`
- if the current checkout matches current `main` after PR `#146`, preserve the post-PR145 docs/progress sync as already landed history rather than dropping it from the tracked PR set
- if the current checkout matches current `main` after PR `#147`, preserve the later APS family settlement closeout as already landed history rather than presenting the packet as merely frozen
- if the current checkout matches current `main` after PR `#148`, preserve the post-PR147 progress-packet closeout as already landed history and keep the tracked PR set and snapshot base aligned with that merged-main state
- if the current checkout matches current `main` after PR `#165`, preserve the merged planning-only `24_L3_WB_FREEZE.md` and `25_L3_QUAL1_FREEZE.md` docs as deferred-scope prep on current `main` rather than promoting them into merged milestones or packet-reopen evidence
- if the current checkout matches current `main` after PR `#166`, preserve the post-PR165 docs/progress/front-door sync as already landed history and keep the artifact, pack front door, and canonical status/index surfaces aligned with those merged planning-only deferred-prep docs
- if the current checkout matches current `main` after PR `#168`, preserve the merged broader-workbench implementation-entry prep packet as deferred-scope planning-only history on current `main`; do not promote it into merged milestones, packet-reopen evidence, or an active lane
- if the current checkout matches current `main` after PR `#169`, preserve the post-PR168 current-main closeout as already landed history and keep the merged workbench packet phrasing current-main-aware rather than branch-local or review-open
- if the current checkout matches current `main` after PR `#170`, preserve the post-PR169 duplicate-default cleanup as already landed history and keep the merged workbench packet free of duplicated planning defaults
- if `next_milestone_plans/Layer3_planning_docs/26_L3_WB_INPUTS.md` is present in the current checkout, preserve it as a planning-only companion input doc for the deferred future workbench route family rather than promoting it into merged milestones, packet-reopen evidence, or an active lane, even when it contains planning-only trigger/route-family/typing/owner/proof/no-go implementation-entry prep
- if a future checkout carries additional branch-local `26_L3_WB_INPUTS.md` revisions plus associated companion-doc edits beyond current `main`, keep them branch-local and planning-only rather than folded into current merged-state facts
- if `next_milestone_plans/Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md` is present in the current checkout, preserve it as the first-slice setup contract; PR `#178` did not make `/review/layer3` or `/api/v1/layer3/...` live by itself, while PR `#184` later made only the bounded first-slice route/API live
- if `next_milestone_plans/Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` is present in the current checkout, preserve it as the first-slice endpoint/state contract; PR `#182` did not make `/review/layer3` or `/api/v1/layer3/...` live by itself, while PR `#184` later made only the bounded first-slice route/API live
- if the checkout matches current `main` after PR `#184`, render `/review/layer3` and `/api/v1/layer3/...` as live only for the bounded first-slice shell/API, including the distinction between UI non-authoritative Gate C typing preview and explicit API owner-service typing materialization when `commit_typing` is true, and do not promote that to merged milestone count changes, packet-reopen evidence, schema widening, runtime snapshot DB writes, downstream execution/package scope, or full mockup/broader-workbench activation
- if the checkout matches current `main` after PR `#190`, preserve PRs `#185` through `#190` as post-PR184 status/cohesion/explicit-Gate-C-typing/review-feedback closeouts; keep the first-slice route/API scope unchanged while carrying forward response-envelope, blocked Gate B error, Gate C authority-rail count/source-context, and tracked-PR metadata corrections
- if the checkout matches current `main` after PR `#191`, preserve `next_milestone_plans/Layer3_planning_docs/30_L3_WB_PLAN_PREVIEW_FREEZE.md` and `next_milestone_plans/Layer3_planning_docs/31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` as the merged second-slice plan-preview packet for the future workbench route family; after PR `#194`, treat only read-only plan preview after explicit Gate C typing commit as live and do not promote that into merged milestone count changes, packet-reopen evidence, schema widening, runtime snapshot DB writes, downstream execution/package scope, or full mockup/broader-workbench activation
- if `next_milestone_plans/Layer3_planning_docs/32_L3_WB_PLAN_APPROVAL_FREEZE.md` and `next_milestone_plans/Layer3_planning_docs/33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md` are present before GitHub confirms their merge, preserve them as branch-local planning-only candidate third-slice docs; if GitHub later confirms merge, preserve them as planning-only plan-approval docs only, not as live approval implementation, pass-run creation, execution/results/package/handoff activation, runtime DB/schema widening, or qualitative/hybrid/RAG/vector/LLM-planning admission
- if a future checkout carries additional branch-local `28_L3_WB_FIRST_SLICE_FREEZE.md` revisions plus associated companion-doc edits beyond current `main`, keep them branch-local and planning-only rather than folded into current merged-state facts until GitHub and current `main` both confirm them
- if the current checkout matches current `main` after PR `#178`, preserve the merged planning-only `28_L3_WB_FIRST_SLICE_FREEZE.md` first-slice setup target as landed current-main history; do not treat PR `#178` by itself as changing settled packet counts, current focus, or live route/API claims
- if the current checkout matches current `main` after PR `#172`, preserve the merged qualitative single-item input packet as deferred-scope planning-only history on current `main`; do not promote it into merged milestones, packet-reopen evidence, or an active lane
- if `next_milestone_plans/Layer3_planning_docs/27_L3_QUAL1_INPUTS.md` is present in the current checkout and the checkout matches current `main` after PR `#172`, preserve it as a merged planning-only companion input doc for the deferred qualitative single-item breadth axis rather than promoting it into merged milestones, packet-reopen evidence, or an active lane
- if the current checkout matches current `main` after PR `#174`, preserve the post-PR172 deferred-prep front-door tightening as already landed history and keep the merged deferred-prep packet phrased consistently across the remaining current-main front-door/status surfaces
- if a future checkout carries additional branch-local `27_L3_QUAL1_INPUTS.md` revisions plus associated companion-doc edits beyond current `main`, keep them branch-local and planning-only rather than folded into current merged-state facts
- if the current checkout matches current `main` after PR `#145`, show promotion as the landed first later APS family beyond the landed dedicated validate-only boundary, keep retrieval cutover later during the freeze decision itself, and do not invent a separate repo-backed post-validate-only top-chain family
- if live repo truth on current `main` already proves the existing promotion governance family sufficient and retrieval cutover already present as a separate parity-proof family, render the later APS family packet as `settled` rather than inventing another next lane

When rebuilding from a checkout that matches current `main` after PR `#144`:
- show the bounded `context_dossier` handoff slice from PR `#121` as completed on `main`
- show the exact-run gate-hardening follow-up as already landed on `main`
- show the landed package-derived-context freeze as completed on `main`
- show the package-derived context handoff slice as `merged`
- show the landed `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze as `merged`
- show the bounded `context_dossier` handoff lane from PR `#121` as `merged`
- show the post-PR121 docs/progress closeout from PR `#122` and the post-PR122 artifact-state fix from PR `#123` as already landed on `main`
- do not present package-derived context as dossier input proof
- show the read-only deterministic continuation freeze, rooted in `deterministic_insight_artifact`, as `merged`
- show the read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze as `merged`
- show the bounded deterministic challenge handoff as `merged`
- show the read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze as `merged`
- show the post-PR132 docs/progress closeout from PR `#133` as already landed on `main`
- show the bounded deterministic challenge review-packet handoff as `merged`
- show `validate_only_gates` as `merged` from PR `#136`
- show the post-PR136 docs/progress closeout from PR `#137` as already landed on `main`
- show the bounded validate-only gate-report refresh lane as `merged`
- show the post-PR138 docs/progress closeout from PR `#139` as already landed on `main`
- show `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md` as `merged`
- show the post-PR140 docs/progress sync from PR `#141` as already landed on `main`
- show the post-PR141 docs/progress sync from PR `#142` as already landed on `main`
- show the dedicated validate-only runtime/report-ref implementation lane from PR `#143` as `merged`
- show the post-PR143 docs/progress sync from PR `#144` as already landed on `main`
- if refreshing from a checkout that matches current `main` after PR `#145`, show that freeze as `merged`
- if refreshing from a checkout that matches current `main` after PR `#146`, keep that docs/progress sync in the tracked GitHub PR set and merged-history wording
- if refreshing from a checkout that matches current `main` after PR `#147`, keep that settlement closeout in the tracked GitHub PR set and merged-history wording
- if refreshing from a checkout that matches current `main` after PR `#148`, keep that progress-packet closeout in the tracked GitHub PR set and merged-history wording, and refresh the snapshot base to that merged-main commit instead of leaving an older pre-PR148 base
- if refreshing from a checkout that matches current `main` after PR `#165`, keep the merged planning-only `24_L3_WB_FREEZE.md` and `25_L3_QUAL1_FREEZE.md` docs visible as deferred-scope prep only, without counting them as merged milestones or inventing an active lane
- if refreshing from a checkout that matches current `main` after PR `#166`, keep that docs/progress/front-door sync in the tracked GitHub PR set and merged-history wording, and refresh the snapshot base and seed-checkout fields to the artifact refresh that already includes PR `#166`
- if `next_milestone_plans/Layer3_planning_docs/26_L3_WB_INPUTS.md` is present in the current checkout, keep it adjacent to `24_L3_WB_FREEZE.md` as deferred-scope companion prep rather than treating it as a milestone or active-lane marker, even when it has become specific enough to guide a later typing/owner/proof/no-go implementation-entry packet
- if `next_milestone_plans/Layer3_planning_docs/28_L3_WB_FIRST_SLICE_FREEZE.md` is present in the current checkout, keep it adjacent to `24_L3_WB_FREEZE.md` and `26_L3_WB_INPUTS.md` as the first-slice setup contract; PR `#178` did not activate route/API by itself, while PR `#184` later activated only the bounded first-slice route/API
- if `next_milestone_plans/Layer3_planning_docs/29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` is present in the current checkout, keep it adjacent to `28_L3_WB_FIRST_SLICE_FREEZE.md` as the first-slice endpoint/state companion; PR `#182` did not activate route/API by itself, while PR `#184` later activated only the bounded first-slice route/API
- if refreshing from a checkout that matches current `main` after PR `#194`, keep `30_L3_WB_PLAN_PREVIEW_FREEZE.md` and `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` adjacent to `28_L3_WB_FIRST_SLICE_FREEZE.md` and `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` as the governing second-slice plan-preview packet; plan preview is live only as the PR `#194` read-only endpoint/UI state after explicit Gate C typing commit, and it still does not admit execution/results/package/handoff, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, or LLM planning
- if `32_L3_WB_PLAN_APPROVAL_FREEZE.md` and `33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md` are present, keep them adjacent to the `30`/`31` plan-preview packet as the candidate third-slice plan-approval packet; approval is still planning-only until implemented, and the docs must keep `materialize_pass_entry(...)`, `L3PassRun` creation, analysis execution, results/package/handoff, runtime DB/schema widening, and qualitative/hybrid/RAG/vector/LLM planning out of scope
- if refreshing from a checkout that matches current `main` after PR `#196`, preserve PRs `#195` and `#196` as post-PR194 proof/board-metadata closeouts only; do not treat them as implementation milestones, packet-reopen evidence, or downstream activation
- if `next_milestone_plans/layer3-mockups/mockup-spec.txt` and `next_milestone_plans/layer3-mockups/assets.md` are present in the current checkout, preserve them as repo-tracked mockup source context only; do not promote them into merged milestones, active implementation scope, route/API live-state claims, or binary asset dependencies
- if refreshing from a checkout that matches current `main` after PR `#178`, keep that first-slice setup target in the tracked GitHub PR set and merged-history wording, and refresh the snapshot base and seed-checkout fields to the artifact refresh that already includes PR `#178`
- if refreshing from a checkout that matches current `main` after PR `#182`, keep that endpoint/state companion in the tracked GitHub PR set and merged-history wording, and refresh the snapshot base and seed-checkout fields to the artifact refresh that already includes PR `#182`
- if refreshing from a checkout that matches current `main` after PR `#196`, keep PRs `#181` through `#196` in the tracked GitHub PR set where applicable, refresh the snapshot base and seed-checkout fields to the artifact refresh that includes PR `#194`, and do not treat the closeout/correction, metadata-sync, proof-sync, board-metadata-sync, or read-only plan-preview implementation PRs as new merged milestones
- if refreshing from a checkout that matches current `main` after PR `#172`, keep that merged qualitative single-item input packet in the tracked GitHub PR set and merged-history wording, and refresh the snapshot base and seed-checkout fields to the artifact refresh that already includes PR `#172`
- if `next_milestone_plans/Layer3_planning_docs/27_L3_QUAL1_INPUTS.md` is present in the current checkout and the checkout matches current `main` after PR `#172`, keep it adjacent to `25_L3_QUAL1_FREEZE.md` as merged deferred-scope companion prep rather than treating it as a milestone or active-lane marker
- if refreshing from a checkout that matches current `main` after PR `#174`, keep that front-door tightening in the tracked GitHub PR set and merged-history wording, and refresh the snapshot base and seed-checkout fields to the artifact refresh that already includes PR `#174`
- if a future checkout carries additional branch-local `27_L3_QUAL1_INPUTS.md` revisions plus associated companion-doc edits beyond current `main`, keep them branch-local and planning-only rather than folded into current merged-state facts

Current merged-state fact to preserve when present:
- current `main` now also includes the landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`, the post-PR145 docs/progress sync from PR `#146`, and the later APS family settlement closeout from PR `#147`
- current `main` now also includes the post-PR147 progress-packet closeout from PR `#148`, which keeps the settled later APS family packet and its tracked PR history aligned with merged repo truth
- current `main` now also includes the merged planning-only `24_L3_WB_FREEZE.md` and `25_L3_QUAL1_FREEZE.md` docs from PR `#165`, but they remain deferred-scope prep artifacts and do not reopen the settled packet or change the merged milestone count
- current `main` now also includes the post-PR165 docs/progress/front-door sync from PR `#166`, which aligns the progress artifact, pack front door, and canonical status/index surfaces with those merged planning-only deferred-prep docs without changing the settled packet state
- current `main` now also includes the merged broader-workbench implementation-entry prep packet from PR `#168`, the post-PR168 current-main closeout from PR `#169`, and the post-PR169 duplicate-default cleanup from PR `#170`; together they land and finalize `26_L3_WB_INPUTS.md` plus companion updates to `24_L3_WB_FREEZE.md`, `25_L3_QUAL1_FREEZE.md`, `README_LAYER3_PHASE1A_PACK.md`, and the progress/control packet without changing the settled packet state or merged milestone count
- current `main` now also includes the merged qualitative single-item input packet from PR `#172`, which lands `27_L3_QUAL1_INPUTS.md` plus companion updates to `25_L3_QUAL1_FREEZE.md`, `README_LAYER3_PHASE1A_PACK.md`, and the progress/control packet as planning-only deferred-scope prep without changing the settled packet state or merged milestone count
- current `main` now also includes the post-PR172 deferred-prep front-door tightening from PR `#174`, which carries the merged workbench and qualitative companion prep into the remaining current-main status/front-door surfaces without changing the settled packet state or merged milestone count
- current `main` now also includes the merged planning-only `28_L3_WB_FIRST_SLICE_FREEZE.md` first-slice setup target from PR `#178`; preserve it as the first-slice scope/no-go contract, without treating PR `#178` by itself as changing the settled packet state, merged milestone count, current focus, or route/API live-state claims
- current `main` now also includes the merged planning-only `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md` endpoint/state companion from PR `#182`; preserve it as the first-slice API/state contract, without treating PR `#182` by itself as changing the settled packet state, merged milestone count, current focus, route/API live-state claims, schema/runtime widening posture, or downstream execution/package/handoff scope
- current `main` now also includes the bounded first-slice workbench implementation from PR `#184`; preserve `/review/layer3` and `/api/v1/layer3/...` as live only for the bounded first-slice shell/API, including UI non-authoritative Gate C typing preview plus explicit API owner-service typing materialization when `commit_typing` is true, not as full mockup/broader-workbench activation
- current `main` now also includes the post-PR184 status/cohesion/explicit-Gate-C-typing/review-feedback closeouts from PRs `#185` through `#190`; these preserve the bounded first-slice live scope while tightening response-envelope, Gate B blocked-error, Gate C authority-rail, and PR-tracking metadata
- current `main` now also includes the merged `30_L3_WB_PLAN_PREVIEW_FREEZE.md` and `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md` second-slice plan-preview prep from PR `#191`, the post-PR191 progress/tracked-metadata syncs from PRs `#192` and `#193`, the bounded read-only implementation from PR `#194`, and the post-PR194 proof/board-metadata closeouts from PRs `#195` and `#196`; preserve plan preview as live only after explicit Gate C typing commit and still keep downstream execution, results, package review, handoff, qualitative/hybrid/RAG/vector execution, runtime DB writes, schema widening, and LLM planning out of scope
- when present on a branch, the `32`/`33` plan-approval docs freeze only a later operator approval and approved-plan persistence boundary; they require a future implementation to add a narrow owner-service helper because current `materialize_pass_entry(...)` is execution-bearing
- the landed freeze from PR `#145` selected promotion as the first later APS family beyond the landed dedicated validate-only runtime/report-ref boundary while keeping retrieval cutover later during the freeze decision itself
- live repo truth now also shows the existing promotion governance family already sufficient on current `main`, while retrieval cutover already exists there as a separate validate-only parity-proof family

Also update the scheduled refresh task so it no longer:
- writes or references `current_main_commit`
- treats Mermaid as primary
- refreshes only the repo files while leaving the artifact itself stale

Success criteria:
- the artifact renders correctly without relying on Mermaid
- the milestone table is present without JS-created critical rows
- done, current focus, candidate next consumers, and deferred scope are visually distinct
- each deferred item shows both candidate-next and current-focus activation criteria in static HTML
- the scheduled refresh and the artifact are wired so the visible artifact actually updates after refresh
```
