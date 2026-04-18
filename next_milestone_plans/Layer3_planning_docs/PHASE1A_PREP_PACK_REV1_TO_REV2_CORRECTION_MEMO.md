# Phase1A Prep Pack REV1 To REV2 Correction Memo

## Historical Note

This memo explains why REV2 was created from the earlier REV1 snapshot.
On current `main`, the repo-root analyst-insight page, alias-router, static-asset, and runtime-helper same-path surfaces are now live.
Treat the contradiction table below as historical explanation of the REV2 pivot, not as current live-repo truth.

## 1. Purpose

This memo records the bounded correction from the REV1 Phase 1A prep pack to the REV2 pack. It is not a new architecture synthesis and it does not reopen the Phase 1A tranche boundary.

Authority order used for this correction pass:
1. primary planning
2. secondary planning
3. curated repo-root implementation-truth
4. same-path worktree confirmations
5. current implementation-prep docs
6. current final-pack artifacts
7. historical report artifacts

## 2. Claims retained unchanged

1. `Retained`
   `Claim:` `Phase 1A = Gate-B-only feeder/ledger entry`.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE.md|artifact|REV1 retained`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

2. `Retained`
   `Claim:` The Phase 1A object set remains `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, `l3_material_snapshot`.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC.md|artifact|REV1 retained`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`

3. `Retained`
   `Claim:` Typing, orchestration, packaging, APS handoff, route-family freeze, broader UI/API widening, and consumer widening remain out of Phase 1A.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN.md|artifact|REV1 retained`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

4. `Retained`
   `Claim:` The two feeder planes remain distinct and the runtime DB boundary remains read-only.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE.md|artifact|REV1 retained`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Source plane definitions|59-84`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`

## 3. Claims revised

1. `Revised`
   `From REV1:` broad wording that treated the analyst-insight/page/alias/runtime-helper situation as a generic repo-root absence or broad worktree-only divergence.
   `REV2 correction:` exact same-path code/status contradiction. Higher-authority planning and the repo-root analyst-insight status doc treat the narrow analyst-insight surface as real, current repo-root same-path code does not confirm five exact executable surfaces, and same-path worktree files do.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE.md|artifact|REV1 correction target`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|The shipped analyst-insight surface is real, but narrow|118-140`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary and current contract summary|20-52`; `R|backend/main.py|review routes only; no analyst_insight_page symbol|47-80`; `R|backend/app/api/router.py|legacy market_data routers only|93-97`; `W|worktrees/mainline-lane/backend/main.py|confirmation-only|75-77`; `W|worktrees/mainline-lane/backend/app/api/router.py|confirmation-only|98-100`

2. `Revised`
   `From REV1:` wording that implied there were only four relevant live strengths in the current repo posture.
   `REV2 correction:` the broader posture is six adjacent lanes, while only four directly relevant reusable strengths matter for Phase 1A.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE.md|artifact|REV1 correction target`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Live repo reality: there are already multiple adjacent lanes|52-61`

3. `Revised`
   `From REV1:` generic confidence rationale tied to broad repo-root/worktree mismatch.
   `REV2 correction:` confidence remains `Medium`, but the limiting factor is narrowed to the exact analyst-insight/runtime-helper executable-surface contradiction and is explicitly non-blocking for Phase 1A.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN.md|artifact|REV1 correction target`; `R|backend/main.py|review routes only; no analyst_insight_page symbol|47-80`; `R|backend/app/api/router.py|legacy market_data routers only|93-97`; `W|worktrees/mainline-lane/backend/main.py|confirmation-only|75-77`; `W|worktrees/mainline-lane/backend/app/api/router.py|confirmation-only|98-100`

## 4. Claims retracted

1. `Retracted`
   `Claim:` broad bundled phrasing that the repo-root analyst-insight overlap was simply "not established" without separating status-doc overlap, deterministic-kernel overlap, and exact same-path executable-surface mismatch.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE.md|artifact|REV1 retracted claim target`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current contract summary|34-52`

2. `Retracted`
   `Claim:` broad bundled wording that the whole analyst-insight/runtime-helper family should be carried as undifferentiated "worktree-only divergence."
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC.md|artifact|REV1 retracted claim target`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary|20-25`; `R|backend/main.py|review routes only; no analyst_insight_page symbol|47-80`; `W|worktrees/mainline-lane/backend/main.py|confirmation-only|75-77`

## 5. Five-target repo-root and worktree reconciliation

| Target | Repo-root result | Worktree result | Corrected disposition | Evidence |
| --- | --- | --- | --- | --- |
| `/review/analyst-insight` route in `backend/main.py` | Status doc describes it as live, but current repo-root `backend/main.py` does not implement it. | Same-path worktree `backend/main.py` does implement it. | Exact same-path code/status contradiction; not a broad analyst-insight absence claim. | `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary|20-21`; `R|backend/main.py|review routes only; no analyst_insight_page symbol|47-80`; `W|worktrees/mainline-lane/backend/main.py|confirmation-only|75-77` |
| analyst-insight alias-router inclusion in `backend/app/api/router.py` | Status doc describes alias routes as live, but repo-root router and repo-root `market_data_*` API files expose only legacy `router` surfaces. | Same-path worktree router includes `alias_router`, and same-path worktree `market_data_*` API files define it. | Exact same-path code/status contradiction; Phase 1A must not assume alias-router baseline in root checkout. | `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary and current contract summary|20-52`; `R|backend/app/api/router.py|legacy market_data routers only|93-97`; `R|backend/app/api/market_data_integration.py|router only; legacy prefix|1-39`; `R|backend/app/api/market_data_validation.py|router only; legacy prefix|1-34`; `R|backend/app/api/market_insight_ai.py|router only; legacy prefix|1-21`; `W|worktrees/mainline-lane/backend/app/api/router.py|confirmation-only|98-100`; `W|worktrees/mainline-lane/backend/app/api/market_data_integration.py|confirmation-only|1-59`; `W|worktrees/mainline-lane/backend/app/api/market_data_validation.py|confirmation-only|1-49`; `W|worktrees/mainline-lane/backend/app/api/market_insight_ai.py|confirmation-only|1-32` |
| `backend/app/review_ui/static/analyst_insight.html` | Status doc names the file, but the same-path repo-root file is not present. | Same-path worktree file exists. | Exact same-path asset contradiction; not proof that the whole analyst-insight kernel is missing. | `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current contract summary|43-52`; `R|backend/app/review_ui/static/analyst_insight.html|missing-at-repo-root|not present`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists` |
| `backend/app/review_ui/static/analyst_insight.js` | Status doc names the file, but the same-path repo-root file is not present. | Same-path worktree file exists. | Exact same-path asset contradiction; not proof that the whole analyst-insight kernel is missing. | `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current contract summary|43-52`; `R|backend/app/review_ui/static/analyst_insight.js|missing-at-repo-root|not present`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists` |
| `backend/app/services/review_nrc_aps_runtime_db.py` | Same-path repo-root helper file is not present, but the runtime DB read-only boundary is still confirmed by primary planning and repo-root trace/runtime routes. | Same-path worktree helper file exists. | Exact helper-path divergence; not runtime-boundary ambiguity. | `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_runtime_db.py|missing-at-repo-root|not present`; `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`; `R|backend/app/api/review_nrc_aps.py|runtime root and trace/source routes|23-31`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists` |

## 6. Cross-doc consistency outcome

1. `Confirmed`
   `Conclusion:` The REV2 baseline, prep spec, and validation plan all retain the same Phase 1A scope, the same object set, the same no-go boundaries, and the same corrected confidence rationale.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|final REV2`; `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md|artifact|final REV2`; `A|next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md|artifact|final REV2`

## 7. Readiness and confidence impact

1. `No change`
   `Overall confidence:` remains `Medium`.
   `Why:` unresolved wording was corrected into an exact same-path contradiction, but the contradiction still exists and still prevents a higher confidence ceiling.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|section 9`; `A|next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md|artifact|section 9`

2. `No change`
   `Readiness judgment:` unchanged. The pack remains sufficient for a bounded Phase 1A implementation entry.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|section 9`; `A|next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md|artifact|section 9`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

3. `No change`
   `Recommended next step:` unchanged. Accept the corrected pack and proceed, when implementation is authorized, with the bounded Gate-B-only feeder/ledger slice.
   `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|section 7`; `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md|artifact|sections 2-9`

4. `No change`
   `Broader architecture or tranche content reopened:` no.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Frozen decisions in scope|17-24`; `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|Correction Note`
