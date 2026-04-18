# Layer3 Phase1A Planning Pack

## Purpose

This file is the front door for the bounded Phase 1A Layer 3 planning and closure pack on `codex/layer3-lane`.

Use it to orient quickly across the three active pack directories:
- `next_milestone_plans/Layer3_planning_docs`
- `next_milestone_plans/Layer3_execution_handoff`
- `next_milestone_plans/Layer3_execution_freeze`

This README is operational and navigational.
If it conflicts with the stronger frozen control docs, the control docs govern.

## Current state

The lane now contains:
- the frozen Phase 1A planning baseline
- the execution handoff/control fence
- the implementation-local freeze docs
- the committed bounded Phase 1A code slice
- the committed postcode acceptance audit
- the pack-local roadmap, reconciliation, and navigation surfaces needed for lane-local closure

Committed branch-local closure sequence:
- `a95bc104` `docs(layer3): freeze phase1a planning pack`
- `0b0ecf7e` `feat(layer3): add Phase 1A feeder-ledger entry slice`
- `d67bc0e8` `docs(layer3): add Phase 1A postcode acceptance audit`

Current bounded posture:
- Phase 1A remains Gate-B-only feeder / ledger entry
- landed objects remain exactly:
  - `l3_session`
  - `l3_selection_manifest`
  - `l3_descriptor`
  - `l3_retrieval_event`
  - `l3_material_snapshot`
- typing, orchestration, packaging, APS handoff, route-family work, UI widening, and consumer widening remain deferred

## One-line use rule

Use this pack as the lane-local authoritative planning and closure bundle for the bounded Phase 1A Layer 3 slice; do not treat it as permission to reopen broader Layer 3 scope.

## Pack layout

### 1. Planning baseline

Read these first when you need the tranche boundary, prep rules, and validation posture:
- `Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`

### 2. Execution handoff

Read these when you need the touch envelope, proof runbook, and direct write-enabled contract:
- `Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md`

### 3. Local freeze and closure

Read these when you need the implementation-local defaults, acceptance criteria, write-enabled prompt, reconciliation posture, roadmap, and postcode audit:
- `Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `Layer3_execution_freeze/08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `Layer3_execution_freeze/09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `Layer3_execution_freeze/10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- `Layer3_execution_freeze/11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `Layer3_execution_freeze/12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `Layer3_execution_freeze/layer3_phase1a_roadmap.png`
- `Layer3_execution_freeze/FREEZE_PACK_REV1_TO_REV2_SOURCE_HYGIENE_MEMO.md`

## Doc classification

### Normative control docs

These define the actual tranche boundary and control posture:
- `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `06_PHASE1A_CODEWRITING_HANDOFF.md`
- `07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### Operational companion docs

These help navigation, reconciliation, and visual orientation, but do not override the normative set:
- `README_LAYER3_PHASE1A_PACK.md`
- `11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`
- `layer3_phase1a_roadmap.png`

Rule:
- if a rule exists only in an operational companion doc, move or restate it in the normative control spine before relying on it as durable control guidance

## Current use guidance

### If you are auditing scope

Start with:
- `01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### If you are checking whether the lane is closed enough to review

Start with:
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- `11_PHASE1A_RECONCILIATION_CHECKLIST.md`
- `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md`

### If you are deciding whether more Phase 1A code work is justified

Start with:
- `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
- the committed code diff at `0b0ecf7e`

Current answer:
- no additional Phase 1A code work is justified by default from the current lane state

## Residual boundary note

This README closes the lane-local navigation gap, not broader repo-wide Layer 3 documentation closure.

It does not prove that unrelated dirty root planning pools or higher-level repo front doors are globally reconciled.
That broader question requires a separate read-only root-doc audit.
