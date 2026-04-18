# 02 Phase1A Implementation Prep Spec REV2

## Correction Note

This revision corrects the REV1 spec in three bounded ways:
1. it replaces broad wording that implied the analyst-insight/page/alias/runtime-helper baseline was simply absent at repo root with a revalidated current-main repo-root confirmation,
2. it corrects the repo/project posture wording so the broader six-lane posture is acknowledged while Phase 1A still reuses only the four directly relevant strengths,
3. it narrows the confidence rationale to the later-gate freezes that remain intentionally open.

Retained unchanged:
- `Phase 1A = Gate-B-only feeder/ledger entry`
- the bounded object set: `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, `l3_material_snapshot`
- the two-feeder-plane distinction
- the runtime DB read-only boundary
- the exclusion of typing, orchestration, packaging, APS handoff, route-family freeze, and consumer widening from the tranche

Material effect on judgment:
- readiness judgment: unchanged
- recommended next step: unchanged
- overall confidence: unchanged at `Medium`

Evidence basis: `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC.md|artifact|REV1 correction target`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Live repo reality: there are already multiple adjacent lanes|52-61`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current contract summary|34-52`; `R|backend/main.py|analyst_insight_page and root link|75-97`; `R|backend/app/api/router.py|review_nrc_aps plus legacy and alias analyst-insight routers|93-100`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`

## 1. Purpose and authority note

This document specifies only what must be prepared for a bounded `Phase 1A` implementation entry. It is not a redesign of Layer 3, and it does not reopen later-phase architecture.

Applied authority order for this correction lane:
1. primary planning
2. secondary planning
3. curated repo-root implementation-truth
4. same-path worktree confirmations
5. current implementation-prep docs
6. current final-pack artifacts
7. historical report artifacts

Primary-planning citation note:
- `P` citations whose path segment begins `layer3_primary_planningdocs/` refer to the external canonical Layer 3 planning corpus at `C:\Users\benny\OneDrive\Desktop\Layer3\layer3_primary_planningdocs`.
- Those files are not tracked in this repo/worktree and must not be misread as repo-local implementation truth.

Overall confidence for this spec remains `Medium`.
Reason: the Phase 1A object boundary is stable, and the former Gate C typing/unit blocker is now frozen by `next_milestone_plans/Layer3_planning_docs/05_GATEC_IMPLEMENTATION_FREEZE.md`, but later-gate freezes for the workbench route family and qualitative-engine ambition remain intentionally open. Those are later-phase blockers, not Phase 1A blockers.

## 2. Exact Phase 1A scope

1. `Settled from source evidence`
   `Conclusion:` Phase 1A remains a `Gate-B-only feeder/ledger entry` slice that starts after operator selection commit and stops before typing, orchestration, and packaging.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-135`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`

2. `Settled from source evidence`
   `Conclusion:` Phase 1A object scope remains limited to `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, and `l3_material_snapshot`.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Recommended first implementation slice|109-121`

3. `Recommended but not settled`
   `Conclusion:` Phase 1A should remain additive, internal, and service-first, with no new public route family and no consumer contract widening.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Boundary posture|41-47`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

## 3. Exact objects, contracts, and interfaces needed for Phase 1A

1. `Settled from source evidence`
   `Conclusion:` `l3_session` is the durable session header for a committed selection run and anchors the rest of the Phase 1A write order.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Session ledger entities|27-37`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-79`

2. `Settled from source evidence`
   `Conclusion:` `l3_selection_manifest` records the committed selection set as the first durable feeder/ledger object after session creation.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion|89-103`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|79-80`

3. `Settled from source evidence`
   `Conclusion:` `l3_descriptor` records descriptor expansion results per selection item, including explicit resolution outcomes rather than implied success.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion|103-119`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|80-81`

4. `Settled from source evidence`
   `Conclusion:` `l3_retrieval_event` records load attempts and outcomes against descriptor-backed materialization work, including failure-closed retrieval results.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Session ledger entities|40-49`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|81-83`

5. `Settled from source evidence`
   `Conclusion:` `l3_material_snapshot` stores refs to the normalized content material required downstream; Phase 1A prepares the snapshot ledgering boundary, not later typing or package artifacts.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Session ledger entities|50-58`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|83-89`

6. `Recommended but not settled`
   `Conclusion:` Minimum internal interfaces for Phase 1A are:
   - `commit_selection(session_input) -> l3_session + l3_selection_manifest`
   - `expand_descriptors(selection_manifest) -> l3_descriptor[*]`
   - `record_retrieval(descriptor, load_outcome) -> l3_retrieval_event`
   - `persist_material_snapshot(retrieval_event, storage_ref) -> l3_material_snapshot`
   These are internal service boundaries, not public route or consumer contracts.
   `Claim strength:` primary-planning evidence plus bounded implementation recommendation.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

## 4. Exact persistence and storage split needed for Phase 1A

1. `Settled from source evidence`
   `Conclusion:` The Phase 1A persistence model is a split between a durable ledger and a workspace/content-addressed material store. The ledger carries identity, status, refs, and outcomes; heavy payload bodies live outside the ledger.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`

2. `Settled from source evidence`
   `Conclusion:` The exact write order for Phase 1A is session, then selection manifest, then descriptors, then retrieval events, then material snapshots.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`

3. `Settled from source evidence`
   `Conclusion:` The runtime DB remains a read-only external surface and is not part of Phase 1A write-side persistence.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`; `R|backend/app/api/review_nrc_aps.py|runtime root and trace/source routes|23-31`

## 5. Exact feeder-plane touchpoints for Phase 1A

1. `Settled from source evidence`
   `Conclusion:` The generic quantitative plane and the APS feeder/content plane remain separate inputs into Phase 1A descriptor and retrieval work. They must not be collapsed into one generic source layer.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Frozen decisions in scope|17-22`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Source plane definitions|59-84`

2. `Settled from source evidence`
   `Conclusion:` The broader repo posture is six adjacent lanes, but only four reusable strengths are direct Phase 1A touchpoints: the quantitative plane, the APS feeder/context plane, the narrow analyst-insight kernel, and the mature APS downstream artifact lane.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Live repo reality: there are already multiple adjacent lanes|52-61`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Generic dataset/version/analysis plane already exists|65-89`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|APS connector/content/retrieval plane already exists|91-116`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|The shipped analyst-insight surface is real, but narrow|118-140`; `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|The APS downstream consumer/artifact lane already exists|143-160`

3. `Revised from REV1`
   `Conclusion:` Phase 1A may treat the analyst-insight kernel as a bounded reuse candidate through repo-root deterministic and legacy market-pipeline service logic, but the confirmed repo-root analyst-insight page, alias-router, static-asset, and runtime-helper surfaces remain adjacent surfaces and do not authorize route/UI widening or consumer coupling in Gate B.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Shipped analyst-insight kernel|127-148`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary and current contract summary|20-52`; `R|backend/main.py|analyst_insight_page and root link|75-97`; `R|backend/app/api/router.py|review_nrc_aps plus legacy and alias analyst-insight routers|93-100`; `R|backend/app/api/market_data_integration.py|router and alias_router surfaces|1-59`; `R|backend/app/api/market_data_validation.py|router and alias_router surfaces|1-49`; `R|backend/app/api/market_insight_ai.py|router and alias_router surfaces|1-32`; `R|backend/app/review_ui/static/analyst_insight.html|present|exists`; `R|backend/app/review_ui/static/analyst_insight.js|present|exists`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`

## 6. Exact write-side vs read-side boundaries for Phase 1A

1. `Settled from source evidence`
   `Conclusion:` Write-side scope is limited to the five Phase 1A ledger/material objects and their storage refs.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`

2. `Settled from source evidence`
   `Conclusion:` Read-side scope is limited to feeder-plane inputs, descriptor resolution inputs, retrieval inputs, existing reusable deterministic logic, and read-only runtime/context lookups where explicitly allowed.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|First-pass reuse recommendation|180-185`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/market_data_integration.py|build_integrated_dataset|1-79`; `R|backend/app/services/market_data_validation.py|validate_market_rows|1-231`; `R|backend/app/services/market_insight_ai.py|process_market_insights and heuristic emitters|1-152`

3. `No-go for current horizon`
   `Conclusion:` Phase 1A must not introduce runtime DB writes, direct APS artifact writes, or write-through behavior into existing analyst-insight or APS review/operator surfaces.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`; `R|backend/app/api/review_nrc_aps.py|runtime root and trace/source routes|23-31`

## 7. Exact assumptions allowed for Phase 1A

1. `Allowed and settled`
   `Conclusion:` It is safe to assume the two feeder planes are distinct, selection commit is the Layer 3 entry boundary, and descriptor expansion must produce explicit outcomes.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-135`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Source plane definitions|59-84`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`

2. `Allowed and settled`
   `Conclusion:` It is safe to assume the runtime DB boundary remains read-only, and that the repo-root runtime-helper module is a consumer-side read-only surface rather than a write-side authorization for Phase 1A.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`; `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`

3. `Allowed and settled`
   `Conclusion:` It is safe to assume the repo has broader six-lane overlap beyond Phase 1A, while only four of those strengths are direct reuse candidates for the Phase 1A entry slice.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Live repo reality: there are already multiple adjacent lanes|52-61`

## 8. Exact assumptions not allowed for Phase 1A

1. `Not allowed`
   `Conclusion:` Phase 1A may not assume typing, analysis-set formation, pass execution, package creation, handoff shape, or consumer routing is already frozen.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is still intentionally not frozen|85-91`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

2. `Revised from REV1`
   `Conclusion:` Phase 1A may not assume that the presence of repo-root analyst-insight page, alias-router, same-path static assets, or `review_nrc_aps_runtime_db.py` authorizes touching those surfaces or widening the tranche. They are confirmed adjacent surfaces, not Gate-B owner surfaces.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|The shipped analyst-insight surface is real, but narrow|118-140`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Boundary posture|41-47`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary and current contract summary|20-52`; `R|backend/main.py|analyst_insight_page and root link|75-97`; `R|backend/app/api/router.py|review_nrc_aps plus legacy and alias analyst-insight routers|93-100`; `R|backend/app/review_ui/static/analyst_insight.html|present|exists`; `R|backend/app/review_ui/static/analyst_insight.js|present|exists`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`

3. `Not allowed`
   `Conclusion:` Phase 1A may not smuggle in a new truth surface, self-HTTP reuse, generalized route-family redesign, or a merged generic source layer as a convenience shortcut.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open questions|24-31`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Frozen decisions in scope|17-22`

## 9. What must wait until Phase 2+

1. `Deferred / not for this tranche`
   `Conclusion:` `l3_typing_record`, analysis units, analysis sets, pass records, package artifacts, handoff packets, and downstream consumer-specific material remain Phase 2+ work.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|84-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

2. `Deferred / not for this tranche`
   `Conclusion:` Public workbench/UI route freeze, analyst-facing widening, APS handoff packaging, and broader consumer admission remain outside Phase 1A even if adjacent reusable repo surfaces already exist.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open questions|24-31`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Must-have|67-72`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

## 10. Concise evidence appendix

Primary planning anchors most heavily relied upon in this revision:
- `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Live repo reality: there are already multiple adjacent lanes|52-61`
- `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion and resolution outcomes|89-131`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split and canonical write order|61-89`
- `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Shipped analyst-insight kernel and reuse anti-patterns|127-195`
- `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B and Gate C|95-105`
- `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Recommended first implementation slice and explicit out-of-scope items|109-129`

Repo-root anchors most heavily relied upon in this revision:
- `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current status summary and current contract summary|20-52`
- `R|backend/main.py|analyst_insight_page and root link|75-97`
- `R|backend/app/api/router.py|review_nrc_aps plus legacy and alias analyst-insight routers|93-100`
- `R|backend/app/api/market_data_integration.py|router and alias_router surfaces|1-59`
- `R|backend/app/api/market_data_validation.py|router and alias_router surfaces|1-49`
- `R|backend/app/api/market_insight_ai.py|router and alias_router surfaces|1-32`
- `R|backend/app/services/market_data_integration.py|build_integrated_dataset|1-79`
- `R|backend/app/services/market_data_validation.py|validate_market_rows|1-231`
- `R|backend/app/services/market_insight_ai.py|process_market_insights and heuristic emitters|1-152`
- `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`
- `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`
