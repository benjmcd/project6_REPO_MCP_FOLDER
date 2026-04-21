# NRC APS Runtime DB Reconceptualization And Next Steps

## Purpose

This document captures the current repo-confirmed DB situation for the NRC APS review and Document Trace surfaces, disregarding `/review/market-pipeline` except where shared startup or routing still affects the same backend process.

This is a planning and decision document. It is not an implementation spec for a single patch and it is not a generic database-optimization memo.
It now reflects current `main` after the runtime-centric review/document-trace shift and the landed runtime DB safety rails.

## Canonical Source Of Truth

For the current live implementation on `main`, the primary authority is:

- [backend/app/core/config.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/core/config.py)
- [backend/app/db/session.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/db/session.py)
- [backend/app/api/deps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/deps.py)
- [backend/app/api/review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)
- [backend/app/services/review_nrc_aps_catalog.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_catalog.py)
- [backend/app/services/review_nrc_aps_runtime.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime.py)
- [backend/app/services/review_nrc_aps_document_trace.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_document_trace.py)
- [backend/app/models/models.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/models/models.py)
- [backend/main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py)

Historical reference only:

- branch `codex/review-ui-runtime-switching-bbox`
- commit `f3d03b3d`

That branch is real historical evidence for an earlier runtime-switching direction, but it is not current `main` authority and must not be treated as directly promotable as-is.

## Repo-Confirmed Current State

### 1. There are two different DB realities

The repo currently mixes:

- one mutable app database configured by `DATABASE_URL`
- many immutable local-corpus runtime databases under `backend/app/storage_test_runtime/lc_e2e/*/lc.db`

This is not theoretical. It is visible in:

- [config.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/core/config.py), which binds one process-global `database_url`
- [session.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/db/session.py), which creates one global `engine` and one global `SessionLocal`
- [review_nrc_aps_runtime.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime.py), which separately discovers summary-backed runtime roots on disk

### 2. Current `main` now routes review/document-trace through runtime DB sessions

On current `main`, the review/document-trace routes use the runtime DB helper in:

- [review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)
- [review_nrc_aps_runtime_db.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime_db.py)

Current live behavior now includes:

- review/document-trace route handlers open runtime-scoped sessions through `runtime_db_session_for_run(run_id)`
- runtime DBs open read-only via SQLite URI `mode=ro`
- required review/document-trace tables are validated before a session is yielded
- the runtime DB/session contract is directly tested in `backend/tests/test_review_nrc_aps_runtime_db.py`

The process-global app DB still exists for the control plane, but the review/document-trace consumption plane no longer depends on it for runtime evidence reads.

### 3. The frozen side branch is historical only

The branch:

- `codex/review-ui-runtime-switching-bbox`

contains an earlier runtime-switching and bbox-overlay snapshot. It still has evidentiary value for historical direction, but it is stale relative to current `main` and is not a safe promotion target now.

Use current `main` as authority first and consult that branch only if a narrowly scoped historical comparison is actually needed.

### 4. The biggest DB risk is not scale, it is identity and authority

The most important immediate DB risks are:

- wrong runtime binding because `.env` or startup defaults point at the wrong DB/storage pair
- accidental migration of a runtime snapshot DB because [main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py) runs migrations unless `DB_INIT_MODE=none`
- stale operator or docs assumptions about which runtime DB/storage pair is actually being viewed

### 5. Performance is secondary to correct binding

There are real query and schema issues, but they are not the first priority:

- [review_nrc_aps_document_trace.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_document_trace.py) issues repeated run/target/content queries and broad extracted-unit loads
- [models.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/models/models.py) stores `visual_page_refs_json` as `Text` in APS tables
- APS tables rely mostly on unique constraints and do not express many targeted read indexes in the model layer

Those are real future work items, but they are less urgent than making runtime identity and operator visibility clearer.

## Reconceptualized Model

The NRC APS review system should be treated as three planes:

### 1. Control Plane

The mutable operational application DB:

- connector execution state
- general app tables
- operational workflows

This remains bound by `DATABASE_URL` and the global `SessionLocal`.

### 2. Evidence Plane

Per-run immutable local-corpus runtime snapshots:

- `lc.db`
- `storage`
- `local_corpus_e2e_summary.json`
- runtime review artifacts

These should be treated as read-only evidence surfaces, not as interchangeable with the control-plane DB.

### 3. Consumption Plane

The review/document-trace UI and API:

- `/review/nrc-aps`
- `/review/nrc-aps/document-trace`
- `/api/v1/review/nrc-aps/...`

This plane should be runtime-centric and keyed by `run_id`, not globally DB-centric.

## What Should Come Next

### Landed Foundation On Current `main`

The following are already landed on current `main` and should no longer be treated as future promotion work:

- runtime-centric review/document-trace route binding by `run_id`
- explicit runtime DB path and storage-dir resolution
- read-only runtime DB access
- runtime DB required-table compatibility checks
- direct test coverage for runtime DB session safety rails
- operator-safe runtime binding summaries in the review run catalog and compare run sources
- runtime, DB, and storage authority labeling in the shipped review and document-trace identity surfaces
- selected-source authority labeling in the shipped workbench compare identity surface and compare-unavailable overlay path

### Phase 4: Review/Document-Trace Transparency Is Now Landed

Current landed scope:

- review exposes runtime, DB, and storage authority in the run identity bar
- document trace exposes runtime, DB, and storage authority in the identity summary for the selected run/target
- workbench compare exposes baseline runtime, Candidate A runtime, and Candidate B source authority in the identity summary
- compare-unavailable state now carries selected-source authority instead of leaving runtime provenance implicit

Verification result:

- headed Chrome and headless Chrome now both show matching runtime identity on the runtime-backed review/document-trace surfaces
- headed Chrome and headless Chrome now both show matching selected-source authority on the runtime-backed compare-unavailable path
- the compare-available identity band is browser-proved in the repo's fixture-backed review-browser harness, not inferred from static tests alone
- operators can now tell what runtime they are viewing without checking server startup history

### Phase 5: Optimize Document Trace Data Paths

Objective:

- improve the actual query/data path once runtime identity is correct

Likely targets:

- page-scoped extracted-unit loading where justified
- reducing repeated run/target/content lookups
- targeted indexes only after query evidence justifies them
- medium-term cleanup of `visual_page_refs_json` if visual-page metadata becomes query-critical

Acceptance criteria:

- optimizations are evidence-driven
- no new second state/fetch/cache path is introduced without clear need

## What Should Explicitly Wait

The following should not drive the next step:

- generic Redis/caching work
- sharding/read-replica planning
- broad raw-SQL rewrites
- market-pipeline-driven backend structure
- generic DB "modernization" not tied to the NRC APS review/runtime model

Those may become relevant later, but they are not the narrowest correct next move.

## Guidance On The Current Dirty Repo State

Current repo reality should shape implementation sequencing:

- `main` remains the current live baseline
- there is unrelated dirty/untracked work in the repo, including market-pipeline-related files

Therefore:

- further review/document-trace work should start from the shipped current-`main` posture, not from stale branch-era assumptions
- `/review/market-pipeline` should be ignored as a product driver unless shared startup or routing must be disentangled for review safety

## Immediate Recommended Action Tree

### 1. Verification Result On Current `main`

The runtime-identity clarity gate has now been rerun against current `main`.

Verified operator-visible facts:

- which runtime is selected
- which target/document is selected
- which runtime DB/storage pair is authoritative for the current view
- why a compare surface is unavailable when Candidate B source coverage is incomplete

Scope boundary:

- runtime-backed browser proof covered review, document trace, and compare-unavailable
- fixture-backed browser proof covered the compare-available identity band

### 2. Default Next Step

Stop and do not open another lane from this document by default.

### 3. Reopen Rule

Only reopen a bounded follow-up if:

- a new browser/operator repro proves remaining runtime-identity ambiguity, or
- measured evidence justifies the Phase 5 data-path optimization work

## Residual Risks

- current startup still couples migrations to the configured `DATABASE_URL`
- runtime DB schema compatibility across older snapshots may not be uniform
- review/document-trace tests can prove route behavior, but browser validation still matters for runtime identity clarity and bbox continuity

## Bottom Line

The next implementation should not be "optimize the DB" in the abstract.

Current `main` now has the runtime-centric shift and the bounded transparency pass.

The next implementation, if a real gap is later proven, should be:

1. keep current `main` as the authority baseline
2. avoid reopening transparency work unless a concrete browser/operator ambiguity is reproduced
3. only then do targeted data-path optimization if measured evidence justifies it
