# 06D Critical Blocker Validation Set

## Purpose

Prioritize the small subset of validation surfaces that should be treated as immediate blockers for any selector/bootstrap work.

## Critical blocker set

### Category A — Test-verified blockers (B1–B6)

Each of these has one or more verified test files that must pass under the canonical acceptance convention (see `06K`).

#### B1 -- Owner behavior
- `tests/test_nrc_aps_document_processing.py`

Why:
- protects core process_document behavior,
- protects visual-lane classification/integration,
- protects OCR fallback strictness.

#### B2 -- Artifact behavior
- `backend/tests/test_visual_artifact_pipeline.py`

Why:
- directly exercises artifact existence, hashing, metadata, and roundtrip persistence.

Current operational caveat:
- the live file is currently a script-style probe with `main()`, not a pytest-collected module under the canonical acceptance command
- treat artifact behavior as a verified surface whose harness still needs reconciliation, not as a cleanly executed grouped pytest gate

#### B3 -- Config-path behavior
- `backend/tests/test_nrc_aps_run_config.py`

Why:
- protects the repo-native control path most likely to carry selector activation later.

#### B4 -- Runtime-root discovery
- `backend/tests/test_review_nrc_aps_catalog.py`

Why:
- protects summary-backed candidate-run discovery under the allowlisted `lc_e2e` review roots
- protects stable default-run selection once candidate runs are discovered

#### B5 -- Diagnostics persistence safety
- `backend/tests/test_diagnostics_ref_persistence.py`

Why:
- protects cross-run diagnostics-ref correctness and serializer safety.

#### B6 -- Run-scoped review-root / runtime DB access
- `backend/tests/test_review_nrc_aps_document_trace_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_service.py`
- `backend/tests/test_review_nrc_aps_runtime_db.py`

Why:
- protects run-scoped review-root resolution
- protects read-only runtime DB access against audited `lc_e2e` data
- protects path safety and run-bound trace payload access on review surfaces

Current operational caveat:
- in this clean worktree, review/runtime validation requires explicit read-only `STORAGE_DIR` pointing at the shared audited runtime root
- shared runtime `20260331_101919` is summary-marked passed but contains no `aps_content_*` rows, leaving one multi-runtime document-selector failure that appears fixture-quality rather than selector-path-related

### Category B — Planning-closed blockers (B7–B8)

Each of these is a planning-verified blocker requirement. Implementation must produce explicit visibility controls or test coverage before these can be marked implementation-closed. Planning closure alone is not sufficient.

#### B7 -- Review/catalog/report/API visibility
- No single test file; verified via live code analysis of `review_nrc_aps_catalog.discover_candidate_runs()`, `review_nrc_aps.py` run-bound endpoints, and `nrc_aps_evidence_report*.py` run-bound persistence into `run.query_plan_json`.

Current status: **planning-closed as a blocker requirement; not yet implementation-closed.**

Why:
- separate runtime or artifact roots do not guarantee invisibility
- baseline-facing selectors, run-bound endpoints, and shared run-bound report/export persistence can still expose or incorporate experiment runs
- review/catalog/API visibility and report/export run visibility are both directly verified as blocker-level concerns

#### B8 -- Review API exposure
- No single test file; verified via live code analysis of `backend/app/api/review_nrc_aps.py` endpoints.

Current status: **planning-closed as a blocker requirement; not yet implementation-closed.**

Why:
- if baseline-facing API endpoints can expose experiment-derived artifacts/diagnostics/text/chunks/trace, then "out-of-band" remains overstated even if runtime roots are separated.

## Governing rule

If any future selector/bootstrap proposal cannot state how it preserves **all of B1 through B8**, it is not strict enough to proceed.

### Status interpretation
- **Category A (B1–B6):** Test-verified. Each has one or more verified test files that must pass under the canonical acceptance convention (see `06K`).
- **Category B (B7–B8):** Planning-closed only. Each requires implementation-produced visibility controls or test coverage before it can be marked implementation-closed. Planning closure alone is not sufficient.
