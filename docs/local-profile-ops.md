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

## RC2 Public Connector Lifecycle Posture

This posture note is for the RC2-targeted public connector slice only: ScienceBase public/MCS and Senate LDA anonymous. It does not activate the selected analytics-only RC1 profile, and it does not change the empty owner-selected gates in `config/release_readiness.yaml`.

Connector restart recovery is operator-resume-driven in RC2. After an executor crash or process loss, an operator rechecks run status and posts `POST /api/v1/connectors/runs/{connector_run_id}/resume`; RC2 does not run an automatic orphan-run or lease-expiry reaper. A run left `running` with an expired lease is detectable through the connector run status payload and persisted lease owner/token/expiry fields.

The RC2 local posture is single worker and single process. Connector leases are single-process safe and prevent duplicate executor authority inside that posture. Multi-worker concurrent execution, cross-process atomic lease acquisition, and high availability are not RC2 claims.

## Artifact-Baked Build Identity

Build the app image from the repo root with the scripted Docker build path:

```powershell
python .\scripts\build_app_image.py --tag method-aware-app:local
```

The helper resolves the current source identity with `git rev-parse HEAD`, validates it as a 40-character SHA, and passes it to `Dockerfile.app` as `--build-arg PROJECT6_SOURCE_SHA=<sha>`. `Dockerfile.app` promotes that build arg to the runtime `PROJECT6_SOURCE_SHA` env var, so `/ready` reports the same SHA at `build.source_sha` instead of `unknown`.

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
