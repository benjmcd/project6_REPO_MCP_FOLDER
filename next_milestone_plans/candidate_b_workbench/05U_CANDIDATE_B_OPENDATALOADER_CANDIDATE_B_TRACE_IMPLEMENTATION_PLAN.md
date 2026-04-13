# 05U - Candidate B OpenDataLoader Candidate B Trace Implementation Plan

## Purpose

Define the narrowest justified implementation lane for a separate Candidate B inspection surface after the compare surface has landed on `main`.

Status note:

- this document froze the Candidate B Trace lane before implementation
- current branch code now implements that additive lane without widening runtime admission or the existing single-run `document-trace` contract

The gap this lane closed was that the compare page could compare Candidate B summaries,
but could not yet open an ODL-native inspection surface for the selected Candidate B fixture.

---

## Canonical source of truth

Use these files as authority before editing:

- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tools/run_nrc_aps_candidate_b_compare.py`
- `backend/app/services/review_nrc_aps_workbench_compare.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/main.py`
- `frontend_UI_plans/wb-compare-spec.md`
- `frontend_UI_plans/wb-compare-blueprint.md`
- `next_milestone_plans/candidate_b_workbench/04D_CANDIDATE_B_OPENDATALOADER_ANNOTATED_PDF_AND_INSPECTION_ARTIFACT_CONTRACT.md`

---

## Product goal

Add a read-only Candidate B-specific inspection page that lets an operator inspect ODL-native artifacts for one selected bundle-backed fixture, especially:

- the annotated PDF
- the raw JSON structure output
- the raw Markdown output
- the bundle-level summary and warning posture for that fixture

This lane is meant to complement Workbench Compare,
not replace it.

---

## Architecture decision

Implement the inspection surface as a separate additive page and API family.

Do not:

- widen `document-trace` into a Candidate B page
- add Candidate B to the normal review run selector
- add a Candidate B `visual_lane_mode`
- thread Candidate B through `runtime_db` as if it were a current review runtime

Candidate B remains bundle-scoped in the first inspection pass.

---

## Frozen product identity

Product name:

- `Candidate B Trace`

Page route:

- `/review/nrc-aps/candidate-b-trace`

Canonical page identity:

- `candidate_b_bundle_id + fixture_id`

Query parameters:

- `candidate_b_bundle_id`
- `fixture_id`
- optional `tab`

No additional query parameters in the first pass.

---

## Frozen page model

The first pass page must use tabs:

- `annotated_pdf`
- `summary`
- `raw_json`
- `raw_markdown`

Default tab policy:

- if the annotated PDF is present, default to `annotated_pdf`
- otherwise default to `summary`

This page is deep-link oriented.
Do not add a new top-level header nav item for it in the first pass.

---

## Frozen compare-surface integration decision

Workbench Compare follow-on changes are limited to:

- add `candidate_b_trace` to the compare manifest deep-link contract
- add a Candidate B column `deep_link` pointing at the Candidate B Trace page

Do not change:

- baseline trace links
- Candidate A trace links
- compare target identity
- compare tab semantics

The Candidate B compare column may link to the Candidate B Trace page without trying to map compare tabs 1:1 onto Candidate B Trace tabs in the first pass.

---

## Frozen classification decision

Do **not** modify `backend/app/services/review_nrc_aps_runtime.py` in the first inspection pass.

Why:

- Candidate B is still bundle-based rather than runtime-root based
- forcing it into the current `visual_lane_mode` family would widen runtime semantics without need
- the required classification for this lane is already expressible at the compare/inspection layer through:
  - `variant_id = "candidate_b"`
  - bundle-scoped identity

If true runtime admission is ever desired later,
that must be a separate explicitly reopened lane.

---

## Planned area of effect

### 1. Candidate B output generation and retention

- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tools/run_nrc_aps_candidate_b_compare.py`
- `next_milestone_plans/candidate_b_workbench/09A_CANDIDATE_B_OPENDATALOADER_OUTPUT_ISOLATION_RETENTION_AND_EVENT_REGISTRY.md`

Responsibilities:

- request annotated PDF output from ODL
- canonicalize it to `raw/annotated/<fixture_id>.pdf`
- record the new artifact refs in bundle outputs
- preserve existing compare bundle shape

### 2. Compare deep-link surface

- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_workbench_compare.py`
- `backend/app/review_ui/static/workbench_compare.js`
- `backend/tests/test_review_nrc_aps_workbench_compare_api.py`
- `backend/tests/test_review_nrc_aps_workbench_compare_service.py`
- `backend/tests/test_review_nrc_aps_workbench_compare_page.py`

Responsibilities:

- add `candidate_b_trace` to compare manifest deep links
- populate Candidate B column deep links
- preserve current baseline/Candidate A deep-link behavior

### 3. Candidate B Trace backend surface

- `backend/main.py`
- `backend/app/api/review_nrc_aps.py`
- new `backend/app/services/review_nrc_aps_candidate_b_trace.py`
- `backend/app/schemas/review_nrc_aps.py`

Additive API routes:

- `/candidate-b-trace/manifest`
- `/candidate-b-trace/annotated-pdf`
- `/candidate-b-trace/raw-json`
- `/candidate-b-trace/raw-markdown`

All of those routes remain read-only.

### 4. Candidate B Trace frontend surface

Add new static files:

- `backend/app/review_ui/static/candidate_b_trace.html`
- `backend/app/review_ui/static/candidate_b_trace.css`
- `backend/app/review_ui/static/candidate_b_trace.js`

Reuse shared review tokens from:

- `backend/app/review_ui/static/review.css`

Do not widen:

- `document_trace.html`
- `document_trace.css`
- `document_trace.js`

### 5. Tests

Add:

- `backend/tests/test_review_nrc_aps_candidate_b_trace_api.py`
- `backend/tests/test_review_nrc_aps_candidate_b_trace_service.py`
- `backend/tests/test_review_nrc_aps_candidate_b_trace_page.py`

Update compare tests only as needed for the new deep-link fields.

---

## Path-safety and trust-boundary rules

The inspection lane must reuse the same bundle validation posture already frozen for Workbench Compare:

- public `candidate_b_bundle_id` stays POSIX-style checkout-relative
- the backend must revalidate it to an exact discovered allowlisted bundle root
- the browser must never supply raw artifact paths directly

For raw artifact serving:

- the service must read the per-fixture refs from validated bundle metadata
- then resolve them against checkout root
- then reject if the resolved path is outside the validated run-scoped raw root

Do not rely on checkout-root containment alone.

---

## Non-goals

Do not use this lane to:

- add Candidate B to the run selector
- add Candidate B to `discover_candidate_runs()`
- change `document-trace` query semantics
- change `document-trace` API payloads
- persist Candidate B artifacts into runtime DB tables
- widen Candidate B into evidence/report/export/context families
- make the compare page render full PDFs inline

---

## Expected follow-through after implementation

Minimum doc sync:

- `frontend_UI_plans/README.md`
- `frontend_UI_plans/wb-compare-spec.md`
- `frontend_UI_plans/wb-compare-blueprint.md`
- `frontend_UI_plans/wb-compare-validation.md`
- `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md`
- `frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md`
- this Candidate B planning pack

The compare docs should remain current for shipped behavior while clearly recording that Candidate B trace is now a separate additive follow-on surface rather than a retrofit of `document-trace`.
