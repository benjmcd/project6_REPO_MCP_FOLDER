# 27 L3 Qual1 Inputs

## Status
- planning-only
- not active
- branch-local on `codex/qual1-next`; not merged on current `main`
- companion input doc for `25_L3_QUAL1_FREEZE.md`
- does not reopen the settled packet or change merged milestone counts

## Lane
- broader Layer 3 breadth
- purpose: exact-freeze input preparation and planning decision capture only
- exact selected axis: qualitative single-item breadth

## Role separation
- `25_L3_QUAL1_FREEZE.md` remains the boundary, dependency, non-goal, and ambiguity-control doc for this lane.
- This doc records the exact-freeze inputs and planning decisions captured in this branch-local packet without pretending the lane is active.
- This doc does not activate qualitative single-item breadth or change current-`main` state.

## Decision posture for this pass
- Freeze-ready recommendations in this doc are limited to what live repo truth plus primary planning already support.
- This branch-local packet adopts:
  - one exact operator task
  - one minimum qualitative single-item pass-family contract
  - one exact owner-surface table
  - one exact proof matrix
  - one exact remains-out list
- This branch-local packet does not freeze route/UI surfaces, exact module filenames, exact heuristic thresholds, or broader qualitative-engine ambition beyond the minimum first slice.

## Authority order
1. live repo truth on current `main`
2. active packet, front-door, and control docs on current `main`
3. primary Layer 3 planning authority
4. `25_L3_QUAL1_FREEZE.md`
5. this companion input doc

## Repo-confirmed current truth
- current `main` already lands the internal Layer 3 owner-service chain through:
  - `backend/app/services/layer3_session_entry.py`
  - `backend/app/services/layer3_typing_entry.py`
  - `backend/app/services/layer3_pass_entry.py`
  - `backend/app/services/layer3_package_entry.py`
- current typing entry already types `aps_content_document` as `qualitative` with `planning_shape_family=document_chunks`.
- current typing entry already materializes:
  - a `single_item` analysis set whenever a group contains one analysis unit
  - an `associated_cohort` analysis set when same-descriptor or same-co-retrieval grouping contains multiple units
- current pass entry already admits:
  - quantitative `single_item`
  - quantitative `associated_cohort`
- current pass entry currently excludes non-quantitative sets and fails closed when no admitted set exists.
- current package entry already reconciles accepted, warning, and failed pass provenance into:
  - `canonical_internal`
  - `user_facing`
  - `review_facing`
  packages without widening APS contracts or route/UI surfaces.
- current analyst-insight kernel remains a bounded deterministic helper family, not the qualitative engine itself.
- current `main` does not yet ship a qualitative single-item pass family, qualitative proof outputs, or broader qualitative route/API surfaces.
- the merged `24_L3_WB_FREEZE.md` / `26_L3_WB_INPUTS.md` packet already settles the planning-only route-family, typing minimums, owner/proof posture, and no-go boundaries for any later broader workbench lane, but it does not activate a workbench/UI lane for this qualitative slice.

## Repo-confirmed implementation-entry map
- current durable model ownership for this lane already exists in `backend/app/models/models.py` through:
  - `L3AnalysisUnit`
  - `L3AnalysisSet`
  - `L3AnalysisPlan`
  - `L3PassRun`
  - `L3OutputPackage`
- current manual migration chain `0012` through `0015` already covers the landed Layer 3 ledger/typing/pass/package persistence boundary; no new migration is admitted by default for this qualitative slice.
- current upstream owner services that a qualitative single-item slice must compose around are:
  - `backend/app/services/layer3_session_entry.py`
  - `backend/app/services/layer3_typing_entry.py`
- current downstream owner service that a qualitative single-item slice must compose into is:
  - `backend/app/services/layer3_package_entry.py`
- current quantitative `backend/app/services/layer3_pass_entry.py` is a bounded quantitative owner surface; this lane must not silently widen it unless a later freeze explicitly chooses in-place extension.
- current direct service proof pattern already lives in:
  - `backend/tests/test_layer3_session_entry.py`
  - `backend/tests/test_layer3_typing_entry.py`
  - `backend/tests/test_layer3_pass_entry.py`
  - `backend/tests/test_layer3_package_entry.py`
- current route/API/browser shells are not required owner surfaces for the first qualitative single-item slice; this lane can remain service-first.

## Exact freeze inputs
### 1. Exact operator task
- Status:
  - adopted in this branch-local planning-only packet
- Adopted operator task:
  - `Run one committed qualitative single-item pass on one qualitative analysis set after typing review and before package entry so the operator can obtain bounded qualitative findings and caveats inside the existing Layer 3 session/package chain without cross-unit synthesis.`
- Why this task is adopted here:
  - it is the narrowest honest first qualitative breadth task supported by current typing/pass/package boundaries
  - it keeps the first qualitative lane within the already-landed session, typing, and package chain
  - it avoids cohort, hybrid, comparative, and cross-modal orchestration in the first slice
- Non-adopted alternatives:
  - qualitative associated/cohort synthesis
  - hybrid single-item execution
  - comparative or cross-modal execution
  - broader route/UI operator flow in the same slice

### 2. Minimum qualitative single-item pass-family contract
- Status:
  - adopted in this branch-local planning-only packet
- Adopted minimum contract:
  - one session-scoped qualitative `single_item` pass family
  - input must be one committed `L3AnalysisSet` whose `set_type` is `single_item`
  - that set must resolve to one committed `L3AnalysisUnit` whose `analysis_modality` is `qualitative`
  - inputs come only from durable selection-manifest, material-snapshot, typing-record, analysis-unit, and analysis-set state after selection commit and typing review
  - the pass must produce one `L3PassRun` tied to one `L3AnalysisPlan` and one `analysis_set_id`
  - the pass must emit bounded qualitative result/caveat provenance that existing package-entry surfaces can reconcile without schema widening
- Adopted engine posture:
  - new Layer 3-native or future qualitative engine family
  - analyst-insight may only assist as a bounded integration/validation/helper family
  - no internal HTTP self-calls
- Adopted failure posture:
  - fail closed on missing provenance, unsupported modality, unsupported set shape, or incomplete required inputs
  - any later quarantine or partial-completion posture must be explicitly proven rather than implied from planning
- Still intentionally unresolved inside this minimum contract:
  - exact result schema
  - exact contradiction model
  - exact heuristic thresholds
  - exact checked-in versus operator-local proof artifact split
  - exact module/file names

### 3. Exact owner-surface table
- Status:
  - adopted in this branch-local planning-only packet
  - exact filenames remain implementation-local once this packet is accepted

| Concern | Exact current touchpoints | Adopted future owner class | Must stay separate from |
| --- | --- | --- | --- |
| Durable model family | `backend/app/models/models.py` (`L3AnalysisUnit`, `L3AnalysisSet`, `L3AnalysisPlan`, `L3PassRun`, `L3OutputPackage`) | existing Layer 3 model family remains the persistence owner surface | inventing a parallel browser-local or route-local qualitative persistence model |
| Migration/schema family | `backend/alembic/versions/0012_layer3_session_entry.py` through `0015_layer3_package_entry.py` | no new migration or schema owner surface is admitted by default | treating qualitative single-item prep as implicit permission to widen schema |
| Upstream session boundary | `backend/app/services/layer3_session_entry.py` | existing session-entry owner service remains authoritative for committed session/selection state | route-local or ad hoc session mutation |
| Upstream typing boundary | `backend/app/services/layer3_typing_entry.py` | existing typing/unit/set owner service remains authoritative for qualitative modality and single-item/admitted-set provenance | bypassing or rewriting typed-unit/set formation in the qualitative pass service |
| Qualitative pass contract/service family | `backend/app/services/layer3_pass_entry.py` as the current bounded quantitative owner, plus `backend/app/api/market_data_integration.py`, `backend/app/api/market_data_validation.py`, and `backend/app/api/market_insight_ai.py` as bounded helper-family touchpoints | one additive qualitative single-item contract/service/gate family under `backend/app/services/` that composes around the landed owner-service chain | silently broadening the current quantitative `layer3_pass_entry.py` slice, or treating analyst-insight helper modules as the full qualitative owner surface |
| Packaging/reconciliation boundary | `backend/app/services/layer3_package_entry.py` | existing package-entry owner surface remains authoritative for canonical/user/review package formation | a parallel qualitative-only packaging path |
| Direct proof family | `backend/tests/test_layer3_typing_entry.py`, `backend/tests/test_layer3_pass_entry.py`, `backend/tests/test_layer3_package_entry.py` | one additive qualitative direct-service proof family under `backend/tests/` | claiming qualitative lane proof from adjacent quantitative or browser-only tests |

Explicit anti-patterns:
- do not widen `layer3_pass_entry.py` by implication just because it is the current pass owner surface for quantitative execution
- do not treat route-backed analyst-insight helpers as the qualitative engine itself
- do not introduce a new frontend stack or route/UI shell as part of the first qualitative single-item slice
- do not duplicate session, typing, or package persistence logic inside the qualitative pass service

### 4. Exact proof matrix
- Status:
  - adopted in this branch-local planning-only packet

| Proof area | Current repo-backed harness or pattern to reuse | Exact later proof requirement |
| --- | --- | --- |
| Qualitative admissibility contract | `backend/app/services/layer3_typing_entry.py`, `backend/tests/test_layer3_typing_entry.py`, `backend/app/services/layer3_pass_entry.py`, `backend/tests/test_layer3_pass_entry.py` | one direct proof family showing that qualitative single-item sets are admitted only when modality/provenance rules are satisfied and fail closed otherwise |
| Qualitative pass happy path | direct service harness pattern in `backend/tests/test_layer3_pass_entry.py` | one service-first happy-path proof from finalized session through typing into one qualitative single-item pass run |
| Partial-failure or bounded-warning path | fail-closed and warning-path patterns in `backend/tests/test_layer3_pass_entry.py` and `backend/tests/test_layer3_package_entry.py` | one proof showing either fail-closed behavior or explicitly recorded bounded-warning behavior for incomplete qualitative inputs |
| Package/reconciliation preservation | `backend/app/services/layer3_package_entry.py`, `backend/tests/test_layer3_package_entry.py` | one proof showing qualitative pass outputs reconcile through the existing canonical/user/review package boundary without schema widening or APS contract widening |
| Quantitative-lane preservation | existing direct proof in `backend/tests/test_layer3_pass_entry.py` | proof that the new qualitative slice does not silently change the landed quantitative single-item or associated-cohort behavior |
| Browser/operator proof | guidance in `24_L3_WB_FREEZE.md`, `26_L3_WB_INPUTS.md`, and `11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md` | not required for the first service-first qualitative slice unless a later lane admits new operator UI; if UI is later admitted, both headed and headless Chrome proof are mandatory |

### 5. Preparation rules
- Status:
  - adopted in this branch-local planning-only packet
- Adopted preparation rules:
  - keep the first qualitative slice service-first and direct-proof-first
  - preserve the merged planning-only `24_L3_WB_FREEZE.md` / `26_L3_WB_INPUTS.md` packet as boundary context rather than as activation permission
  - preserve current package-entry and APS boundary rules; qualitative single-item execution is not permission to widen APS contracts, route/UI, runtime DB, or schema
  - preserve the rule that current review/document-trace/runtime DB surfaces remain consumer/read surfaces rather than execution state

## Recommended defaults not yet frozen
- the first qualitative slice should prefer one qualitative single-item pass family before any qualitative cohort, hybrid, comparative, or cross-modal breadth
- the qualitative lane should compose into the existing package-entry boundary rather than invent a parallel packaging layer
- route/UI should remain out of the first qualitative slice unless a separate later lane explicitly reopens them
- exact module/file names remain implementation-local even if this packet is accepted

## Exact remains-out list
- no qualitative associated/cohort synthesis
- no hybrid single-item execution
- no comparative or cross-modal breadth
- no route or UI work
- no runtime DB writes or migrations
- no schema widening
- no takeover of review/document-trace/workbench-compare/Candidate B or analyst-insight routes as the qualitative owner surface
- no replacement of the landed session, typing, or package owner-service chain
- no internal HTTP self-calls
- no promotion of package-derived context into dossier truth
- no broad qualitative-engine ambition beyond the minimum single-item slice

## Implementation-entry posture after this pass
- This branch-local packet now makes explicit:
  - one exact operator task
  - one minimum qualitative single-item pass-family contract
  - one exact owner-surface table
  - one exact proof matrix
  - one exact remains-out list
- That is enough to let a later qualitative implementation-entry packet stay narrow without guessing the first operator task, pass-family scope, owner surfaces, or no-go boundaries.
- It is not enough to claim the lane is active or live.

## Still not activation-ready
- no live qualitative single-item pass family exists on current `main`
- no exact module filenames are chosen yet
- no broader workbench or operator UI is active for this lane
- no qualitative proof outputs have been produced yet
- no implementation/status note or machine-checkable proof output exists yet for the qualitative single-item lane

## Exact non-goals
- no activation decision in this doc
- no implementation code
- no route or UI edits
- no runtime DB writes or migrations
- no schema widening
- no cohort, hybrid, comparative, or cross-modal lane activation
- no promotion of package-derived context into dossier truth

## Stop conditions
- If the operator task cannot remain single-item without immediately forcing cohort, hybrid, or comparative semantics, stop and reopen the lane choice.
- If the first qualitative slice requires route/UI, runtime DB writes, schema widening, or APS contract reopening just to stay coherent, stop and reopen those lanes separately.
- If the proposed qualitative engine posture collapses analyst-insight helpers into the full engine family, stop and restate ownership before any implementation-entry claim.

## Evidence basis for the freeze-ready subset
- primary planning:
  - `04_LAYER3_ANALYSIS_UNIT_MODALITY_AND_SET_MODEL.md`
  - `05_LAYER3_SUBLAYER2_ORCHESTRATION_AND_PASS_EXECUTION.md`
  - `06_LAYER3_ENGINE_MAP_AND_EXISTING_REPO_REUSE.md`
  - `11_LAYER3_VALIDATION_PROOF_AND_DECISION_GATES.md`
  - `12_LAYER3_ROADMAP_PHASES_AND_OPEN_QUESTIONS.md`
- current repo truth:
  - `backend/app/models/models.py`
  - `backend/app/services/layer3_session_entry.py`
  - `backend/app/services/layer3_typing_entry.py`
  - `backend/tests/test_layer3_typing_entry.py`
  - `backend/app/services/layer3_pass_entry.py`
  - `backend/tests/test_layer3_pass_entry.py`
  - `backend/app/services/layer3_package_entry.py`
  - `backend/tests/test_layer3_package_entry.py`
  - `docs/analyst_insight/analyst_insight_status_handoff.md`
