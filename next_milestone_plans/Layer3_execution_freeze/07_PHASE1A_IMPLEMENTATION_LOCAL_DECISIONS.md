# 07 Phase1A Implementation Local Decisions

## Purpose and authority note

This document freezes the remaining implementation-local choices for a later write-enabled `Phase 1A` session. It does not reopen tranche scope. It settles the lowest-friction default for owner placement, migration posture, proof placement, internal entrypoint posture, and run order.

Applied authority order:
1. primary planning
2. curated repo-root implementation-truth
3. secondary planning
4. same-path worktree confirmations
5. current implementation-prep baseline docs
6. current/final artifact docs
7. historical report artifacts

Frozen tranche retained:
- `Phase 1A = Gate-B-only feeder/ledger entry`
- object set limited to `l3_session`, `l3_selection_manifest`, `l3_descriptor`, `l3_retrieval_event`, `l3_material_snapshot`
- no typing, orchestration, packaging, APS handoff, broader UI/API widening, or consumer widening
- runtime DB remains read-only and out of write-side scope
- the two feeder planes remain distinct
- the narrow analyst-insight kernel remains bounded and is not the full Layer 3 system

Evidence basis: `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|purpose note and sections 2-8`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Gate B - feeding implementation entry|95-100`

## 1. Settled from source evidence

1. `Settled from source evidence`
   `Decision:` `backend/app/models/models.py` is the repo-root owner surface for new durable write-side ORM identity.
   `Why settled:` The primary planning pack requires a real durable ledger, and the live repo status doc states that DB/model changes live in `backend/app/models/models.py`.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Design thesis and canonical write order|45-89`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Schema/migration authority|142-145`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|row for backend/app/models/models.py`

2. `Settled from source evidence`
   `Decision:` Route, page, and shared-router surfaces remain out of Phase 1A. The later write pass must not use `backend/main.py`, `backend/app/api/router.py`, or `backend/app/api/review_nrc_aps.py` as the implementation entrypoint.
   `Why settled:` The tranche is internal and service-first, and broader route-family work remains explicitly deferred.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Route-family posture and important note|146-155`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Explicit out-of-scope items for the first slice|123-129`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|rows for backend/main.py, backend/app/api/router.py, backend/app/api/review_nrc_aps.py`

3. `Settled from source evidence`
   `Decision:` Runtime DB state remains read-only consumption state and cannot be used as the Layer 3 write target, migration target, or proof harness target.
   `Why settled:` This is a hard runtime boundary, not an implementation-local preference.
   `Evidence:` `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-196`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|preflight rule 4 and stop condition 5`

4. `Settled from source evidence`
   `Decision:` Internal HTTP self-calls are not the default internal entrypoint posture. If the tranche reuses adjacent logic, it must do so through callable service logic or wrappers, not through route calls.
   `Why settled:` The primary planning pack states this explicitly for analyst-insight reuse, and Phase 1A already excludes public route work.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Recommended invocation posture|141-143`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Reuse anti-patterns|189-196`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 4`

5. `Settled from source evidence`
   `Decision:` Some write-side schema migration surface is required for new durable Layer 3 tables, and repo-local migration authority lives under `backend/alembic/versions`.
   `Why settled:` New Phase 1A ledger tables cannot become real durable DB surfaces by editing `models.py` alone, and the repo’s current authority split is explicit.
   `Evidence:` `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|A durable session ledger is required|45-63`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Schema/migration authority|142-145`; `R|backend/main.py|_run_migrations and _initialize_database|19-38`

6. `Settled from source evidence`
   `Decision:` Exact future test filenames are not established by source, but repo-root status docs show a live backend-focused proof pattern under `backend/tests/`.
   `Why settled:` The planning pack leaves filenames open, while the current repo status docs show the existing narrow proof placement convention needed for a bounded backend slice.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Explicit non-goals|24-27`; `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current proof basis|62-68`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Current proof freshness and remaining gaps|36-37`

## 2. Recommended implementation-local choice

1. `Recommended implementation-local choice.`
   `Owner module placement:` create exactly one new internal owner module at `backend/app/services/layer3_session_entry.py`.
   `Why this is the recommended default:` It keeps Phase 1A in the service layer, avoids naming drift into a phase-numbered permanent file, avoids polluting adjacent `analysis.py` or `market_*` families, and is narrow enough to own only selection commit, descriptor expansion, retrieval recording, and material-snapshot persistence.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Can be decided implementation-locally once the pack is accepted|137-141`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Recommended invocation posture|141-143`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|conditional new service module row`

2. `Recommended implementation-local choice.`
   `Do not add a new Phase 1A schema block in backend/app/schemas/api.py.`
   `Why this is the recommended default:` The tranche has no public route family, no browser contract, and no consumer widening. A direct internal service call plus backend proof file is the lowest-blast-radius proof path.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Route-family posture and important note|146-155`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|conditional api.py row`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 5`

3. `Recommended implementation-local choice.`
   `Migration posture:` require one manual Alembic migration file at `backend/alembic/versions/<revision>_layer3_session_entry.py`.
   `Why this is the recommended default:` Phase 1A adds durable DB tables, the repo already treats `backend/alembic/versions` as the migration authority, and a manual migration is lower-blast-radius than schema autogeneration in a very large model set.
   `Evidence:` `R|docs/nrc_adams/nrc_aps_status_handoff.md|Schema/migration authority|142-145`; `R|backend/main.py|_run_migrations and _initialize_database|19-38`; `P|layer3_primary_planningdocs/03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md|Canonical write order|76-89`

4. `Recommended implementation-local choice.`
   `Migration-generation rule:` do not rely on autogenerate as the default Phase 1A posture.
   `Why this is the recommended default:` The materials establish migration authority but do not establish any safe autogenerate workflow for this slice. A manual migration keeps the delta bounded to the five new tables and avoids unrelated schema churn.
   `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Over-claim and proof discipline|120-150`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Schema/migration authority|142-145`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|escalation trigger 2`

5. `Recommended implementation-local choice.`
   `Proof/test placement:` create exactly one targeted proof module at `backend/tests/test_layer3_session_entry.py`.
   `Why this is the recommended default:` It matches the existing repo proof convention shown in the live status docs, keeps the slice backend-only, and allows both the happy-path and partial-feed proof obligations to live in one narrow file.
   `Evidence:` `R|docs/analyst_insight/analyst_insight_status_handoff.md|Current proof basis|62-68`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Current explicit limits and fresh proof basis|157-173`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`

6. `Recommended implementation-local choice.`
   `Internal entrypoint posture:` use a test-only harness that imports `app.services.layer3_session_entry` directly. Do not add a temporary script and do not expose a temporary route.
   `Why this is the recommended default:` It is the smallest proof surface, keeps the tranche internal, avoids route-family drift, and still satisfies the requirement for one machine-checkable proof surface.
   `Evidence:` `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Recommended invocation posture|141-143`; `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 6`

## 3. Exact command-sequence recommendation

All commands below are `Recommended implementation-local choice.` They are not presented as source-established commands.

| step | recommended command or action | why this order | evidence basis |
| --- | --- | --- | --- |
| `1. preflight path check` | `git status --short` | Confirms the write-enabled session starts by seeing the exact local delta. | `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|preflight command status` |
| `2. preflight no-touch check` | `git diff --name-only -- ./backend/main.py ./backend/app/api/router.py ./backend/app/api/review_nrc_aps.py ./backend/app/schemas/review_nrc_aps.py ./backend/app/review_ui/static ./backend/app/services/review_nrc_aps_document_trace.py ./backend/app/services/review_nrc_aps_graph.py ./backend/app/services/analysis.py ./backend/app/api/market_data_integration.py ./backend/app/api/market_data_validation.py ./backend/app/api/market_insight_ai.py ./backend/app/services/market_data_integration.py ./backend/app/services/market_data_validation.py ./backend/app/services/market_insight_ai.py` | Confirms the forbidden surfaces remain untouched before any implementation begins. | `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|forbidden-touch rows`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|preflight rules 1-5` |
| `3. implementation surfaces` | Edit only `./backend/app/models/models.py`; add `./backend/app/services/layer3_session_entry.py`; add `./backend/alembic/versions/<revision>_layer3_session_entry.py`; add `./backend/tests/test_layer3_session_entry.py` | Keeps the patch set inside the frozen owner/touch set and avoids placeholder ambiguity. | `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|models owner row and conditional service/proof rows`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|sections 5 and 8` |
| `4. migration apply` | `python -m alembic -c ./backend/alembic.ini upgrade head` | Applies the single bounded manual migration through the repo’s established write-side migration path. | `R|backend/main.py|_run_migrations and _initialize_database|19-38`; `R|docs/nrc_adams/nrc_aps_status_handoff.md|Schema/migration authority|142-145` |
| `5. targeted proof` | `python -B -m pytest ./backend/tests/test_layer3_session_entry.py -p no:cacheprovider` | Produces the one narrow machine-checkable proof surface without starting the broader app or widening route/UI scope. | `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|validation command status and acceptance criteria` |
| `6. post-proof no-touch regression` | Repeat the step-2 `git diff --name-only -- ...` command | Confirms no forbidden-touch drift was introduced during implementation or proof. | `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|validation order 5 and acceptance criterion 5` |
| `7. final status capture` | `git diff --name-only` | Supplies the exact changed-path list for closeout and proof output. | `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 8` |

## 4. Still unresolved or escalate

1. `Still unresolved / escalate.`
   If the later write pass concludes that `backend/app/schemas/api.py` is required after all, stop and escalate. That would mean the recommended internal service-plus-test posture was insufficient.
   `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|conditional api.py row`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|escalation triggers 1-2`

2. `Still unresolved / escalate.`
   If the later write pass concludes that one owner module is insufficient and that Phase 1A needs multiple new service modules, stop and escalate before splitting the surface. That increases patch sprawl and creates new naming truth.
   `Evidence:` `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Reopen triggers|148-153`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|stop condition 5`

3. `Still unresolved / escalate.`
   If the later write pass cannot implement the five-object slice with a manual migration and instead believes it needs a broader migration strategy decision, stop and escalate rather than improvising autogenerate or startup-side schema creation as the tranche default.
   `Evidence:` `R|backend/main.py|DB_INIT_MODE create_all versus migrate path|31-38`; `P|layer3_primary_planningdocs/12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md|Reopen triggers|148-153`

4. `Still unresolved / escalate.`
   If the later write pass believes a public route, a temporary script, or app startup is required to prove the slice, stop and escalate. That would reopen route/UI scope that the tranche explicitly excludes.
   `Evidence:` `P|layer3_primary_planningdocs/08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md|Route-family posture|146-155`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|sections 3, 5, and 7`
