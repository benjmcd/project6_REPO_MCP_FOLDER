# NRC APS Frontend UI Operator Validation Guide

## Purpose

This document is the current operational reference for:

- starting the NRC APS frontend/backend on a chosen local port
- binding the server to an explicit runtime database and storage root
- validating `/review/nrc-aps`
- validating `/review/nrc-aps/document-trace`
- validating `/review/nrc-aps/workbench-compare` shell reachability after same-checkout compare prep
- validating `/review/nrc-aps/candidate-b-trace` follow-through from prepared compare selections
- validating runtime switching without restarting the backend
- validating bbox overlays across multiple runs, documents, and pages

This is the most practical end-to-end testing guide for the current UI surfaces.
It is not a backend implementation spec and it is not a replacement for the deeper planning docs.

## Canonical Validation Order

Use the current operator docs in this order:

1. Use [docs/nrc_adams/nrc_aps_ui_launch_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_ui_launch_runbook.md) for the canonical launch contract and current-main runtime preconditions.
2. Use [frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md) for the concise startup walkthrough and route/page-shell reachability checks.
3. If Workbench Compare or Candidate B Trace are in scope, use [frontend_UI_plans/wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md) for same-checkout prep and the `tools/validate_wb_prep.py` readiness gate.
4. Use this guide for the broader manual validation pass after launch and prep have already succeeded.

## When To Use This Document

Use this guide when you need to:

- load the frontend/UI locally
- verify the server is pointed at the intended runtime instead of silently falling back
- confirm that the review UI can switch across runs without restart
- confirm that Document Trace works for more than one run
- confirm that the workbench-compare page shell loads on the intended checkout/backend
- confirm bbox overlays render across more than one document and page

## Canonical Source Of Truth

The live implementation authority is the current repo code, not older frozen runtime examples.

Primary authority files:

- [backend/main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py)
- [backend/app/api/review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)
- [backend/app/services/review_nrc_aps_catalog.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_catalog.py)
- [backend/app/services/review_nrc_aps_runtime.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime.py)
- [backend/app/services/review_nrc_aps_runtime_db.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_runtime_db.py)
- [backend/app/review_ui/static/index.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/index.html)
- [backend/app/review_ui/static/review.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/review.js)
- [backend/app/review_ui/static/document_trace.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.html)
- [backend/app/review_ui/static/document_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.js)
- [backend/app/review_ui/static/document_trace.css](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.css)
- [backend/app/review_ui/static/workbench_compare.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/workbench_compare.html)
- [backend/app/review_ui/static/workbench_compare.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/workbench_compare.js)
- [backend/app/review_ui/static/workbench_compare.css](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/workbench_compare.css)
- [backend/app/review_ui/static/candidate_b_trace.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/candidate_b_trace.html)
- [backend/app/review_ui/static/candidate_b_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/candidate_b_trace.js)
- [backend/app/review_ui/static/candidate_b_trace.css](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/candidate_b_trace.css)
- [backend/app/services/review_nrc_aps_workbench_compare.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_workbench_compare.py)
- [backend/app/services/review_nrc_aps_candidate_b_trace.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/services/review_nrc_aps_candidate_b_trace.py)
- [tools/nrc_ui_launch.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/tools/nrc_ui_launch.py)

Related supporting docs:

- [docs/nrc_adams/nrc_aps_ui_launch_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_ui_launch_runbook.md)
- [frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md)
- [frontend_UI_plans/nrc_aps_review_ui_validation_plan.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_review_ui_validation_plan.md)
- [frontend_UI_plans/nrc_aps_document_trace_ui_validation_plan.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_document_trace_ui_validation_plan.md)
- [frontend_UI_plans/wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md)
- [frontend_UI_plans/bbox_overlay_execution_plan.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/bbox_overlay_execution_plan.md)

Important note:

- the older validation plans above contain useful expectations, but some of them are pinned to older audited runtimes
- this guide is the current operational procedure for day-to-day validation

## Scope Of Validation

This guide validates all of the following together:

- backend health and runtime binding
- run discovery
- review UI load
- review UI run switching
- Document Trace load
- Document Trace run switching
- workbench-compare page shell reachability
- Candidate B Trace follow-through from a populated compare selection
- source PDF loading
- tab loading for diagnostics, normalized text, indexed chunks, and extracted units
- source-to-units and units-to-source interaction sanity
- bbox overlay rendering across multiple documents and pages
- bbox visibility toggle behavior
- zoom and page-revisit stability
- theme legibility
- dense-document performance sanity

It does not attempt to validate:

- artifact generation
- write paths
- seeding
- donor worktrees
- experimental frontend variants unless you explicitly point the backend there

Important workbench-compare note:

- populated workbench-compare validation requires same-checkout prep for baseline, Candidate A, and Candidate B sources
- the canonical compare prep flow now includes the validate-only same-checkout prep gate in `tools/validate_wb_prep.py`
- once same-checkout prep exists, this guide should also validate Candidate B Trace follow-through from the compare page
- use [frontend_UI_plans/wb-compare-validation.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/wb-compare-validation.md) for the dedicated same-corpus compare prep, `tools/validate_wb_prep.py` gate, and populated operator-validation sequence

## Preconditions

- repo root: `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER`
- Python environment available for `python -m uvicorn`
- one or more successful local-corpus runtimes available under the checkout's allowlisted review-runtime roots
- current clean `main` may not ship a populated local review runtime by default
- if you are validating from a worktree, the shell-neutral helper may bind the shared repo-root review-runtime root when it exists
- the runtime(s) used for validation must already exist on disk and must not be generated by this validation pass

Required runtime contents:

- `lc.db`
- `storage\`
- `local_corpus_e2e_summary.json`

## Operator Notes

- If you recently changed frontend assets, hard-refresh the browser before trusting a visual result.
- Prefer a clean browser tab for each fresh validation pass.
- If you need to validate a different workspace variant, keep the same binding discipline and change only the backend `--app-dir`.

## Step 1: Identify The Runtime Root You Want To Bind

Do not guess the runtime and do not rely on `backend/.env`.

From the repo root:

```text
python ./tools/nrc_ui_launch.py discover
```

This is the copy-pasteable discovery command for both PowerShell and `cmd`.

## Step 2: Start A Dedicated Backend Instance With Explicit Binding

Pick a dedicated port if you do not want the default `8098`. Otherwise use the default shell-neutral path:

```text
python ./tools/nrc_ui_launch.py serve --latest
```

Rules:

- keep this terminal open
- do not trust ambient shell state
- do not trust `backend/.env` fallback for validation
- the helper binds the selected runtime DB plus the selected runtime-root search path for you
- this single process should now support switching across discovered review runtimes without restart

## Step 3: Prove The Binding Before Opening The UI

Run the shell-neutral verification step:

```text
python ./tools/nrc_ui_launch.py verify --latest
```

If you want the route URLs printed from the same helper, run:

```text
python ./tools/nrc_ui_launch.py urls
```

For one additional static-asset sanity check after the main verify command, run:

```text
python -c "import urllib.request; js=urllib.request.urlopen('http://127.0.0.1:8098/review/nrc-aps/static/document_trace.js').read().decode('utf-8'); print('showBboxes' in js, 'pdf-bbox-marker' in js, 'ensureExtractedUnitsLoaded' in js)"
```

Do not proceed with bbox validation if that last command does not print `True True True`.

## Step 4: Open The UI

Main review UI:

- [http://127.0.0.1:8098/review/nrc-aps](http://127.0.0.1:8098/review/nrc-aps)

Document Trace:

- [http://127.0.0.1:8098/review/nrc-aps/document-trace](http://127.0.0.1:8098/review/nrc-aps/document-trace)

Workbench Compare:

- [http://127.0.0.1:8098/review/nrc-aps/workbench-compare](http://127.0.0.1:8098/review/nrc-aps/workbench-compare)
- from `/review/nrc-aps`, the header should also expose `Workbench Compare` immediately before `Document Trace`

Candidate B Trace:

- `http://127.0.0.1:8098/review/nrc-aps/candidate-b-trace?candidate_b_bundle_id=<BUNDLE_ID>&fixture_id=<FIXTURE_ID>`
- the preferred operator path is still to reach this page from a Candidate B deep link inside Workbench Compare after same-checkout prep

Direct run link:

- `http://127.0.0.1:8098/review/nrc-aps/document-trace?run_id=<RUN_ID>`

Important:

- the numbered launch and verification steps above are copy-pasteable as written
- the direct-route examples below with `<RUN_ID>`, `<BUNDLE_ID>`, or `<FIXTURE_ID>` are parameterized follow-up URLs, not the canonical launch commands

## Step 5: Minimum API Cross-Checks

Before doing deeper browser validation, confirm one run and one target are actually wired correctly.

These are intentional follow-up checks after launch succeeds.
They require replacing `<RUN_ID>` and `<TARGET_ID>` with actual values from the running UI/API session.

Documents:

```powershell
python -c "import urllib.request, json; run_id='<RUN_ID>'; data=json.loads(urllib.request.urlopen(f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents').read().decode()); print('documents=', len(data.get('documents', [])), 'default_target=', data.get('default_target_id'))"
```

Trace manifest:

```powershell
python -c "import urllib.request; run_id='<RUN_ID>'; target_id='<TARGET_ID>'; print(urllib.request.urlopen(f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/trace').status)"
```

Extracted units:

```powershell
python -c "import urllib.request, json; run_id='<RUN_ID>'; target_id='<TARGET_ID>'; data=json.loads(urllib.request.urlopen(f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/extracted-units').read().decode()); units=data.get('units', []); print('units=', len(units), 'paged=', len([u for u in units if u.get('page_number') is not None]), 'bbox=', len([u for u in units if isinstance(u.get('bbox'), list) and len(u.get('bbox')) == 4]))"
```

Optional helper for selecting diverse bbox documents within a run:

```text
python -c "import json, urllib.request; run_id='<RUN_ID>'; docs=json.loads(urllib.request.urlopen(f'http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents').read().decode())['documents']; rows=[]; [rows.append((len([u for u in payload.get('units', []) if isinstance(u.get('bbox'), list) and len(u.get('bbox')) == 4]), len(set(u.get('page_number') for u in payload.get('units', []) if u.get('page_number') is not None)), doc.get('accession_number'), doc['target_id'])) for doc in docs[:25] for payload in [json.loads(urllib.request.urlopen(f\"http://127.0.0.1:8098/api/v1/review/nrc-aps/runs/{run_id}/documents/{doc['target_id']}/extracted-units\").read().decode())]]; [print(f'bbox={bbox_count} pages={page_count} accession={accession} target={target_id}') for bbox_count, page_count, accession, target_id in sorted(rows, reverse=True)[:10]]"
```

## Step 6: Review UI Validation

On `/review/nrc-aps`, verify:

- page loads without a blank screen
- run selector is populated
- at least 2 reviewable runs are available if the API reports them
- the currently selected run is coherent with the API default
- `Document Trace` launches the selected `run_id`
- no blocking console errors
- no critical failed network requests

On `/review/nrc-aps/workbench-compare`, verify:

- the page shell loads without a blank screen
- the review-page header link to `Workbench Compare` is present and ordered immediately before `Document Trace`
- the shared fixture/document identity summary renders as readable labeled metadata, not jammed label/value text
- on a populated high-noise fixture such as `ml17123a319`, the summary band stays bounded and scrolls internally instead of collapsing the compare tab pane
- the compare tab strip remains visible while tab content scrolls
- at a shorter-height viewport around 700px, the compare tab content still retains useful vertical depth
- unavailable-state copy renders cleanly when same-checkout compare sources are absent
- no raw local filesystem paths are displayed in the browser UI
- use the dedicated compare validation plan instead of improvising a demo-corpus prep flow
- theme switch remains usable if exercised

On `/review/nrc-aps/candidate-b-trace`, once same-checkout compare prep is present, verify:

- the page loads from a Candidate B deep link instead of requiring arbitrary path entry
- the identity summary reflects the selected `candidate_b_bundle_id` and `fixture_id`
- `annotated_pdf` is the default tab when the artifact is present
- the annotated PDF renders inline in the page rather than forcing a download response
- `summary`, `raw_json`, and `raw_markdown` tabs load coherently
- no raw local filesystem paths are displayed in the browser UI

If 3 or more reviewable runs are available:

- test at least 3 distinct runs, not just 2

## Step 7: Runtime Switching Validation

This is required. Do not stop at one run.

On `/review/nrc-aps`:

- select one reviewable run
- verify the page updates
- switch to a different reviewable run without restart
- verify the page updates to the new run cleanly
- confirm there is no stale mismatch between selector state and fetched payloads

Then open Document Trace from at least 2 different runs.

Required pass condition:

- run switching works without restarting the backend

## Step 8: Document Trace Validation

For each tested run in Document Trace, verify:

- run selector is populated
- document selector becomes populated after run load
- default target loads
- source PDF fetch succeeds
- `Extracted Units` tab loads
- `Normalized Text` tab loads or degrades clearly if absent
- `Indexed Chunks` tab loads or degrades clearly if absent
- `Diagnostics` tab loads
- clicking an extracted-unit jump control moves the source viewer to the expected page when such controls are present
- changing the visible source page updates the extracted-units page scope for that page
- no blocking console errors
- no critical failed network requests

Do this for more than one run.

## Step 9: BBox Overlay Validation

This is required if the current frontend build is expected to contain bbox overlays.

### Target Selection Rules

Do not validate only one document.

For each tested run, choose multiple representative documents.
Target at minimum:

- 3 documents if the run has enough variety
- otherwise 2 documents and record the limitation

Prefer a spread such as:

- one bbox-rich document
- one sparse or edge-case-looking document
- one materially different document by size, layout, density, or document type

### Page Selection Rules

Do not validate only the default page.

For each selected document:

- test at least 2 pages when possible
- include one page where bbox-bearing units should render
- include one different page with fewer units or different structure if available

### What To Verify

For each selected document and tested page:

- source PDF is visible
- bbox toggle exists
- toggling bbox visibility off hides markers
- toggling bbox visibility on restores markers when renderable bbox data exists
- bbox markers are visible when bbox-capable units exist
- overlays are anchored to the correct page
- overlays remain after page changes
- overlays resync after zoom changes
- overlays remain coherent after repeated zoom in/out, not just one zoom action
- overlays remain coherent after leaving a page and revisiting it
- overlays do not disappear on run switch or document switch unless the new page truly lacks bbox-capable data
- no blocking console/page errors occur during rendering

Required DOM-level expectations:

- `.pdf-page-shell` exists
- `.pdf-page-overlay` exists
- `.pdf-bbox-marker` exists when bbox-capable units exist and rendering should occur

### What Counts As Failure

Treat these as failures until classified:

- no bbox markers created at all
- bbox markers created but not visible
- bbox markers created on the wrong page
- bbox markers created with zero geometry
- bbox markers disappear permanently after rerender
- one document works and another does not
- bbox toggle changes state but does not affect visibility
- overlays drift after repeated zooming or page revisit

### What Does Not Automatically Count As Failure

These are only failures if data and page context prove they should render:

- a page with no bbox-bearing units has no markers
- a document with no renderable bbox data shows no markers
- near-full-page noise boxes are suppressed
- a document with bbox data on one page but not another shows markers only on the page that actually has renderable bbox units

## Step 10: Multi-Run / Multi-Document Minimum Matrix

Minimum acceptable manual validation:

- 2 reviewable runs
- 2 documents per run
- 2 pages per document when possible
- at least 1 extracted-unit jump interaction on each tested run when available
- at least 1 zoom/revisit cycle on each tested run

Preferred validation:

- 3 reviewable runs when available
- 3 documents per run when available
- 2 pages per document when possible

Do not declare frontend/UI success from:

- one run only
- one document only
- one page only
- one zoom state only

## Step 11: Automated Test Commands

Focused review/document-trace regression:

```powershell
python -m pytest backend\tests\test_review_nrc_aps_catalog.py backend\tests\test_review_nrc_aps_api.py backend\tests\test_review_nrc_aps_document_trace_api.py backend\tests\test_review_nrc_aps_document_trace_service.py backend\tests\test_review_nrc_aps_page.py backend\tests\test_review_nrc_aps_document_trace_page.py -q
```

Light page-only check:

```powershell
python -m pytest backend\tests\test_review_nrc_aps_page.py backend\tests\test_review_nrc_aps_document_trace_page.py -q
```

Important note:

- static/page tests are regression guards
- they are not proof of live browser correctness for bbox overlays or runtime switching

## Step 12: Performance And Legibility Sanity

For at least one bbox-dense document:

- verify the page remains usable after initial overlay render
- verify zooming does not cause obvious UI lockup or multi-second visible stalls
- verify repeated rerender does not leave obvious overlay duplication or DOM explosion symptoms

For theme sanity:

- exercise both light and dark theme when practical
- confirm controls, tabs, and bbox markers remain visible enough to validate behavior
- if theme switching is unavailable in the current surface, record that explicitly

## Step 13: Failure Classification

If something fails, classify it before editing anything:

- setup or binding issue
- wrong runtime selected
- runtime-data issue
- run-discovery issue
- per-run DB routing issue
- frontend stale-state issue
- document-trace UI issue
- bbox overlay rendering issue
- browser-only limitation

Do not patch around symptoms before classifying the failure.

## Step 14: Evidence Capture

For any serious issue, capture enough evidence to make the result actionable:

- exact URL
- run id
- target id
- page number
- whether bbox-capable units existed for that page
- relevant console error or failed request
- whether the issue reproduces on another run/document/page

Do not declare a global failure from one isolated page unless the same class of failure reproduces or the code path clearly proves it is universal.

## Step 15: Pass Criteria

The current frontend/UI should be considered acceptable only if:

- backend health is good
- the intended runtime binding is explicit and verified
- `/review/nrc-aps` loads and can switch across runs without restart
- `/review/nrc-aps/document-trace` loads and can switch across runs without restart
- document selector updates correctly per run
- source PDF loads for tested documents
- core trace tabs work or degrade explicitly
- extracted-unit/source sync behavior works for the tested runs when the interaction is available
- bbox overlays render across the tested multi-run, multi-document, multi-page set when renderable bbox data exists
- bbox visibility toggle behaves correctly on the tested set
- repeated zoom and page revisit do not obviously break overlay rendering
- no critical console or network errors remain

## Step 16: Fail / Block Criteria

Stop and treat the validation as failed or blocked if:

- the server binding cannot be proven
- the backend is serving stale or wrong frontend assets
- run switching only works after restart
- Document Trace works for only one run
- bbox overlays work for only one document shape and fail on another without explanation
- extracted-unit/source sync works only once and then falls out of sync on revisit
- repeated zoom or rerender breaks overlays and the behavior is reproducible
- the UI silently falls back to an unintended runtime

## Step 17: Shutdown

When done:

- stop the `uvicorn` process with `Ctrl+C`
- or stop the dedicated process explicitly if it was background-launched

If environment variables were shell-local, closing the shell is sufficient cleanup.
