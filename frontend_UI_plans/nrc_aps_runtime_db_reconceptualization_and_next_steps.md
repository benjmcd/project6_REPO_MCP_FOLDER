# NRC APS Runtime DB Reconceptualization And Next Steps

## Purpose

This document captures the current repo-confirmed DB situation for the NRC APS review and Document Trace surfaces, disregarding `/review/market-pipeline` except where shared startup or routing still affects the same backend process.

This is a planning and decision document. It is not an implementation spec for a single patch and it is not a generic database-optimization memo.

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

For the already-frozen but not-yet-mainlined runtime-switching plus bbox-overlay work, the authority is:

- branch `codex/review-ui-runtime-switching-bbox`
- commit `f3d03b3d`

That branch is real evidence for the preferred direction, but it is not the current `main` baseline.

## Repo-Confirmed Current State

### 1. There are two different DB realities

The repo currently mixes:

- one mutable app database configured by `DATABASE_URL`
- many immutable local-corpus runtime databases under `backend/app/storage_test_runtime/lc_e2e/*/lc.db`

This is not theoretical. It is visible in:

- [config.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/core/config.py), which binds one process-global `database_url`
- [session.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/db/session.py), which creates one global `engine` and one global `SessionLocal`
- [review_nrc_aps_runtime.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime.py), which separately discovers summary-backed runtime roots on disk

### 2. Current `main` still treats review/document-trace as global-DB consumers

On current `main`, the review endpoints still use the process-global session through `Depends(get_db)` in:

- [review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)

and `get_db()` itself comes from:

- [deps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/deps.py)

which yields a session from the one global `SessionLocal`.

That means current `main` still has a structural mismatch:

- runtime discovery is filesystem-driven by `run_id`
- trace data resolution still assumes one process-global DB

### 3. The frozen side branch already proves the direction

The branch:

- `codex/review-ui-runtime-switching-bbox`

contains the already-frozen review/document-trace runtime-switching work and bbox overlay restoration. It demonstrates the preferred architectural direction:

- review/document-trace routes should resolve runtime state by `run_id`
- runtime-backed DB access should not be locked to the global app DB session

### 4. The biggest DB risk is not scale, it is identity and authority

The most important immediate DB risks are:

- wrong runtime binding because `.env` or startup defaults point at the wrong DB/storage pair
- accidental migration of a runtime snapshot DB because [main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py) runs migrations unless `DB_INIT_MODE=none`
- stale assumptions that `/review/nrc-aps` is backed by one canonical DB when the review artifacts actually live per runtime

### 5. Performance is secondary to correct binding

There are real query and schema issues, but they are not the first priority:

- [review_nrc_aps_document_trace.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_document_trace.py) issues repeated run/target/content queries and broad extracted-unit loads
- [models.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/models/models.py) stores `visual_page_refs_json` as `Text` in APS tables
- APS tables rely mostly on unique constraints and do not express many targeted read indexes in the model layer

Those are real future work items, but they are less urgent than making runtime binding explicit and safe.

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

### Phase 1: Mainline The Frozen Runtime-Switching Review Work

Objective:

- promote the `codex/review-ui-runtime-switching-bbox` direction onto `main`

Why first:

- the preferred architecture already exists in a frozen form
- continuing to build new review/document-trace features on old `main` semantics would compound debt
- this is the narrowest way to align `main` with the intended runtime-centric review model

Acceptance criteria:

- current `main` review/document-trace behavior matches the frozen branch direction
- bbox overlays remain present
- runtime switching works without restart

### Phase 2: Formalize Runtime DB Resolution As A First-Class Contract

Objective:

- make runtime-backed DB/session resolution explicit in the review/document-trace backend

Required outcomes:

- `run_id` resolves to:
  - review root
  - runtime DB path
  - runtime storage root
- review/document-trace routes stop depending conceptually on the control-plane global DB for runtime evidence reads
- the runtime DB contract is visible and testable

Acceptance criteria:

- review/document-trace reads are per-runtime by contract
- a wrong global app DB binding no longer silently changes review truth for the selected runtime

### Phase 3: Add Runtime DB Safety Rails

Objective:

- prevent accidental corruption or ambiguity when serving runtime-backed review surfaces

Required outcomes:

- no automatic migration against runtime snapshot DBs
- explicit schema/version compatibility checks before opening a runtime DB
- runtime DB access treated as read-only
- an explicit way to introspect or log the effective runtime DB/storage binding used for review requests

Acceptance criteria:

- review startup/validation can prove the exact DB/storage pair in use
- runtime DB misuse fails closed

### Phase 4: Improve Review/Document-Trace Transparency

Objective:

- make runtime identity and state clearer in the frontend/UI

Examples:

- stronger run labels
- clearer current-run/current-target identity
- explicit empty/missing/not-reviewable messaging
- clearer trace-state communication when source, diagnostics, chunks, or extracted units are absent

Acceptance criteria:

- switching runs/documents does not leave stale ambiguity in the UI
- operators can tell what runtime they are viewing without checking server startup history

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
- the best review/document-trace direction is frozen on `codex/review-ui-runtime-switching-bbox`
- there is unrelated dirty/untracked work in the repo, including market-pipeline-related files

Therefore:

- further review/document-trace work should start from the frozen branch direction, not from generic `main`
- `/review/market-pipeline` should be ignored as a product driver unless shared startup or routing must be disentangled for review safety

## Immediate Recommended Action Tree

### 1. Verification Step

Diff current `main` review/document-trace surfaces against:

- branch `codex/review-ui-runtime-switching-bbox`

and confirm the exact promotion set needed to mainline the runtime-switching plus bbox work.

### 2. If Verification Passes

Make the next implementation pass a bounded mainline-promotion plus safety-rail pass:

- promote the branch work
- formalize runtime DB resolution
- add runtime DB safety/binding introspection where needed

### 3. If Verification Fails

If the branch and `main` have drifted too far for a narrow promotion, stop and produce a reconciliation plan rather than patching incrementally on old `main` assumptions.

## Residual Risks

- branch-to-main drift may be larger than expected
- current startup still couples migrations to the configured `DATABASE_URL`
- runtime DB schema compatibility across older snapshots may not be uniform
- review/document-trace tests can prove route behavior, but browser validation still matters for runtime switching and bbox continuity

## Bottom Line

The next implementation should not be "optimize the DB" in the abstract.

The next implementation should be:

1. land the frozen runtime-switching plus bbox review work on `main`
2. formalize runtime DB identity and routing
3. add safety rails around runtime DB use
4. only then do targeted UI/data-path improvements
