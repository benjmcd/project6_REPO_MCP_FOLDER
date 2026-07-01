# CI Proof Policy

> Documentation only. Recorded against `project6-origin/main` at
> `abd8c3f8ac2b2545fda8b88d46aa916a22b626e8`.
> Verify against the live workflow before relying on job inventory or line numbers.

## Release-Gate Blocking Jobs

`release-gate` currently depends on five jobs:

1. `release-lock-install` - release closure, build identity, and Docker image checks.
2. `backend-layer3-api` - fan-in over the four `backend-layer3-api-shard` jobs.
3. `backend-coverage` - Layer 3 API coverage with the enforced 90 percent floor.
4. `backend-migrations-postgres` - Alembic plus Layer 3 migration and 3C golden-path checks against PostgreSQL.
5. `sec-xbrl-arelle-provisioning` - offline taxonomy provisioning, Arelle readiness, and targeted SEC-XBRL tests.

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
