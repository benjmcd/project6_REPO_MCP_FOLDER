# 02 Phase1A Implementation Prep Spec

## Historical Note

This REV1 artifact preserves an earlier repo snapshot and is superseded by `02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`.
On current `main`, repo-root now contains the analyst-insight page, alias-router, static-asset, and runtime-helper same-path surfaces.
Do not treat the analyst-insight mismatch wording below as current live truth.

## 1. Purpose and authority note

This document specifies only the safest first implementation tranche defined in `01_IMPLEMENTATION_ENTRY_BASELINE.md`: `Phase 1A = Gate-B-only feeder/ledger entry`. It does not authorize typing, orchestration, packaging, consumer widening, or public route-family freeze.

Overall confidence for this spec is `Medium`.
Reason: the object set and tranche boundary are strongly supported by the primary pack, but repo-root/worktree same-path contradictions remain unresolved and one primary-pack timestamp detail for `l3_material_snapshot` is not fully frozen.

## 2. Exact Phase 1A scope

1. `Recommended but not settled`
   `Conclusion:` `Phase 1A` should stop after selection commit, descriptor expansion, explicit resolution recording, and material snapshot persistence.
   `Claim strength:` primary + repo triangulation; recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/00D_LAYER3_PACK_COHERENCE_AND_GAP_AUDIT.md|What is now adequately specified for planning purposes|93-108`

2. `Deferred / not for this tranche`
   `Conclusion:` `l3_typing_record`, `l3_analysis_unit`, `l3_analysis_group`, `l3_analysis_set`, `l3_analysis_plan`, `l3_pass_run`, `l3_reconciliation_record`, and `l3_output_package` are outside Phase 1A.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

3. `No-go for current horizon`
   `Conclusion:` Phase 1A must not smuggle in direct APS artifact emission, widened runtime-document-trace integration, route-family redesign, or broad consumer fan-out.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`; `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`

## 3. Exact objects, contracts, and interfaces needed for Phase 1A

### 3.1 Durable objects

1. `Settled from source evidence`
   `Object:` `l3_session`
   `Required fields:` `session_id`, `created_at`, `started_at`, `completed_at`, `status`, `selection_manifest_id`, `entry_route_context_json`, `operator_context_json`, `summary_json`
   `Phase 1A usage:` record one analytical session and loading-stage state only.
   `Phase 1A status subset:` `draft_created`, `active_loading`, `completed`, `completed_with_warnings`, `failed`, `cancelled`
   `Deferred statuses:` `active_typing`, `active_planning`, `active_execution`, `active_reconciliation`
   `Claim strength:` direct primary-planning evidence for the full contract; recommendation only for the active Phase 1A subset.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_session|92-117`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

2. `Settled from source evidence`
   `Object:` `l3_selection_manifest`
   `Required fields:` `selection_manifest_id`, `session_id`, `manifest_json`, `source_plane_hints_json`, `selection_hash`, `committed_at`, `commit_reason`
   `Phase 1A usage:` one committed selection set per session entry, with enough source-plane hinting to drive descriptor expansion.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_selection_manifest|118-129`; `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-135`

3. `Settled from source evidence`
   `Object:` `l3_descriptor`
   `Required fields:` `descriptor_id`, `session_id`, `selection_manifest_id`, `source_plane`, `descriptor_type`, `selector_payload_json`, `selection_basis_json`, `expansion_reason`, `status`, `descriptor_hash`
   `Required status vocabulary:` `expanded`, `resolved_loaded`, `resolved_empty`, `resolved_partial`, `ambiguous`, `unsupported`, `failed`, `skipped`
   `Phase 1A usage:` one source-plane-specific descriptor per executable lookup intent; no descriptor may disappear silently.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Required descriptor fields|101-111`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_descriptor|130-154`

4. `Settled from source evidence`
   `Object:` `l3_retrieval_event`
   `Required fields:` `retrieval_event_id`, `session_id`, `descriptor_id`, `outcome`, `reason_code`, `material_snapshot_ids_json`, `event_payload_json`, `occurred_at`
   `Phase 1A usage:` one explicit load-resolution record per descriptor resolution attempt.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|155-184`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`

5. `Settled from source evidence`
   `Object:` `l3_material_snapshot`
   `Required fields established across the primary pack:` `material_snapshot_id`, `session_id`, `descriptor_id`, `source_plane`, `source_shape`, `payload_ref`, `payload_hash`, `source_identity_json`, `source_provenance_json`, `co_retrieval_group_id`, `load_summary_json`
   `Phase 1A usage:` record the session-scoped material that actually entered the session; snapshots are not yet analysis units.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|155-184`; `P|layer3_primary_planningdocs/04_LAYER3_ANALYSIS_UNIT_MODALITY_AND_SET_MODEL.md|source_shape, modality, and set distinctions|27-30`

6. `Open due to architecture ambiguity`
   `Conclusion:` The primary pack is not fully frozen on the top-level snapshot timestamp name. One primary source requires `retrieved_at`; another requires `created_at`.
   `Phase 1A handling rule:` do not widen the settled object contract by inventing two required top-level timestamp fields unless later freeze work explicitly approves it.
   `Claim strength:` direct primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|137-149`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|168-183`

### 3.2 Interface responsibilities

1. `Settled from source evidence`
   `Conclusion:` Exact function, class, and module names are not established in the provided materials.
   `Claim strength:` Not established in the provided materials.
   `Evidence:` `Not established in the provided materials.`

2. `Recommended but not settled`
   `Interface responsibility:` `session-entry interface`
   `Required behavior:` create `l3_session`, commit `l3_selection_manifest`, and persist `entry_route_context_json` plus `operator_context_json` before any descriptor load occurs.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-135`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_session|92-117`

3. `Recommended but not settled`
   `Interface responsibility:` `descriptor-expansion interface`
   `Required behavior:` expand one committed manifest into zero, one, or many descriptors, including explicit no-match, ambiguous-match, and invalid-selection outcomes rather than silent disappearance.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion|89-92`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Required descriptor fields|101-111`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Expansion outcomes|113-119`

4. `Recommended but not settled`
   `Interface responsibility:` `load-resolution interface`
   `Required behavior:` resolve each descriptor against its source plane, record one `l3_retrieval_event`, and attach zero, one, or many `l3_material_snapshot` identities with explicit outcome and reason code.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|155-184`

5. `Recommended but not settled`
   `Interface responsibility:` `snapshot-persistence interface`
   `Required behavior:` persist payload bodies into the workspace/content-addressed store and persist only stable references plus provenance in the ledger.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`

6. `Recommended but not settled`
   `Interface responsibility:` `Phase 1A audit-read interface`
   `Required behavior:` expose a machine-checkable proof surface for session, manifest, descriptor, retrieval, and snapshot state without implying that a public consumer-facing UI or package family is already frozen.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-152`

## 4. Exact persistence and storage split needed for Phase 1A

1. `Settled from source evidence`
   `Conclusion:` The write-side relational ledger should store identity, ordering, explicit outcomes, and provenance references for `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, and `l3_material_snapshot`.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`

2. `Settled from source evidence`
   `Conclusion:` The workspace/content-addressed store should hold snapshot payload bodies and nothing in Phase 1A requires it to hold typing, pass, reconciliation, or package payloads yet.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`

3. `Settled from source evidence`
   `Conclusion:` Runtime DB state is not part of the Phase 1A write-side storage split.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`

## 5. Exact feeder-plane touchpoints for Phase 1A

1. `Settled from source evidence`
   `Feeder plane:` generic quantitative dataset/version/analysis plane
   `Phase 1A touchpoint:` may supply selection identity, source-plane hints, and loaded material provenance when a session chooses that plane; it remains a read-side feeder only in Phase 1A.
   `Phase 1A non-expansion rule:` do not collapse Layer 3 onto `AnalysisRun` semantics and do not require new quantitative execution for this tranche.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|Generic dataset/version/analysis plane already exists|65-89`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`; `R|backend/app/models/models.py|Dataset; DatasetVersion; AnalysisRun|36-219`; `R|backend/app/services/analysis.py|recommend_analysis and run_analysis|87-121,541-577`

2. `Settled from source evidence`
   `Feeder plane:` APS feeder/context plane
   `Phase 1A touchpoint:` may supply selection identity, run/target provenance, APS content/chunk/linkage/retrieval references, and loaded-material provenance when a session chooses that plane; it remains a read-side feeder/context plane only in Phase 1A.
   `Phase 1A non-expansion rule:` do not collapse Layer 3 onto connector-run semantics and do not treat APS as the execution engine itself.
   `Claim strength:` primary + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/00B_LAYER3_LIVE_REPO_BASELINE_AND_INVARIANTS.md|APS connector/content/retrieval plane already exists|91-116`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|APS feeder/context plane|150-169`; `R|backend/app/models/models.py|ConnectorRun; ConnectorRunTarget|246-444`; `R|backend/app/models/models.py|ApsContentDocument; ApsContentChunk; ApsContentLinkage; ApsRetrievalChunk|522-659`

3. `Deferred / not for this tranche`
   `Conclusion:` The narrow analyst-insight kernel is not a feeder plane and should not be treated as a Phase 1A touchpoint. It is a later engine-family reuse candidate.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Shipped analyst-insight kernel|127-148`; `R|backend/app/api/market_data_integration.py|router prefix /market-pipeline/integration|1-20`; `R|backend/app/api/market_data_validation.py|router prefix /market-pipeline/validation|1-20`; `R|backend/app/api/market_insight_ai.py|router prefix /market-pipeline/insights|1-20`

## 6. Exact write-side vs read-side boundaries for Phase 1A

1. `Settled from source evidence`
   `Write-side boundary:` new Layer 3 ledger rows plus workspace payload storage only.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`

2. `Settled from source evidence`
   `Read-side boundary:` upstream feeder-plane material and provenance only; runtime DB planes remain read-only consumer surfaces and do not need to be part of the Phase 1A landing path.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`; `R|backend/app/services/review_nrc_aps_document_trace.py|implemented tab payloads and source endpoint comment|414-450`

3. `No-go for current horizon`
   `Boundary rule:` no internal HTTP self-calls to the market-pipeline or analyst-insight alias routes as the default reuse path.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`; `R|backend/app/api/market_data_integration.py|router prefix /market-pipeline/integration|1-20`; `R|backend/app/api/market_data_validation.py|router prefix /market-pipeline/validation|1-20`; `R|backend/app/api/market_insight_ai.py|router prefix /market-pipeline/insights|1-20`

4. `Recommended but not settled`
   `Boundary rule:` Phase 1A should not require a new public route family. If a callable entrypoint is needed, keep it internal or explicitly provisional rather than freezing the public Layer 3 route family early.
   `Claim strength:` primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|137-140`

## 7. Exact assumptions that are allowed for Phase 1A

1. `Settled from source evidence`
   `Allowed assumption:` one manifest item may expand into multiple descriptors, and one descriptor may yield zero, one, or many snapshots.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Why descriptor expansion is required|94-100`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Snapshot rules|151-156`

2. `Settled from source evidence`
   `Allowed assumption:` partial completion is valid if explicitly recorded; failure, empty results, and ambiguity are legitimate explicit outcomes rather than reasons to erase session history.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Frozen decisions in scope|25-30`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`

3. `Recommended but not settled`
   `Allowed assumption:` exact wrapper/module layout and exact storage-root naming may be decided implementation-locally once this prep pack is accepted, as long as the settled object contracts and boundaries are preserved.
   `Claim strength:` direct primary-planning evidence + recommendation only.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|137-140`

## 8. Exact assumptions that are not allowed for Phase 1A

1. `No-go for current horizon`
   `Disallowed assumption:` a repo-root analyst-insight page and alias-route baseline is already proven for this tranche.
   `Claim strength:` repo-root implementation evidence + same-path worktree confirmation.
   `Evidence:` `R|backend/main.py|StaticFiles mounts and review routes|47-64`; `R|backend/app/api/router.py|router includes review_nrc_aps and legacy market-pipeline routers|88-97`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`; `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`

2. `No-go for current horizon`
   `Disallowed assumption:` snapshots are already analysis units or that typing can be skipped because material has been loaded.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`; `P|layer3_primary_planningdocs/04_LAYER3_ANALYSIS_UNIT_MODALITY_AND_SET_MODEL.md|source_shape, modality, and set distinctions|27-30`

3. `No-go for current horizon`
   `Disallowed assumption:` runtime DBs may hold Layer 3 state, receive incidental writes, or substitute for the Phase 1A ledger.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`

4. `No-go for current horizon`
   `Disallowed assumption:` APS feeder/content/index planes or the narrow analyst-insight kernel already equal the full execution engine.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Shipped analyst-insight kernel|127-148`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|APS feeder/context plane|150-169`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-195`

5. `No-go for current horizon`
   `Disallowed assumption:` Phase 1A can silently widen into APS handoff, user/review-facing packages, or generalized public route redesign just because reusable downstream surfaces already exist in repo root.
   `Claim strength:` direct primary-planning evidence + repo triangulation.
   `Evidence:` `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`; `R|backend/app/api/router.py|APS evidence/context/deterministic endpoints|504-877`

## 9. What must wait until Phase 2+

1. `Deferred / not for this tranche`
   `Conclusion:` typing rules, modality assignment, analysis-unit/group/set formation, pass-state and quarantine logic, rerun logic, reconciliation, and canonical packaging must wait until Gate C and Gate D are explicitly crossed.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Frozen decisions in scope|25-30`; `P|layer3_primary_planningdocs/05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md|Quarantine rules and partial completion policy|176-200`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

2. `Deferred / not for this tranche`
   `Conclusion:` user-facing package, review-facing package, APS handoff package, and any direct APS artifact emission must wait.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Derived package families|178-207`; `P|layer3_primary_planningdocs/07_LAYER3_RECONCILIATION_PACKAGING_AND_HANDOFF.md|Recommended APS handoff posture|209-217`

3. `Deferred / not for this tranche`
   `Conclusion:` public route-family freeze, future workbench surface definition, and broader consumer admission must wait.
   `Claim strength:` direct primary-planning evidence.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open route family question|38-38`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Needs explicit user freeze or confirmation|131-135`

## 10. Concise evidence appendix

Primary planning anchors most heavily relied upon in this spec:
- `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Required descriptor fields|101-111`
- `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_session|92-117`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_selection_manifest|118-129`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_descriptor|130-154`
- `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|155-184`
- `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`
- `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

Repo-root anchors most heavily relied upon in this spec:
- `R|backend/app/models/models.py|Dataset; DatasetVersion; AnalysisRun|36-219`
- `R|backend/app/models/models.py|ConnectorRun; ConnectorRunTarget|246-444`
- `R|backend/app/models/models.py|ApsContentDocument; ApsContentChunk; ApsContentLinkage; ApsRetrievalChunk|522-659`
- `R|backend/app/services/analysis.py|recommend_analysis and run_analysis|87-121,541-577`
- `R|backend/app/services/review_nrc_aps_document_trace.py|safe runtime path resolution|169-180`
- `R|backend/app/services/review_nrc_aps_document_trace.py|implemented tab payloads and source endpoint comment|414-450`

Worktree-only divergence references retained only for boundary control:
- `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.html|confirmation-only|exists`
- `W|worktrees/mainline-lane/backend/app/review_ui/static/analyst_insight.js|confirmation-only|exists`
