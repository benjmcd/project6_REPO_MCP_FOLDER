# 06 Phase1A Codewriting Handoff

## Purpose and authority note

This document is the direct execution contract for a later write-enabled Codex session. It does not reopen architecture, tranche scope, or route-family design. It converts the accepted `Phase 1A` baseline into an implementation fence: what to land, what not to land, what must stay unchanged, and what must block the write pass.

Applied authority order for this handoff lane:
1. primary planning
2. curated repo-root implementation-truth
3. secondary planning
4. same-path worktree confirmations
5. current REV2 implementation-prep baseline docs
6. older report and final-pack artifacts

Frozen scope retained:
- `Phase 1A = Gate-B-only feeder/ledger entry`
- object set limited to `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, `l3_material_snapshot`
- no typing, orchestration, packaging, APS handoff, broader UI/API widening, or consumer widening
- runtime DB remains read-only and out of write-side scope
- the two feeder planes remain distinct
- the narrow analyst-insight kernel remains bounded and is not the full Layer 3 system

Evidence basis: `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Frozen decisions in scope|26-32`; `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|sections 4-8`

## 1. Tranche objective

1. Land only the durable internal feeder/ledger entry from committed selection through descriptor expansion, retrieval recording, and session-scoped material snapshots. Do not present this pass as consumer-complete Layer 3 behavior.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Purpose|3-8`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Validation domains by function - Feeding / Connecting|64-70`

2. Keep the slice additive and bounded. The write pass is allowed to establish durable identity for the first five objects only; it is not allowed to redesign the repo around them.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Frozen decisions in scope|26-32`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Phase 1 - session entry and feeding model|54-60`

## 2. Exact objects to land

| object | exact landing requirement | evidence basis |
| --- | --- | --- |
| `l3_session` | Must exist as the durable session root for one Layer 3 analytical session, with session state sufficient to record entry, progress, and bounded summary context. | `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_session|required fields and status enum|91-117`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100` |
| `l3_selection_manifest` | Must record the committed selection set, source-plane hints, stable selection hash, and commit reason. It is the durable record of what the operator asked for. | `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-143`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_selection_manifest|required fields|118-129` |
| `l3_descriptor` | Must record plane-specific descriptor expansion with explicit `source_plane`, `descriptor_type`, selector payload, selection basis, expansion reason, hash, and resolution status. | `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion|89-119`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_descriptor|required fields and status enum|130-153` |
| `l3_retrieval_event` | Must record each resolution/load event, including outcome, reason code, linked snapshot ids, event payload, and occurrence time. | `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event|required fields|155-167`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Hard-stop vs partial-feed failures|202-213` |
| `l3_material_snapshot` | Must record each session-scoped loaded material snapshot with `payload_ref`, `payload_hash`, source-plane identity, provenance, co-retrieval group, and load summary. | `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_material_snapshot|required fields|168-184`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Workspace-store posture|96-121` |

## 3. Exact objects not to land

1. Do not land `l3_typing_record`, `l3_analysis_unit`, `l3_analysis_group`, `l3_analysis_set`, `l3_analysis_plan`, `l3_pass_run`, `l3_reconciliation_record`, or `l3_output_package`.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`

2. Do not land any APS downstream handoff object, evidence-bundle widening, context-packet widening, deterministic artifact widening, or any other consumer-facing APS package projection.
   `Evidence:` `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-78`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Closed layers|103-123`

3. Do not land a new public route family, a new review page, a new analyst-insight alias surface, or any consumer-visible browser flow as part of this pass.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Boundary posture|44-52`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Route-family posture|146-156`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|rows for backend/main.py, backend/app/api/router.py, analyst_insight assets`

## 4. Exact invariants that must not change

1. Plane A and Plane B must remain explicit and distinct. Descriptor and snapshot lineage must preserve original source-plane identity.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Frozen decisions in scope|25-30`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Source plane definitions|59-88`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Guardrails for multi-plane sessions|196-200`

2. Runtime DB state must remain read-only consumption state. No Layer 3 writes, migrations, or ledger reuse may target the runtime DB plane.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_document_trace.py|_resolve_safe_runtime_path|169-180`

3. The current analyst-insight kernel remains an adjacent reusable family, not the whole Layer 3 system. The write pass must not self-call its HTTP routes internally or rename it into Layer 3 by implication.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Frozen decisions in scope|26-33`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Shipped analyst-insight kernel|127-148`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Purpose and truth model|3-15`

4. Route-family naming remains unfrozen for the broader workbench. `Phase 1A` must not force route, page, or shared-router decisions early.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Open questions|37-40`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Important note|154-156`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Open questions|38-41`

5. Existing adjacent repo surfaces remain constraints, not targets. Existing dataset/version, analysis-run, connector-run, APS content, review/document-trace, market-data, and downstream APS artifact semantics must remain intact.
   `Evidence:` `R|backend/app/models/models.py|class Dataset; class DatasetVersion; class AnalysisRun; class AnalysisArtifact; class ConnectorRun; class ConnectorRunTarget; class ApsContentDocument; class ApsContentChunk; class ApsContentLinkage; class DatasetSourceProvenance|36-726`; `R|backend/app/api/review_nrc_aps.py|review/document trace routes|40-220`; `R|backend/app/schemas/review_nrc_aps.py|review/document-trace contracts|8-220`; `R|backend/app/services/analysis.py|artifact persistence helpers; recommend_analysis; run_analysis|48-87`; `R|backend/app/services/analysis.py|run_analysis|541-541`

6. Other worktree files remain caution only. For analyst-insight specifically, repo-root already contains the current page, router, asset, and runtime-helper surfaces, but their presence still does not authorize touching them in Phase 1A.
   `Evidence:` `R|backend/main.py|analyst_insight_page and root link|75-97`; `R|backend/app/api/router.py|review_nrc_aps plus legacy and alias analyst-insight routers|93-100`; `R|backend/app/review_ui/static/analyst_insight.html|present|exists`; `R|backend/app/review_ui/static/analyst_insight.js|present|exists`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|auto-out-of-scope worktrees rule`

## 5. Exact repo surfaces that constrain implementation

1. `Allowed owner surface`
   `backend/app/models/models.py` may be touched only by appending a new bounded Layer 3 model block for the five Phase 1A objects. Existing adjacent classes in the same file are read-only constraints.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|rows 1-2`; `R|backend/app/models/models.py|class Dataset; class DatasetVersion; class AnalysisRun; class AnalysisArtifact; class ConnectorRun; class ConnectorRunTarget; class ApsContentDocument; class ApsContentChunk; class ApsContentLinkage|36-590`

2. `Conditional owner surfaces`
   `backend/app/services/<new phase1a-specific layer3 feed-or-ledger module path>`, `backend/app/schemas/api.py` `(new bounded Phase 1A block only if explicitly required)`, and `backend/tests/<new Phase 1A proof file path>` may be created or touched only if the write pass can justify them without widening scope. Their exact paths are not established in the provided materials.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|conditional rows for new service module, bounded schema block, and proof file`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|137-141`

3. `Shared-router and page shell surfaces`
   `backend/main.py`, `backend/app/api/router.py`, and `backend/app/api/review_nrc_aps.py` constrain the pass by showing the current repo-root route boundary. They must not be touched in Phase 1A.
   `Evidence:` `R|backend/main.py|app include_router; review page routes; root page|43-84`; `R|backend/app/api/router.py|api_router include_router review_nrc_aps and market_data routers|93-97`; `R|backend/app/api/review_nrc_aps.py|review/document trace route family|40-220`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|rows for main/router/review_nrc_aps`

4. `Read-only consumer and runtime-boundary surfaces`
   `backend/app/schemas/review_nrc_aps.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_document_trace.py`, and `backend/app/services/review_nrc_aps_runtime_db.py` constrain the pass by defining adjacent review/runtime behavior. They must not be touched.
   `Evidence:` `R|backend/app/schemas/review_nrc_aps.py|review/document-trace contracts|8-220`; `R|backend/app/services/review_nrc_aps_document_trace.py|compose_document_selector and _resolve_safe_runtime_path|82-180`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|rows for review/document-trace surfaces`

5. `Read-only adjacent engine families`
   `backend/app/api/market_data_integration.py`, `backend/app/api/market_data_validation.py`, `backend/app/api/market_insight_ai.py`, `backend/app/services/market_data_integration.py`, `backend/app/services/market_data_validation.py`, `backend/app/services/market_insight_ai.py`, and `backend/app/services/analysis.py` constrain semantics but must not be touched in Phase 1A.
   `Evidence:` `R|backend/app/api/market_data_integration.py|router prefix /market-pipeline/integration|10-36`; `R|backend/app/api/market_data_validation.py|router prefix /market-pipeline/validation|10-28`; `R|backend/app/api/market_insight_ai.py|router prefix /market-pipeline/insights|9-20`; `R|backend/app/services/market_data_integration.py|def build_integrated_dataset|40-86`; `R|backend/app/services/market_data_validation.py|def validate_market_rows|215-220`; `R|backend/app/services/market_insight_ai.py|def process_market_insights|143-174`; `R|backend/app/services/analysis.py|def recommend_analysis; def run_analysis|87-87`; `R|backend/app/services/analysis.py|def run_analysis|541-541`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|market_data and analysis rows`

6. `Read-only APS downstream surfaces`
   `backend/app/services/nrc_aps_evidence_bundle_contract.py`, `backend/app/services/nrc_aps_evidence_bundle.py`, `backend/app/services/nrc_aps_context_packet.py`, `backend/app/services/nrc_aps_context_dossier.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, and `backend/app/services/nrc_aps_deterministic_challenge_review_packet.py` remain frozen downstream constraints.
   `Evidence:` `R|docs/nrc_adams/nrc_aps_status_handoff.md|Closed layers|103-123`; `R|backend/app/services/nrc_aps_evidence_bundle_contract.py|APS_EVIDENCE_BUNDLE_SCHEMA_ID and runtime failure codes|14-100`; `R|backend/app/services/nrc_aps_evidence_bundle.py|EvidenceBundleError and persisted bundle artifact path/loading logic|19-131`; `R|backend/app/services/nrc_aps_context_packet.py|ContextPacketError and persisted context-packet contract checks|19-226`; `R|backend/app/services/nrc_aps_context_dossier.py|ContextDossierError and persisted dossier contract checks|17-322`; `R|backend/app/services/nrc_aps_deterministic_insight_artifact.py|DeterministicInsightArtifactError and ruleset identity checks|18-374`; `R|backend/app/services/nrc_aps_deterministic_challenge_artifact.py|DeterministicChallengeArtifactError and ruleset identity checks|18-252`; `R|backend/app/services/nrc_aps_deterministic_challenge_review_packet.py|DeterministicChallengeReviewPacketError and projection identity checks|18-215`

7. `Read-only live status docs`
   `docs/nrc_adams/nrc_aps_status_handoff.md` and `docs/analyst_insight/analyst_insight_status_handoff.md` constrain current repo posture and no-go ceilings. They are not implementation targets for the write pass.
   `Evidence:` `R|docs/nrc_adams/nrc_aps_status_handoff.md|Purpose and truth model|3-16`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Recommended next continuation|178-184`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Purpose and truth model|3-15`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Intentional deferred tech debt|70-80`

## 6. Exact proofs that must exist afterward

1. One machine-checkable proof surface must exist for the new five-object slice.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|sections 2-5`

2. One happy-path proof must show committed selection to durable `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, and `l3_material_snapshot`.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-150`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|acceptance criteria 2-3`

3. One partial-feed proof must show explicit non-success outcomes without silent loss of descriptor or snapshot lineage.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Hard-stop vs partial-feed failures|202-213`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|acceptance criterion 4`

4. Proof output must explicitly show payload refs, payload hashes, source-plane lineage, and what loaded versus what failed.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Material snapshot model|133-156`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|required fields|155-184`

5. The closeout evidence must include the exact changed path list and an explicit statement of unchanged forbidden surfaces.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|evidence to capture`

## 7. Exact conditions that should block implementation

1. Stop if any forbidden-touch file from the touch matrix appears necessary.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|forbidden-touch rows`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|stop condition 1`

2. Stop if any Phase 2+ object, APS downstream handoff object, public route family, review-facing contract, or analyst-insight UI/API widening becomes part of the plan.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

3. Stop if runtime DB writes, runtime DB migrations, runtime DB ledger reuse, or dependence on `backend/app/services/review_nrc_aps_runtime_db.py` becomes necessary.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|120-127`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`

4. Stop if the write pass needs to treat other-worktree files as repo-root truth.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|auto-out-of-scope worktrees rule`

5. Stop if the write pass cannot choose its new service-module path or proof-file path without inventing a broader new truth surface.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|137-141`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|conditional new-module and new-proof rows`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|escalation triggers 1-2`

6. Stop if the pass cannot explain what loaded, what failed, and why, or if it cannot produce a machine-checkable proof surface.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|120-127`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Failure criteria for implementation entry|178-185`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|stop conditions 6-7`

## 8. Exact definition of success for the next pass

1. The patch set stays inside the allowed or explicitly escalated conditional owner surfaces, with no forbidden-touch drift.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|full matrix`

2. The landed code creates only the five Phase 1A feeder/ledger objects and no Phase 2+ or consumer-facing objects.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|acceptance criterion 2`

3. Proof exists for one happy path and one partial-feed path, with durable lineage, explicit outcomes, and unchanged runtime/consumer/route boundaries.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|146-150`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|acceptance criteria 3-5`

4. The implementation closeout states, in plain terms, that typing, orchestration, packaging, APS handoff, route-family work, and consumer widening remain deferred and are not now live.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Frozen decisions in scope|18-23`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|sections 5-8`

If any item above cannot be satisfied without widening scope, the correct outcome is to stop and escalate back to planning rather than improvising a larger implementation program.

Evidence basis: `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Reopen triggers|148-153`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|section 6`
