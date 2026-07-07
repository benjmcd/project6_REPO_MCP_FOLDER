# CI Proof Policy

> Documentation only. Recorded against `project6-origin/main` at
> `abd8c3f8ac2b2545fda8b88d46aa916a22b626e8`.
> Verify against the live workflow before relying on job inventory or line numbers.

## 2026-07-07 supersession note (M-RELEASE-GATE-F5)

`release-gate` now depends on eight jobs:

1. `release-lock-install`
2. `backend-layer3-api`
3. `backend-coverage`
4. `backend-migrations-postgres`
5. `sec-xbrl-arelle-provisioning`
6. `root-tests`
7. `nrc-aps-ocr`
8. `test`

The policy's requested strict guard now exists in
`backend/tests/test_ci_coverage_completeness.py`:
`test_release_gate_job_runs_manifest_runner_after_manifest_ci_jobs` asserts that
the workflow `release-gate.needs` exact set equals
`RELEASE_GATE_AGGREGATED_JOBS`, and the existing loop continues to require each
job's `needs['<job>'].result` check in the shell gate.

## Release-Gate Blocking Jobs

`release-gate` currently depends on five jobs:

1. `release-lock-install` - release closure, build identity, and Docker image checks.
2. `backend-layer3-api` - fan-in over the four `backend-layer3-api-shard` jobs.
3. `backend-coverage` - Layer 3 API coverage with the enforced 90 percent floor.
4. `backend-migrations-postgres` - Alembic plus Layer 3 migration and 3C golden-path checks against PostgreSQL.
5. `sec-xbrl-arelle-provisioning` - offline taxonomy provisioning, Arelle readiness, and targeted SEC-XBRL tests.

`sec-xbrl-arelle-provisioning` is intentionally an A7, sidecar, and provisioning
subset. It is not the exhaustive SEC-XBRL test inventory; the backend shards plus
the RC3 exhaustive list cover the tracked `backend/tests/test_sec_xbrl_*.py`
files.

The deterministic Sublayer-3C analytical chain is therefore release-gate-blocking:
`backend-migrations-postgres` runs `tests/test_layer3_3c_golden_path.py`, which imports
and invokes `generate_analysis_product` and asserts provenance and output payload details.

## Running But Non-Blocking Jobs

These jobs run on push and PR, but are not release-gate dependencies:

- `nrc-aps-ocr` - Tesseract-backed document-processing proof.
- `root-tests` - fan-in over the four repo-root pytest shards.
- `test` - fan-in over the four Playwright shards.

That split is deliberate. These lanes provide signal, but they are more environment-coupled
than the release-gate jobs. Promoting any of them to blocking should be a separate CI policy
decision, not a drive-by workflow edit.

CI also blocks SEC/NRC live network proof. Live-network proof remains operator-only; CI proof
must use isolated, synthetic, offline fixtures.

## If A Lane Is Promoted To Blocking

Changing release-gate membership requires synchronized edits:

1. `.github/workflows/playwright.yml` `release-gate.needs`.
2. The `release-gate` shell loop that checks each dependency result.
3. `RELEASE_GATE_AGGREGATED_JOBS` in `backend/tests/test_ci_coverage_completeness.py`.
4. Any relevant `config/release_readiness.yaml` entry and corresponding expected coverage in
   `backend/tests/test_ci_coverage_completeness.py`.

The current tests verify the expected jobs appear in the release-gate block and result loop.
If the membership changes, add or preserve a strict set-equality assertion over the YAML `needs`,
the shell loop, and `RELEASE_GATE_AGGREGATED_JOBS` so an extra or omitted dependency cannot become
silently non-blocking.

## Proof Artifacts

Checked-in `tests/reports/*.json` files are operator snapshots, not CI outputs. See
`tests/reports/PROVENANCE.md`. CI does not currently commit a per-run, commit-stamped proof artifact.
