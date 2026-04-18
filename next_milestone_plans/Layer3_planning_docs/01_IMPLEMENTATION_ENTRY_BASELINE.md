# 01 Implementation Entry Baseline

## 1. Purpose and authority note

This document fixes the working baseline for a bounded implementation-entry pass only. It is not a full Layer 3 architecture restatement. It treats primary planning as baseline authority, secondary planning as supplemental only, curated repo-root files as implementation truth, same-path worktree files as confirmation only, current candidate final-pack artifacts as comparison-only synthesis, and historical report artifacts as lowest-authority comparison material.

Overall confidence for this baseline is `Medium`.
Reason: all text-readable primary files, materially used secondary files, all text-readable curated repo-root files that exist, and all three current candidate final-pack artifacts were fully read in this pass, but three curated same-path repo-root/worktree contradictions remain unresolved and therefore cap overall confidence.

## 2. Sources used and authority model

Applied authority ladder for this pack:
1. Primary planning
2. Secondary planning
3. Repo-root curated implementation-truth
4. Same-path worktree confirmation
5. Current candidate final-pack artifacts
6. Historical report artifacts

Comparison-only artifacts used for omission/defect detection, not for settlement:
- `A|FINAL_LAYER3_SPEC.md|artifact|comparison-only`
- `A|FINAL_LAYER3_DECISIONS_AND_OPEN_ITEMS.md|artifact|comparison-only`
- `A|FINAL_LAYER3_IMPLEMENTATION_AND_VALIDATION_PLAN.md|artifact|comparison-only`

## 3. Current repo/project posture summary

1. `Settled from source evidence`
   `Conclusion:` The current repo posture is to continue above the already-frozen APS analytical ceiling with a bounded continuation, not to reopen lower-layer surfaces or imply a broad new platform cutover.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `R|docs/nrc_adams/nrc_aps_status_handoff.md|Upper analytical ceiling|21-21`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Recommended next continuation|178-184`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`

2. `Settled from source evidence`
   `Conclusion:` The planning pack is specific enough for controlled implementation entry, but route-family freeze, first-v1 typing heuristics, and qualitative-engine ambition are still intentionally unfrozen and must not be silently treated as settled.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Needs explicit user freeze or confirmation|131-135`

3. `Settled from source evidence`
   `Conclusion:` Repo-root implementation truth already includes four relevant live strengths: a generic quantitative dataset/version/analysis plane, an APS feeder/context plane, a mature APS downstream artifact lane, and a narrow deterministic analyst-insight kernel. None of these is already the full intended Layer 3 workspace.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Generic dataset/version/analysis plane already exists|65-89`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|APS connector/content/retrieval plane already exists|91-116`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|The shipped analyst-insight surface is real, but narrow|118-140`; `R|backend/app/models/models.py|Dataset; DatasetVersion; AnalysisRun|36-219`; `R|backend/app/models/models.py|ConnectorRun; ConnectorRunTarget|246-444`; `R|backend/app/models/models.py|ApsContentDocument; ApsContentChunk; ApsContentLinkage; ApsRetrievalChunk|522-659`; `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`; `R|backend/app/services/market_insight_ai.py|trend/correlation/emerging_risk insight emitters|53-162`

4. `Open due to curated-evidence insufficiency`
   `Conclusion:` A repo-root analyst-insight page/alias-route/runtime-db baseline is not established in the provided curated repo-root materials for this pass. The same paths do exist in `worktrees/mainline-lane`, but that is `worktree-only divergence — not repo-root implementation truth.`
   `Claim strength:` direct repo-root implementation evidence for the narrower repo-root route baseline, plus same-path worktree confirmation.
   `Evidence:` `R|docs/analyst_insight/analyst_insight_status_handoff.md|Purpose and truth model|3-14`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary table|18-25`; `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

## 4. Settled implementation-entry baseline

1. `Settled from source evidence`
   `Conclusion:` Layer 3 begins at operator selection commit, not at the external workbench or earlier feeder-plane browsing surface.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Inside Layer 3|62-63`; `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-135`

2. `Settled from source evidence`
   `Conclusion:` The generic quantitative plane and the APS feeder/context plane remain distinct feeder planes. Phase entry must not collapse them into one generic source layer.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|95-98`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Generic dataset/version/analysis plane already exists|65-89`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|APS connector/content/retrieval plane already exists|91-116`

3. `Settled from source evidence`
   `Conclusion:` A committed selection set is not directly executable; it must first become a selection manifest and then expand into descriptors with explicit resolution outcomes.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion|89-92`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Required descriptor fields|101-111`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`

4. `Settled from source evidence`
   `Conclusion:` The persistence model is a split between a durable session ledger and a workspace/content-addressed store. Snapshot and later payload bodies belong in the workspace store, not in a monolithic relational execution body.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`

5. `Settled from source evidence`
   `Conclusion:` The runtime DB plane is read-only and may not become the Layer 3 ledger or an incidental write target.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Boundary 2 - write-side DB vs runtime DB|67-69`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`

6. `Settled from source evidence`
   `Conclusion:` The existing analyst-insight kernel may be reused later as a narrow service-layer kernel, but it is not the full orchestration layer and should not be reused by internal HTTP self-calls.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Shipped analyst-insight kernel|127-148`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`; `R|backend/app/api/market_data_integration.py|router prefix /market-pipeline/integration|1-20`; `R|backend/app/api/market_data_validation.py|router prefix /market-pipeline/validation|1-20`; `R|backend/app/api/market_insight_ai.py|router prefix /market-pipeline/insights|1-20`

## 5. Explicit current-horizon scope

1. `Settled from source evidence`
   `Conclusion:` The current horizon is a controlled implementation-entry pass that preserves boundedness, additive change, and low regression burden rather than attempting a broad first slice.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-152`

2. `Recommended but not settled`
   `Conclusion:` The safest current-horizon entry is an internal, additive, Gate-B-only slice that records selection, descriptor expansion, retrieval outcomes, and material snapshots without widening public route families or consumer contracts.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Recommended first implementation slice|109-121`; `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`

## 6. Explicit non-goals and no-go boundaries

1. `Deferred / not for this tranche`
   `Conclusion:` Typing, analysis-unit/set formation, pass execution, quarantine/rerun behavior, reconciliation, and output packaging must not be smuggled into Phase 1A.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

2. `No-go for current horizon`
   `Conclusion:` Direct APS artifact emission, widened runtime-document-trace integration, generalized route-family redesign, and maximal consumer fan-out are out of scope for Phase 1A.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`; `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`

3. `No-go for current horizon`
   `Conclusion:` The shipped analyst-insight surface must not be overstated into a repo-root-accepted Layer 3 UI baseline for this pass.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|What this surface does not yet provide|133-140`; `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

## 7. Exact safest first tranche recommendation

1. `Recommended but not settled`
   `Conclusion:` Define `Phase 1A` as a `Gate-B-only feeder/ledger entry slice`.
   `Included scope:` `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, and `l3_material_snapshot`, plus the minimum internal interfaces needed to commit selection, expand descriptors, record load outcomes, and persist snapshot payload references.
   `Excluded scope:` `l3_typing_record` onward, any pass family, any package family, any new public route family, any direct APS artifact emission, and any runtime DB write path.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

2. `Recommended but not settled`
   `Conclusion:` Keep Phase 1A additive and service-first. Reuse upstream feeder/context surfaces as read-side inputs only, and avoid introducing a new public truth surface until later gates are explicitly frozen.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|First-pass reuse recommendation|180-185`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|137-140`

## 8. Exact blockers and freezes still needed for later phases

1. `Open due to architecture ambiguity`
   `Conclusion:` The exact future workbench route family still requires explicit freeze before any public Layer 3 route surface is landed.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Needs explicit user freeze or confirmation|131-135`

2. `Open due to architecture ambiguity`
   `Conclusion:` First-v1 typing heuristics remain unfrozen and therefore block typing/orchestration work beyond Phase 1A.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`

3. `Open due to architecture ambiguity`
   `Conclusion:` Qualitative-engine ambition beyond the narrow reusable deterministic pieces remains unfrozen and must wait.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Needs explicit user freeze or confirmation|131-135`

4. `Deferred / not for this tranche`
   `Conclusion:` Canonical internal package freeze, handoff strategy choice, and first consumer scope definition must be completed before packaging or downstream consumer work begins.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`; `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Canonical internal package|126-176`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Must-have|67-72`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`

## 9. Concise readiness judgment

1. `Recommended but not settled`
   `Conclusion:` The repo is ready for a bounded `Phase 1A` implementation entry if, and only if, the project accepts the narrower `Gate-B-only feeder/ledger` tranche instead of forcing the broader first slice described in the roadmap doc.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Recommended first implementation slice|109-121`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`; `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`

2. `Settled from source evidence`
   `Conclusion:` The repo is not ready to claim Phase 2+ readiness for typing, orchestration, packaging, or consumer widening.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`

3. `Settled from source evidence`
   `Conclusion:` Overall baseline confidence remains `Medium` because repo-root/worktree same-path contradictions remain unresolved for three curated paths.
   `Claim strength:` direct repo/worktree evidence.
   `Evidence:` `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`; `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

## 10. Concise evidence appendix

Primary planning sources most heavily relied upon in this baseline:
- `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Generic dataset/version/analysis plane already exists|65-89`
- `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|APS connector/content/retrieval plane already exists|91-116`
- `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`
- `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`
- `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

Curated repo-root implementation-truth sources most heavily relied upon in this baseline:
- `R|docs/nrc_adams/nrc_aps_status_handoff.md|Recommended next continuation|178-184`
- `R|backend/main.py|StaticFiles mounts and review routes|47-64`
- `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`
- `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`
- `R|backend/app/models/models.py|Dataset; DatasetVersion; AnalysisRun|36-219`
- `R|backend/app/models/models.py|ConnectorRun; ConnectorRunTarget|246-444`
- `R|backend/app/models/models.py|ApsContentDocument; ApsContentChunk; ApsContentLinkage; ApsRetrievalChunk|522-659`

Same-path worktree confirmations used only as divergence notes:
- `W|worktrees/mainline-lane/backend/app/services/review_nrc_aps_runtime_db.py|confirmation-only|exists`
- `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`
- `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`
