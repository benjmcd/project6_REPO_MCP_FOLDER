# 08 Phase1A Precode Acceptance Checklist

## Historical Note

This checklist is retained for historical continuity and is superseded by `08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`.
Use the REV2 checklist as the current control doc; older analyst-insight worktree-only wording below is not the current live-repo posture.

## Purpose and use

Use this checklist before a write-enabled session edits any code. Every item must be true before editing begins. If any item cannot be checked cleanly, stop and escalate instead of widening scope.

Evidence basis: `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|full doc`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|sections 1-6`

## Checklist

- [ ] I acknowledge the frozen tranche: `Phase 1A = Gate-B-only feeder/ledger entry`, five objects only, no typing/orchestration/packaging/APS handoff/UI/API widening/consumer widening.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|purpose note and sections 2-3`

- [ ] I acknowledge that the two feeder planes must remain distinct and runtime DB remains read-only and out of write-side scope.  
  `Evidence:` `P|layer3_primary_planningdocs/02_LAYER3_SOURCE_PLANES_AND_FEEDING_MODEL.md|Frozen decisions in scope|25-30`; `P|layer3_primary_planningdocs/09_LAYER3_PERSISTENCE_RUNTIME_AND_SECURITY_BOUNDARIES.md|Runtime DB rule|76-83`

- [ ] I acknowledge the exact repo surfaces already accepted as the baseline pack: `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`, `02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`, `03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`, `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`, `05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`, `06_PHASE1A_CODEWRITING_HANDOFF.md`, and `07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md`.  
  `Evidence:` `A|next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md|artifact|full doc`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|full doc`; `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|full doc`

- [ ] I will treat `backend/app/models/models.py` as the only already-settled direct owner surface.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|settled item 1`; `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|models owner row`

- [ ] I will use exactly one new internal owner module path: `backend/app/services/layer3_session_entry.py`.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|recommended choice 1`

- [ ] I will use exactly one new proof file path: `backend/tests/test_layer3_session_entry.py`.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|recommended choice 5`

- [ ] I will use exactly one manual migration file path pattern: `backend/alembic/versions/<revision>_layer3_session_entry.py`.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|recommended choices 3-4`

- [ ] I will not touch `backend/app/schemas/api.py` unless I stop and explicitly escalate first.
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|recommended choice 2`

- [ ] I will not touch `backend/main.py`, `backend/app/api/router.py`, `backend/app/api/review_nrc_aps.py`, `backend/app/schemas/review_nrc_aps.py`, `backend/app/review_ui/static/**`, `backend/app/services/review_nrc_aps_*`, `backend/app/services/analysis.py`, `backend/app/api/market_data_*.py`, `backend/app/services/market_data_*.py`, or the downstream `backend/app/services/nrc_aps_*` artifact family.
  `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md|artifact|forbidden-touch rows and out-of-scope path families`

- [ ] I will not treat any other-worktree file or route as repo-root implementation truth.
  `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 4 invariant 6`

- [ ] I will use a test-only internal proof harness that imports the new service module directly; I will not add a temporary route or browser surface.
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|recommended choice 6`; `P|layer3_primary_planningdocs/06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md|Recommended invocation posture|141-143`

- [ ] I acknowledge the proof burden: one machine-checkable proof surface, one happy path, one partial-feed path, explicit payload refs/hashes/lineage, and explicit unchanged forbidden surfaces.  
  `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 6`

- [ ] I acknowledge the fail-closed boundary: if I cannot explain what loaded, what failed, and why, I must stop.  
  `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Fail-closed conditions|120-127`; `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|stop conditions 6-7`

- [ ] I acknowledge the exact stop conditions: forbidden-touch need, Phase 2+ drift, runtime DB write need, route/API/UI widening, worktree-only reliance, or inability to produce a machine-checkable proof surface.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md|artifact|stop conditions 1-7`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 7`

- [ ] I have run the recommended preflight commands and confirmed that forbidden surfaces are currently untouched before editing begins.  
  `Evidence:` `A|next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS.md|artifact|command-sequence steps 1-2`

- [ ] I am prepared to close out with the exact changed path list, proof command/results, no-touch verification result, and a plain statement that all later phases remain deferred.  
  `Evidence:` `P|layer3_primary_planningdocs/11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md|Minimum proof outputs per slice|129-134`; `A|next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md|artifact|section 8`
