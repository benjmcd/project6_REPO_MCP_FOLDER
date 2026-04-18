# 09 Phase1A Write Enabled Codex Prompt REV2

## Correction Note

This revision regenerates the write-enabled prompt from the allowed source set only.

Corrected from the prior prompt:
- source hygiene is now explicit and clean,
- the prompt constraints, defaults, and stop conditions were revalidated from allowed sources only.

Retained unchanged:
- the frozen Phase 1A tranche,
- the exact owner/touch/no-touch posture,
- the exact proof obligations,
- the exact stop conditions,
- the exact recommended run order.

Material effect on the later write-enabled session:
- no material change; this remains the prompt to use for the next write-enabled pass.

Evidence basis: `A|next_milestone_plans/Layer3_execution_freeze/09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT.md|artifact|correction target`; `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|sections 1-4`

Use the following prompt for the later write-enabled Codex session. It is already constrained to the frozen `Phase 1A` boundary and the cleanly revalidated implementation-local defaults.

## Ready-to-use prompt

You are performing a **write-enabled, bounded Phase 1A implementation pass**.

This is **not** a broader Layer 3 implementation.
This is **not** a route/UI/API widening pass.
This is **not** a typing/orchestration/packaging/handoff pass.

You must stay inside this frozen tranche:
- `Phase 1A = Gate-B-only feeder/ledger entry`
- land only:
  - `l3_session`
  - `l3_selection_manifest`
  - `l3_descriptor`
  - `l3_retrieval_event`
  - `l3_material_snapshot`
- no typing, orchestration, packaging, APS handoff, broader UI/API widening, or consumer widening
- runtime DB remains read-only and out of write-side scope
- the two feeder planes remain distinct
- the narrow analyst-insight kernel remains bounded and is not the full Layer 3 system

`Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|purpose note and sections 2-4`

### Exact files you may touch

1. `backend/app/models/models.py`
   Purpose: append the new bounded Layer 3 Phase 1A ORM block only.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|models owner row`; `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 1 item 1`

2. `backend/app/services/layer3_session_entry.py`
   Purpose: one new internal owner module for selection commit, descriptor expansion, retrieval recording, and snapshot persistence.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 2 item 1`

3. `backend/alembic/versions/<revision>_layer3_session_entry.py`
   Purpose: one manual migration file for the new durable write-side tables.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 2 items 3-4`

4. `backend/tests/test_layer3_session_entry.py`
   Purpose: one targeted backend proof module that directly imports the new service module.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 2 items 5-6`

### Exact files you must not touch

- `backend/main.py`
- `backend/app/api/router.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/schemas/api.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/review_ui/static/**`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/analysis.py`
- `backend/app/api/market_data_integration.py`
- `backend/app/api/market_data_validation.py`
- `backend/app/api/market_insight_ai.py`
- `backend/app/services/market_data_integration.py`
- `backend/app/services/market_data_validation.py`
- `backend/app/services/market_insight_ai.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/nrc_aps_context_dossier.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
- `backend/app/services/nrc_aps_deterministic_challenge_review_packet.py`

`Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|forbidden-touch rows and out-of-scope path families`; `A|next_milestone_plans/Layer3_execution_freeze/08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md|artifact|forbidden surfaces item`

### Implementation defaults you must follow

1. Use exactly one internal service owner module. Do not split Phase 1A across multiple new service modules unless you stop and escalate first.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 2 item 1 and section 4 item 2`

2. Do not add a new schema block, route, page, browser flow, temporary script, or public API family for proof.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 2 items 2 and 6`; `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Route-family posture|146-155`

3. Use a manual Alembic migration. Do not default to autogenerate for this slice.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 2 items 3-4`

4. Keep Plane A and Plane B provenance explicit in descriptors and snapshots.
   `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Frozen decisions in scope and source plane definitions|25-88`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 4`

5. Do not write to runtime DB state, migrate runtime DB state, or treat runtime DB state as the Layer 3 ledger.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|sections 4 and 7`

6. Do not use internal HTTP self-calls as the default proof or execution path.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Recommended invocation posture|141-143`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-196`

### Recommended run order

These are `Recommended implementation-local choice.` commands, not source-established commands.

1. `git status --short`
2. `git diff --name-only -- ./backend/main.py ./backend/app/api/router.py ./backend/app/api/review_nrc_aps.py ./backend/app/schemas/api.py ./backend/app/schemas/review_nrc_aps.py ./backend/app/review_ui/static ./backend/app/services/review_nrc_aps_graph.py ./backend/app/services/review_nrc_aps_document_trace.py ./backend/app/services/review_nrc_aps_runtime_db.py ./backend/app/services/analysis.py ./backend/app/api/market_data_integration.py ./backend/app/api/market_data_validation.py ./backend/app/api/market_insight_ai.py ./backend/app/services/market_data_integration.py ./backend/app/services/market_data_validation.py ./backend/app/services/market_insight_ai.py ./backend/app/services/nrc_aps_evidence_bundle_contract.py ./backend/app/services/nrc_aps_evidence_bundle.py ./backend/app/services/nrc_aps_context_packet.py ./backend/app/services/nrc_aps_context_dossier.py ./backend/app/services/nrc_aps_deterministic_insight_artifact.py ./backend/app/services/nrc_aps_deterministic_challenge_artifact.py ./backend/app/services/nrc_aps_deterministic_challenge_review_packet.py`
3. implement only the allowed surfaces listed above
4. `python -m alembic -c ./backend/alembic.ini upgrade head`
5. `python -B -m pytest ./backend/tests/test_layer3_session_entry.py -p no:cacheprovider`
6. repeat step 2
7. `git diff --name-only`

`Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 3`

### Proof obligations you must satisfy

1. Produce one machine-checkable proof surface.
2. Prove one happy path from committed selection to durable session, manifest, descriptors, retrieval events, and material snapshots.
3. Prove one partial-feed path with explicit non-success outcomes and no silent descriptor loss.
4. Show payload refs, payload hashes, source-plane lineage, and what loaded versus what failed.
5. Show that forbidden surfaces remained unchanged.

`Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice and strong first-pass validation recommendation|129-150`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 6`

### Stop immediately if any of the following becomes true

1. You need any forbidden-touch file.
2. You need `l3_typing_record` or any later object.
3. You need `backend/app/schemas/api.py`, a public route, a page route, or a browser flow.
4. You need runtime DB writes, runtime DB migrations, or runtime DB ledger reuse.
5. You need to treat worktree-only analyst-insight surfaces as repo-root truth.
6. You cannot keep the implementation inside one new service owner module plus one migration plus one proof file.
7. You cannot explain what loaded, what failed, and why.
8. You cannot produce a machine-checkable proof surface.

`Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|stop conditions 1-7`; `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md|artifact|section 4`

### Output expectations for your final response

Your final response must include:
- the exact changed path list,
- whether the landed objects are exactly the five Phase 1A objects,
- the migration file path,
- the proof command run and result,
- the no-touch regression-check result,
- any stop/escalation trigger encountered,
- one plain statement that typing, orchestration, packaging, APS handoff, route-family work, and consumer widening remain deferred and are not now live.

`Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 8`
