# 26 L3 WB Inputs

## Status
- planning-only
- not active
- merged on current `main` as deferred-scope prep only
- companion input doc for `24_L3_WB_FREEZE.md`
- does not reopen the settled packet or change merged milestone counts

## Lane
- future workbench route family
- purpose: exact-freeze input preparation and planning decision capture only

## Role separation
- `24_L3_WB_FREEZE.md` remains the boundary, dependency, non-goal, and ambiguity-control doc for this lane.
- This doc records the exact-freeze inputs and the planning decisions now landed on current `main` without pretending the lane is active.
- This doc does not itself activate the lane.

## Decision posture for this pass
- Freeze-ready recommendations in this doc are limited to what live repo truth plus primary planning already support.
- The two previous blockers for this lane are now resolved in this planning-only packet:
  - the lane trigger
  - the route-family choice
- This planning-only packet also adopts the minimum typing posture that primary planning plus ADR-003 already support for later implementation-entry prep, without pretending thresholds, APS document-unit granularity, or typing-conflict presentation are already frozen.
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

## Repo-confirmed implementation-entry map
- current page-route registration pattern for adjacent operator surfaces lives in `backend/main.py`
- current shared API include pattern lives in `backend/app/api/router.py`
- current durable Layer 3 model ownership already landed on current `main` lives in `backend/app/models/models.py`
- current manual Layer 3 migration chain already landed on current `main` lives in:
  - `backend/alembic/versions/0012_layer3_session_entry.py`
  - `backend/alembic/versions/0013_layer3_typing_entry.py`
  - `backend/alembic/versions/0014_layer3_pass_entry.py`
  - `backend/alembic/versions/0015_layer3_package_entry.py`
- current review/document-trace/workbench-compare/Candidate B API ownership lives in `backend/app/api/review_nrc_aps.py`
- current analyst-insight alias API ownership lives in:
  - `backend/app/api/market_data_integration.py`
  - `backend/app/api/market_data_validation.py`
  - `backend/app/api/market_insight_ai.py`
- current review-family static shell pattern lives under `backend/app/review_ui/static/` with one HTML/CSS/JS asset set per page family
- current adjacent service/orchestration examples live in:
  - `backend/app/services/review_nrc_aps_graph.py`
  - `backend/app/services/review_nrc_aps_workbench_compare.py`
  - `backend/app/services/review_nrc_aps_candidate_b_trace.py`
- current internal Layer 3 owner-service chain already landed on current `main` lives in:
  - `backend/app/services/layer3_session_entry.py`
  - `backend/app/services/layer3_typing_entry.py`
  - `backend/app/services/layer3_pass_entry.py`
  - `backend/app/services/layer3_package_entry.py`
- current direct Layer 3 service proof surfaces already landed on current `main` live in:
  - `backend/tests/test_layer3_session_entry.py`
  - `backend/tests/test_layer3_typing_entry.py`
  - `backend/tests/test_layer3_pass_entry.py`
  - `backend/tests/test_layer3_package_entry.py`
- current isolated browser-proof harness lives in:
  - `backend/tests/review_browser_server.py`
  - `backend/tests/test_review_browser_server.py`
  - `e2e/nrc-aps-review.spec.js`
  - `playwright.config.js`
  - `.github/workflows/playwright.yml`
- current page/API regression pattern for adjacent surfaces lives in:
  - `backend/tests/test_review_nrc_aps_page.py`
  - `backend/tests/test_review_nrc_aps_document_trace_page.py`
  - `backend/tests/test_review_nrc_aps_workbench_compare_page.py`
  - `backend/tests/test_review_nrc_aps_workbench_compare_api.py`
  - `backend/tests/test_review_nrc_aps_candidate_b_trace_page.py`
  - `backend/tests/test_review_nrc_aps_candidate_b_trace_api.py`
  - `backend/tests/test_analyst_insight_page.py`
  - `backend/tests/test_analyst_insight_alias_parity.py`

## Repo-confirmed dependency posture
- repo-native web entry uses `FastAPI`, `APIRouter`, and `StaticFiles`; no current-main evidence requires a new web stack for this lane
- adjacent operator pages use repo-native static HTML/CSS/JS assets under the shared `/review/nrc-aps/static` mount
- adjacent page/API regression proof uses `pytest` plus `fastapi.testclient.TestClient`
- repo-native browser regression proof uses Playwright Chromium plus the isolated `review_browser_server` harness
- current internal Layer 3 owner services already depend on:
  - SQLAlchemy `Session`
  - `app.models.models` Layer 3 ledger and downstream Layer 3 objects
  - `app.core.config.settings`
  - `app.services.analysis` and `app.services.dataframe_io` for the currently landed quantitative pass-entry slice
  - `pandas` for the currently landed quantitative associated-cohort shaping path inside `layer3_pass_entry.py`
- current-main evidence does not justify a new migration, schema expansion, or replacement persistence layer for workbench/controller entry by itself
- no current-main evidence justifies assuming React, a client-side router, or a new component library for the first additive workbench slice
- no current-main evidence justifies re-implementing the landed Layer 3 ledger, typing, pass, or package core logic inside future route handlers or static browser code

## Repo-confirmed controller-to-service connection map
- Future broader-workbench route/API layers should default to orchestrating the already-landed internal Layer 3 owner-service chain rather than inventing new write-side cores.
- Default connection map for later implementation entry:

| Workbench concern | Current repo-confirmed service surface | Connection rule |
| --- | --- | --- |
| selection commit | `backend/app/services/layer3_session_entry.py::commit_selection(...)` | future controller/API entry should create the durable session and selection manifest through the landed owner service, not through route-local DB mutation |
| descriptor expansion and loading closure | `backend/app/services/layer3_session_entry.py::expand_descriptors(...)`, `record_retrieval_event(...)`, `finalize_session(...)` | future controller/API entry should drive loading through the landed Phase 1A service flow and preserve its session summary semantics |
| typing/unit materialization | `backend/app/services/layer3_typing_entry.py::materialize_typing_entry(...)` | future controller/API entry should invoke the landed typing/unit owner service and keep its fail-closed unsupported-shape behavior intact |
| plan/pass entry | `backend/app/services/layer3_pass_entry.py::materialize_pass_entry(...)` | future controller/API entry should invoke the landed pass-entry owner service and keep its quantitative single-item / associated-cohort bounded semantics intact unless a later freeze reopens them |
| package/reconciliation entry | `backend/app/services/layer3_package_entry.py::materialize_package_entry(...)` | future controller/API entry should invoke the landed package-entry owner service and keep its current package-kind/provenance rules intact unless a later freeze reopens them |

- Connection anti-patterns:
  - no route-local reimplementation of session, typing, pass, or package persistence rules
  - no browser-only state machine that diverges from the landed owner-service chain
  - no hidden route/API shortcut that bypasses the landed direct service proof surfaces

## Exact freeze inputs
### 1. Lane trigger
- Freeze one exact trigger for why this lane should exist next:
  - one exact operator workflow insufficiency in the currently shipped review/document-trace/workbench-compare/Candidate B/analyst-insight posture
  - or one exact product requirement that justifies the broader workbench even without a proven current insufficiency
- Status:
  - adopted in this planning-only packet on current `main`
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
  - adopted in this planning-only packet on current `main`
- Adopted route-family choice:
  - UI root: `/review/layer3`
  - API root: `/api/v1/layer3/...`
- Why this route family is adopted here:
  - primary planning already recommends a new route family rather than pretending `/review/analyst-insight` is already the full workbench
  - current analyst-insight is a stable, separately documented, separately tested product surface with alias-backed APIs
  - current review/document-trace/workbench-compare/Candidate B Trace surfaces are already live, adjacent, and separately tested, so overloading them would blur current repo truth
  - this adopted route family stays additive, matches current primary-planning defaults, and avoids overloading any existing live owner surface
- Still unresolved within this adopted route family:
  - exact subroute layout
  - exact module and file names

### 3. Exact owner-surface table
- Freeze one exact owner-surface mapping for the broader workbench page shell, API/router family, service/orchestration family, and proof surfaces.
- Status:
  - adopted in this planning-only packet on current `main`
  - exact filenames remain implementation-local once this packet is accepted

| Concern | Exact current touchpoints | Adopted future owner class | Must stay separate from |
| --- | --- | --- | --- |
| UI route registration | `backend/main.py` | one additive broader-workbench page route entry rooted at `/review/layer3` | existing `/review/nrc-aps`, `/review/nrc-aps/document-trace`, `/review/nrc-aps/workbench-compare`, `/review/nrc-aps/candidate-b-trace`, `/review/analyst-insight` page handlers |
| Static page shell assets | `backend/app/review_ui/static/index.html`, `document_trace.html`, `workbench_compare.html`, `candidate_b_trace.html`, `analyst_insight.html` and their paired CSS/JS assets | one additive Layer 3 shell asset family under `backend/app/review_ui/static/` using the repo-native static mount pattern | overloading existing review/document-trace/workbench-compare/Candidate B/analyst-insight assets as the Layer 3 owner shell |
| Durable model family | `backend/app/models/models.py` | existing Layer 3 ledger and downstream Layer 3 model family remain the persistence owner surface for workbench/controller entry | inventing a parallel browser-local or route-local persistence model for Layer 3 state |
| Migration and schema family | `backend/alembic/versions/0012_layer3_session_entry.py`, `0013_layer3_typing_entry.py`, `0014_layer3_pass_entry.py`, `0015_layer3_package_entry.py` | no new migration or schema owner surface is admitted by default for workbench/controller entry | treating the additive route/workbench lane as implicit permission to widen schema |
| API include point | `backend/app/api/router.py` | one additive Layer 3 router include rooted at `/api/v1/layer3/...` | folding broader workbench ownership into the existing review or analyst-insight includes |
| API module family | `backend/app/api/review_nrc_aps.py`, `backend/app/api/market_data_integration.py`, `backend/app/api/market_data_validation.py`, `backend/app/api/market_insight_ai.py` | one additive `app.api.layer3` module family for session/controller commands and queries | treating `review_nrc_aps.router` or the `market_*` alias routers as the owner surface for the broader workbench |
| Service/orchestration family | `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_workbench_compare.py`, `backend/app/services/review_nrc_aps_candidate_b_trace.py`, `backend/app/services/layer3_session_entry.py`, `backend/app/services/layer3_typing_entry.py`, `backend/app/services/layer3_pass_entry.py`, `backend/app/services/layer3_package_entry.py` | one additive Layer 3 controller/service family under `backend/app/services/` that orchestrates the already-landed internal Layer 3 owner-service chain rather than replacing it | reusing compare, Candidate B, or analyst-insight helper services as though they were the full workbench controller, or duplicating landed Layer 3 core logic inside a new controller |
| Backend page/API proof | `backend/tests/test_review_nrc_aps_page.py`, `backend/tests/test_review_nrc_aps_document_trace_page.py`, `backend/tests/test_review_nrc_aps_workbench_compare_page.py`, `backend/tests/test_review_nrc_aps_workbench_compare_api.py`, `backend/tests/test_review_nrc_aps_candidate_b_trace_page.py`, `backend/tests/test_review_nrc_aps_candidate_b_trace_api.py`, `backend/tests/test_analyst_insight_page.py`, `backend/tests/test_analyst_insight_alias_parity.py`, `backend/tests/test_layer3_session_entry.py`, `backend/tests/test_layer3_typing_entry.py`, `backend/tests/test_layer3_pass_entry.py`, `backend/tests/test_layer3_package_entry.py` | one additive Layer 3 test family under `backend/tests/` for page, API, controller, and direct service proof | rewriting adjacent page/API tests as if those surfaces had become Layer 3, or dropping direct service proof for the already-landed core Layer 3 chain |
| Browser/operator proof | `backend/tests/review_browser_server.py`, `backend/tests/test_review_browser_server.py`, `e2e/nrc-aps-review.spec.js`, `playwright.config.js`, `.github/workflows/playwright.yml` | one additive Layer 3 browser proof family reusing the repo-native isolated browser harness pattern | claiming browser proof from adjacent review/compare/Candidate B flows alone |

Explicit anti-patterns:
- do not extend `review_nrc_aps.router` as though the broader workbench were just another review/document-trace consumer endpoint
- do not treat the current `market_*` / analyst-insight alias API family as the owner surface for the broader workbench
- do not re-implement landed Layer 3 ledger, typing, pass, or package persistence rules inside future route handlers, browser code, or thin API wrappers; the future controller layer should orchestrate the landed owner-service chain unless a later freeze explicitly reassigns ownership
- do not introduce a new frontend framework or component-library dependency unless a later separate decision explicitly proves the repo-native static-shell pattern insufficient

### 4. Minimum typing posture
- Freeze one exact minimum typing posture for the broader workbench lane that stays within current primary-planning authority and does not invent activation-grade heuristics.
- Status:
  - adopted in this planning-only packet on current `main`
- Authority guardrails:
  - primary `source_shape` taxonomy is authoritative for this lane
  - `analysis_modality` remains distinct from `source_shape`
  - the secondary supplementary-plan `ContentKind` names are not authority for this lane and must not replace primary `source_shape` values such as `mixed_source_payload` or `bundle_artifact`
- Adopted default typing posture:

| Primary `source_shape` | Adopted default modality posture | Adopted split or keep posture | Guardrail |
| --- | --- | --- | --- |
| `tabular_numeric` | `quantitative` | split/atomic | numeric structure is primary unless a later explicit freeze proves otherwise |
| `time_series` | `quantitative` | split/atomic | treat as quantitative-first for v1 broader-workbench prep |
| `document_chunks` | `qualitative` unless strong mixed evidence indicates `hybrid` | keep-adjacent then decide | do not assume purely qualitative from document origin alone |
| `mixed_source_payload` | `hybrid` | keep-intact first | split only if auditably safe and meaning is preserved |
| `bundle_artifact` | bounded review first, then `qualitative` or `hybrid` from actual contents | bounded composition first | do not type from artifact label alone |

- Explicit unresolved typing item that remains out of this adopted minimum posture:
  - `entity_graph` does not receive a default here because the primary suggested v1 matrix and ADR-003 additional posture do not yet assign a repo-backed default; any later implementation-entry packet must either stay out of `entity_graph` or freeze it explicitly before claiming support
- Adopted override semantics:
  - allow override when confidence falls below a later frozen threshold
  - allow override when splitting would break meaning or must-remain-intact semantics
  - allow override when the automatic grouping is obviously wrong to the operator
  - every override must record previous choice, new choice, actor, reason, and whether must-remain-intact status changed
- Still intentionally unresolved inside this adopted minimum posture:
  - exact confidence thresholds
  - exact heuristic precedence when multiple signals conflict
  - exact APS document-derived unit granularity
  - exact UI presentation of typing conflicts and ambiguity

### 5. State editability map
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

### 6. Exact proof matrix
- Freeze one exact proof matrix for the broader workbench shell, its API family, and its adjacent-surface preservation rules.
- Status:
  - adopted in this planning-only packet on current `main`

| Proof area | Current repo-backed harness or pattern to reuse | Exact later proof requirement |
| --- | --- | --- |
| Additive workbench page shell load | page-route pattern in `backend/main.py`; page-shell assertions in `backend/tests/test_review_nrc_aps_page.py`, `backend/tests/test_review_nrc_aps_document_trace_page.py`, `backend/tests/test_review_nrc_aps_workbench_compare_page.py`, `backend/tests/test_review_nrc_aps_candidate_b_trace_page.py`, `backend/tests/test_analyst_insight_page.py` | one additive Layer 3 page-shell proof showing `/review/layer3` loads through the repo-native static-shell pattern without changing adjacent routes |
| Additive workbench API family | `backend/app/api/router.py`; API contract proof pattern in `backend/tests/test_review_nrc_aps_workbench_compare_api.py`, `backend/tests/test_review_nrc_aps_candidate_b_trace_api.py`, `backend/tests/test_analyst_insight_alias_parity.py` | one additive Layer 3 API contract proof family for `/api/v1/layer3/...` commands and queries without overloading review or analyst-insight owners |
| Internal Layer 3 service orchestration | `backend/app/services/layer3_session_entry.py`, `backend/app/services/layer3_typing_entry.py`, `backend/app/services/layer3_pass_entry.py`, `backend/app/services/layer3_package_entry.py` plus `backend/tests/test_layer3_session_entry.py`, `backend/tests/test_layer3_typing_entry.py`, `backend/tests/test_layer3_pass_entry.py`, `backend/tests/test_layer3_package_entry.py` | one implementation-entry proof family showing the future controller/API layer delegates into the landed Layer 3 core owner services instead of duplicating ledger, typing, pass, or package logic |
| State-machine visibility | accepted state list in `24_L3_WB_FREEZE.md`; browser/API proof minimums in `11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md` | one happy-path plus one partial-failure proof covering `draft_selection` -> `selection_review` -> `loading` -> `typing_review` -> `plan_review` -> `pass_monitor` -> `reconciled_results` -> `package_review` |
| Minimum typing posture | primary typing workflow and suggested v1 matrix from `04_LAYER3_ANALYSIS_UNIT_MODALITY_AND_SET_MODEL.md`; ADR default posture in `decisions/ADR-003_TYPING_RULES_QUANT_QUAL_HYBRID.md` | one proof family showing adopted `source_shape` defaults, override recording, and fail-closed handling for ambiguous or partial typing state without inventing unsupported thresholds |
| Headless browser proof | isolated browser harness in `backend/tests/review_browser_server.py`, `backend/tests/test_review_browser_server.py`, and `e2e/nrc-aps-review.spec.js` | one headless Chromium proof flow for the broader workbench route using the repo-native isolated browser harness pattern |
| Headed browser/operator proof | manual operator bring-up and validation docs in `docs/nrc_adams/nrc_aps_ui_launch_runbook.md` and `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md` | one headed Chrome operator proof for the same broader workbench route and state transitions, compared against the headless result rather than treated as optional |
| Adjacent review/document-trace preservation | existing review/document-trace page and API tests plus operator docs in `frontend_UI_plans/README.md` and `docs/nrc_adams/nrc_aps_ui_launch_runbook.md` | proof that `/review/nrc-aps` and `/review/nrc-aps/document-trace` still behave as review and document-trace, not as Layer 3 controller surfaces |
| Workbench Compare and Candidate B boundary preservation | `backend/tests/test_review_nrc_aps_workbench_compare_page.py`, `backend/tests/test_review_nrc_aps_workbench_compare_api.py`, `backend/tests/test_review_nrc_aps_candidate_b_trace_page.py`, `backend/tests/test_review_nrc_aps_candidate_b_trace_api.py`, `e2e/nrc-aps-review.spec.js` | proof that compare remains compare, Candidate B Trace remains bundle-scoped inspection, and Candidate B is not admitted into runtime Layer 3 truth |
| Analyst-insight preservation | `backend/tests/test_analyst_insight_page.py`, `backend/tests/test_analyst_insight_alias_parity.py`, `docs/analyst_insight/analyst_insight_status_handoff.md` | proof that `/review/analyst-insight` and `/api/v1/analyst-insight/...` remain the narrow deterministic product surface rather than becoming the broader workbench owner |
| Fail-closed and provenance hygiene | fail-closed invalid-input patterns in compare/Candidate B API tests; no-local-path assertions in `backend/tests/test_review_browser_server.py` and `e2e/nrc-aps-review.spec.js` | proof that the broader workbench fails closed on missing or partial state, does not leak local filesystem paths, and keeps operator-visible failure states intelligible |
| No runtime-write, schema, or generic-route widening | current no-go rules from `24_L3_WB_FREEZE.md`, `12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md`, and current repo absence of `/review/layer3` and `/api/v1/layer3/...` | one implementation-entry audit showing no migration files, no schema/model widening, no hidden runtime-write dependency, and no generic redesign of existing review/document-trace/compare/Candidate B routes |

### 7. Preparation rules
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
- Exact wrapper class names, exact module filenames, and exact component-library choice remain implementation-local even with this planning-only prep packet landed on current `main`.

## Exact remains-out list
- no live implementation of `/review/layer3` or `/api/v1/layer3/...` in this pass
- no broad rewrite of `backend/main.py`; any later workbench entry should be additive and route-local
- no broad rewrite of `backend/app/api/review_nrc_aps.py`; existing review/document-trace/workbench-compare/Candidate B APIs remain adjacent surfaces
- no takeover of `backend/app/api/market_data_integration.py`, `market_data_validation.py`, or `market_insight_ai.py` as the broader workbench owner
- no replacement of the primary `source_shape` taxonomy with supplementary `ContentKind` naming; any later reconciliation must be frozen explicitly before implementation claims support for it
- no duplication of the landed internal Layer 3 owner-service chain inside future route handlers, API wrappers, or browser state code; later work should compose around `layer3_session_entry`, `layer3_typing_entry`, `layer3_pass_entry`, and `layer3_package_entry` unless a later freeze explicitly changes that ownership
- no rewrite of existing `backend/app/review_ui/static/index.html`, `document_trace.html`, `workbench_compare.html`, `candidate_b_trace.html`, or `analyst_insight.html` into the broader workbench shell
- no migrations, no `backend/alembic/versions/*` additions, and no DB-init behavior change
- no schema/model widening and no runtime DB write dependency
- no Candidate B runtime admission or compare-surface ownership shift
- no promotion of package-derived context into dossier truth
- no generic route-family redesign outside the additive `/review/layer3` plus `/api/v1/layer3/...` family
- no assumption that React, a client-side router, or a new component library is required for v1
- no activation-grade typing-threshold, `entity_graph` default, APS document-derived unit granularity, or typing-conflict UI-presentation freeze beyond the adopted minimum typing posture in this doc
- no qualitative single-item activation or qualitative-engine ambition freeze here; that remains with `25_L3_QUAL1_FREEZE.md`

## Implementation-entry posture after this pass
- This planning-only prep packet now makes explicit:
  - the adopted operator-insufficiency trigger
  - the adopted additive route-family choice
  - the adopted minimum typing posture
  - the exact owner-surface table
  - the recommended state editability map
  - the exact proof matrix
  - the exact remains-out list
- That is enough to let a later implementation-entry packet stay narrow without guessing the owner surfaces, minimum typing defaults, browser-proof posture, or no-go boundaries.
- It is not enough to claim the lane is active or live.

## Still not activation-ready
- no live `/review/layer3` or `/api/v1/layer3/...` route family exists on current `main`
- no exact workbench implementation module filenames are chosen yet
- no activation-grade typing thresholds, `entity_graph` default, APS document-derived unit granularity, or typing-conflict UI presentation are frozen yet
- no headed or headless broader-workbench proof has been produced yet
- no implementation/status note or machine-checkable proof output exists yet for the broader workbench family

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
  - `04_LAYER3_ANALYSIS_UNIT_MODALITY_AND_SET_MODEL.md`
  - `08_LAYER3_UI_WORKBENCH_AND_API_SURFACE.md`
  - `11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md`
  - `12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md`
- linked ADR and naming authority:
  - `decisions/ADR-003_TYPING_RULES_QUANT_QUAL_HYBRID.md`
  - `00C_LAYER3_GLOSSARY_AND_NAMING_MAP.md`
- current repo truth:
  - `backend/main.py`
  - `backend/app/api/router.py`
  - `backend/app/models/models.py`
  - `backend/alembic/versions/0012_layer3_session_entry.py`
  - `backend/alembic/versions/0013_layer3_typing_entry.py`
  - `backend/alembic/versions/0014_layer3_pass_entry.py`
  - `backend/alembic/versions/0015_layer3_package_entry.py`
  - `backend/app/api/review_nrc_aps.py`
  - `backend/app/services/layer3_session_entry.py`
  - `backend/app/services/layer3_typing_entry.py`
  - `backend/app/services/layer3_pass_entry.py`
  - `backend/app/services/layer3_package_entry.py`
  - `backend/app/services/review_nrc_aps_graph.py`
  - `docs/analyst_insight/analyst_insight_status_handoff.md`
  - `frontend_UI_plans/README.md`
  - `frontend_UI_plans/wb-compare-spec.md`
  - `frontend_UI_plans/wb-compare-validation.md`
