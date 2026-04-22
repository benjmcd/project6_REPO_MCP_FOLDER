# 26 L3 WB Inputs

## Status
- planning-only
- not active
- companion input doc for `24_L3_WB_FREEZE.md`
- does not reopen the settled packet or change merged milestone counts

## Lane
- future workbench route family
- purpose: exact-freeze input preparation and branch-local decision capture only

## Role separation
- `24_L3_WB_FREEZE.md` remains the boundary, dependency, non-goal, and ambiguity-control doc for this lane.
- This doc records the exact-freeze inputs and the branch-local planning decisions that can now be adopted without pretending the lane is active.
- This doc does not itself activate the lane.

## Decision posture for this pass
- Freeze-ready recommendations in this doc are limited to what live repo truth plus primary planning already support.
- The two previous blockers for this lane are now resolved on this branch-local planning pass:
  - the lane trigger
  - the route-family choice
- A later activation-ready freeze may keep those adopted decisions, narrow them, or explicitly reopen them, but it must do so explicitly.

## Authority order
1. live repo truth on current `main`
2. active packet, front-door, and control docs on current `main`
3. primary Layer 3 planning authority
4. `24_L3_WB_FREEZE.md`
5. this companion input doc

## Repo-confirmed current truth
- current `main` already ships:
  - `/review/nrc-aps`
  - `/review/nrc-aps/document-trace`
  - `/review/nrc-aps/workbench-compare`
  - `/review/nrc-aps/candidate-b-trace`
  - `/review/analyst-insight`
- current `main` already ships review-shell API surfaces under `/api/v1/review/nrc-aps/...`.
- current `main` does not yet ship a broader Layer 3 workbench page family rooted at `/review/layer3`.
- current `main` does not yet ship a broader Layer 3 API family rooted at `/api/v1/layer3/...`.
- current review graph truth still ends at `validate_only_gates`; it does not already encode a broader Layer 3 controller/workbench lane.
- current Workbench Compare and Candidate B Trace remain additive consumer surfaces, not Layer 3 controller truth.
- current analyst-insight remains a separate deterministic product surface, not the broader Layer 3 workbench.

## Exact freeze inputs
### 1. Lane trigger
- Freeze one exact trigger for why this lane should exist next:
  - one exact operator workflow insufficiency in the currently shipped review/document-trace/workbench-compare/Candidate B/analyst-insight posture
  - or one exact product requirement that justifies the broader workbench even without a proven current insufficiency
- Status:
  - adopted on this branch-local planning pass
- Adopted trigger path:
  - operator-insufficiency path
- Adopted exact trigger statement:
  - `The currently shipped adjacent surfaces are insufficient because no single live surface owns the full selection-commit -> loading -> typing-review -> plan-review -> pass-monitor -> reconciled-results -> package-review lifecycle as one operator controller.`
- Evidence for the adopted trigger:
  - current `main` ships separate review, document-trace, Workbench Compare, Candidate B Trace, and analyst-insight pages rather than one broader controller route family
  - current `main` ships review-shell API surfaces under `/api/v1/review/nrc-aps/...`, but no broader `/api/v1/layer3/...` family
  - current review graph truth still ends at `validate_only_gates`; it does not already encode a broader Layer 3 controller/workbench lane
  - primary planning says the broader workbench is a new stateful operator surface rather than a claim that the current analyst-insight page already covers the full workflow
- Non-adopted alternative:
  - a product-requirement path may still be chosen later only if a later freeze explicitly reopens the trigger decision

### 2. Route-family choice
- Freeze one exact route-family choice:
  - preferred current planning default: a new additive family rooted at `/review/layer3` plus `/api/v1/layer3/...`
  - only acceptable alternative: an explicitly justified evolution of `/review/analyst-insight`
- Inadmissible choices:
  - folding the broader workbench into `/review/nrc-aps`
  - folding it into `/review/nrc-aps/document-trace`
  - relabeling `/review/nrc-aps/workbench-compare` as the broader workbench
  - relabeling `/review/nrc-aps/candidate-b-trace` as the broader workbench
- Status:
  - adopted on this branch-local planning pass
- Adopted route-family choice:
  - UI root: `/review/layer3`
  - API root: `/api/v1/layer3/...`
- Why this route family is adopted here:
  - primary planning already recommends a new route family rather than pretending `/review/analyst-insight` is already the full workbench
  - current analyst-insight is a stable, separately documented, separately tested product surface with alias-backed APIs
  - current review/document-trace/workbench-compare/Candidate B Trace surfaces are already live, adjacent, and separately tested, so overloading them would blur current repo truth
  - the user delegated continuation discretion for the next planning step, which is enough to choose the narrowest supported branch-local route-family decision here
- Still unresolved within this adopted route family:
  - exact subroute layout
  - exact module and file names

### 3. Owner-surface class
- Freeze one exact owner-surface class for:
  - the broader workbench page shell
  - the broader workbench API/router surface
  - the validation/proof surfaces
- Exact file and module names remain unresolved here.
- Status:
  - freeze-ready recommendation present
  - exact filenames remain implementation-local once the route family is explicitly confirmed
- Recommended owner-surface class:
  - one new broader-workbench page shell served as its own route family rather than as an extension of the current review/document-trace page shells
  - one new Layer 3 API router/module family mounted through `backend/app/api/router.py`
  - one new validation/proof surface family for broader-workbench shell and operator-flow proof
- Explicit anti-patterns:
  - do not extend `review_nrc_aps.router` as though the broader workbench were just another review/document-trace consumer endpoint
  - do not treat the current `market_*` / analyst-insight alias API family as the owner surface for the broader workbench

### 4. State editability map
- Freeze one exact editability decision for each required state:
  - `draft_selection`
  - `selection_review`
  - `loading`
  - `typing_review`
  - `plan_review`
  - `pass_monitor`
  - `reconciled_results`
  - `package_review`
- Current planning default is to preserve the state-boundary posture already recorded in `24_L3_WB_FREEZE.md` unless a later explicit freeze changes it.
- Status:
  - freeze-ready recommendation present
- Recommended v1 state editability map:

| State | Recommended posture |
| --- | --- |
| `draft_selection` | editable; no durable Layer 3 session yet |
| `selection_review` | review plus commit only; no silent mutation after commit |
| `loading` | read-only progress visibility |
| `typing_review` | bounded override-only review |
| `plan_review` | bounded approve/reject only; no execution side effects during review |
| `pass_monitor` | inspect status; rerun only where a later lane explicitly allows it |
| `reconciled_results` | read-only accepted versus quarantined review |
| `package_review` | inspect package variants; bounded handoff initiation only if a later active lane explicitly admits it |

### 5. Proof contract
- Freeze one exact headed Chrome operator flow.
- Freeze one exact headless Chrome proof flow for the same shell and state transitions.
- Freeze one exact adjacent-surface preservation requirement for:
  - review
  - document-trace
  - Workbench Compare
  - Candidate B Trace
  - analyst-insight
- Freeze one exact proof that Candidate B remains bundle-scoped and non-admitted unless a later separate lane explicitly reopens that boundary.
- Freeze one exact proof that runtime DB writes, schema widening, and generic route widening remain out.
- Status:
  - freeze-ready recommendation present
- Recommended minimum proof contract:
  - headed Chrome and headless Chrome both cover one broader-workbench shell path through:
    - route load
    - `draft_selection`
    - `selection_review`
    - `loading`
    - `typing_review`
    - `plan_review`
    - `pass_monitor`
    - `reconciled_results`
    - `package_review`
  - both proof paths must show intelligible failure or partial-state visibility where the state machine expects it
  - both proof paths must verify that:
    - `/review/nrc-aps` still behaves as review
    - `/review/nrc-aps/document-trace` still behaves as document-trace
    - `/review/nrc-aps/workbench-compare` still behaves as compare
    - `/review/nrc-aps/candidate-b-trace` still behaves as bundle-scoped Candidate B inspection
    - `/review/analyst-insight` still behaves as the narrow deterministic product surface
  - both proof paths must verify no hidden runtime-write, schema, or generic route widening dependency

### 6. Preparation rules
- Freeze the exact same-checkout or validate-only preparation rules that govern this broader workbench family.
- Freeze the exact bundle-scope versus runtime-scope constraints that still apply when the lane is later activated.
- Status:
  - freeze-ready recommendation present
- Recommended preparation rules:
  - preserve current same-checkout and validate-only prep rules for adjacent compare/Candidate B validation whenever those surfaces are part of broader-workbench proof
  - do not let broader-workbench proof assume Candidate B runtime admission, compare-page ownership, or document-trace contract widening
  - treat current review/document-trace runtime DBs as read-only evidence-plane surfaces unless a separate later lane explicitly reopens that boundary

## Recommended defaults not yet frozen
- The broader workbench should remain separate from the currently shipped review, document-trace, Workbench Compare, and Candidate B Trace surfaces.
- The state-boundary defaults already written in `24_L3_WB_FREEZE.md` should remain the working default until a later explicit freeze says otherwise.
- Headed and headless Chrome proof should remain mandatory later-lane proof, not optional follow-up.

## Freeze-ready subset vs still-blocking subset
### Freeze-ready now
- adopted operator-insufficiency trigger
- adopted additive route-family choice
- recommended owner-surface class
- recommended state editability map
- recommended minimum proof contract
- recommended preparation rules

### Still blocking
- one exact owner-surface table
- one exact proof matrix
- one exact remains-out list for any later activation-ready freeze or implementation-entry packet

## Exact next-pass outputs
- one exact owner-surface table
- one exact proof matrix
- one exact remains-out list

## Exact non-goals
- no activation decision in this doc
- no implementation code
- no route or UI edits
- no runtime DB writes or migrations
- no schema widening
- no Candidate B runtime admission
- no generic route-family widening
- no promotion of package-derived context into dossier truth
- no qualitative single-item activation from `25_L3_QUAL1_FREEZE.md`

## Stop conditions
- If the chosen route family requires broadening shipped review or document-trace contracts, stop and reopen that as a separate route/UI widening decision.
- If the lane trigger cannot be proven from repo-confirmed operator insufficiency or an explicitly frozen product requirement, stop and keep the lane planning-only.
- If the proof contract would require runtime DB writes, schema widening, or shared APS-contract reopening just to remain coherent, stop and reopen those lanes separately.

## Evidence basis for the freeze-ready subset
- primary planning:
  - `01_LAYER3_OPERATOR_USE_MODEL_AND_SYSTEM_BOUNDARY.md`
  - `03_LAYER3_SESSION_LEDGER_AND_WORKSPACE_MODEL.md`
  - `08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md`
  - `11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md`
  - `12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md`
- current repo truth:
  - `backend/main.py`
  - `backend/app/api/router.py`
  - `backend/app/api/review_nrc_aps.py`
  - `backend/app/services/review_nrc_aps_graph.py`
  - `docs/analyst_insight/analyst_insight_status_handoff.md`
  - `frontend_UI_plans/README.md`
  - `frontend_UI_plans/wb-compare-spec.md`
  - `frontend_UI_plans/wb-compare-validation.md`
