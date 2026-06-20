# Local Profile Ops

This runbook covers the selected L05 operational subcontracts for the analytics-only RC1 `local_expert` profile.

## Profile

- `DEPLOYMENT_MODE=local`
- `AUTH_OWNER=none`
- SQLite database
- local filesystem storage
- no proxy
- no overlay, connector, SEC, OCR, model/agent, provider, or nonlocal activation

`config/release_readiness.yaml` remains profile-neutral. Its `owner_selected_profile_specific_gates` list stays empty.

## CI Acceptance

Run the local posture acceptance harness from the repo root (`scripts/local_profile_acceptance.py`):

```powershell
python .\scripts\local_profile_acceptance.py --work-dir .\tmp\local-profile-acceptance --json
```

The work directory must be empty. The harness fails closed instead of reusing hidden workstation state.

The harness uses an isolated SQLite DB and storage tree, starts the FastAPI app in fresh Python child processes, and proves:

- install/run: a clean local runtime reaches `/ready`, uploads CSV, profiles variables, applies transforms, annotates, runs `cross_correlation`, and records artifacts, assumptions, caveats, and CSV source-fidelity fields.
- restart-survival: the same DB and storage tree are re-opened by a fresh app process, then the analysis run and dataset source-fidelity fields re-read identically.
- backup/restore: the SQLite DB and storage tree are copied to a backup point, restored into the configured isolated local runtime path, and the restored app re-reads the same analysis run, `content_hash`, and artifact hashes.
- backup/restore total-loss check: the original runtime is relocated before restore; the SQLite DB and storage tree are restored from backup into the configured local paths, then dataframe-backed profile reads prove dataset files are loaded from the restored storage tree.
- UPGRADE: not claimed.

The CI hook is `backend/tests/test_release_local_profile_operational_acceptance.py`, which invokes the harness in a pytest temp directory.

## Manual Local Restart

For an operator-style manual check, run the same harness first. It is the authoritative scripted acceptance path.

For a real process restart outside CI, use equivalent local env vars and a uvicorn process:

```powershell
$env:DEPLOYMENT_MODE = "local"
$env:AUTH_OWNER = "none"
$env:DB_INIT_MODE = "migrate"
$env:DATABASE_URL = "sqlite:///C:/path/to/local/method_aware.db"
$env:STORAGE_DIR = "C:/path/to/local/storage"
py -3.11 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Start from `backend/` for the manual uvicorn command. Stop and restart the process, then re-read the analysis run with `GET /api/v1/analysis-runs/{id}` and the dataset with `GET /api/v1/datasets/{id}`. The scripted harness performs the same authority check with fresh app processes so CI does not depend on a long-running local server.
