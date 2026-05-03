# NRC APS UI Launch Runbook

## Purpose

This document is the canonical root-repo runbook for launching the shipped NRC APS UI surfaces from a valid repo checkout or worktree against an explicit local review runtime.

Use it when you need to:

- bind the backend to a specific review runtime intentionally
- start the backend for local UI use on a known port
- prove that the UI is pointed at the intended runtime before trusting what it shows
- open the shipped review, document-trace, workbench-compare, and Candidate B Trace surfaces

This runbook defines the launch contract.
It is not the same thing as the broader manual validation guide, and it is not the same thing as populated Workbench Compare prep.

## Authority Role

This file is the authoritative operator doc for NRC APS UI bring-up on current `main`.

Implementation authority still lives in:

- [backend/main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py)
- [backend/app/api/review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)
- [backend/app/core/config.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/core/config.py)
- [backend/app/services/review_nrc_aps_runtime.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime.py)
- [backend/app/services/review_nrc_aps_runtime_roots.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime_roots.py)
- [backend/app/services/review_nrc_aps_catalog.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_catalog.py)
- [backend/app/services/review_nrc_aps_workbench_compare.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_workbench_compare.py)
- [backend/app/review_ui/static/review.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/review.js)
- [backend/app/review_ui/static/document_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.js)
- [backend/app/review_ui/static/workbench_compare.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/workbench_compare.js)
- [backend/app/review_ui/static/candidate_b_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/candidate_b_trace.js)
- [tools/nrc_ui_launch.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/tools/nrc_ui_launch.py)

## Scope

This runbook covers:

- review UI launch
- document-trace UI launch
- workbench-compare shell bring-up
- Candidate B Trace route bring-up
- explicit runtime binding
- minimum trust checks before UI use

This runbook does not cover:

- generating a new review runtime as part of the launch pass
- populated Workbench Compare prep
- broader manual operator validation
- browser regression harness execution
- generic API startup when explicit review-runtime binding does not matter

## Worktree-Portability Rules

This runbook is written to work from the root of any valid repo checkout or worktree.

Treat these values as inputs:

- `repo_root`
- `port`

The canonical launch flow below resolves the runtime details for you and prints:

- `run_id`
- `review_root`
- `runtime_root`
- `selection_storage_root`
- `database`
- `storage`

Do not hardcode one worktree name as authority.

## Review Runtime Preconditions

Before launch, confirm all of the following:

- you are in the root of the repo checkout or worktree you intend to serve from
- a local review runtime already exists on disk
- the chosen runtime contains:
  - `local_corpus_e2e_summary.json`
  - `lc.db`
  - `storage\`
- the summary is `aps.local_corpus_e2e_summary.v1`
- the chosen port is free

Important current-main note:

- a clean `project6-origin/main` checkout does not guarantee that a populated review runtime is already present
- if you are serving from a worktree, the helper below can also use the shared repo-root review-runtime root when it exists
- if no reviewable runtime is available from the helper's discovery roots, stop here and create or restore one first

If you need to create a fresh isolated local-corpus runtime, use [local_corpus_e2e_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/local_corpus_e2e_runbook.md) first.

## Allowlisted Review Runtime Roots

Current launch discovery looks for summary-backed review runtimes under:

- `.\backend\app\storage_test_runtime\lc_e2e`
- `.\backend\storage_test_runtime\lc_e2e`
- when launched from a worktree, the shared repo-root `backend\app\storage_test_runtime\lc_e2e` via explicit `STORAGE_DIR` binding

The launch flow below assumes the runtime you want to use is reachable from one of those roots.

## Step 1: Discover A Runtime

From the repo or worktree root, run this exact command:

```text
python ./tools/nrc_ui_launch.py discover
```

This is shell-neutral: the same command works unchanged in PowerShell and `cmd`.

The helper prints the launchable run list and marks the current default selection with `selected=true`.

## Step 2: Bind The Runtime Explicitly

The canonical copy-paste path is to launch the current default selection on the default local port `8098`:

```text
python ./tools/nrc_ui_launch.py serve --latest
```

Binding rules:

- `DATABASE_URL` points to the selected runtime's `lc.db`
- `STORAGE_DIR` points to the selected review-runtime root/search root, such as `...\storage_test_runtime`, not the per-run `storage\` directory
- `DB_INIT_MODE` must be `none`

Before `uvicorn` starts, the helper prints:

- `run_id`
- `review_root`
- `runtime_root`
- `selection_storage_root`
- `database`
- `storage`
- `base_url`

Important:

- keep this terminal open while using the UI
- this helper-backed launch path is the canonical operator path for review-runtime bring-up
- [project6.ps1](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/project6.ps1) `-Action start-api` is useful for generic API startup, but it is not the canonical path when you need explicit review-runtime binding
- [tools/start-review-api.ps1](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/tools/start-review-api.ps1) remains a PowerShell-only wrapper; it uses the same shared-root/worktree-local runtime discovery posture as the Python helper and still accepts an explicit `-RuntimeRoot` override

If you need a specific discovered run instead of the default latest one, use:

```text
python ./tools/nrc_ui_launch.py serve --run-id <RUN_ID>
```

That variant is intentionally parameterized. The `--latest` command above is the copy-pasteable default path.

## Step 3: Confirm Runtime Trust Before Using The UI

In a second terminal, run this exact command:

```text
python ./tools/nrc_ui_launch.py verify --latest
```

Fail closed if:

- `/health` is not `ok`
- the review run list is empty when you expected a populated runtime
- the discovered/default run does not match the runtime the helper selected for launch

Do not trust the UI until these checks make sense.

## Step 4: Print The Shipped UI Routes

In any terminal, run:

```text
python ./tools/nrc_ui_launch.py urls
```

By default this prints the route URLs for `127.0.0.1:8098`.

## Step 5: Open The Shipped UI Routes

Main review UI:

- [http://127.0.0.1:8098/review/nrc-aps](http://127.0.0.1:8098/review/nrc-aps)

Document Trace:

- [http://127.0.0.1:8098/review/nrc-aps/document-trace](http://127.0.0.1:8098/review/nrc-aps/document-trace)

Workbench Compare:

- [http://127.0.0.1:8098/review/nrc-aps/workbench-compare](http://127.0.0.1:8098/review/nrc-aps/workbench-compare)

Candidate B Trace:

- `http://127.0.0.1:8098/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=<BUNDLE_ID>&fixture_id=<FIXTURE_ID>`

Optional direct Document Trace route:

- `http://127.0.0.1:8098/review/nrc-aps/document-trace?run_id=<RUN_ID>`

Important:

- the numbered launch steps above are copy-pasteable as written
- the optional direct-route examples here are URL templates, not launch commands

## Step 6: Minimum In-Browser Checks

On `/review/nrc-aps`:

- the page shell loads
- the run selector is populated
- the selected/default run is reviewable

On `/review/nrc-aps/document-trace`:

- the page shell loads
- the run selector is populated
- the document selector loads for a valid run

On `/review/nrc-aps/workbench-compare`:

- the page shell loads
- the page fails clearly if compare sources are not prepared

On `/review/nrc-aps/candidate-b-trace`:

- valid query params load the page
- missing required query params fail clearly

## Critical Distinctions

### Launchable vs trustworthy

A running `uvicorn` process is not enough.
Trust starts after `/health` and `/api/v1/review/nrc-aps/runs` confirm the intended runtime.

### Launch authority vs smoke walkthrough

This file is the launch authority.
[nrc_aps_review_ui_startup_and_smoke_test.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md) remains a concise walkthrough layered on top of this contract.

### Shell-neutral commands vs parameterized follow-up checks

The numbered launch steps in this file are designed to run as-is in PowerShell and `cmd`.
Commands or URLs that still contain `<RUN_ID>`, `<TARGET_ID>`, `<BUNDLE_ID>`, or `<FIXTURE_ID>` are intentionally parameterized follow-up checks, not the canonical launch path.

### Shell reachability vs populated compare validation

This runbook covers bringing up the compare page shell.
Use [wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md) for same-checkout prep and populated compare plus Candidate B Trace validation.

### Runtime truth vs bundle-scoped Candidate B evidence

Candidate B Trace remains a separate bundle-scoped inspection surface.
It does not widen the normal review runtime model.

## Relationship To Other Docs

After this runbook:

- use [frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md) for the concise bring-up walkthrough
- use [frontend_UI_plans/wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md) for same-checkout prep and populated compare validation
- use [frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md) for the broader manual validation pass
- use [nrc_aps_status_handoff.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_status_handoff.md) for live merged-main posture
- use [nrc_aps_authority_matrix.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_authority_matrix.md) if documentation surfaces conflict

## Non-Goals

This runbook must not become:

- a planning/spec artifact
- a donor-runtime migration guide
- a proof report
- a browser regression harness guide
- a catch-all validation document

Its job is narrower:
define the canonical, portable launch path for the shipped NRC APS UI surfaces.
