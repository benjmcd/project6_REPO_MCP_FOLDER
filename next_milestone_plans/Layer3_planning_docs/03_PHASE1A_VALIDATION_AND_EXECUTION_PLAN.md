# 03 Phase1A Validation and Execution Plan

## Historical Note

This REV1 artifact preserves an earlier repo snapshot and is superseded by `03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`.
On current `main`, repo-root now contains the analyst-insight page, alias-router, static-asset, and runtime-helper same-path surfaces.
Do not treat the analyst-insight mismatch wording below as current live truth.

## 1. Purpose and authority note

This document defines the bounded sequencing, proof, risk, and rollback posture for `Phase 1A = Gate-B-only feeder/ledger entry`. It does not authorize a broader first slice.

Overall confidence for this plan is `Medium`.
Reason: the gate model and tranche boundary are source-grounded, but overall confidence is capped by unresolved repo-root/worktree same-path contradictions and by later-phase freezes that remain intentionally open.

Execution note from repo instructions: if browser proof is run for this tranche, compare headed Chrome and headless Chrome; and any `validate-*` action used during implementation must remain validate-only and fail closed on empty runtime.

## 2. Tranche sequencing and dependency order

1. `Settled from source evidence`
   `Sequence step:` accept Gate A inputs as already sufficient for controlled implementation entry.
   `What this means:` use the existing planning baseline, invariants, glossary, and ADR-level framing as the entry basis; do not reopen architecture synthesis before Phase 1A.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate A - planning/baseline entry|88-93`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`

2. `Recommended but not settled`
   `Sequence step:` freeze the Phase 1A contract subset before coding.
   `What this means:` freeze `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, and `l3_material_snapshot` as the only new Phase 1A durable objects, and defer all later objects.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

3. `Recommended but not settled`
   `Sequence step:` implement the write path in canonical order and stop at material snapshots.
   `What this means:` `l3_session` -> `l3_selection_manifest` -> `l3_descriptor` -> `l3_retrieval_event` + `l3_material_snapshot`.
   `Claim strength:` direct primary-planning evidence for the order; recommendation only for the stop point.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

4. `Recommended but not settled`
   `Sequence step:` prove the slice before any Gate C work starts.
   `What this means:` add contract proof and session proof for the loading slice, then stop rather than opportunistically continuing into typing or packages.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-152`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|120-127`

5. `Deferred / not for this tranche`
   `Sequence step:` do not cross Gate C or Gate D in the same implementation entry.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

## 3. Validation, proof, and gate plan

1. `Settled from source evidence`
   `Gate decision:` Gate A is already satisfied enough for this bounded entry.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate A - planning/baseline entry|88-93`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`

2. `Settled from source evidence`
   `Gate decision:` Gate B requires the selection-manifest contract, descriptor contract, and minimum session-ledger fields to be frozen enough before load logic lands.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

3. `Recommended but not settled`
   `Required proof set for Phase 1A:` one implementation/status note, one machine-checkable proof surface, one explicit remaining-gap list, and one live/not-live statement that does not overstate later phases.
   `Claim strength:` direct primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`

4. `Recommended but not settled`
   `Required execution proofs:` strong unit and contract proof for the five new core objects, one end-to-end session happy path, and one partial-failure path.
   `Claim strength:` direct primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-152`; `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Frozen decisions in scope|25-30`

5. `Settled from source evidence`
   `Fail-closed proof requirements:` the slice must fail closed if the ledger cannot record what happened, if source-plane material cannot be traced to descriptors, or if runtime DB boundaries would be violated.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|120-127`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`

6. `Deferred / not for this tranche`
   `Landing rule:` Phase 1A may enter implementation without a broad new workbench, but it must not be called fully landed until Gate E proof exists, including at least one operator-readable/browser-visible path.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate E - ship gate|113-118`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Browser-proof minimums for the first pass|136-144`

## 4. Blast radius, regression risk, and operator burden register

1. `Recommended but not settled`
   `Risk area:` new truth surface introduction
   `Current judgment:` acceptable only because Layer 3 requires its own ledger/workspace entry surfaces; keep that truth surface internal, additive, and bounded to Phase 1A.
   `Blast radius:` `Low to Medium`
   `Operator burden:` `Low`
   `Mitigation:` no public route-family freeze, no consumer widening, no reuse-by-self-HTTP.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`

2. `Settled from source evidence`
   `Risk area:` feeder-plane collapse or naming drift
   `Current judgment:` keep the quantitative plane and APS plane separate in both descriptors and provenance, or the tranche will create avoidable tech debt and trace confusion.
   `Blast radius:` `Medium`
   `Operator burden:` `Low`
   `Mitigation:` require `source_plane`, explicit descriptor basis, and explicit source provenance on snapshots.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|95-99`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Required descriptor fields|101-111`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`

3. `Settled from source evidence`
   `Risk area:` runtime-boundary confusion
   `Current judgment:` runtime DB coupling would create high regression and operator burden and is therefore forbidden in Phase 1A.
   `Blast radius:` `High` if violated
   `Operator burden:` `High` if violated
   `Mitigation:` keep runtime DBs entirely outside the Phase 1A write path.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`

4. `Recommended but not settled`
   `Risk area:` regression to existing APS downstream surfaces
   `Current judgment:` risk remains low if Phase 1A stops before direct APS artifact emission and treats existing APS downstream artifacts as future handoff targets rather than active Phase 1A outputs.
   `Blast radius:` `Low`
   `Operator burden:` `Low`
   `Mitigation:` no direct APS artifact emission, no schema widening, no new consumer admission in Phase 1A.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`; `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`; `R|backend/app/schemas/api.py|NrcApsEvidenceBundleOut through NrcApsDeterministicChallengeReviewPacketOut|582-1154`

5. `Open due to curated-evidence insufficiency`
   `Risk area:` analyst-insight repo-root/worktree divergence
   `Current judgment:` any Phase 1A plan that depends on a repo-root analyst-insight page, alias-route family, or `review_nrc_aps_runtime_db.py` surface carries avoidable ambiguity.
   `Blast radius:` `Medium`
   `Operator burden:` `Medium`
   `Mitigation:` treat those same paths as `worktree-only divergence — not repo-root implementation truth.` Keep Phase 1A independent of them.
   `Claim strength:` repo-root implementation evidence + same-path worktree confirmation.
   `Evidence:` `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary table|18-25`; `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

## 5. Rollback and reversibility register

1. `Recommended but not settled`
   `Rollback item:` Phase 1A ledger/workspace introduction
   `Rollback posture:` reversible at low cost if implemented as additive Layer 3-only storage and internal entry logic. Upstream feeder planes remain unchanged.
   `Why rollback is cheap:` no replacement of existing quantitative, APS, review, or market-pipeline surfaces is required.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|APS feeder/context plane|150-169`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`

2. `Recommended but not settled`
   `Rollback item:` provisional internal entrypoint or proof surface
   `Rollback posture:` reversible at low cost if kept internal or explicitly provisional and not allowed to become the frozen public route family.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Recommended route family and API family shape|151-182`

3. `Settled from source evidence`
   `Rollback item:` runtime DB coupling
   `Rollback posture:` do not enter this state at all in Phase 1A.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`

## 6. Implementation-entry risks and mitigations

1. `Open due to architecture ambiguity`
   `Risk:` `l3_material_snapshot` timestamp field naming is not fully frozen.
   `Mitigation:` keep the contract bounded to the already-shared identity/provenance fields and require an explicit later freeze before widening timestamp semantics.
   `Claim strength:` direct primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|137-149`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|168-183`

2. `Open due to curated-evidence insufficiency`
   `Risk:` worktree-only analyst-insight/runtime-db surfaces may tempt implementation to depend on a repo-root baseline that is not established in this pass.
   `Mitigation:` keep Phase 1A independent of those surfaces; if later work needs them, re-open the repo-root/worktree divergence explicitly before coding.
   `Claim strength:` repo-root implementation evidence + same-path worktree confirmation.
   `Evidence:` `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

3. `No-go for current horizon`
   `Risk:` scope creep into typing, pass execution, package creation, or consumer integration.
   `Mitigation:` stop at Gate B and treat any attempt to add Gate C/D objects as tranche violation.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

4. `No-go for current horizon`
   `Risk:` silent plane collapse, naming drift, or execution-engine confusion.
   `Mitigation:` preserve explicit `source_plane` and provenance, and forbid treating APS or the narrow analyst-insight kernel as the full execution engine.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|APS feeder/context plane|150-169`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`

## 7. What evidence must exist before Phase 2 is allowed

1. `Settled from source evidence`
   `Required evidence:` accepted Phase 1A proof artifacts showing contract proof, one happy path, one partial-failure path, and an explicit live/not-live statement.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-152`

2. `Settled from source evidence`
   `Required evidence:` explicit typing-heuristic freeze, accepted analysis-unit/set model, and accepted pass-state model.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`

3. `Settled from source evidence`
   `Required evidence:` canonical internal package definition, handoff strategy choice, and first consumer scope definition.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`; `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Canonical internal package|126-176`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Must-have|67-72`

4. `Recommended but not settled`
   `Required evidence:` if Phase 2 intends to add a public surface, route-family freeze must be explicit before that work starts.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Recommended route family and API family shape|151-182`

5. `Open due to curated-evidence insufficiency`
   `Required evidence:` if later phases intend to rely on analyst-insight page/alias-route/runtime-db same paths, the current repo-root/worktree divergence must be resolved first.
   `Claim strength:` repo-root implementation evidence + same-path worktree confirmation; recommendation only.
   `Evidence:` `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary table|18-25`; `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

## 8. What should explicitly not be implemented yet

1. `No-go for current horizon`
   `Conclusion:` do not implement typing, modality overrides, analysis-unit/set formation, pass orchestration, quarantine flows, rerun flows, reconciliation, or package creation.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Frozen decisions in scope|25-30`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

2. `No-go for current horizon`
   `Conclusion:` do not implement direct APS artifact emission, widened runtime-document-trace integration, deep compare/trace additive integration, or broad consumer fan-out.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

3. `No-go for current horizon`
   `Conclusion:` do not treat the shipped analyst-insight page or alias routes as the settled repo-root Layer 3 workbench baseline for this tranche.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Current workbench/new surface warning|27-29`; `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`

4. `No-go for current horizon`
   `Conclusion:` do not use runtime DBs as write-side state and do not replace existing market-pipeline or review surfaces.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`

## 9. Concise implementation-readiness judgment

1. `Recommended but not settled`
   `Conclusion:` The safest implementation entry is ready now if the team accepts the narrower Gate-B-only tranche and treats Phase 1A as an internal additive slice rather than a broad first launch.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Recommended first implementation slice|109-121`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Recommended next continuation|178-184`

2. `Settled from source evidence`
   `Conclusion:` The tranche is not ready to be called landed until Gate E proof exists, and it is not ready to expand into Phase 2 without additional freezes and proof.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate E - ship gate|113-118`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Browser-proof minimums for the first pass|136-144`

3. `Settled from source evidence`
   `Conclusion:` Overall implementation-entry confidence remains `Medium`.
   `Claim strength:` direct source-read completeness plus unresolved divergence status.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`; `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

## 10. Concise evidence appendix

Primary planning anchors most heavily relied upon in this plan:
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`
- `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Frozen decisions in scope|25-30`
- `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`
- `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Current workbench/new surface warning|27-29`
- `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`
- `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`
- `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Must-have|67-72`
- `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate E - ship gate|113-118`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-152`

Repo-root anchors most heavily relied upon in this plan:
- `R|docs/nrc_adams/nrc_aps_status_handoff.md|Recommended next continuation|178-184`
- `R|backend/main.py|StaticFiles mounts and review routes|47-64`
- `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`
- `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`
- `R|backend/app/schemas/api.py|NrcApsEvidenceBundleOut through NrcApsDeterministicChallengeReviewPacketOut|582-1154`
- `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`

Worktree-only divergence references retained only for boundary control:
- `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`
- `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`
- `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`
