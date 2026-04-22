# 24 L3 Workbench Freeze

## Status
- planning-only
- not active
- prepared from settled current-main posture
- active manifest, board, and status docs remain settled unless reopened separately

## Lane
- future workbench route family

## Companion exact-freeze input doc
- `26_L3_WB_INPUTS.md` now records the adopted branch-local trigger and route-family choice for this lane, the adopted minimum typing posture, the exact owner-surface and proof mapping for implementation-entry prep, and the exact remains-out list that keeps later work narrow.
- This doc remains the boundary, dependency, non-goal, and ambiguity-control surface.
- The companion input doc is planning-only prep and does not itself satisfy activation prerequisites.

## Why prep is justified now
- Current `main` already ships adjacent operator consumers, but not a full Layer 3 workbench.
- Primary planning still treats the broader workbench route family as an explicit open freeze item.
- This prep can stay additive and planning-only without reopening APS packet state, runtime DB boundaries, schema, or generic route widening.

## Why activation is not automatic
- An exact branch-local route-family choice is now recorded in `26_L3_WB_INPUTS.md`, but no live route family is active yet.
- Only a minimum branch-local typing posture is now recorded in `26_L3_WB_INPUTS.md`; activation-grade thresholds, `entity_graph` defaults, APS document-unit granularity, and typing-conflict presentation remain unfrozen.
- No exact shell or state-transition proof exists yet for the broader workbench.
- No headed plus headless Chrome proof exists yet for the future broader workbench family.
- The active packet is still settled and does not nominate this as an active lane.

## Exact scope
- Freeze a planning-only additive Layer 3 workbench family.
- Keep `/review/analyst-insight` as the narrow shipped kernel/demo surface.
- Keep review, document-trace, Workbench Compare, and Candidate B Trace as adjacent consumer surfaces.
- Planning default route family:
  - UI: `/review/layer3`
  - API: `/api/v1/layer3/...`
- Required workbench states:
  - `draft_selection`
  - `selection_review`
  - `loading`
  - `typing_review`
  - `plan_review`
  - `pass_monitor`
  - `reconciled_results`
  - `package_review`

## Accepted state machine
- Accepted unchanged from primary planning.
- Reason:
  - it preserves the `selection commit` boundary before Layer 3 starts
  - it keeps controller-state concerns separate from adjacent inspection pages
  - it matches the minimum v1 acceptance criteria already stated in primary planning

## State boundaries
- `draft_selection`
  - editable
  - no durable Layer 3 session yet
- `selection_review`
  - review plus commit only
  - no silent mutation after commit
- `loading`
  - read-only progress visibility
  - no operator data edits
- `typing_review`
  - bounded override-only review
  - no route-family spill into adjacent pages
- `plan_review`
  - approve or reject bounded plan only
  - no execution side effects during review
- `pass_monitor`
  - inspect status
  - rerun only where later lane rules allow it
- `reconciled_results`
  - read-only accepted versus quarantined review
- `package_review`
  - inspect package variants
  - bounded handoff initiation only if a later active lane admits it

## Dependencies
- selection-commit boundary remains the Layer 3 start condition
- session-scoped workspace model remains authoritative
- read-only runtime DB boundary remains unchanged
- active packet remains settled while this doc is only planning
- the companion input doc now adopts the branch-local operator-insufficiency trigger, additive route-family choice, and minimum typing posture, and records the exact owner-surface/proof/no-go mapping for implementation-entry prep, but activation still requires an explicit later freeze outcome rather than the prep doc by itself
- later implementation must still choose exact filenames and subroutes, honor the no-go list, and produce the headed/headless plus backend proof outputs before activation

## Boundary-level owner-surface classes for later activation
- repo-confirmed current touchpoints that would likely participate:
  - `backend/main.py`
  - `backend/app/api/router.py`
- planning-only owner classes, with exact filenames still unresolved:
  - one Layer 3 workbench API module or equivalent router surface
  - one broader workbench page shell plus supporting static assets
  - backend API and page proof surfaces for the broader workbench family
  - one headed plus headless browser proof surface for the broader workbench family

## Adjacent surfaces that must remain separate
- `backend/app/review_ui/static/review.js`
- `backend/app/review_ui/static/document_trace.js`
- `backend/app/review_ui/static/workbench_compare.js`
- `backend/app/review_ui/static/candidate_b_trace.js`
- `backend/app/review_ui/static/analyst_insight.js`
- `backend/app/services/review_nrc_aps_runtime_db.py`

## Later activation prerequisites
- the adopted branch-local operator-insufficiency trigger and additive route-family choice from `26_L3_WB_INPUTS.md` must remain intact unless a later freeze explicitly reopens them
- the adopted minimum typing posture from `26_L3_WB_INPUTS.md` must remain inside the primary `source_shape != analysis_modality` boundary, and any later threshold, `entity_graph`, granularity, or UI-presentation choices must be frozen explicitly rather than assumed ad hoc
- one exact file/module-local route/API ownership implementation must still be chosen; current planning-default route names plus the branch-local owner-surface table do not by themselves settle final route strings or file/module names
- headed Chrome proof that the broader workbench shell loads and exposes the full state machine
- headless Chrome proof of the same shell and state transitions
- proof that typing review and override behavior follow the adopted minimum typing posture and record auditable override state
- proof that adjacent review and document-trace surfaces remain unchanged and non-overloaded
- proof that Workbench Compare and Candidate B Trace remain bundle-scoped or consumer-scoped rather than being promoted into Layer 3 control truth
- proof that no runtime DB writes, schema widening, or generic route widening were smuggled into the lane

## Exact non-goals
- no code implementation in this prep step
- no route/UI edits in current shipped review or document-trace pages
- no runtime DB writes or migrations
- no schema widening
- no shared APS contract reopening
- no Candidate B admission into normal runtime truth
- no package-derived-context promotion into dossier truth
- no packet or front-door status update that implies this lane is active

## Debt and ambiguity controls
- do not let this doc become a second truth surface for shipped behavior
- do not treat planning-default route names as already active repo truth
- do not widen from additive workbench family into generic route/UI widening
- do not treat the workbench as only a visual shell; it is a controller surface in planning, but still outside Layer 3 itself

## Rollback or abandonment posture
- If later evidence shows no broader workbench is needed, abandon this planning doc without changing the settled packet.
- If later evidence supports a different route family, supersede this doc with a narrower replacement rather than editing active packet artifacts first.
- If later proof shows the broader workbench would require schema or runtime-write widening, stop and reopen those lanes separately instead of broadening this one.
