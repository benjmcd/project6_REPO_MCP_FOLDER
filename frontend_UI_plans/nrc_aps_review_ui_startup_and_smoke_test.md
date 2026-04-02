# NRC APS Review UI Startup And Smoke Test

## Purpose

This document is the operational reference for bringing up the NRC APS review UI and the separate Document Trace UI against an explicit local runtime on a chosen port.

Use this when you need to:

- start the backend with a known `DATABASE_URL` and `STORAGE_DIR`
- avoid accidental fallback to `backend/.env`
- open the review UI in a browser
- open the Document Trace UI for a specific run
- switch between discovered summary-backed review runtimes from the UI without restarting the backend
- confirm the basic frontend/API path is working before deeper validation

This is a startup and smoke-test guide, not an implementation spec.

## Canonical Source Of Truth

The live implementation authority for the UI routes and startup surface is:

- [backend/main.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/main.py)
- [backend/app/api/review_nrc_aps.py](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/api/review_nrc_aps.py)
- [backend/app/review_ui/static/index.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/index.html)
- [backend/app/review_ui/static/review.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/review.js)
- [backend/app/review_ui/static/document_trace.html](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.html)
- [backend/app/review_ui/static/document_trace.js](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/review_ui/static/document_trace.js)
- [project6.ps1](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/project6.ps1)

This file is an operational reference layered on top of those sources.

## Live UI Routes

The backend serves these UI entrypoints:

- `/review/nrc-aps`
- `/review/nrc-aps/document-trace`

The backend also serves the review UI static assets under:

- `/review/nrc-aps/static`

## Preconditions

- Run from the repo root:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER`
- Use a runtime that already exists on disk and already contains:
  - `lc.db`
  - `storage\`
  - `local_corpus_e2e_summary.json` with `"passed": true`
- Prefer a dedicated port for UI validation so you do not collide with another local API process.

## Step 1: Identify The Runtime You Want To Serve

Do not guess the runtime path and do not rely on `backend/.env` to pick one for you.

From the repo root, run:

```powershell
@'
from pathlib import Path
import json

root = Path(r"C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e")
candidates = []
for path in root.iterdir():
    if not path.is_dir():
        continue
    summary = path / "local_corpus_e2e_summary.json"
    if not summary.exists():
        continue
    try:
        payload = json.loads(summary.read_text(encoding="utf-8"))
    except Exception:
        continue
    if payload.get("passed") is True:
        candidates.append((path.name, str(payload.get("run_id") or ""), path))

if not candidates:
    raise SystemExit("No successful local-corpus runtime found.")

name, run_id, path = sorted(candidates, reverse=True)[0]
print(f"runtime_dir={path}")
print(f"run_id={run_id}")
print(f"database={path / 'lc.db'}")
print(f"storage={path / 'storage'}")
'@ | python -
```

Record the printed values. You will use them in the next steps.

## Step 2: Start A Dedicated API Instance With Explicit Binding

This is the preferred path for frontend/UI validation because it makes the runtime binding explicit.

From the repo root, set the runtime values you just discovered:

```powershell
$RuntimeDb = "C:\ABSOLUTE\PATH\TO\lc.db"
$RuntimeStorage = "C:\ABSOLUTE\PATH\TO\storage"
$Port = 8098
```

Then launch the backend from the repo's backend directory:

```powershell
$env:DATABASE_URL = "sqlite:///$($RuntimeDb -replace '\\','/')"
$env:STORAGE_DIR = $RuntimeStorage
$env:DB_INIT_MODE = "none"
py -3.11 -m uvicorn main:app --host 127.0.0.1 --port $Port --app-dir "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend"
```

Important rules:

- Keep this terminal open while you are using the UI.
- This path is preferred over relying on `backend/.env` because it prevents silent fallback to an older runtime.
- `DB_INIT_MODE=none` is intentional here because the runtime DB already exists.
- Once the backend is up, the review/document-trace run selector can switch across discovered summary-backed runtimes without restarting the process, as long as those runtimes live under the allowlisted review-runtime roots.

## Step 3: Confirm The Server Is Bound To The Intended Runtime

In a second terminal, verify the API is up:

```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8098/health').read().decode())"
```

Then confirm the run list is populated:

```powershell
python -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8098/api/v1/review/nrc-aps/runs').read().decode()); print('runs=', len(data.get('runs', [])), 'default=', data.get('default_run_id'))"
```

If this returns zero runs, do not trust the UI. Fix the runtime binding first.

## Step 4: Open The UI

Main review UI:

- [http://127.0.0.1:8098/review/nrc-aps](http://127.0.0.1:8098/review/nrc-aps)

Document Trace UI:

- [http://127.0.0.1:8098/review/nrc-aps/document-trace](http://127.0.0.1:8098/review/nrc-aps/document-trace)

If you want to open Document Trace directly for a specific run:

- `http://127.0.0.1:8098/review/nrc-aps/document-trace?run_id=<RUN_ID>`

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

## Step 6: Minimal API Cross-Checks

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
