# NRC APS Review UI Startup And Smoke Test

## Purpose

This document is the concise operational walkthrough for bringing up the NRC APS review UI, the separate Document Trace UI, and the separate Workbench Compare UI against an explicit local runtime on a chosen port.

Use this when you need to:

- start the backend with a known `DATABASE_URL` and `STORAGE_DIR`
- avoid accidental fallback to `backend/.env`
- open the review UI in a browser
- open the Document Trace UI for a specific run
- open the Workbench Compare UI after same-checkout compare-source prep
- switch between discovered summary-backed review runtimes from the UI without restarting the backend
- confirm the basic frontend/API path is working before deeper validation

This is a startup and smoke-test walkthrough, not the root launch authority and not an implementation spec.

## Document Role

Use this guide to:

- bind an explicit runtime and storage root
- start the backend on a known port
- prove basic route and page-shell reachability for the review, Document Trace, and Workbench Compare surfaces

Use [docs/nrc_adams/nrc_aps_ui_launch_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_ui_launch_runbook.md) first for:

- the canonical launch contract
- current-main preconditions
- allowlisted runtime-discovery rules
- the authoritative distinction between launch, compare prep, and broader operator validation

Use [frontend_UI_plans/wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md) for:

- same-checkout prep
- `tools/validate_wb_prep.py`
- populated Workbench Compare and Candidate B Trace follow-through

Use [frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md) for the broader manual validation pass after launch and prep succeed.

## Canonical Source Of Truth

The live implementation authority for the UI routes and startup surface is:

- [backend/main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py)
- [backend/app/api/review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)
- [backend/app/review_ui/static/index.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/index.html)
- [backend/app/review_ui/static/review.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/review.js)
- [backend/app/review_ui/static/document_trace.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.html)
- [backend/app/review_ui/static/document_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.js)
- [backend/app/review_ui/static/workbench_compare.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/workbench_compare.html)
- [backend/app/review_ui/static/workbench_compare.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/workbench_compare.js)
- [backend/app/review_ui/static/candidate_b_trace.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/candidate_b_trace.html)
- [backend/app/review_ui/static/candidate_b_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/candidate_b_trace.js)
- [tools/nrc_ui_launch.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/tools/nrc_ui_launch.py)
- [project6.ps1](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/project6.ps1)

This file is an operational reference layered on top of those sources.

## Live UI Routes

The backend serves these UI entrypoints:

- `/review/nrc-aps`
- `/review/nrc-aps/document-trace`
- `/review/nrc-aps/workbench-compare`
- `/review/nrc-aps/candidate-b-trace`

The backend also serves the review UI static assets under:

- `/review/nrc-aps/static`

Workbench-compare scope note:

- this guide covers route reachability and shell bring-up for `/review/nrc-aps/workbench-compare`
- populated compare validation requires same-checkout prep for baseline, Candidate A, and Candidate B sources
- the canonical populated prep flow now includes the validate-only same-checkout prep gate in `tools/validate_wb_prep.py`, including its emitted operator handoff metadata for prep/recovery
- use [frontend_UI_plans/wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md) for the dedicated prep, `tools/validate_wb_prep.py` gate, emitted operator handoff metadata, and populated compare validation flow
- after same-checkout prep, Candidate B follow-through should use the separate `Candidate B Trace` page rather than widening `document-trace`

## Preconditions

- Run from the repo or worktree root you intend to serve from.
- Use a runtime that already exists on disk and already contains:
  - `lc.db`
  - `storage\`
  - `local_corpus_e2e_summary.json` with `"passed": true`
- Current `main` does not guarantee that a populated local review runtime is already present under the checkout's allowlisted roots.
- If you are launching from a worktree, the shell-neutral helper can also discover and bind the shared repo-root review-runtime root when it exists.
- If no allowlisted runtime exists yet, stop and follow [docs/nrc_adams/local_corpus_e2e_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/local_corpus_e2e_runbook.md) or another approved restore path before using this walkthrough.
- Prefer a dedicated port for UI validation so you do not collide with another local API process.

## Step 1: Identify The Runtime You Want To Serve

Do not guess the runtime path and do not rely on `backend/.env` to pick one for you.

From the repo or worktree root, run:

```text
python ./tools/nrc_ui_launch.py discover
```

This is the copy-pasteable discovery command for both PowerShell and `cmd`.

## Step 2: Start A Dedicated API Instance With Explicit Binding

This is the preferred path for frontend/UI validation because it makes the runtime binding explicit.

From the repo or worktree root, launch the latest reviewable runtime on the default port `8098`:

```text
python ./tools/nrc_ui_launch.py serve --latest
```

Important rules:

- Keep this terminal open while you are using the UI.
- This path is preferred over relying on `backend/.env` because it prevents silent fallback to an older runtime.
- The helper binds `DB_INIT_MODE=none`, the selected runtime database, and the selected runtime-root search path for you.
- Once the backend is up, the review/document-trace run selector can switch across discovered summary-backed runtimes without restarting the process, as long as those runtimes live under the allowlisted review-runtime roots.

## Step 3: Confirm The Server Is Bound To The Intended Runtime

In a second terminal, verify the launch:

```text
python ./tools/nrc_ui_launch.py verify --latest
```

If this fails, do not trust the UI. Fix the runtime binding first.

## Step 4: Open The UI

If you want the URLs printed directly from the same shell-neutral helper, run:

```text
python ./tools/nrc_ui_launch.py urls
```

Main review UI:

- [http://127.0.0.1:8098/review/nrc-aps](http://127.0.0.1:8098/review/nrc-aps)

Document Trace UI:

- [http://127.0.0.1:8098/review/nrc-aps/document-trace](http://127.0.0.1:8098/review/nrc-aps/document-trace)

Workbench Compare UI:

- [http://127.0.0.1:8098/review/nrc-aps/workbench-compare](http://127.0.0.1:8098/review/nrc-aps/workbench-compare)
- after the review page loads, the header should expose `Workbench Compare` immediately before `Document Trace`

Candidate B Trace UI:

- `http://127.0.0.1:8098/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=<BUNDLE_ID>&fixture_id=<FIXTURE_ID>`
- preferred access path is via a Candidate B deep link from Workbench Compare after same-checkout prep
- the Workbench Compare deep link should carry `baseline_run_id`, `candidate_a_run_id`, `candidate_b_source_kind=bundle`, `candidate_b_bundle_id`, and `fixture_id` so the Candidate B Trace Back link and fixture navigation/status keep compare context
- direct bundle/fixture URLs can inspect one Candidate B fixture but do not prove compare-context preservation by themselves

If you want to open Document Trace directly for a specific run:

- `http://127.0.0.1:8098/review/nrc-aps/document-trace?run_id=<RUN_ID>`

Important:

- the numbered bring-up steps above are copy-pasteable as written
- the direct route examples below with `<RUN_ID>`, `<BUNDLE_ID>`, or `<FIXTURE_ID>` are parameterized follow-up URLs, not the canonical launch commands

## Step 5: Basic UI Smoke Checklist

On `/review/nrc-aps`:

- page loads without a blank screen
- run selector is populated
- the selected/default run is reviewable
- the page renders the review surface rather than an error placeholder
- clicking `Document Trace` carries the selected `run_id` into the URL

On `/review/nrc-aps/document-trace`:

- run selector is populated
- document selector is populated after the run loads
- the source pane loads a document
- the provenance tabs render
- the following tab requests succeed when opened:
  - Extracted Units
  - Normalized Text
  - Indexed Chunks
  - Diagnostics

On `/review/nrc-aps/workbench-compare`:

- the page loads without a blank screen
- the review-page header link to `Workbench Compare` is present and ordered immediately before `Document Trace`
- the shell renders even if same-checkout compare sources are absent
- no raw local filesystem paths are displayed in the UI
- use the dedicated compare validation plan for populated compare testing

On `/review/nrc-aps/candidate-b-trace` after same-checkout prep:

- the page loads from a Candidate B deep link without a 500
- `annotated_pdf` is the default tab when present
- the annotated PDF renders inline in the page rather than forcing a download response
- `summary`, `raw_json`, and `raw_markdown` tabs render or degrade explicitly
- artifact availability/status cards are visible for annotated PDF, raw JSON, and raw Markdown
- unavailable artifact states are explicit read-only states
- the Back link preserves available Workbench Compare context
- fixture navigation/status is visible; multi-fixture source sets enable Previous/Next and one-fixture source sets render `Fixture 1 of 1` with disabled Previous/Next
- no raw local filesystem paths are displayed in the UI

## Step 6: Optional Parameterized API Cross-Checks

These are intentional follow-up checks after launch succeeds.
They require replacing `<RUN_ID>` and `<TARGET_ID>` with actual values from the running UI/API session.

After the UI is open, these are the minimum useful API checks:

```powershell
python -c "import urllib.request, json; run_id='<RUN_ID>'; data=json.loads(urllib.request.urlopen(f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents').read().decode()); print('documents=', len(data.get('documents', [])), 'default_target=', data.get('default_target_id'))"
```

For one visible target:

```powershell
python -c "import urllib.request, json; run_id='<RUN_ID>'; target_id='<TARGET_ID>'; url=f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/trace'; print(urllib.request.urlopen(url).status)"
```

```powershell
python -c "import urllib.request, json; run_id='<RUN_ID>'; target_id='<TARGET_ID>'; url=f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/extracted-units'; data=json.loads(urllib.request.urlopen(url).read().decode()); print('units=', len(data.get('units', [])))"
```

## Step 7: Stop The Server

When you are done, stop the API with `Ctrl+C` in the terminal where `uvicorn` is running.

If you set process-local environment variables in that shell only, closing the shell is sufficient cleanup.

## Optional: Wrapper Reference

[project6.ps1](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/project6.ps1) contains API startup helpers and database/storage binding helpers, but the explicit `uvicorn` path above is the most direct operational reference for frontend/UI bring-up because it makes the runtime choice visible.

## Troubleshooting

If `/health` works but the review UI shows no runs:

- the server is probably pointed at the wrong DB
- or the runtime you chose is not a passed local-corpus runtime

If the review UI loads but Document Trace shows no documents:

- check `/api/v1/review/nrc-aps/runs/<RUN_ID>/documents`
- confirm the selected run is reviewable and has targets

If static assets fail to load:

- confirm the server was started from the repo backend via `main:app`
- confirm `/review/nrc-aps/static/review.css` loads

If you need to validate a different frontend variant, such as an isolated worktree:

- repeat the same explicit-binding process
- but change `--app-dir` to that worktree's `backend` directory
- keep the same discipline: explicit `DATABASE_URL`, explicit `STORAGE_DIR`, no fallback guessing
