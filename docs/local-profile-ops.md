# Local Profile Ops

> **2026-09-04 current pointer:** The local-profile acceptance contract remains
> unchanged. Public ScienceBase Layer 3 analysis and result-value inspection are
> bounded experimental default-off subfeatures under the selected profile, not
> additions to the base local harness. Their source defaults are
> `LAYER3_PUBLIC_DATASET_ANALYSIS_ENABLED=false` and
> `LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED=false`; values require both
> flags plus newest admitted `sciencebase/public_api` provenance, provenance
> co-display, and storage-reference exclusion. See
> [MASTER_CONTEXT](MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation).

This runbook covers the base local operational subcontracts for `local_expert`. The current selected 0.3.0 final profile also includes `public_connectors` and `sec_xbrl_offline` overlays; use `config/support_matrix.yaml` and `docs/support-matrix-local-expert.md` as the current capability-status authority.

## Profile

- `DEPLOYMENT_MODE=local`
- `AUTH_OWNER=none`
- SQLite database
- local filesystem storage
- no proxy
- no OCR, model/agent, provider, HA, keyed connector, or nonlocal activation in the base local harness

`config/release_readiness.yaml` remains profile-neutral. Its `owner_selected_profile_specific_gates` list stays empty.

## Public Connector Lifecycle Posture

This posture note is for the public connector slice selected by the current local profile: ScienceBase public/MCS, Senate LDA anonymous metadata, World Bank Indicators anonymous metadata, BLS Public Data API v1 anonymous metadata, OECD SDMX anonymous metadata, and CFTC COT anonymous public report rows. It does not change the empty owner-selected gates in `config/release_readiness.yaml`, and it does not broaden connector support into keyed connectors, HA, nonlocal deployment, real provider delivery, OCR, SEC value reveal, or default-on SEC live network behavior.

Connector restart recovery is operator-resume-driven. After an executor crash or process loss, an operator rechecks run status and posts `POST /api/v1/connectors/runs/{connector_run_id}/resume`; the selected profile does not run an automatic orphan-run or lease-expiry reaper. A run left `running` with an expired lease is detectable through the connector run status payload and persisted lease owner/token/expiry fields.

The local connector posture is single worker and single process. Connector leases are single-process safe and prevent duplicate executor authority inside that posture. Multi-worker concurrent execution, cross-process atomic lease acquisition, and high availability are not current selected-profile claims.

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
