# 03L Runtime DB Binding and Isolation Policy

## Verified live evidence

`backend/app/services/review_nrc_aps_runtime.py` defines:
- allowlisted `lc_e2e` review-root discovery
- summary-backed review-root resolution by run via `find_review_root_for_run(...)`

`backend/app/services/review_nrc_aps_runtime_roots.py` defines:
- `candidate_review_runtime_roots(...)`
- deterministic review-runtime root candidates under app/backend `storage_test_runtime/lc_e2e`
- optional explicit root reuse via `STORAGE_DIR`

`backend/app/services/review_nrc_aps_runtime_db.py` defines:
- `runtime_db_session_for_run(...)`
- `runtime_db_session_for_binding(...)`
- `get_runtime_binding_for_run(...)`
- schema/read-only runtime DB safety rails

`backend/tests/test_review_nrc_aps_document_trace_api.py` and
`backend/tests/test_review_nrc_aps_document_trace_service.py` verify:

- run-scoped review-root resolution for audited runs
- read-only SQLAlchemy access against an audited runtime DB under `.../storage_test_runtime/lc_e2e/...`
- path safety and missing-layer behavior for run-bound trace payloads

`backend/tests/test_review_nrc_aps_runtime_db.py` verifies:
- explicit runtime DB resolution for known runs
- read-only session behavior
- invalid/missing path rejection
- schema compatibility validation

`backend/tests/test_review_nrc_aps_details.py`,
`backend/tests/test_review_nrc_aps_tree.py`, and
`backend/tests/test_review_nrc_aps_graph.py` also fail if `find_review_root_for_run(...)` stops resolving audited runs.

Validated operational note:
- this clean worktree does not carry its own `backend/app/storage_test_runtime/lc_e2e` tree
- clean-worktree review/runtime validation now auto-aligns read-only to the shared audited runtime root through `backend/tests/review_nrc_aps_runtime_fixture.py`
- grouped T8 review/runtime acceptance currently passes under the canonical repo-root `pytest` posture without seeding new runtime data

## Current policy

Run-scoped review-root resolution and audited runtime DB access behavior are baseline-locked in the first integrated selector pass.

## Why

Even if selector changes are local to PDF visual-lane logic, review/runtime tooling still depends on stable run-to-review-root resolution, safe in-root path handling, and read-only runtime DB access for audited runs.

## First-pass rule

Do not change:
- how a run resolves to a review root,
- the allowlisted `lc_e2e` discovery bases used by review/runtime lookup,
- read-only expectations for runtime DB sessions used by run-bound review/document-trace flows,
- path-safety guarantees that keep resolved artifacts inside the review root,
- or validate by seeding/generating new runtime data just to satisfy review/runtime tests.

## Experimental policy

Experimental runs must remain out-of-band from default baseline review-root discovery and audited runtime DB access unless and until a later explicit decision reopens that scope.
