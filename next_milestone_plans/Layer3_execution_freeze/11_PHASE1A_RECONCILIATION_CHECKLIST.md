# 11 Phase1A Reconciliation Checklist

## Purpose

This checklist is the lane-local reconciliation and future re-verification surface for the bounded Phase 1A Layer 3 pack on `codex/layer3-lane`.

It exists to prevent:
- the frozen planning pack being mistaken for broader Layer 3 closure
- the code slice being mistaken for downstream-ready Layer 3 behavior
- navigation aids being mistaken for normative control
- branch-local planning drift from being missed after doc or code follow-up work
- the acceptance audit being treated as optional once the code is committed

This document is operational and non-normative.
Normative control remains with the active Phase 1A control spine and the postcode acceptance audit.

## Current adopted-state note

The following state is already achieved on `codex/layer3-lane`:
- the bounded Phase 1A code slice is committed
- the postcode acceptance audit is committed
- the lane-local planning pack now includes a front-door README, a reconciliation checklist, a roadmap notes + PNG pair, and a concrete implementation surface map

This checklist is therefore:
- a record of what was required for lane-local closure
- and a future reconciliation checklist if the lane is reopened, reviewed, or merged later

## 1. Pack integrity checklist

These items should remain true for the pack to be considered lane-locally coherent:

1. Confirm the three pack directories are present:
   - `next_milestone_plans/Layer3_planning_docs`
   - `next_milestone_plans/Layer3_execution_handoff`
   - `next_milestone_plans/Layer3_execution_freeze`
2. Confirm the normative REV2 planning and handoff docs remain present and readable.
3. Confirm `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md` is present inside `Layer3_execution_freeze`.
4. Confirm `README_LAYER3_PHASE1A_PACK.md` is present as the front-door navigation doc.
5. Confirm `11_PHASE1A_RECONCILIATION_CHECKLIST.md` is present as the operational future-recheck surface.
6. Confirm `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md` and `layer3_phase1a_roadmap.png` are present together.
7. Confirm `13-phase1a-surface-map.md` is present as the concrete module / dependency / boundary map.
8. Confirm no pack-local doc claims broader Layer 3 implementation closure than the bounded Phase 1A slice actually provides.

## 2. Code-to-doc closure checklist

These items tie the planning pack to the committed implementation:

1. Confirm the committed code slice remains exactly:
   - `backend/app/models/models.py`
   - `backend/app/services/layer3_session_entry.py`
   - `backend/alembic/versions/0012_layer3_session_entry.py`
   - `backend/tests/test_layer3_session_entry.py`
2. Confirm the landed objects remain exactly:
   - `l3_session`
   - `l3_selection_manifest`
   - `l3_descriptor`
   - `l3_retrieval_event`
   - `l3_material_snapshot`
3. Confirm no later object is implied as live:
   - `l3_typing_record`
   - `l3_analysis_*`
   - `l3_pass_run`
   - `l3_reconciliation_record`
   - `l3_output_package`
4. Confirm the README, roadmap notes, reconciliation checklist, and surface map all describe the same frozen boundary as the normative control docs.
5. Confirm the surface map does not imply a new route family, public endpoint, runtime DB write surface, or downstream APS handoff surface is now live.
6. Confirm no operational companion doc implies that route-family work, UI widening, APS handoff, or consumer widening is now live.

## 3. Commit-state checklist

These items should remain true for lane-local closure to stay coherent:

1. Confirm the freeze-pack commit remains in history:
   - `a95bc104` `docs(layer3): freeze phase1a planning pack`
2. Confirm the bounded code commit remains in history:
   - `0b0ecf7e` `feat(layer3): add Phase 1A feeder-ledger entry slice`
3. Confirm the postcode acceptance audit commit remains in history:
   - `d67bc0e8` `docs(layer3): add Phase 1A postcode acceptance audit`
4. Confirm the front-door / roadmap closeout commit remains in history:
   - `f252d820` `docs(layer3): add phase1a pack front door and roadmap`
5. Confirm the surface-map closeout commit remains in history:
   - `119c1d73` `docs(layer3): add phase1a surface map`
6. If a later follow-up adds docs or review material, confirm it does not rewrite or blur the meaning of those five commits by implication.

## 4. Proof-state checklist

These items are the minimum continued proof posture for the lane:

1. The bounded Alembic upgrade path should still pass on the local disposable worktree DB target.
2. `python -B -m pytest ./backend/tests/test_layer3_session_entry.py -p no:cacheprovider` should still pass.
3. `git diff --check` should remain clean enough for normal commit-readiness, ignoring only non-semantic LF/CRLF normalization warnings if they recur.
4. The worktree should be clean after closure unless a new explicitly bounded docs or code pass is in progress.

## 5. Navigation and classification checklist

These items keep navigation docs from drifting into fake authority:

1. `README_LAYER3_PHASE1A_PACK.md` must continue to classify normative vs operational docs explicitly.
2. `12_PHASE1A_ROADMAP_AND_DECISION_NOTES.md` must continue to declare that stronger control docs govern if there is a conflict.
3. `layer3_phase1a_roadmap.png` must remain a derived artifact from the roadmap notes rather than a separate planning truth source.
4. If roadmap notes change materially, the PNG must be updated in the same pass.
5. `13-phase1a-surface-map.md` must remain an operational companion and must not silently become a stronger authority than the control spine.
6. If a new lane-local control doc is added, the README should be updated so the front door stays accurate.

## 6. Reopen triggers

Do not treat the lane as fully closed if any of the following becomes true:

1. the code slice widens beyond the four committed code files
2. a doc starts implying Phase 2+ objects are live
3. a doc starts implying route-family or consumer widening is live
4. the postcode acceptance audit disappears from the lane
5. the roadmap notes and PNG diverge materially
6. the lane no longer matches the intended bounded Phase 1A tranche

## 7. Future reconciliation use

If future reconciliation is needed:

1. Recheck the committed lane state before trusting older closure language.
2. Reconfirm the four-file code slice and one-file postcode audit still match the described closure state.
3. Reconfirm the README, roadmap notes, and checklist still agree with the normative control spine.
4. Record any mismatch explicitly instead of smoothing it over.

## Result

The lane remains adequately reconciled only while:
- the normative Phase 1A control spine stays intact
- the committed code slice stays bounded
- the postcode acceptance audit stays present
- and the operational companion docs stay synchronized with those stronger authority surfaces
