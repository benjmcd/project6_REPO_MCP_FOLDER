# 05 Phase1A Proof Runbook And Stop Conditions

## Purpose and authority note

This document is the bounded proof and stop-condition runbook for a later write-enabled `Phase 1A` session. It is not a broader validation program and it does not authorize Phase 2+ work.

Applied authority order for this handoff lane:
1. primary planning
2. curated repo-root implementation-truth
3. secondary planning
4. same-path worktree confirmations
5. current REV2 implementation-prep baseline docs
6. older report and final-pack artifacts

Phase 1A retained objective:
- `Gate-B-only feeder/ledger entry`
- only `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, `l3_material_snapshot`
- no typing, orchestration, packaging, APS handoff, broader UI/API widening, or consumer widening

## 1. Preflight

1. `Preflight rule`
   Confirm that the intended patch set is a strict subset of the allowed or conditional surfaces in the Phase 1A touch matrix before any editing starts.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|full matrix`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Frozen decisions in scope|17-24`

2. `Preflight rule`
   Confirm that the intended landed objects stop at `l3_material_snapshot`. If any design note, model draft, schema, or code stub includes `l3_typing_record` onward, stop before editing.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`; `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md|artifact|sections 2-4`

3. `Preflight rule`
   Confirm that the write pass does not rely on `backend/main.py`, `backend/app/api/router.py`, `backend/app/api/review_nrc_aps.py`, `backend/app/schemas/review_nrc_aps.py`, `backend/app/review_ui/static/analyst_insight.html`, `backend/app/review_ui/static/analyst_insight.js`, or `backend/app/services/review_nrc_aps_runtime_db.py`.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|forbidden-touch rows`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 4 invariant 6`

4. `Preflight rule`
   Confirm that the runtime DB remains read-only and is not being reused as the Layer 3 ledger, write target, or incidental migration surface.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `R|backend/app/services/review_nrc_aps_document_trace.py|_resolve_safe_runtime_path|169-180`; `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|section 4`

5. `Preflight rule`
   Keep authority classes separate. The repo-root analyst-insight surfaces are live, but they remain adjacent forbidden-touch surfaces for Phase 1A; other worktrees may be used only as caution or comparison notes and not as current truth overrides.
   `Evidence:` `R|backend/main.py|analyst_insight_page and root link|75-97`; `R|backend/app/api/router.py|review_nrc_aps plus legacy and alias analyst-insight routers|93-100`; `R|backend/app/review_ui/static/analyst_insight.html|present|exists`; `R|backend/app/review_ui/static/analyst_insight.js|present|exists`; `R|backend/app/services/review_nrc_aps_runtime_db.py|read-only runtime DB session management|1-87`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|auto-out-of-scope worktrees rule`

6. `Command status`
   Exact preflight commands for Phase 1A are **not established in the provided materials.**
   `Recommended command pattern:` `git status --short`; `git diff --name-only`; `git diff --name-only -- ./backend/main.py ./backend/app/api/router.py ./backend/app/api/review_nrc_aps.py ./backend/app/schemas/review_nrc_aps.py`
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|This doc does not enumerate exact future test filenames|15-20`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|project6.ps1 remains the operator entrypoint for migrations and APS validators|154-158`

## 2. Proof obligations

1. `Proof obligation`
   Prove that a committed selection set yields a durable `l3_session` and `l3_selection_manifest`.
   `Evidence:` `P|layer3_primary_planningdocs/01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md|Checkpoint 1 - selection commit|135-135`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_session and l3_selection_manifest|required fields section`

2. `Proof obligation`
   Prove that descriptor expansion is explicit and auditable: every manifest item becomes one or more descriptors or an explicit `no-match`, `ambiguous-match`, or `invalid-selection` style outcome, and each descriptor records a resolution status.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Selection manifest to descriptor expansion|89-119`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_descriptor required status enum|58-79`

3. `Proof obligation`
   Prove that `l3_retrieval_event` and `l3_material_snapshot` record what actually loaded, what failed, and where heavy payload bodies live. Phase 1A proof is incomplete if payload lineage exists only in memory.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Persistence split|61-75`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|l3_retrieval_event and l3_material_snapshot|required fields section`; `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md|artifact|sections 3-6`

4. `Proof obligation`
   Prove that feeder-plane identity remains explicit. Plane A and Plane B inputs must stay distinguishable in descriptor and snapshot lineage.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Frozen decisions in scope|17-22`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Source plane definitions|59-84`

5. `Proof obligation`
   Prove that the runtime DB boundary was not crossed: no runtime DB writes, no runtime DB ledger reuse, no review/document-trace coupling as execution state.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|49-56`

6. `Proof obligation`
   Prove that the slice did not smuggle in Phase 2+ objects, route-family widening, or APS downstream handoff behavior.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C - typing/orchestration entry|101-105`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate D - packaging/handoff entry|107-111`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`

7. `Evidence to capture`
   Capture at minimum:
   - exact changed path list,
   - exact landed object list,
   - one machine-checkable proof surface,
   - one happy-path result,
   - one partial-feed failure result,
   - one explicit statement of unchanged forbidden surfaces.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|59-64`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|71-76`

## 3. Validation order

1. `Validation order`
   First, validate the touched-path set against the touch matrix before reading test output. A proof run does not rescue a widened patch.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|full matrix`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Over-claim guardrail|78-82`

2. `Validation order`
   Second, validate structural model and contract presence for the five Phase 1A objects only.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md|artifact|section 3`

3. `Validation order`
   Third, validate descriptor expansion and explicit resolution outcomes, including one partial-feed outcome.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Expansion outcomes|103-131`; `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Hard-stop vs partial-feed failures|159-167`

4. `Validation order`
   Fourth, validate retrieval and snapshot persistence, including payload refs, payload hashes, and source-plane lineage.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Required reference semantics|125-132`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Replay model|133-145`

5. `Validation order`
   Fifth, run no-go regression checks: no forbidden surface changed, no runtime DB write path introduced, no Phase 2+ object landed.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Hard boundaries and runtime DB rule|56-83`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Failure criteria for implementation entry|89-95`

6. `Validation order`
   Sixth, capture the final bounded status statement: what is now live, what remains deferred, and what was intentionally not touched.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Over-claim guardrail|78-82`; `A|next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md|artifact|section 9`

7. `Command status`
   Exact Phase 1A validation commands are **not established in the provided materials.**
   `Recommended command pattern:`
   - structural diff: `git diff --name-only`
   - targeted proof: `python -B -m pytest ./backend/tests/<phase1a-targeted-proof-file>.py -p no:cacheprovider`
   - forbidden-surface regression check: `git diff --name-only -- ./backend/main.py ./backend/app/api ./backend/app/review_ui/static`
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|This doc does not enumerate exact future test filenames|15-20`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|validate-* actions remain validate-only and project6.ps1 is the operator entrypoint|154-158`

## 4. Stop conditions

1. `Stop immediately`
   If any forbidden-touch file from the touch matrix appears necessary.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|forbidden-touch rows`

2. `Stop immediately`
   If the patch plan includes `l3_typing_record`, `l3_analysis_unit`, `l3_analysis_set`, `l3_analysis_plan`, `l3_pass_run`, `l3_reconciliation_record`, or `l3_output_package`.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate C and Gate D|101-111`

3. `Stop immediately`
   If implementation requires `backend/main.py`, `backend/app/api/router.py`, `backend/app/api/review_nrc_aps.py`, `backend/app/schemas/review_nrc_aps.py`, analyst-insight static assets, or `backend/app/services/review_nrc_aps_runtime_db.py`.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|rows for main, router, review_nrc_aps, review_nrc_aps_document_trace, review_nrc_aps_runtime_db, analyst_insight assets`

4. `Stop immediately`
   If the later pass reaches for other-worktree files as if they were current repo-root authority. This is a source-class violation.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|auto-out-of-scope worktrees rule`

5. `Stop immediately`
   If runtime DB writes, runtime DB migrations, or runtime DB ledger reuse appear necessary.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|49-56`

6. `Stop immediately`
   If the session cannot explicitly explain what loaded, what failed, and why. Silent descriptor disappearance or in-memory-only lineage is a fail-closed condition.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Resolution outcomes|121-131`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Failure criteria for implementation entry|89-95`

7. `Stop immediately`
   If the write pass cannot produce a machine-checkable proof surface and only has manual confidence.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|59-64`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Over-claim guardrail|78-82`

## 5. Acceptance criteria

1. `Acceptance criterion`
   Changed paths are limited to `yes` or explicitly escalated `conditional` surfaces from the touch matrix.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|full matrix`

2. `Acceptance criterion`
   The landed object set contains exactly `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, and `l3_material_snapshot`, with no Phase 2+ objects.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`; `A|next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md|artifact|sections 2-4`

3. `Acceptance criterion`
   One happy-path proof shows committed selection to durable session, manifest, descriptors, retrieval events, and material snapshots.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Strong first-pass validation recommendation|71-76`

4. `Acceptance criterion`
   One partial-feed proof shows explicit non-success outcomes without silent loss, while preserving the ledger.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Hard-stop vs partial-feed failures|159-167`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Partial implementation is acceptable only when boundaries are explicit and tested|13-14`

5. `Acceptance criterion`
   Evidence shows that runtime DB boundaries, consumer boundaries, and route-family boundaries were preserved.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Hard boundaries|56-83`; `P|layer3_primary_planningdocs/10_LAYER3_CONSUMER_INTEGRATION_MAP.md|Not first-pass by default|74-76`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Route-family posture|92-102`

6. `Acceptance criterion`
   The completion statement is scoped to Phase 1A only and explicitly says what remains deferred.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Over-claim guardrail|78-82`; `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|sections 5-9`

## 6. Escalation triggers

1. `Escalate back to planning`
   If the exact new Phase 1A owner-module or proof-file path cannot be chosen without creating a new truth surface not established in the provided materials.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|conditional new-module and new-test rows`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|53-56`

2. `Escalate back to planning`
   If the later pass believes a migration file, new route family, or new public API family is required.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Important note|96-102`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|What is still not fully contextualized here|196-201`

3. `Escalate back to planning`
   If the later pass concludes that the current five-object Gate-B slice cannot satisfy the required proof obligations without Phase 2+ objects.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B and Gate C|95-105`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Reopen triggers|58-63`

4. `Escalate back to planning`
   If the later pass needs to interpret other-worktree files as current repo-root truth.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|auto-out-of-scope worktrees rule`
